#!/usr/bin/env python3
"""Hell Quest: isla volcánica, destino de barco (reemplaza la isla generada de damero, nov 2026).

  z7  Isla del Infierno (variada):
        Puerto (Nimral) -> Camino de Ceniza -> Cruce
        Campos de Ceniza (oeste, llanura abierta): Fire Elemental, Dragon
        Ríos de Lava (este, ríos de lava con vados): Dragon, Dragon Lord
        Fortaleza del Culto (noroeste, patio de mármol negro): Warlock, Necromancer
        Cráter (noreste, lago de lava con fuentes; bajada en el borde)
  z8  Fauces del Infierno: red de cámaras con lava, unidas en circuito: Hellhound, Dragon Lord,
      Demon Skeleton
  z9  Abismo: Sala de los Demonios, Nido Negro (Black Dragon), arena del Ashen Lord (boss, 2 h) y la
      Cámara de la Elección: 4 cofres, se elige UNO (hellchest.lua, uid 5100-5103) + portal al templo.

Caja: x 288-405, y 124-226, z7-z9 (incluye la isla vieja x 329-371, y 160-199 y su sala de z8).

Valida antes de escribir (si algo falla no escribe nada): costa, bordes de lava (una pieza por
casilla), paredes de cueva, que se llegue del puerto a la bajada, de z8 a z9, a la arena, a los
cofres y al portal, y que ninguna casilla caminable vea el borde de la caja.

Uso (desde la raíz del repo):
  python3 scripts/map/generate-hell-quest.py --dry-run --preview /tmp/hell.png
  python3 scripts/map/generate-hell-quest.py        # escribe mapa, spawns, carteles, NPC y barco
Re-ejecutable: borra la caja z7-z9 y reemplaza los bloques HELL_QUEST de spawns y carteles.
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
_spec = importlib.util.spec_from_file_location("frozen_isle", HERE / "generate-frozen-isle.py")
FI = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(FI)
NP = FI.NP
from mapdata import (DIRS, MAP, T_AREA, T_HOUSETILE, T_TILE, parse_tree, serialize_tree)  # noqa: E402

Noise, neighbors_in, pieces_for, fix_until_valid, reach, Blocking = (
    NP.Noise, NP.neighbors_in, NP.pieces_for, NP.fix_until_valid, NP.reach, NP.Blocking)
brush, ellipse, grow = FI.brush, FI.ellipse, FI.grow
blocks_to_tiles, fix_diagonals, b_line, b_rect = FI.blocks_to_tiles, FI.fix_diagonals, FI.b_line, FI.b_rect
WALL_SIDE, WALL_CORNER, WALL_INNER, ROCK = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER, NP.ROCK
COAST_SIDE, COAST_CORNER, COAST_INNER, WATER = FI.COAST_SIDE, FI.COAST_CORNER, FI.COAST_INNER, FI.WATER
CARD = NP.CARD

SPAWNS, NPCS, READABLES, BOAT = FI.SPAWNS, FI.NPCS, FI.READABLES, FI.BOAT
MANIFEST = FI.WORLD / "generated-hell-quest.json"

X0, Y0, W, H = 288, 124, 118, 103             # x 288-405, y 124-226
Z7, Z8, Z9 = 7, 8, 9
SEA = 9
OLD_NIMRAL = (346, 168)

# --- piezas -------------------------------------------------------------------------------------
ASH, LAVA, MARBLE = 105, 598, 407             # grava (ceniza), lava, mármol negro
LAVA_SIDE = {"n": 554, "s": 555, "w": 556, "e": 557}          # lava con borde de grava (suelo)
LAVA_CORNER = {("n", "w"): 558, ("n", "e"): 559, ("s", "w"): 560, ("s", "e"): 561}
LAVA_INNER = {"nw": 562, "ne": 563, "se": 564, "sw": 565}
STONE, RUBBLE, PEBBLES, LAVA_HOLE, LAVA_FOUNTAIN = 1285, 1309, 1336, 389, 5074
DEAD_TREES = (2709, 2717, 2720)
DEMON_SKELETON, SKULLS, BONES = 2919, 5018, (3125, 2248, 2320, 3121)
DRAGON_SKULL, DRAGON_BONES = 2247, 3122
PILLAR, BROKEN_PILLAR, STATUE, ALTAR, COAL_BASIN = 1515, 3767, 1442, 1642, 2602
BARREL, CRATE, BOAT_ITEM, CAMPFIRE, SIGN, CHEST = 1770, 1739, 3591, 1423, 1429, 1740
FIRE = 1494                                   # fuego que no bloquea (decorado en la cámara)
STAIR_DOWN, STAIRS_UP, TELEPORT = 432, 1385, 1387
TEMPLE = (130, 53, 6)
# puertas de nivel (leveldoor.lua: actionId = nivel + 1000) y paredes de ladrillo para el santuario
LEVEL_FAUCES, LEVEL_ABYSS = 80, 100
DOOR_H = 1229                                 # puerta en pared horizontal (se cruza de norte a sur)
WALL_H, WALL_V, WALL_NW, WALL_SW, WALL_POST = 1028, 1030, 1029, 1033, 1032
ATTR_ACTION_ID = 4
CHEST_UIDS = (5100, 5101, 5102, 5103)         # hellchest.lua: demon helmet, MPA, BoH, demon shield

# --- superficie (coordenadas locales x 0-117, y 0-102) -------------------------------------------
HARBOR = (58, 87)
LANDING = (57, 87)
NIMRAL = (60, 86)
HUB = (58, 61)
WEST = (30, 60, 15.5, 13.0)                   # Campos de Ceniza: centro y radios
EAST = (88, 61, 16.5, 14.0)                   # Ríos de Lava
FORT = (18, 13, 44, 32)                       # Fortaleza del Culto: x0, y0, x1, y1
CRATER = (85, 22, 12.5, 7.5)                  # lago de lava del cráter
STAIRS = (70, 22)                             # bajada, en el borde oeste del cráter


def blockify(mask: set) -> set:
    """Solo los bloques de 2x2 (alineados a coordenadas pares) que caen enteros dentro de la máscara."""
    out = set()
    for (x, y) in mask:
        bx, by = x // 2 * 2, y // 2 * 2
        blk = {(bx, by), (bx + 1, by), (bx, by + 1), (bx + 1, by + 1)}
        if blk <= mask:
            out |= blk
    return out


def shrink_lava(lava: set, universe: set) -> set:
    """Achica la lava hasta que cada casilla de lava tenga UNA pieza de borde válida (las piezas van
    sobre la lava; la ceniza no lleva pieza, así que puede ser angosta). Monótono: siempre termina."""
    lava = set(lava)
    while True:
        other = universe - lava
        bad = set()
        for c in lava:
            p = pieces_for(neighbors_in(other, *c), LAVA_SIDE, LAVA_CORNER, LAVA_INNER)
            if p is None or len(p) > 1:
                bad.add(c)
        if not bad:
            return lava
        lava -= bad


def build_surface(seed: int, bl):
    rng = random.Random(seed)
    nz = Noise(seed)
    cells = {(x, y) for y in range(H) for x in range(W)}

    road = brush([(57, 84), (57, 64)], 3) | brush([(44, 60), (52, 60)], 3) | brush([(63, 60), (73, 60)], 3)
    road |= brush([(29, 47), (29, 33)], 3) | brush([(86, 47), (86, 31)], 3)
    harbor = ellipse(HARBOR[0] + 0.5, HARBOR[1], 7.5, 3.6)
    hub = ellipse(HUB[0] + 0.5, HUB[1] + 0.5, 6.5, 4.5)
    west = {(x, y) for (x, y) in ellipse(WEST[0], WEST[1], WEST[2], WEST[3])
            if nz.fbm(x / 6, y / 6, 3, 5) > 0.3}
    east = ellipse(EAST[0], EAST[1], EAST[2], EAST[3])
    fx0, fy0, fx1, fy1 = FORT
    fort = {(x, y) for x in range(fx0, fx1 + 1) for y in range(fy0, fy1 + 1)}
    cx, cy, rx, ry = CRATER
    # la lava se arma en bloques de 2x2 (como las paredes de cueva): así cada casilla tiene pieza
    crater_lava = blockify(ellipse(cx, cy, rx, ry))
    rim = ellipse(cx, cy, rx + 4.2, ry + 4.0) - ellipse(cx, cy, rx + 0.6, ry + 0.6)
    stairs_pad = ellipse(STAIRS[0] + 0.5, STAIRS[1] + 0.5, 2.0, 2.6)

    # ríos de lava del este: dos ríos de 2 bloques que bajan serpenteando, con dos vados cada uno
    rivers = set()
    for k, base in enumerate((80, 94)):
        bx = base // 2
        rows = range((EAST[1] - 16) // 2, (EAST[1] + 16) // 2 + 1)
        fords = set(rng.sample(list(rows)[3:-3], 2))
        for by in rows:
            nb = bx + (rng.choice((-1, 1)) if rng.random() < 0.35 else 0)
            for b_ in {bx, nb, bx + 1, nb + 1}:
                if by not in fords and (by - 1) not in fords:
                    rivers |= {(2 * b_ + i, 2 * by + j) for i in (0, 1) for j in (0, 1)}
            bx = nb
    rivers = blockify((rivers & grow(east, 1)) - grow(road, 1))
    # charcos de lava en los campos del oeste
    pools = set()
    for (px, py, w_, h_) in ((22, 54, 3, 2), (36, 66, 2, 2), (26, 70, 2, 1)):
        pools |= blockify(ellipse(px, py, w_ * 1.6, h_ * 1.8))
    pools = blockify(pools & grow(west, 1))

    open_ = road | harbor | hub | west | east | fort | rim | stairs_pad
    lava = (rivers | pools | crater_lava) - road - stairs_pad
    walk_core = open_ - lava

    # tierra: bloque con costa irregular que contiene todo lo jugable (+1 de orilla intransitable)
    keep_land = grow(open_ | lava, 1)
    land = set()
    for (x, y) in cells:
        edge = min(x - SEA, W - SEA - 1 - x, y - SEA, H - SEA - 1 - y)
        if edge >= 0 and (edge > 3 or nz.fbm(x / 5, y / 5, 3, 3) > 0.38 + 0.1 * (3 - edge)):
            land.add((x, y))
    land |= keep_land
    for x in range(HARBOR[0] - 4, HARBOR[0] + 5):        # bahía del puerto
        for y in range(HARBOR[1] + 4, H):
            land.discard((x, y))
    water = fix_until_valid(cells - land, cells - keep_land, COAST_SIDE, COAST_CORNER, COAST_INNER)
    land = cells - water

    # mar de lava tierra adentro: lejos de lo jugable (2) y de la costa (3), en bloques de 2x2
    sea_of_fire = blockify(land - grow(open_, 2) - grow(water, 3))
    lava = (lava | sea_of_fire) & land
    # bordes de lava: una pieza por casilla de lava que toca ceniza
    # para el borde de lava cuenta como "otro terreno" todo lo que no es lava (la lava nunca toca agua)
    lava = shrink_lava(lava, cells)
    not_lava = cells - lava
    ashy = land - lava

    tiles: dict = {}
    for c in cells:
        x, y = c
        if c in water:
            tiles[c] = [WATER]
            continue
        if c in lava:
            p = pieces_for(neighbors_in(not_lava, x, y), LAVA_SIDE, LAVA_CORNER, LAVA_INNER)
            tiles[c] = [p[0] if p else LAVA]
        elif c in fort:
            tiles[c] = [MARBLE]
        else:
            tiles[c] = [ASH]
        coast = pieces_for(neighbors_in(water, x, y), COAST_SIDE, COAST_CORNER, COAST_INNER)
        if coast:
            tiles[c] += coast

    coastal = {c for c in land if neighbors_in(water, *c)}
    walk = {c for c in walk_core if c in land and c not in lava and c not in coastal}
    occupied = set()

    def put(c, item):
        tiles[c].append(item)
        occupied.add(c)

    # obstáculos sueltos en los campos y en los ríos (rompen la llanura sin cortar el paso)
    base_reach = reach(walk, LANDING)
    n_reach = len(base_reach)
    keep_clear = grow(road | harbor | hub | stairs_pad, 1)
    for c in sorted(walk, key=lambda c: (c[1], c[0])):
        if c in keep_clear or c in fort:
            continue
        r = rng.random()
        item = None
        if r < 0.035:
            item = rng.choice((STONE, RUBBLE, LAVA_HOLE, rng.choice(DEAD_TREES)))
        if item is not None and bl.blocks(item):
            if len(reach(walk - {c}, LANDING)) != n_reach - 1:
                continue
            put(c, item)
            walk.discard(c)
            n_reach -= 1
        elif r < 0.07:
            tiles[c].append(rng.choice(BONES + (PEBBLES, SKULLS, DEMON_SKELETON)))

    # relleno: todo lo que no es jugable es roca volcánica (bloquea); lo grande no tapa el camino
    big = set()
    for c in sorted(land - walk - lava - coastal - set(occupied), key=lambda c: (c[1], c[0])):
        x, y = c
        r = rng.random()
        put(c, STONE if r < 0.55 else LAVA_HOLE if r < 0.7 else rng.choice(DEAD_TREES) if r < 0.85 else STONE)
        covers = any(q in walk for q in ((x - 1, y), (x, y - 1), (x - 1, y - 1)))
        near_big = any((x + dx, y + dy) in big for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        if not covers and not near_big and rng.random() < 0.6:
            tiles[c].append(RUBBLE)
            big.add(c)
    for c in sorted(coastal):
        if rng.random() < 0.05 and len(tiles[c]) <= 2:
            tiles[c].append(STONE)

    # --- fortaleza: columnas en el perímetro, estatuas, altar, braseros, ruinas ---
    for x in range(fx0 + 1, fx1, 3):
        for y in (fy0 + 1, fy1 - 1):
            c = (x, y)
            if c in walk and abs(x - 29) > 2:
                put(c, BROKEN_PILLAR if rng.random() < 0.35 else PILLAR)
                walk.discard(c)
    for y in range(fy0 + 4, fy1 - 2, 3):
        for x in (fx0 + 1, fx1 - 1):
            c = (x, y)
            if c in walk:
                put(c, BROKEN_PILLAR if rng.random() < 0.5 else PILLAR)
                walk.discard(c)
    altar = (31, fy0 + 3)
    for c, it in ((altar, ALTAR), ((28, fy0 + 4), STATUE), ((34, fy0 + 4), STATUE),
                  ((fx0 + 4, fy0 + 6), COAL_BASIN), ((fx1 - 4, fy0 + 6), COAL_BASIN),
                  ((fx0 + 4, fy1 - 4), COAL_BASIN), ((fx1 - 4, fy1 - 4), COAL_BASIN)):
        if c in walk:
            put(c, it)
            walk.discard(c)
    for c in ((24, 22), (37, 18), (40, 27), (22, 28)):
        if c in walk and rng.random() < 0.9:
            tiles[c].append(rng.choice((DEMON_SKELETON, SKULLS) + BONES[:2]))
    # --- cráter: fuentes de lava en el lago ---
    for c in ((cx - 5, cy - 2), (cx + 4, cy + 1), (cx, cy - 4)):
        c = (int(c[0]), int(c[1]))
        if c in lava:
            tiles[c].append(LAVA_FOUNTAIN)
    # --- puerto ---
    hx, hy = HARBOR
    for c, it in (((hx - 6, hy), BARREL), ((hx - 6, hy + 1), BARREL), ((hx - 5, hy + 1), CRATE),
                  ((hx + 5, hy - 1), CAMPFIRE)):
        if c in walk and c not in (LANDING, NIMRAL):
            put(c, it)
            walk.discard(c)
    if (hx + 1, hy + 5) in water:
        tiles[(hx + 1, hy + 5)].append(BOAT_ITEM)
    # --- bajada: santuario de ladrillo con puerta de nivel al sur (única entrada) ---
    # adentro queda un anillo caminable alrededor de la escalera: quien sube desde z8 aparece al
    # norte de la escalera y sale por la misma puerta.
    sx, sy = STAIRS
    doors = {}
    inner = {(sx + dx, sy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - {STAIRS}
    for c in inner | {(sx, sy + 3), (sx, sy + 4)}:
        tiles[c] = [tiles[c][0] if tiles[c][0] in (ASH, MARBLE) else ASH]
        walk.add(c)
    tiles[STAIRS] = [STAIR_DOWN]
    walk.discard(STAIRS)
    ring = {(sx - 2, sy - 2): WALL_NW, (sx - 2, sy + 2): WALL_SW, (sx + 2, sy + 2): WALL_POST}
    for x in range(sx - 1, sx + 3):
        ring[(x, sy - 2)] = WALL_H
    for y in range(sy - 1, sy + 2):
        ring[(sx - 2, y)] = WALL_V
        ring[(sx + 2, y)] = WALL_V
    ring[(sx - 1, sy + 2)] = WALL_H
    ring[(sx + 1, sy + 2)] = WALL_H
    ring[(sx, sy + 2)] = DOOR_H
    for c, it in ring.items():
        tiles[c] = [ASH, it]
        walk.discard(c)
    doors[(sx, sy + 2)] = LEVEL_FAUCES + 1000

    signs = {
        (hx + 3, hy - 3): "ISLA DEL INFIERNO\nAl norte, el Cruce. Oeste: Campos de Ceniza.\nEste: Rios de Lava. Arriba: la Fortaleza y el Crater.",
        (HUB[0] + 4, HUB[1] - 3): "EL CRUCE\nOeste: Campos de Ceniza. Este: Rios de Lava.\nNorte: Fortaleza del Culto y el Crater.",
        (29, fy1 + 2): "FORTALEZA DEL CULTO\nLos brujos de fuego ya no rezan a nadie.",
        (sx + 4, sy + 4): "LAS FAUCES DEL INFIERNO\nPuerta: nivel 80. Abajo cazan los perros del infierno.\nEn el Abismo, la puerta del Senor de la Ceniza pide nivel 100.",
    }
    placed = {}
    for anchor, text in signs.items():
        cands = [c for c in land - walk - lava - coastal - set(placed)
                 if any((c[0] + dx, c[1] + dy) in walk for dx, dy in CARD)]
        c = min(cands, key=lambda c: (abs(c[0] - anchor[0]) + abs(c[1] - anchor[1]), c))
        tiles[c] = [tiles[c][0], SIGN]
        placed[c] = text

    zones = {"west": west - lava, "east": east - lava, "fort": fort, "rim": rim - lava,
             "road": road | hub}
    return tiles, {"walk": walk, "water": water, "lava": lava, "ashy": ashy, "signs": placed, "zones": zones,
                   "doors": doors}


# --- cuevas ----------------------------------------------------------------------------------------

def floor_tiles(floor: set, lava: set, box: set) -> dict:
    """Piso de ceniza; charcos de lava con borde; paredes de cueva alrededor del piso + lava."""
    solid_floor = floor | lava
    lava = shrink_lava(lava, box)
    not_lava = box - lava
    ashy = solid_floor - lava
    tiles = {}
    for c in box:
        x, y = c
        if c in lava:
            p = pieces_for(neighbors_in(not_lava, x, y), LAVA_SIDE, LAVA_CORNER, LAVA_INNER)
            tiles[c] = [p[0] if p else LAVA]
        elif c in solid_floor:
            tiles[c] = [ASH]
        else:
            wall = pieces_for(neighbors_in(solid_floor, x, y), WALL_SIDE, WALL_CORNER, WALL_INNER)
            tiles[c] = [wall[0]] if wall else [ROCK]
    return tiles, ashy, lava


def build_caves(seed: int):
    rng = random.Random(seed + 11)
    box = {(x, y) for x in range(W) for y in range(H)}
    sb = (STAIRS[0] // 2, STAIRS[1] // 2)

    # z8: grilla de 3x3 cámaras unidas por un árbol + 3 pasillos extra (circuitos)
    cols, rows = (6, 20, 34, 48), (5, 17, 29, 41)       # en bloques (casillas = x2)
    rooms, centers = {}, {}
    for i, bx in enumerate(cols[:-1]):
        for j, by in enumerate(rows[:-1]):
            w_ = rng.randint(4, 7)
            h_ = rng.randint(3, 5)
            ox = bx + rng.randint(1, 13 - w_)
            oy = by + rng.randint(1, 11 - h_)
            rooms[(i, j)] = b_rect(ox, oy, ox + w_ - 1, oy + h_ - 1)
            centers[(i, j)] = (ox + w_ // 2, oy + h_ // 2)
    # cámara de llegada: la que queda bajo la bajada
    start_room = min(centers, key=lambda k: abs(centers[k][0] - sb[0]) + abs(centers[k][1] - sb[1]))
    f8 = set().union(*rooms.values())
    edges = []
    order = list(rooms)
    rng.shuffle(order)
    linked = {start_room}
    while len(linked) < len(rooms):
        cand = [(a, b) for a in linked for b in rooms if b not in linked and abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1]
        a, b = rng.choice(cand)
        edges.append((a, b))
        linked.add(b)
    extra = [(a, b) for a in rooms for b in rooms if a < b and abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
             and (a, b) not in edges and (b, a) not in edges]
    rng.shuffle(extra)
    edges += extra[:3]
    for a, b in edges:
        f8 |= b_line(centers[a], centers[b])
    f8 |= b_line(sb, centers[start_room]) | {sb, (sb[0], sb[1] + 1), (sb[0], sb[1] - 1)}
    far_room = max(rooms, key=lambda k: abs(k[0] - start_room[0]) + abs(k[1] - start_room[1]))
    down_b = centers[far_room]
    allowed8 = b_rect(4, 4, W // 2 - 5, H // 2 - 4)
    f8 = fix_diagonals(f8, allowed8) & allowed8
    floor8 = blocks_to_tiles(f8)
    down = (2 * down_b[0], 2 * down_b[1] + 1)
    # lava: charcos dentro de las cámaras grandes, lejos de pasillos y escaleras
    lava8 = set()
    for k, room in rooms.items():
        tiles_r = blocks_to_tiles(room)
        if len(room) >= 20 and k not in (start_room, far_room):
            xs = [x for x, _ in tiles_r]
            ys = [y for _, y in tiles_r]
            lx, ly = (min(xs) + max(xs)) / 2 + 0.5, (min(ys) + max(ys)) / 2 + 0.5
            lava8 |= ellipse(lx, ly, 2.2, 1.6) & tiles_r
    lava8 -= grow({STAIRS, down}, 3)
    t8, ashy8, lava8 = floor_tiles(floor8 - lava8, lava8, box)
    t8[STAIRS] = [ASH, STAIRS_UP]
    t8[down] = [STAIR_DOWN]

    # z9: bajada -> Sala de los Demonios -> Nido Negro -> antesala -> arena -> Cámara de la Elección
    db = (down[0] // 2, down[1] // 2)
    hall_d = b_rect(db[0] - 6, db[1] - 10, db[0] + 5, db[1] - 3)
    f9 = {db, (db[0], db[1] - 1), (db[0], db[1] + 1)} | b_line((db[0], db[1] - 1), (db[0], db[1] - 3)) | hall_d
    # el resto se arma hacia donde haya lugar (izquierda o derecha de la caja)
    go_left = db[0] > W // 4
    step = -1 if go_left else 1
    nest_c = (db[0] + step * 16, db[1] - 6)
    nest = b_rect(nest_c[0] - 5, nest_c[1] - 4, nest_c[0] + 5, nest_c[1] + 4)
    f9 |= nest | b_line((db[0], db[1] - 6), nest_c)
    arena_c = (nest_c[0], nest_c[1] - 15)
    arena = {b for b in b_rect(arena_c[0] - 4, arena_c[1] - 4, arena_c[0] + 4, arena_c[1] + 4)
             if (b[0] - arena_c[0]) ** 2 + (b[1] - arena_c[1]) ** 2 <= 20}
    f9 |= arena | b_line((nest_c[0], nest_c[1] - 4), (arena_c[0], arena_c[1] + 4))
    gate_y = 2 * (arena_c[1] + 7)            # fila de la puerta en el pasillo (2 de ancho)
    reward_c = (arena_c[0], arena_c[1] - 9)
    reward = b_rect(reward_c[0] - 2, reward_c[1] - 1, reward_c[0] + 2, reward_c[1] + 1)
    f9 |= reward | b_line((arena_c[0], arena_c[1] - 4), (reward_c[0], reward_c[1] + 1))
    # pilares de roca en la Sala de los Demonios y en el Nido (huecos de 1 bloque)
    for room in (hall_d, nest):
        for b in sorted(room):
            if rng.random() < 0.06 and all(n in room for n in ((b[0] + 1, b[1]), (b[0] - 1, b[1]), (b[0], b[1] + 1), (b[0], b[1] - 1))):
                f9.discard(b)
    allowed9 = b_rect(4, 4, W // 2 - 5, H // 2 - 4)
    f9 = fix_diagonals(f9, allowed9) & allowed9
    floor9 = blocks_to_tiles(f9)
    lava9 = set()
    arena_t = blocks_to_tiles(arena) & floor9
    # anillo de lava en la arena (deja el centro y la entrada libres)
    ax, ay = 2 * arena_c[0] + 1, 2 * arena_c[1] + 1
    ring = {c for c in arena_t if 4.0 <= math.hypot(c[0] + 0.5 - ax, c[1] + 0.5 - ay) <= 7.2
            and abs(c[0] + 0.5 - ax) > 2.5 and abs(c[1] + 0.5 - ay) > 1.5}
    lava9 = blockify(ring)               # cuatro arcos de lava; libres el pasillo central y los costados
    t9, ashy9, lava9 = floor_tiles(floor9 - lava9, lava9, box)
    t9[down] = [ASH, STAIRS_UP]
    rw = blocks_to_tiles(reward) & floor9
    rx = 2 * reward_c[0] + 1
    ry = 2 * reward_c[1]
    chests = {}
    for k, dx in enumerate((-4, -2, 2, 4)):
        c = (rx + dx - (1 if dx > 0 else 0), ry - 1)
        chests[c] = CHEST_UIDS[k]
        t9[c] = [t9[c][0], CHEST]
    portal = (rx, ry + 1)
    t9[portal] = [t9[portal][0], TELEPORT]
    gx = 2 * arena_c[0]
    gate = (gx, gate_y)
    t9[gate] = [ASH, DOOR_H]
    t9[(gx + 1, gate_y)] = [ASH, WALL_H]
    doors9 = {gate: LEVEL_ABYSS + 1000}
    for c in ((rx - 4, ry + 2), (rx + 3, ry + 2)):
        if c in floor9 and c not in chests:
            t9[c] = [t9[c][0], COAL_BASIN]
    return {"t8": t8, "floor8": floor8 - lava8, "rooms8": {k: blocks_to_tiles(r) - lava8 for k, r in rooms.items()},
            "down": down, "t9": t9, "floor9": floor9 - lava9, "hall_d": blocks_to_tiles(hall_d) & floor9,
            "nest": blocks_to_tiles(nest) & floor9, "arena": arena_t - lava9, "arena_c": (ax, ay),
            "reward": rw, "chests": chests, "portal": portal, "doors": doors9}


def decorate_cave(tiles, floor, start, keep, seed, rate, bl):
    rng = random.Random(seed + 4242)
    walk = set(floor)
    base = len(reach(walk, start, CARD))
    for c in sorted(floor, key=lambda c: (c[1], c[0])):
        if c in keep or len(tiles[c]) > 1 or tiles[c][0] != ASH:
            continue
        rock_n = 8 - len(neighbors_in(floor, *c))
        r = rng.random()
        if rock_n >= 3 and r < 0.10:
            if len(reach(walk - {c}, start, CARD)) == base - 1:
                tiles[c].append(rng.choice((STONE, LAVA_HOLE, STONE)))
                walk.discard(c)
                base -= 1
        elif r < 0.025:
            tiles[c].append(PEBBLES)
        elif r < 0.025 + rate:
            tiles[c].append(rng.choice(BONES + (SKULLS, DRAGON_SKULL)))


def new_tile(x, y, bx, by, items, uid=None, aid=None, tele=None):
    """Casilla con suelo + ítems; el cofre lleva uniqueId, la puerta actionId y el portal destino."""
    props = bytearray([x - bx, y - by, 9]) + struct.pack("<H", items[0])
    kids = []
    for i in items[1:]:
        p = bytearray(struct.pack("<H", i))
        if i in FI.NEEDS_COUNT:                   # el server exige el byte de cantidad
            p.append(1)
        if i == CHEST and uid is not None:
            p += bytes([FI.ATTR_UNIQUE_ID]) + struct.pack("<H", uid)
        if i == DOOR_H and aid is not None:
            p += bytes([ATTR_ACTION_ID]) + struct.pack("<H", aid)
        if i == TELEPORT and tele is not None:
            p += bytes([FI.ATTR_TELE_DEST]) + struct.pack("<HHB", *tele)
        kids.append([FI.T_ITEM, p, []])
    return [T_TILE, props, kids]


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{X0 + cx}" centery="{Y0 + cy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--dump", type=Path)
    a = ap.parse_args()

    bl = Blocking()
    otb = bl.otb
    surf, info = build_surface(a.seed, bl)
    caves = build_caves(a.seed)
    sx, sy = STAIRS
    dn = caves["down"]
    decorate_cave(caves["t8"], caves["floor8"], (sx, sy + 1), grow({STAIRS, dn, (sx, sy + 1)}, 2), a.seed + 1, 0.03, bl)
    keep9 = grow({dn} | set(caves["chests"]) | {caves["portal"]} | set(caves["doors"]), 2) | caves["reward"] | caves["arena"]
    decorate_cave(caves["t9"], caves["floor9"], (dn[0], dn[1] - 1), keep9, a.seed + 2, 0.05, bl)

    errors = []
    land = set(surf) - info["water"]
    for c, it in surf.items():                      # costa
        if c in info["water"]:
            continue
        want = pieces_for(neighbors_in(info["water"], *c), COAST_SIDE, COAST_CORNER, COAST_INNER)
        have = [i for i in it if i in set(COAST_SIDE.values()) | set(COAST_CORNER.values()) | set(COAST_INNER.values())]
        if want is None or sorted(want) != sorted(have):
            errors.append(f"costa {c}: quiere {want} tiene {have}")
    lava_pieces = set(LAVA_SIDE.values()) | set(LAVA_CORNER.values()) | set(LAVA_INNER.values())
    for label, t in (("z7", surf), ("z8", caves["t8"]), ("z9", caves["t9"])):
        lav = {c for c, it in t.items() if it[0] == LAVA or it[0] in lava_pieces}
        ash = set(t) - lav
        for c in lav:
            want = pieces_for(neighbors_in(ash, *c), LAVA_SIDE, LAVA_CORNER, LAVA_INNER)
            if want is None or len(want) > 1 or (want and t[c][0] != want[0]) or (not want and t[c][0] != LAVA):
                errors.append(f"lava {label} {c}: quiere {want} tiene {t[c][0]}")
    for t, label in ((caves["t8"], "z8"), (caves["t9"], "z9")):
        fl = {c for c, it in t.items() if it[0] in (ASH, LAVA, STAIR_DOWN) or it[0] in lava_pieces}
        for c, it in t.items():
            if c in fl:
                continue
            want = pieces_for(neighbors_in(fl, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
            if want is None or len(want) > 1 or (want and it[0] != want[0]) or (not want and it[0] != ROCK):
                errors.append(f"pared {label} {c}: quiere {want} tiene {it[0]}")

    # las puertas de nivel cuentan como paso (para quien tiene el nivel); hay que poder pararse enfrente
    for t, drs, label in ((surf, info["doors"], "z7"), (caves["t9"], caves["doors"], "z9")):
        for (x, y) in drs:
            for q in ((x, y - 1), (x, y + 1)):
                if not bl.walkable(t[q]):
                    errors.append(f"{label}: la puerta {(x, y)} no tiene piso libre en {q}")
    walk7 = {c for c, it in surf.items() if bl.walkable(it) or c in info["doors"]}
    d7 = reach(walk7, LANDING)
    for label, c in (("Nimral", NIMRAL), ("bajada (sur)", (sx, sy + 1)), ("bajada (norte)", (sx, sy - 1)),
                     ("fortaleza", (31, 25)), ("campos", (30, 60)), ("ríos (este)", (100, 60))):
        if c not in d7:
            errors.append(f"z7: {label} {c} no se alcanza desde el puerto")
    sin_puerta = reach(walk7 - set(info["doors"]), LANDING)
    if (sx, sy + 1) in sin_puerta or (sx, sy - 1) in sin_puerta:
        errors.append("z7: se llega a la bajada sin pasar la puerta de nivel")
    walk8 = {c for c, it in caves["t8"].items() if bl.walkable(it) and it[0] in (ASH, STAIR_DOWN)}
    d8 = reach(walk8, (sx, sy + 1), CARD)
    if (dn[0], dn[1] - 1) not in d8 or (dn[0], dn[1] + 1) not in d8:
        errors.append(f"z8: la bajada a z9 {dn} no se alcanza")
    for k, room in caves["rooms8"].items():
        if room and not (room & set(d8)):
            errors.append(f"z8: cámara {k} aislada")
    walk9 = {c for c, it in caves["t9"].items() if (bl.walkable(it) and it[0] == ASH) or c in caves["doors"]}
    d9 = reach(walk9, (dn[0], dn[1] - 1), CARD)
    for c in list(caves["chests"]) + [caves["portal"]]:
        if not any((c[0] + ddx, c[1] + ddy) in d9 for ddx, ddy in CARD):
            errors.append(f"z9: {c} sin acceso")
    if not (caves["arena"] & set(d9)):
        errors.append("z9: la arena no se alcanza")
    if caves["arena"] & set(reach(walk9 - set(caves["doors"]), (dn[0], dn[1] - 1), CARD)):
        errors.append("z9: se llega a la arena sin pasar la puerta de nivel")
    for label, wk in (("z7", walk7), ("z8", walk8), ("z9", walk9)):
        bad = [(x, y) for (x, y) in wk if x < 8 or x > W - 9 or y < 6 or y > H - 7]
        if bad:
            errors.append(f"{label}: {len(bad)} casillas ven el borde de la caja, ej. {bad[0]}")

    # spawns
    rng = random.Random(a.seed + 99)
    z = info["zones"]
    avoid7 = grow({LANDING, NIMRAL, HARBOR}, 8) | grow({STAIRS}, 5) | grow({HUB}, 3)
    spawns7 = FI.place([
        ("Fire Elemental", 5, 2, 120, z["west"]),
        ("Dragon", 4, 2, 150, z["west"]),
        ("Dragon", 4, 2, 150, z["east"]),
        ("Dragon Lord", 3, 1, 200, z["east"]),
        ("Warlock", 3, 1, 300, z["fort"]),
        ("Necromancer", 3, 2, 180, z["fort"]),
        ("Dragon Lord", 2, 1, 200, z["rim"]),
    ], walk7, avoid7, 7, rng)
    walk8r = {c for c in walk8 if c in d8}
    rooms = set().union(*caves["rooms8"].values())
    spawns8 = FI.place([
        ("Hellhound", 9, 3, 180, rooms),
        ("Dragon Lord", 4, 1, 200, rooms),
        ("Demon Skeleton", 6, 2, 150, walk8r),
    ], walk8r, grow({STAIRS, dn}, 4), 8, rng, min_gap=6)
    walk9r = {c for c in walk9 if c in d9}
    spawns9 = FI.place([
        ("Demon", 4, 1, 300, caves["hall_d"]),
        ("Black Dragon", 4, 1, 300, caves["nest"]),
        ("Hellhound", 2, 2, 180, walk9r - caves["arena"] - caves["reward"]),
    ], walk9r, grow({dn} | set(caves["doors"]), 4) | caves["arena"] | caves["reward"], 9, rng, min_gap=5)
    boss_c = caves["arena_c"]
    boss_spot = min(caves["arena"], key=lambda c: abs(c[0] + 0.5 - boss_c[0]) + abs(c[1] + 0.5 - boss_c[1]))
    spawns9.append((boss_spot, 9, [("Ashen Lord", boss_spot, 7200)]))

    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        if a.preview:
            FI.W, FI.H = W, H  # la vista previa usa el tamaño de la caja del módulo
            FI.write_preview(a.preview, [surf, caves["t8"], caves["t9"]], otb)
        return 1

    n_mon = sum(len(m) for s in (spawns7, spawns8, spawns9) for _c, _z, m in s)
    print(f"hell quest x{X0}-{X0 + W - 1} y{Y0}-{Y0 + H - 1}: z7 {len(walk7)} caminables, z8 {len(walk8)}, z9 {len(walk9)}; "
          f"spawns {len(spawns7)}+{len(spawns8)}+{len(spawns9)} ({n_mon} monstruos); llegada {X0 + LANDING[0]},{Y0 + LANDING[1]},7; "
          f"bajada {X0 + sx},{Y0 + sy},7; z9 {X0 + dn[0]},{Y0 + dn[1]},8; boss {X0 + boss_spot[0]},{Y0 + boss_spot[1]},9")
    if a.preview:
        FI.W, FI.H = W, H  # la vista previa usa el tamaño de la caja del módulo
        FI.write_preview(a.preview, [surf, caves["t8"], caves["t9"]], otb)
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
    backup = MAP.with_name(MAP.name + ".bak-hellquest")
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
    buckets = {}
    for zz, t in ((Z7, surf), (Z8, caves["t8"]), (Z9, caves["t9"])):
        for (x, y), it in t.items():
            buckets.setdefault(((X0 + x) & ~0xFF, (Y0 + y) & ~0xFF, zz), []).append((X0 + x, Y0 + y, (x, y), it))
    for (bx, by, zz), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, zz)), []]
        for gx, gy, loc, it in sorted(lst, key=lambda t: (t[1], t[0])):
            uid = caves["chests"].get(loc) if zz == Z9 else None
            aid = (info["doors"] if zz == Z7 else caves["doors"] if zz == Z9 else {}).get(loc)
            area[2].append(new_tile(gx, gy, bx, by, it, uid=uid, aid=aid, tele=TEMPLE))
        md[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    # --- spawns: fuera los de la caja; adentro el bloque nuevo ---
    sp = SPAWNS.read_text(encoding="latin-1")
    sp = re.sub(r"\t?<!-- BEGIN HELL_QUEST_SPAWNS.*?<!-- END HELL_QUEST_SPAWNS -->\n?", "", sp, flags=re.S)

    def in_box(m):
        x, y, zz = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return X0 <= x < X0 + W and Y0 <= y < Y0 + H and zz in (Z7, Z8, Z9)

    sp = re.sub(r'[ \t]*<spawn centerx="(\d+)" centery="(\d+)" centerz="(\d+)"[^>]*>.*?</spawn>\n?',
                lambda m: "" if in_box(m) else m.group(0), sp, flags=re.S)
    block = "\t<!-- BEGIN HELL_QUEST_SPAWNS (scripts/map/generate-hell-quest.py) -->\n" + \
        spawn_xml(spawns7 + spawns8 + spawns9) + "\n\t<!-- END HELL_QUEST_SPAWNS -->\n"
    sp = sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")

    # --- carteles ---
    rd = READABLES.read_text(encoding="latin-1")
    rd = re.sub(r"\t?<!-- BEGIN HELL_QUEST_SIGNS -->.*?<!-- END HELL_QUEST_SIGNS -->\n?", "", rd, flags=re.S)
    lines = ["\t<!-- BEGIN HELL_QUEST_SIGNS -->"]
    for (x, y), t in sorted(info["signs"].items()):
        lines.append(f'\t<readable x="{X0 + x}" y="{Y0 + y}" z="7" text="{t.replace(chr(10), chr(92) + "n")}"/>')
    lines.append("\t<!-- END HELL_QUEST_SIGNS -->\n")
    rd = rd.replace("</readables>", "\n".join(lines) + "</readables>")
    READABLES.write_text(rd, encoding="latin-1")

    # --- Nimral del puerto ---
    npc = NPCS.read_text(encoding="latin-1")
    line = f'<npc name="Nimral" x="{X0 + NIMRAL[0]}" y="{Y0 + NIMRAL[1]}" z="7" dir="2"/>'
    pat = rf'<npc name="Nimral" x="({OLD_NIMRAL[0]}|{X0 + NIMRAL[0]})" y="({OLD_NIMRAL[1]}|{Y0 + NIMRAL[1]})" z="7" dir="\d"/>'
    npc, n = re.subn(pat, line, npc)
    if n == 0:
        print("aviso: no encontré el Nimral de Hell Quest en npc.xml; revisarlo a mano", file=sys.stderr)
    NPCS.write_text(npc, encoding="latin-1")

    # --- barco ---
    boat = BOAT.read_text(encoding="utf-8")
    boat, n = re.subn(r"(\{keys = \{'hell quest', 'hell'\}, price = 20, dest = )\{\d+, \d+, \d+\}",
                      rf"\g<1>{{{X0 + LANDING[0]}, {Y0 + LANDING[1]}, 7}}", boat)
    if n == 0:
        print("aviso: no encontré el destino Hell Quest en boat.lua; revisarlo a mano", file=sys.stderr)
    BOAT.write_text(boat, encoding="utf-8")

    MANIFEST.write_text(json.dumps({
        "name": "generated-hell-quest", "seed": a.seed,
        "box": {"x1": X0, "y1": Y0, "x2": X0 + W - 1, "y2": Y0 + H - 1, "z": [Z7, Z8, Z9]},
        "landing": {"x": X0 + LANDING[0], "y": Y0 + LANDING[1], "z": 7},
        "nimral": {"x": X0 + NIMRAL[0], "y": Y0 + NIMRAL[1], "z": 7},
        "stairs": {"x": X0 + sx, "y": Y0 + sy, "z": 7},
        "toAbyss": {"x": X0 + dn[0], "y": Y0 + dn[1], "z": 8},
        "boss": {"x": X0 + boss_spot[0], "y": Y0 + boss_spot[1], "z": 9, "name": "Ashen Lord", "spawntime": 7200},
        "chests": [{"x": X0 + c[0], "y": Y0 + c[1], "z": 9, "uid": u} for c, u in caves["chests"].items()],
        "portal": {"x": X0 + caves["portal"][0], "y": Y0 + caves["portal"][1], "z": 9, "to": list(TEMPLE)},
        "spawns": {"z7": len(spawns7), "z8": len(spawns8), "z9": len(spawns9), "monsters": n_mon},
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK carteles {READABLES}\nOK npc {NPCS}\nOK barco {BOAT}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
