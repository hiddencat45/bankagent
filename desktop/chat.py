"""Native chat bubbles and receipt cards; no business execution or model parsing."""

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor
from PySide6.QtWidgets import (QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QSizePolicy, QLayout, QProgressBar)
from desktop.client import money
from desktop.icons import icon as native_icon
from desktop.wealth_chat import STYLE as WEALTH_CHAT_STYLE, render as render_wealth


class ChatView(QScrollArea):
    receipt_opened = Signal(dict)
    wealth_opened = Signal(str, dict)
    reply_requested = Signal(str)
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAccessibleName('与有度的对话')
        self.setMinimumHeight(140)
        self.content = QWidget()
        self.setWidget(self.content)
        self.stack = QVBoxLayout(self.content)
        self.stack.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.stack.setContentsMargins(4, 8, 4, 8)
        self.stack.setSpacing(14)
        self.stack.addStretch()
        self.rows = []
        self.transcript = []
        self.placeholder = QLabel('可问余额、查询交易，或描述要办理的业务。\n写操作仍需明确确认。')
        self.placeholder.setWordWrap(True)
        self.stack.insertWidget(0, self.placeholder)
        self.setStyleSheet('''
            QScrollArea {border:0;background:transparent;}
            QWidget#userBubble {background:#dceee4;border:1px solid #c6dfd1;border-radius:12px;}
            QWidget#assistantBubble {background:#ffffff;border:1px solid #dce6df;border-radius:12px;}
            QWidget#receiptCard {background:#f7fcf9;border:1px solid #bdd9cb;border-radius:12px;}
            QWidget#errorBubble {background:#fff3ee;border:1px solid #e7c0b5;border-radius:12px;}
            QLabel {background:transparent;border:0;}
            QLabel#speaker {font-size:11px;color:#708078;}
            QLabel#receiptAmount {font-size:24px;font-weight:600;color:#194f42;}
            QPushButton#replyDetails {border:0;background:transparent;text-align:left;
                color:#60786c;padding:4px 0;font-size:12px;}
        ''' + WEALTH_CHAT_STYLE)
        self.follow_tail = True
        bar = self.verticalScrollBar()
        bar.valueChanged.connect(lambda value: setattr(self, 'follow_tail', value >= bar.maximum()-24))
        bar.rangeChanged.connect(self.scroll_range_changed)

    def scroll_range_changed(self, low, high):
        if self.follow_tail:
            self.verticalScrollBar().setValue(high)

    @staticmethod
    def label(value, name=None):
        label = QLabel(value)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        if name:
            label.setObjectName(name)
        return label

    def bubble(self, role, style, display_name=None):
        self.placeholder.hide()
        row = QWidget()
        row.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(6)
        bubble = QWidget()
        bubble.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        bubble.setObjectName(style)
        body = QVBoxLayout(bubble)
        body.setContentsMargins(12, 10, 12, 10)
        body.setSpacing(7)
        body.setAlignment(Qt.AlignmentFlag.AlignTop)
        speaker = self.label((display_name or '你') if role == 'user' else '有度', 'speaker')
        if role == 'user':
            speaker.setAlignment(Qt.AlignmentFlag.AlignRight)
        body.addWidget(speaker)
        if role == 'user':
            line.addStretch(1)
        else:
            avatar = QLabel()
            avatar.setFixedSize(28, 28)
            avatar.setPixmap(native_icon('brand', 28).pixmap(28, 28))
            line.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)
        line.addWidget(bubble, 0, Qt.AlignmentFlag.AlignTop)
        if role == 'user':
            avatar = QLabel()
            avatar.setObjectName('userAvatar')
            avatar.setAccessibleName('用户头像')
            avatar.setFixedSize(28, 28)
            icon = QPixmap(56, 56)
            icon.fill(Qt.GlobalColor.transparent)
            painter = QPainter(icon)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor('#d2e7dc'))
            painter.drawEllipse(0, 0, 56, 56)
            painter.setBrush(QColor('#39715c'))
            painter.drawEllipse(20, 11, 16, 16)
            painter.drawRoundedRect(13, 30, 30, 18, 9, 9)
            painter.end()
            icon.setDevicePixelRatio(2)
            avatar.setPixmap(icon)
            line.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)
        else:
            line.addStretch(1)
        self.stack.insertWidget(self.stack.count() - 1, row)
        self.rows.append((row, bubble))
        QTimer.singleShot(0, self.fit_bubbles)
        return body

    def fit_bubbles(self):
        width = max(120, int(self.viewport().width() * .84) - 32)
        for _, bubble in self.rows:
            bubble.setMinimumHeight(0)
            bubble.setMaximumWidth(width)
            # Wrapped QLabel size hints otherwise collapse a long reply into a narrow column.
            bubble.setMinimumWidth(min(width, 120 if bubble.objectName() == 'userBubble' else
                                       620 if bubble.objectName() == 'assistantBubble' else 480))
            bubble.layout().invalidate()
            bubble.setMinimumHeight(max(bubble.minimumSizeHint().height(),
                                        bubble.layout().totalHeightForWidth(bubble.width())))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_bubbles()

    def add_message(self, role, value, error=False, display_name=None):
        if not value:
            return
        for button in self.findChildren(QPushButton,'wealthQuickReply'):button.setEnabled(False)
        body = self.bubble(role, 'errorBubble' if error else
                           'userBubble' if role == 'user' else 'assistantBubble', display_name)
        body.addWidget(self.label(value))
        if role=='assistant' and not error:
            from bankagent.agent.wealth_interview import quick_replies
            for reply in quick_replies(value):
                button=QPushButton(reply);button.setObjectName('wealthQuickReply')
                button.clicked.connect(lambda checked=False,text=reply:self.reply_requested.emit(text))
                body.addWidget(button)
        self.transcript.append(('你：' if role == 'user' else '有度：') + value)

    def add_receipt(self, receipt, summary):
        wealth = render_wealth(self, receipt)
        if wealth is not None:
            self.transcript.append(summary)
            return wealth
        body = self.bubble('assistant', 'receiptCard' if receipt['status'] == 'COMPLETED' else 'errorBubble')
        if receipt['operation'] == 'GET_BALANCE' and receipt['status'] == 'COMPLETED':
            body.addWidget(self.label('账户余额'))
            body.addWidget(self.label('¥ ' + money(receipt['data']['balance_minor']), 'receiptAmount'))
            body.addWidget(self.label('人民币 · 本次查询结果', 'speaker'))
        else:
            body.addWidget(self.label(summary))
        data = receipt.get('data') or {}
        from bankagent.banking.wealth import OPERATIONS
        if receipt['operation'] in OPERATIONS:
            button = QPushButton('查看理财并核对 →')
            button.setObjectName('wealthChatLink')
            button.clicked.connect(lambda: self.receipt_opened.emit(receipt))
            body.addWidget(button)
        if receipt['operation'] == 'QUERY_BILLS' and receipt['status'] == 'COMPLETED':
            categories = {}
            for row in data.get('transactions', []):
                if row['kind'] == 'EXPENSE':
                    categories[row['category']] = categories.get(row['category'], 0) + row['amount_minor']
            for category, amount in sorted(categories.items(), key=lambda item: -item[1]):
                body.addWidget(self.label(category + '  ¥ ' + money(amount)))
                bar = QProgressBar(); bar.setRange(0, 1000); bar.setValue(amount*1000//max(1, sum(categories.values())))
                bar.setTextVisible(False); bar.setFixedHeight(5); body.addWidget(bar)
        if receipt['status'] == 'COMPLETED' and receipt['operation'] in {
                'QUERY_BILLS', 'TRANSFER', 'BATCH_TRANSFER', 'PAY_BY_CARD', 'QUERY_CARD_LIMITS',
                'ACTIVATE_DEBIT_CARD', 'FREEZE_CARD', 'UNFREEZE_CARD', 'ISSUE_DEBIT_CARD'}:
            button = QPushButton('查看相关交易  →' if receipt['operation'] in {
                'QUERY_BILLS', 'TRANSFER', 'BATCH_TRANSFER', 'PAY_BY_CARD'} else '查看卡片与可用操作  →')
            button.setObjectName('quietAction')
            button.clicked.connect(lambda: self.receipt_opened.emit(receipt))
            body.addWidget(button)
        self.transcript.append(summary)
        return body

    def add_turn(self, events, summarize, pending=False):
        # Explanations stay visible; source receipts follow as supporting evidence.
        from bankagent.banking.wealth import OPERATIONS
        wealth_result = any(event == 'card' and data.get('type') == 'result'
                            and data['payload']['operation'] in OPERATIONS
                            and data['payload']['status'] == 'COMPLETED' for event, data in events)
        wealth_summaries = {summarize(data['payload']) for event, data in events
                           if event == 'card' and data.get('type') == 'result'
                           and data['payload']['operation'] in OPERATIONS
                           and data['payload']['status'] == 'COMPLETED'}
        for event, data in events:
            if event in {'message', 'error'}:
                value = data.get('text', data.get('message', ''))
                # This fixed transport notice duplicates the structured receipt below.
                if event == 'message' and wealth_result and (value in wealth_summaries or value == (
                        '已读取模拟业务结果，具体金额、筛选理由和订单状态见下方服务端回执。'
                        '理财申请已提交不等于成交或到账；未核实真实渠道的在售和到账信息。')):
                    continue
                self.add_message('assistant', value, error=event == 'error')
        for event, data in events:
            if event == 'card' and data.get('type') == 'result':
                self.add_receipt(data['payload'], summarize(data['payload']))

    def clear(self):
        for row, _ in self.rows:
            self.stack.removeWidget(row)
            row.hide()
            row.deleteLater()
        self.rows.clear()
        self.transcript.clear()
        self.follow_tail = True
        self.placeholder.show()

    def toPlainText(self):
        """Accessible transcript of visible messages and business receipts."""
        return '\n'.join(self.transcript)
