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
Write-Host "=== 1/4 测试 ===" -ForegroundColor Cyan
Push-Location $root
& $py -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Host "测试未通过" -ForegroundColor Red; $fail++ }
Pop-Location

# ---- 2. 前端测试 ----
# 之前门禁只跑 pytest，frontend 的 .mjs 测试根本没被调用：前端改坏了照样显示绿。
# 这里补上。前端源码在 #16 合并前还不在 main，所以做成"有就跑、没有就明说跳过"，
# 避免同一个脚本在 main 和分支上行为不一致。
# 前端测试存在时 node 是硬要求：缺了就算失败，不能静默跳过。
Write-Host "=== 2/4 前端测试 ===" -ForegroundColor Cyan
$feTestDir = Join-Path $root 'frontend\tests'
$feTests = @(Get-ChildItem -Path $feTestDir -Recurse -Filter *.test.mjs -ErrorAction SilentlyContinue)
if ($feTests.Count -eq 0) {
    Write-Host "跳过：frontend 下没有测试文件（main 尚无前端源码）" -ForegroundColor DarkGray
} else {
    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    if (-not $nodeCmd) {
        Write-Host "有前端测试但找不到 node，无法验证前端" -ForegroundColor Red
        $fail++
    } else {
        Write-Host ("node: " + (& node --version))
        Push-Location (Join-Path $root 'frontend')
        & node --test @($feTests.FullName)
        if ($LASTEXITCODE -ne 0) { Write-Host "前端测试未通过" -ForegroundColor Red; $fail++ }
        Pop-Location
    }
}

# ---- 3. 敏感字段扫描（提示性质，不直接判失败）----
# 教学代码里合法地存在 demo-otp-ok 这类占位符，所以这里只报告、交给人判断，
# 不自动判失败——一个永远失败的门禁等于没有门禁。
Write-Host "=== 3/4 敏感字段扫描（人工确认）===" -ForegroundColor Cyan
$scanPaths = @((Join-Path $root 'src'), (Join-Path $root 'tests'), (Join-Path $root 'frontend')) | Where-Object { Test-Path $_ }
$pyFiles = Get-ChildItem -Path $scanPaths -Recurse -Filter *.py -ErrorAction SilentlyContinue
$hits = $pyFiles | Select-String -Pattern 'demo-otp-ok|password\s*=\s*["'']|secret\s*=\s*["'']|api[_-]?key\s*=\s*["'']' -ErrorAction SilentlyContinue
if ($hits) {
    Write-Host "发现以下疑似硬编码，请人工确认是否属于教学占位符：" -ForegroundColor Yellow
    $hits | ForEach-Object { '  {0}:{1}  {2}' -f (Split-Path $_.Path -Leaf), $_.LineNumber, $_.Line.Trim() }
} else {
    Write-Host "无发现" -ForegroundColor DarkGray
}

# ---- 4. 依赖完整性 ----
Write-Host "=== 4/4 依赖完整性 ===" -ForegroundColor Cyan
& $py -m pip check
if ($LASTEXITCODE -ne 0) { Write-Host "依赖有冲突" -ForegroundColor Red; $fail++ }

Write-Host ""
if ($fail -gt 0) {
    Write-Host "门禁未通过（$fail 项）" -ForegroundColor Red
    exit 1
}
Write-Host "门禁通过" -ForegroundColor Green
exit 0
