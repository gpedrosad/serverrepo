"""Extiende el basalto/cian a la galería y torres originales del templo.

Se llama desde temple-portals.py: conserva tiles/atributos y sustituye solo IDs.
No usa las piezas exclusivas del depot ni modifica sus lockers.
"""
import struct
from collections import Counter

BOX = (151, 43, 170, 56)
FLOORS = range(2, 8)
BASALT, CONDUIT = 20214, 20215
POST, HORIZONTAL, VERTICAL, CORNER, WINDOW_H, WINDOW_V = range(20217, 20223)
WALLS = {
    1025: VERTICAL, 1026: HORIZONTAL, 1027: POST, 1028: HORIZONTAL,
    1029: CORNER, 1030: VERTICAL, 1031: HORIZONTAL, 1032: VERTICAL,
    1033: CORNER, 1034: HORIZONTAL, 1035: CORNER,
    1111: VERTICAL, 1113: POST, 1115: CORNER, 1116: VERTICAL,
    1118: HORIZONTAL, 1119: CORNER, 1164: WINDOW_H,
    1176: HORIZONTAL, 1178: HORIZONTAL, 1192: HORIZONTAL,
    1265: WINDOW_H, 1266: WINDOW_V,
    # Reemplazar los bordes sólidos de los techos por parapetos visibles.
    921: HORIZONTAL, 922: VERTICAL, 923: POST,
}
GROUNDS = {406, 407, 431, 457, 920}


def inside(x, y, z):
    return BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3] and z in FLOORS


def item_offsets(tile, otb):
    props = tile[1]
    offset = 2
    while offset < len(props):
        attr = props[offset]
        if attr == 3:
            offset += 5
        elif attr == 9:
            yield props, offset + 1
            sid = struct.unpack_from('<H', props, offset + 1)[0]
            rec = otb.get(sid, {})
            counted = 'stackable' in rec.get('flags', []) or rec.get('group') in ('splash', 'fluid')
            offset += 3 + int(counted)
        else:
            raise ValueError(f'Atributo de tile inesperado: {attr}')
    for child in tile[2]:
        if child[0] == 6:
            yield child[1], 0


def apply_style(root, otb):
    changes = Counter()
    for area in root[2][0][2]:
        if area[0] != 4:
            continue
        ax, ay, z = struct.unpack_from('<HHB', area[1])
        for tile in area[2]:
            if tile[0] not in (5, 14):
                continue
            x, y = ax + tile[1][0], ay + tile[1][1]
            if not inside(x, y, z):
                continue
            if tile[0] == 14:
                raise ValueError(f'No se remodela una casa: {x},{y},{z}')
            for props, offset in item_offsets(tile, otb):
                sid = struct.unpack_from('<H', props, offset)[0]
                replacement = WALLS.get(sid)
                if sid in GROUNDS:
                    # Un eje luminoso en cada ala; el resto queda oscuro y legible.
                    replacement = CONDUIT if x in (153, 161) or y == 54 else BASALT
                if replacement is not None:
                    struct.pack_into('<H', props, offset, replacement)
                    changes[sid, replacement, z] += 1
    return changes
