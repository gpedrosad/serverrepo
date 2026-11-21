#!/usr/bin/env python3
"""Torre del Puente y puentes del canal: une el Islote del Minotauro con la isla del Castillo Imperial
y la isla con una torre de monstruos de río parada en medio del río.

Recorrido a pie: ciudad -> muelle -> Islote del Minotauro -> puente del canal -> isla del Castillo ->
puente del río -> Torre del Puente.

- Puente Castillo <-> Islote del Minotauro (madera 405): x103-104, y48-50, sobre la única fila de
  agua (49) que separa la isla del Castillo del islote. Entra una casilla en cada orilla, como el
  puente del islote al muelle.
- Puente del río (madera 405): x113-116, y46-47, desde la orilla este de la isla del Castillo hasta
  el portón de la torre.
- Torre del Puente: torre de piedra en medio del río, en la junta con el brazo oeste. Huella 8x7
  en x117-124, y42-48 (interior x118-123, y43-47), z7 a z2, portón al oeste (117,46-47). Monstruos de
  río cada vez más fuertes: piratas abajo, quaras y ahogados en el medio, un Quara Predator arriba.
  No tiene salida al este: del otro lado del río están las paredes traseras de las tiendas (x126) y
  la orilla 4526 no se pisa.

Por qué acá (nov 2026): z6 del río en y37-41 es el puente del Castillo (no se toca); de y42 al sur
los pisos altos están vacíos. La caja del islote (x97-120, y49-58) y los Mini Trainer Monk
(122-125, 55-57) quedan afuera; la torre empieza en x117 porque en 116,44 hay un spawn de Imperial
Squire del Castillo.

Escaleras (regla de MAPEAR_TORRE_BARQUERO.md): subida 1385 en el piso de abajo y bajada 432 en el
de arriba, misma x,y; la 1385 lleva a x,y-1 arriba y la 432 deja en x,y+1 abajo.

Uso:
  python3.11 scripts/map/generate-bridge-tower.py --dry-run --preview-dir /tmp/torre-puente
  python3.11 scripts/map/generate-bridge-tower.py --replace
Doc: docs/items-and-map/MAPEAR_TORRE_PUENTE.md
"""
from __future__ import annotations

import argparse
import json
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

WORLD = REPO / "server/YurOTS/ots/data/world"
MAP = WORLD / "test.otbm"
SPAWNS = WORLD / "test-spawn.xml"
MONSTERS = REPO / "server/YurOTS/ots/data/monster/monsters.xml"
HOUSES = REPO / "server/YurOTS/ots/data/houses.xml"
NPCS = WORLD / "npc.xml"
MANIFEST = WORLD / "generated-bridge-tower.json"

TOWER_BOX = (117, 42, 124, 48)              # 8x7 con paredes
ROOM = (118, 43, 6, 5)                       # interior x118-123, y43-47
FLOORS = (7, 6, 5, 4, 3, 2)
GATES = [(117, 46), (117, 47)]                          # portón oeste (z7), a la isla del Castillo
STAIRS = {7: (122, 44), 6: (119, 44), 5: (122, 44), 4: (119, 44), 3: (122, 44)}
BRAZIERS = ((118, 43), (123, 43))
SIGN = (112, 45, 7)                          # en la isla, al lado de la punta del puente
SPAWN_CENTER = (120, 45)
MONSTERS_BY_FLOOR = {                        # (nombre, x, y, respawn s)
    7: [("Pirate Marauder", 123, 47, 120), ("Pirate Marauder", 120, 43, 120), ("Blood Crab", 121, 47, 120)],
    6: [("Pirate Cutthroat", 118, 47, 150), ("Pirate Buccaneer", 123, 47, 150), ("Quara Constrictor", 120, 45, 150)],
    5: [("Drowned Sailor", 118, 47, 200), ("Drowned Sailor", 123, 47, 200), ("Pirate Corsair", 120, 45, 200)],
    4: [("Quara Mantassin", 118, 47, 300), ("Water Elemental", 123, 47, 300), ("Tide Priest", 120, 45, 300)],
    3: [("Quara Hydromancer", 118, 47, 400), ("Bog Raider", 123, 47, 400)],
    2: [("Quara Pincher", 118, 47, 450), ("Quara Predator", 121, 45, 900)],
}
# Puentes afuera de la torre (todas las casillas de cada caja pasan a madera)
BRIDGES = {
    "puente del rio": (113, 46, 116, 47),
    "castillo-islote": (103, 48, 104, 50),
}
# Llegadas de cada puente (tienen que ser caminables)
LANDINGS = {
    "puente del rio": [(112, 46), (112, 47)],
    "castillo-islote": [(103, 47), (104, 47), (103, 51), (104, 51)],
}
# Monstruos ajenos: ninguno adentro de la torre ni de los puentes; el del canal, además, lejos (regla
# del islote: nada a menos de 3 casillas de un puente). El Imperial Squire de 116,44 queda afuera.
SPAWN_MARGIN = {"torre": 0, "puente del rio": 0, "castillo-islote": 2, "cartel": 0}
WOOD = 405                                   # piso de madera (el del puente del islote)
GATE = 1220                                  # puerta abierta de pared vertical (Torre del Barquero)
BRAZIER = 1486
STAIR_DOWN, STAIRS_UP = 432, 1385
GRASS, SHORE = 4756, 4526
WATER = {4608, 4609, 4610, 4611, 4612, 4613, 4614, 4615, 4616, 4617, 4618, 4619, 4620, 4621, 4622,
         4623, 4624, 4625, 4664, 4665, 4666}
COAST = set(range(4632, 4700))
ALLOWED_GROUNDS = {GRASS, SHORE} | WATER
ALLOWED_ITEMS = COAST | set(range(2700, 2790)) | {4150, 4158}     # bordes, árboles, arbustos, flores


def in_box(x, y, z, b=TOWER_BOX, zs=FLOORS) -> bool:
    return b[0] <= x <= b[2] and b[1] <= y <= b[3] and z in zs


def floor_map(z: int) -> roomkit.Map:
    m = roomkit.Map()
    roomkit.build_room(m, roomkit.Room(ROOM[0], ROOM[1], ROOM[2], ROOM[3], z), WOOD, "stone")
    if z == 7:
        for x, y in GATES:
            m.t[(x, y, z)] = {"ground": WOOD, "items": [{"id": GATE}], "pz": False}
    for x, y in BRAZIERS:
        m.add((x, y, z), BRAZIER)
    return m


def build_floors():
    maps = {z: floor_map(z) for z in FLOORS}
    for lower_z, (x, y) in STAIRS.items():
        maps[lower_z].add((x, y, lower_z), STAIRS_UP)
        maps[lower_z - 1].floor((x, y, lower_z - 1), STAIR_DOWN)
    return maps


def fix_wall_grounds(maps, existing):
    """Fila norte y columna oeste: en z7 el suelo que había (el agua o la orilla, con sus bordes), arriba
    sin suelo, para que la losa de los pisos altos no sobresalga (como la Torre del Mago)."""
    edge = {(x, TOWER_BOX[1]) for x in range(TOWER_BOX[0], TOWER_BOX[2] + 1)}
    edge |= {(TOWER_BOX[0], y) for y in range(TOWER_BOX[1], TOWER_BOX[3] + 1)}
    for x, y in edge:
        if (x, y) in GATES:
            continue
        for z, m in maps.items():
            pos = (x, y, z)
            if z != 7:
                m.t[pos]["ground"] = None
                continue
            old = existing.get(pos) or [WATER and 4608]
            m.t[pos]["ground"] = old[0]
            m.t[pos]["items"] = [{"id": i} for i in old[1:] if i in COAST] + m.t[pos]["items"]


def bridge_maps():
    out = {}
    for name, (x0, y0, x1, y1) in BRIDGES.items():
        m = roomkit.Map()
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                m.ground((x, y, 7), WOOD)
        out[name] = m
    return out


def build_sign(existing) -> roomkit.Map:
    m = roomkit.Map()
    old = existing.get(SIGN) or [GRASS]
    m.ground(SIGN, old[0])
    for i in old[1:]:
        m.add(SIGN, i)
    m.add(SIGN, roomkit.SIGN)
    return m


def spawn_xml() -> str:
    cx, cy = SPAWN_CENTER
    lines = []
    for z in FLOORS:
        if not MONSTERS_BY_FLOOR[z]:
            continue
        lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="{z}" radius="3">')
        for name, x, y, st in MONSTERS_BY_FLOOR[z]:
            lines.append(f'\t\t<monster name="{name}" x="{x - cx}" y="{y - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def spawn_centers_near(box, margin):
    """Spawns ajenos (fuera de este bloque) a menos de `margin` casillas de la caja, en z7."""
    sp = re.sub(r"<!-- BEGIN BRIDGE_TOWER_SPAWNS.*?<!-- END BRIDGE_TOWER_SPAWNS -->", "",
                SPAWNS.read_text(encoding="latin-1"), flags=re.S)
    hits = []
    for m in re.finditer(r'<spawn centerx="(\d+)" centery="(\d+)" centerz="7"[^>]*>(.*?)</spawn>', sp, re.S):
        cx, cy = int(m.group(1)), int(m.group(2))
        for name, dx, dy in re.findall(r'name="([^"]+)" x="(-?\d+)" y="(-?\d+)"', m.group(3)):
            x, y = cx + int(dx), cy + int(dy)
            if box[0] - margin <= x <= box[2] + margin and box[1] - margin <= y <= box[3] + margin:
                hits.append((name, x, y))
    return hits


def validate(existing, maps, bridges, regenerating: bool) -> list:
    errs = []
    chk7 = roomkit.Checker(maps[7])
    houses = HOUSES.read_text(encoding="latin-1")
    npcs = NPCS.read_text(encoding="latin-1")
    boxes = [("torre", TOWER_BOX, FLOORS)] + [(n, b, (7,)) for n, b in BRIDGES.items()] + \
            [("cartel", (SIGN[0], SIGN[1], SIGN[0], SIGN[1]), (7,))]
    for label, b, zs in boxes:
        for m in re.finditer(r'<tile x="(\d+)" y="(\d+)" z="(\d+)"', houses):
            if in_box(*map(int, m.groups()), b, zs):
                errs.append(f"{label}: hay una casa en {m.groups()}")
        for m in re.finditer(r'<npc[^>]*x="(\d+)"[^>]*y="(\d+)"[^>]*z="(\d+)"', npcs):
            if in_box(*map(int, m.groups()), b, zs):
                errs.append(f"{label}: hay un NPC en {m.groups()}")
        for name, x, y in spawn_centers_near(b, SPAWN_MARGIN[label]):
            errs.append(f"{label}: monstruo ajeno a menos de 3 casillas ({name} en {x},{y})")
    if not regenerating:
        for label, b, zs in boxes[:-1]:
            for (x, y, z), ids in existing.items():
                if not in_box(x, y, z, b, zs):
                    continue
                if z != 7:
                    errs.append(f"{label} {x},{y},{z}: el piso alto no está vacío {ids}")
                    continue
                if ids[0] not in ALLOWED_GROUNDS:
                    errs.append(f"{label} {x},{y},7: suelo inesperado {ids[0]}")
                bad = [i for i in ids[1:] if i not in ALLOWED_ITEMS]
                if bad:
                    errs.append(f"{label} {x},{y},7: ítem inesperado {bad}")
    # llegadas de los puentes y del cartel
    for label, pts in LANDINGS.items():
        for x, y in pts:
            ids = existing.get((x, y, 7), [])
            if not ids or ids[0] in WATER or any(i in chk7.solid for i in ids):
                errs.append(f"{label}: la llegada {x},{y},7 no es caminable {ids}")
    sign_tile = existing.get(SIGN, [])
    if not sign_tile or sign_tile[0] in WATER or any(i in chk7.solid for i in sign_tile):
        errs.append(f"el cartel {SIGN} no cae en suelo libre")
    # cada piso conectado; en z7 de portón a portón
    for z, m in maps.items():
        chk = roomkit.Checker(m)
        chk.tiles()
        errs += [f"z{z}: {e}" for e in chk.errs]
        walk = {p for p in m.t if chk.walkable(p)}
        start = (ROOM[0], ROOM[1] + ROOM[3] - 1, z)
        seen, todo = {start}, [start]
        while todo:
            x, y, _ = todo.pop()
            for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z)):
                if n in walk and n not in seen:
                    seen.add(n)
                    todo.append(n)
        interior = {(x, y, z) for x in range(ROOM[0], ROOM[0] + ROOM[2]) for y in range(ROOM[1], ROOM[1] + ROOM[3])}
        lost = (interior & walk) - seen
        if start not in walk or lost:
            errs.append(f"z{z}: interior cortado ({len(lost)} casillas aisladas)")
        if z == 7:
            for x, y in GATES:
                if (x, y, 7) not in seen:
                    errs.append(f"z7: el portón {x},{y} no se alcanza")
        if z in STAIRS:
            sx, sy = STAIRS[z]
            up = z - 1
            if not any(i["id"] == STAIRS_UP for i in m.t[(sx, sy, z)]["items"]):
                errs.append(f"z{z}: falta la subida 1385 en {sx},{sy}")
            if (sx, sy + 1, z) not in walk:
                errs.append(f"z{z}: llegada al bajar {sx},{sy+1} no caminable")
            if maps[up].t[(sx, sy, up)]["ground"] != STAIR_DOWN:
                errs.append(f"z{up}: falta la bajada 432 en {sx},{sy}")
            if not roomkit.Checker(maps[up]).walkable((sx, sy - 1, up)):
                errs.append(f"z{up}: llegada al subir {sx},{sy-1} no caminable")
        for (x, y, _z), tile in m.t.items():
            if tile.get("ground") == STAIR_DOWN and STAIRS.get(z + 1) != (x, y):
                errs.append(f"z{z}: bajada 432 en {x},{y} sin subida debajo")
        stairs_here = {STAIRS.get(z), STAIRS.get(z + 1)} - {None}
        landings = {(sx, sy - 1) for sx, sy in stairs_here} | {(sx, sy + 1) for sx, sy in stairs_here}
        for name, x, y, _st in MONSTERS_BY_FLOOR[z]:
            if (x, y, z) not in walk or (x, y) in stairs_here or (x, y) in landings or (x, y) in BRAZIERS:
                errs.append(f"z{z}: spawn de {name} en {x},{y} no es piso libre")
    for name, m in bridges.items():
        chk = roomkit.Checker(m)
        if not all(chk.walkable(p) for p in m.t):
            errs.append(f"{name}: el puente tiene casillas no caminables")
    known = set(re.findall(r'<monster name="([^"]+)"', MONSTERS.read_text(encoding="latin-1")))
    for z, lst in MONSTERS_BY_FLOOR.items():
        for name, *_ in lst:
            if name not in known:
                errs.append(f"monstruo inexistente: {name}")
    return errs


def preview(existing, maps, bridges, out: Path):
    """PNG de z7 alrededor (torre + puentes sobre el mapa real) y de cada piso de la torre."""
    out.mkdir(parents=True, exist_ok=True)
    m = roomkit.Map()
    for x in range(98, 131):
        for y in range(38, 58):
            ids = existing.get((x, y, 7))
            if ids:
                m.ground((x, y, 7), ids[0])
                for i in ids[1:]:
                    m.add((x, y, 7), i)
    for src in [maps[7]] + list(bridges.values()):
        for pos, t in src.t.items():
            m.t[pos] = {"ground": t["ground"], "items": list(t["items"]), "pz": False}
    roomkit.render_png(m, out / "zona_z7.png", 7)
    for z, fm in maps.items():
        roomkit.render_png(fm, out / f"torre_z{z}.png", z)
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
    maps = build_floors()
    fix_wall_grounds(maps, existing)
    bridges = bridge_maps()
    errs = validate(existing, maps, bridges, regenerating)
    print("Torre del Puente: 6 pisos z7-z2, huella 8x7 en x117-124, y42-48, portón al oeste")
    for z in FLOORS:
        print(f"  z{z}: " + (", ".join(n for n, *_ in MONSTERS_BY_FLOOR[z]) or "paso, sin monstruos"))
    print("Puentes: " + ", ".join(f"{n} {b}" for n, b in BRIDGES.items()))
    if a.preview_dir:
        preview(existing, maps, bridges, a.preview_dir)
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs[:40]), file=sys.stderr)
        return 1
    if a.dry_run or not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    backup = Path(tempfile.gettempdir()) / f"bridge-tower-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a.map, backup / "test.otbm")
    shutil.copy2(SPAWNS, backup / "test-spawn.xml")
    print(f"backup: {backup}")

    stackable = roomkit.Checker(maps[7]).stackable
    for z, m in maps.items():
        roomkit.write_map(a.map, m, TOWER_BOX, z, stackable)
    for name, m in bridges.items():
        roomkit.write_map(a.map, m, BRIDGES[name], 7, stackable)
    roomkit.write_map(a.map, build_sign(existing), (SIGN[0], SIGN[1], SIGN[0], SIGN[1]), SIGN[2], stackable)

    sp = SPAWNS.read_text(encoding="latin-1")
    block = "\t<!-- BEGIN BRIDGE_TOWER_SPAWNS (scripts/map/generate-bridge-tower.py) -->\n" + \
        spawn_xml() + "\n\t<!-- END BRIDGE_TOWER_SPAWNS -->\n"
    old = re.compile(r"[ \t]*<!-- BEGIN BRIDGE_TOWER_SPAWNS.*?<!-- END BRIDGE_TOWER_SPAWNS -->\n?", re.S)
    sp = old.sub(lambda _m: block, sp, count=1) if old.search(sp) else sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")

    roomkit.patch_readables("<!-- BEGIN BRIDGE_TOWER_SIGNS -->", "<!-- END BRIDGE_TOWER_SIGNS -->", [
        dict(x=SIGN[0], y=SIGN[1], z=SIGN[2],
             text='BRIDGE TOWER\n6 floors in the middle of the river.\nPirates below, Quaras and Drowned creatures above,\neach floor stronger than the last.'),
    ])

    MANIFEST.write_text(json.dumps({
        "name": "Torre del Puente", "box": TOWER_BOX, "floors": list(FLOORS), "gates": GATES,
        "sign": list(SIGN), "stairs": {f"z{z}": list(p) for z, p in STAIRS.items()},
        "bridges": {n: list(b) for n, b in BRIDGES.items()},
        "monsters": {f"z{z}": [dict(name=n, pos=[x, y, z], respawn=s) for n, x, y, s in lst]
                     for z, lst in MONSTERS_BY_FLOOR.items()},
    }, indent=2) + "\n")
    print(f"OK {a.map}, test-spawn.xml, readables.xml y {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
