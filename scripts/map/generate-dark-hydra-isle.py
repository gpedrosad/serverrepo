#!/usr/bin/env python3
"""Isla de las Dark Hydras: isla larga en el mar al sur del bosque (50,139,7), a la que se entra como al Spot del
Dragón Negro: bajada en la orilla, túnel de 1 de ancho bajo el agua, islote del cazador y un puente de 1x4.

  z7  orilla: agujero 469 en 50,138 (al subir se llega a 50,139) y cartel en 49,137
      islote del cazador (pasto con costa) alrededor de 50,146, con su agujero 469 en 50,145 (se sube a 50,146)
      puente de madera 405, 1 de ancho y 4 sobre el agua, en x50 (y149-152)
      isla de las hydras: unión de cuatro elipses de x29 a x70 (y152-162), con borde de costa 4644-4655
  z8  túnel de cueva x50, y138-145, 1 de ancho, escalera de mano 1386 debajo de cada agujero

Las hydras no llegan a tierra firme: la isla, el puente y el islote no tocan ninguna orilla y los monstruos no
pisan agujeros. Si aprietan, el cazador baja por el agujero del islote, se cura en el túnel y vuelve a subir.
Lo que se ve desde las islas y que hoy es vacío (el mapa termina en x44 desde y149) pasa a ser mar.

Uso:
  python3.11 scripts/map/generate-dark-hydra-isle.py --dry-run --preview-dir /tmp/hydra-isle
  python3.11 scripts/map/generate-dark-hydra-isle.py --replace
Doc: docs/items-and-map/MAPEAR_ISLA_DARK_HYDRAS.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
import tempfile
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
MANIFEST = WORLD / "generated-dark-hydra-isle.json"

# Islas: unión de elipses (centro, radio x, radio y). El anillo que toca el agua lleva borde de costa (no se pisa).
ISLET = [((50.5, 146.0), 3.4, 2.6)]                                   # islote del cazador
ISLE = [((35.5, 157.3), 6.5, 3.8), ((44.5, 156.8), 7.5, 4.6),     # isla larga (x29-70): cuatro elipses
        ((54.5, 156.5), 7.5, 4.8), ((63.5, 157.2), 6.5, 4.0)]
BRIDGE_X = 50                               # el puente baja por esta columna (1 de ancho, 4 sobre el agua)
Z7_BOX = (26, 141, 74, 166)                 # se reescribe entera: islas, puente y el resto mar
SHORE_HOLE = (50, 138)                      # bajada en la orilla (469); al subir se llega a 50,139
ISLET_HOLE = (50, 145)                      # bajada en el islote (469); al subir se llega a 50,146
TUNNEL = {(50, y) for y in range(138, 146)}                     # z8, 1 de ancho, recto de escalera a escalera
Z8_BOX = (47, 135, 53, 148)                 # se reescribe entera
SIGN = (49, 137, 7)
HYDRA = ("Dark Hydra", 240)                 # nombre, respawn (s)
HYDRA_GAP = 7                               # distancia mínima (Manhattan) entre hydras
LANDING_CLEAR = 6                           # ninguna hydra a menos de esto de la punta del puente
WOOD, WATER, GRASS, SHORE = 405, 4608, 4756, 4526
WATERS = set(range(4608, 4626)) | {4664, 4665, 4666}
HOLE_ID, LADDER = 469, 1386
ROCK = 101
LAVA = {598, 599, 600, 601}
VIEW = (9, 7)                               # lo que se ve en pantalla (regla del Islote del Minotauro)
COAST_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
COAST_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
COAST_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}


def rect(b):
    return {(x, y) for x in range(b[0], b[2] + 1) for y in range(b[1], b[3] + 1)}


def blob(specs):
    out = set()
    for (cx, cy), rx, ry in specs:
        out |= {(x, y) for x in range(int(cx - rx) - 1, int(cx + rx) + 2) for y in range(int(cy - ry) - 1, int(cy + ry) + 2)
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0}
    return out


def window(cells):
    return {(x + dx, y + dy) for (x, y) in cells for dx in range(-VIEW[0], VIEW[0] + 1) for dy in range(-VIEW[1], VIEW[1] + 1)}


def coast(water, c):
    return NP.pieces_for(NP.neighbors_in(water, *c), COAST_SIDE, COAST_CORNER, COAST_INNER)


def build_z7(existing):
    islet, isle = blob(ISLET), blob(ISLE)
    land = islet | isle
    around = {(x + dx, y + dy) for (x, y) in land for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - rect(Z7_BOX)
    outside_water = {c for c in around if (existing.get((c[0], c[1], 7)) or [0])[0] in WATERS}
    water0 = (rect(Z7_BOX) - land) | outside_water
    inner = {c for c in land if not coast(water0, c)}
    # el puente va del último pasto del islote al primero de la isla en BRIDGE_X; las casillas de orilla que
    # cruza (entries) también pasan a madera
    south = max(y for x, y in inner & islet if x == BRIDGE_X)
    north = min(y for x, y in inner & isle if x == BRIDGE_X)
    span = {(BRIDGE_X, y) for y in range(south + 1, north)}
    bridge = span - land
    entries = span & land
    water = (rect(Z7_BOX) - land - bridge) | outside_water
    m, walk, bad = roomkit.Map(), set(), []
    for c in rect(Z7_BOX):
        pos = (c[0], c[1], 7)
        if c in bridge or c in entries:
            m.ground(pos, WOOD)
            walk.add(c)
        elif c in land:
            pcs = coast(water, c)
            if pcs is None:
                bad.append(c)
                pcs = []
            m.ground(pos, SHORE if pcs else GRASS)
            for i in pcs:
                m.add(pos, i)
            if not pcs:
                walk.add(c)
        else:
            m.ground(pos, WATER)
    m.t[(ISLET_HOLE[0], ISLET_HOLE[1], 7)] = {"ground": HOLE_ID, "items": [], "pz": False}
    hole = roomkit.Map()
    hole.ground((SHORE_HOLE[0], SHORE_HOLE[1], 7), HOLE_ID)
    landing = (BRIDGE_X, north)
    return m, hole, walk, bridge, entries, islet, isle, bad, landing


def build_z8():
    tiles = NP.cave_tiles(TUNNEL, rect(Z8_BOX), 8686)
    for x, y in (SHORE_HOLE, ISLET_HOLE):
        tiles[(x, y)] = [tiles[(x, y)][0], LADDER]
    m = roomkit.Map()
    for (x, y), ids in tiles.items():
        m.ground((x, y, 8), ids[0])
        for i in ids[1:]:
            m.add((x, y, 8), i)
    return m


def hydra_spots(walk7, isle, landing):
    """Hydras sueltas a lo largo de la isla: casillas con todo el 3x3 de pasto, a HYDRA_GAP entre sí y lejos
    de la punta del puente; se eligen de oeste a este para que queden repartidas."""
    cells = sorted(c for c in walk7 & isle
                   if all((c[0] + dx, c[1] + dy) in walk7 for dx in (-1, 0, 1) for dy in (-1, 0, 1))
                   and abs(c[0] - landing[0]) + abs(c[1] - landing[1]) >= LANDING_CLEAR)
    cy = round(sum(y for _x, y in cells) / len(cells))
    out = []
    for c in sorted(cells, key=lambda c: (c[0], abs(c[1] - cy))):
        if all(abs(c[0] - o[0]) + abs(c[1] - o[1]) >= HYDRA_GAP for o in out):
            out.append(c)
    return out


def void_and_lava(existing, walk7):
    """z7: vacío o lava a la vista desde las islas -> mar. z8: vacío o lava a la vista del túnel -> roca."""
    z7 = {c for c in window(walk7) - rect(Z7_BOX)
          if not existing.get((c[0], c[1], 7)) or existing[(c[0], c[1], 7)][0] in LAVA}
    z8 = {c for c in window(TUNNEL) - rect(Z8_BOX)
          if not existing.get((c[0], c[1], 8)) or existing[(c[0], c[1], 8)][0] in LAVA}
    return z7, z8


def validate(existing, z7, walk7, bridge, entries, islet, isle, bad, z8, landing, hydras, regenerating) -> list:
    errs = []
    chk = roomkit.Checker(z7)
    solid = chk.solid
    if bad:
        errs.append(f"isla con casillas de 1 de ancho (sin pieza de costa): {bad[:5]}")
    if not (islet | isle) <= rect(Z7_BOX):
        errs.append(f"las islas se salen de la caja: {sorted((islet | isle) - rect(Z7_BOX))[:5]}")
    if islet & isle:
        errs.append("el islote y la isla se tocan")
    for c in islet | isle:               # todo pasto que toca agua lleva su pieza de orilla
        t = z7.t.get((c[0], c[1], 7))
        if not t or t["ground"] in (WOOD, HOLE_ID):
            continue
        wet = [d for d, (dx, dy) in NP.DIRS.items() if (c[0] + dx, c[1] + dy) not in islet | isle | bridge | entries]
        if wet and not t["items"]:
            errs.append(f"{c}: pasto contra el agua sin pieza de orilla ({wet})")
    if len(bridge) != 4:
        errs.append(f"el puente mide {len(bridge)} sobre el agua, no 4")
    if not regenerating:
        for c in rect(Z7_BOX):
            ids = existing.get((c[0], c[1], 7))
            if ids and ids[0] not in WATERS and ids[0] not in LAVA:
                errs.append(f"z7 {c}: no es agua ni vacío {ids}")
    for (x, y) in walk7:                  # nada de tierra ajena pegada a las islas
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n in rect(Z7_BOX):
                    continue
                ids = existing.get((n[0], n[1], 7), [])
                if ids and ids[0] not in WATERS and not any(i in solid for i in ids):
                    errs.append(f"{(x, y)} toca tierra caminable ajena {n} {ids}")
    if ISLET_HOLE not in islet:
        errs.append(f"la bajada {ISLET_HOLE} no está en el islote")
    arrive = (ISLET_HOLE[0], ISLET_HOLE[1] + 1)
    if arrive not in walk7:
        errs.append(f"al subir al islote se llega a {arrive}, que no es pasto libre")
    shore = existing.get((SHORE_HOLE[0], SHORE_HOLE[1], 7), [])
    up_shore = existing.get((SHORE_HOLE[0], SHORE_HOLE[1] + 1, 7), [])
    if not regenerating and shore != [GRASS]:
        errs.append(f"la bajada de la orilla {SHORE_HOLE} no es pasto libre {shore}")
    if not up_shore or any(i in solid for i in up_shore):
        errs.append(f"al subir a la orilla se llega a {SHORE_HOLE[0]},{SHORE_HOLE[1] + 1},7, que no es libre {up_shore}")
    # las hydras no salen: lo que recorren (sin pisar agujeros) queda adentro de la caja
    if not hydras:
        errs.append("no entró ninguna hydra")
    walk = walk7 - {ISLET_HOLE}
    start = hydras[0] if hydras else landing
    seen, todo = {start}, deque([start])
    while todo:
        x, y = todo.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n in walk and n not in seen:
                    seen.add(n)
                    todo.append(n)
    if arrive not in seen:
        errs.append("el puente no une la isla con el islote")
    if any(c not in rect(Z7_BOX) for c in seen):
        errs.append("las hydras pueden salir de las islas")
    for h in hydras:
        if h not in seen:
            errs.append(f"hydra {h} separada del resto")
    chk8 = roomkit.Checker(z8)
    walk8 = {(x, y) for (x, y, _z) in z8.t if chk8.walkable((x, y, 8))}
    if walk8 != TUNNEL:
        errs.append(f"el túnel no es de 1 de ancho / sobra piso: {sorted(walk8 ^ TUNNEL)[:5]}")
    for (x, y) in rect(Z8_BOX) - TUNNEL:
        want = NP.pieces_for(NP.neighbors_in(TUNNEL, x, y), NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER)
        if want is None or len(want) > 1:
            errs.append(f"pared z8 {(x, y)}: piezas {want}")
    near8 = {(x + dx, y + dy) for (x, y) in TUNNEL for dx in range(-4, 5) for dy in range(-4, 5)} - rect(Z8_BOX)
    for c in near8:                       # el túnel no se arrima a otra cueva (CAVE_SEPARATION)
        ids = existing.get((c[0], c[1], 8))
        if ids and ids[0] not in (ROCK,) and ids[0] not in LAVA:
            errs.append(f"z8 {c}: hay algo a menos de 4 del túnel {ids}")
    sign = [i for i in existing.get(SIGN, []) if i != roomkit.SIGN]
    if not sign or any(i in solid for i in sign):
        errs.append(f"el cartel {SIGN} no cae en suelo libre {sign}")
    known = set(re.findall(r'<monster name="([^"]+)"', MONSTERS.read_text(encoding="latin-1")))
    if HYDRA[0] not in known:
        errs.append(f"monstruo inexistente: {HYDRA[0]}")
    chk.tiles()
    chk8.tiles()
    errs += chk.errs + chk8.errs
    return errs


def preview(existing, maps, out: Path, z7_fill, z8_fill):
    out.mkdir(parents=True, exist_ok=True)
    for z, (x0, y0, x1, y1) in ((7, (24, 130, 76, 170)), (8, (36, 128, 64, 155))):
        m = roomkit.Map()
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                ids = existing.get((x, y, z))
                if z == 7 and (x, y) in z7_fill:
                    ids = [WATER]
                if z == 8 and (x, y) in z8_fill:
                    ids = [ROCK]
                if ids:
                    m.ground((x, y, z), ids[0])
                    for i in ids[1:]:
                        m.add((x, y, z), i)
        for src in maps[z]:
            for pos, t in src.t.items():
                m.t[pos] = {"ground": t["ground"], "items": list(t["items"]), "pz": False}
        roomkit.render_png(m, out / f"isla_z{z}.png", z)
    print(f"PNG en {out}")


def write_cells(path, cells_ids: dict, z, stackable):
    """Escribe casillas sueltas por filas (cada fila, una caja de 1 de alto con sus casillas contiguas)."""
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", type=Path, default=MAP)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview-dir", type=Path)
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()

    import mapdata
    mapdata.MAP = a.map
    existing = load_tiles()
    regenerating = MANIFEST.exists()
    z7, hole, walk7, bridge, entries, islet, isle, bad, landing = build_z7(existing)
    z8 = build_z8()
    hydras = hydra_spots(walk7, isle, landing)
    z7_fill, z8_fill = void_and_lava(existing, walk7)
    errs = validate(existing, z7, walk7, bridge, entries, islet, isle, bad, z8, landing, hydras, regenerating)
    print(f"Isla de las Dark Hydras: islote {len(islet)} casillas, isla {len(isle)} "
          f"(x{min(x for x, _ in isle)}-{max(x for x, _ in isle)}, y{min(y for _, y in isle)}-{max(y for _, y in isle)}), "
          f"puente x{BRIDGE_X} y{min(bridge)[1]}-{max(bridge)[1]}; túnel z8 de {len(TUNNEL)} casillas")
    print(f"  {len(hydras)} Dark Hydras: {hydras}")
    print(f"  vacío/lava a la vista -> mar en z7: {len(z7_fill)}; -> roca en z8: {len(z8_fill)}")
    if a.preview_dir:
        preview(existing, {7: [z7, hole], 8: [z8]}, a.preview_dir, z7_fill, z8_fill)
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs[:40]), file=sys.stderr)
        return 1
    if a.dry_run or not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    backup = Path(tempfile.gettempdir()) / f"hydra-isle-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a.map, backup / "test.otbm")
    shutil.copy2(SPAWNS, backup / "test-spawn.xml")
    print(f"backup: {backup}")

    stackable = roomkit.Checker(z7).stackable
    roomkit.write_map(a.map, z7, Z7_BOX, 7, stackable)
    roomkit.write_map(a.map, hole, (SHORE_HOLE[0], SHORE_HOLE[1], SHORE_HOLE[0], SHORE_HOLE[1]), 7, stackable)
    roomkit.write_map(a.map, z8, Z8_BOX, 8, stackable)
    if z7_fill:
        write_cells(a.map, {c: [WATER] for c in z7_fill}, 7, stackable)
    if z8_fill:
        write_cells(a.map, {c: [ROCK] for c in z8_fill}, 8, stackable)
    sign = roomkit.Map()
    old = existing.get(SIGN) or [GRASS]
    sign.ground(SIGN, old[0])
    for i in old[1:]:
        if i != roomkit.SIGN:
            sign.add(SIGN, i)
    sign.add(SIGN, roomkit.SIGN)
    roomkit.write_map(a.map, sign, (SIGN[0], SIGN[1], SIGN[0], SIGN[1]), 7, stackable)

    name, st = HYDRA
    lines = ["\t<!-- BEGIN DARK_HYDRA_ISLE_SPAWNS (scripts/map/generate-dark-hydra-isle.py) -->"]
    for x, y in hydras:
        lines += [f'\t<spawn centerx="{x}" centery="{y}" centerz="7" radius="1">',
                  f'\t\t<monster name="{name}" x="0" y="0" z="7" spawntime="{st}" />',
                  "\t</spawn>"]
    block = "\n".join(lines) + "\n\t<!-- END DARK_HYDRA_ISLE_SPAWNS -->\n"
    sp = SPAWNS.read_text(encoding="latin-1")
    old_re = re.compile(r"[ \t]*<!-- BEGIN DARK_HYDRA_ISLE_SPAWNS.*?<!-- END DARK_HYDRA_ISLE_SPAWNS -->\n?", re.S)
    sp = old_re.sub(lambda _m: block, sp, count=1) if old_re.search(sp) else sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")
    roomkit.patch_readables("<!-- BEGIN DARK_HYDRA_ISLE_SIGNS -->", "<!-- END DARK_HYDRA_ISLE_SIGNS -->", [
        dict(x=SIGN[0], y=SIGN[1], z=SIGN[2],
             text="ISLA DE LAS DARK HYDRAS\nBaja por el agujero y sigue el tunel hasta el islote.\n"
                  "Si te aprietan, baja por el agujero del islote y vuelve a subir."),
    ])
    MANIFEST.write_text(json.dumps({
        "name": "Isla de las Dark Hydras", "box": list(Z7_BOX), "islet": ISLET, "isle": ISLE,
        "bridge": [BRIDGE_X, min(bridge)[1], BRIDGE_X, max(bridge)[1]], "shore_hole": SHORE_HOLE,
        "islet_hole": ISLET_HOLE, "tunnel": sorted(TUNNEL), "z8_box": list(Z8_BOX),
        "void_or_lava_to_water_z7": len(z7_fill), "void_or_lava_to_rock_z8": len(z8_fill), "sign": list(SIGN),
        "monsters": [dict(name=name, pos=[x, y, 7], respawn=st) for x, y in hydras],
    }, indent=2) + "\n")
    print(f"OK {a.map}, test-spawn.xml, readables.xml y {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
