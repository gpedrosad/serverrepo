#!/usr/bin/env bash
# Backup de data runtime (cuentas, personajes, casas, online).
# Uso:
#   ./scripts/backup-runtime-data.sh              # solo local (Mac)
#   ./scripts/backup-runtime-data.sh --server       # servidor de la ThinkPad + copia espejo en la Mac
#   ./scripts/backup-runtime-data.sh --server-only  # solo en la ThinkPad (sin rsync)
# El servidor es el de prueba de la ThinkPad (docs/systems/THINKPAD_TEST_SERVER.md); no hay VPS.
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
SERVER_HOST="${SERVER_HOST:-thinkpad}"
SERVER_DATA="${SERVER_DATA:-apps/serverrepo/server/YurOTS/ots/data}"   # relativo al home del servidor
DO_SERVER=0
SERVER_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --server) DO_SERVER=1 ;;
    --server-only) DO_SERVER=1; SERVER_ONLY=1 ;;
    -h|--help)
      sed -n '2,7p' "$0"
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

run_server_backup() {
  local server_dest="backups/server-${LABEL}-${STAMP}"     # relativo al home del servidor
  echo "==> backup servidor ($SERVER_HOST) → ~/$server_dest"
  ssh "$SERVER_HOST" bash -s <<REMOTE
set -euo pipefail
cd "\$HOME"
DATA="$SERVER_DATA"
DEST="$server_dest"
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
source=server
host=\$(hostname)
accounts=\$ACC
players=\$PLR
house_owners=\$OWN
path=\$DEST
EOF
echo "    \$ACC cuentas, \$PLR archivos players/, \$OWN casas con dueño"
echo "\$DEST"
REMOTE

  if [[ "$SERVER_ONLY" == "1" ]]; then
    echo "~/$server_dest"
    return
  fi

  local mirror="$LOCAL_BACKUP_ROOT/server-${LABEL}-${STAMP}"
  echo "==> copia espejo servidor → Mac: $mirror"
  mkdir -p "$mirror"
  rsync -az "$SERVER_HOST:$server_dest/" "$mirror/"
  write_manifest "$mirror" "$mirror/accounts-state.json"
  echo "$mirror"
}

mkdir -p "$LOCAL_BACKUP_ROOT"

LOCAL_PATH="$(run_local_backup)"
if [[ "$DO_SERVER" == "1" ]]; then
  SERVER_PATH="$(run_server_backup)"
  echo ""
  echo "OK backups:"
  echo "  local:    $LOCAL_PATH"
  echo "  servidor: $SERVER_PATH"
else
  echo ""
  echo "OK backup local: $LOCAL_PATH"
  echo "Tip: incluir el servidor de la ThinkPad → ./scripts/backup-runtime-data.sh --server"
fi
