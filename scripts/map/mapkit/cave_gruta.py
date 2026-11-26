"""Receta cave-gruta: primera versión de cueva (26 nov 2026), solo para la Gruta de los Gárgolas.
Receta "cave": cueva subterránea de caza, cavada en la roca.

Igual que "island" pero bajo tierra: un recorrido en zigzag (filas a 14) cavado con `carve_cave`
(autómata de bloques 2x2, igual que `generate-north-pass.py` / `generate-beast-valley.py`), piso de
tierra con paleta barro/alterno, paredes de tierra `356-367` y roca `101` alrededor. La llegada es un
portal (teleport del templo): no hay boca ni escalera de superficie.

Qué sale de la ficha (`zones/<zona>.json`): caja, recorrido, salas, monstruos y etapas. Lo que decide
jev (con fallback): qué monstruos van en cada etapa, el cartel y la semilla. Todo lo demás es geometría
con semilla: dos corridas con la misma semilla dan el mismo mapa.
"""
from __future__ import annotations

import math
import random

from . import (ALL8, CARD, Noise, Otb, box_cells, grow, neighbors_in, place_stages, polyline, reach,
               slices_by)

RIBBON_BAND = 5          # media franja donde puede haber cueva: tramos paralelos a 14 casillas no se tocan


def _sizes():
    import mapdata
    r = mapdata.Renderer()
    cache = {}

    def size(sid):
        if sid not in cache:
            e = r.entry(sid)
            cache[sid] = (e["w"], e["h"]) if e else (1, 1)
        return cache[sid]
    return size


def stamp(points, r: int) -> set:
    """Casillas a distancia de bloque `r` de una polilínea, avanzando en pasos Manhattan (sin diagonales)."""
    cells = set()

    def block(x, y):
        cells.update({(x + a, y + b) for a in range(-r, r + 1) for b in range(-r, r + 1)})

    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        x, y = x1, y1
        block(x, y)
        axes = ("x", "y") if abs(x2 - x1) >= abs(y2 - y1) else ("y", "x")
        for axis in axes:
            while (x != x2) if axis == "x" else (y != y2):
                if axis == "x":
                    x += 1 if x2 > x else -1
                else:
                    y += 1 if y2 > y else -1
                block(x, y)
    return cells


def ellipse(cx, cy, rx, ry) -> set:
    return {(x, y) for x in range(int(cx - rx) - 1, int(cx + rx) + 2) for y in range(int(cy - ry) - 1, int(cy + ry) + 2)
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1}


def rooms_along(path, min_len=20, r=3):
    """Una sala a mitad de cada tramo de `min_len` casillas o más y otra al final del recorrido."""
    rooms = [(((x1 + x2) // 2, (y1 + y2) // 2), r) for (x1, y1), (x2, y2) in zip(path, path[1:])
             if abs(x2 - x1) + abs(y2 - y1) >= min_len]
    return rooms + [(path[-1], r)]


def ribbon(pts, rooms, seed: int):
    """Franja y núcleo de un pasillo angosto: 4-6 de ancho según ruido, zigzag de ±1 lejos de las
    esquinas y ensanches en las salas. Devuelve (franja permitida, núcleo que se cava sí o sí)."""
    nz = Noise(seed + 4242)
    core, i = set(), 0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if x1 != x2 and y1 != y2:          # tramo diagonal (boca -> recorrido): en L, sin zigzag
            core |= stamp([(x1, y1), (x2, y1), (x2, y2)], 1)
            continue
        n = abs(x2 - x1) + abs(y2 - y1)
        sx, sy = (x2 > x1) - (x2 < x1), (y2 > y1) - (y2 < y1)
        for k in range(n + 1):
            x, y = x1 + sx * k, y1 + sy * k
            wob = 0 if min(k, n - k) < 4 else round((nz.fbm(i / 7, 1.5, 2, 31) - 0.5) * 4)
            wob = max(-1, min(1, wob))
            r = 2 if nz.fbm(i / 6, 7.5, 2, 37) > 0.55 else 1
            cx, cy = x + sy * wob, y + sx * wob          # el zigzag va perpendicular al tramo
            core |= {(cx + a, cy + b) for a in range(-r, r + 1) for b in range(-r, r + 1)}
            i += 1
    for (rx, ry), rr in rooms:
        core |= ellipse(rx + 0.5, ry + 0.5, rr + 0.6, rr)
    band = stamp(pts, RIBBON_BAND) | grow(core, 1)
    return band, core


def carve_cave(seed: int, allowed: set, core: set, start, min_size: int):
    """Cueva en una grilla de bloques 2x2 que después se amplía: todo pasillo y toda pared quedan de
    2 de ancho como mínimo, así cada roca que toca piso tiene una única pieza de pared válida."""
    ox, oy = start[0] % 2, start[1] % 2

    def blk(c):
        return ((c[0] - ox) // 2, (c[1] - oy) // 2)

    def cells_of(b):
        return {(ox + 2 * b[0] + i, oy + 2 * b[1] + j) for i in (0, 1) for j in (0, 1)}

    allowed_b = {b for b in {blk(c) for c in allowed} if cells_of(b) <= allowed}
    # un bloque de margen: la pared de afuera también debe caber en la caja
    allowed_b = {b for b in allowed_b if all((b[0] + dx, b[1] + dy) in allowed_b for dx, dy in ALL8)}
    core_b = {blk(c) for c in core}
    start_b = blk(start)
    for attempt in range(80):
        rng = random.Random(seed * 1000 + attempt)
        floor = {b for b in allowed_b if rng.random() < 0.55} | core_b
        for _ in range(5):                    # autómata celular clásico de cuevas, a escala de bloques
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


SETTING = "an underground earth cave corridor"
LEGEND = "# rock/wall, . floor, * decoration, M monster, T teleport"


def glades(spec) -> list:
    return []


def build(spec: dict, theme, seed: int, decisions: dict, otb: Otb | None = None, world: dict | None = None) -> dict:
    otb = otb or Otb()
    nz = Noise(seed * 7919 + 13)
    z = spec["z"]
    bx = spec["box"]
    box = box_cells(bx)
    # zona cavable = caja menos 6 de cada lado (como generate-beast-valley.py)
    allowed = {(x, y) for x in range(bx[0] + 6, bx[2] - 5) for y in range(bx[1] + 6, bx[3] - 5)}

    route = [tuple(p) for p in spec["route"]]
    mouth = route[0]
    rooms = [((mouth[0], mouth[1] + 1), 3)] + [tuple(r) for r in spec.get("rooms", rooms_along(route))]
    band, core = ribbon(route, rooms, seed)
    core |= {(mouth[0] + dx, mouth[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1, 2)}
    floor = carve_cave(seed, allowed & band, core, (mouth[0], mouth[1] + 1), spec.get("min", 700))

    # llegada del portal: casilla de piso cerca de la boca, fuera del eje del pasillo
    dx, dy = route[1][0] - mouth[0], route[1][1] - mouth[1]
    n = math.hypot(dx, dy) or 1.0
    px, py = -dy / n, dx / n                       # perpendicular al pasillo

    def off(c):
        return (c[0] - mouth[0]) * px + (c[1] - mouth[1]) * py

    near = {c for c in floor if (c[0] - mouth[0]) ** 2 + (c[1] - mouth[1]) ** 2 <= 20}
    landing = max(near, key=lambda c: (abs(off(c)), c))
    ret = max((n2 for n2 in ((landing[0] + 1, landing[1]), (landing[0] - 1, landing[1]),
                             (landing[0], landing[1] + 1), (landing[0], landing[1] - 1)) if n2 in floor),
              key=lambda c: abs(off(c)))
    reserved = {landing, ret}

    # piso final: se descartan bolsillos que no se alcanzan desde la llegada (carve_cave ya conecta)
    floor = floor & set(reach(floor, landing, CARD))

    # suelos y paredes (la pared sale del piso final, no de lo decorado)
    wall = theme.border("wall")
    tiles: dict = {}
    for c in box:
        if c in floor:
            v = nz.fbm(c[0] / 5, c[1] / 5, 3, 10) + spec.get("mud_bias", 0.42) - 0.42
            tiles[c] = [theme["mud"] if v > 0.66 else theme["floor_alt"] if v < 0.36 else theme["floor"]]
        else:
            p = wall.piece_at(floor, c)
            tiles[c] = [p] if p else [theme["rock"]]

    # cartel: en una roca pegada a la llegada, fuera del piso
    sign = None
    for c in sorted(grow({landing}, 2) - floor):
        if c in box and tiles[c][0] == theme["rock"]:
            tiles[c].append(theme["sign"])
            sign = c
            break
    if sign is None:
        raise RuntimeError("no hay roca para el cartel de la llegada")

    # decoración: piedras que bloquean (sin cortar el paso ni tapar piso) y huesos/hongos sueltos
    walk = set(floor)
    base = len(reach(walk, landing, CARD))
    srng = random.Random(f"{spec['name']}-deco-{seed}")
    size = _sizes()
    for c in sorted(floor):
        if c in reserved or len(tiles[c]) > 1:
            continue
        rock_n = 8 - len(neighbors_in(floor, *c))
        r = srng.random()
        if rock_n >= 2 and r < spec.get("stones", 0.05):
            stone = srng.choice(theme["stones"])
            w, h = size(stone)
            foot = {(c[0] - a, c[1] - b) for a in range(w) for b in range(h)} - {c}
            if foot & walk:                        # las piedras 2x2 solo donde tapan pared, no piso
                continue
            if len(reach(walk - {c}, landing, CARD)) == base - 1:
                tiles[c].append(stone)
                walk.discard(c)
                base -= 1
        elif r < 0.05 + spec.get("bones", 0.06):
            tiles[c].append(srng.choice(theme["bones"]))
        elif r < 0.05 + spec.get("bones", 0.06) + 0.05:
            tiles[c].append(srng.choice(theme["mushrooms"]))

    dist = reach(walk, landing, CARD)
    lost = walk - set(dist)
    for c in lost:                                 # no debería pasar (las piedras no cortan el paso)
        tiles[c] = [theme["rock"]]
    walk -= lost

    # techo: roca en el piso de arriba donde está vacío (para no ver los pisos de arriba)
    ceiling = {c: [theme["rock"]] for c in box}

    # monstruos por etapas a lo largo del recorrido caminado
    stages = decisions.get("stages") or spec["stages"]
    avoid = set(reserved)
    avoid |= grow({landing}, spec.get("portal", {}).get("clear", 6))
    avoid |= {c for c in walk if len(tiles[c]) > 1}
    srng = random.Random(f"{spec['name']}-spawns-{seed}")
    spawns = place_stages(stages, slices_by(walk - avoid, dist.__getitem__, len(stages)), walk, avoid, z, srng)

    samples = polyline(route, 0.5)
    return {"tiles": tiles, "walk": walk, "dist": dist, "trail": set(walk), "shore": set(),
            "water": set(), "land": set(), "forest": set(), "glades": [], "spawns": spawns,
            "info": {"landing": landing, "npc": None, "sign": sign, "boat": {}, "return": ret,
                     "props": {}, "lost": len(lost)},
            "samples": samples, "seed": seed, "stages": stages, "ceiling": ceiling, "floor": floor,
            # formato del motor de main (cdb3be4d): techo como celdas extra en z-1 y bordes de pared para el lint
            "extra": {(x, y, z - 1): ids for (x, y), ids in ceiling.items()},
            "borders": [("wall", {c for c, ids in tiles.items()
                                  if ids[0] not in set(theme.border("wall").ids) | {theme["rock"]}})]}
