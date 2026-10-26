"""Optional native-widget regressions; offscreen, never takes desktop focus."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
pytest.importorskip('PySide6.QtWidgets')
from PySide6.QtWidgets import QApplication
from desktop.window import BankWindow, QTimer


def test_reconnect_available_after_initial_failure(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QTimer, 'singleShot', lambda *args: None)
    window = BankWindow('http://127.0.0.1')
    window.receive('error', '会话建立失败')
    assert window.reconnect.isEnabled()
    assert not window.submit.isEnabled()
    assert not window.new.isEnabled()
    window.client.token = 'test-token'
    window.thread = 'old-thread'
    window.receive('connect', 'offline')
    assert not window.blocked
    assert window.thread is None
    assert window.submit.isEnabled()
    assert window.mode == '离线规则'
    window.close()
    window.deleteLater()
    app.processEvents()
