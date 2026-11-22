#!/usr/bin/env python3
"""Unifica las paredes eléctricas del depot, ala norte y acceso (z4-z7).

Dry-run por defecto; --apply escribe; --before MAPA valida contra un mapa anterior.
No reconstruye tiles: sustituye solo los u16 de las piezas de ladrillo y conserva
los bytes de lockers/depotid, mostradores, puertas, pisos y cualquier atributo.
"""
from __future__ import annotations

import argparse
from collections import Counter
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE / 'kb'), str(ROOT / 'scripts/client-rme')]
from mapdata import MAP, T_AREA, T_TILE, T_HOUSETILE, T_ITEM, load_otb, parse_tree, serialize_tree
from depot_electric_assets import WALL_ITEMS, WALL_MAP

BOX = (126, 41, 134, 59)
FLOORS = (4, 5, 6, 7)
REVERSE = {new: old for old, new in WALL_MAP.items()}


def inside(x, y, z):
    return BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3] and z in FLOORS


def tiles(root):
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        ax, ay, z = struct.unpack_from('<HHB', area[1])
        for tile in area[2]:
            if tile[0] in (T_TILE, T_HOUSETILE):
                yield (ax + tile[1][0], ay + tile[1][1], z), tile


def item_offsets(tile, otb):
    """(payload mutable, offset del id) para items inline y nodos del tile."""
    p = tile[1]
    pos = 6 if tile[0] == T_HOUSETILE else 2
    while pos < len(p):
        attr = p[pos]
        if attr == 3:
            pos += 5
        elif attr == 9:
            yield p, pos + 1
            sid = struct.unpack_from('<H', p, pos + 1)[0]
            rec = otb.get(sid, {})
            count = 'stackable' in rec.get('flags', []) or rec.get('group') in ('splash', 'fluid')
            pos += 3 + int(count)
        else:
            raise ValueError(f'Atributo de tile desconocido: {attr}')
    for child in tile[2]:
        if child[0] == T_ITEM:
            yield child[1], 0


def transform(root, mapping, otb):
    counts, changed_tiles = Counter(), 0
    for pos, tile in tiles(root):
        changed = False
        for payload, off in item_offsets(tile, otb):
            sid = struct.unpack_from('<H', payload, off)[0]
            if sid in REVERSE and not inside(*pos):
                raise ValueError(f'Pared exclusiva fuera del depot: {sid} en {pos}')
            if inside(*pos) and sid in mapping:
                payload[off:off + 2] = struct.pack('<H', mapping[sid])
                counts[sid] += 1
                changed = True
        changed_tiles += int(changed)
    return counts, changed_tiles


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--map', type=Path, default=MAP)
    ap.add_argument('--before', type=Path)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    raw = args.map.read_bytes()
    root = parse_tree(raw)
    if serialize_tree(root, raw[:4]) != raw:
        raise SystemExit('El mapa no hace round-trip exacto; no se escribe')
    otb = load_otb()
    for item in WALL_ITEMS:
        old, new = otb[item['prototype']], otb[item['server_id']]
        if (old['flags'], old['group']) != (new['flags'], new['group']):
            raise SystemExit(f"Cambió el bloqueo/capa de {item['server_id']}")
    counts, ntiles = transform(root, WALL_MAP, otb)
    result = serialize_tree(root, raw[:4])
    # Revertir solo nuestros IDs debe recuperar el mapa original byte por byte.
    restored = parse_tree(result)
    transform(restored, REVERSE, otb)
    original = args.before.read_bytes() if args.before else raw
    original_tree = parse_tree(original)
    transform(original_tree, REVERSE, otb)
    if serialize_tree(restored, raw[:4]) != serialize_tree(original_tree, original[:4]):
        raise SystemExit('Hay cambios fuera de los IDs de pared permitidos')
    print(f'Depot {BOX}, z{FLOORS}: {sum(counts.values())} piezas en {ntiles} tiles')
    print('Reemplazos:', dict(sorted(counts.items())))
    print('OK: inversión exacta; lockers/atributos y resto del mapa intactos')
    if args.apply and result != raw:
        args.map.write_bytes(result)
        print(f'Aplicado: {args.map}')
    elif not args.apply:
        print('Dry-run: usar --apply para escribir')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
