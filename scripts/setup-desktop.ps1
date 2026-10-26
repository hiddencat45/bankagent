param([string]$Mirror = 'https://pypi.tuna.tsinghua.edu.cn/simple')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'setup.ps1') -Mirror $Mirror
if ($LASTEXITCODE -ne 0) { exit 1 }
& (Join-Path $root '.venv/Scripts/python.exe') -m pip install -r (Join-Path $root 'requirements-desktop.txt') -i $Mirror --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host 'Desktop ready. Double-click start-desktop.cmd.'
