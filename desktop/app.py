"""Windows desktop entry; the local service lives only as long as its window."""
import argparse
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.startup import StartupError, database_error, prepare_database
MODEL_SETTINGS = ('API_KEY', 'BASE_URL', 'NAME', 'TIMEOUT', 'MAX_TOKENS', 'THINKING')


def desktop_environment():
    env = os.environ.copy()
    if sys.platform == 'win32':
        import winreg
        # Explorer may still carry the environment from before configuration.
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
            for name in ['BANKAGENT_MODEL_' + suffix for suffix in MODEL_SETTINGS] + ['BANKAGENT_DB_PATH']:
                if not env.get(name):
                    try:
                        value, _ = winreg.QueryValueEx(key, name)
                        env[name] = str(value)
                    except FileNotFoundError:
                        pass
    env['BANKAGENT_DEMO_ALLOW_LAN'] = '0'
    if not env.get('BANKAGENT_DB_PATH'):
        base = Path(env.get('LOCALAPPDATA') or (Path.home() / '.local' / 'share'))
        env['BANKAGENT_DB_PATH'] = str(base / 'BankAgent' / 'bankagent.sqlite3')
    return env


def serve(ready_file):
    # A broken parent pipe also cleans up after a crashed desktop process.
    def watch_parent():
        sys.stdin.buffer.read()
        os._exit(0)

    threading.Thread(target=watch_parent, daemon=True).start()
    sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
    error_file = Path(ready_file).with_suffix('.error.json')
    def report(code):
        # Only a fixed category crosses the process boundary; no URLs, keys or tracebacks.
        error_file.write_text(json.dumps({'code': code}), encoding='utf-8')

    try:
        import uvicorn
        from frontend.dev_app import create_app
        from bankagent.agent.model_providers import ProviderConfigError
    except ImportError:
        report('DEPENDENCY')
        return

    try:
        os.environ['BANKAGENT_DEMO_ALLOW_LAN'] = '0'
        application = create_app()
    except ProviderConfigError:
        report('MODEL_CONFIG')
        return
    except (OSError, sqlite3.Error, ValueError) as exc:
        report(database_error(exc) if os.environ.get('BANKAGENT_DB_PATH') else 'SERVICE')
        return
    except Exception:
        report('SERVICE')
        return

    os.environ['BANKAGENT_DEMO_ALLOW_LAN'] = '0'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        config = uvicorn.Config(application, log_config=None, access_log=False)
        Path(ready_file).write_text(json.dumps({'port': sock.getsockname()[1]}))
        uvicorn.Server(config).run(sockets=[sock])


class LocalService:
    def __init__(self, *, env=None, timeout=30):
        self.env = env
        self.timeout = timeout
        self.process = None
        self.temp = None
        self.database_path = None

    def start(self):
        self.temp = tempfile.TemporaryDirectory(prefix='bankagent-')
        ready = Path(self.temp.name) / 'ready.json'
        try:
            env = dict(self.env) if self.env is not None else desktop_environment()
            self.database_path = prepare_database(env, ROOT)
            self.process = subprocess.Popen(
                [str(Path(sys.executable).with_name('python.exe')) if sys.platform == 'win32'
                 else sys.executable, str(Path(__file__).resolve()), '--serve', str(ready)],
                cwd=ROOT, env=env,
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            )
            opener = build_opener(ProxyHandler({}))
            deadline = time.monotonic() + self.timeout
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    code = 'SERVICE'
                    try:
                        code = json.loads(ready.with_suffix('.error.json').read_text(encoding='utf-8'))['code']
                    except (OSError, ValueError, KeyError):
                        pass
                    raise StartupError(code, self.database_path)
                try:
                    port = json.loads(ready.read_text())['port']
                    url = f'http://127.0.0.1:{port}'
                    with opener.open(url + '/health', timeout=0.5) as response:
                        if response.status == 200:
                            return url
                except (OSError, ValueError, KeyError):
                    pass
                time.sleep(0.1)
            raise StartupError('TIMEOUT', self.database_path)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.process is not None:
            if self.process.stdin is not None:
                self.process.stdin.close()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
            self.process = None
        if self.temp is not None:
            self.temp.cleanup()
            self.temp = None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', metavar='READY_FILE')
    parser.add_argument('--preview', action='store_true', help='Compatibility alias for the default native workspace')
    parser.add_argument('--legacy', action='store_true', help='Use the previous native layout')
    parser.add_argument('--demo', action='store_true', help='Explicit developer demo identities; no password login')
    args = parser.parse_args()
    if args.serve:
        serve(args.serve)
        return
    env = desktop_environment()
    env['BANKAGENT_LOCAL_LOGIN'] = '0' if args.demo else '1'
    service = LocalService(env=env)
    try:
        from PySide6.QtWidgets import QApplication
        sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
        from desktop.window import BankWindow

        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Youdu.BankAgent.Desktop')
        app = QApplication(sys.argv[:1])
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(str(ROOT / 'desktop' / 'assets' / 'youdu-app.ico')))
        url = service.start()
        if not args.demo:
            from desktop.login import LoginWindow
            window = LoginWindow(url, str(service.database_path))
        elif not args.legacy:
            from desktop.preview import PreviewWindow
            window = PreviewWindow(url, startup_customer='zhang-wei')
        else:
            window = BankWindow(url, startup_customer='zhang-wei')
        if args.demo:
            window.statusBar().showMessage('当前账本：' + str(service.database_path))
            window.statusBar().setToolTip('当前账本：' + str(service.database_path))
        window.show()
        app.exec()
    except Exception as exc:
        # Provider exceptions and URLs can contain secrets; never show raw errors.
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, str(exc) if isinstance(exc, StartupError) else
            str(StartupError('DEPENDENCY' if isinstance(exc, ImportError) else 'SERVICE')),
            '有度 · 启动失败', 0x10)
    finally:
        service.close()


if __name__ == '__main__':
    main()
