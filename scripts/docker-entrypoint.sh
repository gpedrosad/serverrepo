#!/bin/bash
# docker-entrypoint.sh — wrapper for ./source/yurots that:
#   1) Enables core dumps (writes to /cores)
#   2) Pipes stdout+stderr through `ts` (timestamps) + `tee` (persistence)
#
# Invoked by docker-compose.prod.yml: command: ["/app/YurOTS/docker-entrypoint.sh"]
# The Dockerfile copies this file into /app/YurOTS/.

set -u

# --- 1) Core dumps ---
ulimit -c unlimited 2>/dev/null || true

# Best-effort: redirect core_pattern to /cores.
# If /proc/sys/kernel/core_pattern is read-only, we fall back to the
# default (cwd = /app/YurOTS/ots).
if [ -w /proc/sys/kernel/core_pattern ]; then
    echo '/cores/core.%e.%p.%t' > /proc/sys/kernel/core_pattern 2>/dev/null || true
fi

mkdir -p /cores 2>/dev/null || true

# --- 2) Run yurots with timestamped, persisted output ---
cd /app/YurOTS/ots

LOGFILE="/app/YurOTS/ots/yurots.log"

if command -v ts >/dev/null 2>&1; then
    # `ts` (from moreutils) prefixes each line with a timestamp.
    # `tee -a` appends to the log file (so logs survive restarts).
    # yurots stays in the foreground of the pipeline so Docker sees its exit.
    exec ./source/yurots 2>&1 | ts '[%Y-%m-%dT%H:%M:%SZ]' | tee -a "$LOGFILE"
else
    # Fallback: no ts available, just tee to the log file.
    exec ./source/yurots 2>&1 | tee -a "$LOGFILE"
fi
