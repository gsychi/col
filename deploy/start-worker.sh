#!/bin/sh
set -eu

TABLEBASE_DIR="${TABLEBASE_DIR:-/data/tablebases}"
STATUS_FILE="${STATUS_FILE:-/data/solver_status.json}"
THREADS="${SOLVER_THREADS:-4}"
START_TOTAL="${CONTINUOUS_START_TOTAL:-3}"

mkdir -p "$TABLEBASE_DIR"

set -- python3 /app/continuous_solve.py \
  --skip-existing \
  --status-file "$STATUS_FILE" \
  --tablebase-dir "$TABLEBASE_DIR" \
  --start-total "$START_TOTAL"

if [ -n "${CONTINUOUS_MAX_TOTAL:-}" ]; then
  set -- "$@" --max-total "$CONTINUOUS_MAX_TOTAL"
fi

set -- "$@" -- --progress --threads "$THREADS"

exec "$@"
