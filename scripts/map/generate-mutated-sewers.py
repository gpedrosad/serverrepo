#!/usr/bin/env python3
"""Alcantarilla Profunda y Cloacas Mutadas bajo el centro de la ciudad (z10-z11).

Entrada dentro de las cloacas actuales (bajada 152,54,7 -> caminar al este hasta 168,53,8):
  z8   bajada 469 en 168,53,8 (sur 168,54,8 libre) + cartel en 169,53,8
  z9   antesala chica de piedra (x165-169, y50-54), escalera 1386 en 168,53,9 y bajada 469 en 166,51,9
  z10  Cloacas de las Ratas (Lv 8-20): Rat, Cave Rat y Slime; bajada 469 al fondo en 168,74,10
  z11  Alcantarilla Mutada (Lv 25-45): Mutated Human -> Mutated Rat -> Mutated Bat -> Mutated Tiger / Bog Raider

Solo ocupa vacio o roca [101] (salvo los dos tiles de entrada en z8); preserva lo ajeno y es idempotente.
Uso:
  python3 scripts/map/generate-mutated-sewers.py --dry-run [--preview /tmp/sewers]
  python3 scripts/map/generate-mutated-sewers.py
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

spec = importlib.util.spec_from_file_location("sewers_helpers", HERE / "generate-imperial-crypt.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

WORLD = MAP.parent
MANIFEST = WORLD / "generated-mutated-sewers.json"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"

ENTRY8 = (168, 53)
SIGN8 = (169, 53)
DOWN9 = (166, 51)
DOWN10 = (168, 74)

# z10: Cloacas de las Ratas (U larga, columnas a 14 casillas: x153 y x167)
BOX10 = (145, 38, 177, 94)
PATH10 = [DOWN9, (167, 44), (153, 44), (153, 86), (168, 86), DOWN10]
STAGES10 = (
    (("Rat", "Cave Rat"), 2, 70, 10),
    (("Rat", "Cave Rat"), 2, 75, 10),
    (("Cave Rat", "Slime"), 2, 105, 11),
)

# z11: Alcantarilla Mutada (serpentina, filas a 14 casillas: y74, y60, y46, y32)
BOX11 = (144, 26, 193, 86)
PATH11 = [DOWN10, (152, 74), (152, 60), (184, 60), (184, 46), (152, 46), (152, 32), (184, 32)]
STAGES11 = (
    (("Mutated Human",), 1, 115, 12),
    (("Mutated Human", "Mutated Rat"), 1, 130, 12),
    (("Mutated Rat", "Mutated Bat"), 2, 160, 11),
    (("Mutated Bat", "Mutated Tiger"), 2, 195, 11),
    (("Mutated Tiger", "Bog Raider"), 2, 235, 11),
)

STONE_FLOOR, DARK_FLOOR, MUD_FLOOR = 431, 966, 355
PROPS_SEWER = (3767, 1353, 1309, 2602)
FLOOR_NO_BLOCK = (2248, 4170)


def validate_walls(tmap: dict, floor: set, stone: bool = True):
    for p, ids in tmap.items():
        if p not in floor:
            want = C.pieces_for(C.neighbors_in(floor, *p), C.WALL_SIDE, C.WALL_CORNER, C.WALL_INNER)
            assert want is not None and len(want) <= 1, f"Pared ambigua en {p}: {want}"
            expected = (want[0] + (15 if stone else 0)) if want else 101
            assert ids[0] == expected, f"Pared incorrecta en {p}: {ids} vs {expected}"


def to_stone_walls(tmap: dict):
    for ids in tmap.values():
        if 356 <= ids[0] <= 367:
            ids[0] += 15


def build_floor_cave(box_rect, path, start, end_hole, stages, seed, rng_key, z, min_floor,
                     min_dens, max_dens, mud_ratio=0.25):
    x0, y0, x1, y1 = box_rect
    box = {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    inner = {(x, y) for x in range(x0 + 3, x1 - 2) for y in range(y0 + 3, y1 - 2)}
    rooms = C.rooms_along(path)
    band, core = C.ribbon(path, rooms, seed)
    core = (core & inner) | C.grow({start}, 1)
    if end_hole:
        core |= C.grow({end_hole}, 1)
    floor = C.carve_cave(seed, band & inner, core, start, min_floor)
    tmap = C.cave_tiles(floor, box, seed)
    paved = C.stamp(path, 0)
    rng = random.Random(rng_key)
    for p in floor:
        if p in paved:
            tmap[p] = [DARK_FLOOR if (p[0] // 5 + p[1] // 5) % 3 == 0 else STONE_FLOOR]
        elif ((p[0] // 3 * 31 + p[1] // 3 * 17 + seed) % 13) < max(2, int(mud_ratio * 10)):
            tmap[p] = [MUD_FLOOR]
        else:
            tmap[p] = [STONE_FLOOR]
    keep = C.grow({start}, 3) | ({(start[0], start[1] + 1)} if start else set())
    if end_hole:
        keep |= C.grow({end_hole}, 3) | {(end_hole[0], end_hole[1] + 1)}
    C.place_props(tmap, floor, start, PROPS_SEWER, 0.14, seed, keep)
    # Huesos y hongos no bloqueantes cerca de paredes
    for p in sorted(floor - keep):
        if len(tmap[p]) == 1 and any(q not in floor for q in C.grow({p}, 1)) and rng.random() < 0.05:
            tmap[p].append(rng.choice(FLOOR_NO_BLOCK))
    # Telaranas en paredes norte/oeste
    for p, ids in tmap.items():
        if ids[0] in (C.WALL_SIDE["n"], C.WALL_SIDE["w"]) and (p[0] * 7 + p[1] * 13) % 19 == 0:
            ids.append(1906 if ids[0] == C.WALL_SIDE["n"] else 1907)
    bl = C.Blocking()
    walk = {p for p in floor if bl.walkable(tmap[p])}
    distances = C.reach(walk, start, C.NP.CARD)
    assert walk == set(distances), f"z{z}: decoracion corta el recorrido"
    if end_hole:
        assert end_hole in walk and (end_hole[0], end_hole[1] + 1) in walk, f"z{z}: bajada bloqueada"
        assert distances[end_hole] >= 50, f"z{z}: recorrido muy corto ({distances[end_hole]})"
    tmap[start] = [STONE_FLOOR, 1386]
    if end_hole:
        tmap[end_hole] = [469]
        tmap[(end_hole[0], end_hole[1] + 1)] = [STONE_FLOOR]
    to_stone_walls(tmap)
    validate_walls(tmap, floor, stone=True)
    avoid = C.grow({start}, 6)
    if end_hole:
        avoid |= C.grow({end_hole}, 5)
    spawns = C.place_stages(stages, C.slices_by(walk - avoid, distances.__getitem__, len(stages)),
                            walk, avoid, z, random.Random(f"{rng_key}-spawns"))
    positions = [p for _, _, ms in spawns for _, p, _ in ms]
    assert len(positions) == len(set(positions)) and all(p in walk for p in positions)
    assert positions, f"z{z}: sin spawns"
    density = len(walk) / len(positions)
    assert min_dens < density < max_dens, f"z{z}: densidad {density:.1f} fuera de ({min_dens}, {max_dens})"
    return tmap, floor, walk, spawns, round(density, 1)


def build(values, otb):
    previous = json.loads(MANIFEST.read_text())["cells"] if MANIFEST.exists() else {}
    bl = C.Blocking()

    t10, floor10, walk10, spawns10, dens10 = build_floor_cave(
        BOX10, PATH10, DOWN9, DOWN10, STAGES10, 101, "mutated-sewers-z10", 10,
        min_floor=420, min_dens=14, max_dens=45, mud_ratio=0.18,
    )
    t11, floor11, walk11, spawns11, dens11 = build_floor_cave(
        BOX11, PATH11, DOWN10, None, STAGES11, 111, "mutated-sewers-z11", 11,
        min_floor=900, min_dens=25, max_dens=58, mud_ratio=0.30,
    )

    # Antesala en z9 (bloque 2x2 en x166-169, y51-54: vacio en z9)
    shaft9 = {(x, y) for x in range(166, 170) for y in range(51, 54)}
    t9 = C.cave_tiles(shaft9, C.grow(shaft9, 1), 91)
    for p in shaft9:
        t9[p] = [STONE_FLOOR]
    t9[ENTRY8] = [STONE_FLOOR, 1386]
    t9[DOWN9] = [469]
    t9[(DOWN9[0], DOWN9[1] + 1)] = [STONE_FLOOR]
    t9[(169, 51)] = [STONE_FLOOR, 2602]  # brasero fijo iluminando
    to_stone_walls(t9)
    validate_walls(t9, shaft9, stone=True)

    cells = {}
    for z, tmap in ((9, t9), (10, t10), (11, t11)):
        for (x, y), ids in tmap.items():
            cells[x, y, z] = ids

    # Relleno de pantalla (evita vacio negro en mismo piso) SOLO en vacio/propio
    for z, fl in ((9, shaft9), (10, floor10), (11, floor11)):
        for x, y in C.grow(fl, 9):
            p = x, y, z
            if p not in cells and (p not in values or previous.get(",".join(map(str, p))) == [101]):
                cells[p] = [101]

    # Techo de roca en z-1 donde no haya tile (evita "se ve lo de arriba")
    def walkable_existing(pos):
        if pos in cells:
            return bl.walkable(cells[pos])
        return bl.walkable(values.get(pos, []))

    for z_up, fl in ((9, floor10), (10, floor11)):
        for x, y in C.grow(fl, 2):
            p = x, y, z_up
            if p in cells:
                continue
            if p in values and previous.get(",".join(map(str, p))) != [101]:
                continue
            # No poner roca pelada pegada a un piso caminable de z_up
            if any(walkable_existing((x + dx, y + dy, z_up)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                continue
            cells[p] = [101]

    # Entrada en la cloaca existente de z8 (168,53,8 -> 469, cartel en 169,53,8)
    entry_cells = {
        (*ENTRY8, 8): [469],
        (*SIGN8, 8): [407, 1429],
    }
    cells.update(entry_cells)

    merged = values | cells
    for up, z in ((ENTRY8, 8), (DOWN9, 9), (DOWN10, 10)):
        x, y = up
        assert cells[x, y, z] == [469], f"Falta bajada 469 en {up} z{z}"
        assert 1386 in cells[x, y, z + 1], f"Falta escalera 1386 en {up} z{z+1}"
        assert bl.walkable(merged.get((x, y + 1, z), [])), f"Salida sur bloqueada: {up} z{z}"
        assert bl.walkable(merged.get((x, y, z + 1), [])), f"Aterrizaje bloqueado: {up} z{z+1}"

    # Distancia minima de 3 casillas respecto de cualquier piso preexistente en z9, z10, z11
    for z, fl in ((9, shaft9), (10, floor10), (11, floor11)):
        foreign = {(x, y) for (x, y, zz), ids in values.items()
                   if zz == z and bl.walkable(ids) and f"{x},{y},{zz}" not in previous}
        overlap = C.grow(fl, 3) & foreign
        assert not overlap, f"z{z}: demasiado cerca de piso ajeno: {sorted(overlap)[:5]}"

    spawns = spawns10 + spawns11
    report = dict(
        z10=dict(walkable=len(walk10), density=dens10, spawns=len(spawns10)),
        z11=dict(walkable=len(walk11), density=dens11, spawns=len(spawns11)),
        entry=[*ENTRY8, 8],
        entry_cells=[list(p) for p in entry_cells],
    )
    style_cells(cells, values, otb)
    return cells, spawns, report


def block(text, key, body, close):
    marked = f"\t<!-- BEGIN {key} (scripts/map/generate-mutated-sewers.py) -->\n{body}\n\t<!-- END {key} -->\n"
    pattern = rf"[ \t]*<!-- BEGIN {key}(?: \([^>]*\))? -->.*?<!-- END {key} -->\n?"
    return re.sub(pattern, lambda _: marked, text, flags=re.S) if re.search(pattern, text, re.S) else text.replace(close, marked + close)


def render_preview(prefix: Path, cells: dict):
    tiles = load_tiles()
    tiles.update(cells)
    r = Renderer()
    for z, rect, hl in ((10, BOX10, DOWN9), (11, BOX11, DOWN10)):
        x0, y0, x1, y1 = rect
        W, H, img = r.area(tiles, x0 - 1, y0 - 1, x1 + 1, y1 + 1, z, highlight=hl)
        Path(f"{prefix}-z{z}.png").write_bytes(png_bytes(W, H, img))


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
    entry_set = {tuple(p) for p in report["entry_cells"]}
    orig_entry = {(*ENTRY8, 8): [407], (*SIGN8, 8): [407]}
    for p, ids in cells.items():
        old = values.get(p)
        owned = previous.get(",".join(map(str, p))) == old
        if p in entry_set and not owned and old != orig_entry[p]:
            raise ValueError(f"Entrada modificada por otra zona: {p}: {old}")
        if p not in entry_set and old not in (None, [101]) and not owned:
            raise ValueError(f"Tile ajeno protegido: {p}: {old}")
        for tile in nodes.get(p, []):
            assert tile[0] == 5 and not tile_flags(tile[1]), f"Casa/flags protegidos: {p}"
            assert all(c[0] == 6 and len(c[1]) == 2 and not c[2] for c in tile[2]), f"Atributos protegidos: {p}"

    sp = SPAWNS.read_text(encoding="latin-1")
    spawn_text = block(sp, "MUTATED_SEWERS_SPAWNS", C.spawn_xml(spawns), "</spawns>")
    signs = READABLES.read_text(encoding="latin-1")
    sign_text = block(
        signs, "MUTATED_SEWERS_SIGNS",
        '\t<readable x="169" y="53" z="8" text="DEEP SEWERS\\nLevel 8-20: Rats and Slimes below.\\nBeyond: Mutated Sewers (level 25-45)."/>',
        "</readables>",
    )
    changed = sum(values.get(p) != ids for p, ids in cells.items())
    counts = Counter(n for _, _, ms in spawns for n, _, _ in ms)
    print(json.dumps(report | dict(changed=changed, monsters=dict(counts)), ensure_ascii=False))
    if args.preview:
        render_preview(args.preview, cells)
    if args.dry_run:
        return

    backup = REPO / "backups/map" / ("mutated-sewers-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
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
        name="mutated-sewers", version=1, down9=[*DOWN9, 9], down10=[*DOWN10, 10],
        monsters=dict(counts), **report,
        cells={",".join(map(str, p)): ids for p, ids in sorted(cells.items())},
    ), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
