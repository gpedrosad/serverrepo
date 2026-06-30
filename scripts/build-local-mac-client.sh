#!/usr/bin/env bash
# Empaqueta un launcher de OTClientV8 para probar Retro76 en local (127.0.0.1).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
ROOT="$(resolve_project_root)"

OTC_DIR="${OTCLIENT_DIR:-$HOME/Downloads/otclientv8-master}"
DESKTOP_DIR="$HOME/Desktop/Retro76-Cliente-Local-Mac"
ZIP_PATH="$HOME/Desktop/Retro76-Cliente-Local-Mac.zip"
IP="127.0.0.1"

if [[ ! -x "$OTC_DIR/otclient_mac" ]]; then
  echo "Falta OTClientV8 en $OTC_DIR (otclient_mac)" >&2
  echo "Descargá otclientv8-master y dejalo en ~/Downloads/otclientv8-master" >&2
  exit 1
fi

mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/Iniciar Cliente.command" <<EOF
#!/bin/bash
cd "$ROOT"
export OTCLIENT_DIR="$OTC_DIR"
./scripts/play-yurots-client.sh
EOF
chmod +x "$DESKTOP_DIR/Iniciar Cliente.command"

cat > "$DESKTOP_DIR/LEEME.txt" <<EOF
Retro76 — Cliente local (Mac)
=============================

1. Asegurate de que el servidor local esté corriendo:
   cd $ROOT
   docker compose -f docker-compose.prod.yml up -d yurots

2. Doble clic en "Iniciar Cliente.command"
   (si macOS lo bloquea: clic derecho → Abrir)

3. En el login elegí Retro76 → cuenta numérica + contraseña.

Servidor: $IP:7171
Web local (opcional): ./scripts/web.sh → http://127.0.0.1:8080/

OTClient: $OTC_DIR
EOF

# Parchear init.lua del OTClient para 127.0.0.1 sin abrir el juego
python3 - "$OTC_DIR/init.lua" "$IP" <<'PY'
import re, sys
path, ip = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
new, n = re.subn(
    r'(Servers\s*=\s*\{\s*\n\s*)(YurOTS|Retro76)(\s*=\s*")[^"]*(")',
    rf'\g<1>Retro76\g<3>{ip}:7171:760\4',
    text,
    count=1,
)
if not n:
    sys.exit("No se pudo actualizar Servers.Retro76 en init.lua")
open(path, "w", encoding="utf-8").write(new)
print(f"init.lua → Retro76 = {ip}:7171:760")
PY

THINGS="$OTC_DIR/data/things/760"
if [[ ! -f "$THINGS/Tibia.dat" || ! -f "$THINGS/Tibia.spr" ]]; then
  mkdir -p "$THINGS"
  cp "$HOME/Downloads/tibia76/Tibia.dat" "$HOME/Downloads/tibia76/Tibia.spr" "$THINGS/"
fi

if [[ -f "$ZIP_PATH" ]]; then
  rm -f "$ZIP_PATH"
fi
(
  cd "$HOME/Desktop"
  zip -rq "$(basename "$ZIP_PATH")" "$(basename "$DESKTOP_DIR")"
)

echo ""
echo "Cliente local listo:"
echo "  Carpeta: $DESKTOP_DIR"
echo "  ZIP:     $ZIP_PATH"
echo "  Servidor: $IP:7171 (docker compose -f docker-compose.prod.yml up -d yurots)"
echo ""
echo "Doble clic en: $DESKTOP_DIR/Iniciar Cliente.command"
