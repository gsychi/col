#!/bin/sh
set -eu

TABLEBASE_DIR="${TABLEBASE_DIR:-/data/tablebases}"
STATUS_FILE="${STATUS_FILE:-/data/solver_status.json}"
COL_M="${COL_M:-3}"
COL_N="${COL_N:-11}"
PORT="${PORT:-8000}"

mkdir -p "$TABLEBASE_DIR"

exec python3 /app/python/gui_server.py \
  --host 0.0.0.0 \
  --port "$PORT" \
  --m "$COL_M" \
  --n "$COL_N" \
  --tablebase-dir "$TABLEBASE_DIR" \
  --status-file "$STATUS_FILE"
