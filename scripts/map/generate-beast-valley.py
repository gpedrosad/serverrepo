#!/usr/bin/env python3
"""Valle de las Bestias v3: valle compacto, zonas temáticas y cuevas de dos pisos.

La v1 (nov 2026) era un campo abierto de ~9.000 casillas con dos cuevas enormes de ~6.000: se veía
vacío y todos los monstruos estaban mezclados. La v3 reduce el valle a un camino de bosque con seis
zonas chicas y bien separadas, y da a cada cueva un segundo piso más largo y con más monstruos:

  z7  Llegada (portales de vuelta) -> Cruce del Valle (cartel)
      Campamento Minotauro (oeste)     Minotaur, Archer, Guard, Mage
      Cantera de los Cíclopes (este)   Cyclops, Cyclops Drone, Cyclops Smith
      Ruinas Antiguas (norte)          Skeleton, Ghoul, Mummy, Demon Skeleton
  z8  Entrada de cada cueva (corta)
      Catacumbas / Cueva de las Quaras / Guarida del Dragón
  z9  Fondo de cada cueva (largo, 4 tramos, más monstruos)
      Cripta Profunda (no-muertos), Nido de las Quaras, Nido del Dragón
  z10 Abismo: Hydra/Dark Hydra -> Behemoth/Serpent Spawn -> Demon/Fury, Root Colossus y portal final

Cada zona y cada cueva tiene su cartel y su decoración (columnas y lápidas en las ruinas, huesos y
pilares en las catacumbas, hongos y barro en las quaras, huesos de dragón y braseros). El valle es un
corredor de ~11 casillas rodeado de bosque cerrado: no se ve el borde de la caja ni quedan claros.

Caja: x 262-361, y 232-378, z7-z10. Borra además todo el Hunt Maze viejo (x 280-349, y 243-400, z7).
No toca la Hell Quest (y <= 226), el Paso del Norte (x >= 370), el Reloj de Arena (z5-z6) ni la
Torre del Barquero.

Reglas que valida antes de escribir (si algo falla no escribe nada):
  - bordes de tierra con su pieza; paredes de cada cueva con pieza única sobre su piso combinado;
  - se llega de la llegada a cada zona, a las tres bocas y a los portales;
  - en z8, la bajada de cada cueva se alcanza desde su boca; en z9, la bajada del dragón;
  - en z10, el portal final; desde cualquier casilla caminable la pantalla entera tiene casillas.

Uso (desde la raíz del repo; Pillow no hace falta):
  python3 scripts/map/generate-beast-valley.py --dry-run --preview /tmp/valle.png
  python3 scripts/map/generate-beast-valley.py          # escribe mapa, spawns, carteles y manifiesto
  python3 scripts/map/temple-portals.py                 # después: apunta el portal de la plaza
Re-ejecutable: borra la caja z7-z10 y reemplaza los bloques BEAST_VALLEY de spawns y carteles.
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
CAVE_FLOORS, CARD, ALL8 = NP.CAVE_FLOORS, NP.CARD, NP.ALL8

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MANIFEST = WORLD / "generated-beast-valley.json"
OLD_MANIFEST = WORLD / "generated-hunt-maze.json"

X0, Y0, W, H = 262, 232, 100, 147          # x 262-361, y 232-378
OLD_MAZE = (280, 243, 349, 400)            # Hunt Maze viejo (z7): se borra entero
Z7, Z8, Z9, Z10 = 7, 8, 9, 10
BAND = 8                                    # franja exterior intransitable (la pantalla no ve el borde)
TEMPLE_BACK = (158, 48, 7)                  # llegada del portal de la plaza (temple-portals.py)
VIEW = (7, 5)                               # media pantalla del cliente 7.6

# --- piezas (ids de servidor) ---------------------------------------------------------------------
GRASS, DIRT = NP.GRASS, NP.DIRT
FOREST_TREES, SMALL_TREE, BUSHES = NP.FOREST_TREES, NP.FOREST_SMALL_TREE, NP.BUSHES
FLOWERS, MUSHROOMS, DEAD_TREES = NP.FLOWERS, NP.MUSHROOMS, NP.DEAD_TREES
STONE, RUBBLE, RUBBLE_BROWN, PEBBLES = NP.STONE, NP.RUBBLE_GREY, NP.RUBBLE_BROWN, NP.PEBBLES
BONES, DRAGON_SKULL, DRAGON_BONES, SKELETON = NP.BONES, NP.DRAGON_SKULL, NP.DRAGON_BONES, NP.HUMAN_SKELETON
CAMPFIRE, LANTERN, SIGN = NP.CAMPFIRE, NP.LANTERN, NP.SIGN
TELEPORT, ATTR_TELE_DEST = NP.TELEPORT, NP.ATTR_TELE_DEST
STAIR_DOWN, STAIRS_UP = NP.STAIR_DOWN, NP.STAIRS_UP
PILLAR, BROKEN_PILLAR, STATUE, ALTAR, COAL_BASIN = 1515, 3767, 1442, 1642, 2602
BARREL, CRATE = 1770, 1739
CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD = NP.CAVE_FLOOR, NP.CAVE_FLOOR_ALT, NP.CAVE_MUD

# --- recorrido de la superficie (coordenadas locales, x 0-99, y 0-146) ----------------------------
ARRIVAL = (50, 128)                          # destino del portal de la plaza
PORTALS_BACK = [(50, 133), (51, 133)]        # vuelta al templo, al sur de la llegada
CROSS = (50, 96)                             # Cruce del Valle (cartel)
RUINS = (50, 41, 12, 9)                      # patio de las ruinas: centro x, y y radios (tierra)
STAIRS_CAT = (50, 34)                        # bajada a las Catacumbas
MOUTH_QUARA = (29, 62)                       # bajada a la Cueva de las Quaras
MOUTH_DRAGON = (72, 56)                      # bajada a la Guarida del Dragón

ROUTES = [
    ((50, 126), (50, 112), (48, 104), (50, 96)),                 # llegada -> cruce
    ((45, 96), (39, 92), (34, 88), (30, 84)),                    # cruce -> campamento
    ((55, 96), (62, 93), (67, 90), (71, 88)),                    # cruce -> cantera
    ((50, 94), (52, 84), (48, 72), (52, 60), (50, 50), (50, 44)),  # cruce -> ruinas
    ((46, 50), (41, 55), (35, 59), (30, 62)),                    # ruinas -> dell de quaras
    ((54, 50), (60, 53), (66, 55), (71, 56)),                    # ruinas -> dell del dragón
    ((50, 40), (50, 36), (50, 34)),                              # patio -> bajada catacumbas
]
ZONES = {
    "camp": (30, 84, 10, 7),
    "quarry": (71, 88, 10, 7),
    "cross": (50, 96, 9, 7),
    "ruins": RUINS,
    "quara": (29, 62, 8, 6),
    "dragon": (72, 56, 9, 7),
}

# --- caza por zona: una familia por zona, dificultad de arriba a abajo ----------------------------
SURFACE_HUNTS = {
    "camp": (("Minotaur", "Minotaur Archer", "Minotaur Guard", "Minotaur Mage"), 3, 70),
    "quarry": (("Cyclops", "Cyclops Drone", "Cyclops Smith"), 3, 80),
    "ruins": (("Skeleton", "Ghoul", "Mummy", "Demon Skeleton"), 3, 90),
}
SURFACE_HUNTS_N = {"camp": 14, "quarry": 12, "ruins": 13}
CAVE_HUNTS = {"catacumbs": (("Ghoul", "Skeleton"), ("Vampire", "Mummy", "Demon Skeleton"),
                            ("Necromancer", "Priestess", "Vampire Bride"))}
# --- cuevas: z8 entrada (corta), z9 fondo (largo, más monstruos) y z10 Abismo -----------------------
CAVES = [
    {"name": "catacumbs", "box": (30, 8, 44, 40), "mouth": STAIRS_CAT, "mud": 0.10, "alt": 0.36,
     "bones": 0.10, "min": 320, "sign": "CATACUMBAS\nNo-muertos: ghouls, vampiros, momias y nigromantes.\nAbajo: Cripta Profunda."},
    {"name": "quara", "box": (8, 44, 44, 38), "mouth": MOUTH_QUARA, "mud": 0.55, "alt": 0.28,
     "bones": 0.05, "min": 340,
     "sign": "CUEVA DE LAS QUARAS\nQuaras constrictor, mantassin, pincher, hidromante y predator.\nAbajo: Nido de las Quaras."},
    {"name": "dragon", "box": (50, 40, 44, 40), "mouth": MOUTH_DRAGON, "mud": 0.28, "alt": 0.30,
     "bones": 0.09, "min": 320, "sign": "GUARIDA DEL DRAGON\nDragones, wyrms y un dragon negro.\nAbajo: el Nido y el Abismo."},
]
# segundo piso de cada cueva: más largo y con más monstruos
DEEP_CAVES = [
    # corrida 16 al este (nov 2026) para quedar debajo de la bajada de las Catacumbas (z8, x 44-65)
    {"name": "catacumbs", "box": (22, 4, 46, 46), "mouth": (41, 41), "mud": 0.12, "alt": 0.34,
     "bones": 0.12, "min": 420,
     "spine": [(41, 33), (34, 28), (34, 18), (46, 14), (56, 18), (56, 26)]},
    {"name": "quara", "box": (6, 50, 46, 40), "mouth": (24, 80), "mud": 0.58, "alt": 0.26,
     "bones": 0.05, "min": 420,
     "spine": [(24, 72), (17, 66), (17, 60), (28, 58), (38, 62), (40, 70)]},
    {"name": "dragon", "box": (50, 42, 46, 42), "mouth": (72, 74), "mud": 0.30, "alt": 0.28,
     "bones": 0.10, "min": 420,
     "spine": [(72, 68), (63, 66), (60, 58), (70, 53), (82, 55), (86, 64)]},
]
# La boca de cada piso de abajo (z9 y el Abismo) es la bajada del piso de arriba: build_caves() la elige
# dentro de la caja del piso de abajo y reemplaza "mouth". Por eso la caja del Abismo pisa (en x, y) la
# del Nido del Dragón. Hasta nov 2026 cada piso tenía una boca fija y las bajadas caían sobre roca.
ABYSS = {"name": "abyss", "box": (50, 52, 46, 46), "mouth": (72, 92), "mud": 0.60, "alt": 0.26,
         "bones": 0.12, "min": 400}
CAVE_STAGES = {
    "catacumbs": [(("Ghoul", "Skeleton"), 3, 100), (("Vampire", "Mummy", "Demon Skeleton"), 3, 130),
                  (("Necromancer", "Priestess", "Vampire Bride"), 3, 160)],
    "quara": [(("Quara Constrictor", "Quara Mantassin"), 2, 110), (("Quara Pincher", "Quara Hydromancer"), 2, 140),
              (("Quara Predator",), 2, 170)],
    "dragon": [(("Dragon Hatchling", "Dragon"), 3, 150), (("Dragon", "Wyrm"), 3, 190),
               (("Dragon Lord", "Black Dragon"), 2, 240)],
}
DEEP_STAGES = {
    "catacumbs": [(("Ghoul", "Skeleton"), 4, 120), (("Mummy", "Vampire", "Demon Skeleton"), 4, 140),
                  (("Necromancer", "Priestess", "Vampire Bride"), 3, 170),
                  (("Vampire Bride", "Necromancer", "Priestess", "Demon Skeleton"), 3, 200)],
    "quara": [(("Quara Constrictor", "Quara Mantassin"), 2, 120),
              (("Quara Pincher", "Quara Hydromancer"), 2, 150),
              (("Quara Predator", "Quara Pincher"), 2, 180),
              (("Quara Predator", "Quara Hydromancer"), 2, 210)],
    "dragon": [(("Dragon Hatchling", "Dragon"), 3, 160), (("Dragon", "Wyrm"), 3, 190),
               (("Wyrm", "Dragon Lord"), 3, 220), (("Dragon Lord", "Black Dragon"), 2, 260)],
}
ABYSS_STAGES = [(("Hydra", "Dark Hydra"), 3, 220), (("Behemoth", "Serpent Spawn"), 3, 250),
                (("Demon", "Fury"), 2, 300), (("Demon", "Behemoth", "Fury"), 2, 330)]
GAP = 6                                       # distancia mínima entre centros de spawn
# Quaras (nov 2026): salían 3-4 por spawn cada 6 casillas y 17 grupos en z8 alrededor de la escalera.
# Ahora de a 2, más separados en la entrada y sin spawns pegados a las escaleras (~58 en vez de 130).
CAVE_GAP = {("quara", 8): 7, ("quara", 9): 6}  # (cueva, piso): separación; el resto usa GAP
STAIR_CLEAR = {"quara": 5}                    # sin spawns a esta distancia de las escaleras (el resto: 3)


def ellipse(cx, cy, rx, ry) -> set:
    return {(x, y) for x in range(int(cx - rx) - 1, int(cx + rx) + 2) for y in range(int(cy - ry) - 1, int(cy + ry) + 2)
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1}


def grow(cells, r: int) -> set:
    return {(x + dx, y + dy) for (x, y) in cells for dx in range(-r, r + 1) for dy in range(-r, r + 1)}


def stamp(points, r: int) -> set:
    """Casillas a distancia de bloque `r` de una polilínea, avanzando en pasos Manhattan
    (sin diagonales: los bordes de tierra necesitan formas ortogonales para converger)."""
    cells = set()

    def block(x, y):
        cells.update({(x + a, y + b) for a in range(-r, r + 1) for b in range(-r, r + 1)})

    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        x, y = x1, y1
        block(x, y)
        axes = ("x", "y") if abs(x2 - x1) >= abs(y2 - y1) else ("y", "x")
        for axis in axes:
            while (x != x2) if axis == "x" else (y != y2):
                if axis == "x":
                    x += 1 if x2 > x else -1
                else:
                    y += 1 if y2 > y else -1
                block(x, y)
    return cells


# --- superficie -------------------------------------------------------------------------------------

def build_surface(seed: int, bl: Blocking):
    rng = random.Random(seed)
    nz = Noise(seed)
    cells = {(x, y) for y in range(H) for x in range(W)}
    inner = {(x, y) for (x, y) in cells if BAND + 1 <= x < W - BAND - 1 and BAND + 1 <= y < H - BAND - 1}

    # 1) corredor: camino + plazas + zonas (forma limpia para los bordes de tierra)
    route = set().union(*(stamp(pts, 3) for pts in ROUTES))
    zones = {name: ellipse(*z) for name, z in ZONES.items()}
    arrival_zone = {(ARRIVAL[0] + dx, ARRIVAL[1] + dy) for dx in range(-4, 5) for dy in range(-3, 6)}
    mouths = {STAIRS_CAT, MOUTH_QUARA, MOUTH_DRAGON}
    mouth_zones = set().union(*({(m[0] + dx, m[1] + dy) for dx in range(-3, 4) for dy in range(-3, 4)} for m in mouths))
    play = (route | set().union(*zones.values()) | arrival_zone | mouth_zones) & inner

    # 2) tierra: caminos (3 de ancho), patio de ruinas, campamento, cantera y llegada
    path = set().union(*(stamp(pts, 1) for pts in ROUTES)) & play
    dirt = (path | (zones["ruins"] & play) | ellipse(30, 84, 7, 5) | ellipse(71, 88, 7, 5)
            | {(ARRIVAL[0] + dx, ARRIVAL[1] + dy) for dx in range(-3, 4) for dy in range(-2, 4)}) & play
    dirt = fix_until_valid(dirt, inner, DIRT_SIDE, DIRT_CORNER, DIRT_INNER, single=True)
    play |= dirt

    # 3) borde orgánico del valle (sin tocar la tierra, que ya tiene sus piezas)
    for c in sorted(play - dirt):
        edge = any((c[0] + dx, c[1] + dy) not in play for dx, dy in ALL8)
        if edge and nz.fbm(c[0] / 5.5, c[1] / 5.5, 2, 120) < 0.44:
            play.discard(c)
    for c in sorted(grow(play, 1) & inner):
        if c not in play and nz.fbm(c[0] / 4.5, c[1] / 4.5, 2, 220) > 0.64:
            play.add(c)
    play |= set(PORTALS_BACK) | mouths | {ARRIVAL}

    tiles: dict = {}
    for c in cells:
        if c in dirt:
            tiles[c] = [DIRT]
        else:
            edge = pieces_for(neighbors_in(dirt, *c), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
            tiles[c] = [edge[0]] if edge else [GRASS]

    # 3) bosque cerrado: pinares 2x2 y relleno 1x1 en todo lo que no es valle
    occupied: set = set()

    def free(c, r=0):
        return all((c[0] + dx, c[1] + dy) not in occupied for dx in range(-r, r + 1) for dy in range(-r, r + 1))

    def put(c, item, size=1):
        tiles[c].append(item)
        for dx in range(size):
            for dy in range(size):
                occupied.add((c[0] - dx, c[1] - dy))

    keep_clear = path | arrival_zone | mouth_zones | {(x, y) for x in range(45, 56) for y in range(30, 52)}
    occupied |= keep_clear

    def themed_fill(x, y):
        near_quarry = math.hypot(x - 71, y - 88) < 20
        near_quara = math.hypot(x - 29, y - 62) < 17
        near_ruins = math.hypot(x - 50, y - 41) < 24
        r = rng.random()
        if near_quarry:
            return rng.choice((STONE, RUBBLE)) if r < 0.22 else rng.choice((SMALL_TREE,) + BUSHES)
        if near_quara:
            return rng.choice((SMALL_TREE, SMALL_TREE) + BUSHES)
        if near_ruins:
            return rng.choice(DEAD_TREES) if r < 0.30 else rng.choice((SMALL_TREE,) + BUSHES)
        return rng.choice((SMALL_TREE, SMALL_TREE, SMALL_TREE) + BUSHES)

    # pinares grandes (2x2) en una grilla alterna; cada casilla del bosque queda con su bloqueo 1x1
    for c in sorted(cells - play):
        x, y = c
        if x % 2 == 1 and y % 2 == 1 and rng.random() < 0.62:
            tiles[c].append(rng.choice(FOREST_TREES))
        else:
            tiles[c].append(themed_fill(x, y))

    # 4) campamento minotauro: fogatas y pertrechos alrededor del claro
    camps = []
    for k, (dx, dy) in enumerate(((0, -4), (-4, 0), (0, 4), (4, 0))):
        camp = (30 + dx, 84 + dy)
        if camp not in play:
            continue
        items = {camp: CAMPFIRE, (camp[0] + 1, camp[1] - 1): STONE,
                 (camp[0] + 1, camp[1] + 1): BARREL, (camp[0] - 1, camp[1] - 1): CRATE}
        for c, it in items.items():
            if c in play and c not in keep_clear and len(tiles[c]) == 1 and free(c):
                put(c, it)
        occupied |= {(camp[0] + a, camp[1] + b) for a in range(-2, 3) for b in range(-2, 3)}
        camps.append(camp)

    # 5) cantera de los cíclopes: rocas agrupadas, piedras y troncos secos
    for c in sorted(zones["quarry"] & play - keep_clear):
        x, y = c
        r = rng.random()
        rocky = nz.fbm(x / 4.0, y / 4.0, 2, 700)
        if r < 0.30 and free(c, 1):
            put(c, rng.choice((RUBBLE, RUBBLE_BROWN)), 2)
        elif r < 0.44 and free(c):
            put(c, STONE)
        elif r < 0.50 and free(c, 1):
            put(c, rng.choice(DEAD_TREES), 2)
        elif r < 0.62:
            tiles[c].append(PEBBLES)

    # 6) ruinas: avenida de columnas, estatuas, braseros, altar y cementerio
    cx, cy, rx, ry = RUINS
    ruin_items = {}
    for y in range(STAIRS_CAT[1] + 3, int(cy + ry), 3):
        for x in (46, 54):
            ruin_items[(x, y)] = BROKEN_PILLAR if (x * 7 + y * 3) % 4 == 0 else PILLAR
    ruin_items[(44, cy + 6)] = STATUE
    ruin_items[(56, cy + 6)] = STATUE
    ruin_items[(43, cy - 1)] = ALTAR
    for c in ((44, cy - 5), (56, cy - 5), (44, cy + 3), (56, cy + 3)):
        ruin_items[c] = COAL_BASIN
    for c, it in ruin_items.items():
        if c in play and c not in keep_clear and len(tiles[c]) == 1 and free(c):
            put(c, it)
    for c in sorted(zones["ruins"] & play):
        x, y = c
        if c in occupied or len(tiles[c]) > 1:
            continue
        if 45 <= x <= 55:
            continue
        r = rng.random()
        if r < 0.05 and free(c, 1):
            put(c, rng.choice((RUBBLE, RUBBLE_BROWN)), 2)
        elif r < 0.10:
            tiles[c].append(rng.choice(BONES + (PEBBLES, SKELETON)))
    graves = set()
    for y in range(20, cy + ry, 3):
        for x in range(BAND + 3, W - BAND - 3, 3):
            if rng.random() < 0.5:
                continue
            c = (x + rng.choice((-1, 0, 1)), y + rng.choice((0, 0, 1)))
            if (c in play and c not in zones["ruins"] and c not in keep_clear
                    and nz.fbm(x / 8, y / 8, 2, 300) > 0.50 and free(c, 1)):
                put(c, BROKEN_PILLAR)
                graves.add(c)

    # 7) dell de las quaras y dell del dragón: cada boca con su paisaje
    for c in sorted(zones["quara"] & play - keep_clear):
        x, y = c
        if c in occupied or len(tiles[c]) > 1:
            continue
        r = rng.random()
        if r < 0.10 and free(c):
            put(c, rng.choice(MUSHROOMS))
        elif r < 0.16 and free(c, 1):
            put(c, rng.choice(DEAD_TREES), 2)
        elif r < 0.22:
            tiles[c].append(rng.choice(BONES + (PEBBLES,)))
    for c in sorted(zones["dragon"] & play - keep_clear):
        x, y = c
        if c in occupied or len(tiles[c]) > 1:
            continue
        r = rng.random()
        if r < 0.06 and free(c, 1):
            put(c, rng.choice((RUBBLE, RUBBLE_BROWN)), 2)
        elif r < 0.10:
            tiles[c].append(DRAGON_SKULL if r < 0.08 else DRAGON_BONES)

    # 8) flores y hongos en el corredor, lejos del camino
    for c in sorted(play - keep_clear):
        if c in occupied or len(tiles[c]) > 1:
            continue
        r = rng.random()
        if r < 0.035:
            tiles[c].append(rng.choice(FLOWERS))
        elif r < 0.05:
            tiles[c].append(rng.choice(MUSHROOMS))

    # 9) faroles siguiendo el camino
    for pts in ROUTES[:4]:
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            n = max(abs(x2 - x1), abs(y2 - y1), 1)
            for i in range(4, n, 11):
                x, y = int(round(x1 + (x2 - x1) * i / n)), int(round(y1 + (y2 - y1) * i / n))
                c = (x - 2, y)
                if c in play and c not in keep_clear and len(tiles[c]) == 1 and free(c):
                    put(c, LANTERN)

    # 10) bocas de cueva: escalera, marco de piedra, braseros y cartel
    for mouth in (STAIRS_CAT, MOUTH_QUARA, MOUTH_DRAGON):
        mx, my = mouth
        tiles[mouth] = [STAIR_DOWN]
        for dx, dy in ((-2, -1), (-2, 0), (-2, 1), (2, -1), (2, 1), (-1, -2), (1, -2)):
            c = (mx + dx, my + dy)
            if c in play:
                tiles[c] = [tiles[c][0], STONE]
        for dx in (-1, 1):
            c = (mx + dx, my + 1)
            if c in play:
                tiles[c] = [tiles[c][0], COAL_BASIN]
    # portales de vuelta en la llegada
    for c in PORTALS_BACK:
        tiles[c] = [tiles[c][0], TELEPORT]
    px0, px1, py = PORTALS_BACK[0][0], PORTALS_BACK[1][0], PORTALS_BACK[0][1]
    for c in ((px0 - 1, py), (px1 + 1, py), (px0 - 1, py + 1), (px1 + 1, py + 1), (px0, py + 1), (px1, py + 1)):
        tiles[c] = [tiles[c][0], STONE]
    for c in ((px0 - 2, py - 1), (px1 + 2, py - 1)):
        tiles[c] = [tiles[c][0], LANTERN]

    hy = ARRIVAL[1] - 2
    signs = {
        (ARRIVAL[0] + 3, ARRIVAL[1] - 1): "VALLE DE LAS BESTIAS\nAl norte: Cruce del Valle.\n"
                                          "Campamento Minotauro (oeste), Cantera de Ciclopes (este),\n"
                                          "Ruinas y cuevas (norte). Portal al sur: templo.",
        (CROSS[0] + 3, CROSS[1] - 1): "CRUCE DEL VALLE\nOeste: Campamento Minotauro.\n"
                                      "Este: Cantera de Ciclopes.\nNorte: Ruinas Antiguas y cuevas.",
        (STAIRS_CAT[0] - 3, STAIRS_CAT[1] + 1): "CATACUMBAS\nNo-muertos: ghouls, vampiros, momias\n"
                                                "y nigromantes.",
        (MOUTH_QUARA[0] + 3, MOUTH_QUARA[1] + 1): "CUEVA DE LAS QUARAS\nQuaras constrictor, mantassin, pincher,\n"
                                                  "hidromante y predator.",
        (MOUTH_DRAGON[0] + 3, MOUTH_DRAGON[1] + 1): "GUARIDA DEL DRAGON\nDragones, wyrms y un dragon negro.\n"
                                                    "Solo para veteranos.",
        (RUINS[0] + 3, RUINS[1] + 8): "RUINAS ANTIGUAS\nNo todos los muertos descansan.",
    }
    placed = {}
    for anchor, text in signs.items():
        cands = [c for c in play - keep_clear if len(tiles[c]) == 1 and c not in placed
                 and any((c[0] + dx, c[1] + dy) in keep_clear for dx, dy in CARD)]
        if not cands:
            raise RuntimeError(f"no hay lugar para el cartel cerca de {anchor}")
        c = min(cands, key=lambda c: (abs(c[0] - anchor[0]) + abs(c[1] - anchor[1]), c))
        tiles[c] = [tiles[c][0], SIGN]
        placed[c] = text

    return tiles, {"path": path, "play": play, "dirt": dirt, "zones": zones, "camps": camps,
                   "signs": placed, "cells": cells, "inner": inner}


# --- cuevas -------------------------------------------------------------------------------------------

def carve_named(seed: int, spec: dict):
    """Cava una cueva dentro de su caja (x, y, w, h) desde su boca y devuelve piso y tiles."""
    bx, by, bw, bh = spec["box"]
    allowed = {(x, y) for x in range(bx + 6, bx + bw - 6) for y in range(by + 6, by + bh - 6)}
    mx, my = spec["mouth"]
    core = {(mx + dx, my + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1, 2)}
    spine = spec.get("spine", [])
    for sx, sy in spine:
        core |= {(sx + dx, sy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    if spine:  # pasillo en L de la boca al punto más cercano del recorrido
        sx, sy = min(spine, key=lambda c: abs(c[0] - mx) + abs(c[1] - my))
        for x in range(min(mx, sx), max(mx, sx) + 1):
            core |= {(x, my + d) for d in (-1, 0, 1)}
        for y in range(min(my, sy), max(my, sy) + 1):
            core |= {(sx + d, y) for d in (-1, 0, 1)}
    floor = carve_cave(seed, allowed, core, (mx, my + 1), spec["min"])
    return floor


def mouth_zone(spec: dict) -> set:
    """Casillas donde puede ir la boca de una cueva: el núcleo (boca y 2 al sur) y un margen para los
    bloques de 2x2 de carve_cave tienen que caber en su caja."""
    bx, by, bw, bh = spec["box"]
    return {(x, y) for x in range(bx + 6 + 4, bx + bw - 6 - 4) for y in range(by + 6 + 4, by + bh - 6 - 6)}


def stair_down(floor: set, start, below: dict):
    """La bajada: la casilla ancha (3x5 de piso) más lejos de la entrada que además sirve de boca para
    la cueva de abajo."""
    d = reach(floor, start, CARD)
    zone = mouth_zone(below)
    wide = [c for c in floor if c in zone and c in d and all((c[0] + dx, c[1] + dy) in floor
                                                             for dx in (-1, 0, 1) for dy in (-2, -1, 0, 1, 2))]
    if not wide:
        raise ValueError(f"{below['name']}: no hay dónde poner la bajada encima de su caja")
    return max(wide, key=lambda c: (d[c], c))


def paint_cave(tiles: dict, floor: set, seed: int, mud: float, alt: float):
    """Repinta el piso de una cueva con su paleta (barro/alterno) sin tocar las paredes."""
    nz = Noise(seed + 515)
    for (x, y) in floor:
        v = nz.fbm(x / 5, y / 5, 3, 10) + mud - 0.42
        tiles[(x, y)] = [CAVE_MUD if v > 0.55 else CAVE_FLOOR_ALT if v < alt else CAVE_FLOOR]


def build_caves(seed: int):
    cells = {(x, y) for x in range(W) for y in range(H)}

    # z8: cuevas de entrada (cortas), una bajada al fondo de cada una
    floors8 = {}
    for i, spec in enumerate(CAVES):
        floors8[spec["name"]] = carve_named(seed + 1 + i, spec)
    union8 = set().union(*floors8.values())
    t8 = cave_tiles(union8, cells, seed + 1)
    for i, spec in enumerate(CAVES):
        paint_cave(t8, floors8[spec["name"]], seed + i, spec["mud"], spec["alt"])
        t8[spec["mouth"]].append(STAIRS_UP)
    down8 = {}
    for spec, deep in zip(CAVES, DEEP_CAVES):
        floor = floors8[spec["name"]]
        down8[spec["name"]] = stair_down(floor, (spec["mouth"][0], spec["mouth"][1] + 1), deep)
        t8[down8[spec["name"]]] = [STAIR_DOWN]
        deep["mouth"] = down8[spec["name"]]      # el fondo empieza justo debajo

    # z9: fondo largo de cada cueva (misma familia, más monstruos)
    floors9 = {}
    for i, spec in enumerate(DEEP_CAVES):
        floors9[spec["name"]] = carve_named(seed + 11 + i, spec)
    union9 = set().union(*floors9.values())
    t9 = cave_tiles(union9, cells, seed + 11)
    for i, spec in enumerate(DEEP_CAVES):
        paint_cave(t9, floors9[spec["name"]], seed + 31 + i, spec["mud"], spec["alt"])
        t9[spec["mouth"]].append(STAIRS_UP)
    # el fondo de los dragones baja al Abismo
    d9 = reach(floors9["dragon"], (DEEP_CAVES[2]["mouth"][0], DEEP_CAVES[2]["mouth"][1] + 1), CARD)
    down9 = stair_down(floors9["dragon"], (DEEP_CAVES[2]["mouth"][0], DEEP_CAVES[2]["mouth"][1] + 1), ABYSS)
    t9[down9] = [STAIR_DOWN]
    ABYSS["mouth"] = down9

    # z10: Abismo (final de la progresión)
    floor10 = carve_named(seed + 41, ABYSS)
    t10 = cave_tiles(floor10, cells, seed + 41)
    paint_cave(t10, floor10, seed + 47, ABYSS["mud"], ABYSS["alt"])
    t10[ABYSS["mouth"]].append(STAIRS_UP)
    d10 = reach(floor10, (ABYSS["mouth"][0], ABYSS["mouth"][1] + 1), CARD)
    portal_cands = [c for c in floor10 if all((c[0] + a, c[1] + b) in floor10 for a in (-1, 0, 1) for b in (-1, 0, 1))]
    portal = max(portal_cands, key=lambda c: d10[c])
    t10[portal].append(TELEPORT)
    for a, b in ((-1, -1), (1, -1)):
        t10[(portal[0] + a, portal[1] + b)].append(COAL_BASIN)
    return {"t8": t8, "floors8": floors8, "down8": down8,
            "t9": t9, "floors9": floors9, "down9": down9, "d9": d9,
            "t10": t10, "floor10": floor10, "d10": d10, "portal": portal}


def place_props(tiles: dict, floor: set, start, props, rate: float, seed: int, keep=frozenset()):
    """Props de tema (pilares, braseros, huesos) en el borde de la cueva, sin cortar el paso."""
    rng = random.Random(seed + 777)
    walk = set(floor)
    base = len(reach(walk, start, CARD))
    for c in sorted(floor, key=lambda c: (c[1], c[0])):
        if c not in walk or c in keep or len(tiles[c]) > 1 or tiles[c][0] == STAIR_DOWN:
            continue
        x, y = c
        if 8 - len(neighbors_in(floor, x, y)) < 2 or rng.random() > rate:
            continue
        item = rng.choice(props)
        walk.discard(c)
        if len(reach(walk, start, CARD)) != base - 1:
            walk.add(c)
            continue
        base -= 1
        tiles[c].append(item)


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


def root_colossus_spawn(walk, distances, avoid=frozenset(), z=Z9):
    """Un guardián al final del Abismo, antes del portal; busca una sala de 3x3 libre."""
    late = slices_by(walk - avoid, lambda c: distances[c], 3)[-1]
    threshold = min(distances[c] for c in late)
    candidates = []
    for x, y in late:
        if distances[(x, y)] > threshold + 22:
            continue
        if not all((x + dx, y + dy) in walk and (x + dx, y + dy) not in avoid
                   for dx in range(-1, 2) for dy in range(-1, 2)):
            continue
        candidates.append((abs(distances[(x, y)] - threshold - 8), x, y))
    if not candidates:
        raise ValueError("Abismo: no hay una sala libre para Root Colossus en el último tramo")
    _distance, x, y = min(candidates)
    return ((x, y), z, [("Root Colossus", (x, y), 300)])


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


def write_preview(path: Path, layers, otb, bl=None):
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
        base = ((c // 36) % 6 * 51, (c // 6) % 6 * 51, c % 6 * 51)
        if bl and any(bl.blocks(i) for i in items):
            return tuple(v // 3 for v in base)
        return base

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
    portal = caves["portal"]
    dn8, dn9 = caves["down8"], caves["down9"]

    # decoración de cada cueva con su tema
    for i, spec in enumerate(CAVES):
        start_pos = (spec["mouth"][0], spec["mouth"][1] + 1)
        decorate_cave(caves["t8"], caves["floors8"][spec["name"]], start_pos,
                      grow({spec["mouth"], dn8[spec["name"]]}, 2), a.seed + i + 1, spec["bones"], bl)
    for i, spec in enumerate(DEEP_CAVES):
        start_pos = (spec["mouth"][0], spec["mouth"][1] + 1)
        keep = grow({spec["mouth"]}, 2) | (grow({dn9}, 2) if spec["name"] == "dragon" else set())
        decorate_cave(caves["t9"], caves["floors9"][spec["name"]], start_pos, keep,
                      a.seed + 51 + i, spec["bones"], bl)
    decorate_cave(caves["t10"], caves["floor10"], (ABYSS["mouth"][0], ABYSS["mouth"][1] + 1),
                  grow({ABYSS["mouth"], portal}, 2), a.seed + 61, ABYSS["bones"], bl)
    CAVE_PROPS = {
        "catacumbs": ((BROKEN_PILLAR, COAL_BASIN, SKELETON, SKELETON), 0.09),
        "quara": (MUSHROOMS + BONES, 0.07),
        "dragon": ((DRAGON_SKULL, DRAGON_BONES, COAL_BASIN), 0.07),
    }
    for i, spec in enumerate(CAVES):
        place_props(caves["t8"], caves["floors8"][spec["name"]], (spec["mouth"][0], spec["mouth"][1] + 1),
                    *CAVE_PROPS[spec["name"]], a.seed + i, grow({spec["mouth"], dn8[spec["name"]]}, 2))
    for i, spec in enumerate(DEEP_CAVES):
        place_props(caves["t9"], caves["floors9"][spec["name"]], (spec["mouth"][0], spec["mouth"][1] + 1),
                    *CAVE_PROPS[spec["name"]], a.seed + 70 + i, grow({spec["mouth"], dn9}, 2))
    place_props(caves["t10"], caves["floor10"], (ABYSS["mouth"][0], ABYSS["mouth"][1] + 1),
                (COAL_BASIN, DRAGON_BONES), 0.07, a.seed + 80, grow({ABYSS["mouth"], portal}, 2))

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
    targets = {"cruce": CROSS, "campamento": (30, 84), "cantera": (71, 88), "ruinas": (50, 41),
               "bajada catacumbas": (STAIRS_CAT[0], STAIRS_CAT[1] + 1),
               "boca quaras": (MOUTH_QUARA[0], MOUTH_QUARA[1] + 1),
               "boca dragon": (MOUTH_DRAGON[0], MOUTH_DRAGON[1] + 1)}
    for label, c in targets.items():
        if not any((c[0] + dx, c[1] + dy) in d7 for dx, dy in CARD + ((0, 0),)):
            errors.append(f"z7: {label} {c} no se alcanza desde la llegada")
    for c in PORTALS_BACK:
        if not any((c[0] + dx, c[1] + dy) in d7 for dx, dy in CARD):
            errors.append(f"z7: portal de la llegada {c} sin acceso")

    def cave_walk(t, floor):
        return {c for c in floor if bl.walkable(t[c])}

    d8 = {}
    for spec in CAVES:
        floor = caves["floors8"][spec["name"]]
        walk = cave_walk(caves["t8"], floor)
        start_pos = (spec["mouth"][0], spec["mouth"][1] + 1)
        d8[spec["name"]] = reach(walk, start_pos, CARD)
        if len(d8[spec["name"]]) < spec["min"] * 0.75:
            errors.append(f"{spec['name']}: piso corto ({len(d8[spec['name']])} de {len(floor)})")
        if dn8[spec["name"]] not in d8[spec["name"]]:
            errors.append(f"{spec['name']}: la bajada {dn8[spec['name']]} no se alcanza")
    d9 = {}
    for spec in DEEP_CAVES:
        floor = caves["floors9"][spec["name"]]
        walk = cave_walk(caves["t9"], floor)
        start_pos = (spec["mouth"][0], spec["mouth"][1] + 1)
        d9[spec["name"]] = reach(walk, start_pos, CARD)
        if len(d9[spec["name"]]) < spec["min"] * 0.75:
            errors.append(f"{spec['name']} fondo: piso corto ({len(d9[spec['name']])} de {len(floor)})")
    if dn9 not in d9["dragon"]:
        errors.append(f"dragón fondo: la bajada {dn9} no se alcanza")
    walk10 = cave_walk(caves["t10"], caves["floor10"])
    d10 = reach(walk10, (ABYSS["mouth"][0], ABYSS["mouth"][1] + 1), CARD)
    if not any((portal[0] + dx, portal[1] + dy) in d10 for dx, dy in CARD):
        errors.append(f"z10: el portal final {portal} sin acceso")

    # escaleras: bajada (432) en z con escalera de mano (1385) justo debajo, que sube hacia el norte; se
    # llega caminando a la casilla de abajo (sur) y la de arriba al norte se puede pisar
    layers = {Z7: surf, Z8: caves["t8"], Z9: caves["t9"], Z10: caves["t10"]}
    for z, t in layers.items():
        for (x, y), it in t.items():
            if STAIR_DOWN in it:
                below = layers.get(z + 1, {}).get((x, y))
                if not below or STAIRS_UP not in below or below[0] not in CAVE_FLOORS:
                    errors.append(f"escalera z{z} {(X0 + x, Y0 + y)}: abajo no hay escalera de mano ({below})")
                elif not bl.walkable(layers[z + 1].get((x, y + 1), [ROCK])):
                    errors.append(f"escalera z{z} {(X0 + x, Y0 + y)}: no se puede salir hacia el sur abajo")
            if STAIRS_UP in it:
                above = layers.get(z - 1, {}).get((x, y))
                north = layers.get(z - 1, {}).get((x, y - 1))
                if not above or STAIR_DOWN not in above:
                    errors.append(f"escalera de mano z{z} {(X0 + x, Y0 + y)}: arriba no hay bajada ({above})")
                elif not north or not bl.walkable(north):
                    errors.append(f"escalera de mano z{z} {(X0 + x, Y0 + y)}: al subir se cae en {north}")

    walk8 = {c for c, it in caves["t8"].items() if bl.walkable(it) and it[0] in CAVE_FLOORS}
    walk9 = {c for c, it in caves["t9"].items() if bl.walkable(it) and it[0] in CAVE_FLOORS}
    for t, label in ((caves["t8"], "z8"), (caves["t9"], "z9"), (caves["t10"], "z10")):
        fl = {c for c, it in t.items() if it[0] in CAVE_FLOORS}
        for c, it in t.items():
            if c in fl:
                continue
            want = pieces_for(neighbors_in(fl, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
            if want is None or len(want) > 1 or (want and it[0] != want[0]) or (not want and it[0] != ROCK):
                errors.append(f"pared {label} {c}: quiere {want} tiene {it[0]}")
    for label, wk in (("z7", walk7), ("z8", walk8), ("z9", walk9), ("z10", walk10)):
        for (x, y) in wk:
            if x < VIEW[0] or x > W - VIEW[0] - 1 or y < VIEW[1] or y > H - VIEW[1] - 1:
                errors.append(f"{label} {(x, y)}: se ve el borde de la caja")
                break

    # spawns: una familia por zona; cuevas de un solo tipo con gradiente y fondo más duro
    rng = random.Random(a.seed + 99)
    spawns7 = []
    for name, zone in info["zones"].items():
        if name not in SURFACE_HUNTS:
            continue
        walk = (zone & walk7) - grow(info["camps"], 1) if name == "camp" else zone & walk7
        pool = walk - grow({ARRIVAL} | set(PORTALS_BACK), 6)
        placed = place_stages([SURFACE_HUNTS[name]], [pool], pool, set(), Z7, rng, GAP)
        spawns7.extend(placed[:SURFACE_HUNTS_N[name]])

    spawns8 = []
    for spec in CAVES:
        name = spec["name"]
        avoid8 = grow({spec["mouth"], dn8[name]}, STAIR_CLEAR.get(name, 3))
        walk = cave_walk(caves["t8"], caves["floors8"][name])
        stages = CAVE_STAGES[name]
        spawns8.extend(place_stages(stages, slices_by(walk - avoid8, lambda c: d8[name][c], len(stages)),
                                    walk, avoid8, Z8, rng, CAVE_GAP.get((name, Z8), GAP)))

    spawns9 = []
    for spec in DEEP_CAVES:
        name = spec["name"]
        avoid9 = grow({spec["mouth"]} | ({dn9} if name == "dragon" else set()), STAIR_CLEAR.get(name, 3))
        walk = cave_walk(caves["t9"], caves["floors9"][name])
        stages = DEEP_STAGES[name]
        spawns9.extend(place_stages(stages, slices_by(walk - avoid9, lambda c: d9[name][c], len(stages)),
                                    walk, avoid9, Z9, rng, CAVE_GAP.get((name, Z9), GAP)))

    try:
        root_spawn = root_colossus_spawn(walk10, d10, grow({portal}, 3), Z10)
        root_pos = root_spawn[0]
    except ValueError as error:
        errors.append(str(error))
        root_spawn, root_pos = None, None
    avoid10 = grow({ABYSS["mouth"], portal}, 3) | (grow({root_pos}, 3) if root_pos else set())
    spawns10 = place_stages(ABYSS_STAGES, slices_by(walk10 - avoid10, lambda c: d10[c], len(ABYSS_STAGES)),
                            walk10, avoid10, Z10, rng, GAP)
    if root_spawn:
        spawns10.append(root_spawn)
    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        if a.preview:
            write_preview(a.preview, [surf, caves["t8"], caves["t9"], caves["t10"]], bl.otb, bl)
        return 1

    counts: dict = {}
    for s in (spawns7, spawns8, spawns9, spawns10):
        for _c, _z, mons in s:
            for name, _p, _t in mons:
                counts[name] = counts.get(name, 0) + 1
    n_mon = sum(counts.values())
    print(f"valle x{X0}-{X0 + W - 1} y{Y0}-{Y0 + H - 1}: z7 {len(walk7)} casillas, z8 {len(walk8)}, "
          f"z9 {len(walk9)}, z10 {len(walk10)}; spawns {len(spawns7)}+{len(spawns8)}+{len(spawns9)}+{len(spawns10)} "
          f"({n_mon} monstruos); llegada {X0 + ARRIVAL[0]},{Y0 + ARRIVAL[1]},7; "
          f"bocas {X0 + STAIRS_CAT[0]},{Y0 + STAIRS_CAT[1]},7 / {X0 + MOUTH_QUARA[0]},{Y0 + MOUTH_QUARA[1]},7 / "
          f"{X0 + MOUTH_DRAGON[0]},{Y0 + MOUTH_DRAGON[1]},7; fondos {X0 + DEEP_CAVES[0]['mouth'][0]},{Y0 + DEEP_CAVES[0]['mouth'][1]},9 / "
          f"{X0 + DEEP_CAVES[1]['mouth'][0]},{Y0 + DEEP_CAVES[1]['mouth'][1]},9 / {X0 + DEEP_CAVES[2]['mouth'][0]},{Y0 + DEEP_CAVES[2]['mouth'][1]},9; "
          f"abismo {X0 + ABYSS['mouth'][0]},{Y0 + ABYSS['mouth'][1]},10; portal {X0 + portal[0]},{Y0 + portal[1]},10")
    print("monstruos: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    if a.preview:
        write_preview(a.preview, [surf, caves["t8"], caves["t9"], caves["t10"]], bl.otb, bl)
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
        in_box = X0 <= gx < X0 + W and Y0 <= gy < Y0 + H and z in (Z7, Z8, Z9, Z10)
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
    for zz, t in ((Z7, surf), (Z8, caves["t8"]), (Z9, caves["t9"]), (Z10, caves["t10"])):
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
    block = "\t<!-- BEGIN BEAST_VALLEY_SPAWNS (scripts/map/generate-beast-valley.py) -->\n" + \
        spawn_xml(spawns7 + spawns8 + spawns9 + spawns10) + "\n\t<!-- END BEAST_VALLEY_SPAWNS -->\n"
    old = re.search(r"[ \t]*<!-- BEGIN BEAST_VALLEY_SPAWNS.*?<!-- END BEAST_VALLEY_SPAWNS -->\n?", sp, flags=re.S)
    if old:   # en su lugar: el diff queda chico
        sp = sp[:old.start()] + "\x00BLOCK\x00" + sp[old.end():]
    sp = re.sub(r'[ \t]*<spawn centerx="(\d+)" centery="(\d+)" centerz="(\d+)"[^>]*>.*?</spawn>\n?',
                lambda m: "" if gone(int(m.group(1)), int(m.group(2)), int(m.group(3))) else m.group(0), sp, flags=re.S)
    sp = sp.replace("\x00BLOCK\x00", block) if old else sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")

    # --- carteles ---
    rd = READABLES.read_text(encoding="latin-1")
    lines = ["\t<!-- BEGIN BEAST_VALLEY_SIGNS -->"]
    for (x, y), t in sorted(info["signs"].items()):
        lines.append(f'\t<readable x="{X0 + x}" y="{Y0 + y}" z="7" text="{t.replace(chr(10), chr(92) + "n")}"/>')
    lines.append("\t<!-- END BEAST_VALLEY_SIGNS -->\n")
    old = re.search(r"\t?<!-- BEGIN BEAST_VALLEY_SIGNS -->.*?<!-- END BEAST_VALLEY_SIGNS -->\n?", rd, flags=re.S)
    if old:
        rd = rd[:old.start()] + "\n".join(lines) + rd[old.end():]
    else:
        rd = rd.replace("</readables>", "\n".join(lines) + "</readables>")
    READABLES.write_text(rd, encoding="latin-1")

    if OLD_MANIFEST.exists():
        OLD_MANIFEST.unlink()
    MANIFEST.write_text(json.dumps({
        "name": "generated-beast-valley", "seed": a.seed, "replaces": "hunt-maze", "version": 3,
        "box": {"x1": X0, "y1": Y0, "x2": X0 + W - 1, "y2": Y0 + H - 1, "z": [Z7, Z8, Z9, Z10]},
        "oldMazeCleared": {"x1": OLD_MAZE[0], "y1": OLD_MAZE[1], "x2": OLD_MAZE[2], "y2": OLD_MAZE[3], "z": Z7},
        "landing": {"x": X0 + ARRIVAL[0], "y": Y0 + ARRIVAL[1], "z": 7},
        "portalsBack": [{"x": X0 + x, "y": Y0 + y, "z": 7, "to": list(TEMPLE_BACK)} for x, y in PORTALS_BACK]
        + [{"x": X0 + portal[0], "y": Y0 + portal[1], "z": 10, "to": list(TEMPLE_BACK)}],
        "mouths": [
            {"name": "Catacumbas", "x": X0 + STAIRS_CAT[0], "y": Y0 + STAIRS_CAT[1], "z": 7},
            {"name": "Cueva de las Quaras", "x": X0 + MOUTH_QUARA[0], "y": Y0 + MOUTH_QUARA[1], "z": 7},
            {"name": "Guarida del Dragon", "x": X0 + MOUTH_DRAGON[0], "y": Y0 + MOUTH_DRAGON[1], "z": 7},
        ],
        "deepMouths": [
            {"name": name, "x": X0 + specc["mouth"][0], "y": Y0 + specc["mouth"][1], "z": 9}
            for name, specc in ((c["name"], c) for c in DEEP_CAVES)
        ],
        "downs": [{"name": name, "x": X0 + pos[0], "y": Y0 + pos[1], "z": 8} for name, pos in dn8.items()]
        + [{"name": "dragonDeep", "x": X0 + dn9[0], "y": Y0 + dn9[1], "z": 9}],
        "abyss": {"x": X0 + ABYSS["mouth"][0], "y": Y0 + ABYSS["mouth"][1], "z": 10},
        "rootColossus": ({"x": X0 + root_pos[0], "y": Y0 + root_pos[1], "z": 10} if root_pos else None),
        "zones": {name: {"x": X0 + int(z[0]), "y": Y0 + int(z[1]), "rx": z[2], "ry": z[3]} for name, z in ZONES.items()},
        "spawns": {"z7": len(spawns7), "z8": len(spawns8), "z9": len(spawns9), "z10": len(spawns10),
                   "monsters": n_mon},
        "monsters": dict(sorted(counts.items())),
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK carteles {READABLES}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
