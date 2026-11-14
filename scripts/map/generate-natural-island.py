#!/usr/bin/env python3
"""Isla natural (portal 156,47,7 de la plaza): herradura con una cueva de tres pisos.

Reemplaza a la isla vieja (un campo abierto de 46x44 con 13 Cyclops repartidos y una cueva ancha
sin recorrido). La forma de la isla ES el recorrido: una franja de tierra en herradura alrededor
de una laguna. Se llega a una punta y la cueva está en la otra; no hay otro camino.

  z7  Llegada (punta oeste, portal de vuelta) -> sendero de tierra -> Campamento 1 (oeste)
      -> Campamento 2 (norte) -> Campamento 3 (este) -> boca de la cueva (punta este, otro portal)
  z8  Escalera -> Golems -> Galería -> Cripta -> Guarida del Grorlam (bajada a z9)
  z9  Wyverns / murciélagos / hatchlings -> Descenso (bajada a z10)
  z10 Mutantes / cristal / hatchlings -> Cámara de la Reina (Old Widow + portal al templo)

Reglas (las mismas del resto del mapa, ver docs/items-and-map/map-kb/):
  - costa: pasto 4526 + borde 4644-4655 según dónde está el agua;
  - pasto junto a tierra 103: suelo de pasto con borde dibujado (110-121), nunca sobre la costa;
  - cueva en bloques de 2x2: toda roca que toca piso tiene una única pieza de pared;
  - sin monstruos "rage" (Angry/Furious/Enraged) ni troncos sueltos.

Uso:
  python3 scripts/map/generate-natural-island.py --dry-run --preview /tmp/isla   # isla-z7..z10.png
  python3 scripts/map/generate-natural-island.py                                 # escribe mapa, spawns, carteles
  python3 scripts/map/temple-portals.py                                          # el portal de la plaza
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
from mapdata import (MAP, REPO, T_AREA, T_HOUSETILE, T_TILE, Renderer,  # noqa: E402
                     parse_tree, png_bytes, serialize_tree)

_spec = importlib.util.spec_from_file_location("north_pass", HERE / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)
Noise, neighbors_in, pieces_for, fix_until_valid, reach, Blocking = (
    NP.Noise, NP.neighbors_in, NP.pieces_for, NP.fix_until_valid, NP.reach, NP.Blocking)
DIRT_SIDE, DIRT_CORNER, DIRT_INNER = NP.DIRT_SIDE, NP.DIRT_CORNER, NP.DIRT_INNER
WALL_SIDE, WALL_CORNER, WALL_INNER, ROCK = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER, NP.ROCK
CAVE_FLOORS, CARD, ALL8 = NP.CAVE_FLOORS, NP.CARD, NP.ALL8

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MANIFEST = WORLD / "generated-natural-island.json"

OLD_BOX = (124, 426, 187, 483)              # isla vieja (z7-z10): se borra entera
X0, Y0, W, H = 131, 433, 50, 44             # caja nueva (adentro de la vieja)
Z7, Z8, Z9, Z10 = 7, 8, 9, 10
TEMPLE_BACK = (156, 48, 7)                  # llegada del portal de la plaza (temple-portals.py)
VIEW = (8, 6)                               # media pantalla del cliente: no se ve el borde de la caja

# --- piezas (ids de servidor) ---------------------------------------------------------------------
WATER, GRASS, GRASS_COAST, DIRT = 4608, 4756, 4526, 103
COAST_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
COAST_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
COAST_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}
COAST_PIECES = set(range(4644, 4656))
DIRT_PIECES = set(DIRT_SIDE.values()) | set(DIRT_CORNER.values()) | set(DIRT_INNER.values())
TREES = (2701, 2702, 2703, 2704, 2705, 2706, 2708, 4009)    # 2x2, bloquean su casilla
BUSHES = (2767, 2786, 2768)
SMALL = (4158, 2740, 4179, 4150, 4183)                       # flores, hongos, maleza
HOLE_ID, LADDER = 469, 1386                                  # la escalera sale a x, y+1, z-1
TELEPORT, SIGN, CAMPFIRE = NP.TELEPORT, NP.SIGN, NP.CAMPFIRE
STONE = NP.STONE
BONES, SKULL = (3125, 2248), 2247                            # no bloquean

# --- recorrido de la superficie (coordenadas locales) ---------------------------------------------
CENTER = (24.5, 21.0)                       # centro de la herradura (la laguna)
RX, RY = 10.5, 9.0                          # radios del sendero
ARC = (50, 310)                             # grados desde el sur, pasando por oeste, norte y este
TIP_Y = 30.5                                # las dos puntas bajan derecho hasta acá
HALF = 4.8                                  # medio ancho de la franja de tierra (con ruido)
CAMP_ANGLES = (105, 180, 255)               # campamentos sobre el sendero
CAMP_DIRT = 2.9                             # radio del claro de tierra de cada campamento
ARRIVAL = (16, 29)                          # destino del portal de la plaza
PORTAL_BACK = (16, 32)                      # vuelta al templo, al sur de la llegada
HOLE = (32, 30)                             # boca de la cueva (la escalera devuelve a 32,31)
#        (monstruo, cantidad, spawntime) por campamento, en orden de recorrido
CAMPS = [[("Cyclops", 3, 90)], [("Cyclops", 4, 90)], [("Cyclops", 4, 90)]]
CAMP_NAMES = ("Campamento del oeste", "Campamento del norte", "Campamento del este")

# --- cueva (z8): salas encadenadas desde la escalera ----------------------------------------------
#        (nombre, centro, radio, [(monstruo, cantidad, spawntime)])
ROOMS8 = [
    ("Sala de los Golems", (33, 21), 3.6, [("Stone Golem", 3, 90), ("Gazer", 1, 90)]),
    ("Galeria", (24, 14), 3.8, [("Stone Golem", 2, 90), ("Crypt Shambler", 2, 90), ("Gazer", 1, 90)]),
    ("Cripta", (13, 20), 3.8, [("Crypt Shambler", 3, 100), ("Stalker", 2, 100)]),
    ("Guarida del Grorlam", (21, 29), 4.4, [("Grorlam", 1, 1800), ("Crypt Shambler", 2, 120)]),
]
LINKS8 = [[HOLE, (33, 21)], [(33, 21), (30, 15), (24, 14)], [(24, 14), (16, 15), (13, 20)],
          [(13, 20), (13, 27), (21, 29)]]
LADDER_ROOM = 2.2                           # radio del rellano de la escalera
LINK_HALF = 1.5                             # medio ancho de los pasillos (>= 1.42: sin cortes en la grilla 2x2)

# --- pisos nuevos: z9 y z10 -----------------------------------------------------------------------
ROOMS9 = [
    ("Sala de los Wyverns", (33, 32), 4.0, [("Wyvern", 2, 120), ("Dragon Hatchling", 1, 120)]),
    ("Galeria de los Murcielagos", (33, 20), 3.8, [("Mutated Bat", 3, 120), ("Mutated Rat", 1, 120)]),
    ("Camara de los Hatchlings", (22, 13), 3.8, [("Dragon Hatchling", 2, 120), ("Wyvern", 1, 120)]),
    ("Descenso", (11, 19), 4.0, [("Mutated Rat", 2, 120), ("Mutated Bat", 1, 120)]),
]
ROOMS10 = [
    ("Sala de los Mutantes", (16, 34), 4.0, [("Mutated Rat", 3, 120), ("Mutated Human", 1, 150)]),
    ("Galeria de Cristal", (32, 33), 3.8, [("Emerald Scarab", 1, 600), ("Mutated Bat", 2, 120)]),
    ("Sala de los Hatchlings", (35, 18), 3.8, [("Dragon Hatchling", 2, 120), ("Wyvern", 1, 120)]),
    ("Camara de la Reina", (18, 13), 4.8, [("Old Widow", 1, 1800), ("Giant Spider", 2, 120)]),
]

# huella mínima (casillas) para que el sprite no quede metido en la pared
SIZE = {
    "Old Widow": 2, "Giant Spider": 2, "Wyvern": 2, "Dragon Hatchling": 2,
    "Mutated Bat": 2, "Mutated Rat": 2, "Mutated Human": 2, "Emerald Scarab": 2,
    "Grorlam": 2, "Stone Golem": 2, "Gazer": 2, "Cyclops": 2,
}

SIGNS = {
    "arrival": "ISLA NATURAL\\nSigue el sendero: tres\\ncampamentos de Cyclops\\ny al final la cueva.",
    "cave": "CUEVA DE PIEDRA\\nGolems, Shamblers y\\nun descenso a wyverns.\\nAl fondo, la Reina.",
}


def grow(cells, r: int) -> set:
    return {(x + dx, y + dy) for (x, y) in cells for dx in range(-r, r + 1) for dy in range(-r, r + 1)}


def arc_point(deg: float) -> tuple[float, float]:
    t = math.radians(deg)
    return CENTER[0] - RX * math.sin(t), CENTER[1] + RY * math.cos(t)


def sample_line(points, step=0.25) -> list[tuple[float, float]]:
    out = []
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) / step))
        out += [(ax + (bx - ax) * i / n, ay + (by - ay) * i / n) for i in range(n)]
    return out + [points[-1]]


def line_dist(samples) -> dict:
    """Casilla -> (distancia al recorrido, avance sobre el recorrido en muestras)."""
    out = {}
    for y in range(H):
        for x in range(W):
            out[(x, y)] = min((math.hypot(x - sx, y - sy), i) for i, (sx, sy) in enumerate(samples))
    return out


def pick_spots(cands, n, rng, gap=2) -> list:
    """n casillas separadas entre sí (se achica la separación si no alcanzan)."""
    cands = sorted(cands)
    rng.shuffle(cands)
    while True:
        out = []
        for c in cands:
            if all(max(abs(c[0] - o[0]), abs(c[1] - o[1])) >= gap for o in out):
                out.append(c)
                if len(out) == n:
                    return out
        if gap == 1:
            raise RuntimeError(f"no hay {n} casillas libres para los monstruos")
        gap -= 1


def place_sized(cands, names, near) -> list:
    """Coloca cada monstruo con su huella SIZE: primero los grandes y lo más cerca posible del centro.

    La huella completa (SIZE x SIZE desde la casilla del spawn) tiene que caer en `cands` y no
    pisar la huella de otro monstruo. Devuelve las posiciones en el orden de `names`.
    """
    cands = set(cands)
    occupied = set()
    out = [None] * len(names)
    order = sorted(range(len(names)), key=lambda i: (-SIZE.get(names[i][0], 1), i))
    for i in order:
        s = SIZE.get(names[i][0], 1)
        best = None
        for c in sorted(cands):
            if c in occupied:
                continue
            foot = [(c[0] + dx, c[1] + dy) for dx in range(s) for dy in range(s)]
            if any(p not in cands or p in occupied for p in foot):
                continue
            key = (math.hypot(c[0] + (s - 1) / 2 - near[0], c[1] + (s - 1) / 2 - near[1]), c)
            if best is None or key < best[0]:
                best = (key, c, foot)
        if best is None:
            raise RuntimeError(f"no hay hueco {s}x{s} para {names[i][0]} cerca de {near}")
        out[i] = best[1]
        occupied.update(best[2])
    return out


# --- superficie ---------------------------------------------------------------------------------

def build_surface(seed: int, bl):
    rng = random.Random(seed)
    nz = Noise(seed + 1)
    cells = {(x, y) for y in range(H) for x in range(W)}
    a0, a1 = arc_point(ARC[0]), arc_point(ARC[1])
    samples = sample_line([(a0[0], TIP_Y)] + [arc_point(d) for d in range(ARC[0], ARC[1] + 1, 5)] + [(a1[0], TIP_Y)])
    ld = line_dist(samples)
    camps = [tuple(round(v) for v in arc_point(d)) for d in CAMP_ANGLES]
    bulges = [(HOLE, 0.9), (ARRIVAL, 0.5)]
    near_hole = grow({HOLE}, 1)

    def half(c):
        r = HALF + 1.6 * (nz.fbm(c[0] / 5, c[1] / 5, 3, 100) - 0.5)
        return r + max(b * max(0.0, 1 - math.hypot(c[0] - p[0], c[1] - p[1]) / 6) for p, b in bulges)

    # 1) sendero y claros de los campamentos (tierra), en bloques de 2x2: asi cada pasto vecino tiene
    #    una unica pieza de borde y el sendero no se ensancha al corregir
    def cells_of(b):
        return {(2 * b[0] + i, 2 * b[1] + j) for i in (0, 1) for j in (0, 1)}

    blocks = {(round(sx) // 2, round(sy) // 2) for sx, sy in samples}
    blocks |= {(bx, by) for bx in range(W // 2) for by in range(H // 2)
               if any(math.hypot(2 * bx + 0.5 - p[0], 2 * by + 0.5 - p[1]) <= CAMP_DIRT for p in camps)}
    blocks = {b for b in blocks if not cells_of(b) & near_hole}
    changed = True
    while changed:                                              # sin contactos solo en diagonal
        changed = False
        for (x, y) in sorted(blocks):
            for dx, dy in ((1, 1), (1, -1)):
                side = (x + dx, y)
                if (x + dx, y + dy) in blocks and side not in blocks and (x, y + dy) not in blocks \
                        and not cells_of(side) & near_hole:
                    blocks.add(side)
                    changed = True
    dirt = set().union(*(cells_of(b) for b in blocks))

    # 2) tierra firme: dos casillas alrededor de la tierra (borde de pasto + costa) y, donde el ruido
    #    lo pide, un poco mas de monte; la costa se ajusta hasta que toda casilla tiene pieza
    land = (grow(dirt, 2) | {c for c in cells if ld[c][0] <= half(c)}) & cells
    for _ in range(20):
        sea = fix_until_valid(cells - land, cells, COAST_SIDE, COAST_CORNER, COAST_INNER)
        land = cells - sea
        main = set(reach(land, ARRIVAL, CARD))
        if main == land:
            break
        land = main
    dist = {c: 0 for c in sea}                                  # distancia al agua
    q = deque(sea)
    while q:
        x, y = q.popleft()
        for dx, dy in ALL8:
            n = (x + dx, y + dy)
            if n in cells and n not in dist:
                dist[n] = dist[(x, y)] + 1
                q.append(n)
    deep = {c for c in land if dist[c] >= 3} - near_hole
    dirt = fix_until_valid(dirt & deep, deep, DIRT_SIDE, DIRT_CORNER, DIRT_INNER, single=True)
    for _ in range(60):
        bad = set()
        for c in land - dirt:
            near = neighbors_in(dirt, *c)
            if not near:
                continue
            want = pieces_for(near, DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
            if want is None or len(want) > 1 or dist[c] <= 1 or c == HOLE:
                bad.add(c)
        if not bad:
            break
        dirt -= grow(bad, 1)
        dirt = fix_until_valid(dirt, deep, DIRT_SIDE, DIRT_CORNER, DIRT_INNER, single=True)

    # 3) suelos y bordes
    tiles: dict = {}
    for c in cells:
        if c in sea:
            tiles[c] = [WATER]
        elif c in dirt:
            tiles[c] = [DIRT]
        else:
            coast = pieces_for(neighbors_in(sea, *c), COAST_SIDE, COAST_CORNER, COAST_INNER)
            edge = pieces_for(neighbors_in(dirt, *c), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
            tiles[c] = [GRASS_COAST, *coast] if coast else [edge[0]] if edge else [GRASS]
    tiles[HOLE] = [HOLE_ID]

    def plain(c):                                               # tierra o pasto sin costa ni nada encima
        return c in land and len(tiles[c]) == 1 and tiles[c][0] != HOLE_ID

    # 4) llegada, boca de la cueva, portales y carteles
    hx, hy = HOLE
    reserved = grow({ARRIVAL}, 1) | grow({HOLE}, 1) | {PORTAL_BACK}
    for dx, dy in ((-2, -1), (-2, 0), (-2, 1), (2, -1), (2, 0), (2, 1), (-1, 2), (0, 2), (1, 2)):
        c = (hx + dx, hy + dy)                                  # herradura de piedras abierta al norte
        if plain(c):
            tiles[c].append(STONE)
            reserved.add(c)

    def near_free(want):
        cands = [c for c in land if plain(c) and c not in reserved and c not in dirt]
        c = min(cands, key=lambda c: (math.hypot(c[0] - want[0], c[1] - want[1]), c))
        reserved.add(c)
        return c

    tiles[PORTAL_BACK].append(TELEPORT)
    hole_portal = near_free((hx + 3, hy - 3))
    tiles[hole_portal].append(TELEPORT)
    signs = {near_free((ARRIVAL[0] - 2, ARRIVAL[1] - 1)): SIGNS["arrival"], near_free((hx - 3, hy - 3)): SIGNS["cave"]}
    for c in signs:
        tiles[c].append(SIGN)

    # 5) campamentos: fogata, piedras para sentarse y huesos
    for cx, cy in camps:
        for (dx, dy), item in (((0, 0), CAMPFIRE), ((-2, -1), STONE), ((2, 1), STONE), ((1, -2), BONES[0]),
                               ((-1, 2), BONES[1]), ((2, -1), SKULL)):
            c = (cx + dx, cy + dy)
            if c in dirt and len(tiles[c]) == 1:
                tiles[c].append(item)
        reserved |= grow({(cx, cy)}, 3)

    # 6) monte entre el sendero y la costa: árboles, arbustos y flores (nunca sobre el sendero)
    # el dibujo de un arbol ocupa 2x2 hacia arriba-izquierda: no puede tapar portales, carteles ni piedras
    marked = {c for c in land if c == HOLE or (tiles[c][0] != GRASS_COAST and len(tiles[c]) > 1)}
    occupied = set()
    for c in sorted(land - dirt, key=lambda c: (c[1], c[0])):
        x, y = c
        if tiles[c] != [GRASS] or dist[c] < 2 or c in reserved:
            continue
        r = rng.random()
        if ld[c][0] >= 2.2 and r < 0.34 and not {(x - 1, y), (x, y - 1), (x - 1, y - 1)} & marked and not any((x - i, y - j) in occupied for i in range(-1, 3) for j in range(-1, 3)):
            tiles[c].append(rng.choice(TREES))
            occupied |= {(x, y), (x - 1, y), (x, y - 1), (x - 1, y - 1)}
        elif ld[c][0] >= 2.2 and r < 0.44 and c not in occupied:
            tiles[c].append(rng.choice(BUSHES))
            occupied.add(c)
        elif r < 0.58 and c not in occupied:
            tiles[c].append(rng.choice(SMALL))

    # 7) ningun rincon encerrado por el monte: se saca el arbol o arbusto que lo tapa
    for _ in range(20):
        walk = {c for c in land if c != HOLE and bl.walkable(tiles[c])} - {PORTAL_BACK, hole_portal}
        lost = walk - set(reach(walk, ARRIVAL))
        if not lost:
            break
        for c in grow(lost, 1):
            if c in land and tiles[c][-1] in TREES + BUSHES:
                tiles[c].pop()

    return tiles, {"land": land, "sea": sea, "dirt": dirt, "dist": dist, "ld": ld, "camps": camps,
                   "signs": signs, "hole_portal": hole_portal}


# --- cueva --------------------------------------------------------------------------------------

def build_floor(seed: int, start, rooms, links, bl, final=False):
    nz = Noise(seed + 77)
    lx, ly = start
    ox, oy = lx % 2, ly % 2                                     # grilla de bloques 2x2 alineada a la escalera
    discs = [(start, LADDER_ROOM)] + [(c, r) for _n, c, r, _m in rooms]
    link_samples = [s for pts in links for s in sample_line(pts)]

    def inside(px, py):
        wob = 0.8 * (nz.fbm(px / 3, py / 3, 2, 5) - 0.5)
        return (any(math.hypot(px - c[0], py - c[1]) <= r + wob for c, r in discs)
                or any(math.hypot(px - sx, py - sy) <= LINK_HALF for sx, sy in link_samples))

    blocks = {(bx, by) for bx in range(-1, W // 2 + 1) for by in range(-1, H // 2 + 1)
              if inside(ox + 2 * bx + 0.5, oy + 2 * by + 0.5)}
    changed = True
    while changed:                                              # sin contactos solo en diagonal
        changed = False
        for (x, y) in sorted(blocks):
            for dx, dy in ((1, 1), (1, -1)):
                if (x + dx, y + dy) in blocks and (x + dx, y) not in blocks and (x, y + dy) not in blocks:
                    blocks.add((x + dx, y))
                    changed = True
    floor = {(ox + 2 * bx + i, oy + 2 * by + j) for bx, by in blocks for i in (0, 1) for j in (0, 1)}
    box = {(x, y) for y in range(H) for x in range(W)}
    tiles = NP.cave_tiles(floor, box, seed)
    d = reach(floor, start, CARD)

    # salida: lo más lejos de la escalera, dentro de la última sala y sin pegarse a la pared
    bc, br = rooms[-1][1], rooms[-1][2]
    cands = [c for c in d if math.hypot(c[0] - bc[0], c[1] - bc[1]) <= br
             and all((c[0] + dx, c[1] + dy) in floor for dx, dy in ALL8)]
    exit_tp = max(cands, key=lambda c: (d[c], c))
    tiles[start].append(LADDER)
    if final:
        tiles[exit_tp].append(TELEPORT)
    else:
        tiles[exit_tp] = [HOLE_ID]                              # agujero al piso siguiente
    keep = grow({start, exit_tp}, 2)
    NP.decorate_cave(tiles, floor, start, keep, seed, 0.04, bl)
    return tiles, {"floor": floor, "exit": exit_tp, "start": start, "keep": keep, "final": final}


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{X0 + cx}" centery="{Y0 + cy}" centerz="{z}" radius="4">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def write_preview(base: Path, layers) -> list:
    out = []
    rd = Renderer()
    for z, t in layers:
        used = [c for c, it in t.items() if it[0] not in (WATER, ROCK)]
        x1, x2 = min(x for x, _ in used) - 3, max(x for x, _ in used) + 3
        y1, y2 = min(y for _, y in used) - 3, max(y for _, y in used) + 3
        w, h, img = rd.area({(x, y, z): it for (x, y), it in t.items()}, x1, y1, x2, y2, z)
        p = base.with_name(f"{base.name}-z{z}.png")
        p.write_bytes(png_bytes(w, h, bytes(img)))
        out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path, help="prefijo: escribe <prefijo>-z7.png ... <prefijo>-z10.png")
    a = ap.parse_args()

    bl = Blocking()
    rng = random.Random(a.seed + 99)
    surf, info = build_surface(a.seed, bl)
    cave8, cinfo8 = build_floor(a.seed + 800, HOLE, ROOMS8, LINKS8, bl, final=False)
    start9 = cinfo8["exit"]
    links9 = [[start9, (33, 32)], [(33, 32), (33, 20)], [(33, 20), (22, 13)], [(22, 13), (11, 19)]]
    cave9, cinfo9 = build_floor(a.seed + 900, start9, ROOMS9, links9, bl, final=False)
    start10 = cinfo9["exit"]
    links10 = [[start10, (16, 34)], [(16, 34), (32, 33)], [(32, 33), (35, 18)], [(35, 18), (18, 13)]]
    cave10, cinfo10 = build_floor(a.seed + 1000, start10, ROOMS10, links10, bl, final=True)
    floors = [(Z8, cave8, cinfo8, ROOMS8), (Z9, cave9, cinfo9, ROOMS9), (Z10, cave10, cinfo10, ROOMS10)]
    land, sea, dirt, camps = info["land"], info["sea"], info["dirt"], info["camps"]
    hx, hy = HOLE
    errors = []

    # --- validación: bordes exactos, recorrido sin cortes y nada a la vista del borde de la caja ---
    for c, it in surf.items():
        if it[0] in (WATER, DIRT, HOLE_ID):
            continue
        want = pieces_for(neighbors_in(sea, *c), COAST_SIDE, COAST_CORNER, COAST_INNER)
        if want is None or sorted(want) != sorted(i for i in it[1:] if i in COAST_PIECES):
            errors.append(f"costa {c}: quiere {want} tiene {it}")
        edge = pieces_for(neighbors_in(dirt, *c), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
        if edge is None or len(edge) > 1 or (edge and (it[0] != edge[0] or want)) or (not edge and it[0] in DIRT_PIECES):
            errors.append(f"tierra {c}: quiere {edge} tiene {it}")
    portals7 = {PORTAL_BACK, info["hole_portal"]}
    walk7 = {c for c, it in surf.items() if it[0] not in (WATER, HOLE_ID) and bl.walkable(it)} - portals7
    d7 = reach(walk7, ARRIVAL)
    for label, c in [("salida de la escalera", (hx, hy + 1)), ("entrada a la cueva", (hx, hy - 1))] + \
            [(n, p) for n, p in zip(CAMP_NAMES, camps)]:
        if c not in d7:
            errors.append(f"z7: {label} {c} no se alcanza desde la llegada")
    for label, c in (("portal de la llegada", PORTAL_BACK), ("portal de la cueva", info["hole_portal"])):
        if not any((c[0] + dx, c[1] + dy) in d7 for dx, dy in CARD):
            errors.append(f"z7: {label} {c} sin acceso")
    if set(d7) != walk7:
        errors.append(f"z7: {len(walk7) - len(d7)} casillas caminables aisladas")
    order = [d7.get(c, -1) for c in camps] + [d7.get((hx, hy - 1), -1)]
    if order != sorted(order):
        errors.append(f"z7: los campamentos no quedan en orden de recorrido: {order}")

    floor_reach = {}
    for z, cave, cinfo, rooms in floors:
        floor = cinfo["floor"]
        walk = {c for c, it in cave.items() if it[0] in CAVE_FLOORS and bl.walkable(it)}
        d = reach(walk - {cinfo["exit"]}, cinfo["start"], CARD)
        floor_reach[z] = d
        for c, it in cave.items():
            if c in floor:
                continue
            want = pieces_for(neighbors_in(floor, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
            if want is None or len(want) > 1 or (want and it[0] != want[0]) or (not want and it[0] != ROCK):
                errors.append(f"pared z{z} {c}: quiere {want} tiene {it[0]}")
        if not any((cinfo["exit"][0] + dx, cinfo["exit"][1] + dy) in d for dx, dy in CARD):
            errors.append(f"z{z}: la salida {cinfo['exit']} sin acceso")
        room_d = []
        for name, rc, _r, _m in rooms:
            near = [d[c] for c in grow({rc}, 1) if c in d]
            if not near:
                errors.append(f"z{z}: {name} {rc} no se alcanza desde la escalera")
            room_d.append(min(near, default=-1))
        if room_d != sorted(room_d):
            errors.append(f"z{z}: las salas no quedan en orden de recorrido: {room_d}")
        for (x, y) in floor:
            if x < VIEW[0] or x > W - 1 - VIEW[0] or y < VIEW[1] or y > H - 1 - VIEW[1]:
                errors.append(f"z{z} {(x, y)}: se ve el borde de la caja")
                break
    for (x, y) in land:
        if x < VIEW[0] or x > W - 1 - VIEW[0] or y < VIEW[1] or y > H - 1 - VIEW[1]:
            errors.append(f"z7 {(x, y)}: se ve el borde de la caja")
            break

    # --- spawns: un grupo por campamento y uno por sala, nada suelto ---
    spawns7 = []
    spawns_by_z = {Z8: [], Z9: [], Z10: []}
    try:
        for camp, mons in zip(camps, CAMPS):
            cands = [c for c in d7 if c != camp and max(abs(c[0] - camp[0]), abs(c[1] - camp[1])) <= 3]
            names = [(n, st) for n, k, st in mons for _ in range(k)]
            spots = pick_spots(cands, len(names), rng)
            spawns7.append((camp, Z7, [(n, s, st) for (n, st), s in zip(names, spots)]))
        for z, cave, cinfo, rooms in floors:
            d = floor_reach[z]
            for _name, rc, rr, mons in rooms:
                cands = {c for c in d if c not in cinfo["keep"]
                         and math.hypot(c[0] - rc[0], c[1] - rc[1]) <= rr - 0.5}
                names = [(n, st) for n, k, st in mons for _ in range(k)]
                spots = place_sized(cands, names, rc)
                spawns_by_z[z].append((rc, z, [(n, s, st) for (n, st), s in zip(names, spots)]))
    except RuntimeError as error:
        errors.append(str(error))

    if a.preview:
        layers = [(Z7, {(X0 + x, Y0 + y): it for (x, y), it in surf.items()})]
        layers += [(z, {(X0 + x, Y0 + y): it for (x, y), it in cave.items()})
                   for z, cave, _cinfo, _rooms in floors]
        for p in write_preview(a.preview, layers):
            print(f"preview: {p}")
    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        return 1

    counts: dict = {}
    for _c, _z, mons in spawns7 + [s for z in (Z8, Z9, Z10) for s in spawns_by_z[z]]:
        for name, _p, _t in mons:
            counts[name] = counts.get(name, 0) + 1
    lx = [x for x, _ in land]
    ly = [y for _, y in land]
    g = lambda c, z: {"x": X0 + c[0], "y": Y0 + c[1], "z": z}  # noqa: E731
    cave_tiles = sum(len(cinfo["floor"]) for _z, _cave, cinfo, _rooms in floors)
    print(f"isla x{X0 + min(lx)}-{X0 + max(lx)} y{Y0 + min(ly)}-{Y0 + max(ly)}: {len(land)} casillas de tierra "
          f"({len(d7)} caminables), cueva {cave_tiles} casillas en z8/z9/z10; recorrido z7 {max(order)} pasos")
    print(f"llegada {X0 + ARRIVAL[0]},{Y0 + ARRIVAL[1]},7; campamentos " +
          ", ".join(f"{X0 + x},{Y0 + y}" for x, y in camps) +
          f"; cueva {X0 + hx},{Y0 + hy},7; portal final {X0 + cinfo10['exit'][0]},{Y0 + cinfo10['exit'][1]},10")
    print("monstruos: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    # --- mapa: fuera la isla vieja (z7 y z8), adentro la nueva ---
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    md = root[2][0]
    backup = MAP.with_name(MAP.name + ".bak-naturalisland")
    if not backup.exists():
        shutil.copy2(MAP, backup)

    def gone(gx, gy, z):
        return z in (Z7, Z8, Z9, Z10) and OLD_BOX[0] <= gx <= OLD_BOX[2] and OLD_BOX[1] <= gy <= OLD_BOX[3]

    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        area[2] = [t for t in area[2] if not (t[0] in (T_TILE, T_HOUSETILE) and gone(ax + t[1][0], ay + t[1][1], az))]
        if not area[2]:
            md[2].remove(area)
    buckets: dict = {}
    for zz, t in [(Z7, surf)] + [(z, cave) for z, cave, _cinfo, _rooms in floors]:
        for (x, y), it in t.items():
            buckets.setdefault(((X0 + x) & ~0xFF, (Y0 + y) & ~0xFF, zz), []).append((X0 + x, Y0 + y, it))
    for (bx, by, zz), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, zz)), []]
        for gx, gy, it in sorted(lst, key=lambda t: (t[1], t[0])):
            area[2].append(NP.new_tile_node(gx, gy, bx, by, it, TEMPLE_BACK))
        md[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    # --- spawns: fuera los bloques viejos y todo lo que caiga en la caja vieja ---
    with open(SPAWNS, encoding="latin-1", newline="") as f:
        sp = f.read()
    sp = re.sub(r"[ \t]*<!-- BEGIN NATURAL_ISLAND_\w+.*?<!-- END NATURAL_ISLAND_\w+ -->\r?\n?", "", sp, flags=re.S)
    sp = re.sub(r'[ \t]*<spawn centerx="(\d+)" centery="(\d+)" centerz="(\d+)"[^>]*>.*?</spawn>\r?\n?',
                lambda m: "" if gone(int(m.group(1)), int(m.group(2)), int(m.group(3))) else m.group(0), sp, flags=re.S)
    block = "\t<!-- BEGIN NATURAL_ISLAND_SPAWNS (scripts/map/generate-natural-island.py) -->\n" + \
        spawn_xml(spawns7 + [s for z in (Z8, Z9, Z10) for s in spawns_by_z[z]]) + \
        "\n\t<!-- END NATURAL_ISLAND_SPAWNS -->\n"
    sp = sp.replace("</spawns>", block + "</spawns>")
    with open(SPAWNS, "w", encoding="latin-1", newline="") as f:
        f.write(sp)

    # --- carteles ---
    with open(READABLES, encoding="latin-1", newline="") as f:
        rd = f.read()
    rd = re.sub(r"\t?<!-- BEGIN NATURAL_ISLAND_SIGNS -->.*?<!-- END NATURAL_ISLAND_SIGNS -->\r?\n?", "", rd, flags=re.S)
    lines = ["\t<!-- BEGIN NATURAL_ISLAND_SIGNS -->"]
    for (x, y), t in sorted(info["signs"].items()):
        lines.append(f'\t<readable x="{X0 + x}" y="{Y0 + y}" z="7" text="{t}"/>')
    lines.append("\t<!-- END NATURAL_ISLAND_SIGNS -->\n")
    rd = rd.replace("</readables>", "\n".join(lines) + "</readables>")
    with open(READABLES, "w", encoding="latin-1", newline="") as f:
        f.write(rd)

    MANIFEST.write_text(json.dumps({
        "name": "generated-natural-island", "seed": a.seed,
        "box": {"x1": X0, "y1": Y0, "x2": X0 + W - 1, "y2": Y0 + H - 1, "z": [Z7, Z8, Z9, Z10]},
        "oldBoxCleared": {"x1": OLD_BOX[0], "y1": OLD_BOX[1], "x2": OLD_BOX[2], "y2": OLD_BOX[3],
                          "z": [Z7, Z8, Z9, Z10]},
        "land": {"x1": X0 + min(lx), "y1": Y0 + min(ly), "x2": X0 + max(lx), "y2": Y0 + max(ly), "z": Z7},
        "landTiles": len(land), "caveFloorTiles": cave_tiles,
        "landing": g(ARRIVAL, Z7),
        "portalsBack": [dict(g(c, z), to=list(TEMPLE_BACK)) for c, z in
                        ((PORTAL_BACK, Z7), (info["hole_portal"], Z7), (cinfo10["exit"], Z10))],
        "camps": [dict(g(c, Z7), name=n) for c, n in zip(camps, CAMP_NAMES)],
        "cave": {"hole": g(HOLE, Z7), "ladder": g(HOLE, Z8), "ladderExit": g((hx, hy + 1), Z7),
                 "floors": [
                     {"z": z, "start": g(cinfo["start"], z), "exit": g(cinfo["exit"], z),
                      "rooms": [dict(g(rc, z), name=n) for n, rc, _r, _m in rooms]}
                     for z, _cave, cinfo, rooms in floors
                 ]},
        "signs": [g(c, Z7) for c in sorted(info["signs"])],
        "spawns": {"z7": len(spawns7), **{f"z{z}": len(spawns_by_z[z]) for z in (Z8, Z9, Z10)},
                   "monsters": sum(counts.values())},
        "monsters": dict(sorted(counts.items())),
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK carteles {READABLES}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
