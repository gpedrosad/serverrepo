"""Torre sureste con base y cinco tramos de escalera; ámbito 165–169,52–56,z2–7."""
import struct
from portal_citadel_layout import tile_flags

FLOOR, CONDUIT = 20214, 20215
POST, H, V, CORNER, WINDOW_H, WINDOW_V = range(20217,20223)
BEACON, WALL_LIGHT = 20223,20259
STAIRS_UP, STAIRS_DOWN = 20260,20261
RAIL_V, RAIL_H, RAIL_CORNER = 20256,20257,20258
BOUNDS = (165,52,169,56)
LINKS = [((168,54,7),(168,54,6)), ((166,54,6),(166,54,5)),
         ((168,54,5),(168,54,4)), ((166,54,4),(166,54,3)),
         ((168,54,3),(168,54,2))]
UP = {a for a,b in LINKS}
DOWN = {b for a,b in LINKS}
OWNED = {(x,y,z) for z in range(2,8) for y in range(52,57) for x in range(165,170)}
REPLACED = set(range(20214,20224)) | {1385,1386,428,432,STAIRS_UP,STAIRS_DOWN,
    406,407,431,457,920,921,922,923,1025,1026,1027,1028,1029,1030,1031,1032,
    1033,1034,1035,1111,1113,1115,1116,1118,1119,1164,1265,1266,RAIL_V,RAIL_H,RAIL_CORNER}


def item(sid):
    return [6,bytearray(struct.pack('<H',sid)),[]]


def wall(x,y,z):
    if x==165 and y==54 and z in (5,6,7):
        return None
    if x==165 and y==52:
        return POST
    if z==2:
        if x==169 and y==56:return RAIL_CORNER
        if y in (52,56):return RAIL_H
        if x in (165,169):return RAIL_V
        return None
    if x==169 and y==56:return CORNER
    if y in (52,56):return WINDOW_H if x==167 else H
    if x in (165,169):return WINDOW_V if x==169 and y==54 else V
    return None


def rebuild_tower(root):
    areas,old = {},{}
    for area in root[2][0][2]:
        if area[0]!=4:continue
        ax,ay,z=struct.unpack_from('<HHB',area[1]);areas.setdefault((ax,ay,z),area)
        kept=[]
        for tile in area[2]:
            pos=(ax+tile[1][0],ay+tile[1][1],z) if tile[0] in (5,14) else None
            if pos in OWNED:
                if tile[0]==14:raise ValueError(f'La torre invade una casa: {pos}')
                if pos in old:raise ValueError(f'Casilla duplicada en torre: {pos}')
                old[pos]=tile
            else:kept.append(tile)
        area[2]=kept
    added=0
    for x,y,z in sorted(OWNED,key=lambda p:(p[2],p[1],p[0])):
        pos=(x,y,z);previous=old.get(pos)
        flag_source=previous or old.get((167,54,z))
        flags=tile_flags(flag_source[1]) if flag_source else b''
        props=bytearray([x%256,y%256])+flags
        doorway=x==165 and y==54 and z in (5,6,7)
        ground=None if z<7 and (x==165 or y==52) and not doorway else CONDUIT if y==54 else FLOOR
        if pos in DOWN:ground=STAIRS_DOWN
        if ground is not None:props+=struct.pack('<BH',9,ground)
        extras=[]
        if previous:
            for child in previous[2]:
                if child[0]!=6:
                    extras.append(child);continue
                sid=struct.unpack_from('<H',child[1])[0]
                if sid in REPLACED or z==2 and sid in (2721,1491,3738):continue
                extras.append(child)
        sid=wall(x,y,z)
        if sid:extras.insert(0,item(sid))
        if pos in UP:extras.append(item(STAIRS_UP))
        if pos==(167,54,2):extras.append(item(BEACON))
        if pos==(165,55,7) and not any(c[0]==6 and struct.unpack_from('<H',c[1])[0]==WALL_LIGHT for c in extras):
            extras.append(item(WALL_LIGHT))
        key=(x//256*256,y//256*256,z)
        if key not in areas:
            areas[key]=[4,bytearray(struct.pack('<HHB',*key)),[]]
            root[2][0][2].append(areas[key])
        areas[key][2].append([5,props,extras]);added+=int(previous is None)
    return added
