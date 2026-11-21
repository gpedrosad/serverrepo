#!/usr/bin/env python3
"""Campamento Barbaro (Lv 15-40) ampliando la costa de hielo al noreste de la city (z7).

Empalma al norte de la costa nevada actual (x=220..224, y=25, z=7):
  - Cartel 1429 en (224,25,7)
  - Istmo nevado en x=221..223, y=24 hacia un cabo nevado amplio (x=219..254, y=8..22)
    rodeado de agua 4608 (x=214..261, y=1..24) con bordes de nieve canonicos (NP.SNOW_*).
  - Spawns: Barbarian Headsplitter, Skullhunter, Brutetamer, Bloodwalker, Frost Giant y Frost Giantess.

Preserva la isla helada vieja (y>=25) y el Glaciar del Este (x>=263) y es idempotente.
Uso:
  python3.11 scripts/map/generate-barbarian-camp.py --dry-run
  python3.11 scripts/map/generate-barbarian-camp.py
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
from epstein_cave_repair import index
from portal_citadel_layout import tile_flags


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C = _load("generate-imperial-crypt")
NP = _load("generate-north-pass")

WORLD = MAP.parent
MANIFEST = WORLD / "generated-barbarian-camp.json"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"

WATER, WATER_EDGE, SNOW = 4608, 4619, 670
WATERS = set(range(4608, 4626)) | {4664, 4665, 4666}
PINE = 2698
DEAD_TREES = (2697, 2709, 2717)
STONES = (1285, 1309, 1336)
BONES = (2248,)

BOX = (214, 1, 261, 24)
ENTRY = (222, 24)
SIGN_POS = (224, 25)
JUNCTION_XS = range(221, 224)  # empalma con nieve existente [670] en x=220..224, y=25

STAGES = (
    (("Barbarian Headsplitter", "Barbarian Skullhunter"), 2, 95, 8),
    (("Barbarian Skullhunter", "Barbarian Brutetamer"), 2, 110, 8),
    (("Barbarian Bloodwalker", "Barbarian Brutetamer"), 2, 130, 8),
    (("Barbarian Bloodwalker", "Frost Giant", "Frost Giantess"), 2, 145, 8),
)


def build(values, otb):
    bl = C.Blocking()
    rng = random.Random("barbarian-camp-702")

    x0, y0, x1, y1 = BOX
    box = {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}

    # Cabo nevado organico (union de 3 elipses dentro de x=219..254, y=8..21) + istmo en y=22..24
    land = set()
    ellipses = [
        (225.0, 16.0, 6.2, 5.5),
        (237.5, 14.5, 9.5, 6.2),
        (248.5, 15.0, 6.0, 5.5),
    ]
    for x in range(219, 255):
        for y in range(8, 22):
            if any(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 for cx, cy, rx, ry in ellipses):
                land.add((x, y))
    for x in JUNCTION_XS:
        for y in range(20, 25):
            land.add((x, y))

    # Tierra vieja justo al sur de la caja (y=25..26) para empalmar bordes sin cortes
    old_land = {
        (x, y) for (x, y, z), ids in values.items()
        if z == 7 and (x, y) not in box and ids[0] not in WATERS
        and x0 - 2 <= x <= x1 + 2 and y1 + 1 <= y <= y1 + 2
    }
    allowed = {(x, y) for x in range(219, 255) for y in range(8, 22)} | {
        (x, y) for x in JUNCTION_XS for y in range(21, 25)
    }
    grown = NP.fix_until_valid(land | old_land, allowed | old_land,
                               NP.SNOW_SIDE, NP.SNOW_CORNER, NP.SNOW_INNER, single=True)
    land = (grown - old_land) & box
    land_all = land | old_land
    water = box - land

    tiles = {}
    for c in box:
        x, y = c
        if c in water:
            pcs = NP.pieces_for(NP.neighbors_in(land_all, x, y),
                                NP.SNOW_SIDE, NP.SNOW_CORNER, NP.SNOW_INNER)
            assert pcs is None or len(pcs) <= 1, f"Borde de nieve ambiguo en {c}: {pcs}"
            tiles[c] = [WATER_EDGE] + pcs if pcs else [WATER]
        else:
            tiles[c] = [SNOW]

    # Cartel junto al empalme sur (en nieve vieja 224,25)
    tiles[SIGN_POS] = [SNOW, 1429]

    # Sendero central y 3 fogatas de campamento barbaro
    trail = set()
    segs = [((222, 24), (222, 16)), ((222, 16), (237, 15)), ((237, 15), (249, 15)), ((237, 15), (237, 11))]
    for (ax, ay), (bx, by) in segs:
        x, y = ax, ay
        while (x, y) != (bx, by):
            for dx in (0, 1):
                if (x + dx, y) in land:
                    trail.add((x + dx, y))
            if x != bx:
                x += 1 if bx > x else -1
            elif y != by:
                y += 1 if by > y else -1
        if (bx, by) in land:
            trail.add((bx, by))

    keep = C.grow({ENTRY}, 2) | trail
    for cx, cy in ((226, 14), (237, 17), (248, 13)):
        if (cx, cy) in land and (cx, cy) not in keep:
            tiles[(cx, cy)] = [SNOW, 1423]
            for dx, dy, prop in ((-1, 0, 1739), (1, 0, 1774)):
                q = (cx + dx, cy + dy)
                if q in land and q not in keep and len(tiles[q]) == 1:
                    tiles[q] = [SNOW, prop]

    # Pinos, piedras y huesos respetando conectividad
    for p in sorted(land - keep):
        if len(tiles[p]) != 1:
            continue
        near_edge = any(q in water for q in C.grow({p}, 1))
        if near_edge and rng.random() < 0.24:
            prop = PINE if rng.random() < 0.65 else rng.choice(DEAD_TREES + STONES)
            tiles[p].append(prop)
            walk_tmp = {q for q in land if bl.walkable(tiles[q])}
            if len(C.reach(walk_tmp, ENTRY, C.NP.CARD)) != len(walk_tmp):
                tiles[p].pop()
        elif not near_edge and rng.random() < 0.05:
            prop = rng.choice(STONES)
            tiles[p].append(prop)
            walk_tmp = {q for q in land if bl.walkable(tiles[q])}
            if len(C.reach(walk_tmp, ENTRY, C.NP.CARD)) != len(walk_tmp):
                tiles[p].pop()
        elif rng.random() < 0.04:
            tiles[p].append(rng.choice(BONES))

    walk = {p for p in land if bl.walkable(tiles[p])}
    dist = C.reach(walk, ENTRY, C.NP.CARD)
    assert walk == set(dist), f"Casillas aisladas: {len(walk - set(dist))}"

    avoid = C.grow({ENTRY}, 5) | {(226, 14), (237, 17), (248, 13)}
    spawns = C.place_stages(
        STAGES,
        C.slices_by(walk - avoid, dist.__getitem__, len(STAGES)),
        walk, avoid, 7, random.Random("barbarian-camp-spawns-702"),
    )
    positions = [p for _, _, ms in spawns for _, p, _ in ms]
    assert len(positions) == len(set(positions)) and all(p in walk and 1423 not in tiles[p] for p in positions)

    cells = {(x, y, 7): ids for (x, y), ids in tiles.items()}
    report = dict(
        walkable=len(walk),
        density=round(len(walk) / len(positions), 1),
        spawns=len(spawns),
        entry=[*ENTRY, 7],
    )
    return cells, spawns, report


def block(text, key, body, close):
    marked = f"\t<!-- BEGIN {key} (scripts/map/generate-barbarian-camp.py) -->\n{body}\n\t<!-- END {key} -->\n"
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
    orig_join = {
        (220, 24, 7): [4619, 4739],
        (221, 24, 7): [4619, 4739],
        (222, 24, 7): [4619, 4739],
        (223, 24, 7): [4619, 4739],
        (224, 24, 7): [4619, 4739],
        (225, 24, 7): [4619, 4743],
        (224, 25, 7): [670],
    }
    for p, ids in cells.items():
        old = values.get(p)
        owned = previous.get(",".join(map(str, p))) == old
        if p in orig_join:
            if not owned and old != orig_join[p]:
                raise ValueError(f"Empalme modificado: {p}: {old}")
        elif old not in (None, [WATER]) and not owned:
            raise ValueError(f"Tile ajeno protegido: {p}: {old}")
        for tile in nodes.get(p, []):
            assert tile[0] == 5 and not tile_flags(tile[1]), f"Casa/flags protegidos: {p}"
            if not owned:
                assert all(c[0] == 6 and len(c[1]) == 2 and not c[2] for c in tile[2]), f"Atributos protegidos: {p}"

    sp = SPAWNS.read_text(encoding="latin-1")
    spawn_text = block(sp, "BARBARIAN_CAMP_SPAWNS", C.spawn_xml(spawns), "</spawns>")
    signs = READABLES.read_text(encoding="latin-1")
    sign_text = block(
        signs, "BARBARIAN_CAMP_SIGNS",
        '\t<readable x="224" y="25" z="7" text="BARBARIAN CAMP\\nLevel 15-40.\\nBarbarian raiders and Frost Giants across the northern snowfields."/>',
        "</readables>",
    )
    changed = sum(values.get(p) != ids for p, ids in cells.items())
    counts = Counter(n for _, _, ms in spawns for n, _, _ in ms)
    print(json.dumps(report | dict(changed=changed, monsters=dict(counts)), ensure_ascii=False))
    if args.dry_run:
        return

    backup = REPO / "backups/map" / ("barbarian-camp-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
        name="barbarian-camp", version=1,
        monsters=dict(counts), **report,
        cells={",".join(map(str, p)): ids for p, ids in sorted(cells.items())},
    ), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
