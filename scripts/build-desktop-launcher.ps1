# Build only the small Windows launcher; Python and PySide6 remain in .venv.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) {
    $compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
}
if (-not (Test-Path -LiteralPath $compiler)) { throw 'The .NET Framework C# compiler is unavailable. Use start-desktop.cmd.' }
& $compiler /nologo /target:winexe /optimize+ /reference:System.Windows.Forms.dll "/win32icon:$root\desktop\assets\youdu-app.ico" "/out:$root\Youdu.exe" "$root\desktop\Launcher.cs"
if ($LASTEXITCODE -ne 0) { throw 'Launcher build failed.' }
Write-Host ('Launcher created: ' + (Join-Path $root 'Youdu.exe'))
