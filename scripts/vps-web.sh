#!/usr/bin/env bash
# VPS: Docker directo en :8080 (sin nginx). Consola DigitalOcean:
#   curl -fsSL https://raw.githubusercontent.com/gpedrosad/serverrepo/main/scripts/vps-web.sh | bash
set -euo pipefail

REPO="${YUROTS_REPO:-$HOME/serverrepo}"
URL="${YUROTS_REPO_URL:-https://github.com/gpedrosad/serverrepo.git}"

command -v docker >/dev/null || { echo "Instalá Docker primero." >&2; exit 1; }

if ! command -v git >/dev/null; then
  sudo apt-get update -qq && sudo apt-get install -y git curl
fi

if [[ -d "$REPO/.git" ]]; then
  git -C "$REPO" pull --ff-only origin main
else
  git clone "$URL" "$REPO"
fi

cd "$REPO"
mkdir -p web/state server/YurOTS/ots/data/players

# nginx en :8080 causa 502 — lo apagamos; Docker sirve la web directo
if command -v nginx >/dev/null && systemctl is-active nginx &>/dev/null; then
  sudo systemctl stop nginx
  echo "nginx detenido (liberado puerto 8080)"
fi

docker compose -f docker-compose.prod.yml up -d web yurots

sleep 3
code="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/ || true)"
echo "Web local :8080 -> HTTP $code"
[[ "$code" == "200" ]] || { docker logs yurots-web --tail 30; exit 1; }

echo "OK -> http://159.223.110.159:8080/"
