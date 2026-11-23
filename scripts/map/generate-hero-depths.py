#!/usr/bin/env python3
"""Profundidades del Héroe: mazmorra de 5 pisos (z10-z14) debajo del lugar de los Hero (146,93,9).

Mismo estilo que el lugar de arriba: losa negra 407, ladrillo (1028/1030/1027/1033), tapices rojos 1812
en las paredes del norte, antorchas, monumentos y ataúdes, y lava 598 alrededor (en vez de vacío negro).
Monstruo: Black Knight (1600 exp, el escalón siguiente al Hero), de a 1 arriba y de a 2 en el fondo.

Bajadas (hueco 432 arriba, escalera 1385 en la misma casilla abajo; se llega a y+1 al bajar y a y-1 al subir):
  z9  146,93  ->  z10 antesala  -> 153,106 -> z11 galería -> 160,87 -> z12 puente -> 128,81
  -> z13 salón de los caballeros -> 164,80 -> z14 fondo.

Solo usa casillas vacías o de roca [101] (de cualquier generador) y deja 4 casillas o más entre su piso y el
piso de otro (los generadores vecinos lo validan con grow(piso, 3)). Lava en el vacío a la vista y roca de
techo encima donde el piso de arriba está vacío. Es idempotente.

  python3.11 scripts/map/generate-hero-depths.py --dry-run [--preview /tmp/hero-depths.png]
  python3.11 scripts/map/generate-hero-depths.py
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
DC = _load("generate-dark-cathedral")         # PIECE_BY_NEIGHBORS (tabla de paredes medida en el mapa)

WORLD = MAP.parent
MANIFEST = WORLD / "generated-hero-depths.json"
SPAWNS = WORLD / "test-spawn.xml"

FLOOR, LAVA, ROCK = 407, 598, 101
HOLE, STAIRS = 432, 1385
BRICK = dict(h=1028, v=1030, nw=1027, se=1033)
TAPESTRY, TORCH_H, TORCH_V = 1812, 2059, 2061
MONUMENT, COFFIN_HEAD, COFFIN_FOOT, BANNER = 1445, 1410, 1411, 1822
PILLAR, COAL_BASIN = 1515, 1486
MONSTER = "Black Knight"
VIEW = (9, 7)                                   # media pantalla + colchón: lava donde haya vacío
FOREIGN_GAP = 4                                 # piso propio a 4+ casillas del piso ajeno

TOP = (146, 93, 9)                              # el hueco en el pasillo de los Hero

# Bajadas: (x, y, z) del hueco; abajo la escalera va en (x, y, z+1).
HOLES = [TOP, (134, 86, 10), (158, 83, 11), (127, 82, 12), (164, 80, 13)]

# Planta de cada piso: rectángulos de piso (x0, y0, x1, y1). Las paredes salen solas alrededor.
# Demona Local (z11 y>=94, z12 y>=87) no se toca y sus jugadores no ven estas salas (z12 hasta y=86).
PLAN = {
    10: [(145, 93, 147, 96), (140, 94, 144, 96), (128, 84, 139, 96)],
    11: [(128, 84, 140, 92), (141, 88, 148, 90), (149, 82, 166, 92)],
    12: [(153, 80, 163, 85), (133, 82, 152, 84), (122, 80, 132, 85)],
    13: [(122, 80, 134, 90), (127, 91, 129, 100), (119, 101, 141, 111), (142, 104, 156, 106),
         (157, 95, 172, 114), (163, 84, 165, 94), (156, 77, 172, 83)],
    14: [(157, 79, 171, 91), (163, 92, 165, 96), (139, 97, 171, 112)],
}
# Manifiestos de otros generadores cuyas casillas nunca se tocan (su generador las reescribe y fallaría).
# mutated-sewers, spider-nest y river-grotto solo rellenan vacío o su roca: se comprobó con su --dry-run.
TOUCH_OK = {"mutated-sewers", "spider-nest", "river-grotto"}
# Black Knights por piso: (por spawn, spawntime, separación mínima entre centros)
STAGES = {10: (1, 120, 14), 11: (1, 120, 13), 12: (1, 120, 13), 13: (1, 120, 12), 14: (2, 150, 13)}


def rects(rs):
    return {(x, y) for x0, y0, x1, y1 in rs for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def ring(cells):
    return {(x + dx, y + dy) for x, y in cells for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - cells


def wall_piece(mask, c):
    x, y = c
    key = ((x - 1, y) in mask, (x, y - 1) in mask, (x + 1, y) in mask, (x, y + 1) in mask)
    return BRICK[DC.PIECE_BY_NEIGHBORS[key]]


def protected_cells():
    out = set()
    for f in WORLD.glob("generated-*.json"):
        name = f.stem.removeprefix("generated-")
        if name in TOUCH_OK or name == "hero-depths":
            continue
        cells = json.loads(f.read_text()).get("cells") or {}
        if isinstance(cells, dict):
            for key in cells:
                try:
                    out.add(tuple(int(v) for v in key.split(",")[:3]))
                except ValueError:
                    pass
    return out


def build(values, otb):
    bl = C.Blocking()
    protected = protected_cells()
    rng = random.Random("hero-depths-1")
    cells = {}                                  # (x, y, z) -> ids
    floors, spawns = {}, []

    def walkable_foreign(z):
        return {(x, y) for (x, y, zz), ids in values.items() if zz == z and bl.walkable(ids)}

    for z, plan in PLAN.items():
        floor = rects(plan)
        walls = ring(floor)
        floors[z] = floor
        foreign = walkable_foreign(z) - floor
        close = C.grow(floor, FOREIGN_GAP) & foreign
        assert not close, f"z{z}: piso a menos de {FOREIGN_GAP} de piso ajeno: {sorted(close)[:5]}"
        for (x, y) in floor | walls:
            old = values.get((x, y, z))
            assert old in (None, [ROCK]), f"z{z}: casilla ajena {x},{y}: {old}"
            assert (x, y, z) not in protected, f"z{z}: casilla de otro generador {x},{y}"
        for c in floor:
            cells[(*c, z)] = [FLOOR]
        for (x, y) in walls:
            inside = any(p in floor for p in ((x - 1, y), (x, y - 1), (x - 1, y - 1)))
            cells[(x, y, z)] = [FLOOR if inside else LAVA, wall_piece(walls, (x, y))]

        # lava a la vista: en el vacío y sobre la roca [101] que no ve ningún jugador de otra zona
        # (los generadores vecinos solo rellenan vacío o su roca [101]: la lava no la tocan)
        seen_by_others = {(x + dx, y + dy) for x, y in foreign
                          for dx in range(-VIEW[0], VIEW[0] + 1) for dy in range(-VIEW[1], VIEW[1] + 1)}
        for x, y in {(x + dx, y + dy) for x, y in floor
                     for dx in range(-VIEW[0], VIEW[0] + 1) for dy in range(-VIEW[1], VIEW[1] + 1)}:
            p = (x, y, z)
            if p in cells or p in protected:
                continue
            if p not in values or (values[p] == [ROCK] and (x, y) not in seen_by_others):
                cells[p] = [LAVA]

    # bajadas: hueco arriba, escalera abajo, llegadas libres
    stairs_near = {}
    for (x, y, z) in HOLES:
        if z != TOP[2]:
            assert (x, y) in floors[z] and (x, y - 1) in floors[z], f"Hueco fuera del piso: {x},{y},{z}"
            cells[(x, y, z)] = [HOLE]
        assert (x, y) in floors[z + 1] and (x, y + 1) in floors[z + 1], f"Escalera fuera del piso: {x},{y},{z + 1}"
        cells[(x, y, z + 1)] = [FLOOR, STAIRS]
        stairs_near.setdefault(z, set()).add((x, y))
        stairs_near.setdefault(z + 1, set()).add((x, y))

    # decoración en las paredes y en las salas
    for z, floor in floors.items():
        keep = C.grow(stairs_near.get(z, set()), 2)
        walls = ring(floor)
        north = sorted(c for c in walls if (c[0], c[1] + 1) in floor and cells[(*c, z)][1] == BRICK["h"])
        west = sorted(c for c in walls if (c[0] + 1, c[1]) in floor and cells[(*c, z)][1] == BRICK["v"])
        east = sorted(c for c in walls if (c[0] - 1, c[1]) in floor and cells[(*c, z)][1] == BRICK["v"])
        for (x, y) in north:                    # tapices en tramos de 4 y antorchas entre tramos
            k = (x + y) % 7
            if k < 4:
                cells[(x, y, z)].append(TAPESTRY)
            elif k == 5:
                cells[(x, y, z)].append(TORCH_H)
        for (x, y) in west + east:
            if y % 4 == 0:
                cells[(x, y, z)].append(TORCH_V)
        # monumentos de a pares delante de los tapices y ataúdes en las salas grandes
        for x0, y0, x1, y1 in PLAN[z]:
            w, h = x1 - x0 + 1, y1 - y0 + 1
            if w < 9 or h < 6:
                continue
            for c in ((x0 + 1, y0), (x1 - 1, y0)):
                if c not in keep and len(cells[(*c, z)]) == 1:
                    cells[(*c, z)].append(MONUMENT)
            if w >= 15 and h >= 9:                # columnas y braseros en hilera, a 3 de las paredes
                for i, cx in enumerate(range(x0 + 3, x1 - 2, 4)):
                    for cy in (y0 + 3, y1 - 4):
                        c = (cx, cy)
                        if c not in keep and len(cells[(*c, z)]) == 1:
                            cells[(*c, z)].append(PILLAR if (i + cy) % 2 else COAL_BASIN)
                for cx in (x0 + 1, x1 - 1):
                    head, foot = (cx, y1 - 2), (cx, y1 - 1)
                    if head not in keep and foot not in keep and len(cells[(*head, z)]) == 1 and len(cells[(*foot, z)]) == 1:
                        cells[(*head, z)].append(COFFIN_HEAD)
                        cells[(*foot, z)].append(COFFIN_FOOT)

    # recorrido: de la llegada de arriba al hueco de abajo en cada piso
    for z, floor in floors.items():
        walk = {c for c in floor if bl.walkable(cells[(*c, z)])}
        arrive = next((x, y + 1) for (x, y, zz) in HOLES if zz + 1 == z)
        dist = C.reach(walk, arrive, C.NP.CARD)
        assert walk == set(dist), f"z{z}: casillas sin acceso: {sorted(walk - set(dist))[:5]}"
        nxt = [(x, y - 1) for (x, y, zz) in HOLES if zz == z]
        assert all(c in dist for c in nxt), f"z{z}: no se llega a la bajada"
        per, st, gap = STAGES[z]
        avoid = C.grow(stairs_near.get(z, set()), 4)
        pool = {c for c in walk if HOLE not in cells[(*c, z)] and STAIRS not in cells[(*c, z)]} - avoid
        spawns += C.place_stages([((MONSTER,), per, st, gap)], [pool], pool, avoid, z,
                                 random.Random(f"hero-depths-spawns-{z}"))

    # techo: suelo encima de todo piso propio (roca solo donde arriba no hay nada)
    for z, floor in floors.items():
        for x, y in C.grow(floor, 1):
            p = (x, y, z - 1)
            if p not in cells and p not in values and p not in protected:
                cells[p] = [ROCK]

    positions = [p for _, _, ms in spawns for _, p, _ in ms]
    assert len(positions) == len(set(positions))
    report = dict(floors={z: len(f) for z, f in floors.items()}, spawns=len(spawns),
                  monsters=len(positions), entry=list(TOP))
    return cells, spawns, report


def block(text, key, body, close):
    marked = f"\t<!-- BEGIN {key} (scripts/map/generate-hero-depths.py) -->\n{body}\n\t<!-- END {key} -->\n"
    pattern = rf"[ \t]*<!-- BEGIN {key}(?: \([^>]*\))? -->.*?<!-- END {key} -->\n?"
    return re.sub(pattern, lambda _: marked, text, flags=re.S) if re.search(pattern, text, re.S) else text.replace(close, marked + close)


def preview(path, cells, spawns):
    from PIL import Image, ImageDraw
    from mapdata import Renderer, load_tiles
    from game_render import Sprites, creature_image, parse_dat_all
    import xml.etree.ElementTree as ET

    tiles = load_tiles()
    tiles.update(cells)
    look = ET.parse(REPO / "server/YurOTS/ots/data/monster/black knight.xml").getroot().find("look")
    look = {k: int(v) for k, v in look.attrib.items() if k != "corpse"}
    _, outfits = parse_dat_all()
    actor = creature_image(look, outfits, Sprites())
    x0, y0, x1, y1 = 114, 72, 180, 118
    panels = []
    r = Renderer()
    for z in (9, 10, 11, 12, 13, 14):
        w, h, rgba = r.area(tiles, x0, y0, x1, y1, z)
        im = Image.frombytes("RGBA", (w, h), bytes(rgba))
        for _, zz, ms in spawns:
            if zz == z:
                for _, (x, y), _ in ms:
                    im.alpha_composite(actor, ((x - x0 + 1) * 32 - actor.width, (y - y0 + 1) * 32 - actor.height))
        im = im.convert("RGB").resize((w // 3, h // 3))
        ImageDraw.Draw(im).text((8, 8), f"z{z}", fill="white")
        panels.append(im)
    W, H = panels[0].size
    sheet = Image.new("RGB", (W * 2, H * 3))
    for i, im in enumerate(panels):
        sheet.paste(im, ((i % 2) * W, (i // 2) * H))
    sheet.save(path)


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

    previous = json.loads(MANIFEST.read_text())["cells"] if MANIFEST.exists() else {}
    # en la segunda pasada lo propio cuenta como vacío (así build() ve lo mismo que la primera vez)
    base = {p: ids for p, ids in values.items() if previous.get(",".join(map(str, p))) != ids}
    base[TOP] = [FLOOR] if values.get(TOP) in ([FLOOR], [HOLE]) else values.get(TOP)
    cells, spawns, report = build(base, otb)
    cells[TOP] = [HOLE]

    for p, ids in cells.items():
        old = values.get(p)
        owned = previous.get(",".join(map(str, p))) == old
        if p == TOP:
            assert old in ([FLOOR], [HOLE]), f"El pasillo de los Hero cambió: {old}"
        elif old not in (None, [ROCK]) and not owned:
            raise ValueError(f"Tile ajeno protegido: {p}: {old}")
        for tile in nodes.get(p, []):
            assert tile[0] == 5 and not tile_flags(tile[1]), f"Casa/flags protegidos: {p}"
    for key, ids in previous.items():           # lo propio que ya no se escribe vuelve a vacío -> roca
        p = tuple(map(int, key.split(",")))
        if p not in cells and values.get(p) == ids:
            cells[p] = [ROCK]

    sp = SPAWNS.read_text(encoding="latin-1")
    spawn_text = block(sp, "HERO_DEPTHS_SPAWNS", C.spawn_xml(spawns), "</spawns>")
    changed = sum(values.get(p) != ids for p, ids in cells.items())
    print(json.dumps(report | dict(changed=changed), ensure_ascii=False))
    if args.preview:
        preview(args.preview, cells, spawns)
        print(args.preview)
    if args.dry_run or args.preview:
        return

    backup = REPO / "backups/map" / ("hero-depths-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    for f in (MAP, SPAWNS):
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
    MANIFEST.write_text(json.dumps(dict(
        name="hero-depths", version=1, monster=MONSTER, **report,
        cells={",".join(map(str, p)): ids for p, ids in sorted(cells.items())},
    ), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
