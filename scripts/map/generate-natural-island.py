#!/usr/bin/env python3
"""Isla irregular con costa y bordes como los del mapa real (no cortes rectos).

Reglas aprendidas de test.otbm (ver docs/items-and-map/map-kb/):
  - Costa: el pasto 4526 que toca agua lleva un borde del set 4644-4655 según
    hacia dónde está el agua (lado, esquina exterior o esquina interior).
  - Pasto/tierra: el pasto que toca tierra 103 se cambia por un suelo de pasto con
    borde ya dibujado (110-121), según hacia dónde está la tierra.
  - Ninguna casilla de tierra o pasto queda con el otro terreno en lados opuestos
    (eso no tiene pieza y se ve roto): se corrige la forma hasta que todo encaja.

Uso:
  python3 scripts/map/generate-natural-island.py --dry-run --preview /tmp/isla.png
  python3 scripts/map/generate-natural-island.py --x0 120 --y0 424 --seed 7
"""
from __future__ import annotations

import argparse
import json
import math
import random
import struct
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kb"))
from mapdata import DIRS, MAP, REPO, Renderer, load_tiles, png_bytes  # noqa: E402

WATER = 4608
GRASS = 4756
GRASS_COAST = 4526
DIRT = 103

# lado(s) con agua -> borde de costa (sobre pasto 4526)
COAST_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
COAST_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
COAST_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}

# lado(s) con tierra -> suelo de pasto con borde dibujado
DIRT_SIDE = {"n": 111, "e": 112, "s": 110, "w": 113}
DIRT_CORNER = {("n", "w"): 120, ("n", "e"): 121, ("s", "w"): 119, ("s", "e"): 118}
DIRT_INNER = {"nw": 116, "ne": 117, "sw": 115, "se": 114}

TREES = (2701, 2702, 2703, 2704, 2705, 2706, 2708, 4009)   # 2x2, bloquean
BUSHES = (2767, 2786, 2768)
SMALL = (4158, 2740, 4179, 4150, 4183)                       # flores, hongos, maleza
DIRT_DECO = (4224, 2710)                                      # rama, árbol seco

DIAG_SIDES = {"nw": ("n", "w"), "ne": ("n", "e"), "sw": ("s", "w"), "se": ("s", "e")}


class Noise:
    """Value noise 2D con octavas (determinista por semilla)."""

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


def neighbors_in(mask: set, x: int, y: int) -> set[str]:
    return {d for d, (dx, dy) in DIRS.items() if (x + dx, y + dy) in mask}


def largest_component(cells: set) -> set:
    seen, best = set(), set()
    for c in cells:
        if c in seen:
            continue
        comp, q = set(), deque([c])
        seen.add(c)
        while q:
            x, y = q.popleft()
            comp.add((x, y))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if n in cells and n not in seen:
                    seen.add(n)
                    q.append(n)
        if len(comp) > len(best):
            best = comp
    return best


def pieces_for(other: set[str], side, corner, inner) -> list[int] | None:
    """Piezas para una casilla según en qué direcciones está el otro terreno.
    None = combinación sin pieza (lados opuestos)."""
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


def shape_land(w: int, h: int, seed: int) -> set:
    noise = Noise(seed)
    cx, cy = w / 2, h / 2
    rx, ry = w * 0.36, h * 0.36
    land = set()
    for y in range(h):
        for x in range(w):
            # deformación de dominio para costas irregulares (bahías y cabos)
            wx = x + 18 * (noise.fbm(x / 16, y / 16, 3, 50) - 0.5)
            wy = y + 18 * (noise.fbm(x / 16, y / 16, 3, 80) - 0.5)
            d = math.hypot((wx - cx) / rx, (wy - cy) / ry)
            v = noise.fbm(x / 8, y / 8, 4, 0)
            if 1.0 - d + 0.9 * (v - 0.5) > 0.1:
                land.add((x, y))
    margin = 9
    land = {(x, y) for x, y in land if margin <= x < w - margin and margin - 2 <= y < h - margin + 2}
    return land


def smooth(cells: set, w: int, h: int, passes=2) -> set:
    for _ in range(passes):
        nxt = set()
        for y in range(h):
            for x in range(w):
                n = len(neighbors_in(cells, x, y))
                if ((x, y) in cells and n >= 4) or ((x, y) not in cells and n >= 6):
                    nxt.add((x, y))
        cells = nxt
    return cells


def fix_until_valid(inner: set, w: int, h: int, side, corner, inner_map, keep: set | None = None,
                    single: bool = False) -> set:
    """Saca de `inner` las casillas de afuera (vecinas) que no tienen pieza posible
    agregándolas a `inner`, y quita celdas de `inner` de 1 de ancho. Itera hasta estable."""
    for _ in range(200):
        changed = False
        # celdas de inner de 1 de ancho (el borde de afuera no puede cubrirlas)
        for (x, y) in list(inner):
            out = {d for d, (dx, dy) in DIRS.items() if (x + dx, y + dy) not in inner}
            if {"n", "s"} <= out or {"e", "w"} <= out:
                inner.discard((x, y))
                changed = True
        # casillas del exterior que tocan inner con una combinación sin pieza
        for y in range(h):
            for x in range(w):
                if (x, y) in inner or (keep is not None and (x, y) not in keep):
                    continue
                other = neighbors_in(inner, x, y)
                pcs = pieces_for(other, side, corner, inner_map) if other else []
                if other and (pcs is None or (single and len(pcs) > 1)):
                    inner.add((x, y))
                    changed = True
        if not changed:
            return inner
    raise RuntimeError("no converge")


def build(w: int, h: int, seed: int) -> dict[tuple[int, int], list[int]]:
    rng = random.Random(seed)
    noise = Noise(seed + 1)

    # 1) tierra firme: forma, suavizado, una sola masa, sin lagos chicos
    land = largest_component(smooth(shape_land(w, h, seed), w, h))
    water = {(x, y) for y in range(h) for x in range(w)} - land
    ocean = set()
    q = deque([(0, 0)])
    ocean.add((0, 0))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n in water and n not in ocean:
                ocean.add(n)
                q.append(n)
    land |= water - ocean  # rellena lagos internos
    # la costa va sobre el pasto: el "otro terreno" visto desde la tierra es el agua
    all_cells = {(x, y) for y in range(h) for x in range(w)}
    sea = fix_until_valid(all_cells - land, w, h, COAST_SIDE, COAST_CORNER, COAST_INNER)
    land = all_cells - sea

    # distancia al agua
    dist = {c: 0 for c in sea}
    q = deque(sea)
    while q:
        x, y = q.popleft()
        for dx, dy in DIRS.values():
            n = (x + dx, y + dy)
            if n in all_cells and n not in dist:
                dist[n] = dist[(x, y)] + 1
                q.append(n)

    # 2) claros de tierra adentro (lejos de la costa)
    dirt = {(x, y) for (x, y) in land if dist[(x, y)] >= 4
            and 0.75 * noise.fbm(x / 7, y / 7, 3, 300) + 0.25 * noise.fbm(x / 2.5, y / 2.5, 2, 400) > 0.58}
    dirt = smooth(dirt, w, h, passes=1)
    deep = {c for c in land if dist[c] >= 3}
    dirt = fix_until_valid(dirt & deep, w, h, DIRT_SIDE, DIRT_CORNER, DIRT_INNER, keep=deep)
    # el pasto con borde de tierra no puede ser además costa
    for _ in range(50):
        bad = {c for c in land - dirt if dist[c] <= 1 and neighbors_in(dirt, *c)}
        if not bad:
            break
        dirt -= {(x + dx, y + dy) for (x, y) in bad for dx, dy in DIRS.values()}
        dirt = fix_until_valid(dirt, w, h, DIRT_SIDE, DIRT_CORNER, DIRT_INNER, keep=deep)

    # 3) suelos y bordes
    tiles: dict[tuple[int, int], list[int]] = {}
    for c in all_cells:
        x, y = c
        if c in sea:
            tiles[c] = [WATER]
            continue
        if c in dirt:
            tiles[c] = [DIRT]
            continue
        coast = pieces_for(neighbors_in(sea, x, y), COAST_SIDE, COAST_CORNER, COAST_INNER)
        if coast:
            tiles[c] = [GRASS_COAST, *coast]
            continue
        edge = pieces_for(neighbors_in(dirt, x, y), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
        if edge:
            if len(edge) > 1:  # dos piezas de pasto no se apilan: esa casilla pasa a tierra
                raise RuntimeError(f"pasto {c} necesita {edge}")
            tiles[c] = [edge[0]]
            continue
        tiles[c] = [GRASS]

    # 4) decoración: bosquecitos por ruido, arbustos y flores sueltas
    occupied = set()
    order = sorted(land - dirt, key=lambda c: (c[1], c[0]))
    for c in order:
        x, y = c
        if len(tiles[c]) > 1 or dist[c] < 2 or tiles[c][0] != GRASS:
            continue
        grove = noise.fbm(x / 7, y / 7, 3, 500)
        r = rng.random()
        # árbol 2x2: necesita su casilla y las 3 del noroeste libres de otro árbol
        if grove > 0.52 and r < 0.55 and not any((x - i, y - j) in occupied for i in range(-1, 3) for j in range(-1, 3)):
            tiles[c].append(rng.choice(TREES))
            occupied |= {(x, y), (x - 1, y), (x, y - 1), (x - 1, y - 1)}
        elif r < 0.035 and c not in occupied:
            tiles[c].append(rng.choice(BUSHES))
            occupied.add(c)
        elif r < 0.07 and c not in occupied:
            tiles[c].append(rng.choice(SMALL))
    for c in dirt:
        if rng.random() < 0.03 and dist[c] >= 5:
            tiles[c].append(rng.choice(DIRT_DECO))
    return tiles


def validate(tiles: dict[tuple[int, int], list[int]]) -> list[str]:
    """Chequeo independiente: toda casilla de tierra junto al agua tiene su pieza exacta."""
    sea = {c for c, it in tiles.items() if it[0] == WATER}
    dirt = {c for c, it in tiles.items() if it[0] == DIRT}
    errs = []
    for c, it in tiles.items():
        if it[0] in (WATER, DIRT, HOLE):
            continue
        want = pieces_for(neighbors_in(sea, *c), COAST_SIDE, COAST_CORNER, COAST_INNER)
        have = [i for i in it[1:] if 4644 <= i <= 4655]
        if want is None or sorted(want) != sorted(have):
            errs.append(f"costa {c}: quiere {want} tiene {have}")
        if neighbors_in(dirt, *c):
            e = pieces_for(neighbors_in(dirt, *c), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
            if not e or e != [it[0]]:
                errs.append(f"tierra {c}: quiere {e} tiene {it[0]}")
    return errs


# --- escritura OTBM ---------------------------------------------------------
NODE_START, NODE_END, ESC = 0xFE, 0xFF, 0xFD


def esc(b: bytes) -> bytes:
    out = bytearray()
    for v in b:
        if v in (NODE_START, NODE_END, ESC):
            out.append(ESC)
        out.append(v)
    return bytes(out)


def encode_areas(tiles: dict[tuple[int, int, int], list[int]]) -> bytes:
    buckets: dict[tuple[int, int, int], list] = {}
    for (x, y, z), items in tiles.items():
        buckets.setdefault((x & ~0xFF, y & ~0xFF, z), []).append((x, y, items))
    out = bytearray()
    for (bx, by, z), lst in sorted(buckets.items()):
        out += bytes([NODE_START, 4]) + esc(struct.pack("<HHB", bx, by, z))
        for x, y, items in sorted(lst, key=lambda t: (t[1], t[0])):
            out += bytes([NODE_START, 5]) + esc(struct.pack("<BBBH", x - bx, y - by, 9, items[0]))
            for it in items[1:]:
                out += bytes([NODE_START, 6]) + esc(struct.pack("<H", it)) + bytes([NODE_END])
            out.append(NODE_END)
        out.append(NODE_END)
    return bytes(out)


def map_data_end(raw: bytes) -> int:
    """Offset del NODE_END que cierra MAP_DATA (respetando escapes)."""
    depth, pos, n = 0, 4, len(raw)
    while pos < n:
        b = raw[pos]
        if b == ESC:
            pos += 2
            continue
        if b == NODE_START:
            depth += 1
            pos += 2
            continue
        if b == NODE_END:
            if depth == 2:
                return pos
            depth -= 1
        pos += 1
    raise ValueError("MAP_DATA sin cierre")


# --- cueva debajo de la isla -------------------------------------------------
# Reglas aprendidas de las cuevas de test.otbm (pisos 8-9):
#   roca = suelo 101 (bloquea); piso = tierra 351-355;
#   la roca que toca piso se cambia por "dirt wall" 356-367 según hacia dónde está el piso.
#   Entrada: agujero 469 sobre pasto en z (como en el mapa); debajo, escalera 1386 (sube a x, y+1, z-1).
ROCK = 101
CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD = 351, 352, 355
HOLE, LADDER = 469, 1386
WALL_SIDE = {"s": 356, "n": 357, "e": 358, "w": 359}
WALL_CORNER = {("s", "e"): 364, ("s", "w"): 365, ("n", "w"): 366, ("n", "e"): 367}
WALL_INNER = {"se": 360, "sw": 361, "nw": 362, "ne": 363}
CAVE_ROCKS = (1309, 1323)  # montones de piedra 2x2, bloquean
CAVE_PEBBLES = (1336,)
ALL8 = list(DIRS.values())


def _reach(walk: set, start) -> set:
    seen, q = {start}, deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in ALL8:
            n = (x + dx, y + dy)
            if n in walk and n not in seen:
                seen.add(n)
                q.append(n)
    return seen


def pick_hole(island: dict) -> tuple[int, int]:
    """Como en el mapa real, el agujero 469 va sobre pasto: casilla de pasto liso rodeada
    (radio 2) de pasto sin nada encima; la de abajo queda libre para salir por la escalera."""
    def plain(c):
        it = island.get(c)
        return it == [GRASS]
    cands = [c for c in island if plain(c)
             and all(plain((c[0] + dx, c[1] + dy)) for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2))]
    if not cands:
        raise RuntimeError("la isla no tiene un claro de pasto de 5x5 para el agujero")
    cx = sum(x for x, _ in cands) / len(cands)
    cy = sum(y for _, y in cands) / len(cands)
    return min(cands, key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2)


def build_cave(island: dict, w: int, h: int, seed: int) -> tuple[dict, tuple[int, int]]:
    all_cells = {(x, y) for y in range(h) for x in range(w)}
    sea = {c for c, it in island.items() if it[0] == WATER}
    dist = {c: 0 for c in sea}
    q = deque(sea)
    while q:
        x, y = q.popleft()
        for dx, dy in ALL8:
            n = (x + dx, y + dy)
            if n in all_cells and n not in dist:
                dist[n] = dist[(x, y)] + 1
                q.append(n)
    allowed = {c for c in all_cells if dist.get(c, 0) >= 3}
    hole = pick_hole(island)
    hx, hy = hole
    core = {(hx + dx, hy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}

    for attempt in range(40):
        rng = random.Random(seed * 1000 + attempt)
        floor = {c for c in allowed if rng.random() < 0.55} | core
        for _ in range(5):  # autómata celular clásico de cuevas
            nxt = set(core)
            for c in allowed:
                walls = sum(1 for dx, dy in ALL8 if (c[0] + dx, c[1] + dy) not in floor)
                if walls <= 3 or (c in floor and walls <= 4):
                    nxt.add(c)
            floor = nxt
        for _ in range(30):
            prev = set(floor)
            floor = fix_until_valid(floor, w, h, WALL_SIDE, WALL_CORNER, WALL_INNER, keep=allowed, single=True)
            floor |= core
            floor = _reach(floor, hole)
            if floor == prev:
                break
        if len(floor) >= 350:
            break
    else:
        raise RuntimeError("no salió una cueva suficientemente grande")

    noise = Noise(seed + 909)
    rng = random.Random(seed + 4242)
    cave: dict[tuple[int, int], list[int]] = {}
    for c in all_cells:
        x, y = c
        if c in floor:
            v = noise.fbm(x / 5, y / 5, 3, 10)
            g = CAVE_MUD if v > 0.66 else CAVE_FLOOR_ALT if v < 0.36 else CAVE_FLOOR
            cave[c] = [g]
            continue
        wall = pieces_for(neighbors_in(floor, x, y), WALL_SIDE, WALL_CORNER, WALL_INNER)
        cave[c] = [wall[0]] if wall else [ROCK]
    cave[hole].append(LADDER)

    # piedras: sin cortar el paso (se prueba cada una)
    walk = set(floor)
    base = len(_reach(walk, hole))
    for c in sorted(floor, key=lambda c: (c[1], c[0])):
        if c in core or len(cave[c]) > 1:
            continue
        x, y = c
        rock_n = 8 - len(neighbors_in(floor, x, y))
        r = rng.random()
        if rock_n >= 3 and r < 0.12:
            if len(_reach(walk - {c}, hole)) == base - 1:
                cave[c].append(rng.choice(CAVE_ROCKS))
                walk.discard(c)
                base -= 1
        elif r < 0.03:
            cave[c].append(rng.choice(CAVE_PEBBLES))
    return cave, hole


def validate_cave(cave: dict, island: dict, hole) -> list[str]:
    floor = {c for c, it in cave.items() if it[0] in (CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD)}
    errs = []
    for c, it in cave.items():
        if c in floor:
            continue
        want = pieces_for(neighbors_in(floor, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
        if want is None or len(want) > 1:
            errs.append(f"roca {c}: combinación sin pieza {want}")
        elif want and it[0] != want[0]:
            errs.append(f"roca {c}: quiere {want[0]} tiene {it[0]}")
        elif not want and it[0] != ROCK:
            errs.append(f"roca {c}: debería ser {ROCK}")
    if LADDER not in cave.get(hole, []):
        errs.append("falta la escalera bajo el agujero")
    exit_tile = island.get((hole[0], hole[1] + 1))
    if exit_tile != [GRASS]:
        errs.append(f"la salida de la escalera {(hole[0], hole[1] + 1)} no está libre: {exit_tile}")
    walk = {c for c in floor if not any(i in CAVE_ROCKS for i in cave[c][1:])}
    lost = walk - _reach(walk, hole)
    if lost:
        errs.append(f"{len(lost)} casillas de cueva no se alcanzan desde la escalera")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--x0", type=int, default=124)
    ap.add_argument("--y0", type=int, default=426)
    ap.add_argument("--z", type=int, default=7)
    ap.add_argument("--width", type=int, default=64)
    ap.add_argument("--height", type=int, default=58)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cave", action="store_true", help="cueva en z+1 con agujero y escalera")
    ap.add_argument("--cave-preview", type=Path)
    a = ap.parse_args()

    local = build(a.width, a.height, a.seed)
    errs = validate(local)
    if errs:
        print("\n".join(errs[:20]), file=sys.stderr)
        return 1
    cave, hole = {}, None
    if a.cave:
        cave, hole = build_cave(local, a.width, a.height, a.seed)
        local[hole] = [HOLE]
        errs = validate_cave(cave, local, hole) + validate(local)
        if errs:
            print("\n".join(errs[:20]), file=sys.stderr)
            return 1
        nfloor = sum(1 for it in cave.values() if it[0] in (CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD))
        print(f"cueva z{a.z + 1}: {nfloor} casillas de piso; agujero {a.x0 + hole[0]},{a.y0 + hole[1]},{a.z} "
              f"-> escalera {a.x0 + hole[0]},{a.y0 + hole[1]},{a.z + 1}; validación OK")
    tiles = {(a.x0 + x, a.y0 + y, a.z): it for (x, y), it in local.items()}
    tiles.update({(a.x0 + x, a.y0 + y, a.z + 1): it for (x, y), it in cave.items()})
    if a.x0 + a.width > 512 or a.y0 + a.height > 512:
        print("ERROR: fuera del mapa 512x512", file=sys.stderr)
        return 1
    existing = load_tiles()
    clash = [p for p in tiles if p in existing]
    if clash:
        print(f"ERROR: {len(clash)} casillas ya existen (ej. {clash[:3]})", file=sys.stderr)
        return 1

    land = sum(1 for it in local.values() if it[0] != WATER)
    print(f"isla seed={a.seed}: caja {a.x0},{a.y0}-{a.x0 + a.width - 1},{a.y0 + a.height - 1} z{a.z}; "
          f"tierra {land}, agua {len(local) - land}, validación OK")

    if a.preview:
        r = Renderer()
        tz = {(x, y, a.z): it for (x, y, _z), it in tiles.items()}
        w, h, img = r.area(tz, a.x0, a.y0, a.x0 + a.width - 1, a.y0 + a.height - 1, a.z)
        a.preview.write_bytes(png_bytes(w, h, img))
        print(f"preview: {a.preview}")
    if a.cave_preview and cave:
        r = Renderer()
        w, h, img = r.area(tiles, a.x0, a.y0, a.x0 + a.width - 1, a.y0 + a.height - 1, a.z + 1)
        a.cave_preview.write_bytes(png_bytes(w, h, img))
        print(f"cave preview: {a.cave_preview}")

    if a.dry_run:
        return 0
    raw = MAP.read_bytes()
    end = map_data_end(raw)
    MAP.write_bytes(raw[:end] + encode_areas(tiles) + raw[end:])
    xs = [x for (x, y), it in local.items() if it[0] != WATER]
    ys = [y for (x, y), it in local.items() if it[0] != WATER]
    manifest = {"name": "generated-natural-island", "seed": a.seed, "z": a.z,
                "box": {"x1": a.x0, "y1": a.y0, "x2": a.x0 + a.width - 1, "y2": a.y0 + a.height - 1, "z": a.z},
                "land": {"x1": a.x0 + min(xs), "y1": a.y0 + min(ys), "x2": a.x0 + max(xs), "y2": a.y0 + max(ys), "z": a.z},
                "center": {"x": a.x0 + a.width // 2, "y": a.y0 + a.height // 2, "z": a.z},
                "tileCount": len(tiles), "landTiles": land}
    if hole:
        manifest["cave"] = {"z": a.z + 1,
                            "hole": {"x": a.x0 + hole[0], "y": a.y0 + hole[1], "z": a.z},
                            "ladder": {"x": a.x0 + hole[0], "y": a.y0 + hole[1], "z": a.z + 1},
                            "ladderExit": {"x": a.x0 + hole[0], "y": a.y0 + hole[1] + 1, "z": a.z},
                            "floorTiles": sum(1 for it in cave.values()
                                              if it[0] in (CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD))}
    out = REPO / "server/YurOTS/ots/data/world/generated-natural-island.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"OK mapa: {MAP}\nOK manifiesto: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
