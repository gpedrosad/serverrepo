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

HUNTER = (93, 85, 95, 87)                   # plataforma del cazador (caja)
BRIDGE = (89, 86, 92, 86)                   # 1 de ancho, 4 de largo
DRAGON = (86, 85, 88, 87)                   # plataforma del dragón
Z7_BOX = (86, 85, 95, 87)                   # todo lo de z7 sobre el agua (lo demás de la caja queda agua)
TRAPDOOR = (95, 85)                         # trampilla 427 en la plataforma del cazador
BANK_HOLE = (102, 85)                       # agujero 479 en la orilla de los elfos
TUNNEL = {(x, y) for x in range(95, 103) for y in (85, 86)}   # z8, 2 de ancho
SIGN = (103, 84, 7)
MONSTER = ("Black Dragon", 87, 86, 7, 300)  # nombre, x, y, z, respawn
WOOD, WATER, GRASS = 405, 4608, 4756
TRAPDOOR_ID, HOLE_ID, LADDER = 427, 479, 1386
ROCK = 101
VIEW = (8, 6)                               # media pantalla + 1


def rect(b):
    return {(x, y) for x in range(b[0], b[2] + 1) for y in range(b[1], b[3] + 1)}


def build_z7(existing):
    m = roomkit.Map()
    floor = rect(HUNTER) | rect(BRIDGE) | rect(DRAGON)
    for x, y in rect(Z7_BOX):
        m.ground((x, y, 7), WOOD if (x, y) in floor else WATER)
    m.t[(TRAPDOOR[0], TRAPDOOR[1], 7)]["ground"] = TRAPDOOR_ID
    hole = roomkit.Map()
    hole.ground((BANK_HOLE[0], BANK_HOLE[1], 7), HOLE_ID)
    return m, hole, floor


def build_z8(existing):
    """Túnel vestido como cueva; devuelve (mapa de la caja vestida, caja, casillas de relleno)."""
    box = NP_grow(TUNNEL, 2)
    tiles = NP.cave_tiles(TUNNEL, box, 7676)
    for x, y in (TRAPDOOR, BANK_HOLE):
        tiles[(x, y)] = [tiles[(x, y)][0], LADDER]
    m = roomkit.Map()
    for (x, y), ids in tiles.items():
        m.ground((x, y, 8), ids[0])
        for i in ids[1:]:
            m.add((x, y, 8), i)
    xs, ys = [c[0] for c in box], [c[1] for c in box]
    bbox = (min(xs), min(ys), max(xs), max(ys))
    fill = set()
    for x, y in TUNNEL:
        for dx in range(-VIEW[0], VIEW[0] + 1):
            for dy in range(-VIEW[1], VIEW[1] + 1):
                c = (x + dx, y + dy)
                if c not in box and (c[0], c[1], 8) not in existing:
                    fill.add(c)
    return m, bbox, fill


def NP_grow(cells, r):
    return {(x + dx, y + dy) for (x, y) in cells for dx in range(-r, r + 1) for dy in range(-r, r + 1)}


def validate(existing, z7, hole, floor, z8, z8box, regenerating) -> list:
    errs = []
    chk = roomkit.Checker(z7)
    solid = chk.solid
    if not regenerating:
        for c in rect(Z7_BOX):
            ids = existing.get((c[0], c[1], 7))
            if ids != [WATER]:
                errs.append(f"z7 {c}: no es agua sola {ids}")
        for x in range(z8box[0], z8box[2] + 1):
            for y in range(z8box[1], z8box[3] + 1):
                ids = existing.get((x, y, 8))
                if ids and any(i not in (ROCK, 598, 374) for i in ids):
                    errs.append(f"z8 {x},{y}: hay algo que no es roca/lava {ids}")
        bank = existing.get((BANK_HOLE[0], BANK_HOLE[1], 7))
        if bank != [GRASS]:
            errs.append(f"la orilla {BANK_HOLE} no es pasto libre {bank}")
    # llegadas al subir: (x, y+1) del piso de arriba, libres
    up_hunter = (TRAPDOOR[0], TRAPDOOR[1] + 1)
    if up_hunter not in floor or up_hunter == TRAPDOOR:
        errs.append(f"al subir a la plataforma se llega a {up_hunter}, que no es piso")
    up_bank = existing.get((BANK_HOLE[0], BANK_HOLE[1] + 1, 7), [])
    if not up_bank or any(i in solid for i in up_bank):
        errs.append(f"al subir a la orilla se llega a {BANK_HOLE[0]},{BANK_HOLE[1] + 1},7, que no es libre {up_bank}")
    # el dragón queda aislado: desde su plataforma, caminando por z7, no se llega a tierra
    walk7 = {c for c in floor if c != TRAPDOOR}
    seen, todo = {(MONSTER[1], MONSTER[2])}, deque([(MONSTER[1], MONSTER[2])])
    while todo:
        x, y = todo.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n in seen or n in rect(Z7_BOX):
                    if n in walk7 and n not in seen:
                        seen.add(n)
                        todo.append(n)
                    continue
                ids = existing.get((n[0], n[1], 7), [])
                if ids and not any(i in solid for i in ids):
                    errs.append(f"el dragón puede salir a {n} {ids}")
                    seen.add(n)
    if up_hunter not in seen:
        errs.append("el puente no une la plataforma del dragón con la del cazador")
    # túnel conectado de escalera a escalera
    chk8 = roomkit.Checker(z8)
    walk8 = {(x, y) for (x, y, _z) in z8.t if chk8.walkable((x, y, 8))}
    seen, todo = {BANK_HOLE}, deque([BANK_HOLE])
    while todo:
        x, y = todo.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n in walk8 and n not in seen:
                seen.add(n)
                todo.append(n)
    if TRAPDOOR not in seen:
        errs.append("el túnel no llega de la orilla a la escalera de la plataforma")
    for c in ((MONSTER[1], MONSTER[2]),):
        if c not in floor:
            errs.append(f"el dragón no está sobre la plataforma {c}")
    sign = existing.get(SIGN, [])
    if not sign or any(i in solid for i in sign):
        errs.append(f"el cartel {SIGN} no cae en suelo libre {sign}")
    known = set(re.findall(r'<monster name="([^"]+)"', MONSTERS.read_text(encoding="latin-1")))
    if MONSTER[0] not in known:
        errs.append(f"monstruo inexistente: {MONSTER[0]}")
    chk.tiles()
    chk8.tiles()
    errs += chk.errs + chk8.errs
    return errs


def preview(existing, z7, hole, z8, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    for z, src_maps, (x0, y0, x1, y1) in ((7, [z7, hole], (80, 78, 108, 94)), (8, [z8], (84, 78, 108, 94))):
        m = roomkit.Map()
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                ids = existing.get((x, y, z))
                if ids:
                    m.ground((x, y, z), ids[0])
                    for i in ids[1:]:
                        m.add((x, y, z), i)
        for src in src_maps:
            for pos, t in src.t.items():
                m.t[pos] = {"ground": t["ground"], "items": list(t["items"]), "pz": False}
        roomkit.render_png(m, out / f"spot_z{z}.png", z)
    print(f"PNG en {out}")


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
    z7, hole, floor = build_z7(existing)
    z8, z8box, fill = build_z8(existing)
    errs = validate(existing, z7, hole, floor, z8, z8box, regenerating)
    print(f"Spot del Dragón Negro: plataformas {HUNTER} y {DRAGON}, puente {BRIDGE}; túnel z8 {z8box}; "
          f"relleno de roca {len(fill)} casillas")
    if a.preview_dir:
        preview(existing, z7, hole, z8, a.preview_dir)
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
    roomkit.write_map(a.map, z8, z8box, 8, stackable)
    if fill:
        rock = roomkit.Map()
        for x, y in fill:
            rock.ground((x, y, 8), ROCK)
        xs, ys = [c[0] for c in fill], [c[1] for c in fill]
        # la caja del relleno puede tener casillas ya existentes: se vuelven a escribir tal cual
        for x in range(min(xs), max(xs) + 1):
            for y in range(min(ys), max(ys) + 1):
                if (x, y) in fill:
                    continue
                if z8box[0] <= x <= z8box[2] and z8box[1] <= y <= z8box[3]:
                    t = z8.t[(x, y, 8)]
                    rock.t[(x, y, 8)] = {"ground": t["ground"], "items": list(t["items"]), "pz": False}
                    continue
                ids = existing.get((x, y, 8))
                if ids:
                    rock.ground((x, y, 8), ids[0])
                    for i in ids[1:]:
                        rock.add((x, y, 8), i)
        roomkit.write_map(a.map, rock, (min(xs), min(ys), max(xs), max(ys)), 8, stackable)
    sign = roomkit.Map()
    old = existing.get(SIGN) or [GRASS]
    sign.ground(SIGN, old[0])
    for i in old[1:]:
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
                  "Si te aprieta, pisa la trampilla y vuelve a subir."),
    ])
    MANIFEST.write_text(json.dumps({
        "name": "Spot del Dragón Negro", "box": list(Z7_BOX), "hunter": HUNTER, "bridge": BRIDGE,
        "dragon": DRAGON, "trapdoor": TRAPDOOR, "bank_hole": BANK_HOLE, "z8_box": list(z8box),
        "rock_fill": len(fill), "sign": list(SIGN), "monster": dict(name=name, pos=[x, y, z], respawn=st),
    }, indent=2) + "\n")
    print(f"OK {a.map}, test-spawn.xml, readables.xml y {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
