#!/usr/bin/env python3
"""Pozos del Infierno: zona de caza de fuego en 4 pisos, con la quest de las armas 8.x.

Propuesta de docs/gameplay/QUESTS.md ("Pits of Inferno"): la fuente que falta para la Emerald
Sword, la Avenger, la Arcane Staff y la Arbalest (hoy solo GM), para nivel 100-130 en grupo.
Tema de fuego casi sin uso en el mapa (solo la Cueva de Fuego clasica y el borde de la city);
aqui va en serio: la progresion mas dura de fuego del server, despues de la Isla del Infierno
(que queda como isla de barco, nivel 80-130 con sus propias puertas y cofres).

  z7  Yerma de Ceniza: llegada (2 portales de vuelta) -> Campo de Brasas (oeste) ->
      La Jauria (este) -> santuario de ladrillo con puerta de nivel 90 y la boca del pozo
  z8  Pozos de Ceniza: pasillo en zigzag (~1.100 casillas)   Fire Elemental -> Hellhound
  z9  Garganta de Magma: pasillo hacia el norte (~1.300)      Hellhound de a 2 -> Demon
  z10 Corazon del Infierno: el pasillo mas largo (~1.400) + arena  Demon -> Fury ->
      puerta de nivel 100 -> Arena de las Furias -> Camara de las Armas (4 cofres, se elige
      uno, storage 5104) + portal al templo. Script: data/actions/scripts/pitschest.lua.

Cada piso de cueva arranca donde termina el de arriba (la bajada la elige stair_down dentro
de la caja del piso de abajo): z8 baja al sur, z9 vuelve al norte y z10 cruza al sur hasta el
arena. Cuevas con la receta de docs/items-and-map/MAPAS.md#zonas-de-caza (pasillos largos y
angostos, monstruos sueltos al entrar y de a 2 al fondo) via la maquinaria del Valle; suelos
de ceniza, charcos de lava y paredes de cueva con la maquinaria de la Isla del Infierno.
Portal de la plaza 159,47,7 (scripts/map/temple-portals.py, clave "inferno").

Caja: x 490-589, y 240-460, z7-z10 (vacia: el hub de eventos vive en x 595+). No toca nada
de lo demas: borra solo sus propias casillas (re-ejecutable y determinista con la semilla).

Reglas que valida antes de escribir (si algo falla no escribe nada):
  - bordes de tierra y lava con su pieza unica y paredes de cueva con pieza unica;
  - se llega de la llegada a los portales, a los claros, a la puerta y a la boca;
  - en cada piso de cueva, la bajada al siguiente se alcanza; en z10, la puerta, la arena,
    los cofres y el portal;
  - sin cruzar las puertas de nivel no se llega ni a la boca (z7) ni a los cofres (z10);
  - escaleras: bajada 432 arriba, escalera de mano 1385 justo debajo, salidas caminables;
  - desde ninguna casilla caminable se ve el borde de la caja (media pantalla 7x5);
  - todos los monstruos existen en monsters.xml.

Uso (desde la raiz del repo; Pillow no hace falta):
  python3 scripts/map/generate-inferno-pits.py --dry-run --preview /tmp/pozos.png
  python3 scripts/map/generate-inferno-pits.py          # escribe mapa, spawns, carteles y manifiesto
  python3 scripts/map/temple-portals.py                 # despues: portal de la plaza 159,47,7
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
from mapdata import MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE  # noqa: E402
from mapdata import parse_tree, png_bytes, serialize_tree  # noqa: E402

_spec = importlib.util.spec_from_file_location("beast_valley", HERE / "generate-beast-valley.py")
BV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BV)
NP = BV.NP
_spec = importlib.util.spec_from_file_location("hell_quest", HERE / "generate-hell-quest.py")
HQ = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(HQ)

Noise, neighbors_in, pieces_for, reach, Blocking = (
    NP.Noise, NP.neighbors_in, NP.pieces_for, NP.reach, NP.Blocking)
CARD, ALL8 = NP.CARD, NP.ALL8
grow, ellipse, stamp, rooms_along = BV.grow, BV.ellipse, BV.stamp, BV.rooms_along
carve_named, stair_down = BV.carve_named, BV.stair_down
place_stages, slices_by = BV.place_stages, BV.slices_by
blockify, shrink_lava, floor_tiles = HQ.blockify, HQ.shrink_lava, HQ.floor_tiles

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MONSTERS = REPO / "server/YurOTS/ots/data/monster/monsters.xml"
MANIFEST = WORLD / "generated-inferno-pits.json"

X0, Y0, W, H = 490, 240, 100, 221            # x 490-589, y 240-460
Z7, Z8, Z9, Z10 = 7, 8, 9, 10
BAND = 8                                      # franja exterior intransitable
VIEW = (7, 5)                                 # media pantalla del cliente 7.6
TEMPLE_BACK = (159, 48, 7)                    # llegada del portal de la plaza (temple-portals.py)

# --- piezas (ids de servidor) ---------------------------------------------------------------------
ASH, LAVA = HQ.ASH, HQ.LAVA                   # grava (ceniza), lava
LAVA_SIDE, LAVA_CORNER, LAVA_INNER = HQ.LAVA_SIDE, HQ.LAVA_CORNER, HQ.LAVA_INNER
DIRT_SIDE, DIRT_CORNER, DIRT_INNER = NP.DIRT_SIDE, NP.DIRT_CORNER, NP.DIRT_INNER
WALL_SIDE, WALL_CORNER, WALL_INNER, ROCK = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER, NP.ROCK
STONE, RUBBLE, PEBBLES, LAVA_HOLE = HQ.STONE, HQ.RUBBLE, HQ.PEBBLES, HQ.LAVA_HOLE
DEAD_TREES, COAL_BASIN, FIRE = HQ.DEAD_TREES, HQ.COAL_BASIN, HQ.FIRE
BONES = (2248, 2320, 3121)                    # huesos enteros (nada de piezas del esqueleto de dragon)
LANTERN, SIGN, CAMPFIRE = NP.LANTERN, NP.SIGN, NP.CAMPFIRE
TELEPORT, CHEST, DOOR_H = NP.TELEPORT, HQ.CHEST, HQ.DOOR_H
WALL_H, WALL_V, WALL_NW, WALL_SW, WALL_POST = HQ.WALL_H, HQ.WALL_V, HQ.WALL_NW, HQ.WALL_SW, HQ.WALL_POST
STAIR_DOWN, STAIRS_UP = NP.STAIR_DOWN, NP.STAIRS_UP
ATTR_UNIQUE_ID, ATTR_ACTION_ID, ATTR_TELE_DEST = 5, 4, 8
NEEDS_COUNT = NP.NEEDS_COUNT

LEVEL_MOUTH, LEVEL_HEART = 90, 100            # puertas: actionId = nivel + 1000 (leveldoor.lua)
CHEST_UIDS = (5104, 5105, 5106, 5107)         # pitschest.lua: emerald sword, avenger, arcane staff, arbalest
GUARDIAN_TIME = 600                           # la Furia del arena
STAIR_CLEAR = 6                               # sin spawns a esta distancia de escaleras, portales y llegada

# --- superficie (coordenadas locales, x 0-99, y 0-220) ---------------------------------------------
ARRIVAL = (50, 200)                           # destino del portal de la plaza
PORTALS_BACK = [(50, 205), (51, 205)]         # vuelta al templo, al sur de la llegada
CROSS = (50, 178)                             # El Vado (cartel)
EMBER = (32, 158, 10, 7)                      # Campo de Brasas: centro y radios
HOUNDS = (68, 112, 10, 7)                     # La Jauria
MOUTH = (50, 45)                              # la boca del pozo (bajada 432, dentro del santuario)

ROUTES = [
    ((50, 198), (50, 178)),                                    # llegada -> vado
    ((46, 178), (38, 168), (32, 158)),                         # vado -> campo de brasas
    ((36, 160), (44, 150), (50, 140)),                         # brasas -> norte
    ((54, 140), (62, 126), (68, 112)),                         # -> jauria
    ((64, 114), (56, 100), (50, 88)),                          # jauria -> boca
    ((50, 86), (50, 54)),                                      # -> santuario
]
ZONES = {"ember": EMBER, "hounds": HOUNDS, "cross": (50, 178, 8, 6)}

# --- cuevas: un pasillo por piso, cada uno arranca donde termina el de arriba ----------------------
# z8 arranca en la boca y baja al sur en zigzag. z9 y z10 se arman desde la bajada del piso
# anterior (la elige stair_down dentro de la caja del piso de abajo): z9 vuelve al norte y
# z10 cruza al sur hasta el arena. Tramos paralelos a 14+ casillas (RIBBON_BAND del valle).
CAVE8 = {"name": "cenizas", "box": (6, 36, 88, 70), "mouth": MOUTH, "min": 700,
         "path": [(50, 49), (84, 49), (84, 67), (16, 67), (16, 85), (50, 85)],
         "rooms": rooms_along([(50, 49), (84, 49), (84, 67), (16, 67), (16, 85), (50, 85)])}
CAVE9 = {"name": "magma", "box": (6, 36, 88, 110), "mouth": None, "min": 800}
CAVE10 = {"name": "corazon", "box": (6, 36, 88, 120), "mouth": None, "min": 900}


def deep_path(mouth, dy, x_lo, x_hi, rows, end_x=50):
    """Recorrido en zigzag desde la boca: `rows` filas completas (x_lo-x_hi) cada |dy| casillas
    en la direccion dy (positivo: al sur; negativo: al norte), unidas por los extremos, con una
    sala final en el centro. La boca conecta en L con la primera fila (sin zigzag). Con dy < 0
    la sala final queda 2 casillas al sur de la ultima fila (dentro de la caja del piso de abajo)."""
    m0, m1 = mouth
    pts = [(m0, m1 + 2)]
    x = x_lo if m0 <= (x_lo + x_hi) // 2 else x_hi
    y = m1 + dy
    for _ in range(rows):
        pts.append((x, y))
        x = x_hi if x == x_lo else x_lo
        pts.append((x, y))
        y += dy
    pts.append((end_x, y - dy + (dy if dy > 0 else -2)))
    return pts


# --- caza: fuego de menos a mas; sueltos al entrar, de a 2 al fondo (MAPAS.md#zonas-de-caza) --------------
SURFACE_STAGES = {   # z7: la distancia se mide desde la llegada
    "ember": [(("Fire Devil",), 1, 120, 6), (("Fire Devil", "Fire Elemental"), 1, 140, 6),
              (("Fire Elemental",), 2, 150, 6)],
    "hounds": [(("Fire Elemental", "Hellhound"), 1, 150, 6), (("Hellhound",), 1, 170, 6),
               (("Hellhound",), 2, 190, 6)],
}
STAGES8 = [(("Fire Elemental",), 1, 150, 12),
           (("Fire Elemental", "Hellhound"), 1, 170, 11),
           (("Hellhound",), 1, 190, 11),
           (("Hellhound", "Fire Elemental"), 2, 210, 10)]
STAGES9 = [(("Hellhound",), 1, 180, 13),
           (("Hellhound", "Fire Elemental"), 2, 200, 12),
           (("Demon",), 1, 240, 12),
           (("Demon", "Hellhound"), 2, 260, 11)]
STAGES10 = [(("Demon",), 1, 240, 13),
            (("Demon", "Hellhound"), 2, 260, 12),
            (("Demon", "Fury"), 1, 300, 12),
            (("Fury", "Demon", "Metal Demon"), 2, 330, 11)]


# --- superficie -------------------------------------------------------------------------------------

def build_surface(seed: int, bl: Blocking):
    rng = random.Random(seed)
    nz = Noise(seed)
    cells = {(x, y) for y in range(H) for x in range(W)}
    inner = {(x, y) for (x, y) in cells if BAND + 1 <= x < W - BAND - 1 and BAND + 1 <= y < H - BAND - 1}
    path = set().union(*(stamp(pts, 1) for pts in ROUTES))

    # 1) lo caminable: ruta + claros + llegada + boca; la yerma es un cañon, no un campo abierto
    route = set().union(*(stamp(pts, 3) for pts in ROUTES))
    zones = {name: ellipse(*z) for name, z in ZONES.items()}
    arrival_zone = {(ARRIVAL[0] + dx, ARRIVAL[1] + dy) for dx in range(-4, 5) for dy in range(-3, 6)}
    mouth_area = {(MOUTH[0] + dx, MOUTH[1] + dy) for dx in range(-3, 4) for dy in range(-3, 8)}
    play = (route | set().union(*zones.values()) | arrival_zone | mouth_area) & inner

    # 2) senderos de tierra quemada (los bordes llevan su pieza; el sendero protege la ruta del ruido)
    dirt = (path | ellipse(EMBER[0], EMBER[1], 7, 5) | ellipse(HOUNDS[0], HOUNDS[1], 7, 5)
            | {(ARRIVAL[0] + dx, ARRIVAL[1] + dy) for dx in range(-3, 4) for dy in range(-2, 4)}) & play
    dirt = NP.fix_until_valid(dirt, inner, DIRT_SIDE, DIRT_CORNER, DIRT_INNER, single=True)
    play |= dirt

    # 3) borde organico del cañon (sin tocar la tierra, que ya tiene sus piezas)
    for c in sorted(play - dirt):
        edge = any((c[0] + dx, c[1] + dy) not in play for dx, dy in ALL8)
        if edge and nz.fbm(c[0] / 5.5, c[1] / 5.5, 2, 120) < 0.44:
            play.discard(c)
    for c in sorted(grow(play, 1) & inner):
        if c not in play and nz.fbm(c[0] / 4.5, c[1] / 4.5, 2, 220) > 0.64:
            play.add(c)
    play |= set(PORTALS_BACK) | {ARRIVAL} | mouth_area

    tiles: dict = {}
    for c in cells:
        if c in dirt:
            tiles[c] = [NP.DIRT]
        else:
            # (24 nov 2026) sin borde: DIRT_SIDE es "pasto con borde de tierra" y en la grava volcánica dibujaba
            # una franja verde a los lados del sendero. No hay familia grava/tierra: la grava queda lisa.
            tiles[c] = [ASH]

    # 4) charcos de lava lejos del sendero (con su borde de grava, pieza unica)
    pools = set()
    for px, py, rx, ry in ((20, 190, 5, 4), (75, 172, 4, 4), (15, 118, 4, 5), (83, 66, 4, 4),
                           (29, 62, 4, 3), (66, 148, 3, 3)):
        pools |= ellipse(px, py, rx, ry)
    pools &= cells - play - grow(path, 2)
    pools = shrink_lava(pools, cells)
    not_lava = cells - pools
    for c in sorted(pools):
        p = pieces_for(neighbors_in(not_lava, *c), LAVA_SIDE, LAVA_CORNER, LAVA_INNER)
        tiles[c] = [p[0] if p else LAVA]

    # 5) lo que no es yerma bloquea: piedras, rocas y arboles muertos (como el bosque del valle)
    occupied: set = set()

    def free(c, r=0):
        return all((c[0] + dx, c[1] + dy) not in occupied for dx in range(-r, r + 1) for dy in range(-r, r + 1))

    def put(c, item, size=1):
        tiles[c].append(item)
        for dx in range(size):
            for dy in range(size):
                occupied.add((c[0] - dx, c[1] - dy))

    keep_clear = path | arrival_zone | mouth_area
    occupied |= keep_clear

    #   (todo lo que no es yerma bloquea: cada casilla lleva su pieza, como el bosque del valle;
    #   las de sprite 2x2 van en coordenadas impares y dibujan hacia arriba-izquierda)
    for c in sorted(cells - play - pools):
        x, y = c
        r = rng.random()
        if c not in inner:                                   # pie de montaña: denso
            tiles[c].append(rng.choice((RUBBLE, STONE, STONE)) if x % 2 == 1 and y % 2 == 1 and r < 0.6
                            else rng.choice((STONE, RUBBLE)))
        elif x % 2 == 1 and y % 2 == 1 and r < 0.26:
            tiles[c].append(rng.choice(DEAD_TREES + (RUBBLE,)))
        elif r < 0.72:
            tiles[c].append(rng.choice((STONE, RUBBLE)))
        else:
            tiles[c].append(rng.choice(DEAD_TREES + (LAVA_HOLE,)))

    # 6) claros: brasas (fogata y huesos) y jauria (huesos y piedritas que no bloquean)
    for c in sorted((zones["ember"] | zones["hounds"]) & play):
        if c in occupied or len(tiles[c]) > 1 or c in dirt:
            continue
        r = rng.random()
        if r < 0.10:
            tiles[c].append(rng.choice(BONES))
        elif r < 0.16:
            tiles[c].append(PEBBLES)
    for camp in ((EMBER[0] - 4, EMBER[1]), (HOUNDS[0] + 4, HOUNDS[1])):
        if camp in play and camp not in keep_clear and len(tiles[camp]) == 1 and free(camp):
            put(camp, CAMPFIRE)
            occupied |= grow({camp}, 2)

    # 7) faroles siguiendo el sendero
    for pts in ROUTES:
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            n = max(abs(x2 - x1), abs(y2 - y1), 1)
            for i in range(4, n, 11):
                x, y = int(round(x1 + (x2 - x1) * i / n)), int(round(y1 + (y2 - y1) * i / n))
                c = (x - 2, y)
                if c in play and c not in keep_clear and len(tiles[c]) == 1 and free(c):
                    put(c, LANTERN)

    # 8) santuario de ladrillo con la boca adentro: única entrada por la puerta del sur (nivel 90)
    sx, sy = MOUTH
    doors = {}
    inner_s = {(sx + dx, sy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - {MOUTH}
    approach = {(sx, sy + 3), (sx, sy + 4)}
    for c in inner_s | approach:
        tiles[c] = [ASH]
    tiles[MOUTH] = [STAIR_DOWN]
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
    doors[(sx, sy + 2)] = LEVEL_MOUTH + 1000
    for dx in (-1, 1):
        c = (sx + dx, sy + 3)
        if c in play:
            tiles[c] = [ASH, COAL_BASIN]

    # 9) portales de vuelta en la llegada
    for c in PORTALS_BACK:
        tiles[c] = [tiles[c][0], TELEPORT]
    px0, px1, py = PORTALS_BACK[0][0], PORTALS_BACK[1][0], PORTALS_BACK[0][1]
    for c in ((px0 - 1, py), (px1 + 1, py), (px0 - 1, py + 1), (px1 + 1, py + 1),
              (px0, py + 1), (px1, py + 1)):
        if c in play:
            tiles[c] = [tiles[c][0], STONE]
    for c in ((px0 - 2, py - 1), (px1 + 2, py - 1)):
        if c in play:
            tiles[c] = [tiles[c][0], LANTERN]

    signs = {
        (ARRIVAL[0] + 3, ARRIVAL[1] - 1): 'INFERNO PITS\nAshen wasteland above the pits.\nNorth: the Pit Mouth. Southern portal: temple.',
        (CROSS[0] + 3, CROSS[1] - 1): "THE FORD\nWest: Ember Field.\nNorth: the Pack and the Pit Mouth.",
        (EMBER[0] + 3, EMBER[1] + 6): "EMBER FIELD\nFire Devils and Fire Elementals.",
        (HOUNDS[0] + 3, HOUNDS[1] + 6): "THE PACK\nHellhounds among the rocks.",
        (sx + 4, sy + 5): 'THE PIT MOUTH\nGate: level 90. Ash Pits below.\nThe Heart at the far end requires level 100.',
    }
    placed = {}
    for anchor, text in signs.items():
        cands = [c for c in play - keep_clear - dirt if len(tiles[c]) == 1 and c not in placed
                 and any((c[0] + dx, c[1] + dy) in keep_clear for dx, dy in CARD)]
        if not cands:
            raise RuntimeError(f"no hay lugar para el cartel cerca de {anchor}")
        c = min(cands, key=lambda c: (abs(c[0] - anchor[0]) + abs(c[1] - anchor[1]), c))
        tiles[c] = [tiles[c][0], SIGN]
        placed[c] = text

    return tiles, {"play": play, "dirt": dirt, "zones": zones, "pools": pools, "signs": placed,
                   "doors": doors, "cells": cells, "inner": inner}


# --- cuevas -----------------------------------------------------------------------------------------

def decorate(tiles: dict, floor: set, start, keep, seed: int, rate: float, bl: Blocking):
    """Props de fuego (braseros, piedras, agujeros de lava) en el borde sin cortar el paso,
    huesos y piedritas sueltos que no bloquean. Nada que se mueva; los huesos van enteros."""
    rng = random.Random(seed + 4242)
    walk = set(floor)
    base = len(reach(walk, start, CARD))
    for c in sorted(floor, key=lambda c: (c[1], c[0])):
        if c in keep or len(tiles[c]) > 1 or tiles[c][0] != ASH:
            continue
        rock_n = 8 - len(neighbors_in(floor, *c))
        r = rng.random()
        if rock_n >= 3 and r < rate:
            item = rng.choice((STONE, LAVA_HOLE, COAL_BASIN))
            if bl.blocks(item):
                walk.discard(c)
                if len(reach(walk, start, CARD)) != base - 1:
                    walk.add(c)
                    continue
                base -= 1
            tiles[c].append(item)
        elif r < rate + 0.03:
            tiles[c].append(rng.choice(BONES + (PEBBLES,)))


def lava_pools(floor: set, rooms, keep, seed: int):
    """Charcos de lava en las salas grandes, lejos de escaleras y bajadas (como las camaras z8
    de la Isla del Infierno)."""
    rng = random.Random(seed + 810)
    pools = set()
    for (rx, ry), r in rooms:
        if r < 3 or rng.random() >= 0.45:
            continue
        pools |= ellipse(rx + rng.choice((-1, 0, 1)), ry + rng.choice((-1, 0, 1)), 2.4, 1.7) & floor
    return pools - grow(keep, 3)


def arena_lava(arena: set, cx, cy):
    """Anillo de lava del arena: cuatro arcos (bloques 2x2); libres el centro y las entradas."""
    ring = {c for c in arena if 5.2 <= math.hypot(c[0] + 0.5 - cx, c[1] + 0.5 - cy) <= 8.4
            and abs(c[0] + 0.5 - cx) > 3.2 and abs(c[1] + 0.5 - cy) > 2.2}
    return blockify(ring)


def build_caves(seed: int, bl: Blocking):
    cells = {(x, y) for x in range(W) for y in range(H)}

    # z8: Pozos de Ceniza (arranca en la boca, un zigzag al sur)
    floor8 = carve_named(seed + 1, CAVE8)
    down8 = stair_down(floor8, (CAVE8["mouth"][0], CAVE8["mouth"][1] + 1), CAVE9)
    CAVE9["mouth"] = down8
    CAVE9["path"] = deep_path(down8, -16, 22, 78, 2)      # vuelve al norte
    CAVE9["rooms"] = rooms_along(CAVE9["path"])

    # z9: Garganta de Magma (mas largo)
    floor9 = carve_named(seed + 11, CAVE9)
    down9 = stair_down(floor9, (down8[0], down8[1] + 1), CAVE10)
    CAVE10["mouth"] = down9
    CAVE10["path"] = deep_path(down9, 16, 20, 80, 2)      # cruza al sur, hasta el arena
    CAVE10["rooms"] = rooms_along(CAVE10["path"])

    # z10: Corazon del Infierno + el final manual: corredor angosto -> puerta -> arena -> camara
    floor10 = carve_named(seed + 21, CAVE10)
    ex, ey = CAVE10["path"][-1]
    gate_y = ey + 16                       # fila de la puerta (2 de ancho: puerta + pared)
    corridor = {(x, y) for y in range(ey + 1, gate_y + 5) for x in (ex - 1, ex)}
    cut = {(x, y) for y in range(ey + 1, gate_y + 5) for x in range(ex - 6, ex + 7)
           if x not in (ex - 1, ex)}
    acx, acy = ex + 0.5, gate_y + 13       # centro del arena (circular)
    arena = ellipse(acx, acy, 8.5, 8.5)
    ry = gate_y + 24                       # camara de las armas
    chamber = {(x, y) for x in range(ex - 5, ex + 6) for y in range(ry, ry + 5)}
    link = {(x, y) for y in range(gate_y + 21, ry) for x in (ex - 1, ex)}
    floor10 = (floor10 - cut) | corridor | arena | chamber | link
    ring = arena_lava(arena, acx, acy)
    floor10 -= ring

    pools8 = lava_pools(floor8, CAVE8["rooms"], {CAVE8["mouth"], down8}, seed + 31)
    pools9 = lava_pools(floor9, CAVE9["rooms"], {down8, down9}, seed + 41)
    t8, ashy8, _ = floor_tiles(floor8 - pools8, pools8, cells)
    t9, ashy9, _ = floor_tiles(floor9 - pools9, pools9, cells)
    t10, ashy10, _ = floor_tiles(floor10, ring, cells)

    t8[CAVE8["mouth"]] = [ASH, STAIRS_UP]
    t8[down8] = [STAIR_DOWN]
    t9[down8] = [ASH, STAIRS_UP]
    t9[down9] = [STAIR_DOWN]
    t10[down9] = [ASH, STAIRS_UP]

    # puerta de nivel 100 y su pared; braseros a los lados
    doors10 = {}
    t10[(ex - 1, gate_y)] = [ASH, DOOR_H]
    t10[(ex, gate_y)] = [ASH, WALL_H]
    doors10[(ex - 1, gate_y)] = LEVEL_HEART + 1000
    for c in ((ex - 3, gate_y), (ex + 2, gate_y)):
        if c in t10 and t10[c][0] == ASH and len(t10[c]) == 1:
            t10[c] = [ASH, COAL_BASIN]

    # Camara de las Armas: 4 cofres contra la pared norte, portal al sur, fuego y braseros
    chests = {}
    for k, dx in enumerate((-4, -2, 2, 4)):
        c = (ex + dx - (1 if dx > 0 else 0), ry)
        chests[c] = CHEST_UIDS[k]
        t10[c] = [ASH, CHEST]
    portal = (ex, ry + 4)
    t10[portal] = [ASH, TELEPORT]
    for c in ((ex - 5, ry), (ex + 5, ry), (ex - 5, ry + 4), (ex + 5, ry + 4)):
        if c in t10 and t10[c][0] == ASH and len(t10[c]) == 1:
            t10[c] = [ASH, COAL_BASIN]
    for c in ((ex - 3, ry + 2), (ex + 3, ry + 2)):
        t10[c] = [ASH, FIRE]
    sign_c = (ex + 4, ry + 1)
    if sign_c in t10 and t10[sign_c][0] == ASH and len(t10[sign_c]) == 1:
        t10[sign_c] = [ASH, SIGN]

    return {"t8": t8, "floor8": ashy8, "down8": down8, "pools8": pools8,
            "t9": t9, "floor9": ashy9, "down9": down9, "pools9": pools9,
            "t10": t10, "floor10": ashy10, "doors10": doors10, "chests": chests,
            "portal": portal, "arena": arena - ring, "arena_c": (acx, acy),
            "gate": (ex - 1, gate_y), "sign10": (ex + 4, ry + 1)}


# --- spawns -----------------------------------------------------------------------------------------

def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{X0 + cx}" centery="{Y0 + cy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


# --- OTBM ---------------------------------------------------------------------------------------------

CHEST_MAP: dict = {}
DOOR_MAP: dict = {}


def item_node(iid: int, uid=None, aid=None, tele=None):
    props = bytearray(struct.pack("<H", iid))
    if iid in NEEDS_COUNT:
        props.append(1)
    if uid is not None:
        props += bytes([ATTR_UNIQUE_ID]) + struct.pack("<H", uid)
    if aid is not None:
        props += bytes([ATTR_ACTION_ID]) + struct.pack("<H", aid)
    if tele is not None:
        props += bytes([ATTR_TELE_DEST]) + struct.pack("<HHB", *tele)
    return [T_ITEM, props, []]


def new_tile(x, y, bx, by, items):
    props = bytearray([x - bx, y - by, 9]) + struct.pack("<H", items[0])
    kids = []
    for i in items[1:]:
        tele = TEMPLE_BACK if i == TELEPORT else None
        uid = CHEST_MAP.get((x, y)) if i == CHEST else None
        aid = DOOR_MAP.get((x, y)) if i == DOOR_H else None
        kids.append(item_node(i, uid, aid, tele))
    return [T_TILE, props, kids]


def write_preview(path: Path, layers, otb, bl=None):
    r = BV.Renderer()
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
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()

    bl = Blocking()
    surf, info = build_surface(a.seed, bl)
    caves = build_caves(a.seed, bl)
    CHEST_MAP.update({(X0 + x, Y0 + y): uid for (x, y), uid in caves["chests"].items()})
    DOOR_MAP.update({(X0 + x, Y0 + y): aid for (x, y), aid in info["doors"].items()})
    DOOR_MAP.update({(X0 + x, Y0 + y): aid for (x, y), aid in caves["doors10"].items()})
    down8, down9 = caves["down8"], caves["down9"]
    portal = caves["portal"]
    gate = caves["gate"]

    decorate(caves["t8"], caves["floor8"], (CAVE8["mouth"][0], CAVE8["mouth"][1] + 1),
             grow({CAVE8["mouth"], down8}, 2), a.seed + 51, 0.10, bl)
    decorate(caves["t9"], caves["floor9"], (down8[0], down8[1] + 1),
             grow({down8, down9}, 2), a.seed + 61, 0.11, bl)
    decorate(caves["t10"], caves["floor10"], (down9[0], down9[1] + 1),
             grow({down9, gate, portal} | set(caves["chests"]), 2), a.seed + 71, 0.10, bl)

    errors = []
    # bordes de tierra y lava de la superficie: pieza exacta
    dirt, pools = info["dirt"], info["pools"]
    allp = set(DIRT_SIDE.values()) | set(DIRT_CORNER.values()) | set(DIRT_INNER.values())
    for c, it in surf.items():
        if c in dirt or c in pools:
            continue
        if it[0] in allp:                               # ya no lleva borde de pasto
            errors.append(f"tierra {c}: borde de pasto {it[0]} en la grava")
    not_lava = info["cells"] - pools
    lava_pieces = set(LAVA_SIDE.values()) | set(LAVA_CORNER.values()) | set(LAVA_INNER.values())
    for c in pools:
        want = pieces_for(neighbors_in(not_lava, *c), LAVA_SIDE, LAVA_CORNER, LAVA_INNER)
        if want is None or len(want) > 1 or (want and surf[c][0] != want[0]) or (not want and surf[c][0] != LAVA):
            errors.append(f"lava z7 {c}: quiere {want} tiene {surf[c][0]}")

    def walk_of(t, floor):
        return {c for c in floor if bl.walkable(t[c])}

    # z7: con la puerta abierta se llega a los claros, la puerta y la boca; cerrada, no
    walk7 = {c for c, it in surf.items() if bl.walkable(it)}
    door_cells = set(info["doors"])
    d7 = reach(walk7 | door_cells, ARRIVAL, CARD)
    if not any((MOUTH[0] + dx, MOUTH[1] + dy) in d7 for dx, dy in CARD + ((0, 0),)):
        errors.append(f"z7: la boca {MOUTH} no se alcanza desde la llegada (con la puerta abierta)")
    for c in PORTALS_BACK:
        if not any((c[0] + dx, c[1] + dy) in d7 for dx, dy in CARD):
            errors.append(f"z7: portal de la llegada {c} sin acceso")
    for name in ("ember", "hounds"):
        z = info["zones"][name] & walk7
        if not z or not (z & set(d7)):
            errors.append(f"z7: el claro {name} no se alcanza")
    d7_closed = reach(walk7 - door_cells, ARRIVAL, CARD)
    if any((MOUTH[0] + dx, MOUTH[1] + dy) in d7_closed for dx, dy in CARD + ((0, 0),)):
        errors.append("z7: se llega a la boca sin cruzar la puerta de nivel 90")

    # cuevas: piso, bajadas, puerta, cofres y portal
    layers = {Z7: surf, Z8: caves["t8"], Z9: caves["t9"], Z10: caves["t10"]}
    floors = {Z8: caves["floor8"], Z9: caves["floor9"], Z10: caves["floor10"]}
    starts = {Z8: (CAVE8["mouth"][0], CAVE8["mouth"][1] + 1), Z9: (down8[0], down8[1] + 1),
              Z10: (down9[0], down9[1] + 1)}
    mins = {Z8: CAVE8["min"], Z9: CAVE9["min"], Z10: CAVE10["min"]}
    dists = {}
    for z, floor in floors.items():
        walk = walk_of(layers[z], floor)
        # la distancia se mide con las puertas abiertas (z7 y z10 tienen puerta de nivel);
        # que no se salteen cerradas lo comprueba el chequeo de puertas de abajo
        doors_open = door_cells if z == Z7 else set(caves["doors10"])
        dists[z] = reach(walk | doors_open, starts[z], CARD)
        if len(dists[z]) < mins[z] * 0.75:
            errors.append(f"z{z}: piso corto ({len(dists[z])} casillas, min {mins[z]})")
    for z, down in ((Z8, down8), (Z9, down9)):
        if down not in dists[z]:
            errors.append(f"z{z}: la bajada {down} no se alcanza")
    for c in caves["chests"]:
        if not any((c[0] + dx, c[1] + dy) in dists[Z10] for dx, dy in CARD):
            errors.append(f"z10: el cofre {c} sin acceso")
    if not any((portal[0] + dx, portal[1] + dy) in dists[Z10] for dx, dy in CARD):
        errors.append(f"z10: el portal {portal} sin acceso")
    walk10_closed = walk_of(caves["t10"], caves["floor10"]) - set(caves["doors10"])
    d10_closed = reach(walk10_closed, starts[Z10], CARD)
    for c in list(caves["chests"]) + [portal]:
        if any((c[0] + dx, c[1] + dy) in d10_closed for dx, dy in CARD):
            errors.append(f"z10: {c} se alcanza sin cruzar la puerta de nivel 100")
            break

    # escaleras: bajada 432 arriba / escalera de mano 1385 abajo / salidas caminables
    for z, t in layers.items():
        for (x, y), it in t.items():
            if STAIR_DOWN in it:
                below = layers.get(z + 1, {}).get((x, y))
                if not below or STAIRS_UP not in below or below[0] != ASH:
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

    # paredes de cueva con pieza unica; lava con borde de grava
    for z, t in ((Z8, caves["t8"]), (Z9, caves["t9"]), (Z10, caves["t10"])):
        floor = floors[z]
        lav = {c for c, it in t.items() if it[0] == LAVA or it[0] in lava_pieces}
        solid = floor | lav
        for c, it in t.items():
            if c in solid:
                continue
            want = pieces_for(neighbors_in(solid, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
            if want is None or len(want) > 1 or (want and it[0] != want[0]) or (not want and it[0] != ROCK):
                errors.append(f"pared z{z} {c}: quiere {want} tiene {it[0]}")
        nl = set(t) - lav
        for c in lav:
            want = pieces_for(neighbors_in(nl, *c), LAVA_SIDE, LAVA_CORNER, LAVA_INNER)
            if want is None or len(want) > 1 or (want and t[c][0] != want[0]) or (not want and t[c][0] != LAVA):
                errors.append(f"lava z{z} {c}: quiere {want} tiene {t[c][0]}")

    # desde ninguna casilla caminable se ve el borde de la caja
    for label, wk in (("z7", walk7), ("z8", walk_of(caves["t8"], caves["floor8"])),
                      ("z9", walk_of(caves["t9"], caves["floor9"])),
                      ("z10", walk_of(caves["t10"], caves["floor10"]))):
        for (x, y) in wk:
            if x < VIEW[0] or x > W - VIEW[0] - 1 or y < VIEW[1] or y > H - VIEW[1] - 1:
                errors.append(f"{label} {(x, y)}: se ve el borde de la caja")
                break

    # monstruos: existen en monsters.xml
    names = set(re.findall(r'<monster name="([^"]+)"', MONSTERS.read_text(encoding="latin-1")))
    used = {n for stages in (STAGES8, STAGES9, STAGES10) for st in stages for n in st[0]}
    used |= {n for sts in SURFACE_STAGES.values() for st in sts for n in st[0]} | {"Fury", "Demon"}
    missing = sorted(used - names)
    if missing:
        errors.append(f"monstruos que no existen: {missing}")

    # spawns
    def cave_rng(name, z):
        return random.Random(f"{a.seed}-{name}-{z}")

    density = []

    def note(label, z, walk, placed):
        density.append((label, z, len(walk), len(placed), sum(len(m) for _c, _z, m in placed)))
        return placed

    spawns7 = []
    avoid7 = grow({ARRIVAL} | set(PORTALS_BACK) | {MOUTH, (MOUTH[0], MOUTH[1] + 4)}, STAIR_CLEAR)
    for name, zone in info["zones"].items():
        if name not in SURFACE_STAGES:
            continue
        walk = (zone & walk7) & set(d7)
        stages = SURFACE_STAGES[name]
        spawns7.extend(note(name, Z7, walk, place_stages(
            stages, slices_by(walk - avoid7, lambda c: d7.get(c, 0), len(stages)), walk, avoid7, Z7,
            cave_rng(name, Z7))))

    spawns8 = note("cenizas", Z8, dists[Z8], place_stages(
        STAGES8, slices_by(set(dists[Z8]) - grow({CAVE8["mouth"], down8}, STAIR_CLEAR),
                           lambda c: dists[Z8][c], len(STAGES8)),
        set(dists[Z8]), grow({CAVE8["mouth"], down8}, STAIR_CLEAR), Z8, cave_rng("cenizas", Z8)))

    spawns9 = note("magma", Z9, dists[Z9], place_stages(
        STAGES9, slices_by(set(dists[Z9]) - grow({down8, down9}, STAIR_CLEAR),
                           lambda c: dists[Z9][c], len(STAGES9)),
        set(dists[Z9]), grow({down8, down9}, STAIR_CLEAR), Z9, cave_rng("magma", Z9)))

    avoid10 = grow({down9, portal, gate} | set(caves["chests"]), STAIR_CLEAR)
    spawns10 = note("corazon", Z10, dists[Z10], place_stages(
        STAGES10, slices_by(set(dists[Z10]) - avoid10, lambda c: dists[Z10][c], len(STAGES10)),
        set(dists[Z10]), avoid10, Z10, cave_rng("corazon", Z10)))

    # guardianes del arena: la Furia al centro, demonios a los costados
    acx, acy = caves["arena_c"]
    acxi, acyi = int(acx), int(acy)
    guardians = []
    arena_walk = caves["arena"] & set(dists[Z10])
    if all((acxi + dx, acyi + dy) in arena_walk for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
        guardians.append(((acxi, acyi), Z10, [("Fury", (acxi, acyi), GUARDIAN_TIME)]))
        for dx in (-5, 5):
            c = (acxi + dx, acyi - 2)
            if c in arena_walk and all((c[0] + a, c[1] + b) in arena_walk for a in (-1, 0, 1) for b in (-1, 0, 1)):
                guardians.append((c, Z10, [("Demon", c, 300)]))
    if not guardians:
        errors.append("z10: no hay lugar para los guardianes del arena")

    counts: dict = {}
    for s in (spawns7, spawns8, spawns9, spawns10, guardians):
        for _c, _z, mons in s:
            for name, _p, _t in mons:
                counts[name] = counts.get(name, 0) + 1
    n_mon = sum(counts.values())

    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        if a.preview:
            write_preview(a.preview, [surf, caves["t8"], caves["t9"], caves["t10"]], bl.otb, bl)
        return 1

    print(f"pozos x{X0}-{X0 + W - 1} y{Y0}-{Y0 + H - 1}: z7 {len(walk7)} casillas, "
          f"z8 {len(dists[Z8])}, z9 {len(dists[Z9])}, z10 {len(dists[Z10])}; "
          f"spawns {len(spawns7)}+{len(spawns8)}+{len(spawns9)}+{len(spawns10)}+{len(guardians)} "
          f"({n_mon} monstruos); boca {X0 + MOUTH[0]},{Y0 + MOUTH[1]},7; bajadas "
          f"{X0 + down8[0]},{Y0 + down8[1]},8 / {X0 + down9[0]},{Y0 + down9[1]},9; puerta "
          f"{X0 + gate[0]},{Y0 + gate[1]},10 (nivel {LEVEL_HEART}); portal {X0 + portal[0]},{Y0 + portal[1]},10")
    for label, z, tiles, ns, nm in density:
        print(f"  z{z} {label:<9} {tiles:>5} casillas  {ns:>3} spawns  {nm:>3} monstruos  "
              f"1 cada {tiles / max(nm, 1):.0f} casillas")
    print("monstruos: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    if a.preview:
        write_preview(a.preview, [surf, caves["t8"], caves["t9"], caves["t10"]], bl.otb, bl)
        print(f"preview: {a.preview}")
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    # --- mapa: fuera lo propio de la caja (re-ejecutable), adentro los pozos ---
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    md = root[2][0]
    backup = MAP.with_name(MAP.name + ".bak-infernopits")
    if not backup.exists():
        shutil.copy2(MAP, backup)

    def gone(gx, gy, z):
        return X0 <= gx < X0 + W and Y0 <= gy < Y0 + H and z in (Z7, Z8, Z9, Z10)

    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        area[2] = [t for t in area[2] if not (t[0] in (T_TILE, T_HOUSETILE)
                                              and gone(ax + t[1][0], ay + t[1][1], az))]
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

    # --- spawns ---
    sp = SPAWNS.read_text(encoding="latin-1")
    block = "\t<!-- BEGIN INFERNO_PITS_SPAWNS (scripts/map/generate-inferno-pits.py) -->\n" + \
        spawn_xml(spawns7 + spawns8 + spawns9 + spawns10 + guardians) + "\n\t<!-- END INFERNO_PITS_SPAWNS -->\n"
    old = re.search(r"[ \t]*<!-- BEGIN INFERNO_PITS_SPAWNS.*?<!-- END INFERNO_PITS_SPAWNS -->\n?", sp, flags=re.S)
    if old:
        sp = sp[:old.start()] + "\x00BLOCK\x00" + sp[old.end():]
    sp = re.sub(r'[ \t]*<spawn centerx="(\d+)" centery="(\d+)" centerz="(\d+)"[^>]*>.*?</spawn>\n?',
                lambda m: "" if gone(int(m.group(1)), int(m.group(2)), int(m.group(3))) else m.group(0),
                sp, flags=re.S)
    sp = sp.replace("\x00BLOCK\x00", block) if old else sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")

    # --- carteles ---
    rd = READABLES.read_text(encoding="latin-1")
    lines = ["\t<!-- BEGIN INFERNO_PITS_SIGNS -->"]
    for (x, y), t in sorted(info["signs"].items()):
        lines.append(f'\t<readable x="{X0 + x}" y="{Y0 + y}" z="7" text="{t.replace(chr(10), chr(92) + "n")}"/>')
    lines.append(f'\t<readable x="{X0 + caves["sign10"][0]}" y="{Y0 + caves["sign10"][1]}" z="10" '
                 f'text="WEAPONS CHAMBER\\nFour chests: each hero chooses one.\\n'
                 f'Gate: level {LEVEL_HEART}."/>')
    lines.append("\t<!-- END INFERNO_PITS_SIGNS -->\n")
    old = re.search(r"\t?<!-- BEGIN INFERNO_PITS_SIGNS -->.*?<!-- END INFERNO_PITS_SIGNS -->\n?", rd, flags=re.S)
    if old:
        rd = rd[:old.start()] + "\n".join(lines) + rd[old.end():]
    else:
        rd = rd.replace("</readables>", "\n".join(lines) + "</readables>")
    READABLES.write_text(rd, encoding="latin-1")

    MANIFEST.write_text(json.dumps({
        "name": "generated-inferno-pits", "seed": a.seed, "version": 1,
        "box": {"x1": X0, "y1": Y0, "x2": X0 + W - 1, "y2": Y0 + H - 1, "z": [Z7, Z8, Z9, Z10]},
        "landing": {"x": X0 + ARRIVAL[0], "y": Y0 + ARRIVAL[1], "z": 7},
        "portalsBack": [{"x": X0 + x, "y": Y0 + y, "z": 7, "to": list(TEMPLE_BACK)} for x, y in PORTALS_BACK]
        + [{"x": X0 + portal[0], "y": Y0 + portal[1], "z": 10, "to": list(TEMPLE_BACK)}],
        "mouths": [{"name": "La Boca del Pozo", "x": X0 + MOUTH[0], "y": Y0 + MOUTH[1], "z": 7}],
        "downs": [{"name": "Pozos de Ceniza -> Garganta de Magma", "x": X0 + down8[0], "y": Y0 + down8[1], "z": 8},
                  {"name": "Garganta -> Corazon", "x": X0 + down9[0], "y": Y0 + down9[1], "z": 9}],
        "floors": {"z8": "Pozos de Ceniza", "z9": "Garganta de Magma", "z10": "Corazon del Infierno"},
        "doors": [{"level": LEVEL_MOUTH, "x": X0 + MOUTH[0], "y": Y0 + MOUTH[1] + 2, "z": 7},
                  {"level": LEVEL_HEART, "x": X0 + gate[0], "y": Y0 + gate[1], "z": 10}],
        "chests": [{"uid": uid, "item": item, "x": X0 + c[0], "y": Y0 + c[1], "z": 10}
                   for c, uid, item in zip(sorted(caves["chests"]), CHEST_UIDS,
                                           (20157, 20158, 20159, 20160))],
        "arena": {"x": int(X0 + acx), "y": int(Y0 + acy), "z": 10, "guardians": ["Fury", "Demon x2"]},
        "zones": {name: {"x": X0 + int(z[0]), "y": Y0 + int(z[1]), "rx": z[2], "ry": z[3]}
                  for name, z in ZONES.items()},
        "spawns": {"z7": len(spawns7), "z8": len(spawns8), "z9": len(spawns9), "z10": len(spawns10),
                   "guardians": len(guardians), "monsters": n_mon},
        "monsters": dict(sorted(counts.items())),
        "density": [{"zone": label, "z": z, "tiles": tiles, "spawns": ns, "monsters": nm}
                    for label, z, tiles, ns, nm in density],
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK carteles {READABLES}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
