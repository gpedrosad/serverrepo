#!/usr/bin/env python3
"""Floor Hunt — campus de salas separadas en XY (sin apilar z).

Antes: 16 pisos en la misma huella XY (z0–z15) → se veían teleports del piso de abajo.
Ahora: 16 salas en z7, separadas en el mapa (alas oeste / centro / este),
conectadas solo por teleports. Fondo opaco (no void 100) por ala.

Portal templo 162,54,7 → sala 0. Avance up/down/express + home.

Uso:
  python3 scripts/generate-floor-hunt.py --dry-run
  python3 scripts/generate-floor-hunt.py --replace
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

_maze_path = Path(__file__).resolve().parent / "generate-maze.py"
_spec = importlib.util.spec_from_file_location("generate_maze", _maze_path)
_maze = importlib.util.module_from_spec(_spec)
sys.modules["generate_maze"] = _maze
assert _spec.loader is not None
_spec.loader.exec_module(_maze)

TELEPORT_ITEM = _maze.TELEPORT_ITEM
TileSpec = _maze.TileSpec
group_tile_areas = _maze.group_tile_areas
maze_footprint = _maze.maze_footprint
cell_block_tiles = _maze.cell_block_tiles
generate_maze_cells = _maze.generate_maze_cells
add_cell_block = _maze.add_cell_block
add_connection = _maze.add_connection
north_exit_tiles = _maze.north_exit_tiles
validate_walkable_path = _maze.validate_walkable_path

# Salas más compactas; gap entre footprints ~12–17 sqm.
DEFAULT_CELLS_X = 10
DEFAULT_CELLS_Y = 12
DEFAULT_SEED = 421
CAMPUS_Z = 7
NUM_FLOORS = 16

# Torre vieja apilada (limpiar siempre al regenerar).
LEGACY_STACKED_FOOTPRINT = (200, 339, 245, 400)  # x0,y0,x1,y1
LEGACY_STACKED_Z = tuple(range(0, 16))

# Portal distinto al hunt maze (160,54,7).
HUB_PORTAL = (162, 54, 7)
HUB_LANDING = (163, 54, 7)
HUB_GROUND = 406

ALICE_FOOTPRINT = (380, 18, 433, 103, 7)
HUNT_MAZE_FOOTPRINT = (280, 243, 349, 400, 7)
WAVE_ARENA_FOOTPRINT = (174, 386, 180, 392, 7)

SPAWN_MARK_BEGIN = "<!-- BEGIN FLOOR_HUNT -->"
SPAWN_MARK_END = "<!-- END FLOOR_HUNT -->"
SPAWN_TIME = 65

# (origin_x, origin_y_south) — 6 oeste + 2 centro + 8 este, todo z7.
FLOOR_ORIGINS: tuple[tuple[int, int], ...] = (
    (40, 400),
    (95, 400),
    (40, 350),
    (95, 350),
    (40, 300),
    (95, 300),
    (200, 400),
    (200, 350),
    (360, 400),
    (415, 400),
    (360, 355),
    (415, 355),
    (360, 310),
    (415, 310),
    (360, 265),
    (415, 265),
)

# Temas opacos: camino / fondo (sin void 100 — evita ver a través).
FLOOR_THEMES: tuple[tuple[int, int], ...] = (
    (406, 405),  # marble white / black
    (405, 919),  # black marble / dark stone
    (919, 412),  # dark stone / stone
    (231, 351),  # dirt / sand
    (101, 103),  # grass
    (407, 405),  # yellow / black marble
    (412, 919),  # stone / dark
    (351, 231),  # sand / dirt
    (406, 919),
    (405, 412),
    (919, 405),
    (231, 103),
    (101, 351),
    (407, 919),
    (412, 405),
    (405, 231),
)

FLOOR_LABELS: tuple[str, ...] = (
    "Minotaur Courts",
    "Guard Barracks",
    "Cyclops Yard",
    "Dwarf Bastion",
    "Beholder Vault",
    "Bone Crypt",
    "Spider Catacombs",
    "Necro Cloister",
    "Hero Hall",
    "Dragon Roost",
    "Scarabs & Hex",
    "Lord Lair",
    "Hydra Cistern",
    "Lich Spire",
    "Demon Gate",
    "Behemoth Throne",
)

FLOOR_ROSTERS: tuple[tuple[str, ...], ...] = (
    ("Minotaur", "Minotaur Archer", "Minotaur", "Minotaur Guard"),
    ("Minotaur Guard", "Minotaur Archer", "Minotaur Mage", "Minotaur"),
    ("Cyclops", "Minotaur Guard", "Dwarf Soldier", "Cyclops"),
    ("Dwarf Guard", "Dwarf Geomancer", "Cyclops", "Dwarf Guard"),
    ("Beholder", "Dwarf Guard", "Demon Skeleton", "Beholder"),
    ("Demon Skeleton", "Ghoul", "Ghost", "Beholder"),
    ("Giant Spider", "Vampire", "Demon Skeleton", "Giant Spider"),
    ("Necromancer", "Priestess", "Vampire", "Necromancer"),
    ("Hero", "Black Knight", "Necromancer", "Hero"),
    ("Dragon", "Hero", "Black Knight", "Dragon"),
    ("Ancient Scarab", "Warlock", "Dragon", "Ancient Scarab"),
    ("Dragon Lord", "Warlock", "Dragon", "Dragon Lord"),
    ("Hydra", "Green Djinn", "Dragon Lord", "Hydra"),
    ("Lich", "Blue Djinn", "Hydra", "Lich"),
    ("Demon", "Serpent Spawn", "Lich", "Demon"),
    ("Behemoth", "Fury", "Demon", "Behemoth"),
)


def project_root() -> Path:
    return next(
        p
        for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
        if (p / "AGENTS.md").is_file() or (p / ".git").is_dir()
    )


def overlaps(fp: dict, box: tuple[int, int, int, int, int]) -> bool:
    bx0, by0, bx1, by1, bz = box
    if fp["z"] != bz:
        return False
    return not (
        fp["toX"] < bx0
        or fp["fromX"] > bx1
        or fp["toY"] < by0
        or fp["fromY"] > by1
    )


def build_floor_maze(
    origin_x: int,
    origin_y_south: int,
    z: int,
    cells_x: int,
    cells_y: int,
    seed: int,
    ground_path: int,
    ground_bg: int,
) -> tuple[dict[tuple[int, int, int], TileSpec], set[tuple[int, int]], set, dict]:
    visited, edges = generate_maze_cells(cells_x, cells_y, seed)
    x0, y0, x1, y1 = maze_footprint(origin_x, origin_y_south, cells_x, cells_y)
    tiles: dict[tuple[int, int, int], TileSpec] = {}
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            tiles[(x, y, z)] = TileSpec(ground=ground_bg)
    for cell in visited:
        add_cell_block(tiles, origin_x, origin_y_south, z, cells_y, cell[0], cell[1])
    for edge in edges:
        add_connection(tiles, origin_x, origin_y_south, z, cells_y, edge[0], edge[1])

    if ground_bg == _maze.GROUND_PATH:
        raise ValueError("ground_bg no puede ser 406 (se confunde con el camino)")

    entry_cell = (0, cells_y - 1)
    entry_block = cell_block_tiles(origin_x, origin_y_south, cells_y, *entry_cell)
    entry_sorted = sorted(entry_block, key=lambda p: (p[1], p[0]))
    nw, ne, sw, se = entry_sorted
    exit_tiles = north_exit_tiles(visited, origin_x, origin_y_south, z, cells_x, cells_y)

    # Validar con 406; después aplicar tema del piso.
    conn = validate_walkable_path(
        tiles, z, (nw[0], nw[1]), list(exit_tiles)
    )
    for pos, spec in list(tiles.items()):
        if pos[2] == z and spec.ground == _maze.GROUND_PATH:
            tiles[pos] = TileSpec(ground=ground_path, teleport=spec.teleport)

    meta = {
        "landing": (nw[0], nw[1], z),
        "tpHome": (se[0], se[1], z),
        "tpUp": (sw[0], sw[1], z),
        "tpSpare": (ne[0], ne[1], z),
        "north": exit_tiles[0],
        "northAll": exit_tiles,
        "entryCell": entry_cell,
        "origin": {"x": origin_x, "ySouth": origin_y_south},
        "theme": {"path": ground_path, "background": ground_bg},
        "footprint": {"fromX": x0, "toX": x1, "fromY": y0, "toY": y1, "z": z},
        "connectivity": conn,
    }
    return tiles, visited, edges, meta


def cell_bfs_distance(
    visited: set[tuple[int, int]],
    edges: set[tuple[tuple[int, int], tuple[int, int]]],
    start: tuple[int, int],
) -> dict[tuple[int, int], int]:
    adj: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    dist = {start: 0}
    q: deque[tuple[int, int]] = deque([start])
    while q:
        cur = q.popleft()
        for nxt in adj[cur]:
            if nxt not in visited or nxt in dist:
                continue
            dist[nxt] = dist[cur] + 1
            q.append(nxt)
    for cell in visited:
        dist.setdefault(cell, 0)
    return dist


def plan_floor_spawns(
    origin_x: int,
    origin_y_south: int,
    z: int,
    cells_y: int,
    visited: set[tuple[int, int]],
    edges: set[tuple[tuple[int, int], tuple[int, int]]],
    entry_cell: tuple[int, int],
    skip: set[tuple[int, int, int]],
    roster: tuple[str, ...],
    floor_index: int,
    *,
    milestone: bool = False,
) -> list[dict]:
    dist = cell_bfs_distance(visited, edges, entry_cell)
    ordered = sorted(visited, key=lambda c: (dist[c], c[1], c[0]))
    spawns: list[dict] = []
    for cell in ordered:
        block = cell_block_tiles(origin_x, origin_y_south, cells_y, cell[0], cell[1])
        chosen = None
        for xy in (block[3], block[0], block[1], block[2]):
            pos = (xy[0], xy[1], z)
            if pos not in skip:
                chosen = pos
                break
        if chosen is None:
            continue
        name = roster[(cell[0] * 3 + cell[1] * 5 + floor_index) % len(roster)]
        pack = 1
        if milestone and (cell[0] + cell[1]) % 3 == 0:
            pack = 2
        spawns.append(
            {
                "name": name,
                "x": chosen[0],
                "y": chosen[1],
                "z": z,
                "floor": floor_index,
                "pack": pack,
            }
        )
    return spawns


def build_all_floors(
    cells_x: int,
    cells_y: int,
    seed: int,
    hub_portal: tuple[int, int, int],
    hub_landing: tuple[int, int, int],
) -> tuple[dict[tuple[int, int, int], TileSpec], dict, list[dict]]:
    if len(FLOOR_ORIGINS) != NUM_FLOORS:
        raise ValueError("FLOOR_ORIGINS debe tener 16 entradas")

    all_tiles: dict[tuple[int, int, int], TileSpec] = {}
    floor_meta: dict[int, dict] = {}
    all_spawns: list[dict] = []
    floor_graphs: dict[int, tuple] = {}
    z = CAMPUS_Z

    for i in range(NUM_FLOORS):
        ox, oy = FLOOR_ORIGINS[i]
        path_g, bg_g = FLOOR_THEMES[i]
        tiles, visited, edges, meta = build_floor_maze(
            ox, oy, z, cells_x, cells_y, seed + i * 17, path_g, bg_g
        )
        all_tiles.update(tiles)
        floor_meta[i] = meta
        floor_graphs[i] = (visited, edges, meta["entryCell"], ox, oy)

    m0 = floor_meta[0]
    landing0 = m0["landing"]
    all_tiles[hub_portal] = TileSpec(ground=HUB_GROUND, teleport=landing0)

    for i in range(NUM_FLOORS):
        meta = floor_meta[i]
        landing = meta["landing"]
        tp_home = meta["tpHome"]
        tp_up = meta["tpUp"]
        tp_spare = meta["tpSpare"]
        path_g = meta["theme"]["path"]

        all_tiles[landing] = TileSpec(ground=path_g)
        all_tiles[tp_home] = TileSpec(ground=path_g, teleport=hub_landing)

        if i == 0:
            all_tiles[tp_up] = TileSpec(ground=path_g, teleport=hub_landing)
            up_dest = "temple"
        else:
            dest_up = floor_meta[i - 1]["landing"]
            all_tiles[tp_up] = TileSpec(ground=path_g, teleport=dest_up)
            up_dest = f"floor{i - 1}"

        if i < NUM_FLOORS - 1:
            dest_down = floor_meta[i + 1]["landing"]
            down_dest = f"floor{i + 1}"
        else:
            dest_down = hub_landing
            down_dest = "temple"
        for pos in meta["northAll"]:
            all_tiles[pos] = TileSpec(ground=path_g, teleport=dest_down)

        express_dest = None
        if i % 2 == 0 and i < NUM_FLOORS - 2:
            dest_ex = floor_meta[i + 2]["landing"]
            all_tiles[tp_spare] = TileSpec(ground=path_g, teleport=dest_ex)
            express_dest = f"floor{i + 2}"
        else:
            all_tiles[tp_spare] = TileSpec(ground=path_g)

        label = FLOOR_LABELS[i]
        meta["index"] = i
        meta["label"] = label
        meta["milestone"] = i > 0 and i % 4 == 0
        meta["teleports"] = {
            "home": {
                "x": tp_home[0],
                "y": tp_home[1],
                "z": z,
                "dest": "temple",
            },
            "up": {"x": tp_up[0], "y": tp_up[1], "z": z, "dest": up_dest},
            "down": {
                "x": meta["north"][0],
                "y": meta["north"][1],
                "z": z,
                "dest": down_dest,
            },
            "express": (
                {
                    "x": tp_spare[0],
                    "y": tp_spare[1],
                    "z": z,
                    "dest": express_dest,
                }
                if express_dest
                else None
            ),
        }

    skip = {p for p, s in all_tiles.items() if s.teleport is not None}
    skip.add(hub_portal)

    for i in range(NUM_FLOORS):
        visited, edges, entry_cell, ox, oy = floor_graphs[i]
        roster = FLOOR_ROSTERS[i]
        all_spawns.extend(
            plan_floor_spawns(
                ox,
                oy,
                z,
                cells_y,
                visited,
                edges,
                entry_cell,
                skip,
                roster,
                i,
                milestone=bool(floor_meta[i].get("milestone")),
            )
        )

    fps = [floor_meta[i]["footprint"] for i in range(NUM_FLOORS)]
    summary_meta = {
        "layout": "campus-xy-separated",
        "campusZ": CAMPUS_Z,
        "floors": [
            {
                "index": i,
                "z": CAMPUS_Z,
                "label": floor_meta[i].get("label", f"floor{i}"),
                "milestone": floor_meta[i].get("milestone", False),
                "origin": floor_meta[i]["origin"],
                "theme": floor_meta[i]["theme"],
                "landing": {
                    "x": floor_meta[i]["landing"][0],
                    "y": floor_meta[i]["landing"][1],
                    "z": CAMPUS_Z,
                },
                "teleports": floor_meta[i]["teleports"],
                "roster": list(FLOOR_ROSTERS[i]),
                "footprint": floor_meta[i]["footprint"],
                "connectivity": floor_meta[i]["connectivity"],
            }
            for i in range(NUM_FLOORS)
        ],
        "hubPortal": {"x": hub_portal[0], "y": hub_portal[1], "z": hub_portal[2]},
        "hubLanding": {"x": hub_landing[0], "y": hub_landing[1], "z": hub_landing[2]},
        "entryLanding": {
            "x": landing0[0],
            "y": landing0[1],
            "z": landing0[2],
        },
        "entryReturn": {
            "x": m0["tpHome"][0],
            "y": m0["tpHome"][1],
            "z": m0["tpHome"][2],
        },
        "footprint": {
            "fromX": min(f["fromX"] for f in fps),
            "toX": max(f["toX"] for f in fps),
            "fromY": min(f["fromY"] for f in fps),
            "toY": max(f["toY"] for f in fps),
            "z": CAMPUS_Z,
        },
        "clearBoxes": [
            {
                "fromX": f["fromX"],
                "toX": f["toX"],
                "fromY": f["fromY"],
                "toY": f["toY"],
                "z": CAMPUS_Z,
            }
            for f in fps
        ],
    }
    return all_tiles, summary_meta, all_spawns


def build_spawn_xml(spawns: list[dict]) -> str:
    lines = [f"\t{SPAWN_MARK_BEGIN}"]
    for s in spawns:
        lines.append(
            f'\t<spawn centerx="{s["x"]}" centery="{s["y"]}" centerz="{s["z"]}" radius="1">'
        )
        pack = int(s.get("pack", 1))
        offsets = [(0, 0)] if pack == 1 else [(0, 0), (0, -1)]
        for ox, oy in offsets:
            lines.append(
                f'\t\t<monster name="{s["name"]}" x="{ox}" y="{oy}" z="{s["z"]}" '
                f'spawntime="{SPAWN_TIME}" direction="2" />'
            )
        lines.append("\t</spawn>")
    lines.append(f"\t{SPAWN_MARK_END}")
    return "\n".join(lines) + "\n"


def upsert_spawns(spawn_path: Path, block: str) -> None:
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


def validate_monsters(names: list[str], monsters_xml: Path) -> None:
    registered = set(re.findall(r'name="([^"]+)"', monsters_xml.read_text(encoding="utf-8")))
    missing = sorted({n for n in names if n not in registered})
    if missing:
        raise ValueError(f"monstruos no registrados: {missing}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells-x", type=int, default=DEFAULT_CELLS_X)
    parser.add_argument("--cells-y", type=int, default=DEFAULT_CELLS_Y)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--hub-x", type=int, default=HUB_PORTAL[0])
    parser.add_argument("--hub-y", type=int, default=HUB_PORTAL[1])
    parser.add_argument("--hub-z", type=int, default=HUB_PORTAL[2])
    parser.add_argument("--hub-land-x", type=int, default=HUB_LANDING[0])
    parser.add_argument("--hub-land-y", type=int, default=HUB_LANDING[1])
    parser.add_argument("--hub-land-z", type=int, default=HUB_LANDING[2])
    parser.add_argument("--map", type=Path)
    parser.add_argument("--spawn", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    project = project_root()
    otbm_path = args.map or (project / "server/YurOTS/ots/data/world/test.otbm")
    spawn_path = args.spawn or (project / "server/YurOTS/ots/data/world/test-spawn.xml")
    manifest_path = args.manifest or (
        project / "server/YurOTS/ots/data/world/generated-floor-hunt.json"
    )
    monsters_xml = project / "server/YurOTS/ots/data/monster/monsters.xml"
    hub_portal = (args.hub_x, args.hub_y, args.hub_z)
    hub_landing = (args.hub_land_x, args.hub_land_y, args.hub_land_z)

    if not otbm_path.is_file():
        print(f"ERROR: no existe {otbm_path}", file=sys.stderr)
        return 1

    new_tiles, meta, spawns = build_all_floors(
        args.cells_x,
        args.cells_y,
        args.seed,
        hub_portal,
        hub_landing,
    )

    for fl in meta["floors"]:
        fp = fl["footprint"]
        fp7 = {
            "fromX": fp["fromX"],
            "toX": fp["toX"],
            "fromY": fp["fromY"],
            "toY": fp["toY"],
            "z": CAMPUS_Z,
        }
        if overlaps(fp7, ALICE_FOOTPRINT):
            print(f"ERROR: sala {fl['index']} solapa Alice Maze", file=sys.stderr)
            return 1
        if overlaps(fp7, HUNT_MAZE_FOOTPRINT):
            print(f"ERROR: sala {fl['index']} solapa hunt maze", file=sys.stderr)
            return 1
        if overlaps(fp7, WAVE_ARENA_FOOTPRINT):
            print(f"ERROR: sala {fl['index']} solapa wave arena", file=sys.stderr)
            return 1

    try:
        validate_monsters([s["name"] for s in spawns], monsters_xml)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    path_ids = {t[0] for t in FLOOR_THEMES}
    bg_ids = {t[1] for t in FLOOR_THEMES}
    path_count = sum(1 for s in new_tiles.values() if s.ground in path_ids)
    bg_count = sum(1 for s in new_tiles.values() if s.ground in bg_ids)
    tele_count = sum(1 for s in new_tiles.values() if s.teleport is not None)
    counts = Counter(s["name"] for s in spawns)
    by_floor = Counter(s["floor"] for s in spawns)

    print(
        f"Floor hunt — {NUM_FLOORS} salas en campus XY (z{CAMPUS_Z}), "
        "sin apilar pisos"
    )
    print(f"Celdas {args.cells_x}x{args.cells_y}/sala, seed {args.seed}")
    print(
        f"Portal templo: ({hub_portal[0]},{hub_portal[1]},{hub_portal[2]}) → "
        f"({meta['entryLanding']['x']},{meta['entryLanding']['y']},{meta['entryLanding']['z']})"
    )
    fp = meta["footprint"]
    print(
        f"Envelope: X {fp['fromX']}-{fp['toX']}, Y {fp['fromY']}-{fp['toY']}, z{fp['z']}"
    )
    for fl in meta["floors"]:
        tps = fl["teleports"]
        ex = tps.get("express")
        ex_s = (
            f" | express→{ex['dest']} @ ({ex['x']},{ex['y']})"
            if ex
            else ""
        )
        mark = " ★" if fl.get("milestone") else ""
        th = fl["theme"]
        print(
            f"  f{fl['index']:02d}{mark} {fl.get('label', '')}: "
            f"X{fl['footprint']['fromX']}-{fl['footprint']['toX']} "
            f"Y{fl['footprint']['fromY']}-{fl['footprint']['toY']} "
            f"path={th['path']} bg={th['background']} | "
            f"down→{tps['down']['dest']} up→{tps['up']['dest']}"
            f"{ex_s} | spawns {by_floor[fl['index']]}"
        )
    print(f"Tiles: path~{path_count}, bg~{bg_count}, teleports {tele_count}")
    print(f"Spawns total: {len(spawns)}")
    for name, n in counts.most_common():
        print(f"  {name:<22} {n:3}")

    summary = {
        "name": "generated-floor-hunt",
        "separateFromAlice": True,
        "separateFromHuntMaze": True,
        "layout": "campus-xy-separated",
        "cells": {"x": args.cells_x, "y": args.cells_y},
        "seed": args.seed,
        "campusZ": CAMPUS_Z,
        "teleportItemId": TELEPORT_ITEM,
        "spawnTime": SPAWN_TIME,
        "spawnCount": len(spawns),
        "spawnCounts": dict(counts),
        "spawnsByFloor": dict(by_floor),
        "mapFile": str(otbm_path.relative_to(project)),
        "spawnFile": str(spawn_path.relative_to(project)),
        "tileCounts": {
            "pathApprox": path_count,
            "backgroundApprox": bg_count,
            "teleports": tele_count,
            "total": len(new_tiles),
        },
        **meta,
    }

    if args.dry_run:
        print("\n(dry-run — no se modificó el mapa ni spawns)")
        return 0
    if not args.replace:
        print("ERROR: usá --replace", file=sys.stderr)
        return 1

    raw = otbm_path.read_bytes()
    body = raw[4:]

    # Limpiar torre apilada vieja (todas las z).
    lx0, ly0, lx1, ly1 = LEGACY_STACKED_FOOTPRINT
    for z in LEGACY_STACKED_Z:
        body = _maze.filter_tiles_in_bbox(body, lx0, ly0, lx1, ly1, z)

    # Limpiar cada sala del campus + portal hub.
    for box in meta["clearBoxes"]:
        body = _maze.filter_tiles_in_bbox(
            body, box["fromX"], box["fromY"], box["toX"], box["toY"], box["z"]
        )
    body = _maze.filter_tiles_in_bbox(
        body,
        hub_portal[0],
        hub_portal[1],
        hub_portal[0],
        hub_portal[1],
        hub_portal[2],
    )

    insert_at = _maze.find_map_data_insert(body)
    patch = b"".join(group_tile_areas(new_tiles))
    patched = raw[:4] + body[:insert_at] + patch + body[insert_at:]

    backup = otbm_path.with_suffix(".otbm.bak-floor-hunt")
    if not backup.exists():
        backup.write_bytes(raw)
        print(f"\nBackup: {backup}")

    otbm_path.write_bytes(patched)
    upsert_spawns(spawn_path, build_spawn_xml(spawns))
    manifest_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"\nOK — mapa: {otbm_path}")
    print(f"OK — spawns: {spawn_path}")
    print(f"OK — manifiesto: {manifest_path}")
    print("Reiniciá: docker compose -f docker-compose.prod.yml restart yurots")
    print(
        f"Portal campus: /pos {hub_portal[0]} {hub_portal[1]} {hub_portal[2]}  |  "
        f"Hunt plano: /pos 160 54 7  |  Alice: barco maze"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
