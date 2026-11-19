#!/usr/bin/env python3
"""Elvenbane: la fortaleza élfica de Tibia clásico (7 pisos) con portal en la plaza del templo.

Se recrea la isla del oeste de Ab'Dendriel tal como está en los minimapas de TibiaWiki
(docs/items-and-map/img/elvenbane-ref/): el castillo sobre una isla al norte, la tierra firme con
bosque y montañas al sur, y el túnel del sótano que une la bajada de la entrada con el sótano bajo
el castillo. Las plantas salen del ASCII de referencia (elvenbane_ascii.md, 1 carácter = 1 sqm),
que este script lee y usa como máscara.

  z7  isla con el castillo (muralla, anillo de pasillo, patio, torre central, explanada al sur);
      agua con orilla alrededor; tierra firme al sur con bosque, montañas y la bajada a la cueva;
      llegada del portal del templo y portal de vuelta, junto a la bajada.
  z8  túnel largo N-S + sótano -1 bajo el castillo (sube al patio y baja al -2).
  z9  sótano -2 (sube al -1 y baja a la prisión).
  z10 prisión -3 (celdas al norte y al centro, sala grande al sur).
  z6  adarve: anillo de muralla + torre central, escaleras en las esquinas y en la torre.
  z5  4 torretas de esquina + torre central.
  z4  4 torretas + cima de la torre central (el dragón).

Caja: x 18-72, y 286-360 (z7) y las cajas de los pisos altos y bajos; la región estaba vacía en
z4-z10 (verificado) y el script se niega a escribir si pisa casillas existentes.

Uso (desde la raíz del repo):
  python3 scripts/map/generate-elvenbane.py --dry-run            # valida y no escribe
  python3 scripts/map/generate-elvenbane.py --preview docs/items-and-map/img/elvenbane
  python3 scripts/map/generate-elvenbane.py                      # escribe mapa, spawns y carteles
  python3 scripts/map/temple-portals.py                          # después: portal de la plaza
  python3 scripts/map/check-map-load.py

Re-ejecutable: borra sus cajas (z4-z10) y reemplaza los bloques ELVENBANE de spawns y carteles.
Backup test.otbm.bak-elvenbane la primera vez (no va a git). Doc: docs/items-and-map/MAPEAR_ELVENBANE.md.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import shutil
import struct
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import (KB_DIR, MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE,  # noqa: E402
                     load_otb, load_tiles, parse_tree, png_bytes, serialize_tree)

_spec = importlib.util.spec_from_file_location("north_pass", HERE / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MANIFEST = WORLD / "generated-elvenbane.json"
REF = REPO / "docs/items-and-map/img/elvenbane-ref"
ASCII_MD = REF / "elvenbane_ascii.md"

# --- piezas (ids de servidor que ya están en el mapa/kb) -----------------------------------------
GRASS, GRASS_COAST, WATER, STONE = 4756, 4526, 4608, 431
# "montañita" gris: ground 4566 rocks (el mismo que usa el mapa para las mesetas de roca);
# las paredes de roca 906 (norte) y 903 (oeste) le dan volumen, como en el mapa existente
ROCKS, ROCKS_EDGE_N, ROCKS_EDGE_W = 4566, 906, 903
DIRT, DIRT_ALT = 351, 352
ROCK = 101
WALL_V, WALL_H, WALL_POST, WALL_CORNER = 1049, 1050, 1051, 1053
# Escaleras: dos tipos de par (ver docs/gameplay/STAIRS.md y scripts de actions).
#   - clásico: 432 (stair down, arriba) + 1396 (wooden stairs, floorChangeNorth, abajo).
#     Al subir se llega a (x, y-1); al bajar, a (x, y+1).
#   - escalera de mano / buraco: 469 (hole, floorChangeDown) o 409 (ladder down) arriba +
#     1386 (ladder, LADDERS_UP) abajo. Al subir por 1386 se llega a (x, y+1); al bajar se cae
#     en la misma casilla (x, y) porque 1386 no está en STAIRS_LANDING (offset 0).
STAIRS_UP, STAIR_DOWN = 1396, 432
LADDER_UP, LADDER_DOWN, STONE_HOLE = 1386, 409, 469
DOWN_HOLE, DOWN_SAME = {STAIR_DOWN}, {LADDER_DOWN, STONE_HOLE}
UP_OFFSET = {STAIRS_UP: (0, -1), LADDER_UP: (0, 1)}
TELEPORT, ATTR_TELE_DEST, SIGN = 1387, 8, 1429
POISON = 1490                      # poison field (OTB: cid 2121, sólo block_pathfind)
TREE_BIG, TREE_SMALL = 4009, 2768
BUSHES = (2767, 2786)
FLOWERS = (4158, 4150, 2740)
STONE_ITEM = 1285
NEEDS_COUNT = {2320}
# orilla pasto<->agua: mismo set que generate-natural-island.py (border_sets "grass->water")
SHORE_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
SHORE_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
SHORE_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}
DIRS = {"nw": (-1, -1), "n": (0, -1), "ne": (1, -1), "w": (-1, 0), "e": (1, 0),
        "sw": (-1, 1), "s": (0, 1), "se": (1, 1)}
CARD = ((1, 0), (-1, 0), (0, 1), (0, -1))

# --- geometría -----------------------------------------------------------------------------------
X_CASTLE, Y_CASTLE = 40, 298          # esquina NO de la planta del castillo (21 x 18)
CW, CH = 21, 18
Z7, Z6, Z5, Z4, Z8, Z9, Z10 = 7, 6, 5, 4, 8, 9, 10
BOX7 = (4, 282, 84, 362)              # isla + tierra firme + agua
BOX8 = (30, 288, 67, 349)             # túnel + sótano -1
BOX9 = (33, 291, 67, 322)             # sótano -2
BOX10 = (33, 291, 67, 322)            # prisión -3
BOXT = (38, 296, 62, 317)             # pisos altos (z4-z6): castillo + 2
BOXS = {Z4: BOXT, Z5: BOXT, Z6: BOXT, Z7: BOX7, Z8: BOX8, Z9: BOX9, Z10: BOX10}

GROUND_CROP = (20, 8, 46, 33)         # cols/rows del ASCII ground -> x 37-63, y 295-320
ENTRANCE_CROP = (10, 21, 52, 50)      # cols/rows del ASCII entrance -> x 11-53, y 326-355
PLAN8 = (37, 295)                     # ASCII floor-1: col 3 -> x 40, row 3 -> y 298
# Celdas de la prisión (floor-3) que el minimapa dibuja cerradas: se les abre la puerta al pasillo
PRISON_DOORS = tuple((row, col) for row in (4, 11) for col in (2, 5, 8, 11))

# montañitas grises de la tierra firme: (x, y, ancho, alto) sobre el pasto, lejos del camino
KNOLLS = [(X_CASTLE - 9, Y_CASTLE + CH + 15, 4, 3),
          (X_CASTLE + 2, Y_CASTLE + CH + 20, 4, 3),
          (X_CASTLE - 9, Y_CASTLE + CH + 33, 5, 3)]


def west_arm() -> set:
    """Brazo de agua que entra desde el oeste, como el '~~~~' del ASCII entrance.

    Sale del agua de la caja (x 26) y se interna hacia el noreste subiendo, con la punta redondeada.
    """
    arm = set()
    for i in range(10):
        cx = X_CASTLE - 14 + i                  # 26 .. 35
        cy = Y_CASTLE + CH + 25 - int(round(i * 0.6))   # 341 .. 336
        for dy in (-1, 0, 1):
            arm.add((cx, cy + dy))
    for dx in (-1, 0, 1):                        # punta redondeada
        arm.add((X_CASTLE - 5 + dx, Y_CASTLE + CH + 20))
    return arm


WEST_ARM = west_arm()

ARRIVAL = (39, 346)                   # llegada del portal del templo
PORTALS_BACK = [(41, 347), (42, 347)]  # portales de vuelta al templo
TEMPLE_BACK = (157, 48, 7)            # llegada del portal 157,47,7 (temple-portals.py)
STAIR_ENTRY = (39, 340)               # bajada de la superficie al túnel (S del ASCII entrance)

# --- monstruos (nombres exactos de data/monster/monsters.xml) ------------------------------------
# (nombre, spawns, monstruos por spawn, respawn, zona)
HUNTS = {
    Z7: [
        ("Wasp", 2, 2, 90, "sur"), ("Orc", 2, 2, 90, "sur"), ("Orc Spearman", 1, 2, 90, "sur"),
        ("Elf", 1, 2, 90, "sur"), ("Elf Scout", 1, 1, 120, "sur"), ("Orc Warrior", 2, 2, 90, "sur"),
        ("Minotaur", 2, 2, 90, "castillo"), ("Orc Warrior", 2, 2, 90, "castillo"),
        ("Minotaur Guard", 1, 1, 120, "castillo"), ("Orc Berserker", 1, 1, 120, "castillo"),
    ],
    Z8: [("Troll", 2, 2, 90, None), ("Orc", 2, 2, 90, None), ("Orc Spearman", 1, 2, 90, None),
         ("Dwarf", 1, 1, 120, None), ("Minotaur", 1, 2, 90, None), ("Orc Warrior", 2, 2, 90, None)],
    Z9: [("Orc", 2, 2, 90, None), ("Minotaur", 2, 2, 90, None), ("Orc Warrior", 2, 2, 90, None)],
    Z10: [("Minotaur", 2, 2, 90, None), ("Orc Warrior", 2, 2, 90, None),
          ("Minotaur Guard", 2, 1, 120, None)],
    Z6: [("Minotaur", 2, 1, 90, None), ("Orc Warrior", 1, 1, 90, None)],
    Z5: [("Elf", 1, 1, 120, None), ("Elf Scout", 1, 1, 120, None), ("Orc Warrior", 1, 2, 90, None),
         ("Orc Shaman", 1, 1, 150, "torre"), ("Elf Arcanist", 1, 1, 150, "torre"),
         ("Dragon", 1, 1, 300, "torre")],
}
# Cimas (z4): un monstruo fuerte y distinto en cada torre, en la casilla más lejos de su escalera.
# Fijos (no sorteados), así cada torre tiene siempre el suyo. (nombre, (x, y), respawn)
TOWER_TOPS = [
    ("Black Knight", (43, 301), 900),   # torreta NO
    ("Dragon Lord", (59, 301), 900),    # torreta NE
    ("Hydra", (43, 314), 900),          # torreta SO
    ("Behemoth", (57, 314), 900),       # torreta SE
    ("Demon", (49, 308), 1800),         # cima de la torre central
]
GAP = 3                                # separación mínima entre centros de spawn

# --- escaleras: (etiqueta, piso de arriba, piso de abajo, (x, y) deseado, tipo) -------------------
# tipo: "ladder" = 409 (ladder down) + 1386 (escalera de mano) en las 18 conexiones;
#        "hole" = 469 + 1386, sólo el buraco de la entrada (cercado por 4 piedras 1285).
# Al usar 1386 se sube a (x, y+1, z-1); al bajar por 409 se cae en la misma casilla (offset 0).
LINKS = [
    ("entrada", Z7, Z8, STAIR_ENTRY, "hole"),
    ("sotano->patio", Z7, Z8, (X_CASTLE + 17, Y_CASTLE + 4), "ladder"),
    ("sotano->-2", Z8, Z9, (X_CASTLE + 17, Y_CASTLE + 15), "ladder"),
    ("-2->-3", Z9, Z10, (X_CASTLE + 2, Y_CASTLE + 14), "ladder"),
    ("patio->adarve NO", Z6, Z7, (X_CASTLE + 2, Y_CASTLE + 1), "ladder"),
    ("patio->adarve NE", Z6, Z7, (X_CASTLE + 17, Y_CASTLE + 1), "ladder"),
    ("patio->adarve SO", Z6, Z7, (X_CASTLE + 3, Y_CASTLE + 14), "ladder"),
    ("patio->adarve SE", Z6, Z7, (X_CASTLE + 17, Y_CASTLE + 14), "ladder"),
    ("torre->adarve", Z6, Z7, (X_CASTLE + 13, Y_CASTLE + 6), "ladder"),
    ("adarve->torreta NO", Z5, Z6, (X_CASTLE + 3, Y_CASTLE + 1), "ladder"),
    ("adarve->torreta NE", Z5, Z6, (X_CASTLE + 18, Y_CASTLE + 1), "ladder"),
    ("adarve->torreta SO", Z5, Z6, (X_CASTLE + 2, Y_CASTLE + 15), "ladder"),
    ("adarve->torreta SE", Z5, Z6, (X_CASTLE + 18, Y_CASTLE + 15), "ladder"),
    ("torre adarve->2", Z5, Z6, (X_CASTLE + 8, Y_CASTLE + 6), "ladder"),
    ("torreta NO->3", Z4, Z5, (X_CASTLE + 2, Y_CASTLE + 1), "ladder"),
    ("torreta NE->3", Z4, Z5, (X_CASTLE + 18, Y_CASTLE + 1), "ladder"),
    ("torreta SO->3", Z4, Z5, (X_CASTLE + 2, Y_CASTLE + 14), "ladder"),
    ("torreta SE->3", Z4, Z5, (X_CASTLE + 18, Y_CASTLE + 14), "ladder"),
    ("torre 2->3", Z4, Z5, (X_CASTLE + 13, Y_CASTLE + 5), "ladder"),
]


# ---------------------------------------------------------------- plantas del ASCII
def load_plans() -> dict[str, list[str]]:
    """Cada bloque del .md de referencia como lista de filas (1 char = 1 sqm)."""
    blocks: dict[str, list[str]] = {}
    cur = None
    for line in ASCII_MD.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^### Elvenbane_(\S+)", line)
        if m:
            cur = m.group(1)
            blocks[cur] = []
            continue
        if cur is not None:
            blocks[cur].append(line)
    plans = {}
    for key, rows in blocks.items():
        while rows and not rows[0].strip():
            rows.pop(0)
        while rows and not rows[-1].strip():
            rows.pop()
        width = max(len(r) for r in rows)
        plans[key] = [r.ljust(width) for r in rows]
    sizes = {"ground": (52, 61), "entrance": (51, 53), "floor-1": (48, 24), "floor-2": (18, 21),
             "floor-3": (18, 21), "floor1": (18, 21), "floor2": (18, 21), "floor3": (18, 21)}
    for key, want in sizes.items():
        got = (len(plans[key]), len(plans[key][0]))
        if got != want:
            raise SystemExit(f"ERROR: {ASCII_MD.name} bloque {key}: {got} != {want}")
    return plans


def wall_piece_set(walls: set) -> dict:
    """Pieza de pared según sus vecinas: la pared se dibuja en el borde sur y este."""
    out = {}
    for (x, y) in walls:
        west, north = (x - 1, y) in walls, (x, y - 1) in walls
        out[(x, y)] = (WALL_CORNER if west and north else WALL_H if west
                       else WALL_V if north else WALL_POST)
    return out


def tile(g, items=(), tele=None):
    return {"g": g, "it": list(items), "tele": tele}


# ---------------------------------------------------------------- superficie (z7)
def neighbors_in(mask, x, y) -> set[str]:
    return {d for d, (dx, dy) in DIRS.items() if (x + dx, y + dy) in mask}


def pieces_for(other, side, corner, inner):
    """Piezas de borde para una casilla a partir de dónde está el "otro" terreno."""
    card = other & {"n", "e", "s", "w"}
    if {"n", "s"} <= card or {"e", "w"} <= card:
        return None
    out = []
    if len(card) == 2:
        key = (next(c for c in card if c in "ns"), next(c for c in card if c in "ew"))
        out.append(corner[key])
    elif len(card) == 1:
        out.append(side[next(iter(card))])
    for diag, (a, b) in {"nw": ("n", "w"), "ne": ("n", "e"),
                         "sw": ("s", "w"), "se": ("s", "e")}.items():
        if diag in other and a not in card and b not in card:
            out.append(inner[diag])
    return out


def fix_coast(sea: set, cells: set, protect: set) -> set:
    """Agranda el agua hasta que toda casilla de tierra vecina tenga UNA pieza de orilla válida.

    Igual que `fix_until_valid` de generate-north-pass.py con el set de orilla; las casillas de
    `protect` (camino de la llegada) nunca se convierten en agua.
    """
    sea = set(sea)
    for _ in range(400):
        changed = False
        for (x, y) in list(sea):
            out = {d for d, (dx, dy) in DIRS.items() if (x + dx, y + dy) not in sea}
            if ({"n", "s"} <= out or {"e", "w"} <= out) and (x, y) not in protect:
                sea.discard((x, y))
                changed = True
        ring = {(x + dx, y + dy) for (x, y) in sea for dx, dy in DIRS.values()} - sea
        for c in ring:
            if c not in cells or c in protect:
                continue
            pcs = pieces_for(neighbors_in(sea, *c), SHORE_SIDE, SHORE_CORNER, SHORE_INNER)
            if pcs is None or len(pcs) > 1:
                sea.add(c)
                changed = True
        if not changed:
            return sea
    raise RuntimeError("la orilla no converge")


def components(mask: set) -> list[set]:
    out, seen = [], set()
    for start in sorted(mask):
        if start in seen:
            continue
        comp, q = {start}, deque([start])
        seen.add(start)
        while q:
            x, y = q.popleft()
            for dx, dy in CARD:
                n = (x + dx, y + dy)
                if n in mask and n not in seen:
                    seen.add(n)
                    comp.add(n)
                    q.append(n)
        out.append(comp)
    return out


def close_mask(s: set) -> set:
    big = s | {(x + dx, y + dy) for (x, y) in s for dx, dy in CARD}
    return {c for c in big if all((c[0] + dx, c[1] + dy) in big for dx, dy in CARD)}


def open_mask(s: set) -> set:
    return {c for c in s if all((c[0] + dx, c[1] + dy) in s for dx, dy in CARD)} | set()


def build_surface(plans, seed: int):
    """z7: isla del castillo (ASCII ground) + tierra firme al sur (ASCII entrance), con orilla."""
    rng = random.Random(seed)
    nz = NP.Noise(seed)
    x0, y0, x1, y1 = BOX7
    cells = {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    border = {c for c in cells if c[0] in (x0, x1) or c[1] in (y0, y1)}

    # 1) isla: máscara de tierra del ASCII 'ground' (la misma del minimapa de TibiaWiki),
    #    alineada al castillo que ya está en 40,298. Se queda sólo la masa que toca el castillo:
    #    así salen el lóbulo de bosque del noreste/este y la costa con entrantes de la referencia.
    G_OX, G_OY = X_CASTLE - 23, Y_CASTLE - 11      # (col 0, fila 0) del ASCII ground
    castle = {(x, y) for x in range(X_CASTLE, X_CASTLE + CW)
              for y in range(Y_CASTLE, Y_CASTLE + CH)}
    mask = set()
    for r in range(4, 34):
        row = plans["ground"][r]
        for c in range(10, 61):          # incluye la costa oeste (cols 10-22) y el brazo NE
            if c < len(row) and row[c] in "._TS#":
                mask.add((G_OX + c, G_OY + r))
    island = set(castle)
    for comp in components(mask):
        if comp & castle:
            island |= comp
    # la silueta del ASCII ya es irregular: no se come la costa (así el brazo NE llega a su punta)

    # 2) tierra firme: máscara del ASCII 'entrance' (pasto, árboles, roca y piedra), suavizada
    ec0, er0, ec1, er1 = ENTRANCE_CROP
    ex0 = STAIR_ENTRY[0] - (38 - ec0)
    ey0 = STAIR_ENTRY[1] - (35 - er0)
    main = set()
    for r, row in enumerate(range(er0, er1 + 1)):
        for c, col in enumerate(range(ec0, ec1 + 1)):
            if plans["entrance"][row][col] in "._^TS":
                pos = (ex0 + c, ey0 + r)
                if pos in cells:
                    main.add(pos)
    main = close_mask(main)                       # tapa los agujeros de 1 casilla del recorte
    water = cells - main
    for comp in components(water):                # charcos interiores chicos -> tierra
        if len(comp) < 12 and not (comp & border):
            main |= comp
    # 3) brazo de agua del oeste: el '~' que entra en el ASCII entrance corta la costa oeste
    main -= WEST_ARM

    # 3) lo que no se toca: llegada, portales, bajada, camino y castillo
    keep = {ARRIVAL, STAIR_ENTRY, *PORTALS_BACK}
    keep |= {(x, y) for x in range(STAIR_ENTRY[0] - 1, STAIR_ENTRY[0] + 2)
             for y in range(STAIR_ENTRY[1], ARRIVAL[1] + 2)}
    gate = [(x, y) for x in (X_CASTLE + 10, X_CASTLE + 11)
            for y in range(Y_CASTLE + CH, Y_CASTLE + CH + 4)]
    keep |= set(gate)
    castle = {(x, y) for x in range(X_CASTLE, X_CASTLE + CW)
              for y in range(Y_CASTLE, Y_CASTLE + CH)}
    keep |= castle

    land = island | main | keep

    # 3b) fuera las casillas de tierra totalmente aisladas (no se tocan las puntas del brazo)
    for _ in range(3):
        lone = {p for p in land if p not in keep
                and not any((p[0] + dx, p[1] + dy) in land for dx, dy in CARD)}
        if not lone:
            break
        land -= lone

    # 4) fuera los islotes sueltos que deja el recorte
    for comp in components(land):
        if len(comp) < 8 and not (comp & keep):
            land -= comp

    # 5) orilla: el agua se ajusta hasta que cada casilla de tierra tenga una única pieza, y los
    #    islotes que quedan (rodeados de orilla, sin entrada) pasan a agua
    sea = cells - land
    for _ in range(6):
        sea = fix_coast(sea, cells, keep)
        land = cells - sea
        islets = [c for c in components(land) if len(c) < 14 and not (c & keep)]
        if not islets:
            break
        for c in islets:
            sea |= c
    land = cells - sea

    # 6) montañitas: meseta de roca (4566) con pared 906 al norte y 903 al oeste
    mountain = set()
    for (mx, my, mw, mh) in KNOLLS:
        cx, cy = mx + (mw - 1) / 2, my + (mh - 1) / 2          # meseta ovalada, no un rectángulo
        rx, ry = mw / 2, mh / 2
        blob = {(x, y) for x in range(mx, mx + mw) for y in range(my, my + mh)
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0}
        if blob <= land and not any(neighbors_in(sea, x, y) for (x, y) in blob) and not (blob & keep):
            mountain |= blob

    # 7) castillo: muro, anillo de piedra, patio de pasto y torre central
    walls = {(X_CASTLE + x, Y_CASTLE + y)
             for y, row in enumerate(plans["ground"][11:29])
             for x, ch in enumerate(row[23:44]) if ch == "#"}
    pieces = wall_piece_set(walls)
    override = {(x, y): tile(STONE) for (x, y) in gate}
    for y, row in enumerate(plans["ground"][11:29]):
        for x, ch in enumerate(row[23:44]):
            pos = (X_CASTLE + x, Y_CASTLE + y)
            if ch == "#":
                override[pos] = tile(GRASS if (y == 0 or x == 0) else STONE, [pieces[pos]])
            elif ch in "_S":
                override[pos] = tile(STONE)
            elif ch == ".":
                override[pos] = tile(GRASS)

    # 8) suelos (se recalcula si hay que abrir agua en los bolsones sin salida)
    island_box = {(x, y) for x in range(X_CASTLE - 3, X_CASTLE + CW + 6)
                  for y in range(Y_CASTLE - 3, Y_CASTLE + CH + 6)}

    def grounds() -> dict:
        g = {}
        for c in cells:
            if c not in land:
                g[c] = tile(WATER)
                continue
            if c in mountain:
                edge = []
                if (c[0], c[1] - 1) not in mountain:
                    edge.append(ROCKS_EDGE_N)
                if (c[0] - 1, c[1]) not in mountain:
                    edge.append(ROCKS_EDGE_W)
                g[c] = tile(ROCKS, edge)
                continue
            if c in override:
                g[c] = override[c]
                continue
            coast = pieces_for(neighbors_in(sea, *c), SHORE_SIDE, SHORE_CORNER, SHORE_INNER) or []
            g[c] = tile(GRASS_COAST if coast else GRASS, coast)
        return g

    t = grounds()
    # 9) bolsones: un pedazo de pasto rodeado de orilla (que bloquea) no se puede pisar; se
    #    convierte en agua y se recalcula la orilla. El castillo y su isla quedan aparte.
    for _ in range(20):
        walk = {c for c, cell in t.items() if walk_tile(cell)}
        comps = components(walk)
        main_comp = next((c for c in comps if (ARRIVAL[0], ARRIVAL[1]) in c), set())
        pockets = [c for c in comps if c is not main_comp and not (c & island_box)]
        if not pockets:
            break
        blob = set()
        for comp in pockets:
            for (px, py) in comp:
                blob |= {(px + dx, py + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        blob = (blob & land) - keep
        if not blob:
            break
        land -= blob
        sea |= blob
        sea = fix_coast(sea, cells, keep)
        land = cells - sea
        t = grounds()

    # 9) claro: SÓLO el corredor que une la bajada con la llegada y los portales, más su anillo de
    #    piedra. El resto de la tierra firme es bosque (sin prados).
    clear = {ARRIVAL, STAIR_ENTRY, *PORTALS_BACK}
    clear |= {(STAIR_ENTRY[0], y) for y in range(STAIR_ENTRY[1], ARRIVAL[1] + 1)}
    clear |= {(x, y) for x in range(ARRIVAL[0], PORTALS_BACK[1][0] + 1) for y in (346, 347)}
    clear |= {(STAIR_ENTRY[0] - 1, STAIR_ENTRY[1]), (STAIR_ENTRY[0] + 1, STAIR_ENTRY[1])}
    px0, px1, py = PORTALS_BACK[0][0], PORTALS_BACK[1][0], PORTALS_BACK[0][1]
    clear |= {(px1 + 1, py), (px0 - 1, py + 1), (px1 + 1, py + 1),
              (px0, py + 1), (px1, py + 1), (px0 - 1, py - 1), (px1 + 1, py - 1)}
    clear |= {(x, y) for x in range(X_CASTLE + 9, X_CASTLE + 13) for y in range(Y_CASTLE + CH - 1, Y_CASTLE + CH + 1)}

    # 10) bosque denso pero respirable: árboles grandes separados >= 2, y arbustos/pasto entre medio.
    #     El patio del castillo (todo lo que queda dentro de la muralla) va limpio: sólo pasto y piedra.
    forest = {c for c in t if t[c]["g"] in (GRASS, GRASS_COAST)
              and c not in clear and c not in castle}
    anchors = set()                               # ancla (esquina SE) de cada pino 2x2
    blockers = set()                              # casillas con algo que bloquea
    island_zone = island - castle                 # franja de la isla (angosta: ahí no se apelmaza)
    order = sorted(forest, key=lambda c: (c[1], c[0]))
    rng.shuffle(order)
    for pos in order:
        x, y = pos
        # pino 2x2 con separación Chebyshev >= 3 entre anclas: las copas no se tocan
        # separación Chebyshev >= 2 entre anclas: las copas 2x2 se tocan pero no se superponen
        near = any((x + dx, y + dy) in anchors for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        # el resto de la vegetación que bloquea no se pega a otra que bloquee: así el pasto
        # queda siempre transitable (no se forman bolsones) y el bosque se ve lleno pero respirable
        glued = any((x + dx, y + dy) in blockers for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        if (not near and rng.random() < 0.92
                and all((x - a, y - b) in forest for a in (0, 1) for b in (0, 1))):
            t[pos]["it"].append(TREE_BIG)          # se ve en 4 casillas, bloquea 1
            anchors.add(pos)
            blockers.add(pos)
        elif not glued and rng.random() < 0.55:
            t[pos]["it"].append(TREE_SMALL)
            blockers.add(pos)
        elif not glued and rng.random() < 0.45:
            t[pos]["it"].append(rng.choice(BUSHES))
            blockers.add(pos)
        elif rng.random() < 0.40:
            t[pos]["it"].append(rng.choice(FLOWERS))

    # 11) portales de vuelta, enmarcados; bajada a la cueva
    for pos in PORTALS_BACK:
        t[pos] = tile(GRASS, [TELEPORT], TEMPLE_BACK)
    px0, px1, py = PORTALS_BACK[0][0], PORTALS_BACK[1][0], PORTALS_BACK[0][1]
    for pos in ((px1 + 1, py), (px0 - 1, py + 1), (px1 + 1, py + 1),
                (px0, py + 1), (px1, py + 1), (px0 - 1, py - 1), (px1 + 1, py - 1)):
        base = t[pos]["g"] if pos in t and t[pos]["g"] != WATER else GRASS
        t[pos] = tile(base, [STONE_ITEM])
    t[STAIR_ENTRY] = tile(GRASS)          # el hueco lo pone la escalera (LINKS)
    # el buraco de la entrada va cercado por 4 piedras (1285) y el sur queda libre: es el
    # aterrizaje de la escalera de mano (1386 sube a x, y+1)
    stones = {(STAIR_ENTRY[0] + dx, STAIR_ENTRY[1] + dy)
              for dx, dy in ((-1, 0), (1, 0), (-1, -1), (1, -1))}
    for pos in stones:
        t[pos] = tile(GRASS, [STONE_ITEM])
    t[(STAIR_ENTRY[0], STAIR_ENTRY[1] + 1)] = tile(GRASS)
    t[(STAIR_ENTRY[0], STAIR_ENTRY[1] - 1)] = tile(GRASS)

    # 12) carteles
    sign_1 = (ARRIVAL[0] - 2, ARRIVAL[1] + 1)
    sign_2 = (STAIR_ENTRY[0] + 2, STAIR_ENTRY[1] + 1)
    t[sign_1] = tile(GRASS, [SIGN])
    t[sign_2] = tile(GRASS, [SIGN])
    signs = {sign_1: "ELVENBANE\nFortaleza elfica en 7 pisos.\nBaja a la cueva: el tunel llega\n"
                     "al sotano del castillo.\nPortal al norte: templo.",
             sign_2: "BAJADA A ELVENBANE\nTunel largo hasta el sotano.\nTrolls, orcos y enanos."}
    return t, {"signs": signs, "castle_walls": walls, "mountains": mountain, "forest": forest,
               "no_coast": set(override) | mountain, "stones": stones}


# ---------------------------------------------------------------- sótanos y pisos altos
def build_dungeon(plans, key, z, origin, floor_id, doors=()):
    """Sótano a partir de una planta ASCII: '=' piso, '#' pared, '^' roca, 'S' escalera.

    `doors`: (fila, columna) de la planta que se abren como piso aunque el ASCII tenga pared
    (las celdas de la prisión del -3 están cerradas en el minimapa; se les abre la puerta al pasillo).
    """
    plan = plans[key]
    ox, oy = origin
    t, floor, walls = {}, set(), set()
    for r, row in enumerate(plan):
        for c, ch in enumerate(row):
            pos = (ox + c, oy + r)
            if ch in "=S" or (r, c) in doors:
                floor.add(pos)
            elif ch == "^":
                floor.add(pos)
            elif ch == "#":
                walls.add(pos)
    walls -= floor
    for (x, y) in sorted(floor):                    # pared alrededor de todo el piso
        for dx, dy in DIRS.values():
            pos = (x + dx, y + dy)
            if pos not in floor:
                walls.add(pos)
    pieces = wall_piece_set(walls)
    for pos in sorted(floor):
        t[pos] = tile(floor_id)
    for r, row in enumerate(plan):
        for c, ch in enumerate(row):
            if ch == "^":
                t[(ox + c, oy + r)] = tile(floor_id, [STONE_ITEM])
    for pos in sorted(walls):
        t[pos] = tile(DIRT_ALT, [pieces[pos]])
    x0, y0, x1, y1 = BOXS[z]
    for y in range(max(y0, min(b for _, b in t) - 8), min(y1, max(b for _, b in t) + 8) + 1):
        for x in range(max(x0, min(a for a, _ in t) - 8), min(x1, max(a for a, _ in t) + 8) + 1):
            t.setdefault((x, y), tile(ROCK))
    return t


def build_adarve(plans, key, floor_id):
    """Piso alto del castillo: '#' pared, '_' piso, 'S' escalera, ' ' vacío (no hay tile)."""
    plan = plans[key]
    walls = {(x, y) for y, row in enumerate(plan) for x, ch in enumerate(row) if ch == "#"}
    pieces = wall_piece_set(walls)
    t = {}
    for y, row in enumerate(plan):
        for x, ch in enumerate(row):
            pos = (X_CASTLE + x, Y_CASTLE + y)
            if ch == "#":
                outside = (x == 0 or y == 0 or plan[y][x - 1] == " " or plan[y - 1][x] == " ")
                t[pos] = tile(None if outside else floor_id, [pieces[(x, y)]])
            elif ch in "_S":
                t[pos] = tile(floor_id)
    return t


# ---------------------------------------------------------------- poison fields
def add_poison_fields(plans, layers) -> list:
    """Poison field 1490 en todo el interior de la torre central en z6 (primer piso de la torre).

    La quest clásica dice que el primer piso de la torre está cubierto de poison fields; van sólo
    en las casillas caminables del interior de la torre (no en las torretas ni en el anillo del
    adarve) y nunca encima de una escalera.
    """
    plan = plans["floor1"]
    placed = []
    for r in range(5, 10):                       # interior de la torre en la planta (filas 5-9)
        for c in range(8, 14):                   # columnas 8-13
            if c >= len(plan[r]) or plan[r][c] != "_":
                continue
            pos = (X_CASTLE + c, Y_CASTLE + r)
            cell = layers[Z6].get(pos)
            if cell is None or not walk_tile(cell) or is_stair(cell):
                continue
            if POISON not in cell["it"]:
                cell["it"].append(POISON)
                placed.append(pos)
    return placed


# ---------------------------------------------------------------- escaleras
def walk_tile(cell) -> bool:
    if cell is None or cell["g"] is None:
        return False
    if cell["g"] in OTB_BLOCK:
        return False
    return not any(i in OTB_BLOCK for i in cell["it"])


def is_stair(cell) -> bool:
    if cell is None:
        return False
    return (cell["g"] in DOWN_HOLE | DOWN_SAME
            or any(i in (STAIRS_UP, LADDER_UP) for i in cell["it"]))


def stair_landings(kind: str, p):
    """(llegada al subir en el piso de arriba, llegada al bajar en el de abajo)."""
    x, y = p
    if kind == "stairs":
        return (x, y - 1), (x, y + 1)
    return (x, y + 1), (x, y)


def resolve_stair(upper: dict, lower: dict, zu: int, zl: int, wish, used: dict, label: str, kind: str):
    """Encuentra la casilla de la escalera entre dos pisos, cerca de donde la pide el ASCII."""
    cands = sorted(lower, key=lambda p: (abs(p[0] - wish[0]) + abs(p[1] - wish[1]),
                                         p[1] - wish[1], p[0] - wish[0]))
    for p in cands:
        if abs(p[0] - wish[0]) + abs(p[1] - wish[1]) > 8:
            break
        up, low = upper.get(p), lower.get(p)
        if not walk_tile(up) or not walk_tile(low) or is_stair(up) or is_stair(low):
            continue
        up_land, low_land = stair_landings(kind, p)
        up_cell, low_cell = upper.get(up_land), lower.get(low_land)
        if not walk_tile(up_cell) or not walk_tile(low_cell):
            continue
        if is_stair(up_cell) or is_stair(low_cell):
            continue
        if (p in used.setdefault(zu, set()) or up_land in used[zu]
                or p in used.setdefault(zl, set()) or low_land in used[zl]):
            continue
        used[zu].update({p, up_land})
        used[zl].update({p, low_land})
        return p
    raise SystemExit(f"ERROR: no hay casilla para la escalera {label} cerca de {wish}")


def place_stair(upper: dict, lower: dict, p, kind: str):
    up = upper[p]
    up["g"] = {"stairs": STAIR_DOWN, "hole": STONE_HOLE, "ladder": LADDER_DOWN}[kind]
    up["it"] = []
    up["tele"] = None
    lower[p]["it"].append(LADDER_UP if kind != "stairs" else STAIRS_UP)


# ---------------------------------------------------------------- OTBM
def item_node(iid: int, tele=None):
    props = bytearray(struct.pack("<H", iid))
    if iid in NEEDS_COUNT:
        props.append(1)
    if tele is not None:
        props += bytes([ATTR_TELE_DEST]) + struct.pack("<HHB", *tele)
    return [T_ITEM, props, []]


def new_tile(x: int, y: int, bx: int, by: int, cell: dict):
    props = bytearray([x - bx, y - by])
    if cell["g"] is not None:
        props += bytes([9]) + struct.pack("<H", cell["g"])
        if cell["g"] in NEEDS_COUNT:
            props.append(1)
    kids = [item_node(i, cell["tele"] if i == TELEPORT else None) for i in cell["it"]]
    return [T_TILE, props, kids]


def write_otbm(layers: dict):
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    md = root[2][0]
    backup = MAP.with_name(MAP.name + ".bak-elvenbane")
    if not backup.exists():
        shutil.copy2(MAP, backup)

    def gone(x, y, z):
        if z not in BOXS:
            return False
        x0, y0, x1, y1 = BOXS[z]
        return x0 <= x <= x1 and y0 <= y <= y1

    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        area[2] = [tl for tl in area[2]
                   if not (tl[0] in (T_TILE, T_HOUSETILE) and gone(ax + tl[1][0], ay + tl[1][1], az))]
        if not area[2]:
            md[2].remove(area)

    buckets: dict = {}
    for z, tl in layers.items():
        for (x, y), cell in tl.items():
            buckets.setdefault((x & ~0xFF, y & ~0xFF, z), []).append((x, y, cell))
    for (bx, by, z), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, z)), []]
        for x, y, cell in sorted(lst, key=lambda r: (r[1], r[0])):
            area[2].append(new_tile(x, y, bx, by, cell))
        md[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))


# ---------------------------------------------------------------- validación
def descent_target(cell, x, y, z):
    """A dónde lleva pisar/usar una bajada (hueco o escalera de mano)."""
    if cell is None:
        return None
    if cell["g"] in DOWN_HOLE:                   # 432: se cae al sur
        return (x, y + 1, z + 1)
    if cell["g"] in DOWN_SAME:                   # 409 / 469: se cae en la misma casilla
        return (x, y, z + 1)
    return None


def bfs(layers: dict, start):
    """Alcanzabilidad multi-piso: casillas caminables + escaleras, huecos y escaleras de mano."""
    seen, q = {start}, deque([start])
    while q:
        x, y, z = q.popleft()
        cell = layers[z].get((x, y))
        if cell is None:
            continue
        down = descent_target(cell, x, y, z)
        if down is not None:
            if down[2] in layers and walk_tile(layers[down[2]].get(down[:2])) and down not in seen:
                seen.add(down)
                q.append(down)
            continue
        for item, (dx, dy) in UP_OFFSET.items():
            if item in cell["it"]:
                n = (x + dx, y + dy, z - 1)
                if n[2] in layers and walk_tile(layers[n[2]].get(n[:2])) and n not in seen:
                    seen.add(n)
                    q.append(n)
        for dx, dy in CARD:
            n = (x + dx, y + dy, z)
            nc = layers[z].get((n[0], n[1]))
            if nc is None or not walk_tile(nc):
                continue
            down = descent_target(nc, n[0], n[1], z)
            if down is not None:                 # pisar la bajada: se cae al piso de abajo
                if down[2] in layers and walk_tile(layers[down[2]].get(down[:2])) and down not in seen:
                    seen.add(down)
                    q.append(down)
                continue
            if n not in seen:
                seen.add(n)
                q.append(n)
    return seen


def open_pockets(t7: dict, layers: dict, start, protect=frozenset()):
    """Deja el bosque transitable sacando árboles/arbustos de los bolsones que queden sin salida.

    Nunca cambia el terreno ni saca piezas de orilla (4644-4655): sólo tala el árbol o arbusto
    que encierra una casilla de pasto.
    """
    opened = []
    reach = bfs(layers, start)
    for _ in range(800):
        reach7 = {(x, y) for x, y, z in reach if z == Z7}
        lost = {p for p, c in t7.items() if walk_tile(c) and not is_stair(c)} - reach7
        if not lost:
            break
        progress = False
        for pos in sorted(lost):
            for dx, dy in CARD:
                n = (pos[0] + dx, pos[1] + dy)
                cell = t7.get(n)
                if not cell or cell["g"] in OTB_BLOCK or n in protect:
                    continue
                keep_pieces = [i for i in cell["it"] if i not in OTB_BLOCK or 4644 <= i <= 4655]
                if len(keep_pieces) != len(cell["it"]):
                    cell["it"] = keep_pieces
                    opened.append(n)
                    progress = True
                    break
            if progress:
                break
        if not progress:
            break
        reach = bfs(layers, start)
    return opened


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def place_hunts(layers: dict, walkbyz: dict, avoid: dict, seed: int):
    rng = random.Random(seed + 9001)
    out, centers = [], {}
    for z, spec in HUNTS.items():
        walk = walkbyz[z]
        for name, nspawn, per, spawntime, zone in spec:
            pool = sorted(walk - avoid[z])
            if zone == "sur":
                pool = [c for c in pool if c[1] >= Y_CASTLE + CH + 6]
            elif zone == "castillo":
                pool = [c for c in pool if X_CASTLE < c[0] < X_CASTLE + CW - 1
                        and Y_CASTLE < c[1] < Y_CASTLE + CH - 1]
            elif zone == "torre":
                pool = [c for c in pool if 5 <= c[0] - X_CASTLE <= 15 and 4 <= c[1] - Y_CASTLE <= 12]
            elif zone == "torreta":
                pool = [c for c in pool if not (5 <= c[0] - X_CASTLE <= 15
                                                and 4 <= c[1] - Y_CASTLE <= 12)]
            rng.shuffle(pool)
            placed = 0
            for c in pool:
                if placed >= nspawn:
                    break
                if any(abs(c[0] - o[0]) + abs(c[1] - o[1]) < GAP for o in centers.get(z, [])):
                    continue
                spots = [(c[0] + dx, c[1] + dy) for dx in range(-1, 2) for dy in range(-1, 2)
                         if (c[0] + dx, c[1] + dy) in walk and (c[0] + dx, c[1] + dy) not in avoid[z]]
                if len(spots) < per:
                    continue
                rng.shuffle(spots)
                centers.setdefault(z, []).append(c)
                out.append((c, z, [(name, s, spawntime) for s in spots[:per]]))
                placed += 1
            if placed < nspawn:
                print(f"aviso: {name} z{z}: {placed}/{nspawn} spawns", file=sys.stderr)
    for name, (x, y), spawntime in TOWER_TOPS:
        out.append(((x, y), Z4, [(name, (x, y), spawntime)]))
    return out


def render_floor(layers: dict, z: int, path: Path, scale: int = 3):
    facts = json.loads((KB_DIR / "facts.json").read_text(encoding="utf-8"))["items"]
    mm = {int(k): v.get("minimap_color") for k, v in facts.items()}
    x0, y0, x1, y1 = BOXS[z]
    w, h = x1 - x0 + 1, y1 - y0 + 1
    img = bytearray(b"\x10\x10\x14\xff" * (w * h))
    for (x, y), cell in layers[z].items():
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        color = None
        for sid in ([cell["g"]] if cell["g"] else []) + cell["it"]:
            if mm.get(sid) is not None:
                color = mm[sid]
        if color is None:
            continue
        o = ((y - y0) * w + (x - x0)) * 4
        img[o:o + 4] = bytes(((color // 36) % 6 * 51, (color // 6) % 6 * 51, color % 6 * 51, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes(w, h, bytes(img), scale=scale))


# ---------------------------------------------------------------- principal
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=76)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path, help="carpeta donde dibujar z4.png .. z10.png")
    ap.add_argument("--force", action="store_true",
                    help="escribe aunque haya casillas ajenas en la caja (solo para recuperar)")
    a = ap.parse_args()

    global OTB_BLOCK
    otb = load_otb()
    OTB_BLOCK = {sid for sid, rec in otb.items() if "block_solid" in rec["flags"]}

    plans = load_plans()
    surf, info = build_surface(plans, a.seed)
    layers = {
        Z7: surf,
        Z8: build_dungeon(plans, "floor-1", Z8, PLAN8, DIRT),
        Z9: build_dungeon(plans, "floor-2", Z9, (X_CASTLE, Y_CASTLE), DIRT),
        Z10: build_dungeon(plans, "floor-3", Z10, (X_CASTLE, Y_CASTLE), DIRT, doors=PRISON_DOORS),
        Z6: build_adarve(plans, "floor1", STONE),
        Z5: build_adarve(plans, "floor2", STONE),
        Z4: build_adarve(plans, "floor3", STONE),
    }

    poison = add_poison_fields(plans, layers)

    used: dict = {}
    stairs, moved = [], []
    for label, zu, zl, wish, kind in LINKS:
        p = resolve_stair(layers[zu], layers[zl], zu, zl, wish, used, label, kind)
        if p != wish:
            moved.append((label, wish, p))
        place_stair(layers[zu], layers[zl], p, kind)
        stairs.append((label, zu, zl, p, kind))

    # --- validaciones ---
    errors = []
    opened = open_pockets(layers[Z7], layers, (ARRIVAL[0], ARRIVAL[1], Z7), info["stones"])
    walkbyz = {z: {p for p, c in tl.items() if walk_tile(c)} for z, tl in layers.items()}
    reach = bfs(layers, (ARRIVAL[0], ARRIVAL[1], Z7))
    for z in sorted(layers):
        walk = {p for p, c in layers[z].items() if walk_tile(c) and not is_stair(c)}
        lost = walk - {(x, y) for x, y, zz in reach if zz == z}
        if lost:
            errors.append(f"z{z}: {len(lost)} casillas caminables inalcanzables, p.ej. {sorted(lost)[:5]}")
    if (ARRIVAL[0], ARRIVAL[1], Z7) not in reach:
        errors.append("la llegada no es caminable")
    for pos in PORTALS_BACK:
        if not any((pos[0] + dx, pos[1] + dy, Z7) in reach for dx, dy in CARD):
            errors.append(f"portal de vuelta {pos} sin acceso")
    # ninguna escalera comparte casilla con otra y los destinos son válidos
    seen_stairs = set()
    expected_up = {"stairs": STAIR_DOWN, "hole": STONE_HOLE, "ladder": LADDER_DOWN}
    expected_low = {"stairs": STAIRS_UP, "hole": LADDER_UP, "ladder": LADDER_UP}
    for label, zu, zl, p, kind in stairs:
        if (zu, p) in seen_stairs:
            errors.append(f"escalera {label} repite casilla {p} en z{zu}")
        seen_stairs.add((zu, p))
        up_cell, low_cell = layers[zu].get(p), layers[zl].get(p)
        if not up_cell or up_cell["g"] != expected_up[kind]:
            errors.append(f"escalera {label}: arriba {p},{zu} no es {expected_up[kind]}")
        if not low_cell or expected_low[kind] not in low_cell["it"]:
            errors.append(f"escalera {label}: abajo {p},{zl} no tiene {expected_low[kind]}")
        up_land, low_land = stair_landings(kind, p)
        if not walk_tile(layers[zu].get(up_land)):
            errors.append(f"escalera {label}: llegada al subir {up_land},{zu} no caminable")
        if not walk_tile(layers[zl].get(low_land)):
            errors.append(f"escalera {label}: llegada al bajar {low_land},{zl} no caminable")
    # z7: nada de ground 919 (se dibuja como vacío negro) y orilla exacta en todo el pasto
    if any(c["g"] == 919 for c in layers[Z7].values()):
        errors.append("z7: quedaron casillas con ground 919 (se ven negras)")
    sea7 = {p for p, c in layers[Z7].items() if c["g"] == WATER}
    bad_coast = 0
    for p, c in layers[Z7].items():
        if c["g"] not in (GRASS, GRASS_COAST) or p in info["no_coast"]:
            continue
        want = sorted(pieces_for(neighbors_in(sea7, *p), SHORE_SIDE, SHORE_CORNER, SHORE_INNER) or [])
        have = sorted(i for i in c["it"] if 4644 <= i <= 4655)
        if want != have:
            bad_coast += 1
    if bad_coast:
        errors.append(f"z7: {bad_coast} casillas de pasto con la orilla mal puesta")

    # desde cualquier casilla caminable de z7 no se ve el vacío del borde de la caja
    x0, y0, x1, y1 = BOX7
    for (x, y) in walkbyz[Z7]:
        if x - 7 < x0 or x + 7 > x1 or y - 5 < y0 or y + 5 > y1:
            errors.append(f"z7 {(x, y)}: se ve el borde de la caja")
            break
    # spawns sobre piso caminable
    avoid = {z: set() for z in layers}
    avoid[Z7] |= {(ARRIVAL[0] + dx, ARRIVAL[1] + dy) for dx in range(-3, 4) for dy in range(-3, 4)}
    avoid[Z7] |= {(x + dx, y + dy) for x, y in PORTALS_BACK for dx in range(-2, 3) for dy in range(-2, 3)}
    for label, zu, zl, p, kind in stairs:
        up_land, low_land = stair_landings(kind, p)
        avoid[zu] |= {p, up_land}
        avoid[zl] |= {p, low_land}
    spawns = place_hunts(layers, walkbyz, avoid, a.seed)
    for (cx, cy), z, mons in spawns:
        for name, pos, _st in mons:
            if not walk_tile(layers[z].get(pos)) or layers[z][pos]["g"] == STAIR_DOWN:
                errors.append(f"spawn {name} en {pos},{z}: casilla no caminable")

    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        return 1

    counts: dict = {}
    for _c, z, mons in spawns:
        for name, _p, _st in mons:
            counts[(z, name)] = counts.get((z, name), 0) + 1
    print(f"Elvenbane: caja z7 x{BOX7[0]}-{BOX7[2]} y{BOX7[1]}-{BOX7[3]}; castillo "
          f"{X_CASTLE},{Y_CASTLE} {CW}x{CH}")
    forest7 = info["forest"]
    blk = [p for p in forest7 if any(i in OTB_BLOCK for i in layers[Z7][p]["it"])]
    print(f"  bosque z7: {len(forest7)} casillas de bosque, {len(blk)} con bloqueo "
          f"({100 * len(blk) // max(1, len(forest7))} %)")
    for z in sorted(layers):
        tl = layers[z]
        print(f"  z{z}: {len(tl)} casillas, {sum(1 for c in tl.values() if walk_tile(c))} caminables, "
              f"caja x{BOXS[z][0]}-{BOXS[z][2]} y{BOXS[z][1]}-{BOXS[z][3]}")
    for label, zu, zl, p, kind in stairs:
        print(f"  escalera {label} [{kind}]: arriba {p[0]},{p[1]},{zu} / abajo {p[0]},{p[1]},{zl}")
    for label, wish, got in moved:
        print(f"  reubicada {label}: {wish} -> {got}")
    if opened:
        print(f"  despejados z7: {len(opened)} árboles/arbustos que cortaban el paso")
    print(f"llegada {ARRIVAL[0]},{ARRIVAL[1]},7; portales de vuelta "
          f"{', '.join(f'{x},{y},7' for x, y in PORTALS_BACK)} -> {TEMPLE_BACK}")
    print(f"spawns: {len(spawns)} ({sum(counts.values())} monstruos)")
    for (z, name), n in sorted(counts.items()):
        print(f"  z{z} {name}: {n}")

    if a.preview:
        for z in sorted(layers):
            render_floor(layers, z, a.preview / f"z{z}.png")
        print(f"preview: {a.preview}")

    # la primera vez la caja tiene que estar vacía: no se pisa terreno de nadie
    if not a.force and not MANIFEST.exists():
        clash = [pos for pos in load_tiles()
                 if pos[2] in BOXS and (lambda b: b[0] <= pos[0] <= b[2] and b[1] <= pos[1] <= b[3])(BOXS[pos[2]])]
        if clash:
            print(f"ERROR: {len(clash)} casillas ya existen en la caja (p.ej. {sorted(clash)[:5]}); "
                  f"no se escribe nada (--force para pisar)", file=sys.stderr)
            return 1
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    write_otbm(layers)

    sp = SPAWNS.read_text(encoding="latin-1")
    sp = re.sub(r"[ \t]*<!-- BEGIN ELVENBANE_SPAWNS.*?<!-- END ELVENBANE_SPAWNS -->\n?", "", sp, flags=re.S)
    block = ("\t<!-- BEGIN ELVENBANE_SPAWNS (scripts/map/generate-elvenbane.py) -->\n"
             + spawn_xml(spawns) + "\n\t<!-- END ELVENBANE_SPAWNS -->\n")
    SPAWNS.write_text(sp.replace("</spawns>", block + "</spawns>"), encoding="latin-1")

    rd = READABLES.read_text(encoding="latin-1")
    rd = re.sub(r"\t?<!-- BEGIN ELVENBANE_SIGNS -->.*?<!-- END ELVENBANE_SIGNS -->\n?", "", rd, flags=re.S)
    lines = ["\t<!-- BEGIN ELVENBANE_SIGNS -->"]
    for (x, y), text in sorted(info["signs"].items()):
        lines.append(f'\t<readable x="{x}" y="{y}" z="7" text="{text.replace(chr(10), chr(92) + "n")}"/>')
    lines.append("\t<!-- END ELVENBANE_SIGNS -->\n")
    READABLES.write_text(rd.replace("</readables>", "\n".join(lines) + "</readables>"), encoding="latin-1")

    MANIFEST.write_text(json.dumps({
        "name": "generated-elvenbane", "seed": a.seed,
        "box": {"x1": BOX7[0], "y1": BOX7[1], "x2": BOX7[2], "y2": BOX7[3],
                "z": [Z4, Z5, Z6, Z7, Z8, Z9, Z10]},
        "boxes": {str(z): {"x1": BOXS[z][0], "y1": BOXS[z][1], "x2": BOXS[z][2], "y2": BOXS[z][3]}
                  for z in sorted(BOXS)},
        "castle": {"x": X_CASTLE, "y": Y_CASTLE, "w": CW, "h": CH},
        "landing": {"x": ARRIVAL[0], "y": ARRIVAL[1], "z": Z7},
        "portalsBack": [{"x": x, "y": y, "z": Z7, "to": list(TEMPLE_BACK)} for x, y in PORTALS_BACK],
        "stairs": [{"label": label, "kind": kind, "x": p[0], "y": p[1], "holeZ": zu, "upZ": zl,
                    "upLanding": {"x": stair_landings(kind, p)[0][0], "y": stair_landings(kind, p)[0][1], "z": zu},
                    "downLanding": {"x": stair_landings(kind, p)[1][0], "y": stair_landings(kind, p)[1][1], "z": zl}}
                   for label, zu, zl, p, kind in stairs],
        "relocated": [{"label": l, "wish": list(w), "got": list(g)} for l, w, g in moved],
        "openedPassages": [list(p) for p in opened],
        "spawns": {f"z{z}": sum(1 for _c, zz, _m in spawns if zz == z) for z in sorted(layers)},
        "monsters": {f"z{z}/{name}": n for (z, name), n in sorted(counts.items())},
        "counts": {"spawns": len(spawns), "monsters": sum(counts.values())},
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK carteles {READABLES}\nOK {MANIFEST}")
    return 0


OTB_BLOCK: set = set()

if __name__ == "__main__":
    sys.exit(main())
