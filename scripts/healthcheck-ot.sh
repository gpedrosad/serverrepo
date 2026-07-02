#!/usr/bin/env bash
# Comprueba que el OT responde al protocolo info en el puerto de juego.
# Uso: ./scripts/healthcheck-ot.sh [host] [port]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${1:-127.0.0.1}"
PORT="${2:-7171}"

exec python3 "$ROOT/scripts/ot-probe.py" "$HOST" "$PORT" --quiet --timeout 8
