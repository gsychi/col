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
