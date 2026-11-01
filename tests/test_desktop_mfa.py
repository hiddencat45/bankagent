"""Real HTTP and native dialogs against an ephemeral ledger, no phone emulation in product."""
import os
import secrets
import time
from pathlib import Path


def test_native_enrollment_and_red_transfer(tmp_path, monkeypatch):
    if not os.environ.get('YOUDU_CAPTURE_MFA'):
        monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    import pyotp
    from PySide6.QtWidgets import QApplication, QDialog, QLineEdit
    from PySide6.QtCore import QTimer
    from desktop.app import LocalService
    from desktop.login import LoginWindow, LoginClient
    from desktop.security import EnrollmentDialog
    from desktop.client import business_confirmation
    from test_api_http import result
    app=QApplication.instance() or QApplication([])
    env={k:v for k,v in os.environ.items() if not k.startswith('BANKAGENT_MODEL_')}
    env.update(BANKAGENT_LOCAL_LOGIN='1',BANKAGENT_DB_PATH=str(tmp_path/'ui.sqlite3'))
    service=LocalService(env=env)
    shell=None
    def wait(predicate):
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            app.processEvents()
            if predicate(): return
            time.sleep(.01)
        raise AssertionError('native MFA flow timed out')
    def capture(name,widget):
        if os.environ.get('YOUDU_CAPTURE_MFA'):
            target=Path(os.environ['YOUDU_CAPTURE_MFA']); target.mkdir(parents=True,exist_ok=True)
            app.processEvents(); assert widget.grab().save(str(target/(name+'.png')))
    try:
        shell=LoginWindow(service.start())
        def create(client,username,funding):
            password=secrets.token_urlsafe(24)
            client.request('/auth/register',{'username':username,'display_name':'验收客户','password':password})
            client.token=client.request('/auth/login',{'username':username,'password':password})['token']
            def write(action,**fields):
                return result(client.resume(business_confirmation(client.form(action,fields)),'approve'))
            account=write('OPEN_ACCOUNT',display_name='日常账户')['data']['account_id']
            client.switch_account(account)
            write('ISSUE_DEBIT_CARD',display_name='日常卡'); write('ACTIVATE_DEBIT_CARD',card_name='日常卡')
            if funding: write('SIMULATE_CARD_DEPOSIT',card_name='日常卡',amount=funding)
            return password,client.get('/bank/desktop-objects')['data']['cards'][0]['card_number']
        password,_=create(shell.client,'native_sender','2000')
        receiver=LoginClient(shell.client.url)
        _,target=create(receiver,'native_receiver',None)
        pin=f'{secrets.randbelow(1000000):06d}'
        shell.client.request('/auth/payment-password',{'login_password':password,'payment_password':pin})
        shell.show_bank(); bank=shell.bank
        wait(lambda:not bank.busy and bank.snapshot is not None)
        bank.resize(1200,800)
        def close_levels():
            levels=next(w for w in app.topLevelWidgets() if isinstance(w,QDialog) and w.isVisible())
            capture('security-levels',levels); levels.accept()
        QTimer.singleShot(30,close_levels); bank.show_security_levels()
        bank.send('现在余额多少')
        wait(lambda:not bank.busy)
        assert '低风险' in bank.status.text()
        capture('low-risk-query',bank)
        app.processEvents(); wait(lambda:not bank.busy)
        bank.send(f'给{target}转1000元')
        wait(lambda:not bank.busy and bank.pending is not None)
        assert '中风险' in bank.confirmation_heading.text()
        assert '累计 ¥ 1,000.00' in bank.confirm_text.text()
        assert '所需验证：交易密码。' in bank.confirm_text.text()
        bank.toggle_assistant(True); capture('medium-risk-confirm',bank)
        bank.reject.click(); wait(lambda:not bank.busy and bank.pending is None)
        bank.toggle_assistant(False)
        app.processEvents(); wait(lambda:not bank.busy)
        dialog=EnrollmentDialog(shell.client,bank); dialog.show()
        app.processEvents(); capture('mfa-before-binding',dialog)
        # Observe only this isolated enrollment response to stand in for a phone authenticator.
        original=shell.client.request
        authenticator=[]
        def request(path,payload):
            response=original(path,payload)
            if path=='/auth/mfa/enroll': authenticator.append(pyotp.parse_uri(response['uri']))
            return response
        monkeypatch.setattr(shell.client,'request',request)
        dialog.entry.setText(password); dialog.send()
        wait(lambda:not dialog.busy)
        assert dialog.enrollment and not dialog.qr.pixmap().isNull()
        app.processEvents()
        assert dialog.height() <= dialog.screen().availableGeometry().height()
        assert dialog.entry.text()=='' and dialog.entry.echoMode()==QLineEdit.EchoMode.Password
        dialog.entry.setText(authenticator[0].now()); dialog.send()
        wait(lambda:not dialog.busy)
        assert dialog.result()==QDialog.DialogCode.Accepted
        assert shell.client.get('/auth/me')['mfa_configured']
        bank.send(f'给{target}转1001元')
        wait(lambda:not bank.busy and bank.pending is not None)
        assert bank.pending['risk_level']=='RED'
        assert '高风险' in bank.confirmation_heading.text()
        assert '累计 ¥ 1,001.00' in bank.confirm_text.text()
        assert '所需验证：交易密码＋手机动态码。' in bank.confirm_text.text()
        bank.toggle_assistant(True); capture('high-risk-confirm',bank)
        app.processEvents()
        assert bank.approve.isVisible()
        assert bank.assistant_box.rect().contains(bank.approve.mapTo(bank.assistant_box, bank.approve.rect().bottomRight()))
        errors=[]
        def fill():
            payment=next((w for w in app.topLevelWidgets() if isinstance(w,QDialog) and w.isVisible()),None)
            if payment is None:
                QTimer.singleShot(20,fill); return
            try:
                capture('mfa-payment',payment)  # Before secrets are entered; never capture QR.
                entries=payment.findChildren(QLineEdit)
                assert len(entries)==2 and all(e.echoMode()==QLineEdit.EchoMode.Password for e in entries)
                entries[0].setText(pin)
                entries[1].setText(authenticator[0].at(time.time()+30))
                payment.accept()
            except Exception as exc:
                errors.append(type(exc).__name__); payment.reject()
        QTimer.singleShot(30,fill); bank.approve.click()
        wait(lambda:not bank.busy and bank.pending is None)
        assert not errors
        assert shell.client.accounts()['accounts'][0]['balance_minor']==99900
        assert receiver.accounts()['accounts'][0]['balance_minor']==100100
        bank.load_accounts(); wait(lambda:not bank.busy)
        capture('mfa-paid-account',bank)
        print('Native MFA: sender 2000.00 -> 999.00; receiver 0.00 -> 1001.00; size',
              bank.width(),bank.height(),'DPR',bank.devicePixelRatioF())
    finally:
        if shell:
            if shell.bank:
                shell.bank.close(); shell.bank.deleteLater()
            shell.close(); shell.deleteLater(); app.processEvents()
        service.close()
