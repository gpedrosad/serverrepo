#!/usr/bin/env python3
"""Puentes de madera: muelle junto al depot (elfos / islote del minotauro) y los puentes de la ciudad.

Versión 2 (20 nov 2026). La primera usaba piezas nativas que en el juego se veían rotas: barandas 1516-1519
finitas que se salían del muelle, faroles 3744 que parecían calaveras tiradas, losas de piedra 431 como
parches y una rampa de piedra gris pegada a la madera. Ahora:

- barandas, postes y faroles dibujados para este muelle (scripts/client-rme/dock_bridge_art.py, server
  20282-20296), puestos en las casillas de agua/orilla que ya bloqueaban;
- rampa de escalones de madera (mismo comportamiento que 1390/1391: sube al oeste);
- los suelos vuelven a madera 405 (y pasto 4756 donde había pasto); el rellano de arriba (z6) también es de madera;
- se conserva la limpieza de bordes duplicados y wild growth de la versión 1;
- los puentes de BRIDGES (dock_bridge_art.py) llevan las mismas barandas con faroles en las puntas; se sacan
  sus cuerdas nativas (3758-3791) y el wild growth (1499) que tapaba el tablero y las orillas.

Idempotente y con validación: misma huella, mismo paso/colisión/cambio de piso en cada casilla, nada fuera del
ámbito. Doc: docs/items-and-map/TRANSICIONES_DEPOT.md.

  python3 scripts/map/city-bridge-transitions.py --dry-run
  python3 scripts/map/city-bridge-transitions.py
"""
import argparse
import struct
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'kb'), str(HERE.parent / 'client-rme')]
import mapdata as M  # noqa: E402
from portal_temple_style import item_offsets  # noqa: E402
from dock_bridge_art import PIECES, BRIDGES, placements  # noqa: E402

WOOD, GRASS = 405, 4756
GROUNDS = ({(113, 56, 7): WOOD, (114, 56, 7): WOOD}
           | {(x, y, 7): WOOD for x in (113, 114, 123, 124) for y in (60, 61)}
           | {(x, 59, 7): WOOD for x in (123, 124)}
           | {(125, y, 7): GRASS for y in (59, 60, 61)}
           | {(112, 60, 6): WOOD, (111, 61, 6): WOOD, (112, 61, 6): WOOD})
OLD_GROUNDS = {WOOD, GRASS, 424, 431}
NATIVE = {1516, 1517, 1518, 1519, 3744}          # barandas y faroles nativos de la versión 1
SID = {key: sid for key, sid, *_r in PIECES}
PLACE = {pos: SID[key] for pos, key in placements().items() if key.startswith('rail')}
RAMP = {pos: SID[key] for pos, key in placements().items() if key.startswith('ramp')}
RAMP_OLD = {113: 1390, 114: 1391}
OURS = {sid for _k, sid, *_r in PIECES}
CLEAN_BORDER = {(119, 58, 7): 434, (121, 58, 7): 434, (114, 62, 7): 435, (116, 62, 7): 435,
                (117, 62, 7): 435, (123, 62, 7): 435}
CLEAN_ONLY = {(124, 62, 7)}                      # tenía una baranda nativa: se saca y no va nada
CLEAR = {1499} | set(range(3758, 3762)) | set(range(3768, 3792))   # wild growth y cuerdas del puente


def bridge_area(spec):
    """Tablero, casillas de baranda y una fila más en cada punta (postes de cuerda en tierra)."""
    if spec['kind'] == 'v':
        x0, x1 = spec['deck']
        ya, yb = min(spec['w'][0], spec['e'][0]) - 1, max(spec['w'][1], spec['e'][1]) + 1
        return {(x, y, 7) for x in range(x0 - 1, x1 + 2) for y in range(ya, yb + 1)}
    y0, y1 = spec['deck']
    xa, xb = min(spec['n'][0], spec['s'][0]) - 1, max(spec['n'][1], spec['s'][1]) + 1
    return {(x, y, 7) for x in range(xa, xb + 1) for y in range(y0 - 1, y1 + 2)}


BRIDGE_AREA = set().union(*(bridge_area(s) for s in BRIDGES.values()))
# Puentes oeste-este: el borde de madera (434 al norte, 435 al sur) da el canto del tablero donde se apoya la
# baranda, como en el muelle. Sin él, la del norte queda flotando sobre el agua.
LIPS = {}
for _spec in BRIDGES.values():
    if _spec['kind'] == 'h':
        LIPS.update({(x, _spec['deck'][0] - 1, 7): 434 for x in range(_spec['n'][0], _spec['n'][1] + 1)})
        LIPS.update({(x, _spec['deck'][1] + 1, 7): 435 for x in range(_spec['s'][0], _spec['s'][1] + 1)})
SCOPE = (set(GROUNDS) | set(PLACE) | set(RAMP) | set(CLEAN_BORDER) | CLEAN_ONLY | {(121, 58, 7), (112, 56, 7)}
         | BRIDGE_AREA)


def sid_of(child):
    return struct.unpack_from('<H', child[1])[0] if child[0] == 6 and len(child[1]) >= 2 else None


def plain(child):
    return child[0] == 6 and len(child[1]) == 2 and not child[2]


def tiles(root):
    out = {}
    for area in root[2][0][2]:
        if area[0] != 4:
            continue
        ax, ay, z = struct.unpack_from('<HHB', area[1])
        for tile in area[2]:
            if tile[0] in (5, 14):
                out.setdefault((ax + tile[1][0], ay + tile[1][1], z), []).append(tile)
    return out


def profile(tile, otb):
    ids = [struct.unpack_from('<H', p, o)[0] for p, o in item_offsets(tile, otb)]
    flags = set()
    for sid in ids:
        flags.update(otb.get(sid, {}).get('flags', []))
    return (any(otb.get(sid, {}).get('group') == 'ground' for sid in ids),
            {f for f in flags if f.startswith('block_') or f.startswith('floorchange_')})


def apply(root, otb):
    index, counts = tiles(root), Counter()
    for pos in sorted(SCOPE):
        found = index.get(pos, [])
        if not found and pos in BRIDGE_AREA and pos not in PLACE:
            continue
        if len(found) != 1 or found[0][0] != 5:
            raise ValueError(f'Tile inexistente, duplicado o de casa: {pos}')
        tile = found[0]
        blocked_before = 'block_solid' in profile(tile, otb)[1]
        if pos in BRIDGE_AREA:
            before = len(tile[2])
            tile[2] = [c for c in tile[2] if not (plain(c) and sid_of(c) in CLEAR)]
            counts['cuerdas y wild growth'] += before - len(tile[2])
        if pos in GROUNDS:
            for props, offset in item_offsets(tile, otb):
                old = struct.unpack_from('<H', props, offset)[0]
                if otb.get(old, {}).get('group') == 'ground':
                    if old not in OLD_GROUNDS:
                        raise ValueError(f'Suelo ajeno en {pos}: {old}')
                    if old != GROUNDS[pos]:
                        struct.pack_into('<H', props, offset, GROUNDS[pos])
                        counts['suelos'] += 1
        if pos in CLEAN_BORDER:
            # Capas de borde repetidas y wild growth ocultaban las uniones del muelle (versión 1).
            kept, edge = [], False
            for child in tile[2]:
                sid = sid_of(child)
                if sid in (434, 435, 442, 443, 444, 445, 1499):
                    if not plain(child):
                        raise ValueError(f'Borde con atributos en {pos}')
                    if sid == CLEAN_BORDER[pos] and not edge:
                        kept.append(child)
                        edge = True
                    else:
                        counts['bordes limpiados'] += 1
                else:
                    kept.append(child)
            tile[2] = kept
            if not edge:
                tile[2].append([6, bytearray(struct.pack('<H', CLEAN_BORDER[pos])), []])
                counts['bordes'] += 1
        # fuera las piezas nativas de la versión 1 y cualquier pieza nuestra que no vaya en esta casilla
        want = PLACE.get(pos)
        before = len(tile[2])
        tile[2] = [c for c in tile[2] if not (plain(c) and (sid_of(c) in NATIVE or
                                                            (sid_of(c) in OURS and sid_of(c) not in (want, RAMP.get(pos)))))]
        counts['piezas viejas'] += before - len(tile[2])
        if pos in RAMP:
            new = RAMP[pos]
            ramps = [c for c in tile[2] if sid_of(c) in (RAMP_OLD[pos[0]], new)]
            if len(ramps) != 1 or not plain(ramps[0]):
                raise ValueError(f'Rampa inesperada en {pos}: {[sid_of(c) for c in tile[2]]}')
            if sid_of(ramps[0]) != new:
                ramps[0][1][:] = struct.pack('<H', new)
                counts['rampa'] += 1
        if pos in LIPS and not any(sid_of(c) in (434, 435) for c in tile[2]):
            if not blocked_before:
                raise ValueError(f'Borde de madera en paso libre: {pos}')
            mine = [c for c in tile[2] if sid_of(c) in OURS]
            tile[2] = [c for c in tile[2] if sid_of(c) not in OURS] + [[6, bytearray(struct.pack('<H', LIPS[pos])), []]] + mine
            counts['bordes del tablero'] += 1
        if want:
            if not blocked_before and not any(sid_of(c) == want for c in tile[2]):
                raise ValueError(f'Baranda en paso libre: {pos}')
            if not any(sid_of(c) == want for c in tile[2]):
                tile[2].append([6, bytearray(struct.pack('<H', want)), []])
                counts['barandas y faroles'] += 1
    return counts


def validate(before, after, otb):
    a, b = tiles(before), tiles(after)
    if a.keys() != b.keys():
        raise ValueError('Cambió la huella del mapa')
    changed = 0
    for pos, old in a.items():
        if [M.serialize_tree(t, b'') for t in old] == [M.serialize_tree(t, b'') for t in b[pos]]:
            continue
        if pos not in SCOPE:
            raise ValueError(f'Cambio ajeno: {pos}')
        if len(old) != 1 or len(b[pos]) != 1:
            raise ValueError(f'Tile duplicado: {pos}')
        pa, pb = profile(old[0], otb), profile(b[pos][0], otb)
        if pos in BRIDGE_AREA and pos not in PLACE:
            # sacar wild growth o un poste de cuerda puede liberar la casilla; nada más
            pa = (pa[0], pa[1] - {'block_solid', 'block_pathfind', 'block_projectile'})
            pb = (pb[0], pb[1] - {'block_solid', 'block_pathfind', 'block_projectile'})
        if pa != pb:
            raise ValueError(f'Cambió el paso/colisión/cambio de piso: {pos}')
        keep = lambda t: [M.serialize_tree(c, b'') for c in t[2] if not plain(c)]
        if keep(old[0]) != keep(b[pos][0]):
            raise ValueError(f'Ítem con atributos modificado: {pos}')
        changed += 1
    return changed


def run(dry_run=False):
    raw = M.MAP.read_bytes()
    root, otb = M.parse_tree(raw), M.load_otb()
    missing = sorted(OURS - set(otb))
    if missing:
        raise SystemExit(f'Faltan en el OTB {missing}: correr antes scripts/client-rme/add_custom_items.py')
    counts = apply(root, otb)
    count = validate(M.parse_tree(raw), root, otb)
    print(f'Muelle: {count} tiles; {dict(counts)}; huella, paso y escaleras conservados')
    if not dry_run:
        M.MAP.write_bytes(M.serialize_tree(root, raw[:4]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dry-run', action='store_true')
    run(ap.parse_args().dry_run)


if __name__ == '__main__':
    main()
