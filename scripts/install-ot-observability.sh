#!/usr/bin/env bash
# Instala logs + cron de diagnóstico en el VPS.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${RETRO76_LOG_DIR:-/var/log/retro76}"
MARK_DIAG="# retro76-ot-diagnostics"
MARK_WD="# ot-watchdog-yurots"
CRON_DIAG="*/5 * * * * cd $ROOT && $ROOT/scripts/ot-diagnostics.sh --append"
CRON_WD="*/2 * * * * cd $ROOT && $ROOT/scripts/ot-watchdog.sh >> $LOG_DIR/watchdog.log 2>&1"

chmod +x "$ROOT/scripts/ot-probe.py" \
  "$ROOT/scripts/ot-diagnostics.sh" \
  "$ROOT/scripts/healthcheck-ot.sh" \
  "$ROOT/scripts/ot-watchdog.sh" \
  "$ROOT/scripts/install-ot-watchdog.sh" 2>/dev/null || true

mkdir -p "$LOG_DIR" "$ROOT/web/logs"
touch "$LOG_DIR/diagnostics.log" "$LOG_DIR/watchdog.log" "$ROOT/web/logs/retro76-web.log"

# systemd web: variables de log si existe la unidad
UNIT="/etc/systemd/system/yurots-web.service"
if [[ -f "$UNIT" ]]; then
  grep -q 'WEB_LOG_FILE=' "$UNIT" || sed -i "/^\[Service\]/a Environment=WEB_LOG_FILE=$LOG_DIR/web.log\nEnvironment=WEB_LOG_DIR=$LOG_DIR\nEnvironment=WEB_LOG_STDOUT=1" "$UNIT"
  systemctl daemon-reload
  systemctl restart yurots-web || true
fi

install_cron() {
  local mark="$1"
  local line="$2"
  local existing
  existing="$(crontab -l 2>/dev/null || true)"
  if echo "$existing" | grep -qF "$mark"; then
    if echo "$existing" | grep -qF "$line"; then
      echo "Cron ya presente: $mark"
    else
      echo "$existing" | awk -v mark="$mark" -v line="$line" '
        $0 == mark { print; getline; print line; next }
        { print }
      ' | crontab -
      echo "Cron actualizado: $mark"
    fi
  else
    (echo "$existing"; echo "$mark"; echo "$line") | crontab -
    echo "Cron instalado: $mark"
  fi
}

install_cron "$MARK_DIAG" "$CRON_DIAG"
install_cron "$MARK_WD" "$CRON_WD"

echo ""
echo "Observabilidad instalada."
echo "  Diagnóstico cada 5 min → $LOG_DIR/diagnostics.log"
echo "  Watchdog cada 2 min   → $LOG_DIR/watchdog.log"
echo "  Web                   → $LOG_DIR/web.log (o web/logs/retro76-web.log local)"
echo ""
echo "Comandos útiles:"
echo "  tail -f $LOG_DIR/diagnostics.log"
echo "  tail -f $LOG_DIR/web.log"
echo "  $ROOT/scripts/ot-diagnostics.sh"
