#!/usr/bin/env python3
"""Protege los cofres de quest con nivel y sube las puertas de level existentes.

- Genera la tabla `CHEST_LEVEL` de `actions/scripts/quest.lua`: cada cofre queda con el nivel
  recomendado de su quest. Sin ese nivel, el cofre no se abre.
- Sube el actionId de las puertas de level que ya están en el camino de una quest (actionId =
  nivel + 1000, ver `leveldoor.lua`). No agrega puertas nuevas ni mueve cofres.
- Escribe `server/YurOTS/ots/data/world/generated-quest-protection.json` con el detalle.

Uso:
  python3 scripts/map/protect-quest-chests.py --dry-run
  python3 scripts/map/protect-quest-chests.py
"""
from __future__ import annotations

import json
import re
import struct
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import (MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, parse_tree,  # noqa: E402
                     serialize_tree)

QUESTS = REPO / "web/site/src/data/quests.json"
QUEST_LUA = REPO / "server/YurOTS/ots/data/actions/scripts/quest.lua"
MANIFEST = REPO / "server/YurOTS/ots/data/world/generated-quest-protection.json"

# Puertas de level que ya existen en el camino de alguna quest. (x, y, z), itemid, action actual, nivel nuevo.
DOORS = [
    ((213, 124, 8), 1245, 1050, 60),   # Pharaoh / Ancients A / Shield of Honour (mínimo compartido)
    ((87, 75, 8), 1229, 1020, 30),     # Fire Cave / Knight Legs
    ((251, 25, 8), 1227, 1020, 40),    # Lady Helmet
    ((181, 77, 8), 1247, 1060, 80),    # Steel Boots
    ((242, 126, 8), 1227, 1040, 60),   # Ancients B
    ((145, 101, 8), 1229, 1020, 40),   # Bright Sword
    ((84, 94, 10), 1227, 1020, 50),    # Amazon Shield
    ((136, 62, 7), 1245, 1035, 60),    # Boots of Haste
]


def tile_nodes(root):
    out = {}
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        for tile in area[2]:
            if tile[0] not in (T_TILE, T_HOUSETILE):
                continue
            p = bytes(tile[1])
            out[(ax + p[0], ay + p[1], az)] = tile
    return out


def item_id(node):
    p = bytes(node[1])
    return struct.unpack_from("<H", p, 0)[0] if len(p) >= 2 else None


def set_action(node, action):
    p = bytearray(node[1])
    pos = 2
    while pos < len(p):
        a = p[pos]
        pos += 1
        if a == 4:
            struct.pack_into("<H", p, pos, action)
            node[1] = p
            return True
        if a == 5:
            pos += 2
        elif a in (6, 7):
            if pos + 2 > len(p):
                break
            n = struct.unpack_from("<H", p, pos)[0]
            pos += 2 + n
        elif a == 8:
            pos += 5
        elif a == 12:
            pos += 1
        else:
            break
    # sin action: se la agregamos al final
    p += bytes((4, action & 0xFF, (action >> 8) & 0xFF))
    node[1] = p
    return True


def main() -> int:
    ap = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.loads(QUESTS.read_text(encoding="utf-8"))
    levels = {q["id"]: int(q["level_min"]) for q in data["quests"]}
    chests = []
    table = {}
    for c in data.get("map_chests", []):
        level = levels.get(c["quest_id"])
        if not level:
            continue
        key = f"{c['x']},{c['y']},{c['z']}"
        table[key] = level
        chests.append({"quest": c["quest_id"], "x": c["x"], "y": c["y"], "z": c["z"],
                       "reward": c["reward"], "level": level})

    # tabla Lua
    lines = ["-- BEGIN QUEST_LEVELS (scripts/map/protect-quest-chests.py)",
             "local CHEST_LEVEL = {"]
    for key in sorted(table, key=lambda k: tuple(int(v) for v in k.split(","))):
        lines.append(f'\t["{key}"] = {table[key]},')
    lines += ["}", "-- END QUEST_LEVELS"]
    block = "\n".join(lines)

    lua = QUEST_LUA.read_text(encoding="latin-1")
    new_lua, n = re.subn(r"-- BEGIN QUEST_LEVELS.*?-- END QUEST_LEVELS", block, lua, flags=re.S)
    if n != 1:
        raise SystemExit("no encontré el bloque QUEST_LEVELS en quest.lua")

    # puertas existentes
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    nodes = tile_nodes(root)
    doors = []
    for pos, item, old_action, level in DOORS:
        tile = nodes.get(pos)
        if tile is None:
            print(f"AVISO: no existe la casilla de la puerta {pos}", file=sys.stderr)
            continue
        node = next((c for c in tile[2] if c[0] == T_ITEM and item_id(c) == item), None)
        if node is None:
            print(f"AVISO: no encontré el item {item} en {pos}", file=sys.stderr)
            continue
        new_action = level + 1000
        if new_action <= old_action:
            doors.append({"x": pos[0], "y": pos[1], "z": pos[2], "item": item,
                          "oldAction": old_action, "newAction": old_action, "level": level,
                          "changed": False})
            continue
        set_action(node, new_action)
        doors.append({"x": pos[0], "y": pos[1], "z": pos[2], "item": item,
                      "oldAction": old_action, "newAction": new_action, "level": level,
                      "changed": True})
        print(f"puerta {pos}: nivel {old_action - 1000} -> {level}")

    manifest = {"chests": chests, "doors": doors,
                "note": "Cofres con nivel recomendado y puertas de level subidas; ver quest.lua"}
    if args.dry_run:
        print(f"dry-run: {len(chests)} cofres, {sum(1 for d in doors if d['changed'])} puertas a subir")
        print(block)
        return 0

    QUEST_LUA.write_text(new_lua, encoding="latin-1")
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK {QUEST_LUA}\nOK {MAP}\nOK {MANIFEST}: {len(chests)} cofres, "
          f"{sum(1 for d in doors if d['changed'])} puertas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
