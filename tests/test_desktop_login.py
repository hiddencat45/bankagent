import os
import secrets
import time


def test_native_registration_onboarding_and_logout(tmp_path, monkeypatch):
    if not os.environ.get('YOUDU_CAPTURE_LOGIN'):
        monkeypatch.setenv('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtWidgets import QApplication, QDialog, QLineEdit
    from PySide6.QtCore import QTimer
    from desktop.app import LocalService
    from desktop.login import LoginWindow
    from desktop.client import business_confirmation
    app = QApplication.instance() or QApplication([])
    env={k:v for k,v in os.environ.items() if not k.startswith('BANKAGENT_MODEL_')}
    env.update(BANKAGENT_LOCAL_LOGIN='1',BANKAGENT_DB_PATH=str(tmp_path/'bank.sqlite3'))
    service=LocalService(env=env)
    window=None
    def wait(predicate):
        until=time.monotonic()+25
        while time.monotonic()<until:
            app.processEvents()
            if predicate(): return
            time.sleep(.01)
        raise AssertionError(window.status.text())
    password=secrets.token_urlsafe(24)
    def capture(name, widget):
        if os.environ.get('YOUDU_CAPTURE_LOGIN'):
            from pathlib import Path
            target=Path(os.environ['YOUDU_CAPTURE_LOGIN']); target.mkdir(parents=True,exist_ok=True)
            app.processEvents(); assert widget.grab().save(str(target/(name+'.png')))
    try:
        window=LoginWindow(service.start()); window.show()
        app.processEvents(); capture('login',window)
        for k,v in {'username':'new_user','display_name':'测试新客户','password':password,'repeat':password}.items():
            window.fields[k].setText(v)
        window.register.click(); wait(lambda:not window.busy)
        assert '注册成功' in window.status.text()
        window.fields['password'].setText(password); window.login.click()
        wait(lambda:not window.busy and window.open_account.isVisible())
        assert window.client.get('/bank/accounts')['accounts']==[]
        window.open_account.click(); wait(lambda:not window.busy and window.pending is not None)
        assert '1,000.00' in window.status.text()
        window.approve.click()
        wait(lambda:window.bank is not None and not window.bank.busy and window.bank.snapshot is not None)
        assert window.bank.balance_value.text()=='¥ 1,000.00'
        assert not window.bank.switch_customer.isEnabled()
        assert not window.bank.customer_picker.isEnabled()
        capture('account',window.bank)
        bank=window.bank
        bank.toggle_assistant(True); app.processEvents(); capture('assistant',bank)
        bank.toggle_assistant(False)
        pending=business_confirmation(window.client.form('OPEN_ACCOUNT',{'display_name':'储蓄账户'}))
        window.client.resume(pending,'approve')
        bank.send('给储蓄账户转30元')
        wait(lambda:not bank.busy and bank.pending is not None)
        pin=f'{secrets.randbelow(1000000):06d}'
        def fill(values):
            dialog=next((w for w in app.topLevelWidgets() if isinstance(w,QDialog) and w.isVisible()),None)
            if dialog is None:
                QTimer.singleShot(20,lambda:fill(values)); return
            capture('payment-dialog',dialog)
            entries=dialog.findChildren(QLineEdit)
            assert len(entries)==len(values)
            for entry,value in zip(entries,values):
                assert entry.echoMode()==QLineEdit.EchoMode.Password
                entry.setText(value)
            dialog.accept()
        # Directly drive the same native dialog; actual profile fetch is exercised on approval below.
        QTimer.singleShot(20,lambda:fill([password,pin,pin]))
        bank.payment_dialog(False)
        wait(lambda:not bank.busy)
        QTimer.singleShot(100,lambda:fill([pin]))
        bank.approve.click()
        wait(lambda:not bank.busy and bank.pending is None and bank.balance_value.text()=='¥ 970.00')
        window.client.request('/auth/logout',{}); window.logged_out()
        assert window.client.token is None and window.isVisible()
        window.fields['username'].setText('new_user'); window.fields['password'].setText(password)
        window.login.click()
        wait(lambda:window.bank is not None and not window.bank.busy and window.bank.snapshot is not None)
        assert window.bank.balance_value.text()=='¥ 970.00'
    finally:
        if window:
            if window.bank: window.bank.close()
            window.close()
        service.close()


def test_formal_entry_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtWidgets import QApplication
    import desktop.app as entry
    from desktop.login import LoginWindow
    app=QApplication.instance() or QApplication([])
    env={k:v for k,v in os.environ.items() if not k.startswith('BANKAGENT_MODEL_')}
    env['BANKAGENT_DB_PATH']=str(tmp_path/'formal.sqlite3')
    monkeypatch.setattr(entry,'desktop_environment',lambda:dict(env))
    monkeypatch.setattr(entry.sys,'argv',['desktop/app.py'])
    monkeypatch.setattr('PySide6.QtWidgets.QApplication',lambda *args:app)
    def drive():
        from urllib.error import HTTPError
        import pytest
        window=next(w for w in app.topLevelWidgets() if isinstance(w,LoginWindow) and w.isVisible())
        assert window.client.token is None and window.bank is None
        with pytest.raises(HTTPError) as error: window.client.request('/demo/session',{})
        assert error.value.code==404
        window.close(); window.deleteLater(); app.processEvents()
        return 0
    monkeypatch.setattr(app,'exec',drive)
    import ctypes
    if hasattr(ctypes,'windll'):
        monkeypatch.setattr(ctypes.windll.user32,'MessageBoxW',lambda *a: (_ for _ in ()).throw(AssertionError(a[1])))
    entry.main()
