#!/usr/bin/env python3
"""Laberinto de caza SEPARADO del Alice Maze (y del gauntlet).

- No toca el footprint Alice (380–433, 18–103).
- Misma geometría 2 sqm (camino 406 / fondo 100) que generate-maze.py.
- Portal en templo viejo 160,54,7 → landing del hunt maze.
- Apenas llegás: 1 tile con teleport de vuelta (sin loop).
- Spawns progresivos en bloque <!-- BEGIN HUNT_MAZE -->.

Uso:
  python3 scripts/generate-hunt-maze.py --dry-run
  python3 scripts/generate-hunt-maze.py --replace
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

GROUND_PATH = _maze.GROUND_PATH
GROUND_BG = _maze.GROUND_BG
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

# Zona SE vacía — lejos de Alice (380–433,18–103) y gauntlet (~450+).
DEFAULT_ORIGIN_X = 280
DEFAULT_ORIGIN_Y_SOUTH = 400
DEFAULT_CELLS_X = 18
DEFAULT_CELLS_Y = 40
DEFAULT_SEED = 230
DEFAULT_Z = 7

HUB_PORTAL = (160, 54, 7)
HUB_LANDING = (161, 54, 7)
HUB_GROUND = 415

# Alice Maze footprint — NUNCA escribir aquí.
ALICE_FOOTPRINT = (380, 18, 433, 103, 7)

SPAWN_MARK_BEGIN = "<!-- BEGIN HUNT_MAZE -->"
SPAWN_MARK_END = "<!-- END HUNT_MAZE -->"
LEGACY_ALICE_HUNT_BEGIN = "<!-- BEGIN ALICE_HUNT -->"
LEGACY_ALICE_HUNT_END = "<!-- END ALICE_HUNT -->"
SPAWN_TIME = 70

# Progresión mid→hard: entra en Minotaur, sube hasta demonios al fondo.
DIFFICULTY_BANDS: list[tuple[str, ...]] = [
    ("Minotaur", "Minotaur Archer"),
    ("Minotaur", "Minotaur Guard"),
    ("Minotaur Guard", "Minotaur Archer", "Minotaur"),
    ("Minotaur Mage", "Minotaur Guard"),
    ("Cyclops", "Minotaur Guard", "Dwarf Soldier"),
    ("Dwarf Guard", "Cyclops", "Dwarf Geomancer"),
    ("Beholder", "Dwarf Guard", "Demon Skeleton"),
    ("Demon Skeleton", "Ghoul", "Beholder"),
    ("Giant Spider", "Vampire", "Demon Skeleton"),
    ("Necromancer", "Priestess", "Vampire"),
    ("Hero", "Black Knight", "Necromancer"),
    ("Dragon", "Hero", "Ancient Scarab"),
    ("Dragon Lord", "Warlock", "Dragon"),
    ("Hydra", "Lich", "Green Djinn"),
    ("Demon", "Behemoth", "Serpent Spawn", "Fury"),
]


def project_root() -> Path:
    return next(
        p
        for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
        if (p / "AGENTS.md").is_file() or (p / ".git").is_dir()
    )


def assert_no_alice_overlap(fp: dict) -> None:
    ax0, ay0, ax1, ay1, az = ALICE_FOOTPRINT
    if fp["z"] != az:
        return
    overlap = not (
        fp["toX"] < ax0
        or fp["fromX"] > ax1
        or fp["toY"] < ay0
        or fp["fromY"] > ay1
    )
    if overlap:
        raise ValueError(
            f"Hunt maze footprint X{fp['fromX']}-{fp['toX']} Y{fp['fromY']}-{fp['toY']} "
            f"solapa Alice Maze X{ax0}-{ax1} Y{ay0}-{ay1}. Elegí otro origin."
        )


def build_hunt_tiles(
    origin_x: int,
    origin_y_south: int,
    z: int,
    cells_x: int,
    cells_y: int,
    seed: int,
    hub_portal: tuple[int, int, int],
    hub_landing: tuple[int, int, int],
) -> tuple[dict[tuple[int, int, int], TileSpec], dict]:
    visited, edges = generate_maze_cells(cells_x, cells_y, seed)
    x0, y0, x1, y1 = maze_footprint(origin_x, origin_y_south, cells_x, cells_y)

    tiles: dict[tuple[int, int, int], TileSpec] = {}
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            tiles[(x, y, z)] = TileSpec(ground=GROUND_BG)

    for cell in visited:
        add_cell_block(tiles, origin_x, origin_y_south, z, cells_y, cell[0], cell[1])
    for edge in edges:
        add_connection(tiles, origin_x, origin_y_south, z, cells_y, edge[0], edge[1])

    entry_cell = (0, cells_y - 1)
    entry_block = cell_block_tiles(origin_x, origin_y_south, cells_y, *entry_cell)
    entry_sorted = sorted(entry_block, key=lambda p: (p[1], p[0]))
    landing_xy = entry_sorted[0]  # norte del 2×2 (hacia el maze)
    return_xy = entry_sorted[-1]  # sur — retorno apenas llegás
    landing_pos = (landing_xy[0], landing_xy[1], z)
    return_pos = (return_xy[0], return_xy[1], z)

    tiles[return_pos] = TileSpec(ground=GROUND_PATH, teleport=hub_landing)

    # Escape opcional al fondo (1 tile), misma lógica de laberinto.
    exit_tiles = north_exit_tiles(visited, origin_x, origin_y_south, z, cells_x, cells_y)
    escape_pos = exit_tiles[0]
    tiles[escape_pos] = TileSpec(ground=GROUND_PATH, teleport=hub_landing)

    tiles[hub_portal] = TileSpec(ground=HUB_GROUND, teleport=landing_pos)

    connectivity = validate_walkable_path(
        tiles, z, (landing_xy[0], landing_xy[1]), exit_tiles
    )
    meta = {
        "entryLanding": {"x": landing_pos[0], "y": landing_pos[1], "z": landing_pos[2]},
        "entryReturn": {"x": return_pos[0], "y": return_pos[1], "z": return_pos[2]},
        "exit": {"x": escape_pos[0], "y": escape_pos[1], "z": escape_pos[2]},
        "hubPortal": {"x": hub_portal[0], "y": hub_portal[1], "z": hub_portal[2]},
        "hubLanding": {"x": hub_landing[0], "y": hub_landing[1], "z": hub_landing[2]},
        "footprint": {"fromX": x0, "toX": x1, "fromY": y0, "toY": y1, "z": z},
        "connectivity": connectivity,
        "entryCell": list(entry_cell),
        "aliceUntouched": True,
    }
    return tiles, meta


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


def pick_monster(band_index: int, cell: tuple[int, int]) -> str:
    band = DIFFICULTY_BANDS[min(band_index, len(DIFFICULTY_BANDS) - 1)]
    return band[(cell[0] * 3 + cell[1] * 7) % len(band)]


def band_for_percentile(pct: float) -> int:
    n = len(DIFFICULTY_BANDS)
    return min(int((pct**1.35) * n), n - 1)


def plan_spawns(
    origin_x: int,
    origin_y_south: int,
    z: int,
    cells_y: int,
    visited: set[tuple[int, int]],
    edges: set[tuple[tuple[int, int], tuple[int, int]]],
    entry_cell: tuple[int, int],
    skip_positions: set[tuple[int, int, int]],
) -> list[dict]:
    dist = cell_bfs_distance(visited, edges, entry_cell)
    ordered = sorted(visited, key=lambda c: (dist[c], c[1], c[0]))
    n_cells = len(ordered)
    spawns: list[dict] = []
    for rank, cell in enumerate(ordered):
        block = cell_block_tiles(origin_x, origin_y_south, cells_y, cell[0], cell[1])
        chosen = None
        for xy in (block[3], block[0], block[1], block[2]):
            pos = (xy[0], xy[1], z)
            if pos not in skip_positions:
                chosen = pos
                break
        if chosen is None:
            continue
        pct = rank / max(n_cells - 1, 1)
        band = band_for_percentile(pct)
        spawns.append(
            {
                "name": pick_monster(band, cell),
                "x": chosen[0],
                "y": chosen[1],
                "z": z,
                "band": band,
                "dist": dist[cell],
                "rankPct": round(pct, 4),
            }
        )
    return spawns


def build_spawn_xml(spawns: list[dict]) -> str:
    lines = [f"\t{SPAWN_MARK_BEGIN}"]
    for s in spawns:
        lines.append(
            f'\t<spawn centerx="{s["x"]}" centery="{s["y"]}" centerz="{s["z"]}" radius="1">'
        )
        lines.append(
            f'\t\t<monster name="{s["name"]}" x="0" y="0" z="{s["z"]}" '
            f'spawntime="{SPAWN_TIME}" direction="2" />'
        )
        lines.append("\t</spawn>")
    lines.append(f"\t{SPAWN_MARK_END}")
    return "\n".join(lines) + "\n"


def strip_block(text: str, begin: str, end: str) -> str:
    return re.sub(
        re.escape(begin) + r".*?" + re.escape(end) + r"\n?",
        "",
        text,
        flags=re.DOTALL,
    )


def upsert_hunt_spawns(spawn_path: Path, block: str) -> None:
    text = spawn_path.read_text(encoding="utf-8")
    text = strip_block(text, SPAWN_MARK_BEGIN, SPAWN_MARK_END)
    text = strip_block(text, LEGACY_ALICE_HUNT_BEGIN, LEGACY_ALICE_HUNT_END)
    if SPAWN_MARK_BEGIN in text:
        raise ValueError("no se pudo limpiar bloque HUNT_MAZE previo")
    if "</spawns>" not in text:
        raise ValueError(f"no se encontró </spawns> en {spawn_path}")
    text = text.replace("</spawns>", block + "</spawns>", 1)
    spawn_path.write_text(text, encoding="utf-8")


def validate_monsters(names: list[str], monsters_xml: Path) -> None:
    registered = set(re.findall(r'name="([^"]+)"', monsters_xml.read_text(encoding="utf-8")))
    missing = sorted({n for n in names if n not in registered})
    if missing:
        raise ValueError(f"monstruos no registrados en monsters.xml: {missing}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin-x", type=int, default=DEFAULT_ORIGIN_X)
    parser.add_argument("--origin-y-south", type=int, default=DEFAULT_ORIGIN_Y_SOUTH)
    parser.add_argument("--z", type=int, default=DEFAULT_Z)
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
        project / "server/YurOTS/ots/data/world/generated-hunt-maze.json"
    )
    monsters_xml = project / "server/YurOTS/ots/data/monster/monsters.xml"
    hub_portal = (args.hub_x, args.hub_y, args.hub_z)
    hub_landing = (args.hub_land_x, args.hub_land_y, args.hub_land_z)

    if not otbm_path.is_file():
        print(f"ERROR: no existe {otbm_path}", file=sys.stderr)
        return 1

    visited, edges = generate_maze_cells(args.cells_x, args.cells_y, args.seed)
    new_tiles, meta = build_hunt_tiles(
        args.origin_x,
        args.origin_y_south,
        args.z,
        args.cells_x,
        args.cells_y,
        args.seed,
        hub_portal,
        hub_landing,
    )
    fp = meta["footprint"]
    try:
        assert_no_alice_overlap(fp)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    skip = {pos for pos, spec in new_tiles.items() if spec.teleport is not None}
    skip.add(hub_portal)
    spawns = plan_spawns(
        args.origin_x,
        args.origin_y_south,
        args.z,
        args.cells_y,
        visited,
        edges,
        tuple(meta["entryCell"]),
        skip,
    )
    try:
        validate_monsters([s["name"] for s in spawns], monsters_xml)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    path_count = sum(1 for s in new_tiles.values() if s.ground == GROUND_PATH)
    bg_count = sum(1 for s in new_tiles.values() if s.ground == GROUND_BG)
    tele_count = sum(1 for s in new_tiles.values() if s.teleport is not None)
    counts = Counter(s["name"] for s in spawns)

    print("Hunt maze SEPARADO — Alice Maze no se toca")
    print(
        f"Celdas {args.cells_x}x{args.cells_y}, seed {args.seed}, "
        f"camino {GROUND_PATH} / fondo {GROUND_BG}"
    )
    print(
        f"Portal templo viejo: ({hub_portal[0]},{hub_portal[1]},{hub_portal[2]}) → "
        f"({meta['entryLanding']['x']},{meta['entryLanding']['y']},{meta['entryLanding']['z']})"
    )
    print(
        f"Retorno al llegar: ({meta['entryReturn']['x']},{meta['entryReturn']['y']},"
        f"{meta['entryReturn']['z']}) → "
        f"({hub_landing[0]},{hub_landing[1]},{hub_landing[2]})"
    )
    print(
        f"Escape norte: ({meta['exit']['x']},{meta['exit']['y']},{meta['exit']['z']}) → "
        f"mismo hub landing"
    )
    print(f"Footprint hunt: X {fp['fromX']}-{fp['toX']}, Y {fp['fromY']}-{fp['toY']}, z {fp['z']}")
    print("Alice Maze: X 380-433, Y 18-103 (intacta)")
    conn = meta["connectivity"]
    print(
        f"Tiles: camino {path_count}, fondo {bg_count}, teleports {tele_count} | "
        f"conectividad {conn['reachablePathTiles']}/{conn['totalPathTiles']}"
    )
    print(f"Spawns: {len(spawns)} (spawntime {SPAWN_TIME}s)")
    for name, n in counts.most_common():
        print(f"  {name:<22} {n:3}")

    summary = {
        "name": "generated-hunt-maze",
        "separateFromAlice": True,
        "aliceFootprint": {
            "fromX": 380,
            "toX": 433,
            "fromY": 18,
            "toY": 103,
            "z": 7,
        },
        "cells": {"x": args.cells_x, "y": args.cells_y},
        "seed": args.seed,
        "groundPathId": GROUND_PATH,
        "groundBackgroundId": GROUND_BG,
        "teleportItemId": TELEPORT_ITEM,
        "difficultyBands": [list(b) for b in DIFFICULTY_BANDS],
        "spawnTime": SPAWN_TIME,
        "spawnCount": len(spawns),
        "spawnCounts": dict(counts),
        "mapFile": str(otbm_path.relative_to(project)),
        "spawnFile": str(spawn_path.relative_to(project)),
        "tileCounts": {
            "path": path_count,
            "background": bg_count,
            "teleports": tele_count,
            "total": len(new_tiles),
        },
        **meta,
    }

    if args.dry_run:
        print("\n(dry-run — no se modificó el mapa ni spawns)")
        return 0

    if not args.replace:
        print("ERROR: usá --replace para escribir el hunt maze.", file=sys.stderr)
        return 1

    raw = otbm_path.read_bytes()
    body = raw[4:]
    body = _maze.filter_tiles_in_bbox(
        body, fp["fromX"], fp["fromY"], fp["toX"], fp["toY"], args.z
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

    backup = otbm_path.with_suffix(".otbm.bak-hunt-maze")
    if not backup.exists():
        backup.write_bytes(raw)
        print(f"\nBackup: {backup}")

    otbm_path.write_bytes(patched)
    upsert_hunt_spawns(spawn_path, build_spawn_xml(spawns))
    manifest_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"\nOK — mapa: {otbm_path}")
    print(f"OK — spawns: {spawn_path}")
    print(f"OK — manifiesto: {manifest_path}")
    print("Reiniciá: docker compose -f docker-compose.prod.yml restart yurots")
    print(
        f"Portal: /pos {hub_portal[0]} {hub_portal[1]} {hub_portal[2]}  |  "
        f"Hunt: /pos {meta['entryLanding']['x']} {meta['entryLanding']['y']} "
        f"{meta['entryLanding']['z']}  |  Alice: /pos 380 102 7 (barco maze)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
