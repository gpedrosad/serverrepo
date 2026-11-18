#!/usr/bin/env python3
"""Mueve el TP de vuelta de la zona de trainers junto a la llegada.

Se entra al training por el TP del depot (127,53,6) y se aparece en la alfombra roja (146,12,7).
El TP de vuelta estaba en el rincón este de la fila de Trainer Monks (158,16,7): a 12+ casillas de
la llegada y ~20 del extremo oeste de la fila. Ahora queda en (145,12,7), la casilla de alfombra
al oeste de la llegada — fuera de los caminos rectos llegada→monk norte (x146) y llegada→fila de
monks (x146), para que nadie pise el TP sin querer al ir a entrenar. El destino no cambia: el TP
de la entrada del depot (128,53,6), junto a los lockers.

  python3 scripts/map/move-trainer-exit-tp.py            # dry-run: muestra lo que haría
  python3 scripts/map/move-trainer-exit-tp.py --replace  # escribe test.otbm

Después: check-map-load.py y validate-tele-dest.py (chequeo de siempre antes de deployar mapa).
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import MAP, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, load_otb, load_tiles, parse_tree, serialize_tree  # noqa: E402

TELEPORT, ATTR_TELE_DEST = 1387, 8
OLD, NEW, DEST = (158, 16, 7), (145, 12, 7), (128, 53, 6)
ARRIVAL = (146, 12, 7)
# caminos rectos desde la llegada que no deben tener un TP encima
PATHS = [(146, 11, 7), (146, 13, 7), ARRIVAL]


def tile_nodes(root) -> dict:
    out = {}
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        for t in area[2]:
            if t[0] in (T_TILE, T_HOUSETILE):
                out[(ax + t[1][0], ay + t[1][1], az)] = t
    return out


def tele_dest(props: bytes):
    pos = 2
    while pos < len(props):
        a = props[pos]
        if a == ATTR_TELE_DEST:
            return struct.unpack_from("<HHB", props, pos + 1)
        if a in (4, 5):
            pos += 3
        elif a == 15:
            pos += 2
        elif a == 6:
            pos += 3 + struct.unpack_from("<H", props, pos + 1)[0]
        else:
            return None
    return None


def find_tp(tile):
    for k in tile[2]:
        if k[0] == T_ITEM and len(k[1]) >= 2 and struct.unpack_from("<H", bytes(k[1]), 0)[0] == TELEPORT:
            return k, tele_dest(bytes(k[1]))
    return None, None


def item_node(iid: int, tele):
    props = bytearray(struct.pack("<H", iid)) + struct.pack("<BHHB", ATTR_TELE_DEST, *tele)
    return [T_ITEM, props, []]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()

    otb = load_otb()
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    tiles = tile_nodes(root)

    errors = []
    for pos in (OLD, NEW, ARRIVAL) + tuple(PATHS):
        if pos not in tiles:
            errors.append(f"{pos}: no existe tile")
    old_k, old_dest = find_tp(tiles[OLD]) if OLD in tiles else (None, None)
    new_k, new_dest = find_tp(tiles[NEW]) if NEW in tiles else (None, None)

    if new_k and old_k is None:
        print(f"Ya movido: el TP está en {NEW} -> {new_dest}. Nada que hacer.")
        return 0 if new_dest == DEST else 1
    if old_k is None:
        print(f"ERROR: no hay TP en {OLD} y tampoco en {NEW}; no se de dónde moverlo.")
        return 1
    if old_dest != DEST:
        errors.append(f"{OLD}: destino inesperado {old_dest} (se esperaba {DEST})")

    # la casilla nueva: piso pisable, sin nada que bloquee, y sin TP en los caminos
    floor = [i for i in load_tiles().get(NEW, ())]
    if not floor:
        errors.append(f"{NEW}: sin items")
    blocking = [otb.get(i, {}).get("name", i) for i in floor if "block_solid" in otb.get(i, {}).get("flags", [])]
    if blocking:
        errors.append(f"{NEW}: bloqueado por {blocking}")
    for pos in PATHS:
        k, _ = find_tp(tiles[pos]) if pos in tiles else (None, None)
        if k:
            errors.append(f"{pos}: hay un TP en el camino de la llegada")

    if errors:
        print("ERROR:\n  " + "\n  ".join(errors))
        return 1

    print(f"saco  el TP de {OLD} -> {old_dest}")
    tiles[OLD][2].remove(old_k)
    print(f"pongo el TP en {NEW} -> {DEST} (alfombra, al oeste de la llegada {ARRIVAL})")
    tiles[NEW][2].append(item_node(TELEPORT, DEST))

    if not a.replace:
        print("dry-run: usá --replace para escribir")
        return 0
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    print(f"OK {MAP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
