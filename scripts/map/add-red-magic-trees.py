#!/usr/bin/env python3
"""Magic trees rojos (20191) junto a los azules del bosque al sur de la ciudad.

Los 7 magic trees azules (2699) están en el pasto del bosque que va del claro de árboles
mágicos (x 69-81, y 92-101) al pantano de la Cripta Imperial. Este script agrega los
rojos en dos lugares libres, y es idempotente:

  - (79, 98, 7): en el claro, entre el azul de (76, 98) y el de (81, 101).
  - (71, 123, 7): al lado del azul aislado de (69, 123), con una columna de por medio.

Ancla = casilla abajo-derecha del 2x2 (igual que los azules): el cliente dibuja sobre
(x-1..x, y-1..y). Solo esa casilla queda bloqueada en el servidor.

Requisito por casilla ancla: pasto (4756) y sin ningún otro ítem (evita apilar el árbol
encima de un willow o un peach). Si un futuro cambio de mapa rompe eso, el script falla
con el mensaje en vez de escribir.

Uso: python3 scripts/map/add-red-magic-trees.py [--dry-run]
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import MAP, T_ITEM, T_TILE, parse_tree, serialize_tree  # noqa: E402

Z = 7
RED_TREE = 20191
GRASS = 4756
SPOTS = [(79, 98), (71, 123)]


def tile_items(tile) -> list[int]:
    """Server ids del tile: ítems inline (attr 9) + nodos hijos (T_ITEM)."""
    p = bytes(tile[1])
    items, pos = [], 2
    while pos < len(p):
        if p[pos] == 3:
            pos += 5
        elif p[pos] == 9:
            items.append(struct.unpack_from("<H", p, pos + 1)[0])
            pos += 4
        else:
            break
    for child in tile[2]:
        if child[0] == T_ITEM and len(child[1]) >= 2:
            items.append(struct.unpack_from("<H", bytes(child[1]), 0)[0])
    return items


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    raw = MAP.read_bytes()
    root = parse_tree(raw)
    targets = {(x, y): None for x, y in SPOTS}
    for area in root[2][0][2]:
        if area[0] != 4:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        if az != Z:
            continue
        for tile in area[2]:
            if tile[0] != T_TILE:
                continue
            p = bytes(tile[1])
            pos = (ax + p[0], ay + p[1])
            if pos in targets:
                targets[pos] = tile

    log, changed, failed = [], 0, 0
    for (x, y), tile in targets.items():
        where = f"({x}, {y}, {Z})"
        if tile is None:
            log.append(f"  {where}: ERROR no hay tile")
            failed += 1
            continue
        items = tile_items(tile)
        if RED_TREE in items:
            log.append(f"  {where}: ya está el magic tree rojo")
            continue
        if items != [GRASS]:
            log.append(f"  {where}: ERROR el tile no es pasto limpio ({items}); no se escribe")
            failed += 1
            continue
        tile[2].append([T_ITEM, bytearray(struct.pack("<H", RED_TREE)), []])
        changed += 1
        log.append(f"  {where}: magic tree rojo (dibuja sobre {x - 1}-{x}, {y - 1}-{y})")

    print("\n".join(log))
    if failed:
        print(f"{failed} casillas inválidas: no se escribe nada")
        return 1
    if not changed:
        print("ya estaban los dos; no se escribe nada")
        return 0
    if a.dry_run:
        print("dry-run: no se escribió nada")
        return 0
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    print(f"OK: {changed} magic trees rojos en test.otbm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
