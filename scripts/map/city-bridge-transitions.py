#!/usr/bin/env python3
"""Remates discretos del muelle junto al depot y pasos a elfos/minotauros."""
import argparse
import struct
import sys
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE/'kb')]
from mapdata import MAP,load_otb,parse_tree,serialize_tree
from portal_temple_style import item_offsets

WOOD,STONE,LAMP=405,431,3744
STONE_PADS=({(x,y,7) for x in (123,124,125) for y in (59,60,61)}
            |{(x,56,7) for x in (113,114)}
            |{(x,y,7) for x in (113,114) for y in (60,61)}
            |{(112,60,6),(111,61,6),(112,61,6)})
RAILS=({(x,58,7):1516 for x in range(115,122)}
       |{(x,62,7):1517 for x in range(115,125)}
       |{(112,y,7):1518 for y in (56,57,58)}
       |{(115,y,7):1519 for y in (56,57)})
LAMPS={(112,56,7),(115,58,7),(121,58,7),(123,62,7)}
CLEAN_BORDER={(119,58,7):434,(121,58,7):434,(114,62,7):435,(116,62,7):435,
              (117,62,7):435,(123,62,7):435}
SCOPE=STONE_PADS|set(RAILS)|LAMPS|set(CLEAN_BORDER)


def ids(tile,otb):
    return [struct.unpack_from('<H',p,o)[0] for p,o in item_offsets(tile,otb)]


def tiles(root):
    out={}
    for area in root[2][0][2]:
        if area[0]!=4:continue
        ax,ay,z=struct.unpack_from('<HHB',area[1])
        for tile in area[2]:
            if tile[0] in (5,14):out.setdefault((ax+tile[1][0],ay+tile[1][1],z),[]).append(tile)
    return out


def add(tile,sid):
    if not any(c[0]==6 and struct.unpack_from('<H',c[1])[0]==sid for c in tile[2]):
        tile[2].append([6,bytearray(struct.pack('<H',sid)),[]]);return 1
    return 0


def profile(tile,otb):
    items=ids(tile,otb);flags=set()
    for sid in items:flags.update(otb.get(sid,{}).get('flags',[]))
    return (any(otb.get(sid,{}).get('group')=='ground' for sid in items),
            {f for f in flags if f.startswith('block_') or f.startswith('floorchange_')})


def apply(root,otb):
    index=tiles(root);counts=Counter()
    for pos in sorted(SCOPE):
        found=index.get(pos,[])
        if len(found)!=1 or found[0][0]!=5:raise ValueError(f'Tile inexistente, duplicado o de casa: {pos}')
        tile=found[0]
        if pos in STONE_PADS:
            for props,offset in item_offsets(tile,otb):
                old=struct.unpack_from('<H',props,offset)[0]
                if otb.get(old,{}).get('group')=='ground':
                    if old not in (WOOD,STONE,424,4756):raise ValueError(f'Suelo ajeno en {pos}: {old}')
                    if old!=STONE:struct.pack_into('<H',props,offset,STONE);counts['pavimento']+=1
        if pos in CLEAN_BORDER:
            # Capas de borde repetidas y wild growth ocultaban las uniones del muelle.
            kept=[];edge=False
            for child in tile[2]:
                sid=struct.unpack_from('<H',child[1])[0] if child[0]==6 else None
                if sid in (434,435,442,443,444,445,1499):
                    if len(child[1])!=2 or child[2]:raise ValueError(f'Borde con atributos en {pos}')
                    if sid==CLEAN_BORDER[pos] and not edge:kept.append(child);edge=True
                    else:counts['bordes limpiados']+=1
                else:kept.append(child)
            tile[2]=kept
            if not edge:counts['borde']+=add(tile,CLEAN_BORDER[pos])
        if pos in RAILS:
            # Norte/oeste usan 2×1/1×2; sur/este 2×2. Intercambiarlas flota sobre agua.
            tile[2]=[c for c in tile[2] if not (c[0]==6 and len(c[1])==2 and not c[2]
                     and struct.unpack_from('<H',c[1])[0] in (1516,1517,1518,1519)
                     and struct.unpack_from('<H',c[1])[0]!=RAILS[pos])]
            if 'block_solid' not in profile(tile,otb)[1]:raise ValueError(f'Baranda en paso libre: {pos}')
            counts['barandas']+=add(tile,RAILS[pos])
        if pos in LAMPS:
            if 'block_solid' not in profile(tile,otb)[1]:raise ValueError(f'Farol en paso libre: {pos}')
            counts['faroles']+=add(tile,LAMP)
    return counts


def validate(before,after,otb):
    a,b=tiles(before),tiles(after)
    if a.keys()!=b.keys():raise ValueError('Cambió la huella del mapa')
    changed=0
    for pos,old in a.items():
        if [serialize_tree(t,b'') for t in old]==[serialize_tree(t,b'') for t in b[pos]]:continue
        if pos not in SCOPE:raise ValueError(f'Cambio ajeno: {pos}')
        if len(old)!=1 or len(b[pos])!=1:raise ValueError(f'Tile duplicado: {pos}')
        if profile(old[0],otb)!=profile(b[pos][0],otb):raise ValueError(f'Cambió el paso/colisión: {pos}')
        def protected(tile):
            return [serialize_tree(c,b'') for c in tile[2] if c[0]!=6 or len(c[1])>2 or c[2]
                    or struct.unpack_from('<H',c[1])[0] in (1390,1391)
                    or any(f.startswith('floorchange_') for f in otb.get(struct.unpack_from('<H',c[1])[0],{}).get('flags',[]))]
        if protected(old[0])!=protected(b[pos][0]):raise ValueError(f'Escalera/atributo modificado: {pos}')
        changed+=1
    return changed


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--dry-run',action='store_true');args=ap.parse_args()
    raw=MAP.read_bytes();root=parse_tree(raw);otb=load_otb();counts=apply(root,otb)
    count=validate(parse_tree(raw),root,otb)
    print(f'Transiciones: {count} tiles; {dict(counts)}; huella, paso y escaleras conservados')
    if not args.dry_run:MAP.write_bytes(serialize_tree(root,raw[:4]))


if __name__=='__main__':main()
