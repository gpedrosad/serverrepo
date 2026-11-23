#!/usr/bin/env python3
"""Small rotworm riverbank beneath Ironbound, with its sole access in the southwest."""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import shutil
import struct
import sys
from datetime import datetime
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'kb')]
from mapdata import MAP, REPO, load_otb, parse_tree, serialize_tree
from epstein_cave_repair import index

spec = importlib.util.spec_from_file_location('bank_coasts', HERE / 'generate-north-pass.py')
N = importlib.util.module_from_spec(spec)
spec.loader.exec_module(N)
WORLD = MAP.parent
SPAWNS = WORLD / 'test-spawn.xml'
MANIFEST = WORLD / 'generated-bridge-rotworms.json'
Z, WATER, GRASS, COAST_GRASS, DIRT, PIER = 7, 4608, 4756, 4526, 103, 20579
COAST_SIDE = dict(n=4644, e=4645, s=4646, w=4647)
COAST_CORNER = {('n', 'w'): 4648, ('n', 'e'): 4649, ('s', 'w'): 4650, ('s', 'e'): 4651}
COAST_INNER = dict(nw=4652, ne=4653, sw=4654, se=4655)
COASTS = set(range(4644, 4656))
LAND = {(x, y) for ya, yb, xa, xb in ((64, 65, 140, 143), (66, 67, 138, 145),
                                      (68, 70, 133, 145), (71, 71, 133, 141), (72, 72, 133, 137))
        for y in range(ya, yb + 1) for x in range(xa, xb + 1)} - {(145, 66)}
ENTRY = (135, 73)
MUD = {(140, 68), (141, 68), (142, 68), (135, 70), (135, 71)}
MONSTERS = ((136, 69), (140, 67), (143, 69), (142, 65))
MARKER = 'IRONBOUND_ROTWORMS'


def walkable(ids, otb):
    return bool(ids) and any(otb[s]['group'] == 'ground' for s in ids) and not any(
        'block_solid' in otb[s]['flags'] for s in ids)


def spawn_text(text):
    groups = []
    for x, y in MONSTERS:
        groups.append(f'\t<spawn centerx="{x}" centery="{y}" centerz="7" radius="2">\n'
                      '\t\t<monster name="Rotworm" x="0" y="0" z="7" spawntime="90"/>\n\t</spawn>')
    block = f'\t<!-- BEGIN {MARKER} -->\n' + '\n'.join(groups) + f'\n\t<!-- END {MARKER} -->\n'
    pattern = rf'[ \t]*<!-- BEGIN {MARKER} -->.*?<!-- END {MARKER} -->\n?'
    return re.sub(pattern, lambda _: block, text, flags=re.S) if re.search(pattern, text, re.S) else text.replace('</spawns>', block + '</spawns>')


def plan(values, otb):
    def water(p):
        ids = values.get((*p, Z), [])
        return p not in LAND and (WATER in ids or bool(COASTS & set(ids)))

    coast = {}
    for x, y in LAND:
        neighbors = {d for d, (dx, dy) in N.DIRS.items() if water((x + dx, y + dy))}
        pieces = N.pieces_for(neighbors, COAST_SIDE, COAST_CORNER, COAST_INNER)
        assert pieces is not None and len(pieces) <= 1, ('Ambiguous coast', x, y, pieces)
        if pieces:
            coast[x, y] = pieces[0]
    core = LAND - coast.keys()
    assert all((x + dx, y + dy) in core for x, y in MUD for dx, dy in N.ALL8)
    cells = {}
    for x, y in sorted(LAND):
        if (x, y) in coast:
            ids = [COAST_GRASS, coast[x, y]]
        elif (x, y) in MUD:
            ids = [DIRT]
        else:
            pieces = N.pieces_for(N.neighbors_in(MUD, x, y), N.DIRT_SIDE, N.DIRT_CORNER, N.DIRT_INNER)
            assert pieces is not None and len(pieces) <= 1, ('Ambiguous soil edge', x, y, pieces)
            ids = [pieces[0] if pieces else GRASS]
        if PIER in values.get((x, y, Z), []):
            assert (x, y) not in coast, ('Pier on new coastline', x, y)
            ids.append(PIER)
        cells[x, y, Z] = ids
    walk = {(x, y) for (x, y, z), ids in cells.items() if walkable(ids, otb)}
    assert walkable(values.get((*ENTRY, Z), []), otb)
    road = (136, 77)
    assert walkable(values.get((*road, Z), []), otb)
    approach, todo = {road}, [road]
    while todo:
        x, y = todo.pop()
        for dx, dy in N.CARD:
            p = x + dx, y + dy
            if (129 <= p[0] <= 149 and 73 <= p[1] <= 80 and p not in approach
                    and walkable(values.get((*p, Z), []), otb)):
                approach.add(p)
                todo.append(p)
    assert ENTRY in approach, 'Southwest entrance is not reachable from the road'
    seen, todo = {ENTRY}, [ENTRY]
    while todo:
        x, y = todo.pop()
        for dx, dy in N.CARD:
            p = x + dx, y + dy
            if p in walk and p not in seen:
                seen.add(p)
                todo.append(p)
    assert walk <= seen, ('Disconnected bank', walk - seen)
    # Existing land can only touch the new walkable area at the southwest mouth.
    frontier = {(x + dx, y + dy) for x, y in walk for dx, dy in N.ALL8
                if (x + dx, y + dy) not in LAND
                and walkable(values.get((x + dx, y + dy, Z), []), otb)}
    assert frontier and all(y == 73 and 133 <= x <= 137 for x, y in frontier), ('Other bank connected', frontier)
    assert all(p in walk and abs(p[0] - ENTRY[0]) + abs(p[1] - ENTRY[1]) >= 4 for p in MONSTERS)
    assert all(abs(x - a) + abs(y - b) >= 4 for i, (x, y) in enumerate(MONSTERS) for a, b in MONSTERS[i + 1:])
    return cells, dict(entry=[*ENTRY, Z], tiles=len(cells), walkable=len(walk),
                       coast=len(coast), monsters=4, spawnTime=90, frontier=sorted(frontier))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--remove', action='store_true', help='Restore the recorded river tiles and remove only our four spawns')
    args = ap.parse_args()
    raw = MAP.read_bytes()
    root, otb = parse_tree(raw), load_otb()
    nodes, values, _ = index(root, otb)
    previous = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    if args.remove:
        assert previous.get('original') and previous.get('cells'), 'Missing restoration manifest'
        cells = {tuple(map(int, key.split(','))): ids for key, ids in previous['original'].items()}
        for p, ids in cells.items():
            key = ','.join(map(str, p))
            assert values.get(p) in (ids, previous['cells'][key]), ('Foreign tile modification', p)
            assert len(nodes.get(p, [])) == 1 and nodes[p][0][0] == 5
            tile = nodes[p][0]
            assert len(tile[1]) == 5 and tile[1][2] == 9, ('Protected tile', p)
            assert all(c[0] == 6 and len(c[1]) == 2 and not c[2] for c in tile[2]), ('Attributed object', p)
        text = SPAWNS.read_text(encoding='latin-1')
        updated = re.sub(rf'[ \t]*<!-- BEGIN {MARKER} -->.*?<!-- END {MARKER} -->\n?', '', text, flags=re.S)
        ET.fromstring(updated)
        changed = sum(values[p] != ids for p, ids in cells.items())
        print(json.dumps(dict(removed=True, restoredTiles=changed, spawnFileChanged=text != updated)))
        if args.dry_run or (not changed and text == updated):
            return
        backup = REPO / 'backups/map' / ('remove-bridge-rotworms-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
        backup.mkdir(parents=True)
        for path in (MAP, SPAWNS, MANIFEST):
            shutil.copy2(path, backup / path.name)
        for (x, y, z), ids in cells.items():
            tile = nodes[x, y, z][0]
            tile[1] = bytearray((x % 256, y % 256)) + struct.pack('<BH', 9, ids[0])
            tile[2] = [[6, bytearray(struct.pack('<H', sid)), []] for sid in ids[1:]]
        MAP.write_bytes(serialize_tree(root, raw[:4]))
        SPAWNS.write_text(updated, encoding='latin-1')
        MANIFEST.write_text(json.dumps(previous | dict(removed=True), separators=(',', ':')) + '\n')
        return
    if previous.get('removed'):
        print(json.dumps(dict(removed=True, changed=0, reason='Riverbank removed by user; generation disabled')))
        return
    cells, report = plan(values, otb)
    original = previous.get('original', {})
    for p, ids in cells.items():
        key = ','.join(map(str, p))
        old = values.get(p)
        owned = previous.get('cells', {}).get(key) == old
        if not owned:
            assert old and old[0] in (WATER, COAST_GRASS), ('Foreign ground', p, old)
            assert set(old[1:]) <= COASTS | {PIER}, ('Foreign object', p, old)
        assert len(nodes.get(p, [])) == 1
        tile = nodes[p][0]
        assert tile[0] == 5 and (len(tile[1]) == 2 or (len(tile[1]) == 5 and tile[1][2] == 9)), ('Protected tile', p)
        assert all(c[0] == 6 and len(c[1]) == 2 and not c[2] for c in tile[2]), ('Attributed object', p)
        original.setdefault(key, old)
    text = SPAWNS.read_text(encoding='latin-1')
    # An existing spawn must never be displaced by the bank.
    clean = re.sub(rf'<!-- BEGIN {MARKER} -->.*?<!-- END {MARKER} -->', '', text, flags=re.S)
    for spawn in ET.fromstring(clean):
        x, y, z = [int(spawn.get(k, '0')) for k in ('centerx', 'centery', 'centerz')]
        for monster in spawn:
            p = x + int(monster.get('x', '0')), y + int(monster.get('y', '0')), int(monster.get('z', z))
            assert p not in cells, ('Existing monster protected', p)
    updated = spawn_text(text)
    ET.fromstring(updated)
    changed = sum(values[p] != ids for p, ids in cells.items())
    print(json.dumps(report | dict(changed=changed, spawnFileChanged=text != updated)))
    if args.dry_run or (not changed and text == updated):
        return
    backup = REPO / 'backups/map' / ('bridge-rotworms-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True)
    for path in (MAP, SPAWNS):
        shutil.copy2(path, backup / path.name)
    for (x, y, z), ids in cells.items():
        tile = nodes[x, y, z][0]
        tile[1] = bytearray((x % 256, y % 256)) + struct.pack('<BH', 9, ids[0])
        tile[2] = [[6, bytearray(struct.pack('<H', sid)), []] for sid in ids[1:]]
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    SPAWNS.write_text(updated, encoding='latin-1')
    MANIFEST.write_text(json.dumps(report | dict(original=original,
        cells={','.join(map(str, p)): ids for p, ids in sorted(cells.items())}), separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
