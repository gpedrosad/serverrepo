#!/usr/bin/env bash
# Levanta la web YurOTS en el VPS (detrás de nginx en :8080).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
ROOT="$(resolve_project_root)"

cd "$ROOT"

if [[ -f .git/config ]]; then
  git pull --ff-only origin main || true
fi

mkdir -p web/state
mkdir -p server/YurOTS/ots/data/accounts server/YurOTS/ots/data/players

docker compose -f docker-compose.prod.yml -f docker-compose.vps.yml up -d --force-recreate web

sleep 2
code="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8081/api/data || true)"
echo "Backend local :8081 -> HTTP $code"

if [[ "$code" != "200" ]]; then
  echo "Revisá logs: docker logs yurots-web --tail 50" >&2
  exit 1
fi

echo "OK. nginx :8080 debe apuntar a 127.0.0.1:8081 (deploy/nginx-yurots-web.conf)."
