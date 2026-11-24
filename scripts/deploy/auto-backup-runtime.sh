#!/usr/bin/env bash
# Respaldo automático de los datos de jugadores (cada hora, cron de la ThinkPad). 24 nov 2026.
#
# Guarda en ~/backups/auto/hourly/runtime-AAAAMMDD-HHMM.tar.gz todo lo que el servidor escribe en runtime
# (cuentas, personajes, vip, casas, houseitems, guilds, cartas escritas, padrinazgo, trainers, ranking de
# la Wave Arena y web/state). El servidor guarda solo cada 10 min (`autosave` en config.lua): no hace
# falta pedir un save. Si se copia justo mientras guarda, algún XML puede quedar a medias: por eso se
# valida cada XML/JSON de la copia y, si alguno no abre, se reintenta a los 20 s (hasta 3 veces).
#
# Rotación: los horarios duran 48 h; el primero de cada día queda en daily/ por 30 días.
# La copia fuera de la ThinkPad la trae la Mac: scripts/deploy/pull-auto-backups.sh.
#
# Uso (en la ThinkPad):
#   scripts/deploy/auto-backup-runtime.sh             # un respaldo ahora
#   scripts/deploy/auto-backup-runtime.sh --install   # deja el cron cada hora (idempotente)
# Restaurar: docs/systems/THINKPAD_TEST_SERVER.md#respaldo-automático-de-jugadores
set -euo pipefail

ROOT="${RETRO76_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
DATA="server/YurOTS/ots/data"
DEST="${AUTO_BACKUP_DIR:-$HOME/backups/auto}"
KEEP_HOURS="${KEEP_HOURS:-48}"
KEEP_DAYS="${KEEP_DAYS:-30}"
MARK="# retro76-auto-backup"

if [[ "${1:-}" == "--install" ]]; then
  mkdir -p "$DEST"
  job="17 * * * * $ROOT/scripts/deploy/auto-backup-runtime.sh >> $DEST/backup.log 2>&1 $MARK"
  { crontab -l 2>/dev/null | grep -v -F "$MARK" || true; echo "$job"; } | crontab -
  echo "cron instalado: $job"
  exit 0
fi

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [auto-backup] $*"; }

cd "$ROOT"
items=()
for f in players accounts vip houses houseitems.xml online.xml queue.xml guilds.xml private_trainers.xml \
         sponsors.xml scrolltexts.xml logs/wave_arena_rank.json; do
  [[ -e "$DATA/$f" ]] && items+=("$DATA/$f")
done
[[ -d web/state ]] && items+=(web/state)
[[ -d "$DATA/players" && -d "$DATA/accounts" ]] || { log "ERROR: no están players/ y accounts/ en $ROOT/$DATA"; exit 1; }

mkdir -p "$DEST/hourly" "$DEST/daily"
stamp="$(date +%Y%m%d-%H%M)"
out="$DEST/hourly/runtime-$stamp.tar.gz"

for try in 1 2 3; do
  tmp="$(mktemp -d)"
  cp -a --parents "${items[@]}" "$tmp/"
  if bad="$(python3 - "$tmp" <<'PY'
import json, pathlib, sys
import xml.etree.ElementTree as ET
bad = []
for p in sorted(pathlib.Path(sys.argv[1]).rglob("*")):
    try:
        if p.suffix == ".xml":
            ET.parse(p)
        elif p.suffix == ".json":
            json.loads(p.read_bytes())
    except Exception as e:
        bad.append(f"{p.name}: {e}")
print("; ".join(bad))
sys.exit(1 if bad else 0)
PY
)"; then
    tar -czf "$out.tmp" -C "$tmp" . && mv "$out.tmp" "$out"
    rm -rf "$tmp"
    break
  fi
  rm -rf "$tmp"
  log "intento $try: archivo a medias ($bad); reintento en 20 s"
  sleep 20
done
[[ -f "$out" ]] || { log "ERROR: no se pudo hacer una copia entera en 3 intentos"; exit 1; }

day="$DEST/daily/runtime-${stamp%%-*}.tar.gz"
[[ -f "$day" ]] || cp -a "$out" "$day"
find "$DEST/hourly" -name 'runtime-*.tar.gz' -mmin "+$((KEEP_HOURS * 60))" -delete
find "$DEST/daily" -name 'runtime-*.tar.gz' -mtime "+$KEEP_DAYS" -delete

acc=$(find "$DATA/accounts" -maxdepth 1 -name '*.xml' | wc -l)
plr=$(find "$DATA/players" -maxdepth 1 -name '*.xml' | wc -l)
hou=$(grep -l 'owner name="[^"]' "$DATA/houses"/*.xml 2>/dev/null | wc -l || true)
log "OK $(basename "$out") $(du -h "$out" | cut -f1): $acc cuentas, $plr personajes, $hou casas con dueño"
