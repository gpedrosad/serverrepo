"""Geometria y decoracion de Mina Enana. Solo cava roca/vacio; sin tocar otras cuevas."""
from collections import Counter
from hole_entrance_style import style_cells
import heapq
import importlib.util
from pathlib import Path
import random

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("mine_cave_helpers", HERE / "generate-imperial-crypt.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
MOUTH = (195, 59)
SHAFT = (197, 58)
DOWN = (290, 80)
BOSS = (334, 134)
PATHS = {9: [(270, 80), (270, 98), (330, 98), (330, 80), DOWN],
         10: [DOWN, (290, 98), (346, 98), (346, 116), (278, 116), (278, 134), BOSS]}
STAGES = {9: ((("Dwarf",), 1, 100, 13), (("Dwarf", "Dwarf Soldier"), 1, 120, 12),
              (("Dwarf Soldier",), 2, 145, 12)),
          10: ((("Dwarf Guard",), 1, 165, 13), (("Dwarf Guard", "Dwarf Geomancer"), 1, 190, 12),
               (("Dwarf Guard", "Dwarf Geomancer"), 2, 220, 12))}
RAILS = {frozenset("ns"): 20360, frozenset("ew"): 20361, frozenset("se"): 20362,
         frozenset("sw"): 20363, frozenset("ne"): 20364, frozenset("nw"): 20365}
DIR = {(0, -1): "n", (0, 1): "s", (1, 0): "e", (-1, 0): "w"}


def line(path):
    out = [path[0]]
    for a, b in zip(path, path[1:]):
        x, y = a
        assert x == b[0] or y == b[1], (a, b)
        dx, dy = (b[0] > x) - (b[0] < x), (b[1] > y) - (b[1] < y)
        while (x, y) != b:
            x, y = x + dx, y + dy
            out.append((x, y))
    return out


def adit(values):
    """Tunel de acceso en bloques 2x2, con su anillo de pared libre de estructuras."""
    start, end = (196, 58), (270, 80)
    def allowed(c):
        x, y = c
        return (178 <= x <= 272 and 40 <= y <= 100 and
                all(values.get((x + dx, y + dy, 9)) in (None, [101])
                    for dx in range(-1, 3) for dy in range(-1, 3)))
    assert allowed(start) and allowed(end), "Inicio o final del acceso ocupado"
    queue, distance, parent = [(0, start)], {start: 0}, {}
    while queue:
        _, p = heapq.heappop(queue)
        if p == end:
            break
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            q = p[0] + dx, p[1] + dy
            cost = distance[p] + 1
            if allowed(q) and cost < distance.get(q, 100000):
                distance[q], parent[q] = cost, p
                heapq.heappush(queue, (cost + (abs(q[0] - end[0]) + abs(q[1] - end[1])) / 2, q))
    assert end in distance, "No hay tunel seguro desde el camino"
    blocks = [end]
    while blocks[-1] != start:
        blocks.append(parent[blocks[-1]])
    blocks.reverse()
    floor = {(x + dx, y + dy) for x, y in blocks for dx in (0, 1) for dy in (0, 1)}
    return floor, line(blocks)


def add_rails(tiles, path, skip):
    assert len(path) == len(set(path)), "Riel que se cruza consigo mismo"
    for i, p in enumerate(path):
        if p in skip:
            continue
        near = path[max(0, i - 1):i] + path[i + 1:i + 2]
        dirs = {DIR[q[0] - p[0], q[1] - p[1]] for q in near}
        sid = RAILS.get(frozenset(dirs))
        if sid is None:
            assert len(dirs) == 1, (p, dirs)
            sid = 20360 if dirs <= {"n", "s"} else 20361
        assert p in tiles, p
        tiles[p].append(sid)


def build(values, otb):
    bl = C.Blocking()
    cells, spawns, report = {}, [], {}
    tunnel, rail_access = adit(values)
    floors = {}
    for z, path in PATHS.items():
        box = {(x, y) for x in range(262, 355) for y in range(70, 143 if z == 10 else 107)}
        band, core = C.ribbon(path, C.rooms_along(path), 210 + z)
        allowed = {p for p in band & box if values.get((*p, z)) in (None, [101])}
        inner = {p for p in allowed if all((p[0] + dx, p[1] + dy) in allowed
                                          for dx in range(-2, 3) for dy in range(-2, 3))}
        floor = C.carve_cave(210 + z, allowed, core & inner, path[0], 600 if z == 9 else 950)
        if z == 9:
            floor |= tunnel
            for cx in (222, 242):
                bay = {(x, y) for x in range(cx, cx + 4) for y in range(78, 82)}
                assert all(values.get((*p, z)) in (None, [101]) for p in C.grow(bay, 1))
                floor |= bay
        floors[z] = floor
        edge = C.grow(floor, 1)
        t = C.cave_tiles(floor, edge, 310 + z)
        # Tierra seca y ensanches de losas junto a las estaciones y la forja.
        for p in floor:
            t[p] = [352 if (p[0] // 3 + p[1] // 3) % 5 else 351]
            if z == 10 and max(abs(p[0] - BOSS[0]), abs(p[1] - BOSS[1])) <= 3:
                t[p] = [431]
        rails = (rail_access[:-1] if z == 9 else []) + line(path)
        rail_set = set(rails)
        keep = rail_set | C.grow({path[0], path[-1]}, 4) | (tunnel if z == 9 else set())
        C.place_props(t, floor, path[0], (1285, 20366, 1483), 0.17, 410 + z, keep)
        if z == 10:
            for dx, dy, sid in ((0, -2, 2555), (-2, -2, 1483), (2, -2, 1483)):
                p = BOSS[0] + dx, BOSS[1] + dy
                if p in floor:
                    t[p].append(sid)
        # Vigas de 2x2 solo en esquinas: su dibujo hacia NO no tapa piso transitable.
        for x, y in sorted(floor):
            if (x, y) not in keep and len(t[x, y]) == 1 and (x + y) % 3 == 0 and all(
                    (x + dx, y + dy) not in floor for dx, dy in ((-1, 0), (0, -1), (-1, -1))):
                t[x, y].append(20367)
        add_rails(t, rails, {path[-1]} if z == 9 else {DOWN})
        for p, ids in t.items():
            if p in floor:
                continue
            want = C.pieces_for(C.neighbors_in(floor, *p), C.WALL_SIDE, C.WALL_CORNER, C.WALL_INNER)
            assert want is not None and len(want) <= 1 and ids[0] == (want[0] if want else 101), (p, want)
            if ids[0] == C.WALL_SIDE["n"] and (p[0] + 3 * p[1]) % 9 == 0:
                ids.append(2059)
            elif ids[0] == C.WALL_SIDE["w"] and (p[0] + p[1]) % 13 == 0:
                ids.append(2061)
            if 356 <= ids[0] <= 367:
                ids[0] += 15
        if z == 9:
            t[SHAFT].append(1386)
            t[DOWN] = [469]
        else:
            t[DOWN].append(1386)
        walk = {p for p in floor if bl.walkable(t[p])}
        distances = C.reach(walk, SHAFT if z == 9 else DOWN, C.NP.CARD)
        assert set(distances) == walk, f"Paso cortado en z{z}"
        avoid = C.grow({SHAFT, DOWN}, 6) | (set() if z == 9 else C.grow({BOSS}, 8))
        spawns.extend(C.place_stages(STAGES[z], C.slices_by(walk - avoid, distances.__getitem__, 3),
                                     walk, avoid, z, random.Random(f"dwarven-mine-{z}")))
        cells.update({(*p, z): ids for p, ids in t.items()})
        for x, y in C.grow(floor, 9):
            p = x, y, z
            if p not in values and p not in cells:
                cells[p] = [101]
        for x, y in C.grow(floor, 1):
            p = x, y, z - 1
            if p not in values and p not in cells:
                cells[p] = [101]
        report[str(z)] = dict(walkable=len(walk), distanceToEnd=distances[path[-1]])
    spawns.append((BOSS, 10, [("Capataz de Hierro", BOSS, 900)]))
    # Antesala z8: dos bajadas, sin monstruos y con ambos retornos libres.
    shaft_floor = {(x, y) for x in range(195, 198) for y in range(58, 61)}
    shaft_tiles = C.cave_tiles(shaft_floor, C.grow(shaft_floor, 1), 250)
    for p in shaft_floor:
        shaft_tiles[p] = [405]
    shaft_tiles[MOUTH].append(1386)
    shaft_tiles[SHAFT] = [469]
    for p, ids in shaft_tiles.items():
        old = values.get((*p, 8))
        if p not in shaft_floor and old not in (None, [101], [598]):
            assert not bl.walkable(old), f"Antesala toca cueva ajena: {p}"
            continue
        if 356 <= ids[0] <= 367:
            ids[0] += 15
        cells[*p, 8] = ids
    # Solo lava desnuda e impasable a la vista del vestibulo se vuelve roca.
    for x, y in C.grow(shaft_floor, 8):
        p = x, y, 8
        if p not in cells and (p not in values or (values[p] == [598] and bl.blocks(598))):
            cells[p] = [101]
    # Exterior discreto: pasto original, sin vias, tablones ni piezas sueltas sobre el camino.
    surface = {(*MOUTH, 7): [469], (195, 60, 7): [4756], (195, 61, 7): [4756],
               (194, 58, 7): [113], (197, 60, 7): [4756],
               (194, 60, 7): [113, 1429]}
    cells.update(surface)
    merged = values | cells
    for p, z in ((MOUTH, 7), (SHAFT, 8), (DOWN, 9)):
        x, y = p
        assert merged[x, y, z] == [469] and 1386 in merged[x, y, z + 1]
        assert bl.walkable(merged[x, y + 1, z]) and bl.walkable(merged[x, y, z + 1])
    positions = [(z, p) for _, z, ms in spawns for _, p, _ in ms]
    assert len(positions) == len(set(positions))
    counts = Counter(n for _, _, ms in spawns for n, _, _ in ms)
    for z in PATHS:
        amount = sum(len(ms) for _, mz, ms in spawns if mz == z)
        density = report[str(z)]["walkable"] / amount
        assert 30 <= density <= 65, f"Densidad fuera de rango en z{z}: {density}"
        report[str(z)]["densityTilesPerMonster"] = round(density, 1)
    report.update(monsters=dict(counts), surface=[list(p) for p in surface], aditSteps=len(rail_access) - 1)
    style_cells(cells, values, otb)
    return cells, spawns, report
