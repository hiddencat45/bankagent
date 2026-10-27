# Generate a machine-local shortcut; never commit its absolute paths.
param([string]$Destination)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $Destination) { $Destination = Join-Path $root 'Youdu.lnk' }
$python = Join-Path $root '.venv\Scripts\pythonw.exe'
$icon = Join-Path $root 'desktop\assets\youdu-app.ico'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run scripts/setup-desktop.ps1 first.' }
if (-not (Test-Path -LiteralPath $icon)) { throw 'Application icon is missing.' }
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut([System.IO.Path]::GetFullPath($Destination))
$shortcut.TargetPath = $python
$shortcut.Arguments = '"' + (Join-Path $root 'desktop\app.py') + '"'
$shortcut.WorkingDirectory = $root
$shortcut.IconLocation = $icon + ',0'
$shortcut.Description = 'Youdu - local banking assistant'
$shortcut.Save()
Write-Host ('Shortcut created: ' + $Destination)
