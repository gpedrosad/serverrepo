#!/usr/bin/env bash
# Watchdog: si el OT no responde, reinicia el container con gracia.
# Pensado para cron en el VPS cada 2 minutos.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

HOST="${OT_HEALTH_HOST:-127.0.0.1}"
PORT="${OT_PORT:-7171}"
STATE_DIR="${OT_WATCHDOG_STATE:-/var/lib/ot-watchdog}"
FAIL_FILE="$STATE_DIR/fail_count"
LOG_DIR="${RETRO76_LOG_DIR:-/var/log/retro76}"
LOG_TAG="ot-watchdog"
MIN_UPTIME_SEC="${OT_WATCHDOG_MIN_UPTIME:-90}"
PROBE_TIMEOUT="${OT_WATCHDOG_PROBE_TIMEOUT:-5}"
FAIL_THRESHOLD="${OT_WATCHDOG_FAIL_THRESHOLD:-2}"

mkdir -p "$STATE_DIR" "$LOG_DIR"

log() {
  echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [$LOG_TAG] $*"
}

started_at=$(docker inspect yurots --format '{{.State.StartedAt}}' 2>/dev/null || echo "")
if [[ -n "$started_at" ]]; then
  started_epoch=$(date -d "$started_at" +%s 2>/dev/null || echo 0)
  now_epoch=$(date +%s)
  if [[ "$started_epoch" -gt 0 && $((now_epoch - started_epoch)) -lt $MIN_UPTIME_SEC ]]; then
    exit 0
  fi
fi

if python3 "$ROOT/scripts/ot-probe.py" "$HOST" "$PORT" --timeout "$PROBE_TIMEOUT" --quiet; then
  if [[ -f "$FAIL_FILE" ]]; then
    prev=$(cat "$FAIL_FILE")
    if [[ "$prev" -gt 0 ]]; then
      log "recuperado (probe OK tras $prev fallo(s))"
    fi
    rm -f "$FAIL_FILE"
  fi
  exit 0
fi

probe_line=$(python3 "$ROOT/scripts/ot-probe.py" "$HOST" "$PORT" --timeout "$PROBE_TIMEOUT" 2>/dev/null | tail -1 || echo "probe error")

fails=0
if [[ -f "$FAIL_FILE" ]]; then
  fails=$(cat "$FAIL_FILE")
fi
fails=$((fails + 1))
echo "$fails" > "$FAIL_FILE"

log "healthcheck falló ($fails/$FAIL_THRESHOLD) en $HOST:$PORT — $probe_line"

if [[ "$fails" -lt "$FAIL_THRESHOLD" ]]; then
  exit 0
fi

log "capturando diagnóstico previo a reinicio"
"$ROOT/scripts/ot-diagnostics.sh" --append >> "$LOG_DIR/watchdog.log" 2>&1 || true

log "reiniciando yurots (restart -t 45)"
docker compose -f docker-compose.prod.yml restart -t 45 yurots

sleep 10
if "$ROOT/scripts/healthcheck-ot.sh" "$HOST" "$PORT" >/dev/null 2>&1; then
  log "recuperado tras restart"
  rm -f "$FAIL_FILE"
  exit 0
fi

log "ERROR: sigue sin responder tras restart"
"$ROOT/scripts/ot-diagnostics.sh" --append >> "$LOG_DIR/watchdog.log" 2>&1 || true
docker logs yurots --tail 30 >> "$LOG_DIR/watchdog.log" 2>&1 || true
exit 1
