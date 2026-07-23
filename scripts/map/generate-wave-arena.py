#!/usr/bin/env python3
"""Arena de oleadas — portal desde templo viejo 159,54,7.

Sala 7×7 de caza + vestíbulo con:
- landing / retorno al templo
- palanca Start/Next (uniqueid 7100)
- palanca Ranking semanal (uniqueid 7101)

Uso:
  python3 scripts/generate-wave-arena.py --dry-run
  python3 scripts/generate-wave-arena.py --replace
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

_maze_path = Path(__file__).resolve().parent / "generate-maze.py"
_spec = importlib.util.spec_from_file_location("generate_maze", _maze_path)
_maze = importlib.util.module_from_spec(_spec)
sys.modules["generate_maze"] = _maze
assert _spec.loader is not None
_spec.loader.exec_module(_maze)

GROUND_PATH = _maze.GROUND_PATH
GROUND_BG = _maze.GROUND_BG
TELEPORT_ITEM = _maze.TELEPORT_ITEM
NODE_START = _maze.NODE_START
NODE_END = _maze.NODE_END
OTBM_TILE_AREA = _maze.OTBM_TILE_AREA
OTBM_TILE = _maze.OTBM_TILE
OTBM_ITEM = _maze.OTBM_ITEM
OTBM_ATTR_TELE_DEST = _maze.OTBM_ATTR_TELE_DEST
OTBM_ATTR_ITEM = _maze.OTBM_ATTR_ITEM
OTBM_ATTR_UNIQUE_ID = 5
write_props = _maze.write_props

HUB_PORTAL = (159, 54, 7)
HUB_LANDING = (158, 54, 7)
HUB_GROUND = 407

# Arena al SW del floor-hunt / hunt-maze (zona vacía).
ARENA_Z = 7
FIGHT_X0, FIGHT_Y0 = 174, 386
FIGHT_SIZE = 7  # 174–180, 386–392
VEST_Y0 = 393
VEST_Y1 = 395
# Vestíbulo centrado bajo la arena
LANDING = (177, 394, ARENA_Z)
RETURN_TP = (178, 395, ARENA_Z)
LEVER_START = (176, 394, ARENA_Z)
LEVER_RANK = (179, 394, ARENA_Z)
LEVER_ITEM = 1945
UID_START = 7100
UID_RANK = 7101


@dataclass
class ArenaTile:
    ground: int
    teleport: tuple[int, int, int] | None = None
    items: list[tuple[int, int | None]] = field(default_factory=list)


def project_root() -> Path:
    return next(
        p
        for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
        if (p / "AGENTS.md").is_file() or (p / ".git").is_dir()
    )


def encode_item_node(
    item_id: int,
    *,
    unique_id: int | None = None,
    tele: tuple[int, int, int] | None = None,
) -> bytes:
    props = struct.pack("<H", item_id)
    if unique_id is not None:
        props += struct.pack("<BH", OTBM_ATTR_UNIQUE_ID, unique_id)
    if tele is not None:
        props += struct.pack("<BHHB", OTBM_ATTR_TELE_DEST, tele[0], tele[1], tele[2])
    buf = bytearray()
    buf.append(NODE_START)
    buf.append(OTBM_ITEM)
    write_props(buf, props)
    buf.append(NODE_END)
    return bytes(buf)


def encode_tile_node(x_off: int, y_off: int, spec: ArenaTile) -> bytes:
    props = struct.pack("<BB", x_off, y_off)
    props += struct.pack("<BH", OTBM_ATTR_ITEM, spec.ground)
    buf = bytearray()
    buf.append(NODE_START)
    buf.append(OTBM_TILE)
    write_props(buf, props)
    if spec.teleport is not None:
        buf.extend(encode_item_node(TELEPORT_ITEM, tele=spec.teleport))
    for item_id, uid in spec.items:
        buf.extend(encode_item_node(item_id, unique_id=uid))
    buf.append(NODE_END)
    return bytes(buf)


def encode_tile_area(base_x: int, base_y: int, base_z: int, rel: list) -> bytes:
    area_props = struct.pack("<HHB", base_x, base_y, base_z)
    buf = bytearray()
    buf.append(NODE_START)
    buf.append(OTBM_TILE_AREA)
    write_props(buf, area_props)
    for ox, oy, spec in sorted(rel, key=lambda t: (t[0], t[1])):
        buf.extend(encode_tile_node(ox, oy, spec))
    buf.append(NODE_END)
    return bytes(buf)


def group_tile_areas(tiles: dict[tuple[int, int, int], ArenaTile]) -> list[bytes]:
    from collections import defaultdict

    by_z: dict[int, list] = defaultdict(list)
    for (x, y, z), spec in tiles.items():
        by_z[z].append((x, y, spec))
    chunks: list[bytes] = []
    for z, entries in sorted(by_z.items()):
        buckets: dict[tuple[int, int], list] = defaultdict(list)
        for x, y, spec in entries:
            bx = (x // 256) * 256
            by = (y // 256) * 256
            buckets[(bx, by)].append((x - bx, y - by, spec))
        for (bx, by), rel in sorted(buckets.items()):
            chunks.append(encode_tile_area(bx, by, z, rel))
    return chunks


def build_arena_tiles(
    hub_portal: tuple[int, int, int],
    hub_landing: tuple[int, int, int],
) -> tuple[dict[tuple[int, int, int], ArenaTile], dict]:
    z = ARENA_Z
    fx0, fy0 = FIGHT_X0, FIGHT_Y0
    fx1, fy1 = fx0 + FIGHT_SIZE - 1, fy0 + FIGHT_SIZE - 1
    # Footprint con borde void
    x0, y0 = fx0 - 2, fy0 - 2
    x1, y1 = fx1 + 2, VEST_Y1 + 1

    tiles: dict[tuple[int, int, int], ArenaTile] = {}
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            tiles[(x, y, z)] = ArenaTile(ground=GROUND_BG)

    # Piso de pelea
    for y in range(fy0, fy1 + 1):
        for x in range(fx0, fx1 + 1):
            tiles[(x, y, z)] = ArenaTile(ground=GROUND_PATH)

    # Vestíbulo
    for y in range(VEST_Y0, VEST_Y1 + 1):
        for x in range(fx0 + 1, fx1):
            tiles[(x, y, z)] = ArenaTile(ground=GROUND_PATH)

    # Conectar arena ↔ vestíbulo (hueco sur del fight)
    for x in range(fx0 + 2, fx1 - 1):
        tiles[(x, fy1, z)] = ArenaTile(ground=GROUND_PATH)
        tiles[(x, VEST_Y0, z)] = ArenaTile(ground=GROUND_PATH)

    tiles[LANDING] = ArenaTile(ground=GROUND_PATH)
    tiles[RETURN_TP] = ArenaTile(ground=GROUND_PATH, teleport=hub_landing)
    tiles[LEVER_START] = ArenaTile(
        ground=GROUND_PATH, items=[(LEVER_ITEM, UID_START)]
    )
    tiles[LEVER_RANK] = ArenaTile(
        ground=GROUND_PATH, items=[(LEVER_ITEM, UID_RANK)]
    )
    tiles[hub_portal] = ArenaTile(ground=HUB_GROUND, teleport=LANDING)

    meta = {
        "fight": {"fromX": fx0, "toX": fx1, "fromY": fy0, "toY": fy1, "z": z},
        "landing": {"x": LANDING[0], "y": LANDING[1], "z": LANDING[2]},
        "returnTp": {"x": RETURN_TP[0], "y": RETURN_TP[1], "z": RETURN_TP[2]},
        "leverStart": {"x": LEVER_START[0], "y": LEVER_START[1], "z": LEVER_START[2], "uid": UID_START},
        "leverRank": {"x": LEVER_RANK[0], "y": LEVER_RANK[1], "z": LEVER_RANK[2], "uid": UID_RANK},
        "hubPortal": {"x": hub_portal[0], "y": hub_portal[1], "z": hub_portal[2]},
        "hubLanding": {"x": hub_landing[0], "y": hub_landing[1], "z": hub_landing[2]},
        "footprint": {"fromX": x0, "toX": x1, "fromY": y0, "toY": y1, "z": z},
    }
    return tiles, meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    project = project_root()
    otbm_path = args.map or (project / "server/YurOTS/ots/data/world/test.otbm")
    manifest_path = args.manifest or (
        project / "server/YurOTS/ots/data/world/generated-wave-arena.json"
    )
    if not otbm_path.is_file():
        print(f"ERROR: no existe {otbm_path}", file=sys.stderr)
        return 1

    tiles, meta = build_arena_tiles(HUB_PORTAL, HUB_LANDING)
    fp = meta["footprint"]
    path_n = sum(1 for s in tiles.values() if s.ground == GROUND_PATH)
    tele_n = sum(1 for s in tiles.values() if s.teleport)
    item_n = sum(len(s.items) for s in tiles.values())

    print("Wave arena — oleadas (aparte de Alice / hunt / floor)")
    print(
        f"Portal: ({HUB_PORTAL[0]},{HUB_PORTAL[1]},{HUB_PORTAL[2]}) → "
        f"({LANDING[0]},{LANDING[1]},{LANDING[2]})"
    )
    print(
        f"Retorno: ({RETURN_TP[0]},{RETURN_TP[1]},{RETURN_TP[2]}) → "
        f"({HUB_LANDING[0]},{HUB_LANDING[1]},{HUB_LANDING[2]})"
    )
    print(
        f"Fight 7×7: X {FIGHT_X0}-{FIGHT_X0+6}, Y {FIGHT_Y0}-{FIGHT_Y0+6}, z{ARENA_Z}"
    )
    print(
        f"Lever start uid={UID_START} @ ({LEVER_START[0]},{LEVER_START[1]}) | "
        f"rank uid={UID_RANK} @ ({LEVER_RANK[0]},{LEVER_RANK[1]})"
    )
    print(f"Tiles path={path_n} teleports={tele_n} items={item_n}")
    print(f"Footprint X {fp['fromX']}-{fp['toX']} Y {fp['fromY']}-{fp['toY']}")

    summary = {
        "name": "generated-wave-arena",
        "leverItemId": LEVER_ITEM,
        "uidStart": UID_START,
        "uidRank": UID_RANK,
        "tileCounts": {"path": path_n, "teleports": tele_n, "items": item_n, "total": len(tiles)},
        **meta,
    }

    if args.dry_run:
        print("\n(dry-run — no se escribió)")
        return 0
    if not args.replace:
        print("ERROR: usá --replace", file=sys.stderr)
        return 1

    raw = otbm_path.read_bytes()
    body = raw[4:]
    body = _maze.filter_tiles_in_bbox(
        body, fp["fromX"], fp["fromY"], fp["toX"], fp["toY"], ARENA_Z
    )
    body = _maze.filter_tiles_in_bbox(
        body,
        HUB_PORTAL[0],
        HUB_PORTAL[1],
        HUB_PORTAL[0],
        HUB_PORTAL[1],
        HUB_PORTAL[2],
    )
    insert_at = _maze.find_map_data_insert(body)
    patch = b"".join(group_tile_areas(tiles))
    patched = raw[:4] + body[:insert_at] + patch + body[insert_at:]

    backup = otbm_path.with_suffix(".otbm.bak-wave-arena")
    if not backup.exists():
        backup.write_bytes(raw)
        print(f"\nBackup: {backup}")

    otbm_path.write_bytes(patched)
    manifest_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"\nOK — mapa: {otbm_path}")
    print(f"OK — manifiesto: {manifest_path}")
    print("Reiniciá yout OT para cargar actions Lua.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
