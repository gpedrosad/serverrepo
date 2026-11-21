#!/usr/bin/env python3
"""El Foso Olvidado: reemplaza la vieja Arena PvP por cuevas de caza progresivas.

La arena de z9 (x 114-136, y 27-40) se rehace como sala de entrada natural. Se conserva la
escalera de mano 1386 de (125,30) que sube a las cloacas de la ciudad. Desde el este de la sala
baja una escalera (140,28) a un corredor de z10 y, desde ahí, a tres pisos de laberinto:

  z10  Galerias Humedas   (nivel 20-45)    corredor + laberinto
  z11  Cavernas Profundas (nivel 45-80)    laberinto, Dipthrah en una sala lateral
  z12  El Corazon         (nivel 70-110+)  4 faraones opcionales + Orshabaal

La dificultad sube con la distancia a la entrada en cada piso. Todos los monstruos son
criaturas que hoy no tienen spawn en el mapa (tortugas, quaras 8.60, elementales, golems,
acechadores y los faraones/Orshabaal). El laberinto se genera sobre una grilla de celdas de
2x2 casillas: pasillos de 2 de ancho, paredes de 2, salas de 3x3 celdas y callejones sin salida.

La arena PvP queda retirada: el generador borra sus tiles (marfil, alfombras, palanca 7001,
teleport y pads) y `data/pvparenas.xml` queda vacío. El C++ de pvparena sigue existiendo para
una arena futura, pero ningún tile queda marcado como arena.

Uso:
  python3 scripts/map/generate-forgotten-pit.py --dry-run --preview-dir /tmp/foso
  python3 scripts/map/generate-forgotten-pit.py --replace
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import shutil
import sys
from collections import deque
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "kb"))
import roomkit  # noqa: E402
from mapdata import REPO, load_tiles  # noqa: E402

_spec = importlib.util.spec_from_file_location("north_pass", HERE / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)

WORLD = REPO / "server/YurOTS/ots/data/world"
MAP = WORLD / "test.otbm"
SPAWNS = WORLD / "test-spawn.xml"
MONSTERS = REPO / "server/YurOTS/ots/data/monster/monsters.xml"
MANIFEST = WORLD / "generated-forgotten-pit.json"
PVPARENAS = REPO / "server/YurOTS/ots/data/pvparenas.xml"

Z9, Z10, Z11, Z12 = 9, 10, 11, 12
CARD = NP.CARD
grow = lambda cells, r: {(x + dx, y + dy) for (x, y) in cells for dx in range(-r, r + 1) for dy in range(-r, r + 1)}

# --- piezas ---------------------------------------------------------------------------------------
TELEPORT, SIGN, CAMPFIRE = 1387, 1429, 1423
STAIR_DOWN, STAIRS_UP, LADDER = 432, 1385, 1386
HALL_BOX = (100, 20, 145, 44)              # se borra entero: arena vieja + roca alrededor
HALL_LADDER = (125, 30)                     # sube a las cloacas (no se toca)
HALL_STAIRS = (140, 28)                     # bajada nueva a z10
HALL_LANDING = (140, 29)                    # donde caen los que suben de z10
CITY_SIGN = (128, 33, 7)                    # cartel junto a la trampilla de la ciudad

CORRIDOR_BOX = (130, 0, 199, 32)            # roca/void; no toca la cueva del minotauro (y 33+)
CORRIDOR_START = (140, 28)                  # escalera de subida 1385
CORRIDOR_END = (198, 10)                    # empalma con el túnel del laberinto

MAIN_BOX = (200, 0, 275, 90)                # vacío en z10-z12
MAIN_ORIGIN = (209, 7)                      # casilla NO de la celda (0,0)
MAIN_CW, MAIN_CH = 15, 19                   # celdas lógicas (footprint 58x74)
MAIN_ENTRY_TUNNEL = {(x, y) for x in range(200, 213) for y in (11, 12)}
MAIN_START_CELL = (1, 1)
MIN_PATH_CELLS = 80                         # recorrido mínimo entrada -> salida (celdas)
LOOPS = 0.07                                # conexiones extra: menos callejones ciegos
VIEW = (8, 6)                               # media pantalla del cliente 7.6 + margen
# Techo (nov 2026): z9 estaba vacío encima del corredor y del laberinto de z10. Sin nada justo arriba, el
# cliente dibuja los pisos de arriba (las cuevas de z8 de x 195-280) encima del laberinto: desde 675
# casillas de z10 se veía "lo de arriba". Se pone roca en z9 donde no hay nada, con 2 de margen (el
# cliente mira la casilla de arriba y la de arriba en diagonal, x+1 y+1).
CEILING_MARGIN = 2

STAGE_DEFS = {
    Z10: [
        (("Poison Spider", "Centipede", "Tiger"), 2, 60, 10),
        (("Tortoise", "Thornback Tortoise", "Dworc Voodoomaster"), 2, 75, 10),
        (("Blood Crab", "Cyclops Drone", "Quara Constrictor"), 2, 90, 10),
        (("Cyclops Smith", "Quara Mantassin", "Blue Djinn"), 2, 120, 8),
    ],
    Z11: [
        (("Earth Elemental", "Nightstalker", "Blue Djinn"), 2, 120, 10),
        (("Quara Constrictor", "Quara Mantassin", "Cyclops Smith"), 2, 140, 10),
        (("Quara Pincher", "Worker Golem", "Nightstalker"), 2, 180, 10),
        (("Quara Predator", "Worker Golem", "Quara Pincher"), 2, 220, 8),
    ],
    Z12: [
        (("Worker Golem", "Quara Predator", "Nightstalker"), 2, 240, 12),
        (("Quara Pincher", "Quara Predator", "Worker Golem"), 3, 260, 10),
        (("Nightstalker", "Quara Predator", "Worker Golem"), 3, 300, 8),
    ],
}
BOSS_NAMES = {"Dipthrah", "Mahrdis", "Morguthis", "Vashresamun", "Ashmunrah", "Orshabaal"}


def block(x: int, y: int) -> set:
    return {(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)}


def rect(x0: int, y0: int, x1: int, y1: int) -> set:
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def to_map(tiles: dict, z: int) -> roomkit.Map:
    m = roomkit.Map()
    for (x, y), ids in tiles.items():
        pos = (x, y, z)
        m.ground(pos, ids[0])
        for iid in ids[1:]:
            m.add(pos, iid)
    return m


def walkable_xy(tiles: dict, bl) -> set:
    return {(x, y) for (x, y), ids in tiles.items() if bl.walkable(ids)}


def reachable(walk: set, start) -> set:
    seen = {start}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in CARD:
            n = (x + dx, y + dy)
            if n in walk and n not in seen:
                seen.add(n)
                q.append(n)
    return seen


# --- celdas 2x2 / laberinto -----------------------------------------------------------------------
def cell_xy(cell) -> tuple[int, int]:
    return (MAIN_ORIGIN[0] + 4 * cell[0], MAIN_ORIGIN[1] + 4 * cell[1])


def cell_tiles(cell) -> set:
    x, y = cell_xy(cell)
    return block(x, y)


def cell_center(cell) -> tuple[int, int]:
    x, y = cell_xy(cell)
    return (x + 1, y + 1)


def h_conn(cell) -> set:
    x, y = cell_xy(cell)
    return block(x + 2, y)


def v_conn(cell) -> set:
    x, y = cell_xy(cell)
    return block(x, y + 2)


def neighbors(cell, cw: int, ch: int):
    x, y = cell
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = (x + dx, y + dy)
        if 0 <= n[0] < cw and 0 <= n[1] < ch:
            yield n


def maze_graph(cw: int, ch: int, seed: int, start, loops: float):
    rng = random.Random(seed)
    links: set = set()
    seen = {start}
    stack = [start]
    while stack:
        cell = stack[-1]
        nbrs = [n for n in neighbors(cell, cw, ch) if n not in seen]
        if not nbrs:
            stack.pop()
            continue
        n = rng.choice(nbrs)
        links.add(frozenset((cell, n)))
        seen.add(n)
        stack.append(n)
    if len(seen) != cw * ch:
        raise RuntimeError(f"laberinto incompleto: {len(seen)}/{cw * ch}")
    for x in range(cw):
        for y in range(ch):
            c = (x, y)
            for n in ((x + 1, y), (x, y + 1)):
                if n[0] < cw and n[1] < ch and frozenset((c, n)) not in links and rng.random() < loops:
                    links.add(frozenset((c, n)))
    return links


def cell_distances(links: set, start, cw: int, ch: int) -> dict:
    adj: dict = {}
    for e in links:
        a, b = tuple(e)
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    dist = {start: 0}
    q = deque([start])
    while q:
        c = q.popleft()
        for n in adj.get(c, ()):
            if n not in dist:
                dist[n] = dist[c] + 1
                q.append(n)
    return dist


def open_room(links: set, cell, w: int, h: int):
    cx, cy = cell
    x0, y0 = cx - w // 2, cy - h // 2
    for x in range(x0, x0 + w):
        for y in range(y0, y0 + h):
            if x + 1 < x0 + w:
                links.add(frozenset(((x, y), (x + 1, y))))
            if y + 1 < y0 + h:
                links.add(frozenset(((x, y), (x, y + 1))))
    return (x0, y0, w, h)


def room_tiles(cell, w: int, h: int) -> set:
    cx, cy = cell
    x0, y0 = cx - w // 2, cy - h // 2
    out = set()
    for x in range(x0, x0 + w):
        for y in range(y0, y0 + h):
            out |= cell_tiles((x, y))
            if x + 1 < x0 + w:
                out |= h_conn((x, y))
            if y + 1 < y0 + h:
                out |= v_conn((x, y))
    return out


def floor_from_links(links: set, cw: int, ch: int) -> set:
    floor = set()
    for x in range(cw):
        for y in range(ch):
            floor |= cell_tiles((x, y))
    for e in links:
        a, b = sorted(tuple(e))
        if b[0] > a[0]:
            floor |= h_conn(a)
        elif b[1] > a[1]:
            floor |= v_conn(a)
    return floor


def degree_map(links: set) -> dict:
    deg: dict = {}
    for e in links:
        for c in e:
            deg[c] = deg.get(c, 0) + 1
    return deg


def pick_side_rooms(links: set, start_cell, exit_cell, count: int) -> list:
    deg = degree_map(links)
    dist = cell_distances(links, start_cell, MAIN_CW, MAIN_CH)
    cands = [c for c in dist if deg.get(c, 0) <= 1 and dist[c] > 35
             and c != start_cell and c != exit_cell
             and 1 <= c[0] <= MAIN_CW - 2 and 1 <= c[1] <= MAIN_CH - 2]
    chosen = []
    for _ in range(count):
        if not cands:
            cands = [c for c in dist if c != start_cell and c != exit_cell
                     and dist.get(c, 0) > 30 and c not in chosen
                     and 1 <= c[0] <= MAIN_CW - 2 and 1 <= c[1] <= MAIN_CH - 2]
        if not cands:
            break
        ref = [start_cell, exit_cell] + chosen
        best = max(cands, key=lambda c: min(max(abs(c[0] - r[0]), abs(c[1] - r[1])) for r in ref))
        chosen.append(best)
        cands = [c for c in cands if max(abs(c[0] - best[0]), abs(c[1] - best[1])) >= 3]
    return chosen


# --- pisos ----------------------------------------------------------------------------------------
def build_hall(seed: int, bl):
    floor = set()
    remove = {(110, 26), (136, 26), (110, 40), (136, 40), (122, 32), (130, 36)}
    for bx in range(110, 138, 2):
        for by in range(26, 42, 2):
            if (bx, by) not in remove:
                floor |= block(bx, by)
    for bx, by in ((138, 26), (140, 26), (138, 28), (140, 28)):
        floor |= block(bx, by)
    assert HALL_LADDER in floor and HALL_STAIRS in floor and HALL_LANDING in floor
    t = NP.cave_tiles(floor, rect(*HALL_BOX), seed)
    spots = {HALL_LADDER, HALL_STAIRS, HALL_LANDING, (114, 39), (122, 39)}
    keep = grow(spots, 2)
    NP.decorate_cave(t, floor, HALL_LADDER, keep, seed, 0.03, bl)
    t[HALL_LADDER].append(LADDER)
    t[HALL_STAIRS] = [STAIR_DOWN]
    t[(114, 39)].append(CAMPFIRE)
    t[(122, 39)].append(SIGN)
    return t, floor


def corridor_path():
    waypoints = [(140, 28), (144, 28), (144, 24), (150, 24), (150, 18), (158, 18), (158, 12),
                 (166, 12), (166, 8), (176, 8), (176, 12), (186, 12), (186, 10), (198, 10)]
    floor = set()
    for a, b in zip(waypoints, waypoints[1:]):
        if a[0] == b[0]:
            for y in range(min(a[1], b[1]), max(a[1], b[1]) + 1, 2):
                floor |= block(a[0], y)
        else:
            for x in range(min(a[0], b[0]), max(a[0], b[0]) + 1, 2):
                floor |= block(x, a[1])
    for bx, by in ((140, 26), (142, 26), (142, 28), (196, 8), (198, 8), (196, 10), (196, 12), (198, 12)):
        floor |= block(bx, by)
    assert CORRIDOR_START in floor and CORRIDOR_END in floor
    return floor


def build_corridor(seed: int, bl):
    floor = corridor_path()
    t = NP.cave_tiles(floor, rect(*CORRIDOR_BOX), seed, mud_bias=0.02)
    spots = {CORRIDOR_START, CORRIDOR_END, (142, 26), (143, 26), (197, 9)}
    NP.decorate_cave(t, floor, CORRIDOR_START, grow(spots, 2), seed, 0.04, bl)
    t[CORRIDOR_START].append(STAIRS_UP)
    t[(142, 26)].append(CAMPFIRE)
    t[(143, 26)].append(SIGN)
    t[(197, 9)].append(CAMPFIRE)
    return t, floor


def ceiling_tiles(existing) -> roomkit.Map:
    """Roca en z9 sobre el corredor y el laberinto, solo en casillas sin tile (no pisa otras zonas)."""
    m = roomkit.Map()
    for x0, y0, x1, y1 in (CORRIDOR_BOX, MAIN_BOX):
        for x in range(x0 - CEILING_MARGIN, x1 + CEILING_MARGIN + 1):
            for y in range(max(0, y0 - CEILING_MARGIN), y1 + CEILING_MARGIN + 1):
                if (x, y, Z9) not in existing:
                    m.ground((x, y, Z9), NP.ROCK)
    return m


def build_city_sign() -> roomkit.Map:
    m = roomkit.Map()
    m.ground(CITY_SIGN, 431)
    m.add(CITY_SIGN, SIGN)
    return m


def build_main(seed: int, z: int, start_cell, bl, side_count: int, final: bool):
    """Un piso de laberinto. Devuelve tiles, floor, start, exit, salas laterales y portal."""
    for attempt in range(60):
        links = maze_graph(MAIN_CW, MAIN_CH, seed + attempt * 17, start_cell, LOOPS)
        dist = cell_distances(links, start_cell, MAIN_CW, MAIN_CH)
        # Lejos en el laberinto Y lejos en el mapa: si no, la salida puede quedar al lado
        # de la entrada aunque el camino sea largo (el laberinto da muchas vueltas).
        cands = [c for c in dist if 1 <= c[0] <= MAIN_CW - 2 and 1 <= c[1] <= MAIN_CH - 2]
        good = [c for c in cands if dist[c] >= MIN_PATH_CELLS]
        if good:
            far = max(good, key=lambda c: (abs(c[0] - start_cell[0]) + abs(c[1] - start_cell[1]), dist[c], c))
            break
    else:
        raise RuntimeError("no se encontró un laberinto suficientemente largo")

    open_room(links, start_cell, 3, 3)
    open_room(links, far, 3, 3)
    sides = pick_side_rooms(links, start_cell, far, side_count)
    for c in sides:
        open_room(links, c, 3, 3)

    floor = floor_from_links(links, MAIN_CW, MAIN_CH)
    if z == Z10:
        floor |= MAIN_ENTRY_TUNNEL
    t = NP.cave_tiles(floor, rect(*MAIN_BOX), seed + z, mud_bias={Z10: 0.02, Z11: 0.08, Z12: 0.14}[z])

    sx, sy = cell_center(start_cell)
    stair = cell_center(far)
    portal = None
    final_sign = None
    keep = {(sx, sy), stair, (sx + 2, sy + 2), (sx + 2, sy + 3)}
    if final:
        x0, y0 = cell_xy((far[0] - 1, far[1] - 1))
        portal = (x0 + 8, y0 + 8)
        final_sign = (x0 + 1, y0 + 8)
        keep |= {portal, final_sign}
    for c in sides:
        keep.add(cell_center(c))
    NP.decorate_cave(t, floor, cell_center(start_cell), grow(keep, 2), seed + z,
                     0.04 + 0.02 * (z - Z10), bl)

    if z != Z10:
        t[cell_center(start_cell)].append(STAIRS_UP)
    if final:
        t[portal].append(TELEPORT)
        t[final_sign].append(SIGN)
    else:
        t[stair] = [STAIR_DOWN]
    t[(sx + 2, sy + 2)].append(CAMPFIRE)
    t[(sx + 2, sy + 3)].append(SIGN)
    return t, floor, start_cell, far, sides, portal, final_sign


# --- spawns ---------------------------------------------------------------------------------------
def place_stages(stages, walk: set, order: dict, avoid: set, z: int, rng, gap: int):
    cells = sorted(walk, key=lambda c: (order.get(c, 0), c))
    size = max(1, len(cells) / len(stages))
    out = []
    for k, (names, per, st, cap) in enumerate(stages):
        pool = [c for c in cells[int(k * size):int((k + 1) * size)] if c not in avoid]
        rng.shuffle(pool)
        centers = []
        n = 0
        for c in pool:
            if len(centers) >= cap:
                break
            if any(max(abs(c[0] - o[0]), abs(c[1] - o[1])) < gap for o in centers):
                continue
            spots = [(c[0] + dx, c[1] + dy) for dx in range(-2, 3) for dy in range(-2, 3)
                     if (c[0] + dx, c[1] + dy) in walk and (c[0] + dx, c[1] + dy) not in avoid]
            if len(spots) < per + 3:
                continue
            rng.shuffle(spots)
            centers.append(c)
            out.append((c, z, [(names[(n + j) % len(names)], s, st) for j, s in enumerate(spots[:per])], 3))
            n += per
    return out


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons, radius in spawns:
        lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="{z}" radius="{radius}">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


# --- validación -----------------------------------------------------------------------------------
def validate(existing, hall_tiles, corridor_tiles, floors, spawns, regenerating=False) -> list:
    errs = []
    bl = NP.Blocking()

    # Zonas que se pueden reescribir: z9 (arena), z10 corredor (roca) y z10-z12 laberinto (vacío).
    # Si ya existe el manifiesto, se asume una regeneración y esas cajas son nuestras.
    if not regenerating:
        for (x, y, z), ids in existing.items():
            if z == Z10 and CORRIDOR_BOX[0] <= x <= CORRIDOR_BOX[2] and CORRIDOR_BOX[1] <= y <= CORRIDOR_BOX[3]:
                if bl.walkable(ids):
                    errs.append(f"z10 corredor: {x},{y} ya es caminable ({ids})")
            if z in (Z10, Z11, Z12) and MAIN_BOX[0] <= x <= MAIN_BOX[2] and MAIN_BOX[1] <= y <= MAIN_BOX[3]:
                errs.append(f"z{z} laberinto: {x},{y} ya existe ({ids})")

    # La arena vieja no debe sobrevivir (salvo la escalera de mano 1386).
    for (x, y), ids in hall_tiles.items():
        for iid in ids[1:]:
            if iid in (1945, 1387, 1900, 1901, 1902, 1903, 1904, 1905, 1546, 1547):
                errs.append(f"hall: quedó item de arena {iid} en {x},{y}")
    if LADDER not in hall_tiles.get(HALL_LADDER, []):
        errs.append("hall: falta la escalera de mano 1386 en 125,30")
    landing = hall_tiles.get((128, 31))
    if not landing or not bl.walkable(landing):
        errs.append("hall: la llegada del portal final 128,31,9 no es caminable")
    hm = to_map(hall_tiles, Z9)
    hchk = roomkit.Checker(hm)
    hwalk = {(p[0], p[1]) for p in hm.t if hchk.walkable(p)}
    hreach = reachable(hwalk, HALL_LADDER)
    for p in (HALL_STAIRS, HALL_LANDING, (114, 39)):
        if p not in hreach:
            errs.append(f"hall: {p} no se alcanza desde la escalera de mano")
    if not any((122 + dx, 39 + dy) in hreach for dx, dy in CARD):
        errs.append("hall: no se puede leer el cartel de 122,39")

    # Corredor + laberinto z10.
    z10 = floors[Z10]
    z10walk = walkable_xy(corridor_tiles, bl) | walkable_xy(z10[0], bl)
    z10order = NP.reach(z10walk, CORRIDOR_START, CARD)
    if cell_center(z10[3]) not in z10order:
        errs.append(f"z10: la salida {cell_center(z10[3])} no se alcanza desde el corredor")

    for z, fl in floors.items():
        t, floor, start, far, sides, portal, final_sign = fl
        walk = walkable_xy(t, bl)
        if z == Z10:
            walk = z10walk
        st = cell_center(start)
        if st not in walk:
            errs.append(f"z{z}: la llegada {st} no es caminable")
            continue
        seen = reachable(walk, st)
        ex = cell_center(far)
        if ex not in seen:
            errs.append(f"z{z}: la salida {ex} no se alcanza")
        for c in sides:
            if cell_center(c) not in seen:
                errs.append(f"z{z}: la sala lateral {c} no se alcanza")
        if portal and portal not in seen:
            errs.append(f"z{z}: el portal {portal} no se alcanza")
        if len(seen) < len(walk) * 0.85:
            errs.append(f"z{z}: {len(walk) - len(seen)} casillas caminables aisladas")
        for (x, y) in walk:
            left = CORRIDOR_BOX[0] if (z == Z10 and y <= CORRIDOR_BOX[3]) else MAIN_BOX[0]
            if x - VIEW[0] < left or x + VIEW[0] > MAIN_BOX[2] or y - VIEW[1] < MAIN_BOX[1] or y + VIEW[1] > MAIN_BOX[3]:
                errs.append(f"z{z}: {x},{y} ve el borde negro")
                break
        special = {st, ex} | ({portal} if portal else set()) | {cell_center(c) for c in sides}
        for (cx, cy), zz, mons, _radius in spawns:
            if zz != z:
                continue
            if (cx, cy) not in walk:
                errs.append(f"z{z}: spawn {cx},{cy} no es caminable")
            for name, (mx, my), _st in mons:
                if (mx, my) not in walk:
                    errs.append(f"z{z}: monstruo {name} en {mx},{my} no es caminable")
                if (mx, my) in special and name not in BOSS_NAMES:
                    errs.append(f"z{z}: spawn {name} sobre llegada/salida")

    known = set(re.findall(r'<monster name="([^"]+)"', MONSTERS.read_text(encoding="latin-1")))
    for _c, _z, mons, _r in spawns:
        for name, _p, _t in mons:
            if name not in known:
                errs.append(f"monstruo inexistente: {name}")

    if not (existing.get((125, 30, 8)) and 428 in existing[(125, 30, 8)]):
        errs.append("acceso: falta la trampilla 428 en 125,30,8")
    if not (existing.get((127, 32, 7)) and 428 in existing[(127, 32, 7)]):
        errs.append("acceso: falta la trampilla 428 en 127,32,7")
    old_sign = existing.get(CITY_SIGN)
    if old_sign not in (None, [431], [431, SIGN]):
        errs.append(f"cartel de ciudad: {CITY_SIGN} no es piso de piedra común ({old_sign})")
    return errs


# --- main -----------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=1976)
    ap.add_argument("--map", type=Path, default=MAP)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview-dir", type=Path)
    ap.add_argument("--replace", action="store_true", help="escribe mapa, spawns y carteles")
    a = ap.parse_args()

    import mapdata
    mapdata.MAP = a.map
    existing = load_tiles()
    bl = NP.Blocking()
    rng = random.Random(a.seed + 99)

    hall_tiles, hall_floor = build_hall(a.seed, bl)
    corridor_tiles, corridor_floor = build_corridor(a.seed + 1, bl)
    floors = {}
    for z, seed in ((Z10, a.seed + 10), (Z11, a.seed + 20), (Z12, a.seed + 30)):
        start = MAIN_START_CELL if z == Z10 else floors[z - 1][3]
        side_count = 1 if z == Z11 else (4 if z == Z12 else 0)
        floors[z] = build_main(seed, z, start, bl, side_count, z == Z12)
        fl = floors[z]
        print(f"z{z}: {len(fl[1])} casillas de piso, entrada {cell_center(fl[2])}, "
              f"salida {cell_center(fl[3])}, laterales {[cell_center(c) for c in fl[4]]}")

    # Spawns normales por distancia a la entrada.
    corridor_walk = walkable_xy(corridor_tiles, bl)
    z10walk = corridor_walk | walkable_xy(floors[Z10][0], bl)
    z10spawn = {p for p in z10walk if
                (p in corridor_tiles and len(corridor_tiles[p]) == 1) or
                (p in floors[Z10][0] and len(floors[Z10][0][p]) == 1)}
    z10order = NP.reach(z10walk, CORRIDOR_START, CARD)
    f10 = floors[Z10]
    avoid10 = grow({CORRIDOR_START, cell_center(f10[2]), cell_center(f10[3])}, 3)
    avoid10 |= grow(room_tiles(f10[2], 3, 3) | room_tiles(f10[3], 3, 3), 2)
    spawns = place_stages(STAGE_DEFS[Z10], z10spawn, z10order, avoid10, Z10, rng, 7)
    paths = {Z10: z10order.get(cell_center(f10[3]))}

    for z in (Z11, Z12):
        t, floor, start, far, sides, portal, final_sign = floors[z]
        walk_all = walkable_xy(t, bl)
        walk_spawn = {p for p in walk_all if len(t[p]) == 1}
        order = NP.reach(walk_all, cell_center(start), CARD)
        paths[z] = order.get(cell_center(far))
        special = {cell_center(start), cell_center(far)} | {cell_center(c) for c in sides}
        if portal:
            special.add(portal)
        avoid = grow(special, 3) | grow(room_tiles(start, 3, 3) | room_tiles(far, 3, 3), 2)
        for c in sides:
            avoid |= grow(room_tiles(c, 3, 3), 2)
        spawns += place_stages(STAGE_DEFS[z], walk_spawn, order, avoid, z, rng, 7)

    # Jefes: uno en z11 y cuatro faraones + Orshabaal en z12.
    bosses = [(Z11, floors[Z11][4][0], "Dipthrah", 3600)]
    for cell, name in zip(floors[Z12][4], ("Mahrdis", "Morguthis", "Vashresamun", "Ashmunrah")):
        bosses.append((Z12, cell, name, 7200))
    bosses.append((Z12, floors[Z12][3], "Orshabaal", 14400))
    for z, cell, name, st in bosses:
        pos = cell_center(cell)
        spawns.append((pos, z, [(name, pos, st)], 1))

    regenerating = MANIFEST.exists()
    errs = validate(existing, hall_tiles, corridor_tiles, floors, spawns, regenerating=regenerating)
    counts: dict = {}
    for _c, z, mons, _r in spawns:
        for name, _p, _t in mons:
            counts.setdefault(z, {}).setdefault(name, 0)
            counts[z][name] += 1
    print(f"hall: {len(hall_floor)} casillas; escalera de mano {HALL_LADDER}, bajada {HALL_STAIRS}")
    print(f"corredor z10: {len(corridor_floor)} casillas; {CORRIDOR_START} -> {CORRIDOR_END}")
    for z in (Z10, Z11, Z12):
        print(f"  z{z} recorrido entrada->salida: {paths.get(z)} pasos; spawns:",
              ", ".join(f"{k} {v}" for k, v in sorted(counts.get(z, {}).items())))
    print("jefes:", ", ".join(f"{n} {cell_center(c)} z{z}" for z, c, n, _s in bosses))

    if a.preview_dir:
        a.preview_dir.mkdir(parents=True, exist_ok=True)
        for z, (t, floor, start, far, sides, portal, final_sign) in floors.items():
            roomkit.render_png(to_map(t, z), a.preview_dir / f"z{z}.png", z)
        roomkit.render_png(to_map(hall_tiles, Z9), a.preview_dir / "z9_hall.png", Z9)
        roomkit.render_png(to_map(corridor_tiles, Z10), a.preview_dir / "z10_corridor.png", Z10)
        print(f"PNG en {a.preview_dir}")

    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs[:40]), file=sys.stderr)
        return 1
    if a.dry_run or not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    # Backup fuera del repo.
    backup = Path("/private/var/folders/c8/k2dtzwbx3ml4l81234tng6vc0000gn/T/opencode") / \
        f"forgotten-pit-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a.map, backup / "test.otbm")
    shutil.copy2(SPAWNS, backup / "test-spawn.xml")
    print(f"backup: {backup}")

    stackable = roomkit.Checker(to_map(floors[Z10][0], Z10)).stackable
    roomkit.write_map(a.map, to_map(hall_tiles, Z9), HALL_BOX, Z9, stackable)
    roomkit.write_map(a.map, to_map(corridor_tiles, Z10), CORRIDOR_BOX, Z10, stackable)
    roomkit.write_map(a.map, build_city_sign(),
                      (CITY_SIGN[0], CITY_SIGN[1], CITY_SIGN[0], CITY_SIGN[1]), CITY_SIGN[2], stackable)
    for z in (Z10, Z11, Z12):
        t, floor, start, far, sides, portal, final_sign = floors[z]
        m = to_map(t, z)
        for tile in m.t.values():
            for item in tile["items"]:
                if item["id"] == TELEPORT and "tele" not in item:
                    item["tele"] = (128, 31, Z9)
        roomkit.write_map(a.map, m, MAIN_BOX, z, stackable)
    ceiling = ceiling_tiles(existing)
    if ceiling.t:   # caja vacía (1, 1, 0, 0): no borra nada, solo agrega roca donde no había tile
        roomkit.write_map(a.map, ceiling, (1, 1, 0, 0), Z9, stackable)
    print(f"techo z9: {len(ceiling.t)} casillas de roca nuevas")

    # Spawns
    sp = SPAWNS.read_text(encoding="latin-1")
    sp = re.sub(r"[ \t]*<!-- BEGIN FORGOTTEN_PIT_SPAWNS.*?<!-- END FORGOTTEN_PIT_SPAWNS -->\n?", "", sp, flags=re.S)
    block = "\t<!-- BEGIN FORGOTTEN_PIT_SPAWNS (scripts/map/generate-forgotten-pit.py) -->\n" + \
        spawn_xml(spawns) + "\n\t<!-- END FORGOTTEN_PIT_SPAWNS -->\n"
    SPAWNS.write_text(sp.replace("</spawns>", block + "</spawns>"), encoding="latin-1")

    # Carteles
    signs = [
        dict(x=CITY_SIGN[0], y=CITY_SIGN[1], z=CITY_SIGN[2],
             text="THE FORGOTTEN PIT\nCave entrance (level 20+).\nEnter through the trapdoor."),
        dict(x=122, y=39, z=Z9, text='THE FORGOTTEN PIT\nA former PvP arena, now hunting caves.\nLevel 20+: take the eastern stairs down.\n3 floors. Return portal at the end.\nExit to the city: northern ladder.'),
        dict(x=143, y=26, z=Z10, text="DAMP GALLERIES\nLevel 20-45.\nBelow: Deep Caverns."),
        dict(x=cell_center(floors[Z11][2])[0] + 2, y=cell_center(floors[Z11][2])[1] + 3, z=Z11,
             text="DEEP CAVERNS\nLevel 45-80.\nBeware of Quaras and Golems.\nBelow: the Heart."),
        dict(x=cell_center(floors[Z12][2])[0] + 2, y=cell_center(floors[Z12][2])[1] + 3, z=Z12,
             text="THE HEART\nLevel 70+. Pharaoh guardians.\nIn the depths: Orshabaal (level 100+)."),
    ]
    if floors[Z12][6]:
        signs.append(dict(x=floors[Z12][6][0], y=floors[Z12][6][1], z=Z12,
                          text="ORSHABAAL\nLevel 100+ boss.\nBring a group. Return portal at the far end."))
    roomkit.patch_readables("<!-- BEGIN FORGOTTEN_PIT_SIGNS -->", "<!-- END FORGOTTEN_PIT_SIGNS -->", signs)

    # pvparenas.xml vacío: la arena PvP queda retirada.
    PVPARENAS.write_text('<?xml version="1.0"?>\n<pvparenas/>\n', encoding="utf-8")

    MANIFEST.write_text(json.dumps({
        "name": "El Foso Olvidado", "seed": a.seed,
        "hall": {"box": HALL_BOX, "ladder": [*HALL_LADDER, Z9], "stairs": [*HALL_STAIRS, Z9]},
        "citySign": [*CITY_SIGN],
        "floors": {f"z{z}": {"box": MAIN_BOX, "start": [*cell_center(fl[2]), z],
                             "exit": [*cell_center(fl[3]), z],
                             "portal": ([*fl[5], z] if fl[5] else None),
                             "sides": [[*cell_center(c), z] for c in fl[4]],
                             "floorTiles": len(fl[1])} for z, fl in floors.items()},
        "corridor": {"box": CORRIDOR_BOX, "start": [*CORRIDOR_START, Z10], "end": [*CORRIDOR_END, Z10]},
        "bosses": [{"name": n, "pos": [*cell_center(c), z], "respawn": s} for z, c, n, s in bosses],
        "spawns": len(spawns), "monsters": {f"z{z}": c for z, c in sorted(counts.items())},
    }, indent=2) + "\n")
    print(f"OK {a.map}, test-spawn.xml, readables.xml, pvparenas.xml y {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
