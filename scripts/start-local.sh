#!/usr/bin/env bash
# Arranque local completo: IP 127.0.0.1 + Docker + cliente.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$ROOT/server/YurOTS/ots/config.lua"

python3 - "$CONFIG" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
text, n = re.subn(r'^(ip\s*=\s*")[^"]*(")', r'\g<1>127.0.0.1\2', text, count=1, flags=re.M)
if not n:
    sys.exit("No se encontró ip = en config.lua")
open(path, "w", encoding="utf-8").write(text)
PY

echo "→ config.lua ip = 127.0.0.1"

cd "$ROOT"
docker compose up -d yurots

echo "→ Recompilando servidor (fix socket race)..."
docker compose exec -T yurots bash -c 'cd /app/YurOTS/ots/source && make -j2 yurots' || {
  echo "→ Contenedor no listo, build con run..."
  docker compose run --rm yurots bash -c 'cd /app/YurOTS/ots/source && make -j2 yurots'
  docker compose up -d yurots
}

docker compose restart yurots

echo "→ Esperando servidor..."
for i in $(seq 1 120); do
  if python3 -c "import socket; s=socket.create_connection(('127.0.0.1',7171),2); s.close()" 2>/dev/null; then
    if docker logs yurots 2>&1 | tail -5 | grep -q "Server Running"; then
      echo "→ Servidor listo (127.0.0.1:7171)"
      break
    fi
  fi
  if [[ "$i" -eq 120 ]]; then
    echo "El servidor no respondió. Logs:" >&2
    docker logs yurots --tail 30 >&2
    exit 1
  fi
  sleep 2
done

echo "→ Probando login al mundo..."
if "$ROOT/scripts/test-local-login.sh"; then
  echo "→ Login de prueba OK"
else
  echo "⚠ Login de prueba falló — podés intentar igual con el cliente" >&2
fi

pkill -f otclient_mac 2>/dev/null || true
sleep 1

echo "→ Abriendo cliente..."
exec "$ROOT/scripts/play-yurots-client.sh"
