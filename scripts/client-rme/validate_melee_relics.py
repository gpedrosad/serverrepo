#!/usr/bin/env python3
"""Audita IDs, armas, sprites previos y efectos contra el backup de instalación."""
import argparse
import struct
from pathlib import Path
from xml.etree import ElementTree as ET
import add_custom_items as A
from add_melee_relics import ROOT, ITEMS, effects
from add_recolor_effects import read_sections


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--before',type=Path,default=ROOT/'backups/map/melee-relics-before')
    args=ap.parse_args(); things=ROOT/'devtools/rme/rme-client-760'
    old_dat=(args.before/'Tibia.dat').read_bytes();new_dat=(things/'Tibia.dat').read_bytes()
    old=A.B.DatReader(old_dat);new=A.B.DatReader(new_dat)
    e0,tail0=old.read_item_entries();e1,tail1=new.read_item_entries()
    assert {a.client_id for a,b in zip(e0,e1) if a.raw!=b.raw}=={i['client_id'] for i in ITEMS}
    assert (old.item_count,old.outfit_count)==(new.item_count,new.outfit_count)
    c0,fx0,mi0=read_sections(old_dat);c1,fx1,mi1=read_sections(new_dat)
    assert c0[2:]==(47,21) and c1[2:]==(50,21)
    assert tail0[:fx0[0]['start']-(len(old_dat)-len(tail0))]==tail1[:fx1[0]['start']-(len(new_dat)-len(tail1))]
    for a,b in [(fx0,fx1[:47]),(mi0,mi1)]:
        assert [old_dat[t['start']:t['end']] for t in a]==[new_dat[t['start']:t['end']] for t in b]
    s0=A.B.SprReader((args.before/'Tibia.spr').read_bytes());s1=A.B.SprReader((things/'Tibia.spr').read_bytes())
    assert s1.sprite_count==s0.sprite_count+27
    assert all(s0.sprite_raw(i)==s1.sprite_raw(i) for i in range(1,s0.sprite_count+1))
    _,r0=A.load_otb(args.before/'items-zagan-test.otb')
    _,r1=A.load_otb(ROOT/'server/YurOTS/ots/data/items/items-zagan-test.otb')
    assert r0.props==r1.props
    n0={A.node_ids(n)[0]:A.B.write_node(n) for n in r0.children}
    n1={A.node_ids(n)[0]:A.B.write_node(n) for n in r1.children}
    assert set(n1)-set(n0)=={i['server_id'] for i in ITEMS}
    assert all(n1[sid]==raw for sid,raw in n0.items())
    for item,weapon_type,slot in zip(ITEMS,[1,3,2],[10,10,6]):
        node=next(n for n in r1.children if A.node_ids(n)[0]==item['server_id'])
        flags,blocks=A.B.parse_item_props(node.props)
        assert struct.unpack('<I',flags)[0]==0x70
        assert node.node_type==3
        assert A.B.get_block_payload(blocks,A.ITEM_ATTR_WEAPON2)==bytes([weapon_type,0,0,item['attack'],item['defence']])
        slot_bytes=A.B.get_block_payload(blocks,0x15)
        assert struct.unpack('<H',slot_bytes)[0]==slot,(item['name'],slot_bytes)
    for monster,item,chance in [('warlock',20250,300),('root colossus',20251,350),('worker golem',20252,400)]:
        entries=ET.parse(ROOT/'server/YurOTS/ots/data/monster'/f'{monster}.xml').findall(f'./loot/item[@id="{item}"]')
        assert len(entries)==1 and entries[0].get('chance')==str(chance)
    effects(things,True)
    for platform in ['mac','windows']:
        for name in ['Tibia.dat','Tibia.spr']:
            assert (things/name).read_bytes()==(ROOT/'devtools/clients/cliente-oficial-retro'/platform/'data/things/760'/name).read_bytes()
    print(f'PASS: {s0.sprite_count} sprites intactos; +27; solo tres slots item cambiados')
    print('PASS: outfits, 47 efectos, 21 proyectiles y nodos OTB previos intactos')
    print('PASS: sword/axe 1H, club 2H, flags/ataque/defensa, loot y paridad Mac/Windows')


if __name__=='__main__': main()
