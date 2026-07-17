#!/usr/bin/env bash
set -euo pipefail
_BOOT="$(cd "$(dirname "$0")" && pwd)"
while [[ ! -f "$_BOOT/resolve-project-root.sh" ]]; do
  _BOOT="$(dirname "$_BOOT")"
  if [[ "$_BOOT" == "/" ]]; then
    echo "ERROR: resolve-project-root.sh no encontrado" >&2
    exit 1
  fi
done
# shellcheck source=scripts/resolve-project-root.sh
source "$_BOOT/resolve-project-root.sh"
ROOT="$(resolve_project_root)"
cd "$ROOT"

if ! "$ROOT/scripts/recover-rme-macos.sh"; then
  echo "Recuperación falló."
fi

export MAP_OVERRIDE="$ROOT/server/YurOTS/ots/data/world/test.otbm"
export ZAGAN_RME=1
export OPEN_RME_FAST=1
export SKIP_ZAGAN_SERVER_RESTART=1
export RME_ROOT="$ROOT/rme-zagan-test-root"
export RME_BUILD="$ROOT/rme-zagan-test-root/build"
export RME_BIN="$RME_BUILD/rme"
export RME_REAL="$RME_BIN"
export RME_CLIENT_DIR_OVERRIDE="$ROOT/rme-client-760-zagan-test"

"$ROOT/scripts/setup-rme-zagan-items.sh"
RME_ROOT="$RME_ROOT" RME_BIN="$RME_REAL" RME_BUILD="$RME_BUILD" \
  RME_CLIENT_DIR_OVERRIDE="$RME_CLIENT_DIR_OVERRIDE" ZAGAN_RME=1 \
  "$ROOT/scripts/setup-rme-config.sh"
RME_ROOT="$RME_ROOT" RME_BUILD="$RME_BUILD" "$ROOT/scripts/setup-rme-creatures.sh"
RME_ROOT="$RME_ROOT" RME_BUILD="$RME_BUILD" "$ROOT/scripts/setup-rme-extensions.sh"

cd "$RME_BUILD"
echo "→ Abriendo Remere (items Zagan)..."
echo "→ Mapa: $MAP_OVERRIDE"
export DISPLAY="${DISPLAY:-:0}"
exec "$RME_BIN" "$MAP_OVERRIDE"
