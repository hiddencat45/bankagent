"""Native Qt widgets, with network work outside the GUI thread."""
import threading
from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QPlainTextEdit, QLineEdit, QGroupBox)
from desktop.client import QueryClient, query_result, transfer_confirmation, money


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
        layout.addWidget(QLabel('支持余额、消费查询和模拟转账；高风险转账仅可取消，理财推荐尚未开放。'))
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
        self.confirmation = QGroupBox('请核对本次模拟转账')
        confirm_layout = QVBoxLayout(self.confirmation)
        self.confirm_text = QLabel()
        self.confirm_text.setTextFormat(Qt.TextFormat.PlainText)
        self.confirm_text.setWordWrap(True)
        confirm_layout.addWidget(self.confirm_text)
        actions = QHBoxLayout()
        self.approve = QPushButton('确认转账')
        self.reject = QPushButton('取消转账')
        self.retry = QPushButton('重试原决定 / 核对结果')
        self.approve.clicked.connect(lambda: self.decide('approve'))
        self.reject.clicked.connect(lambda: self.decide('reject'))
        self.retry.clicked.connect(lambda: self.decide(self.decision))
        for button in (self.approve, self.reject, self.retry):
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

    def controls(self):
        enabled = bool(self.client.token) and not self.busy and not self.blocked
        for item in self.buttons + [self.input, self.submit]:
            item.setEnabled(enabled)
        self.new.setEnabled(bool(self.client.token) and not self.busy and not self.uncertain)
        self.reconnect.setEnabled(not self.busy and not self.uncertain)
        self.confirmation.setVisible(self.pending is not None)
        ready = self.pending is not None and not self.busy
        self.approve.setEnabled(ready and self.decision is None and self.pending['risk_level'] == 'YELLOW')
        self.reject.setEnabled(ready and self.decision is None)
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
            except Exception:
                kind_result = 'decision_error' if kind == 'decision' else 'error'
                result = ('会话建立失败，请点击「重新连接」重试。' if kind == 'connect' else
                          '提交后的结果尚未确认。请重试原决定核对结果，勿另建同一笔转账。' if kind == 'decision' else
                          '连接或响应异常，结果尚未确认。请新建对话或重新连接后重试；不会自动重发。')
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
        if kind == 'connect':
            self.clear_confirmation()
            self.thread = None
            self.blocked = False
            self.mode = '真实模型' if result == 'model' else '离线规则'
            self.history.appendPlainText('有度：已建立新会话，可以开始查询。')
            self.status.setText('已连接 · ' + self.mode)
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
                pending = transfer_confirmation(result)
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
                             '\n确认后才会执行；如需改金额或收款人，请先取消，再重新提出请求。')
                    self.confirm_text.setText(f"收款人：{pending['recipient']}\n金额：¥ {money(pending['amount_minor'])}" + extra)
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
                                    + ' · ' + self.mode)
            except (KeyError, TypeError, ValueError):
                self.history.appendPlainText('有度：服务返回的数据不完整，已停止展示。请新建对话重试。')
                self.blocked = True
                self.uncertain = kind == 'decision'
        self.controls()

    def new_chat(self):
        if self.busy or self.uncertain:
            return
        self.clear_confirmation()
        self.thread = None
        self.blocked = False
        self.history.clear()
        self.status.setText('新对话 · ' + self.mode)
        self.controls()

    def closeEvent(self, event):
        self.closed.set()
        super().closeEvent(event)
