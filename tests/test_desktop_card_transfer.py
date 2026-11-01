"""Two registered clients, real loopback HTTP, native form and PIN dialog."""
import os
import secrets
import time
from pathlib import Path
from types import SimpleNamespace

import httpx

from test_card_number_transfer import customer


def test_registered_card_transfer_window(tmp_path, monkeypatch):
    capture = os.environ.get('YOUDU_CAPTURE_CARD_TRANSFER')
    if not capture:
        monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QDialog, QLineEdit
    from desktop.app import LocalService
    from desktop.login import LoginClient, AuthenticatedWindow
    app = QApplication.instance() or QApplication([])
    env = {k:v for k,v in os.environ.items() if not k.startswith('BANKAGENT_MODEL_')}
    env.update(BANKAGENT_LOCAL_LOGIN='1', BANKAGENT_DB_PATH=str(tmp_path/'bank.sqlite3'))
    service = LocalService(env=env)
    window = None
    def wait(predicate):
        until = time.monotonic()+25
        while time.monotonic()<until:
            app.processEvents()
            if predicate(): return
            time.sleep(.01)
        raise AssertionError(window.status.text())
    def shot(name):
        if capture:
            path = Path(capture); path.mkdir(parents=True, exist_ok=True)
            app.processEvents()
            assert window.grab().save(str(path/(name+'.png')))
    try:
        url = service.start()
        with httpx.Client(base_url=url, timeout=30) as c:
            a, password, own = customer(c, 'sender')
            b, _, number = customer(c, 'receiver')
            pin = f'{secrets.randbelow(1000000):06d}'
            c.post('/auth/payment-password', headers=a, json={
                'login_password':password, 'payment_password':pin}).raise_for_status()
            client = LoginClient(url); client.token = a['Authorization'].split(' ',1)[1]
            window = AuthenticatedWindow(SimpleNamespace(client=client))
            window.resize(1200,800); window.show()
            wait(lambda:not window.busy and window.snapshot is not None)
            assert window.balance_value.text()=='¥ 1,000.00'
            window.card_list.setCurrentRow(0)
            assert own[-4:] in window.card_note.text() and own not in window.card_note.text()
            window.go_transfer.click(); window.recipient.setEditText(number); window.amount.setText('40')
            assert window.prepare_transfer.isEnabled()
            shot('card-transfer-form')
            window.prepare_transfer.click(); wait(lambda:not window.busy and window.pending is not None)
            assert number[-4:] in window.confirm_text.text() and number not in window.confirm_text.text()
            window.edit.click(); wait(lambda:not window.busy and window.pending is None)
            assert window.recipient_value()==number and window.amount.text()=='40'
            window.amount.setText('30'); window.prepare_transfer.click()
            wait(lambda:not window.busy and window.pending is not None)
            shot('card-transfer-confirm')
            def fill_pin():
                dialog=next((w for w in app.topLevelWidgets() if isinstance(w,QDialog) and w.isVisible()),None)
                if not dialog:
                    QTimer.singleShot(20,fill_pin); return
                entries=dialog.findChildren(QLineEdit)
                assert len(entries)==1 and entries[0].echoMode()==QLineEdit.EchoMode.Password
                entries[0].setText(pin); dialog.accept()
            QTimer.singleShot(100,fill_pin); window.approve.click()
            wait(lambda:not window.busy and window.pending is None and window.balance_value.text()=='¥ 970.00')
            shot('card-transfer-result')
            assert c.get('/bank/accounts',headers=b).json()['accounts'][0]['balance_minor']==103000
            # AI card-number confirmation also retains the original candidate when editing.
            window.send(f'给{number}转20元')
            wait(lambda:not window.busy and window.pending is not None)
            window.edit.click(); wait(lambda:not window.busy and window.pending is None and window.amount.text()=='20.00')
            assert window.recipient_value()==number
            assert c.get('/bank/accounts',headers=a).json()['accounts'][0]['balance_minor']==97000
    finally:
        if window: window.close()
        service.close()
