"""Native offscreen onboarding over a real child server and temporary ledger."""
import time
import pytest
from test_desktop import offline_env
from test_desktop_transfer import receipt


def test_native_create_switch_issue_activate_reopen(tmp_path, monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6.QtWidgets')
    from PySide6.QtWidgets import QApplication
    from desktop.window import BankWindow, QInputDialog
    from desktop.app import LocalService
    app = QApplication.instance() or QApplication([])
    env = {**offline_env(), 'BANKAGENT_DB_PATH': str(tmp_path / 'new-customer.sqlite3')}
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
        return not window.busy and window.customers.count() > 0 and window.accounts.count() > 0
    def write(button, values):
        values = iter(values)
        monkeypatch.setattr(QInputDialog, 'getText', lambda *a, **kw: (next(values), True))
        button.click()
        wait(lambda: window.pending is not None and not window.busy)
        assert not window.create_customer.isEnabled()
        assert not window.switch_customer.isEnabled()
        summary = window.confirm_text.text()
        window.approve.click()
        wait(lambda: ready() and window.pending is None)
        return summary
    for first in (True, False):
        service = LocalService(env=env)
        try:
            window = BankWindow(service.start())
            wait(ready)
            if first:
                summary = write(window.create_customer, ['小林', '日常首账户'])
                assert '小林' in summary and '日常首账户' in summary and '0.00' in summary
            wait(lambda: ready() and window.customers.count() == 3)
            index = next(i for i in range(window.customers.count()) if '小林' in window.customers.itemText(i))
            window.customers.setCurrentIndex(index)
            window.switch_customer.click()
            wait(lambda: ready() and '小林' in window.current_customer.text())
            assert ('0.00' if first else '1,000.00') in window.current_account.text()
            if first:
                for label, value in [('办理借记卡', '首卡'), ('激活', '首卡')]:
                    write(next(b for b in window.business_buttons if b.text() == label), [value])
                write(next(b for b in window.business_buttons if b.text() == '模拟入金'), ['首卡', '1000'])
            cards = receipt(window.client.query('我的卡片'))['data']['cards']
            assert len(cards) == 1 and cards[0]['display_name'] == '首卡' and cards[0]['status'] == 'ACTIVE'
            window.bills.click()
            wait(lambda: ready() and '本机测试资金' in window.history.toPlainText())
        finally:
            if window:
                window.close()
                window.deleteLater()
                app.processEvents()
            service.close()
