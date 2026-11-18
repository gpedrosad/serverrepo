#!/usr/bin/env python3
"""Torre del Mago Oscuro: torre de 6 pisos al sur de la city, en el claro entre el río y la roca.

Huella 9x9 en x120-128, y124-132 (interior 7x7 en x121-127, y125-131), z7 a z2. Paredes de piedra,
piso de mármol negro, dos braseros por piso y puerta al este (128,128,7), mirando al camino que baja
del puente de la city. Cada piso tiene magos más fuertes; arriba de todo está el Dark Mage:

  z7  Elf Arcanist x2, Dark Monk
  z6  Witch x2, Minotaur Mage
  z5  Ice Monk x2, Court Mage
  z4  Necromancer x2, Priestess
  z3  Warlock, Necromancer
  z2  Dark Mage

Escaleras (regla de docs/items-and-map/MAPEAR_TORRE_BARQUERO.md): en cada conexión la subida 1385 va
en el piso de abajo y la bajada 432 (el hueco) en el de arriba, misma x,y. Pisar la 1385 lleva a
x,y-1 del piso de arriba; pisar la 432 deja en x,y+1 del de abajo. La planta baja no tiene bajada.

La fila norte y la columna oeste de la pared llevan en z7 el suelo que ya había (pasto u orilla, con
sus bordes de agua) y van sin suelo en los pisos altos, para que la losa no sobresalga.

Uso:
  python3 scripts/map/generate-mage-tower.py --dry-run --preview-dir /tmp/torre-mago
  python3 scripts/map/generate-mage-tower.py --replace
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
MANIFEST = WORLD / "generated-mage-tower.json"

TOWER_BOX = (120, 124, 128, 132)            # 9x9 con paredes
ROOM = (121, 125, 7, 7)                      # interior x121-127, y125-131
FLOORS = (7, 6, 5, 4, 3, 2)
DOOR = (128, 128, 7)                         # pared este, al camino del puente
SIGN = (129, 127, 7)
STAIRS = {7: (126, 126), 6: (122, 126), 5: (126, 126), 4: (122, 126), 3: (126, 126)}
BRAZIERS = ((121, 131), (127, 131))
SPAWN_CENTER = (124, 129)
MONSTERS_BY_FLOOR = {                        # (nombre, x, y, respawn s)
    7: [("Elf Arcanist", 122, 129, 120), ("Elf Arcanist", 126, 130, 120), ("Dark Monk", 124, 128, 120)],
    6: [("Witch", 122, 129, 150), ("Witch", 126, 130, 150), ("Minotaur Mage", 124, 128, 150)],
    5: [("Ice Monk", 122, 129, 240), ("Ice Monk", 126, 130, 240), ("Court Mage", 124, 128, 240)],
    4: [("Necromancer", 122, 129, 300), ("Necromancer", 126, 130, 300), ("Priestess", 124, 128, 300)],
    3: [("Warlock", 124, 129, 600), ("Necromancer", 126, 130, 300)],
    2: [("Dark Mage", 124, 129, 900)],
}
FLOOR_ID = 407                               # mármol negro (el de la plaza del templo)
WOODEN_DOOR = 1220                           # puerta abierta de pared vertical (ver Torre del Barquero)
BRAZIER = 1486
STAIR_DOWN, STAIRS_UP = 432, 1385
GRASS = 4756
WATER = {4608, 4609, 4610, 4611, 4612, 4613, 4614, 4615, 4616, 4617, 4618, 4619, 4620, 4621, 4622,
         4623, 4624, 4625, 4664, 4665, 4666}
# Lo que puede haber en la huella antes de la torre: pasto, orilla y sus bordes, plantas sueltas.
ALLOWED_GROUNDS = {GRASS, 4526}
ALLOWED_ITEMS = set(range(4632, 4700)) | set(range(2700, 2790))   # bordes de agua, árboles y arbustos


def in_box(x, y, z) -> bool:
    b = TOWER_BOX
    return b[0] <= x <= b[2] and b[1] <= y <= b[3] and z in FLOORS


def floor_map(z: int) -> roomkit.Map:
    m = roomkit.Map()
    roomkit.build_room(m, roomkit.Room(ROOM[0], ROOM[1], ROOM[2], ROOM[3], z), FLOOR_ID, "stone")
    if z == 7:
        m.t[DOOR] = {"ground": FLOOR_ID, "items": [{"id": WOODEN_DOOR, "uid": None}], "pz": False}
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
    """Fila norte y columna oeste: en z7 el suelo que había (con sus bordes de agua), arriba sin suelo."""
    edge = {(x, TOWER_BOX[1]) for x in range(TOWER_BOX[0], TOWER_BOX[2] + 1)}
    edge |= {(TOWER_BOX[0], y) for y in range(TOWER_BOX[1], TOWER_BOX[3] + 1)}
    for x, y in edge:
        for z, m in maps.items():
            pos = (x, y, z)
            if z != 7:
                m.t[pos]["ground"] = None
                continue
            old = existing.get(pos) or [GRASS]
            ground = old[0] if old[0] not in WATER else GRASS
            borders = [{"id": i} for i in old[1:] if 4632 <= i < 4700]
            m.t[pos]["ground"] = ground
            m.t[pos]["items"] = borders + m.t[pos]["items"]


def build_sign(existing) -> roomkit.Map:
    m = roomkit.Map()
    m.ground(SIGN, (existing.get(SIGN) or [GRASS])[0])
    m.add(SIGN, roomkit.SIGN)
    return m


def spawn_xml() -> str:
    cx, cy = SPAWN_CENTER
    lines = []
    for z in FLOORS:
        lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="{z}" radius="3">')
        for name, x, y, st in MONSTERS_BY_FLOOR[z]:
            lines.append(f'\t\t<monster name="{name}" x="{x - cx}" y="{y - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def validate(existing, maps, regenerating: bool) -> list:
    errs = []
    chk7 = roomkit.Checker(maps[7])
    for line in HOUSES.read_text(encoding="latin-1").splitlines():
        m = re.search(r'<tile x="(\d+)" y="(\d+)" z="(\d+)"', line)
        if m and in_box(*map(int, m.groups())):
            errs.append(f"hay una casa en {m.groups()}")
    for m in re.finditer(r'<npc[^>]*x="(\d+)"[^>]*y="(\d+)"[^>]*z="(\d+)"', NPCS.read_text(encoding="latin-1")):
        if in_box(*map(int, m.groups())):
            errs.append(f"hay un NPC en {m.groups()}")
    if not regenerating:
        for (x, y, z), ids in existing.items():
            if not in_box(x, y, z):
                continue
            if z != 7:
                errs.append(f"{x},{y},{z}: el piso alto no está vacío {ids}")
                continue
            if ids[0] not in ALLOWED_GROUNDS and not (ids[0] in WATER and (x, y) == (x, TOWER_BOX[1])):
                errs.append(f"{x},{y},7: suelo inesperado {ids[0]}")
            bad = [i for i in ids[1:] if i not in ALLOWED_ITEMS]
            if bad:
                errs.append(f"{x},{y},7: item inesperado en la huella {bad}")
    out = existing.get((DOOR[0] + 1, DOOR[1], 7), [])
    if not out or any(i in chk7.solid for i in out):
        errs.append(f"la salida de la puerta {DOOR[0]+1},{DOOR[1]},7 no es caminable")
    sign_tile = existing.get(SIGN, [])
    if not sign_tile or any(i in chk7.solid for i in sign_tile):
        errs.append(f"el cartel {SIGN} no cae en pasto libre")
    interior = lambda z: {(x, y, z) for x in range(ROOM[0], ROOM[0] + ROOM[2])
                          for y in range(ROOM[1], ROOM[1] + ROOM[3])}
    for z, m in maps.items():
        chk = roomkit.Checker(m)
        walk = {p for p in m.t if chk.walkable(p)}
        start = (DOOR[0] - 1, DOOR[1], z)
        seen, todo = {start}, [start]
        while todo:
            x, y, _ = todo.pop()
            for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z)):
                if n in walk and n not in seen:
                    seen.add(n)
                    todo.append(n)
        lost = (interior(z) & walk) - seen
        if start not in walk or lost:
            errs.append(f"z{z}: interior cortado ({len(lost)} casillas aisladas)")
        if z == 7 and (DOOR not in walk):
            errs.append("la puerta no es caminable")
        if z in STAIRS:
            sx, sy = STAIRS[z]
            up = z - 1
            if not any(i["id"] == STAIRS_UP for i in m.t[(sx, sy, z)]["items"]):
                errs.append(f"z{z}: falta la subida 1385 en {sx},{sy}")
            if (sx, sy + 1, z) not in walk:
                errs.append(f"z{z}: llegada al bajar {sx},{sy+1} no caminable")
            if maps[up].t[(sx, sy, up)]["ground"] != STAIR_DOWN:
                errs.append(f"z{up}: falta la bajada 432 en {sx},{sy}")
            upc = roomkit.Checker(maps[up])
            if not upc.walkable((sx, sy - 1, up)):
                errs.append(f"z{up}: llegada al subir {sx},{sy-1} no caminable")
        for (x, y, _z), tile in m.t.items():
            if tile.get("ground") == STAIR_DOWN and STAIRS.get(z + 1) != (x, y):
                errs.append(f"z{z}: bajada 432 en {x},{y} sin subida debajo")
        stairs_here = {STAIRS.get(z), STAIRS.get(z + 1)} - {None}
        landings = {(sx, sy - 1) for sx, sy in stairs_here} | {(sx, sy + 1) for sx, sy in stairs_here}
        for name, x, y, _st in MONSTERS_BY_FLOOR[z]:
            if (x, y, z) not in walk or (x, y) in stairs_here or (x, y) in landings:
                errs.append(f"z{z}: spawn de {name} en {x},{y} no es piso libre")
    known = set(re.findall(r'<monster name="([^"]+)"', MONSTERS.read_text(encoding="latin-1")))
    for z, lst in MONSTERS_BY_FLOOR.items():
        for name, *_ in lst:
            if name not in known:
                errs.append(f"monstruo inexistente: {name}")
    return errs


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
    errs = validate(existing, maps, regenerating)
    print("Torre del Mago Oscuro: 6 pisos z7-z2, huella 9x9 en x120-128, y124-132")
    for z in FLOORS:
        print(f"  z{z}: " + ", ".join(n for n, *_ in MONSTERS_BY_FLOOR[z]))
    if a.preview_dir:
        a.preview_dir.mkdir(parents=True, exist_ok=True)
        for z, m in maps.items():
            roomkit.render_png(m, a.preview_dir / f"torre_z{z}.png", z)
        print(f"PNG en {a.preview_dir}")
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs[:40]), file=sys.stderr)
        return 1
    if a.dry_run or not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    backup = Path(tempfile.gettempdir()) / f"mage-tower-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a.map, backup / "test.otbm")
    shutil.copy2(SPAWNS, backup / "test-spawn.xml")
    print(f"backup: {backup}")

    stackable = roomkit.Checker(maps[7]).stackable
    for z, m in maps.items():
        roomkit.write_map(a.map, m, TOWER_BOX, z, stackable)
    roomkit.write_map(a.map, build_sign(existing), (SIGN[0], SIGN[1], SIGN[0], SIGN[1]), SIGN[2], stackable)

    sp = SPAWNS.read_text(encoding="latin-1")
    block = "\t<!-- BEGIN MAGE_TOWER_SPAWNS (scripts/map/generate-mage-tower.py) -->\n" + \
        spawn_xml() + "\n\t<!-- END MAGE_TOWER_SPAWNS -->\n"
    old = re.compile(r"[ \t]*<!-- BEGIN MAGE_TOWER_SPAWNS.*?<!-- END MAGE_TOWER_SPAWNS -->\n?", re.S)
    sp = old.sub(lambda _m: block, sp, count=1) if old.search(sp) else sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")

    roomkit.patch_readables("<!-- BEGIN MAGE_TOWER_SIGNS -->", "<!-- END MAGE_TOWER_SIGNS -->", [
        dict(x=SIGN[0], y=SIGN[1], z=SIGN[2],
             text="TORRE DEL MAGO OSCURO\n6 pisos de magos, cada uno mas fuerte.\n"
                  "Arriba de todo espera el Dark Mage."),
    ])

    MANIFEST.write_text(json.dumps({
        "name": "Torre del Mago Oscuro", "box": TOWER_BOX, "floors": list(FLOORS),
        "door": list(DOOR), "sign": list(SIGN), "stairs": {f"z{z}": list(p) for z, p in STAIRS.items()},
        "monsters": {f"z{z}": [dict(name=n, pos=[x, y, z], respawn=s) for n, x, y, s in lst]
                     for z, lst in MONSTERS_BY_FLOOR.items()},
    }, indent=2) + "\n")
    print(f"OK {a.map}, test-spawn.xml, readables.xml y {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
