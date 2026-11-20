#!/usr/bin/env python3
"""Repara bordes, relleno y escaleras de Epstein conservando rutas y spawns."""
import argparse
import importlib.util
import json
import struct
import sys
import xml.etree.ElementTree as ET
from collections import Counter,defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE/'kb')]
from mapdata import MAP,REPO,load_otb,parse_tree,serialize_tree
from portal_temple_style import item_offsets
from portal_citadel_layout import tile_flags

spec=importlib.util.spec_from_file_location('epstein_north',HERE/'generate-north-pass.py')
NP=importlib.util.module_from_spec(spec);spec.loader.exec_module(NP)
WORLD=REPO/'server/YurOTS/ots/data/world'
FLOORS=set(range(351,356));WALLS=set(range(356,368));ROCK=101
HOLE,LADDER,FIRE=479,1386,1423


def index(root,otb):
    nodes={};values={};areas={}
    for area in root[2][0][2]:
        if area[0]!=4:continue
        ax,ay,z=struct.unpack_from('<HHB',area[1]);areas[ax,ay,z]=area
        for tile in area[2]:
            if tile[0] not in (5,14):continue
            pos=ax+tile[1][0],ay+tile[1][1],z
            nodes.setdefault(pos,[]).append(tile)
            values[pos]=[struct.unpack_from('<H',p,o)[0] for p,o in item_offsets(tile,otb)]
    return nodes,values,areas


def connected(floor,start):
    seen=set();todo=[start]
    while todo:
        p=todo.pop()
        if p in seen or p not in floor:continue
        seen.add(p);x,y=p;todo.extend((x+dx,y+dy) for dx,dy in NP.CARD)
    return seen


def pieces(floor,pos):
    return NP.pieces_for(NP.neighbors_in(floor,*pos),NP.WALL_SIDE,NP.WALL_CORNER,NP.WALL_INNER) or []


def plan(values):
    meta=json.loads((WORLD/'generated-epstein-caves.json').read_text())['zones']
    regions={};ground={};lights={};counts=Counter();removed=defaultdict(set)
    protected={p for p,ids in values.items() if HOLE in ids or LADDER in ids}
    protected|={(x,y+1,z-1) for (x,y,z),ids in values.items() if LADDER in ids}
    for spawn in ET.parse(WORLD/'test-spawn.xml').getroot():
        x,y,z=[int(spawn.get(k,'0')) for k in ('centerx','centery','centerz')]
        protected.update((x+int(m.get('x','0')),y+int(m.get('y','0')),int(m.get('z',z))) for m in spawn)
    original_floor=defaultdict(set)
    for (x,y,z),ids in values.items():
        if ids and ids[0] in FLOORS|{HOLE}:original_floor[z].add((x,y))
    # La cueva vieja se conserva; solo retraer su borde sur una casilla para que
    # no comparta una pared de una sola cara con Wyvern Roost.
    legacy=connected({(x,y) for (x,y,z),ids in values.items() if z==8 and ids and ids[0] in FLOORS},(82,190))
    trim={p for p in legacy if p[1]==199}
    if any((*p,8) in protected for p in trim):raise ValueError('Entidad en el borde sur de Mutant Burrow')
    legacy-=trim
    removed[8]|=trim;original_floor[8]-=trim
    regions['mutant']=dict(z=8,start=[82,190,8],floor=legacy,target={p for p in legacy if p[1]>=175})
    for name,m in meta.items():
        x0,y0,x1,y1=m['box'];z=m['z']
        floor={(x,y) for (x,y,zz),ids in values.items() if zz==z and x0<=x<=x1 and y0<=y<=y1
               and ids and ids[0] in FLOORS|{HOLE}}
        original=set(floor)
        external=original_floor[z]-floor
        near=lambda p:any((p[0]+dx,p[1]+dy) in external for dx in range(-2,3) for dy in range(-2,3))
        edge={p for p in floor if near(p)}
        if any((*p,z) in protected for p in edge):raise ValueError(f'Entidad en borde compartido: {name}')
        floor-=edge;removed[z]|=edge;counts['bordes compartidos separados']+=len(edge)
        for _ in range(50):
            ring={(x+dx,y+dy) for x,y in floor for dx,dy in NP.ALL8}-floor
            bad={p for p in ring if len(pieces(floor,p))!=1}
            if not bad:break
            for x,y in bad:
                old=values.get((x,y,z),[])
                if near((x,y)) or not(x0<=x<=x1 and y0<=y<=y1) or any(i not in WALLS|{ROCK} for i in old):
                    raise ValueError(f'Borde ambiguo fuera de la cueva: {name} {(x,y,z)} {old}')
            floor|=bad
        else:raise ValueError(f'El borde no converge: {name}')
        for x,y in floor-original:
            nearby=[values[x+dx,y+dy,z][0] for dx,dy in NP.CARD
                    if values.get((x+dx,y+dy,z),[None])[0] in FLOORS]
            ground[x,y,z]=Counter(nearby).most_common(1)[0][0] if nearby else 351
        counts['rocas estrechas cavadas']+=len(floor-original)
        if connected(floor,tuple(m['start'][:2]))!=floor:raise ValueError(f'Cueva desconectada: {name}')
        regions[name]=dict(m,floor=floor,target=floor)
    all_floor=defaultdict(set);target=defaultdict(set)
    for (x,y,z),ids in values.items():
        if ids and ids[0] in FLOORS|{HOLE}:all_floor[z].add((x,y))
    for z,cells in removed.items():all_floor[z]-=cells
    for r in regions.values():
        all_floor[r['z']]|=r['floor'];target[r['z']]|=r['target']
    for x,y in trim:
        pcs=pieces(all_floor[8],(x,y))
        if len(pcs)!=1:raise ValueError(f'Separación de cuevas inválida: {(x,y)}')
        ground[x,y,8]=pcs[0]
    counts['borde sur de Mutant Burrow']+=len(trim)
    for z,floor in target.items():
        ring={(x+dx,y+dy) for x,y in floor for dx,dy in NP.ALL8}-all_floor[z]
        for x,y in ring:
            pcs=pieces(all_floor[z],(x,y))
            if len(pcs)!=1:raise ValueError(f'Pared sin pieza única: {(x,y,z)}')
            old=values.get((x,y,z),[])
            if z==8 and old and 371<=old[0]<=382:continue
            allowed=WALLS|{ROCK,2059,2061}|(FLOORS if (x,y) in removed[z] else set())
            if any(i not in allowed for i in old):raise ValueError(f'Pared ajena: {(x,y,z)} {old}')
            ground[x,y,z]=pcs[0]
        # Rellenar únicamente vacío visible; las casillas existentes ajenas quedan intactas.
        view={(x+dx,y+dy,z) for x,y in floor for dx in range(-9,10) for dy in range(-7,8)}
        for pos in view:
            if pos in values or pos in ground:continue
            pcs=pieces(all_floor[z],pos[:2])
            if len(pcs)>1:raise ValueError(f'Relleno junto a pared ambigua: {pos}')
            ground[pos]=pcs[0] if pcs else ROCK
            counts['relleno de vacío']+=1
    # Sustituir fogatas sobre escaleras por antorchas fijadas a una pared cercana.
    for name,m in meta.items():
        x,y,z=m['start'];candidates=[]
        for dx in range(-4,5):
            for dy in range(-4,5):
                q=x+dx,y+dy,z;sid=ground.get(q,values.get(q,[None])[0])
                if sid not in (356,357,358,359) or max(abs(dx),abs(dy))<2:continue
                existing=values.get(q,[])
                if any(i not in WALLS|{ROCK,2059,2061} for i in existing):continue
                candidates.append((not any(i in (2059,2061) for i in existing),abs(dx)+abs(dy),q,sid))
        if not candidates:raise ValueError(f'No hay pared para iluminar {name}')
        _,_,q,sid=min(candidates);lights[q]=2059 if sid in (356,357) else 2061
    return regions,ground,lights,counts


def apply(root,otb):
    nodes,values,areas=index(root,otb)
    regions,ground,lights,counts=plan(values)
    if any(not(30<=x<=132 and 167<=y<=268 and 8<=z<=10) for x,y,z in ground.keys()|lights.keys()):
        raise ValueError('La reparación sale del ámbito de Epstein')
    for pos,sid in sorted(ground.items()):
        found=nodes.get(pos,[])
        if found:
            if len(found)!=1 or found[0][0]!=5:raise ValueError(f'Tile duplicado/de casa: {pos}')
            tile=found[0]
            if values[pos] and values[pos][0]==sid:continue
            if any(c[0]!=6 or len(c[1])!=2 or c[2] for c in tile[2]):raise ValueError(f'Atributos protegidos: {pos}')
            if any(i not in FLOORS|WALLS|{ROCK,2059,2061} for i in values[pos]):raise ValueError(f'Ítem ajeno en {pos}')
            tile[1]=tile[1][:2]+tile_flags(tile[1])+struct.pack('<BH',9,sid)
            counts['suelos/paredes reemplazados']+=1
        else:
            x,y,z=pos;key=x//256*256,y//256*256,z
            if key not in areas:
                areas[key]=[4,bytearray(struct.pack('<HHB',*key)),[]];root[2][0][2].append(areas[key])
            tile=[5,bytearray([x%256,y%256])+struct.pack('<BH',9,sid),[]]
            areas[key][2].append(tile);nodes[pos]=[tile]
    for r in regions.values():
        tile=nodes[tuple(r['start'])][0]
        old=len(tile[2]);tile[2]=[c for c in tile[2] if not(c[0]==6 and len(c[1])==2
                            and struct.unpack_from('<H',c[1])[0]==FIRE)]
        counts['fogatas retiradas de escalera']+=old-len(tile[2])
    for pos,sid in lights.items():
        tile=nodes[pos][0]
        if not any(c[0]==6 and struct.unpack_from('<H',c[1])[0]==sid for c in tile[2]):
            tile[2].append([6,bytearray(struct.pack('<H',sid)),[]]);counts['antorchas']+=1
    return regions,counts


def validate(root,otb,regions):
    _,values,_=index(root,otb)
    def free(pos):
        ids=values.get(pos,[])
        return bool(ids) and any(otb.get(i,{}).get('group')=='ground' for i in ids) and not any(
            'block_solid' in otb.get(i,{}).get('flags',[]) for i in ids)
    floors=defaultdict(set)
    for (x,y,z),ids in values.items():
        if ids and ids[0] in FLOORS|{HOLE}:floors[z].add((x,y))
    for name,r in regions.items():
        x,y,z=r['start'];ladder=values.get((x,y,z),[])
        if len(ladder)!=2 or ladder[0] not in FLOORS or ladder[1]!=LADDER or not free((x,y+1,z-1)) or HOLE not in values.get((x,y,z-1),[]):
            raise ValueError(f'Escalera/salida inválida: {name}')
        if connected(r['floor'],(x,y))!=r['floor']:raise ValueError(f'Cueva sin acceso: {name}')
        for x,y in r['target']:
            for dx,dy in NP.ALL8:
                p=x+dx,y+dy,z
                if p[:2] not in floors[z]:
                    pcs=pieces(floors[z],p[:2])
                    actual=values.get(p,[None])[0]
                    native=name=='mutant' and actual is not None and 371<=actual<=382
                    if len(pcs)!=1 or not(native or actual==pcs[0]):raise ValueError(f'Pared inválida: {p}')
            for dx in range(-8,10):
                for dy in range(-6,8):
                    if (x+dx,y+dy,z) not in values:raise ValueError(f'Vacío visible desde {(x,y,z)}')
    for spawn in ET.parse(WORLD/'test-spawn.xml').getroot():
        x,y,z=[int(spawn.get(k,'0')) for k in ('centerx','centery','centerz')]
        for monster in spawn:
            p=x+int(monster.get('x','0')),y+int(monster.get('y','0')),int(monster.get('z',z))
            if 40<=p[0]<=122 and 175<=p[1]<=260 and p[2] in (8,9,10) and not free(p):
                raise ValueError(f'Monstruo sobre pared: {monster.get("name")} {p}')


def run(dry_run=False):
    raw=MAP.read_bytes();root=parse_tree(raw);otb=load_otb()
    regions,counts=apply(root,otb);validate(root,otb,regions)
    print('Cuevas de Epstein:',dict(counts))
    print('Paredes con pieza única, sin vacío visible; diez escaleras y spawns conservados')
    if not dry_run:MAP.write_bytes(serialize_tree(root,raw[:4]))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--dry-run',action='store_true')
    run(ap.parse_args().dry_run)
