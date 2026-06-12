#!/bin/sh
set -eu

. "$(dirname "$0")/resources.sh"

TABLEBASE_DIR="${TABLEBASE_DIR:-/data/tablebases}"
STATUS_FILE="${STATUS_FILE:-/data/solver_status.json}"
START_TOTAL="${CONTINUOUS_START_TOTAL:-3}"

mkdir -p "$TABLEBASE_DIR"

if [ -n "${SOLVER_MEM_MB:-}" ]; then
  echo "Solver resources: ${SOLVER_THREADS} thread(s), ${SOLVER_MEM_MB} MB RAM, memo ${SOLVER_MEMO} (~${SOLVER_MEMO_TABLE_MB} MB cap)" >&2
else
  echo "Solver resources: ${SOLVER_THREADS} thread(s), memo ${SOLVER_MEMO} (~${SOLVER_MEMO_TABLE_MB} MB cap)" >&2
fi

solver_extra="--progress --threads $SOLVER_THREADS --memo $SOLVER_MEMO"
if [ "$SOLVER_MEMO" = "fixed" ]; then
  solver_extra="$solver_extra --memo-bits $SOLVER_MEMO_BITS"
fi
if [ -n "${SOLVER_MEMO_MIN_LEGAL:-}" ]; then
  solver_extra="$solver_extra --memo-min-legal $SOLVER_MEMO_MIN_LEGAL"
fi

set -- python3 /app/continuous_solve.py \
  --skip-existing \
  --status-file "$STATUS_FILE" \
  --tablebase-dir "$TABLEBASE_DIR" \
  --start-total "$START_TOTAL"

if [ -n "${CONTINUOUS_MAX_TOTAL:-}" ]; then
  set -- "$@" --max-total "$CONTINUOUS_MAX_TOTAL"
fi

# shellcheck disable=SC2086
set -- "$@" -- $solver_extra

exec "$@"
