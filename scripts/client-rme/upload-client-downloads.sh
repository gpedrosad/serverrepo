#!/usr/bin/env bash
# Sube ZIPs del cliente y archivos del updater a web/ en el VPS.
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
DL="$ROOT/web/downloads"
UPDATER_FILES="$ROOT/web/updater/files"
VPS="${VPS:-root@64.176.20.238}"
REMOTE="${REMOTE:-/root/yurots-principal/web/downloads}"
REMOTE_UPDATER="${REMOTE_UPDATER:-/root/yurots-principal/web/updater/files}"

for f in Retro76-Windows.zip Retro76-Mac.zip Retro76-Sprites-760.zip; do
  if [[ ! -f "$DL/$f" ]]; then
    echo "Falta $DL/$f"
    echo "Corré: ./scripts/publish-client-patcher.sh  (o build-zips.sh en clienteretro)"
    exit 1
  fi
done

if [[ ! -f "$UPDATER_FILES/data/things/760/Tibia.dat" || ! -f "$UPDATER_FILES/data/things/760/Tibia.spr" ]]; then
  echo "Faltan archivos del updater en $UPDATER_FILES/data/things/760/"
  echo "Corré primero: ./scripts/publish-client-patcher.sh"
  exit 1
fi

echo "==> Subiendo ZIPs a $VPS:$REMOTE"
rsync -az --progress \
  "$DL/Retro76-Windows.zip" \
  "$DL/Retro76-Mac.zip" \
  "$DL/Retro76-Sprites-760.zip" \
  "$VPS:$REMOTE/"

echo "==> Subiendo parche updater a $VPS:$REMOTE_UPDATER"
ssh "$VPS" "mkdir -p $REMOTE_UPDATER/data/things/760"
rsync -az --progress "$UPDATER_FILES/" "$VPS:$REMOTE_UPDATER/"

echo "==> Subiendo API updater (server.py, client_updater.py)"
rsync -az --progress \
  "$ROOT/web/server.py" \
  "$ROOT/web/client_updater.py" \
  "$ROOT/web/index.html" \
  "$VPS:/root/yurots-principal/web/"

ssh "$VPS" "ls -lh $REMOTE/ $REMOTE_UPDATER/data/things/760/ && systemctl restart yurots-web"
echo "OK: https://retro76.cl/downloads/Retro76-Windows.zip"
echo "OK: https://retro76.cl/downloads/Retro76-Sprites-760.zip"
echo "OK: https://retro76.cl/api/updater.php"
