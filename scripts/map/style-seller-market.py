#!/usr/bin/env python3
"""Style Seller and Small Street, and fit Tonka's arcade beside the south path."""
import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path
import shutil
import struct
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'kb'), str(HERE.parent / 'client-rme')]
from mapdata import MAP, REPO, load_otb, parse_tree, serialize_tree
from epstein_cave_repair import index, connected
from portal_temple_style import item_offsets
from seller_market_art import (
    FLOOR_IDS, FURNITURE, REPLACEMENTS, SELLER_DISPLAY, TONKA_COUNTER, TONKA_CREST,
    TONKA_DIVIDER, TONKA_SIDE, TONKA_WORKTOP, TONKA_RAIL,
)

NPCS = MAP.with_name('npc.xml')
OLD_NPC = '<npc name="Tonka" x="140" y="50" z="7" dir="2"/>'
FIRST_SHOP_NPC = '<npc name="Tonka" x="149" y="55" z="7" dir="3"/>'
NEW_NPC = '<npc name="Tonka" x="148" y="55" z="7" dir="2"/>'
HOUSE_TILES = {(x, y, z) for x in (143, 144, 146) for y in range(43, 46) for z in (5, 6, 7)}
SELLER_ORIGINAL = {(144, 47): 1624, (144, 51): 1622, (144, 52): 1628,
                   (145, 52): 1623, (146, 52): 1627}
SELLER_CASES = {47: (1621, 1988), 48: (1620, 2120), 49: (1620, 2554), 50: (1620, 2580)}
COUNTER_ALIASES = {REPLACEMENTS[proto]: proto for proto in FURNITURE}
FORMER_TONKA_FURNITURE = {
    (145,54): TONKA_DIVIDER, (146,54): TONKA_DIVIDER, (147,54): TONKA_CREST,
    (148,54): TONKA_DIVIDER, (149,54): TONKA_DIVIDER, (145,55): TONKA_SIDE,
    (145,56): TONKA_SIDE, (148,55): TONKA_COUNTER,
    (148,56): TONKA_DIVIDER, (149,56): TONKA_DIVIDER,
}
TONKA_FURNITURE = {
    (145, 54): TONKA_DIVIDER, (146, 54): TONKA_DIVIDER, (147, 54): TONKA_CREST,
    (148, 54): TONKA_DIVIDER, (149, 54): TONKA_DIVIDER,
    (145, 55): TONKA_RAIL, (149, 55): TONKA_RAIL,
    (145, 56): TONKA_SIDE, (147, 56): TONKA_WORKTOP, (148, 56): TONKA_COUNTER,
    (149, 56): TONKA_SIDE,
}
TONKA_FLOOR = {(x, y) for x in range(145, 150) for y in range(54, 57)}
PROMENADE = ({(x, y) for x in (142, 143, 144) for y in (54, 55)}
             | {(144, 56)} | {(x, 57) for x in range(144, 150)})


def item(sid):
    return [6, bytearray(struct.pack('<H', sid)), []]


def plain_item(tile, sid):
    matches = [c for c in tile[2] if c == item(sid)]
    if len(matches) != 1:
        raise ValueError(f'Expected one plain object {sid}')
    return matches[0]


def pave(tile, ids, key):
    sid = FLOOR_IDS[key]
    if sid in ids:
        return False
    if set(FLOOR_IDS.values()).intersection(ids):
        raise ValueError('Tile already has a different market finish')
    tile[2].insert(0, item(sid))
    return True


def in_building(x, y, z):
    return (z == 7 and 141 <= x <= 147 and 42 <= y <= 53
            or z in (5, 6) and 140 <= x <= 148 and 41 <= y <= 54
            or z == 4 and 141 <= x <= 147 and 42 <= y <= 54)


def paint(nodes, values, otb):
    changes = Counter()
    for p, ids in values.items():
        x, y, z = p
        if not in_building(*p):
            continue
        tile, = nodes[p]
        if tile[0] != 5:
            raise ValueError(f'Unexpected house tile encoding at {p}')
        if z == 7 and (x, y) in SELLER_ORIGINAL:
            proto = SELLER_ORIGINAL[x, y]
            if proto not in ids and REPLACEMENTS[proto] not in ids:
                if set(ids) - {431, FLOOR_IDS['seller']} or 431 not in ids:
                    raise ValueError(f'Original counter space has other items at {p}: {ids}')
                tile[2].append(item(proto))
                changes['original seller counters restored'] += 1
        if z == 7 and x == 146 and y in SELLER_CASES:
            proto, loose = SELLER_CASES[y]
            new = SELLER_DISPLAY + y - 47
            if new in ids:
                assert set(ids) <= {431, FLOOR_IDS['seller'], new}, (p, ids)
                plain_item(tile, new)[1][:] = struct.pack('<H', proto)
                tile[2].append(item(loose))
                changes['original equipment displays restored'] += 1
        for props, offset in item_offsets(tile, otb):
            sid = struct.unpack_from('<H', props, offset)[0]
            if sid in COUNTER_ALIASES:
                struct.pack_into('<H', props, offset, COUNTER_ALIASES[sid])
                changes['original furniture restored'] += 1
            elif sid in REPLACEMENTS and sid not in FURNITURE:
                struct.pack_into('<H', props, offset, REPLACEMENTS[sid])
                changes['fixture aliases'] += 1
        allowed = {405, 431, 920}
        if (not allowed.intersection(ids) or set(ids).intersection({1385, 1386})):
            continue
        key = ('roof' if z == 4 else 'house' if p in HOUSE_TILES else
               'arcade' if y < 47 else 'seller' if z == 7 else 'gallery' if z == 6 else 'terrace')
        changes['building paving'] += pave(tile, ids, key)
    for x, y in sorted(TONKA_FLOOR | PROMENADE):
        p = (x, y, 7)
        tile, = nodes[p]
        ids = values[p]
        if (x,y) in TONKA_FLOOR:
            fixture = TONKA_FURNITURE.get((x,y))
            former = FORMER_TONKA_FURNITURE.get((x,y))
            former_ids = [431, FLOOR_IDS['tonka']] + ([former] if former else [])
            finish = 'tonka' if y == 54 or (y == 56 and x in (145, 149)) else 'seller'
            expected = [431, FLOOR_IDS[finish]] + ([fixture] if fixture else [])
            if ids == expected:
                continue
            expected_children = [item(sid) for sid in ids[1:]]
            if (ids not in ([4756], former_ids) or tile[0] != 5 or len(tile[1]) != 5
                    or tile[1][2] != 9 or tile[2] != expected_children):
                raise ValueError(f'Tonka arcade overlaps existing content at {p}: {ids}')
            struct.pack_into('<H', tile[1], 3, 431)
            tile[2][:] = [item(sid) for sid in expected[1:]]
            changes['Tonka arcade'] += 1
        else:
            if ids[0] not in (4756, 724) or set(ids[1:]) - {4542, FLOOR_IDS['threshold']}:
                raise ValueError(f'Promenade overlaps existing content at {p}: {ids}')
            if 4542 in ids:
                tile[2].remove(plain_item(tile, 4542))
                changes['grass edging removed at approach'] += 1
            changes['entry paving'] += pave(tile, ids, 'threshold')
    return +changes


def verify(values, otb):
    def walk(x, y, z):
        items = values.get((x,y,z), ())
        return (any(otb[s]['group'] == 'ground' for s in items)
                and not any('block_solid' in otb[s]['flags'] for s in items))
    floor = {(x,y) for x in range(141,151) for y in range(47,59) if walk(x,y,7)}
    reach = connected(floor, (146,58))
    assert {(146,56), (147,57), (148,57), (143,50), (143,53), (142,48)} <= reach
    assert walk(148,55,7) and TONKA_COUNTER in values[148,56,7]
    assert walk(145,50,7) and walk(145,51,6) and walk(144,52,5)
    for x, y, z in HOUSE_TILES:
        assert FLOOR_IDS['house'] in values[x,y,z] and walk(x,y,z)
    for z in (5,6,7):
        assert all(1212 in values[x,42,z] for x in (144,146))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    raw = MAP.read_bytes()
    root, otb = parse_tree(raw), load_otb()
    nodes, values, _ = index(root, otb)
    report = paint(nodes, values, otb)
    del nodes, values
    _, updated, _ = index(root, otb)
    verify(updated, otb)
    npc_text = NPCS.read_text(encoding='utf-8')
    assert sum(npc_text.count(npc) for npc in (OLD_NPC, FIRST_SHOP_NPC, NEW_NPC)) == 1
    new_text = npc_text.replace(OLD_NPC, NEW_NPC).replace(FIRST_SHOP_NPC, NEW_NPC)
    assert sum(n.attrib.get('name') == 'Tonka' for n in ET.fromstring(new_text)) == 1
    print(dict(report), 'Tonka:', 'moved' if new_text != npc_text else 'already in arcade')
    if args.apply and (report or new_text != npc_text):
        backup = REPO / 'backups/map' / datetime.now().strftime('seller-market-%Y%m%d-%H%M%S')
        backup.mkdir(parents=True)
        for path in (MAP, NPCS):
            shutil.copy2(path, backup / path.name)
        MAP.write_bytes(serialize_tree(root, raw[:4]))
        NPCS.write_text(new_text, encoding='utf-8')


if __name__ == '__main__':
    main()
