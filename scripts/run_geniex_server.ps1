param(
  [int]$Port = 8080,
  [string]$Model = "ai-hub-models/Qwen3-4B-Instruct-2507",
  [string]$BaseUrl = "http://127.0.0.1:18181/v1"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:VEIL_PORT = "$Port"
$env:VEIL_SEMANTIC_PROVIDER = "geniex_server"
$env:VEIL_SEMANTIC_MODEL = $Model
$env:VEIL_GENIEX_BASE_URL = $BaseUrl
Write-Host "Expecting GenieX local server at $BaseUrl" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m uvicorn veil.main:app --app-dir backend --host 127.0.0.1 --port $Port
