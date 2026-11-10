#!/bin/bash
# Instala (o reinstala) en la Mac mini los LaunchAgents del sitio local de docs:
#   com.gonzalo.retro76-docs       sirve ~/apps/retro76-docs en http://127.0.0.1:8765
#   com.gonzalo.retro76-docs-maps  cada 10 min corre refresh-maps.sh (mapas al día con main)
# Uso: scripts/docs-site/install-agents.sh          Desinstalar: scripts/docs-site/install-agents.sh --remove
set -euo pipefail

SITE="$HOME/apps/retro76-docs"
WT="$HOME/proyectos/serverrepo-docs-map"
LA="$HOME/Library/LaunchAgents"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
uid="$(id -u)"

for label in com.gonzalo.retro76-docs com.gonzalo.retro76-docs-maps; do
    launchctl bootout "gui/$uid/$label" 2>/dev/null || true
    rm -f "$LA/$label.plist"
done
if [ "${1:-}" = "--remove" ]; then
    echo "agentes quitados"
    exit 0
fi

[ -d "$SITE" ] || { echo "falta el sitio en $SITE"; exit 1; }
if [ ! -d "$WT" ]; then
    git -C "$REPO" fetch -q origin main
    git -C "$REPO" worktree add -q --detach "$WT" origin/main
fi

# el server.py suelto de antes (si hay uno escuchando en 8765) se reemplaza por el agente
old="$(lsof -t -nP -iTCP:8765 -sTCP:LISTEN 2>/dev/null || true)"
[ -n "$old" ] && kill $old && sleep 1

cat > "$LA/com.gonzalo.retro76-docs.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.gonzalo.retro76-docs</string>
  <key>ProgramArguments</key><array>
    <string>/opt/homebrew/bin/python3</string><string>-m</string><string>http.server</string>
    <string>8765</string><string>--bind</string><string>127.0.0.1</string>
    <string>--directory</string><string>$SITE</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$SITE/.server.log</string>
  <key>StandardErrorPath</key><string>$SITE/.server.log</string>
</dict></plist>
EOF

cat > "$LA/com.gonzalo.retro76-docs-maps.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.gonzalo.retro76-docs-maps</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string><string>$WT/scripts/docs-site/refresh-maps.sh</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>StartInterval</key><integer>600</integer>
  <key>Nice</key><integer>10</integer>
  <key>LowPriorityIO</key><true/>
  <key>StandardOutPath</key><string>$SITE/.maps.log</string>
  <key>StandardErrorPath</key><string>$SITE/.maps.log</string>
</dict></plist>
EOF

for label in com.gonzalo.retro76-docs com.gonzalo.retro76-docs-maps; do
    plutil -lint -s "$LA/$label.plist"
    launchctl bootstrap "gui/$uid" "$LA/$label.plist"
done
echo "listo: http://127.0.0.1:8765 (mapas al día con main cada 10 min, registro en $SITE/.maps.log)"
