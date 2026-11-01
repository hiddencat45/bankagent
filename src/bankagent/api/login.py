"""Local account login routes; no public identity-claim or demo switch."""
from fastapi import Request
from bankagent.api.contracts import ApiError
from bankagent.api.credentials import CredentialStore
from bankagent.banking.bank_types import TrustedContext
from bankagent.banking.bank_backend import query_accounts


def install_login(app, service, database_path):
    store = CredentialStore(database_path)
    service.credentials = store

    async def body(request, fields):
        try:
            data = await request.json()
        except ValueError:
            raise ApiError('INVALID_REQUEST', '请填写有效请求。', 400)
        if not isinstance(data, dict) or set(data) != set(fields) or not all(isinstance(v, str) for v in data.values()):
            raise ApiError('INVALID_REQUEST', '请求字段不正确。', 400)
        return data

    @app.post('/auth/register')
    async def register(request: Request):
        data = await body(request, ['username', 'display_name', 'password'])
        service.reserve()
        try:
            store.register(**data)
            return {'status': 'REGISTERED'}
        finally:
            service.running.release()

    @app.post('/auth/login')
    async def login(request: Request):
        data = await body(request, ['username', 'password'])
        service.reserve()
        try:
            identity = store.login(**data)
            accounts = query_accounts(context=TrustedContext(identity['user_id'], 'unopened', 'login'))
            if accounts['status'] != 'COMPLETED':
                raise ApiError('ACCOUNT_NOT_ACCESSIBLE', '客户信息无法读取。', 403)
            rows = accounts['data']['accounts']
            session = service.sessions.issue(user_id=identity['user_id'], account_id=rows[0]['account_ref'] if rows else 'unopened')
            return {'token': session.token, 'mode': service.runtime.mode,
                    'display_name': identity['display_name'], 'needs_account': not rows}
        finally:
            service.running.release()

    @app.post('/auth/logout')
    async def logout(request: Request):
        await body(request, [])
        service.reserve()
        try:
            current = service.sessions.resolve(request.headers.get('authorization'))
            service.sessions.invalidate_family(current)
            return {'status': 'LOGGED_OUT'}
        finally:
            service.running.release()

    @app.post('/auth/payment-password')
    async def payment_password(request: Request):
        data = await body(request, ['login_password', 'payment_password'])
        service.reserve()
        try:
            current = service.sessions.resolve(request.headers.get('authorization'))
            store.set_payment_password(current.user_id, **data)
            return {'status': 'CONFIGURED'}
        finally:
            service.running.release()
