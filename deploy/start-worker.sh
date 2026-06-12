#!/bin/sh
set -eu

. "$(dirname "$0")/resources.sh"

TABLEBASE_DIR="${TABLEBASE_DIR:-/data/tablebases}"
STATUS_FILE="${STATUS_FILE:-/data/solver_status.json}"
START_TOTAL="${CONTINUOUS_START_TOTAL:-3}"

mkdir -p "$TABLEBASE_DIR"

if [ -n "${SOLVER_MEM_MB:-}" ]; then
  echo "Solver resources: ${SOLVER_THREADS} thread(s), ${SOLVER_MEM_MB} MB RAM" >&2
else
  echo "Solver resources: ${SOLVER_THREADS} thread(s)" >&2
fi

set -- python3 /app/continuous_solve.py \
  --skip-existing \
  --status-file "$STATUS_FILE" \
  --tablebase-dir "$TABLEBASE_DIR" \
  --start-total "$START_TOTAL"

if [ -n "${CONTINUOUS_MAX_TOTAL:-}" ]; then
  set -- "$@" --max-total "$CONTINUOUS_MAX_TOTAL"
fi

set -- "$@" -- --progress --threads "$SOLVER_THREADS"

exec "$@"
