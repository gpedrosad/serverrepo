#!/usr/bin/env bash
# Lanza OTClientV8 (otclientv8-master) apuntando a YurOTS.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
ROOT="$(resolve_project_root)"
CONFIG="$ROOT/server/YurOTS/ots/config.lua"

OTC_DIR="${OTCLIENT_DIR:-$HOME/Downloads/otclientv8-master}"
INIT_LUA="$OTC_DIR/init.lua"

if [[ ! -d "$OTC_DIR" ]]; then
  echo "No encontré OTClientV8 en $OTC_DIR"
  echo "Descargá otclientv8-master y poné OTCLIENT_DIR o dejalo en ~/Downloads/otclientv8-master"
  exit 1
fi

if [[ ! -f "$INIT_LUA" ]]; then
  echo "No existe $INIT_LUA"
  exit 1
fi

IP="$(python3 - "$CONFIG" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r'^\s*ip\s*=\s*"([^"]+)"\s*$', text, re.M)
print(m.group(1) if m else "127.0.0.1")
PY
)"

python3 - "$INIT_LUA" "$IP" <<'PY'
import re, sys
path, ip = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
new, n = re.subn(
    r'(Servers\s*=\s*\{\s*\n\s*YurOTS\s*=\s*")[^"]*(")',
    rf'\g<1>{ip}:7171:760\2',
    text,
    count=1,
)
if not n:
    sys.exit("No se pudo actualizar Servers.YurOTS en init.lua")
open(path, "w", encoding="utf-8").write(new)
PY

# Sprites 7.6
THINGS="$OTC_DIR/data/things/760"
if [[ ! -f "$THINGS/Tibia.dat" || ! -f "$THINGS/Tibia.spr" ]]; then
  mkdir -p "$THINGS"
  SRC="$HOME/Downloads/tibia76"
  if [[ -f "$SRC/Tibia.dat" && -f "$SRC/Tibia.spr" ]]; then
    cp "$SRC/Tibia.dat" "$SRC/Tibia.spr" "$THINGS/"
  else
    echo "Faltan Tibia.dat/spr en $THINGS (copiá desde tibia76)" >&2
    exit 1
  fi
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  CLIENT="$OTC_DIR/otclient_mac"
  if [[ ! -x "$CLIENT" ]]; then
    chmod +x "$CLIENT" 2>/dev/null || true
  fi
  if [[ ! -f "$CLIENT" ]]; then
    echo "No hay otclient_mac en $OTC_DIR" >&2
    exit 1
  fi
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
