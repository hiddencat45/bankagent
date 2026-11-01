"""Local authenticator enrollment. QR and credentials stay out of chat and files."""
import io
import threading

import segno
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton

from desktop.client import VerificationRejected


class EnrollmentResult(QObject):
    ready = Signal(object, object)


class EnrollmentDialog(QDialog):
    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self.enrollment = None
        self.busy = False
        self.delivery = EnrollmentResult(self)
        self.delivery.ready.connect(self.received)
        self.setWindowTitle('绑定手机验证器')
        self.resize(490, 590)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24); layout.setSpacing(12)
        heading = QLabel('为高风险转账增加安全验证')
        heading.setObjectName('dialogHeading'); heading.setWordWrap(True); layout.addWidget(heading)
        note = QLabel('同一客户名下所有卡当日累计转出超过1,000元，需要交易密码和手机动态码。\n'
                      '请在独立手机验证器中添加账号。本次仅绑定，不会执行转账。')
        note.setWordWrap(True); layout.addWidget(note)
        self.qr = QLabel(); self.qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr.setMaximumHeight(200)
        self.qr.hide(); layout.addWidget(self.qr)
        self.entry = QLineEdit(); self.entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.entry.setPlaceholderText('重新输入登录密码'); self.entry.setAccessibleName('登录密码')
        self.entry.setMaxLength(128); layout.addWidget(self.entry)
        self.status = QLabel('先验证登录密码，再使用手机验证器扫描二维码。\n绑定后暂不支持自助换绑或找回，请保管好验证器。')
        self.status.setWordWrap(True); self.status.setTextFormat(Qt.TextFormat.PlainText); layout.addWidget(self.status)
        self.submit = QPushButton('验证密码，显示二维码'); self.submit.setObjectName('primary')
        self.submit.clicked.connect(self.send); self.entry.returnPressed.connect(self.send); layout.addWidget(self.submit)
        self.cancel = QPushButton('返回，暂不绑定'); self.cancel.clicked.connect(self.reject); layout.addWidget(self.cancel)

    def send(self):
        if self.busy:
            return
        value = self.entry.text(); self.entry.clear()
        if not value:
            self.status.setText('请填写' + ('手机动态码。' if self.enrollment else '登录密码。'))
            return
        path = '/auth/mfa/confirm' if self.enrollment else '/auth/mfa/enroll'
        payload = {'enrollment_id': self.enrollment, 'code': value} if self.enrollment else {'login_password': value}
        self.busy = True; self.submit.setEnabled(False); self.cancel.setEnabled(False); self.entry.setEnabled(False)
        self.status.setText('正在验证，请稍候…')

        def work():
            try:
                result, error = self.client.request(path, payload), None
            except VerificationRejected as exc:
                result, error = None, str(exc)
            except Exception:
                result, error = None, '服务暂时不可用。若绑定结果不确定，请返回后重新查看；不会自动转账。'
            finally:
                payload.clear()
            self.delivery.ready.emit(result, error)
        threading.Thread(target=work, daemon=True).start()

    def received(self, result, error):
        self.busy = False; self.submit.setEnabled(True); self.cancel.setEnabled(True); self.entry.setEnabled(True)
        if error:
            self.status.setText(error); return
        if result.get('status') == 'CONFIGURED':
            self.qr.clear(); self.enrollment = None; self.accept(); return
        self.enrollment = result['enrollment_id']
        buffer = io.BytesIO()
        segno.make(result.pop('uri'), micro=False).save(buffer, kind='png', scale=4, border=4)
        pixmap = QPixmap(); pixmap.loadFromData(buffer.getvalue()); buffer.close()
        self.qr.setPixmap(pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio)); self.qr.show()
        self.entry.setPlaceholderText('手机验证器6位动态码'); self.entry.setAccessibleName('手机验证器6位动态码')
        self.entry.setMaxLength(6); self.entry.setFocus()
        self.status.setText('扫描二维码，输入动态码完成绑定（5分钟内有效）。\n'
                            '请勿分享二维码。保持手机与电脑时间准确。')
        self.submit.setText('验证动态码，完成绑定')

    def reject(self):
        if not self.busy:
            self.qr.clear(); self.entry.clear(); self.enrollment = None
            super().reject()

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
        else:
            self.reject(); event.accept()
