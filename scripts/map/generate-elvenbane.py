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

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MANIFEST = WORLD / "generated-elvenbane.json"
REF = REPO / "docs/items-and-map/img/elvenbane-ref"
ASCII_MD = REF / "elvenbane_ascii.md"

# --- piezas (ids de servidor que ya están en el mapa/kb) -----------------------------------------
GRASS, WATER, STONE, MOUNTAIN = 4756, 4608, 431, 919
DIRT, DIRT_ALT = 351, 352
ROCK = 101
WALL_V, WALL_H, WALL_POST, WALL_CORNER = 1049, 1050, 1051, 1053
STAIRS_UP, STAIR_DOWN = 1385, 432
TELEPORT, ATTR_TELE_DEST, SIGN = 1387, 8, 1429
TREE_BIG, TREE_SMALL = 4009, 2768
BUSHES = (2767, 2786)
FLOWERS = (4158, 4150, 2740)
STONE_ITEM = 1285
NEEDS_COUNT = {2320}
SHORE = {("n",): 4644, ("e",): 4645, ("s",): 4646, ("w",): 4647,
         ("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651,
         ("nw",): 4652, ("ne",): 4653, ("sw",): 4654, ("se",): 4655}
DIRS = {"nw": (-1, -1), "n": (0, -1), "ne": (1, -1), "w": (-1, 0), "e": (1, 0),
        "sw": (-1, 1), "s": (0, 1), "se": (1, 1)}
CARD = ((1, 0), (-1, 0), (0, 1), (0, -1))

# --- geometría -----------------------------------------------------------------------------------
X_CASTLE, Y_CASTLE = 40, 298          # esquina NO de la planta del castillo (21 x 18)
CW, CH = 21, 18
Z7, Z6, Z5, Z4, Z8, Z9, Z10 = 7, 6, 5, 4, 8, 9, 10
BOX7 = (18, 286, 72, 360)             # isla + tierra firme + agua
BOX8 = (30, 288, 67, 349)             # túnel + sótano -1
BOX9 = (33, 291, 67, 322)             # sótano -2
BOX10 = (33, 291, 67, 322)            # prisión -3
BOXT = (38, 296, 62, 317)             # pisos altos (z4-z6): castillo + 2
BOXS = {Z4: BOXT, Z5: BOXT, Z6: BOXT, Z7: BOX7, Z8: BOX8, Z9: BOX9, Z10: BOX10}

GROUND_CROP = (20, 8, 46, 33)         # cols/rows del ASCII ground -> x 37-63, y 295-320
ENTRANCE_CROP = (26, 24, 50, 48)      # cols/rows del ASCII entrance -> x 27-51, y 329-353
PLAN8 = (37, 295)                     # ASCII floor-1: col 3 -> x 40, row 3 -> y 298
# Celdas de la prisión (floor-3) que el minimapa dibuja cerradas: se les abre la puerta al pasillo
PRISON_DOORS = tuple((row, col) for row in (4, 11) for col in (2, 5, 8, 11))

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
         ("Orc Shaman", 1, 1, 150, "torre"), ("Elf Arcanist", 1, 1, 150, "torre")],
    Z4: [("Orc Berserker", 1, 1, 120, "torreta"), ("Hunter", 1, 1, 120, "torreta"),
         ("Minotaur Archer", 1, 1, 120, "torreta"), ("Minotaur Mage", 1, 1, 150, "torre"),
         ("Demon Skeleton", 1, 1, 180, "torre"), ("Dragon", 1, 1, 300, "torre")],
}
GAP = 3                                # separación mínima entre centros de spawn

# --- escaleras: (etiqueta, piso de arriba, piso de abajo, (x, y) deseado) -------------------------
# El hueco 432 va arriba y la escalera 1385 abajo, en la misma casilla. Al subir se llega a
# (x, y-1) del piso de arriba; al bajar, a (x, y+1) del de abajo (docs/gameplay/STAIRS.md).
LINKS = [
    ("entrada", Z7, Z8, STAIR_ENTRY),
    ("sotano->patio", Z7, Z8, (X_CASTLE + 17, Y_CASTLE + 4)),
    ("sotano->-2", Z8, Z9, (X_CASTLE + 17, Y_CASTLE + 15)),
    ("-2->-3", Z9, Z10, (X_CASTLE + 2, Y_CASTLE + 14)),
    ("patio->adarve NO", Z6, Z7, (X_CASTLE + 2, Y_CASTLE + 1)),
    ("patio->adarve NE", Z6, Z7, (X_CASTLE + 17, Y_CASTLE + 1)),
    ("patio->adarve SO", Z6, Z7, (X_CASTLE + 3, Y_CASTLE + 14)),
    ("patio->adarve SE", Z6, Z7, (X_CASTLE + 17, Y_CASTLE + 14)),
    ("torre->adarve", Z6, Z7, (X_CASTLE + 13, Y_CASTLE + 6)),
    ("adarve->torreta NO", Z5, Z6, (X_CASTLE + 3, Y_CASTLE + 1)),
    ("adarve->torreta NE", Z5, Z6, (X_CASTLE + 18, Y_CASTLE + 1)),
    ("adarve->torreta SO", Z5, Z6, (X_CASTLE + 2, Y_CASTLE + 15)),
    ("adarve->torreta SE", Z5, Z6, (X_CASTLE + 18, Y_CASTLE + 15)),
    ("torre adarve->2", Z5, Z6, (X_CASTLE + 8, Y_CASTLE + 6)),
    ("torreta NO->3", Z4, Z5, (X_CASTLE + 2, Y_CASTLE + 1)),
    ("torreta NE->3", Z4, Z5, (X_CASTLE + 18, Y_CASTLE + 1)),
    ("torreta SO->3", Z4, Z5, (X_CASTLE + 2, Y_CASTLE + 14)),
    ("torreta SE->3", Z4, Z5, (X_CASTLE + 18, Y_CASTLE + 14)),
    ("torre 2->3", Z4, Z5, (X_CASTLE + 13, Y_CASTLE + 5)),
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


def add_shores(t: dict):
    """Agua poco profunda 4644-4655 en la casilla de tierra que toca el agua."""
    for (x, y), cell in t.items():
        if cell["g"] == WATER or any(4644 <= i <= 4655 for i in cell["it"]):
            continue
        water = tuple(d for d, (dx, dy) in DIRS.items()
                      if t.get((x + dx, y + dy), {}).get("g") == WATER)
        cards = tuple(sorted(set(water) & {"n", "e", "s", "w"}))
        piece = SHORE.get(cards) if len(cards) in (1, 2) else None
        if piece is None and not cards:
            diag = tuple(sorted(set(water) & {"nw", "ne", "sw", "se"}))
            piece = SHORE.get(diag) if len(diag) == 1 else None
        if piece:
            cell["it"].append(piece)


# ---------------------------------------------------------------- superficie (z7)
def build_surface(plans, seed: int):
    """z7: agua, isla con el castillo (ASCII ground) y tierra firme al sur (ASCII entrance)."""
    rng = random.Random(seed)
    x0, y0, x1, y1 = BOX7
    t = {(x, y): tile(WATER) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}
    trees = set()

    # 1) recortes del ASCII: '~' agua, '.' pasto, '_' piedra, '^' montaña, 'T' árbol
    crops = [("ground", GROUND_CROP, X_CASTLE - (23 - GROUND_CROP[0]), Y_CASTLE - (11 - GROUND_CROP[1])),
             ("entrance", ENTRANCE_CROP, STAIR_ENTRY[0] - (38 - ENTRANCE_CROP[0]),
              STAIR_ENTRY[1] - (35 - ENTRANCE_CROP[1]))]
    for key, (c0, r0, c1, r1), ox, oy in crops:
        for r, row in enumerate(range(r0, r1 + 1)):
            for c, col in enumerate(range(c0, c1 + 1)):
                ch, pos = plans[key][row][col], (ox + c, oy + r)
                if pos not in t or ch in "# S":
                    continue
                if ch == "~":
                    t[pos] = tile(WATER)
                elif ch == "_":
                    t[pos] = tile(STONE)
                elif ch == "^":
                    t[pos] = tile(MOUNTAIN)
                elif ch == ".":
                    t[pos] = tile(GRASS)
                elif ch == "T":
                    t[pos] = tile(GRASS)
                    trees.add(pos)

    # 2) fuera los islotes chicos (el ASCII deja motas de tierra y árboles sueltos en el agua)
    land = {p for p, c in t.items() if c["g"] in (GRASS, STONE, MOUNTAIN)}
    keep = {(ARRIVAL[0], ARRIVAL[1]), STAIR_ENTRY, *PORTALS_BACK}
    seen = set()
    for start in sorted(land):
        if start in seen:
            continue
        comp, q = {start}, deque([start])
        seen.add(start)
        while q:
            x, y = q.popleft()
            for dx, dy in CARD:
                n = (x + dx, y + dy)
                if n in land and n not in seen:
                    seen.add(n)
                    comp.add(n)
                    q.append(n)
        if len(comp) < 10 and not (comp & keep):
            for pos in comp:
                t[pos] = tile(WATER)

    # 3) el castillo: muro, anillo de piedra, patio de pasto y la torre central
    walls = {(X_CASTLE + x, Y_CASTLE + y)
             for y, row in enumerate(plans["ground"][11:29])
             for x, ch in enumerate(row[23:44]) if ch == "#"}
    pieces = wall_piece_set(walls)
    for y, row in enumerate(plans["ground"][11:29]):
        for x, ch in enumerate(row[23:44]):
            pos = (X_CASTLE + x, Y_CASTLE + y)
            if ch == "#":
                t[pos] = tile(GRASS if (y == 0 or x == 0) else STONE, [pieces[pos]])
            elif ch in "_S":
                t[pos] = tile(STONE)
            elif ch == ".":
                t[pos] = tile(GRASS)

    # 3) camino de piedra de la puerta sur (cols 10-11 de la planta) a la explanada
    gate = [(x, y) for x in (X_CASTLE + 10, X_CASTLE + 11)
            for y in range(Y_CASTLE + CH, Y_CASTLE + CH + 4)]
    for pos in gate:
        if pos in t:
            t[pos] = tile(STONE)

    # 4) claros: llegada, portales, bajada, el camino entre ellos y la puerta del castillo
    clear = set(gate)
    for cx, cy, r in ((ARRIVAL[0], ARRIVAL[1], 2), (PORTALS_BACK[0][0] + 1, PORTALS_BACK[0][1], 2),
                      (STAIR_ENTRY[0], STAIR_ENTRY[1], 2)):
        clear |= {(cx + dx, cy + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)}
    for y in range(STAIR_ENTRY[1], ARRIVAL[1] + 2):
        for x in range(STAIR_ENTRY[0] - 1, STAIR_ENTRY[0] + 2):
            clear.add((x, y))
    for pos in clear:
        if pos in t and t[pos]["g"] not in (WATER, STONE):
            t[pos] = tile(GRASS)

    # 5) bosque: árbol en las casillas 'T' que quedaron sobre tierra; arbustos y flores sueltos
    castle_box = {(x, y) for x in range(X_CASTLE, X_CASTLE + CW) for y in range(Y_CASTLE, Y_CASTLE + CH)}
    for pos in sorted(trees):
        cell = t.get(pos)
        if cell is None or pos in clear or pos in castle_box or cell["g"] != GRASS:
            continue
        cell["it"].append(TREE_BIG if rng.random() < 0.35 else TREE_SMALL)
    for pos, cell in sorted(t.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if cell["g"] != GRASS or pos in clear or pos in trees or pos in castle_box:
            continue
        r = rng.random()
        if r < 0.05:
            cell["it"].append(rng.choice(BUSHES))
        elif r < 0.09:
            cell["it"].append(rng.choice(FLOWERS))

    # 6) orilla: el agua poco profunda 4644-4655 es block_solid, así que el camino de la
    #    llegada queda sin borde para que se pueda caminar por la costa
    add_shores(t)
    for pos in clear:
        if pos in t:
            t[pos]["it"] = [i for i in t[pos]["it"] if not (4644 <= i <= 4655)]

    # 7) portales de vuelta, enmarcados; bajada a la cueva
    for pos in PORTALS_BACK:
        t[pos] = tile(GRASS, [TELEPORT], TEMPLE_BACK)
    px0, px1, py = PORTALS_BACK[0][0], PORTALS_BACK[1][0], PORTALS_BACK[0][1]
    for pos in ((px0 - 1, py), (px1 + 1, py), (px0 - 1, py + 1), (px1 + 1, py + 1),
                (px0, py + 1), (px1, py + 1), (px0 - 1, py - 1), (px1 + 1, py - 1)):
        base = t[pos]["g"] if pos in t and t[pos]["g"] != WATER else GRASS
        t[pos] = tile(base, [STONE_ITEM])
    t[STAIR_ENTRY] = tile(GRASS)          # el hueco lo pone la escalera (LINKS)
    t[(STAIR_ENTRY[0] - 1, STAIR_ENTRY[1])] = tile(GRASS, [STONE_ITEM])
    t[(STAIR_ENTRY[0] + 1, STAIR_ENTRY[1])] = tile(GRASS, [STONE_ITEM])
    t[(STAIR_ENTRY[0], STAIR_ENTRY[1] + 1)] = tile(GRASS)
    t[(STAIR_ENTRY[0], STAIR_ENTRY[1] - 1)] = tile(GRASS)

    # 8) carteles
    sign_1 = (ARRIVAL[0] - 2, ARRIVAL[1] + 1)
    sign_2 = (STAIR_ENTRY[0] + 2, STAIR_ENTRY[1] + 1)
    t[sign_1] = tile(GRASS, [SIGN])
    t[sign_2] = tile(GRASS, [SIGN])
    signs = {sign_1: "ELVENBANE\nFortaleza elfica en 7 pisos.\nBaja a la cueva: el tunel llega\n"
                     "al sotano del castillo.\nPortal al norte: templo.",
             sign_2: "BAJADA A ELVENBANE\nTunel largo hasta el sotano.\nTrolls, orcos y enanos."}
    return t, {"signs": signs, "castle_walls": walls}


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


# ---------------------------------------------------------------- escaleras
def walk_tile(cell) -> bool:
    if cell is None or cell["g"] is None:
        return False
    if cell["g"] in OTB_BLOCK:
        return False
    return not any(i in OTB_BLOCK for i in cell["it"])


def is_stair(cell) -> bool:
    return cell is not None and (cell["g"] == STAIR_DOWN or STAIRS_UP in cell["it"])


def resolve_stair(upper: dict, lower: dict, zu: int, zl: int, wish, used: dict, label: str):
    """Encuentra la casilla de la escalera entre dos pisos, cerca de donde la pide el ASCII."""
    cands = sorted(lower, key=lambda p: (abs(p[0] - wish[0]) + abs(p[1] - wish[1]),
                                         p[1] - wish[1], p[0] - wish[0]))
    for p in cands:
        if abs(p[0] - wish[0]) + abs(p[1] - wish[1]) > 8:
            break
        x, y = p
        up, low = upper.get(p), lower.get(p)
        if not walk_tile(up) or not walk_tile(low) or is_stair(up) or is_stair(low):
            continue
        up_land, low_land = upper.get((x, y - 1)), lower.get((x, y + 1))
        if not walk_tile(up_land) or not walk_tile(low_land):
            continue
        if is_stair(up_land) or is_stair(low_land):
            continue
        if (p in used.setdefault(zu, set()) or (x, y - 1) in used[zu]
                or p in used.setdefault(zl, set()) or (x, y + 1) in used[zl]):
            continue
        used[zu].update({p, (x, y - 1)})
        used[zl].update({p, (x, y + 1)})
        return p
    raise SystemExit(f"ERROR: no hay casilla para la escalera {label} cerca de {wish}")


def place_stair(upper: dict, lower: dict, p):
    up = upper[p]
    up["g"] = STAIR_DOWN
    up["it"] = []
    up["tele"] = None
    lower[p]["it"].append(STAIRS_UP)


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
def bfs(layers: dict, start):
    """Alcanzabilidad multi-piso: casillas caminables + escaleras/huecos."""
    seen, q = {start}, deque([start])
    while q:
        x, y, z = q.popleft()
        cell = layers[z].get((x, y))
        if cell is None:
            continue
        if cell["g"] == STAIR_DOWN:
            n = (x, y + 1, z + 1)
            if n[2] in layers and walk_tile(layers[n[2]].get((x, y + 1))) and n not in seen:
                seen.add(n)
                q.append(n)
            continue
        if STAIRS_UP in cell["it"]:
            n = (x, y - 1, z - 1)
            if n[2] in layers and walk_tile(layers[n[2]].get((x, y - 1))) and n not in seen:
                seen.add(n)
                q.append(n)
        for dx, dy in CARD:
            n = (x + dx, y + dy, z)
            nc = layers[z].get((n[0], n[1]))
            if nc is None or not walk_tile(nc):
                continue
            if nc["g"] == STAIR_DOWN:            # pisar el hueco: se baja al piso de abajo
                d = (n[0], n[1] + 1, z + 1)
                if d[2] in layers and walk_tile(layers[d[2]].get(d[:2])) and d not in seen:
                    seen.add(d)
                    q.append(d)
                continue
            if n not in seen:
                seen.add(n)
                q.append(n)
    return seen


def open_pockets(t7: dict, layers: dict, start):
    """Deja z7 sin bolsones inalcanzables: abre un paso de pasto en la montaña o los tapa.

    Primero intenta un paso de pasto entre dos montañas (queda un sendero natural); si el bolsón
    está rodeado de agua, la casilla pasa a agua (islote) o a roca según lo que tenga al lado.
    """
    opened, filled = [], []
    reach = bfs(layers, start)
    for _ in range(400):
        reach7 = {(x, y) for x, y, z in reach if z == Z7}
        lost = {p for p, c in t7.items() if walk_tile(c) and c["g"] != STAIR_DOWN
                and STAIRS_UP not in c["it"]} - reach7
        if not lost:
            break
        cands = []
        for pos, cell in t7.items():
            around = {(pos[0] + dx, pos[1] + dy) for dx, dy in CARD}
            if not (around & lost) or not (around & reach7):
                continue
            if cell["g"] == MOUNTAIN:
                cands.append(("montaña", pos))
            elif any(i in OTB_BLOCK for i in cell["it"]):
                cands.append(("decorado", pos))
        if cands:
            kind, pos = cands[0]
            if kind == "montaña":
                t7[pos] = tile(GRASS)
                opened.append(pos)
            else:                                    # un árbol/arbusto cortaba el paso
                t7[pos]["it"] = [i for i in t7[pos]["it"] if i not in OTB_BLOCK]
                opened.append(pos)
        else:
            cell = min(lost)
            t7[cell] = tile(MOUNTAIN)          # roca: no crea orillas nuevas (que bloquean)
            filled.append(cell)
        reach = bfs(layers, start)
    return opened, filled


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

    used: dict = {}
    stairs, moved = [], []
    for label, zu, zl, wish in LINKS:
        p = resolve_stair(layers[zu], layers[zl], zu, zl, wish, used, label)
        if p != wish:
            moved.append((label, wish, p))
        place_stair(layers[zu], layers[zl], p)
        stairs.append((label, zu, zl, p))

    # --- validaciones ---
    errors = []
    opened, filled = open_pockets(layers[Z7], layers, (ARRIVAL[0], ARRIVAL[1], Z7))
    walkbyz = {z: {p for p, c in tl.items() if walk_tile(c)} for z, tl in layers.items()}
    reach = bfs(layers, (ARRIVAL[0], ARRIVAL[1], Z7))
    for z in sorted(layers):
        walk = {p for p, c in layers[z].items() if walk_tile(c) and c["g"] != STAIR_DOWN}
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
    for label, zu, zl, p in stairs:
        if (zu, p) in seen_stairs:
            errors.append(f"escalera {label} repite casilla {p} en z{zu}")
        seen_stairs.add((zu, p))
        for zz, land in ((zu, (p[0], p[1] - 1)), (zl, (p[0], p[1] + 1))):
            if not walk_tile(layers[zz].get(land)):
                errors.append(f"escalera {label}: llegada {land},{zz} no caminable")
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
    for label, zu, zl, p in stairs:
        avoid[zu] |= {p, (p[0], p[1] - 1)}
        avoid[zl] |= {p, (p[0], p[1] + 1)}
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
    for z in sorted(layers):
        tl = layers[z]
        print(f"  z{z}: {len(tl)} casillas, {sum(1 for c in tl.values() if walk_tile(c))} caminables, "
              f"caja x{BOXS[z][0]}-{BOXS[z][2]} y{BOXS[z][1]}-{BOXS[z][3]}")
    for label, zu, zl, p in stairs:
        print(f"  escalera {label}: hueco {p[0]},{p[1]},{zu} / subida {p[0]},{p[1]},{zl}")
    for label, wish, got in moved:
        print(f"  reubicada {label}: {wish} -> {got}")
    if opened or filled:
        print(f"  despejados z7: {len(opened)} pasos de montaña, {len(filled)} bolsones tapados")
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
        "stairs": [{"label": label, "x": p[0], "y": p[1], "holeZ": zu, "upZ": zl,
                    "upLanding": {"x": p[0], "y": p[1] - 1, "z": zu},
                    "downLanding": {"x": p[0], "y": p[1] + 1, "z": zl}}
                   for label, zu, zl, p in stairs],
        "relocated": [{"label": l, "wish": list(w), "got": list(g)} for l, w, g in moved],
        "openedPassages": [list(p) for p in opened],
        "sealedPockets": [list(p) for p in filled],
        "spawns": {f"z{z}": sum(1 for _c, zz, _m in spawns if zz == z) for z in sorted(layers)},
        "monsters": {f"z{z}/{name}": n for (z, name), n in sorted(counts.items())},
        "counts": {"spawns": len(spawns), "monsters": sum(counts.values())},
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK carteles {READABLES}\nOK {MANIFEST}")
    return 0


OTB_BLOCK: set = set()

if __name__ == "__main__":
    sys.exit(main())
