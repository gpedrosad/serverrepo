#!/usr/bin/env bash
# Pide un serverSave al OT en vivo (sin kick).
#
# Por defecto avisa en rojo a todos y guarda a los 5 minutos
# (data/.request-server-save → Game::scheduledServerSave).
#
# Uso (VPS o local con Docker):
#   ./scripts/server-save.sh                 # aviso 5 min + save
#   ./scripts/server-save.sh --now           # save inmediato (sin espera)
#   ./scripts/server-save.sh --backup        # + backup runtime tras el save
#   ./scripts/server-save.sh --restart       # + restart container tras el save
#   ./scripts/server-save.sh --backup --restart
#   ./scripts/server-save.sh --now --backup
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

DATA="$ROOT/server/YurOTS/ots/data"
REQUEST_DELAYED="$DATA/.request-server-save"
REQUEST_NOW="$DATA/.request-server-save-now"
OK_FILE="$DATA/.server-save-ok"
LOG_DIR="${RETRO76_LOG_DIR:-/var/log/retro76}"
DO_BACKUP=0
DO_RESTART=0
DO_NOW=0

for arg in "$@"; do
  case "$arg" in
    --backup) DO_BACKUP=1 ;;
    --restart) DO_RESTART=1 ;;
    --now) DO_NOW=1 ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *)
      echo "Opción desconocida: $arg" >&2
      exit 1
      ;;
  esac
done

# Delayed path needs ~5 min + margen; --now is quick.
if [[ -z "${SERVER_SAVE_TIMEOUT:-}" ]]; then
  if [[ "$DO_NOW" == "1" ]]; then
    TIMEOUT_SEC=60
  else
    TIMEOUT_SEC=360
  fi
else
  TIMEOUT_SEC="$SERVER_SAVE_TIMEOUT"
fi

log() {
  echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [server-save] $*"
}

if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'yurots'; then
  log "ERROR: container yurots no está Up"
  exit 1
fi

rm -f "$OK_FILE"
if [[ "$DO_NOW" == "1" ]]; then
  : > "$REQUEST_NOW"
  log "pedido .request-server-save-now (inmediato, timeout ${TIMEOUT_SEC}s)"
else
  : > "$REQUEST_DELAYED"
  log "pedido .request-server-save (aviso rojo + save en 5 min, timeout ${TIMEOUT_SEC}s)"
fi

elapsed=0
while [[ $elapsed -lt $TIMEOUT_SEC ]]; do
  if [[ -f "$OK_FILE" ]]; then
    ok_content="$(tr -d '\n' < "$OK_FILE" 2>/dev/null || true)"
    log "save OK ($ok_content)"
    break
  fi
  sleep 1
  elapsed=$((elapsed + 1))
  # Heartbeat cada minuto en el path diferido.
  if [[ "$DO_NOW" != "1" && $((elapsed % 60)) -eq 0 && $elapsed -lt $TIMEOUT_SEC ]]; then
    log "esperando save diferido... ${elapsed}s"
  fi
done

if [[ ! -f "$OK_FILE" ]]; then
  log "ERROR: timeout esperando .server-save-ok — ¿binario con checkSaveRequest + warn 5 min?"
  rm -f "$REQUEST_DELAYED" "$REQUEST_NOW"
  exit 1
fi

if [[ "$DO_BACKUP" == "1" ]]; then
  export BACKUP_LABEL="${BACKUP_LABEL:-midnight-save}"
  log "backup runtime (label=$BACKUP_LABEL)"
  BACKUP_LABEL="$BACKUP_LABEL" "$ROOT/scripts/backup-runtime-data.sh"
fi

if [[ "$DO_RESTART" == "1" ]]; then
  log "restart yurots"
  docker compose -f docker-compose.prod.yml restart -t 45 yurots
  sleep 3
  if python3 "$ROOT/scripts/ot-probe.py" 127.0.0.1 7171; then
    log "probe OK tras restart"
  else
    log "ERROR: probe FAIL tras restart"
    exit 1
  fi
fi

mkdir -p "$LOG_DIR" 2>/dev/null || true
log "listo"
