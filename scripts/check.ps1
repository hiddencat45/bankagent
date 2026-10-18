# 一键门禁：说"做完了"之前必须跑通这个脚本
#
# 用法：
#   .\scripts\check.ps1
#
# 退出码 0 = 通过，非 0 = 有项目没过。AI 助手不得在门禁未通过时声称任务完成。

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$py   = Join-Path $root '.venv\Scripts\python.exe'
$fail = 0

if (-not (Test-Path $py)) {
    Write-Host "找不到 .venv，先跑 .\scripts\setup.ps1" -ForegroundColor Red
    exit 1
}

# ---- 1. 测试 ----
Write-Host "=== 1/3 测试 ===" -ForegroundColor Cyan
Push-Location (Join-Path $root 'preparaion')
& $py -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Host "测试未通过" -ForegroundColor Red; $fail++ }
Pop-Location

# ---- 2. 敏感字段扫描（提示性质，不直接判失败）----
# 教学代码里合法地存在 demo-otp-ok 这类占位符，所以这里只报告、交给人判断，
# 不自动判失败——一个永远失败的门禁等于没有门禁。
Write-Host "=== 2/3 敏感字段扫描（人工确认）===" -ForegroundColor Cyan
$pyFiles = Get-ChildItem -Path (Join-Path $root 'preparaion') -Recurse -Filter *.py -ErrorAction SilentlyContinue
$hits = $pyFiles | Select-String -Pattern 'demo-otp-ok|password\s*=\s*["'']|secret\s*=\s*["'']|api[_-]?key\s*=\s*["'']' -ErrorAction SilentlyContinue
if ($hits) {
    Write-Host "发现以下疑似硬编码，请人工确认是否属于教学占位符：" -ForegroundColor Yellow
    $hits | ForEach-Object { '  {0}:{1}  {2}' -f (Split-Path $_.Path -Leaf), $_.LineNumber, $_.Line.Trim() }
} else {
    Write-Host "无发现" -ForegroundColor DarkGray
}

# ---- 3. 依赖完整性 ----
Write-Host "=== 3/3 依赖完整性 ===" -ForegroundColor Cyan
& $py -m pip check
if ($LASTEXITCODE -ne 0) { Write-Host "依赖有冲突" -ForegroundColor Red; $fail++ }

Write-Host ""
if ($fail -gt 0) {
    Write-Host "门禁未通过（$fail 项）" -ForegroundColor Red
    exit 1
}
Write-Host "门禁通过" -ForegroundColor Green
exit 0
