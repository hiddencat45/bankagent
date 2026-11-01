import time
from copy import deepcopy
import pytest
from desktop.client import business_confirmation
from test_desktop_transfer import frames


def opening():
    stream = frames()
    card = stream[1][1]['payload']
    card.pop('recipient')
    card.pop('amount_minor')
    card.update(operation='OPEN_ACCOUNT', display_name='生活账户', opening_credit_minor=0)
    return stream


@pytest.mark.parametrize('key,value', [('display_name', ''), ('risk_level', 'RED'),
    ('operation_hash', 'mismatch'), ('opening_credit_minor', 1), ('currency', 'USD')])
def test_invalid_lifecycle_confirmation(key, value):
    stream = opening()
    stream[1][1]['payload'][key] = value
    with pytest.raises(ValueError):
        business_confirmation(stream)


def test_real_desktop_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6.QtWidgets')
    from PySide6.QtWidgets import QApplication
    from desktop.window import BankWindow, QInputDialog
    from desktop.app import LocalService
    from test_desktop import offline_env
    from test_desktop_transfer import receipt
    app = QApplication.instance() or QApplication([])
    service = LocalService(env={**offline_env(), 'BANKAGENT_DB_PATH': str(tmp_path / 'bank.sqlite3')})
    window = None
    def wait(predicate):
        until = time.monotonic() + 15
        while time.monotonic() < until:
            app.processEvents()
            if predicate():
                return
            time.sleep(.01)
        assert predicate()
    def ready():
        return not window.busy and window.client.token and window.accounts.count() > 0
    def form(label, values):
        values = iter(values)
        monkeypatch.setattr(QInputDialog, 'getText', lambda *a, **kw: (next(values), True))
        monkeypatch.setattr(QInputDialog, 'getItem', lambda *a: ('购物', True))
        with monkeypatch.context() as direct:
            direct.setattr(window.client, 'query', lambda *a, **kw: pytest.fail('form used natural language'))
            next(b for b in window.business_buttons if b.text() == label).click()
            wait(lambda: window.pending is not None and not window.busy)
            assert not window.switch_account.isEnabled()
            assert not any(b.isEnabled() for b in window.business_buttons)
            pending = deepcopy(window.pending)
            window.approve.click()
            wait(lambda: not window.busy and window.pending is None)
        return pending
    try:
        window = BankWindow(service.start())
        wait(ready)
        form('开户', ['生活账户'])
        wait(lambda: ready() and window.accounts.count() == 3)
        window.accounts.setCurrentIndex(2)
        window.switch_account.click()
        wait(lambda: ready() and '生活账户' in window.current_account.text())
        assert window.thread is None
        form('办理借记卡', ['生活卡'])
        form('激活', ['生活卡'])
        form('模拟入金', ['生活卡', '1000'])
        pending = form('刷卡消费', ['生活卡', '演示超市', '12.30'])
        assert receipt(window.client.resume(pending, 'approve'))['data']['remaining_balance_minor'] == 98770
        form('冻结', ['生活卡'])
        form('解冻', ['生活卡'])
        assert receipt(window.client.query('查询余额'))['data']['balance_minor'] == 98770
        assert '模拟支付 12.30 元' in window.history.toPlainText()
        form('设置限额', ['生活卡', '10', '20'])
        limits = receipt(window.client.query('查询限额「生活卡」'))['data']
        assert limits['single_limit_minor'] == 1000 and limits['daily_limit_minor'] == 2000
        blocked = business_confirmation(window.client.query('使用「生活卡」在商户「商店」刷卡支付12.30元'))
        assert receipt(window.client.resume(blocked, 'approve'))['error_code'] == 'CARD_SINGLE_LIMIT_EXCEEDED'
        wait(ready)
        form('转账', ['张伟', '40'])
        assert receipt(window.client.query('查询余额'))['data']['balance_minor'] == 94770
    finally:
        if window:
            window.close()
            window.deleteLater()
            app.processEvents()
        service.close()
