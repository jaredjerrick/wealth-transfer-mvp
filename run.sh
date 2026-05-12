#!/usr/bin/env bash
# Single-command bootstrapper for the wealth-transfer MVP.
# Starts the FastAPI backend on :8000 and the Next.js frontend on :3000.
#
# Backend-only mode: pass --backend-only to skip the Next.js install/dev step.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

BACKEND_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --backend-only) BACKEND_ONLY=1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
echo "▶ Installing backend deps..."
if pip install -e "$BACKEND[dev]" >/tmp/wte-pip.log 2>&1; then
  echo "  ✓ Editable install ok."
else
  echo "  ! Editable install failed (see /tmp/wte-pip.log). Falling back to direct deps."
  pip install pydantic fastapi 'uvicorn[standard]' reportlab httpx pytest pytest-asyncio
fi

echo "▶ Running engine tests..."
( cd "$BACKEND" && python -m pytest tests/ -q )

echo "▶ Starting backend on http://localhost:8000 ..."
( cd "$BACKEND" && python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload ) &
BACKEND_PID=$!

trap 'kill $BACKEND_PID 2>/dev/null || true; [[ -n "${FRONTEND_PID:-}" ]] && kill $FRONTEND_PID 2>/dev/null || true' EXIT INT TERM

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
if [[ "$BACKEND_ONLY" -eq 1 ]]; then
  echo
  echo "  Backend running at http://localhost:8000"
  echo "  Skipping frontend (--backend-only). Press Ctrl+C to stop."
  wait $BACKEND_PID
  exit 0
fi

if ! command -v npm >/dev/null 2>&1; then
  echo
  echo "  ! npm not found. Backend is up at http://localhost:8000; install Node.js to run the frontend."
  echo "  ! Or re-run with --backend-only to suppress this notice."
  wait $BACKEND_PID
  exit 0
fi

echo "▶ Installing frontend deps..."
( cd "$FRONTEND" && npm install --silent )

echo "▶ Starting frontend on http://localhost:3000 ..."
( cd "$FRONTEND" && npm run dev ) &
FRONTEND_PID=$!

echo
echo "  Backend:   http://localhost:8000"
echo "  Frontend:  http://localhost:3000"
echo "  Press Ctrl+C to stop both."
wait
