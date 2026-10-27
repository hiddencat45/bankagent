"""Real HTTP + Qt dialog, isolated ledger, no model or visible desktop."""
import time
import pytest
from desktop.app import LocalService
from test_desktop import offline_env


def test_auth_dialog_wrong_code_then_lost_response_replay(tmp_path, monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication, QLineEdit
    from PySide6.QtCore import QTimer
    from desktop.preview import PreviewWindow
    qt = QApplication.instance() or QApplication([])
    service = LocalService(env={**offline_env(), 'BANKAGENT_DB_PATH':str(tmp_path/'bank.sqlite3')})
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
        window.go_transfer.click()
        window.recipient.setCurrentIndex(window.recipient.findData('张伟'))
        window.amount.setText('1200')
        window.prepare_transfer.click()
        wait(lambda: not window.busy and window.pending is not None)
        assert window.pending['risk_level'] == 'RED' and window.verify.isEnabled()
        assert not window.approve.isEnabled()
        original = window.show_verification
        wrong = [True]
        def dialog(info):
            def fill():
                modal = qt.activeModalWidget()
                code = info['demo_code']
                if wrong[0]:
                    code = ('1' if code[0] != '1' else '2') + code[1:]
                modal.findChild(QLineEdit).setText(code)
                modal.accept()
            QTimer.singleShot(0, fill)
            original(info)
        monkeypatch.setattr(window, 'show_verification', dialog)
        window.verify.click()
        wait(lambda: not window.busy and '错误' in window.status.text())
        assert window.pending and not window.uncertain and window.verify.isEnabled()
        assert window.client.accounts()['accounts'][0]['balance_minor'] == 500000
        wrong[0] = False
        resume = window.client.resume
        def lost(pending, decision, otp=None):
            resume(pending, decision, otp)
            raise TimeoutError('response lost after commit')
        monkeypatch.setattr(window.client, 'resume', lost)
        window.verify.click()
        wait(lambda: not window.busy and window.uncertain)
        monkeypatch.setattr(window.client, 'resume', resume)
        window.retry.click()
        wait(lambda: not window.busy and window.pending is None and window.balance_value.text() == '¥ 3,800.00')
        assert len([r for r in window.snapshot['ledger']['transactions'] if r['kind'] == 'TRANSFER_OUT']) == 1
    finally:
        if window:
            window.close()
            window.deleteLater()
            qt.processEvents()
        service.close()
