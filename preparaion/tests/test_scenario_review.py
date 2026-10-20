import re

import pytest

from bank_types import TrustedContext
from scenarios import build_registry
from scenarios import balance, transfer


@pytest.mark.parametrize('token', ['300.001', '1,000', '1e3', '-300', '300万', '1_000'])
def test_amount_token_is_never_truncated(token):
    match = re.search(transfer.INTENTS['TRANSFER']['slots']['amount'], f'给张伟转 {token} 元')
    assert match.group(1) == token
    assert transfer._to_minor(match.group(1)) is None


def test_balance_is_registered_read_only_and_projects_before_state(monkeypatch):
    registry = build_registry()
    assert registry.effect_of('balance', 'GET_BALANCE') == 'READ'
    assert registry.risk_floor('balance', 'GET_BALANCE') == 'GREEN'
    monkeypatch.setattr('bank_backend.get_balance', lambda **kw: {
        'operation': 'GET_BALANCE', 'status': 'COMPLETED', 'error_code': None,
        'data': {'balance_minor': 500000, 'currency': 'CNY', 'daily_transfer_total_minor': 99},
    })
    out = balance.execute('GET_BALANCE', {}, TrustedContext('u', 'a', 'r'))
    assert out['data'] == {'balance_minor': 500000, 'currency': 'CNY'}
    assert '5000.00' in balance.render(out)
