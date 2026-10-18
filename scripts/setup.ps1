# 一键搭建开发环境：建 venv、升级 pip、按锁定版本装依赖
#
# 用法：
#   .\scripts\setup.ps1
#   .\scripts\setup.ps1 -Mirror "https://mirrors.aliyun.com/pypi/simple/"
#
# 这个脚本把两个坑封装掉了：
#   1. Python 3.10 自带的 pip 22.3.1 在解析 langgraph 依赖时会疯狂回溯，
#      表现为 CPU 跑满、缓存几百 MB、但一个包都装不上。必须先升级 pip。
#   2. 国内直连 PyPI 极慢，默认走清华镜像。

param(
    [string]$Mirror = "https://pypi.tuna.tsinghua.edu.cn/simple"
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root '.venv'
$py   = Join-Path $venv 'Scripts\python.exe'

Write-Host "项目根目录: $root" -ForegroundColor Cyan
Write-Host ""

# ---- 1. 虚拟环境 ----
if (-not (Test-Path $py)) {
    Write-Host "[1/3] 创建虚拟环境 .venv" -ForegroundColor Cyan
    python -m venv $venv
    if (-not (Test-Path $py)) { Write-Host "创建失败，请确认 python 在 PATH 中" -ForegroundColor Red; exit 1 }
} else {
    Write-Host "[1/3] 虚拟环境已存在，跳过" -ForegroundColor DarkGray
}

# ---- 2. 升级 pip（关键步骤）----
Write-Host "[2/3] 升级 pip（旧版 pip 会在 langgraph 上回溯卡死，这步不能省）" -ForegroundColor Cyan
& $py -m pip install --upgrade pip -i $Mirror --quiet --disable-pip-version-check
& $py -m pip --version

# ---- 3. 安装依赖 ----
Write-Host "[3/3] 安装锁定版本的依赖" -ForegroundColor Cyan
& $py -m pip install -r (Join-Path $root 'requirements.txt') -i $Mirror --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Write-Host "依赖安装失败" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "环境就绪。验证一下：.\scripts\check.ps1" -ForegroundColor Green
