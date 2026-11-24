#!/usr/bin/env python3
"""Saca del mapa las tumbas incompletas (ataúdes y sarcófagos de varias piezas).

Un ataúd o sarcófago nunca va de a una pieza (docs/items-and-map/PIEZAS_DE_MAPA.md):

  1410/1412/1413/1414 (cabecera) + 1411 (pie) abajo (y+1)
  1415 (ataúd enterrado, cabecera) + 1416 (pie) abajo (y+1)
  1417 + 1418 abajo (y+1)          sarcófago de pie
  1419 + 1420 a la derecha (x+1)   sarcófago acostado
  1742 + 1743 abajo (y+1)          ataúd de madera
  1744 + 1745 a la derecha (x+1)   ataúd de madera acostado

Si falta la pareja, las dos mitades sueltas se ven cortadas. Este script las saca y deja
las tumbas completas (y las lápidas 1406–1409, que son de una sola casilla).

El generador del Camino de los Caídos (generate-epstein-road.py) era el que las ponía
sueltas: el patio usaba 1411 y 1413 por separado, y el decorado del camino elegía 1415 o
1416 al azar. Ese generador ya no lo hace.

  python3 scripts/map/remove-incomplete-tombs.py            # dry-run
  python3 scripts/map/remove-incomplete-tombs.py --replace  # escribe test.otbm

Después: check-map-load.py (y, si se va a deployar, scan-map-depots.py y
sync-houses-with-map.py --dry-run).
"""
from __future__ import annotations

import argparse
import struct
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import MAP, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, parse_tree, serialize_tree  # noqa: E402

ATTR_FLAGS, ATTR_ITEM = 3, 9

# cabecera -> (pie, dx, dy)
HEADS = {
    1410: (1411, 0, 1),
    1412: (1411, 0, 1),
    1413: (1411, 0, 1),
    1414: (1411, 0, 1),
    1415: (1416, 0, 1),
    1417: (1418, 0, 1),
    1419: (1420, 1, 0),
    1742: (1743, 0, 1),
    1744: (1745, 1, 0),
}
FEET = {}
for head, (foot, dx, dy) in HEADS.items():
    FEET.setdefault(foot, []).append((head, dx, dy))
TOMB_PARTS = set(HEADS) | set(FEET)

NAMES = {
    1410: "ataúd de piedra (cabecera lisa)",
    1411: "ataúd de piedra (pie)",
    1412: "ataúd de piedra (gema amarilla)",
    1413: "ataúd de piedra (gema azul)",
    1414: "ataúd de piedra (gema roja)",
    1415: "ataúd enterrado (cabecera)",
    1416: "ataúd enterrado (pie)",
    1417: "sarcófago de pie (cabecera)",
    1418: "sarcófago de pie (pie)",
    1419: "sarcófago acostado (cabecera)",
    1420: "sarcófago acostado (pie)",
    1742: "ataúd de madera (cabecera)",
    1743: "ataúd de madera (pie)",
    1744: "ataúd de madera acostado (cabecera)",
    1745: "ataúd de madera acostado (pie)",
}


def tile_xy(area, tile) -> tuple[int, int, int]:
    ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
    p = bytes(tile[1])
    return ax + p[0], ay + p[1], az


def items_of(tile) -> list[int]:
    """Ids del tile en orden (inline + hijos), incluido el suelo."""
    p = bytes(tile[1])
    pos = 2 + (4 if tile[0] == T_HOUSETILE else 0)
    items = []
    while pos < len(p):
        attr = p[pos]
        if attr == ATTR_FLAGS:
            pos += 5
        elif attr == ATTR_ITEM:
            items.append(struct.unpack_from("<H", p, pos + 1)[0])
            pos += 3
        else:
            break
    for k in tile[2]:
        if k[0] == T_ITEM and len(k[1]) >= 2:
            items.append(struct.unpack_from("<H", bytes(k[1]), 0)[0])
    return items


def drop_ids(tile, drop: set[int]) -> int:
    """Saca del tile los ids de `drop` (inline no-suelo + hijos). Devuelve cuántos sacó."""
    p = bytes(tile[1])
    head = 2 + (4 if tile[0] == T_HOUSETILE else 0)
    segs, pos, first_item, n = [], head, True, 0
    while pos < len(p):
        attr = p[pos]
        if attr == ATTR_FLAGS:
            segs.append(p[pos:pos + 5])
            pos += 5
        elif attr == ATTR_ITEM:
            iid = struct.unpack_from("<H", p, pos + 1)[0]
            if not first_item and iid in drop:
                n += 1
            else:
                segs.append(p[pos:pos + 3])
            first_item = False
            pos += 3
        else:
            segs.append(p[pos:])
            break
    out = p[:head] + b"".join(segs)
    if out != p:
        tile[1] = bytearray(out)
    keep = []
    for k in tile[2]:
        if k[0] == T_ITEM and len(k[1]) >= 2 and struct.unpack_from("<H", bytes(k[1]), 0)[0] in drop:
            n += 1
            continue
        keep.append(k)
    tile[2] = keep
    return n


def index_tiles(root) -> dict[tuple[int, int, int], list[int]]:
    out = {}
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        for tile in area[2]:
            if tile[0] not in (T_TILE, T_HOUSETILE):
                continue
            out[tile_xy(area, tile)] = items_of(tile)
    return out


def incomplete(tiles: dict) -> dict[tuple[int, int, int], set[int]]:
    """(x,y,z) -> ids de piezas de tumba que no tienen su pareja en la casilla que toca."""
    bad = defaultdict(set)
    for (x, y, z), items in tiles.items():
        ids = set(items)
        for head, (foot, dx, dy) in HEADS.items():
            if head in ids and foot not in tiles.get((x + dx, y + dy, z), []):
                bad[(x, y, z)].add(head)
        for foot, mates in FEET.items():
            if foot in ids and not any(
                head in tiles.get((x - dx, y - dy, z), []) for head, dx, dy in mates
            ):
                bad[(x, y, z)].add(foot)
    return dict(bad)


def sweep(root, drop_at: dict[tuple[int, int, int], set[int]]) -> list[tuple[int, int, int, int, int]]:
    """Quita las piezas indicadas. Devuelve [(x,y,z,iid,n), ...]."""
    removed = []
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        for tile in area[2]:
            if tile[0] not in (T_TILE, T_HOUSETILE):
                continue
            key = tile_xy(area, tile)
            if key not in drop_at:
                continue
            drop = drop_at[key]
            n = drop_ids(tile, drop)
            assert n >= 1, f"no se pudo sacar {drop} de {key}"
            assert len(items_of(tile)) >= 1, f"el tile {key} quedaría sin ítems"
            for iid in sorted(drop):
                removed.append((key[0], key[1], key[2], iid, n))
    return removed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--map", type=Path, default=MAP)
    a = ap.parse_args()

    raw = a.map.read_bytes()
    root = parse_tree(raw)
    tiles = index_tiles(root)
    bad = incomplete(tiles)
    if not bad:
        print("No hay tumbas incompletas; nada que hacer.")
        return 0

    print(f"{sum(len(s) for s in bad.values())} piezas incompletas en {len(bad)} casillas:")
    for (x, y, z) in sorted(bad, key=lambda k: (k[2], k[1], k[0])):
        for iid in sorted(bad[(x, y, z)]):
            print(f"  {x},{y},{z}  {iid}  {NAMES.get(iid, '?')}")

    removed = sweep(root, bad)
    assert len(removed) == sum(len(s) for s in bad.values())
    leftover = incomplete(index_tiles(root))
    assert not leftover, f"quedaron tumbas incompletas: {leftover}"

    if not a.replace:
        print("dry-run: usá --replace para escribir")
        return 0
    a.map.write_bytes(serialize_tree(root, raw[:4]))
    print(f"OK: {len(removed)} piezas sacadas, {a.map}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
