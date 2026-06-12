#!/bin/sh
# Run continuous solve + web UI in one container (Render disks are per-service only).
set -eu

TABLEBASE_DIR="${TABLEBASE_DIR:-/data/tablebases}"
STATUS_FILE="${STATUS_FILE:-/data/solver_status.json}"
mkdir -p "$TABLEBASE_DIR"

echo "Starting continuous solver in background..." >&2
./deploy/start-worker.sh &
WORKER_PID=$!

cleanup() {
  if kill -0 "$WORKER_PID" 2>/dev/null; then
    echo "Stopping solver (pid $WORKER_PID)..." >&2
    kill "$WORKER_PID" 2>/dev/null || true
    wait "$WORKER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "Starting web UI on port ${PORT:-8000}..." >&2
exec ./deploy/start-web.sh
