#!/usr/bin/env bash
# Abre el cliente test con los 5 items Zagan+Square cargados.
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
if python3 "$ROOT/scripts/ot-probe.py" 127.0.0.1 7171 --timeout 3 --quiet 2>/dev/null; then
  export SKIP_ZAGAN_SERVER_RESTART=1
fi

TERMINAL_LAUNCHER="$SCRIPT_DIR/open-zagan-test-client-terminal.command"
if [[ -n "${VSCODE_IPC_HOOK:-}" || -n "${CURSOR_EXTENSION_HOST_ROLE:-}" ]]; then
  if [[ -x "$TERMINAL_LAUNCHER" ]]; then
    open "$TERMINAL_LAUNCHER"
    echo "OK — cliente Zagan se abre en Terminal.app (Cursor no puede mostrar OTClient)."
    echo "Si no aparece, hacé doble clic en: $TERMINAL_LAUNCHER"
    exit 0
  fi
fi

exec "$SCRIPT_DIR/play-yurots-client.sh"
