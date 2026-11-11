#!/usr/bin/env python3
"""Valle de las Bestias: zona de caza del portal del templo (158,47,7) que reemplaza al Hunt Maze.

El Hunt Maze era un laberinto generado de piso crema y paredes de lava. En su lugar, un valle natural
que se recorre de sur a norte y después baja, con la misma progresión de monstruos (de Minotauros a
Demonios) repartida por etapas:

  z7  Llegada (portal de vuelta) -> Campamento Minotauro (bosque y fogatas)
      -> Colinas de los Cíclopes (rocas y piedras) -> Ruinas Antiguas (patio de tierra con columnas,
      estatuas y braseros) -> bajada, con otro portal de vuelta al lado
  z8  Catacumbas: cueva natural; Giant Spider y Vampire -> Necromancer y Priestess -> Hero y Black Knight
  z9  Abismo: cueva natural; Dragon -> Dragon Lord y Warlock -> Hydra, Lich y Green Djinn
      -> Demon, Behemoth, Fury y Serpent Spawn al fondo, con el portal de vuelta al templo

Caja: x 262-361, y 232-378, z7-z9. Borra además todo el Hunt Maze viejo (x 280-349, y 243-400, z7).
No toca la Hell Quest (y <= 226), el Paso del Norte (x >= 370) ni el Reloj de Arena (z5-z6, y >= 383).

Reglas que valida antes de escribir (si algo falla no escribe nada):
  - bordes de tierra con su pieza; paredes de las cuevas con pieza única;
  - se llega de la llegada a la bajada, a los portales y, en z8 y z9, a la bajada y al portal final;
  - desde cualquier casilla caminable la pantalla entera tiene casillas (sin negro).

Uso (desde la raíz del repo; Pillow no hace falta):
  python3 scripts/map/generate-beast-valley.py --dry-run --preview /tmp/valle.png
  python3 scripts/map/generate-beast-valley.py          # escribe mapa, spawns, carteles y manifiesto
  python3 scripts/map/temple-portals.py                 # después: apunta el portal de la plaza
Re-ejecutable: borra la caja z7-z9 y reemplaza los bloques BEAST_VALLEY de spawns y carteles.
Doc: docs/items-and-map/MAPEAR_VALLE_DE_LAS_BESTIAS.md.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import re
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import (MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, Renderer,  # noqa: E402
                     parse_tree, png_bytes, serialize_tree)

_spec = importlib.util.spec_from_file_location("north_pass", HERE / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)
Noise, neighbors_in, pieces_for, fix_until_valid, reach, Blocking = (
    NP.Noise, NP.neighbors_in, NP.pieces_for, NP.fix_until_valid, NP.reach, NP.Blocking)
carve_cave, cave_tiles, decorate_cave = NP.carve_cave, NP.cave_tiles, NP.decorate_cave
DIRT_SIDE, DIRT_CORNER, DIRT_INNER = NP.DIRT_SIDE, NP.DIRT_CORNER, NP.DIRT_INNER
WALL_SIDE, WALL_CORNER, WALL_INNER, ROCK = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER, NP.ROCK
CAVE_FLOORS = NP.CAVE_FLOORS
CARD = NP.CARD

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MANIFEST = WORLD / "generated-beast-valley.json"
OLD_MANIFEST = WORLD / "generated-hunt-maze.json"

X0, Y0, W, H = 262, 232, 100, 147          # x 262-361, y 232-378
OLD_MAZE = (280, 243, 349, 400)            # Hunt Maze viejo (z7): se borra entero
Z7, Z8, Z9 = 7, 8, 9
BAND = 8                                    # franja exterior intransitable (la pantalla no ve el borde)
TEMPLE_BACK = (158, 48, 7)                  # llegada del portal de la plaza (temple-portals.py)

# --- piezas (ids de servidor) ---------------------------------------------------------------------
GRASS, DIRT = NP.GRASS, NP.DIRT
FOREST_TREES, SMALL_TREE, BUSHES = NP.FOREST_TREES, NP.FOREST_SMALL_TREE, NP.BUSHES
FLOWERS, MUSHROOMS, LOGS, DEAD_TREES = NP.FLOWERS, NP.MUSHROOMS, NP.LOGS, NP.DEAD_TREES
STONE, RUBBLE, RUBBLE_BROWN, PEBBLES = NP.STONE, NP.RUBBLE_GREY, NP.RUBBLE_BROWN, NP.PEBBLES
BONES, DRAGON_SKULL, DRAGON_BONES, SKELETON = NP.BONES, NP.DRAGON_SKULL, NP.DRAGON_BONES, NP.HUMAN_SKELETON
CAMPFIRE, BRANCH, LANTERN, SIGN = NP.CAMPFIRE, NP.BRANCH, NP.LANTERN, NP.SIGN
TELEPORT, ATTR_TELE_DEST = NP.TELEPORT, NP.ATTR_TELE_DEST
STAIR_DOWN, STAIRS_UP = NP.STAIR_DOWN, NP.STAIRS_UP
PILLAR, BROKEN_PILLAR, STATUE, ALTAR, COAL_BASIN = 1515, 3767, 1442, 1642, 2602
BARREL, CRATE = 1770, 1739

# --- recorrido de la superficie (coordenadas locales, x 0-99, y 0-146) ----------------------------
ARRIVAL = (50, 128)                         # destino del portal de la plaza
PORTALS_BACK = [(50, 133), (51, 133)]       # vuelta al templo, al sur de la llegada
STAIRS = (50, 20)                           # bajada a las Catacumbas
STAIRS_PORTAL = (57, 22)                    # vuelta al templo junto a la bajada
HILLS_Y, RUINS_Y = 92, 50                   # al norte de HILLS_Y: colinas; al norte de RUINS_Y: ruinas
RUINS = (50, 31, 14, 10)                    # patio de las ruinas: centro x, y y radios (tierra)
AVENUE = (46, 55)                           # columnas a los dos lados del camino que cruza el patio (x)
CAMPS = (124, 114, 104, 96)                 # fogatas de los minotauros junto al camino (y)

# --- caza: etapas en orden; cada spawn mezcla los monstruos de su etapa --------------------------
#       (monstruos, monstruos por spawn, spawntime)
STAGES7 = [
    (("Minotaur", "Minotaur Archer"), 2, 60),
    (("Minotaur", "Minotaur Guard"), 2, 60),
    (("Minotaur Guard", "Minotaur Archer", "Minotaur"), 2, 70),
    (("Minotaur Mage", "Minotaur Guard"), 2, 80),
    (("Cyclops", "Minotaur Guard", "Dwarf Soldier"), 2, 90),
    (("Dwarf Guard", "Cyclops", "Dwarf Geomancer"), 2, 90),
    (("Beholder", "Dwarf Guard", "Demon Skeleton"), 2, 100),
    (("Demon Skeleton", "Ghoul", "Beholder"), 2, 100),
]
STAGES8 = [
    (("Giant Spider", "Vampire", "Demon Skeleton"), 2, 120),
    (("Necromancer", "Priestess", "Vampire"), 2, 120),
    (("Hero", "Black Knight", "Necromancer"), 2, 150),
]
STAGES9 = [
    (("Dragon", "Hero", "Ancient Scarab"), 2, 150),
    (("Dragon Lord", "Warlock", "Dragon"), 2, 180),
    (("Hydra", "Lich", "Green Djinn"), 2, 180),
    (("Demon", "Behemoth", "Serpent Spawn", "Fury"), 1, 300),
]


GAP = 9                                     # distancia mínima entre centros de spawn


def ellipse(cx, cy, rx, ry) -> set:
    return {(x, y) for x in range(int(cx - rx) - 1, int(cx + rx) + 2) for y in range(int(cy - ry) - 1, int(cy + ry) + 2)
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1}


def grow(cells, r: int) -> set:
    return {(x + dx, y + dy) for (x, y) in cells for dx in range(-r, r + 1) for dy in range(-r, r + 1)}


# --- superficie -------------------------------------------------------------------------------------

def build_surface(seed: int, bl):
    rng = random.Random(seed)
    nz = Noise(seed)
    cells = {(x, y) for y in range(H) for x in range(W)}
    inner = {(x, y) for (x, y) in cells if BAND <= x < W - BAND and BAND <= y < H - BAND}

    # forma jugable: rectángulo con bordes irregulares
    play = set()
    for (x, y) in inner:
        edge = min(x - BAND, W - BAND - 1 - x, y - BAND, H - BAND - 1 - y)
        if edge > 3 or nz.fbm(x / 6, y / 6, 3, 7) > 0.35 + 0.12 * (3 - edge):
            play.add((x, y))

    # camino de tierra: línea serpenteante de la llegada a la bajada (2 de ancho)
    center = {}
    top, bottom = STAIRS[1] + 2, ARRIVAL[1]
    court_bottom = RUINS[1] + RUINS[3]
    for y in range(top, bottom + 1):                # recto por el patio de las ruinas, después serpentea
        if y <= court_bottom:
            center[y] = STAIRS[0]
            continue
        t = (y - court_bottom) / (bottom - court_bottom)
        wave = 20 * math.sin((y - court_bottom) / 15.0) * math.sin(math.pi * t)
        center[y] = int(round(STAIRS[0] + wave + 4 * (nz.fbm(0, y / 9, 2, 11) - 0.5) * math.sin(math.pi * t)))
    path = set()
    for y, cx in center.items():
        path |= {(cx, y), (cx + 1, y)}
        if y + 1 in center:                         # sin saltos en diagonal
            nx = center[y + 1]
            path |= {(x, y) for x in range(min(cx, nx), max(cx, nx) + 2)}
    arrival_zone = {(ARRIVAL[0] + dx, ARRIVAL[1] + dy) for dx in range(-3, 5) for dy in range(-2, 7)}
    stairs_zone = {(STAIRS[0] + dx, STAIRS[1] + dy) for dx in range(-3, 4) for dy in range(-3, 4)}
    portal_zone = {(STAIRS_PORTAL[0] + dx, STAIRS_PORTAL[1] + dy) for dx in range(-2, 3) for dy in range(-2, 3)}
    path |= {(STAIRS[0] + dx, y) for dx in (0, 1) for y in range(STAIRS[1] + 2, top + 1)}
    path |= {(x, STAIRS_PORTAL[1] + 1) for x in range(STAIRS[0], STAIRS_PORTAL[0] + 1)}
    court = ellipse(*RUINS) & inner
    play |= path | arrival_zone | stairs_zone | portal_zone | court

    # tierra: el camino (salvo en la llegada) y el patio de las ruinas, con bordes de pasto
    dirt = {c for c in path if c[1] < ARRIVAL[1] - 1} | court | stairs_zone
    dirt = fix_until_valid(dirt, inner, DIRT_SIDE, DIRT_CORNER, DIRT_INNER, single=True)

    tiles: dict = {}
    for c in cells:
        if c in dirt:
            tiles[c] = [DIRT]
        else:
            edge = pieces_for(neighbors_in(dirt, *c), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
            tiles[c] = [edge[0]] if edge else [GRASS]

    occupied: set = set()

    def free(c, r=0):
        return all((c[0] + dx, c[1] + dy) not in occupied for dx in range(-r, r + 1) for dy in range(-r, r + 1))

    def put(c, item, size=1):
        tiles[c].append(item)
        for dx in range(size):
            for dy in range(size):
                occupied.add((c[0] - dx, c[1] - dy))

    keep_clear = set(path) | arrival_zone | stairs_zone | portal_zone
    occupied |= keep_clear

    # 1) franja exterior: bosque cerrado (un bloqueo 1x1 por casilla y, cada dos, un árbol grande)
    band = sorted(cells - play, key=lambda c: (c[1], c[0]))
    for c in band:
        ruins_side = c[1] < RUINS_Y
        tiles[c].append(rng.choice((STONE, SMALL_TREE) if ruins_side else (SMALL_TREE,) + BUSHES))
        occupied.add(c)
    for c in band:
        x, y = c
        if x % 2 == 1 and y % 2 == 1:
            tiles[c].append(rng.choice(DEAD_TREES + (RUBBLE,)) if y < RUINS_Y else rng.choice(FOREST_TREES))

    # 2) fogatas de los minotauros junto al camino
    camps = []
    for k, cy in enumerate(CAMPS):
        side = 4 if k % 2 == 0 else -4
        camp = (center[cy] + (side + 1 if side > 0 else side), cy)
        items = {camp: CAMPFIRE, (camp[0] - 1, camp[1] + 1): LOGS[1], (camp[0] + 1, camp[1] - 1): LOGS[2],
                 (camp[0] + 1, camp[1] + 1): BARREL, (camp[0] - 1, camp[1] - 1): CRATE}
        for c, it in items.items():
            if c in play and c not in path:
                put(c, it)
        occupied |= {(camp[0] + dx, camp[1] + dy) for dx in range(-2, 3) for dy in range(-2, 3)}
        camps.append(camp)

    # 3) ruinas: avenida de columnas hasta la bajada, estatuas a la entrada, montones de escombro,
    #    braseros y un altar al fondo; alrededor, un cementerio de lápidas rotas entre árboles secos
    cx, cy, rx, ry = RUINS
    ruin_items = {}
    for y in range(STAIRS[1] + 4, int(cy + ry) + 1, 3):
        for x in AVENUE:
            ruin_items[(x, y)] = BROKEN_PILLAR if (x * 7 + y * 3) % 4 == 0 else PILLAR
    entry_y = int(cy + ry) + 1
    ruin_items.update({(AVENUE[0] - 1, entry_y): STATUE, (AVENUE[1] + 1, entry_y): STATUE,
                       (AVENUE[0] - 4, cy - 4): COAL_BASIN, (AVENUE[1] + 4, cy - 4): COAL_BASIN,
                       (AVENUE[0] - 4, cy + 5): COAL_BASIN, (AVENUE[1] + 4, cy + 5): COAL_BASIN,
                       (cx - 9, cy - 3): ALTAR, (cx - 8, cy + 3): SKELETON, (cx + 9, cy + 1): SKELETON})
    for c, it in ruin_items.items():
        if c in play and c not in keep_clear and free(c):
            put(c, it)
    for c in sorted(court, key=lambda c: (c[1], c[0])):          # escombros en el patio, lejos de la avenida
        x, y = c
        if AVENUE[0] - 2 <= x <= AVENUE[1] + 2 or c in occupied:
            continue
        if rng.random() < 0.035 and free(c, 1):
            put(c, rng.choice((RUBBLE, RUBBLE_BROWN)), 2)
        elif rng.random() < 0.03 and free(c):
            put(c, rng.choice((BROKEN_PILLAR, STONE)))
    graves = set()
    for y in range(BAND + 3, RUINS_Y - 2, 3):                    # lápidas en filas sueltas
        for x in range(BAND + 3, W - BAND - 3, 3):
            if rng.random() < 0.45:
                continue
            c = (x + rng.choice((-1, 0, 1)), y + rng.choice((0, 0, 1)))
            if c in play and c not in court and c not in keep_clear and not (grow(court, 2) & {c}) \
                    and nz.fbm(x / 9, y / 9, 2, 300) > 0.48 and free(c, 1):
                put(c, BROKEN_PILLAR)
                graves.add(c)

    # 4) interior según la etapa
    for c in sorted(play, key=lambda c: (c[1], c[0])):
        x, y = c
        if c in occupied or len(tiles[c]) > 1:
            continue
        r = rng.random()
        grove = nz.fbm(x / 7, y / 7, 3, 500)
        if y >= HILLS_Y:                                    # bosque del campamento
            if grove > 0.5 and r < 0.6 and free(c, 2):
                put(c, rng.choice(FOREST_TREES), 2)
            elif grove > 0.42 and r < 0.1 and free(c):
                put(c, SMALL_TREE)
            elif r < 0.03 and free(c):
                put(c, rng.choice(BUSHES))
            elif r < 0.07:
                tiles[c].append(rng.choice(FLOWERS))
            elif r < 0.085:
                tiles[c].append(rng.choice(MUSHROOMS))
            elif r < 0.092:
                tiles[c].append(rng.choice(LOGS + (BRANCH,)))
        elif y >= RUINS_Y:                                  # colinas: rocas agrupadas, poco árbol
            rocky = nz.fbm(x / 5, y / 5, 2, 700)
            if rocky > 0.6 and r < 0.4 and free(c, 1):
                put(c, rng.choice((RUBBLE, RUBBLE_BROWN)), 2)
            elif rocky > 0.52 and r < 0.14 and free(c):
                put(c, STONE)
            elif grove > 0.62 and r < 0.3 and free(c, 2):
                put(c, rng.choice(FOREST_TREES), 2)
            elif r < 0.03 and free(c, 1):
                put(c, rng.choice(DEAD_TREES), 2)
            elif r < 0.07:
                tiles[c].append(rng.choice((PEBBLES, PEBBLES, BRANCH) + BONES[:1]))
        else:                                               # alrededor de las ruinas
            if c in court:
                if r < 0.03:
                    tiles[c].append(rng.choice(BONES + (PEBBLES,)))
                continue
            if grove > 0.55 and r < 0.4 and free(c, 1):
                put(c, rng.choice(DEAD_TREES), 2)
            elif r < 0.03 and free(c):
                put(c, STONE)
            elif r < 0.09:
                tiles[c].append(rng.choice(BONES + (PEBBLES,)))

    # 5) faroles a lo largo del camino en las colinas y las ruinas
    for y in range(STAIRS[1] + 10, HILLS_Y, 11):
        c = (center[y] - 2, y)
        if c in play and len(tiles[c]) == 1 and free(c):
            put(c, LANTERN)

    # 6) bajada con marco de piedras (abierta al sur: 1385 sube hacia el norte)
    sx, sy = STAIRS
    tiles[STAIRS] = [STAIR_DOWN]
    for dx, dy in ((-2, -1), (-2, 0), (-2, 1), (2, -1), (2, 1), (-1, -2), (1, -2), (0, -2)):
        c = (sx + dx, sy + dy)
        tiles[c] = [tiles[c][0], STONE]
    tiles[(sx - 1, sy + 1)] = [tiles[(sx - 1, sy + 1)][0], DRAGON_SKULL]
    # portales de vuelta: en la llegada (dos, enmarcados) y uno junto a la bajada
    for c in PORTALS_BACK:
        tiles[c] = [tiles[c][0], TELEPORT]
    px0, px1, py = PORTALS_BACK[0][0], PORTALS_BACK[1][0], PORTALS_BACK[0][1]
    for c in ((px0 - 1, py), (px1 + 1, py), (px0 - 1, py + 1), (px1 + 1, py + 1), (px0, py + 1), (px1, py + 1)):
        tiles[c] = [tiles[c][0], STONE]
    for c in ((px0 - 2, py - 1), (px1 + 2, py - 1)):
        tiles[c] = [tiles[c][0], LANTERN]
    tiles[STAIRS_PORTAL] = [tiles[STAIRS_PORTAL][0], TELEPORT]
    for dx in (-1, 1):
        tiles[(STAIRS_PORTAL[0] + dx, STAIRS_PORTAL[1] - 1)] = [tiles[(STAIRS_PORTAL[0] + dx, STAIRS_PORTAL[1] - 1)][0], COAL_BASIN]

    hy = HILLS_Y - 2
    signs = {
        (ARRIVAL[0] + 3, ARRIVAL[1] - 1): "VALLE DE LAS BESTIAS\nEl camino sube al norte: Campamento Minotauro,\n"
                                          "Colinas de los Ciclopes y las Ruinas.\nPortal al sur: templo.",
        (center[hy] + 3, hy): "COLINAS DE LOS CICLOPES\nCiclopes y enanos de la cantera.",
        (center[RUINS_Y + 3] + 3, RUINS_Y + 3): "RUINAS ANTIGUAS\nNo todos los muertos descansan.",
        (sx + 3, sy + 1): "CATACUMBAS\nAbajo: aranas, vampiros y nigromantes.\nMas abajo, el Abismo.",
        (STAIRS_PORTAL[0] + 2, STAIRS_PORTAL[1]): "Portal al templo.",
    }
    placed = {}
    for anchor, text in signs.items():
        cands = [c for c in play - keep_clear if len(tiles[c]) == 1 and c not in placed
                 and any((c[0] + dx, c[1] + dy) in keep_clear for dx, dy in CARD)]
        c = min(cands, key=lambda c: (abs(c[0] - anchor[0]) + abs(c[1] - anchor[1]), c))
        tiles[c] = [tiles[c][0], SIGN]
        placed[c] = text

    return tiles, {"path": path, "play": play, "dirt": dirt, "court": court, "signs": placed, "camps": camps,
                   "center": center, "cells": cells, "inner": inner}


# --- cuevas -------------------------------------------------------------------------------------------

def build_caves(seed: int):
    sx, sy = STAIRS
    box = {(x, y) for x in range(W) for y in range(H)}
    allowed = {(x, y) for x in range(6, W - 6) for y in range(6, H - 6)}
    # z8: Catacumbas
    core8 = {(sx + dx, sy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1, 2)}
    floor8 = carve_cave(seed + 1, allowed, core8, (sx, sy + 1), 4200)
    t8 = cave_tiles(floor8, box, seed + 1)
    t8[(sx, sy)].append(STAIRS_UP)
    d8 = reach(floor8, (sx, sy + 1), CARD)
    cands = [c for c in floor8 if all((c[0] + dx, c[1] + dy) in floor8 for dx in (-1, 0, 1) for dy in (-2, -1, 0, 1, 2))]
    down = max(cands, key=lambda c: d8[c])
    t8[down] = [STAIR_DOWN]
    # z9: Abismo, desde la bajada
    dx0, dy0 = down
    core9 = {(dx0 + dx, dy0 + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1, 2)}
    floor9 = carve_cave(seed + 2, allowed, core9, (dx0, dy0 + 1), 3600)
    t9 = cave_tiles(floor9, box, seed + 2, mud_bias=0.18)
    t9[down].append(STAIRS_UP)
    d9 = reach(floor9, (dx0, dy0 + 1), CARD)
    portal_cands = [c for c in floor9 if all((c[0] + a, c[1] + b) in floor9 for a in (-1, 0, 1) for b in (-1, 0, 1))]
    portal = max(portal_cands, key=lambda c: d9[c])
    t9[portal].append(TELEPORT)
    for a, b in ((-1, -1), (1, -1)):
        t9[(portal[0] + a, portal[1] + b)].append(COAL_BASIN)
    return {"t8": t8, "floor8": floor8, "d8": d8, "down": down, "t9": t9, "floor9": floor9, "d9": d9,
            "portal": portal}


# --- spawns ---------------------------------------------------------------------------------------------

def place_stages(stages, slices, walk, avoid, z, rng, min_gap):
    """Un grupo de spawns por etapa, cada uno en su franja (`slices`, en orden de dificultad)."""
    out, centers = [], []
    for (names, per, spawntime), pool in zip(stages, slices):
        cands = sorted((pool & walk) - avoid)
        rng.shuffle(cands)
        k = 0
        for c in cands:
            if any(abs(c[0] - o[0]) + abs(c[1] - o[1]) < min_gap for o in centers):
                continue
            spots = [(c[0] + dx, c[1] + dy) for dx in range(-2, 3) for dy in range(-2, 3)
                     if (c[0] + dx, c[1] + dy) in walk and (c[0] + dx, c[1] + dy) not in avoid]
            if len(spots) < per + 3:
                continue
            rng.shuffle(spots)
            centers.append(c)
            out.append((c, z, [(names[(k + i) % len(names)], s, spawntime) for i, s in enumerate(spots[:per])]))
            k += per
    return out


def slices_by(cells, key, n):
    """Parte `cells` en n franjas de igual tamaño según `key` (de menor a mayor)."""
    order = sorted(cells, key=lambda c: (key(c), c))
    size = len(order) / n
    return [set(order[int(i * size):int((i + 1) * size)]) for i in range(n)]


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{X0 + cx}" centery="{Y0 + cy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


# --- OTBM -----------------------------------------------------------------------------------------------

NEEDS_COUNT = NP.NEEDS_COUNT                # apilables: el server exige el byte de cantidad


def item_node(iid: int, tele=None):
    props = bytearray(struct.pack("<H", iid))
    if iid in NEEDS_COUNT:
        props.append(1)
    if tele is not None:
        props += bytes([ATTR_TELE_DEST]) + struct.pack("<HHB", *tele)
    return [T_ITEM, props, []]


def new_tile(x, y, bx, by, items):
    props = bytearray([x - bx, y - by, 9]) + struct.pack("<H", items[0])
    return [T_TILE, props, [item_node(i, TEMPLE_BACK if i == TELEPORT else None) for i in items[1:]]]


def write_preview(path: Path, layers, otb):
    r = Renderer()
    color = {}
    for sid, e in otb.items():
        d = r.dat.get(e.get("cid")) if e.get("cid") else None
        if d and 0x1C in d["flags"]:
            color[sid] = struct.unpack("<H", d["flags"][0x1C])[0]

    def rgb(items):
        c = None
        for i in items:
            if i in color:
                c = color[i]
        if c is None:
            return (24, 24, 30)
        return ((c // 36) % 6 * 51, (c // 6) % 6 * 51, c % 6 * 51)

    S, gap = 3, 8
    Wp, Hp = (W * S + gap) * len(layers), H * S
    img = bytearray(b"\x10\x10\x14\xff" * (Wp * Hp))
    for k, t in enumerate(layers):
        ox = k * (W * S + gap)
        for (x, y), items in t.items():
            col = rgb(items)
            for dy in range(S):
                for dx in range(S):
                    o = ((y * S + dy) * Wp + ox + x * S + dx) * 4
                    img[o:o + 4] = bytes((*col, 255))
    path.write_bytes(png_bytes(Wp, Hp, bytes(img)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()

    bl = Blocking()
    surf, info = build_surface(a.seed, bl)
    caves = build_caves(a.seed)
    sx, sy = STAIRS
    dn, portal = caves["down"], caves["portal"]
    decorate_cave(caves["t8"], caves["floor8"], (sx, sy + 1), grow({STAIRS, dn, (sx, sy + 1)}, 2), a.seed + 1, 0.05, bl)
    decorate_cave(caves["t9"], caves["floor9"], (dn[0], dn[1] + 1), grow({dn, portal}, 2), a.seed + 2, 0.04, bl)

    errors = []
    # bordes de tierra: pieza exacta en el suelo
    dirt = info["dirt"]
    allp = set(DIRT_SIDE.values()) | set(DIRT_CORNER.values()) | set(DIRT_INNER.values())
    for c, it in surf.items():
        if c in dirt:
            continue
        want = pieces_for(neighbors_in(dirt, *c), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
        if want is None or len(want) > 1 or (want and it[0] != want[0]) or (not want and it[0] in allp):
            errors.append(f"tierra {c}: quiere {want} tiene {it[0]}")

    walk7 = {c for c, it in surf.items() if bl.walkable(it)}
    d7 = reach(walk7, ARRIVAL)
    for label, c in (("bajada", (sx, sy + 1)), ("portal junto a la bajada", STAIRS_PORTAL)):
        if not any((c[0] + dx, c[1] + dy) in d7 for dx, dy in CARD + ((0, 0),)):
            errors.append(f"z7: {label} {c} no se alcanza desde la llegada")
    for c in PORTALS_BACK:
        if not any((c[0] + dx, c[1] + dy) in d7 for dx, dy in CARD):
            errors.append(f"z7: portal de la llegada {c} sin acceso")
    walk8 = {c for c, it in caves["t8"].items() if bl.walkable(it) and it[0] in CAVE_FLOORS}
    d8 = reach(walk8, (sx, sy + 1), CARD)
    if not any((dn[0], dn[1] + k) in d8 for k in (-1, 1)):
        errors.append(f"z8: la bajada {dn} no se alcanza")
    walk9 = {c for c, it in caves["t9"].items() if bl.walkable(it) and it[0] in CAVE_FLOORS}
    d9 = reach(walk9, (dn[0], dn[1] + 1), CARD)
    if not any((portal[0] + dx, portal[1] + dy) in d9 for dx, dy in CARD):
        errors.append(f"z9: el portal final {portal} sin acceso")
    for t, label in ((caves["t8"], "z8"), (caves["t9"], "z9")):
        fl = {c for c, it in t.items() if it[0] in CAVE_FLOORS}
        for c, it in t.items():
            if c in fl:
                continue
            want = pieces_for(neighbors_in(fl, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
            if want is None or len(want) > 1 or (want and it[0] != want[0]) or (not want and it[0] != ROCK):
                errors.append(f"pared {label} {c}: quiere {want} tiene {it[0]}")
    for label, wk in (("z7", walk7), ("z8", walk8), ("z9", walk9)):
        for (x, y) in wk:
            if x < 8 or x > W - 9 or y < 6 or y > H - 7:
                errors.append(f"{label} {(x, y)}: se ve el borde de la caja")
                break

    # spawns: superficie por franjas de sur a norte, cuevas por distancia a la entrada
    rng = random.Random(a.seed + 99)
    reach7 = set(d7)
    avoid7 = grow({ARRIVAL} | set(PORTALS_BACK), 6) | grow({STAIRS, STAIRS_PORTAL}, 3) | grow(set(info["camps"]), 1)
    camp_area = {c for c in reach7 if c[1] >= HILLS_Y}
    hills_area = {c for c in reach7 if RUINS_Y <= c[1] < HILLS_Y}
    ruins_area = {c for c in reach7 if c[1] < RUINS_Y}
    slices7 = (slices_by(camp_area, lambda c: -c[1], 4) + slices_by(hills_area, lambda c: -c[1], 2)
               + slices_by(ruins_area, lambda c: -c[1], 2))
    spawns7 = place_stages(STAGES7, slices7, reach7, avoid7, Z7, rng, GAP)
    reach8 = set(d8)
    spawns8 = place_stages(STAGES8, slices_by(reach8, lambda c: d8[c], len(STAGES8)), reach8,
                           grow({STAIRS, dn}, 4), Z8, rng, GAP)
    reach9 = set(d9)
    spawns9 = place_stages(STAGES9, slices_by(reach9, lambda c: d9[c], len(STAGES9)), reach9,
                           grow({dn}, 4) | grow({portal}, 2), Z9, rng, GAP)

    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        if a.preview:
            write_preview(a.preview, [surf, caves["t8"], caves["t9"]], bl.otb)
        return 1

    counts: dict = {}
    for s in (spawns7, spawns8, spawns9):
        for _c, _z, mons in s:
            for name, _p, _t in mons:
                counts[name] = counts.get(name, 0) + 1
    n_mon = sum(counts.values())
    print(f"valle x{X0}-{X0 + W - 1} y{Y0}-{Y0 + H - 1}: z7 {len(reach7)} casillas, z8 {len(reach8)}, z9 {len(reach9)}; "
          f"spawns {len(spawns7)}+{len(spawns8)}+{len(spawns9)} ({n_mon} monstruos); llegada {X0 + ARRIVAL[0]},{Y0 + ARRIVAL[1]},7; "
          f"bajada {X0 + sx},{Y0 + sy},7; z9 {X0 + dn[0]},{Y0 + dn[1]},8; portal final {X0 + portal[0]},{Y0 + portal[1]},9")
    print("monstruos: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    if a.preview:
        write_preview(a.preview, [surf, caves["t8"], caves["t9"]], bl.otb)
        print(f"preview: {a.preview}")
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    # --- mapa: fuera el Hunt Maze viejo y la caja; adentro el valle ---
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    md = root[2][0]
    backup = MAP.with_name(MAP.name + ".bak-beastvalley")
    if not backup.exists():
        shutil.copy2(MAP, backup)

    def gone(gx, gy, z):
        in_box = X0 <= gx < X0 + W and Y0 <= gy < Y0 + H and z in (Z7, Z8, Z9)
        in_old = z == Z7 and OLD_MAZE[0] <= gx <= OLD_MAZE[2] and OLD_MAZE[1] <= gy <= OLD_MAZE[3]
        return in_box or in_old

    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        area[2] = [t for t in area[2] if not (t[0] in (T_TILE, T_HOUSETILE) and gone(ax + t[1][0], ay + t[1][1], az))]
        if not area[2]:
            md[2].remove(area)
    buckets: dict = {}
    for zz, t in ((Z7, surf), (Z8, caves["t8"]), (Z9, caves["t9"])):
        for (x, y), it in t.items():
            buckets.setdefault(((X0 + x) & ~0xFF, (Y0 + y) & ~0xFF, zz), []).append((X0 + x, Y0 + y, it))
    for (bx, by, zz), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, zz)), []]
        for gx, gy, it in sorted(lst, key=lambda t: (t[1], t[0])):
            area[2].append(new_tile(gx, gy, bx, by, it))
        md[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    # --- spawns: fuera el bloque del Hunt Maze y todo lo que caiga en las cajas ---
    sp = SPAWNS.read_text(encoding="latin-1")
    sp = re.sub(r"[ \t]*<!-- BEGIN HUNT_MAZE -->.*?<!-- END HUNT_MAZE -->\n?", "", sp, flags=re.S)
    sp = re.sub(r"[ \t]*<!-- BEGIN BEAST_VALLEY_SPAWNS.*?<!-- END BEAST_VALLEY_SPAWNS -->\n?", "", sp, flags=re.S)
    sp = re.sub(r'[ \t]*<spawn centerx="(\d+)" centery="(\d+)" centerz="(\d+)"[^>]*>.*?</spawn>\n?',
                lambda m: "" if gone(int(m.group(1)), int(m.group(2)), int(m.group(3))) else m.group(0), sp, flags=re.S)
    block = "\t<!-- BEGIN BEAST_VALLEY_SPAWNS (scripts/map/generate-beast-valley.py) -->\n" + \
        spawn_xml(spawns7 + spawns8 + spawns9) + "\n\t<!-- END BEAST_VALLEY_SPAWNS -->\n"
    sp = sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")

    # --- carteles ---
    rd = READABLES.read_text(encoding="latin-1")
    rd = re.sub(r"\t?<!-- BEGIN BEAST_VALLEY_SIGNS -->.*?<!-- END BEAST_VALLEY_SIGNS -->\n?", "", rd, flags=re.S)
    lines = ["\t<!-- BEGIN BEAST_VALLEY_SIGNS -->"]
    for (x, y), t in sorted(info["signs"].items()):
        lines.append(f'\t<readable x="{X0 + x}" y="{Y0 + y}" z="7" text="{t.replace(chr(10), chr(92) + "n")}"/>')
    lines.append("\t<!-- END BEAST_VALLEY_SIGNS -->\n")
    rd = rd.replace("</readables>", "\n".join(lines) + "</readables>")
    READABLES.write_text(rd, encoding="latin-1")

    if OLD_MANIFEST.exists():
        OLD_MANIFEST.unlink()
    MANIFEST.write_text(json.dumps({
        "name": "generated-beast-valley", "seed": a.seed, "replaces": "hunt-maze",
        "box": {"x1": X0, "y1": Y0, "x2": X0 + W - 1, "y2": Y0 + H - 1, "z": [Z7, Z8, Z9]},
        "oldMazeCleared": {"x1": OLD_MAZE[0], "y1": OLD_MAZE[1], "x2": OLD_MAZE[2], "y2": OLD_MAZE[3], "z": Z7},
        "landing": {"x": X0 + ARRIVAL[0], "y": Y0 + ARRIVAL[1], "z": 7},
        "portalsBack": [{"x": X0 + x, "y": Y0 + y, "z": 7, "to": list(TEMPLE_BACK)} for x, y in PORTALS_BACK + [STAIRS_PORTAL]]
        + [{"x": X0 + portal[0], "y": Y0 + portal[1], "z": 9, "to": list(TEMPLE_BACK)}],
        "stairs": {"x": X0 + sx, "y": Y0 + sy, "z": 7},
        "toAbyss": {"x": X0 + dn[0], "y": Y0 + dn[1], "z": 8},
        "spawns": {"z7": len(spawns7), "z8": len(spawns8), "z9": len(spawns9), "monsters": n_mon},
        "monsters": dict(sorted(counts.items())),
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK carteles {READABLES}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
