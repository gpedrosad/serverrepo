#!/usr/bin/env bash
# Lanza Tibia 7.6 parcheado (Windows exe vía Wine en Mac).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
CLIENT_DIR="$(resolve_project_root)/client-760"
EXE="$CLIENT_DIR/YurOTS.exe"

if [[ ! -f "$EXE" ]]; then
  echo "No hay cliente en $CLIENT_DIR"
  echo "Ejecutá: python3 scripts/patch-tibia760-client.py --desktop"
  exit 1
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  for wine in wine64 wine crossover-wine wine; do
    if command -v "$wine" >/dev/null 2>&1; then
      cd "$CLIENT_DIR"
      exec "$wine" YurOTS.exe
    fi
  done
  echo "Instalá Wine o CrossOver para ejecutar YurOTS.exe en Mac."
  echo "Alternativa: copiá client-760/ a un PC Windows y ejecutá YurOTS.exe."
  exit 1
fi

cd "$CLIENT_DIR"
exec wine YurOTS.exe
