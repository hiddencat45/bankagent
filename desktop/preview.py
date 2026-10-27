"""Opt-in two-view preview. Reuses BankWindow's sessions, confirmations and retry controller."""
import re
from decimal import Decimal
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QStackedWidget, QScrollArea, QLineEdit, QComboBox, QListWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QPlainTextEdit, QSizePolicy)
from desktop.window import BankWindow
from desktop.client import money

STYLE = '''
QWidget {font-family:"Microsoft YaHei";font-size:14px;color:#233631;background:#f4f6f5;}
QWidget#rail {background:#e7eeeb;} QWidget#rail QLabel {background:transparent;} QLabel#brand {font-size:23px;font-weight:700;}
QLabel#title {font-size:24px;font-weight:600;} QLabel#balance {font-size:36px;font-weight:600;color:#164f42;}
QLabel#muted {color:#63766e;font-size:12px;} QLabel#error {color:#a33829;}
QLabel#status {padding:10px;background:#e7eeeb;border-radius:4px;}
QLabel#status[state="error"] {background:#fbece8;color:#9a3024;}
QLabel#status[state="pending"] {background:#fff1d5;color:#79520f;}
QGroupBox {background:white;border:1px solid #dbe3de;border-radius:6px;margin-top:12px;padding:16px;}
QGroupBox::title {subcontrol-origin:margin;left:16px;padding:0 6px;color:#476158;}
QGroupBox QLabel,QGroupBox QWidget {background:white;}
QLineEdit,QComboBox {background:white;border:1px solid #bacac2;border-radius:4px;padding:10px;min-height:20px;}
QLineEdit:focus,QComboBox:focus {border:2px solid #27735e;}
QPushButton {background:white;border:1px solid #bacac2;border-radius:4px;padding:9px 12px;}
QPushButton:hover {background:#e8f2ed;} QPushButton:checked {background:#d5e7dd;border-color:#44816a;}
QPushButton#primary {background:#1d6551;color:white;border-color:#1d6551;}
QPushButton:disabled {background:#edf0ee;color:#89968f;border-color:#dbe2dd;}
QPushButton#primary:disabled {background:#edf0ee;color:#89968f;border-color:#dbe2dd;}
QLineEdit:disabled,QComboBox:disabled {color:#718078;background:#edf0ee;}
QPlainTextEdit,QListWidget,QTableWidget {background:white;border:1px solid #dbe3de;border-radius:4px;padding:6px;}
QListWidget::item {padding:12px;border-bottom:1px solid #edf0ee;}
QListWidget::item:selected {background:#dbece3;color:#204b3c;}
QHeaderView::section {background:#f4f7f5;color:#61756b;border:0;padding:8px;}
QScrollArea {border:0;} QStatusBar {color:#63766e;}
'''


def text(value, role=None):
    item = QLabel(value)
    item.setTextFormat(Qt.TextFormat.PlainText)
    item.setWordWrap(True)
    if role:
        item.setObjectName(role)
    return item


def box(title):
    widget = QGroupBox(title)
    layout = QVBoxLayout(widget)
    layout.setSpacing(12)
    return widget, layout


class PreviewWindow(BankWindow):
    def __init__(self, url):
        super().__init__(url)
        # Preserve the existing controller/widgets; only these two views are previewed.
        self.legacy_root = self.takeCentralWidget()
        self.legacy_root.setParent(self)
        self.legacy_root.hide()
        self.snapshot = None
        self.actor = None
        self._prepared_from_form = False
        self.completed_form = False
        self.card_details = {}
        self.setWindowTitle('有度 · 账户与转账预览')
        self.resize(1280, 850)
        self.setMinimumSize(1040, 720)
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        rail = QWidget()
        rail.setObjectName('rail')
        rail.setFixedWidth(174)
        nav = QVBoxLayout(rail)
        nav.setContentsMargins(18, 26, 18, 20)
        nav.setSpacing(12)
        nav.addWidget(text('有度', 'brand'))
        nav.addWidget(text('本地模拟银行\n两页设计预览', 'muted'))
        self.overview_nav = QPushButton('账户概览')
        self.transfer_nav = QPushButton('转账')
        for index, button in enumerate((self.overview_nav, self.transfer_nav)):
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, page=index: self.show_page(page))
            nav.addWidget(button)
        nav.addStretch()
        nav.addWidget(text('演示身份', 'muted'))
        nav.addWidget(self.customers)
        nav.addWidget(self.switch_customer)
        nav.addWidget(self.reconnect)
        nav.addWidget(text('仅使用虚构演示数据\n其他业务页尚未改版', 'muted'))
        outer.addWidget(rail)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 18, 24, 16)
        layout.setSpacing(14)
        identity = QHBoxLayout()
        labels = QVBoxLayout()
        labels.addWidget(self.current_customer)
        labels.addWidget(self.current_account)
        identity.addLayout(labels, 1)
        self.accounts.setFixedWidth(190)
        identity.addWidget(self.accounts)
        identity.addWidget(self.switch_account)
        identity.addWidget(self.refresh_accounts)
        layout.addLayout(identity)
        self.status.setObjectName('status')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        columns = QHBoxLayout()
        columns.setSpacing(20)
        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(14)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.build_overview())
        self.pages.addWidget(self.build_transfer())
        main_layout.addWidget(self.pages)
        self.confirmation.setTitle('请核对 · 确认前不会扣款')
        self.approve.setObjectName('primary')
        self.approve.setText('确认转账 / 办理')
        self.edit.setText('返回修改')
        main_layout.addWidget(self.confirmation)
        self.result_box, result_layout = box('本次办理结果')
        self.result_text = text('尚未提交业务。')
        result_layout.addWidget(self.result_text)
        self.another_transfer = QPushButton('再转一笔')
        self.another_transfer.clicked.connect(self.start_another_transfer)
        result_layout.addWidget(self.another_transfer)
        self.another_transfer.hide()
        main_layout.addWidget(self.result_box)
        self.result_box.hide()
        main_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(main)
        self.main_scroll = scroll
        columns.addWidget(scroll, 1)
        assistant, ai = box('AI 助手')
        self.assistant_box = assistant
        assistant.setFixedWidth(310)
        ai.addWidget(text('与左侧业务共享当前客户、账户和账本。', 'muted'))
        self.conversation = QPlainTextEdit()
        self.conversation.setReadOnly(True)
        self.conversation.setPlaceholderText('可问余额、查询交易，或描述要办理的业务。写操作仍会显示确认卡。')
        ai.addWidget(self.conversation, 1)
        for button in self.buttons[:2]:
            ai.addWidget(button)
        self.input.setPlaceholderText('例如：转完后查看余额')
        ai.addWidget(self.input)
        self.submit.setObjectName('primary')
        ai.addWidget(self.submit)
        ai.addWidget(self.new)
        diagnostics = QGroupBox('展开操作详情')
        diagnostics.setCheckable(True)
        diagnostics.setChecked(False)
        detail_layout = QVBoxLayout(diagnostics)
        self.history.setMaximumHeight(120)
        detail_layout.addWidget(self.history)
        self.history.hide()
        diagnostics.toggled.connect(self.history.setVisible)
        ai.addWidget(diagnostics)
        columns.addWidget(assistant)
        layout.addLayout(columns, 1)
        outer.addWidget(body, 1)
        self.setStyleSheet(STYLE)
        self.show_page(0)
        self.controls()

    def build_overview(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(text('账户概览', 'title'))
        balance, content = box('当前账户')
        self.balance_value = text('正在读取…', 'balance')
        balance_row = QHBoxLayout()
        balance_labels = QVBoxLayout()
        balance_labels.addWidget(self.balance_value)
        self.balance_note = text('账户余额 · 人民币', 'muted')
        balance_labels.addWidget(self.balance_note)
        balance_row.addLayout(balance_labels, 1)
        self.go_transfer = QPushButton('发起转账')
        self.go_transfer.setObjectName('primary')
        self.go_transfer.clicked.connect(lambda: self.show_page(1))
        self.go_transfer.setFixedWidth(160)
        balance_row.addWidget(self.go_transfer)
        content.addLayout(balance_row)
        layout.addWidget(balance)
        cards, card_layout = box('我的借记卡')
        self.card_list = QListWidget()
        self.card_list.setMaximumHeight(112)
        self.card_list.currentRowChanged.connect(self.select_card)
        card_row = QHBoxLayout()
        card_row.addWidget(self.card_list, 1)
        card_info = QVBoxLayout()
        self.card_note = text('从当前账户的实际卡片中选择。', 'muted')
        card_info.addWidget(self.card_note)
        self.card_limits = QPushButton('查看所选卡限额')
        self.card_limits.clicked.connect(self.read_card_limits)
        card_info.addWidget(self.card_limits)
        card_row.addLayout(card_info, 1)
        card_layout.addLayout(card_row)
        layout.addWidget(cards)
        ledger, entries = box('近期流水 · 当前业务月')
        self.transactions = QTableWidget(0, 3)
        self.transactions.setHorizontalHeaderLabels(['日期', '类型 / 对象', '金额（元）'])
        self.transactions.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.transactions.verticalHeader().hide()
        self.transactions.setColumnWidth(0, 145)
        self.transactions.setColumnWidth(2, 115)
        self.transactions.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.transactions.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.transactions.setMaximumHeight(210)
        entries.addWidget(self.transactions)
        self.empty_ledger = text('正在读取流水…', 'muted')
        entries.addWidget(self.empty_ledger)
        layout.addWidget(ledger)
        return page

    def build_transfer(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(text('转账', 'title'))
        layout.addWidget(text('填写信息 → 核对并确认 → 查看实际结果', 'muted'))
        form, fields = box('转账信息')
        self.transfer_form = form
        self.payer = text('付款账户正在读取…')
        fields.addWidget(self.payer)
        fields.addWidget(text('收款人'))
        self.recipient = QComboBox()
        self.recipient.setAccessibleName('收款人')
        self.recipient.setPlaceholderText('请选择联系人或本人其他账户')
        self.recipient.currentIndexChanged.connect(self.validate_transfer)
        fields.addWidget(self.recipient)
        self.recipient_error = text('', 'error')
        fields.addWidget(self.recipient_error)
        fields.addWidget(text('转账金额（元）'))
        self.amount = QLineEdit()
        self.amount.setAccessibleName('转账金额')
        self.amount.setPlaceholderText('0.00')
        self.amount.setMaxLength(20)
        self.amount.textChanged.connect(self.validate_transfer)
        fields.addWidget(self.amount)
        self.amount_error = text('', 'error')
        fields.addWidget(self.amount_error)
        fields.addWidget(text('填写后先核对确认，不会直接扣款。返回概览保留本页内容。', 'muted'))
        self.prepare_transfer = QPushButton('下一步 · 核对转账')
        self.prepare_transfer.setObjectName('primary')
        self.prepare_transfer.clicked.connect(self.prepare_form_transfer)
        fields.addWidget(self.prepare_transfer)
        layout.addWidget(form)
        return page

    def show_page(self, index):
        self.pages.setCurrentIndex(index)
        self.overview_nav.setChecked(index == 0)
        self.transfer_nav.setChecked(index == 1)
        for i in range(self.pages.count()):
            self.pages.widget(i).setSizePolicy(QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Preferred if i == index else QSizePolicy.Policy.Ignored)
        self.fit_page()

    def fit_page(self):
        page = self.pages.currentWidget()
        page.layout().activate()
        self.pages.setFixedHeight(page.sizeHint().height())

    def run(self, kind, function):
        if self.busy:
            return
        self.status.setText({'accounts': '正在更新账户与流水…', 'query': '正在处理请求，请稍候…',
                             'decision': '正在核对并办理，请勿重复提交…'}.get(kind, '正在连接服务…'))
        super().run(kind, function)

    def load_accounts(self):
        if self.client.token and not self.busy and self.pending is None and not self.uncertain:
            self.run('accounts', self.client.workspace_overview)

    def controls(self):
        super().controls()
        if not hasattr(self, 'prepare_transfer'):
            return
        editable = bool(self.snapshot and self.client.token) and not self.busy and self.pending is None and not self.uncertain and not self.blocked
        for widget in (self.recipient, self.amount, self.card_list, self.go_transfer):
            widget.setEnabled(editable)
        self.prepare_transfer.setEnabled(editable and self.validate_transfer())
        selected_card = self.card_list.currentRow()
        unique_card = self.snapshot and selected_card >= 0 and sum(r['display_name'] == self.snapshot['objects']['cards'][selected_card]['display_name'] for r in self.snapshot['objects']['cards']) == 1
        self.card_limits.setEnabled(editable and bool(unique_card))
        self.new.setEnabled(not self.busy and self.pending is None and not self.uncertain)
        self.reconnect.setEnabled(not self.busy and self.pending is None and not self.uncertain)
        self.confirmation.setTitle('核对原操作 · 不要重新提交同一笔付款' if self.decision is not None else '请核对 · 确认前不会扣款')
        self.transfer_form.setVisible(not self.completed_form and not (self.pending and self._prepared_from_form))
        self.another_transfer.setVisible(self.completed_form)
        self.another_transfer.setEnabled(not self.busy and not self.pending and not self.uncertain)
        self.fit_page()
        self.status.setProperty('state', 'pending' if self.pending else 'error' if self.blocked or self.uncertain else 'normal')
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def validate_transfer(self):
        if not hasattr(self, 'amount_error'):
            return False
        value = self.amount.text().strip()
        valid = bool(re.fullmatch(r'[0-9]+(?:\.[0-9]{1,2})?', value)) and Decimal(value) > 0
        minor = int(Decimal(value) * 100) if valid else None
        reason = ''
        if value and not valid:
            reason = '请输入大于零、最多两位小数的金额。'
        elif minor and self.snapshot:
            account = next(a for a in self.snapshot['accounts'] if a['account_ref'] == self.snapshot['current_account_ref'])
            if minor > account['balance_minor']:
                reason = '金额超过当前余额，请修改后再提交。'
            elif minor > 1000000:
                reason = '超过当前单笔转账上限 10,000 元。'
        self.amount_error.setText(reason)
        self.amount_error.setVisible(bool(reason))
        selected = self.recipient.currentData()
        self.recipient_error.setText('当前没有可唯一选择的收款人。' if self.snapshot and self.recipient.count() == 0 else '')
        ready = bool(valid and not reason and selected)
        self.prepare_transfer.setEnabled(ready and not self.busy and not self.blocked and self.pending is None and not self.uncertain)
        return ready

    def start_another_transfer(self):
        if self.busy or self.pending or self.uncertain:
            return
        self.completed_form = False
        self.amount.clear()
        self.recipient.setCurrentIndex(-1)
        self.result_box.hide()
        self.show_page(1)
        self.controls()

    def prepare_form_transfer(self):
        if self.busy or self.pending or self.uncertain or self.blocked or not self.validate_transfer():
            return
        fields = {'recipient_name': self.recipient.currentData(), 'amount': self.amount.text().strip()}
        self.form_active = True
        self.last_form = ('转账', fields)
        self.edit_requested = False
        self._prepared_from_form = True
        self.completed_form = False
        self.result_box.hide()
        self.run('query', lambda: self.client.form('TRANSFER', fields))

    def business_form(self, action, defaults=None):
        if action != '转账':
            return super().business_form(action, defaults)
        if self.busy or self.pending or self.uncertain:
            return
        self.show_page(1)
        if defaults:
            self.recipient.setCurrentIndex(self.recipient.findData(defaults['recipient_name']))
            self.amount.setText(defaults['amount'])
        self.controls()

    def select_card(self):
        if not self.snapshot or self.card_list.currentRow() < 0:
            return
        row = self.snapshot['objects']['cards'][self.card_list.currentRow()]
        status = {'ACTIVE': '已激活', 'FROZEN': '已冻结', 'PENDING_ACTIVATION': '待激活'}[row['status']]
        self.card_note.setText(f"已选择：{row['display_name']} · {status}" + ('\n' + self.card_details[row['display_name']] if row['display_name'] in self.card_details else ''))
        duplicates = sum(r['display_name'] == row['display_name'] for r in self.snapshot['objects']['cards'])
        if duplicates > 1:
            self.card_note.setText('存在同名卡，当前名称接口不能唯一选择，暂不办理。')
        self.controls()

    def read_card_limits(self):
        if self.busy or self.pending or self.uncertain or not self.snapshot or self.card_list.currentRow() < 0:
            return
        row = self.snapshot['objects']['cards'][self.card_list.currentRow()]
        self.form_active = True
        self.run('query', lambda: self.client.form('QUERY_CARD_LIMITS', {'card_name': row['display_name']}))

    def send(self, text=None):
        value = text if text is not None else self.input.text()
        if value.strip() and not self.busy and (not self.blocked or self.can_interrupt_chat()):
            self.conversation.appendPlainText('你：' + value.strip())
            self._prepared_from_form = False
        super().send(text)

    def receive(self, kind, result):
        super().receive(kind, result)
        if not hasattr(self, 'pages'):
            return
        if kind in {'connect', 'customer', 'customer_error'}:
            self.snapshot = None
            self.actor = None
            self.completed_form = False
            self.card_details.clear()
            self.assistant_box.setTitle('AI 助手 · ' + self.mode)
            self.amount.clear()
            self.recipient.clear()
            self.card_list.clear()
            self.transactions.setRowCount(0)
            self.balance_value.setText('正在读取…' if self.client.token else '尚未连接')
            self.payer.setText('付款账户尚未确认')
            self.conversation.clear()
            self.result_box.hide()
        elif kind == 'accounts':
            actor = (result.get('current_customer_ref'), result['current_account_ref'])
            if self.actor is not None and actor != self.actor:
                self.amount.clear()
            self.actor, self.snapshot = actor, result
            self.status.setText('账户与流水已更新 · 与助手共享同一账本')
            for index, account in enumerate(result['accounts']):
                self.accounts.setItemText(index, account['display_name'])
            current = next(a for a in result['accounts'] if a['account_ref'] == actor[1])
            self.current_account.setText('当前账户：' + current['display_name'])
            self.balance_value.setText('¥ ' + money(current['balance_minor']))
            self.balance_note.setText(current['display_name'] + ' · 人民币账户余额')
            self.payer.setText('付款账户：' + current['display_name'] + '\n可用余额：¥ ' + money(current['balance_minor']))
            choice = self.recipient.currentData()
            self.recipient.blockSignals(True)
            self.recipient.clear()
            rows = result['objects']['recipients']
            for row in rows:
                # Existing name resolver refuses ambiguity; never silently choose a namesake.
                if sum(r['display_name'] == row['display_name'] for r in rows) == 1:
                    self.recipient.addItem(row['display_name'] + ' · ' + row['kind'], row['display_name'])
            self.recipient.setCurrentIndex(self.recipient.findData(choice))
            self.recipient.blockSignals(False)
            card_choice = self.card_list.currentItem().text().split('    ')[0] if self.card_list.currentItem() else None
            self.card_list.blockSignals(True)
            self.card_list.clear()
            statuses = {'ACTIVE': '已激活', 'FROZEN': '已冻结', 'PENDING_ACTIVATION': '待激活'}
            for row in result['objects']['cards']:
                self.card_list.addItem(row['display_name'] + '    ' + statuses[row['status']])
            self.card_list.blockSignals(False)
            self.card_note.setText('请选择一张卡查看限额。' if self.card_list.count() else '当前账户暂无借记卡。')
            if card_choice is not None:
                for index, row in enumerate(result['objects']['cards']):
                    if row['display_name'] == card_choice:
                        self.card_list.setCurrentRow(index)
                        break
            transactions = sorted(result['ledger']['transactions'], key=lambda r: (r['occurred_at'], r['transaction_id']), reverse=True)[:5]
            self.transactions.setRowCount(len(transactions))
            labels = {'INCOME': '收入', 'EXPENSE': '消费', 'TRANSFER_OUT': '转出', 'TRANSFER_IN': '转入'}
            for index, row in enumerate(transactions):
                values = [row['occurred_at'][:16].replace('T', ' '), labels[row['kind']] + ' · ' + (row['merchant'] or row['category']),
                          ('+' if row['kind'] in {'INCOME', 'TRANSFER_IN'} else '−') + money(row['amount_minor'])]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if col == 2:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.transactions.setItem(index, col, item)
            self.empty_ledger.setText('最近5笔，数据来自当前账户实际账本。' if transactions else '本月暂无流水。')
        elif kind in {'error', 'decision_error'}:
            if kind == 'decision_error':
                self.status.setText('办理结果待核对 · 请重试原决定，不要另建付款')
                self.result_text.setText('未收到可靠结果，付款可能已经完成。请使用“重试原决定 / 核对结果”，不会另建付款。\n' + result)
                self.confirm_text.setText(self.pending['summary'] + '\n原决定已发送，当前结果未知。请核对原操作，不要重新发起。')
            else:
                self.result_text.setText(result)
            self.result_box.show()
        elif isinstance(result, list):
            summaries = []
            write_statuses = []
            for event, data in result:
                if event in {'message', 'error'}:
                    self.conversation.appendPlainText('有度：' + data.get('text', data.get('message', '')))
                if event == 'card' and data.get('type') == 'result':
                    receipt = data['payload']
                    if receipt['operation'] in {'TRANSFER', 'BATCH_TRANSFER', 'PAY_BY_CARD'}:
                        write_statuses.append(receipt['status'])
                    detail = self.summarize(receipt)
                    if detail:
                        summaries.append(detail)
                        if receipt['operation'] == 'QUERY_CARD_LIMITS':
                            if self.snapshot and self.card_list.currentRow() >= 0:
                                name = self.snapshot['objects']['cards'][self.card_list.currentRow()]['display_name']
                                self.card_details[name] = detail
                            self.card_note.setText(detail)
            if self._prepared_from_form and 'COMPLETED' in write_statuses and result[-1][1]['status'] == 'COMPLETED':
                self.completed_form = True
            if summaries:
                partial = 'COMPLETED' in write_statuses and any(s != 'COMPLETED' for s in write_statuses)
                if write_statuses or not self.result_box.isVisible():
                    self.result_box.setTitle('部分完成 · 已完成付款不会撤回' if partial else '本次办理结果')
                    self.result_text.setText('\n\n'.join(summaries))
                    self.result_box.show()
                self.conversation.appendPlainText('实际结果：\n' + '\n'.join(summaries))
            if self.pending:
                self.status.setText('办理结果待核对 · 请重试原决定，不要另建付款' if self.decision is not None else '等待确认 · 尚未执行付款或业务变更')
                if self.decision is None:
                    self.result_box.hide()
                QTimer.singleShot(0, lambda: self.main_scroll.ensureWidgetVisible(self.confirmation))
                if self._prepared_from_form and self.decision is None:
                    guidance = ('该操作需要独立认证，当前尚未接入，只能取消或返回修改。' if self.pending['risk_level'] == 'RED'
                                else '请核对收款人和金额，确认后才会扣款。')
                    self.confirm_text.setText('付款：' + self.payer.text().split('\n')[0].removeprefix('付款账户：') + '\n' + self.pending['summary'] + '\n' + guidance)
            elif result[-1][1]['status'] == 'REJECTED' and not summaries:
                self.result_text.setText('本次操作未执行。填写内容已保留，可返回修改。')
                self.result_box.show()
        self.controls()

    @staticmethod
    def summarize(receipt):
        data = receipt.get('data') or {}
        operation, status = receipt['operation'], receipt['status']
        if operation == 'BATCH_TRANSFER' and data.get('items'):
            labels = {'COMPLETED': '成功', 'FAILED': '失败', 'NOT_EXECUTED': '未执行'}
            return ('整批转账成功' if data.get('committed') else '整批未提交，未扣款') + '\n' + '\n'.join(
                f"{row['recipient']} ¥ {money(row['amount_minor'])} · {labels[row['status']]}" for row in data['items'])
        if status != 'COMPLETED':
            return '操作未完成：' + {'INSUFFICIENT_BALANCE': '余额不足，未扣款。', 'USER_CANCELLED': '已取消，未执行。'}.get(receipt.get('error_code'), '请核对提示后处理；结果不确定时重试原决定。')
        if operation == 'TRANSFER':
            return f"转账成功 · {data['recipient']} ¥ {money(data['amount_minor'])}\n账户余额：¥ {money(data['remaining_balance_minor'])}"
        if operation == 'GET_BALANCE':
            return '账户余额：¥ ' + money(data['balance_minor'])
        if operation == 'QUERY_BILLS':
            return f"已查询 {len(data['transactions'])} 笔流水；消费合计 ¥ {money(data['total_minor'])}。"
        if operation == 'QUERY_CARD_LIMITS':
            return f"单笔限额 ¥ {money(data['single_limit_minor'])} · 每日限额 ¥ {money(data['daily_limit_minor'])}"
        if operation == 'BATCH_TRANSFER':
            return '整批转账成功\n' + '\n'.join(f"{row['recipient']} ¥ {money(row['amount_minor'])} · 成功" for row in data['items'])
        return '业务已完成；详细回执可展开查看。'
