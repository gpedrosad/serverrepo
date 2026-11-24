#!/usr/bin/env bash
# Trae a la Mac los respaldos automáticos de la ThinkPad (auto-backup-runtime.sh). 24 nov 2026.
#
# Copia ~/backups/auto/ de la ThinkPad a ~/Retro76-backups/thinkpad-auto/ en la Mac, para que los datos de
# jugadores sobrevivan aunque se rompa el disco de la ThinkPad. No borra nada en la Mac (son unos KB por
# respaldo). Prueba la red local y, si no está, Tailscale (alias `thinkpad` y `thinkpad-tailscale` de
# ~/.ssh/config).
#
# Uso (en la Mac):
#   scripts/deploy/pull-auto-backups.sh             # traer ahora
#   scripts/deploy/pull-auto-backups.sh --install   # launchd: todos los días a las 13:00 y al prender
set -euo pipefail

DEST="${PULL_DEST:-$HOME/Retro76-backups/thinkpad-auto}"
LABEL="com.retro76.pull-auto-backups"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Retro76-backups/pull.log"

if [[ "${1:-}" == "--install" ]]; then
  mkdir -p "$DEST" "$(dirname "$PLIST")"
  script="$HOME/Retro76-backups/pull-auto-backups.sh"   # copia fuera del repo: el worktree puede cambiar
  cp "$0" "$script" && chmod +x "$script"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$script</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>13</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
EOF
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  echo "launchd instalado: $PLIST (script $script)"
  exit 0
fi

mkdir -p "$DEST"
for host in thinkpad thinkpad-tailscale; do
  if rsync -a -e "ssh -o BatchMode=yes -o ConnectTimeout=10" "$host:backups/auto/" "$DEST/"; then
    n=$(find "$DEST" -name 'runtime-*.tar.gz' | wc -l | tr -d ' ')
    echo "$(date '+%Y-%m-%d %H:%M:%S') [pull] OK desde $host: $n respaldos en $DEST"
    exit 0
  fi
done
echo "$(date '+%Y-%m-%d %H:%M:%S') [pull] ERROR: no se llegó a la ThinkPad (ni LAN ni Tailscale)"
exit 1
