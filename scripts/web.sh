#!/usr/bin/env bash
# Web local — sin Docker, sin VPS. Lee los XML del server en disco.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p web/state

docker stop yurots-web 2>/dev/null || true

if [[ -f web/.items-admin-token ]]; then
  export ITEMS_ADMIN_TOKEN="$(tr -d '[:space:]' < web/.items-admin-token)"
elif [[ -z "${ITEMS_ADMIN_TOKEN:-}" ]]; then
  ITEMS_ADMIN_TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"
  printf '%s\n' "$ITEMS_ADMIN_TOKEN" > web/.items-admin-token
  chmod 600 web/.items-admin-token
  echo "→ Token privado /items guardado en web/.items-admin-token"
fi
export ITEMS_ADMIN_TOKEN

python3 scripts/sync-zagan-items-web.py 2>/dev/null || true

export OT_HOST=127.0.0.1
export SERVER_IP=127.0.0.1
echo "Retro76 web → http://localhost:8080/"
echo "Catálogo privado → http://localhost:8080/items"
exec python3 web/server.py
