"""Native Qt widgets, with network work outside the GUI thread."""
import threading
from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QPlainTextEdit, QLineEdit, QGroupBox, QComboBox, QInputDialog)
from desktop.client import QueryClient, query_result, business_confirmation, money, CustomerSwitchBusy


class Delivery(QObject):
    completed = Signal(str, object)


class BankWindow(QMainWindow):
    def __init__(self, url):
        super().__init__()
        self.client = QueryClient(url)
        self.thread = None
        self.busy = False
        self.blocked = False
        self.mode = '尚未连接'
        self.pending = None
        self.decision = None
        self.uncertain = False
        self.form_active = False
        self.last_form = None
        self.edit_requested = False
        self.closed = threading.Event()
        self.delivery = Delivery(self)
        self.delivery.completed.connect(self.receive)
        self.setWindowTitle('有度 · 银行 AI 助理')
        self.resize(1080, 760)
        self.setMinimumSize(760, 560)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        heading = QLabel('有度  /  银行 AI 助理')
        heading.setObjectName('heading')
        layout.addWidget(heading)
        self.status = QLabel('正在连接本地模拟银行…')
        layout.addWidget(self.status)
        layout.addWidget(QLabel('模拟开户、借记卡、消费与转账 · 所有写操作先确认 · 理财推荐尚未开放'))
        self.current_customer = QLabel('当前演示客户：正在读取…')
        self.current_customer.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.current_customer)
        customers = QHBoxLayout()
        self.customers = QComboBox()
        self.customers.setAccessibleName('选择演示客户')
        self.switch_customer = QPushButton('切换演示客户')
        self.switch_customer.clicked.connect(self.select_customer)
        self.create_customer = QPushButton('创建演示客户')
        self.create_customer.clicked.connect(lambda: self.business_form('创建演示客户'))
        customers.addWidget(self.customers, 1)
        customers.addWidget(self.switch_customer)
        customers.addWidget(self.create_customer)
        layout.addLayout(customers)
        accounts = QHBoxLayout()
        self.current_account = QLabel('当前账户：正在读取…')
        self.current_account.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.current_account)
        self.accounts = QComboBox()
        self.accounts.setAccessibleName('选择待切换账户')
        self.refresh_accounts = QPushButton('刷新账户')
        self.switch_account = QPushButton('切换账户')
        self.batch_receipts = QPushButton('批量回执')
        self.batch_receipts.clicked.connect(lambda: self.run('batch_receipts', self.client.transfer_batches))
        self.bills = QPushButton('本月流水')
        self.bills.clicked.connect(lambda: self.run('bills', self.client.bills))
        self.refresh_accounts.clicked.connect(self.load_accounts)
        self.switch_account.clicked.connect(self.select_account)
        accounts.addWidget(self.accounts, 1)
        accounts.addWidget(self.refresh_accounts)
        accounts.addWidget(self.switch_account)
        accounts.addWidget(self.bills)
        accounts.addWidget(self.batch_receipts)
        layout.addLayout(accounts)
        business = QHBoxLayout()
        self.business_buttons = []
        for label in ('开户', '办理借记卡', '激活', '刷卡消费', '转账', '冻结', '解冻', '查询限额', '设置限额'):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, action=label: self.business_form(action))
            business.addWidget(button)
            self.business_buttons.append(button)
        layout.addLayout(business)
        quick = QHBoxLayout()
        self.buttons = []
        for label, message in [('查询余额', '查询余额'), ('消费去向', '最近钱花在哪里了'),
                               ('只看餐饮', '只看餐饮')]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, text=message: self.send(text))
            quick.addWidget(button)
            self.buttons.append(button)
        self.new = QPushButton('新对话')
        self.new.clicked.connect(self.new_chat)
        quick.addWidget(self.new)
        self.reconnect = QPushButton('重新连接')
        self.reconnect.clicked.connect(lambda: self.run('connect', self.client.connect))
        quick.addWidget(self.reconnect)
        layout.addLayout(quick)
        self.history = QPlainTextEdit()
        self.history.setReadOnly(True)
        self.history.setAccessibleName('业务对话')
        self.history.setPlaceholderText('从一笔有依据的查询开始。')
        layout.addWidget(self.history, 1)
        self.confirmation = QGroupBox('请核对本次模拟业务')
        confirm_layout = QVBoxLayout(self.confirmation)
        self.confirm_text = QLabel()
        self.confirm_text.setTextFormat(Qt.TextFormat.PlainText)
        self.confirm_text.setWordWrap(True)
        confirm_layout.addWidget(self.confirm_text)
        actions = QHBoxLayout()
        self.approve = QPushButton('确认办理')
        self.reject = QPushButton('取消办理')
        self.retry = QPushButton('重试原决定 / 核对结果')
        self.edit = QPushButton('修改表单')
        self.edit.clicked.connect(self.edit_form)
        self.approve.clicked.connect(lambda: self.decide('approve'))
        self.reject.clicked.connect(lambda: self.decide('reject'))
        self.retry.clicked.connect(lambda: self.decide(self.decision))
        for button in (self.approve, self.reject, self.edit, self.retry):
            actions.addWidget(button)
        confirm_layout.addLayout(actions)
        layout.addWidget(self.confirmation)
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setAccessibleName('业务请求')
        self.input.setPlaceholderText('例如：最近钱花在哪里了')
        self.input.setMaxLength(2000)
        self.input.returnPressed.connect(lambda: self.send())
        row.addWidget(self.input, 1)
        self.submit = QPushButton('发送')
        self.submit.clicked.connect(lambda: self.send())
        row.addWidget(self.submit)
        layout.addLayout(row)
        layout.addWidget(QLabel('本地模拟银行 · 账目保存在本机 · 聊天与待确认操作不跨重启保留'))
        self.setStyleSheet('''QWidget {font-family: "Microsoft YaHei"; font-size: 14px;
            color: #203348; background: #f2f5f8;} QLabel#heading {font-size: 25px; font-weight: bold;}
            QPlainTextEdit,QLineEdit {background:white; border:1px solid #d3dee8; border-radius:8px; padding:12px;}
            QPushButton {background:#176f69; color:white; border:0; border-radius:6px; padding:10px 18px;}
            QPushButton:disabled {background:#c2ccd5; color:#647484;}''')
        self.controls()
        QTimer.singleShot(0, lambda: self.run('connect', self.client.connect))

    def can_interrupt_chat(self):
        return (self.pending is not None and not self.form_active and self.mode == '真实模型'
                and self.decision is None and not self.uncertain)

    def controls(self):
        enabled = bool(self.client.token) and not self.busy and not self.blocked
        for item in self.buttons + [self.input, self.submit]:
            item.setEnabled(enabled)
        if self.can_interrupt_chat() and not self.busy:
            self.input.setEnabled(True)
            self.submit.setEnabled(True)
        for item in self.business_buttons + [self.accounts, self.refresh_accounts, self.switch_account,
                                            self.customers, self.switch_customer, self.create_customer, self.bills, self.batch_receipts]:
            item.setEnabled(enabled and self.pending is None and not self.uncertain)
        self.new.setEnabled(bool(self.client.token) and not self.busy and not self.uncertain)
        self.reconnect.setEnabled(not self.busy and not self.uncertain)
        self.confirmation.setVisible(self.pending is not None)
        ready = self.pending is not None and not self.busy
        self.approve.setEnabled(ready and self.decision is None and self.pending['risk_level'] == 'YELLOW')
        self.reject.setEnabled(ready and self.decision is None)
        self.edit.setEnabled(ready and self.decision is None and self.form_active and self.last_form is not None)
        self.retry.setVisible(self.decision is not None)
        self.retry.setEnabled(ready and self.decision is not None)

    def run(self, kind, function):
        if self.busy:
            return
        self.busy = True
        if kind == 'connect':
            self.status.setText('正在建立本地会话…')
        self.controls()
        def work():
            try:
                result = function()
            except CustomerSwitchBusy:
                kind_result, result = 'customer_busy', None
            except Exception:
                kind_result = ('customer_error' if kind == 'customer' else
                               'decision_error' if kind == 'decision' else 'error')
                result = ('会话建立失败，请点击「重新连接」重试。' if kind == 'connect' else
                          '提交后的结果尚未确认。请重试原决定核对结果，勿另建同一笔业务。' if kind == 'decision' else
                          '连接或响应异常，结果尚未确认。请新建对话或重新连接后重试；不会自动重发。')
            else:
                kind_result = kind
            if not self.closed.is_set():
                try:
                    self.delivery.completed.emit(kind_result, result)
                except RuntimeError:
                    pass  # Window was destroyed during delivery.
        threading.Thread(target=work, daemon=True).start()

    def load_accounts(self):
        if self.client.token and not self.busy and self.pending is None and not self.uncertain:
            self.run('accounts', self.client.overview)

    def select_customer(self):
        reference = self.customers.currentData()
        if reference and not self.busy and not self.blocked and self.pending is None and not self.uncertain:
            self.run('customer', lambda: self.client.switch_customer(reference))

    def select_account(self):
        reference = self.accounts.currentData()
        if reference and not self.busy and self.pending is None and not self.uncertain:
            self.run('connect', lambda: self.client.switch_account(reference))

    def edit_form(self):
        if self.busy or self.pending is None or self.decision is not None or not self.form_active or not self.last_form:
            return
        self.edit_requested = True
        self.decide('reject')

    def business_form(self, action, defaults=None):
        if self.busy or self.blocked or self.pending is not None:
            return
        defaults = defaults or {}
        operations = {'创建演示客户': 'CREATE_DEMO_CUSTOMER', '开户': 'OPEN_ACCOUNT', '办理借记卡': 'ISSUE_DEBIT_CARD',
            '激活': 'ACTIVATE_DEBIT_CARD', '刷卡消费': 'PAY_BY_CARD', '转账': 'TRANSFER',
            '冻结': 'FREEZE_CARD', '解冻': 'UNFREEZE_CARD',
            '查询限额': 'QUERY_CARD_LIMITS', '设置限额': 'SET_CARD_LIMITS'}
        name, ok = QInputDialog.getText(self, action, '账户名称：' if action == '开户' else
                                       '虚构客户名称（勿填写真实身份资料）：' if action == '创建演示客户' else
                                       '收款联系人或本人账户名称：' if action == '转账' else '卡片名称：',
                                       text=next((defaults[k] for k in ('display_name', 'customer_name', 'recipient_name', 'card_name') if k in defaults), ''))
        if not ok:
            return
        name = name.strip()
        if not name or len(name) > 80 or any(c in name for c in '\n\r'):
            self.status.setText('请输入 1–80 字的名称，不含换行。')
            return
        key = 'display_name' if action in {'开户', '办理借记卡'} else 'recipient_name' if action == '转账' else 'card_name'
        fields = {key: name}
        if action == '创建演示客户':
            account, ok = QInputDialog.getText(self, action, '首次开户名称（确认后记入1,000元演示资金）：', text=defaults.get('account_name', ''))
            if not ok:
                return
            if not account.strip() or len(account) > 80 or any(c in account for c in '\n\r'):
                self.status.setText('请输入1–80字的账户名称，不含换行。')
                return
            fields = {'customer_name': name, 'account_name': account.strip()}
        elif action == '设置限额':
            import re
            amounts = []
            for label in ('单笔', '每日'):
                value, ok = QInputDialog.getText(self, action, label + '消费限额（元；0 表示禁止消费）：',
                                                text=defaults.get('single_limit' if label == '单笔' else 'daily_limit', ''))
                if not ok:
                    return
                if not re.fullmatch(r'[0-9]+(?:\.[0-9]{1,2})?', value):
                    self.status.setText('限额须为非负金额，最多两位小数。')
                    return
                amounts.append(value)
            fields.update(single_limit=amounts[0], daily_limit=amounts[1])
        elif action in {'刷卡消费', '转账'}:
            if action == '刷卡消费':
                merchant, ok = QInputDialog.getText(self, action, '演示商户名称：', text=defaults.get('merchant', ''))
                if not ok:
                    return
                if not merchant.strip() or len(merchant) > 80 or any(c in merchant for c in '\n\r'):
                    self.status.setText('商户名称不合法。')
                    return
                fields['merchant'] = merchant.strip()
            amount, ok = QInputDialog.getText(self, action, '金额（元，最多两位小数）：', text=defaults.get('amount', ''))
            if not ok:
                return
            import re
            if not re.fullmatch(r'[0-9]+(?:\.[0-9]{1,2})?', amount) or not any(c in '123456789' for c in amount):
                self.status.setText('请输入大于零、最多两位小数的金额。')
                return
            fields['amount'] = amount
            if action == '刷卡消费':
                categories = ['餐饮', '交通', '购物', '居住', '其他']
                category, ok = QInputDialog.getItem(self, action, '分类：', categories,
                                                   categories.index(defaults.get('category', '其他')), False)
                if not ok:
                    return
                fields['category'] = category
        self.history.appendPlainText('表单：' + action + ' · ' + name)
        self.form_active = True
        self.last_form = (action, dict(fields))
        self.status.setText('正在校验表单，请稍候…')
        self.run('query', lambda: self.client.form(operations[action], fields))

    def send(self, text=None):
        text = (text if text is not None else self.input.text()).strip()
        if not text or self.busy or (self.blocked and not self.can_interrupt_chat()) or not self.client.token:
            return
        self.history.appendPlainText('你：' + text)
        self.form_active = False
        self.last_form = None
        self.edit_requested = False
        self.input.clear()
        self.status.setText('正在查询，请稍候…')
        thread = self.thread
        self.run('query', lambda: self.client.query(text, thread))

    def decide(self, decision):
        if self.busy or self.pending is None or decision not in {'approve', 'reject'}:
            return
        if self.decision is not None and decision != self.decision:
            return
        if decision == 'approve' and self.pending['risk_level'] != 'YELLOW':
            return
        self.decision = decision
        self.status.setText('正在提交原确认操作，请稍候…')
        pending = dict(self.pending)
        self.run('decision', lambda: self.client.resume(pending, decision))

    def clear_confirmation(self):
        self.pending = None
        self.decision = None
        self.uncertain = False

    def receive(self, kind, result):
        self.busy = False
        if kind in {'connect', 'customer'}:
            self.form_active = False
            self.last_form = None
            self.edit_requested = False
            self.clear_confirmation()
            self.thread = None
            self.blocked = False
            self.accounts.clear()
            self.customers.clear()
            self.current_customer.setText('当前演示客户：正在读取新会话…')
            self.current_account.setText('当前账户：正在读取新会话账户…')
            self.mode = '真实模型' if result == 'model' else '离线规则'
            self.history.clear()
            self.input.clear()
            self.history.appendPlainText('有度：已建立新会话，可以开始查询。')
            self.status.setText('已连接 · ' + self.mode)
            QTimer.singleShot(0, self.load_accounts)
        elif kind == 'accounts':
            self.customers.clear()
            for row in result.get('customers', []):
                self.customers.addItem(row['display_name'], row['customer_ref'])
                if row['customer_ref'] == result['current_customer_ref']:
                    self.current_customer.setText('当前演示客户：' + row['display_name'])
            self.customers.setCurrentIndex(self.customers.findData(result.get('current_customer_ref')))
            self.accounts.clear()
            for row in result['accounts']:
                label = f"{row['display_name']} · {row['account_ref'][-6:]} · ¥ {money(row['balance_minor'])}"
                self.accounts.addItem(label, row['account_ref'])
                if row['account_ref'] == result['current_account_ref']:
                    self.current_account.setText('当前账户：' + label)
            self.accounts.setCurrentIndex(self.accounts.findData(result['current_account_ref']))
        elif kind in {'bills', 'batch_receipts'}:
            self.history.appendPlainText(result + '\n')
            self.status.setText('业务记录已读取 · 直接查询本地账本')
        elif kind == 'customer_busy':
            self.status.setText('服务正在办理业务或有待确认操作，请先完成或取消，再切换演示客户。')
        elif kind == 'customer_error':
            # The response may have been lost after the old session was revoked.
            self.client.token = None
            self.thread = None
            self.clear_confirmation()
            self.accounts.clear()
            self.customers.clear()
            self.history.clear()
            self.input.clear()
            self.current_customer.setText('当前演示客户：未确认')
            self.current_account.setText('当前账户：未确认')
            self.blocked = True
            self.status.setText('客户切换未确认，请重新连接默认演示客户；不会自动重试切换。')
        elif kind in {'error', 'decision_error'}:
            self.history.appendPlainText('有度：' + result)
            self.status.setText('请求失败')
            self.blocked = True
            self.uncertain = kind == 'decision_error'
        else:
            try:
                # Validate/format the whole result before displaying any success text.
                details = [query_result(data['payload']) for event, data in result
                           if event == 'card' and data.get('type') == 'result']
                pending = business_confirmation(result)
                self.thread = result[0][1]['thread_id']
                for event, data in result:
                    if event == 'message':
                        self.history.appendPlainText('有度：' + data['text'])
                    elif event == 'error':
                        self.history.appendPlainText('有度：' + data['message'])
                for detail in details:
                    if detail:
                        self.history.appendPlainText(detail + '\n')
                final = result[-1][1]['status']
                self.uncertain = False
                if pending is not None:
                    self.pending, self.decision = pending, None
                    extra = ('\n该操作需要独立认证，当前仅支持取消。' if pending['risk_level'] == 'RED' else
                             '\n确认后才会执行；对话业务可直接提出修改、取消或先查询，旧确认将失效。')
                    self.confirm_text.setText(pending['summary'] + extra)
                elif kind != 'decision' or final not in {'FAILED', 'PENDING'}:
                    self.clear_confirmation()
                self.blocked = final in {'AWAITING_CONFIRMATION', 'AWAITING_AUTHENTICATION'}
                if self.pending is not None:
                    self.blocked = True
                if self.blocked and self.pending is None:
                    self.history.appendPlainText('当前操作尚无桌面确认入口，本次未执行。请新建对话。')
                labels = {'COMPLETED': '办理完成', 'NEEDS_CLARIFICATION': '等待补充信息',
                          'FAILED': '办理失败', 'REJECTED': '已拒绝或取消', 'PENDING': '结果待确认'}
                self.status.setText(('等待本人确认' if pending is not None else labels.get(final, final))
                                    + ' · ' + ('表单直达' if self.form_active else self.mode))
                if final == 'COMPLETED' and self.pending is None:
                    QTimer.singleShot(0, self.load_accounts)
                if kind == 'decision' and final == 'REJECTED' and self.edit_requested:
                    self.edit_requested = False
                    action, fields = self.last_form
                    token = self.client.token
                    self.status.setText('旧确认已取消，请修改表单并重新确认。')
                    QTimer.singleShot(0, lambda: self.business_form(action, fields)
                        if not self.closed.is_set() and self.client.token == token
                        and self.last_form == (action, fields) else None)
            except (KeyError, TypeError, ValueError):
                self.history.appendPlainText('有度：服务返回的数据不完整，已停止展示。请新建对话重试。')
                self.blocked = True
                self.uncertain = kind == 'decision'
        self.controls()

    def new_chat(self):
        if self.busy or self.uncertain:
            return
        self.clear_confirmation()
        self.last_form = None
        self.edit_requested = False
        self.thread = None
        self.blocked = False
        self.history.clear()
        self.status.setText('新对话 · ' + self.mode)
        self.controls()

    def closeEvent(self, event):
        self.closed.set()
        super().closeEvent(event)
