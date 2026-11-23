#!/usr/bin/env python3
"""Campo de Brasas: agranda la península de tierra de 36,63,7 hacia el norte, sobre el mar de lava.

La isla volcánica del noroeste (Demon Skeletons, tumbas, coal basins) termina al oeste en una península angosta
(x 36-45, y 59-63). Este generador le suma tierra al norte de esa península, sobre la lava, con la misma
receta que la isla: suelo `dirt` 103, bordes de lava `4667-4678` puestos SOBRE la casilla de lava según dónde
está la tierra (regla `lava_borders`, que reproduce los 1501 bordes que ya tiene la isla), árboles muertos,
madera vieja y coal basins (luz). Spawns de Demon Skeleton, Fire Devil y Bone Beast.

No rompe el mapa (lo valida antes de escribir; si algo falla, no escribe nada):
  - solo convierte lava (598/601) sin otros ítems que bordes; no toca casillas de la isla ni de otras zonas;
  - la tierra nueva queda a 3+ casillas de cualquier suelo que no sea lava ni de la isla (la estructura del
    norte no se une a la isla por acá);
  - desde ninguna casilla nueva se ve el vacío negro (todas las casillas a ±9, ±7 existen);
  - toda la tierra nueva se alcanza caminando desde la península; ni lava de 1 casilla encerrada ni tierra
    suelta de 1 casilla;
  - cada spawn sobre tierra libre.

  python3.11 scripts/map/generate-ember-field.py --dry-run --preview /tmp/brasas.png
  python3.11 scripts/map/generate-ember-field.py
Re-ejecutable: si la tierra ya está, solo rehace bordes, decoración propia y spawns (bloque EMBER_FIELD_SPAWNS).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
import mapdata  # noqa: E402

ROOT = HERE.parents[1]
MAP = ROOT / "server/YurOTS/ots/data/world/test.otbm"
SPAWNS = ROOT / "server/YurOTS/ots/data/world/test-spawn.xml"
Z = 7
LAVA = {598, 601}               # se reemplaza en main() por todos los suelos "lava" que bloquean (del OTB)
CONVERTIBLE = {598, 601}        # lava común: la única que se convierte en tierra (600 y otras quedan como pozos)
MANIFEST = ROOT / "server/YurOTS/ots/data/world/generated-ember-field.json"
DIRT = 103
BORDER = dict(n=4667, e=4668, s=4669, w=4670, nw_in=4671, ne_in=4672, sw_in=4673, se_in=4674,
              nw_out=4675, ne_out=4676, sw_out=4677, se_out=4678)
BORDER_IDS = set(BORDER.values())
DEAD_TREES = (2709, 2717, 2720)
RUSH_WOOD = 2721
COAL = 1484
OWN_DECOR = set(DEAD_TREES) | {RUSH_WOOD, COAL}
PENINSULA = (40, 61)                        # casilla de la península actual (arranque del BFS)
AREA = (28, 49, 62, 63)                     # dónde puede crecer (x0, y0, x1, y1)
# forma: elipses (cx, cy, rx, ry) unidas; la de abajo se apoya en la península
BLOBS = [(39, 55.5, 5.5, 4.0), (46, 53.5, 5.0, 3.5), (52, 54.5, 4.0, 3.0), (34, 56.5, 3.5, 2.5),
         (57, 52.5, 4.5, 2.8)]
SPAWN_LIST = [  # (nombre, x, y, respawn)
    ("Demon Skeleton", 38, 54, 120), ("Demon Skeleton", 45, 52, 120), ("Demon Skeleton", 51, 55, 120),
    ("Fire Devil", 35, 57, 120), ("Fire Devil", 42, 56, 120), ("Fire Devil", 48, 54, 120),
    ("Bone Beast", 41, 52, 180), ("Bone Beast", 46, 56, 180), ("Demon Skeleton", 57, 52, 120),
]
T_AREA, T_TILE, T_ITEM, T_HOUSETILE = 4, 5, 6, 14


def h(x, y, k=0):
    return ((x * 73856093) ^ (y * 19349663) ^ (k * 83492791)) & 0xFFFF


def lava_borders(isdirt, x, y):
    n, s, e, w = isdirt(x, y - 1), isdirt(x, y + 1), isdirt(x + 1, y), isdirt(x - 1, y)
    out = []
    if n and w:
        out.append(BORDER["nw_out"])
    elif n and e:
        out.append(BORDER["ne_out"])
    elif s and w:
        out.append(BORDER["sw_out"])
    elif s and e:
        out.append(BORDER["se_out"])
    else:
        out += [BORDER[k] for k, v in (("n", n), ("s", s), ("e", e), ("w", w)) if v]
    for k, (dx, dy), o1, o2 in (("nw_in", (-1, -1), n, w), ("ne_in", (1, -1), n, e),
                                ("sw_in", (-1, 1), s, w), ("se_in", (1, 1), s, e)):
        if isdirt(x + dx, y + dy) and not o1 and not o2:
            out.append(BORDER[k])
    return out


def island_of(t, start):
    """Casillas de suelo no-lava conectadas (8 direcciones) a start: la isla."""
    seen, todo = {start}, [start]
    while todo:
        x, y = todo.pop()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p = (x + dx, y + dy)
                ids = t.get((p[0], p[1], Z))
                if p not in seen and ids and ids[0] not in LAVA:
                    seen.add(p)
                    todo.append(p)
    return seen


def design(t):
    island = island_of(t, PENINSULA)
    other = {(x, y) for (x, y, z), ids in t.items() if z == Z and ids and ids[0] not in LAVA and (x, y) not in island}
    x0, y0, x1, y1 = AREA

    def free_lava(x, y):
        ids = t.get((x, y, Z))
        return bool(ids) and ids[0] in CONVERTIBLE and all(i in BORDER_IDS for i in ids[1:])

    def safe(x, y):
        if not free_lava(x, y) or not (x0 <= x <= x1 and y0 <= y <= y1):
            return False
        if any((x + dx, y + dy) in other for dx in range(-3, 4) for dy in range(-3, 4)):
            return False
        return all((x + dx, y + dy, Z) in t for dx in range(-9, 10) for dy in range(-7, 8))

    new = set()
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for cx, cy, rx, ry in BLOBS:
                wob = 1 + ((h(x, y) % 7) - 3) * 0.035
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= wob and safe(x, y):
                    new.add((x, y))
    land = lambda p: p in new or p in island  # noqa: E731
    for _ in range(4):                       # limpiar: sin lava de 1 casilla ni tierra suelta
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                p = (x, y)
                orth = sum(land((x + dx, y + dy)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if p not in new and p not in island and orth >= 3 and safe(x, y):
                    new.add(p)
                elif p in new and orth <= 1:
                    new.discard(p)
    # solo lo conectado a la península
    seen, todo = set(), [p for p in new if any((p[0] + dx, p[1] + dy) in island
                                               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    seen.update(todo)
    while todo:
        x, y = todo.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (x + dx, y + dy)
            if q in new and q not in seen:
                seen.add(q)
                todo.append(q)
    return seen, island, other


def reachable(new, island, blocked):
    walk = new - blocked
    start = [p for p in walk if any((p[0] + dx, p[1] + dy) in island for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    seen, todo = set(start), list(start)
    while todo:
        x, y = todo.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (x + dx, y + dy)
            if q in walk and q not in seen:
                seen.add(q)
                todo.append(q)
    return seen == walk


def decorate(new, island):
    """Todo lo decorado bloquea: se pone de a uno y se descarta si deja casillas sin acceso o tapa un spawn."""
    spawn_cells = {(x, y) for _n, x, y, _s in SPAWN_LIST}
    wish = [((x, y), COAL) for x, y in ((40, 53), (47, 55), (36, 56), (56, 52))]
    for x, y in sorted(new):
        r = h(x, y, 1) % 100
        if r < 4:
            wish.append(((x, y), DEAD_TREES[h(x, y, 2) % 3]))
        elif r < 7:
            wish.append(((x, y), RUSH_WOOD))
    deco = {}
    for p, item in wish:
        if p not in new or p in deco or p in spawn_cells:
            continue
        deco[p] = item
        if not reachable(new, island, set(deco)):
            del deco[p]
    return deco


def validate(t, new, island, deco, spawn_list):
    errs = []
    land = new | island
    for x, y in new:
        for dx in range(-9, 10):
            for dy in range(-7, 8):
                if (x + dx, y + dy, Z) not in t:
                    errs.append(f"{x},{y}: se ve el vacío en {x + dx},{y + dy}")
                    break
    walk = {p for p in new if p not in deco or deco[p] == 0}
    blocked = {p for p, i in deco.items()}
    # todo lo nuevo caminable se alcanza desde la península
    start = [p for p in walk if any((p[0] + dx, p[1] + dy) in island for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    seen, todo = set(start), list(start)
    while todo:
        x, y = todo.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (x + dx, y + dy)
            if q in walk and q not in seen:
                seen.add(q)
                todo.append(q)
    lost = walk - seen
    if lost:
        errs.append(f"{len(lost)} casillas nuevas no se alcanzan: {sorted(lost)[:6]}")
    for name, x, y, _ in spawn_list:
        if (x, y) not in walk or (x, y) in blocked:
            errs.append(f"spawn {name} en {x},{y}: no es tierra libre nueva")
    known = set(re.findall(r'<monster name="([^"]+)"', (ROOT / "server/YurOTS/ots/data/monster/monsters.xml").read_text(encoding="latin-1")))
    for name, *_ in spawn_list:
        if name not in known:
            errs.append(f"monstruo inexistente: {name}")
    return errs


def preview(t, new, deco, path: Path):
    tiles = dict(t)
    for (x, y) in new:
        tiles[(x, y, Z)] = [DIRT] + ([deco[(x, y)]] if (x, y) in deco else [])
    isdirt = lambda x, y: bool(tiles.get((x, y, Z))) and tiles[(x, y, Z)][0] not in LAVA  # noqa: E731
    for (x, y, z), ids in list(tiles.items()):
        if z == Z and ids[0] in LAVA and AREA[0] - 2 <= x <= AREA[2] + 2 and AREA[1] - 2 <= y <= AREA[3] + 2:
            tiles[(x, y, z)] = [ids[0]] + lava_borders(isdirt, x, y)
    w, hh, px = mapdata.Renderer().area(tiles, AREA[0] - 6, AREA[1] - 6, AREA[2] + 10, AREA[3] + 16, Z)
    path.write_bytes(mapdata.png_bytes(w, hh, px, scale=1))


def write_map(raw, new, deco):
    root = mapdata.parse_tree(raw)
    if mapdata.serialize_tree(root, raw[:4]) != raw:
        raise SystemExit("el OTBM no se reescribe idéntico: no toco nada")
    nodes = {}
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        if az != Z:
            continue
        for tile in area[2]:
            if tile[0] == T_TILE:
                nodes[(ax + tile[1][0], ay + tile[1][1])] = tile

    def ground_of(tile):
        p = bytes(tile[1])
        pos = 2
        while pos < len(p):
            attr = p[pos]
            pos += 1
            if attr == 3:
                pos += 4
            elif attr == 9:
                return struct.unpack_from("<H", p, pos)[0]
            else:
                break
        for c in tile[2]:
            if c[0] == T_ITEM:
                return struct.unpack_from("<H", bytes(c[1]), 0)[0]
        return None

    def flags_of(tile):
        p = bytes(tile[1])
        return p[3:7] if len(p) >= 7 and p[2] == 3 else None

    def set_tile(tile, ground, items):
        fl = flags_of(tile)
        props = bytearray(tile[1][:2]) + (bytearray(b"\x03" + fl) if fl else bytearray())
        tile[1] = props
        tile[2] = [[T_ITEM, bytearray(struct.pack("<H", i)), []] for i in [ground] + items]

    isdirt = lambda x, y: (x, y) in new or ((x, y) in nodes and ground_of(nodes[(x, y)]) not in LAVA  # noqa: E731
                                            and ground_of(nodes[(x, y)]) is not None)
    changed = 0
    for (x, y) in new:
        set_tile(nodes[(x, y)], DIRT, [deco[(x, y)]] if (x, y) in deco else [])
        changed += 1
    x0, y0, x1, y1 = AREA
    for x in range(x0 - 2, x1 + 3):
        for y in range(y0 - 2, y1 + 3):
            tile = nodes.get((x, y))
            if tile is None or (x, y) in new:
                continue
            g = ground_of(tile)
            if g not in LAVA:
                continue
            others = [struct.unpack_from("<H", bytes(c[1]), 0)[0] for c in tile[2] if c[0] == T_ITEM][1:]
            if any(i not in BORDER_IDS for i in others):
                continue                         # lava con otra cosa encima: no se toca
            want = lava_borders(isdirt, x, y)
            if sorted(others) != sorted(want):
                set_tile(tile, g, want)
                changed += 1
    return mapdata.serialize_tree(root, raw[:4]), changed


def spawn_xml(spawn_list):
    lines = []
    for name, x, y, st in spawn_list:
        lines.append(f'\t<spawn centerx="{x}" centery="{y}" centerz="{Z}" radius="2">')
        lines.append(f'\t\t<monster name="{name}" x="0" y="0" z="{Z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()
    raw = MAP.read_bytes()
    mapdata.MAP = MAP
    t = mapdata.load_tiles()
    otb = mapdata.load_otb()
    LAVA.clear()
    LAVA.update(i for i, r in otb.items() if r.get("name") == "lava" and "block_solid" in r["flags"])
    if MANIFEST.exists():
        # re-ejecución: la tierra nueva es la del manifiesto (no se vuelve a diseñar sobre el mapa ya cambiado)
        new = {tuple(p) for p in json.loads(MANIFEST.read_text())["tiles"]}
        island = island_of(t, PENINSULA) - new
    else:
        new, island, _other = design(t)
    deco = decorate(new, island)
    errs = validate(t, new, island, deco, SPAWN_LIST)
    print(f"Campo de Brasas: {len(new)} casillas de tierra nuevas, {len(deco)} decorados, {len(SPAWN_LIST)} monstruos "
          f"(1 cada {len(new) // max(1, len(SPAWN_LIST))} casillas)")
    if a.preview:
        preview(t, new, deco, a.preview)
        print(f"preview {a.preview}")
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs[:30]), file=sys.stderr)
        return 1
    if a.dry_run:
        print("(dry-run)")
        return 0
    data, changed = write_map(raw, new, deco)
    MAP.write_bytes(data)
    sp = SPAWNS.read_text(encoding="latin-1")
    block = "\t<!-- BEGIN EMBER_FIELD_SPAWNS (scripts/map/generate-ember-field.py) -->\n" + \
        spawn_xml(SPAWN_LIST) + "\n\t<!-- END EMBER_FIELD_SPAWNS -->\n"
    old = re.compile(r"[ \t]*<!-- BEGIN EMBER_FIELD_SPAWNS.*?<!-- END EMBER_FIELD_SPAWNS -->\n?", re.S)
    sp = old.sub(lambda _m: block, sp, count=1) if old.search(sp) else sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")
    MANIFEST.write_text(json.dumps({"name": "Campo de Brasas", "z": Z, "area": AREA, "tiles": sorted(new),
                                    "decor": {f"{x},{y}": i for (x, y), i in sorted(deco.items())},
                                    "spawns": SPAWN_LIST}, indent=1) + "\n")
    print(f"OK {MAP} ({changed} casillas), {SPAWNS.name}, {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
