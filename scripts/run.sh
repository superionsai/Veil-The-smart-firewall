#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[ -d .venv ] || { echo "Missing .venv. Run ./scripts/setup.sh"; exit 1; }
. .venv/bin/activate
PORT="${VEIL_PORT:-8080}"
exec python -m uvicorn veil.main:app --app-dir backend --host 127.0.0.1 --port "$PORT"
