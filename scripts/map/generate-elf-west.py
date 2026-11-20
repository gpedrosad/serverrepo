#!/usr/bin/env python3
"""Ruinas del Sauce: amplía Elfland al oeste y remata sus terrazas existentes.

Solo mapa, cuatro spawns y luz fija 20353; no requiere sprites ni C++ nuevos.
Uso: python3 scripts/map/generate-elf-west.py [--dry-run]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import struct
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "kb")]
from mapdata import MAP, REPO, load_otb, parse_tree, serialize_tree
from portal_temple_style import item_offsets
from portal_citadel_layout import tile_flags

spec = importlib.util.spec_from_file_location("elf_coast", HERE / "generate-dragon-spot.py")
COAST = importlib.util.module_from_spec(spec)
spec.loader.exec_module(COAST)
WORLD = MAP.parent
MANIFEST = WORLD / "generated-elf-west.json"
SPAWNS = WORLD / "test-spawn.xml"
LIGHT = 20353
SIGN = (101, 72, 7)
BRIDGE = {(x, y) for x in range(95, 101) for y in (72, 73)}
ENTRY = (100, 73, 7)
LAVA_SCREEN_RADIUS = (11, 9)  # ventana 9x7 del cliente + dos casillas de margen
GROUPS = [((95, 65), [("Elf Scout", (95, 65), 150)]),
          ((94, 56), [("Elf Arcanist", (94, 56), 180)]),
          ((89, 51), [("Blue Elf Arcanist", (89, 51), 220),
                      ("Elf Arcanist", (90, 51), 220)])]


def house_reservations():
    """Las casas comprables conservan su planta y techo al regenerar el hunt."""
    path = WORLD / "generated-curious-houses.json"
    if not path.exists():
        return set()
    return {tuple(map(int, p.split(","))) for p in json.loads(path.read_text())["cells"]}


def index(root, otb):
    nodes, values = {}, {}
    for area in root[2][0][2]:
        if area[0] != 4:
            continue
        ax, ay, z = struct.unpack_from("<HHB", area[1])
        for tile in area[2]:
            if tile[0] not in (5, 14):
                continue
            p = ax + tile[1][0], ay + tile[1][1], z
            if p in nodes:
                raise ValueError(f"Tile duplicado: {p}")
            nodes[p] = tile
            values[p] = [struct.unpack_from("<H", b, o)[0] for b, o in item_offsets(tile, otb)]
    return nodes, values


def free(ids, otb):
    return bool(ids) and any(otb[i]["group"] == "ground" for i in ids) and not any(
        "block_solid" in otb[i]["flags"] for i in ids)


def plan(values, otb):
    land = (COAST.ellipse(((91, 52), 5.5, 3.5)) | COAST.ellipse(((94.5, 65), 3.5, 12))
            | {(x, y) for x in range(91, 97) for y in range(54, 61)})
    land -= {(91, 65), (98, 65)}  # puntas de una casilla, sin remate de costa válido
    water = {(x + dx, y + dy) for x, y in land for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - land - BRIDGE
    water = {p for p in water if values.get((*p, 7), [0])[0] in COAST.WATERS}
    cells = {}
    for x, y in sorted(land | BRIDGE):
        if (x, y) in BRIDGE:
            cells[x, y, 7] = [405]
            continue
        pcs = COAST.NP.pieces_for(COAST.NP.neighbors_in(water, x, y),
                                 COAST.COAST_SIDE, COAST.COAST_CORNER, COAST.COAST_INNER)
        if pcs is None or len(pcs) > 1:
            raise ValueError(f"Costa sin pieza única: {x},{y}: {pcs}")
        cells[x, y, 7] = [4526, *pcs] if pcs else [4756]
    # Santuario abierto al sur: muros bajos y columnas, sin cerrar el paso.
    for x in range(89, 94):
        for y in range(51, 54):
            if free(cells.get((x, y, 7), []), otb):
                cells[x, y, 7] = [406]
    for x in range(89, 94):
        if free(cells.get((x, 50, 7), []), otb):
            cells[x, 50, 7].append(1112)
    for p, sid in { (88, 50): 1113, (88, 51): 1111,
                    (94, 54): 1515, (93, 62): 1113, (94, 62): 1112, (93, 63): 1111,
                    (94, 68): 1112, (92, 56): 2701, (97, 58): 2702,
                    (92, 60): 2701, (92, 69): 2702, (97, 67): 2701,
                    (93, 74): 2768, (96, 75): 2768 }.items():
        if (*p, 7) in cells:
            cells[*p, 7].append(sid)
    for y in range(55, 72):
        p = (94 if y < 60 else 95, y, 7)
        if free(cells.get(p, []), otb) and y % 4 != 0:
            cells[p][0] = 406
    for y in (58, 64, 70):
        for x in (94, 95):
            p = x, y, 7
            if free(cells.get(p, []), otb):
                cells[p][0] = 406
    # Puente de mármol envejecido: las orillas originales solo se abren en el tablero.
    for x, y in BRIDGE:
        cells[x, y, 7] = [406]
    for y in (71, 74):
        for x in (97, 98, 99):
            p = x, y, 7
            ids = cells.get(p, list(values.get(p, [])))
            if ids and ids[0] in COAST.WATERS | {4526}:
                cells[p] = ids
                if 1121 not in ids:
                    ids.append(1121)
    # Terraza vieja: cambiar suelo/barreras conservando cofres, puertas y escaleras.
    for p, ids in values.items():
        x, y, z = p
        if 106 <= x <= 110 and 63 <= y <= 67 and z in (4, 5, 6, 7):
            new = [406 if i == 424 else 1111 if i == 1497 else
                   (1112 if y in (63, 67) else 1515) if i == 1499 else i for i in ids]
            if new != ids:
                cells[p] = new
    # Sendero roto de acceso: conservar toda la vegetación y los cambios de piso.
    path = [(111, 62), (111, 64), (104, 64), (104, 69), (102, 69), (102, 73), (100, 73)]
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        for x in range(min(ax, bx), max(ax, bx) + 1):
            for y in range(min(ay, by), max(ay, by) + 1):
                for dx in (0, 1):
                    p = x + dx, y, 7
                    ids = values.get(p, [])
                    if ids == [4756] and (x + y + dx) % 4 != 0:
                        cells.setdefault(p, [406])
    for p in ((95, 71, 7), (94, 61, 7), (92, 52, 7),
              (98, 71, 7), (98, 74, 7), (103, 64, 7), (105, 69, 7), (111, 62, 7),
              (108, 63, 6), (108, 63, 5), (108, 63, 4)):
        cells.setdefault(p, list(values.get(p, [])))
        if LIGHT not in cells[p]:
            cells[p].append(LIGHT)
    cells[SIGN] = list(values.get(SIGN, []))
    if 1429 not in cells[SIGN]:
        cells[SIGN].append(1429)
    # Ampliar el lago: lava y agua bloquean igual. No tocar el piso del hunt vecino.
    rx, ry = LAVA_SCREEN_RADIUS
    screen = {(x + dx, y + dy, 7) for x, y in land | BRIDGE
              for dx in range(-rx, rx + 1) for dy in range(-ry, ry + 1)}
    for p in screen:
        if values.get(p, [None])[0] in COAST.LAVA:
            if len(values[p]) != 1:
                continue  # conservar bordes/decoración del hunt fuera de la vista
            cells[p] = [4608]
    for p in house_reservations():
        cells.pop(p, None)
    return cells, land


def validate(values, cells, land, otb):
    assert LIGHT in otb and not ({"moveable", "pickupable"} & set(otb[LIGHT]["flags"]))
    merged = values | cells
    previous = json.loads(MANIFEST.read_text()).get("cells", {}) if MANIFEST.exists() else {}
    private = house_reservations()
    for x, y in land | BRIDGE:
        p = x, y, 7
        if p in private:
            continue
        old = values.get(p, [])
        owned = previous.get(",".join(map(str, p))) == old
        allowed = COAST.WATERS | ({4526, 4756} if (x, y) in BRIDGE else set())
        if not owned and (not old or old[0] not in allowed or any(i not in range(4644, 4656) for i in old[1:])):
            raise ValueError(f"La ampliación pisa terreno/ítems ajenos: {p} {old}")
    walk = {p for p, ids in merged.items() if p[2] == 7 and free(ids, otb)
            and 85 <= p[0] <= 115 and 48 <= p[1] <= 85}
    seen, todo = set(), [ENTRY]
    while todo:
        p = todo.pop()
        if p not in walk or p in seen:
            continue
        seen.add(p)
        x, y, z = p
        todo.extend((x + dx, y + dy, z) for dx, dy in COAST.NP.CARD)
    expected = {(*p, 7) for p in land | BRIDGE if (*p, 7) not in private and free(merged.get((*p, 7), []), otb)}
    if not expected <= seen:
        raise ValueError(f"Isla desconectada: {sorted(expected - seen)[:8]}")
    for center, monsters in GROUPS:
        for name, p, _delay in monsters:
            if (*p, 7) not in seen or abs(p[0] - ENTRY[0]) + abs(p[1] - ENTRY[1]) < 6:
                raise ValueError(f"Spawn sin acceso o junto a entrada: {name} {p}")
    known = {m.get("name", "").casefold() for m in ET.parse(REPO / "server/YurOTS/ots/data/monster/monsters.xml").getroot()}
    for _center, monsters in GROUPS:
        for name, _p, _delay in monsters:
            if name.casefold() not in known:
                raise ValueError(f"Monstruo no registrado: {name}")
    for block in ET.parse(SPAWNS).getroot():
        x, y, z = [int(block.get(k, "0")) for k in ("centerx", "centery", "centerz")]
        for monster in block:
            p = x + int(monster.get("x", "0")), y + int(monster.get("y", "0")), int(monster.get("z", z))
            if p in cells and free(values.get(p, []), otb) and not free(merged[p], otb):
                raise ValueError(f"Decoración bloquea un spawn existente: {p}")
    # No alterar la colisión, escaleras ni puertas de la torre existente.
    for p, new in cells.items():
        old = values.get(p, [])
        if p[2] < 7 and free(old, otb) != free(new, otb):
            raise ValueError(f"Colisión de terraza alterada: {p}")
        water_screen = (p[2] == 7 and 75 <= p[0] <= 111 and 40 <= p[1] <= 85
                        and len(old) == 1 and old[0] in COAST.LAVA and new == [4608]
                        and not free(old, otb) and not free(new, otb))
        if not water_screen and not (85 <= p[0] <= 114 and 49 <= p[1] <= 76 and 4 <= p[2] <= 7):
            raise ValueError(f"Fuera de ámbito: {p}")
    for x, y, _z in expected:
        for dx in range(-9, 10):
            for dy in range(-7, 8):
                if merged.get((x + dx, y + dy, 7), [None])[0] in COAST.LAVA:
                    raise ValueError(f"Lava visible desde las ruinas: {x},{y}")
    return len(expected)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    otb = load_otb()
    nodes, values = index(root, otb)
    cells, land = plan(values, otb)
    walk = validate(values, cells, land, otb)
    # Todas las modificaciones son sobre tiles existentes; casas/atributos protegidos.
    changed = 0
    for p, ids in cells.items():
        tile = nodes[p]
        if tile[0] != 5:
            raise ValueError(f"Casa dentro de la intervención: {p}")
        old = values[p]
        if old == ids:
            continue
        # Ítems atribuidos solo se conservan, en el mismo orden y con el mismo ID.
        attributed = [c for c in tile[2] if c[0] != 6 or len(c[1]) != 2 or c[2]]
        if attributed:
            if p[2] == 7 or [i for i in ids if i != 406] != [i for i in old if i != 424]:
                raise ValueError(f"Ítem con atributos en {p}")
            offsets = list(item_offsets(tile, otb))
            for buf, off in offsets:
                if struct.unpack_from("<H", buf, off)[0] == 424:
                    struct.pack_into("<H", buf, off, 406)
        else:
            tile[1] = tile[1][:2] + tile_flags(tile[1]) + struct.pack("<BH", 9, ids[0])
            tile[2] = [[6, bytearray(struct.pack("<H", sid)), []] for sid in ids[1:]]
        changed += 1
    print(f"Ruinas del Sauce: {len(land)} tierra / {walk} transitables; {changed} tiles modificados; 4 elfos nuevos")
    if args.dry_run:
        return
    backup = REPO / "backups/map" / ("elf-west-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    for file in (MAP, SPAWNS, REPO / "server/YurOTS/ots/data/readables.xml"):
        shutil.copy2(file, backup / file.name)
    lines = ["\t<!-- BEGIN ELF_WEST_SPAWNS -->"]
    for (cx, cy), monsters in GROUPS:
        lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="7" radius="2">')
        for name, (x, y), delay in monsters:
            lines.append(f'\t\t<monster name="{name}" x="{x-cx}" y="{y-cy}" z="7" spawntime="{delay}" />')
        lines.append("\t</spawn>")
    lines.append("\t<!-- END ELF_WEST_SPAWNS -->\n")
    text = SPAWNS.read_text(encoding="latin-1")
    block = "\n".join(lines)
    pattern = r"[ \t]*<!-- BEGIN ELF_WEST_SPAWNS -->.*?<!-- END ELF_WEST_SPAWNS -->\n?"
    text = re.sub(pattern, lambda _m: block, text, flags=re.S) if re.search(pattern, text, re.S) else text.replace("</spawns>", block + "</spawns>")
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    SPAWNS.write_text(text, encoding="latin-1")
    import roomkit
    roomkit.patch_readables("<!-- BEGIN ELF_WEST_SIGNS -->", "<!-- END ELF_WEST_SIGNS -->",
        [dict(x=SIGN[0], y=SIGN[1], z=SIGN[2], text="RUINAS DEL SAUCE\nAl oeste: exploradores y arcanistas.\nEl santuario azul queda al fondo.")])
    header = json.dumps(dict(name="Ruinas del Sauce", entry=ENTRY, land=len(land),
        walkable=walk, groups=GROUPS, light=LIGHT, sign=SIGN))[:-1]
    owned = {(*p, 7) for p in land | BRIDGE}
    rows = [json.dumps(",".join(map(str, p))) + ": " + json.dumps(cells.get(p, values[p])) for p in sorted(owned)]
    MANIFEST.write_text(header + ', "cells": {\n' + ",\n".join(rows) + "\n}}\n")
    print(f"Aplicado. Respaldo: {backup}")


if __name__ == "__main__":
    main()
