param(
  [int]$Port = 8080
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "Missing .venv. Run .\scripts\setup.ps1 first." }
$env:VEIL_PORT = "$Port"
& .\.venv\Scripts\python.exe -m uvicorn veil.main:app --app-dir backend --host 127.0.0.1 --port $Port
