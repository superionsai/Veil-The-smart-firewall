param(
  [int]$Port = 8080,
  [string]$Model = "ai-hub-models/Qwen3-4B-Instruct-2507"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "Missing .venv. Run .\scripts\setup_snapdragon.ps1 first." }
$env:VEIL_PORT = "$Port"
$env:VEIL_SEMANTIC_PROVIDER = "geniex_direct"
$env:VEIL_SEMANTIC_MODEL = $Model
$env:VEIL_GENIEX_DEVICE_MAP = "qairt"
Write-Host "Starting Veil with direct GenieX/QAIRT model: $Model" -ForegroundColor Green
& .\.venv\Scripts\python.exe -m uvicorn veil.main:app --app-dir backend --host 127.0.0.1 --port $Port
