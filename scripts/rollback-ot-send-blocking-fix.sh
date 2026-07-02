#!/usr/bin/env bash
# Vuelve al binario anterior al fix anti-cuelgue (send bloqueante / flush fuera de gameLock).
#
# Uso en VPS:
#   DEPLOY_I_READ_README=yes ./scripts/rollback-ot-send-blocking-fix.sh
#
# Tag de referencia: pre-ot-send-blocking-fix
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TAG="${OT_ROLLBACK_TAG:-pre-ot-send-blocking-fix}"
BINARY="$ROOT/server/YurOTS/ots/source/yurots"
BACKUP_BIN="$ROOT/server/YurOTS/ots/source/yurots.pre-send-blocking-fix"

if [[ "${DEPLOY_I_READ_README:-}" != "yes" ]]; then
  echo "Ejecutá con: DEPLOY_I_READ_README=yes $0"
  exit 1
fi

echo "==> rollback a tag $TAG"
if ! git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "ERROR: tag $TAG no encontrado. Probá: git fetch --tags"
  exit 1
fi

CURRENT="$(git rev-parse --short HEAD)"
TARGET="$(git rev-parse --short "$TAG")"
echo "    HEAD actual: $CURRENT"
echo "    destino:     $TARGET ($TAG)"

if [[ -f "$BINARY" && ! -f "$BACKUP_BIN" ]]; then
  cp -a "$BINARY" "$BACKUP_BIN"
  echo "    backup binario: $BACKUP_BIN"
fi

git checkout "$TAG" -- \
  server/YurOTS/ots/source/game.cpp \
  server/YurOTS/ots/source/networkmessage.cpp \
  server/YurOTS/ots/source/protocol76.cpp

echo "==> recompilar y reiniciar (mismo flujo que deploy-vps)"
docker compose -f docker-compose.prod.yml stop -t 45 yurots
docker compose -f docker-compose.prod.yml run --rm --entrypoint bash yurots -c \
  'cd /app/YurOTS/ots/source && make clean && make -j"$(nproc 2>/dev/null || echo 4)" yurots'

docker compose -f docker-compose.prod.yml up -d yurots
sleep 8
python3 "$ROOT/scripts/ot-probe.py" 127.0.0.1 7171

echo ""
echo "Rollback de código aplicado (archivos fuente en $TARGET)."
echo "Para volver al fix: git checkout main -- esos .cpp && DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh"
