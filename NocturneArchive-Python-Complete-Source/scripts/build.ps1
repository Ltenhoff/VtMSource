$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $Python = "py -3" }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $Python = "python" }
else { throw "Python 3 was not found. Run scripts\bootstrap-and-build.cmd instead." }

if (-not (Test-Path ".venv")) { Invoke-Expression "$Python -m venv .venv" }
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
& $VenvPython -m PyInstaller --noconfirm NocturneArchive.spec
Write-Host ""
Write-Host "Built: $Root\dist\NocturneArchive.exe" -ForegroundColor Green
