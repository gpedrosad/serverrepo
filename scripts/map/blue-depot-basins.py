#!/usr/bin/env python3
"""Blue bassins (20192) en el edificio del depot: reemplaza los coal bassins.

El depot (lockers 2589 en x 127-133, y 58, z5-6; tiles 2590 en x 127, z7) tiene 18
coal bassins (1483) de braseros: 4 por piso en z4-z6 (x 128 y 132, y 56-57) y 6 en
z7 (x 128-129, y 54, 56 y 58). Este script los cambia por el blue bassin (20192,
`docs/items-and-map/ZAGAN_TEST_ITEMS.md`) y es idempotente: un tile sin 1483 no se
toca, así que se puede correr dos veces. No toca lockers ni ningún otro ítem.

Uso: python3 scripts/map/blue-depot-basins.py [--dry-run]
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import MAP, T_ITEM, T_TILE, parse_tree, serialize_tree  # noqa: E402

COAL = 1483
BLUE = 20192
# edificio del depot (bbox generoso alrededor de los 18 braseros)
ZS = (4, 5, 6, 7)
X0, X1, Y0, Y1 = 126, 134, 52, 60


def replace_in_tile(tile) -> tuple[int, int]:
    """Reemplaza 1483 -> 20192 en un tile, tanto en ítems inline (attr 9) como en
    nodos hijos T_ITEM. Devuelve (reemplazados, blue ya había)."""
    replaced = blues = 0
    p = tile[1]
    pos = 2
    while pos < len(p):
        if p[pos] == 3:
            pos += 5
        elif p[pos] == 9:
            sid = struct.unpack_from("<H", p, pos + 1)[0]
            if sid == COAL:
                p[pos + 1:pos + 3] = struct.pack("<H", BLUE)
                replaced += 1
            elif sid == BLUE:
                blues += 1
            pos += 4
        else:
            break
    for child in tile[2]:
        if child[0] != T_ITEM or len(child[1]) < 2:
            continue
        sid = struct.unpack_from("<H", child[1], 0)[0]
        if sid == COAL:
            child[1][:2] = struct.pack("<H", BLUE)
            replaced += 1
        elif sid == BLUE:
            blues += 1
    return replaced, blues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    raw = MAP.read_bytes()
    root = parse_tree(raw)
    replaced = blues = 0
    log = []
    for area in root[2][0][2]:
        if area[0] != 4:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        if az not in ZS or ax > X1 or ax + 255 < X0 or ay > Y1 or ay + 255 < Y0:
            continue
        for tile in area[2]:
            if tile[0] != T_TILE:
                continue
            p = bytes(tile[1])
            x, y = ax + p[0], ay + p[1]
            if not (X0 <= x <= X1 and Y0 <= y <= Y1):
                continue
            nrep, nblue = replace_in_tile(tile)
            if nrep:
                replaced += nrep
                log.append(f"  ({x}, {y}, {az}): coal bassin -> blue bassin")
            blues += nblue

    print("\n".join(log))
    if not replaced:
        print(f"no quedan coal bassins en el depot ({blues} blue bassins); no se escribe nada")
        return 0
    if a.dry_run:
        print(f"dry-run: {replaced} reemplazos, no se escribió nada")
        return 0
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    print(f"OK: {replaced} blue bassins en el depot ({blues} ya estaban)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
