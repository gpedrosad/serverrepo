"""Geometría decorativa de la plaza; temple-portals.py sigue siendo su único dueño.

Dos torres nuevas al norte. La galería/torres antiguas del templo al sur no se pisan.
Los portales de PORTALS van en su (x, y); y=47 por defecto (los originales conservan coordenadas).
La fila y=47 se llenó: los nuevos van en la fila espejo y=51 (cartel y=50, llegada y=52).
El pasillo cian (x=160-162) y las filas y=43/y=49 no. No requiere C++.
"""
from __future__ import annotations

import struct

FLOOR, CONDUIT, DAIS = 20214, 20215, 20216
POST, HORIZONTAL, VERTICAL, CORNER, WINDOW_H, WINDOW_V = range(20217,20223)
BEACON, OBELISK = 20223,20224
CUSTOM = set(range(FLOOR,OBELISK+1))
TOWERS = ((155,42),(167,42))
TOWER_BASE = {(x+dx,y+dy) for x,y in TOWERS for dx in range(3) for dy in range(3)}


def tower_cell(dx,dy,roof=False):
    if dx==dy==1:
        return [FLOOR,[BEACON] if roof else [],None]
    if dx==dy==0:wall=POST
    elif dx==dy==2:wall=CORNER
    elif dy==0:wall=HORIZONTAL
    elif dx==0:wall=VERTICAL
    elif dy==2:wall=WINDOW_H if dx==1 else HORIZONTAL
    else:wall=WINDOW_V if dy==1 else VERTICAL
    # Norte/oeste están fuera de la línea de pared; arriba no llevan suelo.
    return [None if dx==0 or dy==0 else FLOOR,[wall],None]


def plaza_plan(portals):
    spec={}
    for x in range(155,170):
        for y in range(43,53):
            path=x in (160,161,162) or y==49 or y==43
            spec[x,y]=[CONDUIT if path else FLOOR,[],None]
    for _key,x,py,dest,_text,_zones in portals:
        spec[x,py]=[DAIS,[],dest]
        spec[x,py-1]=[CONDUIT,[1429],None]
        spec[x,py+1]=[DAIS,[],None]
    for x,y in TOWERS:
        for dy in range(3):
            for dx in range(3):
                ground,items,tele=tower_cell(dx,dy)
                spec[x+dx,y+dy]=[ground or FLOOR,items,tele]
    for x,y in ((157,51),(168,51)):spec[x,y][1].append(BEACON)
    for x,y in ((155,50),(169,50)):spec[x,y][1].append(OBELISK)
    return spec


def upper_plan():
    return {(x+dx,y+dy,z):tower_cell(dx,dy,roof=z==4)
            for x,y in TOWERS for z in (4,5,6) for dy in range(3) for dx in range(3)}


def tile_flags(props):
    """Conservar flags de la casilla original (PZ/training/etc.), sin inventarlos."""
    pos,out=2,b''
    while pos<len(props):
        attr=props[pos];pos+=1
        if attr==3:out+=bytes([3])+props[pos:pos+4];pos+=4
        elif attr==9:pos+=2
        else:raise ValueError(f'Atributo de casilla inesperado: {attr}')
    return out


def install_upper(root,item_node):
    plan=upper_plan();areas={};existing={}
    data=root[2][0][2]
    for area in data:
        if area[0]!=4:continue
        ax,ay,z=struct.unpack_from('<HHB',area[1])
        areas.setdefault((ax,ay,z),area)
        for tile in area[2]:
            if tile[0] in (5,14):existing[ax+tile[1][0],ay+tile[1][1],z]=(area,tile)
    added=0
    for (x,y,z),(ground,items,_tele) in sorted(plan.items()):
        old=existing.get((x,y,z))
        if old:
            area,tile=old
            ids=[struct.unpack_from('<H',ch[1])[0] for ch in tile[2] if ch[0]==6]
            props=bytes(tile[1]);p=2
            while p<len(props):
                attr=props[p];p+=1
                if attr==9:ids.append(struct.unpack_from('<H',props,p)[0]);p+=2
                elif attr==3:p+=4
                else:raise ValueError(f'Casilla ocupada en {x,y,z}')
            if tile[0]!=5 or any(i not in CUSTOM for i in ids):
                raise ValueError(f'La torre pisa una construcción existente en {x,y,z}: {ids}')
        else:
            key=(x//256*256,y//256*256,z)
            if key not in areas:
                areas[key]=[4,bytearray(struct.pack('<HHB',*key)),[]];data.append(areas[key])
            area=areas[key];tile=[5,bytearray(),[]];area[2].append(tile);added+=1
        tile[1]=bytearray([x%256,y%256])
        if ground is not None:tile[1]+=struct.pack('<BH',9,ground)
        tile[2]=[item_node(i) for i in items]
    return added
