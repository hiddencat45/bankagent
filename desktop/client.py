"""Native desktop transport; identities and authorization stay on the server."""
from datetime import datetime
import json
from urllib.request import Request, ProxyHandler, build_opener
from urllib.error import HTTPError


class CustomerSwitchBusy(Exception):
    """Server refused the switch before replacing the session."""


class QueryClient:
    def __init__(self, url):
        self.url = url
        self.token = None
        self.opener = build_opener(ProxyHandler({}))

    def post(self, path, payload):
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        return self.opener.open(Request(self.url + path,
            data=json.dumps(payload).encode(), headers=headers), timeout=90)

    def connect(self):
        with self.post('/demo/session', {}) as response:
            session = json.load(response)
        if (not isinstance(session, dict) or not isinstance(session.get('token'), str)
                or not session['token'].strip() or session.get('mode') not in {'model', 'offline'}):
            raise ValueError('invalid session')
        self.token = session['token']
        return session['mode']

    def query(self, message, thread=None):
        return self._chat({'message': message, 'thread_id': thread}, thread)

    def form(self, action, fields):
        return self._chat({'action': action, 'fields': fields}, path='/bank/form')

    def accounts(self):
        with self.opener.open(Request(self.url + '/bank/accounts',
                headers={'Authorization': 'Bearer ' + self.token}), timeout=20) as response:
            data = json.load(response)
        rows = data['accounts']
        if not isinstance(rows, list) or not rows:
            raise ValueError('invalid accounts')
        refs = set()
        for row in rows:
            if (not isinstance(row.get('account_ref'), str) or not row['account_ref']
                    or not isinstance(row.get('display_name'), str) or not row['display_name']
                    or row.get('currency') != 'CNY' or row['account_ref'] in refs):
                raise ValueError('invalid account')
            money(row['balance_minor'])
            refs.add(row['account_ref'])
        if data['current_account_ref'] not in refs:
            raise ValueError('invalid selected account')
        return data

    def switch_account(self, reference):
        with self.post('/bank/account-session', {'account_ref': reference}) as response:
            data = json.load(response)
        if not isinstance(data.get('token'), str) or not data['token'] or data.get('mode') not in {'offline', 'model'}:
            raise ValueError('invalid session')
        self.token = data['token']
        return data['mode']

    def overview(self):
        accounts = self.accounts()
        with self.opener.open(Request(self.url + '/demo/customers',
                headers={'Authorization': 'Bearer ' + self.token}), timeout=20) as response:
            data = json.load(response)
        rows = data['customers']
        if (not isinstance(rows, list) or not rows or any(
                not isinstance(row, dict) or not isinstance(row.get('customer_ref'), str)
                or not row['customer_ref'] or not isinstance(row.get('display_name'), str)
                or not row['display_name'] for row in rows)
                or len({row['customer_ref'] for row in rows}) != len(rows)
                or data.get('current_customer_ref') not in {row['customer_ref'] for row in rows}):
            raise ValueError('invalid demo customers')
        return {**accounts, **data}

    def bills(self):
        with self.opener.open(Request(self.url + '/bank/bills',
                headers={'Authorization': 'Bearer ' + self.token}), timeout=20) as response:
            data = json.load(response)
        if data.get('operation') != 'QUERY_BILLS' or data.get('status') != 'COMPLETED':
            raise ValueError('bill query failed')
        return query_result(data)

    def transfer_batches(self):
        with self.opener.open(Request(self.url + '/bank/transfer-batches',
                headers={'Authorization': 'Bearer ' + self.token}), timeout=20) as response:
            result = json.load(response)
        if result.get('operation') != 'QUERY_TRANSFER_BATCHES' or result.get('status') != 'COMPLETED':
            raise ValueError('invalid batch receipts')
        return query_result(result)

    def switch_customer(self, reference):
        try:
            with self.post('/demo/customer-session', {'customer_ref': reference}) as response:
                data = json.load(response)
        except HTTPError as exc:
            if exc.code == 409:
                raise CustomerSwitchBusy() from None
            raise
        if not isinstance(data.get('token'), str) or not data['token'] or data.get('mode') not in {'offline', 'model'}:
            raise ValueError('invalid session')
        self.token = data['token']
        return data['mode']

    def resume(self, pending, decision):
        if decision not in {'approve', 'reject'}:
            raise ValueError('invalid decision')
        if decision == 'approve' and pending['risk_level'] != 'YELLOW':
            raise ValueError('independent authentication required')
        frames = self._chat({'thread_id': pending['thread_id'], 'resume': {
            'challenge_id': pending['challenge_id'], 'decision': decision}}, pending['thread_id'])
        if frames[0][1]['request_id'] != pending['request_id']:
            raise ValueError('request mismatch')
        return frames

    def _chat(self, payload, thread=None, path='/agent/chat'):
        with self.post(path, payload) as response:
            if response.headers.get_content_type() != 'text/event-stream':
                raise ValueError('invalid response')
            raw = response.read(2 * 1024 * 1024 + 1)
        return parse_stream(raw, thread)


def parse_stream(raw, thread=None):
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('response too large')
    text = raw.decode('utf-8').replace('\r\n', '\n')
    if not text.endswith('\n\n'):
        raise ValueError('incomplete stream')
    frames = []
    for frame in text.split('\n\n'):
        if not frame.strip():
            continue
        fields = frame.splitlines()
        event = next((line[7:] for line in fields if line.startswith('event: ')), None)
        data = json.loads('\n'.join(line[6:] for line in fields if line.startswith('data: ')))
        if not isinstance(data, dict):
            raise ValueError('invalid envelope')
        if event not in {'status', 'message', 'card', 'interrupt', 'error', 'done'}:
            raise ValueError('unknown event')
        identity = tuple(data.get(k) for k in ('thread_id', 'request_id', 'mode'))
        if not all(isinstance(v, str) and v for v in identity) or identity[2] not in {'model', 'offline'}:
            raise ValueError('invalid envelope')
        if (thread and identity[0] != thread) or (frames and identity != frames[0][2]):
            raise ValueError('envelope mismatch')
        if frames and frames[-1][0] == 'done':
            raise ValueError('data after done')
        if event in {'message', 'error'}:
            value = data.get('text' if event == 'message' else 'message')
            if not isinstance(value, str) or not value.strip():
                raise ValueError('invalid message')
        if event == 'card' and (data.get('type') not in {'confirm', 'evidence', 'result'}
                                or not isinstance(data.get('payload'), dict)):
            raise ValueError('invalid card')
        frames.append((event, data, identity))
    if not frames or frames[0][0] != 'status' or frames[-1][0] != 'done':
        raise ValueError('incomplete stream')
    if frames[-1][1]['status'] not in {'COMPLETED', 'FAILED', 'REJECTED', 'PENDING',
            'NEEDS_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_AUTHENTICATION'}:
        raise ValueError('invalid final status')
    return [(event, data) for event, data, _ in frames]


def money(minor):
    if type(minor) is not int or minor < 0:
        raise ValueError('invalid amount')
    return f'{minor // 100:,}.{minor % 100:02d}'


def query_result(payload):
    if payload.get('operation') == 'QUERY_TRANSFER_BATCHES' and payload.get('status') == 'COMPLETED':
        return '\n\n'.join(query_result(r) for r in payload['data']['receipts']) or '当前账户没有批量转账回执。'
    if payload.get('operation') == 'BATCH_TRANSFER' and payload.get('data'):
        data = payload['data']
        if data.get('atomic') is not True or data.get('currency') != 'CNY':
            raise ValueError('invalid batch receipt')
        committed = data.get('committed') is True
        if committed != (payload['status'] == 'COMPLETED'):
            raise ValueError('invalid batch status')
        lines = ['整批转账成功' if committed else '整批未提交，全部款项均未扣除']
        if 'total_minor' in data:
            lines.append('整批合计：¥ ' + money(data['total_minor']))
        if 'starting_balance_minor' in data:
            lines.append('办理前余额：¥ ' + money(data['starting_balance_minor']))
        if data.get('batch_id'):
            lines.append('批量编号：' + data['batch_id'])
        labels = {'COMPLETED': '成功', 'FAILED': '失败', 'NOT_EXECUTED': '未执行'}
        for row in data['items']:
            if (row['status'] == 'COMPLETED') != committed:
                raise ValueError('inconsistent atomic receipt')
            lines.append(f"{row['recipient']}：¥ {money(row['amount_minor'])} — {labels[row['status']]}")
            if row.get('error_code'):
                lines.append('原因：' + {'INSUFFICIENT_BALANCE': '余额不足', 'BATCH_ABORTED': '整批未提交',
                    'USER_CANCELLED': '用户取消', 'REAUTHORIZATION_REQUIRED': '需重新认证',
                    'TRANSFER_LIMIT_EXCEEDED': '超过单笔上限', 'CONTACT_NOT_ACCESSIBLE': '收款人不可用',
                    'RECIPIENT_ACCOUNT_INVALID': '收款账户不可用'}.get(row['error_code'], row['error_code']))
            if row.get('transaction_id'):
                lines.append(f"流水：{row['transaction_id']}；转账编号：{row['transfer_id']}")
        return '\n'.join(lines)
    if payload.get('status') != 'COMPLETED':
        return ''
    data = payload['data']
    if payload['operation'] == 'TRANSFER':
        if data['currency'] != 'CNY' or not isinstance(data.get('recipient'), str):
            raise ValueError('invalid transfer')
        return (f"转账成功：向 {data['recipient']} 转入 ¥ {money(data['amount_minor'])}\n"
                f"交易编号：{data['transaction_id']}\n账户余额：¥ {money(data['remaining_balance_minor'])}")
    if payload['operation'] == 'GET_BALANCE':
        if data['currency'] != 'CNY':
            raise ValueError('invalid currency')
        return '账户余额：¥ ' + money(data['balance_minor'])
    if payload['operation'] == 'QUERY_BILLS':
        if data['currency'] != 'CNY':
            raise ValueError('invalid currency')
        lines = [f"消费合计：¥ {money(data['total_minor'])}",
                 f"查询期间：{data['start']} 至 {data['end']}（不含结束日）"]
        kinds = {'INCOME': '收入', 'EXPENSE': '消费', 'TRANSFER_OUT': '转出', 'TRANSFER_IN': '转入'}
        for row in data['transactions']:
            lines.append(f"{row['occurred_at']}  {kinds[row['kind']]}  {row.get('merchant') or row['category']}  ¥ {money(row['amount_minor'])}")
            if row.get('transfer_id') and row.get('related_transaction_id'):
                lines.append(f"流水：{row['transaction_id']}\n转账编号：{row['transfer_id']}\n关联流水：{row['related_transaction_id']}")
        return '\n'.join(lines)
    return ''


def transfer_confirmation(frames):
    final = frames[-1][1]['status']
    if final not in {'AWAITING_CONFIRMATION', 'AWAITING_AUTHENTICATION'}:
        return None
    cards = [data['payload'] for event, data in frames if event == 'card' and data['type'] == 'confirm']
    signals = [data for event, data in frames if event == 'interrupt']
    if len(cards) != 1 or len(signals) != 1:
        raise ValueError('missing confirmation binding')
    card, signal = cards[0], signals[0]
    if card.get('operation') not in {'TRANSFER', 'BATCH_TRANSFER'}:
        return None  # Other operations are validated by business_confirmation.
    batch = card['operation'] == 'BATCH_TRANSFER'
    if batch:
        rows = card.get('items')
        if (card.get('atomic') is not True or not isinstance(rows, list) or not 2 <= len(rows) <= 10
                or any(not isinstance(r, dict) or not isinstance(r.get('recipient'), str) or not r['recipient'].strip()
                       or type(r.get('amount_minor')) is not int or r['amount_minor'] <= 0 or r.get('currency') != 'CNY' for r in rows)
                or type(card.get('total_minor')) is not int or card['total_minor'] != sum(r['amount_minor'] for r in rows)):
            raise ValueError('invalid batch confirmation')
    required = ('challenge_id', 'operation_hash', 'expires_at') + (() if batch else ('recipient',))
    if any(not isinstance(card.get(key), str) or not card[key].strip() for key in required):
        raise ValueError('invalid confirmation')
    money(card['total_minor'] if batch else card['amount_minor'])
    if (not batch and card['amount_minor'] == 0) or card.get('currency') != 'CNY':
        raise ValueError('invalid transfer amount')
    if datetime.fromisoformat(card['expires_at']).utcoffset() is None:
        raise ValueError('invalid expiry')
    expected = {'YELLOW': ('AWAITING_CONFIRMATION', 'CONFIRMATION'),
                'RED': ('AWAITING_AUTHENTICATION', 'STRONG_AUTH')}
    if expected.get(card.get('risk_level')) != (final, signal.get('kind')):
        raise ValueError('invalid confirmation risk')
    if any(card[key] != signal.get(key) for key in ('challenge_id', 'operation_hash')):
        raise ValueError('confirmation mismatch')
    fields = ('items', 'total_minor', 'atomic', 'operation') if batch else ('amount_minor',)
    return {**{key: card[key] for key in (*required, *fields, 'currency', 'risk_level')},
            'thread_id': frames[0][1]['thread_id'], 'request_id': frames[0][1]['request_id']}


def business_confirmation(frames):
    transfer = transfer_confirmation(frames)
    if transfer is not None and transfer.get('operation') == 'BATCH_TRANSFER':
        summary = '\n'.join(f"{i}. {row['recipient']}：¥ {money(row['amount_minor'])}" for i, row in enumerate(transfer['items'], 1))
        return {**transfer, 'summary': summary + f"\n合计：¥ {money(transfer['total_minor'])}\n整批全有或全无：任一笔失败，整批不扣款。"}
    if transfer is not None:
        return {**transfer, 'summary': f"收款人：{transfer['recipient']}\n金额：¥ {money(transfer['amount_minor'])}"}
    if frames[-1][1]['status'] not in {'AWAITING_CONFIRMATION', 'AWAITING_AUTHENTICATION'}:
        return None
    card = next(d['payload'] for e, d in frames if e == 'card' and d['type'] == 'confirm')
    signal = next(d for e, d in frames if e == 'interrupt')
    labels = {'CREATE_DEMO_CUSTOMER': '创建演示客户并首次开户',
              'OPEN_ACCOUNT': '开立模拟账户', 'ISSUE_DEBIT_CARD': '办理借记卡',
              'ACTIVATE_DEBIT_CARD': '激活借记卡', 'PAY_BY_CARD': '模拟消费',
              'FREEZE_CARD': '冻结卡片', 'UNFREEZE_CARD': '解冻卡片', 'SET_CARD_LIMITS': '设置消费限额'}
    operation = card.get('operation')
    if operation not in labels:
        return None
    for key in ('display_name', 'challenge_id', 'operation_hash', 'expires_at'):
        if not isinstance(card.get(key), str) or not card[key].strip():
            raise ValueError('invalid business confirmation')
    if (card.get('risk_level') != 'YELLOW' or signal.get('kind') != 'CONFIRMATION'
            or frames[-1][1]['status'] != 'AWAITING_CONFIRMATION'
            or any(card[k] != signal.get(k) for k in ('challenge_id', 'operation_hash'))
            or datetime.fromisoformat(card['expires_at']).utcoffset() is None):
        raise ValueError('invalid confirmation binding')
    summary = f"业务：{labels[operation]}\n名称：{card['display_name']}"
    if operation in {'OPEN_ACCOUNT', 'CREATE_DEMO_CUSTOMER'}:
        if card.get('opening_credit_minor') != 100000 or card.get('currency') != 'CNY':
            raise ValueError('invalid opening credit')
        summary += '\n将记入 ¥ 1,000.00 演示资金（非真实存款）。'
        if operation == 'CREATE_DEMO_CUSTOMER':
            if not isinstance(card.get('account_name'), str) or not card['account_name'].strip():
                raise ValueError('invalid first account')
            summary += '\n首次开户名称：' + card['account_name'] + '\n仅创建虚构演示身份，不进行实名注册。'
    elif operation == 'PAY_BY_CARD':
        if (not isinstance(card.get('merchant'), str) or not card['merchant'].strip()
                or card.get('currency') != 'CNY' or type(card.get('amount_minor')) is not int
                or card['amount_minor'] <= 0 or card.get('category') not in ['餐饮', '交通', '购物', '居住', '其他']):
            raise ValueError('invalid payment')
        summary += f"\n商户：{card['merchant']}\n金额：¥ {money(card['amount_minor'])}\n分类：{card['category']}"
    elif operation == 'SET_CARD_LIMITS':
        single, daily = card.get('single_limit_minor'), card.get('daily_limit_minor')
        if type(single) is not int or type(daily) is not int or not 0 <= single <= daily <= 100000000 or card.get('currency') != 'CNY':
            raise ValueError('invalid card limits')
        summary += f'\n单笔上限：¥ {money(single)}\n每日上限：¥ {money(daily)}\n零限额将拒绝新的卡支付；不影响账户转账。'
    elif operation in {'FREEZE_CARD', 'UNFREEZE_CARD'}:
        target = 'FROZEN' if operation == 'FREEZE_CARD' else 'ACTIVE'
        if card.get('current_status') not in {'ACTIVE', 'FROZEN'} or card.get('target_status') != target:
            raise ValueError('invalid card transition')
    return {**{k: card[k] for k in ('challenge_id', 'operation_hash', 'expires_at', 'risk_level')},
            'summary': summary, 'thread_id': frames[0][1]['thread_id'], 'request_id': frames[0][1]['request_id']}
