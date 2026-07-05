#!/usr/bin/env bash
# Publica Tibia.dat/spr Zagan para el updater OTCv8 y opcionalmente sincroniza clienteretro.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
ROOT="$(resolve_project_root)"

CLIENTERETRO="${CLIENTERETRO:-$HOME/clienteretro}"
SRC="$ROOT/zagan-test/client-things/760"
DEST="$ROOT/web/updater/files/data/things/760"
SKIP_CLIENTERETRO="${SKIP_CLIENTERETRO:-0}"

"$ROOT/scripts/install-zagan-test-env.sh"

if [[ ! -f "$SRC/Tibia.dat" || ! -f "$SRC/Tibia.spr" ]]; then
  echo "ERROR: No hay pack Zagan en $SRC" >&2
  exit 1
fi

mkdir -p "$DEST"
cp "$SRC/Tibia.dat" "$DEST/Tibia.dat"
cp "$SRC/Tibia.spr" "$DEST/Tibia.spr"
echo "OK updater files → $DEST"
echo "  .dat $(wc -c < "$DEST/Tibia.dat") bytes"
echo "  .spr $(wc -c < "$DEST/Tibia.spr") bytes"

python3 - <<'PY' "$DEST"
import sys
import zlib
from pathlib import Path

dest = Path(sys.argv[1])
for name in ("Tibia.dat", "Tibia.spr"):
    path = dest / name
    digest = zlib.crc32(path.read_bytes()) & 0xFFFFFFFF
    checksum = format(digest, "x").lstrip("0") or "0"
    print(f"  /data/things/760/{name} → crc32b {checksum}")
PY

if [[ "$SKIP_CLIENTERETRO" != "1" && -x "$CLIENTERETRO/sync-from-yurots.sh" ]]; then
  YUROTS_ROOT="$ROOT" "$CLIENTERETRO/sync-from-yurots.sh"
  if [[ -x "$CLIENTERETRO/build-zips.sh" ]]; then
    CLIENTERETRO_DIST="$ROOT/web/downloads" "$CLIENTERETRO/build-zips.sh"
  fi
fi

SPRITES_ZIP="$ROOT/web/downloads/Retro76-Sprites-760.zip"
STAGE="$(mktemp -d)"
mkdir -p "$STAGE/data/things/760"
cp "$SRC/Tibia.dat" "$STAGE/data/things/760/Tibia.dat"
cp "$SRC/Tibia.spr" "$STAGE/data/things/760/Tibia.spr"
(
  cd "$STAGE"
  export COPYFILE_DISABLE=1
  zip -r -y "$SPRITES_ZIP" data >/dev/null
)
rm -rf "$STAGE"
echo "OK sprites zip → $SPRITES_ZIP ($(wc -c < "$SPRITES_ZIP") bytes)"

echo ""
echo "Siguiente paso (VPS): ./scripts/upload-client-downloads.sh"
