#!/usr/bin/env bash
# Arranca yurots dentro del contenedor (usado por docker-compose local).
set -euo pipefail
cd /app/YurOTS/ots
exec ./source/yurots
