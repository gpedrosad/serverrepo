#!/usr/bin/env python3
"""Genera un laberinto procedural en test.otbm.

Camino de 2 sqm de ancho con suelo id 406 (white marble floor).
Fondo id 100 (void decorativo) en todo el footprint del laberinto.
Entrada al sur; al norte un teleport (1387) al templo.

Uso:
  python3 scripts/generate-maze.py --dry-run
  python3 scripts/generate-maze.py --replace
  docker compose restart yurots
"""
from __future__ import annotations

import argparse
import json
import random
import struct
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

NODE_START = 0xFE
NODE_END = 0xFF
ESCAPE_CHAR = 0xFD

OTBM_TILE_AREA = 4
OTBM_TILE = 5
OTBM_ITEM = 6
OTBM_ATTR_TELE_DEST = 8
OTBM_ATTR_ITEM = 9

GROUND_PATH = 406
GROUND_BG = 100
TELEPORT_ITEM = 1387
TEMPLE_DEST = (130, 53, 6)
CELL_STRIDE = 4  # 2 sqm de camino + 2 sqm de separación


@dataclass
class TileSpec:
    ground: int
    teleport: tuple[int, int, int] | None = None


def read_props(data: bytes, pos: int) -> tuple[bytes, int]:
    out = bytearray()
    while pos < len(data):
        b = data[pos]
        pos += 1
        if b in (NODE_START, NODE_END):
            pos -= 1
            break
        if b == ESCAPE_CHAR:
            if pos >= len(data):
                raise ValueError("OTBM truncado")
            out.append(data[pos])
            pos += 1
        else:
            out.append(b)
    return bytes(out), pos


def write_props(buf: bytearray, props: bytes) -> None:
    for b in props:
        if b in (NODE_START, NODE_END, ESCAPE_CHAR):
            buf.append(ESCAPE_CHAR)
        buf.append(b)


def skip_node(body: bytes, pos: int) -> int:
    if pos >= len(body) or body[pos] != NODE_START:
        raise ValueError("nodo OTBM inválido")
    pos += 1
    pos += 1
    _, pos = read_props(body, pos)
    while pos < len(body):
        if body[pos] == NODE_END:
            return pos + 1
        if body[pos] == NODE_START:
            pos = skip_node(body, pos)
        else:
            pos += 1
    raise ValueError("OTBM sin cierre de nodo")


def tile_position(body: bytes, pos: int, area_base: tuple[int, int, int]) -> tuple[int, int, int] | None:
    if pos >= len(body) or body[pos] != NODE_START:
        return None
    pos += 1
    ntype = body[pos]
    pos += 1
    props, _ = read_props(body, pos)
    if ntype != OTBM_TILE or len(props) < 2:
        return None
    return (
        area_base[0] + props[0],
        area_base[1] + props[1],
        area_base[2],
    )


def filter_tiles_in_bbox(
    body: bytes,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    z: int,
) -> bytes:
    """Elimina nodos TILE dentro del bbox (inclusive)."""

    def copy_node(pos: int, area_base: tuple[int, int, int]) -> tuple[bytes, int]:
        if pos >= len(body) or body[pos] != NODE_START:
            return b"", pos
        node_start = pos
        pos += 1
        ntype = body[pos]
        pos += 1
        props, pos = read_props(body, pos)
        local = area_base
        drop = False
        if ntype == OTBM_TILE_AREA and len(props) >= 5:
            bx, by, bz = struct.unpack_from("<HHB", props, 0)
            local = (bx, by, bz)
        elif ntype == OTBM_TILE and len(props) >= 2:
            tx = local[0] + props[0]
            ty = local[1] + props[1]
            tz = local[2]
            if tz == z and x0 <= tx <= x1 and y0 <= ty <= y1:
                drop = True

        children = bytearray()
        depth = 1
        while pos < len(body) and depth > 0:
            if body[pos] == NODE_START:
                if drop:
                    pos = skip_node(body, pos)
                else:
                    child, pos = copy_node(pos, local)
                    children.extend(child)
            elif body[pos] == NODE_END:
                pos += 1
                depth -= 1
            else:
                pos += 1

        if drop:
            return b"", pos

        out = bytearray()
        out.append(NODE_START)
        out.append(ntype)
        write_props(out, props)
        out.extend(children)
        out.append(NODE_END)
        return bytes(out), pos

    out, _ = copy_node(0, (0, 0, 0))
    return out


def find_map_data_insert(body: bytes) -> int:
    pos = 0
    if body[pos] != NODE_START:
        raise ValueError("sin nodo raíz")
    pos += 2
    _, pos = read_props(body, pos)
    while pos < len(body):
        if body[pos] != NODE_START:
            break
        node_begin = pos
        pos += 1
        ntype = body[pos]
        pos += 1
        _, pos = read_props(body, pos)
        if ntype == 2:
            return pos
        pos = skip_node(body, node_begin)
    raise ValueError("no se encontró nodo map_data")


def load_existing_tiles(body: bytes) -> dict[tuple[int, int, int], int]:
    tiles: dict[tuple[int, int, int], int] = {}

    def walk(pos: int, area_base: tuple[int, int, int]) -> int:
        if pos >= len(body) or body[pos] != NODE_START:
            return pos
        pos += 1
        ntype = body[pos]
        pos += 1
        props, pos = read_props(body, pos)
        local = area_base
        if ntype == OTBM_TILE_AREA and len(props) >= 5:
            bx, by, bz = struct.unpack_from("<HHB", props, 0)
            local = (bx, by, bz)
        elif ntype == OTBM_TILE and len(props) >= 2:
            x = local[0] + props[0]
            y = local[1] + props[1]
            z = local[2]
            p = 2
            while p < len(props):
                attr = props[p]
                p += 1
                if attr == OTBM_ATTR_ITEM and p + 2 <= len(props):
                    tiles[(x, y, z)] = struct.unpack_from("<H", props, p)[0]
                    break
        depth = 1
        while pos < len(body) and depth > 0:
            if body[pos] == NODE_START:
                pos = walk(pos, local)
            elif body[pos] == NODE_END:
                pos += 1
                depth -= 1
            else:
                pos += 1
        return pos

    walk(0, (0, 0, 0))
    return tiles


def generate_maze_cells(
    cells_x: int,
    cells_y: int,
    seed: int,
) -> tuple[set[tuple[int, int]], set[tuple[tuple[int, int], tuple[int, int]]]]:
    """Laberinto perfecto (sin loops) con backtracking recursivo."""
    rng = random.Random(seed)
    visited: set[tuple[int, int]] = set()
    edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    start = (0, cells_y - 1)
    stack = [start]
    visited.add(start)

    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
    while stack:
        cx, cy = stack[-1]
        options: list[tuple[int, int]] = []
        for dx, dy in dirs:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < cells_x and 0 <= ny < cells_y and (nx, ny) not in visited:
                options.append((nx, ny))
        if options:
            nx, ny = rng.choice(options)
            visited.add((nx, ny))
            edges.add(tuple(sorted(((cx, cy), (nx, ny)))))
            stack.append((nx, ny))
        else:
            stack.pop()

    return visited, edges


def maze_footprint(
    origin_x: int,
    origin_y_south: int,
    cells_x: int,
    cells_y: int,
) -> tuple[int, int, int, int]:
    """BBox en tiles del laberinto completo (fondo incluido)."""
    width = (cells_x - 1) * CELL_STRIDE + 2
    height = (cells_y - 1) * CELL_STRIDE + 2
    north_y = origin_y_south - height + 1
    return origin_x, north_y, origin_x + width - 1, origin_y_south


def cell_base_y(origin_y_south: int, cells_y: int, cy: int) -> int:
    return origin_y_south - (cells_y - 1 - cy) * CELL_STRIDE - 1


def cell_block_tiles(
    origin_x: int,
    origin_y_south: int,
    cells_y: int,
    cx: int,
    cy: int,
) -> list[tuple[int, int]]:
    base_x = origin_x + cx * CELL_STRIDE
    base_y = cell_base_y(origin_y_south, cells_y, cy)
    return [
        (base_x, base_y),
        (base_x + 1, base_y),
        (base_x, base_y + 1),
        (base_x + 1, base_y + 1),
    ]


def connection_block_tiles(
    origin_x: int,
    origin_y_south: int,
    cells_y: int,
    c1: tuple[int, int],
    c2: tuple[int, int],
) -> list[tuple[int, int]]:
    """Puente 2×2 walkable entre dos celdas adyacentes (reemplaza el hueco de fondo 100)."""
    x1, y1 = c1
    x2, y2 = c2
    if x1 == x2:
        cy_north = min(y1, y2)
        cx = x1
        base_x = origin_x + cx * CELL_STRIDE
        base_y = cell_base_y(origin_y_south, cells_y, cy_north) + 2
    elif y1 == y2:
        cx_west = min(x1, x2)
        cy = y1
        base_x = origin_x + cx_west * CELL_STRIDE + 2
        base_y = cell_base_y(origin_y_south, cells_y, cy)
    else:
        raise ValueError(f"celdas no adyacentes: {c1} {c2}")
    return [
        (base_x, base_y),
        (base_x + 1, base_y),
        (base_x, base_y + 1),
        (base_x + 1, base_y + 1),
    ]


def add_cell_block(
    tiles: dict[tuple[int, int, int], TileSpec],
    origin_x: int,
    origin_y_south: int,
    z: int,
    cells_y: int,
    cx: int,
    cy: int,
) -> None:
    for x, y in cell_block_tiles(origin_x, origin_y_south, cells_y, cx, cy):
        tiles[(x, y, z)] = TileSpec(ground=GROUND_PATH)


def add_connection(
    tiles: dict[tuple[int, int, int], TileSpec],
    origin_x: int,
    origin_y_south: int,
    z: int,
    cells_y: int,
    c1: tuple[int, int],
    c2: tuple[int, int],
) -> None:
    for x, y in connection_block_tiles(origin_x, origin_y_south, cells_y, c1, c2):
        tiles[(x, y, z)] = TileSpec(ground=GROUND_PATH)


def path_positions(tiles: dict[tuple[int, int, int], TileSpec], z: int) -> set[tuple[int, int]]:
    return {
        (x, y)
        for (x, y, tz), spec in tiles.items()
        if tz == z and spec.ground == GROUND_PATH
    }


def validate_walkable_path(
    tiles: dict[tuple[int, int, int], TileSpec],
    z: int,
    entry: tuple[int, int],
    exit_positions: list[tuple[int, int, int]],
) -> dict:
    """Comprueba que todos los tiles 406 forman un solo componente y que la salida es alcanzable."""
    walkable = path_positions(tiles, z)
    if not walkable:
        raise ValueError("el laberinto no tiene tiles de camino")

    start = entry
    if start not in walkable:
        raise ValueError(f"la entrada {start} no está sobre camino {GROUND_PATH}")

    exit_xy = {(x, y) for x, y, _ in exit_positions}
    seen: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque([start])
    seen.add(start)

    while queue:
        x, y = queue.popleft()
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nxt = (x + dx, y + dy)
            if nxt in walkable and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)

    unreachable = walkable - seen
    if unreachable:
        raise ValueError(
            f"camino fragmentado: {len(unreachable)} tile(s) de camino no alcanzables desde la entrada"
        )
    if not seen.intersection(exit_xy):
        raise ValueError("la entrada no alcanza la salida del laberinto")

    return {
        "reachablePathTiles": len(seen),
        "totalPathTiles": len(walkable),
        "entryReachable": True,
        "exitReachable": True,
    }


def north_exit_tiles(
    visited: set[tuple[int, int]],
    origin_x: int,
    origin_y_south: int,
    z: int,
    cells_x: int,
    cells_y: int,
) -> list[tuple[int, int, int]]:
    north_cy = min(cy for _, cy in visited)
    candidates = sorted(cx for cx, cy in visited if cy == north_cy)
    exit_cx = candidates[len(candidates) // 2]
    return [(x, y, z) for x, y in cell_block_tiles(origin_x, origin_y_south, cells_y, exit_cx, north_cy)]


def build_maze_tiles(
    origin_x: int,
    origin_y_south: int,
    z: int,
    cells_x: int,
    cells_y: int,
    seed: int,
    temple_dest: tuple[int, int, int],
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

    exit_tiles = north_exit_tiles(visited, origin_x, origin_y_south, z, cells_x, cells_y)
    for pos in exit_tiles:
        tiles[pos] = TileSpec(ground=GROUND_PATH, teleport=temple_dest)

    entry_x, entry_y = cell_block_tiles(origin_x, origin_y_south, cells_y, 0, cells_y - 1)[0]
    connectivity = validate_walkable_path(tiles, z, (entry_x, entry_y), exit_tiles)
    meta = {
        "entry": {"x": entry_x, "y": entry_y, "z": z},
        "exit": {"x": exit_tiles[0][0], "y": exit_tiles[0][1], "z": z},
        "teleportDest": {"x": temple_dest[0], "y": temple_dest[1], "z": temple_dest[2]},
        "footprint": {"fromX": x0, "toX": x1, "fromY": y0, "toY": y1, "z": z},
        "connectivity": connectivity,
    }
    return tiles, meta


def encode_teleport_item(dest: tuple[int, int, int]) -> bytes:
    props = struct.pack("<H", TELEPORT_ITEM)
    props += struct.pack("<BHHB", OTBM_ATTR_TELE_DEST, dest[0], dest[1], dest[2])
    buf = bytearray()
    buf.append(NODE_START)
    buf.append(OTBM_ITEM)
    write_props(buf, props)
    buf.append(NODE_END)
    return bytes(buf)


def encode_tile_node(x_off: int, y_off: int, spec: TileSpec) -> bytes:
    if not (0 <= x_off <= 255 and 0 <= y_off <= 255):
        raise ValueError(f"offset fuera de rango: {x_off},{y_off}")
    props = struct.pack("<BB", x_off, y_off)
    props += struct.pack("<BH", OTBM_ATTR_ITEM, spec.ground)
    buf = bytearray()
    buf.append(NODE_START)
    buf.append(OTBM_TILE)
    write_props(buf, props)
    if spec.teleport is not None:
        buf.extend(encode_teleport_item(spec.teleport))
    buf.append(NODE_END)
    return bytes(buf)


def encode_tile_area(
    base_x: int,
    base_y: int,
    base_z: int,
    rel_tiles: list[tuple[int, int, TileSpec]],
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


def group_tile_areas(tiles: dict[tuple[int, int, int], TileSpec]) -> list[bytes]:
    by_z: dict[int, list[tuple[int, int, TileSpec]]] = defaultdict(list)
    for (x, y, z), spec in tiles.items():
        by_z[z].append((x, y, spec))

    chunks: list[bytes] = []
    for z, entries in sorted(by_z.items()):
        buckets: dict[tuple[int, int], list[tuple[int, int, TileSpec]]] = defaultdict(list)
        for x, y, spec in entries:
            bx = (x // 256) * 256
            by = (y // 256) * 256
            buckets[(bx, by)].append((x - bx, y - by, spec))

        for (bx, by), rel in sorted(buckets.items()):
            current: list[tuple[int, int, TileSpec]] = []
            for ox, oy, spec in sorted(rel, key=lambda t: (t[0], t[1])):
                if ox > 255 or oy > 255:
                    if current:
                        chunks.append(encode_tile_area(bx, by, z, current))
                        current = []
                    sub_bx = bx + (ox // 256) * 256
                    sub_by = by + (oy // 256) * 256
                    chunks.append(
                        encode_tile_area(sub_bx, sub_by, z, [(ox % 256, oy % 256, spec)])
                    )
                    continue
                current.append((ox, oy, spec))
            if current:
                chunks.append(encode_tile_area(bx, by, z, current))
    return chunks


def summarize_maze(
    tiles: dict[tuple[int, int, int], TileSpec],
    origin_x: int,
    origin_y_south: int,
    z: int,
    cells_x: int,
    cells_y: int,
    seed: int,
    meta: dict,
) -> dict:
    path_coords = [(x, y) for (x, y, tz), spec in tiles.items() if tz == z and spec.ground == GROUND_PATH]
    xs = [x for x, _ in path_coords]
    ys = [y for _, y in path_coords]
    bg_count = sum(1 for spec in tiles.values() if spec.ground == GROUND_BG)
    tele_count = sum(1 for spec in tiles.values() if spec.teleport is not None)
    return {
        "name": "generated-maze",
        "cells": {"x": cells_x, "y": cells_y},
        "seed": seed,
        "groundPathId": GROUND_PATH,
        "groundBackgroundId": GROUND_BG,
        "pathWidthSqm": 2,
        "teleportItemId": TELEPORT_ITEM,
        "originSouth": {"x": origin_x, "y": origin_y_south, "z": z},
        "entry": meta["entry"],
        "exit": meta["exit"],
        "teleportDest": meta["teleportDest"],
        "center": {
            "x": round((min(xs) + max(xs)) / 2),
            "y": round((min(ys) + max(ys)) / 2),
            "z": z,
        },
        "bounds": {
            "fromX": min(xs),
            "toX": max(xs),
            "fromY": min(ys),
            "toY": max(ys),
            "z": z,
        },
        "tileCounts": {
            "path": len(path_coords),
            "background": bg_count,
            "teleports": tele_count,
            "total": len(tiles),
        },
        "footprint": meta["footprint"],
        "connectivity": meta["connectivity"],
    }


def patch_otbm(
    raw: bytes,
    new_tiles: dict[tuple[int, int, int], TileSpec],
    *,
    replace_bbox: tuple[int, int, int, int, int] | None = None,
) -> bytes:
    header, body = raw[:4], raw[4:]
    if replace_bbox is not None:
        x0, y0, x1, y1, z = replace_bbox
        body = filter_tiles_in_bbox(body, x0, y0, x1, y1, z)
    else:
        existing = load_existing_tiles(body)
        conflicts = [pos for pos in new_tiles if pos in existing]
        if conflicts:
            sample = conflicts[:5]
            raise ValueError(
                f"{len(conflicts)} tile(s) ya existen en el mapa (ej. {sample}). "
                "Usá --replace o elegí otro --origin-x/--origin-y-south."
            )

    insert_at = find_map_data_insert(body)
    area_nodes = group_tile_areas(new_tiles)
    patch = b"".join(area_nodes)
    return header + body[:insert_at] + patch + body[insert_at:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin-x", type=int, default=380, help="esquina oeste del laberinto (X)")
    parser.add_argument(
        "--origin-y-south",
        type=int,
        default=103,
        help="borde sur del footprint (Y; entrada al sur)",
    )
    parser.add_argument("--z", type=int, default=7, help="piso (default 7)")
    parser.add_argument("--cells-x", type=int, default=14, help="celdas del laberinto en X")
    parser.add_argument("--cells-y", type=int, default=22, help="celdas del laberinto en Y (más = más largo al norte)")
    parser.add_argument("--seed", type=int, default=76, help="semilla procedural")
    parser.add_argument("--temple-x", type=int, default=TEMPLE_DEST[0])
    parser.add_argument("--temple-y", type=int, default=TEMPLE_DEST[1])
    parser.add_argument("--temple-z", type=int, default=TEMPLE_DEST[2])
    parser.add_argument("--map", type=Path, help="ruta al .otbm (default: test.otbm)")
    parser.add_argument("--manifest", type=Path, help="ruta al JSON de salida")
    parser.add_argument("--replace", action="store_true", help="reemplaza tiles en el footprint del laberinto")
    parser.add_argument("--dry-run", action="store_true", help="no escribe archivos")
    args = parser.parse_args()

    project = Path(__file__).resolve().parents[1]
    otbm_path = args.map or (project / "server/YurOTS/ots/data/world/test.otbm")
    manifest_path = args.manifest or (project / "server/YurOTS/ots/data/world/generated-maze.json")
    temple_dest = (args.temple_x, args.temple_y, args.temple_z)

    if not otbm_path.is_file():
        print(f"ERROR: no existe {otbm_path}", file=sys.stderr)
        return 1

    new_tiles, meta = build_maze_tiles(
        args.origin_x,
        args.origin_y_south,
        args.z,
        args.cells_x,
        args.cells_y,
        args.seed,
        temple_dest,
    )
    summary = summarize_maze(
        new_tiles,
        args.origin_x,
        args.origin_y_south,
        args.z,
        args.cells_x,
        args.cells_y,
        args.seed,
        meta,
    )
    summary["mapFile"] = str(otbm_path.relative_to(project))

    fp = summary["footprint"]
    print(
        f"Laberinto: {args.cells_x}x{args.cells_y} celdas, camino 2 sqm ({GROUND_PATH}), "
        f"fondo {GROUND_BG}"
    )
    print(f"Sur: ({args.origin_x}, {args.origin_y_south}, {args.z}), semilla {args.seed}")
    print(
        f"Tiles: camino {summary['tileCounts']['path']}, fondo {summary['tileCounts']['background']}, "
        f"teleports {summary['tileCounts']['teleports']}"
    )
    print(
        f"Entrada: ({summary['entry']['x']}, {summary['entry']['y']}, {summary['entry']['z']})"
    )
    print(
        f"Salida/TP: ({summary['exit']['x']}, {summary['exit']['y']}, {summary['exit']['z']}) "
        f"→ templo ({temple_dest[0]}, {temple_dest[1]}, {temple_dest[2]})"
    )
    print(
        f"Footprint: X {fp['fromX']}-{fp['toX']}, Y {fp['fromY']}-{fp['toY']}"
    )
    conn = summary["connectivity"]
    print(
        f"Conectividad: OK — {conn['reachablePathTiles']}/{conn['totalPathTiles']} "
        f"tiles de camino alcanzables (entrada → salida)"
    )

    if args.dry_run:
        print("\n(dry-run — no se modificó el mapa)")
        return 0

    raw = otbm_path.read_bytes()
    replace_bbox = None
    if args.replace:
        replace_bbox = (fp["fromX"], fp["fromY"], fp["toX"], fp["toY"], args.z)
    try:
        patched = patch_otbm(raw, new_tiles, replace_bbox=replace_bbox)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    backup = otbm_path.with_suffix(".otbm.bak")
    if not backup.exists():
        backup.write_bytes(raw)
        print(f"\nBackup: {backup}")

    otbm_path.write_bytes(patched)
    manifest_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"\nOK — mapa actualizado: {otbm_path}")
    print(f"OK — manifiesto: {manifest_path}")
    print("Reiniciá el servidor: docker compose -f docker-compose.prod.yml restart yurots")
    print(
        f"Entrada GM: /pos {summary['entry']['x']} {summary['entry']['y']} {summary['entry']['z']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
