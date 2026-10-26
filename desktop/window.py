"""Native Qt widgets, with network work outside the GUI thread."""
import threading
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QPlainTextEdit, QLineEdit)
from desktop.client import QueryClient, query_result


class Delivery(QObject):
    completed = Signal(str, object)


class BankWindow(QMainWindow):
    def __init__(self, url):
        super().__init__()
        self.client = QueryClient(url)
        self.thread = None
        self.busy = False
        self.blocked = False
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
        layout.addWidget(QLabel('当前开放余额、消费查询与连续筛选；转账确认和理财推荐尚未开放。'))
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
        layout.addLayout(quick)
        self.history = QPlainTextEdit()
        self.history.setReadOnly(True)
        self.history.setAccessibleName('业务对话')
        self.history.setPlaceholderText('从一笔有依据的查询开始。')
        layout.addWidget(self.history, 1)
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
        layout.addWidget(QLabel('本地模拟银行 · 未连接真实银行 · 关闭应用后演示数据恢复初始状态'))
        self.setStyleSheet('''QWidget {font-family: "Microsoft YaHei"; font-size: 14px;
            color: #203348; background: #f2f5f8;} QLabel#heading {font-size: 25px; font-weight: bold;}
            QPlainTextEdit,QLineEdit {background:white; border:1px solid #d3dee8; border-radius:8px; padding:12px;}
            QPushButton {background:#176f69; color:white; border:0; border-radius:6px; padding:10px 18px;}
            QPushButton:disabled {background:#c2ccd5; color:#647484;}''')
        self.controls()
        QTimer.singleShot(0, lambda: self.run('connect', self.client.connect))

    def controls(self):
        enabled = bool(self.client.token) and not self.busy and not self.blocked
        for item in self.buttons + [self.input, self.submit]:
            item.setEnabled(enabled)
        self.new.setEnabled(bool(self.client.token) and not self.busy)

    def run(self, kind, function):
        self.busy = True
        self.controls()
        def work():
            try:
                result = function()
            except Exception:
                kind_result, result = 'error', '连接或响应异常，结果尚未确认。请新建对话后重试；不会自动重发。'
            else:
                kind_result = kind
            if not self.closed.is_set():
                try:
                    self.delivery.completed.emit(kind_result, result)
                except RuntimeError:
                    pass  # Window was destroyed during delivery.
        threading.Thread(target=work, daemon=True).start()

    def send(self, text=None):
        text = (text if text is not None else self.input.text()).strip()
        if not text or self.busy or self.blocked or not self.client.token:
            return
        self.history.appendPlainText('你：' + text)
        self.input.clear()
        self.status.setText('正在查询，请稍候…')
        thread = self.thread
        self.run('query', lambda: self.client.query(text, thread))

    def receive(self, kind, result):
        self.busy = False
        if kind == 'connect':
            self.mode = '真实模型' if result == 'model' else '离线规则'
            self.status.setText('已连接 · ' + self.mode)
        elif kind == 'error':
            self.history.appendPlainText('有度：' + result)
            self.status.setText('请求失败')
            self.blocked = True
        else:
            try:
                # Validate/format the whole result before displaying any success text.
                details = [query_result(data['payload']) for event, data in result
                           if event == 'card' and data.get('type') == 'result']
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
                self.blocked = final in {'AWAITING_CONFIRMATION', 'AWAITING_AUTHENTICATION'}
                if self.blocked:
                    self.history.appendPlainText('当前桌面版尚不提供写操作确认，本次未执行。请点击「新对话」继续查询。')
                labels = {'COMPLETED': '查询完成', 'NEEDS_CLARIFICATION': '等待补充信息',
                          'FAILED': '查询失败', 'REJECTED': '已拒绝', 'PENDING': '结果待确认'}
                self.status.setText(('未执行，等待新对话' if self.blocked else labels.get(final, final))
                                    + ' · ' + self.mode)
            except (KeyError, TypeError, ValueError):
                self.history.appendPlainText('有度：服务返回的数据不完整，已停止展示。请新建对话重试。')
                self.blocked = True
        self.controls()

    def new_chat(self):
        self.thread = None
        self.blocked = False
        self.history.clear()
        self.status.setText('新对话 · ' + self.mode)
        self.controls()

    def closeEvent(self, event):
        self.closed.set()
        super().closeEvent(event)
