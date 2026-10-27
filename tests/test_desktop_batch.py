"""Offscreen native batch confirmation, lost approval response and restart receipts."""
import io
import time
from email.message import Message
import pytest
from test_batch_transfer import app as bank_app, batch, balances
from test_query_loop import Scripted, answer


def test_native_batch_lost_response_retry_and_reopen_receipts(tmp_path, monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6.QtWidgets')
    from PySide6.QtWidgets import QApplication
    from desktop.window import BankWindow
    from desktop.client import QueryClient
    qt = QApplication.instance() or QApplication([])
    path = tmp_path / 'native.sqlite3'
    transport = {'client': None, 'lose': True}
    class Opener:
        def open(self, request, timeout=None):
            c = transport['client']
            response = c.request(request.get_method(), request.full_url, content=request.data, headers=dict(request.header_items()))
            response.raise_for_status()
            if request.data and b'"resume"' in request.data and transport['lose']:
                transport['lose'] = False
                raise OSError('response lost after server completed')
            stream = io.BytesIO(response.content)
            stream.headers = Message()
            stream.headers['Content-Type'] = response.headers['content-type']
            return stream
    original = QueryClient.__init__
    def init(self, url):
        original(self, url)
        self.opener = Opener()
    monkeypatch.setattr(QueryClient, '__init__', init)
    def wait(predicate):
        until = time.monotonic() + 15
        while time.monotonic() < until:
            qt.processEvents()
            if predicate():
                return
            time.sleep(.01)
        assert predicate()
    for restart in (False, True):
        model = None if restart else Scripted(batch(), answer('整批已完成。'))
        with bank_app(model, path) as c:
            transport['client'] = c
            window = BankWindow('http://localhost')
            try:
                wait(lambda: not window.busy and window.accounts.count() > 0)
                if not restart:
                    window.send('给张伟40、李娜25，整批办理')
                    wait(lambda: not window.busy and window.pending is not None)
                    assert all(x in window.confirm_text.text() for x in ('张伟', '李娜', '65.00', '全有或全无'))
                    window.approve.click()
                    wait(lambda: not window.busy and window.uncertain)
                    assert balances()[0] == 493500
                    assert not window.approve.isEnabled() and window.retry.isEnabled()
                    window.retry.click()
                    wait(lambda: not window.busy and window.pending is None)
                    assert balances()[0] == 493500
                    wait(lambda: not window.busy and window.batch_receipts.isEnabled())
                window.batch_receipts.click()
                wait(lambda: not window.busy and '批量编号' in window.history.toPlainText())
                text = window.history.toPlainText()
                assert all(x in text for x in ('张伟', '李娜', '40.00', '25.00', '流水', '成功'))
                assert balances()[0] == 493500
            finally:
                window.close()
                window.deleteLater()
                qt.processEvents()
