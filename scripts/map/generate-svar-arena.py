#!/usr/bin/env python3
"""Arena de Fosos (estilo Svargrond 8.x) — un piso de juego + fondo neutro.

Portal templo 161,54,7 → lobby z6. Diez fosos en fila (mismo z).
Reward: 3 cofres (elegir uno); showcase 1 sqm al norte sin acceso.
Fondo neutro: z5 = solo GROUND_BG bajo el footprint.

UID palancas:
  7300 Greenhorn / 7301 Scrapper / 7302 Warlord / 7303 Info
  7304 Next pit (en cada foso) / 7305 Forfeit (en cada foso)
UID cofres reward: 7310 / 7311 / 7312

Uso:
  python3 scripts/map/generate-svar-arena.py --dry-run
  python3 scripts/map/generate-svar-arena.py --replace
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
OTBM_ATTR_UNIQUE_ID = 5
OTBM_ATTR_TEXT = 6
OTBM_ATTR_DESC = 7
write_props = _maze.write_props

HUB_PORTAL = (161, 54, 7)
HUB_LANDING_TEMPLE = (163, 54, 7)
HUB_GROUND = 407
SIGN_ITEM = 1433
LEVER_ITEM = 1945
CHEST_ITEM = 1740
WALL_ITEM = 1036  # bloquea paso al showcase

Z_PLAY = 6
Z_BG = 5

# Lobby
LOBBY = dict(x0=200, y0=390, x1=214, y1=400)
LANDING = (205, 396, Z_PLAY)
RETURN_TP = (206, 398, Z_PLAY)
LEVER_GREEN = (203, 393, Z_PLAY)
LEVER_SCRAP = (205, 393, Z_PLAY)
LEVER_WAR = (207, 393, Z_PLAY)
LEVER_INFO = (210, 393, Z_PLAY)

# 10 pits in a row east of lobby (5x5 each, gap 2)
PIT_Y0, PIT_Y1 = 390, 394
PIT_SIZE = 5
PIT_GAP = 2
PIT_X0 = 218
N_PITS = 10

# Reward room south of lobby
# y404 showcase (sin acceso) | y405 muro | y407 cofres | y411 salida
REWARD = dict(x0=200, y0=403, x1=214, y1=412)
REWARD_ENTRY = (207, 408, Z_PLAY)
REWARD_EXIT = (207, 411, Z_PLAY)
CHESTS = (
    (204, 407, Z_PLAY),
    (207, 407, Z_PLAY),
    (210, 407, Z_PLAY),
)
SHOWCASES = (
    (204, 404, Z_PLAY),
    (207, 404, Z_PLAY),
    (210, 404, Z_PLAY),
)
WALL_ROW_Y = 405

UID_GREEN = 7300
UID_SCRAP = 7301
UID_WAR = 7302
UID_INFO = 7303
UID_NEXT = 7304
UID_FORFEIT = 7305
UID_CHESTS = (7310, 7311, 7312)

# Display prizes (must match svar_arena.lua). One per chest slot.
SHOW_ITEMS = (
    # greenhorn defaults shown; Lua picks set by difficulty. Map shows greenhorn set.
    2160,  # crystal coin
    2392,  # fire sword
    2476,  # knight armor
)

TEMPLE_SIGN = (
    161,
    53,
    7,
    "FOSOS\n3 dificultades. 10 pits.\nElegi 1 cofre al final",
)


@dataclass
class SItem:
    item_id: int
    unique_id: int | None = None
    description: str | None = None


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


def pit_box(i: int) -> dict:
    """0-based pit index → box + entry/lever spots."""
    x0 = PIT_X0 + i * (PIT_SIZE + PIT_GAP)
    x1 = x0 + PIT_SIZE - 1
    cx = x0 + PIT_SIZE // 2
    cy = PIT_Y0 + PIT_SIZE // 2
    return {
        "i": i + 1,
        "x0": x0,
        "x1": x1,
        "y0": PIT_Y0,
        "y1": PIT_Y1,
        "z": Z_PLAY,
        "entry": (cx, cy, Z_PLAY),
        "lever_next": (cx - 1, PIT_Y1, Z_PLAY),
        "lever_forfeit": (cx + 1, PIT_Y1, Z_PLAY),
    }


def encode_string(text: str) -> bytes:
    raw = text.encode("ascii", errors="replace")
    return struct.pack("<H", len(raw)) + raw


def encode_item_node(it: SItem, tele: tuple[int, int, int] | None = None) -> bytes:
    props = struct.pack("<H", it.item_id)
    if it.unique_id is not None:
        props += struct.pack("<BH", OTBM_ATTR_UNIQUE_ID, it.unique_id)
    if it.description is not None:
        props += struct.pack("<B", OTBM_ATTR_DESC) + encode_string(it.description)
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


def fill_rect(
    tiles: dict[tuple[int, int, int], STile],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    z: int,
    ground: int,
) -> None:
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            tiles[(x, y, z)] = STile(ground=ground)


def build_tiles() -> tuple[dict[tuple[int, int, int], STile], dict]:
    pits = [pit_box(i) for i in range(N_PITS)]
    last = pits[-1]
    x0 = min(LOBBY["x0"], PIT_X0) - 2
    x1 = max(LOBBY["x1"], last["x1"], REWARD["x1"]) + 2
    y0 = min(LOBBY["y0"], PIT_Y0, REWARD["y0"]) - 2
    y1 = max(LOBBY["y1"], PIT_Y1, REWARD["y1"]) + 2

    tiles: dict[tuple[int, int, int], STile] = {}

    # Fondo neutro (z5) + void play (z6)
    fill_rect(tiles, x0, y0, x1, y1, Z_BG, GROUND_BG)
    fill_rect(tiles, x0, y0, x1, y1, Z_PLAY, GROUND_BG)

    # Lobby
    fill_rect(
        tiles,
        LOBBY["x0"],
        LOBBY["y0"],
        LOBBY["x1"],
        LOBBY["y1"],
        Z_PLAY,
        GROUND_PATH,
    )
    tiles[LANDING] = STile(ground=GROUND_PATH)
    tiles[RETURN_TP] = STile(ground=GROUND_PATH, teleport=HUB_LANDING_TEMPLE)
    tiles[LEVER_GREEN] = STile(
        ground=GROUND_PATH,
        items=[SItem(LEVER_ITEM, unique_id=UID_GREEN, description="Greenhorn (1000 gp)")],
    )
    tiles[LEVER_SCRAP] = STile(
        ground=GROUND_PATH,
        items=[SItem(LEVER_ITEM, unique_id=UID_SCRAP, description="Scrapper (5000 gp)")],
    )
    tiles[LEVER_WAR] = STile(
        ground=GROUND_PATH,
        items=[SItem(LEVER_ITEM, unique_id=UID_WAR, description="Warlord (10000 gp)")],
    )
    tiles[LEVER_INFO] = STile(
        ground=GROUND_PATH,
        items=[SItem(LEVER_ITEM, unique_id=UID_INFO, description="Arena rules")],
    )

    # Pits
    for p in pits:
        fill_rect(tiles, p["x0"], p["y0"], p["x1"], p["y1"], Z_PLAY, GROUND_PATH)
        tiles[p["lever_next"]] = STile(
            ground=GROUND_PATH,
            items=[SItem(LEVER_ITEM, unique_id=UID_NEXT, description="Next pit")],
        )
        tiles[p["lever_forfeit"]] = STile(
            ground=GROUND_PATH,
            items=[SItem(LEVER_ITEM, unique_id=UID_FORFEIT, description="Forfeit")],
        )

    # Corridor lobby → pit1
    for x in range(LOBBY["x1"] + 1, pits[0]["x0"]):
        tiles[(x, 392, Z_PLAY)] = STile(ground=GROUND_PATH)

    # Reward room
    fill_rect(
        tiles,
        REWARD["x0"],
        REWARD["y0"],
        REWARD["x1"],
        REWARD["y1"],
        Z_PLAY,
        GROUND_PATH,
    )
    # Corridor lobby → reward
    for y in range(LOBBY["y1"] + 1, REWARD["y0"]):
        tiles[(207, y, Z_PLAY)] = STile(ground=GROUND_PATH)

    tiles[REWARD_ENTRY] = STile(ground=GROUND_PATH)
    tiles[REWARD_EXIT] = STile(ground=GROUND_PATH, teleport=HUB_LANDING_TEMPLE)

    # Wall row: blocks walking to showcase tiles
    for x in range(REWARD["x0"], REWARD["x1"] + 1):
        tiles[(x, WALL_ROW_Y, Z_PLAY)] = STile(
            ground=GROUND_PATH, items=[SItem(WALL_ITEM)]
        )

    # Chests + showcases (north of wall, no player access from reward floor)
    for i, (chest, show, prize, uid) in enumerate(
        zip(CHESTS, SHOWCASES, SHOW_ITEMS, UID_CHESTS)
    ):
        tiles[chest] = STile(
            ground=GROUND_PATH,
            items=[SItem(CHEST_ITEM, unique_id=uid, description=f"Prize chest {i + 1}")],
        )
        # Showcase sits north of wall (y=405); wall at 406 blocks from chests at 407
        tiles[show] = STile(
            ground=GROUND_PATH,
            items=[
                SItem(WALL_ITEM),
                SItem(prize, description="Display only"),
            ],
        )

    # Temple portal + sign
    tiles[HUB_PORTAL] = STile(ground=HUB_GROUND, teleport=LANDING)
    sx, sy, sz, stext = TEMPLE_SIGN
    tiles[(sx, sy, sz)] = STile(
        ground=HUB_GROUND if (sx, sy) == (161, 53) else GROUND_PATH,
        items=[SItem(SIGN_ITEM)],
    )

    meta = {
        "hubPortal": {"x": HUB_PORTAL[0], "y": HUB_PORTAL[1], "z": HUB_PORTAL[2]},
        "hubLanding": {
            "x": HUB_LANDING_TEMPLE[0],
            "y": HUB_LANDING_TEMPLE[1],
            "z": HUB_LANDING_TEMPLE[2],
        },
        "landing": {"x": LANDING[0], "y": LANDING[1], "z": LANDING[2]},
        "returnTp": {"x": RETURN_TP[0], "y": RETURN_TP[1], "z": RETURN_TP[2]},
        "rewardEntry": {"x": REWARD_ENTRY[0], "y": REWARD_ENTRY[1], "z": REWARD_ENTRY[2]},
        "rewardExit": {"x": REWARD_EXIT[0], "y": REWARD_EXIT[1], "z": REWARD_EXIT[2]},
        "zPlay": Z_PLAY,
        "zBg": Z_BG,
        "levers": {
            "greenhorn": {"x": LEVER_GREEN[0], "y": LEVER_GREEN[1], "z": Z_PLAY, "uid": UID_GREEN},
            "scrapper": {"x": LEVER_SCRAP[0], "y": LEVER_SCRAP[1], "z": Z_PLAY, "uid": UID_SCRAP},
            "warlord": {"x": LEVER_WAR[0], "y": LEVER_WAR[1], "z": Z_PLAY, "uid": UID_WAR},
            "info": {"x": LEVER_INFO[0], "y": LEVER_INFO[1], "z": Z_PLAY, "uid": UID_INFO},
            "next": {"uid": UID_NEXT},
            "forfeit": {"uid": UID_FORFEIT},
        },
        "chests": [
            {
                "x": c[0],
                "y": c[1],
                "z": c[2],
                "uid": uid,
                "showcase": {"x": s[0], "y": s[1], "z": s[2], "item": prize},
            }
            for c, s, uid, prize in zip(CHESTS, SHOWCASES, UID_CHESTS, SHOW_ITEMS)
        ],
        "pits": pits,
        "templeSign": {"x": sx, "y": sy, "z": sz, "text": stext},
        "clearBoxes": [
            {"fromX": x0, "toX": x1, "fromY": y0, "toY": y1, "z": Z_PLAY},
            {"fromX": x0, "toX": x1, "fromY": y0, "toY": y1, "z": Z_BG},
            {
                "fromX": HUB_PORTAL[0],
                "toX": HUB_PORTAL[0],
                "fromY": HUB_PORTAL[1],
                "toY": HUB_PORTAL[1],
                "z": 7,
            },
            {
                "fromX": HUB_LANDING_TEMPLE[0],
                "toX": HUB_LANDING_TEMPLE[0],
                "fromY": HUB_LANDING_TEMPLE[1],
                "toY": HUB_LANDING_TEMPLE[1],
                "z": 7,
            },
            {"fromX": sx, "toX": sx, "fromY": sy, "toY": sy, "z": sz},
        ],
        "footprint": {"fromX": x0, "toX": x1, "fromY": y0, "toY": y1},
    }
    return tiles, meta


def patch_readables(project: Path, meta: dict) -> None:
    path = project / "server/YurOTS/ots/data/readables.xml"
    begin = "<!-- BEGIN SVAR_ARENA_SIGNS -->"
    end = "<!-- END SVAR_ARENA_SIGNS -->"
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
        project / "server/YurOTS/ots/data/world/generated-svar-arena.json"
    )

    tiles, meta = build_tiles()
    pits = meta["pits"]
    print("Arena de Fosos (Svargrond-style)")
    print(
        f"Portal ({HUB_PORTAL[0]},{HUB_PORTAL[1]},{HUB_PORTAL[2]}) → "
        f"({LANDING[0]},{LANDING[1]},{LANDING[2]}) z{Z_PLAY}"
    )
    print(f"Fondo neutro z{Z_BG} | juego z{Z_PLAY} | pits={N_PITS}")
    print(
        f"Levers {UID_GREEN}/{UID_SCRAP}/{UID_WAR}/{UID_INFO} "
        f"next={UID_NEXT} forfeit={UID_FORFEIT}"
    )
    print(f"Chests uid {UID_CHESTS[0]}-{UID_CHESTS[2]} | tiles={len(tiles)}")
    print(
        f"Pit1 ({pits[0]['x0']}-{pits[0]['x1']},{pits[0]['y0']}-{pits[0]['y1']}) … "
        f"Pit10 ({pits[-1]['x0']}-{pits[-1]['x1']},{pits[-1]['y0']}-{pits[-1]['y1']})"
    )

    summary = {"name": "generated-svar-arena", "tileCount": len(tiles), **meta}

    if args.dry_run:
        print("\n(dry-run)")
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

    backup = otbm_path.with_suffix(".otbm.bak-svar-arena")
    if not backup.exists():
        backup.write_bytes(raw)
        print(f"Backup: {backup}")

    otbm_path.write_bytes(patched)
    patch_readables(project, meta)
    manifest_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"OK mapa {otbm_path}")
    print(f"OK readables + manifiesto {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
