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

count_house_owners() {
  local houses_dir="$1"
  if [[ ! -d "$houses_dir" ]]; then
    echo 0
    return
  fi
  grep -h 'owner name=' "$houses_dir"/*.xml 2>/dev/null | grep -cv 'owner name=""' || echo 0
}

# Flush online players (daily-task storage, inventory, houseitems) to disk
# BEFORE backing up / pulling. Without this, docker stop could lose RAM state.
graceful_stop_yurots() {
  if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'yurots'; then
    echo "==> yurots no está corriendo; skip graceful stop"
    return 0
  fi

  echo "==> graceful save+stop (daily tasks / inventory / houseitems)"
  rm -f "$DATA/.server-save-ok" "$DATA/.request-server-save"
  # File request works once the new binary with checkSaveRequest is live.
  # Also safe no-op on older binaries.
  : > "$DATA/.request-shutdown"

  # Explicit compose stop: sends SIGTERM, marks container stopped so
  # restart: unless-stopped does NOT bring it back mid-deploy.
  docker compose -f docker-compose.prod.yml stop -t 50 yurots || true

  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'yurots'; then
    echo "    WARNING: container aún Up; forzando docker kill"
    docker kill yurots >/dev/null 2>&1 || true
    sleep 2
  else
    echo "    container detenido"
  fi
  rm -f "$DATA/.request-shutdown"
}

BEFORE_ACCOUNTS=$(count_files "$DATA/accounts" "*.xml")
BEFORE_PLAYERS=$(count_files "$DATA/players" "*.xml")
BEFORE_HOUSE_OWNERS=$(count_house_owners "$DATA/houses")

echo "==> pre-deploy: $BEFORE_ACCOUNTS cuentas, $BEFORE_PLAYERS archivos en players/, $BEFORE_HOUSE_OWNERS casas con dueño"

graceful_stop_yurots

echo "==> backup runtime data (post-save)"
mkdir -p "$BACKUP"
cp -a "$DATA/players" "$DATA/accounts" "$BACKUP/"
[ -d "$DATA/vip" ] && cp -a "$DATA/vip" "$BACKUP/"
cp -a "$DATA/online.xml" "$DATA/queue.xml" "$BACKUP/" 2>/dev/null || true
[ -f "$DATA/houseitems.xml" ] && cp -a "$DATA/houseitems.xml" "$BACKUP/"
[ -f "$DATA/private_trainers.xml" ] && cp -a "$DATA/private_trainers.xml" "$BACKUP/"
[ -d "$DATA/houses" ] && cp -a "$DATA/houses" "$BACKUP/"
echo "    guardado en $BACKUP"

echo "==> git pull"
git pull origin main

# Bind-mounted entrypoint lives under server/YurOTS/; keep it in sync with scripts/.
if [[ -f "$ROOT/scripts/docker-entrypoint.sh" ]]; then
  cp -a "$ROOT/scripts/docker-entrypoint.sh" "$ROOT/server/YurOTS/docker-entrypoint.sh"
  chmod +x "$ROOT/server/YurOTS/docker-entrypoint.sh"
fi

echo "==> restaurar runtime data (por si git tocó algo)"
cp -an "$BACKUP/players/." "$DATA/players/"
cp -an "$BACKUP/accounts/." "$DATA/accounts/"
[ -d "$BACKUP/vip" ] && mkdir -p "$DATA/vip" && cp -an "$BACKUP/vip/." "$DATA/vip/"
[ -f "$BACKUP/online.xml" ] && cp -an "$BACKUP/online.xml" "$DATA/online.xml"
[ -f "$BACKUP/queue.xml" ] && cp -an "$BACKUP/queue.xml" "$DATA/queue.xml"
[ -f "$BACKUP/houseitems.xml" ] && cp -a "$BACKUP/houseitems.xml" "$DATA/houseitems.xml"
[ -f "$BACKUP/private_trainers.xml" ] && cp -a "$BACKUP/private_trainers.xml" "$DATA/private_trainers.xml"
if [[ -d "$BACKUP/houses" ]]; then
  mkdir -p "$DATA/houses"
  # Sobrescribe lo que git pull haya pisado (dueños, guests, subowners).
  cp -a "$BACKUP/houses/." "$DATA/houses/"
fi

AFTER_ACCOUNTS=$(count_files "$DATA/accounts" "*.xml")
AFTER_PLAYERS=$(count_files "$DATA/players" "*.xml")
AFTER_HOUSE_OWNERS=$(count_house_owners "$DATA/houses")

echo "==> post-restore: $AFTER_ACCOUNTS cuentas, $AFTER_PLAYERS archivos en players/, $AFTER_HOUSE_OWNERS casas con dueño"

if [[ "$AFTER_ACCOUNTS" -lt "$BEFORE_ACCOUNTS" ]] || [[ "$AFTER_PLAYERS" -lt "$BEFORE_PLAYERS" ]]; then
  echo ""
  echo "ERROR: bajó el número de cuentas o personajes tras el deploy."
  echo "       NO reinicies. Restaurá desde: $BACKUP"
  echo "       Si usaste git stash antes, ver scripts/README-DEPLOY-VPS.md § Recuperación"
  echo ""
  exit 1
fi

if [[ "$AFTER_HOUSE_OWNERS" -lt "$BEFORE_HOUSE_OWNERS" ]]; then
  echo ""
  echo "ERROR: bajó el número de casas con dueño tras el deploy ($BEFORE_HOUSE_OWNERS -> $AFTER_HOUSE_OWNERS)."
  echo "       NO reinicies. Restaurá data/houses/ desde: $BACKUP/houses/"
  echo "       Ver docs/gameplay/HOUSES.md"
  echo ""
  exit 1
fi

echo "==> compile (container ya parado)"
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
