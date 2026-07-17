#!/usr/bin/env bash
# Gate del save de medianoche. Cron del VPS está en UTC y CRON_TZ no aplica
# en cron 3.0pl1 de Ubuntu — por eso validamos la hora Chile acá.
#
# Crontab (UTC): 55 2,3,4 * * *  → cubre America/Santiago UTC-3/-4/-5
# Solo corre el save si en Chile son las 23:55.
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
LOG_DIR="${RETRO76_LOG_DIR:-/var/log/retro76}"
LOCK="${RETRO76_MIDNIGHT_SAVE_LOCK:-/var/run/retro76-midnight-server-save.lock}"

HHMM="$(TZ=America/Santiago date +%H%M)"
if [[ "$HHMM" != "2355" ]]; then
  exit 0
fi

mkdir -p "$LOG_DIR"
# Evita doble disparo si coinciden dos horas UTC el mismo minuto (no debería).
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [midnight-gate] ya en curso, skip" >> "$LOG_DIR/server-save.log"
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

{
  echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [midnight-gate] Chile=$(TZ=America/Santiago date '+%Y-%m-%d %H:%M %Z') — disparando save"
  BACKUP_LABEL=midnight-save "$ROOT/scripts/server-save.sh" --backup
} >> "$LOG_DIR/server-save.log" 2>&1
