#!/usr/bin/env bash
# Genera creatures.xml de RME con monstruos/NPCs custom de YurOTS (no duplica los de Tibia 7.6).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/resolve-project-root.sh
source "$SCRIPT_DIR/resolve-project-root.sh"
PROJECT_ROOT="$(resolve_project_root)"

NPC_DIR="$PROJECT_ROOT/server/YurOTS/ots/data/npc"
MONSTER_DIR="$PROJECT_ROOT/server/YurOTS/ots/data/monster"
RME_ROOT="${RME_ROOT:-$HOME/dev/rme}"
RME_BUILD="${RME_BUILD:-$RME_ROOT/build}"
RME_DEFAULT_CREATURES="$RME_ROOT/data/760/creatures.xml"
TMP="$(mktemp /tmp/rme-creatures.XXXXXX.xml)"

python3 - "$NPC_DIR" "$MONSTER_DIR" "$RME_DEFAULT_CREATURES" "$TMP" <<'PY'
import os
import sys
import xml.etree.ElementTree as ET

npc_dir, monster_dir, rme_default_path, out_path = sys.argv[1:5]

def look_attrs(elem):
    if elem is None:
        return {}
    attrs = {}
    mapping = {
        "type": "looktype",
        "item": "lookitem",
        "lookex": "lookitem",
        "typeex": "lookitem",
        "mount": "lookmount",
        "addon": "lookaddon",
        "head": "lookhead",
        "body": "lookbody",
        "legs": "looklegs",
        "feet": "lookfeet",
    }
    for src, dst in mapping.items():
        val = elem.get(src)
        if val is not None:
            attrs[dst] = val
    return attrs

default_names = set()
if os.path.isfile(rme_default_path):
    try:
        for node in ET.parse(rme_default_path).getroot():
            if node.tag == "creature":
                name = node.get("name")
                if name:
                    default_names.add(name.lower())
    except ET.ParseError:
        pass

entries = {}

if os.path.isdir(npc_dir):
    for fname in sorted(os.listdir(npc_dir)):
        if not fname.lower().endswith(".xml"):
            continue
        path = os.path.join(npc_dir, fname)
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        if root.tag != "npc":
            continue
        name = root.get("name") or os.path.splitext(fname)[0]
        attrs = look_attrs(root.find("look"))
        if "looktype" not in attrs:
            attrs["looktype"] = "128"
        key = name.lower()
        if key in default_names:
            continue
        entries[key] = ("npc", name, attrs)

if os.path.isdir(monster_dir):
    for fname in sorted(os.listdir(monster_dir)):
        if not fname.lower().endswith(".xml") or fname == "monsters.xml":
            continue
        path = os.path.join(monster_dir, fname)
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        if root.tag != "monster":
            continue
        name = root.get("name") or os.path.splitext(fname)[0]
        key = name.lower()
        if key in default_names:
            continue
        attrs = look_attrs(root.find("look"))
        if "looktype" not in attrs:
            continue
        entries[key] = ("monster", name, attrs)

lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<creatures>"]
for ctype, name, attrs in sorted(entries.values(), key=lambda x: x[1].lower()):
    parts = [f'name="{name}"', f'type="{ctype}"']
    for key in ("looktype", "lookitem", "lookmount", "lookaddon", "lookhead", "lookbody", "looklegs", "lookfeet"):
        if key in attrs:
            parts.append(f'{key}="{attrs[key]}"')
    lines.append(f'  <creature {" ".join(parts)}/>')
lines.append("</creatures>")

with open(out_path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

print(len(entries))
PY

count="$(grep -c '<creature' "$TMP" || true)"

DEST_PATHS=(
  "$RME_BUILD/data/user/data/760/creatures.xml"
  "$HOME/Library/Application Support/.rme/data/760/creatures.xml"
)

for dest in "${DEST_PATHS[@]}"; do
  mkdir -p "$(dirname "$dest")"
  cp "$TMP" "$dest"
  echo "Escrito: $dest"
done

rm -f "$TMP"
echo "Criaturas custom exportadas: $count"
