#!/usr/bin/env python3
"""Campamento de Amazonas (Lv 15-30) en una isla al noroeste de la city (z7). Versión 2 (22 nov 2026).

Acceso a pie desde la orilla oeste del Castillo Imperial (75,33,7):
  - Cartel 1429 en (74,34,7).
  - Puente de sogas de 1 de ancho (3756/3757 alternados) en x=75, y=21..33.
  - Isla de selva (x=72..107, y=6..20) con costa canónica 4644-4655: árboles de selva en la orilla,
    sendero de tierra con sus bordes (110-121) desde el puente hasta el portón oeste.
  - Campamento: empalizada en punta (3512/3520/3531/3532) de x=84..98, y=9..17, con portones al oeste
    y al este; adentro patio de tierra, tres tiendas abiertas (paredes de tela roja, de piel y a rayas)
    con heno, fogata con troncos, pila de leña, barril y caja. Calaveras en estaca a los lados del portón.
  - Al este, un puesto con fogata. Spawns: Amazon, Valkyrie y Assassin.
  - Sin vacío negro a la vista: mar hasta x=54 al oeste y en y=0, y en x=114..115 (entre el mar y el
    bosque del este) una franja de bosque con su costa.

Preserva lo ajeno (Castillo Imperial en y>=25, lava en x<=65 y>=20, bosque en x>=116) y es idempotente.
Uso:
  python3.11 scripts/map/generate-amazon-camp.py --dry-run [--preview /tmp/amazon.png]
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

WATER, GRASS, GRASS_COAST, DIRT = 4608, 4756, 4526, 103
WATERS = set(range(4608, 4626)) | {4664, 4665, 4666}
COAST_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
COAST_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
COAST_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}
DIRT_SIDE, DIRT_CORNER, DIRT_INNER = NP.DIRT_SIDE, NP.DIRT_CORNER, NP.DIRT_INNER

ROPE_BRIDGE = (3756, 3757)                     # tablas del puente de sogas (norte-sur), alternadas
# empalizada en punta: la pared se dibuja en el borde sur/este de su casilla (MAPAS.md#paredes)
PALISADE = dict(h=3512, v=3520, pole=3532, corner=3531)
TENTS = ((3867, 3868), (3869, 3870), (3896, 3897))   # tela roja, piel, a rayas: (horizontal, vertical)
HAY = (3848, 3849, 3850, 3851)
CAMPFIRE, LOGS, LOG_PILE, BARREL, CRATE, SKULL_POLE, SIGN = 1423, 3873, 3871, 1774, 1739, 5019, 1429
JUNGLE_TREES = (4008, 4008, 4007, 4009, 4006, 2725, 2726, 4025, 4026)
JUNGLE_PLANTS = (4010, 4011, 4012, 4014, 4017, 4019, 4021)     # bloquean
JUNGLE_GRASS, FLOWERS = 2781, (4158, 2740, 4179, 4150)
FOREST_TREES = (4009, 4009, 4009, 2768, 2767, 2702, 2708)      # como el bosque vecino (x>=116)

SEA_BOX = (67, 1, 113, 24)                     # el mar de la v1
WEST_FILL = (54, 0, 66, 19)                    # vacío al oeste del mar (arriba de la lava)
TOP_ROW = (54, 0, 113, 0)                      # vacío en y=0
EAST_STRIP = (114, 0, 115, 19)                 # vacío entre el mar y el bosque del este
BRIDGE_X, BRIDGE_YS = 75, range(21, 34)
SHORE_KEEP = {(76, 33): [GRASS_COAST, 4644]}   # orilla del castillo junto al puente (como era)
SIGN_POS = (74, 34)
LANDING = (75, 20)
ENTRY = (75, 33)

PAL = (84, 9, 98, 17)                          # empalizada: x0, y0, x1, y1 (marco)
WEST_GATE = {(84, 13), (84, 14)}
EAST_GATE = {(98, 12), (98, 13)}
TRAIL = ({(x, y) for x in (75, 76) for y in range(13, 19)}
         | {(x, y) for x in range(75, 84) for y in (13, 14)})
TENT_X = (86, 90, 94)                          # tiendas de 3 de ancho contra la empalizada norte
CAMP_FIRE, OUTPOST_FIRE = (91, 14), (102, 13)

STAGES = (
    (("Amazon",), 2, 90, 7),
    (("Amazon", "Valkyrie"), 2, 105, 7),
    (("Valkyrie", "Assassin"), 2, 120, 7),
)


def box(b):
    x0, y0, x1, y1 = b
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def island_shape():
    land = set()
    ellipses = [(78.5, 14.0, 6.8, 6.6), (90.5, 12.8, 10.5, 7.0), (101.5, 13.5, 6.2, 5.8)]
    for x in range(71, 108):
        for y in range(5, 22):
            if any(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 for cx, cy, rx, ry in ellipses):
                land.add((x, y))
    # llegada del puente: punta de 3 de ancho en y=21, así la casilla de llegada (75,20) no tiene costa
    # (las piezas de costa 4644-4655 bloquean el paso)
    land |= {(x, y) for x in range(73, 79) for y in range(17, 21)} | {(x, 21) for x in (74, 75, 76)}
    allowed = {(x, y) for x in range(71, 108) for y in range(5, 22)}
    return NP.fix_until_valid(land, allowed, COAST_SIDE, COAST_CORNER, COAST_INNER, single=True)


def wall_piece(walls, x, y):
    west, north = (x - 1, y) in walls, (x, y - 1) in walls
    return PALISADE["corner" if west and north else "h" if west else "v" if north else "pole"]


def build(values, otb):
    bl = C.Blocking()
    rng = random.Random("amazon-camp-v2")
    tiles = {}

    # --- mar, rellenos y franja de bosque -------------------------------------------------------
    for c in box(SEA_BOX) | box(WEST_FILL) | box(TOP_ROW):
        tiles[c] = [WATER]
    land = island_shape()
    bridge = {(BRIDGE_X, y) for y in BRIDGE_YS}
    strip = box(EAST_STRIP)

    land -= bridge

    def is_water(c):
        if c in bridge:
            return False                       # el puente no lleva costa al lado: se pisa
        if c in tiles or c in land or c in strip:
            return c not in land and c not in strip
        v = values.get((*c, 7))
        return bool(v) and v[0] in WATERS

    def coast_or_grass(c):
        near = {d for d, (dx, dy) in NP.DIRS.items() if is_water((c[0] + dx, c[1] + dy))}
        pcs = NP.pieces_for(near, COAST_SIDE, COAST_CORNER, COAST_INNER)
        assert pcs is not None and len(pcs) <= 1, f"Costa ambigua en {c}: {near}"
        return [GRASS_COAST, pcs[0]] if pcs else [GRASS]

    for c in strip:
        tiles[c] = coast_or_grass(c)
        if len(tiles[c]) == 1 and rng.random() < 0.7:
            tiles[c].append(rng.choice(FOREST_TREES))

    shore = {c for c in land if any(is_water((c[0] + dx, c[1] + dy)) for dx, dy in NP.DIRS.values())}
    deep = land - C.grow(shore, 1)

    # --- tierra: sendero + patio + portones, con sus bordes --------------------------------------
    px0, py0, px1, py1 = PAL
    yard = {(x, y) for x in range(px0 + 1, px1) for y in range(py0 + 1, py1)}
    dirt = TRAIL | yard | WEST_GATE | EAST_GATE
    assert dirt <= deep, f"Tierra fuera del interior: {sorted(dirt - deep)[:5]}"
    dirt = NP.fix_until_valid(dirt, deep, DIRT_SIDE, DIRT_CORNER, DIRT_INNER, single=True)

    for c in land:
        if c in dirt:
            tiles[c] = [DIRT]
        elif c in shore:
            tiles[c] = coast_or_grass(c)
        else:
            edge = NP.pieces_for(NP.neighbors_in(dirt, *c), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
            assert edge is not None and len(edge) <= 1, f"Borde de tierra ambiguo en {c}"
            tiles[c] = [edge[0]] if edge else [GRASS]
    for c in bridge:
        tiles[c] = [ROPE_BRIDGE[c[1] % 2]]
    for y in range(25, 33):                    # la segunda columna del puente de la v1 vuelve a ser agua
        tiles[(BRIDGE_X + 1, y)] = [WATER]
    tiles.update({c: list(v) for c, v in SHORE_KEEP.items()})
    tiles[SIGN_POS] = [GRASS, SIGN]

    # --- empalizada ----------------------------------------------------------------------------
    frame = {(x, y) for x in range(px0, px1 + 1) for y in (py0, py1)} | \
            {(x, y) for y in range(py0, py1 + 1) for x in (px0, px1)}
    walls = frame - WEST_GATE - EAST_GATE
    for (x, y) in walls:
        tiles[(x, y)].append(wall_piece(walls, x, y))

    # --- tiendas: techo (horizontal) en la fila de arriba, costados (vertical), abiertas al sur --
    tent_inside = set()
    for (h, v), tx in zip(TENTS, TENT_X):
        ty = py0 + 1
        for x in range(tx, tx + 3):
            tiles[(x, ty)].append(h)
        for y in (ty + 1, ty + 2):
            tiles[(tx, y)].append(v)
            tiles[(tx + 2, y)].append(v)
        tiles[(tx + 1, ty + 1)].append(rng.choice(HAY))
        tent_inside |= {(tx + 1, ty + 1), (tx + 1, ty + 2)}

    # --- patio: fogata, leña, barril, caja y heno; calaveras en el portón -----------------------
    fx, fy = CAMP_FIRE
    props = {CAMP_FIRE: CAMPFIRE, (fx - 1, fy + 1): LOGS, (fx + 1, fy + 1): LOGS,
             (px1 - 1, py1 - 1): LOG_PILE, (px1 - 2, py1 - 1): BARREL, (px1 - 1, py1 - 2): CRATE,
             (px0 + 1, py1 - 1): HAY[2], (px0 + 2, py1 - 1): HAY[3],
             (px0 - 1, min(WEST_GATE)[1] - 1): SKULL_POLE, (px0 - 1, max(WEST_GATE)[1] + 1): SKULL_POLE,
             OUTPOST_FIRE: CAMPFIRE, (OUTPOST_FIRE[0], OUTPOST_FIRE[1] + 1): LOGS,
             (OUTPOST_FIRE[0] + 1, OUTPOST_FIRE[1] - 1): SKULL_POLE}
    for c, item in props.items():
        assert c in land and c not in walls and len(tiles[c]) == 1, f"Lugar ocupado para {item}: {c} {tiles[c]}"
        tiles[c].append(item)

    # --- selva: árboles en la orilla, plantas y pasto alto adentro --------------------------------
    island = land | bridge
    enclosure = {(x, y) for x in range(px0, px1 + 1) for y in range(py0, py1 + 1)}
    keep = (C.grow({LANDING, (75, 19)}, 1) | C.grow(dirt, 0) | C.grow(WEST_GATE | EAST_GATE, 1)
            | C.grow({OUTPOST_FIRE}, 1) | C.grow(set(props), 0) | enclosure)

    def walk_set():
        return {c for c in island if bl.walkable(tiles[c])}

    def connected():
        w = walk_set()
        return len(C.reach(w, ENTRY, C.NP.CARD)) == len(w)

    # bolsillos entre la empalizada y la costa a los que no se llega: selva cerrada
    reachable = C.reach(walk_set(), ENTRY, C.NP.CARD)
    for c in sorted(walk_set() - set(reachable)):
        tiles[c].append(rng.choice(JUNGLE_TREES + JUNGLE_PLANTS))

    for c in sorted(land - shore - keep):
        if len(tiles[c]) != 1:
            continue
        near_shore = any(q in shore for q in C.grow({c}, 1))
        roll = rng.random()
        if near_shore and roll < 0.5:
            tiles[c].append(rng.choice(JUNGLE_TREES))
        elif not near_shore and roll < 0.08:
            tiles[c].append(rng.choice(JUNGLE_PLANTS if rng.random() < 0.6 else JUNGLE_TREES))
        elif roll > 0.9:
            tiles[c].append(JUNGLE_GRASS if rng.random() < 0.7 else rng.choice(FLOWERS))
            continue
        else:
            continue
        if not connected():
            tiles[c].pop()

    walk = walk_set()
    dist = C.reach(walk, ENTRY, C.NP.CARD)
    assert walk == set(dist), f"Casillas aisladas: {sorted(walk - set(dist))[:5]}"

    # --- spawns -------------------------------------------------------------------------------
    blocked_fire = {c for c in island if CAMPFIRE in tiles[c]}
    island_walk = (walk & land) - blocked_fire - tent_inside
    avoid = C.grow({LANDING}, 5) | C.grow(blocked_fire, 1)
    spawns = C.place_stages(
        STAGES,
        C.slices_by(island_walk - avoid, dist.__getitem__, len(STAGES)),
        island_walk, avoid, 7, random.Random("amazon-camp-spawns-v2"),
    )
    positions = [p for _, _, ms in spawns for _, p, _ in ms]
    assert len(positions) == len(set(positions)) and all(p in island_walk for p in positions)

    cells = {(x, y, 7): ids for (x, y), ids in tiles.items()}
    report = dict(walkable=len(island_walk), density=round(len(island_walk) / len(positions), 1),
                  spawns=len(spawns), entry=[*ENTRY, 7])
    return cells, spawns, report


def block(text, key, body, close):
    marked = f"\t<!-- BEGIN {key} (scripts/map/generate-amazon-camp.py) -->\n{body}\n\t<!-- END {key} -->\n"
    pattern = rf"[ \t]*<!-- BEGIN {key}(?: \([^>]*\))? -->.*?<!-- END {key} -->\n?"
    return re.sub(pattern, lambda _: marked, text, flags=re.S) if re.search(pattern, text, re.S) else text.replace(close, marked + close)


def preview(path, cells, spawns):
    from PIL import Image
    from mapdata import Renderer, load_tiles
    from game_render import Sprites, creature_image, parse_dat_all
    import xml.etree.ElementTree as ET

    tiles = load_tiles()
    tiles.update(cells)
    x0, y0, x1, y1 = 56, 0, 118, 36
    w, h, rgba = Renderer().client_view(tiles, x0, y0, x1, y1, 7)
    im = Image.frombytes("RGBA", (w, h), bytes(rgba))
    _, outfits = parse_dat_all()
    spr = Sprites()
    data = REPO / "server/YurOTS/ots/data/monster"
    looks = {}
    for m in ET.parse(data / "monsters.xml").getroot():
        if m.get("name") in ("Amazon", "Valkyrie", "Assassin"):
            look = ET.parse(data / m.get("file")).getroot().find("look")
            looks[m.get("name")] = {k: int(v) for k, v in look.attrib.items() if k != "corpse"}
    for _, _, ms in spawns:
        for name, (x, y), _ in ms:
            actor = creature_image(looks[name], outfits, spr)
            im.alpha_composite(actor, ((x - x0 + 1) * 32 - actor.width, (y - y0 + 1) * 32 - actor.height))
    im.convert("RGB").save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path, help="PNG con la isla y los monstruos, sin escribir nada")
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
    # lo de la v1 que la v2 ya no escribe vuelve a ser agua (nunca queda una casilla vieja suelta)
    for key, ids in previous.items():
        p = tuple(map(int, key.split(",")))
        if p not in cells and values.get(p) == ids:
            cells[p] = [WATER]

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
    if args.preview:
        preview(args.preview, cells, spawns)
        print(args.preview)
    if args.dry_run or args.preview:
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
        name="amazon-camp", version=2,
        monsters=dict(counts), **report,
        cells={",".join(map(str, p)): ids for p, ids in sorted(cells.items())},
    ), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
