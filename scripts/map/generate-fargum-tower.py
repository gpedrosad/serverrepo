#!/usr/bin/env python3
"""Torre del Barquero: reemplaza el patio de mesas de Fargum por una torre de 5 pisos.

El patio está al lado del bote de Fargum, en la orilla este del río:
  z7  patio de mesas (se saca)  x174-180, y61-67
  z6  techo de madera del patio  (se reemplaza por el piso 2)
  z5  libre
  z4  libre
  z3  libre

La torre ocupa la misma huella 7x7, con interior 5x5 y paredes de piedra. Tiene 5 pisos
(z7 a z3), una escalera entre cada piso y un monstruo por piso, de menor a mayor:

  z7  Tortoise
  z6  Thornback Tortoise
  z5  Blood Crab
  z4  Quara Constrictor
  z3  Quara Predator

Escaleras: en cada conexión la subida 1385 va en el piso de abajo y la bajada 432 (el hueco) en el
de arriba, en la misma x,y. Pisar la 1385 lleva a x,y-1 del piso de arriba; pisar la 432 lleva al
piso de abajo y deja al sur de la 1385. Hasta el 16 nov 2026 estaban al revés: la planta baja tenía
una bajada a la cueva de z8 (178,63), donde uno quedaba encerrado, y ningún piso subía.

El bote (171,62-66) y Fargum (172,66) quedan afuera. La torre no toca el dungeon de la city
(z8, Smuggler's Den) ni el techo de la casa del norte.

Uso:
  python3 scripts/map/generate-fargum-tower.py --dry-run --preview-dir /tmp/torre
  python3 scripts/map/generate-fargum-tower.py --replace
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "kb"))
import roomkit  # noqa: E402
from mapdata import REPO, load_otb, load_tiles  # noqa: E402

WORLD = REPO / "server/YurOTS/ots/data/world"
MAP = WORLD / "test.otbm"
SPAWNS = WORLD / "test-spawn.xml"
MONSTERS = REPO / "server/YurOTS/ots/data/monster/monsters.xml"
HOUSES = REPO / "server/YurOTS/ots/data/houses.xml"
NPCS = WORLD / "npc.xml"
MANIFEST = WORLD / "generated-fargum-tower.json"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"

Z_BOTTOM, Z_TOP = 7, 3
TOWER_BOX = (174, 61, 180, 67)              # 7x7; el interior es x175-179, y62-66
ROOM = (175, 62, 5, 5)
DOOR = (174, 64, 7)
SIGN = (173, 63, 7)
FLOORS = (7, 6, 5, 4, 3)
STAIRS = {7: (178, 63), 6: (175, 63), 5: (178, 63), 4: (175, 63)}  # piso -> su subida al de arriba
MONSTERS_BY_FLOOR = {
    7: ("Tortoise", 120),
    6: ("Thornback Tortoise", 180),
    5: ("Blood Crab", 240),
    4: ("Quara Constrictor", 300),
    3: ("Quara Predator", 600),
}
SPAWN = (176, 66)                            # interior, lejos de puerta, escaleras y fogata
CAMPFIRE = (179, 66)
WOODEN_DOOR = 1220  # puerta abierta para pared vertical (la 1215 es horizontal y dejaba mal el marco)
CAMPFIRE_ID = 1423
STAIR_DOWN, STAIRS_UP = 432, 1385
TABLE_IDS = {1622, 1623, 1627, 1628, 1629, 1630, 1631, 1637}
OLD_FLOOR_Z6 = {945, 947, 949, 950, 954, 955, 959, 960, 964}
OLD_FRAME = {1036, 1037, 1038, 1039, 1040, 1041, 1042, 1043, 1044, 1263, 1264}


def floor_map(z: int) -> roomkit.Map:
    m = roomkit.Map()
    room = roomkit.Room(ROOM[0], ROOM[1], ROOM[2], ROOM[3], z)
    roomkit.build_room(m, room, 431, "stone")
    if z == 7:
        # Puerta oeste, frente al bote/Fargum.
        m.t[DOOR] = {"ground": 431, "items": [{"id": WOODEN_DOOR, "uid": None}], "pz": False}
    # Fogata en la esquina sureste, para iluminar el piso.
    m.add((CAMPFIRE[0], CAMPFIRE[1], z), CAMPFIRE_ID)
    return m


def build_floors():
    maps = {z: floor_map(z) for z in FLOORS}
    # Cada conexión: subida 1385 en el piso de abajo, bajada 432 (hueco) en el de arriba, misma x,y.
    for lower_z, pos in STAIRS.items():
        upper_z = lower_z - 1
        x, y = pos
        maps[lower_z].add((x, y, lower_z), STAIRS_UP)
        maps[upper_z].ground((x, y, upper_z), STAIR_DOWN)
    return maps


def fix_wall_grounds(maps, existing):
    """La fila norte y la columna oeste de una pared van con el suelo de afuera (z7) o sin
    ground (pisos altos). Si no, la losa de piedra sobresale en las esquinas."""
    north = [(x, 61) for x in range(174, 181)]
    west = [(174, y) for y in range(61, 68)]
    for x, y in set(north + west):
        # La fila norte y la columna oeste, incluida la esquina NE, llevan el ground
        # de afuera en z7 y sin ground en los pisos altos.
        for z, m in maps.items():
            pos = (x, y, z)
            if pos not in m.t or pos == DOOR:
                continue
            if z == 7:
                # Copiar el ground de la casilla de afuera (norte o oeste), no el de la torre:
                # si se regenera, la torre ya tiene piedra en la huella y no queremos copiarla.
                outside = existing.get((x, y - 1, 7)) if y == 61 else existing.get((x - 1, y, 7))
                if not outside:
                    outside = existing.get((x - 1, y, 7)) or existing.get((x, y - 1, 7))
                m.t[pos]["ground"] = outside[0] if outside else 4756
            else:
                m.t[pos]["ground"] = None


def build_sign(existing) -> roomkit.Map:
    m = roomkit.Map()
    ids = existing.get(SIGN) or [110]
    m.ground(SIGN, ids[0])
    m.add(SIGN, 1429)
    return m


def spawn_xml() -> str:
    lines = []
    for z in FLOORS:
        name, st = MONSTERS_BY_FLOOR[z]
        lines.append(f'\t<spawn centerx="{SPAWN[0]}" centery="{SPAWN[1]}" centerz="{z}" radius="1">')
        lines.append(f'\t\t<monster name="{name}" x="0" y="0" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def in_box(x, y, z, box=TOWER_BOX) -> bool:
    return box[0] <= x <= box[2] and box[1] <= y <= box[3] and z in FLOORS


def validate(existing, maps, regenerating: bool) -> list:
    errs = []
    bl = roomkit.Checker(maps[7])
    # 1. La huella no puede tener casas ni NPCs.
    for line in HOUSES.read_text(encoding="latin-1").splitlines():
        m = re.search(r'<tile x="(\d+)" y="(\d+)" z="(\d+)"', line)
        if m:
            x, y, z = map(int, m.groups())
            if in_box(x, y, z):
                errs.append(f"hay una casa en {x},{y},{z}")
    for m in re.finditer(r'<npc[^>]*x="(\d+)"[^>]*y="(\d+)"[^>]*z="(\d+)"', NPCS.read_text(encoding="latin-1")):
        x, y, z = map(int, m.groups())
        if in_box(x, y, z):
            errs.append(f"hay un NPC en {x},{y},{z}")
    # 2. Primera ejecución: la huella solo puede tener el patio/techo viejo.
    if not regenerating:
        for (x, y, z), ids in existing.items():
            if not in_box(x, y, z):
                continue
            if z == 7:
                if not ids or bl.otb.get(ids[0], {}).get("group") != "ground":
                    errs.append(f"{x},{y},{z}: la huella no tiene un ground válido ({ids})")
                    continue
                allowed = TABLE_IDS | OLD_FRAME
                bad = [i for i in ids[1:] if i not in allowed]
            elif z == 6:
                bad = [i for i in ids if i not in (OLD_FLOOR_Z6 | OLD_FRAME)]
            else:
                bad = list(ids)
            if bad:
                errs.append(f"{x},{y},{z}: item inesperado en la huella {bad}")
    # 3. La puerta tiene que abrir a una casilla caminable.
    outside = existing.get((DOOR[0] - 1, DOOR[1], 7), [])
    if not outside or any(i in bl.solid for i in outside):
        errs.append(f"la salida de la puerta {DOOR[0]-1},{DOOR[1]},7 no es caminable")
    # 4. Cada piso: interior conectado, escaleras y llegadas libres.
    for z, m in maps.items():
        chk = roomkit.Checker(m)
        walk = {p for p in m.t if chk.walkable(p)}
        start = (ROOM[0] + 1, ROOM[1] + 4, z)  # interior, junto a la puerta / sur
        if start not in walk:
            errs.append(f"z{z}: llegada {start} no caminable")
            continue
        seen = {start}
        todo = [start]
        while todo:
            x, y, _ = todo.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy, z)
                if n in walk and n not in seen:
                    seen.add(n)
                    todo.append(n)
        interior = {(x, y, z) for y in range(ROOM[1], ROOM[1] + ROOM[3]) for x in range(ROOM[0], ROOM[0] + ROOM[2])}
        lost = interior - seen
        if lost:
            errs.append(f"z{z}: {len(lost)} casillas del interior aisladas")
        if z in STAIRS:
            sx, sy = STAIRS[z]
            upper = z - 1
            if not any(it["id"] == STAIRS_UP for it in m.t[(sx, sy, z)]["items"]):
                errs.append(f"z{z}: falta la subida 1385 en {sx},{sy}")
            if (sx, sy + 1, z) not in walk:      # al bajar se aterriza al sur de la 1385
                errs.append(f"z{z}: llegada al bajar {sx},{sy+1} no caminable")
            if maps[upper].t[(sx, sy, upper)]["ground"] != STAIR_DOWN:
                errs.append(f"z{upper}: falta la bajada 432 en {sx},{sy}")
            up_chk = roomkit.Checker(maps[upper])
            up_walk = {p for p in maps[upper].t if up_chk.walkable(p)}
            if (sx, sy - 1, upper) not in up_walk:  # al subir se aparece al norte
                errs.append(f"z{upper}: llegada al subir {sx},{sy-1} no caminable")
        if (SPAWN[0], SPAWN[1], z) not in walk:
            errs.append(f"z{z}: spawn {SPAWN} no caminable")
    # Ningún piso puede tener una bajada que no esté sobre una subida (la planta baja daba a z8).
    for z, m in maps.items():
        for (x, y, _z), tile in m.t.items():
            if tile.get("ground") == STAIR_DOWN and STAIRS.get(z + 1) != (x, y):
                errs.append(f"z{z}: bajada 432 en {x},{y} sin subida debajo")
    # 5. Nombres de monstruos.
    known = set(re.findall(r'<monster name="([^"]+)"', MONSTERS.read_text(encoding="latin-1")))
    for z, (name, _st) in MONSTERS_BY_FLOOR.items():
        if name not in known:
            errs.append(f"monstruo inexistente: {name}")
    # 6. El bote y Fargum quedan afuera.
    for p in ((171, 62, 7), (171, 63, 7), (171, 64, 7), (171, 65, 7), (171, 66, 7), (172, 66, 7)):
        if p in maps[7].t:
            errs.append(f"la torre pisó {p}")
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
    print("torre: 5 pisos z7-z3, huella 7x7, interior 5x5")
    for z in FLOORS:
        name, st = MONSTERS_BY_FLOOR[z]
        print(f"  z{z}: {name} (respawn {st}s) en {SPAWN[0]},{SPAWN[1]}")
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

    backup = Path(tempfile.gettempdir()) / f"fargum-tower-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a.map, backup / "test.otbm")
    shutil.copy2(SPAWNS, backup / "test-spawn.xml")
    print(f"backup: {backup}")

    stackable = roomkit.Checker(maps[7]).stackable
    for z, m in maps.items():
        roomkit.write_map(a.map, m, TOWER_BOX, z, stackable)
    roomkit.write_map(a.map, build_sign(existing),
                      (SIGN[0], SIGN[1], SIGN[0], SIGN[1]), SIGN[2], stackable)

    # Spawns
    sp = SPAWNS.read_text(encoding="latin-1")
    block = "\t<!-- BEGIN FARGUM_TOWER_SPAWNS (scripts/map/generate-fargum-tower.py) -->\n" + \
        spawn_xml() + "\n\t<!-- END FARGUM_TOWER_SPAWNS -->\n"
    old_block = re.compile(r"[ \t]*<!-- BEGIN FARGUM_TOWER_SPAWNS.*?<!-- END FARGUM_TOWER_SPAWNS -->\n?", re.S)
    if old_block.search(sp):    # en su lugar, así regenerar no mueve el bloque al final del archivo
        sp = old_block.sub(lambda _m: block, sp, count=1)
    else:
        sp = sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")

    # Cartel
    roomkit.patch_readables("<!-- BEGIN FARGUM_TOWER_SIGNS -->", "<!-- END FARGUM_TOWER_SIGNS -->", [
        dict(x=SIGN[0], y=SIGN[1], z=SIGN[2],
             text="FERRYMAN'S TOWER\n5 floors, one monster per floor.\nTortoise -> Thornback Tortoise -> Crab -> Quara -> Predator."),
    ])

    MANIFEST.write_text(json.dumps({
        "name": "Torre del Barquero", "box": TOWER_BOX, "floors": list(FLOORS),
        "door": list(DOOR), "sign": list(SIGN), "spawn": list(SPAWN),
        "monsters": {f"z{z}": {"name": n, "respawn": s} for z, (n, s) in MONSTERS_BY_FLOOR.items()},
    }, indent=2) + "\n")
    print(f"OK {a.map}, test-spawn.xml, readables.xml y {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
