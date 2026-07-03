#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="127.0.0.1"
PORT="7171"
START_SERVER=0
PASSTHRU=()

while [[ $# -gt 0 ]]; do
  case "$1" in
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
