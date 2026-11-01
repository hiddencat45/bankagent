"""Native chat bubbles and receipt cards; no business execution or model parsing."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QPainter, QColor
from PySide6.QtWidgets import (QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QSizePolicy, QLayout, QProgressBar)
from desktop.client import money
from desktop.icons import icon as native_icon


class ChatView(QScrollArea):
    receipt_opened = Signal(dict)
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
        ''')
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
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
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
        line.addWidget(bubble)
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
        self.fit_bubbles()
        return body

    def fit_bubbles(self):
        width = max(120, int(self.viewport().width() * .84) - 32)
        for _, bubble in self.rows:
            bubble.setMaximumWidth(width)
            # Wrapped QLabel size hints otherwise collapse a long reply into a narrow column.
            bubble.setMinimumWidth(min(width, 120 if bubble.objectName() == 'userBubble' else
                                       620 if bubble.objectName() == 'assistantBubble' else 480))
            bubble.layout().invalidate()
            bubble.setMinimumHeight(max(bubble.minimumSizeHint().height(),
                                        bubble.layout().heightForWidth(width)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_bubbles()

    def add_message(self, role, value, error=False, display_name=None):
        if not value:
            return
        body = self.bubble(role, 'errorBubble' if error else
                           'userBubble' if role == 'user' else 'assistantBubble', display_name)
        body.addWidget(self.label(value))
        self.transcript.append(('你：' if role == 'user' else '有度：') + value)

    def add_receipt(self, receipt, summary):
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
            button = QPushButton('查看理财持仓与订单 →')
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
        for event, data in events:
            if event in {'message', 'error'}:
                value = data.get('text', data.get('message', ''))
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
