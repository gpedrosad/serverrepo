#!/usr/bin/env bash
# Backup de data runtime (cuentas, personajes, casas, online).
# Uso:
#   ./scripts/backup-runtime-data.sh              # solo local (Mac)
#   ./scripts/backup-runtime-data.sh --vps        # VPS + copia espejo en Mac
#   ./scripts/backup-runtime-data.sh --vps-only   # solo en el VPS (sin rsync)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
while [[ ! -f "$SCRIPT_DIR/resolve-project-root.sh" ]]; do
  SCRIPT_DIR="$(dirname "$SCRIPT_DIR")"
  if [[ "$SCRIPT_DIR" == "/" ]]; then
    echo "ERROR: resolve-project-root.sh no encontrado" >&2
    exit 1
  fi
done
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
ROOT="$(resolve_project_root)"

DATA="$ROOT/server/YurOTS/ots/data"
LABEL="${BACKUP_LABEL:-pre-change}"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOCAL_BACKUP_ROOT="${BACKUP_ROOT:-$HOME/ot-backups}"
VPS="${VPS:-root@64.176.20.238}"
VPS_DATA="${VPS_DATA:-/root/yurots-principal/server/YurOTS/ots/data}"
DO_VPS=0
VPS_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --vps) DO_VPS=1 ;;
    --vps-only) DO_VPS=1; VPS_ONLY=1 ;;
    -h|--help)
      sed -n '2,6p' "$0"
      exit 0
      ;;
    *)
      echo "Opción desconocida: $arg" >&2
      exit 1
      ;;
  esac
done

count_files() {
  local dir="$1" pattern="$2"
  find "$dir" -maxdepth 1 -name "$pattern" 2>/dev/null | wc -l | tr -d ' '
}

backup_tree() {
  local src_data="$1"
  local dest="$2"
  mkdir -p "$dest"
  cp -a "$src_data/accounts" "$src_data/players" "$dest/"
  [[ -d "$src_data/vip" ]] && cp -a "$src_data/vip" "$dest/"
  cp -a "$src_data/online.xml" "$src_data/queue.xml" "$dest/" 2>/dev/null || true
  [[ -f "$src_data/houseitems.xml" ]] && cp -a "$src_data/houseitems.xml" "$dest/"
  [[ -f "$src_data/private_trainers.xml" ]] && cp -a "$src_data/private_trainers.xml" "$dest/"
  [[ -d "$src_data/houses" ]] && cp -a "$src_data/houses" "$dest/" 2>/dev/null || true
}

write_manifest() {
  local data_dir="$1"
  local out="$2"
  python3 "$SCRIPT_DIR/write-accounts-state-manifest.py" "$data_dir" "$out"
}

run_local_backup() {
  local dest="$LOCAL_BACKUP_ROOT/local-${LABEL}-${STAMP}"
  echo "==> backup LOCAL → $dest"
  backup_tree "$DATA" "$dest"
  write_manifest "$DATA" "$dest/accounts-state.json"
  local acc players owners
  acc=$(count_files "$DATA/accounts" "*.xml")
  players=$(count_files "$DATA/players" "*.xml")
  owners=$(grep -h 'owner name=' "$DATA/houses"/*.xml 2>/dev/null | grep -cv 'owner name=""' || echo 0)
  cat > "$dest/BACKUP_INFO.txt" <<EOF
label=$LABEL
stamp=$STAMP
source=local
host=$(hostname)
accounts=$acc
players=$players
house_owners=$owners
path=$dest
EOF
  echo "    $acc cuentas, $players archivos players/, $owners casas con dueño"
  echo "$dest"
}

run_vps_backup() {
  local vps_dest="/root/ot-backups/vps-${LABEL}-${STAMP}"
  echo "==> backup VPS → $vps_dest"
  ssh "$VPS" bash -s <<REMOTE
set -euo pipefail
DATA="$VPS_DATA"
DEST="$vps_dest"
mkdir -p "\$DEST"
cp -a "\$DATA/accounts" "\$DATA/players" "\$DEST/"
[[ -d "\$DATA/vip" ]] && cp -a "\$DATA/vip" "\$DEST/"
cp -a "\$DATA/online.xml" "\$DATA/queue.xml" "\$DEST/" 2>/dev/null || true
[[ -f "\$DATA/houseitems.xml" ]] && cp -a "\$DATA/houseitems.xml" "\$DEST/"
[[ -f "\$DATA/private_trainers.xml" ]] && cp -a "\$DATA/private_trainers.xml" "\$DEST/"
[[ -d "\$DATA/houses" ]] && cp -a "\$DATA/houses" "\$DEST/"
ACC=\$(find "\$DATA/accounts" -maxdepth 1 -name '*.xml' | wc -l | tr -d ' ')
PLR=\$(find "\$DATA/players" -maxdepth 1 -name '*.xml' | wc -l | tr -d ' ')
OWN=\$(grep -h 'owner name=' "\$DATA/houses"/*.xml 2>/dev/null | grep -cv 'owner name=""' || echo 0)
cat > "\$DEST/BACKUP_INFO.txt" <<EOF
label=$LABEL
stamp=$STAMP
source=vps
host=\$(hostname)
accounts=\$ACC
players=\$PLR
house_owners=\$OWN
path=\$DEST
EOF
echo "    \$ACC cuentas, \$PLR archivos players/, \$OWN casas con dueño"
echo "\$DEST"
REMOTE

  if [[ "$VPS_ONLY" == "1" ]]; then
    echo "$vps_dest"
    return
  fi

  local mirror="$LOCAL_BACKUP_ROOT/vps-${LABEL}-${STAMP}"
  echo "==> copia espejo VPS → Mac: $mirror"
  mkdir -p "$mirror"
  rsync -az "$VPS:$vps_dest/" "$mirror/"
  write_manifest "$mirror" "$mirror/accounts-state.json"
  echo "$mirror"
}

mkdir -p "$LOCAL_BACKUP_ROOT"

LOCAL_PATH="$(run_local_backup)"
if [[ "$DO_VPS" == "1" ]]; then
  VPS_PATH="$(run_vps_backup)"
  echo ""
  echo "OK backups:"
  echo "  local: $LOCAL_PATH"
  echo "  vps:   $VPS_PATH"
else
  echo ""
  echo "OK backup local: $LOCAL_PATH"
  echo "Tip: incluir VPS → ./scripts/backup-runtime-data.sh --vps"
fi
