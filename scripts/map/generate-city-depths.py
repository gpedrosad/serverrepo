#!/usr/bin/env python3
"""Dungeon de la city: 3 pisos de cueva bajo el distrito este (agujero en 185,58,7, al lado de la
Torre del Barquero).

  z8  Guarida de los Orcos   Orc Berserker Pot Thrower x4 (fogón, depósito, pozo) y Carniphila x3
  z9  Nido Hundido           Dragon Lord Hatchling x4 y Emerald Scarab x2
  z10 Bóveda Inundada        Dark Hydra x1 y Dragon Lord Hatchling x2 (sin salida: se vuelve subiendo)

Cada piso son salas redondas unidas por pasillos de 3 de ancho, cavadas en una grilla de bloques
2x2 alineada a la escalera: así toda pared que toca piso tiene **una sola** pieza válida (356-367) y
la roca (101) nunca queda pegada al piso. Se baja por agujeros (479) y se sube con la escalera de
mano (1386) que está justo debajo; usarla deja en x, y+1 del piso de arriba.

Reglas que valida (si algo falla no escribe nada), ver docs/items-and-map/MAPEAR_DUNGEON_CITY.md:
- solo toca casillas propias: vacías o del dungeon viejo; nunca la lava del sur ni la roca de otras
  zonas, y entre el piso y lo ajeno queda al menos la pared;
- desde ningún piso caminable se ve el vacío negro (media pantalla 8x6 con casilla);
- cada pared tiene su pieza exacta y la roca no toca piso;
- todo el piso se alcanza desde la escalera y las salas quedan en orden de recorrido;
- la escalera de mano está sola en su casilla, debajo del agujero, y la casilla al sur del agujero
  (donde deja la escalera) se pisa; la decoración no corta el paso ni tapa escaleras;
- solo decoración que no se mueve ni se levanta (nada de barriles, cajas, huesos agarrables).

Spawns: bloque CITY_DEPTHS_SPAWNS de test-spawn.xml, reemplazado en su lugar.

Uso:
  python3 scripts/map/generate-city-depths.py --dry-run --preview /tmp/city   # valida y dibuja
  python3 scripts/map/generate-city-depths.py                                  # escribe mapa y spawns
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import (MAP, REPO, T_AREA, T_HOUSETILE, T_TILE, Renderer, iter_tiles,  # noqa: E402
                     parse_tree, png_bytes, serialize_tree)

_spec = importlib.util.spec_from_file_location("north_pass", HERE / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)
Noise, neighbors_in, pieces_for, reach, Blocking = NP.Noise, NP.neighbors_in, NP.pieces_for, NP.reach, NP.Blocking
WALL_SIDE, WALL_CORNER, WALL_INNER, ROCK = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER, NP.ROCK
CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD = NP.CAVE_FLOOR, NP.CAVE_FLOOR_ALT, NP.CAVE_MUD
CARD, ALL8 = NP.CARD, NP.ALL8
WALLS = set(WALL_SIDE.values()) | set(WALL_CORNER.values()) | set(WALL_INNER.values())

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
MANIFEST = WORLD / "generated-city-depths.json"

HOLE, LADDER, CAMPFIRE = 479, 1386, 1423
ENTRANCE = (185, 58)                        # agujero de la superficie (z7); la escalera de z8 va debajo
VIEW = (8, 6)                               # media pantalla del cliente 7.6 + 1
LINK_HALF = 1.9                             # medio ancho de los pasillos (>= 1.42: sin cortes en la grilla 2x2)
LANDING_R = 2.2                             # radio del rellano de cada escalera

# decoración fija: nada se mueve ni se levanta (se podría empujar para trabar el paso o tirar)
SKULLS = (2247, 2248, 5016, 5018)           # calaveras sueltas (no bloquean)
BONES = (2248,)                             # huesos enteros (no bloquean); 3125 ya no se usa (nov 2026)
BIG_BONES = 3122                            # esqueleto de dragón grande (bloquea)
PEBBLES = 1336                              # piedritas (no bloquean)
STONES = (1285, 1309, 1323)                 # piedras (bloquean)
MOSSY = 1353                                # piedra con musgo (bloquea)
MUSHROOMS = (4183, 4171, 4181)              # hongos (no bloquean)
WEBS = (1906, 1907, 1908)                   # telarañas (no bloquean)

# Cajas de trabajo por piso: lo propio (vacío o dungeon viejo) dentro de RECT; OLD es la caja del
# dungeon viejo (se reescribe entera).
FLOORS = {
    8: dict(rect=(172, 32, 220, 64), old=(181, 39, 198, 59), mud=0.10, seed=801),
    9: dict(rect=(168, 28, 222, 80), old=(181, 39, 198, 65), mud=0.0, seed=901),
    10: dict(rect=(172, 30, 204, 82), old=(181, 39, 198, 70), mud=0.22, seed=1001),
}

#        (nombre, centro, radio, tema, [(monstruo, cantidad, spawntime)])
ROOMS = {
    8: [
        ("Fogón de los orcos", (190, 52), 4.4, "camp", [("Orc Berserker Pot Thrower", 2, 300)]),
        ("Depósito", (201, 55), 3.6, "store", [("Orc Berserker Pot Thrower", 1, 300)]),
        ("Jardín de carniphilas", (203, 44), 4.4, "garden", [("Carniphila", 3, 175)]),
        ("Pozo", (183, 41), 3.4, "pit", [("Orc Berserker Pot Thrower", 1, 300)]),
    ],
    9: [
        ("Nido", (193, 47), 4.6, "nest", [("Dragon Lord Hatchling", 2, 300)]),
        ("Galería de los escarabajos", (206, 39), 4.2, "bones", [("Emerald Scarab", 2, 600)]),
        ("Cámara de huesos", (207, 58), 4.6, "nest", [("Dragon Lord Hatchling", 2, 300)]),
        ("Grieta", (190, 66), 3.6, "pit", []),
    ],
    10: [
        ("Charcas", (185, 55), 4.4, "bones", [("Dragon Lord Hatchling", 2, 300)]),
        ("Bóveda de la hydra", (188, 41), 5.0, "lair", [("Dark Hydra", 1, 900)]),
    ],
}
# puntos intermedios de cada pasillo (de la escalera a la sala 1, de la sala 1 a la 2, ...)
VIA = {
    8: [[(185, 54)], [(195, 54)], [(204, 50)], [(193, 41)]],
    9: [[], [(199, 42)], [(210, 48)], [(199, 63)]],
    10: [[(190, 59)], []],
}
SPRITE: dict[int, tuple[int, int]] = {}            # id -> (ancho, alto) del sprite, se llena en main()
SIZE2 = {"Orc Berserker Pot Thrower", "Carniphila", "Dragon Lord Hatchling", "Emerald Scarab", "Dark Hydra"}


def sample_line(points, step=0.25):
    out = []
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) / step))
        out += [(ax + (bx - ax) * i / n, ay + (by - ay) * i / n) for i in range(n)]
    return out + [points[-1]]


def written_before() -> dict:
    """Casillas que escribió una corrida anterior (manifiesto): siguen siendo propias."""
    if not MANIFEST.is_file():
        return {}
    cells = json.loads(MANIFEST.read_text(encoding="utf-8")).get("cells", {})
    return {int(z): {(x, y) for y, x0, x1 in runs for x in range(x0, x1 + 1)} for z, runs in cells.items()}


def runs_of(cells) -> list:
    out = []
    for y in sorted({c[1] for c in cells}):
        xs = sorted(c[0] for c in cells if c[1] == y)
        start = prev = xs[0]
        for x in xs[1:]:
            if x != prev + 1:
                out.append([y, start, prev])
                start = x
            prev = x
        out.append([y, start, prev])
    return out


PREVIOUS: dict = {}
RESERVED: set = set()  # accesos/techo de la Mina Enana, escritos por otro generador


def ownership(z: int, world: dict):
    """(propias, ajenas): propias = vacías, del dungeon viejo o escritas antes por este script,
    dentro de RECT."""
    x1, y1, x2, y2 = FLOORS[z]["rect"]
    o = FLOORS[z]["old"]
    prev = PREVIOUS.get(z, set())
    own, foreign = set(), set()
    for x in range(x1 - VIEW[0] - 2, x2 + VIEW[0] + 3):
        for y in range(y1 - VIEW[1] - 2, y2 + VIEW[1] + 3):
            in_old = (o[0] <= x <= o[2] and o[1] <= y <= o[3]) or (x, y) in prev
            has = (x, y, z) in world
            if (x, y, z) in RESERVED:
                if has:
                    foreign.add((x, y))
                continue
            if x1 <= x <= x2 and y1 <= y <= y2 and (in_old or not has):
                own.add((x, y))
            elif has:
                foreign.add((x, y))
    return own, foreign


def allowed_cells(own: set, foreign: set) -> set:
    """Donde puede haber piso: pared propia alrededor, nada ajeno pegado y sin vacío a la vista."""
    solid = own | foreign
    out = set()
    for (x, y) in own:
        if not all((x + dx, y + dy) in own for dx, dy in ALL8):
            continue
        if not all((x + dx, y + dy) in solid for dx in range(-VIEW[0], VIEW[0] + 1) for dy in range(-VIEW[1], VIEW[1] + 1)):
            continue
        out.add((x, y))
    return out


def carve(z: int, start, origin, allowed: set):
    """Piso del piso z: rellano + salas + pasillos, en bloques 2x2 con origen `origin`."""
    nz = Noise(FLOORS[z]["seed"])
    ox, oy = origin
    rooms = ROOMS[z]
    discs = [(start, LANDING_R)] + [(c, r) for _n, c, r, _t, _m in rooms]
    centers = [start] + [c for _n, c, _r, _t, _m in rooms]
    samples = []
    for i in range(len(rooms)):
        samples += sample_line([centers[i]] + VIA[z][i] + [centers[i + 1]])

    def inside(px, py):
        wob = 1.4 * (nz.fbm(px / 3, py / 3, 2, 5) - 0.5)
        return (any(math.hypot(px - c[0], py - c[1]) <= r + wob for c, r in discs)
                or any(math.hypot(px - sx, py - sy) <= LINK_HALF for sx, sy in samples))

    cells_of = lambda b: {(ox + 2 * b[0] + i, oy + 2 * b[1] + j) for i in (0, 1) for j in (0, 1)}  # noqa: E731
    xs = [c[0] for c in allowed]
    ys = [c[1] for c in allowed]
    blocks = {(bx, by) for bx in range((min(xs) - ox) // 2 - 1, (max(xs) - ox) // 2 + 2)
              for by in range((min(ys) - oy) // 2 - 1, (max(ys) - oy) // 2 + 2)
              if cells_of((bx, by)) <= allowed and inside(ox + 2 * bx + 0.5, oy + 2 * by + 0.5)}
    changed = True
    while changed:                                      # sin contactos solo en diagonal
        changed = False
        for (x, y) in sorted(blocks):
            for dx, dy in ((1, 1), (1, -1)):
                d, a, b = (x + dx, y + dy), (x + dx, y), (x, y + dy)
                if d in blocks and a not in blocks and b not in blocks:
                    fill = a if cells_of(a) <= allowed else b if cells_of(b) <= allowed else None
                    if fill is None:
                        blocks.discard(d)
                    else:
                        blocks.add(fill)
                    changed = True
    floor = set().union(*(cells_of(b) for b in blocks))
    return set(reach(floor, start, CARD))


def ground_for(c, floor: set, nz: Noise, mud: float) -> int:
    if c in floor:
        v = nz.fbm(c[0] / 5, c[1] / 5, 3, 10) + mud
        return CAVE_MUD if v > 0.66 else CAVE_FLOOR_ALT if v < 0.36 else CAVE_FLOOR
    wall = pieces_for(neighbors_in(floor, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
    return wall[0] if wall else ROCK


def decorate(tiles: dict, floor: set, start, keep: set, rooms, rng: random.Random, bl: Blocking):
    """Decoración por sala según su tema + piedritas sueltas en los pasillos. Cada pieza que bloquea
    se prueba: si corta el paso no va."""
    walk = set(floor)
    base = len(reach(walk, start, CARD))

    def put(c, iid) -> bool:
        nonlocal base
        if c in keep or c not in floor or len(tiles[c]) > 1:
            return False
        w, h = SPRITE.get(iid, (1, 1))                   # lo grande que bloquea se dibuja hacia arriba-
        if bl.blocks(iid) and any((c[0] - i, c[1] - j) in floor    # izquierda: solo puede tapar pared
                                  for i in range(w) for j in range(h) if (i, j) != (0, 0)):
            return False
        if bl.blocks(iid):
            if len(reach(walk - {c}, start, CARD)) != base - 1:
                return False
            walk.discard(c)
            base -= 1
        tiles[c].append(iid)
        return True

    def rock_n(c):
        return 8 - len(neighbors_in(floor, *c))

    in_room = set()
    for _name, rc, rr, theme, _m in rooms:
        cells = sorted(c for c in floor if math.hypot(c[0] - rc[0], c[1] - rc[1]) <= rr + 0.5)
        in_room.update(cells)
        edge = [c for c in cells if rock_n(c) >= 3]
        rng.shuffle(edge)
        if theme == "camp":                              # fogón al medio, calaveras alrededor
            fire = min(cells, key=lambda c: (math.hypot(c[0] - rc[0], c[1] - rc[1]), c))
            put(fire, CAMPFIRE)
            ring = [c for c in cells if 1.5 <= math.hypot(c[0] - fire[0], c[1] - fire[1]) <= 2.5]
            rng.shuffle(ring)
            for c in ring[:4]:
                put(c, rng.choice(SKULLS))
            for c in edge[:3]:
                put(c, rng.choice(STONES))
        elif theme == "store":                           # piedras apiladas contra la pared, calaveras
            for c in edge[:5]:
                put(c, rng.choice(STONES))
            for c in edge[5:8]:
                put(c, rng.choice(SKULLS + (PEBBLES,)))
        elif theme == "garden":                          # hongos, musgo y telarañas
            for c in edge[:3]:
                put(c, MOSSY)
            for c in edge[3:7]:
                put(c, rng.choice(WEBS))
            inner = [c for c in cells if c not in edge]
            rng.shuffle(inner)
            for c in inner[:6]:
                put(c, rng.choice(MUSHROOMS))
        elif theme == "pit":                             # escombros alrededor de la bajada
            for c in edge[:4]:
                put(c, rng.choice(STONES))
            for c in edge[4:7]:
                put(c, PEBBLES)
        elif theme in ("nest", "bones", "lair"):         # huesos de dragón y calaveras
            big = 1 if theme == "nest" else 2 if theme == "lair" else 0
            for c in edge[:big]:
                put(c, BIG_BONES)
            for c in edge[big:big + 4]:
                put(c, rng.choice(BONES + SKULLS))
            for c in edge[big + 4:big + 6]:
                put(c, rng.choice(STONES))
            if theme == "lair":
                for c in edge[big + 6:big + 9]:
                    put(c, rng.choice(WEBS))
    for c in sorted(floor - in_room):                    # pasillos: algo suelto, sin bloquear
        r = rng.random()
        if r < 0.05:
            put(c, PEBBLES)
        elif r < 0.07 and rock_n(c) >= 3:
            put(c, rng.choice(SKULLS))


def landing_fire(tiles: dict, floor: set, start, keep_path: set, bl: Blocking):
    """Fogata para iluminar el rellano: pegada a la pared, a 2-3 casillas de la escalera."""
    walk = {c for c in floor if bl.walkable(tiles[c])}
    base = len(reach(walk, start, CARD))
    cands = sorted((c for c in floor if 2 <= max(abs(c[0] - start[0]), abs(c[1] - start[1])) <= 3
                    and c not in keep_path and len(tiles[c]) == 1
                    and 8 - len(neighbors_in(floor, *c)) >= 3), key=lambda c: (abs(c[0] - start[0]) + abs(c[1] - start[1]), c))
    for c in cands:
        if len(reach(walk - {c}, start, CARD)) == base - 1:
            tiles[c].append(CAMPFIRE)
            return c
    return None


def pick_spawns(floor: set, tiles: dict, rc, rr, names, avoid: set, bl: Blocking, rng: random.Random):
    """Casillas para los monstruos de una sala: libres, con la huella 2x2 hacia arriba-izquierda
    libre (ahí se dibuja el sprite) y separadas entre sí."""
    free = {c for c in floor if bl.walkable(tiles[c]) and len(tiles[c]) == 1} - avoid
    cands = sorted(c for c in free if math.hypot(c[0] - rc[0], c[1] - rc[1]) <= rr - 0.5)
    rng.shuffle(cands)
    out = []
    for gap in (3, 2, 1):
        out = []
        for name in names:
            for c in cands:
                foot = [(c[0] - dx, c[1] - dy) for dx in (0, 1) for dy in (0, 1)] if name in SIZE2 else [c]
                if all(p in free for p in foot) and all(max(abs(c[0] - o[0]), abs(c[1] - o[1])) >= gap for o, _n in out):
                    out.append((c, name))
                    break
        if len(out) == len(names):
            return out
    raise RuntimeError(f"no hay lugar para {names} en la sala de {rc}")


def build(world: dict, bl: Blocking, rng: random.Random, errors: list):
    out = {}
    start = ENTRANCE
    origin = (start[0] % 2, (start[1] - 1) % 2)          # z8: el bloque de la escalera es y57-58 (y59 toca la lava)
    for z in (8, 9, 10):
        own, foreign = ownership(z, world)
        allowed = allowed_cells(own, foreign)
        if start not in allowed:
            errors.append(f"z{z}: la escalera {start} cae fuera de lo que se puede cavar")
            return out
        floor = carve(z, start, origin, allowed)
        nz = Noise(FLOORS[z]["seed"] + 909)
        d = reach(floor, start, CARD)
        rooms = ROOMS[z]
        last = z == 10
        hole = None
        if not last:                                      # agujero al piso de abajo: en la última sala,
            rc, rr = rooms[-1][1], rooms[-1][2]          # lo más lejos posible, con piso alrededor
            below_own, below_foreign = ownership(z + 1, world)
            below_ok = allowed_cells(below_own, below_foreign)
            cands = [c for c in d if math.hypot(c[0] - rc[0], c[1] - rc[1]) <= rr
                     and all((c[0] + dx, c[1] + dy) in floor for dx, dy in ALL8) and c in below_ok]
            if not cands:
                errors.append(f"z{z}: no hay lugar para el agujero en {rooms[-1][0]}")
                return out
            hole = max(cands, key=lambda c: (d[c], c))
        # casillas a escribir: lo propio cerca del piso + toda la caja vieja
        o = FLOORS[z]["old"]
        near = {(x + dx, y + dy) for (x, y) in floor for dx in range(-VIEW[0] - 1, VIEW[0] + 2)
                for dy in range(-VIEW[1] - 1, VIEW[1] + 2)}
        write = ((near & own) | {(x, y) for x in range(o[0], o[2] + 1) for y in range(o[1], o[3] + 1)}) - {
            (x, y) for x, y, rz in RESERVED if rz == z}
        tiles = {c: [ground_for(c, floor, nz, FLOORS[z]["mud"])] for c in write}
        tiles[start].append(LADDER)
        if hole:
            tiles[hole] = [HOLE]
        # lo que no se toca: la escalera, la casilla donde deja el agujero de arriba y el agujero
        keep = {(start[0] + dx, start[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1, 2)}
        if hole:
            keep |= {(hole[0] + dx, hole[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        fire = landing_fire(tiles, floor, start, keep, bl)
        decorate(tiles, floor, start, keep | ({fire} if fire else set()), rooms, rng, bl)
        walk = {c for c in floor if bl.walkable(tiles[c]) and tiles[c][0] != HOLE}
        dw = reach(walk, start, CARD)
        spawns = []
        avoid = set(keep) | {c for c in floor if max(abs(c[0] - start[0]), abs(c[1] - start[1])) <= 3}
        try:
            for name, rc, rr, _t, mons in rooms:
                names = [n for n, k, _st in mons for _ in range(k)]
                if not names:
                    continue
                st = {n: s for n, _k, s in mons}
                placed = pick_spawns(set(dw), tiles, rc, rr, names, avoid, bl, rng)
                spawns.append((rc, z, [(n, c, st[n]) for c, n in placed]))
        except RuntimeError as e:
            errors.append(f"z{z}: {e}")
        out[z] = dict(tiles=tiles, floor=floor, start=start, hole=hole, own=own, foreign=foreign,
                      walk=walk, d=dw, spawns=spawns, fire=fire, write=write)
        if hole:
            start = hole
            origin = (hole[0] % 2, hole[1] % 2)
    return out


def validate(world: dict, floors: dict, bl: Blocking, errors: list):
    # superficie: el agujero y la casilla al sur (ahí deja la escalera de z8)
    ex, ey = ENTRANCE
    if HOLE not in world.get((ex, ey, 7), []):
        errors.append(f"z7: no está el agujero en {ex},{ey}")
    if not bl.walkable(world.get((ex, ey + 1, 7), [])):
        errors.append(f"z7: la escalera de z8 deja en {ex},{ey + 1} y no se pisa")
    for z, f in floors.items():
        tiles, floor, start, hole = f["tiles"], f["floor"], f["start"], f["hole"]
        for c, it in tiles.items():
            if c not in f["own"]:
                errors.append(f"z{z} {c}: casilla ajena")
            if c in floor:
                continue
            want = pieces_for(neighbors_in(floor, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
            if want is None or len(want) > 1 or (want and it != [want[0]]) or (not want and it != [ROCK]):
                errors.append(f"z{z} pared {c}: quiere {want} tiene {it}")
        for c in floor:
            for dx, dy in ALL8:
                n = (c[0] + dx, c[1] + dy)
                if n not in tiles:
                    errors.append(f"z{z} {c}: pegado a {n}, que no es del dungeon")
            if not all((c[0] + dx, c[1] + dy) in tiles or (c[0] + dx, c[1] + dy, z) in world and (c[0] + dx, c[1] + dy) not in f["own"]
                       for dx in range(-VIEW[0], VIEW[0] + 1) for dy in range(-VIEW[1], VIEW[1] + 1)):
                errors.append(f"z{z} {c}: se ve el vacío negro")
        if tiles[start] != [tiles[start][0], LADDER] or tiles[start][0] not in (CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD):
            errors.append(f"z{z}: la escalera {start} no está sola sobre piso de cueva: {tiles[start]}")
        if set(f["d"]) != f["walk"]:
            errors.append(f"z{z}: {len(f['walk']) - len(f['d'])} casillas caminables aisladas")
        order = []
        for name, rc, _r, _t, _m in ROOMS[z]:
            near = [f["d"][c] for c in f["d"] if max(abs(c[0] - rc[0]), abs(c[1] - rc[1])) <= 1]
            if not near:
                errors.append(f"z{z}: {name} {rc} no se alcanza desde la escalera")
            order.append(min(near, default=-1))
        if order != sorted(order):
            errors.append(f"z{z}: las salas no quedan en orden de recorrido: {order}")
        if hole:
            below = floors.get(z + 1)
            if below is None or below["start"] != hole:
                errors.append(f"z{z}: el agujero {hole} no tiene la escalera abajo")
            south = (hole[0], hole[1] + 1)
            if south not in f["d"]:
                errors.append(f"z{z}: la escalera de abajo deja en {south} y no se alcanza")
            if not any((hole[0] + dx, hole[1] + dy) in f["d"] for dx, dy in CARD):
                errors.append(f"z{z}: el agujero {hole} sin acceso")
        for _rc, _z, mons in f["spawns"]:
            for name, c, _st in mons:
                if c not in f["d"] or len(tiles[c]) != 1:
                    errors.append(f"z{z}: spawn de {name} en {c} no está sobre piso libre")
        for c, it in tiles.items():
            for i in it[1:]:
                rec = bl.otb.get(i, {})
                if {"moveable", "pickupable"} & set(rec.get("flags", [])):
                    errors.append(f"z{z} {c}: {i} {rec.get('name')} se puede mover o levantar")


def spawn_block(floors: dict) -> str:
    lines = ["\t<!-- BEGIN CITY_DEPTHS_SPAWNS (scripts/map/generate-city-depths.py) -->"]
    for z in sorted(floors):
        for (cx, cy), zz, mons in floors[z]["spawns"]:
            lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="{zz}" radius="3">')
            for name, (mx, my), st in mons:
                lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{zz}" spawntime="{st}" />')
            lines.append("\t</spawn>")
    lines.append("\t<!-- END CITY_DEPTHS_SPAWNS -->\n")
    return "\n".join(lines)


def write_preview(base: Path, floors: dict, world: dict):
    rd = Renderer()
    out = []
    for z, f in floors.items():
        t = {(x, y, zz): it for (x, y, zz), it in world.items() if zz == z}
        for (x, y), it in f["tiles"].items():
            t[(x, y, z)] = it
        xs = [c[0] for c in f["floor"]]
        ys = [c[1] for c in f["floor"]]
        w, h, img = rd.area(t, min(xs) - VIEW[0], min(ys) - VIEW[1], max(xs) + VIEW[0], max(ys) + VIEW[1], z)
        p = base.with_name(f"{base.name}-z{z}.png")
        p.write_bytes(png_bytes(w, h, bytes(img)))
        out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path, help="prefijo: escribe <prefijo>-z8.png ... <prefijo>-z10.png")
    a = ap.parse_args()

    bl = Blocking()
    rd = Renderer(otb=bl.otb)
    for iid in (CAMPFIRE, BIG_BONES, PEBBLES, MOSSY) + SKULLS + BONES + STONES + MUSHROOMS + WEBS:
        e = rd.entry(iid)
        SPRITE[iid] = (e["w"], e["h"]) if e else (1, 1)
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    world = {(x, y, z): items for x, y, z, items in iter_tiles(root)}
    PREVIOUS.update(written_before())
    mine = MAP.parent / "generated-dwarven-mine.json"
    if mine.exists():
        RESERVED.update(tuple(map(int, p.split(","))) for p in json.loads(mine.read_text())["cells"])
    rng = random.Random(4711)
    errors: list[str] = []
    floors = build(world, bl, rng, errors)
    if not errors:
        validate(world, floors, bl, errors)
    if a.preview and floors:
        for p in write_preview(a.preview, floors, world):
            print(f"preview: {p}")
    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        return 1

    for z, f in floors.items():
        counts = {}
        for _c, _z, mons in f["spawns"]:
            for name, _p, _st in mons:
                counts[name] = counts.get(name, 0) + 1
        print(f"z{z}: {len(f['floor'])} casillas de piso ({len(f['walk'])} caminables), escalera {f['start']}, "
              f"agujero {f['hole']}, fogata {f['fire']}; " + ", ".join(f"{k} x{v}" for k, v in counts.items()))
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    md = root[2][0]
    gone = {(x, y, z) for z, f in floors.items() for (x, y) in f["tiles"]}
    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        area[2] = [t for t in area[2] if not (t[0] in (T_TILE, T_HOUSETILE) and (ax + t[1][0], ay + t[1][1], az) in gone)]
        if not area[2]:
            md[2].remove(area)
    buckets: dict = {}
    for z, f in floors.items():
        for (x, y), it in f["tiles"].items():
            buckets.setdefault((x & ~0xFF, y & ~0xFF, z), []).append((x, y, it))
    for (bx, by, z), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, z)), []]
        for x, y, it in sorted(lst, key=lambda t: (t[1], t[0])):
            area[2].append(NP.new_tile_node(x, y, bx, by, it))
        md[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    print(f"escrito: {MAP}")

    names = {8: "den", 9: "deeper", 10: "vault"}
    meta = {names[z]: {"z": z, "start": [*f["start"], z], "hole": list(f["hole"]) if f["hole"] else None,
                       "rooms": [{"name": n, "center": list(c)} for n, c, _r, _t, _m in ROOMS[z]]}
            for z, f in floors.items()}
    cells = {str(z): runs_of(set(f["tiles"]) | PREVIOUS.get(z, set())) for z, f in floors.items()}
    MANIFEST.write_text(json.dumps({"entrance": [*ENTRANCE, 7], "zones": meta}, indent=2, ensure_ascii=False)[:-2]
                        + ',\n  "cells": ' + json.dumps(cells, separators=(",", ":")) + "\n}\n", encoding="utf-8")
    print(f"manifiesto: {MANIFEST}")

    sp = SPAWNS.read_text(encoding="latin-1")
    pat = re.compile(r"\t?<!-- BEGIN CITY_DEPTHS_SPAWNS.*?<!-- END CITY_DEPTHS_SPAWNS -->\n?", re.S)
    block = spawn_block(floors)
    sp = pat.sub(lambda _m: block, sp, count=1) if pat.search(sp) else sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")
    print(f"spawns: {SPAWNS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
