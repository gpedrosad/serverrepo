#!/usr/bin/env bash
# Abre OTClient Zagan test en Terminal.app (Cursor no puede mostrar ventanas X11).
set -euo pipefail
_BOOT="$(cd "$(dirname "$0")" && pwd)"
while [[ ! -f "$_BOOT/resolve-project-root.sh" ]]; do
  _BOOT="$(dirname "$_BOOT")"
  if [[ "$_BOOT" == "/" ]]; then
    echo "ERROR: resolve-project-root.sh no encontrado" >&2
    exit 1
  fi
done
# shellcheck source=scripts/resolve-project-root.sh
source "$_BOOT/resolve-project-root.sh"
ROOT="$(resolve_project_root)"
cd "$ROOT"

export OTCLIENT_DIR="$ROOT/client-local-zagan-test"
export SKIP_ZAGAN_SERVER_RESTART=1
export CLIENT_INSTANCE="${CLIENT_INSTANCE:-1}"

open -a XQuartz 2>/dev/null || true
sleep 2
for d in /private/tmp/com.apple.launchd.*/org.xquartz:0; do
  if [[ -e "$d" ]]; then
    export DISPLAY="$d"
    break
  fi
done
export DISPLAY="${DISPLAY:-:0}"

echo "→ Cliente Zagan test: $OTCLIENT_DIR"
echo "→ Servidor: 127.0.0.1:7171:760 (items-zagan-test.otb)"
exec "$ROOT/scripts/play-yurots-client.sh"
