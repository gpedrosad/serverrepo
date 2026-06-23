#!/usr/bin/env bash
# Abre Remere con test.otbm (una sola instancia, sin colgarse).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RME_BIN="${RME_BIN:-$HOME/dev/rme/build/rme}"
RME_BUILD="$(dirname "$RME_BIN")"

# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
PROJECT_ROOT="$(resolve_project_root)"

MAP="$PROJECT_ROOT/server/YurOTS/ots/data/world/test.otbm"
CLIENT_DIR="$PROJECT_ROOT/rme-client-760"

# Matar instancias previas (evita zombies + ONLY_ONE_INSTANCE colgado).
if pgrep -x rme >/dev/null 2>&1; then
  "$SCRIPT_DIR/kill-rme.sh" || true
fi

# Setup completo solo la primera vez o si faltan assets.
if [[ ! -f "$CLIENT_DIR/Tibia.dat" || ! -f "$RME_BUILD/Tibia.dat" ]]; then
  "$SCRIPT_DIR/setup-rme-client.sh"
  "$SCRIPT_DIR/setup-rme-config.sh"
  "$SCRIPT_DIR/setup-rme-creatures.sh"
  "$SCRIPT_DIR/setup-rme-extensions.sh"
else
  "$SCRIPT_DIR/setup-rme-config.sh"
  "$SCRIPT_DIR/setup-rme-creatures.sh"
  "$SCRIPT_DIR/setup-rme-extensions.sh"
fi

if [[ ! -x "$RME_BIN" ]]; then
  echo "ERROR: No existe $RME_BIN"
  exit 1
fi

if [[ ! -f "$MAP" ]]; then
  echo "ERROR: No existe el mapa: $MAP"
  exit 1
fi

cd "$RME_BUILD"

# Lanzar desacoplado del shell de Cursor (evita procesos UE/zombie).
nohup "$RME_BIN" "$MAP" > /tmp/rme-yurots.log 2>&1 &
disown 2>/dev/null || true

echo "Remere iniciado (log: /tmp/rme-yurots.log)"
sleep 2
if pgrep -x rme >/dev/null; then
  echo "OK — buscá la ventana en el Dock."
else
  echo "ERROR — revisá /tmp/rme-yurots.log"
  tail -20 /tmp/rme-yurots.log 2>/dev/null || true
  exit 1
fi
