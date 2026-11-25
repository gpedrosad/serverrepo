#!/usr/bin/env python3
"""Saca todos los dead tree 2715 del mapa test.otbm (24 nov 2026).

Gonzalo señaló en el juego (24/11/2026, 19:57 hora de Buenos Aires):
    You see a dead tree. Id: 2715. Pos: 88 244 7. Tile: 4756 2715

Solo se saca el item 2715; el suelo y el resto de los items de la casilla quedan.
Las casillas que tengan atributos (depot, tele, count, texto, action/unique id) o que
sean house tiles se reportan como excepción y NO se tocan.

    python3.11 scripts/map/remove-dead-tree-2715.py             # inventario (dry-run)
    python3.11 scripts/map/remove-dead-tree-2715.py --replace   # escribe test.otbm

Doc: docs/items-and-map/REMOVE_DEAD_TREE_2715_2026_11_24.md.
Mismo método que la pasada de los dead tree 2716
(scripts/map/fix-city-visual-20261124.py, commit bb7817f): index de tiles con
mapdata.py, tile_is_simple + drop_ids, y verificación de que no queda ninguno.
"""
from __future__ import annotations

import argparse
import struct
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import (  # noqa: E402
    MAP, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, load_otb, parse_tree, serialize_tree,
)

ATTR_FLAGS, ATTR_ITEM = 3, 9
DEAD_TREE = 2715


def tile_xy(area, tile) -> tuple[int, int, int]:
    ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
    p = bytes(tile[1])
    return ax + p[0], ay + p[1], az


def items_of(tile) -> list[int]:
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


def tile_is_simple(tile) -> bool:
    """True si solo tiene flags e ítems de 2 bytes (sin depot/tele/count/texto)."""
    if tile[0] == T_HOUSETILE:
        return False
    p = bytes(tile[1])
    pos = 2
    while pos < len(p):
        attr = p[pos]
        if attr == ATTR_FLAGS:
            pos += 5
        elif attr == ATTR_ITEM:
            pos += 3
        else:
            return False
    for k in tile[2]:
        if k[0] == T_ITEM and len(k[1]) != 2:
            return False
    return True


def drop_ids(tile, drop: set[int]) -> int:
    """Saca de la casilla todas las apariciones de los ids en `drop` (nunca el suelo)."""
    p = bytes(tile[1])
    head = 2
    segs, pos, first, n = [], head, True, 0
    while pos < len(p):
        attr = p[pos]
        if attr == ATTR_FLAGS:
            segs.append(p[pos:pos + 5])
            pos += 5
        elif attr == ATTR_ITEM:
            iid = struct.unpack_from("<H", p, pos + 1)[0]
            if not first and iid in drop:
                n += 1
            else:
                segs.append(p[pos:pos + 3])
            first = False
            pos += 3
        else:
            segs.append(p[pos:])
            break
    out = p[:head] + b"".join(segs)
    if out != p:
        tile[1] = bytearray(out)
    keep = []
    for k in tile[2]:
        if k[0] == T_ITEM and len(k[1]) >= 2 \
                and struct.unpack_from("<H", bytes(k[1]), 0)[0] in drop:
            n += 1
            continue
        keep.append(k)
    tile[2] = keep
    return n


def index_nodes(root):
    out = {}
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        for tile in area[2]:
            if tile[0] not in (T_TILE, T_HOUSETILE):
                continue
            out[tile_xy(area, tile)] = tile
    return out


def find_dead_trees(root, otb) -> tuple[list, list]:
    """(para borrar, excepciones): posiciones con 2715 en casillas simples o no."""
    hits, skipped = [], []
    for pos, tile in sorted(index_nodes(root).items()):
        ids = items_of(tile)
        if DEAD_TREE not in ids:
            continue
        ground = ids[0]
        gname = (otb.get(ground) or {}).get("name", ground)
        if not tile_is_simple(tile):
            skipped.append((pos, ids, gname, "casa o atributos en la casilla"))
            continue
        hits.append((pos, ids, gname))
    return hits, skipped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replace", action="store_true", help="escribe test.otbm")
    args = ap.parse_args()

    otb = load_otb()
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    hits, skipped = find_dead_trees(root, otb)

    print(f"Inventario de dead tree {DEAD_TREE} en {MAP.name}:")
    print(f"  tiles con {DEAD_TREE}: {len(hits)}  ({sum(i.count(DEAD_TREE) for _, i, _ in hits)} apariciones)")
    print(f"  excepciones (no se tocan): {len(skipped)}")
    print(f"  por piso: " + ", ".join(f"z{z}: {n}" for z, n in sorted(Counter(p[2] for p, _, _ in hits).items())))
    for pos, ids, gname in skipped:
        print(f"  EXCEPCIÓN {pos}: {ids} ({gname})")
    if not args.replace:
        for pos, ids, gname in hits:
            print(f"  {pos}: {ids} (suelo {gname})")
        print("dry-run: usá --replace para escribir")
        return 0

    removed = 0
    log = []
    nodes = index_nodes(root)
    for pos, ids, gname in hits:
        tile = nodes[pos]
        n = drop_ids(tile, {DEAD_TREE})
        after = items_of(tile)
        if DEAD_TREE in after or not after:
            raise SystemExit(f"ERROR: al sacar {DEAD_TREE} de {pos} quedó {after}")
        removed += n
        log.append(f"  {pos}: {ids} -> {after}")
    if removed != sum(i.count(DEAD_TREE) for _, i, _ in hits):
        raise SystemExit("ERROR: el conteo de apariciones no coincide")
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    # verificación: releer el archivo escrito
    after_root = parse_tree(MAP.read_bytes())
    hits2, skipped2 = find_dead_trees(after_root, otb)
    print("Cambios:")
    print("\n".join(log))
    print(f"{removed} × {DEAD_TREE} sacados")
    print(f"quedan en el mapa: {len(hits2)} tiles con {DEAD_TREE} "
          f"({sum(i.count(DEAD_TREE) for _, i, _ in hits2)} apariciones); "
          f"excepciones conservadas: {len(skipped2)}")
    if hits2:
        for pos, ids, gname in hits2:
            print(f"  QUEDA {pos}: {ids}")
        if len(hits2) > len(skipped):
            return 1
    print(f"OK: escrito {MAP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
