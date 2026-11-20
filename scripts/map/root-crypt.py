#!/usr/bin/env python3
"""Visual exclusiva de la casa BoH al sur del depot, sin mover salas/teleports/cofres."""
import argparse
import struct
import sys
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE/'kb')]
from mapdata import MAP,load_otb,parse_tree,serialize_tree
from portal_temple_style import item_offsets

BOUNDS=(127,61,136,66)
WALLS={1038:20264,1039:20265,1041:20270,1043:20266,1044:20267,1263:20268,1264:20269}
PARTITIONS={7:{130,132,134},6:{130,133}}
LAMPS={(130,61,7),(127,64,7),(133,61,7),(129,61,6),(132,61,6),(135,61,6)}


def inside(pos):
    x,y,z=pos
    return 127<=x<=136 and 61<=y<=66 and z in (6,7)


def apply(root,otb):
    changes=Counter()
    for area in root[2][0][2]:
        if area[0]!=4:continue
        ax,ay,z=struct.unpack_from('<HHB',area[1])
        for tile in area[2]:
            if tile[0] not in (5,14):continue
            pos=ax+tile[1][0],ay+tile[1][1],z
            if not inside(pos):continue
            if tile[0]==14:raise ValueError(f'La cripta invade una casa: {pos}')
            x,y,_=pos
            portal=any(c[0]==6 and struct.unpack_from('<H',c[1])[0]==1387 for c in tile[2])
            for props,offset in item_offsets(tile,otb):
                sid=struct.unpack_from('<H',props,offset)[0]
                new=WALLS.get(sid,sid)
                if sid in (405,20262,20263) or pos==(132,66,7) and sid==4756:
                    new=20263 if portal else 20262
                if sid in (1043,20266) and x in PARTITIONS[z] and 62<=y<=65:new=20270
                if sid in (2059,2061):new=20271
                if pos==(136,62,7) and sid==1245:new=20272
                if new!=sid:
                    struct.pack_into('<H',props,offset,new);changes[sid,new]+=1
            # Decoración fija vieja, sin attrs de quest; no tocar cofres ni puerta.
            tile[2]=[c for c in tile[2] if not (c[0]==6 and len(c[1])==2 and not c[2]
                       and struct.unpack_from('<H',c[1])[0] in (1868,1903,2024))]
            if pos in LAMPS and not any(c[0]==6 and struct.unpack_from('<H',c[1])[0]==20271 for c in tile[2]):
                tile[2].append([6,bytearray(struct.pack('<H',20271)),[]]);changes[0,20271]+=1
    return changes


def validate(before,after,otb):
    def tiles(tree):
        out={}
        for a in tree[2][0][2]:
            if a[0]!=4:continue
            ax,ay,z=struct.unpack_from('<HHB',a[1])
            for n in a[2]:
                if n[0] in (5,14):out.setdefault((ax+n[1][0],ay+n[1][1],z),[]).append(n)
        return out
    old,new=tiles(before),tiles(after)
    if old.keys()!=new.keys():raise ValueError('Cambió la huella del mapa')
    count=0
    def protected(nodes):
        return [bytes(c[1]) for n in nodes for c in n[2] if c[0]==6
                and struct.unpack_from('<H',c[1])[0] in (1387,1740)]
    def collision(n):
        flags=set();ground=False
        for p,o in item_offsets(n,otb):
            e=otb.get(struct.unpack_from('<H',p,o)[0],{})
            ground|=e.get('group')=='ground'
            flags.update(f for f in e.get('flags',[]) if f.startswith('block_') or f.startswith('floorchange_'))
        return ground,flags
    for pos,nodes in old.items():
        a=[serialize_tree(n,b'') for n in nodes];b=[serialize_tree(n,b'') for n in new[pos]]
        if a==b:continue
        if not inside(pos):raise ValueError(f'Cambio fuera de la quest: {pos}')
        if len(nodes)!=1 or len(new[pos])!=1:raise ValueError(f'Tile duplicado: {pos}')
        if collision(nodes[0])!=collision(new[pos][0]):raise ValueError(f'Cambió la colisión: {pos}')
        if protected(nodes)!=protected(new[pos]):raise ValueError(f'Cofre/teleport modificado: {pos}')
        count+=1
    def gate_attrs(nodes):
        return [bytes(c[1][2:]) for n in nodes for c in n[2] if c[0]==6
                and struct.unpack_from('<H',c[1])[0] in (1245,20272)]
    if gate_attrs(old[136,62,7])!=gate_attrs(new[136,62,7]):raise ValueError('Cambió el nivel de la puerta')
    return count


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--dry-run',action='store_true');args=ap.parse_args()
    raw=MAP.read_bytes();tree=parse_tree(raw);otb=load_otb();counts=apply(tree,otb)
    changed=validate(parse_tree(raw),tree,otb)
    print(f'Cripta de Raíces: {sum(counts.values())} sustituciones/adiciones en dos pisos')
    print(f'{changed} tiles modificados; huella, colisiones, cofres, puerta y teleports preservados')
    if not args.dry_run:MAP.write_bytes(serialize_tree(tree,raw[:4]))


if __name__=='__main__':main()
