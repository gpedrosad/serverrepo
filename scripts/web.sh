#!/usr/bin/env bash
# Web local — sin Docker, sin VPS. Lee los XML del server en disco.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p web/state

docker stop yurots-web 2>/dev/null || true

export OT_HOST=127.0.0.1
export SERVER_IP=127.0.0.1
echo "YurOTS web → http://localhost:8080/"
exec python3 web/server.py
