#!/usr/bin/env python3
"""Agrega una puerta de level antes del cofre en las quests que todavía no tienen una.

No toca las quests que ya tienen una puerta de level en el camino (esas las maneja
`protect-quest-chests.py`). Para las que no tienen, busca un punto angosto del camino, pone una
puerta de level (actionId = nivel + 1000) y tapa los costados con paredes del mismo estilo.

Uso:
  python3 scripts/map/add-quest-gates.py --dry-run
  python3 scripts/map/add-quest-gates.py
"""
from __future__ import annotations

import json
import struct
import sys
import xml.etree.ElementTree as ET
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import (MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, load_otb,  # noqa: E402
                     parse_tree, serialize_tree)

QUESTS = REPO / "web/site/src/data/quests.json"
ROUTES = HERE / "quest-routes.json"
MANIFEST = REPO / "server/YurOTS/ots/data/world/generated-quest-gates.json"
OTB = load_otb()

_spec = __import__("importlib.util").util.spec_from_file_location("routes", HERE / "build-routes.py")
br = __import__("importlib.util").util.module_from_spec(_spec)
_spec.loader.exec_module(br)

# Quests sin puerta de level en el camino (las que ya tienen se saltean).
TARGETS = ["imperial", "frozen-lumberjack", "frozen-yeti", "frozen-lair",
           "desert-lizard", "desert-bone", "crusader-helmet", "guardian-halberd", "dark-shield"]

# Casos donde el camino llega por una escalera y no hay un punto limpio en el mismo piso.
MANUAL = {
    "guardian-halberd": {"point": (144, 143, 4), "axis": "ns", "walls": [(143, 143, 4)]},
}

# Estilo de puerta/pared por contexto: dorada en templos/castillo, madera en costa/campamento,
# piedra en cuevas, arenisca en el desierto.
STYLE = {
    "imperial":         {"door_ns": 1247, "door_ew": 1245, "wall": 1050},
    "frozen-lumberjack": {"door_ns": 1229, "door_ew": 1227, "wall": 1038},
    "frozen-yeti":      {"door_ns": 1229, "door_ew": 1227, "wall": 1052},
    "frozen-lair":      {"door_ns": 1229, "door_ew": 1227, "wall": 1052},
    "desert-lizard":    {"door_ns": 1247, "door_ew": 1245, "wall": 1067},
    "desert-bone":      {"door_ns": 1247, "door_ew": 1245, "wall": 1067},
    "crusader-helmet":  {"door_ns": 1229, "door_ew": 1227, "wall": 1038},
    "guardian-halberd": {"door_ns": 1229, "door_ew": 1227, "wall": 1038},
    "dark-shield":      {"door_ns": 1229, "door_ew": 1227, "wall": 1052},
}

DOOR_IDS = {1219, 1220, 1221, 1222, 1223, 1224, 1225, 1226, 1227, 1228, 1229, 1230,
            1231, 1232, 1233, 1234, 1235, 1236, 1237, 1238, 1239, 1240, 1241, 1242,
            1243, 1244, 1245, 1246, 1247, 1248, 1249, 1250, 1251, 1252, 1253, 1254,
            1255, 1256, 1257, 1258, 1259, 1260, 1261, 1262, 3535, 3536, 3537, 3538,
            3539, 3540, 3541, 3542, 3543, 3544, 3545, 3546, 3547, 3548, 3549, 3550,
            3551, 3552, 4913, 4914, 4915, 4916, 5082, 5083, 5084, 5085}


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


def add_item(tile, item_id, action=None):
    props = bytearray(struct.pack("<H", item_id))
    if action is not None:
        props.append(4)
        props += struct.pack("<H", action)
    tile[2].append([T_ITEM, props, []])


def remove_item(tile, item_id, action=None):
    for i, node in enumerate(tile[2]):
        if node[0] != T_ITEM:
            continue
        p = bytes(node[1])
        if len(p) < 2 or struct.unpack_from("<H", p, 0)[0] != item_id:
            continue
        if action is not None:
            found = False
            pos = 2
            while pos < len(p):
                a = p[pos]
                pos += 1
                if a == 4 and pos + 2 <= len(p):
                    found = struct.unpack_from("<H", p, pos)[0] == action
                    break
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
            if not found:
                continue
        tile[2].pop(i)
        return True
    return False


def load_spawns():
    out = set()
    path = REPO / "server/YurOTS/ots/data/world/test-spawn.xml"
    root = ET.parse(path).getroot()
    for sp in root.iter("spawn"):
        cx, cy, cz = int(sp.get("centerx")), int(sp.get("centery")), int(sp.get("centerz"))
        for m in sp.iter("monster"):
            out.add((cx + int(m.get("x", 0)), cy + int(m.get("y", 0)), int(m.get("z", cz))))
    return out


def item_name(sid):
    return (OTB.get(sid) or {}).get("name", "")


def wall_item(near, tiles):
    """Pared del mismo estilo: la pared más común en un radio de 4."""
    counts = {}
    for p, tile in tiles.items():
        if abs(p[0] - near[0]) > 4 or abs(p[1] - near[1]) > 4 or p[2] != near[2]:
            continue
        for it in tile["items"]:
            name = item_name(it["id"])
            if "wall" in name and "door" not in name:
                counts[it["id"]] = counts.get(it["id"], 0) + 1
    if counts:
        return max(counts, key=counts.get)
    for sid in (1052, 1053, 1051):
        if (OTB.get(sid) or {}).get("name") == "stone wall":
            return sid
    return 1052


def main() -> int:
    ap = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--remove", action="store_true", help="quita las puertas agregadas por este script")
    args = ap.parse_args()

    if args.remove:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        raw = MAP.read_bytes()
        root = parse_tree(raw)
        nodes = tile_nodes(root)
        for g in manifest.get("gates", []):
            d = g["door"]
            tile = nodes.get((d["x"], d["y"], d["z"]))
            if tile:
                remove_item(tile, d["item"], d["action"])
            for w in g.get("walls", []):
                tile = nodes.get((w["x"], w["y"], w["z"]))
                if tile:
                    remove_item(tile, w["item"])
        MAP.write_bytes(serialize_tree(root, raw[:4]))
        print(f"OK removidas {len(manifest.get('gates', []))} puertas de quest")
        return 0

    br.MAP_PATH = MAP
    br.tiles = br.load_map()
    br.walk, br.vert = br.build_graph(br.tiles)
    SPAWNS = load_spawns()
    quests = {q["id"]: q for q in json.loads(QUESTS.read_text(encoding="utf-8"))["quests"]}
    routes = {r["quest"]: r for r in json.loads(ROUTES.read_text(encoding="utf-8"))["routes"]}
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    nodes = tile_nodes(root)
    blocked = set()
    used = set()
    gates = []
    no_gate = set()
    for p in br.walk:
        for it in br.tiles[p]["items"]:
            sid = it["id"]
            if it["tele"] is not None:
                no_gate.add(p)
                no_gate.add(it["tele"])
            if "floorchange_down" in br.flags_of(it):
                no_gate.add(p)
                no_gate.add(br.down_landing(br.tiles, p))
            if br.dirs_of(br.tiles, p):
                q = br.up_landing(br.tiles, p)
                no_gate.add(p)
                if q:
                    no_gate.add(q)
            elif sid in br.UP_IDS or sid in br.LADDER_UP_IDS:
                q = br.item_fc_landing(br.tiles, p, sid)
                no_gate.add(p)
                if q:
                    no_gate.add(q)

    for qid in TARGETS:
        if qid not in routes or qid not in quests:
            print(f"AVISO: falta ruta/quest {qid}", file=sys.stderr)
            continue
        q = quests[qid]
        level = int(q["level_min"])
        chests = [c for c in json.loads(QUESTS.read_text(encoding="utf-8"))["map_chests"]
                  if c["quest_id"] == qid]
        if not chests:
            continue
        chest = (chests[0]["x"], chests[0]["y"], chests[0]["z"])
        pts = []
        for seg in routes[qid]["segments"]:
            for x, y in seg["points"]:
                pts.append((x, y, seg["z"]))

        def walk(p):
            return p in br.walk and p not in blocked and p not in used

        def has_special(p):
            if p in SPAWNS or p in no_gate:
                return True
            tile = br.tiles.get(p)
            if not tile:
                return True
            for it in tile["items"]:
                if it["id"] in DOOR_IDS or it["unique"] is not None or it["tele"] is not None:
                    return True
                if it["action"] is not None:
                    return True
            return False

        def gate_sides(p, axis):
            """Lados inmediatos de la puerta. Si el lado es caminable, hay que taparlo;
            si el camino sigue más allá, la puerta sería esquiviable y no sirve."""
            x, y, z = p
            dirs = [(-1, 0), (1, 0)] if axis == "ns" else [(0, -1), (0, 1)]
            walls, frame = [], []
            for dx, dy in dirs:
                q = (x + dx, y + dy, z)
                if walk(q):
                    beyond = (x + 2 * dx, y + 2 * dy, z)
                    if walk(beyond):
                        return None
                    walls.append(q)
                else:
                    tile = nodes.get(q)
                    if tile is None:
                        continue
                    if any(it["unique"] is not None or it["tele"] is not None for it in br.tiles[q]["items"]):
                        return None
                    if has_special(q):
                        continue
                    items = br.tiles[q]["items"]
                    if any("wall" in item_name(it["id"]) and "block_solid" in br.flags_of(it) for it in items):
                        continue
                    ground = [it for it in items if br.group_of(it) == "ground"]
                    if not ground or any("water" in item_name(it["id"]) for it in ground):
                        continue
                    frame.append(q)
            return walls, frame

        candidates = []
        if qid in MANUAL:
            m = MANUAL[qid]
            p = m["point"]
            walls = [w for w in m["walls"] if walk(w) and not has_special(w)]
            if walk(p) and not has_special(p):
                candidates.append((len(walls), 5, m["axis"], p, walls, []))
        for i, p in enumerate(pts if qid not in MANUAL else []):
            if p[2] != chest[2] or p == chest or not walk(p) or has_special(p):
                continue
            d = abs(p[0] - chest[0]) + abs(p[1] - chest[1])
            if d < 2 or d > 16:
                continue
            prev = pts[i - 1] if i > 0 and pts[i - 1][2] == p[2] else None
            nxt = pts[i + 1] if i + 1 < len(pts) and pts[i + 1][2] == p[2] else None
            if not prev and not nxt:
                continue
            dx = (nxt[0] - prev[0]) if prev and nxt else (nxt[0] - p[0]) if nxt else (p[0] - prev[0])
            dy = (nxt[1] - prev[1]) if prev and nxt else (nxt[1] - p[1]) if nxt else (p[1] - prev[1])
            axis = "ns" if abs(dy) >= abs(dx) else "ew"
            sides = gate_sides(p, axis)
            if sides is None:
                continue
            walls, frame = sides
            candidates.append((len(frame), d, axis, p, walls, frame))
        if not candidates:
            # fallback: para barco/portal, la entrada (primer punto del último tramo);
            # para caminar, el punto más cercano al cofre (la entrada de la zona).
            last_seg = routes[qid]["segments"][-1]
            pts_last = [(x, y, last_seg["z"]) for x, y in last_seg["points"]]
            if routes[qid]["kind"] in ("boat", "portal"):
                ordered = pts_last
            else:
                ordered = list(reversed(pts_last))
            for p in ordered:
                d = abs(p[0] - chest[0]) + abs(p[1] - chest[1])
                if d >= 3 and walk(p) and not has_special(p):
                    dx = pts_last[-1][0] - pts_last[0][0]
                    dy = pts_last[-1][1] - pts_last[0][1]
                    axis = "ns" if abs(dy) >= abs(dx) else "ew"
                    side = [(p[0] - 1, p[1], p[2]), (p[0] + 1, p[1], p[2])] if axis == "ns" else \
                           [(p[0], p[1] - 1, p[2]), (p[0], p[1] + 1, p[2])]
                    forced = []
                    for q in side:
                        tile = nodes.get(q)
                        if tile is None or q in SPAWNS:
                            continue
                        if any(it["unique"] is not None or it["tele"] is not None or it["action"] is not None
                               for it in br.tiles[q]["items"]):
                            continue
                        forced.append(q)
                    candidates.append((len(forced), d, axis, p, forced, []))
                    break
            if not candidates:
                print(f"AVISO: no encontré dónde poner la puerta de {qid}", file=sys.stderr)
                continue
        candidates.sort(key=lambda c: (c[0], abs(c[1] - 5), c[1]))
        _frame_n, d, axis, p, walls, frame = candidates[0]
        style = STYLE.get(qid, {"door_ns": 1229, "door_ew": 1227, "wall": 1052})
        door_id = style["door_ns"] if axis == "ns" else style["door_ew"]
        action = level + 1000
        wall_id = style["wall"]
        tile = nodes.get(p)
        if tile is None:
            print(f"AVISO: no existe el tile {p} para {qid}", file=sys.stderr)
            continue
        add_item(tile, door_id, action)
        used.add(p)
        wall_positions = []
        for w in walls + frame:
            wt = nodes.get(w)
            if wt is not None:
                add_item(wt, wall_id)
                blocked.add(w)
                wall_positions.append(w)
        gates.append({"quest": qid, "level": level, "door": {"x": p[0], "y": p[1], "z": p[2],
                      "item": door_id, "action": action}, "walls": [{"x": w[0], "y": w[1], "z": w[2],
                      "item": wall_id} for w in wall_positions], "axis": axis})
        print(f"{qid:18} puerta {p} nivel {level} ({'horizontal' if axis == 'ns' else 'vertical'}), "
              f"paredes {wall_positions}")

    manifest = {"gates": gates}
    if args.dry_run:
        print(f"dry-run: {len(gates)} puertas")
        return 0
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK {MAP}\nOK {MANIFEST}: {len(gates)} puertas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
