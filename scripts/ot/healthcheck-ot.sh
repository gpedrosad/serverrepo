#!/usr/bin/env bash
# Comprueba que el OT responde al protocolo info en el puerto de juego.
# Uso: ./scripts/healthcheck-ot.sh [host] [port]
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
HOST="${1:-127.0.0.1}"
PORT="${2:-7171}"

exec python3 "$ROOT/scripts/ot-probe.py" "$HOST" "$PORT" --quiet --timeout "${OT_PROBE_TIMEOUT:-5}"
