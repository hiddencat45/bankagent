"""The installed launcher entry must not rely on pytest's src path injection."""
import os
from pathlib import Path
import subprocess
import sys
import pytest


@pytest.mark.skipif(os.name!='nt',reason='Windows desktop launcher')
def test_clean_desktop_entry_loads_login_with_wealth_module(tmp_path):
    root=Path(__file__).resolve().parents[1]
    probe=tmp_path/'entry_probe.py'
    probe.write_text('''import ctypes, os, runpy, sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
namespace=runpy.run_path(sys.argv[1])
entry=namespace['main']
entry.__globals__['desktop_environment']=lambda: dict(os.environ)
sys.argv=[sys.argv[1]]
seen=[]
original=QApplication.exec
def execute(app):
    assert any(w.__class__.__name__=='LoginWindow' for w in app.topLevelWidgets())
    seen.append(True)
    QTimer.singleShot(50,app.quit)
    return original()
def startup_failure(*args):
    raise RuntimeError('Desktop entry failed')
ctypes.windll.user32.MessageBoxW=startup_failure
QApplication.exec=execute
entry()
assert seen
''',encoding='utf-8')
    env={k:v for k,v in os.environ.items() if not k.startswith('BANKAGENT_') and k!='PYTHONPATH'}
    env.update(QT_QPA_PLATFORM='offscreen',BANKAGENT_DB_PATH=str(tmp_path/'entry.sqlite3'))
    result=subprocess.run([sys.executable,str(probe),str(root/'desktop'/'app.py')],cwd=tmp_path,
                          env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
