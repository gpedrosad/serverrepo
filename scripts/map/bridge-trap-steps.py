#!/usr/bin/env python3
"""Puente de madera de z6 sobre el río (x 139-144, y 57-76): dos tramos de 1 sqm para trapear (22 nov 2026).

El puente es de 3 de ancho (x 140-142) con baranda 1518 a los costados y trampillas 429 en las dos
puntas. En y 62-65 y 68-71 se angosta a una tabla (x 141), con las mismas piezas de madera, corridas una
casilla hacia adentro:

  ancho      139 [436 1518] 140 [405] 141 [405] 142 [405] 143 [405 1518] 144 [437]
  angosto    139 -          140 [436 1518] 141 [405] 142 [405 1518] 143 [437] 144 -
  primera y última fila del tramo angosto: 139 [445] / 144 [444] y 139 [442] / 144 [443] (esquinas)

A los costados de la tabla no hay casilla en z6: se ve el río de z7. Valida que el puente esté como antes
(o ya cambiado) y es idempotente.

  python3.11 scripts/map/bridge-trap-steps.py --dry-run
  python3.11 scripts/map/bridge-trap-steps.py
"""
from __future__ import annotations

import argparse
import shutil
import struct
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "kb")]
from mapdata import MAP, REPO, load_otb, parse_tree, serialize_tree
from epstein_cave_repair import index

Z = 6
XS = range(139, 145)
WIDE = [[436, 1518], [405], [405], [405], [405, 1518], [437]]
NARROW = [None, [436, 1518], [405], [405, 1518], [437], None]
FIRST = [[445], [436, 1518], [405], [405, 1518], [437], [444]]     # entra al tramo angosto
LAST = [[442], [436, 1518], [405], [405, 1518], [437], [443]]      # sale del tramo angosto
SEGMENTS = ((62, 65), (68, 71))


def wanted():
    out = {}
    for y0, y1 in SEGMENTS:
        for y in range(y0, y1 + 1):
            row = FIRST if y == y0 else LAST if y == y1 else NARROW
            for x, ids in zip(XS, row):
                out[(x, y, Z)] = ids
    return out


def item_node(iid):
    return [6, bytearray(struct.pack("<H", iid)), []]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = MAP.read_bytes()
    root = parse_tree(raw)
    otb = load_otb()
    nodes, values, areas = index(root, otb)
    want = wanted()
    changed = 0
    for (x, y, z), ids in want.items():
        old = values.get((x, y, z))
        orig = WIDE[x - XS.start]
        assert old in (orig, ids), f"El puente cambió en {x},{y},{z}: {old}"
        assert len(nodes.get((x, y, z), [])) <= 1
        if old != ids:
            changed += 1
    print(f"casillas a cambiar: {changed}")
    if args.dry_run or not changed:
        return

    backup = REPO / "backups/map" / ("bridge-trap-steps-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    shutil.copy2(MAP, backup / MAP.name)
    for (x, y, z), ids in want.items():
        key = x // 256 * 256, y // 256 * 256, z
        tile = nodes[(x, y, z)][0] if (x, y, z) in nodes else None
        if ids is None:
            if tile is not None:
                parent = next(a for a in root[2][0][2] if a[0] == 4 and any(t is tile for t in a[2]))
                parent[2][:] = [t for t in parent[2] if t is not tile]
            continue
        if tile is None:
            tile = [5, bytearray([x % 256, y % 256]), []]
            areas[key][2].append(tile)
        ground = otb[ids[0]]["group"] == "ground"
        tile[1] = bytearray([x % 256, y % 256]) + (struct.pack("<BH", 9, ids[0]) if ground else b"")
        tile[2] = [item_node(i) for i in ids[1 if ground else 0:]]
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    print("escrito")


if __name__ == "__main__":
    main()
