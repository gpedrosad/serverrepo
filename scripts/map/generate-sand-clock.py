#!/usr/bin/env python3
"""Reloj de Arena — sala compartida con fases globales (Chronos).

Templo: TP 166,54,7 → sala z6. Retorno templo 167,54,7.
Sala simple path 406 + fondo neutro z5 (mismo patrón Wave/Fish/Fosos).
NPC Chronos se spawnea vía data/world/npc.xml (no en OTBM).

Uso:
  python3 scripts/map/generate-sand-clock.py --dry-run
  python3 scripts/map/generate-sand-clock.py --replace
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

HUB_PORTAL = (166, 54, 7)
TEMPLE_RETURN = (167, 54, 7)
HUB_GROUND = 407
SIGN_ITEM = 1433

Z_PLAY = 6
Z_BG = 5

ROOM = dict(x0=330, y0=385, x1=346, y1=399)
LANDING = (338, 392, Z_PLAY)
RETURN_TP = (338, 398, Z_PLAY)
# Chronos stand (libre, norte de la sala) — documentado; spawn en npc.xml
CHRONOS_POS = (338, 387, Z_PLAY)

TEMPLE_SIGN = (
    166,
    53,
    7,
    "RELOJ DE ARENA\nSala compartida.\nFases cada 120 s",
)


@dataclass
class SItem:
    item_id: int
    text: str | None = None


@dataclass
class STile:
    ground: int
    teleport: tuple[int, int, int] | None = None
    items: list[SItem] = field(default_factory=list)


def project_root() -> Path:
    return next(
        p
        for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
        if (p / "AGENTS.md").is_file() or (p / ".git").is_dir()
    )


def encode_string(text: str) -> bytes:
    raw = text.encode("ascii", errors="replace")
    return struct.pack("<H", len(raw)) + raw


def encode_item_node(it: SItem, tele: tuple[int, int, int] | None = None) -> bytes:
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


def encode_tile_node(x_off: int, y_off: int, spec: STile) -> bytes:
    props = struct.pack("<BB", x_off, y_off)
    props += struct.pack("<BH", OTBM_ATTR_ITEM, spec.ground)
    buf = bytearray()
    buf.append(NODE_START)
    buf.append(OTBM_TILE)
    write_props(buf, props)
    if spec.teleport is not None:
        buf.extend(encode_item_node(SItem(TELEPORT_ITEM), tele=spec.teleport))
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


def group_tile_areas(tiles: dict[tuple[int, int, int], STile]) -> list[bytes]:
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
            tiles[(x, y, z)] = STile(ground=ground)


def build_tiles() -> tuple[dict[tuple[int, int, int], STile], dict]:
    pad = 2
    x0, y0 = ROOM["x0"] - pad, ROOM["y0"] - pad
    x1, y1 = ROOM["x1"] + pad, ROOM["y1"] + pad
    tiles: dict[tuple[int, int, int], STile] = {}

    fill_rect(tiles, x0, y0, x1, y1, Z_BG, GROUND_BG)
    fill_rect(tiles, x0, y0, x1, y1, Z_PLAY, GROUND_BG)
    fill_rect(
        tiles,
        ROOM["x0"],
        ROOM["y0"],
        ROOM["x1"],
        ROOM["y1"],
        Z_PLAY,
        GROUND_PATH,
    )

    tiles[LANDING] = STile(ground=GROUND_PATH)
    tiles[RETURN_TP] = STile(ground=GROUND_PATH, teleport=TEMPLE_RETURN)
    tiles[CHRONOS_POS] = STile(ground=GROUND_PATH)

    # Temple pad + portal + return + sign
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            tx, ty = HUB_PORTAL[0] + dx, HUB_PORTAL[1] + dy
            tiles[(tx, ty, 7)] = STile(ground=HUB_GROUND)
    tiles[HUB_PORTAL] = STile(ground=HUB_GROUND, teleport=LANDING)
    tiles[TEMPLE_RETURN] = STile(ground=HUB_GROUND)
    sx, sy, sz, stext = TEMPLE_SIGN
    tiles[(sx, sy, sz)] = STile(ground=HUB_GROUND, items=[SItem(SIGN_ITEM)])

    meta = {
        "hubPortal": {"x": HUB_PORTAL[0], "y": HUB_PORTAL[1], "z": HUB_PORTAL[2]},
        "templeReturn": {
            "x": TEMPLE_RETURN[0],
            "y": TEMPLE_RETURN[1],
            "z": TEMPLE_RETURN[2],
        },
        "landing": {"x": LANDING[0], "y": LANDING[1], "z": LANDING[2]},
        "returnTp": {"x": RETURN_TP[0], "y": RETURN_TP[1], "z": RETURN_TP[2]},
        "chronos": {"x": CHRONOS_POS[0], "y": CHRONOS_POS[1], "z": CHRONOS_POS[2]},
        "room": {**ROOM, "z": Z_PLAY},
        "zPlay": Z_PLAY,
        "zBg": Z_BG,
        "phaseSec": 120,
        "templeSign": {"x": sx, "y": sy, "z": sz, "text": stext},
        "clearBoxes": [
            {"fromX": x0, "toX": x1, "fromY": y0, "toY": y1, "z": Z_PLAY},
            {"fromX": x0, "toX": x1, "fromY": y0, "toY": y1, "z": Z_BG},
            {
                "fromX": HUB_PORTAL[0] - 1,
                "toX": HUB_PORTAL[0] + 1,
                "fromY": HUB_PORTAL[1] - 1,
                "toY": HUB_PORTAL[1] + 1,
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
    begin = "<!-- BEGIN SAND_CLOCK_SIGNS -->"
    end = "<!-- END SAND_CLOCK_SIGNS -->"
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
        project / "server/YurOTS/ots/data/world/generated-sand-clock.json"
    )

    tiles, meta = build_tiles()
    print("Reloj de Arena / Sand Clock")
    print(
        f"Portal ({HUB_PORTAL[0]},{HUB_PORTAL[1]},{HUB_PORTAL[2]}) "
        f"→ landing ({LANDING[0]},{LANDING[1]},{LANDING[2]})"
    )
    print(
        f"Chronos ({CHRONOS_POS[0]},{CHRONOS_POS[1]},{CHRONOS_POS[2]}) "
        f"room {ROOM['x0']}-{ROOM['x1']},{ROOM['y0']}-{ROOM['y1']} z{Z_PLAY}"
    )
    print(f"tiles={len(tiles)} zPlay={Z_PLAY} zBg={Z_BG}")

    summary = {"name": "generated-sand-clock", "tileCount": len(tiles), **meta}
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

    backup = otbm_path.with_suffix(".otbm.bak-sand-clock")
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
    raise SystemExit(main())
