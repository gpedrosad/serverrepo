#!/usr/bin/env bash
# Copia Tibia.dat / Tibia.spr (7.6) desde otclientv8 para Remere's Map Editor.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
PROJECT_ROOT="$(resolve_project_root)"
DEST="$PROJECT_ROOT/rme-client-760"
LOG="$SCRIPT_DIR/../rme-setup-log.txt"

{
  echo "=== RME client setup $(date) ==="
  echo "PROJECT_ROOT=$PROJECT_ROOT"

  THINGS760=""
  CLIENT_DIR=""

  for candidate in \
    "$HOME/Downloads/otclientv8-master/data/things/760" \
    "$HOME/Downloads/otclientv8-master/otclientv8-master/data/things/760" \
    "$HOME/clientv8master/data/things/760" \
    "$HOME/ClientV8Master/data/things/760" \
    "$HOME/client-v8-master/data/things/760" \
    "$HOME/projects/clientv8master/data/things/760" \
    "$HOME/dev/clientv8master/data/things/760"; do
    if [[ -f "$candidate/Tibia.dat" && -f "$candidate/Tibia.spr" ]]; then
      THINGS760="$candidate"
      break
    fi
  done

  if [[ -z "$CLIENT_DIR" ]]; then
    for candidate in \
      "$HOME/Downloads/otclientv8-master" \
      "$HOME/Downloads/otclientv8-master/otclientv8-master" \
      "$HOME/clientv8master" \
      "$HOME/ClientV8Master"; do
      if [[ -d "$candidate" ]]; then
        CLIENT_DIR="$candidate"
        break
      fi
    done
  fi

  if [[ -z "$CLIENT_DIR" ]]; then
    CLIENT_DIR="$(find "$HOME/Downloads" "$HOME" -maxdepth 5 -type d -iname 'otclientv8-master' 2>/dev/null | head -1 || true)"
  fi

  if [[ -z "$CLIENT_DIR" ]]; then
    CLIENT_DIR="$(find "$HOME" -maxdepth 6 -type d -iname 'clientv8master' 2>/dev/null | head -1 || true)"
  fi

  if [[ -z "$CLIENT_DIR" ]]; then
    CLIENT_DIR="$(find "$HOME" -maxdepth 6 -type d -iname '*clientv8*' 2>/dev/null | head -1 || true)"
  fi

  echo "CLIENT_DIR=${CLIENT_DIR:-NOT_FOUND}"

  if [[ -z "$THINGS760" && -n "$CLIENT_DIR" && -d "$CLIENT_DIR" ]]; then
    for candidate in \
      "$CLIENT_DIR/data/things/760" \
      "$CLIENT_DIR/things/760"; do
      if [[ -f "$candidate/Tibia.dat" && -f "$candidate/Tibia.spr" ]]; then
        THINGS760="$candidate"
        break
      fi
    done
  fi

  if [[ -z "$THINGS760" && -n "$CLIENT_DIR" && -d "$CLIENT_DIR" ]]; then
    DAT="$(find "$CLIENT_DIR" -path '*/760/Tibia.dat' 2>/dev/null | head -1 || true)"
    if [[ -n "$DAT" ]]; then
      THINGS760="$(dirname "$DAT")"
    fi
  fi

  if [[ -z "$THINGS760" ]]; then
    DAT="$(find "$HOME/Downloads" -path '*/760/Tibia.dat' 2>/dev/null | head -1 || true)"
    if [[ -n "$DAT" ]]; then
      THINGS760="$(dirname "$DAT")"
    fi
  fi

  echo "THINGS760=$THINGS760"

  if [[ ! -f "$THINGS760/Tibia.dat" || ! -f "$THINGS760/Tibia.spr" ]]; then
    echo "ERROR: No se encontraron Tibia.dat y Tibia.spr"
    echo "Busca manualmente: find ~/Downloads -path '*/760/Tibia.dat'"
    exit 1
  fi

  mkdir -p "$DEST"
  cp -v "$THINGS760/Tibia.dat" "$THINGS760/Tibia.spr" "$DEST/"
  xattr -d com.apple.quarantine "$DEST/Tibia.dat" 2>/dev/null || true
  xattr -d com.apple.quarantine "$DEST/Tibia.spr" 2>/dev/null || true

  echo "DEST=$DEST"
  ls -la "$DEST"

  ITEMS_OTB="$PROJECT_ROOT/server/YurOTS/ots/data/items/items.otb"
  if [[ -f "$ITEMS_OTB" ]]; then
    echo "ITEMS_OTB=$ITEMS_OTB"
  else
    echo "WARN: items.otb no encontrado en ruta esperada del server"
    find "$PROJECT_ROOT" -name 'items.otb' 2>/dev/null | head -3 || true
  fi

  echo "OK"
} 2>&1 | tee "$LOG"
