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
DISABLE_FILE="$ROOT/scripts/.smoke-tests-disabled"
HOST="127.0.0.1"
PORT="7171"
START_SERVER=0
FORCE=0
PASSTHRU=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)
      FORCE=1
      shift
      ;;
    --start)
      START_SERVER=1
      shift
      ;;
    --host)
      HOST="$2"
      PASSTHRU+=("$1" "$2")
      shift 2
      ;;
    --port)
      PORT="$2"
      PASSTHRU+=("$1" "$2")
      shift 2
      ;;
    *)
      PASSTHRU+=("$1")
      shift
      ;;
  esac
done

if [[ -f "$DISABLE_FILE" && "$FORCE" -eq 0 ]]; then
  echo "Smoke tests desactivados temporalmente ($DISABLE_FILE existe)."
  echo "Para reactivar: rm scripts/.smoke-tests-disabled"
  echo "Para forzar una corrida puntual: bash scripts/test-local-smoke.sh --force"
  exit 0
fi

if [[ "$START_SERVER" -eq 1 ]]; then
  echo "-> Levantando contenedor local de YurOTS..."
  (cd "$ROOT" && docker compose up -d yurots)
fi

python3 - "$HOST" "$PORT" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
try:
    sock = socket.create_connection((host, port), timeout=3)
except OSError as exc:
    print(f"Servidor no disponible en {host}:{port}: {exc}", file=sys.stderr)
    raise SystemExit(1)
else:
    sock.close()
PY

if [[ "${#PASSTHRU[@]}" -gt 0 ]]; then
  exec python3 "$ROOT/scripts/test-local-smoke.py" "${PASSTHRU[@]}"
else
  exec python3 "$ROOT/scripts/test-local-smoke.py"
fi
