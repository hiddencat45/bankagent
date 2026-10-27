@echo off
if not exist "%~dp0.venv\Scripts\pythonw.exe" (
  echo Please run scripts\setup-desktop.ps1 first.
  pause
  exit /b 1
)
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0desktop\app.py" --preview
