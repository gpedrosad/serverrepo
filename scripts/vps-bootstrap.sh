#!/usr/bin/env bash
# Bootstrap en el VPS (consola DigitalOcean): instala/clona repo y arregla el 502.
# Uso remoto:
#   curl -fsSL https://raw.githubusercontent.com/gpedrosad/serverrepo/main/scripts/vps-bootstrap.sh | bash
set -euo pipefail

REPO="${YUROTS_REPO:-$HOME/serverrepo}"
URL="${YUROTS_REPO_URL:-https://github.com/gpedrosad/serverrepo.git}"

if ! command -v docker >/dev/null; then
  echo "Docker no instalado. Instalá Docker en el VPS primero." >&2
  exit 1
fi

if ! command -v git >/dev/null; then
  echo "Instalando git..."
  sudo apt-get update -qq
  sudo apt-get install -y git curl
fi

if [[ -d "$REPO/.git" ]]; then
  git -C "$REPO" pull --ff-only origin main
else
  git clone "$URL" "$REPO"
fi

exec "$REPO/scripts/vps-fix-502.sh"
