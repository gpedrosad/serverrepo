#!/usr/bin/env python3
"""Catedral Oscura: la Dark Cathedral de Tibia 7.6 en una zona vacía del mapa.

Tres pisos apilados en la misma caja, con portal desde la plaza de portales del templo:

  z7  Jungla cerrada (bosque denso, sin mar alrededor). En el centro la NAVE de la catedral,
      negra y larga (norte-sur) con la entrada al sur; alrededor, ruinas de ladrillo con piso de
      tierra: el edificio del oeste (5 salas), las salas chicas del este y la sala gris del sur con
      bancos y escombros. Dos bajadas ("acesso ao -2"): una en la jungla del norte y otra al oeste,
      junto a la sala gris.
  z8  Cripta (-1): eje norte-sur largo desde la jungla hasta la sala del fondo, dos pasillos
      este-oeste con salas a los lados (A-T) y la cueva natural de los gusanos al noreste.
  z9  Cripta profunda (-2): sala grande al norte con laberinto de columnas, octógono central con la
      escalera, brazo oeste con 4 salas en H, brazo este con 2 rombos y la sala oval, anillo sur
      con dos salas a cada lado, sala grande central sur y sala final.

Geometría: cada sala es un rectángulo; las salas se separan por una casilla (pared de una sola
casilla) y las puertas se abren solas donde dos salas quedan a una casilla. La pieza de cada pared
sale del mapa de paredes por vecinos (oeste/norte), como en el resto del mapa
(docs/items-and-map/PIEZAS_DE_MAPA.md): vertical 1049, horizontal 1050, esquina NO 1051, esquina
SE 1053 (ladrillo: 1030, 1028, 1027, 1033). Escaleras: agujero 432 arriba y escalera 1385 abajo en
la misma casilla (sube una al norte, baja una al sur).

Uso (desde la raíz del repo):
  python3.11 scripts/map/generate-dark-cathedral.py --dry-run --preview /tmp/dc
  python3.11 scripts/map/generate-dark-cathedral.py                    # mapa, spawns, carteles
  python3 scripts/map/temple-portals.py                                # portal de la plaza
Re-ejecutable: borra la caja z7-z9 y reemplaza los bloques DARK_CATHEDRAL de spawns y carteles.
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import (DIRS, MAP, REPO, T_AREA, T_HOUSETILE, T_TILE, Renderer,  # noqa: E402
                     load_otb, parse_tree, png_bytes, serialize_tree)

_spec = importlib.util.spec_from_file_location("north_pass", HERE / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)
Noise, neighbors_in, reach, Blocking = NP.Noise, NP.neighbors_in, NP.reach, NP.Blocking
pieces_for, fix_until_valid = NP.pieces_for, NP.fix_until_valid
new_tile_node, TELEPORT = NP.new_tile_node, NP.TELEPORT

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MONSTERS = REPO / "server/YurOTS/ots/data/monster"
MANIFEST = WORLD / "generated-dark-cathedral.json"

# --- caja --------------------------------------------------------------------------------------
# Zona vacía de 99x110. Vecinos (no se pisa nada de esto): Elvenbane termina en x84 (box
# 18-84 x 282-362); la caja oficial de Hydras arranca en x184 (y340-419); al sur, arena en
# x169-183 desde y384 y la Wave Arena reserva x165-190, y380-410 (dejamos colchón en y374); al
# noroeste hay una cueva ajena en x85-122 con y<=255 y tiles en z10 en y256-260 (no se escribe
# y<=263 ni z10). Antes la caja era 60x70 en (118,284); ahora es (85,264) 99x110 y el layout se
# desplaza (33,20) en local para que las coordenadas ABSOLUTAS no cambien.
X0, Y0, W, H = 85, 264, 99, 110            # x 85-183, y 264-373
DX, DY = 33, 20                            # desplazamiento de las locales de diseño
Z7, Z8, Z9 = 7, 8, 9
VIEW = (7, 5)                              # media pantalla del cliente 7.6
BAND = (VIEW[0] + 1, VIEW[1] + 1)          # franja de jungla cerrada en el borde (8 y 6)
TEMPLE_BACK = (155, 48, 7)                 # llegada del portal Dark Cathedral en la plaza

# --- piezas (ids de servidor, todos en items-zagan-test.otb) ------------------------------------
GRASS, DIRT, ROCK = 4756, 103, 101
GRASSY = {4756, 4526} | set(range(110, 122))               # pasto y bordes de tierra (todo camina)
DIRT_SIDE = {"n": 111, "e": 112, "s": 110, "w": 113}        # pasto con borde de tierra
DIRT_CORNER = {("n", "w"): 120, ("n", "e"): 121, ("s", "w"): 119, ("s", "e"): 118}
DIRT_INNER = {"nw": 116, "ne": 117, "sw": 115, "se": 114}
# río en arco: entra por el borde oeste, rodea el predio por el norte y el este y se va por el sur.
# Del otro lado del agua queda jungla ancha hasta el borde de la caja.
RIVER = [(0, 40), (5, 28), (14, 19), (28, 12), (44, 8), (60, 7), (76, 11), (86, 20),
         (90, 32), (90, 46), (88, 60), (84, 72), (76, 84), (66, 92), (54, 96), (42, 97),
         (36, 104), (34, 109)]
RIVER_HALF = 3.0
# claro de la iglesia: elipse con borde irregular (no un rectángulo)
ESP_CENTER, ESP_RADII = (62.0, 58.0), (25.0, 29.0)
COAST_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
COAST_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
COAST_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}
WATER = 4608
BLACK, GREY, WHITE = 407, 431, 406                      # mármol negro, losa gris, mármol blanco
CAVE_A, CAVE_B, CAVE_C = 351, 352, 355                  # pisos de cueva
BRICK = dict(h=1028, v=1030, nw=1027, se=1033)        # ladrillo (ruinas y cripta)
STONE_WALL = dict(h=1050, v=1049, nw=1051, se=1053)   # piedra gris (catedral)
STAIRS_UP, STAIR_DOWN, SIGN = 1385, 432, 1429
BENCH, BENCH_R = 1662, 1663          # banco = dos piezas: 1662 y su mitad derecha 1663
PILLAR, STATUE, COAL_BASIN, CANDELABRUM = 1515, 1442, 1486, 2041
STONE, RUBBLE, PEBBLES = 1285, 1309, 1336
SKULL, HUMAN_SKELETON, DRAGON_SKELETON, RABBIT_SKELETON = 2248, 3133, 3125, 3121
BARREL, CRATE, COFFIN_HEAD, COFFIN_FOOT, TABLE, CHEST = 1770, 1739, 1410, 1411, 1614, 1740
TREES = (2701, 2702, 2703, 2704, 2705, 2706, 2708, 4009)   # 2x2: el dibujo ocupa la casilla y las de arriba-izquierda
BUSHES = (2767, 2786)                                      # bloquean: muro de jungla
SMALL_TREES = (2768, 2709, 2717)                            # pinitos y árboles secos (bloquean)
COVER = (4158, 4150, 4183, 4171, 4181, 2740)               # vegetación baja: no bloquea

# --- superficie (coordenadas locales: 0-59 en x, 0-69 en y) ------------------------------------
ARRIVAL = (30, 51)                          # destino del portal de la plaza
PORTAL_BACK = (33, 51)                      # vuelta al templo
NAVE = (27, 21, 34, 48)                     # nave negra (8 x 28)
NAVE_PILLARS = [(28, 25), (33, 25), (28, 31), (33, 31), (28, 37), (33, 37), (28, 43), (33, 43)]
NAVE_DOORS = [(30, 49), (31, 49), (30, 20), (31, 20)]         # entrada sur y brecha norte
WEST_ROOMS = [                              # 5 salas, una casilla de pared entre ellas
    ("w1", (8, 25, 14, 30)), ("w2", (8, 32, 14, 37)), ("w3", (16, 25, 21, 30)),
    ("w4", (16, 32, 21, 37)), ("w5", (8, 39, 21, 44)),
]
WEST_LINKS = [("w1", "w3"), ("w2", "w4"), ("w1", "w2"), ("w3", "w4"), ("w2", "w5"), ("w4", "w5")]
WEST_DOORS = [(7, 27), (22, 41), (14, 45)]                    # salidas a la jungla
EAST_ROOMS = [                              # 4 salas chicas
    ("e1", (39, 25, 43, 29)), ("e2", (39, 31, 43, 35)),
    ("e3", (45, 25, 49, 30)), ("e4", (45, 32, 49, 36)),
]
EAST_LINKS = [("e1", "e2"), ("e3", "e4"), ("e1", "e3"), ("e2", "e4")]
EAST_DOORS = [(38, 27), (47, 24), (45, 37)]
HALL = (17, 55, 32, 61)                     # sala gris del sur (bancos y escombros)
HALL_DOORS = [(25, 54), (26, 54), (27, 54), (16, 57)]
YARD = (8, 49, 14, 54)                      # sala gris del oeste con la bajada
YARD_DOORS = [(15, 52)]
PLAZA = (25, 50, 36, 53)                    # explanada de la llegada
PLATFORM = (27, 9, 34, 13)                  # rellano de la bajada en la jungla
HOLE_NORTH = (30, 11)                       # bajada A: jungla norte
HOLE_WEST = (10, 52)                        # bajada B: oeste, junto a la sala gris
PATHS = ([(x, 52) for x in range(15, 25)]                     # explanada -> sala gris del oeste
         + [(x, y) for x in (30, 31) for y in range(14, 20)])  # rellano -> brecha norte de la nave
SIGNS = {
    (33, 50): "CATEDRAL OSCURA\nAl norte, la nave.\nBajadas a la cripta: en la jungla\ny junto a la "
              "sala gris.\nEste portal vuelve al templo.",
    (28, 50): "NAVE DE LA CATEDRAL\nSolo monjes y muertos\nrezan aca.",
    (18, 56): "SALA DE LOS BANCOS\nBancos viejos y escombros.\nAl oeste, la bajada a la cripta.",
    (28, 8): "ACCESO A LA CRIPTA\nEscalera abajo.\nNo vuelvas solo.",
}

# --- cripta (-1, z8): eje norte-sur en tramos + pasillos este-oeste ------------------------------
H1A, H1B = (9, 20, 30, 21), (31, 22, 47, 23)               # pasillo norte, en dos tramos
AXIS_A, AXIS_B, AXIS_C = (29, 11, 31, 24), (28, 24, 30, 38), (28, 39, 30, 57)   # eje con quiebre
H2 = (14, 44, 47, 45)                                       # pasillo sur
ROOMS8 = [
    ("A", (10, 12, 16, 18), GREY), ("B", (18, 13, 23, 18), GREY),
    ("J", (33, 15, 39, 20), DIRT),                          # antecámara de la cueva
    ("C", (9, 23, 15, 30), GREY), ("D", (17, 23, 22, 30), DIRT),
    ("K", (32, 25, 37, 31), DIRT), ("L", (39, 25, 44, 31), GREY),
    ("M", (9, 32, 15, 42), DIRT), ("N", (17, 32, 22, 42), GREY),
    ("O", (32, 33, 38, 42), GREY), ("P", (40, 33, 45, 42), DIRT),
    ("Q", (10, 47, 15, 54), GREY), ("R", (17, 47, 23, 52), DIRT),
    ("S", (33, 47, 38, 52), DIRT), ("U", (40, 47, 45, 52), GREY),
    ("T", (23, 59, 37, 64), GREY),                          # sala del fondo
]
LINKS8 = [("A", "H1A"), ("B", "H1A"), ("J", "H1B"),
          ("C", "H1A"), ("D", "H1A"), ("K", "H1B"), ("L", "H1B"),
          ("M", "H2"), ("N", "H2"), ("O", "H2"), ("P", "H2"),
          ("Q", "H2"), ("R", "H2"), ("S", "H2"), ("U", "H2")]
L_ROOMS8 = {"R": ((20, 52, 23, 55),)}                        # cola en L de la sala R
# cueva NE: cámaras irregulares unidas por pasillos (como las salas G-J de la referencia).
# Con la caja nueva hay margen al norte y al este, así que la red crece (no es sólo un desplazamiento).
CAVE_ROOMS = (((79, 26), 3.4), ((72, 23), 2.8), ((67, 28), 2.2), ((76, 31), 2.6),
              ((83, 32), 2.6), ((80, 38), 2.4), ((73, 37), 2.0), ((85, 24), 2.2),
              ((70, 20), 2.0))
CAVE_LINKS = (((79, 26), (72, 23)), ((79, 26), (76, 31)), ((79, 26), (85, 24)),
              ((72, 23), (70, 20)), ((72, 23), (67, 28)), ((76, 31), (83, 32)),
              ((76, 31), (73, 37)), ((83, 32), (80, 38)), ((73, 37), (80, 38)),
              ((67, 28), (73, 37)))
CAVE_BOX = (64, 17, 87, 42)
CAVE_DOOR = ((69, 34), (70, 34))                            # entra desde la antecámara J
DOWN8 = (30, 33)                                            # agujero z8 -> z9

MIRROR_X = 125                             # 2 * (DX + 29.5): eje de simetría del -2

# --- cripta profunda (-2, z9) ------------------------------------------------------------------
NORTH9 = (17, 8, 42, 24)                                    # sala de las columnas
NECK9 = (27, 25, 32, 29)
OCT9 = (25, 30, 34, 36)                                     # octógono de la escalera
ARM_W9, ARM_E9 = (8, 32, 25, 34), (34, 32, 45, 34)          # brazos de la cruz
W_ROOMS9 = [("w1", (8, 24, 13, 30)), ("w2", (16, 24, 21, 30)),      # 4 salas en H (oeste)
            ("w3", (8, 36, 13, 41)), ("w4", (16, 36, 21, 41))]
E_DIAMS9 = [("d1", (38, 24, 42, 30)), ("d2", (38, 36, 42, 42))]     # 2 salas rombo (este)
E_OVAL9 = (44, 26, 51, 40)                                          # sala oval
# anillo sur en zigzag: baja, sale, baja y vuelve a entrar
A_W9, A_E9 = (24, 34, 25, 44), (34, 34, 35, 44)             # primer tramo (baja)
H_W9, H_E9 = (16, 44, 25, 45), (34, 44, 43, 45)             # codo (sale)
V_W9, V_E9 = (16, 45, 17, 52), (42, 45, 43, 52)             # segundo tramo (baja)
L_W9, L_E9 = (16, 52, 25, 53), (34, 52, 43, 53)             # codo (vuelve a entrar)
MID9 = (27, 37, 32, 45)                                     # pasillo central octógono -> sala sur
SIDE_W1, SIDE_W2 = (8, 43, 14, 48), (8, 50, 14, 55)        # salas del anillo (oeste)
SIDE_E1, SIDE_E2 = (45, 43, 51, 48), (45, 50, 51, 55)      # salas del anillo (este)
SOUTH9 = (24, 46, 35, 57)                                   # sala grande central sur (negra)
FINAL9 = (26, 59, 33, 63)                                   # sala final
PILLARS9 = [(x, y) for y in (10, 13, 16, 19, 22) for x in (20, 24, 28, 31, 35, 39)]
PILLAR_ITEM = 1514                                          # pilar de piedra (ítem): se lee como columna alta
DEEP_PORTAL = (29, 61)

# --- desplazamiento a la caja nueva ------------------------------------------------------------
# Todas las coordenadas de arriba están en el espacio de diseño de 60x70. Se desplazan (DX, DY)
# para que las ABSOLUTAS sigan siendo las mismas (llegada 148,335,7, portal 155,47,7, etc.).

def _c(p):
    return (p[0] + DX, p[1] + DY)


def _b(b):
    return (b[0] + DX, b[1] + DY, b[2] + DX, b[3] + DY)


ARRIVAL, PORTAL_BACK = _c(ARRIVAL), _c(PORTAL_BACK)
HOLE_NORTH, HOLE_WEST = _c(HOLE_NORTH), _c(HOLE_WEST)
DOWN8, DEEP_PORTAL = _c(DOWN8), _c(DEEP_PORTAL)
NAVE, HALL, YARD = _b(NAVE), _b(HALL), _b(YARD)
PLAZA, PLATFORM = _b(PLAZA), _b(PLATFORM)
H1A, H1B, H2 = _b(H1A), _b(H1B), _b(H2)
AXIS_A, AXIS_B, AXIS_C = _b(AXIS_A), _b(AXIS_B), _b(AXIS_C)
NAVE_PILLARS = [_c(c) for c in NAVE_PILLARS]
NAVE_DOORS, WEST_DOORS, EAST_DOORS = ([_c(c) for c in x] for x in (NAVE_DOORS, WEST_DOORS, EAST_DOORS))
HALL_DOORS, YARD_DOORS = [_c(c) for c in HALL_DOORS], [_c(c) for c in YARD_DOORS]
WEST_ROOMS = [(n, _b(b)) for n, b in WEST_ROOMS]
EAST_ROOMS = [(n, _b(b)) for n, b in EAST_ROOMS]
ROOMS8 = [(n, _b(b), g) for n, b, g in ROOMS8]
L_ROOMS8 = {n: tuple(_b(b) for b in bs) for n, bs in L_ROOMS8.items()}
# CAVE_ROOMS / CAVE_LINKS / CAVE_BOX / CAVE_DOOR ya están en la caja nueva
PATHS = [_c(c) for c in PATHS]
SIGNS = {_c(k): v for k, v in SIGNS.items()}
NORTH9, NECK9, OCT9 = _b(NORTH9), _b(NECK9), _b(OCT9)
ARM_W9, ARM_E9 = _b(ARM_W9), _b(ARM_E9)
W_ROOMS9 = [(n, _b(b)) for n, b in W_ROOMS9]
E_DIAMS9 = [(n, _b(b)) for n, b in E_DIAMS9]
E_OVAL9 = _b(E_OVAL9)
A_W9, A_E9 = _b(A_W9), _b(A_E9)
H_W9, H_E9 = _b(H_W9), _b(H_E9)
V_W9, V_E9 = _b(V_W9), _b(V_E9)
L_W9, L_E9 = _b(L_W9), _b(L_E9)
MID9, SOUTH9, FINAL9 = _b(MID9), _b(SOUTH9), _b(FINAL9)
SIDE_W1, SIDE_W2, SIDE_E1, SIDE_E2 = (_b(x) for x in (SIDE_W1, SIDE_W2, SIDE_E1, SIDE_E2))
PILLARS9 = [_c(c) for c in PILLARS9]


# --- spawns ------------------------------------------------------------------------------------
SPAWNS7 = [
    ("w1", WEST_ROOMS[0][1], [("Bandit", 2, 70), ("Smuggler", 1, 80)]),
    ("w3", WEST_ROOMS[2][1], [("Wild Warrior", 2, 90), ("Bandit", 1, 70)]),
    ("w5", WEST_ROOMS[4][1], [("Smuggler", 2, 80), ("Hunter", 1, 120)]),
    ("e1", EAST_ROOMS[0][1], [("Bandit", 1, 70), ("Wild Warrior", 1, 90)]),
    ("e3", EAST_ROOMS[2][1], [("Hunter", 1, 120), ("Bandit", 1, 70)]),
    ("hall", HALL, [("Smuggler", 2, 80), ("Bandit", 2, 70), ("Hunter", 1, 120)]),
    ("jungle", (51, 26, 74, 39), [("Wild Warrior", 2, 90), ("Bandit", 2, 70), ("Hunter", 1, 120)]),
]
ROOMS8_BOX = {n: b for n, b, _g in ROOMS8}                  # cajas ya desplazadas
SPAWNS8 = [
    ("A", ROOMS8_BOX["A"], [("Bandit", 2, 80), ("Smuggler", 1, 90)]),
    ("B", ROOMS8_BOX["B"], [("Wild Warrior", 2, 90), ("Bandit", 1, 80)]),
    ("H1B", ROOMS8_BOX["J"], [("Bat", 1, 90), ("Centipede", 1, 110)]),
    ("C", ROOMS8_BOX["C"], [("Bandit", 2, 80), ("Smuggler", 2, 90)]),
    ("D", ROOMS8_BOX["D"], [("Wild Warrior", 2, 90), ("Assassin", 1, 130)]),
    ("K", ROOMS8_BOX["K"], [("Slime", 2, 100), ("Poison Spider", 1, 110)]),
    ("L", ROOMS8_BOX["L"], [("Bandit", 2, 80), ("Wild Warrior", 1, 90)]),
    ("M", ROOMS8_BOX["M"], [("Slime", 1, 100), ("Poison Spider", 2, 110)]),
    ("N", ROOMS8_BOX["N"], [("Skeleton", 2, 110), ("Ghoul", 1, 130)]),
    ("O", ROOMS8_BOX["O"], [("Bandit", 2, 80), ("Smuggler", 1, 90)]),
    ("P", ROOMS8_BOX["P"], [("Assassin", 1, 130), ("Wild Warrior", 2, 90)]),
    ("Q", ROOMS8_BOX["Q"], [("Bandit", 2, 80), ("Smuggler", 1, 90)]),
    ("R", ROOMS8_BOX["R"], [("Centipede", 2, 110), ("Bat", 1, 90)]),
    ("S", ROOMS8_BOX["S"], [("Rotworm", 2, 100), ("Skeleton", 1, 110)]),
    ("U", ROOMS8_BOX["U"], [("Ghoul", 2, 130), ("Skeleton", 1, 110)]),
    ("cave", CAVE_BOX, [("Rotworm", 3, 100), ("Ghoul", 2, 130), ("Skeleton", 2, 110),
                        ("Bat", 1, 90), ("Centipede", 1, 110)]),
    ("T", ROOMS8_BOX["T"], [("Assassin", 2, 130), ("Bandit", 3, 80), ("Wild Warrior", 1, 90),
                            ("Dark Monk", 1, 150)]),
]
SPAWNS9 = [
    ("north", NORTH9, [("Monk", 3, 120), ("Dark Monk", 2, 140), ("Ghost", 1, 160)]),
    ("w1", W_ROOMS9[0][1], [("Monk", 1, 120), ("Ghost", 1, 160)]),
    ("w2", W_ROOMS9[1][1], [("Dark Monk", 2, 140)]),
    ("w3", W_ROOMS9[2][1], [("Witch", 1, 150), ("Monk", 1, 120)]),
    ("w4", W_ROOMS9[3][1], [("Hunter", 1, 120), ("Ghost", 1, 160)]),
    ("d1", E_DIAMS9[0][1], [("Dark Monk", 1, 140), ("Monk", 1, 120)]),
    ("d2", E_DIAMS9[1][1], [("Ghost", 1, 160), ("Witch", 1, 150)]),
    ("oval", E_OVAL9, [("Witch", 1, 150), ("Hunter", 1, 120), ("Dark Monk", 1, 140)]),
    ("s1", SIDE_W1, [("Monk", 1, 120), ("Ghost", 1, 160)]),
    ("s2", SIDE_W2, [("Dark Monk", 1, 140), ("Witch", 1, 150)]),
    ("s3", SIDE_E1, [("Hunter", 1, 120), ("Ghost", 1, 160)]),
    ("s4", SIDE_E2, [("Witch", 1, 150), ("Dark Monk", 1, 140)]),
    ("mid", MID9, [("Dark Monk", 1, 140), ("Monk", 1, 120)]),
    ("south", SOUTH9, [("Dark Monk", 2, 140), ("Mummy", 1, 150), ("Witch", 1, 150),
                       ("Hunter", 1, 120), ("Stone Golem", 1, 160), ("Demon Skeleton", 1, 300)]),
    ("final", FINAL9, [("Ghost", 2, 160), ("Dark Monk", 1, 140)]),
]


# --- geometría ----------------------------------------------------------------------------------

def rect(x0, y0, x1, y1) -> set:
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def grow(cells, r: int) -> set:
    return {(x + dx, y + dy) for (x, y) in cells for dx in range(-r, r + 1) for dy in range(-r, r + 1)}


def ellipse(box, shrink=0.0) -> set:
    """Sala ovalada: elipse inscripta en la caja (bordes escalonados como en 7.6)."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2 + 0.5, (y1 - y0) / 2 + 0.5
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 - shrink}


def chamfer(box, k=1.6) -> set:
    """Rectángulo con las esquinas cortadas (salas 'rombo' de 7.6)."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2 + 0.5, (y1 - y0) / 2 + 0.5
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)
            if abs(x - cx) / rx + abs(y - cy) / ry <= k}


def octagon(box, cut=2) -> set:
    """Octógono: rectángulo con las cuatro esquinas cortadas en diagonal."""
    x0, y0, x1, y1 = box
    cells = rect(x0, y0, x1, y1)
    for i in range(cut):
        for j in range(cut):
            if i + j < cut:
                for c in ((x0 + i, y0 + j), (x1 - i, y0 + j), (x0 + i, y1 - j), (x1 - i, y1 - j)):
                    cells.discard(c)
    return cells


def open_door(a: set, b: set, width=1) -> set:
    """Casilla (o dos) de pared más centrada entre dos salas separadas por una casilla."""
    cands = []
    for (x, y) in a:
        for dx, dy in ((0, 2), (0, -2), (2, 0), (-2, 0)):
            if (x + dx, y + dy) in b:
                cands.append({(x + dx // 2, y + dy // 2)})
    if not cands:
        return set()
    ax = (sum(x for x, _ in a) / len(a), sum(y for _, y in a) / len(a))
    bx = (sum(x for x, _ in b) / len(b), sum(y for _, y in b) / len(b))
    mid = ((ax[0] + bx[0]) / 2, (ax[1] + bx[1]) / 2)
    cands.sort(key=lambda s: (round(math.hypot(next(iter(s))[0] - mid[0],
                                               next(iter(s))[1] - mid[1]), 3), sorted(s)))
    doors = set(cands[0])
    for s in cands[1:]:
        if len(doors) >= width:
            break
        if any(max(abs(c[0] - d[0]), abs(c[1] - d[1])) == 1 for c in s for d in doors):
            doors |= s
    return doors


# Tabla sacada del propio test.otbm: para cada combinación de vecinos (oeste, norte, este, sur)
# que sean pared, qué pieza usa el mapa. Así las paredes del generador se ven como las del resto
# del mapa, con los extremos y las esquinas bien cerrados.
PIECE_BY_NEIGHBORS = {
    (False, False, False, False): "nw",
    (False, False, False, True): "v",
    (False, False, True, False): "h",
    (False, True, False, False): "v",
    (True, False, False, False): "h",
    (False, False, True, True): "nw",
    (False, True, False, True): "v",
    (False, True, True, False): "v",
    (True, False, False, True): "h",
    (True, False, True, False): "h",
    (True, True, False, False): "se",
    (False, True, True, True): "v",
    (True, False, True, True): "h",
    (True, True, False, True): "se",
    (True, True, True, False): "se",
    (True, True, True, True): "se",
}


def wall_piece(mask: set, c, wall: dict) -> int:
    """Pieza de pared 7.6 según los cuatro vecinos (tabla medida en test.otbm)."""
    x, y = c
    key = ((x - 1, y) in mask, (x, y - 1) in mask, (x + 1, y) in mask, (x, y + 1) in mask)
    return wall[PIECE_BY_NEIGHBORS[key]]


def build_zone(rooms, links, ext_doors, pillars=(), default_wall=None, outside=GRASS,
               pillar_item=None, pillar_wall=None):
    """Salas con paredes de una casilla y puertas automáticas.

    `rooms` = [(nombre, caja[, piso[, paredes]])]. Las salas tienen que quedar separadas por
    exactamente una casilla de las que se unen. `pillars` son columnas (ítem, bloquean) dentro de
    una sala. Devuelve (tiles, floor, mask).
    """
    spec = {}
    for r in rooms:
        name, box = r[0], r[1]
        ground = r[2] if len(r) > 2 else GREY
        wall = r[3] if len(r) > 3 else (default_wall or BRICK)
        spec[name] = (set(box) if isinstance(box, set) else rect(*box), ground, wall)
    floors = {n: v[0] for n, v in spec.items()}
    fam_of = {}
    for name, (cells, _g, wall) in spec.items():
        for c in cells:
            fam_of[c] = wall
    column_wall = pillar_wall or default_wall or BRICK
    for c in pillars:
        fam_of[c] = column_wall

    interior: dict = {}
    for name, (cells, ground, _wall) in spec.items():
        for c in cells:
            interior[c] = ground

    doors = set(ext_doors)
    for a, b in links:
        doors |= open_door(floors[a], floors[b])

    columns = {}
    for c in pillars:
        if c in interior:
            columns[c] = interior.pop(c)
    mask = grow(set(interior), 1) - set(interior) | (set(columns) if not pillar_item else set())
    for c in doors:
        mask.discard(c)
        if c not in interior:
            near = [interior[(c[0] + dx, c[1] + dy)] for dx, dy in DIRS.values()
                    if (c[0] + dx, c[1] + dy) in interior]
            interior[c] = near[0] if near else GREY
    # suelo bajo las paredes: el del piso más cercano (para que no queden manchas de pasto)
    under = dict(interior)
    queue = list(interior)
    while queue:
        cx, cy = queue.pop()
        for dx, dy in DIRS.values():
            for n in ((cx + dx, cy + dy), (cx + dx, cy), (cx, cy + dy)):
                if n in mask and n not in under:
                    under[n] = under[(cx, cy)]
                    queue.append(n)
    tiles = {c: [g] for c, g in interior.items()}
    for c in mask:
        west_out = (c[0] - 1, c[1]) not in mask and (c[0] - 1, c[1]) not in interior
        north_out = (c[0], c[1] - 1) not in mask and (c[0], c[1] - 1) not in interior
        ground = outside if (west_out or north_out) else under.get(c, outside)
        tiles[c] = [ground, wall_piece(mask, c, fam_of.get(c, default_wall or BRICK))]
    for c, ground in columns.items():                 # columnas: ítem de pilar alto, no poste de pared
        tiles[c] = [under.get(c, ground), pillar_item] if pillar_item else \
            [under.get(c, ground), wall_piece(mask, c, column_wall or default_wall or BRICK)]
    return tiles, set(interior), mask


# --- superficie ---------------------------------------------------------------------------------

def build_surface(seed: int, bl: Blocking):
    rng = random.Random(seed)
    nz = Noise(seed)
    cells = {(x, y) for y in range(H) for x in range(W)}
    tiles: dict = {c: [GRASS] for c in cells}

    # 1. ríos en arco al norte y al este, como la referencia (el predio queda adentro y la
    #    jungla sigue del otro lado; nunca un marco de agua pegado al borde de la caja)
    def seg_dist(p, a, b):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return math.hypot(p[0] - ax, p[1] - ay)
        t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))

    def river_dist(c):
        return min(seg_dist(c, a, b) for a, b in zip(RIVER, RIVER[1:]))

    water = {c for c in cells
             if river_dist(c) <= RIVER_HALF + 0.55 * math.sin((c[0] * 1.7 + c[1]) / 3.0)}
    land = cells - water
    for c in cells:
        if c in water:
            tiles[c] = [WATER]
        else:
            coast = pieces_for(neighbors_in(water, *c), COAST_SIDE, COAST_CORNER, COAST_INNER)
            if coast:
                tiles[c] = [GRASS, *coast]

    # 2. explanada de tierra alrededor de la catedral (el claro de la iglesia de la referencia):
    #    elipse con borde irregular, no un rectángulo alineado a los ejes
    def in_esplanade(x, y):
        wob = 0.10 * math.sin(x / 3.7) + 0.08 * math.cos(y / 4.3) + 0.05 * math.sin((x + y) / 6.3)
        rx, ry = ESP_RADII[0] * (1 + wob), ESP_RADII[1] * (1 + wob)
        return ((x - ESP_CENTER[0]) / rx) ** 2 + ((y - ESP_CENTER[1]) / ry) ** 2 <= 1.0

    dirt = {c for c in cells if in_esplanade(*c)} & land
    dirt = fix_until_valid(dirt, land, DIRT_SIDE, DIRT_CORNER, DIRT_INNER, single=True)
    for c in land:
        if c in dirt:
            tiles[c] = [DIRT]
            continue
        edge = pieces_for(neighbors_in(dirt, *c), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
        tiles[c] = [edge[0]] if edge else [GRASS]

    # 2. explanadas y senderos (piedra)
    for c in PATHS:
        tiles[c] = [GREY]
    for box in (PLAZA, PLATFORM):
        for c in rect(*box):
            tiles[c] = [GREY]

    # 3. edificios de la superficie
    nave, nave_floor, nave_mask = build_zone(
        [("nave", NAVE, BLACK, STONE_WALL)], [], NAVE_DOORS, pillars=NAVE_PILLARS,
        default_wall=STONE_WALL, outside=GRASS)
    west, west_floor, west_mask = build_zone(
        [(n, b, DIRT, BRICK) for n, b in WEST_ROOMS], WEST_LINKS, WEST_DOORS, outside=GRASS)
    east, east_floor, east_mask = build_zone(
        [(n, b, DIRT, BRICK) for n, b in EAST_ROOMS], EAST_LINKS, EAST_DOORS, outside=GRASS)
    hall, hall_floor, hall_mask = build_zone(
        [("hall", HALL, GREY, STONE_WALL)], [], HALL_DOORS, outside=GRASS)
    yard, yard_floor, yard_mask = build_zone(
        [("yard", YARD, GREY, BRICK)], [], YARD_DOORS, outside=GRASS)
    for z in (nave, west, east, hall, yard):
        for c, it in z.items():
            tiles[c] = it
    wall_cells = nave_mask | west_mask | east_mask | hall_mask | yard_mask
    floor_all = nave_floor | west_floor | east_floor | hall_floor | yard_floor

    # 4. bajadas, llegada, portal de vuelta y carteles
    tiles[HOLE_NORTH] = [STAIR_DOWN]
    tiles[HOLE_WEST] = [STAIR_DOWN]
    for hole in (HOLE_NORTH, HOLE_WEST):                       # marco de piedra y braseros
        for dx, dy in ((-2, -1), (-2, 0), (-2, 1), (2, -1), (2, 1), (-1, -2), (1, -2), (-1, 2), (1, 2)):
            c = (hole[0] + dx, hole[1] + dy)
            if tiles.get(c) == [GRASS] or tiles.get(c) == [GREY]:
                tiles[c] = [tiles[c][0], STONE]
        for dx in (-1, 1):
            c = (hole[0] + dx, hole[1] + 1)
            if tiles.get(c) == [GRASS] or tiles.get(c) == [GREY]:
                tiles[c] = [tiles[c][0], COAL_BASIN]
    tiles[PORTAL_BACK] = [GREY, TELEPORT]
    for c in SIGNS:
        if c in wall_cells or tiles[c][0] == WATER:
            raise SystemExit(f"ERROR: el cartel {c} cae sobre una pared o el agua")
        tiles[c] = [tiles[c][0], SIGN]

    # 5. la nave: araña, candelabros, estatuas y dos filas de bancos alineadas
    nave_decor = [((30 + DX, 22 + DY), COAL_BASIN), ((31 + DX, 22 + DY), COAL_BASIN),
                  ((28 + DX, 23 + DY), CANDELABRUM), ((33 + DX, 23 + DY), CANDELABRUM),
                  ((29 + DX, 48 + DY), STATUE), ((32 + DX, 48 + DY), STATUE)]
    for c, item in nave_decor:
        if tiles.get(c) == [BLACK]:
            tiles[c] = [BLACK, item]
    for y in (42 + DY, 44 + DY):                        # dos filas de bancos enteros
        for x0 in (29 + DX, 31 + DX):
            for dx, item in ((0, BENCH), (1, BENCH_R)):
                if tiles.get((x0 + dx, y)) == [BLACK]:
                    tiles[(x0 + dx, y)] = [BLACK, item]

    # 6. sala gris: bancos en dos filas (pares 1662 + 1663) y escombros que no bloquean
    for y in (57 + DY, 59 + DY):
        for x0 in range(HALL[0] + 2, HALL[2] - 1, 2):
            if tiles.get((x0, y)) == [GREY] and tiles.get((x0 + 1, y)) == [GREY]:
                tiles[(x0, y)] = [GREY, BENCH]
                tiles[(x0 + 1, y)] = [GREY, BENCH_R]
    for (x, y) in sorted(rect(*HALL)):
        if tiles.get((x, y)) == [GREY] and rng.random() < 0.10:
            tiles[(x, y)] = [GREY, rng.choice((PEBBLES, SKULL, HUMAN_SKELETON))]

    # 7. escombros, cofres y ataúdes en las ruinas (siempre sobre piso liso)
    clutter = [((9 + DX, 26 + DY), CRATE), ((10 + DX, 26 + DY), BARREL),
               ((20 + DX, 42 + DY), COFFIN_HEAD), ((20 + DX, 43 + DY), COFFIN_FOOT),
               ((8 + DX, 36 + DY), TABLE), ((13 + DX, 33 + DY), BARREL),
               ((9 + DX, 42 + DY), CHEST), ((21 + DX, 26 + DY), SKULL),
               ((39 + DX, 26 + DY), CRATE), ((48 + DX, 34 + DY), BARREL),
               ((45 + DX, 29 + DY), TABLE), ((40 + DX, 33 + DY), SKULL),
               ((19 + DX, 60 + DY), COFFIN_HEAD), ((19 + DX, 61 + DY), COFFIN_FOOT),
               ((31 + DX, 60 + DY), CRATE), ((24 + DX, 57 + DY), HUMAN_SKELETON),
               ((32 + DX, 58 + DY), SKULL), ((9 + DX, 51 + DY), BARREL)]
    for c, item in clutter:
        if c in floor_all and len(tiles.get(c, [])) == 1:
            tiles[c] = [tiles[c][0], item]
    for c in sorted(floor_all):                                # escombros sueltos en las ruinas
        if len(tiles.get(c, [])) == 1 and tiles[c][0] == DIRT and rng.random() < 0.09:
            tiles[c] = [DIRT, rng.choice((PEBBLES, RUBBLE, SKULL, STONE))]

    keep = (grow({ARRIVAL, PORTAL_BACK, HOLE_NORTH, HOLE_WEST} | set(SIGNS), 2)
            | grow(floor_all | wall_cells, 2) | set(PATHS)
            | grow(rect(*PLAZA), 1) | grow(rect(*PLATFORM), 1))

    # 7b. la explanada no es un plano vacío: piedras, huesos y matas sueltas (todo camina)
    for c in sorted(cells):
        if c not in dirt or tiles.get(c) != [DIRT] or c in keep:
            continue
        r = rng.random()
        if r < 0.05:
            tiles[c] = [DIRT, rng.choice((PEBBLES, SKULL, HUMAN_SKELETON, STONE))]
        elif r < 0.17:
            tiles[c] = [DIRT, rng.choice(COVER)]

    # 8. jungla: franja cerrada en el borde, árboles cada 3 casillas y vegetación baja en el medio
    band = {c for c in cells if c[0] < BAND[0] or c[0] > W - 1 - BAND[0]
            or c[1] < BAND[1] or c[1] > H - 1 - BAND[1]}
    occupied: set = set()

    def plant(c, item, size=1):
        tiles[c] = [tiles[c][0], item]
        for dx in range(size):
            for dy in range(size):
                occupied.add((c[0] - dx, c[1] - dy))

    order = sorted(cells)
    rng.shuffle(order)
    for c in order:                                            # monte cerrado del borde
        if c not in band or tiles.get(c) != [GRASS] or c in keep or c in occupied:
            continue
        r = rng.random()
        if r < 0.52:
            plant(c, rng.choice(TREES), 2)
        elif r < 0.78:
            tiles[c] = [GRASS, rng.choice(BUSHES)]
        else:
            tiles[c] = [GRASS, rng.choice(SMALL_TREES)]
    for c in order:                                            # árboles al azar, nunca dos copas pegadas
        if tiles.get(c) != [GRASS] or c in keep or c in occupied:
            continue
        if rng.random() < 0.22:
            plant(c, rng.choice(TREES), 2)
    for c in order:                                            # algún árbol suelto en el claro
        if tiles.get(c) != [DIRT] or c in keep or c in occupied:
            continue
        r = rng.random()
        if r < 0.035:
            plant(c, rng.choice(TREES), 2)
        elif r < 0.075:
            tiles[c] = [DIRT, rng.choice(BUSHES)]
    for c in order:                                            # vegetación baja en todos los huecos
        if tiles.get(c) != [GRASS] or c in occupied:
            continue
        if c in keep:
            tiles[c] = [GRASS, rng.choice(COVER)]              # claros: sólo tapizado, sigue libre
            continue
        r = rng.random()
        if r < 0.74:
            tiles[c] = [GRASS, rng.choice(COVER)]
        elif r < 0.82:
            tiles[c] = [GRASS, rng.choice(BUSHES)]

    # 9. la franja del borde queda cerrada: nada caminable dentro de ella
    for c in sorted(band):
        it = tiles.get(c)
        if it and it[0] != WATER and bl.walkable(it):
            tiles[c] = [it[0], rng.choice(BUSHES)]

    # 10. rincones y bolsillos: lo que no se alcanza se tapa (agua o monte), nunca queda piso suelto
    for _ in range(60):
        walk = {c for c, it in tiles.items() if bl.walkable(it)} - {PORTAL_BACK}
        lost = walk - set(reach(walk, ARRIVAL))
        if not lost:
            break
        for c in lost:
            if any(((c[0] + dx, c[1] + dy) in water) for dx, dy in DIRS.values()):
                tiles[c] = [WATER]
            else:
                plant(c, rng.choice(TREES), 2)

    info = dict(floor=floor_all, walls=wall_cells, water=water, band=band)
    return tiles, info


# --- cripta -------------------------------------------------------------------------------------

def cave_floor(seed: int, entrance, box, steps=52) -> set:
    """Cueva natural: un blob irregular que crece desde `entrance`."""
    rng = random.Random(seed)
    floor = {entrance}
    frontier = [entrance]
    for _ in range(steps):
        if not frontier:
            break
        x, y = frontier.pop(rng.randrange(len(frontier)))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n in floor or not (box[0] <= n[0] <= box[2] and box[1] <= n[1] <= box[3]):
                continue
            if rng.random() < 0.55:
                floor.add(n)
                frontier.append(n)
    return floor


def clip(tiles: dict) -> dict:
    """Nada fuera de la caja de diseño (la roca de relleno se sale una casilla)."""
    return {c: it for c, it in tiles.items() if 0 <= c[0] < W and 0 <= c[1] < H}


def spawn_xml(spawns) -> str:
    lines = []
    for name, (x, y), z, st in spawns:
        lines.append(f'\t<spawn centerx="{X0 + x}" centery="{Y0 + y}" centerz="{z}" radius="2">')
        lines.append(f'\t\t<monster name="{name}" x="0" y="0" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def plain(tiles, walk, bl) -> set:
    return {c for c in walk if len(tiles[c]) == 1 and bl.walkable(tiles[c])}


def place_zone(tiles, walk, bl, zone, monsters, avoid, rng, gap=2):
    box = zone if isinstance(zone, set) else set(rect(*zone))
    cands = sorted((plain(tiles, walk, bl) & box) - avoid)
    rng.shuffle(cands)
    out, taken = [], []
    for name, count, st in monsters:
        placed = 0
        for c in cands:
            if placed >= count:
                break
            if any(max(abs(c[0] - o[0]), abs(c[1] - o[1])) < gap for o in taken):
                continue
            taken.append(c)
            out.append((name, c, st))
            placed += 1
        if placed < count:
            raise RuntimeError(f"zona {box}: solo entraron {placed} de {count} {name}")
    return out


def write_preview(base: Path, layers, scale=1.0):
    """PNG por piso con los sprites del juego y la altura de las paredes (como se ve in-game)."""
    from PIL import Image
    from game_render import LAYER_RANK as RANK, Sprites, compose, layer_of, parse_dat_all
    otb = load_otb()
    items, _outfits = parse_dat_all()
    spr = Sprites()
    entry = {sid: items.get(e.get("cid")) for sid, e in otb.items() if e.get("cid")}
    out = []
    for z, t in layers:
        used = [c for c, it in t.items() if it[0] != ROCK]
        x1, x2 = min(x for x, _ in used) - 1, max(x for x, _ in used) + 3
        y1, y2 = min(y for _, y in used) - 1, max(y for _, y in used) + 3
        cols, rows = x2 - x1 + 1, y2 - y1 + 1
        canvas = Image.new("RGBA", (cols * 32, rows * 32), (14, 14, 18, 255))
        cache = {}
        for ty in range(y1, y2 + 1):
            for tx in range(x1, x2 + 1):
                draw = []
                for sid in t.get((tx, ty), []):
                    e = entry.get(sid)
                    if e is None:
                        continue
                    key = (sid, tx % e["px"], ty % e["py"])
                    im = cache.get(key) or cache.setdefault(key, compose(e, spr, key[1], key[2]))
                    draw.append((RANK[layer_of(e)], im, e))
                draw.sort(key=lambda d: d[0])
                elev = 0
                for _r, im, e in draw:
                    dx = dy = 0
                    if 0x18 in e["flags"]:
                        dx, dy = struct.unpack("<HH", e["flags"][0x18])
                    canvas.paste(im, ((tx - x1) * 32 - (e["w"] - 1) * 32 - dx - elev,
                                      (ty - y1) * 32 - (e["h"] - 1) * 32 - dy - elev), im)
                    if 0x19 in e["flags"]:
                        elev = min(24, elev + struct.unpack("<H", e["flags"][0x19])[0])
        p = base.with_name(f"{base.name}-z{z}.png")
        im = canvas.convert("RGB")
        if scale != 1:
            im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
            im = im.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
        im.save(p, optimize=True)
        out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=76)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path, help="prefijo: escribe <prefijo>-z7.png ... -z9.png")
    ap.add_argument("--preview-scale", type=float, default=1.0, help="0.5 para las imágenes del doc")
    a = ap.parse_args()

    bl = Blocking()
    otb = load_otb()
    errors: list[str] = []

    from mapdata import load_tiles
    existing = {(x, y, z) for (x, y, z) in load_tiles()
                if X0 <= x < X0 + W and Y0 <= y < Y0 + H and z in (Z7, Z8, Z9)}
    ours = False
    if MANIFEST.exists():                                  # re-ejecución: la caja vieja está adentro
        box = json.loads(MANIFEST.read_text()).get("box", {})
        try:
            ours = (X0 <= int(box["x1"]) and Y0 <= int(box["y1"])
                    and int(box["x2"]) <= X0 + W - 1 and int(box["y2"]) <= Y0 + H - 1)
        except (KeyError, TypeError, ValueError):
            ours = False
    if existing and not ours:
        print(f"ERROR: la caja x{X0}-{X0 + W - 1} y{Y0}-{Y0 + H - 1} ya tiene {len(existing)} casillas: "
              f"{sorted(existing)[:3]}. Elegí otra zona.", file=sys.stderr)
        return 1

    surf, s_info = build_surface(a.seed, bl)
    surf = clip(surf)

    # --- z8: cripta con cueva natural grande al noreste ---
    shape8 = {n: rect(*b) | rect(*L_ROOMS8[n][0]) for n, b, _g in ROOMS8 if n in L_ROOMS8}
    rooms8 = ([(n, shape8.get(n, b), g, BRICK) for n, b, g in ROOMS8]
              + [("H1A", H1A, GREY, BRICK), ("H1B", H1B, GREY, BRICK), ("H2", H2, GREY, BRICK),
                 ("AXA", AXIS_A, GREY, BRICK), ("AXB", AXIS_B, GREY, BRICK),
                 ("AXC", AXIS_C, GREY, BRICK)])
    links8 = LINKS8 + [("AXA", "H1A"), ("AXB", "AXA"), ("AXB", "H1B"), ("AXB", "H2"),
                       ("AXC", "AXB"), ("AXC", "H2"), ("AXC", "T")]
    t8, floor8, mask8 = build_zone(rooms8, links8, [], default_wall=BRICK, outside=ROCK)
    # cueva: discos unidos (contorno orgánico) que entra desde la sala J
    cave = {CAVE_DOOR[0], CAVE_DOOR[1]}
    print(f"cueva z8: {len(cave)} casillas tras los discos")
    for (cx, cy), r in CAVE_ROOMS:
        for dx in range(-int(r) - 1, int(r) + 2):
            for dy in range(-int(r) - 1, int(r) + 2):
                c = (cx + dx, cy + dy)
                wob = 0.72 + 0.55 * ((c[0] * 7 + c[1] * 13) % 5) / 4.0
                if math.hypot(dx, dy) <= r * wob and CAVE_BOX[0] <= c[0] <= CAVE_BOX[2] \
                        and CAVE_BOX[1] <= c[1] <= CAVE_BOX[3]:
                    cave.add(c)
    for (ax, ay), (bx, by) in CAVE_LINKS:                     # pasillos entre cámaras
        n = max(abs(bx - ax), abs(by - ay)) * 2
        for i in range(n + 1):
            px, py = ax + (bx - ax) * i / n, ay + (by - ay) * i / n
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    c = (round(px) + dx, round(py) + dy)
                    if CAVE_BOX[0] <= c[0] <= CAVE_BOX[2] and CAVE_BOX[1] <= c[1] <= CAVE_BOX[3]:
                        cave.add(c)
    rooms_floor8 = set(floor8)                                 # salas de ladrillo (sin la cueva)
    cave -= rooms_floor8 - set(CAVE_DOOR)                      # la cueva no invade el ladrillo
    cave -= {c for c in cave if any((c[0] + dx, c[1] + dy) in rooms_floor8 for dx, dy in DIRS.values())} \
        - set(CAVE_DOOR)                                       # deja una casilla de pared contra las salas
    cave_tiles = NP.cave_tiles(cave, grow(cave, 2) | rect(*CAVE_BOX), a.seed + 812)
    for c in grow(floor8 | mask8, 6):
        t8.setdefault(c, [ROCK])
    for c, it in cave_tiles.items():
        if c not in floor8:                                    # no pisa las salas de ladrillo
            t8[c] = it
    floor8 = (floor8 - cave) | cave
    mask8 -= cave
    # lo que quedó suelto se vuelve roca (la cueva es una sola masa conectada a la boca)
    linked = set(reach(cave, CAVE_DOOR[0]))
    for c in cave - linked:
        t8[c] = [ROCK]
    floor8 -= cave - linked
    cave = linked
    mask8 -= {c for c, it in t8.items() if it == [ROCK] and c not in floor8 and c not in cave}
    print(f"cueva z8: {len(cave)} casillas, x{min(c[0] for c in cave)}-"
          f"{max(c[0] for c in cave)} y{min(c[1] for c in cave)}-{max(c[1] for c in cave)}")
    t8[HOLE_NORTH] = [GREY, STAIRS_UP]
    t8[HOLE_WEST] = [GREY, STAIRS_UP]
    t8[DOWN8] = [STAIR_DOWN]
    floor8 |= {HOLE_NORTH, HOLE_WEST, DOWN8}

    # --- z9: planta del -2 ---
    rooms9 = ([("north", NORTH9, GREY, BRICK), ("neck", NECK9, WHITE, BRICK),
               ("oct", octagon(OCT9, 2), WHITE, BRICK),
               ("armw", ARM_W9, GREY, BRICK), ("arme", ARM_E9, GREY, BRICK),
               ("mid", MID9, GREY, BRICK)]
              + [(n, b, GREY, BRICK) for n, b in W_ROOMS9]
              + [("d1", chamfer(E_DIAMS9[0][1], 1.45), GREY, BRICK),
                 ("d2", chamfer(E_DIAMS9[1][1], 1.45), GREY, BRICK),
                 ("oval", ellipse(E_OVAL9), GREY, BRICK)]
              + [("aw", A_W9, GREY, BRICK), ("ae", A_E9, GREY, BRICK),
                 ("hw", H_W9, GREY, BRICK), ("he", H_E9, GREY, BRICK),
                 ("vw", V_W9, GREY, BRICK), ("ve", V_E9, GREY, BRICK),
                 ("lw", L_W9, GREY, BRICK), ("le", L_E9, GREY, BRICK),
                 ("s1", SIDE_W1, GREY, BRICK), ("s2", SIDE_W2, GREY, BRICK),
                 ("s3", SIDE_E1, GREY, BRICK), ("s4", SIDE_E2, GREY, BRICK),
                 ("south", SOUTH9, BLACK, BRICK), ("final", FINAL9, BLACK, BRICK)])
    links9 = [("neck", "north"), ("neck", "oct"), ("armw", "oct"), ("arme", "oct"),
              ("w1", "armw"), ("w2", "armw"), ("w3", "armw"), ("w4", "armw"),
              ("d1", "arme"), ("d2", "arme"), ("oval", "arme"),
              ("mid", "oct"), ("mid", "south"),
              ("vw", "s1"), ("vw", "s2"), ("ve", "s3"), ("ve", "s4"),
              ("south", "final")]
    t9, floor9, mask9 = build_zone(rooms9, links9, [], pillars=PILLARS9, default_wall=BRICK,
                                   outside=ROCK, pillar_item=PILLAR_ITEM)
    for c in grow(floor9 | mask9, 6):
        t9.setdefault(c, [ROCK])
    t9[DOWN8] = [WHITE, STAIRS_UP]
    t9[DEEP_PORTAL] = [BLACK, TELEPORT]
    floor9 |= {DOWN8, DEEP_PORTAL}
    t8, t9 = clip(t8), clip(t9)

    # escombros solo donde no molestan (nunca sobre escaleras, portales ni sus llegadas)
    octagon_floor = octagon(OCT9, 2) | rect(*NECK9) | rect(*MID9)
    for tiles, floor, seed, stairs, extra in ((t8, floor8, a.seed + 21, (HOLE_NORTH, HOLE_WEST, DOWN8), set()),
                                              (t9, floor9, a.seed + 22, (DOWN8, DEEP_PORTAL), octagon_floor)):
        avoid = grow(set(stairs), 2) | extra
        rng = random.Random(seed)
        for c in sorted(floor - avoid):
            it = tiles.get(c)
            if not it or len(it) != 1 or it[0] not in (GREY, DIRT, BLACK, WHITE, CAVE_A, CAVE_B, CAVE_C):
                continue
            r = rng.random()
            if r < 0.03:
                tiles[c] = [it[0], rng.choice((PEBBLES, SKULL, HUMAN_SKELETON, RABBIT_SKELETON))]
            elif r < 0.045:
                tiles[c] = [it[0], rng.choice((RUBBLE, STONE, DRAGON_SKELETON))]

    walk7 = {c for c, it in surf.items() if bl.walkable(it)}
    d7 = reach(walk7, ARRIVAL)
    walk8 = {c for c in floor8 if bl.walkable(t8.get(c, [ROCK]))}
    d8 = reach(walk8, (HOLE_NORTH[0], HOLE_NORTH[1] + 1))
    walk9 = {c for c in floor9 if bl.walkable(t9.get(c, [ROCK]))}
    d9 = reach(walk9, (DOWN8[0], DOWN8[1] + 1))

    # --- validación ---
    for c in (PORTAL_BACK, HOLE_NORTH, HOLE_WEST):
        if c not in d7 and not any((c[0] + dx, c[1] + dy) in d7 for dx, dy in DIRS.values()):
            errors.append(f"z7: {c} sin acceso desde la llegada")
    if (HOLE_NORTH[0], HOLE_NORTH[1] - 1) not in walk7:
        errors.append("z7: al subir por la escalera de la jungla se llega a una casilla no libre")
    if (HOLE_WEST[0], HOLE_WEST[1] - 1) not in walk7:
        errors.append("z7: al subir por la escalera del oeste se llega a una casilla no libre")
    if set(d7) != walk7:
        lost = sorted(walk7 - set(d7))
        errors.append(f"z7: {len(lost)} casillas caminables aisladas, ej. {lost[0]}")
    if (HOLE_WEST[0], HOLE_WEST[1] + 1) not in walk8:
        errors.append("z8: la escalera del oeste no cae sobre piso libre")
    if (HOLE_NORTH[0], HOLE_NORTH[1] + 1) not in walk8:
        errors.append("z8: la escalera del norte no cae sobre piso libre")
    if HOLE_WEST not in d8:
        errors.append("z8: la bajada oeste no se conecta con la del norte")
    if DOWN8 not in d8 or (DOWN8[0], DOWN8[1] - 1) not in walk8:
        errors.append("z8: la bajada al -2 no se alcanza")
    if set(d8) != walk8:
        lost = sorted(walk8 - set(d8))
        errors.append(f"z8: {len(lost)} casillas aisladas, ej. {lost[0]}")
        for c in lost[:8]:
            print("   aislada", c, t8.get(c), "en floor8:", c in floor8)
    if (DOWN8[0], DOWN8[1] - 1) not in walk8:
        errors.append("z9: al subir la escalera central se llega a una casilla no libre en z8")
    if (DOWN8[0], DOWN8[1] + 1) not in walk9:
        errors.append("z9: al caer por el agujero del -1 se llega a una casilla no libre")
    if DEEP_PORTAL not in walk9:
        errors.append("z9: el portal del fondo no está sobre el piso")
    if set(d9) != walk9:
        lost = sorted(walk9 - set(d9))
        errors.append(f"z9: {len(lost)} casillas aisladas, ej. {lost[0]}")

    # paredes: una sola pieza por casilla, y el piso nunca queda con pieza de pared
    for label, t, fl, ma in (("z7", surf, s_info["floor"], s_info["walls"]),
                             ("z8", t8, floor8, mask8), ("z9", t9, floor9, mask9)):
        for c, it in t.items():
            if len(it) > 2:
                errors.append(f"{label} {c}: {len(it)} ítems en una casilla ({it})")
                break
        for c in fl & set(ma):
            errors.append(f"{label} {c}: piso y pared en la misma casilla")
            break
        for c, it in t.items():
            bad = [i for i in it if i not in otb]
            if bad:
                errors.append(f"{label} {c}: ids que no están en el .otb {bad}")
                break

    # los bancos son de dos piezas: 1662 siempre con su 1663 a la derecha, y viceversa
    for c, it in surf.items():
        if BENCH in it:
            if BENCH_R not in surf.get((c[0] + 1, c[1]), []):
                errors.append(f"z7 {c}: banco 1662 sin su mitad derecha")
        if BENCH_R in it:
            if BENCH not in surf.get((c[0] - 1, c[1]), []):
                errors.append(f"z7 {c}: banco 1663 sin su mitad izquierda")

    # el -2: anillo, U y salas laterales espejadas
    def mirrored(box):                       # espejo sobre el eje del layout (no el de la caja)
        x0, y0, x1, y1 = box
        return (MIRROR_X - x1, y0, MIRROR_X - x0, y1)
    for a_box, b_box in ((A_W9, A_E9), (H_W9, H_E9), (V_W9, V_E9), (L_W9, L_E9),
                         (SIDE_W1, SIDE_E1), (SIDE_W2, SIDE_E2), (MID9, MID9),
                         (SOUTH9, SOUTH9), (FINAL9, FINAL9)):
        if mirrored(a_box) != b_box:
            errors.append(f"z9: {a_box} no está espejada con {b_box}")

    # que no se vea el borde de la caja (jungla cerrada arriba, roca abajo)
    for (x, y) in walk7:
        if x < BAND[0] or x > W - 1 - BAND[0] or y < BAND[1] or y > H - 1 - BAND[1]:
            errors.append(f"z7 {(x, y)}: piso caminable dentro de la franja del borde")
            break

    # spawns
    rng = random.Random(a.seed + 99)
    avoid7 = grow({ARRIVAL, PORTAL_BACK, HOLE_NORTH, HOLE_WEST} | set(SIGNS), 2)
    avoid8 = grow({HOLE_NORTH, HOLE_WEST, DOWN8}, 2)
    avoid9 = grow({DOWN8, DEEP_PORTAL}, 2)
    spawns = []
    for _lbl, zone, mons in SPAWNS7:
        spawns += [(n, c, Z7, st) for n, c, st in place_zone(surf, walk7, bl, zone, mons, avoid7, rng)]
    for _lbl, zone, mons in SPAWNS8:
        spawns += [(n, c, Z8, st) for n, c, st in place_zone(t8, walk8, bl, zone, mons, avoid8, rng)]
    for _lbl, zone, mons in SPAWNS9:
        spawns += [(n, c, Z9, st) for n, c, st in place_zone(t9, walk9, bl, zone, mons, avoid9, rng)]

    registry = (MONSTERS / "monsters.xml").read_text(encoding="latin-1")
    for name in sorted({s[0] for s in spawns}):
        if f'name="{name}"' not in registry:
            errors.append(f"monstruo sin registrar en monsters.xml: {name}")

    if a.preview:
        layers = [(Z7, {(X0 + x, Y0 + y): it for (x, y), it in surf.items()}),
                  (Z8, {(X0 + x, Y0 + y): it for (x, y), it in t8.items()}),
                  (Z9, {(X0 + x, Y0 + y): it for (x, y), it in t9.items()})]
        for p in write_preview(a.preview, layers, a.preview_scale):
            print(f"preview: {p}")
    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        return 1

    counts: dict = {}
    for name, _c, _z, _st in spawns:
        counts[name] = counts.get(name, 0) + 1
    g = lambda c, z: {"x": X0 + c[0], "y": Y0 + c[1], "z": z}   # noqa: E731
    print(f"catedral x{X0}-{X0 + W - 1} y{Y0}-{Y0 + H - 1} ({W}x{H}): "
          f"z7 {len(walk7)} pisables, z8 {len(walk8)}, z9 {len(walk9)}")
    print(f"llegada {X0 + ARRIVAL[0]},{Y0 + ARRIVAL[1]},7; portal vuelta {X0 + PORTAL_BACK[0]},"
          f"{Y0 + PORTAL_BACK[1]},7; bajadas {X0 + HOLE_NORTH[0]},{Y0 + HOLE_NORTH[1]},7 y "
          f"{X0 + HOLE_WEST[0]},{Y0 + HOLE_WEST[1]},7; bajada -2 {X0 + DOWN8[0]},{Y0 + DOWN8[1]},8; "
          f"portal fondo {X0 + DEEP_PORTAL[0]},{Y0 + DEEP_PORTAL[1]},9")
    print(f"spawns {len([s for s in spawns if s[2] == Z7])}+{len([s for s in spawns if s[2] == Z8])}"
          f"+{len([s for s in spawns if s[2] == Z9])}: " +
          ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    # --- mapa ---
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    md = root[2][0]
    backup = MAP.with_name(MAP.name + ".bak-darkcathedral")
    if not backup.exists():
        shutil.copy2(MAP, backup)

    def in_box(gx, gy, z):
        return z in (Z7, Z8, Z9) and X0 <= gx < X0 + W and Y0 <= gy < Y0 + H

    def leftover_rock(tile, gx, gy, z):
        """Roca de relleno que se salió una casilla de la caja en una corrida vieja."""
        p = bytes(tile[1])
        return (z in (Z8, Z9) and X0 - 1 <= gx <= X0 + W and Y0 - 1 <= gy <= Y0 + H
                and (gx < X0 or gx >= X0 + W or gy < Y0 or gy >= Y0 + H)
                and len(p) >= 5 and p[2] == 9 and struct.unpack_from("<H", p, 3)[0] == ROCK
                and not tile[2])

    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        area[2] = [t for t in area[2]
                   if not (t[0] in (T_TILE, T_HOUSETILE)
                           and (in_box(ax + t[1][0], ay + t[1][1], az)
                                or leftover_rock(t, ax + t[1][0], ay + t[1][1], az)))]
        if not area[2]:
            md[2].remove(area)
    buckets: dict = {}
    for (x, y), it in surf.items():
        buckets.setdefault(((X0 + x) & ~0xFF, (Y0 + y) & ~0xFF, Z7), []).append((X0 + x, Y0 + y, it))
    for (x, y), it in t8.items():
        buckets.setdefault(((X0 + x) & ~0xFF, (Y0 + y) & ~0xFF, Z8), []).append((X0 + x, Y0 + y, it))
    for (x, y), it in t9.items():
        buckets.setdefault(((X0 + x) & ~0xFF, (Y0 + y) & ~0xFF, Z9), []).append((X0 + x, Y0 + y, it))
    for (bx, by, z), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, z)), []]
        for x, y, it in sorted(lst, key=lambda t: (t[1], t[0])):
            area[2].append(new_tile_node(x, y, bx, by, it, TEMPLE_BACK))
        md[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    # --- spawns ---
    sp = SPAWNS.read_text(encoding="latin-1")
    sp = re.sub(r"[ \t]*<!-- BEGIN DARK_CATHEDRAL_SPAWNS.*?<!-- END DARK_CATHEDRAL_SPAWNS -->\n?", "",
                sp, flags=re.S)
    sp = re.sub(r'[ \t]*<spawn centerx="(\d+)" centery="(\d+)" centerz="(\d+)"[^>]*>.*?</spawn>\n?',
                lambda m: "" if in_box(int(m.group(1)), int(m.group(2)), int(m.group(3))) else m.group(0),
                sp, flags=re.S)
    block = ("\t<!-- BEGIN DARK_CATHEDRAL_SPAWNS (scripts/map/generate-dark-cathedral.py) -->\n"
             + spawn_xml(spawns) + "\n\t<!-- END DARK_CATHEDRAL_SPAWNS -->\n")
    SPAWNS.write_text(sp.replace("</spawns>", block + "</spawns>"), encoding="latin-1")

    # --- carteles ---
    rd = READABLES.read_text(encoding="latin-1")
    rd = re.sub(r"\t?<!-- BEGIN DARK_CATHEDRAL_SIGNS -->.*?<!-- END DARK_CATHEDRAL_SIGNS -->\n?", "",
                rd, flags=re.S)
    lines = ["\t<!-- BEGIN DARK_CATHEDRAL_SIGNS -->"]
    for (x, y), t in sorted(SIGNS.items()):
        lines.append(f'\t<readable x="{X0 + x}" y="{Y0 + y}" z="{Z7}" '
                     f'text="{t.replace(chr(10), chr(92) + "n")}"/>')
    lines.append("\t<!-- END DARK_CATHEDRAL_SIGNS -->\n")
    READABLES.write_text(rd.replace("</readables>", "\n".join(lines) + "</readables>"), encoding="latin-1")

    MANIFEST.write_text(json.dumps({
        "name": "generated-dark-cathedral", "seed": a.seed,
        "box": {"x1": X0, "y1": Y0, "x2": X0 + W - 1, "y2": Y0 + H - 1, "z": [Z7, Z8, Z9]},
        "landing": g(ARRIVAL, Z7),
        "portalTemple": {"x": TEMPLE_BACK[0], "y": TEMPLE_BACK[1], "z": TEMPLE_BACK[2]},
        "portalsBack": [dict(g(PORTAL_BACK, Z7), to=list(TEMPLE_BACK)),
                        dict(g(DEEP_PORTAL, Z9), to=list(TEMPLE_BACK))],
        "holes": [dict(g(HOLE_NORTH, Z7), to=Z8), dict(g(HOLE_WEST, Z7), to=Z8),
                  dict(g(DOWN8, Z8), to=Z9)],
        "stairs": [{"x": X0 + HOLE_NORTH[0], "y": Y0 + HOLE_NORTH[1], "z": Z8,
                    "up": g((HOLE_NORTH[0], HOLE_NORTH[1] - 1), Z7)},
                   {"x": X0 + HOLE_WEST[0], "y": Y0 + HOLE_WEST[1], "z": Z8,
                    "up": g((HOLE_WEST[0], HOLE_WEST[1] - 1), Z7)},
                   {"x": X0 + DOWN8[0], "y": Y0 + DOWN8[1], "z": Z9,
                    "up": g((DOWN8[0], DOWN8[1] - 1), Z8)}],
        "zones": {
            "nave": {"x1": X0 + NAVE[0], "y1": Y0 + NAVE[1], "x2": X0 + NAVE[2], "y2": Y0 + NAVE[3],
                     "z": Z7},
            "oeste": {"x1": X0 + 7, "y1": Y0 + 24, "x2": X0 + 22, "y2": Y0 + 45, "z": Z7},
            "este": {"x1": X0 + 38, "y1": Y0 + 24, "x2": X0 + 50, "y2": Y0 + 37, "z": Z7},
            "sala_gris": {"x1": X0 + HALL[0], "y1": Y0 + HALL[1], "x2": X0 + HALL[2], "y2": Y0 + HALL[3],
                          "z": Z7},
            "cripta": {"x1": X0 + 9, "y1": Y0 + 11, "x2": X0 + 47, "y2": Y0 + 63, "z": Z8},
            "cripta_profunda": {"x1": X0 + 8, "y1": Y0 + 8, "x2": X0 + 51, "y2": Y0 + 62, "z": Z9},
        },
        "spawns": {"z7": len([s for s in spawns if s[2] == Z7]),
                   "z8": len([s for s in spawns if s[2] == Z8]),
                   "z9": len([s for s in spawns if s[2] == Z9]), "monsters": len(spawns)},
        "monsters": dict(sorted(counts.items())),
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK carteles {READABLES}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
