"""Real child HTTP service and native controls, offscreen; no personal ledger."""
import time
import pytest
from test_desktop import offline_env
from test_desktop_transfer import receipt


def test_startup_customer_failure_never_keeps_bootstrap_session(monkeypatch):
    import io
    from desktop.client import QueryClient
    client = QueryClient('http://unused', startup_customer='zhang-wei')
    monkeypatch.setattr(client, 'post', lambda *args: io.BytesIO(b'{"token":"bootstrap-only","mode":"offline"}'))
    def unavailable(reference):
        assert reference == 'zhang-wei'
        raise TimeoutError('selection response lost')
    monkeypatch.setattr(client, 'switch_customer', unavailable)
    with pytest.raises(TimeoutError):
        client.connect()
    assert client.token is None


def test_native_customer_switch_receiving_bill_and_return(tmp_path, monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6.QtWidgets')
    from PySide6.QtWidgets import QApplication
    from desktop.window import BankWindow
    from desktop.app import LocalService
    app = QApplication.instance() or QApplication([])
    service = LocalService(env={**offline_env(), 'BANKAGENT_DB_PATH': str(tmp_path / 'bank.sqlite3')})
    window = None
    def wait(predicate):
        until = time.monotonic() + 20
        while time.monotonic() < until:
            app.processEvents()
            if predicate():
                return
            time.sleep(.01)
        assert predicate()
    def ready():
        return not window.busy and window.customers.count() == 2 and window.accounts.count() > 0
    def select(reference, name):
        window.customers.setCurrentIndex(window.customers.findData(reference))
        window.switch_customer.click()
        wait(lambda: ready() and name in window.current_customer.text())
        assert window.thread is None and window.pending is None
        assert window.input.text() == ''
    try:
        window = BankWindow(service.start())
        wait(ready)
        window.send('给张伟转40元')
        wait(lambda: window.pending is not None and not window.busy)
        assert not window.switch_customer.isEnabled()
        assert not window.customers.isEnabled()
        window.approve.click()
        wait(lambda: ready() and window.pending is None and '4,960.00' in window.current_account.text())
        window.input.setText('付款方未发送草稿')
        select('zhang-wei', '张伟')
        assert '440.00' in window.current_account.text()
        assert '4,960.00' not in window.history.toPlainText()
        window.bills.click()
        wait(lambda: ready() and '关联流水' in window.history.toPlainText())
        text = window.history.toPlainText()
        assert '转入' in text and '40.00' in text and '消费合计：¥ 0.00' in text
        select('primary', '默认演示客户')
        assert '4,960.00' in window.current_account.text()
        assert '转入' not in window.history.toPlainText()
        assert receipt(window.client.query('查询余额'))['data']['balance_minor'] == 496000
    finally:
        if window:
            window.close()
            window.deleteLater()
            app.processEvents()
        service.close()


def test_uncertain_switch_clears_stale_identity_but_busy_keeps_it(monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6.QtWidgets')
    from PySide6.QtWidgets import QApplication
    from desktop.window import BankWindow, QTimer
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QTimer, 'singleShot', lambda *args: None)
    window = BankWindow('http://127.0.0.1')
    window.client.token = 'old-token'
    window.history.setPlainText('旧客户账单')
    window.current_customer.setText('旧客户')
    window.receive('customer_busy', None)
    assert window.client.token == 'old-token'
    assert '先完成或取消' in window.status.text()
    window.receive('customer_error', None)
    assert window.client.token is None and window.thread is None
    assert not window.history.toPlainText() and not window.submit.isEnabled()
    assert '未确认' in window.current_customer.text() and window.reconnect.isEnabled()
    window.close()
    window.deleteLater()
    app.processEvents()
