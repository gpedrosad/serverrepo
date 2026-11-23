#!/usr/bin/env python3
"""Demona Local / Camara de Warlocks y Behemoths (Lv 75-120+) bajo la zona sur (z12).

Entrada junto al lado oeste de la Torre del Mago Oscuro (119,129,7):
  z7   agujero 469 en 119,129,7 (salida sur 119,130,7 libre) + cartel 1429 en 118,128,7
       + puerta 1220 en la pared oeste de la torre (120,130,7): la franja de pasto de la entrada queda
       encerrada entre el río y la torre, así que se llega cruzando la torre (puerta este 128,128,7)
  z8   corredor de piedra (119,129 -> 119,134) sorteando la lava de z9 (y <= 130)
  z9   antesala 2x2 (119,134 -> 120,134)
  z10  antesala 2x2 (120,134 -> 119,134)
  z11  antesala 2x2 (119,134 -> 120,134)
  z12  Vestibulo central (120,134) con dos alas separadas y columnas para cortar linea de vision:
       - Ala de Piedra (oeste): Cyclops Smith / Stone Golem -> Behemoths + Wyrms
       - Ala Arcana (este): Priestess / Necromancer -> Warlocks sueltos (separacion 12-13)

Solo ocupa vacio o roca [101] (salvo los 3 tiles de entrada en z7: agujero, cartel y puerta); preserva lo ajeno y es idempotente.
Uso:
  python3.11 scripts/map/generate-demona-local.py --dry-run
  python3.11 scripts/map/generate-demona-local.py
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
import random
import re
import shutil
import struct
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "kb")]
from mapdata import MAP, REPO, load_otb, parse_tree, serialize_tree
from hole_entrance_style import style_cells
from epstein_cave_repair import index
from portal_citadel_layout import tile_flags

spec = importlib.util.spec_from_file_location("demona_helpers", HERE / "generate-imperial-crypt.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

WORLD = MAP.parent
MANIFEST = WORLD / "generated-demona-local.json"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"

MOUTH = (119, 129)
SIGN = (118, 128)
DOOR = (120, 130)              # acceso: pared oeste de la Torre del Mago Oscuro (1049 -> puerta abierta 1220)
DOWN8 = (119, 134)
DOWN9 = (120, 134)
DOWN10 = (119, 134)
DOWN11 = (120, 134)

# Dos alas en z12, ambas dentro de x=70..206, y=94..150 (100% libre)
# Ala de Piedra (oeste): x=70..124, y=94..150; conecta con vestibulo en (120,134)
BOX_STONE = (70, 94, 126, 150)
PATH_STONE = [
    (112, 134), (112, 142), (78, 142), (78, 128),
    (112, 128), (112, 114), (78, 114), (78, 100), (112, 100),
]
STAGES_STONE = (
    (("Cyclops Smith", "Stone Golem"), 1, 130, 12),
    (("Behemoth",), 1, 210, 12),
    (("Behemoth", "Wyrm"), 2, 230, 12),
    (("Behemoth", "Wyrm"), 2, 245, 12),
    (("Behemoth",), 2, 260, 12),
)

# Ala Arcana (este): x=132..186, y=94..150; conecta por pasillo corto desde (120,134) hasta (140,134)
BOX_ARCANE = (132, 94, 186, 150)
PATH_ARCANE = [
    (140, 134), (140, 142), (178, 142), (178, 128),
    (140, 128), (140, 114), (178, 114), (178, 100), (140, 100),
]
STAGES_ARCANE = (
    (("Priestess", "Necromancer"), 1, 140, 12),
    (("Warlock",), 1, 240, 13),
    (("Warlock",), 1, 255, 13),
    (("Warlock",), 1, 270, 13),
)

STONE_FLOOR, DARK_FLOOR, COB_FLOOR = 431, 966, 407
PILLAR_ID = 1514  # columna de piedra para cortar linea de vision
PROPS_DEMONA = (1309, 1353, 1514, 1484)
FLOOR_NO_BLOCK = (2248, 4170)


def to_stone_walls(tmap: dict):
    for ids in tmap.values():
        if 356 <= ids[0] <= 367:
            ids[0] += 15


def validate_walls(tmap: dict, floor: set):
    for p, ids in tmap.items():
        if p not in floor:
            want = C.pieces_for(C.neighbors_in(floor, *p), C.WALL_SIDE, C.WALL_CORNER, C.WALL_INNER)
            assert want is not None and len(want) <= 1, f"Pared ambigua en {p}: {want}"
            expected = (want[0] + 15) if want else 101
            assert ids[0] == expected, f"Pared incorrecta en {p}: {ids} vs {expected}"


def make_shaft_room(x0: int, y0: int, up_pos, down_pos, seed: int):
    fl = {(x, y) for x in (x0, x0 + 1) for y in (y0, y0 + 1)}
    tmap = C.cave_tiles(fl, C.grow(fl, 1), seed)
    to_stone_walls(tmap)
    for p in fl:
        tmap[p] = [STONE_FLOOR]
    tmap[up_pos] = [STONE_FLOOR, 1386]
    tmap[down_pos] = [469]
    tmap[(down_pos[0], down_pos[1] + 1)] = [STONE_FLOOR]
    for cand in sorted(fl):
        if cand != up_pos and cand != down_pos and cand != (down_pos[0], down_pos[1] + 1):
            tmap[cand] = [STONE_FLOOR, 1423]
            break
    validate_walls(tmap, fl)
    return tmap, fl


def make_corridor8(seed: int):
    # Pasillo 2x7 desde (119..120, 129..135)
    fl = {(x, y) for x in (119, 120) for y in range(129, 136)}
    tmap = C.cave_tiles(fl, C.grow(fl, 1), seed)
    to_stone_walls(tmap)
    for p in fl:
        tmap[p] = [DARK_FLOOR if (p[0] + p[1]) % 3 == 0 else STONE_FLOOR]
    tmap[MOUTH] = [STONE_FLOOR, 1386]
    tmap[DOWN8] = [469]
    tmap[(DOWN8[0], DOWN8[1] + 1)] = [STONE_FLOOR]
    tmap[(120, 130)] = [STONE_FLOOR, 1423]
    tmap[(120, 134)] = [STONE_FLOOR, 1423]
    validate_walls(tmap, fl)
    return tmap, fl


def carve_wing(box_rect, path, start_pt, seed: int, min_floor: int) -> set:
    x0, y0, x1, y1 = box_rect
    inner = {(x, y) for x in range(x0 + 3, x1 - 2) for y in range(y0 + 3, y1 - 2)}
    rooms = C.rooms_along(path)
    band, core = C.ribbon(path, rooms, seed)
    core = (core & inner) | C.grow({start_pt}, 1)
    return C.carve_cave(seed, band & inner, core, start_pt, min_floor)


def build(values, otb):
    previous = json.loads(MANIFEST.read_text())["cells"] if MANIFEST.exists() else {}
    bl = C.Blocking()

    t8, fl8 = make_corridor8(308)
    t9, fl9 = make_shaft_room(119, 134, DOWN8, DOWN9, 309)
    t10, fl10 = make_shaft_room(119, 134, DOWN9, DOWN10, 310)
    t11, fl11 = make_shaft_room(119, 134, DOWN10, DOWN11, 311)

    # Tallar ambas alas por separado para garantizar separacion entre ellas y sin atajos
    fl_stone = carve_wing(BOX_STONE, PATH_STONE, (112, 134), 312, 1000)
    fl_arcane = carve_wing(BOX_ARCANE, PATH_ARCANE, (140, 134), 313, 1100)
    assert not (C.grow(fl_stone, 2) & fl_arcane), "Las dos alas se tocan"

    # Vestibulo central y pasillos cortos hacia cada ala (en bloques 2x2 para paredes limpias)
    # Vestibulo: x=118..123, y=132..137; puente oeste x=112..118, y=134..135; puente este x=123..140, y=134..135
    vestibule = {(x, y) for x in range(118, 124) for y in range(132, 138)}
    bridge_w = {(x, y) for x in range(112, 118) for y in (134, 135)}
    bridge_e = {(x, y) for x in range(124, 141) for y in (134, 135)}
    connector = vestibule | bridge_w | bridge_e
    conn = {(bx + dx, by + dy) for (x, y) in connector for bx, by in [((x // 2) * 2, (y // 2) * 2)] for dx in (0, 1) for dy in (0, 1)}
    floor12 = fl_stone | fl_arcane | conn

    full_box = {(x, y) for x in range(68, 189) for y in range(92, 153)}
    t12 = C.cave_tiles(floor12, full_box, 314)
    to_stone_walls(t12)

    rng = random.Random("demona-local-314")
    paved = C.stamp(PATH_STONE, 0) | C.stamp(PATH_ARCANE, 0) | conn
    for p in floor12:
        if p in vestibule:
            t12[p] = [COB_FLOOR]
        elif p in paved:
            t12[p] = [DARK_FLOOR if (p[0] // 4 + p[1] // 4) % 2 == 0 else STONE_FLOOR]
        elif p in fl_arcane:
            t12[p] = [DARK_FLOOR if rng.random() < 0.55 else STONE_FLOOR]
        else:
            t12[p] = [STONE_FLOOR if rng.random() < 0.65 else 355]

    keep = C.grow({DOWN11}, 3) | conn
    # Columnas y props en ambas alas (sin cortar el paso)
    C.place_props(t12, floor12, DOWN11, PROPS_DEMONA, 0.13, 314, keep)
    for p in sorted(floor12 - keep):
        if len(t12[p]) == 1 and any(q not in floor12 for q in C.grow({p}, 1)) and rng.random() < 0.05:
            t12[p].append(rng.choice(FLOOR_NO_BLOCK))

    # Escalera de subida + braseros y carteles de cada ala en el vestibulo
    t12[DOWN11] = [COB_FLOOR, 1386]
    t12[(118, 132)] = [COB_FLOOR, 1484]
    t12[(123, 132)] = [COB_FLOOR, 1484]
    t12[(118, 136)] = [COB_FLOOR, 1429]  # cartel Ala de Piedra (oeste)
    t12[(123, 136)] = [COB_FLOOR, 1429]  # cartel Ala Arcana (este)

    walk12 = {p for p in floor12 if bl.walkable(t12[p])}
    all_dist = C.reach(walk12, DOWN11, C.NP.CARD)
    assert walk12 == set(all_dist), "z12: decoracion corta el recorrido"
    validate_walls(t12, floor12)

    # Calcular distancias por ala desde la entrada de cada ala para etapas limpias
    walk_stone = walk12 & fl_stone
    walk_arcane = walk12 & fl_arcane
    dist_stone = C.reach(walk_stone, (112, 134), C.NP.CARD)
    dist_arcane = C.reach(walk_arcane, (140, 134), C.NP.CARD)

    avoid_stone = C.grow(conn, 5)
    avoid_arcane = C.grow(conn, 5)
    sp_stone = C.place_stages(
        STAGES_STONE,
        C.slices_by(walk_stone - avoid_stone, dist_stone.__getitem__, len(STAGES_STONE)),
        walk_stone, avoid_stone, 12, random.Random("demona-stone-312"),
    )
    sp_arcane = C.place_stages(
        STAGES_ARCANE,
        C.slices_by(walk_arcane - avoid_arcane, dist_arcane.__getitem__, len(STAGES_ARCANE)),
        walk_arcane, avoid_arcane, 12, random.Random("demona-arcane-313"),
    )
    spawns = sp_stone + sp_arcane
    positions = [p for _, _, ms in spawns for _, p, _ in ms]
    assert len(positions) == len(set(positions)) and all(p in walk12 for p in positions)

    cells = {}
    for z, tmap in ((8, t8), (9, t9), (10, t10), (11, t11), (12, t12)):
        for (x, y), ids in tmap.items():
            cells[x, y, z] = ids

    for z, fl in ((8, fl8), (9, fl9), (10, fl10), (11, fl11), (12, floor12)):
        for x, y in C.grow(fl, 9):
            p = x, y, z
            if p not in cells and (p not in values or (values[p] == [101] and previous.get(",".join(map(str, p))) == [101])):
                cells[p] = [101]

    def walkable_existing(pos):
        if pos in cells:
            return bl.walkable(cells[pos])
        return bl.walkable(values.get(pos, []))

    for z_up, fl in ((8, fl9), (9, fl10), (10, fl11), (11, floor12)):
        for x, y in C.grow(fl, 2):
            p = x, y, z_up
            if p in cells:
                continue
            if p in values and previous.get(",".join(map(str, p))) != [101]:
                continue
            if any(walkable_existing((x + dx, y + dy, z_up)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                continue
            cells[p] = [101]

    surface = {
        (*MOUTH, 7): [469],
        (*SIGN, 7): [4756, 1429],
        (*DOOR, 7): [4756, 1220],
    }
    cells.update(surface)

    merged = values | cells
    for up, z in ((MOUTH, 7), (DOWN8, 8), (DOWN9, 9), (DOWN10, 10), (DOWN11, 11)):
        x, y = up
        assert cells[x, y, z] == [469], f"Falta bajada 469 en {up} z{z}"
        assert 1386 in cells[x, y, z + 1], f"Falta escalera 1386 en {up} z{z+1}"
        assert bl.walkable(merged.get((x, y + 1, z), [])), f"Salida sur bloqueada: {up} z{z}"
        assert bl.walkable(merged.get((x, y, z + 1), [])), f"Aterrizaje bloqueado: {up} z{z+1}"

    for z, fl in ((8, fl8), (9, fl9), (10, fl10), (11, fl11), (12, floor12)):
        foreign = {(x, y) for (x, y, zz), ids in values.items()
                   if zz == z and bl.walkable(ids) and f"{x},{y},{zz}" not in previous}
        overlap = C.grow(fl, 3) & foreign
        assert not overlap, f"z{z}: demasiado cerca de piso ajeno: {sorted(overlap)[:5]}"

    stone_cnt = sum(len(ms) for _, _, ms in sp_stone)
    arcane_cnt = sum(len(ms) for _, _, ms in sp_arcane)
    report = dict(
        walkableStone=len(walk_stone),
        walkableArcane=len(walk_arcane),
        densityStone=round(len(walk_stone) / stone_cnt, 1),
        densityArcane=round(len(walk_arcane) / arcane_cnt, 1),
        spawns=len(spawns),
        entry=[*MOUTH, 7],
        surface=[list(p) for p in surface],
    )
    style_cells(cells, values, otb)
    return cells, spawns, report


def block(text, key, body, close):
    marked = f"\t<!-- BEGIN {key} (scripts/map/generate-demona-local.py) -->\n{body}\n\t<!-- END {key} -->\n"
    pattern = rf"[ \t]*<!-- BEGIN {key}(?: \([^>]*\))? -->.*?<!-- END {key} -->\n?"
    return re.sub(pattern, lambda _: marked, text, flags=re.S) if re.search(pattern, text, re.S) else text.replace(close, marked + close)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = MAP.read_bytes()
    root = parse_tree(raw)
    otb = load_otb()
    nodes, values, areas = index(root, otb)
    assert all(len(ns) == 1 for ns in nodes.values()), "Casillas duplicadas"
    cells, spawns, report = build(values, otb)

    previous = json.loads(MANIFEST.read_text())["cells"] if MANIFEST.exists() else {}
    surf_set = {tuple(p) for p in report["surface"]}
    orig_surf = {(*MOUTH, 7): [4756], (*SIGN, 7): [4756], (*DOOR, 7): [4756, 1049]}
    for p, ids in cells.items():
        old = values.get(p)
        owned = previous.get(",".join(map(str, p))) == old
        if p in surf_set and not owned and old != orig_surf[p]:
            raise ValueError(f"Entrada modificada por otra zona: {p}: {old}")
        if p not in surf_set and old not in (None, [101]) and not owned:
            raise ValueError(f"Tile ajeno protegido: {p}: {old}")
        for tile in nodes.get(p, []):
            assert tile[0] == 5 and not tile_flags(tile[1]), f"Casa/flags protegidos: {p}"
            assert all(c[0] == 6 and len(c[1]) == 2 and not c[2] for c in tile[2]), f"Atributos protegidos: {p}"

    sp = SPAWNS.read_text(encoding="latin-1")
    spawn_text = block(sp, "DEMONA_LOCAL_SPAWNS", C.spawn_xml(spawns), "</spawns>")
    signs = READABLES.read_text(encoding="latin-1")
    sign_body = "\n".join([
        '\t<readable x="118" y="128" z="7" text="DEEP HALLS OF DEMONA\\nLevel 75-120+.\\nTwo wings below: Stone Wing (Behemoths &amp; Wyrms) and Arcane Wing (Warlocks)."/>',
        '\t<readable x="118" y="136" z="12" text="WEST: STONE WING\\nCyclops Smith, Stone Golems, Wyrms and Behemoths."/>',
        '\t<readable x="123" y="136" z="12" text="EAST: ARCANE WING\\nPriestesses, Necromancers and Warlocks. Watch your line of sight."/>',
    ])
    sign_text = block(signs, "DEMONA_LOCAL_SIGNS", sign_body, "</readables>")
    changed = sum(values.get(p) != ids for p, ids in cells.items())
    counts = Counter(n for _, _, ms in spawns for n, _, _ in ms)
    print(json.dumps(report | dict(changed=changed, monsters=dict(counts)), ensure_ascii=False))
    if args.dry_run:
        return

    backup = REPO / "backups/map" / ("demona-local-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    for f in (MAP, SPAWNS, READABLES):
        shutil.copy2(f, backup / f.name)
    for (x, y, z), ids in sorted(cells.items()):
        key = x // 256 * 256, y // 256 * 256, z
        if key not in areas:
            areas[key] = [4, bytearray(struct.pack("<HHB", *key)), []]
            root[2][0][2].append(areas[key])
        if (x, y, z) in nodes:
            tile = nodes[x, y, z][0]
        else:
            tile = [5, bytearray([x % 256, y % 256]), []]
            areas[key][2].append(tile)
        ground = otb[ids[0]]["group"] == "ground"
        tile[1] = bytearray([x % 256, y % 256]) + (struct.pack("<BH", 9, ids[0]) if ground else b"")
        tile[2] = [C.item_node(i) for i in ids[1 if ground else 0:]]
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    SPAWNS.write_text(spawn_text, encoding="latin-1")
    READABLES.write_text(sign_text, encoding="latin-1")
    MANIFEST.write_text(json.dumps(dict(
        name="demona-local", version=1, down11=[*DOWN11, 11],
        monsters=dict(counts), **report,
        cells={",".join(map(str, p)): ids for p, ids in sorted(cells.items())},
    ), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
