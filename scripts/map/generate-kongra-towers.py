#!/usr/bin/env python3
"""Torres del Kongra: tres torres de piedra en la selva del Bamboo Camp.

El claro de los Kongras (x168-193, y92-111) y la franja sur (x160-172, y126-133) ganan
torres "medias": Kongra en la planta baja y Red Kongra (mas fuerte, con rugido y prisa)
en los pisos de arriba.

  Torre del Kongra (claro)    x170-176, y103-109  3 pisos z7-z5  puerta oeste (170,106)
  Torre Sur del Kongra        x161-167, y126-132  3 pisos z7-z5  puerta este  (167,129)
  Atalaya del Kongra (norte)  x186-190, y74-78    2 pisos z7-z6  puerta oeste (186,76)

Escaleras como la Torre del Barquero: en cada conexion la subida 1385 va en el piso de
abajo y la bajada 432 (el hueco) en el de arriba, en la misma x,y. Pisar la 1385 lleva a
x,y-1 del piso de arriba; pisar la 432 baja y deja al sur de la 1385.

La torre del claro reemplaza los spawns sueltos de kongra (175,103) y (172,105); la sur,
el de (164,132): el generador los quita de test-spawn.xml y cada planta baja pone sus
propios Kongra. Dentro de las huellas solo hay pasto y arboles/arbustos removibles; el
techo de madera huérfano que flota sobre la huella sur (sobró de sacar las casas de
bambú, sin ninguna pared debajo) se limpia al escribir el piso de arriba.

Uso:
  python3 scripts/map/generate-kongra-towers.py --dry-run --preview-dir /tmp/torres
  python3 scripts/map/generate-kongra-towers.py --replace
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
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
MANIFEST = WORLD / "generated-kongra-towers.json"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"

STONE_FLOOR = 431
WOODEN_DOOR = 1220   # puerta abierta para pared vertical (la 1215 es horizontal)
CAMPFIRE_ID = 1423
SIGN_ID = 1429
STAIR_DOWN, STAIRS_UP = 432, 1385

TOWERS = [
    dict(
        key="claro", label="Torre del Kongra",
        box=(170, 103, 7, 7), floors=(7, 6, 5),
        door=(170, 106, 7, "w"), sign=(169, 105, 7),
        stairs={7: (174, 105), 6: (172, 105)},
        campfire=(175, 108), radius=2, center={7: (173, 107), 6: (173, 107), 5: (173, 107)},
        monsters={
            7: [("Kongra", 140, (-2, 0)), ("Kongra", 140, (0, 0))],
            6: [("Red Kongra", 180, (-2, 0)), ("Red Kongra", 180, (0, 0))],
            5: [("Red Kongra", 240, (-2, 0)), ("Red Kongra", 240, (0, 0)), ("Red Kongra", 240, (2, 0))],
        },
        remove_spawns=[(175, 103, 7), (172, 105, 7)],
    ),
    dict(
        key="sur", label="Torre Sur del Kongra",
        box=(161, 126, 7, 7), floors=(7, 6, 5),
        door=(167, 129, 7, "e"), sign=(168, 128, 7),
        stairs={7: (165, 128), 6: (163, 128)},
        campfire=(166, 131), radius=2, center={7: (164, 130), 6: (164, 130), 5: (164, 130)},
        monsters={
            7: [("Kongra", 140, (-2, 0)), ("Kongra", 140, (0, 0))],
            6: [("Red Kongra", 200, (-2, 0)), ("Red Kongra", 200, (0, 0))],
            5: [("Red Kongra", 260, (-2, 0)), ("Red Kongra", 260, (0, 0)), ("Red Kongra", 260, (2, 0))],
        },
        remove_spawns=[(164, 132, 7)],
    ),
    dict(
        key="norte", label="Atalaya del Kongra",
        box=(186, 74, 5, 5), floors=(7, 6),
        door=(186, 76, 7, "w"), sign=(185, 75, 7),
        stairs={7: (189, 76)},
        campfire=(187, 77), radius=1, center={7: (188, 77), 6: (188, 75)},
        monsters={
            7: [("Kongra", 120, (0, 0))],
            6: [("Red Kongra", 160, (0, 0)), ("Red Kongra", 160, (-1, 1))],
        },
        remove_spawns=[],
    ),
]

SIGNS = {
    "claro": "KONGRA TOWER\n3 floors. Kongras below;\nRed Kongras roar above.",
    "sur": "SOUTH KONGRA TOWER\n3 floors; the strongest Red Kongras live above.",
    "norte": "KONGRA WATCHTOWER\n2 floors. Red Kongras watch from above.",
}


def interior(box):
    bx, by, w, h = box
    return (bx + 1, by + 1, w - 2, h - 2)


def clear_of(box):
    bx, by, w, h = box
    return (bx, by, bx + w - 1, by + h - 1)


def in_box(x, y, z, box) -> bool:
    bx, by, w, h = box
    return bx <= x <= bx + w - 1 and by <= y <= by + h - 1 and z in range(7, 3, -1)


def floor_map(tw, z):
    bx, by, w, h = tw["box"]
    m = roomkit.Map()
    room = roomkit.Room(bx + 1, by + 1, w - 2, h - 2, z)
    roomkit.build_room(m, room, STONE_FLOOR, "stone")
    # Puerta en la pared que mira al lado del approach.
    dx, dy, dz, lado = tw["door"]
    if z == dz:
        m.t[(dx, dy, dz)] = {"ground": STONE_FLOOR, "items": [{"id": WOODEN_DOOR, "uid": None}], "pz": False}
    # Fogata en la esquina sureste del interior, para iluminar el piso.
    m.add((tw["campfire"][0], tw["campfire"][1], z), CAMPFIRE_ID)
    return m


def build_floors(tw):
    maps = {z: floor_map(tw, z) for z in tw["floors"]}
    for lower_z, pos in tw["stairs"].items():
        upper_z = lower_z - 1
        x, y = pos
        maps[lower_z].add((x, y, lower_z), STAIRS_UP)
        maps[upper_z].ground((x, y, upper_z), STAIR_DOWN)
    return maps


def fix_wall_grounds(tw, maps, existing):
    """Norte/oeste llevan terreno exterior en z7 y ningún suelo arriba.

    La orientación de la puerta no cambia la perspectiva de los sprites.
    """
    bx, by, w, h = tw["box"]
    door = tuple(tw["door"][:3])
    sides = {(x, by) for x in range(bx, bx + w)} | {(bx, y) for y in range(by, by + h)}
    otb = load_otb()
    for x, y in sides:
        for z, m in maps.items():
            pos = (x, y, z)
            if pos not in m.t or pos == door:
                continue
            if z == 7:
                neighbor = (x, by - 1, 7) if y == by else (bx - 1, y, 7)
                outside = existing.get(neighbor, [])
                m.t[pos]["ground"] = next((i for i in outside if otb.get(i, {}).get("group") == "ground"), 4756)
            else:
                m.t[pos]["ground"] = None


def entry_point(tw, z):
    dx, dy, _dz, lado = tw["door"]
    return (dx + 1, dy, z) if lado == "w" else (dx - 1, dy, z)


def landing_reaches_entry(tw, m, start):
    """El rellano debe salir al pasillo sin pisar otra escalera/hueco."""
    chk = roomkit.Checker(m)
    walk = {p for p, t in m.t.items() if chk.walkable(p) and t["ground"] != STAIR_DOWN
            and not any(i["id"] == STAIRS_UP for i in t["items"])}
    seen, todo = set(), [start]
    while todo:
        p = todo.pop()
        if p in seen or p not in walk:
            continue
        seen.add(p)
        x, y, z = p
        todo.extend((x + dx, y + dy, z) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    return entry_point(tw, start[2]) in seen


def spawn_positions(tw, z):
    cx, cy = tw["center"][z]
    return [(cx + ox, cy + oy, z) for _n, _st, (ox, oy) in tw["monsters"][z]]


def spawn_xml():
    lines = []
    for tw in TOWERS:
        for z in tw["floors"]:
            cx, cy = tw["center"][z]
            lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="{z}" radius="{tw["radius"]}">')
            for name, st, (ox, oy) in tw["monsters"][z]:
                lines.append(f'\t\t<monster name="{name}" x="{ox}" y="{oy}" z="{z}" spawntime="{st}" />')
            lines.append("\t</spawn>")
    return "\n".join(lines)


def covered_by(center, radius):
    cx, cy, cz = center
    return {(cx + dx, cy + dy, cz) for dx in range(-radius, radius + 1) for dy in range(-radius, radius + 1)}


def validate(existing, all_maps, regenerating, spawn_blocks):
    errs = []
    bl = roomkit.Checker(all_maps["claro"][7])
    removable_ok = lambda i: ("block_solid" in bl.otb.get(i, {}).get("flags", [])
                             and "always_on_top" in bl.otb.get(i, {}).get("flags", [])
                             and "block_projectile" not in bl.otb.get(i, {}).get("flags", []))
    for tw in TOWERS:
        box = tw["box"]
        tag = tw["label"]
        maps = all_maps[tw["key"]]
        # 1. La huella no puede tener casas ni NPCs.
        for line in HOUSES.read_text(encoding="latin-1").splitlines():
            m = re.search(r'<tile x="(\d+)" y="(\d+)" z="(\d+)"', line)
            if m and in_box(*map(int, m.groups()), box):
                errs.append(f"{tag}: hay una casa en {m.groups()}")
        for m in re.finditer(r'<npc[^>]*x="(\d+)"[^>]*y="(\d+)"[^>]*z="(\d+)"',
                             NPCS.read_text(encoding="latin-1")):
            if in_box(*map(int, m.groups()), box):
                errs.append(f"{tag}: hay un NPC en {m.groups()}")
        # 2. Primera ejecución: la huella solo puede tener suelo caminable con props
        #    removibles (árboles/arbustos) y, en z6, techos huérfanos (sin nada sólido debajo).
        if not regenerating:
            for (x, y, z), ids in existing.items():
                if not in_box(x, y, z, box):
                    continue
                if z > 7:
                    z6_orphan = z == 6 and ids and not any(
                        "block_solid" in bl.otb.get(i, {}).get("flags", []) for i in ids)
                    below = existing.get((x, y, z - 1)) or []
                    below_ok = not any("block_solid" in bl.otb.get(i, {}).get("flags", [])
                                       for i in below[1:])
                    if not (z6_orphan and below_ok):
                        errs.append(f"{tag}: {x},{y},{z} tiene {ids} arriba de la huella")
                    continue
                if not ids or ids[0] in bl.solid:
                    errs.append(f"{tag}: {x},{y},{z} sin ground válido ({ids})")
                    continue
                bad = [i for i in ids[1:] if (i in bl.solid or i in bl.stackable and False)
                       and not removable_ok(i) and i != CAMPFIRE_ID]
                if bad:
                    errs.append(f"{tag}: {x},{y},{z} item inesperado {bad}")
        # 3. La puerta abre a una casilla caminable.
        dx, dy, dz, lado = tw["door"]
        out = (dx - 1, dy, dz) if lado == "w" else (dx + 1, dy, dz)
        if not regenerating:
            out_ids = existing.get(out)
            if not out_ids or out_ids[0] in bl.solid or any(i in bl.solid for i in out_ids[1:]):
                errs.append(f"{tag}: la salida de la puerta {out} no es caminable")
        # 4. Cada piso: interior conectado desde la puerta, escaleras y llegadas libres.
        for z, m in maps.items():
            chk = roomkit.Checker(m)
            walk = {p for p in m.t if chk.walkable(p)}
            start = entry_point(tw, z)
            if start not in walk:
                errs.append(f"{tag} z{z}: entrada {start} no caminable")
                continue
            seen, todo = {start}, [start]
            while todo:
                x, y, _ = todo.pop()
                for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (x + ddx, y + ddy, z)
                    if n in walk and n not in seen:
                        seen.add(n)
                        todo.append(n)
            ix, iy, iw, ih = interior(box)
            inner = {(x, y, z) for y in range(iy, iy + ih) for x in range(ix, ix + iw)}
            lost = inner - seen
            if lost:
                errs.append(f"{tag} z{z}: {len(lost)} casillas del interior aisladas")
            if z in tw["stairs"]:
                sx, sy = tw["stairs"][z]
                upper = z - 1
                # 1385 ocupa 2x2 hacia NO; el ancla libre no basta.
                for px in (sx - 1, sx):
                    for py in (sy - 1, sy):
                        cell = m.t.get((px, py, z), {})
                        if (px, py, z) not in walk or cell.get("ground") == STAIR_DOWN or any(
                                it["id"] != STAIRS_UP for it in cell.get("items", [])):
                            errs.append(f"{tag} z{z}: huella de escalera obstruida en {px},{py}")
                if not any(it["id"] == STAIRS_UP for it in m.t[(sx, sy, z)]["items"]):
                    errs.append(f"{tag} z{z}: falta la subida {STAIRS_UP} en {sx},{sy}")
                if (sx, sy + 1, z) not in walk:
                    errs.append(f"{tag} z{z}: llegada al bajar {sx},{sy+1} no caminable")
                if maps[upper].t[(sx, sy, upper)]["ground"] != STAIR_DOWN:
                    errs.append(f"{tag} z{upper}: falta la bajada {STAIR_DOWN} en {sx},{sy}")
                up_chk = roomkit.Checker(maps[upper])
                up_walk = {p for p in maps[upper].t if up_chk.walkable(p)}
                if (sx, sy - 1, upper) not in up_walk:
                    errs.append(f"{tag} z{upper}: llegada al subir {sx},{sy-1} no caminable")
                for floor, landing in ((z, (sx, sy + 1, z)), (upper, (sx, sy - 1, upper))):
                    if not landing_reaches_entry(tw, maps[floor], landing):
                        errs.append(f"{tag} z{floor}: rellano {landing} sin salida libre")
            for p in spawn_positions(tw, z):
                if p not in walk:
                    errs.append(f"{tag} z{z}: spawn {p} no caminable")
        # Ningún piso puede tener una bajada que no esté sobre una subida.
        for z, m in maps.items():
            for (x, y, _z), tile in m.t.items():
                if tile.get("ground") == STAIR_DOWN and tw["stairs"].get(z + 1) != (x, y):
                    errs.append(f"{tag} z{z}: bajada {STAIR_DOWN} en {x},{y} sin subida debajo")
        # 5. Spawns existentes (solo primera ejecución): los MONSTRUOS pisados tienen que ser
        #    exactamente los de la lista. Que el radio de un spawn vecino toque la huella no
        #    importa: no hay ningún monstruo parado ahí.
        if not regenerating:
            foot = {(x, y, z) for z in tw["floors"] for x in range(box[0], box[0] + box[2])
                    for y in range(box[1], box[1] + box[3])}
            for center, _radius, monsters in spawn_blocks:
                positions = {(center[0] + ox, center[1] + oy, center[2]) for _n, (ox, oy), _st in monsters}
                if positions & foot:
                    if center not in [tuple(c) for c in tw["remove_spawns"]]:
                        errs.append(f"{tag}: monstruo del spawn {center} caería dentro de la huella")
                    elif [n for n, _o, _s in monsters if n.lower() != "kongra"]:
                        errs.append(f"{tag}: el spawn {center} no es solo kongra: {monsters}")
            for center in tw["remove_spawns"]:
                if center not in [c for c, _r, _m in spawn_blocks]:
                    errs.append(f"{tag}: falta el spawn esperado {center} en test-spawn.xml")
    # 6. Nombres de monstruos.
    known = set(re.findall(r'<monster name="([^"]+)"', MONSTERS.read_text(encoding="latin-1")))
    for tw in TOWERS:
        for z, entries in tw["monsters"].items():
            for name, _st, _pos in entries:
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
    all_maps = {tw["key"]: build_floors(tw) for tw in TOWERS}
    for tw in TOWERS:
        fix_wall_grounds(tw, all_maps[tw["key"]], existing)

    # spawns existentes: (centro, radio, [(nombre, offset)])
    raw = SPAWNS.read_text(encoding="latin-1")
    spawn_blocks = []
    for m in re.finditer(r'<spawn centerx="(\d+)" centery="(\d+)" centerz="(\d+)" radius="(\d+)">(.*?)</spawn>',
                         raw, re.S):
        center = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        radius = int(m.group(4))
        monsters = [(n, (int(ox), int(oy)), int(st)) for n, ox, oy, st in
                   re.findall(r'<monster name="([^"]+)" x="(-?\d+)" y="(-?\d+)"[^>]*spawntime="(\d+)"', m.group(5))]
        spawn_blocks.append((center, radius, monsters))

    errs = validate(existing, all_maps, regenerating, spawn_blocks)

    for tw in TOWERS:
        print(f"{tw['label']}: x{tw['box'][0]}-{tw['box'][0]+tw['box'][2]-1}, "
              f"y{tw['box'][1]}-{tw['box'][1]+tw['box'][3]-1}, pisos {tw['floors']}")
        for z in tw["floors"]:
            counts = {}
            for n, _s, _o in tw["monsters"][z]:
                counts[n] = counts.get(n, 0) + 1
            names = ", ".join(f"{n}×{c}" for n, c in counts.items())
            print(f"  z{z}: {names} (respawn {min(e[1] for e in tw['monsters'][z])}s)")
        if tw["remove_spawns"]:
            print(f"  quita spawns sueltos: {tw['remove_spawns']}")

    if a.preview_dir:
        a.preview_dir.mkdir(parents=True, exist_ok=True)
        for tw in TOWERS:
            for z, m in all_maps[tw["key"]].items():
                roomkit.render_png(m, a.preview_dir / f"torre-{tw['key']}-z{z}.png", z)
        print(f"PNG en {a.preview_dir}")

    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs[:40]), file=sys.stderr)
        return 1
    if a.dry_run or not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    backup = REPO / "backups/map" / f"kongra-towers-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    for f in (a.map, SPAWNS, READABLES):
        shutil.copy2(f, backup / f.name)
    print(f"backup: {backup}")

    stackable = roomkit.Checker(all_maps["claro"][7]).stackable
    for tw in TOWERS:
        for z, m in all_maps[tw["key"]].items():
            roomkit.write_map(a.map, m, clear_of(tw["box"]), z, stackable)

    # Spawns: sacar los bloques pisados y escribir el bloque propio.
    sp = raw
    for tw in TOWERS:
        for (cx, cy, cz) in tw["remove_spawns"]:
            pat = re.compile(rf'\t<spawn centerx="{cx}" centery="{cy}" centerz="{cz}"[^>]*>\n(?:\t\t[^\n]*\n)*?\t</spawn>\n')
            if not pat.search(sp) and regenerating:
                continue
            if not pat.search(sp):
                print(f"ERROR: no encontré el spawn {cx},{cy},{cz} para quitar", file=sys.stderr)
                return 1
            sp = pat.sub("", sp, count=1)
    block = ("\t<!-- BEGIN KONGRA_TOWERS_SPAWNS (scripts/map/generate-kongra-towers.py) -->\n"
             + spawn_xml() + "\n\t<!-- END KONGRA_TOWERS_SPAWNS -->\n")
    old_block = re.compile(r"[ \t]*<!-- BEGIN KONGRA_TOWERS_SPAWNS.*?<!-- END KONGRA_TOWERS_SPAWNS -->\n?", re.S)
    if old_block.search(sp):
        sp = old_block.sub(lambda _m: block, sp, count=1)
    else:
        sp = sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")

    # Carteles
    roomkit.patch_readables("<!-- BEGIN KONGRA_TOWERS_SIGNS -->", "<!-- END KONGRA_TOWERS_SIGNS -->",
                            [dict(x=tw["sign"][0], y=tw["sign"][1], z=tw["sign"][2], text=SIGNS[tw["key"]])
                             for tw in TOWERS])

    MANIFEST.write_text(json.dumps({
        "name": "Torres del Kongra",
        "towers": [dict(key=tw["key"], label=tw["label"], box=list(tw["box"]), floors=list(tw["floors"]),
                         door=list(tw["door"][:3]), sign=list(tw["sign"]),
                         stairs={str(z): list(p) for z, p in tw["stairs"].items()},
                         monsters={str(z): [dict(name=n, respawn=s, offset=list(o))
                                            for n, s, o in tw["monsters"][z]] for z in tw["floors"]},
                         remove_spawns=[list(c) for c in tw["remove_spawns"]])
                        for tw in TOWERS],
    }, indent=2) + "\n")
    print(f"OK {a.map}, test-spawn.xml, readables.xml y {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
