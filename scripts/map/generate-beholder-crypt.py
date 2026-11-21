#!/usr/bin/env python3
"""Cripta de los Ojos y Vampiros al oeste del Castillo Imperial (z10).

Entrada en el jardin oeste de la isla noroeste (78,34,7; salida sur 78,35,7 libre, cartel en 77,34,7):
  z7   agujero 469 en 78,34,7 + cartel 1429 en 77,34,7
  z8   pasillo petreo corto hacia el norte (78,34 -> 78,24) para esquivar el Santuario Petrificado (z9 y>=28)
  z9   antesala petrea chica (x76-79, y22-25): escalera 1386 en 78,24,9 y bajada 469 en 77,23,9
  z10  Cripta de los Ojos y Vampiros (Lv 30-65):
       Ghoul / Gazer -> Beholder / Crypt Shambler -> Beholder / Vampire -> Elder Beholder / Vampire -> Vampire Bride / Banshee

Solo ocupa vacio o roca [101] (salvo los 2 tiles de entrada en z7); preserva lo ajeno y es idempotente.
Uso:
  python3 scripts/map/generate-beholder-crypt.py --dry-run [--preview /tmp/beholder]
  python3 scripts/map/generate-beholder-crypt.py
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
import random
import re
import shutil
import struct
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "kb")]
from mapdata import MAP, REPO, Renderer, load_otb, load_tiles, parse_tree, png_bytes, serialize_tree
from hole_entrance_style import style_cells
from epstein_cave_repair import index
from portal_citadel_layout import tile_flags

spec = importlib.util.spec_from_file_location("beholder_helpers", HERE / "generate-imperial-crypt.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

WORLD = MAP.parent
MANIFEST = WORLD / "generated-beholder-crypt.json"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"

MOUTH = (78, 34)
SIGN = (77, 34)
DOWN8 = (78, 24)
DOWN9 = (77, 23)

# z10: x16..82, y18..86 (100% libre bajo el oeste del mapa; techo natural parcial en z9)
BOX10 = (16, 18, 82, 86)
# Serpentina en 4 filas a 14 casillas (y34, y48, y62, y76), partiendo desde DOWN9 (77,23)
PATH10 = [DOWN9, (77, 34), (24, 34), (24, 48), (66, 48), (66, 62), (24, 62), (24, 76), (66, 76)]
STAGES10 = (
    (("Ghoul", "Gazer"), 1, 110, 12),
    (("Beholder", "Crypt Shambler"), 1, 140, 12),
    (("Beholder", "Vampire"), 2, 175, 12),
    (("Elder Beholder", "Vampire"), 2, 210, 12),
    (("Vampire Bride", "Banshee"), 2, 250, 12),
)

STONE_FLOOR, DARK_FLOOR = 431, 966
PROPS_CRYPT = (1515, 3767, 1452, 1453, 2602)


def validate_walls(tmap: dict, floor: set):
    for p, ids in tmap.items():
        if p not in floor:
            want = C.pieces_for(C.neighbors_in(floor, *p), C.WALL_SIDE, C.WALL_CORNER, C.WALL_INNER)
            assert want is not None and len(want) <= 1, f"Pared ambigua en {p}: {want}"
            expected = (want[0] + 15) if want else 101
            assert ids[0] == expected, f"Pared incorrecta en {p}: {ids} vs {expected}"


def to_stone_walls(tmap: dict):
    for ids in tmap.values():
        if 356 <= ids[0] <= 367:
            ids[0] += 15


def build(values, otb):
    previous = json.loads(MANIFEST.read_text())["cells"] if MANIFEST.exists() else {}
    bl = C.Blocking()

    # z8: corredor corto de 2 de ancho hacia el norte (x77-78, y24-35) — esquiva z9 y>=28 del Santuario
    fl8 = {(x, y) for x in (77, 78) for y in range(24, 36)}
    t8 = C.cave_tiles(fl8, C.grow(fl8, 1), 83)
    for p in fl8:
        t8[p] = [STONE_FLOOR if (p[0] + p[1]) % 2 == 0 else DARK_FLOOR]
    t8[MOUTH] = [STONE_FLOOR, 1386]
    t8[DOWN8] = [469]
    t8[(DOWN8[0], DOWN8[1] + 1)] = [STONE_FLOOR]
    t8[(77, 30)] = [STONE_FLOOR, 2602]
    to_stone_walls(t8)
    validate_walls(t8, fl8)

    # z9: antesala petrea en x77-78, y23-25 (y<=25 -> su pared termina en y=26, lejos de y>=28 del Santuario!)
    fl9 = {(x, y) for x in (77, 78) for y in (23, 24, 25)}
    t9 = C.cave_tiles(fl9, C.grow(fl9, 1), 93)
    for p in fl9:
        t9[p] = [STONE_FLOOR]
    t9[DOWN8] = [STONE_FLOOR, 1386]
    t9[DOWN9] = [469]
    t9[(DOWN9[0], DOWN9[1] + 1)] = [STONE_FLOOR]
    t9[(78, 23)] = [STONE_FLOOR, 2602]
    to_stone_walls(t9)
    validate_walls(t9, fl9)

    # z10: Cripta principal
    x0, y0, x1, y1 = BOX10
    box = {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    inner = {(x, y) for x in range(x0 + 3, x1 - 2) for y in range(y0 + 3, y1 - 2)}
    rooms = C.rooms_along(PATH10)
    band, core = C.ribbon(PATH10, rooms, 103)
    core = (core & inner) | C.grow({DOWN9}, 1)
    floor10 = C.carve_cave(103, band & inner, core, DOWN9, 1100)
    t10 = C.cave_tiles(floor10, box, 103)

    paved = C.stamp(PATH10, 0)
    rng = random.Random("beholder-crypt-103")
    for p in floor10:
        if p in paved and (p[0] // 5 + p[1] // 5) % 3 == 0:
            t10[p] = [DARK_FLOOR]
        else:
            t10[p] = [STONE_FLOOR]

    keep = C.grow({DOWN9}, 3) | {(DOWN9[0], DOWN9[1] + 1)}
    C.place_props(t10, floor10, DOWN9, PROPS_CRYPT, 0.16, 103, keep)
    # Calaveras/huesos enteros (2248) junto a paredes
    for p in sorted(floor10 - keep):
        if len(t10[p]) == 1 and any(q not in floor10 for q in C.grow({p}, 1)) and rng.random() < 0.05:
            t10[p].append(2248)
    # Telaranas y antorchas/decoracion de pared
    for p, ids in t10.items():
        if ids[0] in (C.WALL_SIDE["n"], C.WALL_SIDE["w"]) and (p[0] * 3 + p[1] * 7) % 13 == 0:
            ids.append(1906 if ids[0] == C.WALL_SIDE["n"] else 1907)
        elif ids[0] == C.WALL_SIDE["n"] and (p[0] + p[1]) % 11 == 0:
            ids.append(20259)

    walk10 = {p for p in floor10 if bl.walkable(t10[p])}
    distances = C.reach(walk10, DOWN9, C.NP.CARD)
    assert walk10 == set(distances), "z10: decoracion corta el recorrido"
    t10[DOWN9] = [STONE_FLOOR, 1386]
    to_stone_walls(t10)
    validate_walls(t10, floor10)

    cells = {}
    for z, tmap in ((8, t8), (9, t9), (10, t10)):
        for (x, y), ids in tmap.items():
            cells[x, y, z] = ids

    # Relleno de pantalla (sin vacio negro) SOLO donde no existe tile
    for z, fl in ((8, fl8), (9, fl9), (10, floor10)):
        for x, y in C.grow(fl, 9):
            p = x, y, z
            if p not in cells and (p not in values or previous.get(",".join(map(str, p))) == [101]):
                cells[p] = [101]

    # Techo en z-1 donde no haya tile (sin poner roca pegada a piso caminable de z-1)
    def walkable_existing(pos):
        if pos in cells:
            return bl.walkable(cells[pos])
        return bl.walkable(values.get(pos, []))

    for z_up, fl in ((8, fl9), (9, floor10)):
        for x, y in C.grow(fl, 2):
            p = x, y, z_up
            if p in cells:
                continue
            if p in values and previous.get(",".join(map(str, p))) != [101]:
                continue
            if any(walkable_existing((x + dx, y + dy, z_up)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                continue
            cells[p] = [101]

    surface = {
        (*MOUTH, 7): [469],
        (*SIGN, 7): [4756, 1429],
    }
    cells.update(surface)

    merged = values | cells
    for up, z in ((MOUTH, 7), (DOWN8, 8), (DOWN9, 9)):
        x, y = up
        assert cells[x, y, z] == [469], f"Falta bajada 469 en {up} z{z}"
        assert 1386 in cells[x, y, z + 1], f"Falta escalera 1386 en {up} z{z+1}"
        assert bl.walkable(merged.get((x, y + 1, z), [])), f"Salida sur bloqueada: {up} z{z}"
        assert bl.walkable(merged.get((x, y, z + 1), [])), f"Aterrizaje bloqueado: {up} z{z+1}"

    # Respetar distancia de 3 casillas respecto de pisos preexistentes en z8-z10
    for z, fl in ((8, fl8), (9, fl9), (10, floor10)):
        foreign = {(x, y) for (x, y, zz), ids in values.items()
                   if zz == z and bl.walkable(ids) and f"{x},{y},{zz}" not in previous}
        overlap = C.grow(fl, 3) & foreign
        assert not overlap, f"z{z}: demasiado cerca de piso ajeno: {sorted(overlap)[:5]}"

    avoid = C.grow({DOWN9}, 6)
    spawns = C.place_stages(STAGES10, C.slices_by(walk10 - avoid, distances.__getitem__, len(STAGES10)),
                            walk10, avoid, 10, random.Random("beholder-crypt-spawns-103"))
    positions = [p for _, _, ms in spawns for _, p, _ in ms]
    assert len(positions) == len(set(positions)) and all(p in walk10 for p in positions)
    density = len(walk10) / len(positions)
    assert 25 < density < 60, f"Densidad fuera de rango: {density:.1f}"

    report = dict(
        walkable=len(walk10),
        density=round(density, 1),
        spawns=len(spawns),
        maxDistance=max(distances.values()),
        entry=[*MOUTH, 7],
        surface=[list(p) for p in surface],
    )
    style_cells(cells, values, otb)
    return cells, spawns, report


def block(text, key, body, close):
    marked = f"\t<!-- BEGIN {key} (scripts/map/generate-beholder-crypt.py) -->\n{body}\n\t<!-- END {key} -->\n"
    pattern = rf"[ \t]*<!-- BEGIN {key}(?: \([^>]*\))? -->.*?<!-- END {key} -->\n?"
    return re.sub(pattern, lambda _: marked, text, flags=re.S) if re.search(pattern, text, re.S) else text.replace(close, marked + close)


def render_preview(prefix: Path, cells: dict):
    tiles = load_tiles()
    tiles.update(cells)
    r = Renderer()
    x0, y0, x1, y1 = BOX10
    W, H, img = r.area(tiles, x0 - 1, y0 - 1, x1 + 1, y1 + 1, 10, highlight=DOWN9)
    Path(f"{prefix}-z10.png").write_bytes(png_bytes(W, H, img))
    W2, H2, img2 = r.area(tiles, 70, 26, 86, 40, 7, highlight=MOUTH)
    Path(f"{prefix}-z7.png").write_bytes(png_bytes(W2, H2, img2))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    args = ap.parse_args()

    raw = MAP.read_bytes()
    root = parse_tree(raw)
    otb = load_otb()
    nodes, values, areas = index(root, otb)
    assert all(len(ns) == 1 for ns in nodes.values()), "Casillas duplicadas"
    cells, spawns, report = build(values, otb)

    previous = json.loads(MANIFEST.read_text())["cells"] if MANIFEST.exists() else {}
    surf_set = {tuple(p) for p in report["surface"]}
    orig_surf = {(*MOUTH, 7): [4756], (*SIGN, 7): [4756]}
    for p, ids in cells.items():
        old = values.get(p)
        owned = previous.get(",".join(map(str, p))) == old
        if p in surf_set and not owned and old != orig_surf[p]:
            raise ValueError(f"Entrada modificada por otra zona: {p}: {old}")
        if p not in surf_set and old not in (None, [101]) and not owned:
            raise ValueError(f"Tile ajeno protegido: {p}: {old}")
        for tile in nodes.get(p, []):
            assert tile[0] == 5 and not tile_flags(tile[1]), f"Casa/flags protegidos: {p}"
            assert all(c[0] == 6 and len(c[1]) == 2 and not c[2] for c in tile[2]), f"Atributos protegidos: {p}"

    sp = SPAWNS.read_text(encoding="latin-1")
    spawn_text = block(sp, "BEHOLDER_CRYPT_SPAWNS", C.spawn_xml(spawns), "</spawns>")
    signs = READABLES.read_text(encoding="latin-1")
    sign_text = block(
        signs, "BEHOLDER_CRYPT_SIGNS",
        '\t<readable x="77" y="34" z="7" text="CRYPT OF EYES\\nLevel 30-65.\\nGazers and Beholders at the entrance; Vampires, Vampire Brides and Banshees deeper inside."/>',
        "</readables>",
    )
    changed = sum(values.get(p) != ids for p, ids in cells.items())
    counts = Counter(n for _, _, ms in spawns for n, _, _ in ms)
    print(json.dumps(report | dict(changed=changed, monsters=dict(counts)), ensure_ascii=False))
    if args.preview:
        render_preview(args.preview, cells)
    if args.dry_run:
        return

    backup = REPO / "backups/map" / ("beholder-crypt-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    for f in (MAP, SPAWNS, READABLES):
        shutil.copy2(f, backup / f.name)
    for (x, y, z), ids in sorted(cells.items()):
        key = x // 256 * 256, y // 256 * 256, z
        if key not in areas:
            areas[key] = [4, bytearray(struct.pack("<HHB", *key)), []]
            root[2][0][2].append(areas[key])
        if (x, y, z) in nodes:
            tile = nodes[x, y, z][0]
        else:
            tile = [5, bytearray([x % 256, y % 256]), []]
            areas[key][2].append(tile)
        ground = otb[ids[0]]["group"] == "ground"
        tile[1] = bytearray([x % 256, y % 256]) + (struct.pack("<BH", 9, ids[0]) if ground else b"")
        tile[2] = [C.item_node(i) for i in ids[1 if ground else 0:]]
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    SPAWNS.write_text(spawn_text, encoding="latin-1")
    READABLES.write_text(sign_text, encoding="latin-1")
    MANIFEST.write_text(json.dumps(dict(
        name="beholder-crypt", version=1, down8=[*DOWN8, 8], down9=[*DOWN9, 9],
        monsters=dict(counts), **report,
        cells={",".join(map(str, p)): ids for p, ids in sorted(cells.items())},
    ), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
