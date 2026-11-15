#!/usr/bin/env python3
"""Dark Cathedral: catedral en ruinas en la jungla, con cripta de dos pisos (z8/z9).

Recrea la Dark Cathedral de Tibia 7.6 en una zona vacía del mapa, con portal desde la plaza de
portales del templo. Tres pisos apilados en la misma caja:

  z7  Superficie: jungla cerrada alrededor, nave NEGRA de la catedral (norte-sur) con entrada al
      sur, ruinas de ladrillo al oeste (edificio grande) y al este (salas chicas), sala rectangular
      gris al sur con bancos/escombros, franja de jungla en arco al norte y dos bajadas
      ("acesso ao -2"): una al norte en la jungla y otra al oeste junto a la sala gris.
  z8  Cripta (-1): pasillos y salas de ladrillo sobre roca marrón, conectando las dos bajadas y con
      una bajada al -2.
  z9  Cripta profunda (-2): planta simétrica — sala grande al norte, cruz central con la escalera de
      subida, brazos oeste/este con salas, y al sur la sala grande central + salas laterales.

Reglas (las mismas del resto del mapa, ver docs/items-and-map/map-kb/ y PIEZAS_DE_MAPA.md):
  - paredes de ladrillo (naranja) y piedra (gris) con el modelo de roomkit (post/h/v/se);
  - escaleras: agujero 432 arriba + escalera 1385 abajo en la misma casilla (sube al norte);
  - jungla cerrada en el borde (BAND) para no ver el vacío de la caja.

El portal del templo lo maneja scripts/map/temple-portals.py (destino LANDING, portal 157,47,7).

Uso (desde la raíz del repo):
  python3 scripts/map/generate-dark-cathedral.py --dry-run --preview /tmp/catedral   # valida y dibuja
  python3 scripts/map/generate-dark-cathedral.py                                      # escribe todo
  python3 scripts/map/temple-portals.py                                               # portal de la plaza
Re-ejecutable: borra la caja z7-z9 y reemplaza los bloques DARK_CATHEDRAL de spawns/carteles.
Doc: docs/items-and-map/MAPEAR_DARK_CATHEDRAL.md.
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
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import (MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, Renderer,  # noqa: E402
                     parse_tree, png_bytes, serialize_tree)

_spec = importlib.util.spec_from_file_location("north_pass", HERE / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)
Noise, neighbors_in, reach, Blocking = NP.Noise, NP.neighbors_in, NP.reach, NP.Blocking
CARD, ALL8, DIRS = NP.CARD, NP.ALL8, NP.DIRS
GRASS, DIRT, ROCK = NP.GRASS, NP.DIRT, NP.ROCK
FOREST_TREES, FOREST_SMALL_TREE, BUSHES = NP.FOREST_TREES, NP.FOREST_SMALL_TREE, NP.BUSHES
FLOWERS, MUSHROOMS = NP.FLOWERS, NP.MUSHROOMS
STONE, RUBBLE_GREY, RUBBLE_BROWN, PEBBLES = NP.STONE, NP.RUBBLE_GREY, NP.RUBBLE_BROWN, NP.PEBBLES
CAMPFIRE, LANTERN, SIGN = NP.CAMPFIRE, NP.LANTERN, NP.SIGN
TELEPORT, ATTR_TELE_DEST = NP.TELEPORT, NP.ATTR_TELE_DEST
STAIR_DOWN, STAIRS_UP = NP.STAIR_DOWN, NP.STAIRS_UP
NEEDS_COUNT = NP.NEEDS_COUNT
item_node = NP.item_node
new_tile_node = NP.new_tile_node

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MANIFEST = WORLD / "generated-dark-cathedral.json"

# --- caja (zona vacía; verificado contra el OTBM el 15 nov 2026) -----------------------------
X0, Y0, W, H = 200, 380, 72, 72          # x 200-271, y 380-451
Z7, Z8, Z9 = 7, 8, 9
BAND = 8                                 # franja exterior intransitable (jungla cerrada)
TEMPLE_BACK = (157, 48, 7)               # llegada del portal Dark Cathedral en la plaza
VIEW = (7, 5)                            # media pantalla del cliente 7.6

# --- piezas (ids de servidor) -----------------------------------------------------------------
BLACK, GREY = 407, 415                   # mármol negro (nave) / piedra gris (salas, cripta)
BRICK = dict(h=1028, v=1030, post=1027, se=1033)      # ladrillo naranja
STONE_WALL = dict(h=1050, v=1049, post=1051, se=1053)  # piedra gris
BENCH, RUBBLE, PILLAR, BROKEN_PILLAR = 1662, 1309, 1515, 3767
SKULL, HUMAN_SKELETON = 2247, 3133
COAL_BASIN = 1486

# --- disposición z7 (coordenadas locales) ------------------------------------------------------
ARRIVAL = (36, 48)                        # destino del portal de la plaza (frente a la entrada)
PORTAL_BACK = (33, 50)                    # vuelta al templo, al oeste de la llegada
NAVE = (32, 14, 39, 45)                   # nave negra: interior x32-39, y14-45
NAVE_DOOR = [(35, 46), (36, 46)]          # puerta de la nave (sur)
WEST = (9, 12, 28, 40)                    # edificio grande oeste (ladrillo, piso de tierra)
WEST_WALL = (19, 12, 19, 40)              # tabique interno vertical
WEST_DOORS = [(19, 24), (19, 25)]         # puerta interna del edificio oeste
WEST_DOOR_OUT = [(15, 41), (16, 41)]      # salida del edificio oeste al sur
EAST = (47, 12, 63, 38)                   # salas chicas este (ladrillo, tierra)
EAST_WALLS = [(54, 12, 54, 38)]           # tabique interno
EAST_DOORS = [(54, 24), (54, 25)]
EAST_DOOR_OUT = [(54, 39), (55, 39)]      # salida sur
SOUTH = (26, 53, 46, 62)                  # sala rectangular gris (bancos/escombros)
SOUTH_DOOR = [(35, 52), (36, 52)]         # puerta norte de la sala gris
HOLE_NORTH = (36, 9)                      # bajada A: jungla norte
HOLE_WEST = (24, 50)                      # bajada B: oeste, junto a la sala gris


def rect(x0, y0, x1, y1) -> set:
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def grow(cells, r: int) -> set:
    return {(x + dx, y + dy) for (x, y) in cells for dx in range(-r, r + 1) for dy in range(-r, r + 1)}


def diagonal_fill(floor: set, cells: set) -> set:
    """Rellena contactos solo en diagonal para que las paredes no tengan esquinas internas."""
    changed = True
    while changed:
        changed = False
        for (x, y) in list(floor):
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                if (x + dx, y + dy) in floor and (x + dx, y) not in floor and (x, y + dy) not in floor:
                    if (x + dx, y) in cells:
                        floor.add((x + dx, y))
                        changed = True
                    elif (x, y + dy) in cells:
                        floor.add((x, y + dy))
                        changed = True
    return floor


def wall_piece(card: set, W: dict):
    if card == {"s", "e"}:
        return W["post"]
    if card == {"s", "w"}:
        return W["h"]
    if card == {"n", "e"}:
        return W["v"]
    if card == {"n", "w"}:
        return W["se"]
    if "n" in card or "s" in card:
        return W["h"]
    if "e" in card or "w" in card:
        return W["v"]
    return None


def building(floor: set, cells: set, walls: dict, ground: int) -> dict:
    """Suelo + anillo de paredes para un conjunto de casillas de piso."""
    floor = diagonal_fill(set(floor), cells)
    tiles = {}
    for c in cells:
        if c in floor:
            tiles[c] = [ground]
            continue
        card = {d for d, (dx, dy) in DIRS.items() if (c[0] + dx, c[1] + dy) in floor}
        p = wall_piece(card, walls)
        if p is not None:
            tiles[c] = [ground, p]
    return tiles


def check_walls(tiles, floor, walls, label):
    """Cada casilla de pared debe tener exactamente una pieza (sin esquinas internas)."""
    errs = []
    for c, it in tiles.items():
        if c in floor or it[0] == ROCK or it[0] == GRASS:
            continue
        if len(it) != 2:
            errs.append(f"{label} {c}: pared con {len(it) - 1} piezas {it}")
    return errs


# --- superficie ----------------------------------------------------------------------------------

def build_surface(seed: int, bl: Blocking):
    rng = random.Random(seed)
    nz = Noise(seed)
    cells = {(x, y) for y in range(H) for x in range(W)}
    tiles: dict = {c: [GRASS] for c in cells}

    # edificios: interior (sin puertas) -> anillo de paredes -> abrir puertas
    nave_floor = rect(*NAVE)
    west_floor = rect(*WEST) - {(WEST_WALL[0], y) for y in range(WEST_WALL[1], WEST_WALL[3] + 1)}
    east_floor = rect(*EAST)
    for (wx0, wy0, wx1, wy1) in EAST_WALLS:
        east_floor -= {(x, y) for x in range(wx0, wx1 + 1) for y in range(wy0, wy1 + 1)}
    south_floor = rect(*SOUTH)

    tiles.update(building(nave_floor, cells, STONE_WALL, BLACK))
    tiles.update(building(west_floor, cells, BRICK, DIRT))
    tiles.update(building(east_floor, cells, BRICK, DIRT))
    tiles.update(building(south_floor, cells, STONE_WALL, GREY))

    doors = ([(c, BLACK) for c in NAVE_DOOR]
             + [(c, DIRT) for c in WEST_DOORS + WEST_DOOR_OUT + EAST_DOORS + EAST_DOOR_OUT]
             + [(c, GREY) for c in SOUTH_DOOR])
    for c, g in doors:
        tiles[c] = [g]

    # huecos de bajada
    tiles[HOLE_NORTH] = [STAIR_DOWN]
    tiles[HOLE_WEST] = [STAIR_DOWN]

    # portales, cartel y braseros de la llegada
    tiles[ARRIVAL] = [GRASS]
    tiles[PORTAL_BACK] = [GRASS, TELEPORT]
    for c in ((PORTAL_BACK[0] - 1, PORTAL_BACK[1]), (PORTAL_BACK[0] + 1, PORTAL_BACK[1]),
              (PORTAL_BACK[0], PORTAL_BACK[1] + 1)):
        if c in cells and tiles.get(c) == [GRASS]:
            tiles[c] = [GRASS, STONE]
    for c in ((PORTAL_BACK[0] - 2, PORTAL_BACK[1] - 1), (PORTAL_BACK[0] + 2, PORTAL_BACK[1] - 1)):
        if c in cells and tiles.get(c) == [GRASS]:
            tiles[c] = [GRASS, LANTERN]
    signs = {
        (ARRIVAL[0] + 3, ARRIVAL[1] - 1): "CATEDRAL OSCURA\nAl norte: la nave de la catedral.\n"
                                           "Bajadas a la cripta en la jungla norte\ny junto a la sala gris (oeste).\n"
                                           "Portal al sur: templo.",
        (NAVE[0] - 3, NAVE[1] + 2): "NAVE DE LA CATEDRAL\nSolo los muertos y los monjes\nosaron entrar.",
        (SOUTH[0] - 3, SOUTH[1] + 1): "SALA DE LOS BANCOS\nEscombros y bancos viejos.\nUna bajada al oeste.",
    }
    for c, t in signs.items():
        tiles[c] = [GRASS, SIGN]

    # decoración de la sala gris (bancos y escombros, que no bloquean)
    for (x, y) in rect(*SOUTH):
        if tiles.get((x, y)) != [GREY]:
            continue
        r = rng.random()
        if r < 0.28 and (y - SOUTH[1]) % 3 == 1:
            tiles[(x, y)] = [GREY, BENCH]
        elif r < 0.18:
            tiles[(x, y)] = [GREY, rng.choice((PEBBLES, RUBBLE_BROWN))]

    # pilares dentro de la nave (bloquean, dejan pasillo central)
    for y in range(NAVE[1] + 2, NAVE[3], 4):
        for x in (NAVE[0] + 1, NAVE[2] - 1):
            if tiles.get((x, y)) == [BLACK]:
                tiles[(x, y)] = [BLACK, PILLAR]
    tiles[(NAVE[0] + 1, NAVE[3] - 1)] = [BLACK, BROKEN_PILLAR]
    tiles[(NAVE[2] - 1, NAVE[3] - 1)] = [BLACK, BROKEN_PILLAR]

    # marcos de piedra y braseros en las bajadas
    for hole in (HOLE_NORTH, HOLE_WEST):
        for dx, dy in ((-2, -1), (-2, 0), (-2, 1), (2, -1), (2, 1), (-1, -2), (1, -2), (-1, 2), (1, 2)):
            c = (hole[0] + dx, hole[1] + dy)
            if c in cells and tiles.get(c) == [GRASS]:
                tiles[c] = [GRASS, STONE]
        for dx in (-1, 1):
            c = (hole[0] + dx, hole[1] + 1)
            if c in cells and tiles.get(c) == [GRASS]:
                tiles[c] = [GRASS, COAL_BASIN]

    # zonas que deben quedar libres de decoración (llegadas, puertas, huecos)
    door_cells = (set(NAVE_DOOR) | set(WEST_DOORS) | set(WEST_DOOR_OUT)
                  | set(EAST_DOORS) | set(EAST_DOOR_OUT) | set(SOUTH_DOOR))
    keep_clear = (grow({ARRIVAL, PORTAL_BACK, HOLE_NORTH, HOLE_WEST}, 2)
                  | grow(door_cells, 1) | door_cells
                  | set(signs) | {(36, 8), (24, 49), (24, 51)})
    occupied: set = set()

    def put(c, item, size=1):
        tiles[c] = [tiles[c][0], item] if tiles[c] == [GRASS] else tiles[c] + [item]
        for dx in range(size):
            for dy in range(size):
                occupied.add((c[0] - dx, c[1] - dy))

    # jungla: árboles en el borde y en la franja norte, monte suelto en el resto
    edge = {c for c in cells if c[0] < BAND or c[0] >= W - BAND or c[1] < BAND or c[1] >= H - BAND}
    north_arc = {c for c in cells if c[1] < NAVE[1] - 2}
    for c in sorted(edge | north_arc, key=lambda c: (c[1], c[0])):
        if tiles.get(c) != [GRASS] or c in keep_clear or c in occupied:
            continue
        x, y = c
        if x % 2 == 1 and y % 2 == 1:
            put(c, rng.choice(FOREST_TREES), 2)
        else:
            put(c, rng.choice((FOREST_SMALL_TREE,) + BUSHES))
    for c in sorted(cells, key=lambda c: (c[1], c[0])):
        if tiles.get(c) != [GRASS] or c in keep_clear or c in occupied:
            continue
        r = rng.random()
        if c in north_arc:
            put(c, rng.choice(FOREST_TREES) if r < 0.4 else FOREST_SMALL_TREE)
        elif r < 0.06 and nz.fbm(c[0] / 6, c[1] / 6, 2, 300) > 0.5:
            put(c, rng.choice(FOREST_TREES), 2)
        elif r < 0.12:
            put(c, rng.choice(BUSHES))
        elif r < 0.2:
            tiles[c] = [GRASS, rng.choice(FLOWERS + MUSHROOMS)]

    return tiles, {"cells": cells, "keep_clear": keep_clear,
                   "nave": nave_floor, "west": west_floor, "east": east_floor, "south": south_floor,
                   "signs": signs}


# --- cripta ---------------------------------------------------------------------------------------

def build_dungeon(seed: int, floors: list, cells: set, walls: dict, ground: int):
    """Suelo + paredes de un piso de cripta sobre fondo de roca. floors = rects de piso."""
    floor = set().union(*floors)
    floor = diagonal_fill(floor, cells)
    tiles = {c: [ROCK] for c in cells}
    tiles.update(building(floor, cells, walls, ground))
    return tiles, floor


# z8: cripta (-1), ladrillo sobre roca marrón
def z8_floors():
    spine = rect(35, 9, 36, 50)
    w = [
        rect(12, 14, 26, 26), rect(27, 19, 35, 20),      # sala oeste 1 + corredor
        rect(12, 30, 26, 42), rect(27, 35, 35, 36),      # sala oeste 2 + corredor
        rect(12, 46, 26, 58), rect(27, 47, 35, 48),      # cueva oeste (no-muertos)
    ]
    e = [
        rect(42, 12, 56, 24), rect(37, 16, 41, 17),
        rect(42, 28, 56, 40), rect(37, 32, 41, 33),
        rect(42, 44, 56, 54), rect(37, 46, 41, 47),
    ]
    return [spine] + w + e


# z9: cripta profunda (-2), piedra gris, planta simétrica
def z9_floors():
    return [
        rect(24, 10, 48, 22),        # sala grande norte
        rect(35, 22, 36, 52),        # cruz central vertical (escalera en 36,34)
        rect(16, 33, 56, 34),        # cruz central horizontal
        rect(8, 26, 34, 40),         # brazo oeste
        rect(38, 26, 64, 40),        # brazo este
        rect(24, 42, 48, 52),        # sala central sur (grande)
        rect(8, 44, 22, 56),         # sala lateral oeste
        rect(50, 44, 64, 56),        # sala lateral este
        rect(22, 47, 25, 48),        # pasillo sala lateral oeste -> central
        rect(47, 47, 50, 48),        # pasillo central -> sala lateral este
    ]


# --- spawns --------------------------------------------------------------------------------------

def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{X0 + cx}" centery="{Y0 + cy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def place_zone(walk, zone, groups, z, rng, avoid, min_gap=4):
    """Un <spawn> por bloque, con `per` monstruos. groups = [(name, blocks, per, spawntime)]."""
    pool = sorted((set(zone) & walk) - avoid)
    out, centers = [], []
    for name, blocks, per, st in groups:
        cands = [c for c in pool if all((c[0] + dx, c[1] + dy) in walk for dx in range(-2, 3) for dy in range(-2, 3))]
        rng.shuffle(cands)
        placed = 0
        for c in cands:
            if placed >= blocks:
                break
            if any(abs(c[0] - o[0]) + abs(c[1] - o[1]) < min_gap for o in centers):
                continue
            spots = [(c[0] + dx, c[1] + dy) for dx in range(-2, 3) for dy in range(-2, 3)
                     if (c[0] + dx, c[1] + dy) in walk and (c[0] + dx, c[1] + dy) not in avoid]
            if len(spots) < per + 2:
                continue
            rng.shuffle(spots)
            centers.append(c)
            out.append((c, z, [(name, s, st) for s in spots[:per]]))
            placed += 1
    return out


def write_preview(base: Path, layers):
    rd = Renderer()
    out = []
    for z, t in layers:
        used = [c for c, it in t.items() if it[0] not in (ROCK,)]
        x1 = min(x for x, _ in used) - 1
        x2 = max(x for x, _ in used) + 2
        y1 = min(y for _, y in used) - 1
        y2 = max(y for _, y in used) + 2
        w, h, img = rd.area({(x, y, z): it for (x, y), it in t.items()}, x1, y1, x2, y2, z)
        p = base.with_name(f"{base.name}-z{z}.png")
        p.write_bytes(png_bytes(w, h, bytes(img)))
        out.append(p)
    return out


# --- OTBM -----------------------------------------------------------------------------------------

def new_tile(x, y, bx, by, items, back_dest):
    props = bytearray([x - bx, y - by, 9]) + struct.pack("<H", items[0])
    return [T_TILE, props, [item_node(i, back_dest if i == TELEPORT else None) for i in items[1:]]]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path, help="prefijo: escribe <prefijo>-z7.png ... -z9.png")
    a = ap.parse_args()

    bl = Blocking()
    cells = {(x, y) for y in range(H) for x in range(W)}

    surf, info = build_surface(a.seed, bl)

    # sellar bolsillos de pasto inalcanzables (típico entre paredes de edificios vecinos)
    _walk7 = {c for c, it in surf.items() if bl.walkable(it)}
    _d7 = reach(_walk7, ARRIVAL)
    for c in _walk7 - set(_d7):
        if surf[c][0] == GRASS:
            surf[c] = [GRASS, FOREST_SMALL_TREE]

    t8, floor8 = build_dungeon(a.seed + 800, z8_floors(), cells, BRICK, GREY)
    t9, floor9 = build_dungeon(a.seed + 900, z9_floors(), cells, STONE_WALL, GREY)

    # escaleras: agujero arriba, escalera abajo (misma casilla; sube al norte)
    # bajada A (jungla norte) y B (oeste) -> z8
    t8[HOLE_NORTH] = [GREY, STAIRS_UP]
    t8[HOLE_WEST] = [GREY, STAIRS_UP]
    # bajada z8 -> z9 (centro de la cruz, 36,34)
    DOWN8 = (36, 34)
    t8[DOWN8] = [STAIR_DOWN]
    t9[DOWN8] = [GREY, STAIRS_UP]
    # portal de vuelta profundo en la sala central sur
    DEEP_PORTAL = (36, 51)
    t9[DEEP_PORTAL] = [GREY, TELEPORT]

    errors: list[str] = []

    # suelos de edificios: no deben quedar paredes con 0 piezas ni pisos con pieza de pared
    def floor_walk(t, floor):
        return {c for c in floor if bl.walkable(t[c])}

    walk7 = {c for c, it in surf.items() if bl.walkable(it)}
    d7 = reach(walk7, ARRIVAL)
    for label, c in [("entrada nave", (36, 47)), ("bajada norte", (HOLE_NORTH[0], HOLE_NORTH[1] + 1)),
                     ("bajada oeste", (HOLE_WEST[0], HOLE_WEST[1] + 1))]:
        if not any((c[0] + dx, c[1] + dy) in d7 for dx, dy in CARD + ((0, 0),)):
            errors.append(f"z7: {label} {c} no se alcanza desde la llegada")
    for label, cells in [("puerta nave", NAVE_DOOR), ("puerta oeste", WEST_DOOR_OUT),
                         ("puerta este", EAST_DOOR_OUT), ("puerta sur", SOUTH_DOOR)]:
        for c in cells:
            if c not in d7:
                errors.append(f"z7: {label} {c} no se alcanza")
    for c in (PORTAL_BACK,):
        if not any((c[0] + dx, c[1] + dy) in d7 for dx, dy in CARD):
            errors.append(f"z7: portal de vuelta {c} sin acceso")
    if set(d7) != walk7:
        errors.append(f"z7: {len(walk7) - len(d7)} casillas caminables aisladas")

    walk8 = floor_walk(t8, floor8)
    d8 = reach(walk8, (HOLE_NORTH[0], HOLE_NORTH[1] + 1))
    d8b = reach(walk8, (HOLE_WEST[0], HOLE_WEST[1] + 1))
    if (HOLE_WEST[0], HOLE_WEST[1] + 1) not in d8:
        errors.append("z8: la bajada oeste no se conecta con la norte")
    if (DOWN8[0], DOWN8[1] - 1) not in d8:
        errors.append("z8: la bajada al -2 no se alcanza")
    if len(d8) != len(walk8):
        errors.append(f"z8: {len(walk8) - len(d8)} casillas aisladas")

    walk9 = floor_walk(t9, floor9)
    d9 = reach(walk9, (DOWN8[0], DOWN8[1] + 1))
    if DEEP_PORTAL not in {c for c in walk9 if any((c[0] + dx, c[1] + dy) in d9 for dx, dy in CARD)}:
        errors.append("z9: el portal profundo no se alcanza")
    if len(d9) != len(walk9):
        errors.append(f"z9: {len(walk9) - len(d9)} casillas aisladas")

    # casillas de pared sin pieza única en la cripta
    for t, fl, label in ((t8, floor8, "z8"), (t9, floor9, "z9")):
        for c, it in t.items():
            if c in fl or it[0] == ROCK:
                continue
            if len(it) != 2:
                errors.append(f"{label} {c}: pared con {len(it) - 1} piezas")

    # que no se vea el borde de la caja
    for label, wk in (("z7", walk7), ("z8", walk8), ("z9", walk9)):
        for (x, y) in wk:
            if x < VIEW[0] or x > W - VIEW[0] - 1 or y < VIEW[1] or y > H - VIEW[1] - 1:
                errors.append(f"{label} {(x, y)}: se ve el borde de la caja")
                break

    # spawns
    rng = random.Random(a.seed + 99)
    avoid7 = grow({ARRIVAL, PORTAL_BACK, HOLE_NORTH, HOLE_WEST}, 2) | set(info["signs"])
    spawns7 = []
    spawns7 += place_zone(walk7, info["west"], [("Bandit", 2, 2, 70), ("Smuggler", 1, 2, 80), ("Wild Warrior", 1, 2, 90)], Z7, rng, avoid7)
    spawns7 += place_zone(walk7, info["east"], [("Bandit", 1, 2, 70), ("Wild Warrior", 1, 2, 90), ("Hunter", 1, 1, 120)], Z7, rng, avoid7)
    spawns7 += place_zone(walk7, info["south"], [("Smuggler", 1, 2, 80), ("Hunter", 1, 1, 120), ("Bandit", 1, 2, 70)], Z7, rng, avoid7)
    jungle7 = walk7 - info["nave"] - info["west"] - info["east"] - info["south"] - avoid7
    spawns7 += place_zone(jungle7, {c for c in jungle7 if c[1] < NAVE[1]},
                          [("Wild Warrior", 1, 2, 90), ("Hunter", 1, 1, 120), ("Bandit", 1, 2, 70)], Z7, rng, avoid7)

    avoid8 = grow({HOLE_NORTH, HOLE_WEST, DOWN8}, 2)
    spawns8 = []
    spawns8 += place_zone(walk8, rect(12, 14, 26, 26), [("Bandit", 2, 2, 80), ("Smuggler", 1, 2, 90)], Z8, rng, avoid8)
    spawns8 += place_zone(walk8, rect(12, 30, 26, 42), [("Wild Warrior", 2, 2, 90), ("Bandit", 1, 2, 80)], Z8, rng, avoid8)
    spawns8 += place_zone(walk8, rect(12, 46, 26, 58), [("Rotworm", 2, 2, 100), ("Skeleton", 1, 2, 110), ("Ghoul", 1, 1, 130)], Z8, rng, avoid8)
    spawns8 += place_zone(walk8, rect(42, 12, 56, 24), [("Slime", 2, 2, 100), ("Poison Spider", 1, 2, 110)], Z8, rng, avoid8)
    spawns8 += place_zone(walk8, rect(42, 28, 56, 40), [("Assassin", 1, 2, 130), ("Bandit", 1, 2, 80), ("Smuggler", 1, 2, 90)], Z8, rng, avoid8)
    spawns8 += place_zone(walk8, rect(42, 44, 56, 54), [("Bat", 1, 2, 90), ("Centipede", 1, 2, 110), ("Poison Spider", 1, 2, 110)], Z8, rng, avoid8)

    avoid9 = grow({DOWN8, DEEP_PORTAL}, 2)
    spawns9 = []
    spawns9 += place_zone(walk9, rect(24, 10, 48, 22), [("Monk", 2, 2, 120), ("Dark Monk", 1, 2, 140), ("Ghost", 1, 1, 160)], Z9, rng, avoid9)
    spawns9 += place_zone(walk9, rect(8, 26, 34, 40), [("Dark Monk", 1, 2, 140), ("Ghost", 1, 2, 160)], Z9, rng, avoid9)
    spawns9 += place_zone(walk9, rect(38, 26, 64, 40), [("Witch", 1, 2, 150), ("Hunter", 1, 1, 120), ("Dark Monk", 1, 2, 140)], Z9, rng, avoid9)
    spawns9 += place_zone(walk9, rect(24, 42, 48, 52), [("Mummy", 1, 2, 150), ("Witch", 1, 1, 150), ("Hunter", 1, 1, 120), ("Stone Golem", 1, 1, 160)], Z9, rng, avoid9)
    spawns9 += place_zone(walk9, rect(8, 44, 22, 56), [("Ghost", 1, 2, 160), ("Dark Monk", 1, 2, 140)], Z9, rng, avoid9)
    spawns9 += place_zone(walk9, rect(50, 44, 64, 56), [("Ghost", 1, 2, 160), ("Dark Monk", 1, 2, 140)], Z9, rng, avoid9)

    if a.preview:
        layers = [(Z7, {(X0 + x, Y0 + y): it for (x, y), it in surf.items()}),
                  (Z8, {(X0 + x, Y0 + y): it for (x, y), it in t8.items()}),
                  (Z9, {(X0 + x, Y0 + y): it for (x, y), it in t9.items()})]
        for p in write_preview(a.preview, layers):
            print(f"preview: {p}")

    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        return 1

    counts: dict = {}
    for s in (spawns7, spawns8, spawns9):
        for _c, _z, mons in s:
            for name, _p, _t in mons:
                counts[name] = counts.get(name, 0) + 1
    print(f"catedral x{X0}-{X0 + W - 1} y{Y0}-{Y0 + H - 1}: z7 {len(walk7)} pisables, "
          f"z8 {len(walk8)}, z9 {len(walk9)}; spawns {len(spawns7)}+{len(spawns8)}+{len(spawns9)} "
          f"({sum(counts.values())} monstruos)")
    print(f"llegada {X0 + ARRIVAL[0]},{Y0 + ARRIVAL[1]},7; portal vuelta {X0 + PORTAL_BACK[0]},{Y0 + PORTAL_BACK[1]},7; "
          f"bajadas {X0 + HOLE_NORTH[0]},{Y0 + HOLE_NORTH[1]},7 y {X0 + HOLE_WEST[0]},{Y0 + HOLE_WEST[1]},7; "
          f"bajada -2 {X0 + DOWN8[0]},{Y0 + DOWN8[1]},8; portal profundo {X0 + DEEP_PORTAL[0]},{Y0 + DEEP_PORTAL[1]},9")
    print("monstruos: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    # --- mapa: fuera la caja (re-ejecución) y adentro lo nuevo ---
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    md = root[2][0]
    backup = MAP.with_name(MAP.name + ".bak-darkcathedral")
    if not backup.exists():
        shutil.copy2(MAP, backup)

    def gone(gx, gy, z):
        return z in (Z7, Z8, Z9) and X0 <= gx < X0 + W and Y0 <= gy < Y0 + H

    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        area[2] = [t for t in area[2] if not (t[0] in (T_TILE, T_HOUSETILE) and gone(ax + t[1][0], ay + t[1][1], az))]
        if not area[2]:
            md[2].remove(area)
    all_new = {}
    for (x, y), it in surf.items():
        all_new[(X0 + x, Y0 + y, Z7)] = it
    for (x, y), it in t8.items():
        all_new[(X0 + x, Y0 + y, Z8)] = it
    for (x, y), it in t9.items():
        all_new[(X0 + x, Y0 + y, Z9)] = it
    buckets: dict = {}
    for (x, y, z), it in all_new.items():
        buckets.setdefault((x & ~0xFF, y & ~0xFF, z), []).append((x, y, it))
    for (bx, by, z), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, z)), []]
        for x, y, it in sorted(lst, key=lambda t: (t[1], t[0])):
            area[2].append(new_tile(x, y, bx, by, it, TEMPLE_BACK))
        md[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    # --- spawns ---
    sp = SPAWNS.read_text(encoding="latin-1")
    sp = re.sub(r"[ \t]*<!-- BEGIN DARK_CATHEDRAL_SPAWNS.*?<!-- END DARK_CATHEDRAL_SPAWNS -->\n?", "", sp, flags=re.S)
    sp = re.sub(r'[ \t]*<spawn centerx="(\d+)" centery="(\d+)" centerz="(\d+)"[^>]*>.*?</spawn>\n?',
                lambda m: "" if gone(int(m.group(1)), int(m.group(2)), int(m.group(3))) else m.group(0), sp, flags=re.S)
    block = "\t<!-- BEGIN DARK_CATHEDRAL_SPAWNS (scripts/map/generate-dark-cathedral.py) -->\n" + \
        spawn_xml(spawns7 + spawns8 + spawns9) + "\n\t<!-- END DARK_CATHEDRAL_SPAWNS -->\n"
    sp = sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")

    # --- carteles ---
    rd = READABLES.read_text(encoding="latin-1")
    rd = re.sub(r"\t?<!-- BEGIN DARK_CATHEDRAL_SIGNS -->.*?<!-- END DARK_CATHEDRAL_SIGNS -->\n?", "", rd, flags=re.S)
    lines = ["\t<!-- BEGIN DARK_CATHEDRAL_SIGNS -->"]
    for (x, y), t in sorted(info["signs"].items()):
        lines.append(f'\t<readable x="{X0 + x}" y="{Y0 + y}" z="7" text="{t.replace(chr(10), chr(92) + "n")}"/>')
    lines.append("\t<!-- END DARK_CATHEDRAL_SIGNS -->\n")
    rd = rd.replace("</readables>", "\n".join(lines) + "</readables>")
    READABLES.write_text(rd, encoding="latin-1")

    g = lambda c, z: {"x": X0 + c[0], "y": Y0 + c[1], "z": z}  # noqa: E731
    MANIFEST.write_text(json.dumps({
        "name": "generated-dark-cathedral", "seed": a.seed,
        "box": {"x1": X0, "y1": Y0, "x2": X0 + W - 1, "y2": Y0 + H - 1, "z": [Z7, Z8, Z9]},
        "landing": g(ARRIVAL, Z7),
        "portalsBack": [dict(g(PORTAL_BACK, Z7), to=list(TEMPLE_BACK)),
                        dict(g(DEEP_PORTAL, Z9), to=list(TEMPLE_BACK))],
        "holes": [dict(g(HOLE_NORTH, Z7), to=Z8), dict(g(HOLE_WEST, Z7), to=Z8), dict(g(DOWN8, Z8), to=Z9)],
        "stairs": [{"x": X0 + HOLE_NORTH[0], "y": Y0 + HOLE_NORTH[1], "z": Z8, "up": g((HOLE_NORTH[0], HOLE_NORTH[1] - 1), Z7)},
                   {"x": X0 + HOLE_WEST[0], "y": Y0 + HOLE_WEST[1], "z": Z8, "up": g((HOLE_WEST[0], HOLE_WEST[1] - 1), Z7)},
                   {"x": X0 + DOWN8[0], "y": Y0 + DOWN8[1], "z": Z9, "up": g((DOWN8[0], DOWN8[1] - 1), Z8)}],
        "zones": {
            "nave": dict(g((NAVE[0], NAVE[1]), Z7), x1=X0 + NAVE[2], y1=Y0 + NAVE[3]),
            "west": dict(g((WEST[0], WEST[1]), Z7), x1=X0 + WEST[2], y1=Y0 + WEST[3]),
            "east": dict(g((EAST[0], EAST[1]), Z7), x1=X0 + EAST[2], y1=Y0 + EAST[3]),
            "south": dict(g((SOUTH[0], SOUTH[1]), Z7), x1=X0 + SOUTH[2], y1=Y0 + SOUTH[3]),
        },
        "spawns": {"z7": len(spawns7), "z8": len(spawns8), "z9": len(spawns9), "monsters": sum(counts.values())},
        "monsters": dict(sorted(counts.items())),
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK carteles {READABLES}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
