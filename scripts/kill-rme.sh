#!/usr/bin/env bash
# Mata todas las instancias de Remere's Map Editor (rme).
set -uo pipefail

FORCE="${1:-}"

echo "=== Cierre forzado de Remere (rme) ==="

PIDS=$(pgrep -x rme 2>/dev/null || true)
if [[ -z "$PIDS" ]]; then
  echo "No hay instancias de rme en ejecución."
  exit 0
fi

COUNT=$(echo "$PIDS" | wc -l | tr -d ' ')
echo "Encontrados $COUNT proceso(s): $(echo "$PIDS" | tr '\n' ' ')"

# 1) AppleScript (por si hay ventana activa).
osascript -e 'tell application "System Events" to tell process "rme" to quit' 2>/dev/null || true
osascript -e 'tell application "rme" to quit' 2>/dev/null || true

# 2) Cierre normal + SIGKILL.
killall rme 2>/dev/null || true
sleep 1
while read -r pid; do
  [[ -n "$pid" ]] || continue
  kill -9 "$pid" 2>/dev/null || true
done <<< "$PIDS"
pkill -9 -f '/dev/rme/build/rme' 2>/dev/null || true
pkill -9 -f '[/ ]rme .*test\.otbm' 2>/dev/null || true

# 3) Matar shells padre de open-rme.sh (evita relanzamientos).
pkill -9 -f 'open-rme\.sh' 2>/dev/null || true

if [[ "$FORCE" == "--nuclear" ]]; then
  echo "Reiniciando XQuartz (desbloquea rme colgado en OpenGL)..."
  osascript -e 'tell application "XQuartz" to quit' 2>/dev/null || true
  sleep 2
  killall Xquartz 2>/dev/null || true
  killall X11.bin 2>/dev/null || true
  sleep 2
  killall -9 rme 2>/dev/null || true
  open -a XQuartz 2>/dev/null || true
  sleep 3
  killall -9 rme 2>/dev/null || true
fi

sleep 1
REMAINING=$(pgrep -x rme 2>/dev/null || true)
if [[ -z "$REMAINING" ]]; then
  echo "OK — todos los procesos rme cerrados."
  exit 0
fi

echo ""
echo "Zombies restantes (estado UE = bloqueados en el kernel, no responden a kill -9):"
while read -r pid; do
  [[ -n "$pid" ]] || continue
  ps -p "$pid" -o pid=,state=,etime=,command= 2>/dev/null || true
done <<< "$REMAINING"
echo ""
echo "Probá desde Terminal.app:"
echo "  ~/Desktop/yurots-principal/scripts/kill-rme.sh --nuclear"
echo ""
echo "Si siguen ahí, la única salida es reiniciar el Mac (Apple menu > Reiniciar)."
echo "No abras Remere desde Cursor — solo desde Terminal.app con open-rme.sh"
exit 1
