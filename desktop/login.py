"""Native login/onboarding shell using the same authenticated business client."""
import json
import threading
from urllib.request import Request
from urllib.error import HTTPError
from PySide6.QtCore import Signal, QObject, Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
                              QDialog, QDialogButtonBox, QMenu)
from desktop.client import QueryClient, business_confirmation, VerificationRejected
from desktop.preview import PreviewWindow
from desktop.theme import STYLE, load_chinese_font


class LoginClient(QueryClient):
    def get(self, path):
        with self.opener.open(Request(self.url + path, headers={'Authorization':'Bearer ' + (self.token or '')}), timeout=20) as response:
            return json.load(response)

    def connect(self):
        return self.get('/auth/me')['mode']

    def overview(self):
        profile = self.get('/auth/me')
        return {**self.accounts(), 'customers':[{'customer_ref':'self', 'display_name':profile['display_name']}],
                'current_customer_ref':'self'}

    def request(self, path, payload):
        try:
            with self.post(path, payload) as response:
                return json.load(response)
        except HTTPError as exc:
            if path == '/auth/payment-password' and exc.code in {400,401,409}:
                raise VerificationRejected(json.load(exc).get('message', '交易密码设置失败。')) from None
            raise


class Finished(QObject):
    result = Signal(object, object)


class LoginWindow(QWidget):
    def __init__(self, url, ledger_path=''):
        super().__init__()
        load_chinese_font()
        self.client = LoginClient(url)
        self.ledger_path = ledger_path
        self.bank = None
        self.busy = False
        self.pending = None
        self.setWindowTitle('有度 · 登录本地模拟银行')
        self.resize(520, 620)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self); layout.setContentsMargins(42, 32, 42, 32)
        title = QLabel('有度'); title.setObjectName('title'); layout.addWidget(title)
        layout.addWidget(QLabel('本地账号 · 虚构资金 · 不代表银行实名认证'))
        self.fields = {}
        for key, label, secret in [('username','用户名（4–32位字母、数字或下划线）',False),
                ('display_name','显示姓名（注册时填写）',False), ('password','登录密码（10–128位）',True),
                ('repeat','再次输入密码（注册时填写）',True)]:
            entry = QLineEdit(); entry.setPlaceholderText(label); entry.setAccessibleName(label)
            entry.setMaxLength(128)
            if secret: entry.setEchoMode(QLineEdit.EchoMode.Password)
            self.fields[key] = entry; layout.addWidget(entry)
        self.login = QPushButton('登录'); self.login.setObjectName('primary')
        self.register = QPushButton('注册新客户')
        self.login.clicked.connect(self.sign_in); self.register.clicked.connect(self.sign_up)
        layout.addWidget(self.login); layout.addWidget(self.register)
        self.account = QLineEdit('日常账户'); self.account.setAccessibleName('首次账户名称')
        self.open_account = QPushButton('准备首次开户')
        self.approve = QPushButton('确认开户及演示入账')
        self.cancel = QPushButton('取消开户')
        self.open_account.clicked.connect(self.prepare_account)
        self.approve.clicked.connect(lambda: self.finish_account('approve'))
        self.cancel.clicked.connect(lambda: self.finish_account('reject'))
        for widget in (self.account, self.open_account, self.approve, self.cancel):
            layout.addWidget(widget); widget.hide()
        self.status = QLabel('新用户请先注册。旧演示客户暂不开放登录。')
        self.status.setWordWrap(True); self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status); layout.addStretch()
        self.delivery = Finished(self); self.delivery.result.connect(self.finished)

    def work(self, function, callback):
        if self.busy: return
        self.busy = True; self.setEnabled(False)
        if self.bank: self.bank.setEnabled(False)
        def run():
            try: answer = (True, function())
            except HTTPError as exc:
                try: message = json.load(exc).get('message', '请求被拒绝。')
                except Exception: message = '请求被拒绝。'
                answer = (False, message)
            except Exception: answer = (False, '连接或结果尚未确认。请先重新登录核对，不要重复开户。')
            self.delivery.result.emit(answer, callback)
        threading.Thread(target=run, daemon=True).start()

    def finished(self, answer, callback):
        self.busy = False; self.setEnabled(True)
        if self.bank: self.bank.setEnabled(True)
        if answer[0]: callback(answer[1])
        else:
            self.status.setText(answer[1])
            if self.bank: self.bank.status.setText(answer[1])

    def sign_up(self):
        values = {k: v.text() for k,v in self.fields.items()}
        if values['password'] != values.pop('repeat'):
            self.status.setText('两次登录密码不一致。'); return
        self.fields['password'].clear(); self.fields['repeat'].clear()
        self.work(lambda: self.client.request('/auth/register', values),
                  lambda _: self.status.setText('注册成功，请输入密码登录。尚未开户或入账。'))

    def sign_in(self):
        values = {k:self.fields[k].text() for k in ('username','password')}
        self.fields['password'].clear(); self.fields['repeat'].clear()
        self.work(lambda: self.client.request('/auth/login', values), self.signed_in)

    def signed_in(self, result):
        self.client.token = result['token']
        if result['needs_account']:
            self.status.setText('登录成功。当前没有银行账户，请先开户；确认后记入1000元演示资金。')
            self.account.show(); self.open_account.show()
        else: self.show_bank()

    def prepare_account(self):
        name = self.account.text()
        self.work(lambda: self.client.form('OPEN_ACCOUNT', {'display_name':name}), self.prepared)

    def prepared(self, frames):
        self.pending = business_confirmation(frames)
        if not self.pending:
            self.status.setText('未生成开户确认，请核对名称。'); return
        self.status.setText(self.pending['summary'])
        self.approve.show(); self.cancel.show(); self.open_account.hide(); self.account.setReadOnly(True)

    def finish_account(self, decision):
        pending = self.pending
        if not pending: return
        self.work(lambda: self.client.resume(pending, decision), lambda frames:self.account_finished(frames, decision))

    def account_finished(self, frames, decision):
        if frames[-1][1]['status'] not in {'COMPLETED','REJECTED'}:
            self.status.setText('开户未完成，请核对原操作结果。'); return
        if decision == 'reject':
            self.pending = None; self.approve.hide(); self.cancel.hide(); self.open_account.show()
            self.account.setReadOnly(False); self.status.setText('已取消，未开户。'); return
        receipt = next(d['payload'] for e,d in frames if e == 'card' and d['type']=='result')
        if receipt['status'] != 'COMPLETED':
            self.status.setText('开户失败，未进入业务页面。'); return
        account = receipt['data']['account_id']
        self.work(lambda: self.client.switch_account(account), lambda _: self.show_bank())

    def show_bank(self):
        self.pending = None
        self.bank = AuthenticatedWindow(self)
        self.bank.statusBar().showMessage('当前账本：' + self.ledger_path)
        self.bank.show(); self.hide()

    def logged_out(self):
        self.client.token = None
        self.show()
        self.bank.close(); self.bank.deleteLater(); self.bank = None
        for entry in self.fields.values(): entry.clear()
        for widget in (self.account,self.open_account,self.approve,self.cancel): widget.hide()
        self.account.setReadOnly(False); self.pending = None
        self.status.setText('已退出登录。'); self.show()


class AuthenticatedWindow(PreviewWindow):
    def __init__(self, shell):
        self.shell = shell
        super().__init__(shell.client.url, client=shell.client)
        self.create_customer.hide()
        self.verify.clicked.disconnect()
        self.verify.clicked.connect(lambda: self.decide('approve'))

    def controls(self):
        super().controls()
        self.switch_customer.setEnabled(False); self.create_customer.setEnabled(False)
        if hasattr(self, 'customer_picker'):
            self.customer_picker.setEnabled(False)
            self.customer_picker.setText(self.current_customer.text().removeprefix('当前演示客户：') + '\n本地登录客户')
            self.customer_picker.setToolTip('如需更换客户，请从右上菜单退出登录。')
        if self.pending and ('recipient' in self.pending or 'items' in self.pending):
            self.verify.hide()
            self.approve.setVisible(self.decision is None)
            self.approve.setEnabled(not self.busy and not self.uncertain and self.decision is None)
            self.approve.setText('确认并验证交易密码')

    def show_connection_menu(self):
        menu = QMenu(self)
        action = menu.addAction('退出登录')
        action.setEnabled(not self.busy and not self.pending and not self.uncertain)
        action.triggered.connect(lambda: self.shell.work(lambda: self.client.request('/auth/logout', {}),
                                                        lambda _: self.shell.logged_out()))
        menu.exec(self.more_actions.mapToGlobal(self.more_actions.rect().bottomLeft()))

    def decide(self, decision, otp=None):
        if decision != 'approve' or self.decision is not None or not self.pending or not ('recipient' in self.pending or 'items' in self.pending):
            return super().decide(decision, otp)
        self.run('payment_profile', lambda: self.client.get('/auth/me'))

    def receive(self, kind, result):
        if kind == 'payment_profile':
            self.busy = False; self.controls(); self.payment_dialog(result['payment_configured']); return
        if kind == 'payment_setup':
            self.busy = False; self.controls(); self.status.setText('交易密码已设置，请再次确认原转账。'); return
        super().receive(kind, result)

    def payment_dialog(self, configured):
        dialog = QDialog(self); dialog.setWindowTitle('交易密码认证' if configured else '首次设置交易密码')
        dialog.resize(460, 360); layout = QVBoxLayout(dialog)
        summary = QLabel(self.confirm_text.text()); summary.setWordWrap(True); summary.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(summary)
        entries = []
        for name in (['交易密码'] if configured else ['登录密码','6位数字交易密码','再次输入交易密码']):
            entry=QLineEdit(); entry.setPlaceholderText(name); entry.setAccessibleName(name)
            entry.setEchoMode(QLineEdit.EchoMode.Password); entry.setMaxLength(128 if name=='登录密码' else 6)
            layout.addWidget(entry); entries.append(entry)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('验证并转账' if configured else '设置交易密码')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('返回核对')
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
        accepted=dialog.exec()==QDialog.DialogCode.Accepted
        values=[e.text() for e in entries]
        for entry in entries: entry.clear()
        dialog.deleteLater()
        if not accepted: return
        if configured: super().decide('approve', values[0])
        elif values[1]!=values[2]: self.status.setText('两次交易密码不一致，尚未执行。')
        else:
            self.run('payment_setup', lambda: self.client.request('/auth/payment-password',
                {'login_password':values[0],'payment_password':values[1]}))
