#!/usr/bin/env bash
# Lanza RME en macOS. Desde Cursor delega a Terminal.app (evita bloqueo UE).
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
PROJECT_ROOT="$(resolve_project_root)"

# Binario estable (el de dev/rme); config/assets en RME_BUILD (zagan o default).
RME_BIN="${RME_REAL:-${RME_BIN:-$HOME/dev/rme/build/rme}}"
RME_BUILD="${RME_BUILD:-$(dirname "$RME_BIN")}"
MAP="${MAP_OVERRIDE:-$PROJECT_ROOT/server/YurOTS/ots/data/world/test.otbm}"
LOG="${RME_LOG:-/tmp/rme-yurots.log}"
TERMINAL_LAUNCHER="$SCRIPT_DIR/open-rme-zagan-terminal.command"

if [[ -n "${VSCODE_IPC_HOOK:-}" || -n "${CURSOR_EXTENSION_HOST_ROLE:-}" ]]; then
  if [[ -x "$TERMINAL_LAUNCHER" ]]; then
    open "$TERMINAL_LAUNCHER"
    echo "OK — RME se abre en Terminal.app (Cursor no puede mostrar la ventana de Remere)."
    echo "Si no aparece, hacé doble clic en: $TERMINAL_LAUNCHER"
    exit 0
  fi
fi

if [[ ! -x "$RME_BIN" ]]; then
  echo "ERROR: no existe $RME_BIN" >&2
  exit 1
fi
if [[ ! -f "$MAP" ]]; then
  echo "ERROR: no existe el mapa: $MAP" >&2
  exit 1
fi

has_ue_zombie() {
  local pid state
  while read -r pid; do
    [[ -n "$pid" ]] || continue
    state=$(ps -p "$pid" -o state= 2>/dev/null | tr -d ' ')
    if [[ "$state" == *UE* ]]; then
      return 0
    fi
  done < <(pgrep -x rme 2>/dev/null || true)
  return 1
}

reset_xquartz() {
  echo "→ Reiniciando XQuartz..."
  osascript -e 'tell application "XQuartz" to quit' 2>/dev/null || true
  killall Xquartz 2>/dev/null || true
  killall X11.bin 2>/dev/null || true
  sleep 2
  open -a XQuartz
  sleep 3
}

killall rme 2>/dev/null || true
sleep 1
while read -r pid; do
  [[ -n "$pid" ]] || continue
  kill -9 "$pid" 2>/dev/null || true
done < <(pgrep -x rme 2>/dev/null || true)

if has_ue_zombie; then
  reset_xquartz
fi
if ! pgrep -x Xquartz >/dev/null 2>&1; then
  open -a XQuartz
  sleep 3
fi

cd "$RME_BUILD"
: >"$LOG"

launch_once() {
  nohup "$RME_BIN" "$MAP" >>"$LOG" 2>&1 &
  disown 2>/dev/null || true
  echo $!
}

RME_PID=$(launch_once)
echo "→ RME pid $RME_PID (log: $LOG)"

for attempt in 1 2 3; do
  sleep 3
  if ! kill -0 "$RME_PID" 2>/dev/null; then
    echo "ERROR: RME terminó al arrancar:" >&2
    tail -30 "$LOG" >&2 || true
    exit 1
  fi
  state=$(ps -p "$RME_PID" -o state= 2>/dev/null | tr -d ' ')
  if [[ "$state" == *UE* ]]; then
    echo "→ Intento $attempt: RME bloqueado (UE)..."
    kill -9 "$RME_PID" 2>/dev/null || true
    reset_xquartz
    RME_PID=$(launch_once)
    continue
  fi
  echo "OK — RME corriendo (pid $RME_PID). Buscá la ventana en el Dock."
  exit 0
done

if [[ -x "$TERMINAL_LAUNCHER" ]]; then
  open "$TERMINAL_LAUNCHER"
  echo "WARN: RME no arrancó aquí; lo abrí en Terminal.app."
  exit 0
fi

echo "ERROR: RME no arrancó. Probá reiniciar el Mac y luego:" >&2
echo "  $TERMINAL_LAUNCHER" >&2
tail -30 "$LOG" >&2 || true
exit 1
