"""Local startup diagnostics. Never forward raw provider errors or change ledgers."""
from pathlib import Path
import sqlite3
import tempfile


MESSAGES = {
    'DATA_ACCESS': '无法读写账本文件或其目录。请检查该路径的读写权限、文件占用及磁盘状态。',
    'DATA_PATH': '账本路径无效：目录位置被文件占用，或账本位置是目录。请核对原账本路径。',
    'DATA_INVALID': '账本无法读取：格式损坏、版本不兼容或数据不完整。请使用兼容版本或从备份恢复原账本；不要删除文件重试。',
    'DATA_BUSY': '账本正被其他程序占用。请结束占用后重新打开。',
    'DATA_FULL': '保存账本所需的磁盘空间不足。请释放空间后重新打开。',
    'MODEL_CONFIG': '模型配置不完整或无效。请检查 BANKAGENT_MODEL_* 环境变量。',
    'DEPENDENCY': '启动依赖缺失或无法加载。请运行 scripts/setup-desktop.ps1 后重试。',
    'TIMEOUT': '本地服务启动超时。请关闭本次应用后重试。',
    'SERVICE': '本地服务启动失败。请检查应用依赖与本机服务环境。',
}


class StartupError(RuntimeError):
    def __init__(self, code, path=None):
        self.code = code if code in MESSAGES else 'SERVICE'
        message = '启动失败。' + MESSAGES[self.code]
        if path:
            message += '\n\n当前账本：' + str(path)
        if self.code.startswith('DATA_'):
            message += ('\n\n应用未切换账本，也未清空或重建原数据。'
                        '如需使用已有账本，请将 BANKAGENT_DB_PATH 明确设置为原文件的绝对路径。')
        super().__init__(message)


def prepare_database(env, root):
    """Resolve once before spawning; probe write access without changing an existing file."""
    raw = env.get('BANKAGENT_DB_PATH')
    if not raw:  # Explicit test/service environments can still request an in-memory backend.
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = root / path
    try:
        path = path.resolve()
        env['BANKAGENT_DB_PATH'] = str(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            raise StartupError('DATA_PATH', path)
        # SQLite needs directory access for its transaction journal as well as file access.
        with tempfile.TemporaryFile(dir=path.parent) as probe:
            probe.write(b'bankagent startup check')
            probe.flush()
        if path.exists():
            with path.open('r+b'):
                pass
    except (FileExistsError, NotADirectoryError, IsADirectoryError):
        raise StartupError('DATA_PATH', path) from None
    except OSError:
        raise StartupError('DATA_ACCESS', path) from None
    return path


def database_error(exc):
    # Python 3.10 lacks sqlite_errorcode. Match only known SQLite messages internally;
    # never expose an exception's raw text (or a provider's details) to the user.
    if isinstance(exc, sqlite3.OperationalError):
        return {
            'database is locked': 'DATA_BUSY',
            'database table is locked': 'DATA_BUSY',
            'database or disk is full': 'DATA_FULL',
            'attempt to write a readonly database': 'DATA_ACCESS',
            'unable to open database file': 'DATA_ACCESS',
        }.get(str(exc), 'DATA_ACCESS')
    if isinstance(exc, OSError):
        return 'DATA_ACCESS'
    return 'DATA_INVALID'
