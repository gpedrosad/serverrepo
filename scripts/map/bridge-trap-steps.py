#!/usr/bin/env python3
"""Puente de madera de la ciudad (z6, x 139-144, y 57-76) rehecho con barandas propias y dos tramos de 1 sqm
para trapear (22 nov 2026).

Antes: tablas 405 de 3 de ancho (x 140-142) con la baranda 1518 en casillas bloqueadas a los costados (x 139
y 143) y caras 437/435 en x 144 y y 76. La baranda nativa se dibuja en el borde oeste de su casilla, así que
el puente a la vista no coincidía con el caminable y al angostarlo quedaba feo.

Ahora: solo existen las tablas que se pisan (405, y las trampillas 429 que ya estaban). Cada tabla lleva la
baranda propia (make_bridge_rails.py, server 20480-20488, no bloquea) en los lados que dan al agua y al
costado no hay casilla: se ve el río de z7. En y 62-65 y 68-71 el puente es de una tabla (x 141).

  python3.11 scripts/map/bridge-trap-steps.py --dry-run [--png /tmp/puente.png]
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
sys.path[:0] = [str(HERE), str(HERE / "kb"), str(HERE.parent / "client-rme")]
from mapdata import MAP, REPO, load_otb, parse_tree, serialize_tree
from epstein_cave_repair import index
from make_bridge_rails import SERVER_BASE as OLD_RAIL_BASE
import city_bridge_z6_art as ART

Z = 6
BOX = (138, 56, 144, 77)                                       # tablero + casillas de aire con baranda
WOOD, TRAPDOOR = 405, 429
TRAPDOORS = {(141, 59), (142, 59), (141, 74), (142, 74)}      # bajan a las escaleras 1385 de z7
PILLAR = 1277                                                  # postes del puente, en el río (z7)
PILLAR_MOVES = {(143, 65): (141, 65), (143, 69): (141, 69), (143, 72): (142, 72), (143, 75): (142, 75)}
NARROW = [(62, 65), (68, 71)]                                  # tramos de 1 sqm (x 141)
DECK = ({(x, y) for x in (140, 141, 142) for y in range(57, 76)
         if not any(a <= y <= b for a, b in NARROW)}
        | {(141, y) for a, b in NARROW for y in range(a, b + 1)})


def wanted():
    """Tablero: solo tablas 405 (y trampillas 429). Alrededor, casillas de aire sin suelo con la pieza de
    baranda 3D (city_bridge_z6_art.py); el resto de la caja, sin casilla (se ve el río de z7)."""
    rails = ART.placements()
    assert set(DECK) == set(ART.DECK), "El tablero de acá y el del arte no coinciden"
    out = {}
    for x in range(BOX[0], BOX[2] + 1):
        for y in range(BOX[1], BOX[3] + 1):
            if (x, y) in DECK:
                out[(x, y)] = [TRAPDOOR if (x, y) in TRAPDOORS else WOOD]
            elif (x, y) in rails:
                out[(x, y)] = [rails[(x, y)]]
            else:
                out[(x, y)] = None
    assert set(rails) <= set(out), "Hay barandas fuera de la caja"
    return out


ALLOWED = ({WOOD, TRAPDOOR, 434, 435, 436, 437, 442, 443, 444, 445, 1516, 1518}
           | set(range(OLD_RAIL_BASE, OLD_RAIL_BASE + 9)) | set(range(ART.SERVER_BASE, ART.SERVER_BASE + 40)))


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
    for (x, y), ids in want.items():
        old = values.get((x, y, Z))
        # solo piezas del puente (originales, de las versiones anteriores o de esta)
        assert old is None or set(old) <= ALLOWED, f"Casilla ajena en {x},{y},{Z}: {old}"
        assert len(nodes.get((x, y, Z), [])) <= 1
        changed += old != ids
    pillar_todo = []
    for a, b in PILLAR_MOVES.items():
        ia, ib = values.get((*a, 7), []), values.get((*b, 7), [])
        if PILLAR in ia and PILLAR not in ib:
            pillar_todo.append((a, b))
        else:
            assert PILLAR not in ia and PILLAR in ib, f"Postes inesperados en {a}/{b}: {ia} {ib}"
    changed += len(pillar_todo)
    for iid in {i for ids in want.values() if ids for i in ids}:
        assert iid in otb, f"Falta el ítem {iid} en el OTB (correr add_custom_items.py)"
    print(f"casillas a cambiar: {changed}")
    if args.dry_run or not changed:
        return

    backup = REPO / "backups/map" / ("bridge-trap-steps-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    shutil.copy2(MAP, backup / MAP.name)
    for (x, y), ids in want.items():
        key = x // 256 * 256, y // 256 * 256, Z
        tile = nodes[(x, y, Z)][0] if (x, y, Z) in nodes else None
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
    for a, b in pillar_todo:                   # postes: debajo de los bordes nuevos
        src, dst = nodes[(*a, 7)][0], nodes[(*b, 7)][0]
        node = next(n for n in src[2] if n[0] == 6 and struct.unpack_from("<H", n[1])[0] == PILLAR)
        src[2].remove(node)
        dst[2].append(node)
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    print("escrito")


if __name__ == "__main__":
    main()
