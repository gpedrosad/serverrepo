#!/usr/bin/env python3
"""Paso del Norte: salida por la muralla norte de la ciudad y región nueva.

Uso (desde la raíz del repo):
  python3 scripts/map/generate-north-pass.py --dry-run --preview /tmp/paso.png   # solo valida y dibuja
  python3 scripts/map/generate-north-pass.py                                      # escribe el mapa
  python3 scripts/map/generate-north-pass.py --with-black-dragon                  # + spawns de Black Dragon

Qué hace (ver docs/items-and-map/MAPEAR_PASO_DEL_NORTE.md):
  Ciudad (z7, casillas existentes):
    - abre una puerta en la muralla norte (x 184-185, y 23-25) y un pasillo de piedra por dentro
      (x 185, y 26-33 y y 33, x 182-185) hasta el camino de tierra que baja al templo;
    - campo norte entero (x 116-213, y 0-22) como bosque cerrado, creando las casillas que faltaban
      en los bordes; solo queda caminable un claro alrededor del camino (x 180-189, y 12-22);
    - camino de tierra con bordes de pasto (x 184-185, y 12-22) y portal entre rocas (y 11) con
      cartel y faroles; la sala de trainers y el agua no se tocan;
    - pilar oeste de la puerta con pared y esquina (sin triángulo negro).
  Región nueva en zona vacía (x 370-469, y 236-467):
    - z7: llegada con portal de vuelta, bosque de pinos, línea de nieve, Tundra Helada con lago
      congelado y pie de la montaña con la escalera a las cuevas;
    - z8: Cuevas del Dragón;
    - z9: Nido Negro, con portal de vuelta a la puerta norte.
  Spawns en test-spawn.xml y carteles en readables.xml, en bloques NORTH_PASS (se reemplazan).

Es re-ejecutable: borra lo que haya en la caja de la región (z7-z9), rehace las casillas de la ciudad
que toca y reemplaza los bloques de spawns y carteles. Hace backup test.otbm.bak-northpass la
primera vez. Si test.otbm cambió en main, no mergear el binario: volver a correr este script.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import shutil
import struct
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kb"))
from mapdata import (DIRS, MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, Renderer, load_otb,  # noqa: E402
                     parse_tree, png_bytes, serialize_tree)

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MANIFEST = WORLD / "generated-north-pass.json"

# --- caja de la región (vacía en z7-z9 al crear el script, nov 2026) -------------------------
X0, Y0, W, H = 370, 236, 100, 232          # x 370-469, y 236-467
Z_SURFACE, Z_CAVES, Z_NEST = 7, 8, 9
BAND = 8                                  # franja exterior intransitable (tapa el vacío del borde)

# --- piezas (ids de servidor, ver docs/items-and-map/map-kb) ----------------------------------
GRASS, DIRT, SNOW, ICE, STONE_FLOOR = 4756, 103, 670, 671, 431
DIRT_SIDE = {"n": 111, "e": 112, "s": 110, "w": 113}            # pasto con borde de tierra (suelo)
DIRT_CORNER = {("n", "w"): 120, ("n", "e"): 121, ("s", "w"): 119, ("s", "e"): 118}
DIRT_INNER = {"nw": 116, "ne": 117, "sw": 115, "se": 114}
SNOW_SIDE = {"n": 4737, "e": 4738, "s": 4739, "w": 4740}        # borde de nieve (encima del suelo)
SNOW_CORNER = {("n", "w"): 4745, ("n", "e"): 4746, ("s", "w"): 4747, ("s", "e"): 4748}
SNOW_INNER = {"nw": 4741, "ne": 4742, "sw": 4743, "se": 4744}
SNOW_BORDERS = set(SNOW_SIDE.values()) | set(SNOW_CORNER.values()) | set(SNOW_INNER.values())

FOREST_TREES = (4009, 4009, 4009, 2700, 2707, 2701, 2708)        # pinos sobre todo (2x2, bloquean)
FOREST_SMALL_TREE = 2768                                          # pino chico 1x1
BUSHES = (2767, 2786)
FLOWERS = (4158, 4150, 2740)
MUSHROOMS = (4183, 4171, 4181)
LOGS = (4239, 4187, 4201)
SNOW_TREES = (2698, 2698, 2698, 2697)                             # pino nevado y árbol muerto nevado
DEAD_TREES = (2709, 2717, 2720)
STONE, RUBBLE_GREY, RUBBLE_BROWN, PEBBLES = 1285, 1309, 1323, 1336
ICE_SPIKE = 4995
BONES = (3125, 2248, 2320, 3121)
DRAGON_SKULL, DRAGON_BONES, HUMAN_SKELETON = 2247, 3122, 3133
CAMPFIRE, BRANCH, LANTERN, SIGN = 1423, 4224, 3744, 1429
TELEPORT, ATTR_TELE_DEST = 1387, 8
STAIR_DOWN, STAIRS_UP = 432, 1385                                 # 1385 sube hacia el norte
CITY_WALL_ITEMS = {1049, 1050, 1051}

# cueva (mismas reglas que generate-natural-island.py)
ROCK = 101
CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD = 351, 352, 355
CAVE_FLOORS = {CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD, STAIR_DOWN}
WALL_SIDE = {"s": 356, "n": 357, "e": 358, "w": 359}
WALL_CORNER = {("s", "e"): 364, ("s", "w"): 365, ("n", "w"): 366, ("n", "e"): 367}
WALL_INNER = {"se": 360, "sw": 361, "nw": 362, "ne": 363}

DIAG_SIDES = {"nw": ("n", "w"), "ne": ("n", "e"), "sw": ("s", "w"), "se": ("s", "e")}
CARD = ((1, 0), (-1, 0), (0, 1), (0, -1))
ALL8 = list(DIRS.values())

# --- ciudad -----------------------------------------------------------------------------------
GATE_XS = (184, 185)
GATE_YS = (23, 24, 25)
INNER_PATH = [(185, y) for y in range(26, 34)] + [(x, 33) for x in range(182, 185)] + [(184, 26), (184, 27)]
ROAD_YS = range(12, 23)                     # camino de tierra afuera, x 184-185
CITY_PORTALS = [(184, 11), (185, 11)]       # portal entre rocas al fondo del claro
CITY_LANDING = (184, 14)                    # donde se llega al volver
# Campo norte completo (nov 2026): todo bosque cerrado salvo un claro alrededor del camino. El
# portal quedó lejos del borde del mapa (y 0) y se crean las casillas que faltaban en los bordes,
# así desde el claro nunca se ve negro. El bosque separa el claro de la sala de trainers.
FIELD_BOX = (116, 0, 213, 22)
TRAINING_BOX = (133, 7, 160, 17)            # sala de trainers (cerco incluido): no se toca
CLEARING = (184.5, 17.5, 5.2, 6.2)          # elipse del claro: centro x, y y radios (x 180-189:
                                            # al este de la muralla, x 190+, hay campo abierto)
# pilar oeste de la puerta: pared vertical + esquina, si no queda un triángulo negro de montaña
GATE_PILLAR = {(183, 24): (919, [1049]), (183, 25): (919, [1053])}
VIEW = (8, 6)                               # media pantalla del cliente 7.6 (15x11 + 1 de margen)
PORTAL_ROCKS = [(183, 10), (186, 10), (183, 11), (186, 11)]
PORTAL_BACK = [(184, 10), (185, 10)]        # detrás del portal
FIELD_LANTERNS = [(183, 12), (186, 12)]
FIELD_SIGN = (187, 13)

# --- puntos de la región (coordenadas locales) ------------------------------------------------
ARRIVAL = (50, 216)
REGION_PORTALS = [(50, 220), (51, 220)]
SNOW_LINE = 112                             # ly < SNOW_LINE (con ondulación) = nieve
STAIRS = (50, 22)                           # bajada a las cuevas


class Noise:
    """Value noise 2D con octavas (igual que generate-natural-island.py)."""

    def __init__(self, seed: int):
        self.seed = seed

    def _h(self, x: int, y: int, o: int) -> float:
        n = (x * 374761393 + y * 668265263 + (self.seed + o * 1013) * 2147483647) & 0xFFFFFFFF
        n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 0xFFFF

    def _v(self, x: float, y: float, o: int) -> float:
        xi, yi = math.floor(x), math.floor(y)
        fx, fy = x - xi, y - yi
        sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a, b = self._h(xi, yi, o), self._h(xi + 1, yi, o)
        c, d = self._h(xi, yi + 1, o), self._h(xi + 1, yi + 1, o)
        return (a + (b - a) * sx) + ((c + (d - c) * sx) - (a + (b - a) * sx)) * sy

    def fbm(self, x: float, y: float, octaves=4, o=0) -> float:
        s, amp, f, norm = 0.0, 1.0, 1.0, 0.0
        for i in range(octaves):
            s += amp * self._v(x * f, y * f, o + i)
            norm += amp
            amp *= 0.5
            f *= 2.0
        return s / norm


# --- utilidades de bordes (mismas que la isla) ------------------------------------------------

def neighbors_in(mask, x, y) -> set[str]:
    return {d for d, (dx, dy) in DIRS.items() if (x + dx, y + dy) in mask}


def pieces_for(other: set[str], side, corner, inner) -> list[int] | None:
    card = other & {"n", "e", "s", "w"}
    if {"n", "s"} <= card or {"e", "w"} <= card:
        return None
    out = []
    if len(card) == 2:
        key = (next(c for c in card if c in "ns"), next(c for c in card if c in "ew"))
        out.append(corner[key])
    elif len(card) == 1:
        out.append(side[next(iter(card))])
    for diag, (a, b) in DIAG_SIDES.items():
        if diag in other and a not in card and b not in card:
            out.append(inner[diag])
    return out


def fix_until_valid(inner: set, cells: set, side, corner, inner_map, single=False) -> set:
    """Agranda `inner` hasta que toda casilla vecina tenga pieza (y saca celdas de 1 de ancho).
    Solo revisa el contorno de `inner`, que es lo único que puede cambiar."""
    inner = set(inner)
    for _ in range(400):
        changed = False
        for (x, y) in list(inner):
            out = {d for d, (dx, dy) in DIRS.items() if (x + dx, y + dy) not in inner}
            if {"n", "s"} <= out or {"e", "w"} <= out:
                inner.discard((x, y))
                changed = True
        ring = {(x + dx, y + dy) for (x, y) in inner for dx, dy in ALL8} - inner
        for c in ring:
            if c not in cells:
                continue
            pcs = pieces_for(neighbors_in(inner, *c), side, corner, inner_map)
            if pcs is None or (single and len(pcs) > 1):
                inner.add(c)
                changed = True
        if not changed:
            return inner
    raise RuntimeError("los bordes no convergen")


def reach(walk: set, start, steps=ALL8) -> dict:
    """BFS: casilla -> distancia."""
    dist = {start: 0}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in steps:
            n = (x + dx, y + dy)
            if n in walk and n not in dist:
                dist[n] = dist[(x, y)] + 1
                q.append(n)
    return dist


class Blocking:
    def __init__(self):
        self.otb = load_otb()

    def blocks(self, sid: int) -> bool:
        return "block_solid" in self.otb.get(sid, {}).get("flags", [])

    def walkable(self, items: list[int]) -> bool:
        return bool(items) and not any(self.blocks(i) for i in items)


# --- superficie ---------------------------------------------------------------------------------

def build_surface(seed: int, bl: Blocking):
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

    # camino: línea serpenteante de la llegada a la escalera (2 de ancho)
    center = {}
    for y in range(STAIRS[1], ARRIVAL[1] + 1):
        t = (y - STAIRS[1]) / (ARRIVAL[1] - STAIRS[1])
        base = STAIRS[0] + (ARRIVAL[0] - STAIRS[0]) * t
        center[y] = int(round(base + 13 * math.sin(y / 21.0) * math.sin(math.pi * t) + 4 * (nz.fbm(0, y / 9, 2, 11) - 0.5)))
    path = set()
    for y, cx in center.items():
        for dx in (0, 1):
            path.add((cx + dx, y))
        if y + 1 in center:  # sin saltos diagonales
            nx = center[y + 1]
            for x in range(min(cx, nx), max(cx, nx) + 2):
                path.add((x, y))
    path |= {(ARRIVAL[0] + dx, ARRIVAL[1] + dy) for dx in (-1, 0, 1, 2) for dy in (0, 1, 2, 3)}
    portal_zone = {(x, y) for x in range(REGION_PORTALS[0][0] - 2, REGION_PORTALS[1][0] + 3)
                   for y in range(ARRIVAL[1], REGION_PORTALS[0][1] + 3)}
    play |= path | portal_zone

    # nieve al norte de una línea ondulada
    snow = {(x, y) for (x, y) in cells if y < SNOW_LINE + 6 * (nz.fbm(x / 14, 0, 3, 21) - 0.5) * 2}
    snow = fix_until_valid(snow, cells, SNOW_SIDE, SNOW_CORNER, SNOW_INNER)

    # tierra del camino solo en la parte con pasto (en la nieve el camino es nieve pisada)
    dirt = {c for c in path if c not in snow and c[1] < ARRIVAL[1] + 4}
    grass_cells = cells - snow
    dirt = fix_until_valid(dirt, grass_cells, DIRT_SIDE, DIRT_CORNER, DIRT_INNER, single=True)
    # una casilla con borde de tierra no puede tener además borde de nieve combinado raro: se acepta
    # (el borde de nieve va encima del suelo, el de tierra es el suelo)

    # lago congelado en la tundra
    lake_c = (72, 70)
    lake = {(x, y) for (x, y) in cells & play if y < SNOW_LINE - 14
            and ((x - lake_c[0]) / 11) ** 2 + ((y - lake_c[1]) / 8) ** 2 + 0.5 * (nz.fbm(x / 4, y / 4, 2, 31) - 0.5) < 1}
    lake -= path

    tiles: dict[tuple[int, int], list[int]] = {}
    for c in cells:
        x, y = c
        if c in snow:
            tiles[c] = [ICE if c in lake else SNOW]
        elif c in dirt:
            tiles[c] = [DIRT]
        else:
            edge = pieces_for(neighbors_in(dirt, x, y), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
            tiles[c] = [edge[0]] if edge else [GRASS]
        if c not in snow:
            sb = pieces_for(neighbors_in(snow, x, y), SNOW_SIDE, SNOW_CORNER, SNOW_INNER)
            if sb:
                tiles[c] += sb

    occupied: set = set()

    def free(c, r=0):
        return all((c[0] + dx, c[1] + dy) not in occupied for dx in range(-r, r + 1) for dy in range(-r, r + 1))

    def put(c, item, size=1):
        tiles[c].append(item)
        for dx in range(size):
            for dy in range(size):
                occupied.add((c[0] - dx, c[1] - dy))

    # puntos clave libres de todo
    keep_clear = set(path) | {(STAIRS[0] + dx, STAIRS[1] + dy) for dx in range(-2, 3) for dy in range(-2, 3)}
    keep_clear |= {(ARRIVAL[0] + dx, ARRIVAL[1] + dy) for dx in range(-3, 4) for dy in range(-3, 6)} | portal_zone
    occupied |= keep_clear

    # 1) franja exterior: cada casilla lleva un bloqueo 1x1 y encima, cada dos, un árbol grande
    band = sorted(cells - play, key=lambda c: (c[1], c[0]))
    for c in band:
        in_snow = c in snow
        tiles[c].append(rng.choice((ICE_SPIKE, STONE) if in_snow else (FOREST_SMALL_TREE,) + BUSHES))
        occupied.add(c)
    for c in band:
        x, y = c
        if x % 2 == 1 and y % 2 == 1:
            tiles[c].append(rng.choice(SNOW_TREES if c in snow else FOREST_TREES))

    # 2) campamento de cazadores junto al camino, en el bosque
    camp_y = 175
    camp = (center[camp_y] + 5, camp_y)
    camp_items = {camp: CAMPFIRE, (camp[0] - 1, camp[1] + 1): LOGS[1], (camp[0] + 1, camp[1] - 1): LOGS[2],
                  (camp[0] + 1, camp[1] + 1): BRANCH, (camp[0] - 1, camp[1] - 1): LOGS[0]}
    for c, it in camp_items.items():
        if c in play and c not in path:
            put(c, it)
    occupied |= {(camp[0] + dx, camp[1] + dy) for dx in range(-3, 4) for dy in range(-3, 4)}

    # 3) interior: arboledas por ruido, arbustos, flores, hongos; en la tundra pinos nevados y piedras
    for c in sorted(play, key=lambda c: (c[1], c[0])):
        x, y = c
        if c in occupied or len(tiles[c]) > 1 or c in lake:
            continue
        in_snow = c in snow
        near_lake = in_snow and any((x + dx, y + dy) in lake for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        r = rng.random()
        grove = nz.fbm(x / 7, y / 7, 3, 500)
        if near_lake:
            if r < 0.22 and free(c):
                put(c, ICE_SPIKE)
            continue
        if not in_snow:
            if grove > 0.55 and r < 0.6 and free(c, 2):
                put(c, rng.choice(FOREST_TREES), 2)
            elif grove > 0.45 and r < 0.08 and free(c):
                put(c, FOREST_SMALL_TREE)
            elif r < 0.025 and free(c):
                put(c, rng.choice(BUSHES))
            elif r < 0.06:
                tiles[c].append(rng.choice(FLOWERS))
            elif r < 0.075:
                tiles[c].append(rng.choice(MUSHROOMS))
            elif r < 0.08:
                tiles[c].append(rng.choice(LOGS))
        else:
            north = y < 40  # pie de la montaña: piedras, huesos de dragón
            if north:
                rocky = nz.fbm(x / 5, y / 5, 2, 700)  # piedras agrupadas, no salpicadas
                if rocky > 0.62 and r < 0.35 and free(c, 1):
                    put(c, RUBBLE_GREY, 2)
                elif rocky > 0.55 and r < 0.12 and free(c):
                    put(c, STONE)
                elif r < 0.035:
                    tiles[c].append(rng.choice(BONES + (PEBBLES,)))
                elif r < 0.04 and free(c):
                    put(c, DRAGON_BONES)
                elif r < 0.044:
                    tiles[c].append(DRAGON_SKULL)
            elif grove > 0.55 and r < 0.5 and free(c, 2):
                put(c, rng.choice(SNOW_TREES), 2)
            elif r < 0.02 and free(c):
                put(c, rng.choice((STONE, ICE_SPIKE)))
            elif r < 0.03 and free(c, 1):
                put(c, rng.choice(DEAD_TREES), 2)
            elif r < 0.04:
                tiles[c].append(rng.choice(BONES + (PEBBLES, BRANCH)))

    # 4) faroles a lo largo del camino en la tundra (guían en la nieve)
    for y in range(STAIRS[1] + 6, SNOW_LINE, 12):
        c = (center[y] - 2, y)
        if c in play and c not in path and len(tiles[c]) == 1 and free(c):
            put(c, LANTERN)

    # 5) escalera con marco de piedras (abierta al norte y al sur: 1385 sube hacia el norte)
    tiles[STAIRS] = [STAIR_DOWN]
    for dx, dy in ((-2, -1), (-2, 0), (-2, 1), (2, -1), (2, 1), (-1, -2), (1, -2), (-1, 2), (1, 2)):
        c = (STAIRS[0] + dx, STAIRS[1] + dy)
        tiles[c] = [tiles[c][0], STONE]
    tiles[(STAIRS[0] - 1, STAIRS[1] + 1)] = [tiles[(STAIRS[0] - 1, STAIRS[1] + 1)][0], DRAGON_SKULL]
    # portales de vuelta, enmarcados con piedras 1x1 (las de 2x2 los tapan al dibujarse)
    for c in REGION_PORTALS:
        tiles[c] = [tiles[c][0], TELEPORT]
    px0, px1, py = REGION_PORTALS[0][0], REGION_PORTALS[1][0], REGION_PORTALS[0][1]
    for c in ((px0 - 1, py), (px1 + 1, py), (px0 - 1, py + 1), (px1 + 1, py + 1), (px0, py + 1), (px1, py + 1)):
        tiles[c] = [tiles[c][0], STONE]
    for c in ((px0 - 2, py - 1), (px1 + 2, py - 1)):
        tiles[c] = [tiles[c][0], LANTERN]
    signs = {
        (ARRIVAL[0] + 2, ARRIVAL[1] - 1): "PASO DEL NORTE\nNorte: Tundra Helada y Cuevas del Dragon.\nPortal al sur: Retro76.",
        (center[SNOW_LINE + 4] + 3, SNOW_LINE + 4): "TUNDRA HELADA\nLobos de invierno, osos polares y trolls.\nDicen que un yeti ronda el lago.",
        (STAIRS[0] + 2, STAIRS[1]): "CUEVAS DEL DRAGON\nSolo para cazadores experimentados.",
        (camp[0] + 2, camp[1] - 2): "Campamento de cazadores.\nDescansa junto al fuego.",
    }
    for c, _t in signs.items():
        tiles[c] = [tiles[c][0], SIGN]

    return tiles, {"path": path, "snow": snow, "dirt": dirt, "lake": lake, "play": play, "signs": signs,
                   "camp": camp, "center": center}


# --- cuevas -------------------------------------------------------------------------------------

def carve_cave(seed: int, allowed: set, core: set, start, min_size: int):
    """Cueva en una grilla de bloques 2x2 que después se amplía: todo pasillo y toda pared quedan de
    2 de ancho como mínimo, así cada roca que toca piso tiene una única pieza de pared válida.
    (El ajuste casilla a casilla de la isla oscila en cuevas grandes.)"""
    ox, oy = start[0] % 2, start[1] % 2
    blk = lambda c: ((c[0] - ox) // 2, (c[1] - oy) // 2)  # noqa: E731
    cells_of = lambda b: {(ox + 2 * b[0] + i, oy + 2 * b[1] + j) for i in (0, 1) for j in (0, 1)}  # noqa: E731
    allowed_b = {b for b in {blk(c) for c in allowed} if cells_of(b) <= allowed}
    # un bloque de margen: la pared de afuera también debe caber en la caja
    allowed_b = {b for b in allowed_b if all((b[0] + dx, b[1] + dy) in allowed_b for dx, dy in ALL8)}
    core_b = {blk(c) for c in core}
    start_b = blk(start)
    for attempt in range(80):
        rng = random.Random(seed * 1000 + attempt)
        floor = {b for b in allowed_b if rng.random() < 0.55} | core_b
        for _ in range(5):  # autómata celular clásico de cuevas, a escala de bloques
            nxt = set(core_b)
            for b in allowed_b:
                walls = sum(1 for dx, dy in ALL8 if (b[0] + dx, b[1] + dy) not in floor)
                if walls <= 3 or (b in floor and walls <= 4):
                    nxt.add(b)
            floor = nxt
        floor = set(reach(floor, start_b, CARD))
        # sin contactos solo en diagonal: se rellena uno de los dos bloques del costado
        changed = True
        while changed:
            changed = False
            for (x, y) in sorted(floor):
                for dx, dy in ((1, 1), (1, -1)):
                    d = (x + dx, y + dy)
                    a, b2 = (x + dx, y), (x, y + dy)
                    if d in floor and a not in floor and b2 not in floor:
                        fill = a if a in allowed_b else b2 if b2 in allowed_b else None
                        if fill is None:
                            floor.discard(d)
                        else:
                            floor.add(fill)
                        changed = True
        floor = set(reach(floor, start_b, CARD))
        fine = set().union(*(cells_of(b) for b in floor))
        if len(fine) >= min_size and core <= fine:
            return fine
    raise RuntimeError("no salió una cueva suficientemente grande")


def cave_tiles(floor: set, box: set, seed: int, mud_bias=0.0) -> dict:
    nz = Noise(seed + 909)
    tiles = {}
    for c in box:
        x, y = c
        if c in floor:
            v = nz.fbm(x / 5, y / 5, 3, 10) + mud_bias
            tiles[c] = [CAVE_MUD if v > 0.66 else CAVE_FLOOR_ALT if v < 0.36 else CAVE_FLOOR]
            continue
        wall = pieces_for(neighbors_in(floor, x, y), WALL_SIDE, WALL_CORNER, WALL_INNER)
        tiles[c] = [wall[0]] if wall else [ROCK]
    return tiles


def build_caves(seed: int):
    sx, sy = STAIRS
    # z8: Cuevas del Dragón, debajo de la tundra
    box8 = {(x, y) for x in range(4, W - 4) for y in range(4, 150)}
    allowed8 = {(x, y) for x in range(6, W - 6) for y in range(6, 148)}
    core8 = {(sx + dx, sy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1, 2)}
    floor8 = carve_cave(seed + 1, allowed8, core8, (sx, sy + 1), 2500)
    t8 = cave_tiles(floor8, box8, seed + 1)
    t8[(sx, sy)].append(STAIRS_UP)
    d8 = reach(floor8, (sx, sy + 1), CARD)
    # bajada al Nido: casilla lejana con 3x3 de piso y 1 más al norte y al sur
    cands = [c for c in floor8 if all((c[0] + dx, c[1] + dy) in floor8 for dx in (-1, 0, 1) for dy in (-2, -1, 0, 1, 2))]
    down = max(cands, key=lambda c: d8[c])
    t8[down] = [STAIR_DOWN]

    # z9: Nido Negro, centrado bajo la bajada
    dx0, dy0 = down
    box9 = {(x, y) for x in range(max(4, dx0 - 34), min(W - 4, dx0 + 35)) for y in range(max(4, dy0 - 34), min(H - 4, dy0 + 35))}
    # 8 de roca alrededor como mínimo: que no se vea el vacío desde el piso
    allowed9 = {(x, y) for (x, y) in box9 if min(x - min(c[0] for c in box9), max(c[0] for c in box9) - x,
                                                  y - min(c[1] for c in box9), max(c[1] for c in box9) - y) >= 8}
    core9 = {(dx0 + dx, dy0 + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1, 2)}
    floor9 = carve_cave(seed + 2, allowed9, core9, (dx0, dy0 + 1), 900)
    t9 = cave_tiles(floor9, box9, seed + 2, mud_bias=0.18)  # más barro: más oscuro
    t9[down].append(STAIRS_UP)
    d9 = reach(floor9, (dx0, dy0 + 1), CARD)
    portal_cands = [c for c in floor9 if all((c[0] + ddx, c[1] + ddy) in floor9 for ddx in (-1, 0, 1) for ddy in (-1, 0, 1))]
    nest_portal = max(portal_cands, key=lambda c: d9[c])
    t9[nest_portal].append(TELEPORT)
    return {"t8": t8, "floor8": floor8, "d8": d8, "down": down, "t9": t9, "floor9": floor9, "d9": d9,
            "nest_portal": nest_portal}


def decorate_cave(tiles: dict, floor: set, start, keep: set, seed: int, bones_rate: float, bl: Blocking):
    """Piedras y huesos sin cortar el paso (se prueba cada bloqueo)."""
    rng = random.Random(seed + 4242)
    walk = set(floor)
    base = len(reach(walk, start, CARD))
    for c in sorted(floor, key=lambda c: (c[1], c[0])):
        if c in keep or len(tiles[c]) > 1 or tiles[c][0] == STAIR_DOWN:
            continue
        x, y = c
        rock_n = 8 - len(neighbors_in(floor, x, y))
        r = rng.random()
        if rock_n >= 3 and r < 0.10:
            item = rng.choice((RUBBLE_GREY, RUBBLE_BROWN, STONE))
            if len(reach(walk - {c}, start, CARD)) == base - 1:
                tiles[c].append(item)
                walk.discard(c)
                base -= 1
        elif r < 0.02:
            tiles[c].append(PEBBLES)
        elif r < 0.02 + bones_rate:
            tiles[c].append(rng.choice(BONES + (DRAGON_SKULL,)))
        elif r < 0.02 + bones_rate * 1.15 and rock_n >= 2:
            if len(reach(walk - {c}, start, CARD)) == base - 1:
                tiles[c].append(rng.choice((DRAGON_BONES, HUMAN_SKELETON)))
                if bl.blocks(tiles[c][-1]):
                    walk.discard(c)
                    base -= 1


# --- spawns -------------------------------------------------------------------------------------

def place_spawns(groups, walk: set, avoid: set, z: int, rng: random.Random, min_gap=9, region_filter=None):
    """groups: lista de (nombre, cantidad_de_spawns, monstruos_por_spawn, spawntime, filtro)."""
    out, centers = [], []
    pool = sorted(walk - avoid)
    for name, count, per, spawntime, filt in groups:
        cands = [c for c in pool if filt(c)]
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
    return out


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        gx, gy = X0 + cx, Y0 + cy
        lines.append(f'\t<spawn centerx="{gx}" centery="{gy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


# --- edición del OTBM ---------------------------------------------------------------------------

def tile_ground_and_items(tile, otb) -> tuple[int | None, list]:
    """(ground, children sin el ground) de un nodo TILE existente."""
    p = bytes(tile[1])
    pos = 2 + (4 if tile[0] == T_HOUSETILE else 0)
    ground = None
    while pos < len(p):
        a = p[pos]
        if a == 3:
            pos += 5
        elif a == 9:
            ground = struct.unpack_from("<H", p, pos + 1)[0]
            pos += 3
        else:
            break
    children = list(tile[2])
    if ground is None and children and children[0][0] == T_ITEM:
        first = struct.unpack_from("<H", bytes(children[0][1]), 0)[0]
        if otb.get(first, {}).get("group") == "ground":
            ground = first
            children = children[1:]
    return ground, children


def rebuild_tile_props(tile, ground: int) -> bytearray:
    p = bytes(tile[1])
    head = 2 + (4 if tile[0] == T_HOUSETILE else 0)
    out = bytearray(p[:head])
    pos = head
    while pos < len(p):
        a = p[pos]
        if a == 3:
            out += p[pos:pos + 5]
            pos += 5
        elif a == 9:
            pos += 3
        else:
            break
    out += bytes([9]) + struct.pack("<H", ground)
    return out


# Items apilables según items-zagan-test.otb: el server exige su byte de cantidad o no carga el mapa
# (ver scripts/map/check-map-load.py). 2320 = calavera.
NEEDS_COUNT = {2320}


def item_node(iid: int, tele=None):
    props = bytearray(struct.pack("<H", iid))
    if iid in NEEDS_COUNT:
        props.append(1)
    if tele:
        props += bytes([ATTR_TELE_DEST]) + struct.pack("<HHB", *tele)
    return [T_ITEM, props, []]


def new_tile_node(x: int, y: int, bx: int, by: int, items: list[int], tele=None):
    props = bytearray([x - bx, y - by, 9]) + struct.pack("<H", items[0])
    return [T_TILE, props, [item_node(i, tele if i == TELEPORT else None) for i in items[1:]]]


def build_north_field(index, otb, bl, city, road, seed, errors):
    """Campo norte: bosque cerrado con un claro alrededor del camino y el portal entre rocas.

    Escribe en `city` las casillas existentes que cambian y devuelve las que hay que crear
    ({(x, y): [suelo, ítems...]}). Valida: bordes de tierra, que desde cualquier casilla caminable la
    pantalla entera tenga casillas, y que el claro solo salga a la ciudad por la puerta."""
    rng = random.Random(seed + 404)
    fx1, fy1, fx2, fy2 = FIELD_BOX
    tx1, ty1, tx2, ty2 = TRAINING_BOX
    cx, cy, rx, ry = CLEARING
    water_or_kept = set()
    field = set()
    for x in range(fx1, fx2 + 1):
        for y in range(fy1, fy2 + 1):
            if tx1 <= x <= tx2 and ty1 <= y <= ty2:
                continue
            ex = index.get((x, y, 7))
            if ex is not None:
                if ex[1][0] == T_HOUSETILE:
                    water_or_kept.add((x, y))
                    continue
                g, its = tile_ground_and_items(ex[1], otb)
                ids = [g] + [struct.unpack_from("<H", bytes(c[1]), 0)[0] for c in its if c[0] == T_ITEM]
                if any("water" in (otb.get(i, {}).get("name") or "") for i in ids):  # agua y orillas
                    water_or_kept.add((x, y))
                    continue
            field.add((x, y))

    clearing = {c for c in field if c[1] >= ROAD_YS.start
                and ((c[0] - cx) / rx) ** 2 + ((c[1] - cy) / ry) ** 2 <= 1.0}
    clearing |= road
    portal_ext = set(CITY_PORTALS)
    dirt = road | portal_ext
    blocked_deco = set(PORTAL_ROCKS) | set(PORTAL_BACK) | set(FIELD_LANTERNS) | {FIELD_SIGN}
    forest = field - clearing - portal_ext - blocked_deco

    def ground_for(c):
        if c in dirt:
            return DIRT
        edge = pieces_for(neighbors_in(dirt, *c), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
        if edge is None or len(edge) > 1:
            errors.append(f"campo norte {c}: borde de tierra sin pieza simple")
            return GRASS
        return edge[0] if edge else GRASS

    def dist_to_clearing(c):
        return min(max(abs(c[0] - o[0]), abs(c[1] - o[1])) for o in clearing)

    big_trees = (4009, 4009, 4009, 2700, 2701, 2707, 2708, 2702)
    items = {}
    for c in sorted(forest):
        near = dist_to_clearing(c) if abs(c[0] - cx) < rx + 4 and abs(c[1] - cy) < ry + 4 else 99
        behind_portal = 180 <= c[0] <= 189 and c[1] <= 9
        r = rng.random()
        if near == 1:                                   # borde del claro: más bajo y variado
            it = rng.choice(BUSHES) if r < 0.45 else FOREST_SMALL_TREE if r < 0.8 else rng.choice(big_trees)
        elif behind_portal and r < 0.35:                # loma de piedras detrás del portal
            it = rng.choice((STONE, RUBBLE_GREY))
        else:
            it = rng.choice(big_trees) if r < 0.72 else FOREST_SMALL_TREE if r < 0.9 else rng.choice(BUSHES)
        items[c] = [it]
    for c in clearing - road:                           # pasto del claro con flores y hongos al borde
        r = rng.random()
        edge = any((c[0] + dx, c[1] + dy) in forest for dx, dy in CARD)
        if edge and r < 0.3:
            items[c] = [rng.choice(FLOWERS + MUSHROOMS)]
        elif r < 0.07:
            items[c] = [rng.choice(FLOWERS)]
        else:
            items[c] = []
    for c in road:
        items[c] = []
    for c in PORTAL_ROCKS:
        items[c] = [STONE]
    for c in PORTAL_BACK:
        items[c] = [RUBBLE_GREY]
    for c in FIELD_LANTERNS:
        items[c] = [LANTERN]
    items[FIELD_SIGN] = [SIGN]
    for c in CITY_PORTALS:
        items[c] = [TELEPORT]

    new = {}
    for c, it in items.items():
        tile = [ground_for(c)] + it
        if (c[0], c[1], 7) in index:
            city[c] = (tile[0], tile[1:])
        else:
            new[c] = tile

    # --- validaciones ---
    walk = {c for c, it in items.items() if bl.walkable([ground_for(c)] + it)}
    if not walk <= clearing | portal_ext:
        errors.append(f"campo norte: casillas caminables fuera del claro {sorted(walk - clearing - portal_ext)[:5]}")
    # el claro solo sale del campo por la puerta de la ciudad
    for (x, y) in walk:
        for dx, dy in ALL8:
            n = (x + dx, y + dy)
            if fx1 <= n[0] <= fx2 and fy1 <= n[1] <= fy2:
                continue
            if n[1] > fy2 and n[0] in GATE_XS:
                continue
            ex = index.get((n[0], n[1], 7))
            if ex is not None:
                g, its = tile_ground_and_items(ex[1], otb)
                ids = [struct.unpack_from("<H", bytes(c[1]), 0)[0] for c in its if c[0] == T_ITEM]
                if bl.walkable([g] + ids):
                    errors.append(f"campo norte: el claro sale por {n} (no es la puerta)")
    exists = {k[:2] for k in index if k[2] == 7} | set(new)
    vx, vy = VIEW
    for (x, y) in walk | road:
        for dx in range(-vx, vx + 1):
            for dy in range(-vy, vy + 1):
                if (x + dx, y + dy) not in exists:
                    errors.append(f"campo norte: desde {(x, y)} se vería negro en {(x + dx, y + dy)}")
                    break
            else:
                continue
            break
    if any(tx1 - 7 <= x <= tx2 + 7 and ty1 - 7 <= y <= ty2 + 7 for x, y in walk):
        errors.append("campo norte: el claro queda a menos de 8 casillas de la sala de trainers")
    return new


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=31)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--with-black-dragon", action="store_true",
                    help="agrega spawns de Black Dragon en el Nido (solo con el cliente actualizado, look 230)")
    ap.add_argument("--preview", type=Path, help="minimapa de los 3 pisos de la región + ciudad (PNG)")
    a = ap.parse_args()

    bl = Blocking()
    otb = bl.otb
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    mapdata_node = root[2][0]

    # índice de casillas existentes
    index = {}
    for area in mapdata_node[2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        for tile in area[2]:
            if tile[0] in (T_TILE, T_HOUSETILE):
                index[(ax + tile[1][0], ay + tile[1][1], az)] = (area, tile, ax, ay)

    # --- superficie, cuevas y validaciones locales ---
    surf, info = build_surface(a.seed, bl)
    caves = build_caves(a.seed)
    sx, sy = STAIRS
    decorate_cave(caves["t8"], caves["floor8"], (sx, sy + 1),
                  {(sx + dx, sy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1, 2)}
                  | {(caves["down"][0] + dx, caves["down"][1] + dy) for dx in (-1, 0, 1) for dy in (-2, -1, 0, 1, 2)},
                  a.seed + 1, 0.015, bl)
    dn = caves["down"]
    npx, npy = caves["nest_portal"]
    decorate_cave(caves["t9"], caves["floor9"], (dn[0], dn[1] + 1),
                  {(dn[0] + dx, dn[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1, 2)}
                  | {(npx + dx, npy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)},
                  a.seed + 2, 0.06, bl)

    errors = []

    def check_borders(tiles, mask, side, corner, inner, is_ground_piece, label):
        allp = set(side.values()) | set(corner.values()) | set(inner.values())
        for c, it in tiles.items():
            if c in mask:
                continue
            want = pieces_for(neighbors_in(mask, *c), side, corner, inner)
            have = [i for i in it if i in allp]
            if want is None:
                errors.append(f"{label} {c}: combinación sin pieza")
            elif sorted(want) != sorted(have):
                if not (is_ground_piece and not want and not have):
                    errors.append(f"{label} {c}: quiere {want} tiene {have}")

    check_borders(surf, info["snow"], SNOW_SIDE, SNOW_CORNER, SNOW_INNER, False, "nieve")
    check_borders({c: it for c, it in surf.items() if c not in info["snow"]}, info["dirt"],
                  DIRT_SIDE, DIRT_CORNER, DIRT_INNER, True, "tierra")

    walk7 = {c for c, it in surf.items() if bl.walkable(it)}
    d7 = reach(walk7, ARRIVAL)
    if (sx, sy - 1) not in d7 or (sx, sy + 1) not in d7:
        errors.append("la escalera a las cuevas no se alcanza desde la llegada")
    for c in REGION_PORTALS:
        if not any((c[0] + dx, c[1] + dy) in d7 for dx, dy in CARD):
            errors.append(f"portal {c} sin acceso")
    walk8 = {c for c, it in caves["t8"].items() if bl.walkable(it) and it[0] in CAVE_FLOORS}
    if dn not in reach(walk8, (sx, sy + 1), CARD):
        errors.append("la bajada al Nido no se alcanza en z8")
    walk9 = {c for c, it in caves["t9"].items() if bl.walkable(it) and it[0] in CAVE_FLOORS}
    d9w = reach(walk9, (dn[0], dn[1] + 1), CARD)
    if not any((npx + dx, npy + dy) in d9w for dx, dy in CARD):
        errors.append("el portal del Nido no se alcanza")
    for t, label in ((caves["t8"], "z8"), (caves["t9"], "z9")):
        fl = {c for c, it in t.items() if it[0] in CAVE_FLOORS}
        for c, it in t.items():
            if c in fl:
                continue
            want = pieces_for(neighbors_in(fl, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
            if want is None or len(want) > 1 or (want and it[0] != want[0]) or (not want and it[0] != ROCK):
                errors.append(f"pared {label} {c}: quiere {want} tiene {it[0]}")

    # --- ciudad: casillas a reescribir ---
    city: dict[tuple[int, int], tuple[int | None, list[int] | None]] = {}  # (ground, items|None=conservar)
    for x in GATE_XS:
        for y in GATE_YS:
            city[(x, y)] = (STONE_FLOOR, [])
    for c in INNER_PATH:
        city[c] = (STONE_FLOOR, [])
    road = {(x, y) for x in GATE_XS for y in ROAD_YS}
    field_new = build_north_field(index, otb, bl, city, road, a.seed, errors)
    city.update(GATE_PILLAR)
    # comprobaciones de la ciudad sobre el estado actual (o ya generado)
    for (x, y) in list(city):
        ex = index.get((x, y, 7))
        if ex is None:
            if (x, y) not in field_new:
                errors.append(f"ciudad {(x, y)}: casilla inexistente")
        elif ex[1][0] == T_HOUSETILE:
            errors.append(f"ciudad {(x, y)}: es casa, no se toca")

    city_portal_dest = (X0 + ARRIVAL[0], Y0 + ARRIVAL[1], 7)
    back_dest = (CITY_LANDING[0], CITY_LANDING[1], 7)

    # --- spawns ---
    rng = random.Random(a.seed + 77)
    avoid7 = set(info["path"]) | {(ARRIVAL[0] + dx, ARRIVAL[1] + dy) for dx in range(-12, 13) for dy in range(-12, 13)} \
        | {(sx + dx, sy + dy) for dx in range(-4, 5) for dy in range(-4, 5)} \
        | {(info["camp"][0] + dx, info["camp"][1] + dy) for dx in range(-6, 7) for dy in range(-6, 7)}
    snow, lake = info["snow"], info["lake"]
    forest = lambda c: c not in snow and c[1] < ARRIVAL[1] - 10  # noqa: E731
    near_snow = lambda c: c not in snow and c[1] < SNOW_LINE + 30  # noqa: E731
    tundra = lambda c: c in snow and 40 <= c[1]  # noqa: E731
    lakeside = lambda c: c in snow and any((c[0] + dx, c[1] + dy) in lake for dx in range(-4, 5) for dy in range(-4, 5))  # noqa: E731
    foot = lambda c: c in snow and c[1] < 40  # noqa: E731
    spawns7 = place_spawns([
        ("Wolf", 7, 3, 120, forest),
        ("Bear", 5, 1, 150, forest),
        ("War Wolf", 4, 2, 180, near_snow),
        ("Deer", 4, 2, 120, forest),
        ("Rabbit", 4, 2, 120, forest),
        ("Winter Wolf", 7, 3, 120, tundra),
        ("Polar Bear", 5, 1, 150, tundra),
        ("Frost Troll", 6, 3, 150, tundra),
        ("Yeti", 1, 1, 1800, lakeside),
        ("Winter Wolf", 2, 3, 150, foot),
    ], walk7 - lake, avoid7, 7, rng)
    d8 = caves["d8"]
    far8 = max(d8.values())
    walk8s = {c for c in walk8 if c in d8}
    avoid8 = {(sx + dx, sy + dy) for dx in range(-6, 7) for dy in range(-6, 7)} | \
             {(dn[0] + dx, dn[1] + dy) for dx in range(-3, 4) for dy in range(-3, 4)}
    spawns8 = place_spawns([
        ("Dragon", 22, 2, 150, lambda c: d8[c] < far8 * 0.7),
        ("Dragon Lord", 8, 1, 200, lambda c: d8[c] >= far8 * 0.55),
        ("Dragon", 6, 1, 150, lambda c: d8[c] >= far8 * 0.55),
    ], walk8s, avoid8, 8, rng, min_gap=8)
    d9 = caves["d9"]
    far9 = max(d9.values())
    walk9s = {c for c in walk9 if c in d9}
    avoid9 = {(dn[0] + dx, dn[1] + dy) for dx in range(-5, 6) for dy in range(-5, 6)} | \
             {(npx + dx, npy + dy) for dx in range(-2, 3) for dy in range(-2, 3)}
    g9 = [("Dragon Lord", 6, 1, 200, lambda c: True),
          ("Demodras", 1, 1, 7200, lambda c: d9[c] >= far9 * 0.8)]
    if a.with_black_dragon:
        g9.insert(1, ("Black Dragon", 3, 1, 300, lambda c: d9[c] >= far9 * 0.4))
    spawns9 = place_spawns(g9, walk9s, avoid9, 9, rng, min_gap=7)

    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        return 1

    # --- resumen ---
    n_mon = sum(len(m) for s in (spawns7, spawns8, spawns9) for _c, _z, m in s)
    print(f"región x{X0}-{X0 + W - 1} y{Y0}-{Y0 + H - 1}: superficie {len(walk7)} pisables, "
          f"z8 {len(walk8)} piso, z9 {len(walk9)} piso; spawns {len(spawns7)}+{len(spawns8)}+{len(spawns9)} "
          f"({n_mon} monstruos); escalera {X0 + sx},{Y0 + sy},7 -> z8; bajada al Nido {X0 + dn[0]},{Y0 + dn[1]},8; "
          f"portal del Nido {X0 + npx},{Y0 + npy},9")

    if a.preview:
        write_preview(a.preview, surf, caves, index, city, otb)
        print(f"preview: {a.preview}")
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    # --- escribir OTBM ---
    backup = MAP.with_name(MAP.name + ".bak-northpass")
    if not backup.exists():
        shutil.copy2(MAP, backup)
    # 1) borrar lo que hubiera en la caja de la región (re-ejecución)
    for area in list(mapdata_node[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        if az not in (Z_SURFACE, Z_CAVES, Z_NEST):
            continue
        area[2] = [t for t in area[2] if not (t[0] in (T_TILE, T_HOUSETILE)
                                              and X0 <= ax + t[1][0] < X0 + W and Y0 <= ay + t[1][1] < Y0 + H)]
        if not area[2]:
            mapdata_node[2].remove(area)
    # 2) ciudad: reescribir casillas existentes (las del campo que no existían se crean en 3)
    for (x, y), (ground, items) in city.items():
        if (x, y, 7) not in index:
            continue
        _area, tile, _ax, _ay = index[(x, y, 7)]
        g_old, children = tile_ground_and_items(tile, otb)
        if items is None:
            keep = children
        else:
            keep = [item_node(i, city_portal_dest if i == TELEPORT else None) for i in items]
        tile[1] = rebuild_tile_props(tile, ground)
        tile[2] = keep
    # 3) región nueva
    all_new = {}
    for c, it in surf.items():
        all_new[(X0 + c[0], Y0 + c[1], Z_SURFACE)] = it
    for c, it in caves["t8"].items():
        all_new[(X0 + c[0], Y0 + c[1], Z_CAVES)] = it
    for c, it in caves["t9"].items():
        all_new[(X0 + c[0], Y0 + c[1], Z_NEST)] = it
    for (x, y), it in field_new.items():               # bordes del campo norte que faltaban
        all_new[(x, y, Z_SURFACE)] = it
    buckets = {}
    for (x, y, z), it in all_new.items():
        buckets.setdefault((x & ~0xFF, y & ~0xFF, z), []).append((x, y, it))
    for (bx, by, z), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, z)), []]
        for x, y, it in sorted(lst, key=lambda t: (t[1], t[0])):
            area[2].append(new_tile_node(x, y, bx, by, it, back_dest))
        mapdata_node[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    # --- spawns ---
    block = "\t<!-- BEGIN NORTH_PASS_SPAWNS (scripts/map/generate-north-pass.py) -->\n" + \
        spawn_xml(spawns7 + spawns8 + spawns9) + "\n\t<!-- END NORTH_PASS_SPAWNS -->\n"
    sp = SPAWNS.read_text(encoding="latin-1")
    sp = re.sub(r"\t?<!-- BEGIN NORTH_PASS_SPAWNS.*?<!-- END NORTH_PASS_SPAWNS -->\n?", "", sp, flags=re.S)
    sp = sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")

    # --- carteles ---
    signs = {(X0 + c[0], Y0 + c[1], 7): t for c, t in info["signs"].items()}
    signs[(FIELD_SIGN[0], FIELD_SIGN[1], 7)] = "PASO DEL NORTE\nBosque, Tundra Helada y Cuevas del Dragon.\nCuevas: nivel 60+."
    rd = READABLES.read_text(encoding="latin-1")
    rd = re.sub(r"\t?<!-- BEGIN NORTH_PASS_SIGNS -->.*?<!-- END NORTH_PASS_SIGNS -->\n?", "", rd, flags=re.S)
    lines = ["\t<!-- BEGIN NORTH_PASS_SIGNS -->"]
    for (x, y, z), t in sorted(signs.items()):
        lines.append(f'\t<readable x="{x}" y="{y}" z="{z}" text="{t.replace(chr(10), chr(92) + "n")}"/>')
    lines.append("\t<!-- END NORTH_PASS_SIGNS -->\n")
    rd = rd.replace("</readables>", "\n".join(lines) + "</readables>")
    READABLES.write_text(rd, encoding="latin-1")

    manifest = {
        "name": "generated-north-pass", "seed": a.seed, "withBlackDragon": a.with_black_dragon,
        "box": {"x1": X0, "y1": Y0, "x2": X0 + W - 1, "y2": Y0 + H - 1, "z": [Z_SURFACE, Z_CAVES, Z_NEST]},
        "city": {"gate": [{"x": x, "y": y, "z": 7} for x in GATE_XS for y in GATE_YS],
                 "portals": [{"x": x, "y": y, "z": 7} for x, y in CITY_PORTALS],
                 "landing": {"x": back_dest[0], "y": back_dest[1], "z": 7}},
        "arrival": {"x": city_portal_dest[0], "y": city_portal_dest[1], "z": 7},
        "regionPortals": [{"x": X0 + x, "y": Y0 + y, "z": 7} for x, y in REGION_PORTALS],
        "stairsToCaves": {"x": X0 + sx, "y": Y0 + sy, "z": 7},
        "stairsToNest": {"x": X0 + dn[0], "y": Y0 + dn[1], "z": 8},
        "nestPortal": {"x": X0 + npx, "y": Y0 + npy, "z": 9},
        "spawns": {"z7": len(spawns7), "z8": len(spawns8), "z9": len(spawns9), "monsters": n_mon},
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK carteles {READABLES}\nOK manifiesto {MANIFEST}")
    return 0


def write_preview(path: Path, surf, caves, index, city, otb):
    """Minimapa (colores del .dat) de la región en z7, z8, z9 lado a lado, 2 px por casilla."""
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

    layers = [surf, caves["t8"], caves["t9"]]
    S, gap = 2, 6
    Wp = (W * S + gap) * 3
    Hp = H * S
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


if __name__ == "__main__":
    sys.exit(main())
