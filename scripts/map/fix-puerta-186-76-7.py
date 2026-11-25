#!/usr/bin/env python3
"""Pone en tierra el suelo de la puerta 186,76,7 (24 nov 2026).

La puerta del edificio junto al puente rio_182 (186,76,7) es el único tile de la
columna de pared oeste (x=186, y75-78) que no lleva el suelo de afuera: los tiles
de pared llevan tierra 103 (y75) o borde 113 (y77-78) y la puerta llevaba piso de
piedra 431, que en el render se veía como un parche de piedra clara cortado contra
la tierra del patio. Se cambia el suelo a tierra 103 dejando la 1220 (open door)
encima. No cambia la caminabilidad: 103 es ground sin bloqueo y la 1220 open door
ya es pasable.

  python3.11 scripts/map/fix-puerta-186-76-7.py             # dry-run
  python3.11 scripts/map/fix-puerta-186-76-7.py --replace   # escribe test.otbm

Idempotente: si el tile ya es [103, 1220] no hace nada. Si no es exactamente
[431, 1220] ni [103, 1220], aborta sin escribir.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import (  # noqa: E402
    MAP, T_AREA, T_TILE, parse_tree, serialize_tree,
)

ATTR_FLAGS, ATTR_ITEM = 3, 9
TARGET = (186, 76, 7)
GROUND = 103
DOOR = 1220


def tile_xy(area, tile) -> tuple[int, int, int]:
    ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
    p = bytes(tile[1])
    return ax + p[0], ay + p[1], az


def items_of(tile) -> list[int]:
    p = bytes(tile[1])
    pos = 2 + (4 if tile[0] != T_TILE else 0)
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
        if k[0] == 6 and len(k[1]) >= 2:
            items.append(struct.unpack_from("<H", bytes(k[1]), 0)[0])
    return items


def flags_of(tile) -> bytes | None:
    p = bytes(tile[1])
    return bytes(p[3:7]) if len(p) >= 7 and p[2] == ATTR_FLAGS else None


def set_items(tile, ids: list[int]) -> None:
    fl = flags_of(tile)
    props = bytearray(tile[1][:2])
    if fl:
        props += bytes([ATTR_FLAGS]) + fl
    tile[1] = props
    tile[2] = [[6, bytearray(struct.pack("<H", i)), []] for i in ids]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replace", action="store_true", help="escribe test.otbm")
    args = ap.parse_args()

    raw = MAP.read_bytes()
    root = parse_tree(raw)
    tile = None
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        for t in area[2]:
            if t[0] == T_TILE and tile_xy(area, t) == TARGET:
                tile = t
                break
    if tile is None:
        raise SystemExit(f"ERROR: no está el tile {TARGET}")
    ids = items_of(tile)
    if ids == [GROUND, DOOR]:
        print(f"{TARGET}: ya está {ids}; nada que hacer")
        return 0
    if ids != [431, DOOR]:
        raise SystemExit(f"ERROR: {TARGET} tiene {ids}, se esperaba [431, {DOOR}] o [{GROUND}, {DOOR}]")
    set_items(tile, [GROUND, DOOR])
    print(f"{TARGET}: {ids} -> {items_of(tile)}")
    if not args.replace:
        print("dry-run: usá --replace para escribir")
        return 0
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    print(f"OK: escrito {MAP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
