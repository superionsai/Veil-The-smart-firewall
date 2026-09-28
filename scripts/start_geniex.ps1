param(
  [string]$Model = "ai-hub-models/Qwen3-4B-Instruct-2507",
  [switch]$SkipPull
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Geniex = ".\.venv\Scripts\geniex.exe"
if (-not (Test-Path $Geniex)) { throw "GenieX not found. Run .\scripts\setup_snapdragon.ps1 first." }
if (-not $SkipPull) { & $Geniex pull $Model }
Write-Host "Starting local GenieX server on 127.0.0.1:18181. Keep this terminal open." -ForegroundColor Green
& $Geniex serve
