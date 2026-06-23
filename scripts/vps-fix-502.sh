#!/usr/bin/env bash
# Fix 502 en el VPS: levanta la web en :8081 y configura nginx :8080 -> :8081
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
ROOT="$(resolve_project_root)"

cd "$ROOT"

echo "== YurOTS: fix 502 web =="

if [[ -f .git/config ]]; then
  git pull --ff-only origin main
fi

cp deploy/env.vps .env
mkdir -p web/state
mkdir -p server/YurOTS/ots/data/accounts server/YurOTS/ots/data/players

docker compose -f docker-compose.prod.yml up -d --force-recreate web yurots

sleep 3
backend_code="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8081/api/data || true)"
echo "Docker backend 127.0.0.1:8081 -> HTTP $backend_code"

if [[ "$backend_code" != "200" ]]; then
  echo "ERROR: la web no responde en :8081" >&2
  docker logs yurots-web --tail 40 >&2 || true
  exit 1
fi

if command -v nginx >/dev/null; then
  echo "Configurando nginx..."
  sudo cp deploy/nginx-yurots-web.conf /etc/nginx/sites-available/yurots-web
  sudo ln -sf /etc/nginx/sites-available/yurots-web /etc/nginx/sites-enabled/yurots-web
  sudo nginx -t
  sudo systemctl reload nginx
  proxy_code="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/ || true)"
  echo "nginx proxy 127.0.0.1:8080 -> HTTP $proxy_code"
  if [[ "$proxy_code" != "200" ]]; then
    echo "nginx sigue fallando. Revisá:" >&2
    echo "  sudo grep -R proxy_pass /etc/nginx/sites-enabled/" >&2
    echo "  sudo tail -20 /var/log/nginx/error.log" >&2
    exit 1
  fi
else
  echo "nginx no instalado; accedé directo a http://IP:8081/"
fi

echo "OK — http://159.223.110.159:8080/ debería andar."
