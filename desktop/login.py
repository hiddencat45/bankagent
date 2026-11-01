"""Native login/onboarding shell using the same authenticated business client."""
import json
import threading
from urllib.request import Request
from urllib.error import HTTPError
from PySide6.QtCore import Signal, QObject, Qt
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPainterPath, QPen
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
                              QDialog, QDialogButtonBox, QMenu, QHBoxLayout, QStackedWidget)
from desktop.client import QueryClient, business_confirmation, VerificationRejected, money
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
            if (path == '/auth/payment-password' or path.startswith('/auth/mfa/')) and exc.code in {400,401,409}:
                raise VerificationRejected(json.load(exc).get('message', '交易密码设置失败。')) from None
            raise


class Finished(QObject):
    result = Signal(object, object)


class BrandPanel(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor('#124e40')); gradient.setColorAt(1, QColor('#54a183'))
        painter.fillRect(self.rect(), gradient)
        painter.setPen(QPen(QColor(225, 247, 234, 90), 1.5))
        for offset in (0, 24, 65):
            path = QPainterPath(); path.moveTo(-20, self.height()*.64+offset)
            path.cubicTo(self.width()*.35, self.height()*.86+offset,
                         self.width()*.65, self.height()*.48+offset, self.width()+20, self.height()*.67+offset)
            painter.drawPath(path)
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(235, 255, 240, 90))
        for x,y,r in ((.15,.50,5),(.38,.43,8),(.7,.35,5),(.84,.53,10),(.6,.61,4)):
            painter.drawEllipse(int(self.width()*x), int(self.height()*y),r*2,r*2)


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
        self.resize(860, 590); self.setMinimumSize(760, 570)
        self.setStyleSheet(STYLE + '''
            LoginWindow, QWidget#authForm {background:white;}
            QWidget#authPage, QWidget#authPage QLabel, QStackedWidget {background:white;border:0;}
            QWidget#authForm QLineEdit {border:0;border-bottom:1px solid #dce5e0;
                border-radius:0;padding:12px 2px;background:white;}
            QWidget#authForm QLineEdit:focus {border-bottom:2px solid #24674e;}
            QPushButton#authLink {background:transparent;color:#24674e;text-align:left;padding:8px 0;}
            QLabel#authHeading {font-size:23px;font-weight:600;background:transparent;}
            QLabel#authNote {font-size:12px;color:#73857c;background:transparent;}
        ''')
        outer = QHBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        brand = BrandPanel(); brand.setMinimumWidth(240); brand.setMaximumWidth(300)
        brand_layout = QVBoxLayout(brand); brand_layout.setContentsMargins(30,44,26,32)
        for value, size in [('有度',36),('你的本地银行助手',17)]:
            label=QLabel(value); label.setStyleSheet(f'background:transparent;color:white;font-size:{size}px;')
            brand_layout.addWidget(label)
        brand_layout.addStretch()
        note=QLabel('账户 · 卡片 · AI 对话\n每一步资金操作，都由你确认')
        note.setStyleSheet('background:transparent;color:#e1f3e8;font-size:13px;'); note.setWordWrap(True)
        brand_layout.addWidget(note); outer.addWidget(brand, 1)
        form=QWidget(); form.setObjectName('authForm'); outer.addWidget(form, 2)
        layout=QVBoxLayout(form); layout.setContentsMargins(36,30,36,24); layout.setSpacing(12)
        title=QLabel('有度  /  本地模拟银行'); title.setObjectName('authHeading'); layout.addWidget(title)
        self.pages=QStackedWidget(); layout.addWidget(self.pages,1)
        login_page=QWidget(); register_page=QWidget(); onboarding_page=QWidget()
        for page in (login_page,register_page,onboarding_page):
            page.setObjectName('authPage'); self.pages.addWidget(page)
        login_layout=QVBoxLayout(login_page); register_layout=QVBoxLayout(register_page)
        onboard_layout=QVBoxLayout(onboarding_page)
        for page_layout in (login_layout,register_layout,onboard_layout):
            page_layout.setContentsMargins(0,14,0,0); page_layout.setSpacing(12)
        login_layout.addWidget(QLabel('账号密码登录'))
        register_layout.addWidget(QLabel('创建本地账号'))
        self.fields = {}
        self.register_fields = {}
        for target, page_layout, specs in (
                (self.fields,login_layout,[('username','用户名',False),('password','登录密码',True)]),
                (self.register_fields,register_layout,[('username','用户名：4–32位字母、数字或下划线',False),
                    ('display_name','显示姓名',False),('password','登录密码：10–128位',True),('repeat','确认登录密码',True)])):
            for key,label,secret in specs:
                entry=QLineEdit(); entry.setPlaceholderText(label); entry.setAccessibleName(label); entry.setMaxLength(128)
                if secret: entry.setEchoMode(QLineEdit.EchoMode.Password)
                target[key]=entry; page_layout.addWidget(entry)
        self.login = QPushButton('登录'); self.login.setObjectName('primary')
        self.register = QPushButton('注册账号'); self.register.setObjectName('primary')
        self.login.clicked.connect(self.sign_in); self.register.clicked.connect(self.sign_up)
        login_layout.addWidget(self.login); login_layout.addStretch()
        register_layout.addWidget(self.register); register_layout.addStretch()
        self.to_register=QPushButton('还没有账号？  注册新账号 →'); self.to_register.setObjectName('authLink')
        self.to_login=QPushButton('← 返回登录'); self.to_login.setObjectName('authLink')
        self.to_register.clicked.connect(lambda:self.switch_page(1)); self.to_login.clicked.connect(lambda:self.switch_page(0))
        login_layout.addWidget(self.to_register); register_layout.addWidget(self.to_login)
        self.fields['password'].returnPressed.connect(self.sign_in)
        self.register_fields['repeat'].returnPressed.connect(self.sign_up)
        onboard_layout.addWidget(QLabel('欢迎使用 · 开立首个账户'))
        self.account = QLineEdit('日常账户'); self.account.setAccessibleName('首次账户名称')
        self.open_account = QPushButton('准备首次开户')
        self.approve = QPushButton('确认开户及演示入账')
        self.cancel = QPushButton('取消开户')
        self.open_account.clicked.connect(self.prepare_account)
        self.approve.clicked.connect(lambda: self.finish_account('approve'))
        self.cancel.clicked.connect(lambda: self.finish_account('reject'))
        for widget in (self.account, self.open_account, self.approve, self.cancel):
            onboard_layout.addWidget(widget); widget.hide()
        onboard_layout.addStretch()
        self.status = QLabel('新用户请先注册。旧演示客户暂不开放登录。')
        self.status.setWordWrap(True); self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setObjectName('authNote'); layout.addWidget(self.status)
        footer=QLabel('本地模拟 · 虚构资金 · 不代表银行实名认证'); footer.setObjectName('authNote')
        footer.setWordWrap(True); layout.addWidget(footer)
        self.delivery = Finished(self); self.delivery.result.connect(self.finished)

    def switch_page(self, index):
        if self.busy or self.pending: return
        for fields in (self.fields,self.register_fields):
            for key in ('password','repeat'):
                if key in fields: fields[key].clear()
        self.pages.setCurrentIndex(index)
        self.status.setText('注册仅建立本地客户身份，不自动开户或入账。' if index else '新用户请先注册。旧演示客户暂不开放登录。')
        (self.register_fields if index else self.fields)['username'].setFocus()

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
        values = {k: v.text() for k,v in self.register_fields.items()}
        if values['password'] != values.pop('repeat'):
            self.status.setText('两次登录密码不一致。'); return
        self.register_fields['password'].clear(); self.register_fields['repeat'].clear()
        self.work(lambda: self.client.request('/auth/register', values),
                  lambda _: self.registered(values['username']))

    def registered(self, username):
        self.switch_page(0); self.fields['username'].setText(username)
        self.fields['password'].setFocus()
        self.status.setText('注册成功，请输入密码登录。尚未开户或入账。')

    def sign_in(self):
        values = {k:self.fields[k].text() for k in ('username','password')}
        self.fields['password'].clear()
        self.work(lambda: self.client.request('/auth/login', values), self.signed_in)

    def signed_in(self, result):
        self.client.token = result['token']
        if result['needs_account']:
            self.pages.setCurrentIndex(2)
            self.status.setText('登录成功。请先开立零余额账户，再申请并激活借记卡。需要测试资金时可手动模拟入金。')
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
        self.bank.statusBar().showMessage('本地模拟账本 · 非真实资金')
        self.bank.show(); self.hide()

    def logged_out(self):
        self.client.token = None
        self.show()
        self.bank.close(); self.bank.deleteLater(); self.bank = None
        for fields in (self.fields,self.register_fields):
            for entry in fields.values(): entry.clear()
        for widget in (self.account,self.open_account,self.approve,self.cancel): widget.hide()
        self.account.setReadOnly(False); self.pending = None
        self.switch_page(0); self.status.setText('已退出登录。'); self.show()


class AuthenticatedWindow(PreviewWindow):
    def __init__(self, shell):
        self.shell = shell
        self.read_only_result = False
        super().__init__(shell.client.url, client=shell.client)
        self.create_customer.hide()
        self.verify.clicked.disconnect()
        self.verify.clicked.connect(lambda: self.decide('approve'))

    def run(self, kind, function):
        if kind != 'accounts':
            self.read_only_result = False
        super().run(kind, function)

    def controls(self):
        super().controls()
        self.switch_customer.setEnabled(False); self.create_customer.setEnabled(False)
        if hasattr(self, 'customer_picker'):
            self.more_actions.setToolTip('安全分级、手机验证器与退出登录')
            self.customer_picker.setEnabled(False)
            self.customer_picker.setText(self.current_customer.text().removeprefix('当前演示客户：') + '\n本地登录客户')
            self.customer_picker.setToolTip('如需更换客户，请从右上菜单退出登录。')
        if self.pending and ('recipient' in self.pending or 'items' in self.pending or self.pending.get('operation') == 'SUBSCRIBE_WEALTH'):
            self.verify.hide()
            self.approve.setVisible(self.decision is None)
            self.approve.setEnabled(not self.busy and not self.uncertain and self.decision is None)
            self.approve.setText('确认并追加安全验证' if self.pending['risk_level'] == 'RED' else '确认并验证交易密码')
        else:
            self.approve.setVisible(self.pending is not None and self.decision is None)
            self.approve.setText('确认办理')

    def show_connection_menu(self):
        menu = QMenu(self)
        menu.addAction('安全分级说明').triggered.connect(self.show_security_levels)
        menu.addAction('诊断信息').triggered.connect(self.show_diagnostics)
        security = menu.addAction('绑定手机验证器')
        security.setEnabled(not self.busy and not self.uncertain)
        security.triggered.connect(self.bind_authenticator)
        action = menu.addAction('退出登录')
        action.setEnabled(not self.busy and not self.pending and not self.uncertain)
        action.triggered.connect(lambda: self.shell.work(lambda: self.client.request('/auth/logout', {}),
                                                        lambda _: self.shell.logged_out()))
        menu.exec(self.more_actions.mapToGlobal(self.more_actions.rect().bottomLeft()))

    def show_diagnostics(self):
        dialog=QDialog(self); dialog.setWindowTitle('本地账本诊断'); dialog.resize(560,180)
        layout=QVBoxLayout(dialog)
        label=QLabel('当前账本：\n'+(self.shell.ledger_path or '自动验收临时账本'))
        label.setTextFormat(Qt.TextFormat.PlainText); label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); layout.addWidget(label)
        close=QPushButton('关闭'); close.clicked.connect(dialog.accept); layout.addWidget(close)
        dialog.exec()

    def show_security_levels(self):
        dialog = QDialog(self); dialog.setWindowTitle('安全分级 · 权限与风险'); dialog.resize(540, 420)
        layout = QVBoxLayout(dialog); layout.setContentsMargins(28,24,28,24); layout.setSpacing(16)
        for title, body in [
            ('低风险 · 本人信息查询', '登录后查询本人的余额、卡片和账单；不能读取其他客户数据。'),
            ('中风险 · 确认后办理', '写业务先核对并确认。转账含本次累计不超过1,000元，还需交易密码。'),
            ('高风险 · 追加独立认证', '同一客户所有卡当日累计转出，含本次或整批超过1,000元，或任意金额的模拟理财申购，需交易密码＋手机动态码。'),
            ('禁止执行 · 认证也不能放行', '冻结、余额不足、超限或不属于本人的付款卡，仍由服务端拒绝。AI与普通页面遵守相同规则。')]:
            heading=QLabel(title); heading.setObjectName('dialogHeading'); layout.addWidget(heading)
            label=QLabel(body); label.setWordWrap(True); layout.addWidget(label)
        close=QPushButton('知道了'); close.clicked.connect(dialog.accept); layout.addWidget(close)
        dialog.exec(); dialog.deleteLater()

    def present_security(self):
        if not self.pending or self.decision is not None:
            return
        transfer = 'recipient' in self.pending or 'items' in self.pending
        high = self.pending['risk_level'] == 'RED'
        self.confirmation_heading.setText('高风险 · 需要追加安全验证' if high else '中风险 · 核对后确认办理')
        self.confirmation_heading.setStyleSheet('color:#9a3e18;' if high else 'color:#795b16;')
        details = []
        if transfer:
            snapshot = self.pending.get('risk_context')
            if snapshot:
                details.append('客户当日已转出 ¥ ' + money(snapshot['daily_transfer_total_minor'])
                    + ' ＋ 本次' + ('整批' if 'items' in self.pending else '') + ' ¥ ' + money(snapshot['current_amount_minor'])
                    + ' ＝ 累计 ¥ ' + money(snapshot['projected_total_minor']))
                details.append('范围：本人所有卡／账户；升级阈值：超过 ¥ ' + money(snapshot['threshold_minor']) + '。')
            details.append(('所需验证：交易密码＋手机动态码。' if high else '所需验证：交易密码。') + ' 执行前仍会复核资金规则。')
        elif self.pending.get('operation') == 'SUBSCRIBE_WEALTH':
            details.append('理财申购不论金额均需交易密码＋手机动态码。验证通过后仅提交模拟订单，尚未成交。')
        else:
            details.append('所需操作：核对内容并确认，尚未执行业务变更。')
        self.confirm_text.setText(('付款账户：' if transfer else '办理账户：') + self.context_account.text()
            + '\n' + self.pending['summary'] + '\n' + '\n'.join(details))
        self.confirm_text.setMinimumHeight(0)
        self.confirmation.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
        self.confirm_text.setToolTip('累计金额为确认时快照；执行前复核，冻结、余额不足、限额或归属不符仍拒绝执行。')

    def bind_authenticator(self):
        from desktop.security import EnrollmentDialog
        if EnrollmentDialog(self.client, self).exec() == QDialog.DialogCode.Accepted:
            self.status.setText('手机验证器已绑定。等待下一组动态码，再重新核对原操作；尚未扣款。')

    def decide(self, decision, otp=None):
        if decision != 'approve' or self.decision is not None or not self.pending or not ('recipient' in self.pending or 'items' in self.pending or self.pending.get('operation') == 'SUBSCRIBE_WEALTH'):
            return super().decide(decision, otp)
        self.run('payment_profile', lambda: self.client.get('/auth/me'))

    def receive(self, kind, result):
        if kind == 'payment_profile':
            self.busy = False; self.controls()
            if result['payment_configured'] and self.pending['risk_level'] == 'RED' and not result['mfa_configured']:
                self.bind_authenticator()
            else:
                self.payment_dialog(result['payment_configured'])
            return
        if kind == 'payment_setup':
            self.busy = False; self.controls(); self.status.setText('交易密码已设置，请再次确认原操作。'); return
        super().receive(kind, result)
        self.present_security()
        if kind == 'query' and not self.pending and isinstance(result, list):
            receipts = [d['payload'] for e,d in result if e == 'card' and d.get('type') == 'result']
            read_operations = {'GET_BALANCE', 'QUERY_BILLS', 'QUERY_CARDS', 'QUERY_CARD_LIMITS', 'QUERY_ACCOUNTS', 'QUERY_TRANSFER_BATCHES', 'QUERY_WEALTH', 'RECOMMEND_WEALTH'}
            if receipts and all(r.get('operation') in read_operations and r.get('status') == 'COMPLETED' for r in receipts):
                self.read_only_result = True
        if self.read_only_result and kind in {'query', 'accounts'}:
            self.status.setText('低风险 · 本人信息查询已完成；未执行资金或卡片变更。')

    def payment_dialog(self, configured):
        wealth = self.pending.get('operation') == 'SUBSCRIBE_WEALTH'
        dialog = QDialog(self); dialog.setWindowTitle(('模拟申购 · 追加认证' if wealth else '高风险转账 · 追加认证' if self.pending['risk_level'] == 'RED' else '转账 · 交易密码认证') if configured else '首次设置交易密码')
        dialog.resize(500, 380); layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28,28,28,24); layout.setSpacing(16)
        heading=QLabel(dialog.windowTitle()); heading.setObjectName('dialogHeading'); layout.addWidget(heading)
        summary = QLabel(self.confirm_text.text()); summary.setWordWrap(True); summary.setTextFormat(Qt.TextFormat.PlainText)
        summary.setObjectName('dialogSummary')
        layout.addWidget(summary)
        entries = []
        high_risk = configured and self.pending['risk_level'] == 'RED'
        names = (['交易密码', '手机验证器6位动态码'] if high_risk else ['交易密码']) if configured else ['登录密码','6位数字交易密码','再次输入交易密码']
        for name in names:
            entry=QLineEdit(); entry.setPlaceholderText(name); entry.setAccessibleName(name)
            entry.setEchoMode(QLineEdit.EchoMode.Password); entry.setMaxLength(128 if name=='登录密码' else 6)
            layout.addWidget(entry); entries.append(entry)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(('验证并提交申购' if wealth else '验证并转账') if configured else '设置交易密码')
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName('primary')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('返回核对')
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
        accepted=dialog.exec()==QDialog.DialogCode.Accepted
        values=[e.text() for e in entries]
        for entry in entries: entry.clear()
        dialog.deleteLater()
        if not accepted: return
        if configured: super().decide('approve', values[0], totp=values[1] if high_risk else None)
        elif values[1]!=values[2]: self.status.setText('两次交易密码不一致，尚未执行。')
        else:
            self.run('payment_setup', lambda: self.client.request('/auth/payment-password',
                {'login_password':values[0],'payment_password':values[1]}))
