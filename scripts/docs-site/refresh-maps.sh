#!/bin/bash
# Mantiene el mapa por pisos y el mapa de monstruos del sitio local de docs al día con main.
#
# Uso: scripts/docs-site/refresh-maps.sh [SITIO]        (SITIO por defecto: ~/apps/retro76-docs)
#      FORCE=1 scripts/docs-site/refresh-maps.sh        (regenera aunque no haya cambios)
#
# Trae origin/main a un worktree propio (~/proyectos/serverrepo-docs-map, separado del checkout
# principal) y, si cambió algo de lo que dibujan los mapas, corre build-floor-map.py y
# build-monster-map.py. Lo corre cada 10 minutos el LaunchAgent com.gonzalo.retro76-docs-maps
# (ver docs/items-and-map/MAPA_DE_MONSTRUOS.md). Solo es Python: no compila nada.
set -euo pipefail

SITE="${1:-$HOME/apps/retro76-docs}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WT="$HOME/proyectos/serverrepo-docs-map"
PY="${PYTHON:-/opt/homebrew/bin/python3.11}"
STAMP="$SITE/.maps-stamp"
LOCK="$SITE/.maps-lock"
# lo que dibujan los mapas: mapa, spawns, NPC, monstruos y el cliente de RME
PATHS=(server/YurOTS/ots/data/world server/YurOTS/ots/data/monster server/YurOTS/ots/data/npc
       devtools/rme/rme-client-760 scripts/map)

# todo va en una función: el checkout de abajo puede reescribir este archivo mientras corre
main() {
    mkdir -p "$SITE"
    find "$SITE" -maxdepth 1 -name .maps-lock -mmin +60 -exec rmdir {} \;   # quedó de un corte
    mkdir "$LOCK" 2>/dev/null || { echo "ya hay una actualización corriendo"; exit 0; }
    trap 'rmdir "$LOCK"' EXIT

    git -C "$REPO" fetch -q origin main
    if [ ! -d "$WT" ]; then
        git -C "$REPO" worktree add -q --detach "$WT" origin/main
    fi
    git -C "$WT" checkout -q --detach origin/main

    state="$(git -C "$WT" rev-parse HEAD) $(git -C "$WT" rev-parse "${PATHS[@]/#/HEAD:}" | shasum | cut -c1-12)"
    want="${state#* }"
    if [ -z "${FORCE:-}" ] && [ -f "$STAMP" ] && [ "$(cut -d' ' -f2 "$STAMP")" = "$want" ]; then
        exit 0
    fi

    echo "$(date '+%F %T') regenerando mapas desde main $(git -C "$WT" rev-parse --short HEAD)"
    cd "$WT"
    "$PY" -I scripts/map/build-floor-map.py "$SITE/mapa/"
    "$PY" -I scripts/map/build-monster-map.py "$SITE/"
    echo "$state" > "$STAMP"
    echo "$(date '+%F %T') listo"
}
main "$@"
