param(
  [switch]$SkipModelPull,
  [switch]$SkipTests,
  [string]$Model = "ai-hub-models/Qwen3-4B-Instruct-2507"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[Veil] Snapdragon Windows ARM64 setup" -ForegroundColor Cyan
Write-Host "Architecture: $env:PROCESSOR_ARCHITECTURE"

$arch = (& python -c "import platform; print(platform.machine().lower())" 2>$null)
if ($LASTEXITCODE -ne 0) {
  throw "Python was not found. Install native Windows ARM64 Python 3.11+ first."
}
if ($arch -notin @("arm64","aarch64")) {
  Write-Warning "Python reports architecture '$arch'. For direct GenieX use native ARM64 Python on the Snapdragon PC."
}

$versionOk = (& python -c "import sys; print(int(sys.version_info >= (3,11)))")
if ($versionOk -ne "1") { throw "Python 3.11 or newer is required." }

if (-not (Test-Path ".venv")) { python -m venv .venv }
$Py = ".\.venv\Scripts\python.exe"

& $Py -m pip install --upgrade pip wheel setuptools
# Core dependencies are intentionally OpenCV-free so this environment remains
# native ARM64. Pillow/PyMuPDF/NumPy handle the image/document path.
& $Py -m pip install -r requirements.txt
# Small development/demo extras only; do not pull the generic optional OpenCV wheel.
& $Py -m pip install "pytest>=8,<10" "qrcode[pil]>=8,<9"

Write-Host "Installing Qualcomm GenieX..." -ForegroundColor Cyan
& $Py -m pip install geniex

if (-not $SkipModelPull) {
  Write-Host "Pulling $Model ..." -ForegroundColor Cyan
  $Geniex = ".\.venv\Scripts\geniex.exe"
  if (Test-Path $Geniex) {
    & $Geniex pull $Model
  } else {
    Write-Warning "geniex.exe was not found in .venv\Scripts. Check: .\.venv\Scripts\python.exe -m pip show geniex"
  }
}

# Tesseract may be an x64 desktop executable on Windows ARM; that is acceptable
# because Veil invokes it as a child process. The Python application remains ARM64.
$commonTesseract = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if (-not (Get-Command tesseract -ErrorAction SilentlyContinue) -and -not (Test-Path $commonTesseract)) {
  Write-Warning "Tesseract executable not found. Install Tesseract or configure VEIL_OCR_PROVIDER=rapidocr if a compatible ARM64 ONNX Runtime is available."
  Write-Warning "You can point Veil at a non-PATH installation with: `$env:TESSERACT_CMD='C:\path\to\tesseract.exe'"
}

$env:VEIL_SEMANTIC_PROVIDER = "heuristic"
if (-not $SkipTests) { & $Py -m pytest }
& $Py scripts\check_environment.py

Write-Host "`nSnapdragon setup complete." -ForegroundColor Green
Write-Host "Run .\scripts\run_snapdragon.ps1 for direct QAIRT/NPU semantic inference." -ForegroundColor Green
