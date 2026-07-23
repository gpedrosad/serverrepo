#!/usr/bin/env python3
"""Zona de caza por PISOS + TELEPORTS (aparte de Alice y hunt maze plano).

- 16 plantas (z0→z15), misma huella XY, laberinto 2 sqm (406/100).
- Todo el avance entre pisos es por teleport (item 1387).
- Portal templo viejo 162,54,7 → z0 (más fácil); z15 = fondo.
- Entrada sur: LAND + TP home + TP subir; norte: TP bajar.
- NE: express TP (+2 pisos) en pisos pares — atajo arriesgado.
- Hitos cada 4 pisos: spawns densos (pack×2).
- Spawns en <!-- BEGIN FLOOR_HUNT -->.

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

# Huella al oeste del hunt maze plano (280–349). Vacía en z0–z15.
DEFAULT_ORIGIN_X = 200
DEFAULT_ORIGIN_Y_SOUTH = 400
DEFAULT_CELLS_X = 12
DEFAULT_CELLS_Y = 16
DEFAULT_SEED = 421
# Torre completa: z0 (fácil) → z15 (fondo). Todo vía teleports.
FLOORS = tuple(range(0, 16))
CLEAR_Z_EXTRA = tuple(range(0, 16))

# Portal distinto al hunt maze (160,54,7).
HUB_PORTAL = (162, 54, 7)
HUB_LANDING = (163, 54, 7)
HUB_GROUND = 406

ALICE_FOOTPRINT = (380, 18, 433, 103, 7)
HUNT_MAZE_FOOTPRINT = (280, 243, 349, 400, 7)

SPAWN_MARK_BEGIN = "<!-- BEGIN FLOOR_HUNT -->"
SPAWN_MARK_END = "<!-- END FLOOR_HUNT -->"
SPAWN_TIME = 65

FLOOR_LABELS: tuple[str, ...] = (
    "Rat Cellars",
    "Damp Tunnels",
    "Spider Nest",
    "Larva Pits",
    "Spear Halls",
    "Wolf Den",
    "Bandit Vault",
    "Amazon Wing",
    "Valkyrie March",
    "Stalker Dark",
    "Assassin Row",
    "Hunter Gallery",
    "Mummy Crypt",
    "Terror Aviary",
    "Gazer Spire",
    "Djinn Depths",
)

# 16 bandas — subida lenta y variada.
FLOOR_ROSTERS: tuple[tuple[str, ...], ...] = (
    ("Rat", "Cave Rat", "Rat", "Hyaena"),
    ("Cave Rat", "Hyaena", "Poison Spider", "Cave Rat"),
    ("Poison Spider", "Centipede", "Hyaena", "Poison Spider"),
    ("Centipede", "Larva", "Scorpion", "Centipede"),
    ("Larva", "Scorpion", "Orc Spearman", "Larva"),
    ("Orc Spearman", "Bandit", "War Wolf", "Scorpion"),
    ("Bandit", "War Wolf", "Dworc Fleshhunter", "Orc Spearman"),
    ("War Wolf", "Amazon", "Bandit", "Dworc Fleshhunter"),
    ("Amazon", "Valkyrie", "Stalker", "Amazon"),
    ("Valkyrie", "Stalker", "Assassin", "Amazon"),
    ("Stalker", "Assassin", "Hunter", "Valkyrie"),
    ("Assassin", "Hunter", "Mummy", "Stalker"),
    ("Hunter", "Mummy", "Terror Bird", "Assassin"),
    ("Mummy", "Terror Bird", "Gazer", "Hunter"),
    ("Terror Bird", "Gazer", "Blue Djinn", "Mummy"),
    ("Gazer", "Blue Djinn", "Blue Djinn", "Terror Bird"),
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
) -> tuple[dict[tuple[int, int, int], TileSpec], set[tuple[int, int]], set, dict]:
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
    # 2×2 ordenado: NW, NE, SW, SE (por y luego x).
    entry_sorted = sorted(entry_block, key=lambda p: (p[1], p[0]))
    nw, ne, sw, se = entry_sorted
    exit_tiles = north_exit_tiles(visited, origin_x, origin_y_south, z, cells_x, cells_y)

    meta = {
        "landing": (nw[0], nw[1], z),       # llegar (sin TP)
        "tpHome": (se[0], se[1], z),        # teleport → templo
        "tpUp": (sw[0], sw[1], z),          # teleport → piso de arriba
        "tpSpare": (ne[0], ne[1], z),       # camino libre / señal
        "north": exit_tiles[0],
        "northAll": exit_tiles,             # todos → bajar (teleport)
        "entryCell": entry_cell,
        "footprint": {"fromX": x0, "toX": x1, "fromY": y0, "toY": y1, "z": z},
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
        name = roster[(cell[0] * 3 + cell[1] * 5 + z) % len(roster)]
        pack = 1
        if milestone and (cell[0] + cell[1]) % 3 == 0:
            pack = 2
        spawns.append(
            {
                "name": name,
                "x": chosen[0],
                "y": chosen[1],
                "z": z,
                "floor": z,
                "pack": pack,
            }
        )
    return spawns


def build_all_floors(
    origin_x: int,
    origin_y_south: int,
    cells_x: int,
    cells_y: int,
    seed: int,
    floors: tuple[int, ...],
    hub_portal: tuple[int, int, int],
    hub_landing: tuple[int, int, int],
) -> tuple[dict[tuple[int, int, int], TileSpec], dict, list[dict]]:
    all_tiles: dict[tuple[int, int, int], TileSpec] = {}
    floor_meta: dict[int, dict] = {}
    all_spawns: list[dict] = []
    floor_graphs: dict[int, tuple] = {}

    for i, z in enumerate(floors):
        tiles, visited, edges, meta = build_floor_maze(
            origin_x, origin_y_south, z, cells_x, cells_y, seed + z * 17
        )
        all_tiles.update(tiles)
        floor_meta[z] = meta
        floor_graphs[z] = (visited, edges, meta["entryCell"])

    # Cablear TELEPORTS entre pisos + hub.
    z0 = floors[0]
    m0 = floor_meta[z0]
    landing0 = m0["landing"]

    all_tiles[hub_portal] = TileSpec(ground=HUB_GROUND, teleport=landing0)

    for i, z in enumerate(floors):
        meta = floor_meta[z]
        landing = meta["landing"]
        tp_home = meta["tpHome"]
        tp_up = meta["tpUp"]
        tp_spare = meta["tpSpare"]

        # Llegada siempre limpia (sin TP).
        all_tiles[landing] = TileSpec(ground=GROUND_PATH)

        # Home desde cualquier piso.
        all_tiles[tp_home] = TileSpec(ground=GROUND_PATH, teleport=hub_landing)

        # Subir (teleport) — en el primer piso también vuelve al templo.
        if i == 0:
            all_tiles[tp_up] = TileSpec(ground=GROUND_PATH, teleport=hub_landing)
            up_dest = "temple"
        else:
            dest_up = floor_meta[floors[i - 1]]["landing"]
            all_tiles[tp_up] = TileSpec(ground=GROUND_PATH, teleport=dest_up)
            up_dest = f"z{floors[i - 1]}"

        # Bajar: TODOS los tiles del bloque norte son teleport (bien visible).
        if i < len(floors) - 1:
            dest_down = floor_meta[floors[i + 1]]["landing"]
            down_dest = f"z{floors[i + 1]}"
        else:
            dest_down = hub_landing  # fondo → templo
            down_dest = "temple"
        for pos in meta["northAll"]:
            all_tiles[pos] = TileSpec(ground=GROUND_PATH, teleport=dest_down)

        # Express +2 (NE): atajo arriesgado en pisos pares (no en los 2 últimos).
        express_dest = None
        if i % 2 == 0 and i < len(floors) - 2:
            dest_ex = floor_meta[floors[i + 2]]["landing"]
            all_tiles[tp_spare] = TileSpec(ground=GROUND_PATH, teleport=dest_ex)
            express_dest = f"z{floors[i + 2]}"
        else:
            all_tiles[tp_spare] = TileSpec(ground=GROUND_PATH)

        label = FLOOR_LABELS[i] if i < len(FLOOR_LABELS) else f"Floor {i}"
        meta["label"] = label
        meta["milestone"] = i > 0 and i % 4 == 0
        meta["teleports"] = {
            "home": {"x": tp_home[0], "y": tp_home[1], "z": z, "dest": "temple"},
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

    # Validar cada piso (solo footprint; el portal del hub está fuera).
    for z in floors:
        meta = floor_meta[z]
        fpz = meta["footprint"]
        floor_tiles = {
            p: s
            for p, s in all_tiles.items()
            if p[2] == z
            and fpz["fromX"] <= p[0] <= fpz["toX"]
            and fpz["fromY"] <= p[1] <= fpz["toY"]
        }
        conn = validate_walkable_path(
            floor_tiles,
            z,
            (meta["landing"][0], meta["landing"][1]),
            list(meta["northAll"]),
        )
        meta["connectivity"] = conn

    skip = {p for p, s in all_tiles.items() if s.teleport is not None}
    skip.add(hub_portal)

    for i, z in enumerate(floors):
        visited, edges, entry_cell = floor_graphs[z]
        roster = FLOOR_ROSTERS[min(i, len(FLOOR_ROSTERS) - 1)]
        all_spawns.extend(
            plan_floor_spawns(
                origin_x,
                origin_y_south,
                z,
                cells_y,
                visited,
                edges,
                entry_cell,
                skip,
                roster,
                milestone=bool(floor_meta[z].get("milestone")),
            )
        )

    summary_meta = {
        "floors": [
            {
                "z": z,
                "index": i,
                "label": floor_meta[z].get("label", f"z{z}"),
                "milestone": floor_meta[z].get("milestone", False),
                "landing": {
                    "x": floor_meta[z]["landing"][0],
                    "y": floor_meta[z]["landing"][1],
                    "z": z,
                },
                "teleports": floor_meta[z]["teleports"],
                "roster": list(FLOOR_ROSTERS[min(i, len(FLOOR_ROSTERS) - 1)]),
                "connectivity": floor_meta[z]["connectivity"],
            }
            for i, z in enumerate(floors)
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
            "fromX": floor_meta[z0]["footprint"]["fromX"],
            "toX": floor_meta[z0]["footprint"]["toX"],
            "fromY": floor_meta[z0]["footprint"]["fromY"],
            "toY": floor_meta[z0]["footprint"]["toY"],
            "fromZ": floors[0],
            "toZ": floors[-1],
        },
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
    parser.add_argument("--origin-x", type=int, default=DEFAULT_ORIGIN_X)
    parser.add_argument("--origin-y-south", type=int, default=DEFAULT_ORIGIN_Y_SOUTH)
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
        args.origin_x,
        args.origin_y_south,
        args.cells_x,
        args.cells_y,
        args.seed,
        FLOORS,
        hub_portal,
        hub_landing,
    )
    fp = meta["footprint"]
    # Chequeo anti-solape en z7 (Alice / hunt maze plano).
    fp7 = {
        "fromX": fp["fromX"],
        "toX": fp["toX"],
        "fromY": fp["fromY"],
        "toY": fp["toY"],
        "z": 7,
    }
    if overlaps(fp7, ALICE_FOOTPRINT):
        print("ERROR: solapa Alice Maze", file=sys.stderr)
        return 1
    if overlaps(fp7, HUNT_MAZE_FOOTPRINT):
        print("ERROR: solapa hunt maze plano", file=sys.stderr)
        return 1

    try:
        validate_monsters([s["name"] for s in spawns], monsters_xml)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    path_count = sum(1 for s in new_tiles.values() if s.ground == GROUND_PATH)
    bg_count = sum(1 for s in new_tiles.values() if s.ground == GROUND_BG)
    tele_count = sum(1 for s in new_tiles.values() if s.teleport is not None)
    counts = Counter(s["name"] for s in spawns)
    by_floor = Counter(s["z"] for s in spawns)

    print(
        f"Floor hunt — {len(FLOORS)} pisos con TELEPORTS "
        "(aparte de Alice y hunt maze plano)"
    )
    print(
        f"Celdas {args.cells_x}x{args.cells_y}/piso, seed {args.seed}, "
        f"pisos z{FLOORS[0]}…z{FLOORS[-1]}"
    )
    print(
        f"Portal templo: ({hub_portal[0]},{hub_portal[1]},{hub_portal[2]}) → "
        f"({meta['entryLanding']['x']},{meta['entryLanding']['y']},{meta['entryLanding']['z']})"
    )
    print(
        f"TP home (cada piso, SE entrada): ej. z7 "
        f"({meta['entryReturn']['x']},{meta['entryReturn']['y']},"
        f"{meta['entryReturn']['z']}) → "
        f"({hub_landing[0]},{hub_landing[1]},{hub_landing[2]})"
    )
    print(
        f"Footprint XY: X {fp['fromX']}-{fp['toX']}, Y {fp['fromY']}-{fp['toY']} | "
        f"Z {fp['fromZ']}-{fp['toZ']}"
    )
    for fl in meta["floors"]:
        z = fl["z"]
        tps = fl["teleports"]
        ex = tps.get("express")
        ex_s = (
            f" | TP express→{ex['dest']} @ ({ex['x']},{ex['y']})"
            if ex
            else ""
        )
        mark = " ★" if fl.get("milestone") else ""
        print(
            f"  z{z}{mark} {fl.get('label','')}: "
            f"down→{tps['down']['dest']} up→{tps['up']['dest']}"
            f"{ex_s} | spawns {by_floor[z]}"
        )
    print(f"Tiles: camino {path_count}, fondo {bg_count}, teleports {tele_count}")
    print(f"Spawns total: {len(spawns)}")
    for name, n in counts.most_common():
        print(f"  {name:<22} {n:3}")

    summary = {
        "name": "generated-floor-hunt",
        "separateFromAlice": True,
        "separateFromHuntMaze": True,
        "cells": {"x": args.cells_x, "y": args.cells_y},
        "seed": args.seed,
        "floorsZ": list(FLOORS),
        "groundPathId": GROUND_PATH,
        "groundBackgroundId": GROUND_BG,
        "teleportItemId": TELEPORT_ITEM,
        "spawnTime": SPAWN_TIME,
        "spawnCount": len(spawns),
        "spawnCounts": dict(counts),
        "spawnsByFloor": dict(by_floor),
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
        print("ERROR: usá --replace", file=sys.stderr)
        return 1

    raw = otbm_path.read_bytes()
    body = raw[4:]
    clear_zs = sorted(set(FLOORS) | set(CLEAR_Z_EXTRA))
    for z in clear_zs:
        body = _maze.filter_tiles_in_bbox(
            body, fp["fromX"], fp["fromY"], fp["toX"], fp["toY"], z
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
        f"Portal pisos: /pos {hub_portal[0]} {hub_portal[1]} {hub_portal[2]}  |  "
        f"Hunt plano: /pos 160 54 7  |  Alice: barco maze"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
