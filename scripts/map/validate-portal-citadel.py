#!/usr/bin/env python3
"""Audita la plaza contra su backup: ámbito, rutas, portales y assets anteriores.

  python3.11 scripts/map/validate-portal-citadel.py --before backups/map/portal-citadel-before
"""
import argparse
import importlib.util
import struct
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE/'kb'),str(HERE.parent/'client-rme')]
from mapdata import parse_tree,serialize_tree,iter_tiles,load_otb,MAP
from portal_citadel_layout import TOWER_BASE,upper_plan,plaza_plan,CUSTOM
import add_custom_items as A
from portal_citadel_assets import ITEMS,ROOT

spec=importlib.util.spec_from_file_location('temple',HERE/'temple-portals.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)


def nodes(root):
    result={}
    for area in root[2][0][2]:
        if area[0]!=4:continue
        ax,ay,z=struct.unpack_from('<HHB',area[1])
        for tile in area[2]:
            if tile[0] not in (5,14):continue
            pos=(ax+tile[1][0],ay+tile[1][1],z)
            result.setdefault(pos,[]).append(serialize_tree(tile,b''))
    return result


def teleports(root):
    out=[]
    for area in root[2][0][2]:
        if area[0]!=4:continue
        ax,ay,z=struct.unpack_from('<HHB',area[1])
        for tile in area[2]:
            if tile[0] not in (5,14):continue
            for ch in tile[2]:
                if ch[0]==6 and t.tele_offset(bytes(ch[1])) is not None:
                    out.append(((ax+tile[1][0],ay+tile[1][1],z),bytes(ch[1])))
    return sorted(out)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--before',type=Path,required=True);args=ap.parse_args()
    old=parse_tree((args.before/'test.otbm').read_bytes());new=parse_tree(MAP.read_bytes())
    a,b=nodes(old),nodes(new)
    owned={(x,y,7) for x,y in plaza_plan(t.PORTALS)}|set(upper_plan())
    changed={p for p in set(a)|set(b) if a.get(p)!=b.get(p)}
    assert changed<=owned,changed-owned
    assert len(b)==len(a)+54
    duplicates0={p:len(v) for p,v in a.items() if len(v)>1}
    duplicates1={p:len(v) for p,v in b.items() if len(v)>1}
    assert duplicates0==duplicates1,'Se introdujeron tiles duplicados'
    assert teleports(old)==teleports(new),'Cambió un teleport o su destino'
    tiles={(x,y,z):ids for x,y,z,ids in iter_tiles(new)};otb=load_otb()
    def walkable(pos):
        ids=tiles.get(pos,[])
        return bool(ids) and otb[ids[0]]['group']=='ground' and 1387 not in ids and not any('block_solid' in otb[i]['flags'] for i in ids)
    start=(161,52,7);seen={start};queue=[start]
    while queue:
        x,y,z=queue.pop()
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            pos=(x+dx,y+dy,z)
            if 155<=pos[0]<=169 and 42<=pos[1]<=52 and pos not in seen and walkable(pos):
                seen.add(pos);queue.append(pos)
    for key,x,_d,_text,_zones in t.PORTALS:
        assert (x,48,7) in seen,f'Llegada inaccesible: {key}'
        assert (x,45,7) in seen,f'Cartel inaccesible desde el norte: {key}'
    free={p for p in owned if p[2]==7 and p[:2] not in TOWER_BASE and walkable(p)}
    assert free<=seen,free-seen
    things=ROOT/'devtools/rme/rme-client-760'
    d0=A.B.DatReader((args.before/'Tibia.dat').read_bytes());d1=A.B.DatReader((things/'Tibia.dat').read_bytes())
    e0,tail0=d0.read_item_entries();e1,tail1=d1.read_item_entries()
    assert tail0==tail1,'Cambió un outfit, efecto o proyectil'
    assert {a.client_id for a,b in zip(e0,e1) if a.raw!=b.raw}=={i['client_id'] for i in ITEMS}
    s0=A.B.SprReader((args.before/'Tibia.spr').read_bytes());s1=A.B.SprReader((things/'Tibia.spr').read_bytes())
    assert s1.sprite_count==s0.sprite_count+35
    assert all(s0.sprite_raw(i)==s1.sprite_raw(i) for i in range(1,s0.sprite_count+1))
    _,r0=A.load_otb(args.before/'items-zagan-test.otb');_,r1=A.load_otb(ROOT/'server/YurOTS/ots/data/items/items-zagan-test.otb')
    n0={A.node_ids(n)[0]:A.B.write_node(n) for n in r0.children};n1={A.node_ids(n)[0]:A.B.write_node(n) for n in r1.children}
    assert all(n1[sid]==data for sid,data in n0.items())
    assert [A.B.write_node(n) for n in r0.children]==[A.B.write_node(n) for n in r1.children[:len(r0.children)]]
    assert set(n1)-set(n0)==CUSTOM
    assert not any(sid not in CUSTOM and otb.get(sid,{}).get('cid') in {i['client_id'] for i in ITEMS}
                   for ids in tiles.values() for sid in ids),'Alias de client ID usado fuera de la familia'
    from game_render import parse_dat_all
    entries,_=parse_dat_all()
    for sid in (20214,20215,20216):
        assert entries[otb[sid]['cid']]['flags'][0]==b'd\x00','Velocidad del suelo cambiada'
    for sid,light in ((20223,(6,71)),(20224,(4,71))):
        assert entries[otb[sid]['cid']]['flags'][21]==struct.pack('<HH',*light)
    print(f'PASS: {len(changed)} tiles dentro de plaza/torres; +54 tiles, resto del mapa idéntico')
    print(f'PASS: {len(teleports(new))} teleports intactos; 8 llegadas/carteles accesibles; sin zonas libres aisladas')
    print(f'PASS: {s0.sprite_count} sprites previos intactos; +35 nuevos; 11 slots DAT y 11 nodos OTB nuevos')
    print('PASS: outfits/efectos/proyectiles previos intactos, suelo a 100 y luces declaradas')
    print(f'BASELINE: {len(duplicates0)} posiciones duplicadas previas, idénticas; ninguna nueva')


if __name__=='__main__':main()
