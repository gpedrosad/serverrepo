#!/usr/bin/env bash
# Instala cron del watchdog OT en el VPS (ejecutar en el servidor).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARK="# ot-watchdog-yurots"
LOG_DIR="${RETRO76_LOG_DIR:-/var/log/retro76}"
CRON_LINE="*/2 * * * * cd $ROOT && $ROOT/scripts/ot-watchdog.sh >> $LOG_DIR/watchdog.log 2>&1"

chmod +x "$ROOT/scripts/healthcheck-ot.sh" "$ROOT/scripts/ot-watchdog.sh"
mkdir -p /var/lib/ot-watchdog "$LOG_DIR"
touch "$LOG_DIR/watchdog.log"
# Migrar log viejo si existía
if [[ -f /var/log/ot-watchdog.log && ! -s "$LOG_DIR/watchdog.log" ]]; then
  cat /var/log/ot-watchdog.log >> "$LOG_DIR/watchdog.log" 2>/dev/null || true
fi

if crontab -l 2>/dev/null | grep -qF "$MARK"; then
  if crontab -l 2>/dev/null | grep -qF "$CRON_LINE"; then
    echo "Watchdog ya instalado."
  else
    crontab -l 2>/dev/null | awk -v mark="$MARK" -v line="$CRON_LINE" '
      $0 == mark { print; getline; print line; next }
      { print }
    ' | crontab -
    echo "Watchdog actualizado (ruta de log unificada)."
  fi
else
  (crontab -l 2>/dev/null || true; echo "$MARK"; echo "$CRON_LINE") | crontab -
  echo "Watchdog instalado (cada 2 min)."
fi

echo "Probar ahora:"
"$ROOT/scripts/healthcheck-ot.sh" 127.0.0.1 7171 && echo "OK — OT responde"
