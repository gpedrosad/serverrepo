#!/usr/bin/env bash
# Raíz del repo = carpeta padre de scripts/ (yurots-principal en Desktop).
resolve_project_root() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[1]:-$0}")" && pwd)"
  echo "$(cd "$script_dir/.." && pwd)"
}
