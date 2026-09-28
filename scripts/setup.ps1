param(
  [switch]$InstallRapidOCR,
  [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[Veil] Generic setup" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python 3.11+ was not found on PATH. Install Python and rerun this script."
}

$pyVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Python $pyVersion"

if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip wheel setuptools
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

if ($InstallRapidOCR) {
  Write-Host "Installing optional RapidOCR backend..." -ForegroundColor Yellow
  & .\.venv\Scripts\python.exe -m pip install "rapidocr-onnxruntime>=1.3.24"
}

if (-not $SkipTests) {
  & .\.venv\Scripts\python.exe -m pytest
}

& .\.venv\Scripts\python.exe scripts\check_environment.py

Write-Host "`nSetup complete. Run .\scripts\run.ps1" -ForegroundColor Green
Write-Host "If OCR reports 'none', install a local Tesseract executable or use -InstallRapidOCR where supported." -ForegroundColor Yellow
