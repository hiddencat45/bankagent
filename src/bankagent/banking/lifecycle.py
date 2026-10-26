"""Account/card lifecycle for an already trusted demo customer; no UI or model."""
from copy import deepcopy
from datetime import datetime
import json
from uuid import uuid4

from bankagent.banking.bank_types import TrustedContext, WriteContext

DEMO_OPENING_BALANCE_MINOR = 100000
OPERATIONS = frozenset({'OPEN_ACCOUNT', 'ISSUE_DEBIT_CARD', 'ACTIVATE_DEBIT_CARD', 'PAY_BY_CARD', 'SET_CARD_LIMITS'})
DEFAULT_SINGLE_LIMIT_MINOR = 500000
DEFAULT_DAILY_LIMIT_MINOR = 1000000


def result(operation, data=None, error=None):
    return {'operation': operation, 'status': 'REJECTED' if error else 'COMPLETED',
            'data': data, 'error_code': error}


def text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 80


class LifecycleMixin:
    def _card_limits(self, card_id, card):
        today = self._now().date()
        used = sum(row['amount_minor'] for row in self._data['transactions']
            if row.get('card_id') == card_id and row['kind'] == 'EXPENSE'
            and datetime.fromisoformat(row['occurred_at']).date() == today)
        return {'single_limit_minor': card.get('single_limit_minor', DEFAULT_SINGLE_LIMIT_MINOR),
                'daily_limit_minor': card.get('daily_limit_minor', DEFAULT_DAILY_LIMIT_MINOR),
                'used_today_minor': used, 'business_date': today.isoformat()}

    def query_card_limits(self, *, context: TrustedContext, card_id: str):
        with self._transaction():
            if not self._owned(context):
                return result('QUERY_CARD_LIMITS', error='ACCOUNT_NOT_ACCESSIBLE')
            card = self._data['cards'].get(card_id) if isinstance(card_id, str) else None
            if not card or card['account_id'] != context.account_id:
                return result('QUERY_CARD_LIMITS', error='CARD_NOT_ACCESSIBLE')
            return result('QUERY_CARD_LIMITS', {'display_name': card['display_name'],
                'currency': 'CNY', **self._card_limits(card_id, card)})

    def set_card_limits(self, *, context: WriteContext, card_id: str,
                        single_limit_minor: int, daily_limit_minor: int):
        operation = 'SET_CARD_LIMITS'
        if (not text(card_id) or type(single_limit_minor) is not int or type(daily_limit_minor) is not int
                or not 0 <= single_limit_minor <= daily_limit_minor <= 100000000):
            return result(operation, error='INVALID_CARD_LIMITS')
        params = dict(card_id=card_id, single_limit_minor=single_limit_minor, daily_limit_minor=daily_limit_minor)
        def apply(data):
            card = data['cards'].get(card_id)
            if not card or card['account_id'] != context.account_id:
                return result(operation, error='CARD_NOT_ACCESSIBLE')
            card.update(single_limit_minor=single_limit_minor, daily_limit_minor=daily_limit_minor)
            return result(operation, {'display_name': card['display_name'], 'currency': 'CNY',
                'single_limit_minor': single_limit_minor, 'daily_limit_minor': daily_limit_minor})
        return self._lifecycle_write(context, operation, params, apply)

    def _lifecycle_write(self, context, operation, params, apply):
        with self._transaction():
            if operation not in OPERATIONS:
                return result(operation, error='OPERATION_NOT_ALLOWED')
            if not self._owned(context):
                return result(operation, error='ACCOUNT_NOT_ACCESSIBLE')
            if not isinstance(context, WriteContext) or not context.authorization_ref:
                return result(operation, error='AUTHORIZATION_REQUIRED')
            if not isinstance(context.idempotency_key, str) or not context.idempotency_key:
                return result(operation, error='AUTHORIZATION_INVALID')
            key = (context.user_id, context.account_id, context.idempotency_key)
            fingerprint = (context.request_id, operation, json.dumps(params, sort_keys=True))
            previous = self._completed.get(key)
            if previous:
                return deepcopy(previous[1]) if previous[0] == fingerprint else result(
                    operation, error='IDEMPOTENCY_CONFLICT')
            record = deepcopy(self._lookup(context.authorization_ref))
            if not isinstance(record, dict) or self._hash is None:
                return result(operation, error='AUTHORIZATION_INVALID')
            expected = dict(user_id=context.user_id, account_id=context.account_id,
                request_id=context.request_id, idempotency_key=context.idempotency_key,
                operation=operation, params=params, decision='APPROVED')
            expiry = record.get('expires_at')
            if (any(record.get(k) != v for k, v in expected.items())
                    or not record.get('challenge_id') or record.get('risk_level') not in {'YELLOW', 'RED'}
                    or not isinstance(expiry, datetime) or expiry.utcoffset() is None or expiry <= self._now()):
                return result(operation, error='AUTHORIZATION_INVALID')
            base = TrustedContext(context.user_id, context.account_id, context.request_id)
            expected_hash = self._hash(base, operation, params)
            if not isinstance(expected_hash, str) or not expected_hash or record.get('operation_hash') != expected_hash:
                return result(operation, error='AUTHORIZATION_INVALID')
            updated = deepcopy(self._data)
            reply = apply(updated)
            if reply['status'] != 'COMPLETED':
                return reply
            self._data = updated
            self._completed = {**self._completed, key: (fingerprint, deepcopy(reply))}
            return reply

    def open_account(self, *, context: WriteContext, display_name: str):
        """Open an additional account for the trusted demo customer, not a new login."""
        operation = 'OPEN_ACCOUNT'
        if not text(display_name):
            return result(operation, error='INVALID_ACCOUNT_NAME')
        def apply(data):
            account_id, transaction_id = 'account-' + uuid4().hex, 'txn-' + uuid4().hex
            data.setdefault('customers', {}).setdefault(context.user_id,
                {'display_name': '演示客户', 'identity_type': 'DEMO'})
            data['accounts'][account_id] = {'user_id': context.user_id,
                'display_name': display_name, 'balance_minor': DEMO_OPENING_BALANCE_MINOR, 'currency': 'CNY'}
            data['transactions'].append({'transaction_id': transaction_id, 'account_id': account_id,
                'occurred_at': self._now().isoformat(), 'kind': 'INCOME',
                'amount_minor': DEMO_OPENING_BALANCE_MINOR, 'category': '演示入账',
                'merchant': '模拟银行演示资金', 'subscription_id': None})
            return result(operation, {'customer_id': context.user_id, 'account_id': account_id,
                'display_name': display_name, 'balance_minor': DEMO_OPENING_BALANCE_MINOR,
                'currency': 'CNY', 'funding_source': 'DEMO_CREDIT', 'transaction_id': transaction_id})
        return self._lifecycle_write(context, operation, {'display_name': display_name}, apply)

    def issue_debit_card(self, *, context: WriteContext, display_name: str):
        operation = 'ISSUE_DEBIT_CARD'
        if not text(display_name):
            return result(operation, error='INVALID_CARD_NAME')
        def apply(data):
            card_id = 'card-' + uuid4().hex
            data['cards'][card_id] = {'account_id': context.account_id,
                'display_name': display_name, 'status': 'PENDING_ACTIVATION'}
            return result(operation, {'card_id': card_id, 'account_id': context.account_id,
                'display_name': display_name, 'status': 'PENDING_ACTIVATION'})
        return self._lifecycle_write(context, operation, {'display_name': display_name}, apply)

    def activate_debit_card(self, *, context: WriteContext, card_id: str):
        operation = 'ACTIVATE_DEBIT_CARD'
        if not text(card_id):
            return result(operation, error='CARD_NOT_ACCESSIBLE')
        def apply(data):
            card = data['cards'].get(card_id)
            if not card or card['account_id'] != context.account_id:
                return result(operation, error='CARD_NOT_ACCESSIBLE')
            if card['status'] != 'PENDING_ACTIVATION':
                return result(operation, error='CARD_NOT_PENDING_ACTIVATION')
            card['status'] = 'ACTIVE'
            return result(operation, {'card_id': card_id, 'display_name': card['display_name'], 'status': 'ACTIVE'})
        return self._lifecycle_write(context, operation, {'card_id': card_id}, apply)

    def pay_by_card(self, *, context: WriteContext, card_id: str, amount_minor: int,
                    merchant: str, category: str = '其他'):
        operation = 'PAY_BY_CARD'
        if not text(card_id):
            return result(operation, error='CARD_NOT_ACCESSIBLE')
        if type(amount_minor) is not int or amount_minor <= 0:
            return result(operation, error='INVALID_AMOUNT')
        if not text(merchant) or not isinstance(category, str) or category not in {'餐饮', '交通', '购物', '居住', '其他'}:
            return result(operation, error='INVALID_PAYMENT_DETAILS')
        params = dict(card_id=card_id, amount_minor=amount_minor, merchant=merchant, category=category)
        def apply(data):
            card = data['cards'].get(card_id)
            if not card or card['account_id'] != context.account_id:
                return result(operation, error='CARD_NOT_ACCESSIBLE')
            if card['status'] != 'ACTIVE':
                return result(operation, error='CARD_NOT_ACTIVE')
            account = data['accounts'][context.account_id]
            if amount_minor > account['balance_minor']:
                return result(operation, error='INSUFFICIENT_BALANCE')
            limits = self._card_limits(card_id, card)
            if amount_minor > limits['single_limit_minor']:
                return result(operation, error='CARD_SINGLE_LIMIT_EXCEEDED')
            if amount_minor + limits['used_today_minor'] > limits['daily_limit_minor']:
                return result(operation, error='CARD_DAILY_LIMIT_EXCEEDED')
            transaction_id = 'txn-' + uuid4().hex
            account['balance_minor'] -= amount_minor
            data['transactions'].append({'transaction_id': transaction_id, 'account_id': context.account_id,
                'occurred_at': self._now().isoformat(), 'kind': 'EXPENSE', 'amount_minor': amount_minor,
                'category': category, 'merchant': merchant, 'subscription_id': None, 'card_id': card_id})
            return result(operation, {'transaction_id': transaction_id, 'card_id': card_id,
                'amount_minor': amount_minor, 'currency': 'CNY', 'merchant': merchant,
                'remaining_balance_minor': account['balance_minor']})
        return self._lifecycle_write(context, operation, params, apply)
