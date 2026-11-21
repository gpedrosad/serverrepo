#!/usr/bin/env python3
"""Santuario Petrificado bajo el lago elfico. Solo ocupa roca/vacio; preserva lo ajeno.

python3.11 scripts/map/generate-petrified-sanctuary.py [--dry-run]
Doc: docs/gameplay/PETRIFIED_SANCTUARY.md. No levanta servidor ni ejecuta pruebas de juego.
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

spec = importlib.util.spec_from_file_location("sanctuary_helpers", HERE / "generate-imperial-crypt.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
WORLD = MAP.parent
MANIFEST = WORLD / "generated-petrified-sanctuary.json"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MOUTH, DOWN, BOSS = (94, 74), (92, 77), (24, 41)
PATH = [(92, 77), (24, 77), (24, 59), (86, 59), (86, 41), BOSS]
STAGES = (
    (("Gargoyle",), 1, 120, 13),
    (("Gargoyle", "Stone Golem"), 1, 145, 12),
    (("Stone Golem",), 2, 170, 12),
    (("Stone Golem", "Crystal Spider"), 1, 200, 12),
    (("Crystal Spider",), 2, 240, 12),
)


def build(values, otb):
    seed = 76
    previous = json.loads(MANIFEST.read_text())["cells"] if MANIFEST.exists() else {}
    box = {(x, y) for x in range(14, 103) for y in range(31, 87)}
    inner = {(x, y) for x in range(18, 99) for y in range(35, 83)}
    band, core = C.ribbon(PATH, C.rooms_along(PATH), seed)
    core &= inner
    floor = C.carve_cave(seed, band & inner, core, DOWN, 1000)
    t9 = C.cave_tiles(floor, box, seed)
    # Fragmentos del pavimento ceremonial dentro de la cueva natural.
    paved = C.stamp(PATH, 0)
    for p in floor:
        t9[p] = [431]
        if p in paved and (p[0] // 6 + p[1] // 6) % 4 < 2:
            t9[p] = [966]
        if abs(p[0] - BOSS[0]) <= 3 and abs(p[1] - BOSS[1]) <= 3:
            t9[p] = [406]
    keep = C.grow({DOWN}, 3) | C.grow({BOSS}, 4)
    C.place_props(t9, floor, DOWN, (1452, 1453, 1515, 3767), 0.18, seed, keep)
    for dx, dy in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
        p = BOSS[0] + dx, BOSS[1] + dy
        if p in floor:
            t9[p].append(20223)
    bl = C.Blocking()
    walk = {p for p in floor if bl.walkable(t9[p])}
    distances = C.reach(walk, DOWN, C.NP.CARD)
    assert walk == set(distances), "Decoracion corta el recorrido"
    assert BOSS in walk and distances[BOSS] > 200, "Se corto la progresion del santuario"
    late = {p for p in floor if max((distances.get(q, 0) for q in C.grow({p}, 1)))
            > max(distances.values()) * 0.6}
    # Sustituir estatuas del fondo por cristales, sin cambiar el paso.
    for p in late:
        if len(t9[p]) > 1:
            t9[p][-1] = 20223 if (p[0] + p[1]) % 2 else 4995
    t9[DOWN].append(1386)
    # Telas sobre paredes del tramo de cristal; no obstruyen el piso.
    for p, ids in t9.items():
        if ids[0] in (C.WALL_SIDE["n"], C.WALL_SIDE["w"]) and p[1] < 48 and sum(p) % 7 == 0:
            ids.append(1906 if ids[0] == C.WALL_SIDE["n"] else 1907)
        elif ids[0] == C.WALL_SIDE["n"] and p[1] < 66 and sum(p) % 11 == 0:
            ids.append(20259)
    # Piezas exactas, una por borde (nunca roca lisa junto al piso).
    for p, ids in t9.items():
        if p not in floor:
            want = C.pieces_for(C.neighbors_in(floor, *p), C.WALL_SIDE, C.WALL_CORNER, C.WALL_INNER)
            assert want is not None and len(want) <= 1, (p, want)
            assert ids[0] == (want[0] if want else 101), (p, ids, want)
    # Familia de pared petrea 371-382: mismas doce orientaciones que tierra 356-367.
    for ids in t9.values():
        if 356 <= ids[0] <= 367:
            ids[0] += 15
    cells = {(x, y, 9): ids for (x, y), ids in t9.items()}
    # Relleno de pantalla y techo SOLO donde no existe tile.
    for x, y in C.grow(floor, 9):
        p = x, y, 9
        if p not in cells and (p not in values or previous.get(",".join(map(str, p))) == [101]):
            cells[p] = [101]
    for x, y in C.grow(floor, 1):
        p = x, y, 8
        if p not in values or previous.get(",".join(map(str, p))) == [101]:
            cells[p] = [101]
    # Antesala en z8, separada por la pared vieja de la cueva de rotworms (x95).
    shaft = {(x, y) for x in (91, 92) for y in range(73, 79)} | {
        (x, y) for x in (93, 94) for y in (73, 74)}
    shaft_box = C.grow(shaft, 1)
    t8 = C.cave_tiles(shaft, shaft_box, seed)
    for p in shaft:
        t8[p] = [966]
    t8[MOUTH].append(1386)
    t8[DOWN] = [469]
    t8[(91, 72)].append(20259)
    for ids in t8.values():
        if 356 <= ids[0] <= 367:
            ids[0] += 15
    for (x, y), ids in t8.items():
        old = values.get((x, y, 8))
        owned = previous.get(f"{x},{y},8") == old
        if old and old != [101] and not owned and (x, y) not in shaft:
            assert not bl.walkable(old), f"Antesala toca piso ajeno: {(x, y)}"
            continue
        cells[x, y, 8] = ids
    # La boca usa tierra firme del extremo del puente; salida sur libre.
    surface = {(*MOUTH, 7): [469], (94, 75, 7): [406], (94, 73, 7): [4756],
               (95, 74, 7): [4756], (95, 75, 7): [4526, 4655, 1429]}
    cells.update(surface)
    merged = values | cells
    for up, z in ((MOUTH, 7), (DOWN, 8)):
        x, y = up
        assert cells[x, y, z] == [469]
        assert 1386 in cells[x, y, z + 1]
        assert bl.walkable(merged.get((x, y + 1, z), [])), f"Salida bloqueada: {up} z{z}"
        assert bl.walkable(merged.get((x, y, z + 1), []))
    # Respetar al menos tres casillas respecto de cualquier piso preexistente de z9.
    foreign = {(x, y) for (x, y, z), ids in values.items() if z == 9 and bl.walkable(ids)
               and ",".join(map(str, (x, y, z))) not in previous}
    assert not (C.grow(floor, 3) & foreign), "Otra cueva demasiado cerca"
    avoid = C.grow({DOWN}, 6) | C.grow({BOSS}, 8)
    spawns = C.place_stages(STAGES, C.slices_by(walk - avoid, distances.__getitem__, len(STAGES)),
                            walk, avoid, 9, random.Random("petrified-sanctuary-76"))
    spawns.append((BOSS, 9, [("Lake Custodian", BOSS, 900)]))
    positions = [p for _, _, ms in spawns for _, p, _ in ms]
    assert len(positions) == len(set(positions)) and all(p in walk for p in positions)
    density = len(walk) / len(positions)
    assert 25 < density < 65, f"Densidad fuera de rango: {density}"
    style_cells(cells, values, otb)
    return cells, spawns, dict(walkable=len(walk), density=round(density, 1),
                              bossDistance=distances[BOSS], surface=[list(p) for p in surface])


def block(text, key, body, close):
    marked = f"\t<!-- BEGIN {key} (scripts/map/generate-petrified-sanctuary.py) -->\n{body}\n\t<!-- END {key} -->\n"
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
    surface = {tuple(p) for p in report["surface"]}
    original_surface = {(94, 74, 7): [4756], (94, 75, 7): [4526, 4654],
                        (94, 73, 7): [4756], (95, 74, 7): [4756], (95, 75, 7): [4526, 4655]}
    # No desplazar estructuras ni atributos. Una segunda pasada solo acepta su propia salida.
    for p, ids in cells.items():
        old = values.get(p)
        owned = previous.get(",".join(map(str, p))) == old
        if p in surface and not owned and old != original_surface[p]:
            raise ValueError(f"Entrada modificada por otra zona: {p}: {old}")
        if p not in surface and old not in (None, [101]) and not owned:
            raise ValueError(f"Tile ajeno protegido: {p}: {old}")
        for tile in nodes.get(p, []):
            assert tile[0] == 5 and not tile_flags(tile[1]), f"Casa/flags protegidos: {p}"
            assert all(c[0] == 6 and len(c[1]) == 2 and not c[2] for c in tile[2]), f"Atributos protegidos: {p}"
    old_cells = set(previous)
    assert old_cells <= {",".join(map(str, p)) for p in cells}, "La receta nueva deja restos; revisar antes de reducir"
    # Todos los monstruos de otras zonas permanecen fuera del bloque administrado.
    sp = SPAWNS.read_text(encoding="latin-1")
    spawn_text = block(sp, "PETRIFIED_SANCTUARY_SPAWNS", C.spawn_xml(spawns), "</spawns>")
    signs = READABLES.read_text(encoding="latin-1")
    sign_text = block(signs, "PETRIFIED_SANCTUARY_SIGNS",
        '\t<readable x="95" y="75" z="7" text="PETRIFIED SANCTUARY\\nGargoyles and Golems at the entrance.\\nCrystals and the Lake Custodian in the depths."/>', "</readables>")
    changed = sum(values.get(p) != ids for p, ids in cells.items())
    counts = Counter(n for _, _, ms in spawns for n, _, _ in ms)
    print(json.dumps(report | dict(changed=changed, monsters=dict(counts)), ensure_ascii=False))
    if args.dry_run:
        return
    backup = REPO / "backups/map" / ("petrified-sanctuary-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
    MANIFEST.write_text(json.dumps(dict(name="petrified-sanctuary", version=1, path=PATH,
        entry=[*MOUTH, 7], down=[*DOWN, 8], boss=[*BOSS, 9], monsters=dict(counts), **report,
        cells={",".join(map(str, p)): ids for p, ids in sorted(cells.items())}), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
