#!/usr/bin/env python3
"""Camino de los Caídos: franja de tierra nueva en el mar de Epstein Island, con Zombies y Undead Gladiators.

Hasta nov 2026 nadie usaba el Zombie (look 180) ni el Undead Gladiator (look 183): tenían sprite, cadáver propio
y variantes rage, pero ningún spawn. La isla de Epstein no tiene lugar libre en la superficie, así que el camino
es tierra nueva: la forma de la franja ES el recorrido (como la Isla Natural, generate-natural-island.py).

  z7  punta sur de la isla (75-76,228) -> puente de madera de 2 de ancho -> llegada (cartel)
      -> al este por y 240 -> al norte por x 150 -> al oeste por y 198 -> al sur por x 118 -> Patio de las Tumbas

El patio lleva ataúdes de piedra completos (1413 + 1411 abajo) y el camino ataúdes enterrados
completos (1415 + 1416 abajo). Nunca una mitad suelta; lo valida antes de escribir.

Monstruos por etapas según la distancia caminando desde la llegada (docs/items-and-map/MAPAS.md#zonas-de-caza):
sueltos al principio, de a 2 al fondo; los Undead Gladiators se hacen mayoría hacia el final.

Solo z7 y solo casillas de agua o vacío: no toca la isla (ni su costa: deja 1 casilla de agua alrededor de todo
lo que ya existe). Borra el agua vieja de su zona y escribe agua nueva alrededor del camino hasta donde llega la
pantalla del cliente. Escribe su propio bloque en test-spawn.xml (EPSTEIN_ROAD), que generate-epstein-hunts.py
conserva, el cartel en readables.xml y el manifiesto generated-epstein-road.json.

  python3 scripts/map/generate-epstein-road.py --dry-run --preview /tmp/camino.png
  python3 scripts/map/generate-epstein-road.py
Doc: docs/items-and-map/EPSTEIN_HUNTS.md (Camino de los Caídos).
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
from mapdata import (MAP, REPO, T_AREA, T_HOUSETILE, T_TILE, Renderer, iter_tiles,  # noqa: E402
                     parse_tree, png_bytes, serialize_tree)

_spec = importlib.util.spec_from_file_location("north_pass", HERE / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)
Noise, neighbors_in, pieces_for, fix_until_valid, reach, Blocking = (
    NP.Noise, NP.neighbors_in, NP.pieces_for, NP.fix_until_valid, NP.reach, NP.Blocking)
DIRT_SIDE, DIRT_CORNER, DIRT_INNER = NP.DIRT_SIDE, NP.DIRT_CORNER, NP.DIRT_INNER
CARD, ALL8, SIGN = NP.CARD, NP.ALL8, NP.SIGN

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MANIFEST = WORLD / "generated-epstein-road.json"
Z = 7
VIEW = (8, 6)                                   # media pantalla del cliente

# --- dónde: dos rectángulos de mar (sur y este de la isla), menos lo que ya existe y 1 casilla alrededor ---
REGIONS = [(60, 229, 166, 253), (104, 182, 166, 228)]
BRIDGE_X = (75, 76)                             # sale de la costa de la punta sur (y 228)
BRIDGE_Y0 = 229
PATH = [(76, 240), (150, 240), (150, 198), (118, 198), (118, 224)]
HALF = 4.6                                      # medio ancho de la franja (con ruido)
END_BULGE = 1.6                                 # el patio del final es más ancho
END_DIRT = 3.2                                  # radio del claro de tierra del patio

# --- piezas (ids de servidor) ---
WATER, GRASS, GRASS_COAST, DIRT, BRIDGE = 4608, 4756, 4526, 103, 405
COAST_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
COAST_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
COAST_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}
COAST_PIECES = set(range(4644, 4656))
DIRT_PIECES = set(DIRT_SIDE.values()) | set(DIRT_CORNER.values()) | set(DIRT_INNER.values())
DEAD_TREES = (2709, 2710, 2717, 2719, 2720)     # 2x2, bloquean su casilla
DEAD_SMALL = (2713,)                             # árbol seco de 1x1, bloquea (2715 fuera: se sacó del mapa nov 2026)
GRAVES = (1407, 1408)                           # lápidas, bloquean
FLAT = (1409, 2247)                             # lápida plana y cráneo: se pisan (una pieza)
COFFIN_HEAD, COFFIN_FOOT = 1413, 1411           # ataúd de piedra completo: cabecera + pie abajo (y+1)
BURIED_HEAD, BURIED_FOOT = 1415, 1416           # ataúd enterrado completo: cabecera + pie abajo (y+1)
COFFIN_PARTS = (COFFIN_HEAD, COFFIN_FOOT)

# (nombres, monstruos por spawn, spawntime en s, separación mínima entre centros)
STAGES = [(("Zombie",), 1, 120, 11),
          (("Zombie", "Undead Gladiator"), 1, 150, 11),
          (("Zombie", "Undead Gladiator"), 2, 180, 11),
          (("Undead Gladiator", "Undead Gladiator", "Zombie"), 2, 210, 10)]
STAIR_CLEAR = 6                                 # nada a 6 del puente ni de la llegada

SIGN_TEXT = "PATH OF THE FALLEN\\nZombies at the entrance,\\nUndead Gladiators\\nat the far end."


def grow(cells, r: int) -> set:
    return {(x + dx, y + dy) for (x, y) in cells for dx in range(-r, r + 1) for dy in range(-r, r + 1)}


def sample_line(points, step=0.25) -> list:
    out = []
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) / step))
        out += [(ax + (bx - ax) * i / n, ay + (by - ay) * i / n) for i in range(n)]
    return out + [points[-1]]


def wavy_line(points, nz, amp=1.5, step=0.25) -> list:
    """Como sample_line, pero cada tramo se corre de costado (1-2 casillas, con ruido) para que no se vea
    trazado con regla. Quieto cerca de las esquinas, así los tramos se siguen uniendo en el mismo punto."""
    out = []
    for i, ((ax, ay), (bx, by)) in enumerate(zip(points, points[1:])):
        L = math.hypot(bx - ax, by - ay)
        n = max(1, int(L / step))
        px, py = -(by - ay) / L, (bx - ax) / L                  # perpendicular
        for k in range(n):
            s = L * k / n
            w = min(1.0, s / 5, (L - s) / 5)
            off = w * amp * (math.sin(s / 6.5 + i * 1.7) + 0.9 * (nz.fbm(s / 4, i * 9.1, 2, 300) - 0.5))
            out.append((ax + (bx - ax) * k / n + px * off, ay + (by - ay) * k / n + py * off))
    return out + [points[-1]]


def existing_z7(root) -> dict:
    return {(x, y): items for x, y, z, items in iter_tiles(root) if z == Z}


def area_cells(old7: dict) -> tuple[set, set]:
    """Casillas que escribe el generador: los rectángulos menos lo que no es agua y 1 casilla alrededor.
    Devuelve (casillas, casillas de agua vieja que se reemplazan)."""
    keep_out = grow({c for c, it in old7.items() if it[0] != WATER}, 1)
    cells = set()
    for x1, y1, x2, y2 in REGIONS:
        cells |= {(x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)}
    cells -= keep_out
    return cells, {c for c in cells if c in old7}


def build(seed: int, old7: dict, bl):
    rng = random.Random(seed)
    nz = Noise(seed + 1)
    cells, _old = area_cells(old7)
    samples = wavy_line(PATH, nz)
    end = PATH[-1]

    # distancia de cada casilla al recorrido (solo cerca de él)
    near = grow({(round(sx), round(sy)) for sx, sy in samples}, 9) & cells
    ld = {}
    for c in near:
        ld[c] = min(math.hypot(c[0] - sx, c[1] - sy) for sx, sy in samples[::2])

    def half(c):
        r = HALF + 2.4 * (nz.fbm(c[0] / 5, c[1] / 5, 3, 100) - 0.5)
        return r + END_BULGE * max(0.0, 1 - math.hypot(c[0] - end[0], c[1] - end[1]) / 6)

    # 1) camino de tierra en bloques de 2x2 (cada pasto vecino tiene una única pieza de borde)
    def cells_of(b):
        return {(2 * b[0] + i, 2 * b[1] + j) for i in (0, 1) for j in (0, 1)}

    blocks = {(round(sx) // 2, round(sy) // 2) for sx, sy in samples}
    blocks |= {(bx, by) for bx in range(end[0] // 2 - 3, end[0] // 2 + 4) for by in range(end[1] // 2 - 3, end[1] // 2 + 4)
               if math.hypot(2 * bx + 0.5 - end[0], 2 * by + 0.5 - end[1]) <= END_DIRT}
    changed = True
    while changed:                                              # sin contactos solo en diagonal
        changed = False
        for (x, y) in sorted(blocks):
            for dx, dy in ((1, 1), (1, -1)):
                if (x + dx, y + dy) in blocks and (x + dx, y) not in blocks and (x, y + dy) not in blocks:
                    blocks.add((x + dx, y))
                    changed = True
    dirt = set().union(*(cells_of(b) for b in blocks)) & cells

    # 2) tierra firme: dos casillas alrededor del camino (pasto + costa) y el ancho con ruido
    start = (PATH[0][0], PATH[0][1])
    land = (grow(dirt, 2) | {c for c in near if ld[c] <= half(c)}) & cells
    sea = cells - land
    for _ in range(40):
        sea = fix_until_valid(cells - land, cells, COAST_SIDE, COAST_CORNER, COAST_INNER)
        land = cells - sea
        main = set(reach(land, start, CARD))
        # la costa bloquea: un pasto rodeado de costa queda aislado; pasa a ser agua y se recalcula
        free = {c for c in main if not any((c[0] + dx, c[1] + dy) in sea for dx, dy in ALL8)}
        pockets = free - set(reach(free, start, CARD))
        if main == land and not pockets:
            break
        land = main - pockets
    sea = cells - land
    dist = {c: 0 for c in sea}                                  # distancia al agua
    q = deque(sea)
    while q:
        x, y = q.popleft()
        for dx, dy in ALL8:
            n = (x + dx, y + dy)
            if n in cells and n not in dist:
                dist[n] = dist[(x, y)] + 1
                q.append(n)
    deep = {c for c in land if dist.get(c, 0) >= 3}
    dirt = fix_until_valid(dirt & deep, deep, DIRT_SIDE, DIRT_CORNER, DIRT_INNER, single=True)
    for _ in range(60):
        bad = set()
        for c in land - dirt:
            nb = neighbors_in(dirt, *c)
            if not nb:
                continue
            want = pieces_for(nb, DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
            if want is None or len(want) > 1 or dist.get(c, 0) <= 1:
                bad.add(c)
        if not bad:
            break
        dirt -= grow(bad, 1)
        dirt = fix_until_valid(dirt, deep, DIRT_SIDE, DIRT_CORNER, DIRT_INNER, single=True)

    # 3) puente: las piezas de costa (4644-4655) bloquean el paso, así que la madera arranca en la costa de la
    #    isla (y BRIDGE_Y0 - 1) y sigue hasta la primera fila de pasto sin agua alrededor. Para los bordes la
    #    madera cuenta como tierra: las casillas de al lado no llevan costa hacia el puente.
    bridge = set()
    y = BRIDGE_Y0 - 1
    while True:
        row = [(x, y) for x in BRIDGE_X]
        if all(c in land for c in row) and not any(
                (c[0] + dx, c[1] + dy) in sea and not (c[0] + dx in BRIDGE_X and dy < 0)
                for c in row for dx, dy in ALL8):
            break
        if y > BRIDGE_Y0 + 14:
            raise RuntimeError("el puente no llega a tierra")
        bridge |= set(row)
        y += 1
    arrival = (BRIDGE_X[1], y)
    land -= bridge
    sea -= bridge

    # 4) suelos y bordes
    water_like = sea
    tiles = {}
    for c in cells | bridge:
        if c in bridge:
            tiles[c] = [BRIDGE]
        elif c in sea:
            tiles[c] = [WATER]
        elif c in dirt:
            tiles[c] = [DIRT]
        else:
            coast = pieces_for(neighbors_in(water_like, *c), COAST_SIDE, COAST_CORNER, COAST_INNER)
            edge = pieces_for(neighbors_in(dirt, *c), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
            tiles[c] = [GRASS_COAST, *coast] if coast else [edge[0]] if edge else [GRASS]

    # 5) cartel en la llegada, a un costado del camino
    reserved = grow({arrival}, 2) | grow(bridge, 1)
    sign_cands = [c for c in land - dirt if tiles[c] == [GRASS] and c not in reserved and dist.get(c, 0) >= 2]
    sign = min(sign_cands, key=lambda c: (math.hypot(c[0] - arrival[0] - 2, c[1] - arrival[1] - 1), c))
    tiles[sign].append(SIGN)
    reserved |= grow({sign}, 1)

    # 6) patio del final: ataúdes de piedra COMPLETOS (1413 + 1411 abajo) y lápidas
    #    Nunca una mitad suelta: ver MAPAS.md y remove-incomplete-tombs.py.
    for dx, dy in ((-3, -1), (3, -1)):
        head, foot = (end[0] + dx, end[1] + dy), (end[0] + dx, end[1] + dy + 1)
        if (head in land and foot in land and len(tiles.get(head, [])) == 1
                and len(tiles.get(foot, [])) == 1
                and head not in reserved and foot not in reserved):
            tiles[head].append(COFFIN_HEAD)
            tiles[foot].append(COFFIN_FOOT)
    for i, (dx, dy) in enumerate(((0, 4), (-2, -3), (2, -3))):
        c = (end[0] + dx, end[1] + dy)
        if c in land and len(tiles[c]) == 1 and c not in reserved:
            tiles[c].append(GRAVES[i % 2])
    reserved |= grow({end}, 1)

    # 7) monte seco entre el camino y la costa: árboles muertos, lápidas y restos (nunca sobre el camino)
    marked = {c for c in land if tiles[c][0] != GRASS_COAST and len(tiles[c]) > 1}
    occupied = set()
    for c in sorted(land - dirt, key=lambda c: (c[1], c[0])):
        x, y = c
        if tiles[c] != [GRASS] or dist.get(c, 0) < 2 or c in reserved:
            continue
        r = rng.random()
        far = ld.get(c, 99) >= 2.2
        if far and r < 0.22 and not {(x - 1, y), (x, y - 1), (x - 1, y - 1)} & marked \
                and not any((x - i, y - j) in occupied for i in range(-1, 3) for j in range(-1, 3)):
            tiles[c].append(rng.choice(DEAD_TREES))
            occupied |= {(x, y), (x - 1, y), (x, y - 1), (x - 1, y - 1)}
        elif far and r < 0.30 and c not in occupied:
            tiles[c].append(rng.choice(DEAD_SMALL))
            occupied.add(c)
        elif far and r < 0.37 and c not in occupied:
            tiles[c].append(rng.choice(GRAVES))
            occupied.add(c)
        elif r < 0.47 and c not in occupied:
            south = (x, y + 1)
            if (south in tiles and tiles[south] == [GRASS] and dist.get(south, 0) >= 2
                    and south not in reserved and south not in occupied):
                tiles[c].append(BURIED_HEAD)
                tiles[south].append(BURIED_FOOT)
                occupied |= {c, south}
            else:
                tiles[c].append(rng.choice(FLAT))
                occupied.add(c)

    # 8) ningún rincón encerrado: se saca lo que bloquea alrededor de lo que no se alcanza
    for _ in range(20):
        walk = {c for c in land | bridge if bl.walkable(tiles[c])}
        lost = walk - set(reach(walk, arrival, CARD))
        if not lost:
            break
        for c in grow(lost, 1):
            if c in tiles and len(tiles[c]) > 1 and tiles[c][-1] in DEAD_TREES + DEAD_SMALL + GRAVES + COFFIN_PARTS:
                item = tiles[c].pop()
                if item == COFFIN_HEAD:
                    mate = (c[0], c[1] + 1)
                    if mate in tiles and tiles[mate][-1:] == [COFFIN_FOOT]:
                        tiles[mate].pop()
                elif item == COFFIN_FOOT:
                    mate = (c[0], c[1] - 1)
                    if mate in tiles and tiles[mate][-1:] == [COFFIN_HEAD]:
                        tiles[mate].pop()

    return tiles, dict(cells=cells, land=land, sea=sea, dirt=dirt, bridge=bridge, arrival=arrival,
                       sign=sign, end=end)


def place_stages(stages, slices, walk, avoid, rng):
    """Igual que generate-beast-valley.py: cada etapa pone todos los spawns que entran en su franja sin quedar a
    menos de `separación` (Manhattan) de otro centro, también de las etapas anteriores."""
    out, centers = [], []
    for (names, per, spawntime, gap), pool in zip(stages, slices):
        cands = sorted((pool & walk) - avoid)
        rng.shuffle(cands)
        k = 0
        for c in cands:
            if any(abs(c[0] - o[0]) + abs(c[1] - o[1]) < gap for o in centers):
                continue
            spots = [(c[0] + dx, c[1] + dy) for dx in range(-2, 3) for dy in range(-2, 3)
                     if (c[0] + dx, c[1] + dy) in walk and (c[0] + dx, c[1] + dy) not in avoid]
            if len(spots) < per + 3:
                continue
            rng.shuffle(spots)
            centers.append(c)
            out.append((c, [(names[(k + i) % len(names)], s, spawntime) for i, s in enumerate(spots[:per])]))
            k += per
    return out


def slices_by(cells, key, n):
    order = sorted(cells, key=lambda c: (key(c), c))
    size = len(order) / n
    return [set(order[int(i * size):int((i + 1) * size)]) for i in range(n)]


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), mons in spawns:
        lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="{Z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{Z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def row_spans(cells) -> dict:
    """{y: [[x1, x2], ...]}: las casillas que escribió el generador (para volver a correrlo)."""
    out = {}
    for y in sorted({y for _x, y in cells}):
        xs = sorted(x for x, yy in cells if yy == y)
        spans = [[xs[0], xs[0]]]
        for x in xs[1:]:
            if x == spans[-1][1] + 1:
                spans[-1][1] = x
            else:
                spans.append([x, x])
        out[str(y)] = spans
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=31)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path, help="PNG del camino con la isla")
    a = ap.parse_args()

    raw = MAP.read_bytes()
    root = parse_tree(raw)
    old7 = existing_z7(root)
    # idempotente: lo que escribió una corrida anterior vuelve a ser agua antes de calcular
    if MANIFEST.is_file():
        prev = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for y, spans in prev.get("written", {}).items():
            for x1, x2 in spans:
                for x in range(x1, x2 + 1):
                    if (x, int(y)) in old7:
                        old7[(x, int(y))] = [WATER]
    bl = Blocking()
    tiles, info = build(a.seed, old7, bl)
    cells, land, dirt, bridge, arrival = info["cells"], info["land"], info["dirt"], info["bridge"], info["arrival"]
    sea = info["sea"]
    errors = []

    # --- validación ---
    for c in land:
        if any((c[0] + dx, c[1] + dy) not in cells | bridge for dx, dy in ALL8):
            errors.append(f"tierra {c} pegada al borde de la zona (la costa no se puede calcular)")
            break
    for c, it in tiles.items():
        if c not in land or it[0] == DIRT:
            continue
        want = pieces_for(neighbors_in(sea, *c), COAST_SIDE, COAST_CORNER, COAST_INNER)
        if want is None or sorted(want) != sorted(i for i in it[1:] if i in COAST_PIECES):
            errors.append(f"costa {c}: quiere {want} tiene {it}")
        edge = pieces_for(neighbors_in(dirt, *c), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
        if edge is None or len(edge) > 1 or (edge and (it[0] != edge[0] or want)) or (not edge and it[0] in DIRT_PIECES):
            errors.append(f"tierra {c}: quiere {edge} tiene {it}")
    walk = {c for c in land | bridge if bl.walkable(tiles[c])}
    d = reach(walk, arrival, CARD)
    if set(d) != walk:
        errors.append(f"{len(walk) - len(d)} casillas caminables aisladas")
    # punta de la isla: la madera pisa su costa (y BRIDGE_Y0 - 1) y se llega desde el pasto de arriba
    for x in BRIDGE_X:
        coast, grass = (x, BRIDGE_Y0 - 1), (x, BRIDGE_Y0 - 2)
        if old7.get(coast) != [GRASS_COAST, COAST_SIDE["s"]]:
            errors.append(f"el puente no sale de la costa sur de la isla en {coast}: {old7.get(coast)}")
        if grass not in old7 or not bl.walkable(old7[grass]) or old7[grass][0] != GRASS:
            errors.append(f"sobre el puente no hay pasto caminable de la isla en {grass}: {old7.get(grass)}")
        elif grass not in reach(walk | {grass}, arrival, CARD):
            errors.append(f"el puente no une la isla ({grass}) con la llegada")
    # la costa de la isla junto al puente sigue bien con la madera como tierra
    water_after = {c for c, it in old7.items() if it[0] == WATER and c not in tiles} | sea
    for c in grow({(x, BRIDGE_Y0 - 1) for x in BRIDGE_X}, 1):
        if c in tiles or c not in old7 or old7[c][0] == WATER:
            continue
        want = pieces_for(neighbors_in(water_after, *c), COAST_SIDE, COAST_CORNER, COAST_INNER)
        have = sorted(i for i in old7[c][1:] if i in COAST_PIECES)
        if want is None or sorted(want) != have:
            errors.append(f"costa de la isla {c}: con el puente quiere {want}, tiene {have}")
    if info["end"] not in d:
        errors.append(f"el patio del final {info['end']} no se alcanza")
    # ataúdes de varias piezas: cada cabecera tiene su pie, no hay pies sueltos
    PAIRS = {COFFIN_HEAD: (COFFIN_FOOT, 0, 1), BURIED_HEAD: (BURIED_FOOT, 0, 1)}
    for c, it in tiles.items():
        ids = set(it)
        for head, (foot, dx, dy) in PAIRS.items():
            if head in ids and foot not in tiles.get((c[0] + dx, c[1] + dy), []):
                errors.append(f"ataúd incompleto: {head} en {c[0]},{c[1]} sin {foot} abajo")
        for head, (foot, dx, dy) in PAIRS.items():
            if foot in ids and head not in tiles.get((c[0] - dx, c[1] - dy), []):
                errors.append(f"ataúd incompleto: pie {foot} suelto en {c[0]},{c[1]}")
    for (x, y) in walk:                                         # que no se vea el vacío
        if any((x + dx, y + dy) not in old7 and (x + dx, y + dy) not in tiles
               for dx in range(-VIEW[0], VIEW[0] + 1) for dy in range(-VIEW[1], VIEW[1] + 1)):
            errors.append(f"desde {x},{y} se ve el vacío")
            break
    # el camino va en orden: cada tramo más lejos que el anterior
    order = [min((d[c] for c in grow({p}, 2) if c in d), default=-1) for p in PATH]
    if order != sorted(order):
        errors.append(f"los tramos no quedan en orden de recorrido: {order}")

    # --- spawns por etapas ---
    rng = random.Random(a.seed + 5)
    avoid = grow(bridge | {arrival}, STAIR_CLEAR) | grow({info["sign"]}, 1)
    pool = {c for c in set(d) & land if tiles[c][0] in (DIRT, GRASS) or tiles[c][0] in DIRT_PIECES} - avoid
    slices = slices_by(pool, lambda c: d[c], len(STAGES))
    spawns = place_stages(STAGES, slices, pool, avoid, rng)
    counts = {}
    for _c, mons in spawns:
        for name, _p, _t in mons:
            counts[name] = counts.get(name, 0) + 1
    monsters = sum(counts.values())
    walk_land = len(walk - bridge)
    print(f"camino: {len(land)} casillas de tierra ({walk_land} caminables), puente {len(bridge)}, "
          f"recorrido {max(d.values())} pasos; llegada {arrival[0]},{arrival[1]},7; patio {info['end']}")
    print(f"spawns {len(spawns)}, monstruos {monsters} (" + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
          + f"); 1 cada {walk_land / max(1, monsters):.0f} casillas")
    if monsters < 15:
        errors.append(f"muy pocos monstruos ({monsters})")

    if a.preview:
        allt = {(x, y, Z): it for (x, y), it in old7.items()}
        allt.update({(x, y, Z): it for (x, y), it in tiles.items()})
        xs = [x for x, _ in land] + [70]
        ys = [y for _, y in land] + [215]
        w, h, img = Renderer().area(allt, min(xs) - 4, min(ys) - 4, max(xs) + 4, max(ys) + 4, Z)
        a.preview.write_bytes(png_bytes(w, h, bytes(img)))
        print(f"preview: {a.preview}")
    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        return 1
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    # --- mapa: fuera el agua vieja de la zona, adentro el camino ---
    backup = MAP.with_name(MAP.name + ".bak-epsteinroad")
    if not backup.exists():
        shutil.copy2(MAP, backup)
    md = root[2][0]
    written = set(tiles)
    removed = 0
    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        if az != Z:
            continue
        kept = []
        for t in area[2]:
            if t[0] in (T_TILE, T_HOUSETILE) and (ax + t[1][0], ay + t[1][1]) in written:
                if t[0] != T_TILE:
                    raise SystemExit(f"casilla de casa en la zona: {ax + t[1][0]},{ay + t[1][1]}")
                removed += 1
                continue
            kept.append(t)
        area[2] = kept
        if not area[2]:
            md[2].remove(area)
    buckets = {}
    for (x, y), it in tiles.items():
        buckets.setdefault((x & ~0xFF, y & ~0xFF), []).append((x, y, it))
    for (bx, by), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, Z)), []]
        for x, y, it in sorted(lst, key=lambda t: (t[1], t[0])):
            area[2].append(NP.new_tile_node(x, y, bx, by, it))
        md[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    # --- spawns: bloque propio (generate-epstein-hunts.py lo conserva) ---
    with open(SPAWNS, encoding="latin-1", newline="") as f:
        sp = f.read()
    sp = re.sub(r"[ \t]*<!-- BEGIN EPSTEIN_ROAD.*?<!-- END EPSTEIN_ROAD -->\r?\n?", "", sp, flags=re.S)
    block = "\t<!-- BEGIN EPSTEIN_ROAD (scripts/map/generate-epstein-road.py) -->\n" + spawn_xml(spawns) + \
        "\n\t<!-- END EPSTEIN_ROAD -->\n"
    sp = sp.replace("</spawns>", block + "</spawns>")
    with open(SPAWNS, "w", encoding="latin-1", newline="") as f:
        f.write(sp)

    # --- cartel ---
    with open(READABLES, encoding="latin-1", newline="") as f:
        rd = f.read()
    rd = re.sub(r"\t?<!-- BEGIN EPSTEIN_ROAD_SIGNS -->.*?<!-- END EPSTEIN_ROAD_SIGNS -->\r?\n?", "", rd, flags=re.S)
    rd = rd.replace("</readables>", "\t<!-- BEGIN EPSTEIN_ROAD_SIGNS -->\n"
                    f'\t<readable x="{info["sign"][0]}" y="{info["sign"][1]}" z="7" text="{SIGN_TEXT}"/>\n'
                    "\t<!-- END EPSTEIN_ROAD_SIGNS -->\n</readables>")
    with open(READABLES, "w", encoding="latin-1", newline="") as f:
        f.write(rd)

    lx, ly = [x for x, _ in land], [y for _, y in land]
    MANIFEST.write_text(json.dumps({
        "name": "generated-epstein-road", "seed": a.seed, "z": Z,
        "land": {"x1": min(lx), "y1": min(ly), "x2": max(lx), "y2": max(ly)},
        "landTiles": len(land), "walkableTiles": walk_land, "path": PATH,
        "bridge": sorted(bridge), "arrival": list(arrival), "end": list(info["end"]), "sign": list(info["sign"]),
        "spawns": len(spawns), "monsters": dict(sorted(counts.items())),
        "replacedWaterTiles": removed, "written": row_spans(written),
    }) + "\n")
    print(f"OK mapa ({removed} casillas de agua reemplazadas, {len(written) - removed} nuevas)\n"
          f"OK spawns {SPAWNS}\nOK cartel {READABLES}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
