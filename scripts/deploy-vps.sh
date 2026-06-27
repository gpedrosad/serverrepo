#!/usr/bin/env bash
# Deploy seguro en el VPS: actualiza código, compila y reinicia sin tocar players/accounts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DATA="$ROOT/server/YurOTS/ots/data"
BACKUP="$HOME/ot-backups/pre-deploy-$(date +%Y%m%d-%H%M%S)"

echo "==> backup runtime data"
mkdir -p "$BACKUP"
cp -a "$DATA/players" "$DATA/accounts" "$BACKUP/"
[ -d "$DATA/vip" ] && cp -a "$DATA/vip" "$BACKUP/"
cp -a "$DATA/online.xml" "$DATA/queue.xml" "$BACKUP/" 2>/dev/null || true
echo "    guardado en $BACKUP"

echo "==> git pull"
git pull origin main

echo "==> restaurar runtime data (por si git tocó algo)"
cp -an "$BACKUP/players/." "$DATA/players/"
cp -an "$BACKUP/accounts/." "$DATA/accounts/"
[ -d "$BACKUP/vip" ] && mkdir -p "$DATA/vip" && cp -an "$BACKUP/vip/." "$DATA/vip/"
[ -f "$BACKUP/online.xml" ] && cp -an "$BACKUP/online.xml" "$DATA/online.xml"
[ -f "$BACKUP/queue.xml" ] && cp -an "$BACKUP/queue.xml" "$DATA/queue.xml"

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
