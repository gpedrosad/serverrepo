#!/usr/bin/env python3
"""Genera una isla procedural en test.otbm (suelo + agua + costa).

La isla se escribe en una zona vacía del mapa. Los monstruos no se incluyen:
después abrí RME y pintá spawns en la isla, o editá test-spawn.xml.

Uso:
  python3 scripts/generate-island.py --dry-run
  python3 scripts/generate-island.py --center-x 350 --center-y 180 --radius 14
  docker compose restart yurots
"""
from __future__ import annotations

import argparse
import json
import math
import random
import struct
import sys
from collections import defaultdict
from pathlib import Path

NODE_START = 0xFE
NODE_END = 0xFF
ESCAPE_CHAR = 0xFD

OTBM_TILE_AREA = 4
OTBM_TILE = 5
OTBM_ATTR_ITEM = 9

# IDs de suelo usados en el mapa YurOTS 7.6
GROUND_WATER = 4608
GROUND_SHORE = 4526
GROUND_DIRT = 231
GROUND_GRASS = (405, 598, 407)


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
    pos += 1  # type
    _, pos = read_props(body, pos)
    while pos < len(body):
        if body[pos] == NODE_END:
            return pos + 1
        if body[pos] == NODE_START:
            pos = skip_node(body, pos)
        else:
            pos += 1
    raise ValueError("OTBM sin cierre de nodo")


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


def island_ground(
    dx: float,
    dy: float,
    radius: float,
    rng: random.Random,
) -> int | None:
    dist = math.sqrt(dx * dx + dy * dy) / radius
    if dist > 1.18:
        return None
    wobble = 0.06 * math.sin(dx * 0.55) * math.cos(dy * 0.41)
    dist += wobble
    if dist > 1.05:
        return GROUND_WATER
    if dist > 0.92:
        return GROUND_SHORE
    if dist > 0.78:
        return GROUND_DIRT
    return rng.choice(GROUND_GRASS)


def build_island_tiles(
    center_x: int,
    center_y: int,
    z: int,
    radius: int,
    seed: int,
) -> dict[tuple[int, int, int], int]:
    rng = random.Random(seed)
    tiles: dict[tuple[int, int, int], int] = {}
    margin = 3
    for y in range(center_y - radius - margin, center_y + radius + margin + 1):
        for x in range(center_x - radius - margin, center_x + radius + margin + 1):
            ground = island_ground(x - center_x, y - center_y, radius, rng)
            if ground is not None:
                tiles[(x, y, z)] = ground
    return tiles


def encode_tile_node(x_off: int, y_off: int, ground_id: int) -> bytes:
    if not (0 <= x_off <= 255 and 0 <= y_off <= 255):
        raise ValueError(f"offset fuera de rango: {x_off},{y_off}")
    props = struct.pack("<BB", x_off, y_off)
    props += struct.pack("<BH", OTBM_ATTR_ITEM, ground_id)
    buf = bytearray()
    buf.append(NODE_START)
    buf.append(OTBM_TILE)
    write_props(buf, props)
    for child in ():
        pass
    buf.append(NODE_END)
    return bytes(buf)


def encode_tile_area(base_x: int, base_y: int, base_z: int, rel_tiles: list[tuple[int, int, int]]) -> bytes:
    area_props = struct.pack("<HHB", base_x, base_y, base_z)
    buf = bytearray()
    buf.append(NODE_START)
    buf.append(OTBM_TILE_AREA)
    write_props(buf, area_props)
    for ox, oy, gid in sorted(rel_tiles):
        buf.extend(encode_tile_node(ox, oy, gid))
    buf.append(NODE_END)
    return bytes(buf)


def group_tile_areas(tiles: dict[tuple[int, int, int], int]) -> list[bytes]:
    by_z: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    for (x, y, z), gid in tiles.items():
        by_z[z].append((x, y, gid))

    chunks: list[bytes] = []
    for z, entries in sorted(by_z.items()):
        buckets: dict[tuple[int, int], list[tuple[int, int, int]]] = defaultdict(list)
        for x, y, gid in entries:
            bx = (x // 256) * 256
            by = (y // 256) * 256
            buckets[(bx, by)].append((x - bx, y - by, gid))

        for (bx, by), rel in sorted(buckets.items()):
            current: list[tuple[int, int, int]] = []
            for ox, oy, gid in sorted(rel):
                if ox > 255 or oy > 255:
                    if current:
                        chunks.append(encode_tile_area(bx, by, z, current))
                        current = []
                    sub_bx = bx + (ox // 256) * 256
                    sub_by = by + (oy // 256) * 256
                    chunks.append(
                        encode_tile_area(sub_bx, sub_by, z, [(ox % 256, oy % 256, gid)])
                    )
                    continue
                current.append((ox, oy, gid))
            if current:
                chunks.append(encode_tile_area(bx, by, z, current))
    return chunks


def summarize_island(tiles: dict[tuple[int, int, int], int], center_x: int, center_y: int, z: int) -> dict:
    land = [(x, y) for (x, y, tz), gid in tiles.items() if tz == z and gid != GROUND_WATER]
    if not land:
        raise ValueError("la isla no tiene tierra")
    xs = [x for x, _ in land]
    ys = [y for _, y in land]
    spawn_x = round(sum(xs) / len(xs))
    spawn_y = round(sum(ys) / len(ys))
    return {
        "center": {"x": center_x, "y": center_y, "z": z},
        "spawnCenter": {"x": spawn_x, "y": spawn_y, "z": z},
        "bounds": {
            "fromX": min(xs),
            "toX": max(xs),
            "fromY": min(ys),
            "toY": max(ys),
            "z": z,
        },
        "tileCounts": {
            "total": len(tiles),
            "land": len(land),
            "water": sum(1 for g in tiles.values() if g == GROUND_WATER),
        },
        "spawnXmlHint": (
            f'<spawn centerx="{spawn_x}" centery="{spawn_y}" centerz="{z}" radius="8">\n'
            f'  <!-- agregá monstruos acá en RME o en test-spawn.xml -->\n'
            f"</spawn>"
        ),
    }


def patch_otbm(raw: bytes, new_tiles: dict[tuple[int, int, int], int]) -> bytes:
    header, body = raw[:4], raw[4:]
    existing = load_existing_tiles(body)
    conflicts = [pos for pos in new_tiles if pos in existing]
    if conflicts:
        sample = conflicts[:5]
        raise ValueError(
            f"{len(conflicts)} tile(s) ya existen en el mapa (ej. {sample}). "
            "Elegí otro --center-x/--center-y."
        )

    insert_at = find_map_data_insert(body)
    area_nodes = group_tile_areas(new_tiles)
    patch = b"".join(area_nodes)
    return header + body[:insert_at] + patch + body[insert_at:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--center-x", type=int, default=350, help="centro X de la isla")
    parser.add_argument("--center-y", type=int, default=180, help="centro Y de la isla")
    parser.add_argument("--z", type=int, default=7, help="piso (default 7)")
    parser.add_argument("--radius", type=int, default=14, help="radio aproximado en tiles")
    parser.add_argument("--seed", type=int, default=42, help="semilla para forma/textura")
    parser.add_argument("--map", type=Path, help="ruta al .otbm (default: test.otbm)")
    parser.add_argument("--manifest", type=Path, help="ruta al JSON de salida")
    parser.add_argument("--dry-run", action="store_true", help="no escribe archivos")
    args = parser.parse_args()

    project = next(p for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents] if (p / "AGENTS.md").is_file() or (p / ".git").is_dir())
    otbm_path = args.map or (project / "server/YurOTS/ots/data/world/test.otbm")
    manifest_path = args.manifest or (project / "server/YurOTS/ots/data/world/generated-island.json")

    if not otbm_path.is_file():
        print(f"ERROR: no existe {otbm_path}", file=sys.stderr)
        return 1

    new_tiles = build_island_tiles(args.center_x, args.center_y, args.z, args.radius, args.seed)
    summary = summarize_island(new_tiles, args.center_x, args.center_y, args.z)
    summary["name"] = "generated-island"
    summary["radius"] = args.radius
    summary["seed"] = args.seed
    summary["mapFile"] = str(otbm_path.relative_to(project))

    print(f"Isla: centro ({args.center_x}, {args.center_y}, {args.z}), radio {args.radius}")
    print(f"Tiles nuevos: {summary['tileCounts']['total']} "
          f"(tierra {summary['tileCounts']['land']}, agua {summary['tileCounts']['water']})")
    print(f"Spawn sugerido: ({summary['spawnCenter']['x']}, "
          f"{summary['spawnCenter']['y']}, {summary['spawnCenter']['z']})")
    print()
    print("Pegá esto en test-spawn.xml cuando quieras monstruos:")
    print(summary["spawnXmlHint"])

    if args.dry_run:
        print("\n(dry-run — no se modificó el mapa)")
        return 0

    raw = otbm_path.read_bytes()
    try:
        patched = patch_otbm(raw, new_tiles)
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
    print("Reiniciá el servidor: docker compose restart yurots")
    print("Spawns: ./scripts/open-rme.sh → spawn brush sobre la isla → exportar test-spawn.xml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
