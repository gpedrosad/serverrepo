#!/usr/bin/env bash
# Instala cron de server save a medianoche hora Chile.
# Aviso rojo 23:55 Chile → save ~00:00 (delay 5 min en C++).
#
# No usa CRON_TZ (roto en cron Ubuntu 3.0pl1 del VPS). Dispara a :55 UTC
# en horas 2/3/4 y el gate confirma que en Chile son las 23:55.
#
# Uso (en el VPS):
#   ./scripts/install-midnight-server-save.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${RETRO76_LOG_DIR:-/var/log/retro76}"
MARK="# retro76-midnight-server-save"
# UTC: cubre Chile UTC-3 (02:55), UTC-4 (03:55), UTC-5 (04:55)
CRON_JOB="55 2,3,4 * * * $ROOT/scripts/midnight-server-save-gate.sh"

chmod +x "$ROOT/scripts/server-save.sh" \
  "$ROOT/scripts/backup-runtime-data.sh" \
  "$ROOT/scripts/midnight-server-save-gate.sh" 2>/dev/null || true
mkdir -p "$LOG_DIR"
touch "$LOG_DIR/server-save.log"

existing="$(crontab -l 2>/dev/null || true)"

# Quitar bloque anterior (mark + CRON_TZ opcional + job).
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
  echo "$CRON_JOB"
} | sed '/^$/N;/^\n$/D' | crontab -

NEXT_UTC="$(python3 - <<'PY'
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
cl = ZoneInfo("America/Santiago")
utc = ZoneInfo("UTC")
now = datetime.now(cl)
target = now.replace(hour=23, minute=55, second=0, microsecond=0)
if target <= now:
    target += timedelta(days=1)
print(target.astimezone(utc).strftime("%Y-%m-%d %H:%M UTC"), "↔", target.strftime("%Y-%m-%d %H:%M %Z"))
PY
)"

echo "Cron instalado: gate UTC 55 2,3,4 → solo si Chile=23:55"
echo "  Próximo disparo esperado: $NEXT_UTC"
echo "  Aviso rojo in-game a las 23:55 Chile; save ~00:00"
echo "  Log: $LOG_DIR/server-save.log"
echo ""
echo "Verificar:"
echo "  crontab -l | grep -A2 midnight-server-save"
echo "  TZ=America/Santiago date"
echo "  tail -f $LOG_DIR/server-save.log"
