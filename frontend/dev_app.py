"""本地工作台入口：复用 A 的真实 Demo API，仅挂载前端静态文件。"""
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from bankagent.api.server import create_demo_app


def create_app():
    app = create_demo_app()
    app.mount('/', StaticFiles(directory=Path(__file__).parent, html=True), name='workbench')
    return app
