"""Receta "cave": cueva de un piso con pasillo largo y angosto, salas, paredes de tierra y bajada desde arriba.

Lo que sale de la ficha (`zones/<zona>.json`): caja (`box`), zona cavable (`land`), piso (`z`), la bajada
(`entrance`: x, y del `432` en el piso de arriba; abajo va la `1385` en la misma casilla) y el recorrido
(`route`: tramos horizontales o verticales, filas a 14+). Las salas salen solas del recorrido (`rooms_along`).
Lo que decide jev (con fallback): qué tiene cada sala y qué monstruos van en cada etapa (ver build.py).

Reglas que cumple (docs/items-and-map/MAPAS.md#cuevas): se cava en bloques 2x2 (cada pared tiene una sola
pieza), nunca piso pegado a la roca lisa, nada de vacío a la vista, techo de roca en el piso de arriba donde no
hay nada, decoración fija y los 2x2 solo donde tapan pared. Código portado de generate-north-pass.py
(`carve_cave`) y generate-beast-valley.py (`ribbon`, `stamp`, `rooms_along`).
"""
from __future__ import annotations

import math
import random

from . import (ALL8, CARD, Noise, Otb, box_cells, grow, neighbors_in, place_stages, polyline, reach,
               slices_by)
from .island import _sizes, footprint

SETTING = "a long narrow earth cave corridor with side rooms"
LEGEND = "# rock/wall, . cave floor, * decoration, M monster, H arrival (below the stairs)"
RIBBON_BAND = 2               # media franja cavable (valle: 5 daba pasillos de 7-9 rectangulares); `band` en la ficha


def stamp(points, r: int) -> set:
    """Casillas a distancia de bloque `r` de una polilínea, en pasos Manhattan (formas ortogonales)."""
    cells = set()

    def block(x, y):
        cells.update({(x + a, y + b) for a in range(-r, r + 1) for b in range(-r, r + 1)})

    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        x, y = x1, y1
        block(x, y)
        for axis in (("x", "y") if abs(x2 - x1) >= abs(y2 - y1) else ("y", "x")):
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


def ribbon(pts, rooms, seed: int, band=RIBBON_BAND, wide=0.68):
    """Franja y núcleo de un pasillo de 3 a 5 de ancho (5 donde el ruido pasa `wide`), zigzag de ±1 lejos de las
    esquinas y salas. Al cavar en bloques 2x2 el ancho sube a 4-6 (valle: wide 0,55 daba 6-8).
    Devuelve (franja donde se puede cavar, núcleo que se cava sí o sí)."""
    nz = Noise(seed + 4242)
    core, i = set(), 0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if x1 != x2 and y1 != y2:   # tramo diagonal (boca -> recorrido): en L, sin zigzag
            core |= stamp([(x1, y1), (x2, y1), (x2, y2)], 1)
            continue
        n = abs(x2 - x1) + abs(y2 - y1)
        sx, sy = (x2 > x1) - (x2 < x1), (y2 > y1) - (y2 < y1)
        for k in range(n + 1):
            x, y = x1 + sx * k, y1 + sy * k
            wob = 0 if min(k, n - k) < 4 else round((nz.fbm(i / 7, 1.5, 2, 31) - 0.5) * 4)
            wob = max(-1, min(1, wob))
            r = 2 if nz.fbm(i / 6, 7.5, 2, 37) > wide else 1
            cx, cy = x + sy * wob, y + sx * wob
            core |= {(cx + a, cy + b) for a in range(-r, r + 1) for b in range(-r, r + 1)}
            i += 1
    for (rx, ry), rr in rooms:
        core |= ellipse(rx + 0.5, ry + 0.5, rr + 0.6, rr)
    # la franja sale del recorrido sin el tramo de la boca: si no, una boca corrida unas casillas hacia la fila
    # de al lado se come la roca de 3 que separa las filas (atajo)
    return stamp(pts[1:], band) | grow(core, 1), core


def carve_cave(seed: int, allowed: set, core: set, start, min_size: int):
    """Cueva en una grilla de bloques 2x2 (autómata celular): todo pasillo y toda pared quedan de 2 de ancho,
    así cada roca que toca piso tiene una única pieza de pared válida."""
    ox, oy = start[0] % 2, start[1] % 2
    blk = lambda c: ((c[0] - ox) // 2, (c[1] - oy) // 2)  # noqa: E731
    cells_of = lambda b: {(ox + 2 * b[0] + i, oy + 2 * b[1] + j) for i in (0, 1) for j in (0, 1)}  # noqa: E731
    allowed_b = {b for b in {blk(c) for c in allowed} if cells_of(b) <= allowed}
    allowed_b = {b for b in allowed_b if all((b[0] + dx, b[1] + dy) in allowed_b for dx, dy in ALL8)}
    core_b = {blk(c) for c in core}
    start_b = blk(start)
    for attempt in range(80):
        rng = random.Random(seed * 1000 + attempt)
        floor = {b for b in allowed_b if rng.random() < 0.55} | core_b
        for _ in range(5):
            nxt = set(core_b)
            for b in allowed_b:
                walls = sum(1 for dx, dy in ALL8 if (b[0] + dx, b[1] + dy) not in floor)
                if walls <= 3 or (b in floor and walls <= 4):
                    nxt.add(b)
            floor = nxt
        floor = set(reach(floor, start_b, CARD))
        changed = True
        while changed:          # sin contactos solo en diagonal: se rellena un bloque del costado
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
    raise RuntimeError(f"no salió una cueva de {min_size}+ casillas que cubra el recorrido (bajar `min` o "
                       "alejar el recorrido del borde de land)")


def rooms(spec) -> list:
    """Salas: las de la ficha (`rooms`: [{"center": [x, y], "r": 3}]) o una a mitad de cada tramo de 20+ y
    otra al final. Devuelve dicts con `center`, `r` y `at` (fracción del recorrido) para jev y el lint."""
    route = [tuple(p) for p in spec["route"]]
    if "rooms" in spec:
        out = [{"center": tuple(r["center"]), "r": r.get("r", 3)} for r in spec["rooms"]]
    else:
        out = [{"center": ((x1 + x2) // 2, (y1 + y2) // 2), "r": 3} for (x1, y1), (x2, y2) in zip(route, route[1:])
               if abs(x2 - x1) + abs(y2 - y1) >= 20]
        out.append({"center": route[-1], "r": 3, "role": "end"})
    samples = polyline(route, 0.5)
    total = samples[-1][2] or 1
    for r in out:
        k = min(samples, key=lambda s: math.hypot(s[0] - r["center"][0], s[1] - r["center"][1]))
        r["at"] = round(k[2] / total, 2)
    return out


def glades(spec) -> list:
    return rooms(spec)


def build(spec: dict, theme, seed: int, decisions: dict, otb: Otb | None = None, world: dict | None = None) -> dict:
    otb = otb or Otb()
    world = world or {}
    size = _sizes()
    rng = random.Random(f"{spec['name']}-{seed}")
    z = spec["z"]
    box = box_cells(spec["box"])
    land = box_cells(spec["land"])
    wall = theme.border("wall")
    ex, ey = spec["entrance"]
    arrival = (ex, ey + 1)                  # al bajar por la 432 se aterriza al sur de la 1385

    # 0. la bajada: en el piso de arriba, una casilla de solo suelo caminable con su norte caminable
    up, north = world.get((ex, ey, z - 1)), world.get((ex, ey - 1, z - 1))
    if not (up and len(up) == 1 and otb.is_ground(up[0]) and otb.walkable(up)):
        raise RuntimeError(f"la bajada {ex},{ey},{z - 1} tiene que ser una casilla de solo suelo caminable: {up}")
    if not (north and otb.walkable(north)):
        raise RuntimeError(f"al subir por la 1385 se llega a {ex},{ey - 1},{z - 1}, que no es caminable: {north}")

    # 1. pasillo: franja + núcleo alrededor del recorrido; el núcleo no puede salirse de land menos 2
    route = [arrival] + [tuple(p) for p in spec["route"]]
    rms = rooms(spec)
    band, core = ribbon(route, [(r["center"], r["r"]) for r in rms], seed, spec.get("band", RIBBON_BAND),
                        spec.get("wide", 0.68))
    safe = {c for c in land if all((c[0] + dx, c[1] + dy) in land for dx in (-2, 2) for dy in (-2, 2))}
    mouth = {(ex + dx, ey + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1, 2)}
    if not mouth <= safe:
        raise RuntimeError(f"la bajada {ex},{ey} queda pegada al borde de land: alejarla 4+ casillas")
    core = (core & safe) | mouth
    floor = carve_cave(seed, land & band, core, arrival, spec.get("min", 500))

    # 2. suelos: piso con su paleta (barro/alterno con ruido), pared donde toca piso, roca lisa el resto
    nz = Noise(seed + 909)
    mud, alt = spec.get("mud", 0.3), spec.get("alt", 0.33)
    tiles = {}
    for c in box:
        if c in floor:
            v = nz.fbm(c[0] / 5, c[1] / 5, 3, 10) + mud - 0.42
            tiles[c] = [theme["mud"] if v > 0.55 else theme["floor_alt"] if v < alt else theme["floor"]]
        else:
            p = wall.piece_at(floor, c) if neighbors_in(floor, *c) else None
            tiles[c] = [p or theme["rock"]]
    tiles[(ex, ey)].append(theme["stair_up"])
    walk = set(floor)                       # la 1385 no bloquea: es caminable (sin monstruos, ver `reserved`)
    reserved = (mouth | grow({arrival}, 1)) & walk
    start = arrival
    base = len(reach(walk, start))

    def block(c, item) -> bool:
        """Pone algo que bloquea en `c` solo si no corta el paso (y su dibujo no tapa piso)."""
        nonlocal base
        if c in reserved or len(tiles[c]) > 1 or (footprint(c, size(item)) - {c}) & floor:
            return False
        walk.discard(c)
        if len(reach(walk, start)) != base - 1:
            walk.add(c)
            return False
        base -= 1
        tiles[c].append(item)
        return True

    # 3. cartel cerca de la llegada, contra la pared
    info = {"landing": arrival, "npc": None, "sign": None, "props": {}, "stairs": (ex, ey)}
    for c in sorted(walk - reserved, key=lambda c: (abs(c[0] - arrival[0]) + abs(c[1] - arrival[1]), c)):
        if abs(c[0] - arrival[0]) + abs(c[1] - arrival[1]) > 6:
            break
        if 8 - len(neighbors_in(floor, *c)) >= 3 and block(c, theme["sign"]):
            info["sign"] = c
            reserved |= grow({c}, 1) & walk
            break

    # 4. salas: lo que decidió jev (o el fallback)
    for k, r in enumerate(rms):
        kind = decisions.get("glades", {}).get(str(k)) or r.get("props")
        cells = sorted(c for c in walk if math.hypot(c[0] - r["center"][0], c[1] - r["center"][1]) <= r["r"] + 2)
        if not kind or not cells:
            continue
        prop = theme["props"][kind]
        info["props"][str(k)] = kind
        if prop.get("paint"):
            for c in cells:
                tiles[c][0] = theme[prop["paint"]]
        ctr = tuple(r["center"])
        if prop.get("center") and ctr in walk and ctr not in reserved and len(tiles[ctr]) == 1:
            tiles[ctr].append(theme[prop["center"]])
            reserved.add(ctr)
        for c in cells:
            if c in reserved or len(tiles[c]) > 1:
                continue
            rock_n = 8 - len(neighbors_in(floor, *c))
            if rock_n >= 2 and rng.random() < prop["edge_rate"]:
                block(c, rng.choice(theme[rng.choice(prop["edge"])]))
            elif rock_n < 2 and rng.random() < prop["floor_rate"]:
                tiles[c].append(rng.choice(theme[rng.choice(prop["floor"])]))

    # 5. el resto del pasillo: piedras contra la pared, piedritas y huesos sueltos (todo fijo)
    for c in sorted(walk, key=lambda c: (c[1], c[0])):
        if c in reserved or len(tiles[c]) > 1:
            continue
        rock_n = 8 - len(neighbors_in(floor, *c))
        p, q = rng.random(), rng.random()
        if rock_n >= 3 and p < spec.get("stones", 0.08):
            if block(c, rng.choice(theme["rubble_2x2"] if q < 0.4 else theme["stones"])):
                continue
        if q < 0.03:
            tiles[c].append(rng.choice(theme["pebbles"]))
        elif q < 0.03 + spec.get("bones", 0.03):
            tiles[c].append(rng.choice(theme["bones"]))

    walk = {c for c in walk if otb.walkable(tiles[c])}
    d = reach(walk, start)
    lost = walk - set(d)
    for c in lost:
        tiles[c].append(theme["stones"][0])
    walk -= lost
    info["lost"] = len(lost)

    # 6. piso de arriba: la bajada y el techo de roca donde no hay nada (si no, se ven los pisos de arriba).
    #    No se pone roca pegada a un piso caminable de arriba (quedaría roca pelada): eso lo marca el lint.
    extra, claims = {(ex, ey, z - 1): [theme["stair_down"]]}, {(ex, ey, z - 1): list(up)}
    above = lambda c: world.get((c[0], c[1], z - 1))  # noqa: E731
    for c in sorted(grow(floor, 1)):
        if above(c) is not None or (c[0], c[1], z - 1) in extra:
            continue
        if any(above((c[0] + dx, c[1] + dy)) and otb.walkable(above((c[0] + dx, c[1] + dy))) for dx, dy in ALL8):
            continue
        extra[(c[0], c[1], z - 1)] = [theme["rock"]]
    roofed = lambda x, y: (x, y, z - 1) in extra or above((x, y)) is not None  # noqa: E731
    info["roof_missing"] = sorted(c for c in walk if not roofed(*c) and not roofed(c[0] + 1, c[1] + 1))

    # 7. monstruos por etapas a lo largo del recorrido caminado
    stages = decisions.get("stages") or spec["stages"]
    avoid = set(reserved) | grow({arrival}, spec.get("clear", 6)) | {c for c in walk if len(tiles[c]) > 1}
    srng = random.Random(f"{spec['name']}-spawns-{seed}")
    spawns = place_stages(stages, slices_by(walk - avoid, d.__getitem__, len(stages)), walk, avoid, z, srng)

    return {"tiles": tiles, "walk": walk, "dist": d, "trail": set(), "shore": set(), "water": set(),
            "land": floor, "forest": set(), "glades": rms, "spawns": spawns, "info": info,
            "samples": polyline(route, 0.5), "seed": seed, "stages": stages,
            "borders": [("wall", floor)], "extra": extra, "claims": claims}
