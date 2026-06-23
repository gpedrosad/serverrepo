#!/usr/bin/env bash
# Configura rutas del client 7.6 para Remere (formato compatible con RME).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
PROJECT_ROOT="$(resolve_project_root)"

CLIENT_DIR="$PROJECT_ROOT/rme-client-760"
RME_ROOT="${RME_ROOT:-$HOME/dev/rme}"
RME_BUILD="${RME_BUILD:-$RME_ROOT/build}"
RME_CFG_GLOBAL="$HOME/Library/Preferences/.rme/rme.cfg"
RME_CFG_LOCAL="$RME_BUILD/rme.cfg"

if [[ ! -f "$CLIENT_DIR/Tibia.dat" || ! -f "$CLIENT_DIR/Tibia.spr" ]]; then
  echo "ERROR: Faltan assets en $CLIENT_DIR"
  echo "Ejecutá primero: $SCRIPT_DIR/setup-rme-client.sh"
  exit 1
fi

xattr -d com.apple.quarantine "$CLIENT_DIR/Tibia.dat" 2>/dev/null || true
xattr -d com.apple.quarantine "$CLIENT_DIR/Tibia.spr" 2>/dev/null || true

mkdir -p "$(dirname "$RME_CFG_GLOBAL")"
mkdir -p "$RME_BUILD" "$RME_ROOT"

# Instalar assets en todas las rutas donde RME puede buscarlos.
install_assets() {
  local dir="$1"
  mkdir -p "$dir"
  cp -f "$CLIENT_DIR/Tibia.dat" "$CLIENT_DIR/Tibia.spr" "$dir/" 2>/dev/null || \
    cp "$CLIENT_DIR/Tibia.dat" "$CLIENT_DIR/Tibia.spr" "$dir/"
  xattr -d com.apple.quarantine "$dir/Tibia.dat" 2>/dev/null || true
  xattr -d com.apple.quarantine "$dir/Tibia.spr" 2>/dev/null || true
}

install_assets "$RME_BUILD"
install_assets "$RME_ROOT"

ln -sfn "$CLIENT_DIR/Tibia.dat" "$PROJECT_ROOT/Tibia.dat"
ln -sfn "$CLIENT_DIR/Tibia.spr" "$PROJECT_ROOT/Tibia.spr"

# RME a veces apunta al repo (dev/rme) en vez de build/.
RME_CLIENT_DIR="$CLIENT_DIR"

MAP="$PROJECT_ROOT/server/YurOTS/ots/data/world/test.otbm"
# Centro aproximado de la ciudad (NPCs/spawns de YurOTS).
MAP_POSITION="140:50:7"

patch_cfg() {
  local dest="$1"
  python3 - "$dest" "$RME_CLIENT_DIR" "$MAP" "$MAP_POSITION" <<'PY'
import json
import re
import sys
from pathlib import Path

dest = Path(sys.argv[1])
client_path = sys.argv[2]
map_path = sys.argv[3]
map_position = sys.argv[4]
# Una sola entrada: evita que RME rellene paths vacíos para otras versiones.
assets_line = f'ASSETS_DATA_DIRS=[{{"id":"7.6","path":"{client_path}"}}]'

if dest.exists() and dest.stat().st_size > 0:
    text = dest.read_text(encoding="utf-8", errors="replace")
    if re.search(r"^ASSETS_DATA_DIRS=", text, flags=re.M):
        text = re.sub(r"^ASSETS_DATA_DIRS=.*$", assets_line, text, count=1, flags=re.M)
    elif "[Version]" in text:
        text = text.replace("[Version]\n", f"[Version]\n{assets_line}\n", 1)
    else:
        text = f"[Version]\n{assets_line}\n\n" + text
    if re.search(r"^CHECK_SIGNATURES=", text, flags=re.M):
        text = re.sub(r"^CHECK_SIGNATURES=.*$", "CHECK_SIGNATURES=0", text, count=1, flags=re.M)
    elif "[Version]" in text:
        text = text.replace("[Version]\n", "[Version]\nCHECK_SIGNATURES=0\n", 1)
    if re.search(r"^DEFAULT_CLIENT_VERSION=", text, flags=re.M):
        text = re.sub(r"^DEFAULT_CLIENT_VERSION=.*$", "DEFAULT_CLIENT_VERSION=3", text, count=1, flags=re.M)
    for key, val in [
        ("ONLY_ONE_INSTANCE", "0"),
        ("WELCOME_DIALOG", "0"),
        ("WORKER_THREADS", "1"),
    ]:
        if re.search(rf"^{key}=", text, flags=re.M):
            text = re.sub(rf"^{key}=.*$", f"{key}={val}", text, count=1, flags=re.M)
        elif "[Editor]" in text:
            text = text.replace("[Editor]\n", f"[Editor]\n{key}={val}\n", 1)
    for key, val in [
        ("RECENT_EDITED_MAP_PATH", map_path),
        ("RECENT_EDITED_MAP_POSITION", map_position),
    ]:
        if re.search(rf"^{key}=", text, flags=re.M):
            text = re.sub(rf"^{key}=.*$", f"{key}={val}", text, count=1, flags=re.M)
        else:
            text = f"{key}={val}\n" + text
    for key, val in [
        ("SHOW_AS_MINIMAP", "0"),
        ("SHOW_ITEMS", "1"),
        ("HIDE_ITEMS_WHEN_ZOOMED", "0"),
    ]:
        if re.search(rf"^{key}=", text, flags=re.M):
            text = re.sub(rf"^{key}=.*$", f"{key}={val}", text, count=1, flags=re.M)
        elif "[View]" in text:
            text = text.replace("[View]\n", f"[View]\n{key}={val}\n", 1)
        elif "[Graphics]" in text and key == "HIDE_ITEMS_WHEN_ZOOMED":
            text = text.replace("[Graphics]\n", f"[Graphics]\n{key}={val}\n", 1)
    dest.write_text(text, encoding="utf-8")
else:
    dest.write_text(
        "[Version]\n"
        "CHECK_SIGNATURES=0\n"
        "DEFAULT_CLIENT_VERSION=3\n"
        f"{assets_line}\n\n"
        "[Editor]\n"
        "DEFAULT_CLIENT_VERSION=3\n"
        "ONLY_ONE_INSTANCE=0\n"
        "WELCOME_DIALOG=0\n"
        "WORKER_THREADS=1\n\n"
        "[View]\n"
        "SHOW_AS_MINIMAP=0\n"
        "SHOW_ITEMS=1\n\n"
        "[Graphics]\n"
        "HIDE_ITEMS_WHEN_ZOOMED=0\n",
        encoding="utf-8",
    )
    text = dest.read_text(encoding="utf-8")
    text = f"RECENT_EDITED_MAP_PATH={map_path}\nRECENT_EDITED_MAP_POSITION={map_position}\n" + text
    dest.write_text(text, encoding="utf-8")

raw = None
for line in dest.read_text(encoding="utf-8").splitlines():
    if line.startswith("ASSETS_DATA_DIRS="):
        raw = line.split("=", 1)[1].strip()
        break
if raw is None:
    raise SystemExit(f"No ASSETS_DATA_DIRS in {dest}")
if raw.startswith('"') and raw.endswith('"'):
    raw = raw[1:-1].replace('""', '"')
parsed = json.loads(raw)
assert parsed[0]["path"] == client_path
print(f"OK {dest} -> {client_path}")
PY
}

patch_cfg "$RME_CFG_GLOBAL"
patch_cfg "$RME_CFG_LOCAL"

if [[ ! -e "$RME_BUILD/data" && -d "$RME_ROOT/data" ]]; then
  ln -sf ../data "$RME_BUILD/data"
  echo "Symlink: $RME_BUILD/data -> ../data"
fi

echo ""
echo "Client 7.6: $RME_CLIENT_DIR"
echo "Fallback:   $RME_ROOT/ y $RME_BUILD/"
echo "Mapa: $MAP"
echo "Posición inicial: $MAP_POSITION (centro ciudad)"
