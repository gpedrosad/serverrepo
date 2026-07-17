#!/usr/bin/env bash
# Rebuild and install the 5 Zagan+Square test items into isolated client/RME packs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
while [[ ! -f "$SCRIPT_DIR/resolve-project-root.sh" ]]; do
  SCRIPT_DIR="$(dirname "$SCRIPT_DIR")"
  if [[ "$SCRIPT_DIR" == "/" ]]; then
    echo "ERROR: resolve-project-root.sh no encontrado" >&2
    exit 1
  fi
done
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
ROOT="$(resolve_project_root)"

BASE_CLIENT="$ROOT/client-local"
TEST_CLIENT="$ROOT/client-local-zagan-test"
TEST_RME_CLIENT="$ROOT/rme-client-760-zagan-test"
TEST_RME_ROOT="$ROOT/rme-zagan-test-root"
BASE_RME_ROOT="${RME_BASE_ROOT:-$HOME/dev/rme}"
BASE_RME_BUILD="$BASE_RME_ROOT/build"
SERVER_ITEMS_DIR="$ROOT/server/YurOTS/ots/data/items"
GENERATED_DIR="$ROOT/zagan-test"

if [[ ! -d "$BASE_CLIENT" ]]; then
  echo "ERROR: No existe el cliente base en $BASE_CLIENT" >&2
  exit 1
fi

if [[ ! -d "$BASE_RME_ROOT/data/760" ]]; then
  echo "ERROR: No existe la data base de RME en $BASE_RME_ROOT/data/760" >&2
  exit 1
fi

if [[ ! -x "$BASE_RME_BUILD/rme" ]]; then
  echo "ERROR: No existe el binario base de RME en $BASE_RME_BUILD/rme" >&2
  exit 1
fi

python3 "$ROOT/scripts/build_zagan_test_assets.py"
python3 "$ROOT/scripts/sync-zagan-items-web.py"

if [[ ! -d "$TEST_CLIENT" ]]; then
  cp -R "$BASE_CLIENT" "$TEST_CLIENT"
fi

mkdir -p "$TEST_CLIENT/data/things/760" "$TEST_RME_CLIENT" "$SERVER_ITEMS_DIR" "$TEST_RME_ROOT/build"

cp "$GENERATED_DIR/client-things/760/Tibia.dat" "$TEST_CLIENT/data/things/760/Tibia.dat"
cp "$GENERATED_DIR/client-things/760/Tibia.spr" "$TEST_CLIENT/data/things/760/Tibia.spr"

cp "$GENERATED_DIR/rme-client-760-zagan-test/Tibia.dat" "$TEST_RME_CLIENT/Tibia.dat"
cp "$GENERATED_DIR/rme-client-760-zagan-test/Tibia.spr" "$TEST_RME_CLIENT/Tibia.spr"

cp "$GENERATED_DIR/server-items/items.otb" "$SERVER_ITEMS_DIR/items-zagan-test.otb"
cp "$GENERATED_DIR/server-items/items.xml" "$SERVER_ITEMS_DIR/items-zagan-test.xml"

if [[ ! -d "$TEST_RME_ROOT/data" ]]; then
  cp -R "$BASE_RME_ROOT/data" "$TEST_RME_ROOT/data"
fi

cp "$BASE_RME_BUILD/rme" "$TEST_RME_ROOT/build/rme"
chmod +x "$TEST_RME_ROOT/build/rme"

cp "$GENERATED_DIR/rme-client-760-zagan-test/Tibia.dat" "$TEST_RME_ROOT/build/Tibia.dat"
cp "$GENERATED_DIR/rme-client-760-zagan-test/Tibia.spr" "$TEST_RME_ROOT/build/Tibia.spr"
cp "$GENERATED_DIR/rme-client-760-zagan-test/Tibia.dat" "$TEST_RME_ROOT/Tibia.dat"
cp "$GENERATED_DIR/rme-client-760-zagan-test/Tibia.spr" "$TEST_RME_ROOT/Tibia.spr"

mkdir -p "$TEST_RME_ROOT/data/760"
cp "$GENERATED_DIR/server-items/items.otb" "$TEST_RME_ROOT/data/760/items.otb"

chmod +x "$SCRIPT_DIR/setup-rme-zagan-items.sh" 2>/dev/null || true
"$SCRIPT_DIR/setup-rme-zagan-items.sh"

echo "Cliente test: $TEST_CLIENT"
echo "RME client test: $TEST_RME_CLIENT"
echo "RME root test: $TEST_RME_ROOT"
echo "Items test server: $SERVER_ITEMS_DIR/items-zagan-test.otb"
echo "Manifest: $GENERATED_DIR/manifest.json"

if [[ "${SKIP_ZAGAN_SERVER_RESTART:-0}" != "1" ]] && docker ps --format '{{.Names}}' | grep -qx yurots; then
  export YUROTS_ITEMS_OTB="data/items/items-zagan-test.otb"
  export YUROTS_ITEMS_XML="data/items/items-zagan-test.xml"
  echo "→ Reiniciando servidor (el OTB se carga solo al arranque)..."
  cd "$ROOT"
  docker compose up -d yurots
  docker compose restart yurots
  for i in $(seq 1 60); do
    if python3 -c "import socket; s=socket.create_connection(('127.0.0.1',7171),2); s.close()" 2>/dev/null \
      && docker logs yurots 2>&1 | tail -5 | grep -q "Server Running"; then
      echo "→ Servidor listo con items-zagan-test.otb"
      break
    fi
    if [[ "$i" -eq 60 ]]; then
      echo "WARN: el servidor no respondió tras el restart; revisá: docker logs yurots --tail 30" >&2
    fi
    sleep 1
  done
fi

echo "→ Si el cliente ya estaba abierto, cerralo y volvé a correr: ./scripts/play-zagan-test-client.sh"
