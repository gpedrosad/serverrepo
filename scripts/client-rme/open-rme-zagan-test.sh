#!/usr/bin/env bash
# Abre un RME de prueba aislado con los items Zagan+Square en 7.6.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
while [[ ! -f "$SCRIPT_DIR/resolve-project-root.sh" ]]; do
  SCRIPT_DIR="$(dirname "$SCRIPT_DIR")"
  if [[ "$SCRIPT_DIR" == "/" ]]; then
    echo "ERROR: resolve-project-root.sh no encontrado" >&2
    exit 1
  fi
done
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
ROOT="$(resolve_project_root)"

if [[ "${OPEN_RME_FAST:-0}" != "1" ]]; then
  "$SCRIPT_DIR/install-zagan-test-env.sh"
else
  "$SCRIPT_DIR/setup-rme-zagan-items.sh"
fi

export RME_ROOT="$ROOT/rme-zagan-test-root"
export RME_BIN="$RME_ROOT/build/rme"
export RME_BUILD="$RME_ROOT/build"
export RME_REAL="$RME_BIN"
export RME_CLIENT_DIR_OVERRIDE="$ROOT/rme-client-760-zagan-test"
export ZAGAN_RME=1
export OPEN_RME_FAST=1

if [[ -z "${MAP_OVERRIDE:-}" ]]; then
  export MAP_OVERRIDE="$ROOT/server/YurOTS/ots/data/world/test.otbm"
fi

exec "$SCRIPT_DIR/open-rme.sh"
