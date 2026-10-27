from copy import deepcopy
from datetime import datetime, timezone
import time

import pytest

from desktop.app import LocalService
from desktop.client import QueryClient, transfer_confirmation
from test_desktop import offline_env


def receipt(frames):
    return next(data['payload'] for event, data in frames if event == 'card' and data['type'] == 'result')


def test_transfer_cancel_modify_confirm_replay_restart(tmp_path):
    env = offline_env()
    env['BANKAGENT_DB_PATH'] = str(tmp_path / 'bank.sqlite3')
    service = LocalService(env=env)
    try:
        client = QueryClient(service.start())
        client.connect()
        assert client.query('我想转账')[-1][1]['status'] == 'NEEDS_CLARIFICATION'
        pending = transfer_confirmation(client.query('给张伟转40元'))
        assert pending['recipient'] == '张伟' and pending['amount_minor'] == 4000
        assert receipt(client.query('查询余额'))['data']['balance_minor'] == 500000
        assert client.resume(pending, 'reject')[-1][1]['status'] == 'REJECTED'
        pending = transfer_confirmation(client.query('给张伟转50元'))
        result = client.resume(pending, 'approve')
        assert receipt(result)['data']['remaining_balance_minor'] == 495000
        assert receipt(client.resume(pending, 'approve')) == receipt(result)
        assert receipt(client.query('查询余额'))['data']['balance_minor'] == 495000
        broken = deepcopy(pending)
        broken['risk_level'] = 'RED'
        # Client risk labels cannot change the server's settled decision.
        assert receipt(client.resume(broken, 'approve')) == receipt(result)
    finally:
        service.close()
    restarted = LocalService(env=env)
    try:
        client = QueryClient(restarted.start())
        client.connect()
        assert receipt(client.query('查询余额'))['data']['balance_minor'] == 495000
    finally:
        restarted.close()


def frames(risk='YELLOW'):
    base = {'thread_id': 't1', 'request_id': 'r1', 'mode': 'offline'}
    card = {'operation': 'TRANSFER', 'recipient': '张伟', 'amount_minor': 4000, 'currency': 'CNY',
            'challenge_id': 'c1', 'operation_hash': 'hash1', 'risk_level': risk,
            'expires_at': datetime.now(timezone.utc).isoformat()}
    return [('status', {**base, 'status': 'PROCESSING'}),
            ('card', {**base, 'type': 'confirm', 'payload': card}),
            ('interrupt', {**base, 'challenge_id': 'c1', 'operation_hash': 'hash1',
                           'kind': 'CONFIRMATION' if risk == 'YELLOW' else 'STRONG_AUTH'}),
            ('done', {**base, 'status': 'AWAITING_CONFIRMATION' if risk == 'YELLOW' else 'AWAITING_AUTHENTICATION'})]


@pytest.mark.parametrize('field,value', [('amount_minor', True), ('amount_minor', 0),
    ('recipient', ''), ('risk_level', 'UNKNOWN'), ('operation_hash', 'other')])
def test_bad_confirmation_cannot_be_approved(field, value):
    stream = frames()
    stream[1][1]['payload'][field] = value
    with pytest.raises(ValueError):
        transfer_confirmation(stream)


def test_widget_confirmation_uncertainty_and_risk(monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6.QtWidgets')
    from PySide6.QtWidgets import QApplication
    from desktop.window import BankWindow, QTimer
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QTimer, 'singleShot', lambda *args: None)
    window = BankWindow('http://127.0.0.1')
    window.client.token = 'test-token'
    window.receive('connect', 'offline')
    window.receive('query', frames())
    assert window.approve.isEnabled() and window.reject.isEnabled()
    assert not window.submit.isEnabled()
    called = []
    monkeypatch.setattr(window, 'run', lambda kind, fn: called.append((kind, fn)))
    window.decide('approve')
    window.receive('decision_error', 'unknown outcome')
    assert window.uncertain and window.retry.isEnabled()
    assert not window.new.isEnabled() and not window.reconnect.isEnabled()
    assert not window.approve.isEnabled() and not window.reject.isEnabled()
    window.decide('reject')
    assert len(called) == 1
    window.decide('approve')
    assert len(called) == 2
    window.receive('connect', 'offline')
    window.receive('query', frames('RED'))
    assert not window.approve.isEnabled() and window.reject.isEnabled()
    window.decide('approve')
    assert len(called) == 2
    window.new_chat()
    assert window.pending is None and not window.approve.isEnabled()
    window.close()
    window.deleteLater()
    app.processEvents()


def test_native_button_executes_once_through_real_service(tmp_path, monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6.QtWidgets')
    from PySide6.QtWidgets import QApplication
    from desktop.window import BankWindow
    app = QApplication.instance() or QApplication([])
    service = LocalService(env={**offline_env(), 'BANKAGENT_DB_PATH': str(tmp_path / 'bank.sqlite3')})
    window = None
    def wait_for(predicate):
        deadline = time.monotonic() + 15
        while not predicate() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        assert predicate()
    try:
        window = BankWindow(service.start())
        wait_for(lambda: window.client.token is not None and not window.busy)
        window.send('给张伟转40元')
        wait_for(lambda: window.pending is not None and not window.busy)
        pending = dict(window.pending)
        window.approve.click()
        window.approve.click()  # Disabled immediately; no second submission.
        wait_for(lambda: not window.busy)
        assert window.pending is None
        assert '转账成功：向 张伟 转入 ¥ 40.00' in window.history.toPlainText()
        assert receipt(window.client.resume(pending, 'approve'))['data']['remaining_balance_minor'] == 496000
        assert receipt(window.client.query('查询余额'))['data']['balance_minor'] == 496000
    finally:
        if window is not None:
            window.close()
            window.deleteLater()
            app.processEvents()
        service.close()
