"""Startup failures preserve ledgers; success reopens the exact configured file."""
import hashlib
from pathlib import Path
import sqlite3

import pytest

from desktop.app import LocalService
from desktop.startup import StartupError, prepare_database
from test_desktop import offline_env


def test_unwritable_directory_stops_before_spawn(tmp_path, monkeypatch):
    import desktop.startup as startup
    import desktop.app as entry
    original = tmp_path / 'original.sqlite3'
    original.write_bytes(b'unchanged ledger')
    def denied(*args, **kwargs):
        raise PermissionError('private error details')
    monkeypatch.setattr(startup.tempfile, 'TemporaryFile', denied)
    monkeypatch.setattr(entry.subprocess, 'Popen', lambda *a, **k: pytest.fail('must not start service'))
    service = LocalService(env={**offline_env(), 'BANKAGENT_DB_PATH': str(original)})
    with pytest.raises(StartupError) as caught:
        service.start()
    assert caught.value.code == 'DATA_ACCESS'
    assert str(original) in str(caught.value)
    assert 'private error details' not in str(caught.value)
    assert 'MODEL' not in str(caught.value)
    assert original.read_bytes() == b'unchanged ledger'
    assert list(tmp_path.iterdir()) == [original]
    assert service.process is None and service.temp is None


@pytest.mark.parametrize('kind', ['parent_file', 'directory', 'corrupt', 'empty', 'unknown_version'])
def test_bad_database_is_not_replaced(tmp_path, kind):
    target = tmp_path / 'bank.sqlite3'
    if kind == 'parent_file':
        target.write_bytes(b'keep')
        configured = target / 'nested.sqlite3'
    elif kind == 'directory':
        target.mkdir()
        configured = target
    else:
        configured = target
        target.write_bytes(b'not sqlite' if kind == 'corrupt' else b'')
        if kind == 'unknown_version':
            with sqlite3.connect(target) as db:
                db.execute('CREATE TABLE bank_state (id INTEGER, version INTEGER, data TEXT, receipts TEXT, created_at TEXT)')
                db.execute("INSERT INTO bank_state VALUES (1,999,'{}','[]','2026-10-27T00:00:00+00:00')")
    before = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
    service = LocalService(env={**offline_env(), 'BANKAGENT_DB_PATH': str(configured)})
    with pytest.raises(StartupError) as caught:
        service.start()
    assert caught.value.code == ('DATA_PATH' if kind in {'parent_file', 'directory'} else 'DATA_INVALID')
    assert str(configured) in str(caught.value)
    if before:
        assert hashlib.sha256(target.read_bytes()).hexdigest() == before
    assert list(tmp_path.iterdir()) == [target]
    assert service.process is None and service.temp is None


def test_model_configuration_failure_is_not_database_failure(tmp_path):
    target = tmp_path / 'bank.sqlite3'
    env = {**offline_env(), 'BANKAGENT_DB_PATH': str(target),
           'BANKAGENT_MODEL_API_KEY': 'test-only-secret', 'BANKAGENT_MODEL_TIMEOUT': 'bad'}
    service = LocalService(env=env)
    with pytest.raises(StartupError) as caught:
        service.start()
    assert caught.value.code == 'MODEL_CONFIG'
    assert 'test-only-secret' not in str(caught.value)
    assert not target.exists()


def test_relative_path_does_not_follow_launch_directory(tmp_path, monkeypatch):
    root = tmp_path / 'checkout'
    root.mkdir()
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    original = root / 'original.sqlite3'
    original.write_bytes(b'preserve')
    monkeypatch.chdir(elsewhere)
    env = {'BANKAGENT_DB_PATH': 'original.sqlite3'}
    assert prepare_database(env, root) == original
    assert env['BANKAGENT_DB_PATH'] == str(original)
    assert not list(elsewhere.iterdir())
    assert original.read_bytes() == b'preserve'


def test_desktop_entry_reopens_same_ledger(tmp_path, monkeypatch):
    """Run the real main()/widgets/service twice; only the event-loop driver is replaced."""
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6.QtWidgets')
    from PySide6.QtWidgets import QApplication
    import desktop.app as entry
    from desktop.window import BankWindow
    from test_desktop_transfer import receipt
    import time

    original = tmp_path / 'original.sqlite3'
    env = {**offline_env(), 'BANKAGENT_DB_PATH': str(original)}
    seed = LocalService(env=env)
    from desktop.client import QueryClient, business_confirmation
    try:
        client = QueryClient(seed.start())
        client.connect()
        pending = business_confirmation(client.query('给张伟转40元'))
        assert receipt(client.resume(pending, 'approve'))['data']['remaining_balance_minor'] == 496000
    finally:
        seed.close()
    before = original.read_bytes()
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(entry, 'desktop_environment', lambda: dict(env))
    monkeypatch.setattr(entry.sys, 'argv', ['desktop/app.py'])
    monkeypatch.setattr('PySide6.QtWidgets.QApplication', lambda *args: app)
    def drive():
        window = next(w for w in app.topLevelWidgets() if isinstance(w, BankWindow) and w.isVisible())
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and (window.busy or not window.client.token):
            app.processEvents()
            time.sleep(.01)
        assert window.client.token
        assert str(original) in window.statusBar().currentMessage()
        assert receipt(window.client.query('查询余额'))['data']['balance_minor'] == 496000
        window.close()
        window.deleteLater()
        app.processEvents()
        return 0
    monkeypatch.setattr(app, 'exec', drive)
    # Fail the test instead of opening a real native error message box on regression.
    import ctypes
    if hasattr(ctypes, 'windll'):
        monkeypatch.setattr(ctypes.windll.user32, 'MessageBoxW', lambda *a: pytest.fail(a[1]))
    for _ in range(2):
        entry.main()
        assert original.read_bytes() == before
