"""Native business workspace reusing BankWindow's session and confirmation controller."""
import re
from decimal import Decimal
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QStackedWidget, QScrollArea, QLineEdit, QComboBox, QListWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QMenu, QApplication, QInputDialog)
from desktop.window import BankWindow
from desktop.client import money, LedgerUnavailable
from desktop.bills import BillsPage
from desktop.wealth import WealthPage
from desktop.orb import AssistantOrb
from desktop.chat import ChatView
from desktop.assistant_space import AssistantSpace, MessageInput
from desktop.icons import icon
from desktop.decor import ForestRail

from desktop.theme import STYLE, load_chinese_font



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
    def __init__(self, url, startup_customer=None, client=None):
        load_chinese_font()
        super().__init__(url, startup_customer=startup_customer, client=client)
        # Preserve the existing controller/widgets across the business views.
        self.legacy_root = self.takeCentralWidget()
        self.legacy_root.setParent(self)
        self.legacy_root.hide()
        self.snapshot = None
        self.actor = None
        self._prepared_from_form = False
        self.completed_form = False
        self.card_details = {}
        self.setWindowTitle('有度 · 本地银行 AI 助手')
        self.resize(1280, 850)
        self.setMinimumSize(1040, 720)
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        rail = ForestRail()
        rail.setObjectName('rail')
        rail.setFixedWidth(214)
        nav = QVBoxLayout(rail)
        nav.setContentsMargins(18, 26, 18, 20)
        nav.setSpacing(12)
        brand_row=QHBoxLayout(); brand_row.setSpacing(10)
        brand_mark=QLabel(); brand_mark.setPixmap(QIcon(str(Path(__file__).parent/'assets/youdu-brand.svg')).pixmap(40,40))
        brand_row.addWidget(brand_mark)
        brand_copy=QVBoxLayout(); brand_copy.setSpacing(0)
        brand_copy.addWidget(text('有度','brand')); brand_copy.addWidget(text('更懂你的银行 AI','muted'))
        brand_row.addLayout(brand_copy); brand_row.addStretch(); nav.addLayout(brand_row)
        nav.addSpacing(28)
        self.overview_nav = QPushButton('账户概览')
        self.transfer_nav = QPushButton('转账')
        self.ledger_nav = QPushButton('交易记录')
        self.wealth_nav = QPushButton('理财 · 模拟')
        for index, button in enumerate((self.overview_nav, self.transfer_nav, self.ledger_nav, self.wealth_nav)):
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, page=index: self.show_page(page))
            nav.addWidget(button)
        self.business_menu = QPushButton('账户与卡 ▾')
        self.business_menu.clicked.connect(self.show_business_menu)
        nav.insertWidget(3, self.business_menu)
        nav.addStretch()
        account_card = QWidget()
        account_card.setObjectName('accountCard')
        card_layout = QVBoxLayout(account_card)
        card_layout.setContentsMargins(16, 18, 16, 14)
        card_layout.setSpacing(10)
        card_layout.addWidget(text('当前账户', 'accountCaption'))
        self.context_account = text('正在读取…', 'accountName')
        card_layout.addWidget(self.context_account)
        card_layout.addWidget(text('人民币 · 模拟账户', 'accountCaption'))
        self.account_picker = QPushButton('切换账户    ›')
        self.account_picker.setObjectName('accountPicker')
        self.account_picker.clicked.connect(lambda: self.show_context_menu('account'))
        card_layout.addWidget(self.account_picker)
        account_card.setParent(self.legacy_root); account_card.hide()
        self.customer_picker = QPushButton('演示客户正在读取…')
        self.customer_picker.setObjectName('customerPicker')
        self.customer_picker.setAccessibleName('切换演示客户')
        self.customer_picker.clicked.connect(lambda: self.show_context_menu('customer'))
        self.customer_picker.setParent(self.legacy_root); self.customer_picker.hide()
        nav.addWidget(text('—','railFooter'))
        nav.addWidget(text('有度银行\n安全 · 专业 · 陪伴','railFooter'))
        outer.addWidget(rail)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 18, 24, 28)
        layout.setSpacing(14)
        identity = QHBoxLayout()
        self.context_heading = text('正在读取当前客户与账户…')
        self.context_heading.hide()
        identity.addWidget(self.account_picker)
        self.account_picker.setObjectName('ledgerAccount')
        identity.addStretch(1)
        self.connection_state = text('尚未连接', 'muted')
        identity.addWidget(self.connection_state)
        self.identity_name=text('正在读取身份…', 'identityName')
        self.identity_name.hide()
        self.refresh_accounts.setText('刷新')
        self.refresh_accounts.setIcon(icon('refresh'))
        self.refresh_accounts.setObjectName('quietAction')
        self.refresh_accounts.setToolTip('刷新当前账户、卡与账单')
        identity.addWidget(self.refresh_accounts)
        self.more_actions = QPushButton('···')
        self.more_actions.setObjectName('profileMenu')
        self.more_actions.setIcon(icon('avatar',26)); self.more_actions.setIconSize(QSize(26,26))
        self.more_actions.setAccessibleName('更多操作')
        self.more_actions.setToolTip('更多操作：重新连接')
        self.more_actions.clicked.connect(self.show_connection_menu)
        identity.addWidget(self.more_actions)
        layout.addLayout(identity)
        self.status.setObjectName('status')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addWidget(self.migration_notice)
        columns = QHBoxLayout()
        columns.setSpacing(20)
        main = QWidget()
        main_layout = QVBoxLayout(main)
        self.main_layout = main_layout
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(14)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.build_overview())
        self.pages.addWidget(self.build_transfer())
        self.bills_page = BillsPage()
        self.bills_page.requested.connect(self.load_ledger)
        self.bills_page.geometry_changed.connect(lambda:QTimer.singleShot(0,self.fit_page))
        self.bills_page.account_button.clicked.connect(lambda:self.show_context_menu('account',self.bills_page.account_button))
        layout.insertWidget(1,self.bills_page.header)
        self.pages.addWidget(self.bills_page)
        self.wealth_page = WealthPage()
        self.wealth_page.requested.connect(self.prepare_wealth_form)
        self.wealth_page.refresh_requested.connect(self.load_accounts)
        self.wealth_page.geometry_changed.connect(lambda: QTimer.singleShot(0, self.fit_page))
        self.wealth_page.tabs.currentChanged.connect(lambda: QTimer.singleShot(0, lambda: self.main_scroll.verticalScrollBar().setValue(0)))
        self.pages.addWidget(self.wealth_page)
        main_layout.addWidget(self.pages)
        self.confirmation.setTitle('')
        self.confirmation.setObjectName('operationConfirmation')
        self.confirm_text.setObjectName('confirmationSummary')
        old_actions = self.confirmation.layout().takeAt(1).layout()
        self.confirm_actions = QWidget()
        self.confirm_actions.setFixedHeight(44)
        confirm_actions = QHBoxLayout(self.confirm_actions)
        confirm_actions.setContentsMargins(0,0,0,0)
        confirm_actions.addStretch()
        for button in (self.edit, self.reject, self.retry, self.verify, self.approve):
            old_actions.removeWidget(button)
            button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            confirm_actions.addWidget(button)
        self.confirmation.layout().addWidget(self.confirm_actions)
        self.confirmation_heading = text('确认本次办理 · 确认前不会扣款', 'confirmationHeading')
        self.confirmation.layout().insertWidget(0, self.confirmation_heading)
        self.confirmation.layout().setContentsMargins(20,16,20,16)
        self.confirmation.layout().setSpacing(10)
        self.confirm_text.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.approve.setObjectName('primary')
        self.approve.setText('确认转账 / 办理')
        self.edit.setText('返回修改')
        self.edit.clicked.disconnect()
        self.edit.clicked.connect(self.edit_current_operation)
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
        self.ai_expand, self.ai_close = QPushButton('铺满窗口'), QPushButton('返回业务  ×')
        self.ai_expand.setCheckable(True)
        self.ai_expand.toggled.connect(self.position_assistant)
        self.ai_close.clicked.connect(lambda: self.toggle_assistant(False))
        self.ai_context = text('当前账户正在读取…', 'muted')
        self.ai_context.hide()
        self.conversation = ChatView()
        self.conversation.receipt_opened.connect(self.open_receipt)
        self.conversation.wealth_opened.connect(self.open_wealth_receipt)
        self.input.hide()
        self.input = MessageInput()
        self.input.returnPressed.connect(lambda: self.send())
        self.submit.setObjectName('primary')
        self.assistant_box = AssistantSpace(self)
        self.orb = AssistantOrb(root)
        self.orb.toggled.connect(self.toggle_assistant)
        layout.addLayout(columns, 1)
        outer.addWidget(body, 1)
        self.setStyleSheet(STYLE)
        for button, kind, label in ((self.overview_nav, 'overview', '账户概览'), (self.transfer_nav, 'transfer', '转账'),
                              (self.ledger_nav, 'ledger', '交易记录'), (self.wealth_nav, 'ledger', '理财 · 模拟'), (self.business_menu, 'card', '账户与卡')):
            button.setObjectName('navigation'); button.setText(label)
            button.setIcon(icon(kind, color='#c5dbd1'))
            button.setIconSize(QSize(22,22))
        self.show_page(0)
        self.controls()

    def show_context_menu(self, kind, anchor=None):
        combo, control, default_anchor = ((self.accounts, self.switch_account, self.account_picker)
                                  if kind == 'account' else
                                  (self.customers, self.switch_customer, self.customer_picker))
        anchor=anchor or default_anchor
        if not control.isEnabled():
            return
        menu = QMenu(self)
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        for index in range(combo.count()):
            reference = combo.itemData(index)
            action = menu.addAction(combo.itemText(index))
            action.setCheckable(True)
            action.setChecked(index == combo.currentIndex())
            action.setEnabled(index != combo.currentIndex())
            action.triggered.connect(lambda checked=False, ref=reference:
                                     self.choose_context(kind, ref))
        menu.popup(anchor.mapToGlobal(anchor.rect().topRight()))

    def choose_context(self, kind, reference):
        # Only references from the current server-provided list are selectable.
        combo, control = ((self.accounts, self.switch_account) if kind == 'account'
                          else (self.customers, self.switch_customer))
        index = combo.findData(reference)
        if not control.isEnabled() or index < 0 or index == combo.currentIndex():
            return
        combo.setCurrentIndex(index)
        control.click()

    def show_connection_menu(self):
        menu = QMenu(self)
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        action = menu.addAction('重新连接张伟' if self.client.startup_customer == 'zhang-wei' else '重新连接启动客户')
        action.setEnabled(self.reconnect.isEnabled())
        action.triggered.connect(self.reconnect.click)
        menu.addAction('切换演示客户').triggered.connect(lambda:self.show_context_menu('customer',self.more_actions))
        menu.popup(self.more_actions.mapToGlobal(self.more_actions.rect().bottomLeft()))

    def update_context(self):
        self.account_picker.setEnabled(self.switch_account.isEnabled())
        self.customer_picker.setEnabled(self.switch_customer.isEnabled())
        self.more_actions.setEnabled(self.reconnect.isEnabled())
        self.connection_state.setText('处理中…' if self.busy else
                                      '需核对结果' if self.uncertain else
                                      '等待确认' if self.pending else
                                      '连接或请求异常' if self.blocked else
                                      '● 会话已连接' if self.client.token else '尚未连接')
        if self.snapshot:
            account = next(a for a in self.snapshot['accounts']
                           if a['account_ref'] == self.snapshot['current_account_ref'])
            customer = self.current_customer.text().removeprefix('当前演示客户：')
            self.context_account.setText(account['display_name'])
            self.context_heading.setText('本地模拟银行')
            self.customer_picker.setText(customer + '\n演示客户    ›')
            self.customer_picker.setToolTip('当前演示客户：' + customer + '；点击切换')
        else:
            state = '正在读取…' if self.client.token else '尚未确认'
            self.context_account.setText(state)
            self.context_heading.setText('当前客户与账户' + state)
            self.customer_picker.setText('演示客户' + state)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_assistant()
        # The central widget's layout can settle after QMainWindow.resizeEvent.
        QTimer.singleShot(0, self.position_assistant)

    def position_assistant(self):
        if not hasattr(self, 'orb'): return
        root = self.centralWidget()
        self.orb.move(root.width()-82, root.height()-72)
        if self.ai_expand.isChecked():
            width, height = root.width(), root.height()
        else:
            scale = .55 ** .5
            width = min(root.width()-24, max(720, round(root.width()*scale)))
            height = min(root.height()-24, max(620, round(root.height()*scale)))
        self.assistant_box.setGeometry((root.width()-width)//2, (root.height()-height)//2, width, height)
        self.assistant_box.raise_()
        self.orb.setVisible(not self.assistant_box.isVisible())
        if not self.assistant_box.isVisible():
            self.orb.raise_()

    def toggle_assistant(self, shown):
        self.orb.blockSignals(True); self.orb.setChecked(shown); self.orb.blockSignals(False)
        if shown and self.assistant_box.confirm_scroll.widget() is None:
            self.main_layout.removeWidget(self.confirmation)
            self.assistant_box.confirm_scroll.setWidget(self.confirmation)
            self.confirmation.layout().removeWidget(self.confirm_actions)
            self.assistant_box.column.insertWidget(self.assistant_box.column.indexOf(self.assistant_box.confirm_scroll)+1, self.confirm_actions)
        elif not shown and self.assistant_box.confirm_scroll.widget() is not None:
            self.assistant_box.confirm_scroll.takeWidget()
            self.main_layout.insertWidget(1, self.confirmation)
            self.assistant_box.column.removeWidget(self.confirm_actions)
            self.confirmation.layout().addWidget(self.confirm_actions)
        self.assistant_box.setVisible(shown)
        self.confirmation.setVisible(self.pending is not None)
        self.assistant_box.sync()
        self.position_assistant()
        if shown: self.input.setFocus()

    def new_chat(self):
        if self.busy or self.pending or self.uncertain:
            return
        super().new_chat()
        if hasattr(self, 'conversation'):
            self.conversation.clear(); self.input.clear(); self.assistant_box.sync()

    def edit_current_operation(self):
        if self.busy or not self.pending or self.decision is not None or self.uncertain:
            return
        if not self.form_active and self.pending.get('recipient') and self.pending.get('amount_minor'):
            self.form_active = True
            self.last_form = ('转账', {'recipient_name': self.pending.get('recipient_input', self.pending['recipient']),
                                      'amount': money(self.pending['amount_minor']).replace(',', '')})
            self._prepared_from_form = True
        self.toggle_assistant(False)
        self.edit_form()

    def open_wealth_receipt(self, destination, payload):
        if self.busy or (self.pending and destination == 'profile'):
            self.assistant_box.feedback.setText('请先完成或取消当前操作，再继续。')
            return
        self.toggle_assistant(False)
        page = self.wealth_page
        if destination != 'profile':
            page.defer_onboarding()
        self.show_page(3)
        page.tabs.setCurrentIndex({'profile': 1, 'holdings': 2, 'orders': 3, 'order': 3}.get(destination, 0))
        if destination == 'profile':
            page.open_profile()
        elif destination == 'product' and page.data:
            for i, product in enumerate(page.data['products']):
                if product['code'] == payload.get('code'):
                    page.products.selectRow(i)
                    page.show_product_detail()
                    break
        elif destination == 'order' and page.data:
            for i, order in enumerate(page.data['orders']):
                if order['order_id'] == payload.get('order_id'):
                    page.orders.selectRow(i)
                    break
            else:
                page.feedback.setText('当前账户未找到这笔订单，请刷新后核对。')

    def open_receipt(self, receipt):
        if self.busy:
            self.assistant_box.feedback.setText('正在更新账户，请稍候再查看交易。')
            return
        self.toggle_assistant(False)
        from bankagent.banking.wealth import OPERATIONS
        if receipt['operation'] in OPERATIONS:
            self.show_page(3)
            self.wealth_page.tabs.setCurrentIndex(3 if (receipt.get('data') or {}).get('order') else 0)
            return
        if receipt['operation'] in {'QUERY_BILLS', 'TRANSFER', 'BATCH_TRANSFER', 'PAY_BY_CARD'}:
            self.show_page(2)
            data = receipt.get('data') or {}
            if receipt['operation'] == 'QUERY_BILLS':
                self.bills_page.search.clear(); self.bills_page.category.setCurrentIndex(0)
                self.bills_page.select_tab(False)
                self.bills_page.set_data(data, default=True)
            elif self.bills_page.data:
                self.bills_page.select_tab(False)
                self.bills_page.search.clear(); self.bills_page.category.setCurrentIndex(0)
                self.bills_page.focus_receipt(data)
        else:
            self.show_page(0)
            name = (receipt.get('data') or {}).get('display_name')
            if name and self.snapshot:
                for index, row in enumerate(self.snapshot['objects']['cards']):
                    if row['display_name'] == name:
                        self.card_list.setCurrentRow(index)
                        break
            self.main_scroll.ensureWidgetVisible(self.card_list)

    def show_business_menu(self):
        menu = QMenu(self)
        for button in [self.create_customer] + self.business_buttons + [self.batch_receipts]:
            action = menu.addAction(button.text()); action.setEnabled(button.isEnabled())
            action.triggered.connect(button.click)
        menu.exec(self.business_menu.mapToGlobal(self.business_menu.rect().bottomLeft()))

    def load_ledger(self):
        if self.busy or not self.client.token: return
        start, end = self.bills_page.period()
        if start >= end:
            self.bills_page.clear('开始日期不能晚于结束日期。'); return
        self.bills_page.clear('正在读取账本…')
        def read():
            try: return self.client.ledger(start, end)
            except LedgerUnavailable as exc: return {'read_error':str(exc)}
            except Exception: return {'read_error':'账单连接或响应异常，请重新查询。'}
        self.run('ledger', read)

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
        self.copy_card = QPushButton('复制所选模拟卡号')
        self.copy_card.clicked.connect(self.copy_card_number)
        card_info.addWidget(self.copy_card)
        self.card_action = QPushButton('选择卡片后办理')
        self.card_action.clicked.connect(self.card_status_form)
        card_info.addWidget(self.card_action)
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
        all_bills = QPushButton('查看全部账单'); all_bills.clicked.connect(lambda:self.show_page(2)); layout.addWidget(all_bills)
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
        self.payer_card_picker = QComboBox()
        self.payer_card_picker.setPlaceholderText('请先办卡并激活，或选择本人其他付款卡')
        self.payer_card_picker.setAccessibleName('付款卡')
        self.payer_card_picker.currentIndexChanged.connect(lambda _: self.choose_context('account', self.payer_card_picker.currentData()) if self.payer_card_picker.currentData() else None)
        fields.addWidget(self.payer_card_picker)
        fields.addWidget(text('收款卡号 · 仅支持本地模拟卡'))
        self.recipient = QComboBox()
        self.recipient.setEditable(True)
        self.recipient.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.recipient.setAccessibleName('收款卡号')
        self.recipient.lineEdit().setPlaceholderText('输入16位模拟卡号，无需添加联系人')
        self.recipient.lineEdit().setMaxLength(80)
        self.recipient.editTextChanged.connect(self.validate_transfer)
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
        self.ledger_nav.setChecked(index == 2)
        self.wealth_nav.setChecked(index == 3)
        self.bills_page.header.setVisible(index==2)
        self.account_picker.setVisible(index!=2)
        for i in range(self.pages.count()):
            self.pages.widget(i).setSizePolicy(QSizePolicy.Policy.Preferred if i == index else QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Preferred if i == index else QSizePolicy.Policy.Ignored)
        self.fit_page()

        if index == 3:
            self.main_scroll.verticalScrollBar().setValue(0)

    def fit_page(self):
        page = self.pages.currentWidget()
        page.layout().activate()
        self.pages.setFixedHeight(page.sizeHint().height())
        if self.pending:
            # The shared confirmation moves between the assistant and the page.
            # Preserve its wrapped text height after font/style or parent changes.
            self.confirm_text.ensurePolished()
            self.confirm_text.setMinimumHeight(max(self.confirm_text.sizeHint().height(),
                self.confirm_text.heightForWidth(max(100, self.confirm_text.width()))))

    def run(self, kind, function):
        if self.busy:
            return
        self.status.setText({'ledger': '正在查询账本…', 'accounts': '正在更新账户与流水…', 'query': '正在处理请求，请稍候…',
                             'decision': '正在核对并办理，请勿重复提交…'}.get(kind, '正在连接服务…'))
        super().run(kind, function)

    def load_accounts(self):
        if self.client.token and not self.busy and self.pending is None and not self.uncertain:
            period = self.bills_page.period() if self.bills_page.default_range else None
            def read():
                result = self.client.workspace_overview()
                if hasattr(self.client, 'wealth'):
                    try:
                        result['wealth'] = self.client.wealth()
                    except Exception:
                        result['wealth_error'] = '理财数据未读取，请刷新重试。'
                try:
                    result['bill_ledger'] = self.client.ledger(*period) if period else result['ledger']
                except LedgerUnavailable as exc:
                    result['bill_error'] = str(exc)
                except Exception:
                    result['bill_error'] = '账单连接或响应异常，请重新查询。'
                return result
            self.run('accounts', read)

    def controls(self):
        super().controls()
        if not hasattr(self, 'prepare_transfer'):
            return
        editable = bool(self.snapshot and self.client.token) and not self.busy and self.pending is None and not self.uncertain and not self.blocked
        for widget in (self.recipient, self.amount, self.card_list, self.go_transfer):
            widget.setEnabled(editable)
        self.prepare_transfer.setEnabled(editable and self.validate_transfer())
        self.payer_card_picker.setEnabled(editable)
        selected_card = self.card_list.currentRow()
        unique_card = self.snapshot and selected_card >= 0 and sum(r['display_name'] == self.snapshot['objects']['cards'][selected_card]['display_name'] for r in self.snapshot['objects']['cards']) == 1
        self.card_limits.setEnabled(editable and bool(unique_card))
        self.card_action.setEnabled(editable and bool(unique_card))
        self.new.setEnabled(not self.busy and self.pending is None and not self.uncertain)
        if self.pending and self.pending.get('recipient') and self.pending.get('amount_minor'):
            self.edit.setEnabled(not self.busy and not self.uncertain and self.decision is None)
        self.reconnect.setEnabled(not self.busy and self.pending is None and not self.uncertain)
        self.confirmation_heading.setText('核对原操作 · 不要重新提交同一笔付款' if self.decision is not None else '确认本次办理 · 确认前不会扣款')
        self.transfer_form.setVisible(not self.completed_form and not (self.pending and self._prepared_from_form))
        self.another_transfer.setVisible(self.completed_form)
        self.another_transfer.setEnabled(not self.busy and not self.pending and not self.uncertain)
        self.bills_page.query.setEnabled(bool(self.client.token) and not self.busy)
        self.bills_page.reset.setEnabled(bool(self.client.token) and not self.busy)
        self.bills_page.start.setEnabled(not self.busy)
        self.bills_page.end.setEnabled(not self.busy)
        self.bills_page.month.setEnabled(not self.busy)
        self.bills_page.account_button.setEnabled(bool(self.snapshot) and not self.busy and not self.pending and not self.uncertain)
        if hasattr(self, 'wealth_page'):
            self.wealth_page.set_available(editable)
            self.wealth_page.refresh.setEnabled(editable)
        self.identity_name.setText(self.current_customer.text().removeprefix('当前演示客户：').replace('（演示客户）','').strip())
        self.more_actions.setText(self.identity_name.text()+'  ⌄')
        self.update_context()
        if hasattr(self, "assistant_box"):
            self.assistant_box.sync()
        self.fit_page()
        self.status.setProperty('state', 'pending' if self.pending else 'error' if self.blocked or self.uncertain else 'normal')
        self.status.setVisible(self.status.text() not in {'账户已更新','账单已更新 · 当前账户实际账本'})
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def prepare_wealth_form(self, action, fields):
        if self.busy or self.blocked or self.pending or self.uncertain or not self.client.token:
            return
        self.form_active = True
        self.last_form = None
        self._prepared_from_form = False
        self.completed_form = False
        self.toggle_assistant(False)
        self.run('query', lambda: self.client.form(action, fields))

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
        selected = self.recipient_value()
        shortcut = self.recipient.currentIndex() >= 0 and self.recipient.currentText() == self.recipient.itemText(self.recipient.currentIndex())
        recipient_valid = shortcut or bool(re.fullmatch(r'[0-9]{16}', selected.replace(' ', '')))
        self.recipient_error.setText('请输入16位本地模拟卡号，可包含空格。' if selected and not recipient_valid else '')
        source = self.snapshot and next((a for a in self.snapshot['accounts'] if a['account_ref'] == self.snapshot['current_account_ref']), {})
        card_ready = bool(source and source.get('transfer_card') and source['transfer_card']['status'] == 'ACTIVE')
        ready = bool(valid and not reason and selected and recipient_valid and card_ready)
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
        fields = {'recipient_name': self.recipient_value(), 'amount': self.amount.text().strip()}
        self.form_active = True
        self.last_form = ('转账', fields)
        self.edit_requested = False
        self._prepared_from_form = True
        self.completed_form = False
        self.result_box.hide()
        self.run('query', lambda: self.client.form('TRANSFER', fields))

    def business_form(self, action, defaults=None, _card_checked=False):
        if action == '模拟入金':
            if self.busy or self.pending or self.uncertain or not self.snapshot:
                return
            cards = self.snapshot['objects']['cards']
            if len(cards) != 1 or cards[0]['status'] != 'ACTIVE':
                self.status.setText('请先办理并激活当前卡；冻结卡不能模拟入金。')
                return
            card = cards[0]
            amount, ok = QInputDialog.getText(self, '模拟入金 · 非真实存款',
                card['display_name'] + ' · 尾号' + card['card_number'][-4:] + '\n金额（元，最多10000；下一步核对确认）：',
                text=(defaults or {}).get('amount', ''))
            if not ok: return
            if not re.fullmatch(r'[0-9]+(?:\.[0-9]{1,2})?', amount) or not 0 < Decimal(amount) <= 10000:
                self.status.setText('模拟入金须大于0、最多10000元，保留两位小数。'); return
            fields = {'card_name': card['display_name'], 'amount': amount}
            self.form_active = True; self.last_form = (action, fields); self._prepared_from_form = False
            self.run('query', lambda: self.client.form('SIMULATE_CARD_DEPOSIT', fields))
            return
        if action != '转账':
            return super().business_form(action, defaults, _card_checked)
        if self.busy or self.pending or self.uncertain:
            return
        self.show_page(1)
        if defaults:
            self.recipient.setCurrentIndex(self.recipient.findData(defaults['recipient_name']))
            if self.recipient.currentIndex() < 0: self.recipient.setEditText(defaults['recipient_name'])
            self.amount.setText(defaults['amount'])
        self.controls()

    def recipient_value(self):
        index = self.recipient.currentIndex()
        if index >= 0 and self.recipient.currentText() == self.recipient.itemText(index):
            return self.recipient.itemData(index)
        return self.recipient.currentText().strip()

    def copy_card_number(self):
        if not self.snapshot or self.card_list.currentRow() < 0: return
        row = self.snapshot['objects']['cards'][self.card_list.currentRow()]
        number = row.get('card_number')
        if number:
            QApplication.clipboard().setText(number)
            self.card_note.setText('模拟卡号已复制 · 尾号' + number[-4:])

    def select_card(self):
        if not self.snapshot or self.card_list.currentRow() < 0:
            return
        row = self.snapshot['objects']['cards'][self.card_list.currentRow()]
        status = {'ACTIVE': '已激活', 'FROZEN': '已冻结', 'PENDING_ACTIVATION': '待激活'}[row['status']]
        self.card_note.setText(f"已选择：{row['display_name']} · {status}" + ('\n' + self.card_details[row['display_name']] if row['display_name'] in self.card_details else ''))
        if row.get('card_number'): self.card_note.setText(self.card_note.text() + '\n模拟卡号：**** ' + row['card_number'][-4:])
        self.card_action.setText({'ACTIVE': '冻结此卡', 'FROZEN': '解冻此卡', 'PENDING_ACTIVATION': '激活此卡'}[row['status']])
        duplicates = sum(r['display_name'] == row['display_name'] for r in self.snapshot['objects']['cards'])
        if duplicates > 1:
            self.card_note.setText('存在同名卡，当前名称接口不能唯一选择，暂不办理。')
        self.controls()

    def card_status_form(self):
        if not self.card_action.isEnabled() or not self.snapshot or self.card_list.currentRow() < 0:
            return
        card = self.snapshot['objects']['cards'][self.card_list.currentRow()]
        self.business_form({'ACTIVE': '冻结', 'FROZEN': '解冻', 'PENDING_ACTIVATION': '激活'}[card['status']],
                           {'card_name': card['display_name']})

    def read_card_limits(self):
        if self.busy or self.pending or self.uncertain or not self.snapshot or self.card_list.currentRow() < 0:
            return
        row = self.snapshot['objects']['cards'][self.card_list.currentRow()]
        self.form_active = True
        self.run('query', lambda: self.client.form('QUERY_CARD_LIMITS', {'card_name': row['display_name']}))

    def send(self, text=None):
        value = text if text is not None else self.input.text()
        if value.strip() and not self.busy and (not self.blocked or self.can_interrupt_chat()):
            self.conversation.add_message('user', value.strip(),
                                          display_name=self.current_customer.text().removeprefix('当前演示客户：'))
            self._prepared_from_form = False
        super().send(text)

    def receive(self, kind, result):
        if kind == 'ledger':
            self.busy = False
            if 'read_error' in result:
                self.bills_page.clear(result['read_error'])
                self.status.setText('账单未更新，请重试；未执行任何资金操作。')
            else:
                self.bills_page.set_data(result)
                self.status.setText('账单已更新 · 当前账户实际账本')
            self.controls()
            return
        super().receive(kind, result)
        if not hasattr(self, 'pages'):
            return
        if kind in {'connect', 'customer', 'customer_error'}:
            self.wealth_page.clear()
            self.bills_page.clear()
            self.bills_page.default_range = None
            self.ai_context.setText('当前账户正在读取…')
            self.snapshot = None
            self.actor = None
            self.completed_form = False
            self.card_details.clear()
            self.assistant_box.sync()
            self.amount.clear()
            self.recipient.clear()
            self.card_list.clear()
            self.transactions.setRowCount(0)
            self.balance_value.setText('正在读取…' if self.client.token else '尚未连接')
            self.payer.setText('付款账户尚未确认')
            self.conversation.clear()
            self.result_box.hide()
        elif kind == 'batch_receipts':
            self.conversation.add_message('assistant', result)
            self.toggle_assistant(True)
        elif kind == 'accounts':
            actor = (result.get('current_customer_ref'), result['current_account_ref'])
            if result.get('wealth'):
                self.wealth_page.set_data(result['wealth'], actor)
            else:
                self.wealth_page.clear()
                self.wealth_page.feedback.setText(result.get('wealth_error', '理财数据尚未加载。'))
            if self.actor is not None and actor != self.actor:
                self.amount.clear()
            changed = self.actor != actor
            self.actor, self.snapshot = actor, result
            if changed:
                self.bills_page.search.clear()
                self.bills_page.category.setCurrentIndex(0)
                self.bills_page.select_tab(False)
            if result.get('bill_error'):
                self.bills_page.clear(result['bill_error'])
            else:
                self.bills_page.set_data(result.get('bill_ledger', result['ledger']), default=changed)
            self.status.setText('账户已更新')
            for index, account in enumerate(result['accounts']):
                self.accounts.setItemText(index, account['display_name'])
            current = next(a for a in result['accounts'] if a['account_ref'] == actor[1])
            card=current.get('transfer_card')
            self.bills_page.account_button.setText((card['display_name']+' · 尾号'+card['last4'] if card else current['display_name'])+'  切换')
            self.account_picker.setText(self.bills_page.account_button.text())
            self.account_picker.setIcon(icon('card'))
            self.current_account.setText('当前账户：' + current['display_name'])
            self.ai_context.setText(self.current_customer.text() + '\n当前账户：' + current['display_name'])
            self.balance_value.setText('¥ ' + money(current['balance_minor']))
            self.balance_note.setText(current['display_name'] + ' · 人民币账户余额')
            self.payer.setText('付款账户：' + current['display_name'] + '\n可用余额：¥ ' + money(current['balance_minor']))
            self.payer_card_picker.blockSignals(True)
            self.payer_card_picker.clear()
            for account in result['accounts']:
                card = account.get('transfer_card')
                if card:
                    self.payer_card_picker.addItem(card['display_name'] + ' · 尾号' + card['last4'] +
                        (' · 已激活' if card['status'] == 'ACTIVE' else ' · 不可付款'), account['account_ref'])
            self.payer_card_picker.setCurrentIndex(self.payer_card_picker.findData(current['account_ref']))
            self.payer_card_picker.blockSignals(False)
            choice = self.recipient_value()
            self.recipient.blockSignals(True)
            self.recipient.clear()
            rows = result['objects']['recipients']
            for row in rows:
                # Existing name resolver refuses ambiguity; never silently choose a namesake.
                if sum(r['display_name'] == row['display_name'] for r in rows) == 1:
                    self.recipient.addItem(row['display_name'] + ' · ' + row['kind'], row['display_name'])
            self.recipient.setCurrentIndex(self.recipient.findData(choice))
            if choice and self.recipient.currentIndex() < 0: self.recipient.setEditText(choice)
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
            labels = {'INCOME': '收入', 'EXPENSE': '消费', 'TRANSFER_OUT': '转出', 'TRANSFER_IN': '转入',
                      'WEALTH_RESERVE': '申购冻结', 'WEALTH_RELEASE': '理财解冻', 'WEALTH_CREDIT': '赎回到账'}
            for index, row in enumerate(transactions):
                values = [row['occurred_at'][:16].replace('T', ' '), labels[row['kind']] + ' · ' + (row['merchant'] or row['category']),
                          ('+' if row['kind'] in {'INCOME', 'TRANSFER_IN', 'WEALTH_RELEASE', 'WEALTH_CREDIT'} else '−') + money(row['amount_minor'])]
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
            self.conversation.add_message('assistant', self.result_text.text(), error=True)
        elif isinstance(result, list):
            self.conversation.add_turn(result, self.summarize, pending=self.pending is not None)
            summaries = []
            write_statuses = []
            for event, data in result:
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
                if any(event == 'card' and data.get('type') == 'result'
                       and data['payload']['operation'] not in {'GET_BALANCE', 'QUERY_BILLS', 'QUERY_CARD_LIMITS'}
                       for event, data in result):
                    self.result_box.setTitle('部分完成 · 已完成付款不会撤回' if partial else '本次办理结果')
                    self.result_text.setText('\n\n'.join(summaries))
                    self.result_box.show()
            if self.pending:
                if self.decision is None:
                    label = '付款账户：' if self.pending.get('recipient') or self.pending.get('items') else '办理账户：'
                    self.confirm_text.setText(label + self.context_account.text() + '\n' + self.pending['summary'])
                self.status.setText('办理结果待核对 · 请重试原决定，不要另建付款' if self.decision is not None else '等待确认 · 尚未执行付款或业务变更')
                if self.decision is None:
                    self.result_box.hide()
                if not self.assistant_box.isVisible():
                    QTimer.singleShot(0, lambda: self.main_scroll.ensureWidgetVisible(self.confirmation))
                if self._prepared_from_form and self.decision is None:
                    guidance = ('当日累计转出（含本笔）超过1,000元，请完成当前模式要求的认证后继续；也可取消。' if self.pending['risk_level'] == 'RED'
                                else '请核对收款人和金额，确认后才会扣款。')
                    self.confirm_text.setText('付款：' + self.payer.text().split('\n')[0].removeprefix('付款账户：') + '\n' + self.pending['summary'] + '\n' + guidance)
            elif result[-1][1]['status'] == 'REJECTED' and not summaries:
                self.result_text.setText('本次操作未执行。填写内容已保留，可返回修改。')
                self.result_box.show()
        self.controls()

    @staticmethod
    def summarize(receipt):
        from bankagent.banking.wealth import OPERATIONS
        if receipt['operation'] in OPERATIONS:
            from bankagent.agent.scenarios.wealth import render
            return render(receipt)
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
        if operation == 'SIMULATE_CARD_DEPOSIT':
            return f"模拟入金成功 · {data['display_name']} ¥ {money(data['amount_minor'])}\n余额：¥ {money(data['remaining_balance_minor'])}（非真实存款）"
        if operation == 'GET_BALANCE':
            return '账户余额：¥ ' + money(data['balance_minor'])
        if operation == 'QUERY_BILLS':
            return f"已查询 {len(data['transactions'])} 笔流水；消费合计 ¥ {money(data['total_minor'])}。"
        if operation == 'QUERY_CARD_LIMITS':
            return f"单笔限额 ¥ {money(data['single_limit_minor'])} · 每日限额 ¥ {money(data['daily_limit_minor'])}"
        if operation in {'ACTIVATE_DEBIT_CARD', 'ISSUE_DEBIT_CARD', 'FREEZE_CARD', 'UNFREEZE_CARD'}:
            state = {'ACTIVE': '已激活', 'FROZEN': '已冻结', 'PENDING_ACTIVATION': '待激活'}.get(data.get('status'), '已办理')
            return (data.get('display_name') or '借记卡') + ' · ' + state
        if operation == 'BATCH_TRANSFER':
            return '整批转账成功\n' + '\n'.join(f"{row['recipient']} ¥ {money(row['amount_minor'])} · 成功" for row in data['items'])
        return '业务已完成；详细回执可展开查看。'
