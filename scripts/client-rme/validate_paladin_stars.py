#!/usr/bin/env python3
"""Audita el pack contra un backup: nada previo puede cambiar salvo los 3 slots de ítem.

  python3.11 scripts/client-rme/validate_paladin_stars.py --before backups/map/paladin-stars-before
"""
import argparse
import struct
from pathlib import Path
from xml.etree import ElementTree as ET

import add_custom_items as A
from add_recolor_effects import read_sections
from add_paladin_stars import ITEMS, ROOT


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--before', type=Path, required=True)
    args = ap.parse_args()
    things = ROOT / 'devtools/rme/rme-client-760'
    old_dat = (args.before/'Tibia.dat').read_bytes()
    new_dat = (things/'Tibia.dat').read_bytes()
    before = A.B.DatReader(old_dat)
    after = A.B.DatReader(new_dat)
    entries0, tail0 = before.read_item_entries()
    entries1, tail1 = after.read_item_entries()
    allowed = {item['client_id'] for item in ITEMS}
    changed = {a.client_id for a, b in zip(entries0, entries1) if a.raw != b.raw}
    assert changed == allowed, changed
    assert before.item_count == after.item_count and before.outfit_count == after.outfit_count
    counts0, fx0, mi0 = read_sections(old_dat)
    counts1, fx1, mi1 = read_sections(new_dat)
    assert counts0[2:] == (44, 18) and counts1[2:] == (47, 21)
    # Toda la sección de criaturas (incluidos trolls/kongra) debe ser idéntica.
    assert tail0[:fx0[0]['start']-(len(old_dat)-len(tail0))] == tail1[:fx1[0]['start']-(len(new_dat)-len(tail1))]
    for old, new in ((fx0, fx1[:44]), (mi0, mi1[:18])):
        assert [old_dat[t['start']:t['end']] for t in old] == [new_dat[t['start']:t['end']] for t in new]
    spr0 = A.B.SprReader((args.before/'Tibia.spr').read_bytes())
    spr1 = A.B.SprReader((things/'Tibia.spr').read_bytes())
    assert spr1.sprite_count == spr0.sprite_count + 51
    assert all(spr0.sprite_raw(sid) == spr1.sprite_raw(sid) for sid in range(1, spr0.sprite_count+1))
    _, root0 = A.load_otb(args.before/'items-zagan-test.otb')
    _, root1 = A.load_otb(ROOT/'server/YurOTS/ots/data/items/items-zagan-test.otb')
    assert root0.props == root1.props
    nodes0 = {A.node_ids(n)[0]: A.B.write_node(n) for n in root0.children}
    nodes1 = {A.node_ids(n)[0]: A.B.write_node(n) for n in root1.children}
    assert set(nodes1)-set(nodes0) == {20211,20212,20213}
    assert all(nodes1[sid] == data for sid, data in nodes0.items())
    mapping = {}
    for node in root1.children:
        sid, cid, _ = A.node_ids(node)
        mapping[cid] = sid
        if sid not in (20211,20212,20213):
            continue
        item = next(i for i in ITEMS if i['server_id'] == sid)
        flags, blocks = A.B.parse_item_props(node.props)
        assert struct.unpack('<I', flags)[0] == 0x60  # pickup/move, sin stackable
        assert node.node_type == 3
        assert A.B.get_block_payload(blocks,A.ITEM_ATTR_WEAPON2) == bytes([5,0,7,item['attack'],0])
        assert cid == item['client_id']
    assert all(mapping[item['client_id']] == item['server_id'] for item in ITEMS)
    for name, sid in [('furious amazon',20211),('serpent spawn',20212),('black dragon',20213)]:
        monster = ET.parse(ROOT/'server/YurOTS/ots/data/monster'/f'{name}.xml')
        assert len(monster.findall(f'./loot/item[@id="{sid}"]')) == 1
    print(f'PASS: {spr0.sprite_count} sprites anteriores intactos; +51 nuevos; solo 3 entradas item cambian')
    print('PASS: criaturas, 44 efectos, 18 proyectiles y todos los nodos OTB anteriores intactos')
    print('PASS: DIST no apilable, mapping último-gana correcto, tres drops directos')


if __name__ == '__main__':
    main()
