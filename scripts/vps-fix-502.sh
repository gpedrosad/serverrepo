#!/usr/bin/env bash
# Fix 502 en el VPS: levanta la web y alinea nginx con Docker.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
ROOT="$(resolve_project_root)"

cd "$ROOT"

echo "== YurOTS: fix 502 web =="

if [[ -f .git/config ]]; then
  git pull --ff-only origin main || true
fi

mkdir -p web/state
mkdir -p server/YurOTS/ots/data/accounts server/YurOTS/ots/data/players

start_web() {
  local publish="$1"
  echo "WEB_PUBLISH=$publish" > .env
  docker compose -f docker-compose.prod.yml up -d --force-recreate web yurots
  sleep 4
}

check_backend() {
  local url="$1"
  curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000"
}

disable_other_nginx_8080() {
  command -v nginx >/dev/null || return 0
  local f
  for f in /etc/nginx/sites-enabled/*; do
    [[ -e "$f" ]] || continue
    [[ "$f" == *yurots-web* ]] && continue
    if sudo grep -qE 'listen(\s+\[::\])?\s+8080' "$f" 2>/dev/null; then
      echo "Desactivando nginx conflictivo: $f"
      sudo rm -f "$f"
    fi
  done
  for f in /etc/nginx/conf.d/*.conf; do
    [[ -e "$f" ]] || continue
    if sudo grep -qE 'listen(\s+\[::\])?\s+8080' "$f" 2>/dev/null; then
      echo "Renombrando conf.d conflictivo: $f"
      sudo mv "$f" "${f}.disabled" 2>/dev/null || true
    fi
  done
}

setup_nginx_proxy() {
  disable_other_nginx_8080
  sudo cp deploy/nginx-yurots-web.conf /etc/nginx/sites-available/yurots-web
  sudo ln -sf /etc/nginx/sites-available/yurots-web /etc/nginx/sites-enabled/yurots-web
  sudo nginx -t
  sudo systemctl reload nginx
}

# Modo 1: nginx :8080 -> docker :8081
start_web "127.0.0.1:8081:8080"
backend_code="$(check_backend http://127.0.0.1:8081/api/data)"
echo "Docker 127.0.0.1:8081 -> HTTP $backend_code"

if [[ "$backend_code" != "200" ]]; then
  echo "ERROR: la web no responde en :8081" >&2
  docker ps -a | grep yurots || true
  docker logs yurots-web --tail 50 >&2 || true
  exit 1
fi

if command -v nginx >/dev/null; then
  echo "Configurando nginx proxy 8080 -> 8081..."
  setup_nginx_proxy
  proxy_code="$(check_backend http://127.0.0.1:8080/)"
  echo "nginx 127.0.0.1:8080 -> HTTP $proxy_code"

  if [[ "$proxy_code" != "200" ]]; then
    echo "Proxy nginx falló; aplicando fallback directo en :8080..." >&2
    sudo rm -f /etc/nginx/sites-enabled/yurots-web
    disable_other_nginx_8080
    sudo systemctl reload nginx 2>/dev/null || sudo systemctl stop nginx || true
    start_web "8080:8080"
    direct_code="$(check_backend http://127.0.0.1:8080/api/data)"
    echo "Docker directo 8080 -> HTTP $direct_code"
    if [[ "$direct_code" != "200" ]]; then
      sudo tail -30 /var/log/nginx/error.log 2>/dev/null || true
      docker logs yurots-web --tail 30 >&2 || true
      exit 1
    fi
  fi
else
  start_web "8080:8080"
fi

public_code="$(check_backend http://127.0.0.1:8080/)"
echo "Check local :8080 -> HTTP $public_code"
echo "OK — http://159.223.110.159:8080/"
