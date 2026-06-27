#!/usr/bin/env bash
# Deploy seguro en el VPS: actualiza código, compila y reinicia sin tocar players/accounts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> git pull"
git pull origin main

echo "==> compile (dentro del container)"
docker compose -f docker-compose.prod.yml up -d yurots
docker compose -f docker-compose.prod.yml exec -T yurots bash -c \
  'cd /app/YurOTS/ots/source && make -j"$(nproc 2>/dev/null || echo 4)" yurots'

echo "==> restart services"
docker compose -f docker-compose.prod.yml restart yurots
if systemctl is-active --quiet yurots-web 2>/dev/null; then
  systemctl restart yurots-web
fi

sleep 3
docker logs yurots --tail 20
