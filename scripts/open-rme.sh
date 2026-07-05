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
MAP="${MAP_OVERRIDE:-$MAP}"
CLIENT_DIR="${RME_CLIENT_DIR_OVERRIDE:-$PROJECT_ROOT/rme-client-760}"

# Matar instancias previas (evita zombies + ONLY_ONE_INSTANCE colgado).
if pgrep -x rme >/dev/null 2>&1; then
  "$SCRIPT_DIR/kill-rme.sh" || true
fi

# Setup liviano: en modo Zagan fast solo config + extensiones.
if [[ "${OPEN_RME_FAST:-0}" == "1" ]]; then
  "$SCRIPT_DIR/setup-rme-config.sh"
  "$SCRIPT_DIR/setup-rme-creatures.sh"
  "$SCRIPT_DIR/setup-rme-extensions.sh"
elif [[ ! -f "$CLIENT_DIR/Tibia.dat" || ! -f "$RME_BUILD/Tibia.dat" ]]; then
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

exec "$SCRIPT_DIR/launch-rme-macos.sh"
