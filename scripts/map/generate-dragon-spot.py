#!/usr/bin/env python3
"""Spot del Dragón Negro: un Black Dragon aislado en el lago al oeste del área de los elfos, que se caza
subiendo y bajando.

  z7  plataforma del cazador (madera 405, 3x3) x93-95, y85-87, centrada en 94,86, con trampilla 427 en 95,85
      puente de 1x4 (madera) x89-92, y86
      plataforma del dragón (madera, 3x3) x86-88, y85-87: Black Dragon en 87,86
      agujero 479 en la orilla de los elfos (102,85)
  z8  túnel de cueva (piso 351/352/355, paredes 356-367) bajo el agua, de 95,85 a 102,86, con escalera
      de mano 1386 debajo de la trampilla (95,85) y debajo del agujero (102,85)

Nada toca una orilla: el dragón no sale de las plataformas y el puente. El cazador baja por el agujero de
la orilla, camina el túnel y sube por la escalera a su plataforma (llega a 95,86); si lo aprietan, pisa la
trampilla (cae sobre la escalera, en z8, donde el dragón no llega), se cura y vuelve a subir.

Reglas (docs/items-and-map/PIEZAS_DE_MAPA.md): agujero/trampilla arriba y escalera de mano 1386 abajo en la
misma x,y; al bajar se cae sobre la escalera y al usarla se llega a (x, y+1) arriba. La escalera va sola.
Cueva con cave_tiles de generate-north-pass.py, techo (z7 encima del túnel) y nada de vacío a la vista
(relleno de roca 101 en la media pantalla de cada casilla del túnel).

Uso:
  python3.11 scripts/map/generate-dragon-spot.py --dry-run --preview-dir /tmp/dragon-spot
  python3.11 scripts/map/generate-dragon-spot.py --replace
Doc: docs/items-and-map/MAPEAR_SPOT_DRAGON.md
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
MANIFEST = WORLD / "generated-dragon-spot.json"

# Islas de pasto (elipses): centro, radio x, radio y. El anillo que toca el agua lleva borde de costa
# (4644-4655, no se pisa); el centro es pasto caminable.
HUNTER_ISLE = ((94.5, 85.5), 3.2, 2.9)      # la del cazador, sobre 94,86 (y83-88: hacia el norte hay agua)
DRAGON_ISLE = ((85.0, 87.5), 3.0, 2.2)      # la del dragón; empieza en y86 (y85 queda agua: la lava estaba en y84)
BRIDGE_Y = 87                               # el puente cruza por esta fila (1 de ancho, 4 de largo)
Z7_BOX = (82, 84, 98, 89)                   # se reescribe entera: islas, puente y el resto agua
HOLE = (96, 85)                             # bajada en la isla (agujero 469); al subir se llega a 96,86
BANK_HOLE = (102, 85)                       # bajada en la orilla de los elfos (469); al subir, 102,86
TUNNEL = {(x, 85) for x in range(96, 103)}                    # z8, 1 de ancho, recto de escalera a escalera
Z8_BOX = (93, 83, 104, 88)                  # se reescribe entera (incluye el túnel ancho de la v1)
SIGN = (103, 84, 7)
MONSTER = ("Black Dragon", 85, 88, 7, 300)  # nombre, x, y, z, respawn
WOOD, WATER, GRASS, SHORE = 405, 4608, 4756, 4526
HOLE_ID, LADDER = 469, 1386
ROCK = 101
LAVA = {598, 599, 600, 601}
VIEW = (9, 7)                               # lo que se ve en pantalla (regla del Islote del Minotauro)
COAST_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
COAST_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
COAST_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}


def rect(b):
    return {(x, y) for x in range(b[0], b[2] + 1) for y in range(b[1], b[3] + 1)}


def ellipse(spec):
    (cx, cy), rx, ry = spec
    return {(x, y) for x in range(int(cx - rx) - 1, int(cx + rx) + 2) for y in range(int(cy - ry) - 1, int(cy + ry) + 2)
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0}


def window(cells):
    return {(x + dx, y + dy) for (x, y) in cells for dx in range(-VIEW[0], VIEW[0] + 1) for dy in range(-VIEW[1], VIEW[1] + 1)}


def build_z7():
    hunter, dragon = ellipse(HUNTER_ISLE), ellipse(DRAGON_ISLE)
    land = hunter | dragon
    water0 = rect(Z7_BOX) - land
    ring = {c for c in land if NP.pieces_for(NP.neighbors_in(water0, *c), COAST_SIDE, COAST_CORNER, COAST_INNER)}
    inner = land - ring
    # el puente va del último pasto del dragón al primero del cazador en BRIDGE_Y: sobre el agua son los 4
    # de largo; las casillas de orilla que cruza (entries) también pasan a madera
    east = max(x for x, y in inner & dragon if y == BRIDGE_Y)
    west = min(x for x, y in inner & hunter if y == BRIDGE_Y)
    span = {(x, BRIDGE_Y) for x in range(east + 1, west)}
    bridge = span - land
    entries = span & land
    water = rect(Z7_BOX) - land - bridge
    m, walk, bad = roomkit.Map(), set(), []
    for c in rect(Z7_BOX):
        pos = (c[0], c[1], 7)
        if c in bridge or c in entries:
            m.ground(pos, WOOD)
            walk.add(c)
        elif c in land:
            pcs = NP.pieces_for(NP.neighbors_in(water, *c), COAST_SIDE, COAST_CORNER, COAST_INNER)
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
    m.t[(HOLE[0], HOLE[1], 7)] = {"ground": HOLE_ID, "items": [], "pz": False}
    hole = roomkit.Map()
    hole.ground((BANK_HOLE[0], BANK_HOLE[1], 7), HOLE_ID)
    return m, hole, walk, bridge, entries, hunter, dragon, bad


def build_z8():
    box = rect(Z8_BOX)
    tiles = NP.cave_tiles(TUNNEL, box, 7676)
    for x, y in (HOLE, BANK_HOLE):
        tiles[(x, y)] = [tiles[(x, y)][0], LADDER]
    m = roomkit.Map()
    for (x, y), ids in tiles.items():
        m.ground((x, y, 8), ids[0])
        for i in ids[1:]:
            m.add((x, y, 8), i)
    return m


def lava_and_void(existing, walk7):
    """z7: lava a la vista desde las islas/puente -> agua. z8: lava a la vista del túnel -> roca (también la del
    borde del pozo que se ve desde la sala de ladrillo del noroeste: el pozo queda 2 columnas más angosto);
    casillas vacías a la vista del túnel -> roca."""
    z7_lava = {c for c in window(walk7) - rect(Z7_BOX)
               if (existing.get((c[0], c[1], 7)) or [0])[0] in LAVA}
    z8_lava, z8_void = set(), set()
    for c in window(TUNNEL) - rect(Z8_BOX):
        ids = existing.get((c[0], c[1], 8))
        if not ids:
            z8_void.add(c)
        elif ids[0] in LAVA:
            z8_lava.add(c)
    return z7_lava, z8_lava, z8_void, set()


def validate(existing, z7, walk7, bridge, entries, hunter, dragon, bad, z8, z7_lava, z8_kept, regenerating) -> list:
    errs = []
    chk = roomkit.Checker(z7)
    solid = chk.solid
    if bad:
        errs.append(f"isla con casillas de 1 de ancho (sin pieza de costa): {bad[:5]}")
    if len(bridge) != 4:
        errs.append(f"el puente mide {len(bridge)}, no 4")
    if not regenerating:
        for c in rect(Z7_BOX):
            ids = existing.get((c[0], c[1], 7))
            if not ids or (ids[0] != WATER and ids[0] not in LAVA):
                errs.append(f"z7 {c}: no es agua ni lava {ids}")
    for (x, y) in rect(Z7_BOX):           # nada de tierra ajena pegada a las islas
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n in rect(Z7_BOX):
                    continue
                ids = existing.get((n[0], n[1], 7), [])
                if (x, y) in walk7 and ids and ids[0] not in LAVA and not any(i in solid for i in ids):
                    errs.append(f"{(x, y)} toca tierra caminable ajena {n} {ids}")
    for c in (HOLE,):
        if c not in hunter or c in bridge:
            errs.append(f"la bajada {c} no está en la isla del cazador")
    arrive = (HOLE[0], HOLE[1] + 1)
    if arrive not in walk7 or arrive == HOLE:
        errs.append(f"al subir a la isla se llega a {arrive}, que no es pasto libre")
    up_bank = existing.get((BANK_HOLE[0], BANK_HOLE[1] + 1, 7), [])
    if not up_bank or any(i in solid for i in up_bank):
        errs.append(f"al subir a la orilla se llega a {BANK_HOLE[0]},{BANK_HOLE[1] + 1},7, que no es libre {up_bank}")
    if (MONSTER[1], MONSTER[2]) not in walk7 or (MONSTER[1], MONSTER[2]) not in dragon:
        errs.append(f"el dragón no queda sobre su isla {MONSTER[1:3]}")
    walk = walk7 - {HOLE}
    seen, todo = {(MONSTER[1], MONSTER[2])}, deque([(MONSTER[1], MONSTER[2])])
    while todo:
        x, y = todo.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n in walk and n not in seen:
                    seen.add(n)
                    todo.append(n)
    if arrive not in seen:
        errs.append("el puente no une la isla del dragón con la del cazador")
    if any(c not in rect(Z7_BOX) for c in seen):
        errs.append("el dragón puede salir de las islas")
    chk8 = roomkit.Checker(z8)
    walk8 = {(x, y) for (x, y, _z) in z8.t if chk8.walkable((x, y, 8))}
    if walk8 != TUNNEL:
        errs.append(f"el túnel no es de 1 de ancho / sobra piso: {sorted(walk8 ^ TUNNEL)[:5]}")
    seen, todo = {BANK_HOLE}, deque([BANK_HOLE])
    while todo:
        x, y = todo.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n in walk8 and n not in seen:
                seen.add(n)
                todo.append(n)
    if HOLE not in seen:
        errs.append("el túnel no llega de una escalera a la otra")
    sign = [i for i in existing.get(SIGN, []) if i != roomkit.SIGN]      # el cartel propio no cuenta
    if not sign or any(i in solid for i in sign):
        errs.append(f"el cartel {SIGN} no cae en suelo libre {sign}")
    known = set(re.findall(r'<monster name="([^"]+)"', MONSTERS.read_text(encoding="latin-1")))
    if MONSTER[0] not in known:
        errs.append(f"monstruo inexistente: {MONSTER[0]}")
    chk.tiles()
    chk8.tiles()
    errs += chk.errs + chk8.errs
    return errs


def preview(existing, maps, out: Path, z7_lava, z8_lava, z8_void):
    out.mkdir(parents=True, exist_ok=True)
    for z, (x0, y0, x1, y1) in ((7, (78, 76, 108, 96)), (8, (82, 77, 110, 95))):
        m = roomkit.Map()
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                ids = existing.get((x, y, z))
                if (x, y) in (z7_lava if z == 7 else set()):
                    ids = [WATER]
                if z == 8 and ((x, y) in z8_lava or (x, y) in z8_void):
                    ids = [ROCK]
                if ids:
                    m.ground((x, y, z), ids[0])
                    for i in ids[1:]:
                        m.add((x, y, z), i)
        for src in maps[z]:
            for pos, t in src.t.items():
                m.t[pos] = {"ground": t["ground"], "items": list(t["items"]), "pz": False}
        roomkit.render_png(m, out / f"spot_z{z}.png", z)
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
    z7, hole, walk7, bridge, entries, hunter, dragon, bad = build_z7()
    z8 = build_z8()
    z7_lava, z8_lava, z8_void, z8_kept = lava_and_void(existing, walk7)
    errs = validate(existing, z7, walk7, bridge, entries, hunter, dragon, bad, z8, z7_lava, z8_kept, regenerating)
    print(f"Spot del Dragón Negro: isla del cazador {len(hunter)} casillas, del dragón {len(dragon)}, puente "
          f"{min(bridge)[0]}-{max(bridge)[0]},{BRIDGE_Y}; túnel z8 de {len(TUNNEL)} casillas (1 de ancho)")
    print(f"  lava a la vista -> agua en z7: {len(z7_lava)}; -> roca en z8: {len(z8_lava)} "
          f"; vacío z8 -> roca: {len(z8_void)}")
    if a.preview_dir:
        preview(existing, {7: [z7, hole], 8: [z8]}, a.preview_dir, z7_lava, z8_lava, z8_void)
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs[:40]), file=sys.stderr)
        return 1
    if a.dry_run or not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    backup = Path(tempfile.gettempdir()) / f"dragon-spot-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a.map, backup / "test.otbm")
    shutil.copy2(SPAWNS, backup / "test-spawn.xml")
    print(f"backup: {backup}")

    stackable = roomkit.Checker(z7).stackable
    roomkit.write_map(a.map, z7, Z7_BOX, 7, stackable)
    roomkit.write_map(a.map, hole, (BANK_HOLE[0], BANK_HOLE[1], BANK_HOLE[0], BANK_HOLE[1]), 7, stackable)
    roomkit.write_map(a.map, z8, Z8_BOX, 8, stackable)
    if z7_lava:
        write_cells(a.map, {c: [WATER] for c in z7_lava}, 7, stackable)
    if z8_lava | z8_void:
        write_cells(a.map, {c: [ROCK] for c in z8_lava | z8_void}, 8, stackable)
    sign = roomkit.Map()
    old = existing.get(SIGN) or [GRASS]
    sign.ground(SIGN, old[0])
    for i in old[1:]:
        if i != roomkit.SIGN:
            sign.add(SIGN, i)
    sign.add(SIGN, roomkit.SIGN)
    roomkit.write_map(a.map, sign, (SIGN[0], SIGN[1], SIGN[0], SIGN[1]), 7, stackable)

    name, x, y, z, st = MONSTER
    sp = SPAWNS.read_text(encoding="latin-1")
    block = ("\t<!-- BEGIN DRAGON_SPOT_SPAWNS (scripts/map/generate-dragon-spot.py) -->\n"
             f'\t<spawn centerx="{x}" centery="{y}" centerz="{z}" radius="1">\n'
             f'\t\t<monster name="{name}" x="0" y="0" z="{z}" spawntime="{st}" />\n'
             "\t</spawn>\n\t<!-- END DRAGON_SPOT_SPAWNS -->\n")
    old_re = re.compile(r"[ \t]*<!-- BEGIN DRAGON_SPOT_SPAWNS.*?<!-- END DRAGON_SPOT_SPAWNS -->\n?", re.S)
    sp = old_re.sub(lambda _m: block, sp, count=1) if old_re.search(sp) else sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")
    roomkit.patch_readables("<!-- BEGIN DRAGON_SPOT_SIGNS -->", "<!-- END DRAGON_SPOT_SIGNS -->", [
        dict(x=SIGN[0], y=SIGN[1], z=SIGN[2],
             text="SPOT DEL DRAGON NEGRO\nBaja por el agujero y sigue el tunel.\n"
                  "Si te aprieta, baja por el agujero de la isla y vuelve a subir."),
    ])
    MANIFEST.write_text(json.dumps({
        "name": "Spot del Dragón Negro", "box": list(Z7_BOX), "hunter_isle": HUNTER_ISLE, "dragon_isle": DRAGON_ISLE,
        "bridge": [min(bridge)[0], BRIDGE_Y, max(bridge)[0], BRIDGE_Y], "hole": HOLE, "bank_hole": BANK_HOLE,
        "tunnel": sorted(TUNNEL), "z8_box": list(Z8_BOX), "lava_to_water_z7": len(z7_lava),
        "lava_to_rock_z8": len(z8_lava), "void_to_rock_z8": len(z8_void), "sign": list(SIGN),
        "monster": dict(name=name, pos=[x, y, z], respawn=st),
    }, indent=2) + "\n")
    print(f"OK {a.map}, test-spawn.xml, readables.xml y {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
