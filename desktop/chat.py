"""Native chat bubbles and receipt cards; no business execution or model parsing."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QSizePolicy, QLayout)
from desktop.client import money


class ChatView(QScrollArea):
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
            QWidget#assistantBubble {background:white;border:1px solid #e0e8e3;border-radius:12px;}
            QWidget#receiptCard {background:#f7fcf9;border:1px solid #bdd9cb;border-radius:12px;}
            QWidget#errorBubble {background:#fff3ee;border:1px solid #e7c0b5;border-radius:12px;}
            QLabel {background:transparent;border:0;}
            QLabel#speaker {font-size:11px;color:#708078;}
            QLabel#receiptAmount {font-size:24px;font-weight:600;color:#194f42;}
            QPushButton#replyDetails {border:0;background:transparent;text-align:left;
                color:#60786c;padding:4px 0;font-size:12px;}
        ''')
        self.verticalScrollBar().rangeChanged.connect(lambda lo, hi: self.verticalScrollBar().setValue(hi))

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

    def bubble(self, role, style):
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
        body.addWidget(self.label('你' if role == 'user' else '有度', 'speaker'))
        if role == 'user':
            line.addStretch(1)
        else:
            avatar = QLabel()
            avatar.setFixedSize(28, 28)
            avatar.setPixmap(QPixmap(str(Path(__file__).parent / 'assets' / 'youdu.png')).scaled(
                28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            line.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)
        line.addWidget(bubble)
        if role != 'user':
            line.addStretch(1)
        self.stack.insertWidget(self.stack.count() - 1, row)
        self.rows.append((row, bubble))
        self.fit_bubbles()
        return body

    def fit_bubbles(self):
        width = max(120, int(self.viewport().width() * .84) - 32)
        for _, bubble in self.rows:
            bubble.setMaximumWidth(width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_bubbles()

    def add_message(self, role, value, error=False):
        if not value:
            return
        body = self.bubble(role, 'errorBubble' if error else
                           'userBubble' if role == 'user' else 'assistantBubble')
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
        self.transcript.append(summary)
        return body

    def add_turn(self, events, summarize, pending=False):
        receipts = [data['payload'] for event, data in events
                    if event == 'card' and data.get('type') == 'result']
        # Keep the entire explanation available; never delete sentences by keywords.
        # Errors, failures and pending instructions always remain visible.
        compact = (bool(receipts) and not pending and events[-1][1].get('status') == 'COMPLETED'
                   and not any(event == 'error' for event, _ in events)
                   and all(r['status'] == 'COMPLETED' for r in receipts))
        explanations = []
        last_card = None
        for event, data in events:
            if event in {'message', 'error'}:
                value = data.get('text', data.get('message', ''))
                if compact and event == 'message':
                    explanations.append(value)
                else:
                    self.add_message('assistant', value, error=event == 'error')
            elif event == 'card' and data.get('type') == 'result':
                receipt = data['payload']
                last_card = self.add_receipt(receipt, summarize(receipt))
        if explanations and last_card is not None:
            toggle = QPushButton('查看完整回复 ▾')
            toggle.setObjectName('replyDetails')
            toggle.setCheckable(True)
            detail = self.label('\n\n'.join(explanations))
            detail.hide()
            toggle.toggled.connect(detail.setVisible)
            toggle.toggled.connect(lambda shown: toggle.setText('收起完整回复 ▴' if shown else '查看完整回复 ▾'))
            last_card.addWidget(toggle)
            last_card.addWidget(detail)

    def clear(self):
        for row, _ in self.rows:
            self.stack.removeWidget(row)
            row.hide()
            row.deleteLater()
        self.rows.clear()
        self.transcript.clear()
        self.placeholder.show()

    def toPlainText(self):
        """Accessible transcript of primary messages/cards, excluding folded duplicates."""
        return '\n'.join(self.transcript)
