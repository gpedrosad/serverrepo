#!/usr/bin/env python3
"""Fish TP — pozo de pesca en templo → lagoon con mobs.

Templo: agua en 164,54,7 (usar fishing rod 2580). Cartel 164,53,7.
Lagoon z6 + fondo neutro z5. Retorno templo 165,54,7.

Uso:
  python3 scripts/map/generate-fish-tp.py --dry-run
  python3 scripts/map/generate-fish-tp.py --replace
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
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

GROUND_PATH = 406
GROUND_BG = 405
GROUND_WATER = 490
TELEPORT_ITEM = _maze.TELEPORT_ITEM
NODE_START = _maze.NODE_START
NODE_END = _maze.NODE_END
OTBM_TILE_AREA = _maze.OTBM_TILE_AREA
OTBM_TILE = _maze.OTBM_TILE
OTBM_ITEM = _maze.OTBM_ITEM
OTBM_ATTR_TELE_DEST = _maze.OTBM_ATTR_TELE_DEST
OTBM_ATTR_ITEM = _maze.OTBM_ATTR_ITEM
OTBM_ATTR_TEXT = 6
write_props = _maze.write_props

FISH_HOLE = (164, 54, 7)
TEMPLE_RETURN = (165, 54, 7)
HUB_GROUND = 407
SIGN_ITEM = 1429

Z_PLAY = 6
Z_BG = 5

# Lagoon east of other arenas
LAGOON = dict(x0=300, y0=385, x1=318, y1=400)
LANDING = (309, 392, Z_PLAY)
RETURN_TP = (310, 398, Z_PLAY)
# Inner water pool
WATER = dict(x0=304, y0=388, x1=314, y1=395)

TEMPLE_SIGN = (
    164,
    53,
    7,
    "FISH TP\nUsa fishing rod en el agua.\nLagoon + crabs",
)


@dataclass
class FItem:
    item_id: int
    text: str | None = None


@dataclass
class FTile:
    ground: int
    teleport: tuple[int, int, int] | None = None
    items: list[FItem] = field(default_factory=list)


def project_root() -> Path:
    return next(
        p
        for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
        if (p / "AGENTS.md").is_file() or (p / ".git").is_dir()
    )


def encode_string(text: str) -> bytes:
    raw = text.encode("ascii", errors="replace")
    return struct.pack("<H", len(raw)) + raw


def encode_item_node(it: FItem, tele: tuple[int, int, int] | None = None) -> bytes:
    props = struct.pack("<H", it.item_id)
    if it.text is not None:
        props += struct.pack("<B", OTBM_ATTR_TEXT) + encode_string(it.text)
    if tele is not None:
        props += struct.pack("<BHHB", OTBM_ATTR_TELE_DEST, tele[0], tele[1], tele[2])
    buf = bytearray()
    buf.append(NODE_START)
    buf.append(OTBM_ITEM)
    write_props(buf, props)
    buf.append(NODE_END)
    return bytes(buf)


def encode_tile_node(x_off: int, y_off: int, spec: FTile) -> bytes:
    props = struct.pack("<BB", x_off, y_off)
    props += struct.pack("<BH", OTBM_ATTR_ITEM, spec.ground)
    buf = bytearray()
    buf.append(NODE_START)
    buf.append(OTBM_TILE)
    write_props(buf, props)
    if spec.teleport is not None:
        buf.extend(encode_item_node(FItem(TELEPORT_ITEM), tele=spec.teleport))
    for it in spec.items:
        buf.extend(encode_item_node(it))
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


def group_tile_areas(tiles: dict[tuple[int, int, int], FTile]) -> list[bytes]:
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


def fill_rect(tiles, x0, y0, x1, y1, z, ground) -> None:
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            tiles[(x, y, z)] = FTile(ground=ground)


def build_tiles() -> tuple[dict[tuple[int, int, int], FTile], dict]:
    x0, y0 = LAGOON["x0"] - 2, LAGOON["y0"] - 2
    x1, y1 = LAGOON["x1"] + 2, LAGOON["y1"] + 2
    tiles: dict[tuple[int, int, int], FTile] = {}

    fill_rect(tiles, x0, y0, x1, y1, Z_BG, GROUND_BG)
    fill_rect(tiles, x0, y0, x1, y1, Z_PLAY, GROUND_BG)
    fill_rect(
        tiles,
        LAGOON["x0"],
        LAGOON["y0"],
        LAGOON["x1"],
        LAGOON["y1"],
        Z_PLAY,
        GROUND_PATH,
    )
    fill_rect(
        tiles,
        WATER["x0"],
        WATER["y0"],
        WATER["x1"],
        WATER["y1"],
        Z_PLAY,
        GROUND_WATER,
    )
    # Shore ring around water so landing is walkable
    for y in range(WATER["y0"] - 1, WATER["y1"] + 2):
        for x in range(WATER["x0"] - 1, WATER["x1"] + 2):
            if (
                x < WATER["x0"]
                or x > WATER["x1"]
                or y < WATER["y0"]
                or y > WATER["y1"]
            ):
                if LAGOON["x0"] <= x <= LAGOON["x1"] and LAGOON["y0"] <= y <= LAGOON["y1"]:
                    tiles[(x, y, Z_PLAY)] = FTile(ground=GROUND_PATH)

    tiles[LANDING] = FTile(ground=GROUND_PATH)
    tiles[RETURN_TP] = FTile(ground=GROUND_PATH, teleport=TEMPLE_RETURN)

    # Temple fish hole + small path pad + sign
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            tx, ty = FISH_HOLE[0] + dx, FISH_HOLE[1] + dy
            if (tx, ty) == (FISH_HOLE[0], FISH_HOLE[1]):
                tiles[(tx, ty, 7)] = FTile(ground=GROUND_WATER)
            else:
                tiles[(tx, ty, 7)] = FTile(ground=HUB_GROUND)
    tiles[TEMPLE_RETURN] = FTile(ground=HUB_GROUND)
    sx, sy, sz, stext = TEMPLE_SIGN
    tiles[(sx, sy, sz)] = FTile(ground=HUB_GROUND, items=[FItem(SIGN_ITEM)])

    meta = {
        "fishHole": {"x": FISH_HOLE[0], "y": FISH_HOLE[1], "z": FISH_HOLE[2]},
        "templeReturn": {
            "x": TEMPLE_RETURN[0],
            "y": TEMPLE_RETURN[1],
            "z": TEMPLE_RETURN[2],
        },
        "landing": {"x": LANDING[0], "y": LANDING[1], "z": LANDING[2]},
        "returnTp": {"x": RETURN_TP[0], "y": RETURN_TP[1], "z": RETURN_TP[2]},
        "lagoon": {**LAGOON, "z": Z_PLAY},
        "water": {**WATER, "z": Z_PLAY},
        "zPlay": Z_PLAY,
        "zBg": Z_BG,
        "templeSign": {"x": sx, "y": sy, "z": sz, "text": stext},
        "clearBoxes": [
            {"fromX": x0, "toX": x1, "fromY": y0, "toY": y1, "z": Z_PLAY},
            {"fromX": x0, "toX": x1, "fromY": y0, "toY": y1, "z": Z_BG},
            {
                "fromX": FISH_HOLE[0] - 1,
                "toX": FISH_HOLE[0] + 1,
                "fromY": FISH_HOLE[1] - 1,
                "toY": FISH_HOLE[1] + 1,
                "z": 7,
            },
            {
                "fromX": TEMPLE_RETURN[0],
                "toX": TEMPLE_RETURN[0],
                "fromY": TEMPLE_RETURN[1],
                "toY": TEMPLE_RETURN[1],
                "z": 7,
            },
            {"fromX": sx, "toX": sx, "fromY": sy, "toY": sy, "z": sz},
        ],
    }
    return tiles, meta


def patch_readables(project: Path, meta: dict) -> None:
    path = project / "server/YurOTS/ots/data/readables.xml"
    begin = "<!-- BEGIN FISH_TP_SIGNS -->"
    end = "<!-- END FISH_TP_SIGNS -->"
    s = meta["templeSign"]
    text = s["text"].replace("\n", "\\n")
    block = (
        f"\t{begin}\n"
        f'\t<readable x="{s["x"]}" y="{s["y"]}" z="{s["z"]}" text="{text}"/>\n'
        f"\t{end}\n"
    )
    raw = path.read_text(encoding="utf-8")
    pat = re.compile(re.escape(begin) + r".*?" + re.escape(end) + r"\n?", re.DOTALL)
    if pat.search(raw):
        raw = pat.sub(block, raw, count=1)
    else:
        raw = raw.replace("</readables>", block + "</readables>")
    path.write_text(raw, encoding="utf-8")


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
        project / "server/YurOTS/ots/data/world/generated-fish-tp.json"
    )

    tiles, meta = build_tiles()
    print("Fish TP")
    print(
        f"Hole ({FISH_HOLE[0]},{FISH_HOLE[1]},{FISH_HOLE[2]}) water "
        f"→ landing ({LANDING[0]},{LANDING[1]},{LANDING[2]})"
    )
    print(f"tiles={len(tiles)} zPlay={Z_PLAY} zBg={Z_BG}")

    summary = {"name": "generated-fish-tp", "tileCount": len(tiles), **meta}
    if args.dry_run:
        print("(dry-run)")
        return 0
    if not args.replace:
        print("ERROR: usa --replace", file=sys.stderr)
        return 1

    raw = otbm_path.read_bytes()
    body = raw[4:]
    for box in meta["clearBoxes"]:
        body = _maze.filter_tiles_in_bbox(
            body, box["fromX"], box["fromY"], box["toX"], box["toY"], box["z"]
        )
    insert_at = _maze.find_map_data_insert(body)
    patch = b"".join(group_tile_areas(tiles))
    patched = raw[:4] + body[:insert_at] + patch + body[insert_at:]

    backup = otbm_path.with_suffix(".otbm.bak-fish-tp")
    if not backup.exists():
        backup.write_bytes(raw)
        print(f"Backup: {backup}")

    otbm_path.write_bytes(patched)
    patch_readables(project, meta)
    manifest_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"OK mapa {otbm_path}")
    print(f"OK readables + {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
