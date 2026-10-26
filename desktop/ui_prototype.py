"""Native visual prototype; deliberately has no service, model or ledger connection."""
import argparse
import os
from pathlib import Path
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget)


STYLE = '''
QWidget {font-family:"Microsoft YaHei"; font-size:14px; color:#243e36; background:#f5f7f4;}
QFrame#sidebar {background:#183e34; border-radius:18px;}
QFrame#sidebar QLabel {background:transparent; color:#d8e8df;}
QLabel#brand {font-size:28px; font-weight:700; color:white;}
QLabel#title {font-size:28px; font-weight:700;}
QLabel#subtitle {color:#6b7e73; font-size:13px;}
QLabel#eyebrow {font-size:12px; color:#74877c;}
QLabel#section {font-size:18px; font-weight:600;}
QLabel#balance {font-size:36px; font-weight:600; color:#175743;}
QLabel#notice {color:#82652f; background:#f5eddc; padding:10px; border-radius:8px; font-size:12px;}
QFrame#card {background:white; border:1px solid #e1e8e1; border-radius:14px;}
QFrame#card QLabel {background:transparent;}
QFrame#card QLabel#message {background:#eef5ee; padding:14px; border-radius:10px;}
QFrame#card QLabel#notice {background:#f5eddc;}
QPushButton {background:white; border:1px solid #dbe4da; border-radius:8px; padding:10px 14px;}
QPushButton:hover {background:#e8f1e7; border-color:#8cad96;}
QPushButton:focus, QLineEdit:focus {border:2px solid #3d8b66;}
QPushButton#primary {background:#23694e; color:white; border-color:#23694e; font-weight:600;}
QPushButton#primary:hover {background:#19573e;}
QPushButton#nav {text-align:left; color:#d4e2d9; background:transparent; border:0; padding:13px;}
QPushButton#nav:checked {background:#315b49; color:white;}
QPushButton#nav:disabled {color:#8ba397;}
QLineEdit {background:#f9fbf8; border:1px solid #dbe4da; border-radius:8px; padding:12px;}
QScrollArea {border:0; background:transparent;}
'''


def label(text, role='', wrap=False):
    item = QLabel(text)
    item.setTextFormat(Qt.TextFormat.PlainText)
    item.setObjectName(role)
    item.setWordWrap(wrap)
    return item


def button(text, callback, role=''):
    item = QPushButton(text)
    item.setObjectName(role)
    item.clicked.connect(callback)
    return item


def card():
    frame = QFrame()
    frame.setObjectName('card')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 22, 22, 22)
    layout.setSpacing(16)
    return frame, layout


class PrototypeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('有度 · 原生桌面设计预览（示例数据）')
        self.resize(1280, 840)
        self.setMinimumSize(1024, 768)
        self.setStyleSheet(STYLE)
        root = QWidget()
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(20, 20, 20, 20)
        shell.setSpacing(24)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(160)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(16, 26, 16, 24)
        nav.setSpacing(10)
        nav.addWidget(label('有度', 'brand'))
        nav.addWidget(label('BANKING, WITH CLARITY', wrap=True))
        nav.addSpacing(30)
        self.nav_buttons = []
        for text, page in [('账户概览', 0), ('转账', 1), ('账单 · 待预览', None),
                           ('卡包 · 待预览', None), ('理财 · 待预览', None)]:
            item = button(text, lambda checked=False, p=page: self.navigate(p), 'nav')
            item.setCheckable(page is not None)
            item.setEnabled(page is not None)
            nav.addWidget(item)
            self.nav_buttons.append(item)
        nav.addStretch()
        nav.addWidget(label('本地桌面\n原生控件设计预览', wrap=True))
        shell.addWidget(sidebar)
        center = QVBoxLayout()
        center.setSpacing(18)
        header = QHBoxLayout()
        self.title = label('账户概览', 'title')
        header.addWidget(self.title, 1)
        self.toggle = button('收起助手', self.toggle_assistant)
        header.addWidget(self.toggle)
        center.addLayout(header)
        center.addWidget(label('把账户看清楚，把每一步交给自己决定。', 'subtitle', True))
        center.addWidget(label('设计预览 · 全部为虚构示例 · 不连接银行服务，不执行交易', 'notice', True))
        self.pages = QStackedWidget()
        self.pages.addWidget(self.overview())
        self.pages.addWidget(self.transfer())
        center.addWidget(self.pages, 1)
        center.addWidget(label('示例客户：林晓   /   当前账户：日常账户 · 0088', 'eyebrow', True))
        shell.addLayout(center, 1)
        self.assistant, chat = card()
        self.assistant.setFixedWidth(300)
        chat.addWidget(label('有度 AI', 'section'))
        chat.addWidget(label('与你一起，理清每一笔', 'subtitle'))
        chat.addSpacing(16)
        chat.addWidget(label('你好，林晓。\n\n你可以从账户概览查看收支，也可以直接告诉我想办什么。', 'message', True))
        chat.addWidget(label('建议从这里开始', 'eyebrow'))
        chat.addWidget(button('最近钱花在哪里了？', self.preview_query))
        chat.addWidget(button('帮我准备一笔转账', lambda: self.navigate(1)))
        self.reply = label('此面板展示对话布局，尚未连接模型。', 'subtitle', True)
        chat.addWidget(self.reply)
        chat.addStretch()
        chat.addWidget(label('业务操作会先展示确认信息。', 'eyebrow', True))
        chat.addWidget(button('查看转账确认示例', self.show_confirmation, 'primary'))
        shell.addWidget(self.assistant)
        self.navigate(0)

    def overview(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        balance, contents = card()
        contents.addWidget(label('日常账户   ·   尾号 0088', 'subtitle'))
        contents.addWidget(label('可用余额 / CNY', 'eyebrow'))
        contents.addWidget(label('¥ 12,680.00', 'balance'))
        contents.addWidget(label('示例借记账户  ·  正常', 'subtitle'))
        contents.addWidget(button('发起转账', lambda: self.navigate(1), 'primary'))
        layout.addWidget(balance)
        recent, rows = card()
        rows.addWidget(label('近期交易', 'section'))
        rows.addWidget(label('展示最近 3 笔示例记录', 'eyebrow'))
        for title, detail, amount in [('咖啡与简餐', '今天 09:42 · 餐饮消费', '− ¥ 32.00'),
                                      ('城市交通', '昨天 18:10 · 交通消费', '− ¥ 6.00'),
                                      ('演示入账', '10月24日 10:00 · 收入', '+ ¥ 3,000.00')]:
            row = QHBoxLayout()
            info = QVBoxLayout()
            info.addWidget(label(title))
            info.addWidget(label(detail, 'eyebrow'))
            row.addLayout(info, 1)
            row.addWidget(label(amount))
            rows.addLayout(row)
        layout.addWidget(recent)
        layout.addStretch()
        return self.scrolled(page)

    def transfer(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        form, fields = card()
        self.transfer_form = form
        fields.addWidget(label('准备转账', 'section'))
        fields.addWidget(label('填写信息 → 核对确认 → 查看结果', 'subtitle', True))
        fields.addWidget(label('付款账户', 'eyebrow'))
        fields.addWidget(label('日常账户 · 0088    /    示例余额 ¥ 12,680.00', wrap=True))
        fields.addWidget(label('收款人（示例）', 'eyebrow'))
        self.recipient = QLineEdit('张三 · 示例联系人')
        self.recipient.setAccessibleName('示例收款人')
        fields.addWidget(self.recipient)
        fields.addWidget(label('金额（元）', 'eyebrow'))
        self.amount = QLineEdit('40.00')
        self.amount.setAccessibleName('示例转账金额')
        fields.addWidget(self.amount)
        self.feedback = label('预览只演示信息布局，不会扣款。', 'subtitle', True)
        fields.addWidget(self.feedback)
        fields.addWidget(button('下一步：核对信息', self.show_confirmation, 'primary'))
        layout.addWidget(form)
        self.confirmation, details = card()
        details.addWidget(label('核对这笔转账', 'section'))
        self.summary = label('', wrap=True)
        details.addWidget(self.summary)
        details.addWidget(label('仅预览，点击下方按钮不会产生交易。', 'notice', True))
        actions = QHBoxLayout()
        actions.addWidget(button('返回修改', self.edit_transfer))
        actions.addWidget(button('结束预览', self.finish_preview, 'primary'))
        details.addLayout(actions)
        layout.addWidget(self.confirmation)
        self.confirmation.hide()
        layout.addStretch()
        return self.scrolled(page)

    @staticmethod
    def scrolled(page):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        return scroll

    def navigate(self, page):
        self.pages.setCurrentIndex(page)
        self.title.setText('账户概览' if page == 0 else '转账')
        for index, item in enumerate(self.nav_buttons):
            item.setChecked(index == page)

    def toggle_assistant(self):
        visible = self.assistant.isHidden()
        self.assistant.setVisible(visible)
        self.toggle.setText('收起助手' if visible else '展开助手')

    def preview_query(self):
        self.reply.setText('示例回答：这两笔消费共 38.00 元，其中餐饮 32.00 元、交通 6.00 元。\n\n此处未调用模型或查询账本。')

    def show_confirmation(self):
        from decimal import Decimal, InvalidOperation
        self.navigate(1)
        try:
            amount = Decimal(self.amount.text())
            valid = amount.is_finite() and 0 < amount <= Decimal('12680') and amount == amount.quantize(Decimal('.01'))
        except InvalidOperation:
            valid = False
        if not valid or not self.recipient.text().strip():
            self.confirmation.hide()
            self.feedback.setText('请填写收款人和有效金额，最多两位小数且不超过示例余额。')
            return
        self.feedback.setText('信息已准备，请核对下方预览。')
        self.summary.setText(f'从：日常账户 · 0088\n至：{self.recipient.text().strip()}\n金额：¥ {amount:,.2f}')
        self.transfer_form.hide()
        self.confirmation.show()
        self.pages.currentWidget().ensureWidgetVisible(self.confirmation)

    def edit_transfer(self):
        self.confirmation.hide()
        self.transfer_form.show()

    def finish_preview(self):
        self.edit_transfer()
        self.feedback.setText('预览已结束。没有提交转账，没有改变余额。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', type=Path, help='Render screenshots offscreen without opening a desktop window')
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=840)
    args = parser.parse_args()
    if args.render:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    app = QApplication(sys.argv[:1])
    if args.render and sys.platform == 'win32':
        # Qt's offscreen platform does not enumerate Windows system fonts.
        fonts = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
        for name in ('msyh.ttc', 'msyhbd.ttc'):
            if QFontDatabase.addApplicationFont(str(fonts / name)) < 0:
                raise RuntimeError('Unable to load Chinese preview font')
    app.setFont(QFont('Microsoft YaHei', 10))
    window = PrototypeWindow()
    window.resize(args.width, args.height)
    window.show()
    if args.render:
        args.render.mkdir(parents=True, exist_ok=True)
        for name, action in [('overview', lambda: window.navigate(0)), ('transfer', window.show_confirmation)]:
            action()
            app.processEvents()
            if not window.grab().save(str(args.render / f'{name}.png')):
                raise RuntimeError('Unable to save preview')
        window.close()
    else:
        app.exec()


if __name__ == '__main__':
    main()
