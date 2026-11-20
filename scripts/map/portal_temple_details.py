"""Entrada, iluminación y cerramiento exclusivos del templo de teleports."""
import struct
from collections import Counter
from portal_temple_style import item_offsets

ENTRANCE_LEFT, ENTRANCE_RIGHT = 20253, 20254
LANTERN, RAIL_V, RAIL_H, RAIL_CORNER, WALL_LIGHT = range(20255, 20260)
KEEP_DETAILS = {LANTERN, RAIL_V, RAIL_H, RAIL_CORNER}
REPLACEMENTS = {1120: ENTRANCE_LEFT, 1121: ENTRANCE_RIGHT, 1480: LANTERN,
                1543: RAIL_V, 1544: RAIL_H, 1545: RAIL_CORNER, 2038: WALL_LIGHT}
ENTRY_PAD = {(x,y,7) for x in (160,161) for y in (56,57,58)} | {(159,56,7),(162,56,7)}
FRONT_LIGHTS = {(159,57,7), (162,57,7)}


def inside(x,y,z):
    return 151 <= x <= 170 and 42 <= y <= 56 and 2 <= z <= 7


def apply_details(root,otb):
    counts = Counter()
    for area in root[2][0][2]:
        if area[0] != 4:
            continue
        ax,ay,z = struct.unpack_from('<HHB',area[1])
        for tile in area[2]:
            if tile[0] not in (5,14):
                continue
            pos = (ax+tile[1][0],ay+tile[1][1],z)
            if not inside(*pos) and pos not in ENTRY_PAD|FRONT_LIGHTS:
                continue
            if tile[0] == 14:
                raise ValueError(f'El detalle del templo invade una casa: {pos}')
            for props,offset in item_offsets(tile,otb):
                sid = struct.unpack_from('<H',props,offset)[0]
                replacement = REPLACEMENTS.get(sid)
                if pos in ENTRY_PAD and otb.get(sid,{}).get('group') == 'ground':
                    replacement = 20214 if pos[0] in (159,162) else 20215 if pos[1] == 57 else 20216
                if replacement is not None and sid != replacement:
                    struct.pack_into('<H',props,offset,replacement)
                    counts[sid,replacement] += 1
            if pos in ENTRY_PAD:
                # El borde de pasto del pavimento anterior taparía el umbral rúnico.
                tile[2] = [ch for ch in tile[2] if not (ch[0] == 6 and
                           struct.unpack_from('<H',ch[1])[0] == 4542)]
            if pos in FRONT_LIGHTS and not any(ch[0] == 6 and
                    struct.unpack_from('<H',ch[1])[0] == LANTERN for ch in tile[2]):
                tile[2].append([6,bytearray(struct.pack('<H',LANTERN)),[]])
                counts[0,LANTERN] += 1
    return counts
