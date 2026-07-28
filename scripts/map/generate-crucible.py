#!/usr/bin/env python3
"""El Crisol — 3 puertas (Bronce/Plata/Oro) + bosses diarios + carteles templo.

Portal templo 157,54,7 → hub z0. Salas separadas en XY (z0 vacío).
Carteles 1429 en templo (y=53) para Wave / Maze / Floor / Crisol.
UID palancas: 7200 Bronce, 7201 Plata, 7202 Oro, 7203 cartel del dia.

Uso:
  python3 scripts/generate-crucible.py --dry-run
  python3 scripts/generate-crucible.py --replace
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
write_props = _maze.write_props

# 158,54,7 = landing de retorno Wave Arena — NO ocupar con TP.
HUB_PORTAL = (157, 54, 7)
HUB_LANDING_TEMPLE = (156, 54, 7)
HUB_GROUND = 407
SIGN_ITEM = 1429  # sign de templo (board)
LEVER_ITEM = 1945

Z = 0
# Hub
HUB = dict(x0=80, y0=80, x1=100, y1=96)
LANDING = (85, 92, Z)
RETURN_TP = (86, 93, Z)
LEVER_BRONZE = (83, 88, Z)
LEVER_SILVER = (85, 88, Z)
LEVER_GOLD = (87, 88, Z)
LEVER_INFO = (90, 88, Z)
SIGN_BRONZE = (83, 87, Z)
SIGN_SILVER = (85, 87, Z)
SIGN_GOLD = (87, 87, Z)
SIGN_INFO = (90, 87, Z)

# Arenas (separadas)
BRONZE = dict(x0=110, y0=80, x1=122, y1=92)
SILVER = dict(x0=140, y0=80, x1=154, y1=96)
GOLD = dict(x0=170, y0=80, x1=188, y1=100)
EXIT_BRONZE = (116, 91, Z)
EXIT_SILVER = (147, 95, Z)
EXIT_GOLD = (179, 99, Z)
ENTRY_BRONZE = (116, 86, Z)
ENTRY_SILVER = (147, 88, Z)
ENTRY_GOLD = (179, 90, Z)

UID_BRONZE = 7200
UID_SILVER = 7201
UID_GOLD = 7202
UID_INFO = 7203

# Carteles templo (norte de cada TP). Crisol en 157; 158 libre (retorno Wave).
TEMPLE_SIGNS = (
    (157, 53, 7, "CRISOL\n3 puertas. Boss diario.\nBronce / Plata / Oro"),
    (159, 53, 7, "WAVE ARENA\nOleadas. Palanca = next.\nRanking semanal"),
    (160, 53, 7, "HUNT MAZE\nLaberinto mid-hard\nDesde Minotauros"),
    (162, 53, 7, "FLOOR CAMPUS\n16 salas separadas\nMinos -> Behemoth"),
)


@dataclass
class CItem:
    item_id: int
    unique_id: int | None = None
    text: str | None = None


@dataclass
class CTile:
    ground: int
    teleport: tuple[int, int, int] | None = None
    items: list[CItem] = field(default_factory=list)


def project_root() -> Path:
    return next(
        p
        for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
        if (p / "AGENTS.md").is_file() or (p / ".git").is_dir()
    )


def encode_string(text: str) -> bytes:
    raw = text.replace("\n", "\n").encode("ascii", errors="replace")
    return struct.pack("<H", len(raw)) + raw


def encode_item_node(it: CItem, tele: tuple[int, int, int] | None = None) -> bytes:
    props = struct.pack("<H", it.item_id)
    if it.unique_id is not None:
        props += struct.pack("<BH", OTBM_ATTR_UNIQUE_ID, it.unique_id)
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


def encode_tile_node(x_off: int, y_off: int, spec: CTile) -> bytes:
    props = struct.pack("<BB", x_off, y_off)
    props += struct.pack("<BH", OTBM_ATTR_ITEM, spec.ground)
    buf = bytearray()
    buf.append(NODE_START)
    buf.append(OTBM_TILE)
    write_props(buf, props)
    if spec.teleport is not None:
        buf.extend(
            encode_item_node(CItem(TELEPORT_ITEM), tele=spec.teleport)
        )
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


def group_tile_areas(tiles: dict[tuple[int, int, int], CTile]) -> list[bytes]:
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
    tiles: dict,
    box: dict,
    z: int,
    ground: int,
) -> None:
    for y in range(box["y0"], box["y1"] + 1):
        for x in range(box["x0"], box["x1"] + 1):
            tiles[(x, y, z)] = CTile(ground=ground)


def build_tiles() -> tuple[dict[tuple[int, int, int], CTile], dict]:
    tiles: dict[tuple[int, int, int], CTile] = {}

    fill_rect(tiles, HUB, Z, GROUND_BG)
    fill_rect(tiles, BRONZE, Z, GROUND_BG)
    fill_rect(tiles, SILVER, Z, GROUND_BG)
    fill_rect(tiles, GOLD, Z, GROUND_BG)

    # Hub floor
    for y in range(HUB["y0"] + 1, HUB["y1"]):
        for x in range(HUB["x0"] + 1, HUB["x1"]):
            tiles[(x, y, Z)] = CTile(ground=GROUND_PATH)

    for box in (BRONZE, SILVER, GOLD):
        for y in range(box["y0"] + 1, box["y1"]):
            for x in range(box["x0"] + 1, box["x1"]):
                tiles[(x, y, Z)] = CTile(ground=GROUND_PATH)

    tiles[LANDING] = CTile(ground=GROUND_PATH)
    tiles[RETURN_TP] = CTile(ground=GROUND_PATH, teleport=HUB_LANDING_TEMPLE)
    tiles[EXIT_BRONZE] = CTile(ground=GROUND_PATH, teleport=LANDING)
    tiles[EXIT_SILVER] = CTile(ground=GROUND_PATH, teleport=LANDING)
    tiles[EXIT_GOLD] = CTile(ground=GROUND_PATH, teleport=LANDING)

    tiles[LEVER_BRONZE] = CTile(
        ground=GROUND_PATH,
        items=[CItem(LEVER_ITEM, unique_id=UID_BRONZE)],
    )
    tiles[LEVER_SILVER] = CTile(
        ground=GROUND_PATH,
        items=[CItem(LEVER_ITEM, unique_id=UID_SILVER)],
    )
    tiles[LEVER_GOLD] = CTile(
        ground=GROUND_PATH,
        items=[CItem(LEVER_ITEM, unique_id=UID_GOLD)],
    )
    tiles[LEVER_INFO] = CTile(
        ground=GROUND_PATH,
        items=[CItem(LEVER_ITEM, unique_id=UID_INFO)],
    )

    # Signs in hub (text also in readables.xml for look)
    tiles[SIGN_BRONZE] = CTile(
        ground=GROUND_PATH, items=[CItem(SIGN_ITEM)]
    )
    tiles[SIGN_SILVER] = CTile(
        ground=GROUND_PATH, items=[CItem(SIGN_ITEM)]
    )
    tiles[SIGN_GOLD] = CTile(
        ground=GROUND_PATH, items=[CItem(SIGN_ITEM)]
    )
    tiles[SIGN_INFO] = CTile(
        ground=GROUND_PATH, items=[CItem(SIGN_ITEM)]
    )

    # Temple portal + signs (z7)
    tiles[HUB_PORTAL] = CTile(ground=HUB_GROUND, teleport=LANDING)
    tiles[HUB_LANDING_TEMPLE] = CTile(ground=HUB_GROUND)
    for x, y, z, _txt in TEMPLE_SIGNS:
        # Sign must be top thing (readables.xml). Ground near temple TPs.
        if (x, y) in ((157, 53), (159, 53)):
            g = HUB_GROUND
        elif (x, y) == (160, 53):
            g = 457
        else:
            g = GROUND_PATH
        tiles[(x, y, z)] = CTile(ground=g, items=[CItem(SIGN_ITEM)])

    meta = {
        "hubPortal": {"x": HUB_PORTAL[0], "y": HUB_PORTAL[1], "z": HUB_PORTAL[2]},
        "landing": {"x": LANDING[0], "y": LANDING[1], "z": LANDING[2]},
        "returnTp": {"x": RETURN_TP[0], "y": RETURN_TP[1], "z": RETURN_TP[2]},
        "levers": {
            "bronze": {"x": LEVER_BRONZE[0], "y": LEVER_BRONZE[1], "z": Z, "uid": UID_BRONZE},
            "silver": {"x": LEVER_SILVER[0], "y": LEVER_SILVER[1], "z": Z, "uid": UID_SILVER},
            "gold": {"x": LEVER_GOLD[0], "y": LEVER_GOLD[1], "z": Z, "uid": UID_GOLD},
            "info": {"x": LEVER_INFO[0], "y": LEVER_INFO[1], "z": Z, "uid": UID_INFO},
        },
        "arenas": {
            "bronze": {**BRONZE, "z": Z, "entry": ENTRY_BRONZE, "exit": EXIT_BRONZE},
            "silver": {**SILVER, "z": Z, "entry": ENTRY_SILVER, "exit": EXIT_SILVER},
            "gold": {**GOLD, "z": Z, "entry": ENTRY_GOLD, "exit": EXIT_GOLD},
        },
        "templeSigns": [
            {"x": x, "y": y, "z": z, "text": t} for x, y, z, t in TEMPLE_SIGNS
        ],
        "hubSigns": [
            {"x": SIGN_BRONZE[0], "y": SIGN_BRONZE[1], "z": Z, "text": "BRONCE - riesgo bajo"},
            {"x": SIGN_SILVER[0], "y": SIGN_SILVER[1], "z": Z, "text": "PLATA - riesgo medio"},
            {"x": SIGN_GOLD[0], "y": SIGN_GOLD[1], "z": Z, "text": "ORO - boss diario"},
            {"x": SIGN_INFO[0], "y": SIGN_INFO[1], "z": Z, "text": "INFO - bosses de hoy"},
        ],
        "clearBoxes": [
            {"fromX": HUB["x0"], "toX": HUB["x1"], "fromY": HUB["y0"], "toY": HUB["y1"], "z": Z},
            {"fromX": BRONZE["x0"], "toX": BRONZE["x1"], "fromY": BRONZE["y0"], "toY": BRONZE["y1"], "z": Z},
            {"fromX": SILVER["x0"], "toX": SILVER["x1"], "fromY": SILVER["y0"], "toY": SILVER["y1"], "z": Z},
            {"fromX": GOLD["x0"], "toX": GOLD["x1"], "fromY": GOLD["y0"], "toY": GOLD["y1"], "z": Z},
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
        ]
        + [
            {"fromX": x, "toX": x, "fromY": y, "toY": y, "z": z}
            for x, y, z, _ in TEMPLE_SIGNS
        ],
    }
    return tiles, meta


def patch_readables(project: Path, meta: dict) -> None:
    path = project / "server/YurOTS/ots/data/readables.xml"
    begin = "<!-- BEGIN CRUCIBLE_SIGNS -->"
    end = "<!-- END CRUCIBLE_SIGNS -->"
    lines = [f"\t{begin}"]
    # Keep ASCII for client
    for s in meta["templeSigns"] + meta["hubSigns"]:
        text = s["text"].replace("\n", "\\n")
        lines.append(
            f'\t<readable x="{s["x"]}" y="{s["y"]}" z="{s["z"]}" text="{text}"/>'
        )
    lines.append(f"\t{end}")
    block = "\n".join(lines) + "\n"

    raw = path.read_text(encoding="utf-8")
    import re

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
        project / "server/YurOTS/ots/data/world/generated-crucible.json"
    )

    tiles, meta = build_tiles()
    print("El Crisol — hub + 3 arenas (z0) + carteles templo")
    print(
        f"Portal ({HUB_PORTAL[0]},{HUB_PORTAL[1]},{HUB_PORTAL[2]}) → "
        f"({LANDING[0]},{LANDING[1]},{LANDING[2]})"
    )
    print(
        f"Levers uid {UID_BRONZE}/{UID_SILVER}/{UID_GOLD}/{UID_INFO} | "
        f"tiles {len(tiles)}"
    )
    for s in TEMPLE_SIGNS:
        print(f"  cartel templo ({s[0]},{s[1]},{s[2]}): {s[3].split(chr(10))[0]}")

    summary = {"name": "generated-crucible", "tileCount": len(tiles), **meta}

    if args.dry_run:
        print("\n(dry-run)")
        return 0
    if not args.replace:
        print("ERROR: usá --replace", file=sys.stderr)
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

    backup = otbm_path.with_suffix(".otbm.bak-crucible")
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
