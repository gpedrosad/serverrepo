#!/usr/bin/env python3
"""Gruta Submarina del Rio: cueva de Water Elementals y Quaras bajo el rio de la city (z12).

Entrada junto al camino del muelle/rio al norte de la Torre del Barquero (176,58,7):
  z7   agujero 469 en 176,58,7 (salida sur 176,59,7 libre) + cartel 1429 en 177,58,7
  z8   antesala 2x2 (176,58 -> 175,58)
  z9   antesala 2x2 (175,58 -> 176,58)
  z10  corredor de piedra (176,58 -> 176,68) sorteando la Alcantarilla Mutada de z11
  z11  antesala 2x2 (176,68 -> 177,68)
  z12  Gruta Submarina del Rio (Lv 45-75): Blood Crab / Quara Constrictor ->
       Water Elemental (10-14 sueltos y de a 2) -> Quara Hydromancer / Bog Raider

Solo ocupa vacio o roca [101] (salvo los 2 tiles de entrada en z7); preserva lo ajeno y es idempotente.
Uso:
  python3.11 scripts/map/generate-river-grotto.py --dry-run
  python3.11 scripts/map/generate-river-grotto.py
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
from mapdata import MAP, REPO, Renderer, load_otb, load_tiles, parse_tree, png_bytes, serialize_tree
from river_grotto_style import apply_river_style
from epstein_cave_repair import index
from portal_citadel_layout import tile_flags

spec = importlib.util.spec_from_file_location("grotto_helpers", HERE / "generate-imperial-crypt.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

WORLD = MAP.parent
MANIFEST = WORLD / "generated-river-grotto.json"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"

MOUTH = (176, 58)
SIGN = (177, 58)
DOWN8 = (175, 58)
DOWN9 = (176, 58)
DOWN10 = (176, 68)
DOWN11 = (177, 68)

# z12: x146..196, y20..76 (100% libre bajo el rio y centro-este de la city)
BOX12 = (146, 20, 196, 76)
# Serpentina con filas separadas 14 casillas: y68, y54, y40, y26
PATH12 = [DOWN11, (154, 68), (154, 54), (188, 54), (188, 40), (154, 40), (154, 26), (188, 26)]
STAGES12 = (
    (("Blood Crab", "Quara Constrictor"), 1, 120, 12),
    (("Water Elemental",), 1, 145, 12),
    (("Water Elemental",), 2, 165, 12),
    (("Water Elemental", "Quara Hydromancer"), 2, 195, 12),
    (("Quara Hydromancer", "Bog Raider"), 2, 220, 12),
)

STONE_FLOOR, WET_FLOOR, MUD_FLOOR = 431, 966, 355
PROPS_GROTTO = (1309, 1353, 3767, 2602)
FLOOR_NO_BLOCK = (2248, 4170)


def to_stone_walls(tmap: dict):
    for ids in tmap.values():
        if 356 <= ids[0] <= 367:
            ids[0] += 15


def validate_walls(tmap: dict, floor: set, stone: bool = True):
    for p, ids in tmap.items():
        if p not in floor:
            want = C.pieces_for(C.neighbors_in(floor, *p), C.WALL_SIDE, C.WALL_CORNER, C.WALL_INNER)
            assert want is not None and len(want) <= 1, f"Pared ambigua en {p}: {want}"
            expected = (want[0] + (15 if stone else 0)) if want else 101
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
    validate_walls(tmap, fl, stone=True)
    return tmap, fl


def make_corridor10(seed: int):
    # Corredor 2x12 desde (175..176, 58..69)
    fl = {(x, y) for x in (175, 176) for y in range(58, 70)}
    tmap = C.cave_tiles(fl, C.grow(fl, 1), seed)
    to_stone_walls(tmap)
    for p in fl:
        tmap[p] = [WET_FLOOR if (p[0] + p[1]) % 3 == 0 else STONE_FLOOR]
    tmap[DOWN9] = [STONE_FLOOR, 1386]
    tmap[DOWN10] = [469]
    tmap[(DOWN10[0], DOWN10[1] + 1)] = [STONE_FLOOR]
    tmap[(175, 59)] = [STONE_FLOOR, 1423]
    tmap[(175, 68)] = [STONE_FLOOR, 1423]
    validate_walls(tmap, fl, stone=True)
    return tmap, fl


def build(values, otb):
    previous = json.loads(MANIFEST.read_text())["cells"] if MANIFEST.exists() else {}
    bl = C.Blocking()

    t8, fl8 = make_shaft_room(175, 58, MOUTH, DOWN8, 181)
    t9, fl9 = make_shaft_room(175, 58, DOWN8, DOWN9, 191)
    t10, fl10 = make_corridor10(201)
    t11, fl11 = make_shaft_room(176, 68, DOWN10, DOWN11, 211)

    x0, y0, x1, y1 = BOX12
    box = {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    inner = {(x, y) for x in range(x0 + 3, x1 - 2) for y in range(y0 + 3, y1 - 2)}
    rooms = C.rooms_along(PATH12)
    band, core = C.ribbon(PATH12, rooms, 221)
    core = (core & inner) | C.grow({DOWN11}, 1)
    floor12 = C.carve_cave(221, band & inner, core, DOWN11, 1000)
    t12 = C.cave_tiles(floor12, box, 221)
    to_stone_walls(t12)

    rng = random.Random("river-grotto-221")
    paved = C.stamp(PATH12, 0)
    for p in floor12:
        if p in paved:
            t12[p] = [WET_FLOOR if (p[0] // 4 + p[1] // 4) % 2 == 0 else STONE_FLOOR]
        else:
            r = rng.random()
            t12[p] = [MUD_FLOOR if r < 0.35 else (WET_FLOOR if r < 0.7 else STONE_FLOOR)]

    keep = C.grow({DOWN11}, 3) | {(DOWN11[0], DOWN11[1] + 1)}
    C.place_props(t12, floor12, DOWN11, PROPS_GROTTO, 0.13, 221, keep)
    for p in sorted(floor12 - keep):
        if len(t12[p]) == 1 and any(q not in floor12 for q in C.grow({p}, 1)) and rng.random() < 0.06:
            t12[p].append(rng.choice(FLOOR_NO_BLOCK))

    walk12 = {p for p in floor12 if bl.walkable(t12[p])}
    distances = C.reach(walk12, DOWN11, C.NP.CARD)
    assert walk12 == set(distances), "z12: decoracion corta el recorrido"
    t12[DOWN11] = [STONE_FLOOR, 1386]
    for cand in ((DOWN11[0] - 2, DOWN11[1] + 1), (DOWN11[0] + 2, DOWN11[1] + 1), (DOWN11[0] - 2, DOWN11[1])):
        if cand in walk12 and len(t12[cand]) == 1:
            t12[cand].append(1423)
            break
    validate_walls(t12, floor12, stone=True)

    cells = {}
    for z, tmap in ((8, t8), (9, t9), (10, t10), (11, t11), (12, t12)):
        for (x, y), ids in tmap.items():
            cells[x, y, z] = ids

    # Relleno de pantalla sin vacio negro
    for z, fl in ((8, fl8), (9, fl9), (10, fl10), (11, fl11), (12, floor12)):
        for x, y in C.grow(fl, 9):
            p = x, y, z
            if p not in cells and (p not in values or (values[p] == [101] and previous.get(",".join(map(str, p))) == [101])):
                cells[p] = [101]

    # Techo en piso superior donde haya vacio
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
        (*SIGN, 7): [119, 1429],
    }
    cells.update(surface)

    merged = values | cells
    for up, z in ((MOUTH, 7), (DOWN8, 8), (DOWN9, 9), (DOWN10, 10), (DOWN11, 11)):
        x, y = up
        assert cells[x, y, z] == [469], f"Falta bajada 469 en {up} z{z}"
        assert 1386 in cells[x, y, z + 1], f"Falta escalera 1386 en {up} z{z+1}"
        assert bl.walkable(merged.get((x, y + 1, z), [])), f"Salida sur bloqueada: {up} z{z}"
        assert bl.walkable(merged.get((x, y, z + 1), [])), f"Aterrizaje bloqueado: {up} z{z+1}"

    # Distancia de 3 casillas respecto de pisos ajenos en z8-z12
    for z, fl in ((8, fl8), (9, fl9), (10, fl10), (11, fl11), (12, floor12)):
        foreign = {(x, y) for (x, y, zz), ids in values.items()
                   if zz == z and bl.walkable(ids) and f"{x},{y},{zz}" not in previous}
        overlap = C.grow(fl, 3) & foreign
        assert not overlap, f"z{z}: demasiado cerca de piso ajeno: {sorted(overlap)[:5]}"

    avoid = C.grow({DOWN11}, 6)
    spawns = C.place_stages(STAGES12, C.slices_by(walk12 - avoid, distances.__getitem__, len(STAGES12)),
                            walk12, avoid, 12, random.Random("river-grotto-spawns-221"))
    positions = [p for _, _, ms in spawns for _, p, _ in ms]
    assert len(positions) == len(set(positions)) and all(p in walk12 for p in positions)
    density = len(walk12) / len(positions)
    assert 25 < density < 60, f"Densidad fuera de rango: {density:.1f}"

    report = dict(
        walkable=len(walk12),
        density=round(density, 1),
        spawns=len(spawns),
        maxDistance=max(distances.values()),
        entry=[*MOUTH, 7],
        surface=[list(p) for p in surface],
    )
    report.update(apply_river_style(cells, values, otb, floor12, C.NP, positions))
    return cells, spawns, report


def block(text, key, body, close):
    marked = f"\t<!-- BEGIN {key} (scripts/map/generate-river-grotto.py) -->\n{body}\n\t<!-- END {key} -->\n"
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
    orig_surf = {(*MOUTH, 7): [103], (*SIGN, 7): [119]}
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
    spawn_text = block(sp, "RIVER_GROTTO_SPAWNS", C.spawn_xml(spawns), "</spawns>")
    signs = READABLES.read_text(encoding="latin-1")
    sign_text = block(
        signs, "RIVER_GROTTO_SIGNS",
        '\t<readable x="177" y="58" z="7" text="SUBMERGED RIVER GROTTO\\nLevel 45-75.\\nBlood Crabs and Quara Constrictors at the entrance; Water Elementals, Quara Hydromancers and Bog Raiders below."/>',
        "</readables>",
    )
    changed = sum(values.get(p) != ids for p, ids in cells.items())
    counts = Counter(n for _, _, ms in spawns for n, _, _ in ms)
    print(json.dumps(report | dict(changed=changed, monsters=dict(counts)), ensure_ascii=False))
    if args.dry_run:
        return

    backup = REPO / "backups/map" / ("river-grotto-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
        name="river-grotto", version=1, down11=[*DOWN11, 11],
        monsters=dict(counts), **report,
        cells={",".join(map(str, p)): ids for p, ids in sorted(cells.items())},
    ), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
