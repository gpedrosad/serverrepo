#!/usr/bin/env python3
"""Cuevas de Bambú: bajada desde el claro de Bamboo Camp a una cueva de tres cámaras de dificultad creciente.

  z7  claro de Bamboo Camp: boca natural 469 en 172,99.
  z8  pozo: cámara chica de cueva (172,97-101) sobre un islote de roca en el lago de lava de los behemoths,
      con escalera de mano 1386 en 172,99 (se llega a su ancla) y la bajada 432 en 172,101.
  z9  cueva natural (carve_cave + ribbon, como las zonas de caza): cámara 1 junto a la llegada (172,102),
      cámara 2 al este y cámara 3 (jefe) al fondo. Mismos 17 monstruos que la v1.

v2 (19 nov 2026). La v1 eran rectángulos: el pozo, un cuadrado de paredes metido en la lava, y la cueva,
tres salas rectangulares desde donde se veía el vacío negro (norte y este) y la lava (sur y oeste). Ahora la
cueva es natural, todo lo que se ve desde su piso tiene tile (el vacío pasa a roca) y la lava a la vista desde
z9 pasa a roca. La lava de z8 alrededor del pozo NO se toca: es el hunt de los behemoths y fire elementals; el
pozo queda como un islote de roca adentro.

Uso:
  python3.11 scripts/map/generate-bamboo-depths.py --dry-run --preview /tmp/cuevas-bambu
  python3.11 scripts/map/generate-bamboo-depths.py
Re-ejecutable: reescribe sus cajas de z8/z9, la roca de afuera a la vista y el bloque BAMBOO_DEPTHS_SPAWNS.
Doc: docs/items-and-map/MAPEAR_CUEVAS_BAMBU.md.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "kb"))
import roomkit  # noqa: E402
from mapdata import REPO, load_tiles  # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


NP = _load("generate-north-pass")
BV = _load("generate-beast-valley")
pieces_for, neighbors_in, reach, CARD = NP.pieces_for, NP.neighbors_in, NP.reach, NP.CARD
CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD = NP.CAVE_FLOOR, NP.CAVE_FLOOR_ALT, NP.CAVE_MUD
CAVE_FLOORS = {CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD}
WALL_SIDE, WALL_CORNER, WALL_INNER = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER
WALLS = set(WALL_SIDE.values()) | set(WALL_CORNER.values()) | set(WALL_INNER.values())
ROCK = NP.ROCK
STAIR_DOWN, STAIRS_UP = NP.STAIR_DOWN, NP.STAIRS_UP
ENTRANCE_HOLE, SHAFT_LADDER = 469, 1386
SHAFT_LIGHTS = {(172, 96): 2059, (175, 99): 2061}
LAVA = {598, 599, 600, 601}

WORLD = REPO / "server/YurOTS/ots/data/world"
MAP = WORLD / "test.otbm"
SPAWNS = WORLD / "test-spawn.xml"
MANIFEST = WORLD / "generated-bamboo-depths.json"

Z7, Z8, Z9 = 7, 8, 9
ENTRANCE = (172, 99)             # bajada en z7
SHAFT_UP = (172, 99)             # escalera de subida en z8 (misma x,y)
SHAFT_LAND = (172, 99)           # la escalera de mano no desplaza la bajada desde z7
SHAFT_DOWN = (172, 101)          # bajada de z8 a z9
DEPTHS_UP = (172, 101)           # escalera de subida en z9 (misma x,y)
DEPTHS_LAND = (172, 102)         # llegada real desde z8
CAMP_FIRE = 1423                 # fogata: no bloquea a los jugadores (block_pathfind)

# z8: el pozo. Cámara chica y un islote de roca (elipse) en la lava; la sala de troles de z8 empieza en y103.
FLOOR8 = {(x, y) for x in (171, 172, 173) for y in (98, 99, 100, 101)} | {(170, 99), (170, 100), (174, 99),
                                                                          (174, 100), (172, 97)}
ISLAND8 = ((172.0, 98.6), 4.6, 3.9)
BOX8 = (166, 93, 178, 102)

# z9: cueva natural
BOX9 = (166, 80, 213, 106)
ALLOWED9 = (169, 84, 210, 104)
PATH9 = [(172, 101), (172, 96), (189, 96), (189, 89), (204, 89)]
CHAMBERS = {                      # centro, radio de la sala del ribbon
    "camara1": ((176, 96), 3),
    "camara2": ((189, 93), 3),
    "camara3": ((203, 89), 4),
}
MIN_FLOOR9 = 300
VIEW = (9, 7)
SEED = 42

# (cámara, [(nombre, spawntime), ...]) por grupo; los grupos de una cámara van separados
GROUPS = [
    ("camara1", [("Dworc Venomsniper", 175), ("Dworc Venomsniper", 175)]),
    ("camara1", [("Dworc Fleshhunter", 175), ("Dworc Fleshhunter", 175)]),
    ("camara1", [("Orc Warrior", 175), ("Orc Warrior", 175)]),
    ("camara2", [("Kongra", 175), ("Kongra", 175)]),
    ("camara2", [("Sibang", 175), ("Sibang", 175)]),
    ("camara2", [("Orc Berserker", 175), ("Orc Berserker", 175)]),
    ("camara3", [("Orc Warlord", 900)]),
    ("camara3", [("Orc Leader", 600)]),
    ("camara3", [("Orc Shaman", 300)]),
    ("camara3", [("Orc Berserker", 175), ("Orc Berserker", 175)]),
]


def rect(b):
    return {(x, y) for x in range(b[0], b[2] + 1) for y in range(b[1], b[3] + 1)}


def ellipse(spec):
    (cx, cy), rx, ry = spec
    return {(x, y) for x in range(int(cx - rx) - 1, int(cx + rx) + 2) for y in range(int(cy - ry) - 1, int(cy + ry) + 2)
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0}


def window(cells):
    return {(x + dx, y + dy) for (x, y) in cells for dx in range(-VIEW[0], VIEW[0] + 1)
            for dy in range(-VIEW[1], VIEW[1] + 1)}


def wall_errors(tiles: dict, floor: set, label: str) -> list:
    errs = []
    for c, it in tiles.items():
        if c in floor:
            continue
        want = pieces_for(neighbors_in(floor, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
        if want is None or len(want) > 1 or (want and it[0] != want[0]) or (not want and it[0] != ROCK):
            errs.append(f"{label} pared {c}: quiere {want} tiene {it[0]}")
    return errs


def build_z8(existing) -> tuple[dict, list]:
    errs = []
    island = ellipse(ISLAND8) & rect(BOX8)
    if not BV.grow(FLOOR8, 1) <= island:
        errs.append("z8: el islote no alcanza para las paredes del pozo")
    tiles = NP.cave_tiles(FLOOR8, island, SEED + 1)
    for c in FLOOR8:
        tiles[c] = [CAVE_FLOOR]
    tiles[SHAFT_UP] = [CAVE_FLOOR, SHAFT_LADDER]
    tiles[SHAFT_DOWN] = [STAIR_DOWN]
    errs += wall_errors({c: t for c, t in tiles.items() if c not in (SHAFT_DOWN,)}, FLOOR8, "z8")
    for pos, torch in SHAFT_LIGHTS.items():
        tiles[pos].append(torch)
    # lo que pisa el islote: solo lava o el pozo viejo
    for c in island:
        it = existing.get((c[0], c[1], Z8))
        if it and it[0] not in LAVA | CAVE_FLOORS | WALLS | {ROCK, STAIR_DOWN}:
            errs.append(f"z8: el islote pisa algo ajeno en {c}: {it}")
    # la caja vieja del pozo (v1: 169-175 x 96-102) que quede fuera del islote vuelve a ser lava
    for c in rect((169, 96, 175, 102)) - island:
        tiles[c] = [598]
    return tiles, errs


def build_z9(existing):
    errs = []
    box = rect(BOX9)
    for c in box:
        it = existing.get((c[0], c[1], Z9))
        if it and it[0] not in LAVA | CAVE_FLOORS | WALLS | {ROCK, STAIR_DOWN} and STAIRS_UP not in it:
            errs.append(f"z9: la caja pisa algo ajeno en {c}: {it}")
            break
    allowed = rect(ALLOWED9)
    inner = {c for c in allowed if all((c[0] + dx, c[1] + dy) in allowed for dx in range(-2, 3) for dy in range(-2, 3))}
    rooms = [(center, r) for center, r in CHAMBERS.values()]
    band, core = BV.ribbon(PATH9, rooms, SEED)
    must = {DEPTHS_UP, DEPTHS_LAND, (DEPTHS_UP[0], DEPTHS_UP[1] - 1)}
    floor = NP.carve_cave(SEED, allowed & (band | must), (core & inner) | must, DEPTHS_LAND, MIN_FLOOR9)
    tiles = NP.cave_tiles(floor, box, SEED)
    paint = NP.Noise(SEED + 515)
    for c in floor:
        v = paint.fbm(c[0] / 5, c[1] / 5, 3, 10)
        tiles[c] = [CAVE_MUD if v > 0.68 else CAVE_FLOOR_ALT if v < 0.36 else CAVE_FLOOR]
    tiles[DEPTHS_UP] = [CAVE_FLOOR, STAIRS_UP]
    bl = NP.Blocking()
    keep = BV.grow({DEPTHS_UP, DEPTHS_LAND}, 2)
    NP.decorate_cave(tiles, floor, DEPTHS_LAND, keep, SEED + 2, 0.05, bl)
    errs += wall_errors(tiles, floor, "z9")
    return tiles, floor, errs


def place_groups(tiles, floor, dist, bl):
    walk = {c for c in floor if bl.walkable(tiles[c]) and c != DEPTHS_UP}
    avoid = BV.grow({DEPTHS_LAND}, 4)
    rng = random.Random(f"{SEED}-bamboo")
    taken, out = set(), []
    for chamber, mons in GROUPS:
        (cx, cy), r = CHAMBERS[chamber]
        cands = sorted((c for c in walk - avoid - taken if abs(c[0] - cx) + abs(c[1] - cy) <= r + 3 and c in dist),
                       key=lambda c: (abs(c[0] - cx) + abs(c[1] - cy), rng.random()))
        for c in cands:
            if any(abs(c[0] - o[0][0]) + abs(c[1] - o[0][1]) < 3 for o in out):
                continue
            spots = [c] + [n for n in ((c[0] + 1, c[1]), (c[0], c[1] + 1), (c[0] - 1, c[1]), (c[0], c[1] - 1))
                           if n in walk and n not in taken and n not in avoid]
            if len(spots) < len(mons):
                continue
            out.append((c, Z9, [(name, spots[i], st) for i, (name, st) in enumerate(mons)]))
            taken |= set(spots[:len(mons)])
            break
        else:
            raise SystemExit(f"no entra el grupo {mons} en {chamber}")
    return out


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def write_cells(path, cells_ids: dict, z, stackable):
    """Casillas sueltas por filas (cada fila, una caja de 1 de alto con sus casillas contiguas)."""
    rows = {}
    for (x, y), ids in cells_ids.items():
        rows.setdefault(y, []).append((x, ids))
    for y, lst in rows.items():
        lst.sort()
        run = [lst[0]]
        for item in lst[1:] + [None]:
            if item is not None and item[0] == run[-1][0] + 1:
                run.append(item)
                continue
            m = roomkit.Map()
            for x, ids in run:
                m.ground((x, y, z), ids[0])
                for i in ids[1:]:
                    m.add((x, y, z), i)
            roomkit.write_map(path, m, (run[0][0], y, run[-1][0], y), z, stackable)
            if item is not None:
                run = [item]


def to_map(tiles: dict, z: int) -> roomkit.Map:
    m = roomkit.Map()
    for (x, y), ids in tiles.items():
        m.ground((x, y, z), ids[0])
        for i in ids[1:]:
            m.add((x, y, z), i)
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path, help="carpeta: escribe z8.png y z9.png")
    a = ap.parse_args()

    existing = load_tiles()
    bl = NP.Blocking()
    t8, errs = build_z8(existing)
    t9, floor9, e9 = build_z9(existing)
    errs += e9
    walk9 = {c for c in floor9 if bl.walkable(t9[c])}
    dist = reach(walk9, DEPTHS_LAND, CARD)
    if len(dist) != len(walk9):
        errs.append(f"z9: {len(walk9) - len(dist)} casillas caminables sueltas")
    # fogatas en las cámaras (no cortan el paso: block_pathfind)
    for name, ((cx, cy), r) in CHAMBERS.items():
        cands = sorted((c for c in walk9 if len(t9[c]) == 1 and abs(c[0] - cx) + abs(c[1] - cy) <= r + 2
                        and len(neighbors_in(floor9, *c)) <= 6 and c not in BV.grow({DEPTHS_LAND}, 3)),
                       key=lambda c: (abs(c[0] - cx) + abs(c[1] - cy), c))
        if cands:
            t9[cands[-1]].append(CAMP_FIRE)
    spawns = place_groups(t9, floor9, dist, bl)
    n_mon = sum(len(m) for _c, _z, m in spawns)
    for (_c, _z, mons) in spawns:
        for name, p, _st in mons:
            if p not in dist:
                errs.append(f"spawn {name} {p}: no se llega")
    # La escalera de mano no tiene floorchange: la bajada llega a su ancla.
    surface_exit = existing.get((ENTRANCE[0], ENTRANCE[1] + 1, Z7), [])
    if not surface_exit or not bl.walkable(surface_exit):
        errs.append("salida de escalera de mano bloqueada en superficie")
    if not bl.walkable(t8[SHAFT_UP]) or t8[SHAFT_UP] != [CAVE_FLOOR, SHAFT_LADDER]:
        errs.append("escalera de mano del pozo inválida")
    # La escalera de piedra profunda ocupa 2x2 hacia NO.
    for x in (DEPTHS_UP[0] - 1, DEPTHS_UP[0]):
        for y in (DEPTHS_UP[1] - 1, DEPTHS_UP[1]):
            if not bl.walkable(t9.get((x, y), [])):
                errs.append(f"huella de escalera profunda obstruida: {x},{y}")
    if not bl.walkable(t8[SHAFT_LAND]) or not bl.walkable(t9[DEPTHS_LAND]):
        errs.append("llegada de escalera no caminable")
    # vista: fuera de las cajas, vacío o lava -> roca (z9); vacío -> roca (z8, la lava del hunt se queda)
    view9 = window(walk9) - rect(BOX9)
    fill9 = {c for c in view9 if not existing.get((c[0], c[1], Z9)) or existing[(c[0], c[1], Z9)][0] in LAVA}
    walk8 = {c for c in FLOOR8 if bl.walkable(t8[c])}
    fill8 = {c for c in window(walk8) - rect(BOX8) if not existing.get((c[0], c[1], Z8))}
    print(f"z8: pozo de {len(FLOOR8)} casillas en un islote de {len(ellipse(ISLAND8) & rect(BOX8))}; "
          f"z9: {len(walk9)} caminables, {len(spawns)} spawns / {n_mon} monstruos")
    print(f"  a la vista -> roca: z9 {len(fill9)} (vacío o lava), z8 {len(fill8)} (vacío)")
    if a.preview:
        a.preview.mkdir(parents=True, exist_ok=True)
        from mapdata import Renderer, png_bytes
        for z, t, fill, b in ((8, t8, fill8, BOX8), (9, t9, fill9, BOX9)):
            tiles = {k: v for k, v in existing.items() if k[2] == z}
            for (x, y), ids in t.items():
                tiles[(x, y, z)] = ids
            for (x, y) in fill:
                tiles[(x, y, z)] = [ROCK]
            w, h, rgba = Renderer().area(tiles, b[0] - 10, b[1] - 6, b[2] + 10, b[3] + 6, z)
            (a.preview / f"z{z}.png").write_bytes(png_bytes(w, h, rgba))
        print(f"preview: {a.preview}")
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs[:40]), file=sys.stderr)
        return 1
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    backup = Path(tempfile.gettempdir()) / f"bamboo-depths-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAP, backup / "test.otbm")
    shutil.copy2(SPAWNS, backup / "test-spawn.xml")
    print(f"backup: {backup}")
    m9 = to_map(t9, Z9)
    stackable = roomkit.Checker(m9).stackable
    m7 = roomkit.Map()
    m7.ground((ENTRANCE[0], ENTRANCE[1], Z7), ENTRANCE_HOLE)
    roomkit.write_map(MAP, m7, (ENTRANCE[0], ENTRANCE[1], ENTRANCE[0], ENTRANCE[1]), Z7, stackable)
    write_cells(MAP, t8, Z8, stackable)            # solo el islote (y la caja vieja): la lava de alrededor queda
    roomkit.write_map(MAP, m9, BOX9, Z9, stackable)
    if fill9:
        write_cells(MAP, {c: [ROCK] for c in fill9}, Z9, stackable)
    if fill8:
        write_cells(MAP, {c: [ROCK] for c in fill8}, Z8, stackable)
    raw = SPAWNS.read_text(encoding="latin-1")
    block = ("\t<!-- BEGIN BAMBOO_DEPTHS_SPAWNS (scripts/map/generate-bamboo-depths.py) -->\n"
             + spawn_xml(spawns) + "\n\t<!-- END BAMBOO_DEPTHS_SPAWNS -->\n")
    pat = re.compile(r"[ \t]*<!-- BEGIN BAMBOO_DEPTHS_SPAWNS.*?<!-- END BAMBOO_DEPTHS_SPAWNS -->\n?", re.S)
    raw = pat.sub(lambda _m: block, raw, count=1) if pat.search(raw) else raw.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(raw, encoding="latin-1")
    MANIFEST.write_text(json.dumps({
        "name": "Cuevas de Bambú", "version": 3, "seed": SEED, "entrance": [*ENTRANCE, Z7],
        "access": {"hole": ENTRANCE_HOLE, "ladder": SHAFT_LADDER},
        "z8": {"floor": sorted(FLOOR8), "island": [*ISLAND8[0], ISLAND8[1], ISLAND8[2]], "box": list(BOX8)},
        "z9": {"box": list(BOX9), "walkable": len(walk9), "path": PATH9, "chambers": CHAMBERS},
        "rockFilled": {"z9": len(fill9), "z8": len(fill8)},
        "spawns": len(spawns), "monsters": n_mon,
    }, indent=2) + "\n")
    print(f"OK {MAP}, {SPAWNS.name} y {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
