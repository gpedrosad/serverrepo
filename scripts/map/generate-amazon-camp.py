#!/usr/bin/env python3
"""Campamento de Amazonas (Lv 15-30) en una isla nueva al noroeste de la city (z7).

Acceso a pie desde la orilla oeste del Castillo Imperial (75,34,7):
  - Cartel 1429 en (74,34,7)
  - Puente de madera 405 de 2 de ancho en x=75..76, y=21..33 sobre el agua (y=22..32)
  - Isla verde (x=72..106, y=8..21) rodeada de agua 4608 (x=67..113, y=1..24) con bordes
    de costa canonicos 4644-4655, sendero de tierra, fogatas, arboles y cajas de campamento.
  - Spawns: Amazon, Valkyrie y Assassin (Lv 15-30).

Preserva lo ajeno (Castillo Imperial en y>=25, Cripta de los Ojos en 78,34,7 y lava en x<=65) y es idempotente.
Uso:
  python3.11 scripts/map/generate-amazon-camp.py --dry-run
  python3.11 scripts/map/generate-amazon-camp.py
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
MANIFEST = WORLD / "generated-amazon-camp.json"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"

WATER, GRASS, GRASS_COAST, DIRT, WOOD = 4608, 4756, 4526, 103, 405
COAST_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
COAST_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
COAST_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}

TREES = (2701, 2702, 2703, 2704, 2706)
BUSHES = (2767, 2768)
FLOWERS = (4158, 2740, 4179, 4150)
CAMP_PROPS = (1739, 1774, 1423)  # crate, barrel, campfire (nunca 1770 questbox)

SEA_BOX = (67, 1, 113, 24)
BRIDGE_XS = (75, 76)
BRIDGE_YS = range(21, 34)  # y=33 reemplaza borde de costa sur; y=21 empalma con la isla
SIGN_POS = (74, 34)
LANDING = (75, 20)

STAGES = (
    (("Amazon",), 2, 90, 7),
    (("Amazon", "Valkyrie"), 2, 105, 7),
    (("Valkyrie", "Assassin"), 2, 120, 7),
)


def build(values, otb):
    bl = C.Blocking()
    rng = random.Random("amazon-camp-701")

    x0, y0, x1, y1 = SEA_BOX
    sea_box = {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}

    # Forma organica de isla (union de 3 elipses dentro de x=72..106, y=8..21)
    land = set()
    ellipses = [
        (78.5, 15.0, 6.5, 5.8),
        (90.0, 14.5, 9.5, 6.2),
        (100.5, 14.5, 5.8, 5.2),
    ]
    for x in range(71, 108):
        for y in range(7, 22):
            if any(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 for cx, cy, rx, ry in ellipses):
                land.add((x, y))
    # Asegurar cabecera del puente dentro de la isla
    for x in range(74, 78):
        for y in range(18, 22):
            land.add((x, y))

    # Garantizar que cada borde de costa tenga una unica pieza valida (sin esquinas ambiguas)
    allowed = {(x, y) for x in range(71, 108) for y in range(7, 22)}
    # Para bordes de pasto (COAST_*): la costa vive EN la tierra que limita con el agua.
    # Usamos el complemento (water) para arreglar huecos de 1 casilla en la tierra.
    land = NP.fix_until_valid(land, allowed, COAST_SIDE, COAST_CORNER, COAST_INNER, single=True)

    # Identificar costa (tierra con algun vecino en agua) e interior
    shore = set()
    tiles = {}
    for c in sea_box:
        if c not in land:
            tiles[c] = [WATER]
        else:
            # Vecinos en agua (usamos neighbors_in sobre sea_box - land)
            w_n = NP.neighbors_in(sea_box - land, *c)
            pcs = NP.pieces_for(w_n, COAST_SIDE, COAST_CORNER, COAST_INNER)
            if pcs:
                assert len(pcs) == 1, f"Borde de costa ambiguo en {c}: {pcs}"
                tiles[c] = [GRASS_COAST, pcs[0]]
                shore.add(c)
            else:
                tiles[c] = [GRASS]

    # Puente de madera 2x13 desde (75..76, 33) hasta (75..76, 21)
    for x in BRIDGE_XS:
        for y in BRIDGE_YS:
            tiles[(x, y)] = [WOOD]
    # Cartel junto a la cabecera sur del puente
    tiles[SIGN_POS] = [GRASS, 1429]

    # Sendero interior de tierra (no toca la costa)
    interior = land - shore - {(x, y) for x in BRIDGE_XS for y in BRIDGE_YS}
    trail = set()
    waypoints = [(75, 20), (76, 20), (76, 15), (90, 15), (101, 15), (90, 11), (90, 18)]
    for (ax, ay), (bx, by) in [(waypoints[0], waypoints[2]), (waypoints[2], waypoints[3]),
                               (waypoints[3], waypoints[4]), (waypoints[3], waypoints[5]),
                               (waypoints[3], waypoints[6])]:
        x, y = ax, ay
        while (x, y) != (bx, by):
            for dx in (0, 1):
                if (x + dx, y) in interior:
                    trail.add((x + dx, y))
            if x != bx:
                x += 1 if bx > x else -1
            elif y != by:
                y += 1 if by > y else -1
        if (bx, by) in interior:
            trail.add((bx, by))
    for p in trail:
        tiles[p] = [DIRT]

    # Decoracion de campamento (3 fogatas con cajas/barriles cerca, arboles en perimetro interior)
    camp_centers = [(81, 13), (91, 13), (99, 14)]
    keep = C.grow({LANDING, (76, 20)}, 2) | trail
    for cx, cy in camp_centers:
        if (cx, cy) in interior and (cx, cy) not in keep:
            tiles[(cx, cy)] = [DIRT, 1423]
            for dx, dy, prop in ((-1, 0, 1739), (1, 0, 1774)):
                q = (cx + dx, cy + dy)
                if q in interior and q not in keep and len(tiles[q]) == 1:
                    tiles[q] = [DIRT, prop]

    # Arboles y arbustos solo en borde interior, verificando no aislar ninguna casilla
    for p in sorted(interior - keep):
        if len(tiles[p]) != 1:
            continue
        near_shore = any(q in shore for q in C.grow({p}, 1))
        if near_shore and rng.random() < 0.22:
            prop = rng.choice(TREES if rng.random() < 0.65 else BUSHES)
            tiles[p].append(prop)
            walk_tmp = {q for q in (land | {(x, y) for x in BRIDGE_XS for y in BRIDGE_YS}) if bl.walkable(tiles[q])}
            if len(C.reach(walk_tmp, (75, 33), C.NP.CARD)) != len(walk_tmp):
                tiles[p].pop()
        elif not near_shore and rng.random() < 0.04:
            prop = rng.choice(BUSHES)
            tiles[p].append(prop)
            walk_tmp = {q for q in (land | {(x, y) for x in BRIDGE_XS for y in BRIDGE_YS}) if bl.walkable(tiles[q])}
            if len(C.reach(walk_tmp, (75, 33), C.NP.CARD)) != len(walk_tmp):
                tiles[p].pop()
        elif rng.random() < 0.07:
            tiles[p].append(rng.choice(FLOWERS))

    # Verificar conectividad total desde cabecera del puente (75,33)
    walk = {p for p in (land | {(x, y) for x in BRIDGE_XS for y in BRIDGE_YS}) if bl.walkable(tiles[p])}
    dist = C.reach(walk, (75, 33), C.NP.CARD)
    assert walk == set(dist), f"Casillas aisladas: {len(walk - set(dist))}"

    # Spawns solo dentro de la isla interior (lejos del puente y nunca encima de fogatas 1423)
    island_walk = {p for p in (walk & interior) if 1423 not in tiles[p]}
    avoid = C.grow({LANDING, (76, 20)}, 5) | set(camp_centers)
    spawns = C.place_stages(
        STAGES,
        C.slices_by(island_walk - avoid, dist.__getitem__, len(STAGES)),
        island_walk, avoid, 7, random.Random("amazon-camp-spawns-701"),
    )
    positions = [p for _, _, ms in spawns for _, p, _ in ms]
    assert len(positions) == len(set(positions)) and all(p in island_walk for p in positions)

    cells = {(x, y, 7): ids for (x, y), ids in tiles.items()}
    report = dict(
        walkable=len(island_walk),
        density=round(len(island_walk) / len(positions), 1),
        spawns=len(spawns),
        entry=[75, 33, 7],
    )
    return cells, spawns, report


def block(text, key, body, close):
    marked = f"\t<!-- BEGIN {key} (scripts/map/generate-amazon-camp.py) -->\n{body}\n\t<!-- END {key} -->\n"
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
    allowed_orig = {
        (75, 33, 7): [4526, 4644],
        (76, 33, 7): [4526, 4644],
        (74, 34, 7): [4756],
    }
    for p, ids in cells.items():
        old = values.get(p)
        owned = previous.get(",".join(map(str, p))) == old
        if p in allowed_orig:
            if not owned and old != allowed_orig[p]:
                raise ValueError(f"Cabecera modificada: {p}: {old}")
        elif old not in (None, [WATER]) and not owned:
            raise ValueError(f"Tile ajeno protegido: {p}: {old}")
        for tile in nodes.get(p, []):
            assert tile[0] == 5 and not tile_flags(tile[1]), f"Casa/flags protegidos: {p}"
            assert all(c[0] == 6 and len(c[1]) == 2 and not c[2] for c in tile[2]), f"Atributos protegidos: {p}"

    sp = SPAWNS.read_text(encoding="latin-1")
    spawn_text = block(sp, "AMAZON_CAMP_SPAWNS", C.spawn_xml(spawns), "</spawns>")
    signs = READABLES.read_text(encoding="latin-1")
    sign_text = block(
        signs, "AMAZON_CAMP_SIGNS",
        '\t<readable x="74" y="34" z="7" text="AMAZON CAMP\\nLevel 15-30.\\nAmazons, Valkyries and Assassins across the northern bridge."/>',
        "</readables>",
    )
    changed = sum(values.get(p) != ids for p, ids in cells.items())
    counts = Counter(n for _, _, ms in spawns for n, _, _ in ms)
    print(json.dumps(report | dict(changed=changed, monsters=dict(counts)), ensure_ascii=False))
    if args.dry_run:
        return

    backup = REPO / "backups/map" / ("amazon-camp-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
        name="amazon-camp", version=1,
        monsters=dict(counts), **report,
        cells={",".join(map(str, p)): ids for p, ids in sorted(cells.items())},
    ), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
