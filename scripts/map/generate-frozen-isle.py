#!/usr/bin/env python3
"""Isla del Hielo Eterno: destino de barco que reemplaza al Alice Maze (nov 2026).

Un sendero angosto (2 casillas caminables) que sube de sur a norte por etapas, cada una más difícil,
con desvíos escondidos que premian explorar:

  z7  Puerto (Nimral) -> Bosque Nevado (zigzag entre pinos; desvío al cofre del leñador)
      -> Lago Congelado (paso de hielo en zigzag; desvío al islote del Yeti, cofre frozen starlight)
      -> Monasterio de Escarcha (patio de piedra, Ice Monks) -> Paso de montaña -> bajada
  z8  Grutas de Escarcha: túneles de 2 de ancho en serpentina con salas de Ice Spiders
  z9  Guarida del Dragón de Escarcha: sala grande de Frost Dragons y, al fondo, la cámara con los
      cofres de quest del crimson wand (20123) y el crimson helmet (20113), los mismos que tenía el
      final del Alice Maze, y el portal al templo.

Caja: x 356-433, y 2-117, z7-z9 (el Alice Maze ocupaba x 380-433, y 16-103, z7). La plataforma
del Gauntlet en x 434-437 queda afuera y no se toca.

Reglas que valida antes de escribir (si algo falla no escribe nada):
  - costa: la orilla lleva pieza de borde (y es intransitable: el agua llega hasta ahí);
  - nieve sobre el patio de piedra: pieza de borde exacta; paredes de las cuevas: pieza única;
  - el sendero llega desde el puerto a la bajada, de z8 a z9 y hasta los cofres y el portal;
  - desde cualquier casilla caminable la pantalla entera tiene casillas (sin negro).

Uso (desde la raíz del repo; Pillow no hace falta):
  python3 scripts/map/generate-frozen-isle.py --dry-run --preview /tmp/isla.png
  python3 scripts/map/generate-frozen-isle.py              # escribe mapa, spawns, carteles, NPC y barco
Re-ejecutable: borra la caja z7-z9 y reemplaza los bloques FROZEN_ISLE de spawns y carteles.
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
from mapdata import (DIRS, MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, Renderer,  # noqa: E402
                     parse_tree, png_bytes, serialize_tree)

_spec = importlib.util.spec_from_file_location("north_pass", HERE / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)
Noise, neighbors_in, pieces_for, fix_until_valid, reach, Blocking = (
    NP.Noise, NP.neighbors_in, NP.pieces_for, NP.fix_until_valid, NP.reach, NP.Blocking)
SNOW_SIDE, SNOW_CORNER, SNOW_INNER = NP.SNOW_SIDE, NP.SNOW_CORNER, NP.SNOW_INNER
WALL_SIDE, WALL_CORNER, WALL_INNER, ROCK = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER, NP.ROCK
CARD = NP.CARD
ALL8 = list(DIRS.values())

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
NPCS = WORLD / "npc.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
BOAT = REPO / "server/YurOTS/ots/data/npc/scripts/boat.lua"
MANIFEST = WORLD / "generated-frozen-isle.json"

X0, Y0, W, H = 356, 2, 78, 116             # x 356-433, y 2-117
OLD_MAZE = (380, 16, 433, 103)             # lo que había antes (z7), para limpiar spawns
Z7, Z8, Z9 = 7, 8, 9
SEA = 9                                     # agua alrededor: la pantalla (15x11) nunca ve el borde

# --- piezas -------------------------------------------------------------------------------------
WATER, SNOW, ICE, STONE_FLOOR = 4608, 670, 671, 431
COAST_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
COAST_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
COAST_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}
# hielo con borde de nieve (suelo): lado(s) donde está la nieve
ICE_SIDE = {"n": 684, "s": 685, "w": 686, "e": 687}
ICE_CORNER = {("n", "w"): 688, ("n", "e"): 689, ("s", "w"): 690, ("s", "e"): 691}
ICE_INNER = {"se": 692, "sw": 693, "ne": 694, "nw": 695}

PINE, DEAD_TREES = 2698, (2697, 2709, 2717, 2720)
STALAGMITE, STONE, RUBBLE, PEBBLES = 4995, 1285, 1309, 1336
PILLAR, BROKEN_PILLAR, STATUE, ALTAR = 1515, 3767, 1442, 1642
COAL_BASIN, BARREL, CRATE, BOAT_ITEM = 2602, 1770, 1739, 3591
CAMPFIRE, LANTERN, SIGN, CHEST = 1423, 3744, 1429, 1740
BONES, DRAGON_SKULL, DRAGON_BONES, HUMAN_SKELETON = (3125, 2248, 2320, 3121), 2247, 3122, 3133
STAIR_DOWN, STAIRS_UP, TELEPORT = 432, 1385, 1387
ATTR_UNIQUE_ID, ATTR_TELE_DEST = 5, 8

TEMPLE = (130, 53, 6)                       # adonde llevaba la salida del Alice Maze
PRIZES = {"woodcutter": 2160, "islet": 2361, "wand": 20123, "helmet": 20113}

# --- recorrido de la superficie (coordenadas locales, x 0-77, y 0-115) ---------------------------
HARBOR = (40, 102)                          # centro del claro del puerto
LANDING = (39, 102)                         # destino del barco
NIMRAL = (41, 101)
# Compactado (nov 2026): los zigzags cruzaban la isla entera (291 pasos en z7, 461 en las grutas).
# Ahora son más cortos y hay menos bandas en z8; ver docs/items-and-map/MAPEAR_ISLA_HELADA.md.
FOREST_PATH = [(40, 99), (40, 94), (30, 94), (30, 86), (50, 86), (50, 78), (46, 78), (46, 74)]
WOODCUTTER_SPUR = [(30, 94), (21, 94)]      # sigue de largo en la primera curva
WOODCUTTER = (19, 94)                       # claro del leñador (cofre al oeste)
CHECK_LAKE = (46, 72)                       # claro antes del lago
CAUSEWAY = [(46, 71), (46, 66), (34, 66), (34, 59), (46, 59), (46, 52), (39, 52), (39, 46), (39, 40)]
ISLET_SPUR = [(34, 62), (19, 62)]
ISLET = (15, 61)
LAKE = (39, 59, 30, 10.5)                   # centro x, y y radios del lago
COURTYARD = (32, 30, 46, 41)                # patio del monasterio (x0, y0, x1, y1)
MOUNTAIN_PATH = [(39, 30), (39, 26), (30, 26), (30, 19), (46, 19), (46, 14), (37, 14)]
CAVE_BANDS = 5                              # bandas de la serpentina de z8 (antes 9)
CAVE_BX = (9, 29)                           # bloques 2x2 en x de las grutas (antes 5-33)
STAIRS = (36, 13)
ROCKY_Y = 28                                # al norte de esta línea el relleno es roca, no bosque


def brush(points, width=2) -> set:
    """Camino de `width` de ancho siguiendo tramos horizontales y verticales entre puntos."""
    out = set()
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 != x1 and y0 != y1:
            raise ValueError(f"tramo diagonal {points}")
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for dx in range(width):
                    for dy in range(width):
                        out.add((x + dx, y + dy))
    return out


def ellipse(cx, cy, rx, ry) -> set:
    return {(x, y) for x in range(int(cx - rx) - 1, int(cx + rx) + 2) for y in range(int(cy - ry) - 1, int(cy + ry) + 2)
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1}


def grow(cells: set, r: int) -> set:
    return {(x + dx, y + dy) for (x, y) in cells for dx in range(-r, r + 1) for dy in range(-r, r + 1)}


# --- superficie ---------------------------------------------------------------------------------

def build_surface(seed: int, bl):
    rng = random.Random(seed)
    nz = Noise(seed)
    cells = {(x, y) for y in range(H) for x in range(W)}

    walk_main = brush(FOREST_PATH) | brush(MOUNTAIN_PATH)
    walk_main |= ellipse(HARBOR[0] + 0.5, HARBOR[1] + 0.5, 6.5, 3.2) | ellipse(CHECK_LAKE[0] + 1, CHECK_LAKE[1] + 1, 4.2, 2.6)
    walk_main |= ellipse(STAIRS[0] + 0.5, STAIRS[1] - 0.5, 2.6, 2.2)
    causeway = brush(CAUSEWAY) | brush(ISLET_SPUR)
    spurs = brush(WOODCUTTER_SPUR) | ellipse(WOODCUTTER[0] + 0.5, WOODCUTTER[1] + 0.5, 2.2, 2.2)
    islet_walk = ellipse(ISLET[0] + 0.5, ISLET[1] + 0.5, 3.4, 3.0)
    court = {(x, y) for x in range(COURTYARD[0], COURTYARD[2] + 1) for y in range(COURTYARD[1], COURTYARD[3] + 1)}

    # tierra: un bloque con costa irregular; el lago es agua adentro; el paso de hielo y el islote,
    # tierra con un margen de 1 (la orilla es intransitable)
    land = set()
    for (x, y) in cells:
        edge = min(x - SEA, W - SEA - 1 - x, y - SEA + 2, H - SEA - 1 - y)
        if edge >= 0 and (edge > 3 or nz.fbm(x / 5, y / 5, 3, 3) > 0.38 + 0.1 * (3 - edge)):
            land.add((x, y))
    lake = {(x, y) for (x, y) in cells
            if ((x + 0.5 - LAKE[0]) / LAKE[2]) ** 2 + ((y + 0.5 - LAKE[1]) / LAKE[3]) ** 2
            + 0.45 * (nz.fbm(x / 4, y / 4, 2, 41) - 0.5) < 1}
    keep_land = grow(walk_main | causeway | spurs | islet_walk | court, 1)
    land = (land - lake) | keep_land
    # bahía del puerto: el agua llega a 2 casillas del muelle
    for x in range(HARBOR[0] - 4, HARBOR[0] + 6):
        for y in range(HARBOR[1] + 4, H):
            land.discard((x, y))
    water = cells - land
    water = fix_until_valid(water, cells - keep_land, COAST_SIDE, COAST_CORNER, COAST_INNER)
    land = cells - water

    walk = walk_main | causeway | spurs | islet_walk | court
    # nieve sobre el patio: borde de nieve en las casillas de piedra que tocan nieve
    snow_mask = land - court
    snow_mask = fix_until_valid(snow_mask, court, SNOW_SIDE, SNOW_CORNER, SNOW_INNER)
    court = land - snow_mask
    # charcos de hielo en los claros (con borde de nieve, una pieza por casilla)
    ice = set()
    for c in ellipse(CHECK_LAKE[0] + 3.5, CHECK_LAKE[1] + 0.5, 2.0, 1.4) | ellipse(HARBOR[0] - 3.5, HARBOR[1] - 0.5, 1.8, 1.2):
        if c in walk:
            ice.add(c)
    snow_for_ice = fix_until_valid(land - ice, ice, ICE_SIDE, ICE_CORNER, ICE_INNER, single=True)
    ice = land - snow_for_ice

    tiles: dict = {}
    for c in cells:
        x, y = c
        if c in water:
            tiles[c] = [WATER]
            continue
        if c in court:
            tiles[c] = [STONE_FLOOR] + (pieces_for(neighbors_in(snow_mask, x, y), SNOW_SIDE, SNOW_CORNER, SNOW_INNER) or [])
        elif c in ice:
            p = pieces_for(neighbors_in(snow_for_ice, x, y), ICE_SIDE, ICE_CORNER, ICE_INNER)
            tiles[c] = [p[0] if p else ICE]
        else:
            tiles[c] = [SNOW]
        coast = pieces_for(neighbors_in(water, x, y), COAST_SIDE, COAST_CORNER, COAST_INNER)
        if coast:
            tiles[c] += coast

    coastal = {c for c in land if neighbors_in(water, *c)}
    walk = {c for c in walk if c in land and c not in coastal}

    occupied = set(walk)

    def put(c, item):
        tiles[c].append(item)
        occupied.add(c)

    # relleno: todo lo que no es sendero es bosque cerrado (sur) o roca (norte); siempre bloquea.
    # Los árboles y rocas grandes se dibujan 1 casilla hacia arriba-izquierda: no se ponen donde
    # taparían el sendero, así el camino de 2 se lee entero. Los pinos van con separación irregular
    # (no en grilla) y el suelo entre ellos lleva un bloqueo chico variado.
    filler = sorted(land - walk - coastal, key=lambda c: (c[1], c[0]))
    big = set()

    def covers_path(c):
        x, y = c
        return any(q in walk for q in ((x - 1, y), (x, y - 1), (x - 1, y - 1)))

    for c in filler:
        x, y = c
        rocky = y < ROCKY_Y
        r = rng.random()
        if rocky:
            put(c, STONE if r < 0.55 else STALAGMITE if r < 0.8 else PEBBLES)
            if bl.walkable(tiles[c]):          # las piedritas no bloquean: debajo va una piedra
                tiles[c].append(STONE)
        else:
            put(c, STONE if r < 0.45 else STALAGMITE if r < 0.9 else rng.choice(DEAD_TREES))
        near_big = any((x + dx, y + dy) in big for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        if covers_path(c) or near_big:
            continue
        if rng.random() < (0.55 if rocky else 0.8):
            tiles[c].append(RUBBLE if rocky else (PINE if rng.random() < 0.88 else rng.choice(DEAD_TREES)))
            big.add(c)
    # costa sin sendero: alguna estalagmita en la orilla (ya es intransitable)
    for c in sorted(coastal):
        if rng.random() < 0.06 and len(tiles[c]) <= 2:
            tiles[c].append(STALAGMITE)

    # --- puerto ---
    hx, hy = HARBOR
    deco = {(hx - 5, hy): BARREL, (hx - 5, hy + 1): BARREL, (hx - 4, hy + 1): CRATE, (hx + 4, hy - 1): CAMPFIRE,
            (hx + 5, hy + 1): BARREL}
    for c, it in deco.items():
        if c in walk:
            put(c, it)
    boat_c = (hx + 1, hy + 4)
    if boat_c in water:
        tiles[boat_c].append(BOAT_ITEM)
    # --- monasterio ---
    x0, y0, x1, y1 = COURTYARD
    for x in range(x0 + 1, x1, 3):
        for y in (y0 + 1, y1 - 1):
            c = (x, y)
            if c in court and abs(x - 39) > 2:
                put(c, BROKEN_PILLAR if rng.random() < 0.3 else PILLAR)
    altar = (39, y0 + 2)
    put(altar, ALTAR)
    put((36, y0 + 3), STATUE)
    put((42, y0 + 3), STATUE)
    for c in ((x0 + 2, y0 + 5), (x1 - 2, y0 + 5), (x0 + 2, y1 - 3), (x1 - 2, y1 - 3)):
        if c in court:
            put(c, COAL_BASIN)
    # --- bajada: marco de piedras (abierta al norte y al sur) ---
    sx, sy = STAIRS
    tiles[STAIRS] = [STAIR_DOWN]
    for dx, dy in ((-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)):
        c = (sx + dx, sy + dy)
        if c in walk and c not in brush(MOUNTAIN_PATH[-2:]):
            put(c, STONE)
    # --- cofres de los desvíos ---
    chests = {(WOODCUTTER[0] - 2, WOODCUTTER[1] - 1): PRIZES["woodcutter"], (ISLET[0] - 2, ISLET[1]): PRIZES["islet"]}
    for c in chests:
        put(c, CHEST)
    # faroles en el bosque y en el paso de hielo (guían)
    for c in ((32, 92), (52, 84), (44, 80), (48, 64), (36, 57), (44, 50)):
        if c in land and c not in walk and len(tiles[c]) <= 2:
            tiles[c] = [tiles[c][0], LANTERN]
    # huesos y piedritas sueltos en el sendero (no bloquean)
    for c in sorted(walk):
        if c not in occupied:
            continue
    for c in sorted(walk - set(chests) - {LANDING, NIMRAL}):
        if len(tiles[c]) == 1 and rng.random() < 0.025:
            tiles[c].append(rng.choice((PEBBLES,) + BONES[:2]))

    signs = {
        (hx + 2, hy - 2): "ISLA DEL HIELO ETERNO\nEl sendero sube al norte: Bosque Nevado, Lago Congelado,\n"
                          "Monasterio de Escarcha y las Grutas.",
        (CHECK_LAKE[0] - 3, CHECK_LAKE[1] - 1): "LAGO CONGELADO\nCruza por el paso de hielo. Al oeste, un islote:\ndicen que ahi vive un yeti.",
        (x1 + 1, y1 - 1): "MONASTERIO DE ESCARCHA\nLos monjes de hielo no perdonan a los intrusos.",
        (sx + 3, sy + 1): "GRUTAS DE ESCARCHA\nAranas de hielo y, en lo mas hondo, el dragon.\nNivel 80+.",
        (WOODCUTTER[0] + 2, WOODCUTTER[1] - 2): "Aqui vivia un lenador.\nDejo algo para quien encontrara su escondite.",
    }
    placed_signs = {}
    for anchor, text in signs.items():
        # la casilla de relleno más cercana al ancla que toque el sendero (se lee desde el camino)
        cands = [c for c in land - walk - coastal - set(chests)
                 if any((c[0] + dx, c[1] + dy) in walk for dx, dy in CARD) and c not in placed_signs]
        c = min(cands, key=lambda c: (abs(c[0] - anchor[0]) + abs(c[1] - anchor[1]), c))
        tiles[c] = [tiles[c][0], SIGN]
        placed_signs[c] = text
    signs = placed_signs

    return tiles, {"walk": walk, "water": water, "court": court, "chests": chests, "signs": signs,
                   "zones": {"forest": brush(FOREST_PATH) | spurs, "lake": causeway, "islet": islet_walk,
                             "court": court, "mountain": brush(MOUNTAIN_PATH)}}


# --- cuevas: túneles de bloques 2x2 ---------------------------------------------------------------

def blocks_to_tiles(floor_b: set) -> set:
    return {(2 * bx + i, 2 * by + j) for (bx, by) in floor_b for i in (0, 1) for j in (0, 1)}


def fix_diagonals(floor_b: set, allowed_b: set) -> set:
    floor_b = set(floor_b)
    changed = True
    while changed:
        changed = False
        for (x, y) in sorted(floor_b):
            for dx, dy in ((1, 1), (1, -1)):
                d = (x + dx, y + dy)
                a, b = (x + dx, y), (x, y + dy)
                if d in floor_b and a not in floor_b and b not in floor_b:
                    floor_b.add(a if a in allowed_b else b)
                    changed = True
    return floor_b


def b_line(a, b) -> set:
    """Tramo en L entre dos bloques (primero en x, después en y)."""
    (x0, y0), (x1, y1) = a, b
    out = {(x, y0) for x in range(min(x0, x1), max(x0, x1) + 1)}
    out |= {(x1, y) for y in range(min(y0, y1), max(y0, y1) + 1)}
    return out


def b_rect(x0, y0, x1, y1) -> set:
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def cave_floor_tiles(floor: set, box: set, seed: int, patches=0.0) -> dict:
    nz = Noise(seed + 77)
    tiles = {}
    for c in box:
        x, y = c
        if c in floor:
            tiles[c] = [SNOW if nz.fbm(x / 5, y / 5, 3, 12) < patches else ICE]
            continue
        wall = pieces_for(neighbors_in(floor, x, y), WALL_SIDE, WALL_CORNER, WALL_INNER)
        tiles[c] = [wall[0]] if wall else [ROCK]
    return tiles


def build_caves(seed: int):
    rng = random.Random(seed + 5)
    bx_min, bx_max = CAVE_BX                  # bloques: x 18-59 en casillas (antes 10-65)
    sb = (STAIRS[0] // 2, STAIRS[1] // 2)
    allowed = b_rect(bx_min, 4, bx_max, H // 2 - 5)

    # z8: serpentina de bandas de 4 bloques (pasillo + salas, 1 bloque de pared entre bandas)
    f8 = {sb, (sb[0], sb[1] + 1)}
    rooms8 = []
    band_y = sb[1] + 2
    x = sb[0]
    going_east = True
    prev_row = sb[1] + 1
    for band in range(CAVE_BANDS):
        row = band_y + 1
        f8 |= b_line((x, prev_row), (x, row))
        end = bx_max - rng.randint(0, 3) if going_east else bx_min + rng.randint(0, 3)
        step = 1 if going_east else -1
        cx = x
        lane = row                      # el pasillo serpentea entre las filas band_y y band_y + 2
        while cx != end:
            f8.add((cx, lane))
            if rng.random() < 0.18:
                new_lane = min(band_y + 2, max(band_y, lane + rng.choice((-1, 1))))
                f8 |= b_line((cx, lane), (cx, new_lane))
                lane = new_lane
            cx += step
        f8 |= b_line((end, lane), (end, row))
        prev_row = row
        f8.add((end, row))
        # una sala por banda, en un lugar al azar del pasillo
        rx = rng.randint(min(x, end) + 2, max(x, end) - 4) if abs(end - x) > 7 else None
        if rx is not None:
            room = b_rect(rx, band_y, rx + 2, band_y + 2)
            f8 |= room
            rooms8.append(room)
        x = end
        band_y += 4
        going_east = not going_east
        if band_y + 3 > H // 2 - 5:
            break
    # el final de la última banda baja a z9
    down_b = (x, band_y - 4 + 1)
    f8 |= {(down_b[0], down_b[1] + 1), (down_b[0], down_b[1] - 1)}   # piso al norte y al sur de la bajada
    f8 = fix_diagonals(f8, allowed) & allowed
    floor8 = blocks_to_tiles(f8)
    down = (2 * down_b[0], 2 * down_b[1] + 1)

    # z9: pasillo desde la bajada -> sala grande del dragón -> pasillo -> cámara del tesoro
    db = (down[0] // 2, down[1] // 2)
    hall_x0 = max(bx_min, min(db[0] - 6, bx_max - 12))
    hall_y1 = db[1] - 3
    hall = b_rect(hall_x0, hall_y1 - 7, hall_x0 + 11, hall_y1)
    f9 = {db, (db[0], db[1] - 1)} | b_line((db[0], db[1] - 1), (db[0], hall_y1)) | hall
    # recortes en la sala para que no sea un rectángulo
    for c in list(hall):
        if (c[0] in (hall_x0, hall_x0 + 11) and c[1] in (hall_y1 - 7, hall_y1)) or rng.random() < 0.05:
            if c not in b_line((db[0], db[1] - 1), (db[0], hall_y1)):
                f9.discard(c)
    tx = hall_x0 + 2 if db[0] > hall_x0 + 6 else hall_x0 + 9
    treasure = b_rect(tx - 1, hall_y1 - 15, tx + 1, hall_y1 - 13)
    f9 |= b_line((tx, hall_y1 - 7), (tx, hall_y1 - 12)) | treasure
    allowed9 = b_rect(bx_min, 3, bx_max, H // 2 - 4)
    f9 = fix_diagonals(f9, allowed9) & allowed9
    floor9 = blocks_to_tiles(f9)

    box = {(x, y) for x in range(W) for y in range(H)}
    t8 = cave_floor_tiles(floor8, box, seed + 1, patches=0.3)
    t9 = cave_floor_tiles(floor9, box, seed + 2, patches=0.18)
    t8[STAIRS] = [ICE, STAIRS_UP]
    t8[down] = [STAIR_DOWN]
    t9[down] = [t9[down][0], STAIRS_UP]
    trez = blocks_to_tiles(treasure)
    tcx = 2 * tx + 1
    tcy = 2 * (hall_y1 - 15)
    chest_wand, chest_helm = (tcx - 2, tcy + 1), (tcx + 2, tcy + 1)
    portal = (tcx, tcy)
    for c in (chest_wand, chest_helm):
        t9[c] = [t9[c][0], CHEST]
    t9[portal] = [t9[portal][0], TELEPORT]
    for c in ((tcx - 2, tcy + 4), (tcx + 2, tcy + 4)):
        if c in floor9:
            t9[c] = [t9[c][0], COAL_BASIN]
    return {"t8": t8, "floor8": floor8, "rooms8": [blocks_to_tiles(r) for r in rooms8], "down": down,
            "t9": t9, "floor9": floor9, "hall": blocks_to_tiles(hall) & floor9, "treasure": trez & floor9,
            "chests9": {chest_wand: PRIZES["wand"], chest_helm: PRIZES["helmet"]}, "portal": portal}


def decorate_cave(tiles, floor, start, keep, seed, rate, bl):
    rng = random.Random(seed + 4242)
    walk = set(floor)
    base = len(reach(walk, start, CARD))
    for c in sorted(floor, key=lambda c: (c[1], c[0])):
        if c in keep or len(tiles[c]) > 1 or tiles[c][0] == STAIR_DOWN:
            continue
        rock_n = 8 - len(neighbors_in(floor, *c))
        r = rng.random()
        if rock_n >= 3 and r < 0.12:
            if len(reach(walk - {c}, start, CARD)) == base - 1:
                tiles[c].append(rng.choice((STALAGMITE, STALAGMITE, STONE)))
                walk.discard(c)
                base -= 1
        elif r < 0.02:
            tiles[c].append(PEBBLES)
        elif r < 0.02 + rate:
            tiles[c].append(rng.choice(BONES + (DRAGON_SKULL,)))


# --- spawns -------------------------------------------------------------------------------------

def place(groups, walk, avoid, z, rng, min_gap=7):
    out, centers = [], []
    for name, count, per, spawntime, pool in groups:
        cands = sorted((pool & walk) - avoid)
        rng.shuffle(cands)
        placed = 0
        for c in cands:
            if placed >= count:
                break
            if any(abs(c[0] - o[0]) + abs(c[1] - o[1]) < min_gap for o in centers):
                continue
            spots = [(c[0] + dx, c[1] + dy) for dx in range(-2, 3) for dy in range(-2, 3)
                     if (c[0] + dx, c[1] + dy) in walk and (c[0] + dx, c[1] + dy) not in avoid]
            if len(spots) < per + 2:
                continue
            rng.shuffle(spots)
            centers.append(c)
            out.append((c, z, [(name, s, spawntime) for s in spots[:per]]))
            placed += 1
        if placed < count:
            print(f"aviso: {name} z{z}: {placed}/{count} spawns", file=sys.stderr)
    return out


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{X0 + cx}" centery="{Y0 + cy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


# --- OTBM ---------------------------------------------------------------------------------------

# Items apilables según items-zagan-test.otb: el server exige su byte de cantidad o no carga el mapa
# (ver scripts/map/check-map-load.py). 2320 = calavera.
NEEDS_COUNT = {2320}


def item_node(iid: int, uid=None, tele=None):
    props = bytearray(struct.pack("<H", iid))
    if iid in NEEDS_COUNT:
        props.append(1)
    if uid is not None:
        props += bytes([ATTR_UNIQUE_ID]) + struct.pack("<H", uid)
    if tele is not None:
        props += bytes([ATTR_TELE_DEST]) + struct.pack("<HHB", *tele)
    return [T_ITEM, props, []]


def new_tile(x, y, bx, by, items, uids, tele):
    props = bytearray([x - bx, y - by, 9]) + struct.pack("<H", items[0])
    kids = []
    for i in items[1:]:
        kids.append(item_node(i, uids.get(i) if i == CHEST else None, tele if i == TELEPORT else None))
    return [T_TILE, props, kids]


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
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--dump", type=Path, help="JSON con las casillas generadas (para dibujarlas)")
    a = ap.parse_args()

    bl = Blocking()
    otb = bl.otb
    surf, info = build_surface(a.seed, bl)
    caves = build_caves(a.seed)
    sx, sy = STAIRS
    dn = caves["down"]
    decorate_cave(caves["t8"], caves["floor8"], (sx, sy + 1), grow({STAIRS, dn, (sx, sy + 1)}, 2), a.seed + 1, 0.02, bl)
    decorate_cave(caves["t9"], caves["floor9"], (dn[0], dn[1] - 1),
                  grow({dn, caves["portal"]} | set(caves["chests9"]), 2) | caves["treasure"], a.seed + 2, 0.06, bl)

    errors = []

    def check(tiles, mask, side, corner, inner, label, region=None, ground=False):
        allp = set(side.values()) | set(corner.values()) | set(inner.values())
        for c, it in tiles.items():
            if c in mask or (region is not None and c not in region):
                continue
            want = pieces_for(neighbors_in(mask, *c), side, corner, inner)
            have = [i for i in (it[:1] if ground else it) if i in allp]
            if want is None:
                errors.append(f"{label} {c}: combinación sin pieza")
            elif ground:
                if want and (len(want) != 1 or have != want[:1]):
                    errors.append(f"{label} {c}: quiere {want} tiene {it[0]}")
            elif sorted(want) != sorted(have):
                errors.append(f"{label} {c}: quiere {want} tiene {have}")

    check(surf, info["water"], COAST_SIDE, COAST_CORNER, COAST_INNER, "costa")
    land = set(surf) - info["water"]
    check(surf, land - info["court"], SNOW_SIDE, SNOW_CORNER, SNOW_INNER, "nieve/patio", region=info["court"])

    walk7 = {c for c, it in surf.items() if bl.walkable(it)}
    d7 = reach(walk7, LANDING)
    need = {"llegada (NPC al lado)": NIMRAL, "bajada": (sx, sy + 1), "subida (llegada desde z8)": (sx, sy - 1),
            "islote": ISLET, "patio": (39, 36)}
    for label, c in need.items():
        if label.startswith("llegada"):
            continue
        if c not in d7:
            errors.append(f"z7: {label} {c} no se alcanza desde el puerto")
    for c in info["chests"]:
        if not any((c[0] + dx, c[1] + dy) in d7 for dx, dy in CARD):
            errors.append(f"z7: cofre {c} sin acceso")
    if NIMRAL not in walk7 or NIMRAL == LANDING:
        errors.append("z7: el lugar de Nimral no es caminable")
    floor_ok = {ICE, SNOW}
    walk8 = {c for c, it in caves["t8"].items() if bl.walkable(it) and it[0] in floor_ok | {STAIR_DOWN}}
    d8 = reach(walk8, (sx, sy + 1), CARD)
    if (dn[0], dn[1] - 1) not in d8 or (dn[0], dn[1] + 1) not in d8:
        errors.append(f"z8: la bajada a z9 {dn} no se alcanza")
    walk9 = {c for c, it in caves["t9"].items() if bl.walkable(it) and it[0] in floor_ok}
    d9 = reach(walk9, (dn[0], dn[1] - 1), CARD)
    for c in list(caves["chests9"]) + [caves["portal"]]:
        if not any((c[0] + dx, c[1] + dy) in d9 for dx, dy in CARD):
            errors.append(f"z9: {c} sin acceso")
    for t, label in ((caves["t8"], "z8"), (caves["t9"], "z9")):
        fl = {c for c, it in t.items() if it[0] in floor_ok | {STAIR_DOWN}}
        for c, it in t.items():
            if c in fl:
                continue
            want = pieces_for(neighbors_in(fl, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
            if want is None or len(want) > 1 or (want and it[0] != want[0]) or (not want and it[0] != ROCK):
                errors.append(f"pared {label} {c}: quiere {want} tiene {it[0]}")
    # sin negro en pantalla: todo lo caminable a 8 (x) / 6 (y) del borde de la caja
    for label, wk in (("z7", walk7), ("z8", walk8), ("z9", walk9)):
        for (x, y) in wk:
            if x < 8 or x > W - 9 or y < 6 or y > H - 7:
                errors.append(f"{label} {(x, y)}: se ve el borde de la caja")
                break

    # spawns
    rng = random.Random(a.seed + 99)
    z = info["zones"]
    avoid7 = grow({LANDING, NIMRAL, HARBOR}, 7) | grow(set(info["chests"]), 1) | grow({(sx, sy)}, 3)
    spawns7 = place([
        ("Winter Wolf", 4, 2, 120, z["forest"]),
        ("Polar Bear", 2, 1, 150, z["forest"]),
        ("Frost Troll", 4, 2, 150, z["lake"]),
        ("Yeti", 1, 1, 1800, z["islet"]),
        ("Ice Monk", 4, 2, 180, z["court"]),
        ("Ice Monk", 3, 1, 180, z["mountain"]),
    ], walk7, avoid7, 7, rng)
    walk8r = {c for c in walk8 if c in d8}
    avoid8 = grow({STAIRS, dn}, 4)
    rooms = set().union(*caves["rooms8"]) if caves["rooms8"] else set()
    spawns8 = place([
        ("Ice Spider", len(caves["rooms8"]) * 2, 2, 180, rooms),
        ("Ice Spider", 6, 1, 180, walk8r - rooms),
    ], walk8r, avoid8, 8, rng, min_gap=6)
    walk9r = {c for c in walk9 if c in d9}
    avoid9 = grow({dn}, 4) | caves["treasure"]
    spawns9 = place([
        ("Frost Dragon", 5, 1, 300, caves["hall"]),
        ("Ice Spider", 2, 1, 180, walk9r - caves["hall"]),
    ], walk9r, avoid9, 9, rng, min_gap=5)

    # Criaturas traídas del cliente 8.60 (import_client_look.py, nov 2026). Van con un rng aparte y lejos de
    # los spawns de arriba, así los de antes quedan exactamente donde estaban.
    rng860 = random.Random(a.seed + 860)

    def taken(spawns):
        return grow({c for c, _z, _m in spawns}, 3)

    spawns7 += place([
        ("Chakoya Tribewarden", 2, 1, 90, z["forest"]),
        ("Chakoya Toolshaper", 2, 1, 90, z["forest"]),
        ("Chakoya Windcaller", 2, 1, 90, z["forest"]),
        ("Husky", 2, 1, 120, z["forest"] | z["lake"]),
        ("Barbarian Headsplitter", 1, 1, 120, z["lake"]),
        ("Barbarian Skullhunter", 1, 1, 120, z["lake"]),
        ("Barbarian Brutetamer", 1, 1, 150, z["mountain"]),
        ("Barbarian Bloodwalker", 2, 1, 150, z["mountain"]),
        ("Frost Giant", 2, 1, 150, z["mountain"]),
        ("Frost Giantess", 1, 1, 150, z["mountain"]),
    ], walk7, avoid7 | taken(spawns7), 7, rng860, min_gap=4)
    spawns8 += place([
        ("Ice Golem", 3, 1, 180, walk8r),
        ("Crystal Spider", 2, 1, 240, walk8r),
    ], walk8r, avoid8 | taken(spawns8), 8, rng860, min_gap=5)
    spawns9 += place([
        ("Frost Dragon Hatchling", 2, 1, 240, caves["hall"]),
    ], walk9r, avoid9 | taken(spawns9), 9, rng860, min_gap=4)

    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        if a.preview:
            write_preview(a.preview, [surf, caves["t8"], caves["t9"]], otb)
        return 1

    n_mon = sum(len(m) for s in (spawns7, spawns8, spawns9) for _c, _z, m in s)
    print(f"isla x{X0}-{X0 + W - 1} y{Y0}-{Y0 + H - 1}: sendero {len(walk7)} casillas, z8 {len(walk8)}, z9 {len(walk9)}; "
          f"spawns {len(spawns7)}+{len(spawns8)}+{len(spawns9)} ({n_mon} monstruos); "
          f"llegada {X0 + LANDING[0]},{Y0 + LANDING[1]},7; bajada {X0 + sx},{Y0 + sy},7; z9 {X0 + dn[0]},{Y0 + dn[1]},8")
    if a.preview:
        write_preview(a.preview, [surf, caves["t8"], caves["t9"]], otb)
        print(f"preview: {a.preview}")
    if a.dump:
        a.dump.write_text(json.dumps({f"{z_}": {f"{X0 + x},{Y0 + y}": it for (x, y), it in t.items()}
                                      for z_, t in ((7, surf), (8, caves["t8"]), (9, caves["t9"]))}))
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    # --- mapa ---
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    md = root[2][0]
    backup = MAP.with_name(MAP.name + ".bak-frozenisle")
    if not backup.exists():
        shutil.copy2(MAP, backup)
    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        if az not in (Z7, Z8, Z9):
            continue
        area[2] = [t for t in area[2] if not (t[0] in (T_TILE, T_HOUSETILE)
                                              and X0 <= ax + t[1][0] < X0 + W and Y0 <= ay + t[1][1] < Y0 + H)]
        if not area[2]:
            md[2].remove(area)
    uids7 = {CHEST: None}
    buckets = {}
    for zz, t in ((Z7, surf), (Z8, caves["t8"]), (Z9, caves["t9"])):
        for (x, y), it in t.items():
            buckets.setdefault(((X0 + x) & ~0xFF, (Y0 + y) & ~0xFF, zz), []).append((X0 + x, Y0 + y, (x, y), it))
    chest_uid = {**info["chests"]}
    chest_uid9 = caves["chests9"]
    for (bx, by, zz), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, zz)), []]
        for gx, gy, loc, it in sorted(lst, key=lambda t: (t[1], t[0])):
            uid = (chest_uid if zz == Z7 else chest_uid9 if zz == Z9 else {}).get(loc)
            area[2].append(new_tile(gx, gy, bx, by, it, {CHEST: uid} if uid else uids7, TEMPLE))
        md[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    # --- spawns: fuera los del Alice Maze y los de la caja; adentro el bloque nuevo ---
    sp = SPAWNS.read_text(encoding="latin-1")
    sp = re.sub(r"\t?<!-- BEGIN FROZEN_ISLE_SPAWNS.*?<!-- END FROZEN_ISLE_SPAWNS -->\n?", "", sp, flags=re.S)

    def in_box(m):
        x, y, zz = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return X0 <= x < X0 + W and Y0 <= y < Y0 + H and zz in (Z7, Z8, Z9)

    sp = re.sub(r'[ \t]*<spawn centerx="(\d+)" centery="(\d+)" centerz="(\d+)"[^>]*>.*?</spawn>\n?',
                lambda m: "" if in_box(m) else m.group(0), sp, flags=re.S)
    block = "\t<!-- BEGIN FROZEN_ISLE_SPAWNS (scripts/map/generate-frozen-isle.py) -->\n" + \
        spawn_xml(spawns7 + spawns8 + spawns9) + "\n\t<!-- END FROZEN_ISLE_SPAWNS -->\n"
    sp = sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")

    # --- carteles ---
    rd = READABLES.read_text(encoding="latin-1")
    rd = re.sub(r"\t?<!-- BEGIN FROZEN_ISLE_SIGNS -->.*?<!-- END FROZEN_ISLE_SIGNS -->\n?", "", rd, flags=re.S)
    lines = ["\t<!-- BEGIN FROZEN_ISLE_SIGNS -->"]
    for (x, y), t in sorted(info["signs"].items()):
        lines.append(f'\t<readable x="{X0 + x}" y="{Y0 + y}" z="7" text="{t.replace(chr(10), chr(92) + "n")}"/>')
    lines.append("\t<!-- END FROZEN_ISLE_SIGNS -->\n")
    rd = rd.replace("</readables>", "\n".join(lines) + "</readables>")
    READABLES.write_text(rd, encoding="latin-1")

    # --- Nimral del puerto (el que estaba en el Alice Maze) ---
    npc = NPCS.read_text(encoding="latin-1")
    npc_line = f'<npc name="Nimral" x="{X0 + NIMRAL[0]}" y="{Y0 + NIMRAL[1]}" z="7" dir="2"/>'
    npc, n = re.subn(r'<npc name="Nimral" x="413" y="102" z="7" dir="\d"/>', npc_line, npc)
    if n == 0 and npc_line not in npc:
        print("aviso: no encontré el Nimral del Alice Maze en npc.xml; revisarlo a mano", file=sys.stderr)
    NPCS.write_text(npc, encoding="latin-1")

    # --- barco: el destino Alice Maze pasa a ser la isla ---
    boat = BOAT.read_text(encoding="utf-8")
    new_entry = (f"\t{{keys = {{'frozen isle', 'frozen', 'isla helada', 'hielo'}}, price = 20, "
                 f"dest = {{{X0 + LANDING[0]}, {Y0 + LANDING[1]}, 7}}, name = 'Frozen Isle'}},")
    boat, n = re.subn(r"\t\{keys = \{'alice maze'.*?name = 'Alice Maze'\},", new_entry, boat)
    boat, n2 = re.subn(r"\t\{keys = \{'frozen isle'.*?name = 'Frozen Isle'\},", new_entry, boat) if n == 0 else (boat, 0)
    if n + n2 == 0:
        print("aviso: no encontré la entrada del Alice Maze en boat.lua; revisarla a mano", file=sys.stderr)
    BOAT.write_text(boat, encoding="utf-8")

    MANIFEST.write_text(json.dumps({
        "name": "generated-frozen-isle", "seed": a.seed,
        "box": {"x1": X0, "y1": Y0, "x2": X0 + W - 1, "y2": Y0 + H - 1, "z": [Z7, Z8, Z9]},
        "landing": {"x": X0 + LANDING[0], "y": Y0 + LANDING[1], "z": 7},
        "nimral": {"x": X0 + NIMRAL[0], "y": Y0 + NIMRAL[1], "z": 7},
        "stairs": {"x": X0 + sx, "y": Y0 + sy, "z": 7},
        "toLair": {"x": X0 + dn[0], "y": Y0 + dn[1], "z": 8},
        "portal": {"x": X0 + caves["portal"][0], "y": Y0 + caves["portal"][1], "z": 9, "to": list(TEMPLE)},
        "chests": [{"x": X0 + c[0], "y": Y0 + c[1], "z": 7, "uid": u} for c, u in info["chests"].items()]
        + [{"x": X0 + c[0], "y": Y0 + c[1], "z": 9, "uid": u} for c, u in caves["chests9"].items()],
        "spawns": {"z7": len(spawns7), "z8": len(spawns8), "z9": len(spawns9), "monsters": n_mon},
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK carteles {READABLES}\nOK npc {NPCS}\nOK barco {BOAT}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
