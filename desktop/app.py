"""Windows desktop entry; the local service lives only as long as its window."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
MODEL_SETTINGS = ('API_KEY', 'BASE_URL', 'NAME', 'TIMEOUT', 'MAX_TOKENS', 'THINKING')


def desktop_environment():
    env = os.environ.copy()
    if sys.platform == 'win32':
        import winreg
        # Explorer may still carry the environment from before configuration.
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
            for suffix in MODEL_SETTINGS:
                name = 'BANKAGENT_MODEL_' + suffix
                if not env.get(name):
                    try:
                        value, _ = winreg.QueryValueEx(key, name)
                        env[name] = str(value)
                    except FileNotFoundError:
                        pass
    env['BANKAGENT_DEMO_ALLOW_LAN'] = '0'
    return env


def serve(ready_file):
    # A broken parent pipe also cleans up after a crashed desktop process.
    def watch_parent():
        sys.stdin.buffer.read()
        os._exit(0)

    threading.Thread(target=watch_parent, daemon=True).start()
    sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
    import uvicorn
    from frontend.dev_app import create_app

    os.environ['BANKAGENT_DEMO_ALLOW_LAN'] = '0'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        config = uvicorn.Config(create_app(), log_config=None, access_log=False)
        Path(ready_file).write_text(json.dumps({'port': sock.getsockname()[1]}))
        uvicorn.Server(config).run(sockets=[sock])


class LocalService:
    def __init__(self, *, env=None, timeout=30):
        self.env = env
        self.timeout = timeout
        self.process = None
        self.temp = None

    def start(self):
        self.temp = tempfile.TemporaryDirectory(prefix='bankagent-')
        ready = Path(self.temp.name) / 'ready.json'
        try:
            self.process = subprocess.Popen(
                [str(Path(sys.executable).with_name('python.exe')) if sys.platform == 'win32'
                 else sys.executable, str(Path(__file__).resolve()), '--serve', str(ready)],
                cwd=ROOT, env=self.env if self.env is not None else desktop_environment(),
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            )
            opener = build_opener(ProxyHandler({}))
            deadline = time.monotonic() + self.timeout
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise RuntimeError('本地服务启动失败，请检查依赖与 BANKAGENT_MODEL_* 配置。')
                try:
                    port = json.loads(ready.read_text())['port']
                    url = f'http://127.0.0.1:{port}'
                    with opener.open(url + '/health', timeout=0.5) as response:
                        if response.status == 200:
                            return url
                except (OSError, ValueError, KeyError):
                    pass
                time.sleep(0.1)
            raise RuntimeError('本地服务启动超时，请关闭后重试。')
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
    args = parser.parse_args()
    if args.serve:
        serve(args.serve)
        return
    service = LocalService()
    try:
        from PySide6.QtWidgets import QApplication
        sys.path.insert(0, str(ROOT))
        from desktop.window import BankWindow

        app = QApplication(sys.argv[:1])
        url = service.start()
        window = BankWindow(url)
        window.show()
        app.exec()
    except Exception:
        # Provider exceptions and URLs can contain secrets; never show raw errors.
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, '启动失败。请先运行 scripts/setup-desktop.ps1，'
            '并检查 BANKAGENT_MODEL_* 配置。', '有度', 0x10)
    finally:
        service.close()


if __name__ == '__main__':
    main()
