#!/usr/bin/env bash
# Lanza el cliente OTClient local (solo Retro76 → 127.0.0.1:7171:760).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
ROOT="$(resolve_project_root)"

OTC_DIR="${OTCLIENT_DIR:-$ROOT/client-local}"
INIT_LUA="$OTC_DIR/init.lua"
INSTANCE="${CLIENT_INSTANCE:-1}"

if [[ ! -d "$OTC_DIR" ]]; then
  echo "No encontré el cliente local en $OTC_DIR" >&2
  echo "Ejecutá: rsync desde ~/Downloads/otclientv8-master hacia $ROOT/client-local" >&2
  exit 1
fi

if [[ ! -f "$INIT_LUA" ]]; then
  echo "No existe $INIT_LUA" >&2
  exit 1
fi

# Sprites 7.6
THINGS="$OTC_DIR/data/things/760"
if [[ ! -f "$THINGS/Tibia.dat" || ! -f "$THINGS/Tibia.spr" ]]; then
  mkdir -p "$THINGS"
  for SRC in "$ROOT/rme-client-760" "$HOME/Downloads/tibia76" "$ROOT"; do
    if [[ -f "$SRC/Tibia.dat" && -f "$SRC/Tibia.spr" ]]; then
      cp "$SRC/Tibia.dat" "$SRC/Tibia.spr" "$THINGS/"
      break
    fi
  done
  if [[ ! -f "$THINGS/Tibia.dat" ]]; then
    echo "Faltan Tibia.dat/spr en $THINGS" >&2
    exit 1
  fi
fi

APP_NAME="yurots_local"
if [[ "$INSTANCE" != "1" ]]; then
  APP_NAME="yurots_local_${INSTANCE}"
fi

python3 - "$INIT_LUA" "$APP_NAME" <<'PY'
import re, sys
path, app_name = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
text = re.sub(r'APP_NAME = "[^"]*"', f'APP_NAME = "{app_name}"', text)
text = re.sub(
    r'Servers\s*=\s*\{[^}]*\}',
    'Servers = {\n  ["Retro76 Local"] = "127.0.0.1:7171:760",\n}',
    text,
    count=1,
    flags=re.S,
)
text = re.sub(r'ALLOW_CUSTOM_SERVERS\s*=\s*\w+', 'ALLOW_CUSTOM_SERVERS = false', text)
open(path, "w", encoding="utf-8").write(text)
PY

if [[ "$(uname -s)" == "Darwin" ]]; then
  pkill -f otclient_mac 2>/dev/null || true
  sleep 0.5
  CLIENT="$OTC_DIR/otclient_mac"
  chmod +x "$CLIENT" 2>/dev/null || true
  cd "$OTC_DIR"
  if [[ "$(uname -m)" == "arm64" ]]; then
    exec arch -x86_64 "$CLIENT"
  else
    exec "$CLIENT"
  fi
fi

CLIENT="$OTC_DIR/otclient_gl.exe"
if [[ -f "$CLIENT" ]]; then
  cd "$OTC_DIR"
  exec wine "$CLIENT"
fi

echo "No hay cliente para esta plataforma en $OTC_DIR" >&2
exit 1
