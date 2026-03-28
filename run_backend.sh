#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BIN="$ROOT_DIR/.venv/bin"
UVICORN_CMD="$VENV_BIN/uvicorn"

cd "$ROOT_DIR"

if [[ ! -x "$UVICORN_CMD" ]]; then
  echo "[run_backend] uvicorn not found at $UVICORN_CMD"
  echo "  Run: python3.11 -m venv .venv && source .venv/bin/activate && pip install -r papertrail_backend/requirements.txt"
  exit 1
fi

# Ensure upload directory exists
mkdir -p "$ROOT_DIR/papertrail_backend/uploads"

echo "[run_backend] Stopping existing uvicorn processes..."
PIDS=$(ps -ef | grep "[u]vicorn .*papertrail_backend" | awk '{print $2}' || true)
if [[ -n "${PIDS:-}" ]]; then
  for pid in $PIDS; do
    echo "  - killing PID $pid"
    kill "$pid" || true
  done
else
  echo "  - none running"
fi

echo "[run_backend] Starting PaperTrail backend on http://127.0.0.1:8000"
PYTHONPATH="$ROOT_DIR" exec "$UVICORN_CMD" papertrail_backend.main:app --host 0.0.0.0 --port 8000 --reload
