$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Tools = Join-Path $Root ".tools"
$PyDir = Join-Path $Tools "python"
$Installer = Join-Path $Tools "python-installer.exe"
$Python = Join-Path $PyDir "python.exe"
New-Item -ItemType Directory -Force -Path $Tools | Out-Null

if (-not (Test-Path $Python)) {
    $Url = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    Write-Host "Downloading the official Python compiler/runtime..."
    Invoke-WebRequest -Uri $Url -OutFile $Installer
    Start-Process -FilePath $Installer -ArgumentList "/quiet InstallAllUsers=0 PrependPath=0 Include_test=0 TargetDir=`"$PyDir`"" -Wait
}

Set-Location $Root
if (-not (Test-Path ".venv")) { & $Python -m venv .venv }
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
& $VenvPython -m PyInstaller --noconfirm NocturneArchive.spec
Write-Host ""
Write-Host "Built: $Root\dist\NocturneArchive.exe" -ForegroundColor Green
