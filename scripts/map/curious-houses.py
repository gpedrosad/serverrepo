#!/usr/bin/env python3
"""Tres casas pequeñas comprables sobre plataformas en el agua.

python3 scripts/map/curious-houses.py [--dry-run]
No modifica casas existentes, jugadores ni houseitems.xml.
"""
from __future__ import annotations

import argparse
import json
import shutil
import struct
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "kb"), str(HERE.parent)]
from lib.project_root import project_root
from mapdata import MAP, load_otb, parse_tree, serialize_tree
from portal_citadel_layout import tile_flags
from epstein_cave_repair import index

REPO = project_root(HERE)
DATA = REPO / "server/YurOTS/ots/data"
REGISTRY = DATA / "houses.xml"
MANIFEST = DATA / "world/generated-curious-houses.json"
HOUSES = [
    dict(name="Bamboo Pocket", box=(179, 115, 183, 119), door=(183, 117), landing=(184, 111), side="e", style="bamboo", roof=945),
    dict(name="Willow Nook", box=(85, 57, 89, 61), door=(89, 59), landing=(92, 59), side="e", style="marble", roof=935),
    dict(name="River Nook", box=(165, 65, 169, 69), door=(167, 69), landing=(167, 72), side="s", style="timber", roof=935),
]
WALLS = {"bamboo": (3425, 3424, 3423, 3427),
         "timber": (1038, 1039, 1043, 1044), "marble": (1113, 1112, 1111, 1119)}
DECOR = {2701, 2711, 20353}
WATER = set(range(4608, 4626))


def positions(h):
    x0, y0, x1, y1 = h["box"]
    return {(x, y, 7) for x in range(x0 + 1, x1) for y in range(y0 + 1, y1)}


def outside(h):
    x, y = h["door"]
    dx, dy = {"s": (0, 1), "w": (-1, 0), "e": (1, 0)}[h["side"]]
    return x + dx, y + dy, 7


def deck(h):
    x0, y0, x1, y1 = h["box"]
    return {(x, y, 7) for x in range(x0 - 1, x1 + 2) for y in range(y0 - 1, y1 + 2)}


def jetty(h):
    ax, ay = h["landing"]
    bx, by, _z = outside(h)
    return {(x, ay, 7) for x in range(min(ax, bx), max(ax, bx) + 1)} | {
        (bx, y, 7) for y in range(min(ay, by), max(ay, by) + 1)}


def railings(h, values, cells):
    x0, y0, x1, y1 = h["box"]
    sides = [([(x, y0 - 2, 7) for x in range(x0 - 1, x1 + 2)], (20297, 20283, 20284), 434),
             ([(x, y1 + 2, 7) for x in range(x0 - 1, x1 + 2)], (20298, 20286, 20287), 435),
             ([(x0 - 2, y, 7) for y in range(y0 - 1, y1 + 2)], (20290, 20291, 20299), 436),
             ([(x1 + 2, y, 7) for y in range(y0 - 1, y1 + 2)], (20288, 20289, 20300), 437)]
    bridge = jetty(h)
    for line, (start, mid, end), lip in sides:
        run = []
        for p in line + [None]:
            old = values.get(p, [])
            if (p is not None and p not in bridge and old and old[0] in WATER
                    and all(i in range(20282, 20301) or i in (434, 435, 436, 437) for i in old[1:])):
                run.append(p)
                continue
            if len(run) > 1:
                for i, q in enumerate(run):
                    cells[q] = ([values[q][0], lip, start if i == 0 else end if i == len(run) - 1 else mid], False)
            run = []


def free(ids, otb, doors=False):
    return bool(ids) and otb[ids[0]]["group"] == "ground" and not any(
        "block_solid" in otb[i]["flags"] for i in ids if not (doors and i in (1212, 1219)))


def public_reach(values, start, region, otb):
    seen, todo = set(), [start]
    while todo:
        p = todo.pop()
        if p in seen or p not in region or not free(values.get(p, []), otb):
            continue
        seen.add(p)
        x, y, z = p
        todo.extend((x + dx, y + dy, z) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    return seen


def plan(values):
    cells = {}
    for h in HOUSES:
        x0, y0, x1, y1 = h["box"]
        post, horiz, vert, corner = WALLS[h["style"]]
        floor = 406 if h["style"] == "marble" else 405
        for p in deck(h) | jetty(h):
            cells[p] = ([405], False)
        railings(h, values, cells)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                p = x, y, 7
                wall = x in (x0, x1) or y in (y0, y1)
                if not wall:
                    cells[p] = ([floor], True)
                    continue
                piece = (post if (x, y) == (x0, y0) else corner if (x, y) == (x1, y1)
                         else horiz if y in (y0, y1) and x != x0 else vert)
                base = [floor]
                if (x, y) == h["door"]:
                    cells[p] = ([floor, 1212 if h["side"] == "s" else 1219], True)
                else:
                    if h["style"] == "timber":
                        if y == y0 and x == x0 + 1:
                            piece = 1263
                        elif x == x1 and y == y0 + 1:
                            piece = 1264
                    light = [20353] if h["style"] == "marble" and (x, y) == (x1, y1) else []
                    cells[p] = (base + [piece] + light, False)
        # Eaves: oeste/norte sobre el muro; una fila de vuelo al sur, como River Street.
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 2):
                p = x, y, 6
                row = 0 if y == y0 else 2 if y == y1 + 1 else 1
                edges, center = ((950, 951, 954), (945, 947, 949)) if h["roof"] == 945 else ((940, 941, 943), (935, 936, 938))
                items = [(edges if x == x0 else center)[row]]
                cells[p] = (items, False)
    # La vista de la casa élfica también queda libre de lava, preservando el borde de tierra vecino.
    elf = next(h for h in HOUSES if h["style"] == "marble")
    view = {(x + dx, y + dy, 7) for x, y, _z in deck(elf)
            for dx in range(-10, 11) for dy in range(-8, 9)}
    for p in view:
        old = values.get(p, [])
        if old and old[0] in (598, 599, 600, 601):
            cells[p] = ([4608] + old[1:], False)
    # El árbol de la orilla no debe tapar la pasarela de Willow Nook.
    source, target = (92, 60, 7), (92, 64, 7)
    cells[source] = ([i for i in values[source] if i != 2701], False)
    cells[target] = (list(values[target]) + ([] if 2701 in values[target] else [2701]), False)
    return cells


def validate(values, cells, otb):
    registry = ET.parse(REGISTRY).getroot()
    new_names = {h["name"] for h in HOUSES}
    old_house_tiles = {(int(t.get("x")), int(t.get("y")), int(t.get("z")))
                       for h in registry if h.get("name") not in new_names for t in h}
    if old_house_tiles & cells.keys():
        raise ValueError("Una casa nueva pisa una existente")
    previous = json.loads(MANIFEST.read_text()).get("cells", {}) if MANIFEST.exists() else {}
    for p, (ids, _pz) in cells.items():
        old = values.get(p, [])
        if p[2] == 7 and free(old, otb) and not free(ids, otb):
            raise ValueError(f"La plataforma bloquea un paso público previo: {p}")
        if old and old[0] in (598, 599, 600, 601) and ids == [4608] + old[1:]:
            continue
        if p[2] == 6 and old and previous.get(",".join(map(str, p))) != old:
            raise ValueError(f"Techo ocupado: {p} {old}")
        if p[2] == 7 and previous.get(",".join(map(str, p))) != old:
            if not old or old[0] not in {4756, 405, 406, 4526} | WATER or any(
                    i not in DECOR and i not in range(4644, 4656) for i in old[1:]):
                raise ValueError(f"Terreno/objetos ajenos: {p} {old}")
        if any(i not in otb for i in ids):
            raise ValueError(f"Item desconocido: {p} {ids}")
    merged = values | {p: ids for p, (ids, _pz) in cells.items()}
    elf = next(h for h in HOUSES if h["style"] == "marble")
    if any(merged.get((x + dx, y + dy, 7), [None])[0] in (598, 599, 600, 601)
           for x, y, _z in deck(elf) for dx in range(-9, 10) for dy in range(-7, 8)):
        raise ValueError("Lava visible desde la plataforma élfica")
    for h in HOUSES:
        for p in deck(h):
            old = values.get(p, [])
            if previous.get(",".join(map(str, p))) != old and (len(old) != 1 or old[0] not in WATER):
                raise ValueError(f"La plataforma debe estar enteramente sobre agua: {h['name']} {p}")
        # Todas las casillas interiores y el acceso quedan libres al abrir la puerta.
        owner = DATA / "houses" / (h["name"] + ".xml")
        if owner.exists():
            owner_root = ET.parse(owner).getroot()
            o = owner_root.find("owner")
            if o is None or o.get("name"):
                raise ValueError(f"No modificar dueño existente: {owner}")
            front = owner_root.find("frontdoor")
            if front is None or tuple(int(front.get(k, "0")) for k in ("x", "y", "z")) != (*h["door"], 7):
                raise ValueError(f"Puerta existente diferente: {owner}")
        if not free(merged.get(outside(h), []), otb):
            raise ValueError(f"Salida bloqueada: {h['name']} {outside(h)}")
        want = positions(h) | {(*h["door"], 7)}
        if not all(free(merged[p], otb, doors=True) for p in want):
            raise ValueError(f"Interior bloqueado: {h['name']}")
        seen, todo = set(), [(*h["door"], 7)]
        while todo:
            p = todo.pop()
            if p not in want or p in seen:
                continue
            seen.add(p)
            x, y, z = p
            todo.extend((x + dx, y + dy, z) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if seen != want:
            raise ValueError(f"Cuarto aislado: {h['name']}")
        x0, y0, x1, y1 = h["box"]
        region = {(x, y, 7) for x in range(x0 - 6, x1 + 7) for y in range(y0 - 6, y1 + 7)}
        ring = {(x, y, z) for x, y, z in region
                if (x in (x0 - 1, x1 + 1) and y0 - 1 <= y <= y1 + 1)
                or (y in (y0 - 1, y1 + 1) and x0 - 1 <= x <= x1 + 1)}
        landing = (*h["landing"], 7)
        if not free(values.get(landing, []), otb):
            raise ValueError(f"Desembarco sin acceso en tierra: {h['name']}")
        before = public_reach(values, landing, region, otb)
        after = public_reach(merged, outside(h), region, otb)
        if landing not in after or not (ring & before) <= after:
            raise ValueError(f"La casa corta un paso público: {h['name']}")
    # Ningún monstruo, NPC o escalera existente queda bajo una casa o techo nuevo.
    for file, tag in ((DATA / "world/test-spawn.xml", "spawn"), (DATA / "world/npc.xml", "npc")):
        root = ET.parse(file).getroot()
        for block in root:
            if tag == "npc":
                points = [(int(block.get(k, "0")) for k in ("x", "y", "z"))]
            else:
                x, y, z = [int(block.get(k, "0")) for k in ("centerx", "centery", "centerz")]
                points = [(x + int(m.get("x", "0")), y + int(m.get("y", "0")), int(m.get("z", z))) for m in block]
            for p in points:
                p = tuple(p)
                if p in cells:
                    raise ValueError(f"{tag} dentro de la huella: {p}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    otb = load_otb()
    nodes, values, areas = index(root, otb)
    if any(len(ns) != 1 for ns in nodes.values()):
        raise ValueError("Mapa con casillas duplicadas")
    cells = plan(values)
    validate(values, cells, otb)
    changed = 0
    for p, (ids, pz) in sorted(cells.items()):
        old = nodes.get(p, [])
        if old:
            tile = old[0]
            if tile[0] != 5 or any(c[0] != 6 or len(c[1]) != 2 or c[2] for c in tile[2]):
                raise ValueError(f"Casa/atributos protegidos: {p}")
        else:
            x, y, z = p
            key = x // 256 * 256, y // 256 * 256, z
            if key not in areas:
                areas[key] = [4, bytearray(struct.pack("<HHB", *key)), []]
                root[2][0][2].append(areas[key])
            tile = [5, bytearray([x % 256, y % 256]), []]
            areas[key][2].append(tile)
        before = serialize_tree(tile, b"")
        old_flags = tile_flags(tile[1])
        flags = struct.unpack_from("<I", old_flags, 1)[0] if old_flags else 0
        flags = (flags & ~1) | int(pz)
        props = tile[1][:2] + (struct.pack("<BI", 3, flags) if flags else b"")
        has_ground = otb[ids[0]]["group"] == "ground"
        tile[1] = props + (struct.pack("<BH", 9, ids[0]) if has_ground else b"")
        tile[2] = [[6, bytearray(struct.pack("<H", sid)), []] for sid in ids[1 if has_ground else 0:]]
        changed += before != serialize_tree(tile, b"")
    for h in HOUSES:
        print(f"{h['name']}: {len(positions(h))} sqm; puerta {h['door']}; salida {outside(h)}")
    print(f"Mapa: {changed} casillas modificadas")
    if args.dry_run:
        return
    backup = REPO / "backups/map" / ("curious-houses-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    for f in (MAP, REGISTRY):
        shutil.copy2(f, backup / f.name)
    text = REGISTRY.read_text()
    for h in HOUSES:
        house = DATA / "houses" / (h["name"] + ".xml")
        if not house.exists():
            x, y = h["door"]
            house.write_text(f'<?xml version="1.0"?>\n<house><frontdoor x="{x}" y="{y}" z="7"/><owner name=""/></house>\n')
        entry = ET.fromstring(text).find(f'house[@name="{h["name"]}"]')
        if entry is None:
            body = "\n".join(f'<tile x="{x}" y="{y}" z="{z}" />' for x, y, z in sorted(positions(h)))
            text = text.replace("</houses>", f'<house name="{h["name"]}">\n{body}\n</house>\n</houses>')
        elif {(int(t.get("x")), int(t.get("y")), int(t.get("z"))) for t in entry} != positions(h):
            raise ValueError(f"Registro diferente para {h['name']}")
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    REGISTRY.write_text(text)
    MANIFEST.write_text(json.dumps(dict(version=2, retired=["Kongra Hideout"], houses=HOUSES,
        cells={",".join(map(str, p)): ids for p, (ids, _pz) in sorted(cells.items())}), separators=(",", ":")) + "\n")
    print(f"Aplicado; respaldo: {backup}")


if __name__ == "__main__":
    main()
