#!/usr/bin/env bash
# Sincroniza items.otb + extensión de paleta para RME Zagan test.
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

ZAGAN_OTB="$ROOT/zagan-test/server-items/items.otb"
ZAGAN_XML="$ROOT/zagan-test/server-items/items.xml"
RME_DATA="$ROOT/rme-zagan-test-root/data"
RME_CLIENT="$ROOT/rme-client-760-zagan-test"
RME_SUPPORT="$HOME/Library/Application Support/.rme/data/760"
EXT_SRC="$ROOT/rme-extensions/yurots-zagan-items.xml"
BASE_RME_BIN="$HOME/dev/rme/build/rme"

if [[ ! -f "$ZAGAN_OTB" ]]; then
  echo "ERROR: falta $ZAGAN_OTB — corré install-zagan-test-env.sh primero" >&2
  exit 1
fi

python3 "$ROOT/scripts/generate-rme-zagan-extension.py"

mkdir -p "$RME_DATA/760" "$RME_CLIENT" "$RME_SUPPORT" \
  "$ROOT/rme-zagan-test-root/extensions" \
  "$ROOT/rme-zagan-test-root/build/extensions" \
  "$ROOT/rme-zagan-test-root/build/data/760"

if [[ -x "$BASE_RME_BIN" ]]; then
  mkdir -p "$ROOT/rme-zagan-test-root/build"
  cp -f "$BASE_RME_BIN" "$ROOT/rme-zagan-test-root/build/rme"
  chmod +x "$ROOT/rme-zagan-test-root/build/rme"
  xattr -d com.apple.quarantine "$ROOT/rme-zagan-test-root/build/rme" 2>/dev/null || true
fi

cp -f "$ZAGAN_OTB" "$RME_DATA/760/items.otb"
cp -f "$ZAGAN_OTB" "$RME_CLIENT/items.otb"
cp -f "$ZAGAN_OTB" "$RME_SUPPORT/items.otb"
cp -f "$ZAGAN_OTB" "$ROOT/rme-zagan-test-root/build/data/760/items.otb"
ln -sfn "data/760" "$ROOT/rme-zagan-test-root/760"

if [[ -f "$ZAGAN_XML" ]]; then
  cp -f "$ZAGAN_XML" "$RME_DATA/760/items.xml"
  cp -f "$ZAGAN_XML" "$RME_SUPPORT/items.xml"
  cp -f "$ZAGAN_XML" "$ROOT/rme-zagan-test-root/build/data/760/items.xml"
fi

cp -f "$EXT_SRC" "$ROOT/rme-zagan-test-root/extensions/yurots-zagan-items.xml"
cp -f "$EXT_SRC" "$ROOT/rme-zagan-test-root/build/extensions/yurots-zagan-items.xml"

echo "OK items.otb → RME data + client + Application Support"
echo "OK extensión → yurots-zagan-items.xml"
