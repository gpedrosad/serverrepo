#!/usr/bin/env bash
# Instala cron de server save + backup todas las noches a medianoche hora Chile.
# Dispara a las 23:55 America/Santiago: el OT avisa en rojo y guarda a las 00:00.
#
# Uso (en el VPS):
#   ./scripts/install-midnight-server-save.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${RETRO76_LOG_DIR:-/var/log/retro76}"
MARK="# retro76-midnight-server-save"
CRON_TZ_LINE="CRON_TZ=America/Santiago"
# 23:55 → aviso rojo; save real a las 00:00 (delay 5 min en C++).
CRON_JOB="55 23 * * * cd $ROOT && BACKUP_LABEL=midnight-save $ROOT/scripts/server-save.sh --backup >> $LOG_DIR/server-save.log 2>&1"

chmod +x "$ROOT/scripts/server-save.sh" "$ROOT/scripts/backup-runtime-data.sh" 2>/dev/null || true
mkdir -p "$LOG_DIR"
touch "$LOG_DIR/server-save.log"

existing="$(crontab -l 2>/dev/null || true)"

# Quitar bloque anterior del mismo mark (mark + CRON_TZ opcional + job).
cleaned="$(printf '%s\n' "$existing" | awk -v mark="$MARK" '
  $0 == mark { skip=1; next }
  skip && /^CRON_TZ=/ { next }
  skip && /^[0-9*]/ { skip=0; next }
  skip { skip=0 }
  { print }
')"

{
  printf '%s\n' "$cleaned"
  echo "$MARK"
  echo "$CRON_TZ_LINE"
  echo "$CRON_JOB"
} | sed '/^$/N;/^\n$/D' | crontab -

echo "Cron instalado: aviso 23:55 + server save ~00:00 America/Santiago"
echo "  (C++ muestra texto rojo 5 min antes y guarda al cumplirse)"
echo "  Log: $LOG_DIR/server-save.log"
echo ""
echo "Verificar:"
echo "  crontab -l | grep -A2 midnight-server-save"
echo "  TZ=America/Santiago date"
echo "  tail -f $LOG_DIR/server-save.log"
