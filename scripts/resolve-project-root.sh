#!/usr/bin/env bash
# Resuelve la raíz del repo (yurots-principal) subiendo desde el script llamador
# hasta encontrar AGENTS.md o .git. Funciona desde scripts/ y desde subcarpetas.
resolve_project_root() {
  local dir
  # BASH_SOURCE[1] = script que hizo source; si no, $0
  if [[ -n "${BASH_SOURCE[1]:-}" ]]; then
    dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
  else
    dir="$(cd "$(dirname "$0")" && pwd)"
  fi
  while [[ "$dir" != "/" ]]; do
    if [[ -f "$dir/AGENTS.md" || -d "$dir/.git" ]]; then
      echo "$dir"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  echo "ERROR: no se encontró la raíz del repo (AGENTS.md / .git)" >&2
  return 1
}

# Directorio canónico scripts/ (donde vive este archivo), aunque se llame vía symlink.
resolve_scripts_dir() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  # Si este archivo está en scripts/lib/, subir un nivel; si está en scripts/, listo.
  if [[ "$(basename "$here")" == "lib" ]]; then
    echo "$(cd "$here/.." && pwd)"
  else
    echo "$here"
  fi
}
