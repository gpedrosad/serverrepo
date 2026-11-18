#!/usr/bin/env python3
"""Guarida de los Trolls: cueva de un piso (z8) al sur de las ruinas de los trolls.

Se entra por un agujero en el pasto del sur (la orilla del lago de la catedral vieja), se cae a la
cueva y se sube con la escalera de mano. Los River Troll refugian cerca de la escalera y los Stone
Troll viven al fondo, entre piedras y huesos.

Caja: x 155-176, y 103-114, z8 (22x12). El lugar se cava en un bolsón de lava del mapa original
(mismo criterio que el dungeon de la city, que cavó su caja en este campo). El techo de la cueva es
el pasto/lago de z7, que ya tiene casillas; el generador comprueba que no quede vacío a la vista.

Reglas que valida antes de escribir (receta de docs/items-and-map/PIEZAS_DE_MAPA.md#cuevas,
docs/items-and-map/ZONAS_DE_CAZA.md y docs/items-and-map/MAPEAR_DUNGEON_CITY.md):
  - la caja es propia (solo lava o tiles de una corrida anterior);
  - paredes con pieza única sobre el piso combinado, roca donde no toca piso;
  - sin vacío a media pantalla desde cualquier piso caminable (también fuera de la caja);
  - todo el piso se alcanza desde la escalera;
  - agujero arriba de la escalera, escalera sola sobre piso de cueva, llegada caminable al sur;
  - decoración que no se mueve ni se levanta; fogata a 2-3 casillas, nunca encima de la escalera;
  - cada spawn sobre piso libre, sin pisar la huella 2x2 y a 6+ casillas de la escalera.

Uso (desde la raíz del repo):
  python3 scripts/map/generate-troll-den.py --dry-run --preview /tmp/guarida.png
  python3 scripts/map/generate-troll-den.py           # mapa, spawns, cartel y manifiesto
  python3 scripts/map/check-upper-view.py             # después: techo sobre la cueva
  python3 scripts/map/check-map-load.py               # y que el mapa cargue

Re-ejecutable: borra su caja, reescribe el agujero, el cartel, los spawns y el manifiesto.
Doc: docs/gameplay/RIVER_STONE_TROLLS.md (sección Guarida).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import shutil
import struct
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, parse_tree, serialize_tree  # noqa: E402

_spec = importlib.util.spec_from_file_location("north_pass", HERE / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)
carve_cave, cave_tiles = NP.carve_cave, NP.cave_tiles
pieces_for, neighbors_in, Noise, reach, Blocking = (
    NP.pieces_for, NP.neighbors_in, NP.Noise, NP.reach, NP.Blocking)
WALL_SIDE, WALL_CORNER, WALL_INNER, ROCK = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER, NP.ROCK
CAVE_FLOORS, CAVE_FLOOR, CAVE_MUD, CAVE_FLOOR_ALT = (
    NP.CAVE_FLOORS, NP.CAVE_FLOOR, NP.CAVE_MUD, NP.CAVE_FLOOR_ALT)
CARD, ALL8, NEEDS_COUNT = NP.CARD, NP.ALL8, NP.NEEDS_COUNT

_spec = importlib.util.spec_from_file_location("beast_valley", HERE / "generate-beast-valley.py")
BV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BV)
grow, stamp, ellipse = BV.grow, BV.stamp, BV.ellipse
place_stages, slices_by, rooms_along = BV.place_stages, BV.slices_by, BV.rooms_along

WORLD = MAP.parent
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MANIFEST = WORLD / "generated-troll-den.json"

Z8 = 8
X0, Y0, W, H = 155, 103, 22, 12          # x 155-176, y 103-114
Z7 = 7
LAVA = 598                                # lo que se borra de la caja
GRASS = 4756
HOLE, LADDER, SIGN = 479, 1386, 1429      # agujero arriba, escalera de mano abajo, cartel en el pasto
CAMPFIRE, BONES, STONE, MOSS = 1423, 2248, (1309, 1323), 1353
VIEW = (7, 5)                             # media pantalla del cliente 7.6
STAIR_CLEAR = 6

# Entrada: agujero en el pasto del sur (la franja caminable entre el lago y las ruinas).
ENT_BOX = (156, 104, 174, 112)           # candidatos de agujero en z7
ENT_FROM = (153, 73)                     # extremo sur del puente de sogas (zona de los River Troll)

# Recorrido (coords locales): bajás por la columna oeste, cruzás el sur y subés por la este.
PATH = [(3, 2), (3, 9), (18, 9), (18, 2)]
ROOMS = [((10, 9), 3), ((17, 3), 3)]     # sala del fogón (sur) y cámara de los Stone Troll (NE)

# Etapas de caza (nombres, por spawn, spawntime, separación): sueltos al entrar, de a 2 al fondo.
STAGES = [
    (("River Troll",), 1, 175, 12),
    (("River Troll", "Stone Troll"), 1, 200, 12),
    (("Stone Troll",), 2, 235, 10),
]

SIGN_TEXT = ("GUARIDA DE LOS TROLLS\n"
             "Agujero abajo: river trolls cerca de la escalera\n"
             "y stone trolls al fondo, entre las piedras.")


# ----------------------------------------------------------------------------------------------------------------------
def read_tiles(root):
    """{(x, y, z): (ground, [items])} del árbol OTBM. `ground` puede ser None (muro sobre vacío)."""
    out = {}
    md = root[2][0]
    for area in md[2]:
        if area[0] != T_AREA:
            continue
        bx, by, bz = struct.unpack_from("<HHB", bytes(area[1]), 0)
        for tile in area[2]:
            if tile[0] not in (T_TILE, T_HOUSETILE):
                continue
            props = bytes(tile[1])
            if len(props) < 2:
                continue
            ox, oy = props[0], props[1]
            pos, ground, p = (bx + ox, by + oy, bz), None, 2
            while p < len(props):
                attr = props[p]
                p += 1
                if attr == 3:                                   # TILE_FLAGS
                    p += 4
                elif attr == 9:                                # ground inline
                    ground = props[p] | (props[p + 1] << 8)
                    p += 2
                    if ground in NEEDS_COUNT:
                        p += 1
                    break
                else:
                    break
            items = []
            for child in tile[2]:
                if child[0] == T_ITEM and len(child[1]) >= 2:
                    items.append(child[1][0] | (child[1][1] << 8))
            out[pos] = (ground, items)
    return out


def covered(existing, pos) -> bool:
    """Una casilla se ve (no es vacío negro) si tiene ground o algún ítem encima."""
    g, its = existing.get(pos, (None, []))
    return g is not None or bool(its)


def item_node(iid: int) -> list:
    props = bytearray(struct.pack("<H", iid))
    if iid in NEEDS_COUNT:
        props.append(1)
    return [T_ITEM, props, []]


def new_tile(x: int, y: int, bx: int, by: int, ground: int, items=()) -> list:
    props = bytearray([x - bx, y - by, 9]) + struct.pack("<H", ground)
    return [T_TILE, props, [item_node(i) for i in items]]


def write_preview(path: Path, tiles: dict, cells: set):
    """Dibujo simple de la caja (coords locales): piso claro, pared oscura, escalera marcada."""
    S = 6
    img = bytearray(b"\x20\x20\x28\xff" * (W * S * H * S))
    for (x, y), it in tiles.items():
        g, extra = it[0], it[1:]
        col = {ROCK: (40, 36, 42), CAVE_MUD: (60, 42, 34), CAVE_FLOOR_ALT: (74, 52, 40)}.get(g, (86, 62, 46))
        if g in WALL_SIDE.values() or g in WALL_CORNER.values() or g in WALL_INNER.values():
            col = (52, 34, 26)
        if LADDER in extra:
            col = (240, 200, 90)
        elif CAMPFIRE in extra:
            col = (200, 110, 30)
        elif BONES in extra:
            col = (216, 210, 190)
        elif any(i in STONE or i == MOSS for i in extra):
            col = (110, 120, 96)
        for dy in range(S):
            for dx in range(S):
                o = ((y * S + dy) * W * S + x * S + dx) * 4
                if 0 <= o < len(img):
                    img[o:o + 4] = bytes((*col, 255))
    path.write_bytes(BV.png_bytes(W * S, H * S, bytes(img)))


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{X0 + cx}" centery="{Y0 + cy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines) + "\n"


def pick_entrance(existing: dict) -> tuple[int, int]:
    """El agujero va en el pasto del sur: caminable desde el puente, limpio y con llegada al sur."""
    solid = {sid for sid, rec in Blocking().otb.items() if "block_solid" in rec["flags"]}

    def walk7(pos):
        g, its = existing.get(pos, (None, []))
        return g is not None and g not in solid and not any(i in solid for i in its)

    seen, todo = {ENT_FROM}, [ENT_FROM]
    while todo:
        x, y = todo.pop()
        for dx, dy in CARD:
            n = (x + dx, y + dy)
            if n not in seen and walk7((n[0], n[1], Z7)):
                seen.add(n)
                todo.append(n)
    cands = []
    for y in range(ENT_BOX[1], ENT_BOX[3] + 1):
        for x in range(ENT_BOX[0], ENT_BOX[2] + 1):
            if (x, y) not in seen:
                continue
            g, its = existing.get((x, y, Z7), (None, []))
            if g not in (GRASS, 4526, 103, 110, 111, 113, 114, 116, 117) or its:
                continue
            if not walk7((x, y + 1, Z7)):
                continue                                   # la escalera sube hacia el sur
            drop = (x - X0, y - Y0)
            if not (2 <= drop[0] <= 19 and 2 <= drop[1] <= 9):
                continue                                   # la caída tiene que caer en la zona cavable
            cands.append((abs(x - 165) + abs(y - 108), x, y))
    if not cands:
        raise SystemExit("no hay casilla de entrada válida en el pasto del sur")
    cands.sort()
    return cands[0][1], cands[0][2]


def place_stones(tiles: dict, floor: set, seed: int, keep: set):
    """Piedras 2x2 y musgo contra la pared, huesos enteros sueltos: nada que se mueva ni se levante."""
    rng = random.Random(seed + 777)
    base = len(reach(set(floor), next(iter(floor)), CARD))
    for c in sorted(floor, key=lambda c: (c[1], c[0])):
        if c in keep or len(tiles[c]) > 1:
            continue
        x, y = c
        # piedras/musgo 2x2: solo donde lo que dibujan hacia arriba-izquierda es pared
        up_covered = all((x + dx, y - 1) not in floor and (x - 1, y + dy) not in floor
                         for dx in (0, -1) for dy in (0, -1))
        near_wall = 8 - len(neighbors_in(floor, x, y)) >= 2
        r = rng.random()
        if up_covered and near_wall and r < 0.10:
            item = MOSS if rng.random() < 0.4 else rng.choice(STONE)
        elif near_wall and r > 0.93:
            item = BONES
        else:
            continue
        probe = set(floor) - {c}
        if len(reach(probe, next(iter(probe)), CARD)) != base - 1:
            continue                                       # no cortar el paso
        tiles[c].append(item)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()

    bl = Blocking()
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    existing = read_tiles(root)

    # 0) la caja es propia: solo lava (primera corrida) o tiles de la corrida anterior
    box = {(x, y) for x in range(X0, X0 + W) for y in range(Y0, Y0 + H)}   # global
    cells = {(x, y) for x in range(W) for y in range(H)}                   # local, para cave_tiles
    mine = {LAVA} | CAVE_FLOORS | {ROCK} | set(WALL_SIDE.values()) | set(WALL_CORNER.values()) \
        | set(WALL_INNER.values()) | {HOLE, LADDER, CAMPFIRE, BONES, MOSS, *STONE}
    for (x, y) in box:
        g, its = existing.get((x, y, Z8), (None, []))
        if (g is None and its) or (g is not None and g not in mine):
            raise SystemExit(f"la caja no es propia: ({x},{y},{Z8}) tiene ground {g} items {its}")

    # 1) sin vacío negro a media pantalla alrededor de la caja (muro sin ground cubre igual)
    margin = {(x, y) for x in range(X0 - VIEW[0], X0 + W + VIEW[0])
              for y in range(Y0 - VIEW[1], Y0 + H + VIEW[1])}
    for (x, y) in margin:
        if not covered(existing, (x, y, Z8)):
            raise SystemExit(f"vacío a la vista de la caja: ({x},{y},{Z8})")

    # 2) entrada: agujero en el pasto del sur + escalera de mano abajo
    hx, hy = pick_entrance(existing)
    drop = (hx - X0, hy - Y0)
    if existing.get((hx, hy, Z8), (None,))[0] != LAVA:
        raise SystemExit(f"la caída ({hx},{hy},{Z8}) no es lava de la caja")
    if existing.get((hx, hy + 1, Z7), (None,))[0] is None:
        raise SystemExit("la llegada de la escalera no existe")

    # 3) la cueva: grilla de bloques 2x2 (carve_cave), recorrido en L con dos salas
    allowed = {(x, y) for x in range(2, W - 2) for y in range(2, H - 2)}
    core = set()
    for (x1, y1), (x2, y2) in zip(PATH, PATH[1:]):
        core |= stamp([(x1, y1), (x2, y1), (x2, y2)], 1)
    core |= {(drop[0] + dx, drop[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1, 2)}
    for (cx, cy), r in ROOMS:
        core |= ellipse(cx + 0.5, cy + 0.5, r + 0.6, r)
    core &= allowed                                # carve_cave exige core dentro de allowed
    floor = carve_cave(a.seed, allowed, core, drop, 110)
    if drop not in floor:
        raise SystemExit("la caída no quedó en el piso de la cueva")
    t8 = cave_tiles(floor, cells, a.seed)
    t8[drop].append(LADDER)
    if len(t8[drop]) != 2:
        raise SystemExit("la escalera no va sola")

    # 4) decoración: fogata cerca de la escalera, piedras contra la pared, huesos enteros
    d = reach(floor, drop, CARD)
    fire = [c for c in sorted(floor, key=lambda c: (c[1], c[0]))
            if c != drop and 2 <= d.get(c, 0) <= 4 and 8 - len(neighbors_in(floor, *c)) >= 2]
    if not fire:
        raise SystemExit("no dónde poner la fogata")
    t8[fire[0]].append(CAMPFIRE)
    place_stones(t8, floor, a.seed, grow({drop}, 2))

    # 5) validaciones de la receta
    errors = []
    walk = {c for c in floor if bl.walkable(t8[c])}
    if not walk <= set(reach(walk, drop, CARD)):
        errors.append("hay piso de cueva inalcanzable desde la escalera")
    for c, it in t8.items():
        if c in floor:
            continue
        want = pieces_for(neighbors_in(floor, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
        if want is None or len(want) > 1 or (want and it[0] != want[0]) or (not want and it[0] != ROCK):
            errors.append(f"pared {c}: quiere {want} tiene {it[0]}")
    # sin vacío negro a media pantalla desde el piso caminable
    for c in walk:
        for dx in range(-VIEW[0], VIEW[0] + 1):
            for dy in range(-VIEW[1], VIEW[1] + 1):
                p = (c[0] + dx, c[1] + dy)
                if p in t8:
                    continue
                if not covered(existing, (X0 + p[0], Y0 + p[1], Z8)):
                    errors.append(f"vacío a la vista desde {c}: {p}")
                    break
            else:
                continue
            break

    # 6) spawns por etapas (sueltos al entrar, de a 2 al fondo), lejos de la escalera
    avoid = grow({drop}, STAIR_CLEAR)
    spawns = place_stages(STAGES, slices_by(walk - avoid, lambda c: d[c], len(STAGES)), walk, avoid, Z8,
                          random.Random(f"{a.seed}-troll-den-{Z8}"))
    for (cx, cy), _z, mons in spawns:
        for _name, (mx, my), _st in mons:
            if (mx, my) not in walk:      # trolls 1x1: basta el piso de su casilla
                errors.append(f"spawn en {mx},{my} sin piso libre")

    counts: dict = Counter()
    for _c, _z, mons in spawns:
        for name, _p, _t in mons:
            counts[name] += 1
    n_mon = sum(counts.values())
    print(f"guarida x{X0}-{X0 + W - 1} y{Y0}-{Y0 + H - 1} z8: {len(walk)} casillas caminables; "
          f"{len(spawns)} spawns ({n_mon} monstruos); agujero {hx},{hy},{Z7}; "
          f"densidad 1 cada {len(walk) / max(n_mon, 1):.0f} casillas")
    print("monstruos: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))

    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        if a.preview:
            write_preview(a.preview, t8, cells)
        return 1
    if a.preview:
        write_preview(a.preview, t8, cells)
        print(f"preview: {a.preview}")
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    # 7) mapa: borrar la caja z8 y el agujero/cartel de z7, insertar la cueva
    md = root[2][0]
    mine_xy = {c for c in box} | {(hx, hy), (hx + 2, hy)}
    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        if az == Z8:
            area[2] = [t for t in area[2]
                       if not (t[0] in (T_TILE, T_HOUSETILE) and (ax + t[1][0], ay + t[1][1]) in box)]
            if not area[2]:
                md[2].remove(area)
        elif az == Z7:
            area[2] = [t for t in area[2]
                       if not (t[0] in (T_TILE, T_HOUSETILE)
                               and (ax + t[1][0], ay + t[1][1]) in {(hx, hy), (hx + 2, hy)})]
            if not area[2]:
                md[2].remove(area)
    buckets: dict = {}
    for (x, y), it in t8.items():
        buckets.setdefault(((X0 + x) & ~0xFF, (Y0 + y) & ~0xFF, Z8), []).append((X0 + x, Y0 + y, it[0], it[1:]))
    g7, its7 = existing[(hx, hy, Z7)][0], [HOLE]
    g7b, its7b = existing[(hx + 2, hy, Z7)][0], [SIGN]
    buckets.setdefault((hx & ~0xFF, hy & ~0xFF, Z7), []).append((hx, hy, g7, its7))
    buckets.setdefault(((hx + 2) & ~0xFF, hy & ~0xFF, Z7), []).append((hx + 2, hy, g7b, its7b))
    for (bx, by, zz), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, zz)), []]
        for gx, gy, ground, items in sorted(lst, key=lambda t: (t[1], t[0])):
            area[2].append(new_tile(gx, gy, bx, by, ground, items))
        md[2].append(area)
    backup = MAP.with_name(MAP.name + ".bak-trollden")
    if not backup.exists():
        shutil.copy2(MAP, backup)
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    # 8) spawns y cartel
    sp = SPAWNS.read_text(encoding="latin-1")
    sp = re.sub(r"[ \t]*<!-- BEGIN TROLL_DEN_SPAWNS.*?<!-- END TROLL_DEN_SPAWNS -->\n?", "", sp, flags=re.S)
    block = ("\t<!-- BEGIN TROLL_DEN_SPAWNS (scripts/map/generate-troll-den.py) -->\n"
             + spawn_xml(spawns) + "\t<!-- END TROLL_DEN_SPAWNS -->\n")
    sp = sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")

    rd = READABLES.read_text(encoding="latin-1")
    lines = ["\t<!-- BEGIN TROLL_DEN_SIGNS -->",
             f'\t<readable x="{hx + 2}" y="{hy}" z="{Z7}" text="{SIGN_TEXT.replace(chr(10), chr(92) + "n")}"/>',
             "\t<!-- END TROLL_DEN_SIGNS -->\n"]
    old = re.search(r"\t?<!-- BEGIN TROLL_DEN_SIGNS -->.*?<!-- END TROLL_DEN_SIGNS -->\n?", rd, flags=re.S)
    if old:
        rd = rd[:old.start()] + "\n".join(lines) + rd[old.end():]
    else:
        rd = rd.replace("</readables>", "\n".join(lines) + "</readables>")
    READABLES.write_text(rd, encoding="latin-1")

    MANIFEST.write_text(json.dumps({
        "name": "generated-troll-den", "seed": a.seed,
        "box": {"x1": X0, "y1": Y0, "x2": X0 + W - 1, "y2": Y0 + H - 1, "z": [Z8]},
        "replaces": "lava pocket z8 (campo de lava del mapa original, como el dungeon de la city)",
        "entrance": {"hole": {"x": hx, "y": hy, "z": Z7}, "ladder": {"x": hx, "y": hy, "z": Z8},
                     "arrival": {"x": hx, "y": hy + 1, "z": Z7}},
        "sign": {"x": hx + 2, "y": hy, "z": Z7},
        "stages": [[list(names), per, st, gap] for names, per, st, gap in STAGES],
        "spawns": len(spawns), "monsters": dict(sorted(counts.items())),
        "density": {"tiles": len(walk), "monsters": n_mon},
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK cartel {READABLES}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
