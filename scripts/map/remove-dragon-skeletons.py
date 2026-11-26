#!/usr/bin/env python3
"""Saca del mapa los dragon skeleton (3125).

El 3125 es una pieza cortada del esqueleto grande de dragón (junto con la cabeza 2247 y la garra
3122): puesta sola en el suelo se ve cortada/mal. En el Valle de las Bestias ya se habían cambiado
por huesos enteros (nov 2026, generate-beast-valley.py); este script las saca de TODO el mapa y los
generadores ya no las colocan (ver docs/items-and-map/MAPAS.md, sección Cuevas).

  python3 scripts/map/remove-dragon-skeletons.py            # dry-run: muestra lo que haría
  python3 scripts/map/remove-dragon-skeletons.py --replace  # escribe test.otbm

Después de correrlo: check-map-load.py, scan-map-depots.py y sync-houses-with-map.py --dry-run
(chequeo de siempre antes de deployar mapa).
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import MAP, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, parse_tree, serialize_tree  # noqa: E402

DRAGON_SKELETON = 3125
ATTR_FLAGS, ATTR_ITEM = 3, 9


def drop_inline(tile) -> int:
    """Saca los 3125 inline (attr 9) de las props del tile. El primer attr 9 es el suelo: no se toca."""
    p = bytes(tile[1])
    head = 2 + (4 if tile[0] == T_HOUSETILE else 0)
    segs, pos, first_item = [], head, True
    while pos < len(p):
        attr = p[pos]
        if attr == ATTR_FLAGS:
            segs.append(p[pos:pos + 5])
            pos += 5
        elif attr == ATTR_ITEM:
            if not first_item and struct.unpack_from("<H", p, pos + 1)[0] == DRAGON_SKELETON:
                pass                                   # se omite
            else:
                segs.append(p[pos:pos + 3])
            first_item = False
            pos += 3
        else:
            segs.append(p[pos:])                       # attr desconocido: se copia tal cual y se corta
            break
    out = p[:head] + b"".join(segs)
    if out == p:
        return 0
    assert len(out) < len(p)
    tile[1] = bytearray(out)
    return 1


def items_in(tile) -> int:
    """Cuántos ítems tiene el tile (inline + hijos): siempre tiene que quedar el suelo."""
    p = bytes(tile[1])
    pos = 2 + (4 if tile[0] == T_HOUSETILE else 0)
    n = 0
    while pos < len(p):
        attr = p[pos]
        if attr == ATTR_FLAGS:
            pos += 5
        elif attr == ATTR_ITEM:
            n += 1
            pos += 3
        else:
            break
    return n + sum(1 for k in tile[2] if k[0] == T_ITEM)


def sweep(root) -> tuple[int, list]:
    """Quita todos los 3125 (nodos hijo + inline). Devuelve (cuántos, [(x, y, z, n), ...])."""
    removed, locs = 0, []
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        for t in area[2]:
            if t[0] not in (T_TILE, T_HOUSETILE):
                continue
            p = bytes(t[1])
            x, y = ax + p[0], ay + p[1]
            n = 0
            keep = []
            for k in t[2]:
                if k[0] == T_ITEM and len(k[1]) >= 2 \
                        and struct.unpack_from("<H", bytes(k[1]), 0)[0] == DRAGON_SKELETON:
                    n += 1
                    continue
                keep.append(k)
            t[2] = keep
            n += drop_inline(t)
            if n:
                assert items_in(t) >= 1, f"el tile {x},{y},{az} quedaría sin ítems"
                removed += n
                locs.append((x, y, az, n))
    return removed, locs


def count_all(root) -> list:
    """[(x, y, z, n), ...] con los 3125 actuales (nodos hijo + inline, sin el suelo)."""
    out = []
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        for t in area[2]:
            if t[0] not in (T_TILE, T_HOUSETILE):
                continue
            p = bytes(t[1])
            x, y = ax + p[0], ay + p[1]
            pos = 2 + (4 if t[0] == T_HOUSETILE else 0)
            first_item, n = True, 0
            while pos < len(p):
                attr = p[pos]
                if attr == ATTR_FLAGS:
                    pos += 5
                elif attr == ATTR_ITEM:
                    if not first_item and struct.unpack_from("<H", p, pos + 1)[0] == DRAGON_SKELETON:
                        n += 1
                    first_item = False
                    pos += 3
                else:
                    break
            for k in t[2]:
                if k[0] == T_ITEM and len(k[1]) >= 2 \
                        and struct.unpack_from("<H", bytes(k[1]), 0)[0] == DRAGON_SKELETON:
                    n += 1
            if n:
                out.append((x, y, az, n))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()

    raw = MAP.read_bytes()
    root = parse_tree(raw)
    found = count_all(root)
    if not found:
        print("No hay dragon skeleton (3125) en el mapa; nada que hacer.")
        return 0
    print(f"{len(found)} casillas con 3125 ({sum(n for *_, n in found)} items):")
    by_z = {}
    for x, y, z, n in found:
        by_z.setdefault(z, []).append(f"{x},{y}")
    for z in sorted(by_z):
        print(f"  z{z}: {' '.join(sorted(by_z[z], key=lambda s: tuple(map(int, s.split(','))))[:12])}"
              f"{' ...' if len(by_z[z]) > 12 else ''}  ({len(by_z[z])})")

    removed, locs = sweep(root)
    assert removed == sum(n for *_, n in found)
    assert not count_all(root), "quedaron 3125 después de la pasada"

    if not a.replace:
        print("dry-run: usá --replace para escribir")
        return 0
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    print(f"OK: {removed} dragon skeleton sacados, {MAP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
