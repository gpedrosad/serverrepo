#!/usr/bin/env bash
# Deploy seguro en el VPS: actualiza código, compila y reinicia sin tocar players/accounts.
#
# OBLIGATORIO leer antes de ejecutar:
#   scripts/README-DEPLOY-VPS.md
#
# Uso:
#   DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

README="$ROOT/scripts/README-DEPLOY-VPS.md"

if [[ "${DEPLOY_I_READ_README:-}" != "yes" ]]; then
  echo ""
  echo "╔══════════════════════════════════════════════════════════════════╗"
  echo "║  DEPLOY BLOQUEADO — leé la documentación obligatoria            ║"
  echo "╚══════════════════════════════════════════════════════════════════╝"
  echo ""
  echo "  $README"
  echo ""
  echo "Después ejecutá:"
  echo "  DEPLOY_I_READ_README=yes $0"
  echo ""
  exit 1
fi

DATA="$ROOT/server/YurOTS/ots/data"
BACKUP="$HOME/ot-backups/pre-deploy-$(date +%Y%m%d-%H%M%S)"

count_files() {
  local dir="$1" pattern="$2"
  find "$dir" -maxdepth 1 -name "$pattern" 2>/dev/null | wc -l | tr -d ' '
}

BEFORE_ACCOUNTS=$(count_files "$DATA/accounts" "*.xml")
BEFORE_PLAYERS=$(count_files "$DATA/players" "*.xml")

echo "==> pre-deploy: $BEFORE_ACCOUNTS cuentas, $BEFORE_PLAYERS archivos en players/"
echo "==> backup runtime data"
mkdir -p "$BACKUP"
cp -a "$DATA/players" "$DATA/accounts" "$BACKUP/"
[ -d "$DATA/vip" ] && cp -a "$DATA/vip" "$BACKUP/"
cp -a "$DATA/online.xml" "$DATA/queue.xml" "$BACKUP/" 2>/dev/null || true
[ -f "$DATA/houseitems.xml" ] && cp -a "$DATA/houseitems.xml" "$BACKUP/"
echo "    guardado en $BACKUP"

echo "==> git pull"
git pull origin main

echo "==> restaurar runtime data (por si git tocó algo)"
cp -an "$BACKUP/players/." "$DATA/players/"
cp -an "$BACKUP/accounts/." "$DATA/accounts/"
[ -d "$BACKUP/vip" ] && mkdir -p "$DATA/vip" && cp -an "$BACKUP/vip/." "$DATA/vip/"
[ -f "$BACKUP/online.xml" ] && cp -an "$BACKUP/online.xml" "$DATA/online.xml"
[ -f "$BACKUP/queue.xml" ] && cp -an "$BACKUP/queue.xml" "$DATA/queue.xml"
[ -f "$BACKUP/houseitems.xml" ] && cp -an "$BACKUP/houseitems.xml" "$DATA/houseitems.xml"

AFTER_ACCOUNTS=$(count_files "$DATA/accounts" "*.xml")
AFTER_PLAYERS=$(count_files "$DATA/players" "*.xml")

echo "==> post-restore: $AFTER_ACCOUNTS cuentas, $AFTER_PLAYERS archivos en players/"

if [[ "$AFTER_ACCOUNTS" -lt "$BEFORE_ACCOUNTS" ]] || [[ "$AFTER_PLAYERS" -lt "$BEFORE_PLAYERS" ]]; then
  echo ""
  echo "ERROR: bajó el número de cuentas o personajes tras el deploy."
  echo "       NO reinicies. Restaurá desde: $BACKUP"
  echo "       Si usaste git stash antes, ver scripts/README-DEPLOY-VPS.md § Recuperación"
  echo ""
  exit 1
fi

echo "==> compile (container parado para no tocar el binario en uso)"
docker compose -f docker-compose.prod.yml stop -t 45 yurots
docker compose -f docker-compose.prod.yml run --rm --entrypoint bash yurots -c \
  'cd /app/YurOTS/ots/source && make clean && make -j"$(nproc 2>/dev/null || echo 4)" yurots'

echo "==> validar mapa vs casas (solo lectura)"
python3 "$ROOT/scripts/sync-houses-with-map.py" --dry-run || {
  echo ""
  echo "ERROR: houses.xml tiene tiles que no existen en test.otbm."
  echo "       Arreglá el mapa antes de levantar el servidor."
  exit 1
}

echo "==> restart services"
docker compose -f docker-compose.prod.yml up -d yurots
if systemctl is-active --quiet yurots-web 2>/dev/null; then
  systemctl restart yurots-web
fi

echo "==> post-deploy: esperar arranque"
ok=0
for _ in $(seq 1 60); do
  if docker logs yurots 2>&1 | tail -40 | grep -q "Could not load houses"; then
    echo ""
    echo "ERROR: el servidor no pudo cargar casas — revisá test.otbm / houses.xml"
    docker logs yurots --tail 25
    exit 1
  fi
  if docker logs yurots 2>&1 | tail -8 | grep -q "Retro76 Server Running"; then
    ok=1
    break
  fi
  sleep 1
done
if [[ "$ok" -ne 1 ]]; then
  echo "ERROR: el servidor no llegó a 'Server Running' en 60s"
  docker logs yurots --tail 25
  exit 1
fi

chmod +x "$ROOT/scripts/healthcheck-ot.sh" 2>/dev/null || true
if ! "$ROOT/scripts/healthcheck-ot.sh" 127.0.0.1 7171; then
  echo "ERROR: healthcheck en 7171 falló tras el deploy"
  exit 1
fi
echo "    healthcheck 7171 OK"

echo ""
echo "Deploy OK. Backup en $BACKUP"
