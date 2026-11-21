#!/usr/bin/env python3
"""Nido de Seda Negra: gruta de Giant Spiders al suroeste de la ciudad (z11).

Entrada junto al camino sur-oeste (104,80,7; salida sur 104,81,7 libre, cartel en 102,79,7):
  z7   agujero 469 en 104,80,7 + cartel 1429 en 102,79,7
  z8-z10 pozo corto de bajada (antesalas 3x3 en roca pura, sin tocar cuevas ni lava ajenas)
  z11  Nido de Seda Negra (Lv 40-65): Tarantula / Poison Spider -> Giant Spider (sueltas y de a 2) -> Wyvern

Solo ocupa vacio o roca [101] (salvo los 2 tiles de boca en z7); preserva lo ajeno y es idempotente.
Uso:
  python3 scripts/map/generate-spider-nest.py --dry-run [--preview /tmp/spider]
  python3 scripts/map/generate-spider-nest.py
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
from hole_entrance_style import style_cells
from epstein_cave_repair import index
from portal_citadel_layout import tile_flags

spec = importlib.util.spec_from_file_location("spider_helpers", HERE / "generate-imperial-crypt.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

WORLD = MAP.parent
MANIFEST = WORLD / "generated-spider-nest.json"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"

MOUTH = (105, 80)
SIGN = (103, 79)
DOWN8 = (104, 80)
DOWN9 = (105, 80)
DOWN10 = (104, 80)

# z11: x72..140, y76..138 (100% libre al sur de la Cueva del Minotauro, que termina en y<=67)
BOX11 = (72, 76, 140, 138)
# Recorrido en serpentina desde (104,80): baja al sur y recorre 3 filas separadas 14 casillas (y96, y110, y124)
PATH11 = [DOWN10, (104, 96), (80, 96), (80, 110), (130, 110), (130, 124), (80, 124)]
STAGES11 = (
    (("Tarantula", "Poison Spider"), 2, 100, 12),
    (("Tarantula", "Giant Spider"), 1, 140, 12),
    (("Giant Spider",), 1, 175, 12),
    (("Giant Spider",), 2, 210, 12),
    (("Giant Spider", "Wyvern"), 2, 235, 12),
)

PROPS_SPIDER = (1309, 1353, 4167, 4168)


def validate_walls(tmap: dict, floor: set):
    for p, ids in tmap.items():
        if p not in floor:
            want = C.pieces_for(C.neighbors_in(floor, *p), C.WALL_SIDE, C.WALL_CORNER, C.WALL_INNER)
            assert want is not None and len(want) <= 1, f"Pared ambigua en {p}: {want}"
            expected = want[0] if want else 101
            assert ids[0] == expected, f"Pared incorrecta en {p}: {ids} vs {expected}"


def make_shaft_room(up_pos, down_pos, seed):
    # Bloque compacto 2x2 en x104-105, y80-81 (pared en y79..82, 3+ casillas lejos de y75 y y85)
    fl = {(x, y) for x in (104, 105) for y in (80, 81)}
    tmap = C.cave_tiles(fl, C.grow(fl, 1), seed)
    for p in fl:
        tmap[p] = [351]
    tmap[up_pos] = [351, 1386]
    tmap[down_pos] = [469]
    tmap[(down_pos[0], down_pos[1] + 1)] = [351]
    for cand in ((105, 81), (104, 81), (104, 80), (105, 80)):
        if cand != up_pos and cand != down_pos and cand != (down_pos[0], down_pos[1] + 1):
            tmap[cand] = [351, 1423]
            break
    validate_walls(tmap, fl)
    return tmap, fl


def build(values, otb):
    previous = json.loads(MANIFEST.read_text())["cells"] if MANIFEST.exists() else {}
    bl = C.Blocking()

    t8, fl8 = make_shaft_room(MOUTH, DOWN8, 82)
    t9, fl9 = make_shaft_room(DOWN8, DOWN9, 92)
    t10, fl10 = make_shaft_room(DOWN9, DOWN10, 102)

    x0, y0, x1, y1 = BOX11
    box = {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    inner = {(x, y) for x in range(x0 + 3, x1 - 2) for y in range(y0 + 3, y1 - 2)}
    rooms = C.rooms_along(PATH11)
    band, core = C.ribbon(PATH11, rooms, 112)
    core = (core & inner) | C.grow({DOWN10}, 1)
    floor11 = C.carve_cave(112, band & inner, core, DOWN10, 1000)
    t11 = C.cave_tiles(floor11, box, 112)

    rng = random.Random("spider-nest-112")
    for p in floor11:
        r = rng.random()
        t11[p] = [355 if r < 0.35 else (352 if r < 0.65 else 351)]

    keep = C.grow({DOWN10}, 3) | {(DOWN10[0], DOWN10[1] + 1)}
    C.place_props(t11, floor11, DOWN10, PROPS_SPIDER, 0.14, 112, keep)
    # Huesos enteros (2248) y hongos (4170) no bloqueantes junto a paredes
    for p in sorted(floor11 - keep):
        if len(t11[p]) == 1 and any(q not in floor11 for q in C.grow({p}, 1)) and rng.random() < 0.06:
            t11[p].append(2248 if rng.random() < 0.65 else 4170)
    # Telaranas en paredes de la gruta
    for p, ids in t11.items():
        if ids[0] in (C.WALL_SIDE["n"], C.WALL_SIDE["w"]) and (p[0] * 5 + p[1] * 11) % 7 == 0:
            ids.append(1906 if ids[0] == C.WALL_SIDE["n"] else 1907)

    walk11 = {p for p in floor11 if bl.walkable(t11[p])}
    distances = C.reach(walk11, DOWN10, C.NP.CARD)
    assert walk11 == set(distances), "z11: decoracion corta el recorrido"
    t11[DOWN10] = [351, 1386]
    # Fogata a 2 casillas de la escalera, nunca encima
    for cand in ((DOWN10[0] - 2, DOWN10[1] + 1), (DOWN10[0] + 2, DOWN10[1] + 1)):
        if cand in walk11 and len(t11[cand]) == 1:
            t11[cand].append(1423)
            break
    validate_walls(t11, floor11)

    cells = {}
    for z, tmap in ((8, t8), (9, t9), (10, t10), (11, t11)):
        for (x, y), ids in tmap.items():
            cells[x, y, z] = ids

    # Relleno de pantalla (sin vacio negro) SOLO donde no existe tile
    for z, fl in ((8, fl8), (9, fl9), (10, fl10), (11, floor11)):
        for x, y in C.grow(fl, 9):
            p = x, y, z
            if p not in cells and (p not in values or previous.get(",".join(map(str, p))) == [101]):
                cells[p] = [101]

    # Techo en z10 sobre floor11 (y en z8/z9 sobre los rellanos si hubiera vacio)
    def walkable_existing(pos):
        if pos in cells:
            return bl.walkable(cells[pos])
        return bl.walkable(values.get(pos, []))

    for z_up, fl in ((8, fl9), (9, fl10), (10, floor11)):
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
        (*SIGN, 7): [112, 1429],
    }
    cells.update(surface)

    merged = values | cells
    for up, z in ((MOUTH, 7), (DOWN8, 8), (DOWN9, 9), (DOWN10, 10)):
        x, y = up
        assert cells[x, y, z] == [469], f"Falta bajada 469 en {up} z{z}"
        assert 1386 in cells[x, y, z + 1], f"Falta escalera 1386 en {up} z{z+1}"
        assert bl.walkable(merged.get((x, y + 1, z), [])), f"Salida sur bloqueada: {up} z{z}"
        assert bl.walkable(merged.get((x, y, z + 1), [])), f"Aterrizaje bloqueado: {up} z{z+1}"

    # Distancia de 3 casillas respecto de pisos preexistentes en z8-z11
    for z, fl in ((8, fl8), (9, fl9), (10, fl10), (11, floor11)):
        foreign = {(x, y) for (x, y, zz), ids in values.items()
                   if zz == z and bl.walkable(ids) and f"{x},{y},{zz}" not in previous}
        overlap = C.grow(fl, 3) & foreign
        assert not overlap, f"z{z}: demasiado cerca de piso ajeno: {sorted(overlap)[:5]}"

    avoid = C.grow({DOWN10}, 6)
    spawns = C.place_stages(STAGES11, C.slices_by(walk11 - avoid, distances.__getitem__, len(STAGES11)),
                            walk11, avoid, 11, random.Random("spider-nest-spawns-112"))
    positions = [p for _, _, ms in spawns for _, p, _ in ms]
    assert len(positions) == len(set(positions)) and all(p in walk11 for p in positions)
    density = len(walk11) / len(positions)
    assert 25 < density < 60, f"Densidad fuera de rango: {density:.1f}"

    report = dict(
        walkable=len(walk11),
        density=round(density, 1),
        spawns=len(spawns),
        maxDistance=max(distances.values()),
        entry=[*MOUTH, 7],
        surface=[list(p) for p in surface],
    )
    style_cells(cells, values, otb)
    return cells, spawns, report


def block(text, key, body, close):
    marked = f"\t<!-- BEGIN {key} (scripts/map/generate-spider-nest.py) -->\n{body}\n\t<!-- END {key} -->\n"
    pattern = rf"[ \t]*<!-- BEGIN {key}(?: \([^>]*\))? -->.*?<!-- END {key} -->\n?"
    return re.sub(pattern, lambda _: marked, text, flags=re.S) if re.search(pattern, text, re.S) else text.replace(close, marked + close)


def render_preview(prefix: Path, cells: dict):
    tiles = load_tiles()
    tiles.update(cells)
    r = Renderer()
    x0, y0, x1, y1 = BOX11
    W, H, img = r.area(tiles, x0 - 1, y0 - 1, x1 + 1, y1 + 1, 11, highlight=DOWN10)
    Path(f"{prefix}-z11.png").write_bytes(png_bytes(W, H, img))
    W2, H2, img2 = r.area(tiles, 96, 72, 112, 86, 7, highlight=MOUTH)
    Path(f"{prefix}-z7.png").write_bytes(png_bytes(W2, H2, img2))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    args = ap.parse_args()

    raw = MAP.read_bytes()
    root = parse_tree(raw)
    otb = load_otb()
    nodes, values, areas = index(root, otb)
    assert all(len(ns) == 1 for ns in nodes.values()), "Casillas duplicadas"
    cells, spawns, report = build(values, otb)

    previous = json.loads(MANIFEST.read_text())["cells"] if MANIFEST.exists() else {}
    surf_set = {tuple(p) for p in report["surface"]}
    orig_surf = {(*MOUTH, 7): [103], (*SIGN, 7): [112]}
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
    spawn_text = block(sp, "SPIDER_NEST_SPAWNS", C.spawn_xml(spawns), "</spawns>")
    signs = READABLES.read_text(encoding="latin-1")
    sign_text = block(
        signs, "SPIDER_NEST_SIGNS",
        '\t<readable x="103" y="79" z="7" text="NIDO DE SEDA NEGRA\\nNivel 40-65.\\nTarantulas al entrar; Giant Spiders y Wyverns al fondo."/>',
        "</readables>",
    )
    changed = sum(values.get(p) != ids for p, ids in cells.items())
    counts = Counter(n for _, _, ms in spawns for n, _, _ in ms)
    print(json.dumps(report | dict(changed=changed, monsters=dict(counts)), ensure_ascii=False))
    if args.preview:
        render_preview(args.preview, cells)
    if args.dry_run:
        return

    backup = REPO / "backups/map" / ("spider-nest-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
        name="spider-nest", version=1, down10=[*DOWN10, 10],
        monsters=dict(counts), **report,
        cells={",".join(map(str, p)): ids for p, ids in sorted(cells.items())},
    ), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
