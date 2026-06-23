#!/usr/bin/env bash
# Expone la web local a internet (URL pública temporal, gratis).
# Requiere: cloudflared (brew install cloudflared)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p web/state
LOG="/tmp/yurots-web.log"
TUNNEL_LOG="/tmp/yurots-tunnel.log"
WEB_PID_FILE="/tmp/yurots-web.pid"

start_web() {
  docker stop yurots-web 2>/dev/null || true
  OT_HOST=127.0.0.1 SERVER_IP=127.0.0.1 \
    nohup python3 web/server.py >>"$LOG" 2>&1 &
  echo $! >"$WEB_PID_FILE"
  for _ in $(seq 1 30); do
    curl -sf http://127.0.0.1:8080/ >/dev/null && return 0
    sleep 0.2
  done
  echo "No arrancó la web. Ver $LOG" >&2
  exit 1
}

if ! curl -sf http://127.0.0.1:8080/ >/dev/null 2>&1; then
  echo "Levantando web en :8080..."
  start_web
else
  echo "Web ya corre en :8080"
fi

if ! command -v cloudflared >/dev/null; then
  echo "Instalá cloudflared: brew install cloudflared" >&2
  exit 1
fi

: >"$TUNNEL_LOG"
echo "Abriendo túnel público..."
cloudflared tunnel --url http://127.0.0.1:8080 2>&1 | tee "$TUNNEL_LOG" &
TUNNEL_PID=$!

cleanup() {
  kill "$TUNNEL_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 60); do
  URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -1 || true)"
  [[ -n "$URL" ]] && break
  sleep 0.5
done

if [[ -z "$URL" ]]; then
  echo "No se obtuvo URL. Ver $TUNNEL_LOG" >&2
  wait "$TUNNEL_PID"
  exit 1
fi

echo ""
echo "============================================"
echo "  Compartí este link:"
echo "  $URL"
echo "============================================"
echo "  Local: http://localhost:8080/"
echo "  Ctrl+C cierra el túnel (la web sigue en local)"
echo ""

wait "$TUNNEL_PID"
