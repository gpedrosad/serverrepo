"""Torre sureste: escaleras 2×2 separadas y corredor sur libre, z2–7."""
import struct
from portal_citadel_layout import tile_flags

FLOOR, CONDUIT = 20214, 20215
POST, H, V, CORNER, WINDOW_H, WINDOW_V = range(20217,20223)
BEACON, WALL_LIGHT = 20223,20259
STAIRS_UP, STAIRS_DOWN = 20260,20261
RAIL_V, RAIL_H, RAIL_CORNER = 20256,20257,20258
BOUNDS = (165,52,170,56)
LINKS = [((169,54,7),(169,54,6)), ((167,54,6),(167,54,5)),
         ((169,54,5),(169,54,4)), ((167,54,4),(167,54,3)),
         ((169,54,3),(169,54,2))]
UP = {a for a,b in LINKS}
DOWN = {b for a,b in LINKS}
OWNED = {(x,y,z) for z in range(2,8) for y in range(52,57) for x in range(165,171)}
REPLACED = set(range(20214,20224)) | {1385,1386,428,432,STAIRS_UP,STAIRS_DOWN,
    406,407,431,457,920,921,922,923,1025,1026,1027,1028,1029,1030,1031,1032,
    1033,1034,1035,1111,1113,1115,1116,1118,1119,1164,1265,1266,
    RAIL_V,RAIL_H,RAIL_CORNER,WALL_LIGHT}


def item(sid):
    return [6,bytearray(struct.pack('<H',sid)),[]]


def wall(x,y,z,neighbors):
    if x==165 and y==55 and z in (5,6,7):
        return None
    if x==165 and y==52:
        return H if neighbors.get((164,52,z)) else POST
    if z==2:
        if x==170 and y==56:return RAIL_CORNER
        if y in (52,56):return RAIL_H
        if x in (165,170):return RAIL_V
        return None
    if x==165 and y==56:
        return CORNER if neighbors.get((164,56,z)) else V
    if x==170 and y==56:return CORNER
    if y in (52,56):return WINDOW_H if x==167 else H
    if x in (165,170):return WINDOW_V if x==170 and y==54 else V
    return None


def rebuild_tower(root):
    areas,old,neighbors = {},{},{}
    for area in root[2][0][2]:
        if area[0]!=4:continue
        ax,ay,z=struct.unpack_from('<HHB',area[1]);areas.setdefault((ax,ay,z),area)
        kept=[]
        for tile in area[2]:
            pos=(ax+tile[1][0],ay+tile[1][1],z) if tile[0] in (5,14) else None
            if pos and pos[0]==164 and pos[1] in (52,56):
                neighbors[pos]=any(c[0]==6 and struct.unpack_from('<H',c[1])[0]
                                   in (H,WINDOW_H,CORNER) for c in tile[2])
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
        doorway=x==165 and y==55 and z in (5,6,7)
        ground=None if z<7 and (x==165 or y==52) and not doorway else CONDUIT if y==55 else FLOOR
        if pos in DOWN:ground=STAIRS_DOWN
        if ground is not None:props+=struct.pack('<BH',9,ground)
        extras=[]
        if previous:
            for child in previous[2]:
                if child[0]!=6:
                    extras.append(child);continue
                sid=struct.unpack_from('<H',child[1])[0]
                if pos==(165,54,5) and sid==1210:
                    if len(child[1])!=2 or child[2]:
                        raise ValueError('La puerta de la torre tiene atributos; no se retira')
                    continue
                if sid in REPLACED or z==2 and sid in (2721,1491,3738):continue
                extras.append(child)
        sid=wall(x,y,z,neighbors)
        if sid:extras.insert(0,item(sid))
        if pos in UP:extras.append(item(STAIRS_UP))
        if pos==(167,54,2):extras.append(item(BEACON))
        if x==165 and y==53 and 3<=z<=7:
            extras.append(item(WALL_LIGHT))
        key=(x//256*256,y//256*256,z)
        if key not in areas:
            areas[key]=[4,bytearray(struct.pack('<HHB',*key)),[]]
            root[2][0][2].append(areas[key])
        areas[key][2].append([5,props,extras]);added+=int(previous is None)
    return added


def validate_access(root,otb):
    """Rechazar paredes, puertas y huecos en el dibujo 2×2 o en los rellanos."""
    from portal_temple_style import item_offsets
    tiles={}
    for area in root[2][0][2]:
        if area[0]!=4:continue
        ax,ay,z=struct.unpack_from('<HHB',area[1])
        for tile in area[2]:
            if tile[0] in (5,14):
                tiles[ax+tile[1][0],ay+tile[1][1],z]=[
                    struct.unpack_from('<H',p,o)[0] for p,o in item_offsets(tile,otb)]
    def free(pos,allow_up=False):
        ids=tiles.get(pos,[])
        return (any(otb.get(i,{}).get('group')=='ground' for i in ids)
                and not any('block_solid' in otb.get(i,{}).get('flags',[]) for i in ids)
                and not any(i==STAIRS_DOWN or i==STAIRS_UP and not allow_up for i in ids))
    for lower,upper in LINKS:
        x,y,z=lower
        if STAIRS_UP not in tiles[lower] or STAIRS_DOWN not in tiles[upper]:
            raise ValueError(f'Par de escalera incompleto: {lower}, {upper}')
        for dx in (-1,0):
            for dy in (-1,0):
                pos=x+dx,y+dy,z
                if (not free(pos,allow_up=pos==lower) or
                        any(otb.get(i,{}).get('group')!='ground' and
                            not (pos==lower and i==STAIRS_UP) for i in tiles.get(pos,[]))):
                    raise ValueError(f'Escalera 2×2 sobre muro/puerta/hueco: {pos}')
        for pos in ((x,y+1,z),(x,y-1,z-1)):
            if not free(pos):raise ValueError(f'Rellano ocupado: {pos}')
    # El pasillo sur enlaza entrada, ambos pies de escalera y terraza.
    for z in range(2,8):
        for x in range(166,170):
            if not free((x,55,z)):raise ValueError(f'Corredor sur bloqueado: {x,55,z}')
        if z in (5,6,7):
            for x in (164,165):
                if not free((x,55,z)):raise ValueError(f'Acceso oeste bloqueado: {x,55,z}')
        occupied={(x+dx,y+dy,z) for x,y,sz in UP if sz==z
                  for dx in (-1,0) for dy in (-1,0)}
        seen={(166,55,z)};queue=list(seen)
        while queue:
            x,y,_=queue.pop()
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                pos=x+dx,y+dy,z
                if (166<=pos[0]<=169 and 53<=pos[1]<=55 and pos not in seen
                        and pos not in occupied and free(pos)):
                    seen.add(pos);queue.append(pos)
        for lower,upper in LINKS:
            if upper[2]==z and (upper[0],upper[1]-1,z) not in seen:
                raise ValueError(f'Llegada de subida sin salida al corredor: {upper}')
    for y in range(54,59):
        for x in (160,161):
            if not free((x,y,7)):raise ValueError(f'Entrada del templo bloqueada: {x,y,7}')
