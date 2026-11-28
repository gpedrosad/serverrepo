#!/usr/bin/env bash
# Limpieza semanal del VPS (cron de gonzalo, domingo 04:30). 27 nov 2026. Doc: docs/systems/VPS_VULTR.md#cron.
#
# - Registros mensuales de data/logs (metrics-, logins-, web-, funnel-, play-AAAA-MM.jsonl) de hace más de 12 meses.
#   La Mac ya guarda copia en ~/Retro76-backups/vps-logs/.
# - Respaldos de deploy (~/backups/pre-deploy-*, pre-vps-*): se conservan los 15 más nuevos y todo lo de los
#   últimos 30 días.
# - Logs de cron en ~/backups/*.log y ~/backups/logs/*.log: si pasan de 5 MB quedan las últimas 5000 líneas.
# - Imágenes de Docker sin etiqueta (restos de builds). No toca contenedores ni volúmenes.
#
# Nunca toca players/, accounts/, houses/ ni web/state/.
#   scripts/deploy/prune-runtime.sh            # limpia
#   scripts/deploy/prune-runtime.sh --dry-run  # solo dice qué borraría
set -uo pipefail

ROOT="${RETRO76_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
LOGS="$ROOT/server/YurOTS/ots/data/logs"
BACKUPS="${BACKUPS_DIR:-$HOME/backups}"
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

say() { echo "$(date '+%Y-%m-%d %H:%M:%S') [prune] $*"; }
rm_path() {
  if [[ $DRY -eq 1 ]]; then say "borraría $1"; else rm -rf -- "$1" && say "borrado $1"; fi
}

# 1. registros mensuales de más de 12 meses (por el AAAA-MM del nombre)
cutoff=$(date -d "-12 months" +%Y-%m)
for f in "$LOGS"/{metrics,logins,web,funnel,play}-[0-9][0-9][0-9][0-9]-[0-9][0-9].jsonl; do
  [[ -e "$f" ]] || continue
  ym=$(basename "$f" .jsonl); ym=${ym#*-}
  [[ "$ym" < "$cutoff" ]] && rm_path "$f"
done

# 2. respaldos de deploy: 15 más nuevos + los de los últimos 30 días
mapfile -t olds < <(ls -1dt "$BACKUPS"/pre-deploy-* "$BACKUPS"/pre-vps-* 2>/dev/null | tail -n +16)
for d in "${olds[@]}"; do
  [[ -n "$(find "$d" -maxdepth 0 -mtime +30 2>/dev/null)" ]] && rm_path "$d"
done

# 3. logs de cron grandes
for f in "$BACKUPS"/*.log "$BACKUPS"/logs/*.log; do
  [[ -f "$f" ]] || continue
  if [[ $(stat -c %s "$f") -gt 5242880 ]]; then
    if [[ $DRY -eq 1 ]]; then say "recortaría $f"; else tail -n 5000 "$f" > "$f.tmp" && mv "$f.tmp" "$f" && say "recortado $f"; fi
  fi
done

# 4. imágenes de Docker colgadas
if [[ $DRY -eq 1 ]]; then
  say "imágenes colgadas: $(docker images -f dangling=true -q | wc -l)"
else
  docker image prune -f >/dev/null 2>&1 && say "docker image prune OK"
fi
say "listo (disco: $(df -h / | awk 'NR==2{print $5}') usado)"
