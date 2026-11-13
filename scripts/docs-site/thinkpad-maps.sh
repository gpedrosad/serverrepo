#!/bin/bash
# Sitio de mapas en la ThinkPad (http://192.168.1.17:8077): mapa interactivo de monstruos, mapa por
# pisos y vistas de zona, de lo que está DEPLOYADO (el commit de main en ~/apps/serverrepo, sin los
# cambios sin commitear de otras sesiones).
#
# Uso: scripts/docs-site/thinkpad-maps.sh            (regenera solo si cambió algo de lo que dibuja)
#      FORCE=1 scripts/docs-site/thinkpad-maps.sh    (regenera siempre)
#
# Lo corre cada 10 min el timer retro76-mapas-refresh (scripts/docs-site/install-thinkpad.sh).
# Arma todo en SITIO.next y lo cambia de golpe: la web nunca queda a medio generar.
set -euo pipefail

SITE="${SITE:-$HOME/apps/retro76-mapas}"
REPO="${REPO:-$HOME/apps/serverrepo}"
WT="${WT:-$HOME/apps/serverrepo-mapas}"
STATE="${XDG_CACHE_HOME:-$HOME/.cache}/retro76-mapas"
PY="${PYTHON:-python3}"
HERE="$(cd "$(dirname "$0")" && pwd)"    # la copia instalada (thinkpad-index.py va al lado)
# lo que dibujan los mapas: mapa, spawns, NPC, monstruos, cliente de RME y los generadores
PATHS=(server/YurOTS/ots/data/world server/YurOTS/ots/data/monster server/YurOTS/ots/data/npc
       devtools/rme/rme-client-760 scripts/map)

main() {
    mkdir -p "$STATE"
    find "$STATE" -maxdepth 1 -name lock -mmin +60 -exec rmdir {} \;   # quedó de un corte
    mkdir "$STATE/lock" 2>/dev/null || { echo "ya hay una actualización corriendo"; exit 0; }
    trap 'rmdir "$STATE/lock"' EXIT

    local head
    head="$(git -C "$REPO" rev-parse main)"
    [ -d "$WT" ] || git -C "$REPO" worktree add -q --detach "$WT" "$head"
    git -C "$WT" checkout -q --detach "$head"

    local want
    want="$(git -C "$WT" rev-parse "${PATHS[@]/#/HEAD:}" | sha1sum | cut -c1-12)"
    if [ -z "${FORCE:-}" ] && [ -f "$STATE/stamp" ] && [ "$(cat "$STATE/stamp")" = "$want" ] && [ -f "$SITE/index.html" ]; then
        exit 0
    fi

    echo "$(date '+%F %T') regenerando mapas desde main $(git -C "$WT" rev-parse --short HEAD)"
    local next="${SITE:?}.next" old="${SITE:?}.old"
    rm -rf "${next:?}" "${old:?}"
    mkdir -p "$next"
    cd "$WT"
    "$PY" -I scripts/map/build-floor-map.py "$next/mapa/"
    "$PY" -I scripts/map/build-monster-map.py "$next/"
    "$PY" -I "$HERE/thinkpad-index.py" "$next" "$(git rev-parse --short HEAD)"
    [ -d "$SITE" ] && mv "$SITE" "$old"
    mv "$next" "$SITE"
    rm -rf "${old:?}"
    echo "$want" > "$STATE/stamp"
    echo "$(date '+%F %T') listo"
}
main "$@"
