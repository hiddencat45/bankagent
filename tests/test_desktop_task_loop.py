"""Offscreen native widgets + real HTTP app via in-process transport adapter."""
import io
import time
import pytest
from test_query_loop import Scripted, call, answer, client_for
from test_task_loop import prepare, balance


def test_native_pending_can_modify_query_and_confirm(monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6.QtWidgets')
    from PySide6.QtWidgets import QApplication
    from desktop.window import BankWindow
    from desktop.client import QueryClient
    app = QApplication.instance() or QApplication([])
    model = Scripted(prepare(), prepare('30', ident='p2'), call('get_balance', {}, 'b'),
                     answer('未执行，余额见下方。'), prepare('30', ident='p3'),
                     call('query_transactions', {'period': '本月'}, 'q'), answer('记录如下。'))
    with client_for(model) as client:
        def post(self, path, payload):
            response = client.post(path, json=payload, headers={'Authorization': 'Bearer ' + self.token} if self.token else {})
            response.raise_for_status()
            from email.message import Message
            stream = io.BytesIO(response.content)
            stream.headers = Message()
            stream.headers['Content-Type'] = response.headers['content-type']
            return stream
        monkeypatch.setattr(QueryClient, 'post', post)
        monkeypatch.setattr(BankWindow, 'load_accounts', lambda self: None)
        window = BankWindow('http://localhost')
        def wait(predicate):
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                app.processEvents()
                if predicate():
                    return
                time.sleep(.01)
            assert predicate()
        try:
            wait(lambda: not window.busy and bool(window.client.token))
            window.send('转给张伟40')
            wait(lambda: not window.busy and window.pending is not None)
            assert window.input.isEnabled() and window.submit.isEnabled()
            assert not window.switch_customer.isEnabled()
            window.send('改为三十块')
            wait(lambda: not window.busy and window.pending['amount_minor'] == 3000)
            window.send('先查余额')
            wait(lambda: not window.busy and window.pending is None)
            assert balance() == 500000
            window.send('继续刚才那笔')
            wait(lambda: not window.busy and window.pending is not None)
            old = dict(window.pending)
            window.approve.click()
            wait(lambda: not window.busy and window.pending is None)
            assert balance() == 497000
            assert '关联' in window.history.toPlainText()
            window.client.resume(old, 'approve')
            assert balance() == 497000
        finally:
            window.close()
            window.deleteLater()
            app.processEvents()
