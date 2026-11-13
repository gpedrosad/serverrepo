#!/bin/bash
# Instala (o reinstala) en la ThinkPad los servicios de usuario del sitio de mapas:
#   retro76-mapas.service          sirve ~/apps/retro76-mapas en http://192.168.1.17:8077 (toda la red)
#   retro76-mapas-refresh.timer    cada 10 min corre thinkpad-maps.sh (mapas al día con lo deployado)
# Uso: scripts/docs-site/install-thinkpad.sh        Desinstalar: scripts/docs-site/install-thinkpad.sh --remove
set -euo pipefail

UNITS="$HOME/.config/systemd/user"
BIN="$HOME/.local/share/retro76-mapas"   # copia fija de los scripts: el main deployado puede no tenerlos
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SITE="$HOME/apps/retro76-mapas"
PORT="${PORT:-8077}"

if [ "${1:-}" = "--remove" ]; then
    systemctl --user disable --now retro76-mapas.service retro76-mapas-refresh.timer 2>/dev/null || true
    rm -f "$UNITS/retro76-mapas.service" "$UNITS/retro76-mapas-refresh.service" "$UNITS/retro76-mapas-refresh.timer"
    systemctl --user daemon-reload
    echo "servicios quitados"
    exit 0
fi

mkdir -p "$UNITS" "$SITE" "$BIN"
cp "$REPO/scripts/docs-site/thinkpad-maps.sh" "$REPO/scripts/docs-site/thinkpad-index.py" "$BIN/"
cat > "$UNITS/retro76-mapas.service" <<EOF
[Unit]
Description=Retro76 mapas (sitio estático en $SITE)
After=network-online.target

[Service]
ExecStart=/usr/bin/python3 -m http.server $PORT --bind 0.0.0.0 --directory $SITE
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

cat > "$UNITS/retro76-mapas-refresh.service" <<EOF
[Unit]
Description=Retro76 mapas: regenerar si cambió lo deployado

[Service]
Type=oneshot
ExecStart=/bin/bash $BIN/thinkpad-maps.sh
Nice=10
IOSchedulingClass=idle
EOF

cat > "$UNITS/retro76-mapas-refresh.timer" <<EOF
[Unit]
Description=Retro76 mapas: revisar cada 10 minutos

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now retro76-mapas.service retro76-mapas-refresh.timer
echo "listo: http://192.168.1.17:$PORT (registro: journalctl --user -u retro76-mapas-refresh)"
