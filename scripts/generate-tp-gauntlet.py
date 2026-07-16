#!/usr/bin/env python3
"""Genera un gauntlet de salas 3×3 + sala final de quest.

Salas puzzle (default 40): 3×3 con suelo 406 sobre void 100. Las 4 esquinas
tienen teleport (1387); solo 1 avanza, 3 mandan atrás. Una de las salas tiene
Fury. La última sala puzzle teleporta a la sala final.

Sala final: mismo formato 3×3, un solo TP (al templo), Wrath en el centro y
cofre de quest (soft boots).

Acceso: barco "gauntlet" (boat.lua) → sala 0; Nimral solo ahí (npc.xml).

Uso:
  python3 scripts/generate-tp-gauntlet.py --dry-run
  python3 scripts/generate-tp-gauntlet.py --replace
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
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

GROUND_PATH = _maze.GROUND_PATH
GROUND_BG = _maze.GROUND_BG
TELEPORT_ITEM = _maze.TELEPORT_ITEM
TEMPLE_DEST = _maze.TEMPLE_DEST
NODE_START = _maze.NODE_START
NODE_END = _maze.NODE_END
OTBM_TILE_AREA = _maze.OTBM_TILE_AREA
OTBM_TILE = _maze.OTBM_TILE
OTBM_ITEM = _maze.OTBM_ITEM
OTBM_ATTR_TELE_DEST = _maze.OTBM_ATTR_TELE_DEST
OTBM_ATTR_ITEM = _maze.OTBM_ATTR_ITEM
write_props = _maze.write_props

OTBM_ATTR_UNIQUE_ID = 5
QUEST_CHEST_ID = 1740
# Premio del cofre: Soft Boots (uniqueId = item id; quest.lua acepta 1001–4999).
QUEST_PRIZE_UID = 3549
QUEST_PRIZE_NAME = "soft boots"

ROOM_SIZE = 3
ROOM_GAP = 3
STRIDE = ROOM_SIZE + ROOM_GAP
FINAL_ROOM_GAP = 4  # void entre grid puzzle y sala final

CORNERS = ((0, 0), (2, 0), (2, 2), (0, 2))
CENTER = (1, 1)
CORNER_NAMES = ("NW", "NE", "SE", "SW")

# 40 salas puzzle; Fury forzada en índice FURY_ROOM_INDEX.
DEFAULT_PUZZLE_ROOMS = 40
FURY_ROOM_INDEX = 34
FINAL_BOSS = "Wrath"

DEFAULT_MONSTERS = [
    "Rat",
    "Cave Rat",
    "Snake",
    "Spider",
    "Bug",
    "Wolf",
    "Bear",
    "Orc",
    "Orc Warrior",
    "Minotaur",
    "Rotworm",
    "Skeleton",
    "Ghoul",
    "Cyclops",
    "Dwarf Guard",
    "Beholder",
    "Dragon",
    "Demon Skeleton",
    "Hero",
    "Giant Spider",
    "Black Knight",
    "Dragon Lord",
    "Demon",
    "Behemoth",
    "Furious Dragon",
    "Enraged Demon",
    "Warlock",
    "Ancient Scarab",
    "Hydra",
    "Serpent Spawn",
    "Necromancer",
    "Vampire",
    "Priestess",
    "Hero",
    "Fury",  # índice 34 — FURY_ROOM_INDEX
    "Furious Black Knight",
    "Enraged Dragon Lord",
    "Demon",
    "Warlock",
    "Furious Behemoth",
]

SPAWN_MARK_BEGIN = "<!-- BEGIN TP_GAUNTLET -->"
SPAWN_MARK_END = "<!-- END TP_GAUNTLET -->"
SPAWN_TIME = 120


@dataclass
class GauntletTile:
    ground: int
    teleport: tuple[int, int, int] | None = None
    # Lista de items hijos OTBM: (item_id, unique_id|None)
    items: list[tuple[int, int | None]] = field(default_factory=list)


def room_origin(origin_x: int, origin_y: int, col: int, row: int) -> tuple[int, int]:
    return origin_x + col * STRIDE, origin_y + row * STRIDE


def room_center(origin_x: int, origin_y: int, col: int, row: int, z: int) -> tuple[int, int, int]:
    ox, oy = room_origin(origin_x, origin_y, col, row)
    return ox + CENTER[0], oy + CENTER[1], z


def room_corner_abs(
    origin_x: int,
    origin_y: int,
    col: int,
    row: int,
    z: int,
    corner_idx: int,
) -> tuple[int, int, int]:
    ox, oy = room_origin(origin_x, origin_y, col, row)
    dx, dy = CORNERS[corner_idx % 4]
    return ox + dx, oy + dy, z


def grid_layout(n_rooms: int) -> tuple[int, int]:
    cols = max(1, int(n_rooms**0.5 + 0.999))
    while cols * ((n_rooms + cols - 1) // cols) < n_rooms:
        cols += 1
    rows = (n_rooms + cols - 1) // cols
    return cols, rows


def grid_footprint(
    origin_x: int,
    origin_y: int,
    cols: int,
    rows: int,
) -> tuple[int, int, int, int]:
    x1 = origin_x + (cols - 1) * STRIDE + ROOM_SIZE - 1
    y1 = origin_y + (rows - 1) * STRIDE + ROOM_SIZE - 1
    return origin_x - 1, origin_y - 1, x1 + 1, y1 + 1


def pick_wrong_room(rng: random.Random, room_i: int, n_rooms: int, forbidden: set[int]) -> int:
    earlier = [j for j in range(room_i) if j not in forbidden]
    others = [j for j in range(n_rooms) if j not in forbidden and j != room_i]
    if earlier and rng.random() < 0.75:
        return rng.choice(earlier)
    if others:
        return rng.choice(others)
    if earlier:
        return rng.choice(earlier)
    pool = [j for j in range(n_rooms) if j != room_i]
    return rng.choice(pool) if pool else room_i


def encode_item_node(item_id: int, *, unique_id: int | None = None, tele: tuple[int, int, int] | None = None) -> bytes:
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


def encode_tile_node(x_off: int, y_off: int, spec: GauntletTile) -> bytes:
    if not (0 <= x_off <= 255 and 0 <= y_off <= 255):
        raise ValueError(f"offset fuera de rango: {x_off},{y_off}")
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


def encode_tile_area(
    base_x: int,
    base_y: int,
    base_z: int,
    rel_tiles: list[tuple[int, int, GauntletTile]],
) -> bytes:
    area_props = struct.pack("<HHB", base_x, base_y, base_z)
    buf = bytearray()
    buf.append(NODE_START)
    buf.append(OTBM_TILE_AREA)
    write_props(buf, area_props)
    for ox, oy, spec in sorted(rel_tiles, key=lambda t: (t[0], t[1])):
        buf.extend(encode_tile_node(ox, oy, spec))
    buf.append(NODE_END)
    return bytes(buf)


def group_tile_areas(tiles: dict[tuple[int, int, int], GauntletTile]) -> list[bytes]:
    from collections import defaultdict

    by_z: dict[int, list[tuple[int, int, GauntletTile]]] = defaultdict(list)
    for (x, y, z), spec in tiles.items():
        by_z[z].append((x, y, spec))

    chunks: list[bytes] = []
    for z, entries in sorted(by_z.items()):
        buckets: dict[tuple[int, int], list[tuple[int, int, GauntletTile]]] = defaultdict(list)
        for x, y, spec in entries:
            bx = (x // 256) * 256
            by = (y // 256) * 256
            buckets[(bx, by)].append((x - bx, y - by, spec))
        for (bx, by), rel in sorted(buckets.items()):
            chunks.append(encode_tile_area(bx, by, z, rel))
    return chunks


def build_monster_roster(n_puzzle: int) -> list[str]:
    monsters = list(DEFAULT_MONSTERS)
    while len(monsters) < n_puzzle:
        monsters.append(DEFAULT_MONSTERS[len(monsters) % len(DEFAULT_MONSTERS)])
    monsters = monsters[:n_puzzle]
    # Forzar Fury en la sala dedicada (si hay suficientes salas).
    if n_puzzle > FURY_ROOM_INDEX:
        monsters[FURY_ROOM_INDEX] = "Fury"
    elif n_puzzle >= 2:
        monsters[n_puzzle - 2] = "Fury"
    return monsters


def build_gauntlet_tiles(
    origin_x: int,
    origin_y: int,
    z: int,
    n_puzzle: int,
    temple_dest: tuple[int, int, int],
    entry_pad: tuple[int, int, int],
    seed: int,
) -> tuple[dict[tuple[int, int, int], GauntletTile], dict]:
    cols, rows = grid_layout(n_puzzle)
    gx0, gy0, gx1, gy1 = grid_footprint(origin_x, origin_y, cols, rows)
    rng = random.Random(seed)

    # Sala final 3×3 al sur del grid (mismo formato que las puzzle).
    # Layout:
    #   .  L  .     L = landing (desde última puzzle)
    #   .  W  .     W = Wrath (centro)
    #   C  .  T     C = cofre soft boots, T = único TP → templo
    fox = origin_x
    foy = gy1 + FINAL_ROOM_GAP
    landing = (fox + CENTER[0], foy + 0, z)
    wrath_pos = (fox + CENTER[0], foy + CENTER[1], z)
    chest_pos = (fox + 0, foy + 2, z)  # SW
    temple_tp_pos = (fox + 2, foy + 2, z)  # SE — único TP

    x0 = min(gx0, fox - 1)
    y0 = gy0
    x1 = max(gx1, fox + ROOM_SIZE)
    y1 = foy + ROOM_SIZE

    tiles: dict[tuple[int, int, int], GauntletTile] = {}
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            tiles[(x, y, z)] = GauntletTile(ground=GROUND_BG)

    rooms: list[dict] = []
    for i in range(n_puzzle):
        col = i % cols
        row = i // cols
        ox, oy = room_origin(origin_x, origin_y, col, row)
        for dy in range(ROOM_SIZE):
            for dx in range(ROOM_SIZE):
                tiles[(ox + dx, oy + dy, z)] = GauntletTile(ground=GROUND_PATH)

        is_last_puzzle = i + 1 == n_puzzle
        correct_corner = rng.randrange(4)
        if is_last_puzzle:
            correct_dest = landing
            correct_label = "finalRoom"
            next_room: int | None = None
        else:
            next_room = i + 1
            next_col = next_room % cols
            next_row = next_room // cols
            correct_dest = room_center(origin_x, origin_y, next_col, next_row, z)
            correct_label = f"room{next_room}"

        teleports: list[dict] = []
        used_wrong: set[int] = set()
        for corner_idx in range(4):
            tp_x, tp_y, _ = room_corner_abs(origin_x, origin_y, col, row, z, corner_idx)
            if corner_idx == correct_corner:
                dest = correct_dest
                kind = "correct"
                dest_label = correct_label
            else:
                forbidden = {i}
                if next_room is not None:
                    forbidden.add(next_room)
                wrong_i = pick_wrong_room(rng, i, n_puzzle, forbidden | used_wrong)
                if wrong_i in used_wrong:
                    wrong_i = pick_wrong_room(rng, i, n_puzzle, forbidden)
                used_wrong.add(wrong_i)
                wcol = wrong_i % cols
                wrow = wrong_i // cols
                dest = room_center(origin_x, origin_y, wcol, wrow, z)
                kind = "wrong"
                dest_label = f"room{wrong_i}"

            tiles[(tp_x, tp_y, z)] = GauntletTile(ground=GROUND_PATH, teleport=dest)
            teleports.append(
                {
                    "corner": CORNER_NAMES[corner_idx],
                    "x": tp_x,
                    "y": tp_y,
                    "z": z,
                    "kind": kind,
                    "destLabel": dest_label,
                    "dest": {"x": dest[0], "y": dest[1], "z": dest[2]},
                }
            )

        cx, cy, _ = room_center(origin_x, origin_y, col, row, z)
        rooms.append(
            {
                "index": i,
                "col": col,
                "row": row,
                "kind": "puzzle",
                "origin": {"x": ox, "y": oy, "z": z},
                "center": {"x": cx, "y": cy, "z": z},
                "correctCorner": CORNER_NAMES[correct_corner],
                "teleports": teleports,
                "isLastPuzzle": is_last_puzzle,
            }
        )

    # Sala final 3×3: Wrath + cofre + un solo TP
    for dy in range(ROOM_SIZE):
        for dx in range(ROOM_SIZE):
            tiles[(fox + dx, foy + dy, z)] = GauntletTile(ground=GROUND_PATH)
    tiles[temple_tp_pos] = GauntletTile(ground=GROUND_PATH, teleport=temple_dest)
    tiles[chest_pos] = GauntletTile(
        ground=GROUND_PATH,
        items=[(QUEST_CHEST_ID, QUEST_PRIZE_UID)],
    )

    # Pad de entrada mundo
    epx, epy, epz = entry_pad
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            tiles[(epx + dx, epy + dy, epz)] = GauntletTile(ground=GROUND_PATH)
    for x in range(epx - 4, epx):
        tiles[(x, epy, epz)] = GauntletTile(ground=GROUND_PATH)
        tiles[(x, epy + 1, epz)] = GauntletTile(ground=GROUND_PATH)

    room0 = room_center(origin_x, origin_y, 0, 0, z)
    tiles[(epx, epy, epz)] = GauntletTile(ground=GROUND_PATH, teleport=room0)

    final_room = {
        "kind": "finalRoom",
        "size": ROOM_SIZE,
        "origin": {"x": fox, "y": foy, "z": z},
        "landing": {"x": landing[0], "y": landing[1], "z": landing[2]},
        "monster": {
            "name": FINAL_BOSS,
            "x": wrath_pos[0],
            "y": wrath_pos[1],
            "z": wrath_pos[2],
        },
        "questChest": {
            "itemId": QUEST_CHEST_ID,
            "uniqueId": QUEST_PRIZE_UID,
            "prizeItemId": QUEST_PRIZE_UID,
            "prizeName": QUEST_PRIZE_NAME,
            "x": chest_pos[0],
            "y": chest_pos[1],
            "z": chest_pos[2],
            "corner": "SW",
        },
        "templeTeleport": {
            "x": temple_tp_pos[0],
            "y": temple_tp_pos[1],
            "z": temple_tp_pos[2],
            "corner": "SE",
            "dest": {"x": temple_dest[0], "y": temple_dest[1], "z": temple_dest[2]},
        },
        "teleportCount": 1,
        "note": "Sala 3×3 final: Wrath en centro, cofre soft boots (SW), un solo TP al templo (SE).",
    }

    meta = {
        "nPuzzleRooms": n_puzzle,
        "seed": seed,
        "grid": {"cols": cols, "rows": rows},
        "furyRoomIndex": FURY_ROOM_INDEX if n_puzzle > FURY_ROOM_INDEX else max(0, n_puzzle - 2),
        "rules": {
            "cornersPerRoom": 4,
            "correctPerRoom": 1,
            "wrongPerRoom": 3,
            "wrongPreferEarlier": True,
            "landOnRoomCenter": True,
            "lastPuzzleGoesToFinalRoom": True,
            "finalRoomSize": ROOM_SIZE,
            "finalRoomSingleTeleport": True,
        },
        "footprint": {"fromX": x0, "toX": x1, "fromY": y0, "toY": y1, "z": z},
        "gridFootprint": {"fromX": gx0, "toX": gx1, "fromY": gy0, "toY": gy1, "z": z},
        "entryPad": {"x": epx, "y": epy, "z": epz},
        "room0": {"x": room0[0], "y": room0[1], "z": room0[2]},
        "templeDest": {"x": temple_dest[0], "y": temple_dest[1], "z": temple_dest[2]},
        "rooms": rooms,
        "finalRoom": final_room,
        "solutionPath": [
            {
                "room": r["index"],
                "correctCorner": r["correctCorner"],
                "goesTo": "finalRoom" if r["isLastPuzzle"] else f"room{r['index'] + 1}",
            }
            for r in rooms
        ]
        + [{"room": "finalRoom", "action": "Wrath + soft boots chest → temple TP (SE)"}],
    }
    return tiles, meta


def entry_pad_bbox(entry_pad: tuple[int, int, int]) -> tuple[int, int, int, int, int]:
    epx, epy, epz = entry_pad
    return epx - 4, epy - 1, epx + 1, epy + 1, epz


def build_spawn_xml(rooms: list[dict], monsters: list[str], final_room: dict) -> str:
    lines = [f"\t{SPAWN_MARK_BEGIN}"]
    for room in rooms:
        name = monsters[room["index"]]
        c = room["center"]
        lines.append(
            f'\t<spawn centerx="{c["x"]}" centery="{c["y"]}" centerz="{c["z"]}" radius="1">'
        )
        lines.append(
            f'\t\t<monster name="{name}" x="0" y="0" z="{c["z"]}" '
            f'spawntime="{SPAWN_TIME}" direction="2" />'
        )
        lines.append("\t</spawn>")
    m = final_room["monster"]
    lines.append(
        f'\t<spawn centerx="{m["x"]}" centery="{m["y"]}" centerz="{m["z"]}" radius="1">'
    )
    lines.append(
        f'\t\t<monster name="{m["name"]}" x="0" y="0" z="{m["z"]}" '
        f'spawntime="{SPAWN_TIME}" direction="2" />'
    )
    lines.append("\t</spawn>")
    lines.append(f"\t{SPAWN_MARK_END}")
    return "\n".join(lines) + "\n"


def upsert_spawn_block(spawn_path: Path, block: str) -> None:
    text = spawn_path.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(SPAWN_MARK_BEGIN) + r".*?" + re.escape(SPAWN_MARK_END) + r"\n?",
        re.DOTALL,
    )
    if pattern.search(text):
        text = pattern.sub(block, text, count=1)
    else:
        if "</spawns>" not in text:
            raise ValueError(f"no se encontró </spawns> en {spawn_path}")
        text = text.replace("</spawns>", block + "</spawns>", 1)
    spawn_path.write_text(text, encoding="utf-8")


def validate_monsters(monsters: list[str], monsters_xml: Path) -> None:
    names = set(re.findall(r'name="([^"]+)"', monsters_xml.read_text(encoding="utf-8")))
    missing = [m for m in monsters if m not in names]
    if missing:
        raise ValueError(f"monstruos no registrados en monsters.xml: {missing}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin-x", type=int, default=450)
    parser.add_argument("--origin-y", type=int, default=40)
    parser.add_argument("--z", type=int, default=7)
    parser.add_argument(
        "--rooms",
        type=int,
        default=DEFAULT_PUZZLE_ROOMS,
        help="salas puzzle 3×3 (además de la sala final Wrath/cofre)",
    )
    parser.add_argument("--seed", type=int, default=76)
    parser.add_argument("--entry-x", type=int, default=436)
    parser.add_argument("--entry-y", type=int, default=102)
    parser.add_argument("--entry-z", type=int, default=7)
    parser.add_argument("--temple-x", type=int, default=TEMPLE_DEST[0])
    parser.add_argument("--temple-y", type=int, default=TEMPLE_DEST[1])
    parser.add_argument("--temple-z", type=int, default=TEMPLE_DEST[2])
    parser.add_argument("--map", type=Path)
    parser.add_argument("--spawn", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.rooms < 2:
        print("ERROR: hace falta al menos 2 salas puzzle", file=sys.stderr)
        return 1

    project = Path(__file__).resolve().parents[1]
    otbm_path = args.map or (project / "server/YurOTS/ots/data/world/test.otbm")
    spawn_path = args.spawn or (project / "server/YurOTS/ots/data/world/test-spawn.xml")
    manifest_path = args.manifest or (
        project / "server/YurOTS/ots/data/world/generated-tp-gauntlet.json"
    )
    monsters_xml = project / "server/YurOTS/ots/data/monster/monsters.xml"
    temple_dest = (args.temple_x, args.temple_y, args.temple_z)
    entry_pad = (args.entry_x, args.entry_y, args.entry_z)
    monsters = build_monster_roster(args.rooms)
    validate_monsters(monsters + [FINAL_BOSS], monsters_xml)

    new_tiles, meta = build_gauntlet_tiles(
        args.origin_x,
        args.origin_y,
        args.z,
        args.rooms,
        temple_dest,
        entry_pad,
        args.seed,
    )
    for i, room in enumerate(meta["rooms"]):
        room["monster"] = monsters[i]

    fp = meta["footprint"]
    fr = meta["finalRoom"]
    tele_count = sum(1 for s in new_tiles.values() if s.teleport is not None)
    path_count = sum(1 for s in new_tiles.values() if s.ground == GROUND_PATH)
    bg_count = sum(1 for s in new_tiles.values() if s.ground == GROUND_BG)
    chest_count = sum(1 for s in new_tiles.values() if s.items)

    print(
        f"Gauntlet: {args.rooms} salas puzzle 3×3 + sala final 3×3 (Wrath), "
        f"grid {meta['grid']['cols']}×{meta['grid']['rows']}, semilla {args.seed}"
    )
    print(
        "Reglas: 4 TPs/sala puzzle; última → sala final; "
        "final: 1 TP templo + Wrath + cofre soft boots"
    )
    print(f"Fury en sala puzzle #{meta['furyRoomIndex']}")
    print(f"Origen NW: ({args.origin_x}, {args.origin_y}, {args.z})")
    print(
        f"Tiles: camino {path_count}, fondo {bg_count}, teleports {tele_count}, "
        f"cofres {chest_count}"
    )
    print(
        f"Entrada mundo/barco: sala 0 ({meta['room0']['x']}, {meta['room0']['y']}, "
        f"{meta['room0']['z']})"
    )
    print(
        f"Sala final: origen ({fr['origin']['x']},{fr['origin']['y']}) | "
        f"boss {fr['monster']['name']} @ ({fr['monster']['x']},{fr['monster']['y']}) | "
        f"cofre uid={fr['questChest']['uniqueId']} ({fr['questChest']['prizeName']}) "
        f"@ SW | TP templo @ SE ({fr['templeTeleport']['x']},{fr['templeTeleport']['y']})"
    )
    print(f"Footprint: X {fp['fromX']}-{fp['toX']}, Y {fp['fromY']}-{fp['toY']}, z {fp['z']}")
    print("Solución puzzle (GM):")
    for room in meta["rooms"]:
        wrong = [
            t["corner"] + "→" + t["destLabel"]
            for t in room["teleports"]
            if t["kind"] == "wrong"
        ]
        goes = "sala final" if room["isLastPuzzle"] else f"room{room['index'] + 1}"
        print(
            f"  #{room['index']:02d} {room['monster']:<22} "
            f"OK={room['correctCorner']:<2} → {goes}  "
            f"falsos: {', '.join(wrong)}"
        )

    summary = {
        "name": "generated-tp-gauntlet",
        "puzzleRooms": args.rooms,
        "roomSize": ROOM_SIZE,
        "groundPathId": GROUND_PATH,
        "groundBackgroundId": GROUND_BG,
        "teleportItemId": TELEPORT_ITEM,
        "questChestItemId": QUEST_CHEST_ID,
        "questPrizeUniqueId": QUEST_PRIZE_UID,
        "monsters": monsters,
        "finalBoss": FINAL_BOSS,
        "mapFile": str(otbm_path.relative_to(project)),
        "spawnFile": str(spawn_path.relative_to(project)),
        **meta,
        "tileCounts": {
            "path": path_count,
            "background": bg_count,
            "teleports": tele_count,
            "chests": chest_count,
            "total": len(new_tiles),
        },
    }

    if args.dry_run:
        print("\n(dry-run — no se modificó el mapa ni spawns)")
        return 0

    if not otbm_path.is_file():
        print(f"ERROR: no existe {otbm_path}", file=sys.stderr)
        return 1

    raw = otbm_path.read_bytes()
    # Limpiar footprint amplio (incluye pasillo viejo hasta y=100).
    clear_y1 = max(fp["toY"], 100)
    clear_x1 = max(fp["toX"], 490)
    if args.replace:
        ep = entry_pad_bbox(entry_pad)
        body = raw[4:]
        body = _maze.filter_tiles_in_bbox(
            body, fp["fromX"], fp["fromY"], clear_x1, clear_y1, args.z
        )
        body = _maze.filter_tiles_in_bbox(body, ep[0], ep[1], ep[2], ep[3], ep[4])
        insert_at = _maze.find_map_data_insert(body)
        patch = b"".join(group_tile_areas(new_tiles))
        patched = raw[:4] + body[:insert_at] + patch + body[insert_at:]
    else:
        existing = _maze.load_existing_tiles(raw[4:])
        conflicts = [pos for pos in new_tiles if pos in existing]
        if conflicts:
            print(
                f"ERROR: {len(conflicts)} tile(s) ya existen (ej. {conflicts[:3]}). "
                "Usá --replace.",
                file=sys.stderr,
            )
            return 1
        body = raw[4:]
        insert_at = _maze.find_map_data_insert(body)
        patch = b"".join(group_tile_areas(new_tiles))
        patched = raw[:4] + body[:insert_at] + patch + body[insert_at:]

    backup = otbm_path.with_suffix(".otbm.bak-gauntlet")
    if not backup.exists():
        backup.write_bytes(raw)
        print(f"\nBackup: {backup}")

    otbm_path.write_bytes(patched)
    upsert_spawn_block(
        spawn_path, build_spawn_xml(meta["rooms"], monsters, meta["finalRoom"])
    )
    manifest_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"\nOK — mapa: {otbm_path}")
    print(f"OK — spawns: {spawn_path}")
    print(f"OK — manifiesto: {manifest_path}")
    print("Reiniciá: docker compose -f docker-compose.prod.yml restart yurots")
    print(
        f"Barco: hi / gauntlet / yes  |  GM sala final: "
        f"/pos {fr['landing']['x']} {fr['landing']['y']} {fr['landing']['z']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
