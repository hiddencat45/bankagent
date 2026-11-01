"""Overlay conversation space composed from the existing controller's widgets."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QPlainTextEdit, QScrollArea, QFrame)
from desktop.icons import icon


class MessageInput(QPlainTextEdit):
    returnPressed = Signal()

    def __init__(self):
        super().__init__()
        self.setAccessibleName('业务请求')
        self.setPlaceholderText('帮我看看这个月的钱花在哪里了……')
        self.setFixedHeight(92)

    def text(self):
        return self.toPlainText()

    def setText(self, value):
        self.setPlainText(value)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.returnPressed.emit()
        else:
            super().keyPressEvent(event)


class AssistantSpace(QFrame):
    def __init__(self, owner):
        super().__init__(owner.centralWidget())
        self.owner = owner
        self.setObjectName('assistantSpace')
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 14, 20, 14)
        header = QHBoxLayout()
        mark = QLabel(); mark.setPixmap(icon('brand', 28).pixmap(28, 28)); header.addWidget(mark)
        brand = QLabel('有度'); brand.setObjectName('brand')
        header.addWidget(brand)
        self.context = QLabel(); self.context.setObjectName('muted')
        self.context.setWordWrap(True)
        header.addStretch(1)
        for button in (owner.new, owner.ai_expand, owner.ai_close):
            button.setObjectName('quietAction'); header.addWidget(button)
        outer.addLayout(header)
        outer.addWidget(self.context)
        center_row = QHBoxLayout(); center_row.addStretch()
        self.center = QWidget(); self.center.setObjectName('conversationCenter'); self.center.setMaximumWidth(880)
        self.column = QVBoxLayout(self.center); self.column.setContentsMargins(0, 0, 0, 0); self.column.setSpacing(14)
        self.top_space = QWidget(); self.column.addWidget(self.top_space, 1)
        self.welcome = QWidget(); welcome = QVBoxLayout(self.welcome)
        title = QLabel('今天想了解什么？'); title.setObjectName('welcomeTitle'); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel('查查消费、管理卡片，也可以直接告诉我你的需求')
        subtitle.setObjectName('muted'); subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter); subtitle.setWordWrap(True)
        welcome.addWidget(title); welcome.addWidget(subtitle); self.column.addWidget(self.welcome)
        self.column.addWidget(owner.conversation, 1)
        self.confirm_scroll = QScrollArea(); self.confirm_scroll.setWidgetResizable(True)
        self.confirm_scroll.setMaximumHeight(270); self.confirm_scroll.setMinimumHeight(240)
        self.column.addWidget(self.confirm_scroll)
        self.shortcuts = QWidget(); shortcuts = QHBoxLayout(self.shortcuts); shortcuts.addStretch()
        self.shortcut_buttons = []
        for kind, label, prompt in [('ledger', '消费去向', '帮我看看这个月的消费去向'),
                              ('transfer', '转一笔钱', '我想转账'), ('card', '我的卡片', '查看我的借记卡')]:
            button = QPushButton(label); button.setObjectName('suggestion')
            button.setIcon(icon(kind))
            button.clicked.connect(lambda checked=False, value=prompt: self.prefill(value))
            shortcuts.addWidget(button); self.shortcut_buttons.append(button)
        shortcuts.addStretch(); self.column.addWidget(self.shortcuts)
        composer = QFrame(); composer.setObjectName('composer'); compose = QVBoxLayout(composer)
        compose.addWidget(owner.input)
        footer = QHBoxLayout(); hint = QLabel('Enter 换行 · Ctrl+Enter 发送'); hint.setObjectName('muted')
        footer.addWidget(hint); footer.addStretch(); footer.addWidget(owner.submit); compose.addLayout(footer)
        self.column.addWidget(composer)
        self.feedback = QLabel(); self.feedback.setObjectName('muted'); self.feedback.setWordWrap(True)
        self.column.addWidget(self.feedback)
        self.bottom_space = QWidget(); self.column.addWidget(self.bottom_space, 1)
        self.diagnostics = QPushButton('操作详情'); self.diagnostics.setObjectName('quietAction'); self.diagnostics.setCheckable(True)
        self.diagnostics.toggled.connect(owner.history.setVisible)
        self.column.addWidget(owner.history); owner.history.setMaximumHeight(100); owner.history.hide()
        center_row.addWidget(self.center, 1); center_row.addStretch(); outer.addLayout(center_row, 1)
        bottom = QHBoxLayout(); bottom.addStretch(); bottom.addWidget(self.diagnostics); outer.addLayout(bottom)
        self.hide()

    def prefill(self, value):
        if self.owner.input.isEnabled():
            self.owner.input.setText(value); self.owner.input.setFocus()

    def sync(self):
        owner = self.owner
        self.column.setSpacing(8 if owner.pending else 14)
        active = bool(owner.conversation.rows) or owner.pending is not None
        for widget in (self.welcome, self.shortcuts, self.top_space, self.bottom_space):
            widget.setVisible(not active)
        owner.conversation.setVisible(active)
        self.confirm_scroll.setVisible(owner.pending is not None and self.isVisible())
        owner.confirm_actions.setVisible(owner.pending is not None)
        owner.conversation.setMinimumHeight(40 if owner.pending else 140)
        owner.input.setFixedHeight(48 if owner.pending else 58 if active else 92)
        customer = owner.current_customer.text().removeprefix('当前演示客户：')
        self.context.setText('本地模拟 · ' + owner.mode + '  /  ' + customer + ' · ' + owner.context_account.text())
        self.feedback.setText('正在处理，请稍候…' if owner.busy else
                              '结果待核对，请使用原操作的核对按钮。' if owner.uncertain else
                              '请核对下方操作；批准前不会执行。' if owner.pending else
                              '请求未完成，请查看提示或重新连接。' if owner.blocked else '')
        for button in self.shortcut_buttons:
            button.setEnabled(owner.input.isEnabled())
