#!/usr/bin/env bash
# Rebuild Zagan assets and push Tibia.dat/spr to ~/clienteretro (mac + windows).
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

CLIENTERETRO="${CLIENTERETRO:-$HOME/clienteretro}"

"$ROOT/scripts/install-zagan-test-env.sh"

if [[ ! -x "$CLIENTERETRO/sync-from-yurots.sh" ]]; then
  echo "ERROR: No existe $CLIENTERETRO/sync-from-yurots.sh" >&2
  exit 1
fi

YUROTS_ROOT="$ROOT" "$CLIENTERETRO/sync-from-yurots.sh"
echo "Cliente publicado actualizado en $CLIENTERETRO"
