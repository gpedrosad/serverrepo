#!/usr/bin/env bash
# Compila la web Astro (web/site) en la ThinkPad y trae el resultado a web/dist.
# En la Mac mini no se compila (CLAUDE.md). web/dist va versionado: el servidor no necesita Node,
# server.py lo sirve tal cual. Ver docs/features/18-web-astro.md.
#
#   scripts/web/build-site.sh            # compila y trae web/dist
#   BUILD_HOST=otra-maquina scripts/web/build-site.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOST="${BUILD_HOST:-thinkpad}"
REMOTE='~/build/retro76-web'

echo "→ copiando web/site y web/data a $HOST:$REMOTE"
ssh "$HOST" "mkdir -p $REMOTE/web"
rsync -a --delete --exclude node_modules --exclude .astro "$ROOT/web/site/" "$HOST:$REMOTE/web/site/"
rsync -a "$ROOT/web/data/gem-drops.json" "$HOST:$REMOTE/web/data/"

echo "→ compilando en $HOST"
ssh "$HOST" "export NVM_DIR=\$HOME/.nvm; . \$NVM_DIR/nvm.sh >/dev/null; cd $REMOTE/web/site && \
  if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi && \
  rm -rf ../dist && npm run build"

echo "→ trayendo web/dist y package-lock.json"
rsync -a --delete "$HOST:$REMOTE/web/dist/" "$ROOT/web/dist/"
rm -f "$ROOT"/web/dist/*.mjs   # restos del content layer de Astro; no se sirven
rsync -a "$HOST:$REMOTE/web/site/package-lock.json" "$ROOT/web/site/package-lock.json"
du -sh "$ROOT/web/dist" | sed 's/^/   web\/dist: /'
