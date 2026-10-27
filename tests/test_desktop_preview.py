"""Two connected views, isolated real HTTP service; no visible user window."""
import time
import pytest
from desktop.app import LocalService
from test_desktop import offline_env


def test_preview_transfer_back_edit_cancel_and_shared_account(tmp_path, monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6.QtWidgets')
    from PySide6.QtWidgets import QApplication
    from desktop.preview import PreviewWindow
    from urllib.error import HTTPError
    qt = QApplication.instance() or QApplication([])
    service = LocalService(env={**offline_env(), 'BANKAGENT_DB_PATH': str(tmp_path / 'bank.sqlite3')})
    window = None
    def wait(predicate):
        until = time.monotonic() + 20
        while time.monotonic() < until:
            qt.processEvents()
            if predicate():
                return
            time.sleep(.01)
        assert predicate(), window.status.text()
    try:
        window = PreviewWindow(service.start())
        wait(lambda: not window.busy and window.snapshot is not None)
        assert window.balance_value.text() == '¥ 5,000.00'
        assert window.card_list.count() == 2
        window.card_list.setCurrentRow(1)
        assert '备用卡' in window.card_note.text() and '已冻结' in window.card_note.text()
        window.card_limits.click()
        wait(lambda: not window.busy and '单笔限额' in window.card_note.text())
        window.go_transfer.click()
        window.recipient.setCurrentIndex(window.recipient.findData('张伟'))
        window.amount.setText('40.123')
        assert not window.prepare_transfer.isEnabled() and '两位' in window.amount_error.text()
        window.amount.setText('6000')
        assert not window.prepare_transfer.isEnabled() and '余额' in window.amount_error.text()
        window.amount.setText('40')
        window.overview_nav.click()
        window.transfer_nav.click()
        assert window.amount.text() == '40' and window.recipient.currentData() == '张伟'
        window.prepare_transfer.click()
        wait(lambda: not window.busy and window.pending is not None)
        old = dict(window.pending)
        assert not window.amount.isEnabled() and not window.switch_account.isEnabled()
        assert '40.00' in window.confirm_text.text()
        window.edit.click()
        wait(lambda: not window.busy and window.pending is None and window.amount.isEnabled())
        assert window.amount.text() == '40'
        with pytest.raises(HTTPError) as rejected:
            window.client.resume(old, 'approve')
        assert rejected.value.code == 409
        window.amount.setText('30')
        window.prepare_transfer.click()
        wait(lambda: not window.busy and window.pending is not None)
        final = dict(window.pending)
        original_resume = window.client.resume
        def lost_response(pending, decision):
            original_resume(pending, decision)
            raise TimeoutError('simulated response lost after commit')
        monkeypatch.setattr(window.client, 'resume', lost_response)
        window.approve.click()
        wait(lambda: not window.busy and window.uncertain)
        assert '付款可能已经完成' in window.result_text.text()
        assert '待核对' in window.status.text()
        assert not window.approve.isEnabled() and window.retry.isEnabled()
        assert not window.prepare_transfer.isEnabled()
        monkeypatch.setattr(window.client, 'resume', original_resume)
        window.retry.click()
        wait(lambda: not window.busy and window.pending is None and window.balance_value.text() == '¥ 4,970.00')
        assert '转账成功' in window.result_text.text() and '30.00' in window.result_text.text()
        window.client.resume(final, 'approve')
        window.send('查询余额')
        wait(lambda: not window.busy and '4,970.00' in window.conversation.toPlainText())
        assert 'txn-' not in window.conversation.toPlainText()
        assert any(window.transactions.item(i, 1).text().startswith('转出') for i in range(window.transactions.rowCount()))
        window.customers.setCurrentIndex(window.customers.findData('zhang-wei'))
        window.switch_customer.click()
        wait(lambda: not window.busy and window.snapshot and window.snapshot['current_customer_ref'] == 'zhang-wei')
        assert window.balance_value.text() == '¥ 430.00' and window.amount.text() == ''
        assert window.recipient.count() == 0 and not window.prepare_transfer.isEnabled()
    finally:
        if window:
            window.close()
            window.deleteLater()
            qt.processEvents()
        service.close()
