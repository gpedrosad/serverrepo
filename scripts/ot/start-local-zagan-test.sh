#!/usr/bin/env bash
# Arranca el OT local usando el pack de items Zagan test y abre el cliente test.
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

"$SCRIPT_DIR/install-zagan-test-env.sh"

export OTCLIENT_DIR="$ROOT/client-local-zagan-test"
export YUROTS_ITEMS_OTB="data/items/items-zagan-test.otb"
export YUROTS_ITEMS_XML="data/items/items-zagan-test.xml"

exec "$SCRIPT_DIR/start-local.sh"
