param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root '.venv\Scripts\python.exe'
Push-Location $root
try {
    & $py -m uvicorn api.server:create_demo_app --factory --app-dir preparaion --host 127.0.0.1 --port $Port --workers 1 --no-access-log
    if ($LASTEXITCODE -ne 0) { throw 'API 启动失败。' }
} finally {
    Pop-Location
}
