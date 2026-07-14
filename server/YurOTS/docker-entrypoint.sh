#!/bin/bash
# docker-entrypoint.sh — wrapper for ./source/yurots that:
#   1) Enables core dumps (writes to /cores)
#   2) Pipes stdout+stderr through `ts` (timestamps) + `tee` (persistence)
#   3) Forwards SIGTERM/SIGINT to yurots so deploy can graceful-save players
#
# Used via bind mount: server/YurOTS/docker-entrypoint.sh → /app/YurOTS/
# Keep in sync with scripts/docker-entrypoint.sh (Dockerfile COPY source).

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
YUROTS_PID=""

forward_stop() {
    if [ -n "${YUROTS_PID}" ] && kill -0 "${YUROTS_PID}" 2>/dev/null; then
        echo "[entrypoint] forwarding SIGTERM to yurots pid=${YUROTS_PID}" >&2
        kill -TERM "${YUROTS_PID}" 2>/dev/null || true
        # Allow graceful save (players / daily-task storage / houseitems).
        for _ in $(seq 1 40); do
            kill -0 "${YUROTS_PID}" 2>/dev/null || break
            sleep 1
        done
        if kill -0 "${YUROTS_PID}" 2>/dev/null; then
            echo "[entrypoint] yurots still alive after 40s, sending SIGKILL" >&2
            kill -KILL "${YUROTS_PID}" 2>/dev/null || true
        fi
    fi
}

trap forward_stop TERM INT

if command -v ts >/dev/null 2>&1; then
    ./source/yurots 2>&1 | ts '[%Y-%m-%dT%H:%M:%SZ]' | tee -a "$LOGFILE" &
else
    ./source/yurots 2>&1 | tee -a "$LOGFILE" &
fi
PIPE_PID=$!

# Resolve the real yurots process (child of this shell / pipeline).
for _ in $(seq 1 20); do
    YUROTS_PID=$(pgrep -n -f '/app/YurOTS/ots/source/yurots' 2>/dev/null || true)
    if [ -z "${YUROTS_PID}" ]; then
        YUROTS_PID=$(pgrep -n yurots 2>/dev/null || true)
    fi
    if [ -n "${YUROTS_PID}" ] && kill -0 "${YUROTS_PID}" 2>/dev/null; then
        break
    fi
    sleep 0.25
done

if [ -z "${YUROTS_PID}" ]; then
    echo "[entrypoint] ERROR: could not find yurots process" >&2
    wait "${PIPE_PID}" 2>/dev/null || true
    exit 1
fi

echo "[entrypoint] yurots pid=${YUROTS_PID}" >&2

# Wait until yurots exits (SIGTERM path or crash).
while kill -0 "${YUROTS_PID}" 2>/dev/null; do
    sleep 1
done

wait "${PIPE_PID}" 2>/dev/null || true
exit 0
