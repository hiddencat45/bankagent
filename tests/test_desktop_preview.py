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
        original_customer = window.snapshot['current_customer_ref']
        original_account = window.snapshot['current_account_ref']
        other_account = next(a['account_ref'] for a in window.snapshot['accounts'] if a['account_ref'] != original_account)
        window.choose_context('account', other_account)
        wait(lambda: not window.busy and window.snapshot and window.snapshot['current_account_ref'] == other_account)
        assert window.balance_value.text() == '¥ 0.00'
        assert window.context_account.text() in window.ai_context.text()
        window.choose_context('account', original_account)
        wait(lambda: not window.busy and window.snapshot and window.snapshot['current_account_ref'] == original_account)
        assert window.context_account.text() == '默认演示账户'
        assert '默认演示客户' in window.customer_picker.text()
        window.choose_context('customer', 'not-a-server-reference')
        assert not window.busy
        assert window.card_list.count() == 1
        window.card_list.setCurrentRow(0)
        assert '日常消费卡' in window.card_note.text() and '已激活' in window.card_note.text()
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
        assert not window.account_picker.isEnabled() and not window.customer_picker.isEnabled()
        window.choose_context('customer', 'zhang-wei')
        assert window.pending == old and not window.busy
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
        window.choose_context('customer', 'zhang-wei')
        wait(lambda: not window.busy and window.snapshot and window.snapshot['current_customer_ref'] == 'zhang-wei')
        assert window.balance_value.text() == '¥ 430.00' and window.amount.text() == ''
        assert window.recipient.count() == 0 and not window.prepare_transfer.isEnabled()
        assert '张伟' in window.customer_picker.text() and '张伟' in window.context_heading.text()
        assert window.context_account.text() in window.ai_context.text()
        assert window.context_account.text() in window.payer.text()
        window.choose_context('customer', original_customer)
        wait(lambda: not window.busy and window.snapshot and window.snapshot['current_customer_ref'] == original_customer)
        assert window.balance_value.text() == '¥ 4,970.00'
        assert '默认演示客户' in window.context_heading.text()
    finally:
        if window:
            window.close()
            window.deleteLater()
            qt.processEvents()
        service.close()
