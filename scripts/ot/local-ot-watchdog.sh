#!/usr/bin/env bash
# Watchdog local: reinicia yurots si el probe falla 2 veces seguidas.
# Uso: ./scripts/local-ot-watchdog.sh   (dejar corriendo en una terminal aparte)
set -euo pipefail

_BOOT="$(cd "$(dirname "$0")" && pwd)"
while [[ ! -f "$_BOOT/resolve-project-root.sh" ]]; do
  _BOOT="$(dirname "$_BOOT")"
  if [[ "$_BOOT" == "/" ]]; then
    echo "ERROR: resolve-project-root.sh no encontrado" >&2
    exit 1
  fi
done
# shellcheck source=scripts/resolve-project-root.sh
source "$_BOOT/resolve-project-root.sh"
ROOT="$(resolve_project_root)"
cd "$ROOT"

HOST="${OT_HEALTH_HOST:-127.0.0.1}"
PORT="${OT_PORT:-7171}"
FAILS=0
THRESHOLD=2
INTERVAL="${OT_WATCHDOG_INTERVAL:-45}"

log() { echo "$(date '+%H:%M:%S') [local-watchdog] $*"; }

while true; do
  if python3 "$ROOT/scripts/ot-probe.py" "$HOST" "$PORT" --timeout 5 --quiet 2>/dev/null; then
    if [[ "$FAILS" -gt 0 ]]; then
      log "recuperado (probe OK)"
    fi
    FAILS=0
  else
    FAILS=$((FAILS + 1))
    log "probe FAIL ($FAILS/$THRESHOLD)"
    if [[ "$FAILS" -ge "$THRESHOLD" ]]; then
      log "reiniciando yurots..."
      YUROTS_ITEMS_OTB="${YUROTS_ITEMS_OTB:-data/items/items-zagan-test.otb}" \
      YUROTS_ITEMS_XML="${YUROTS_ITEMS_XML:-data/items/items-zagan-test.xml}" \
        docker compose restart -t 15 yurots || true
      sleep 15
      if python3 "$ROOT/scripts/ot-probe.py" "$HOST" "$PORT" --timeout 8 --quiet 2>/dev/null; then
        log "OK tras restart"
        FAILS=0
      else
        log "sigue sin responder — revisá docker logs yurots"
      fi
    fi
  fi
  sleep "$INTERVAL"
done
