#!/usr/bin/env bash
# Instala extensiones RME de YurOTS (tilesets visibles para monstruos custom).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
PROJECT_ROOT="$(resolve_project_root)"

RME_ROOT="${RME_ROOT:-$HOME/dev/rme}"
RME_BUILD="${RME_BUILD:-$RME_ROOT/build}"
SRC="$PROJECT_ROOT/rme-extensions/yurots-creatures.xml"

if [[ ! -f "$SRC" ]]; then
  echo "ERROR: No existe $SRC"
  exit 1
fi

install_ext() {
  local dir="$1/extensions"
  mkdir -p "$dir"
  cp -f "$SRC" "$dir/yurots-creatures.xml"
  echo "Extension: $dir/yurots-creatures.xml"
}

install_ext "$RME_ROOT"
install_ext "$RME_BUILD"

ZAGAN_EXT="$PROJECT_ROOT/rme-extensions/yurots-zagan-items.xml"
if [[ -f "$ZAGAN_EXT" ]]; then
  install_zagan() {
    local dir="$1/extensions"
    mkdir -p "$dir"
    cp -f "$ZAGAN_EXT" "$dir/yurots-zagan-items.xml"
    echo "Extension: $dir/yurots-zagan-items.xml"
  }
  install_zagan "$RME_ROOT"
  install_zagan "$RME_BUILD"
fi

echo "OK — extensiones YurOTS instaladas."
