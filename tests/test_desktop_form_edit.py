import time
from copy import deepcopy
from urllib.error import HTTPError
import pytest
from test_desktop import offline_env
from test_desktop_transfer import receipt


@pytest.mark.parametrize('lose_cancel_response', [False, True])
def test_edit_cancels_old_payment_before_prefilling_and_only_pays_new_amount(tmp_path, monkeypatch, lose_cancel_response):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6.QtWidgets')
    from PySide6.QtWidgets import QApplication
    from desktop.app import LocalService
    from desktop.window import BankWindow, QInputDialog
    app = QApplication.instance() or QApplication([])
    service = LocalService(env={**offline_env(), 'BANKAGENT_DB_PATH': str(tmp_path / 'edit.sqlite3')})
    window = None
    def wait(predicate):
        until = time.monotonic() + 20
        while time.monotonic() < until:
            app.processEvents()
            if predicate():
                return
            time.sleep(.01)
        assert predicate()
    try:
        window = BankWindow(service.start())
        wait(lambda: not window.busy and window.accounts.count() > 0)
        values = iter(['日常消费卡', '转账冻结商店', '12.30'])
        monkeypatch.setattr(QInputDialog, 'getText', lambda *a, **kw: (next(values), True))
        monkeypatch.setattr(QInputDialog, 'getItem', lambda *a: ('购物', True))
        next(b for b in window.business_buttons if b.text() == '刷卡消费').click()
        wait(lambda: not window.busy and window.pending is not None)
        old = deepcopy(window.pending)
        assert window.edit.isEnabled()
        fields, revised = [], iter(['日常消费卡', '转账冻结商店', '8.50'])
        def edit_input(*args, **kwargs):
            # Before even showing editable values, server must reject the old approval.
            with pytest.raises(HTTPError) as rejected:
                window.client.resume(old, 'approve')
            assert rejected.value.code == 409
            fields.append(kwargs['text'])
            return next(revised), True
        monkeypatch.setattr(QInputDialog, 'getText', edit_input)
        original, calls = window.client.resume, []
        if lose_cancel_response:
            def lost(pending, decision):
                reply = original(pending, decision)
                calls.append(decision)
                if len(calls) == 1:
                    raise OSError('lost cancellation response')
                return reply
            monkeypatch.setattr(window.client, 'resume', lost)
        window.edit.click()
        if lose_cancel_response:
            wait(lambda: not window.busy and window.uncertain)
            assert fields == [] and not window.edit.isEnabled() and not window.approve.isEnabled()
            assert window.decision == 'reject'
            window.retry.click()
        wait(lambda: not window.busy and window.pending is not None and window.pending['challenge_id'] != old['challenge_id'])
        assert fields == ['日常消费卡', '转账冻结商店', '12.30']
        assert '8.50' in window.confirm_text.text()
        assert receipt(window.client.query('查询余额'))['data']['balance_minor'] == 500000
        changed = deepcopy(window.pending)
        window.approve.click()
        wait(lambda: not window.busy and window.pending is None)
        assert receipt(window.client.resume(changed, 'approve'))['data']['remaining_balance_minor'] == 499150
        assert not window.edit.isEnabled()
        wait(lambda: not window.busy and '4,991.50' in window.current_account.text())
        window.bills.click()
        wait(lambda: not window.busy and '8.50' in window.history.toPlainText())
        rows = receipt(window.client.query('本月账单'))['data']['transactions']
        assert [r['amount_minor'] for r in rows if r['merchant'] == '转账冻结商店'] == [850]
    finally:
        if window:
            window.close()
            window.deleteLater()
            app.processEvents()
        service.close()
