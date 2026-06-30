#!/usr/bin/env bash
# Sube los ZIP del cliente a web/downloads/ en el VPS (no van a git).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
ROOT="$(resolve_project_root)"
DL="$ROOT/web/downloads"
VPS="${VPS:-root@64.176.20.238}"
REMOTE="${REMOTE:-/root/yurots-principal/web/downloads}"

for f in Retro76-Windows.zip Retro76-Mac.zip; do
  if [[ ! -f "$DL/$f" ]]; then
    echo "Falta $DL/$f"
    echo "Copiá los zips desde el build del OTClient o desde ~/Desktop/cliente-oficial-retro-*.zip"
    exit 1
  fi
done

echo "==> Subiendo a $VPS:$REMOTE"
rsync -az --progress "$DL/Retro76-Windows.zip" "$DL/Retro76-Mac.zip" "$VPS:$REMOTE/"
ssh "$VPS" "ls -lh $REMOTE/ && systemctl restart yurots-web"
echo "OK: https://retro76.cl/downloads/Retro76-Windows.zip"
