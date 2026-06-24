#!/usr/bin/env bash
# Cambia la IP del OT en config.lua y reinicia Docker.
# Uso:
#   ./scripts/share-ot.sh local   → 127.0.0.1 (solo esta máquina)
#   ./scripts/share-ot.sh lan     → IP de tu red (amigos en la misma WiFi)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$ROOT/server/YurOTS/ots/config.lua"
MODE="${1:-lan}"

if [[ ! -f "$CONFIG" ]]; then
  echo "No existe $CONFIG" >&2
  exit 1
fi

detect_lan_ip() {
  if [[ "$(uname -s)" == "Darwin" ]]; then
    for iface in en0 en1 bridge0; do
      local ip
      ip="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
      if [[ -n "$ip" ]]; then
        echo "$ip"
        return 0
      fi
    done
  else
    hostname -I 2>/dev/null | awk '{print $1}' && return 0
  fi
  return 1
}

case "$MODE" in
  local)
    IP="127.0.0.1"
    ;;
  lan)
    IP="$(detect_lan_ip || true)"
    if [[ -z "$IP" ]]; then
      echo "No pude detectar tu IP de red. Usá: ./scripts/share-ot.sh 192.168.x.x" >&2
      exit 1
    fi
    ;;
  *)
    if [[ "$MODE" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      IP="$MODE"
    else
      echo "Uso: $0 [local|lan|IP]" >&2
      exit 1
    fi
    ;;
esac

python3 - "$CONFIG" "$IP" <<'PY'
import re, sys
path, ip = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
new, n = re.subn(r'^(ip\s*=\s*")[^"]*(")', rf'\g<1>{ip}\2', text, count=1, flags=re.M)
if not n:
    sys.exit("No se encontró ip = en config.lua")
open(path, "w", encoding="utf-8").write(new)
print(ip)
PY

echo "config.lua → ip = $IP"

cd "$ROOT"
docker compose -f docker-compose.prod.yml up -d yurots
docker compose -f docker-compose.prod.yml restart yurots

sleep 6
if docker logs yurots --tail 5 2>&1 | grep -q "YurOTS Server Running"; then
  echo ""
  echo "============================================"
  echo "  OT listo"
  echo "  IP:   $IP"
  echo "  Puerto: 7171"
  if [[ "$IP" == "127.0.0.1" ]]; then
    echo "  Solo vos en esta PC (cliente → 127.0.0.1:7171)"
  else
    echo "  Amigos en tu red: $IP:7171"
    echo "  Parcheá el cliente: python3 scripts/patch-tibia760-client.py --ip $IP"
  fi
  echo "  Web local: ./scripts/web.sh → http://localhost:8080/"
  echo "============================================"
else
  echo "Revisá logs: docker logs yurots --tail 30" >&2
  exit 1
fi
