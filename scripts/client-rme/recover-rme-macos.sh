#!/usr/bin/env bash
# Recuperación antes de abrir RME: XQuartz + binario fresco. Si hay zombies UE, avisa.
set -uo pipefail

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

ue_count=0
while read -r pid state _; do
  [[ -n "${pid:-}" ]] || continue
  if [[ "$state" == *UE* ]]; then
    ue_count=$((ue_count + 1))
  fi
done < <(ps -ax -o pid= -o state= -o comm= 2>/dev/null | awk '$3 ~ /rme$/ || $3 ~ /\/rme$/ || $3 ~ /rme-yurots/')

if [[ "$ue_count" -ge 3 ]]; then
  echo "WARN: $ue_count procesos RME colgados (UE)." >&2
  osascript -e "display alert \"RME puede necesitar reinicio\" message \"Hay $ue_count procesos Remere bloqueados. Si no abre, reiniciá el Mac. Ahora intento abrirlo igual.\" as warning buttons {\"OK\"} default button \"OK\"" 2>/dev/null || true
fi

echo "→ Reiniciando XQuartz..."
osascript -e 'tell application "XQuartz" to quit' 2>/dev/null || true
killall Xquartz X11.bin 2>/dev/null || true
sleep 2
open -a XQuartz
sleep 4

mkdir -p "$ROOT/rme-zagan-test-root/build"
cp -f "${HOME}/dev/rme/build/rme" "$ROOT/rme-zagan-test-root/build/rme"
chmod +x "$ROOT/rme-zagan-test-root/build/rme"
xattr -d com.apple.quarantine "$ROOT/rme-zagan-test-root/build/rme" 2>/dev/null || true

exit 0
