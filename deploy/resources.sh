#!/bin/sh
# Detect host CPU/RAM for solver tuning. Source from deploy/*.sh.
#
# SOLVER_THREADS: unset or "auto" → all CPUs; otherwise an explicit count.
# SOLVER_MEM_MB: set automatically when readable (Linux /proc/meminfo, macOS sysctl).

detect_cpus() {
  if command -v nproc >/dev/null 2>&1; then
    nproc
  elif command -v getconf >/dev/null 2>&1; then
    getconf _NPROCESSORS_ONLN
  else
    echo 1
  fi
}

detect_mem_mb() {
  if [ -r /proc/meminfo ]; then
    awk '/MemTotal:/ {print int($2 / 1024)}' /proc/meminfo
  elif command -v sysctl >/dev/null 2>&1; then
    bytes=$(sysctl -n hw.memsize 2>/dev/null) || return 0
    echo $((bytes / 1048576))
  fi
}

if [ -z "${SOLVER_THREADS:-}" ] || [ "$SOLVER_THREADS" = "auto" ]; then
  SOLVER_THREADS=$(detect_cpus)
fi

if [ -z "${SOLVER_MEM_MB:-}" ]; then
  SOLVER_MEM_MB=$(detect_mem_mb)
fi

# Fixed transposition table: 16 bytes per slot, 2^bits slots total.
# Default to a bounded table on deploy so large boards (e.g. 3×15) cannot grow
# an unbounded DashMap and OOM the container. Override with SOLVER_MEMO=open|hash
# or an explicit SOLVER_MEMO_BITS.
if [ -z "${SOLVER_MEMO:-}" ]; then
  SOLVER_MEMO=fixed
fi

compute_memo_bits() {
  mem_mb=$1
  fraction=${SOLVER_MEMO_FRACTION:-0.18}
  if [ -z "$mem_mb" ] || [ "$mem_mb" -le 0 ] 2>/dev/null; then
    echo 28
    return
  fi
  awk -v mem="$mem_mb" -v f="$fraction" 'BEGIN {
    slots = mem * 1048576 * f / 16
    if (slots < 67108864) slots = 67108864
    bits = int(log(slots) / log(2))
    if (bits < 26) bits = 26
    if (bits > 34) bits = 34
    print bits
  }'
}

if [ -z "${SOLVER_MEMO_BITS:-}" ]; then
  SOLVER_MEMO_BITS=$(compute_memo_bits "$SOLVER_MEM_MB")
fi

memo_table_mb() {
  bits=$1
  awk -v bits="$bits" 'BEGIN { printf "%.0f\n", (2^bits) * 16 / 1048576 }'
}
SOLVER_MEMO_TABLE_MB=$(memo_table_mb "$SOLVER_MEMO_BITS")
