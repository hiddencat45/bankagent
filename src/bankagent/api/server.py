"""本地单进程 Demo 的 FastAPI 接线；认证结果只来自服务端。"""
import threading
from datetime import datetime, timedelta
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from starlette.background import BackgroundTask
from starlette.concurrency import iterate_in_threadpool

from bankagent.agent.agent_graph import BankAgentRuntime, SG_TZ, build_graph
from bankagent.agent.agent_security import ChallengeError, ChallengeStore, compute_operation_hash
from bankagent.banking.bank_backend import configure_backend, get_balance, reset_demo_data
from bankagent.banking.bank_types import TrustedContext
from bankagent.banking.data.generator import REFERENCE_DATE, build_demo_data
from bankagent.agent.scenarios.bills import configure_clock
from bankagent.agent.scenarios.subscription import configure_clock as subscription_clock
from bankagent.api import events
from bankagent.api.contracts import ApiError, parse_chat_request
from bankagent.api.session import DemoSessionStore

# 仅由服务端在归属、操作哈希与原授权校验后产生，不接收客户端执行入口。
_RETRY_EXECUTION = object()
_FORM_SUBMISSION = object()
# Public choice references are NOT user/account IDs. Only this server mapping grants identity.
DEMO_CUSTOMERS = {
    'primary': ('默认演示客户', 'user-001', 'account-001'),
    'zhang-wei': ('张伟（演示客户）', 'user-002', 'account-002'),
}


class Service:
    def __init__(self, *, clock=None, authenticate=None, candidate_model=None,
                 registry=None, phraser=None, query_model=None, database_path=None, allow_demo_customers=False):
        # 固定业务参考日，挑战仍随真实经过时间过期。
        started = datetime.now(SG_TZ)
        reference = datetime.combine(REFERENCE_DATE, datetime.min.time(), SG_TZ).replace(hour=12)
        if database_path is not None and clock is None:
            from bankagent.banking.storage import SQLiteStore
            clock = SQLiteStore(database_path, build_demo_data()).business_now
        self.clock = clock or (lambda: reference + (datetime.now(SG_TZ) - started))
        self.candidate_model = candidate_model
        self.registry = registry
        self.phraser = phraser
        self.query_model = query_model
        self.authenticate = authenticate or (lambda context, otp: False)
        self.lock = threading.RLock()
        self.running = threading.Lock()
        self.sessions = DemoSessionStore(lock=self.lock)
        self.challenges = ChallengeStore(lock=self.lock, clock=self.clock)
        self.challenge_by_thread = {}
        self.saver = InMemorySaver()
        self.runtime = BankAgentRuntime(challenges=self.challenges, clock=self.clock,
                                        candidate_model=self.candidate_model, registry=registry,
                                        phraser=phraser, query_model=query_model)
        self.graph = build_graph(self.runtime, checkpointer=self.saver)
        configure_clock(clock=self.clock)
        subscription_clock(clock=self.clock)
        configure_backend(data_factory=build_demo_data, lookup_authorization=self.challenges.lookup,
                          operation_hash=compute_operation_hash, lock=self.lock, clock=self.clock,
                          database_path=database_path, allow_demo_customers=allow_demo_customers)

    def reserve(self):
        if not self.running.acquire(blocking=False):
            raise ApiError('RUN_BUSY', '演示服务正在办理业务，请稍后重试。', 409)

    def prepare(self, authorization, payload):
        session = self.sessions.resolve(authorization)
        req = parse_chat_request(payload)
        if req.is_resume and req.thread_id is None:
            raise ApiError('INVALID_REQUEST', '恢复时必须提供 thread_id。', 400)
        thread = req.thread_id or f'conv-{uuid4().hex}'
        if req.thread_id:
            self.sessions.require_thread(session, thread)
        self.reserve()
        try:
            cfg = {'configurable': {'thread_id': thread}}
            snapshot = self.graph.get_state(cfg)
            state = snapshot.values or {}
            waiting = [i for task in snapshot.tasks for i in task.interrupts]
            if req.is_resume:
                cid = req.resume.challenge_id
                record = self.challenges.lookup(cid)
                current_cid = self.challenge_by_thread.get(thread)
                if not record or cid != current_cid:
                    raise ApiError('CHALLENGE_INVALID', '确认卡不存在或已失效。', 409)
                context = TrustedContext(session.user_id, session.account_id, state['request_id'])
                expected = compute_operation_hash(context, state['operation'], state['params'])
                if state.get('operation_hash') != expected:
                    raise ApiError('CHALLENGE_STATE_MISMATCH', '操作参数已变化，请重新发起。', 409)
                authenticated = False
                if record['risk_level'] == 'RED' and req.resume.decision == 'approve' and record['decision'] == 'PENDING':
                    try:
                        authenticated = self.authenticate(context, req.resume.otp) is True
                    except Exception:
                        raise ApiError('CHALLENGE_INVALID', '认证服务暂时不可用，尚未执行。', 409) from None
                settled = self.challenges.decide(challenge_id=cid, user_id=session.user_id,
                    request_id=context.request_id, operation_hash=expected,
                    decision=req.resume.decision, authenticated=authenticated)
                # 不把 decision 或凭证交给图/Checkpoint。
                graph_input = Command(resume=True) if snapshot.next else None
                # 已批准、绑定匹配、处于 FAILED 的写操作可以重试执行。
                # 不限定 operation：是否经过确认由 challenge_id 绑定、authorized
                # 与服务端 APPROVED 记录三者共同证明，与具体是哪个写操作无关。
                if (not snapshot.next and state.get('status') == 'FAILED'
                        and state.get('result', {}).get('operation') == state.get('operation')
                        and state.get('challenge_id') == cid and state.get('authorized') is True
                        and settled['decision'] == 'APPROVED'):
                    graph_input = _RETRY_EXECUTION
                request_id = state.get('api_request_id', context.request_id)
            else:
                if waiting:
                    record = self.challenges.lookup(waiting[0].value['challenge_id'])
                    if record and record['expires_at'] > self.clock():
                        if self.runtime.query_agent is None or state.get('input_source') == 'form':
                            raise ApiError('RUN_BUSY', '请先确认或拒绝当前操作。', 409)
                        self.challenges.decide(challenge_id=record['challenge_id'], user_id=session.user_id,
                            request_id=record['request_id'], operation_hash=record['operation_hash'], decision='reject')
                    if self.runtime.query_agent is not None:
                        self.runtime.query_agent.interrupt_task(
                            TrustedContext(session.user_id, session.account_id, state['request_id']), thread)
                    self.challenge_by_thread.pop(thread, None)
                    self.saver.delete_thread(thread)
                request_id = f'req-{uuid4().hex}'
                graph_input = {'user_id': session.user_id, 'account_id': session.account_id,
                               'request_id': request_id, 'api_request_id': request_id, 'message': req.message}
                if not req.thread_id:
                    self.sessions.register_thread(session, thread)
            return cfg, graph_input, state, dict(thread_id=thread, request_id=request_id, mode=self.runtime.mode)
        except ChallengeError as exc:
            self.running.release()
            raise ApiError(exc.code, '确认失败或已失效，请检查当前操作。', 409) from None
        except Exception:
            self.running.release()
            raise

    def prepare_form(self, authorization, payload):
        from bankagent.api.forms import parse_form
        candidate = parse_form(payload, self.runtime.registry)
        self.reserve()
        try:
            with self.lock:
                session = self.sessions.resolve(authorization)
                for old in self.sessions.family_sessions(session):
                    for thread in old.threads:
                        record = self.challenges.lookup(self.challenge_by_thread.get(thread))
                        if record and record['decision'] == 'PENDING' and record['expires_at'] > self.clock():
                            raise ApiError('RUN_BUSY', '请先确认或取消当前业务，再提交表单。', 409)
                thread, request_id = f'conv-{uuid4().hex}', f'req-{uuid4().hex}'
                self.sessions.register_thread(session, thread)
                state = {**candidate, 'user_id': session.user_id, 'account_id': session.account_id,
                         'request_id': request_id, 'input_source': 'form', 'message': '',
                         'status': 'PROCESSING', 'authorized': False}
                return ({'configurable': {'thread_id': thread}}, _FORM_SUBMISSION, state,
                        dict(thread_id=thread, request_id=request_id, mode=self.runtime.mode))
        except Exception:
            self.running.release()
            raise

    def stream(self, cfg, graph_input, previous, base):
        def frame(name, **kw):
            return events.format_sse(name, getattr(events, name)(**base, **kw))
        yield frame('status', step='started', status_value='PROCESSING')
        try:
            retry = graph_input is _RETRY_EXECUTION
            form = graph_input is _FORM_SUBMISSION
            if form:
                # Skip only language understanding; resolve, risk, confirmation and execution are shared.
                self.graph.update_state(cfg, previous, as_node='understand_intent')
            if retry:
                # 原执行失败已经走到 END，不能把它当作成功终态永远重放。
                # 仅调度原执行节点；保留身份/请求/参数/挑战，幂等键仍回查授权表。
                # 后端先查成功幂等结果；未落账时才复核授权期限/风险并写入。
                predecessor = ('interrupt_for_authentication' if previous['risk_level'] == 'RED'
                               else 'interrupt_for_confirmation')
                self.graph.update_state(cfg, {'status': 'PROCESSING', 'result': {}, 'response': ''},
                                        as_node=predecessor)
            if graph_input is None:
                state = previous  # 相同决定重放已完成结果，不再执行图。
            else:
                for _ in self.graph.stream(None if retry or form else graph_input, cfg, stream_mode='updates'):
                    pass
                snapshot = self.graph.get_state(cfg)
                state = snapshot.values
                waiting = [i for task in snapshot.tasks for i in task.interrupts]
                if waiting:
                    intr = waiting[0].value
                    self.challenge_by_thread[base['thread_id']] = intr['challenge_id']
                    record = self.challenges.lookup(intr['challenge_id'])
                    status = 'AWAITING_AUTHENTICATION' if intr['kind'] == 'STRONG_AUTH' else 'AWAITING_CONFIRMATION'
                    yield frame('status', step='awaiting_authentication' if intr['kind'] == 'STRONG_AUTH' else 'awaiting_confirmation', status_value=status)
                    context = TrustedContext(state['user_id'], state['account_id'], state['request_id'])
                    payload = {k: record[k] for k in ('operation', 'risk_level', 'challenge_id', 'operation_hash')}
                    payload['expires_at'] = record['expires_at'].isoformat()
                    # 展示字段由场景自己提供：server 不再按 operation 写死分支，
                    # 新增写操作只要实现 confirmation 钩子即可复用这条流。
                    spec = self.runtime.registry.spec_for_operation(record['operation'])
                    if spec is not None and spec.confirmation is not None:
                        payload.update(spec.confirmation(
                            operation=record['operation'],
                            params=record['params'],
                            candidate_params=state.get('candidate_params') or {},
                            context=context,
                        ))
                    for receipt in state.get('query_results') or []:
                        yield frame('card', card_type='result', payload=receipt)
                    yield frame('card', card_type='confirm', payload=payload)
                    yield frame('interrupt', kind=intr['kind'], challenge_id=record['challenge_id'],
                                operation_hash=record['operation_hash'], prompt='请确认本次操作；高风险操作需要独立认证。')
                    yield frame('done', status_value=status)
                    return
            status = state['status']
            result = state.get('result')
            if status == 'FAILED':
                code = result.get('error_code') if result else None
                code = code if code in {'MODEL_UNAVAILABLE', 'MODEL_OUTPUT_INVALID', 'QUERY_LIMIT_REACHED'} else 'BACKEND_UNAVAILABLE'
                yield frame('error', code=code, message_text=state.get('response') or '业务服务暂时不可用，请稍后重试。')
            else:
                if state.get('response'):
                    yield frame('message', text=state['response'])
            if status != 'FAILED' or state.get('query_results'):
                for result in state.get("query_results") or ([result] if result else []):
                    if result['operation'] == 'GET_BALANCE' and result['data']:
                        result = {**result, 'data': {k: result['data'][k] for k in ('balance_minor', 'currency')}}
                    if result['operation'] == 'QUERY_BILLS' and status == 'COMPLETED':
                        yield frame('card', card_type='evidence', payload={'operation': 'QUERY_BILLS', 'data': result['data']})
                    yield frame('card', card_type='result', payload=result)
            yield frame('status', step='finished', status_value=status)
            yield frame('done', status_value=status)
        except Exception:
            yield frame('error', code='BACKEND_UNAVAILABLE', message_text='办理中断，请核对结果后重试当前确认操作。')
            yield frame('done', status_value='FAILED')


def create_app(*, demo=False, clock=None, authenticate=None, candidate_model=None,
               registry=None, allow_lan=False, phraser=None, query_model=None, database_path=None):
    service = Service(clock=clock, authenticate=authenticate,
                      candidate_model=candidate_model, registry=registry, phraser=phraser, query_model=query_model,
                      database_path=database_path, allow_demo_customers=demo and not allow_lan)
    app = FastAPI(title='有度 · 本地银行 Demo')
    app.state.service = service

    @app.exception_handler(ApiError)
    async def api_error(request, exc):
        code = 'CONVERSATION_NOT_FOUND' if exc.code == 'THREAD_NOT_FOUND' else exc.code
        return JSONResponse({'code': code, 'message': exc.message}, status_code=exc.http_status)

    @app.middleware('http')
    async def local_only(request, call_next):
        host = request.url.hostname
        origin = request.headers.get('origin')
        # allow_lan 是显式降级：只为临时让同一局域网的人访问演示，默认关闭。
        # 打开后同一网段任何人都能拿到演示身份并操作演示账本。
        if (not allow_lan and host not in {'127.0.0.1', 'localhost', '::1'}) or (
            origin and (urlsplit(origin).netloc != request.headers.get('host') or urlsplit(origin).scheme != request.url.scheme)
        ):
            return JSONResponse({'code': 'INVALID_REQUEST', 'message': '仅允许本地同源演示。'}, status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/health')
    def health():
        try:
            result = get_balance(context=TrustedContext('user-001', 'account-001', 'health'))
            ok = result['status'] == 'COMPLETED'
        except Exception:
            ok = False
        interpreter = service.runtime.interpreter or service.query_model
        model = 'not_configured' if interpreter is None else ('ok' if interpreter.health() else 'unavailable')
        return {'status': 'ok' if ok and model != 'unavailable' else 'degraded', 'mode': service.runtime.mode,
                'backend': 'ok' if ok else 'unavailable', 'model': model}

    def require_demo(request):
        if not demo or request.client is None:
            raise ApiError('NOT_FOUND', '入口未开放。', 404)
        # allow_lan 只放宽「谁可以进来」，不放宽「是否演示模式」。
        if not allow_lan and request.client.host not in {'127.0.0.1', '::1', 'testclient'}:
            raise ApiError('NOT_FOUND', '入口未开放。', 404)

    @app.post('/demo/session')
    async def session(request: Request):
        require_demo(request)
        if await request.body() not in (b'', b'{}'):
            raise ApiError('INVALID_REQUEST', '会话入口不接受身份参数。', 400)
        service.reserve()
        try:
            issued = service.sessions.issue(user_id='user-001', account_id='account-001')
            return {'token': issued.token, 'mode': service.runtime.mode}
        finally:
            service.running.release()

    @app.get('/bank/accounts')
    def accounts(request: Request):
        from bankagent.banking.bank_backend import query_accounts
        current = service.sessions.resolve(request.headers.get('authorization'))
        context = TrustedContext(current.user_id, current.account_id, 'account-list')
        data = query_accounts(context=context)
        if data['status'] != 'COMPLETED':
            raise ApiError('ACCOUNT_NOT_ACCESSIBLE', '账户不可访问。', 403)
        return {**data['data'], 'current_account_ref': current.account_id}

    def require_local_customer_demo(request):
        require_demo(request)
        if request.client.host not in {'127.0.0.1', '::1', 'testclient'}:
            raise ApiError('NOT_FOUND', '客户切换仅限本机演示。', 404)

    @app.get('/bank/bills')
    def account_bills(request: Request):
        from bankagent.banking.bank_backend import query_bills
        with service.lock:
            current = service.sessions.resolve(request.headers.get('authorization'))
            start = service.clock().date().replace(day=1)
            end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            return query_bills(context=TrustedContext(current.user_id, current.account_id, 'bill-list'),
                               start=start, end=end)

    @app.get('/demo/customers')
    def demo_customers(request: Request):
        require_local_customer_demo(request)
        current = service.sessions.resolve(request.headers.get('authorization'))
        choices = customer_choices()
        return {'customers': [{'customer_ref': ref, 'display_name': row[0]}
                              for ref, row in choices.items()],
                'current_customer_ref': next((ref for ref, row in choices.items()
                                               if row[1] == current.user_id), None)}

    def customer_choices():
        from bankagent.banking.bank_backend import demo_customer_choices
        return {**DEMO_CUSTOMERS, **demo_customer_choices()}

    @app.post('/demo/customer-session')
    async def customer_session(request: Request):
        require_local_customer_demo(request)
        try:
            payload = await request.json()
        except (ValueError, UnicodeDecodeError):
            raise ApiError('INVALID_REQUEST', '请选择演示客户。', 400) from None
        if (not isinstance(payload, dict) or set(payload) != {'customer_ref'}
                or not isinstance(payload['customer_ref'], str)
                or payload['customer_ref'] not in customer_choices()):
            raise ApiError('INVALID_REQUEST', '只能选择服务端提供的演示客户。', 400)
        service.reserve()
        try:
            with service.lock:
                current = service.sessions.resolve(request.headers.get('authorization'))
                for old in service.sessions.family_sessions(current):
                    for thread in old.threads:
                        record = service.challenges.lookup(service.challenge_by_thread.get(thread))
                        if record and record['decision'] == 'PENDING' and record['expires_at'] > service.clock():
                            raise ApiError('RUN_BUSY', '请先确认或取消当前业务，再切换演示客户。', 409)
                choices = customer_choices()
                if payload['customer_ref'] not in choices:
                    raise ApiError('ACCOUNT_NOT_ACCESSIBLE', '演示客户账户不可访问。', 403)
                _, user, account = choices[payload['customer_ref']]
                if get_balance(context=TrustedContext(user, account, 'demo-customer'))['status'] != 'COMPLETED':
                    raise ApiError('ACCOUNT_NOT_ACCESSIBLE', '演示客户账户不存在或归属不符。', 403)
                issued = service.sessions.issue(user_id=user, account_id=account)
                service.sessions.invalidate_family(current)
                return {'token': issued.token, 'mode': service.runtime.mode}
        finally:
            service.running.release()

    @app.post('/bank/account-session')
    async def account_session(request: Request):
        from bankagent.banking.bank_backend import query_accounts
        current = service.sessions.resolve(request.headers.get('authorization'))
        try:
            payload = await request.json()
        except (ValueError, UnicodeDecodeError):
            raise ApiError('INVALID_REQUEST', '请求体必须是 JSON。', 400) from None
        if (not isinstance(payload, dict) or set(payload) != {'account_ref'}
                or not isinstance(payload['account_ref'], str)):
            raise ApiError('INVALID_REQUEST', '请选择账户。', 400)
        service.reserve()
        try:
            with service.lock:
                current = service.sessions.resolve(request.headers.get('authorization'))
                for thread in current.threads:
                    record = service.challenges.lookup(service.challenge_by_thread.get(thread))
                    if record and record['decision'] == 'PENDING' and record['expires_at'] > service.clock():
                        raise ApiError('RUN_BUSY', '请先确认或取消当前业务。', 409)
                owned = query_accounts(context=TrustedContext(current.user_id, current.account_id, 'switch'))
                if owned['status'] != 'COMPLETED' or payload['account_ref'] not in {
                        row['account_ref'] for row in owned['data']['accounts']}:
                    raise ApiError('ACCOUNT_NOT_ACCESSIBLE', '账户不可访问。', 403)
                issued = service.sessions.issue(user_id=current.user_id, account_id=payload['account_ref'],
                                                family_id=current.family_id)
                return {'token': issued.token, 'mode': service.runtime.mode}
        finally:
            service.running.release()

    @app.post('/demo/reset')
    async def reset(request: Request):
        require_demo(request)
        if database_path is not None:
            raise ApiError('RESET_DISABLED', '持久化账本不支持演示重置，请保留现有数据。', 409)
        if await request.body() not in (b'', b'{}'):
            raise ApiError('INVALID_REQUEST', '重置入口不接受业务参数。', 400)
        service.sessions.resolve(request.headers.get('authorization'))
        service.reserve()
        try:
            with service.lock:
                reset_demo_data()
                service.sessions.invalidate_all()
                service.challenges.invalidate_all()
                service.challenge_by_thread.clear()
                service.saver = InMemorySaver()
                service.runtime = BankAgentRuntime(challenges=service.challenges, clock=service.clock,
                                           candidate_model=service.candidate_model,
                                           registry=service.registry,
                                           phraser=service.phraser, query_model=service.query_model)
                service.graph = build_graph(service.runtime, checkpointer=service.saver)
            return {'status': 'COMPLETED'}
        finally:
            service.running.release()

    async def stream_request(request, prepare):
        try:
            payload = await request.json()
        except (ValueError, UnicodeDecodeError):
            raise ApiError('INVALID_REQUEST', '请求体必须是 JSON。', 400) from None
        prepared = prepare(request.headers.get('authorization'), payload)
        released = False
        def release():
            nonlocal released
            if not released:
                released = True
                service.running.release()
        async def body():
            try:
                # 同一进程 Demo 串行运行；yield 保留真实 SSE 边界。
                async for data in iterate_in_threadpool(service.stream(*prepared)):
                    yield data
            finally:
                release()
        return StreamingResponse(body(), media_type='text/event-stream',
                                 background=BackgroundTask(release))

    @app.post('/agent/chat')
    async def chat(request: Request):
        return await stream_request(request, service.prepare)

    @app.post('/bank/form')
    async def form(request: Request):
        return await stream_request(request, service.prepare_form)
    return app


def create_demo_app():
    """启动入口：有模型环境变量就用模型模式，全空则保持 offline。

    配置只写了一半会在这里抛错并终止启动——静默回退 offline 会让人以为
    模型已经在用，实际上在跑关键词规则。

    ``BANKAGENT_DEMO_ALLOW_LAN=1`` 才会放宽「仅本地访问」的限制。默认关闭，
    因为打开后同一网段任何人都能取到演示身份、操作演示账本、消耗模型额度。
    临时给同事演示时才开，用完记得关。
    """
    import os

    from bankagent.agent.agent_phrasing import ResponsePhraser
    from bankagent.agent.model_providers import build_model_from_env

    allow_lan = os.environ.get('BANKAGENT_DEMO_ALLOW_LAN') == '1'
    # 识别与措辞各用一个实例：两者共用时，改写层一次空响应就会把 /health
    # 标记成模型不可用，而识别其实是好的——这会把人带偏。
    phraser_model = build_model_from_env()
    model = build_model_from_env()
    return create_app(demo=True, candidate_model=model, query_model=model,
                      phraser=ResponsePhraser(phraser_model) if phraser_model is not None else None,
                      allow_lan=allow_lan, database_path=os.environ.get('BANKAGENT_DB_PATH') or None)
