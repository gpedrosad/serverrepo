#!/usr/bin/env python3
"""Cuevas de Bambú: bajada desde el claro de Bamboo Camp con tres salas de dificultad creciente.

  z7  claro de Bamboo Camp (x168-190, y92-110): escalera de bajada en 172,99.
  z8  pozo de entrada (5x5) con la escalera de subida y la bajada a z9.
  z9  cueva: sala 1 (Kongra/Sibang/Dworc), sala 2 (Dworc/Orc) y sala 3 (jefe Orc Warlord).

La cueva se construye en el hueco de z9 que queda debajo del campamento, sin tocar el pasillo
de mármol negro ni la zona de lava/demonios que ya existe al este y al sur.

Uso:
  python3 scripts/map/generate-bamboo-depths.py --dry-run --preview /tmp/bamboo-depth.png
  python3 scripts/map/generate-bamboo-depths.py
Re-ejecutable: borra las cajas z8/z9 y el bloque BAMBOO_DEPTHS_SPAWNS antes de reinsertar.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
import roomkit  # noqa: E402
from mapdata import REPO, T_AREA, T_ITEM, T_TILE, parse_tree, png_bytes, serialize_tree  # noqa: E402

_spec = importlib.util.spec_from_file_location("north_pass", HERE / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)
pieces_for, neighbors_in, reach, CARD = NP.pieces_for, NP.neighbors_in, NP.reach, NP.CARD
CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD = NP.CAVE_FLOOR, NP.CAVE_FLOOR_ALT, NP.CAVE_MUD
WALL_SIDE, WALL_CORNER, WALL_INNER = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER
ROCK = NP.ROCK
STAIR_DOWN, STAIRS_UP = NP.STAIR_DOWN, NP.STAIRS_UP

WORLD = REPO / "server/YurOTS/ots/data/world"
MAP = WORLD / "test.otbm"
SPAWNS = WORLD / "test-spawn.xml"

Z7, Z8, Z9 = 7, 8, 9
ENTRANCE = (172, 99)             # escalera de bajada en z7
SHAFT_UP = (172, 99)             # escalera de subida en z8 (misma x,y)
SHAFT_LAND = (172, 100)          # llegada real al bajar desde z7
SHAFT_DOWN = (172, 101)          # bajada de z8 a z9
DEPTHS_UP = (172, 101)           # escalera de subida en z9 (misma x,y)
DEPTHS_LAND = (172, 102)         # llegada real desde z8
CAMP_FIRE = 1423

ROOMS9 = {
    "sala1": (170, 93, 180, 102),
    "pasillo1": (181, 97, 183, 99),
    "sala2": (184, 92, 194, 100),
    "pasillo2": (195, 94, 197, 96),
    "sala3": (198, 86, 208, 96),
}
BOX8 = (169, 96, 175, 102)
BOX9 = (169, 85, 209, 103)


def rect(x0: int, y0: int, x1: int, y1: int) -> set:
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def make_tiles(floor: set, box: tuple[int, int, int, int], seed: int, z: int) -> dict:
    box_set = rect(*box)
    tiles = NP.cave_tiles(floor, box_set, seed)
    # El pozo de z8 es chico: menos barro y más piso limpio.
    if box == BOX8:
        for c in floor:
            tiles[c] = [CAVE_FLOOR]
    return {(x, y, z): ids for (x, y), ids in tiles.items()}


def to_map(tiles: dict) -> roomkit.Map:
    m = roomkit.Map()
    for pos, ids in tiles.items():
        m.ground(pos, ids[0])
        for iid in ids[1:]:
            m.add(pos, iid)
    return m


def spawn_group(center: tuple[int, int], z: int, mons: list[tuple[str, tuple[int, int], int]]):
    return (center, z, mons)


def build_spawns():
    return [
        # sala 1: dworcs y orcos básicos, el escalón más suave
        spawn_group((174, 95), Z9, [("Dworc Venomsniper", (174, 95), 175),
                                    ("Dworc Venomsniper", (175, 95), 175)]),
        spawn_group((177, 99), Z9, [("Dworc Fleshhunter", (177, 99), 175),
                                    ("Dworc Fleshhunter", (178, 99), 175)]),
        spawn_group((172, 97), Z9, [("Orc Warrior", (172, 97), 175),
                                    ("Orc Warrior", (172, 98), 175)]),
        # sala 2: la fauna del campamento (Kongra/Sibang) y berserkers
        spawn_group((188, 95), Z9, [("Kongra", (188, 95), 175), ("Kongra", (189, 95), 175)]),
        spawn_group((191, 97), Z9, [("Sibang", (191, 97), 175), ("Sibang", (191, 98), 175)]),
        spawn_group((186, 93), Z9, [("Orc Berserker", (186, 93), 175),
                                    ("Orc Berserker", (187, 93), 175)]),
        # sala 3: jefe, líder y escolta
        spawn_group((203, 91), Z9, [("Orc Warlord", (203, 91), 900)]),
        spawn_group((200, 94), Z9, [("Orc Leader", (200, 94), 600)]),
        spawn_group((205, 94), Z9, [("Orc Shaman", (205, 94), 300)]),
        spawn_group((202, 88), Z9, [("Orc Berserker", (202, 88), 175),
                                    ("Orc Berserker", (203, 88), 175)]),
    ]


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def validate(m8: roomkit.Map, m9: roomkit.Map, spawns) -> list[str]:
    errs = []
    chk8, chk9 = roomkit.Checker(m8), roomkit.Checker(m9)
    p8 = lambda p: (p[0], p[1], Z8)
    p9 = lambda p: (p[0], p[1], Z9)
    # llegadas
    for label, m, pos in (("z8", chk8, p8(SHAFT_LAND)), ("z9", chk9, p9(DEPTHS_LAND))):
        if not m.walkable(pos):
            errs.append(f"{label}: llegada {pos} no caminable")
    if not chk8.walkable(p8(SHAFT_UP)) or not chk8.walkable(p8(SHAFT_DOWN)):
        errs.append("z8: escaleras no caminables")
    if not chk9.walkable(p9(DEPTHS_UP)):
        errs.append("z9: escalera de subida no caminable")
    # todas las salas de z9 conectadas desde la llegada
    floor9 = {p for p in m9.t if p[2] == Z9 and chk9.walkable(p)}
    start = p9(DEPTHS_LAND)
    seen = {start}
    todo = [start]
    while todo:
        x, y, z = todo.pop()
        for dx, dy in CARD:
            nxt = (x + dx, y + dy, z)
            if nxt in floor9 and nxt not in seen:
                seen.add(nxt)
                todo.append(nxt)
    if len(seen) != len(floor9):
        errs.append(f"z9: {len(floor9) - len(seen)} casillas caminables aisladas")
    for room, (x0, y0, x1, y1) in ROOMS9.items():
        missing = [(x, y, Z9) for (x, y) in rect(x0, y0, x1, y1) if not chk9.walkable((x, y, Z9))]
        if missing:
            errs.append(f"{room}: {len(missing)} casillas no caminables (ej. {missing[0]})")
    # spawns: existen, son caminables y no se repiten
    occupied = set()
    for (cx, cy), z, mons in spawns:
        for name, pos, _st in mons:
            p = (pos[0], pos[1], z)
            if p in occupied:
                errs.append(f"spawn {name} {p}: posición repetida")
            occupied.add(p)
            if not chk9.walkable(p):
                errs.append(f"spawn {name} {p}: casilla no caminable")
    return errs


def write_spawns(spawns, write: bool) -> bool:
    raw = SPAWNS.read_text(encoding="latin-1")
    pattern = re.compile(r"\t?<!-- BEGIN BAMBOO_DEPTHS_SPAWNS.*?<!-- END BAMBOO_DEPTHS_SPAWNS -->\n?", re.S)
    raw = pattern.sub("", raw)
    block = ("\t<!-- BEGIN BAMBOO_DEPTHS_SPAWNS (scripts/map/generate-bamboo-depths.py) -->\n"
             + spawn_xml(spawns) + "\n\t<!-- END BAMBOO_DEPTHS_SPAWNS -->\n")
    new = raw.replace("</spawns>", block + "\t</spawns>")
    if write and new != raw:
        SPAWNS.write_text(new, encoding="latin-1")
    return new == raw


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    args = ap.parse_args()

    floor8 = rect(170, 97, 174, 101)
    floor9 = set()
    for x0, y0, x1, y1 in ROOMS9.values():
        floor9 |= rect(x0, y0, x1, y1)

    t8 = make_tiles(floor8, BOX8, 41, Z8)
    t9 = make_tiles(floor9, BOX9, 42, Z9)
    t8[(SHAFT_UP[0], SHAFT_UP[1], Z8)] = [CAVE_FLOOR, STAIRS_UP]
    t8[(SHAFT_DOWN[0], SHAFT_DOWN[1], Z8)] = [STAIR_DOWN]
    t9[(DEPTHS_UP[0], DEPTHS_UP[1], Z9)] = [CAVE_FLOOR, STAIRS_UP]
    # luces de campamento, lejos de las escaleras y de los spawns
    for c in ((171, 94), (179, 101), (185, 93), (193, 99), (199, 87), (207, 95)):
        p = (c[0], c[1], Z9)
        if p in t9 and t9[p][0] in (CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD):
            t9[p] = [t9[p][0], CAMP_FIRE]

    m8, m9 = to_map(t8), to_map(t9)
    spawns = build_spawns()
    errs = validate(m8, m9, spawns)
    if errs:
        print("\n".join(errs[:40]), file=sys.stderr)
        print(f"ERROR: {len(errs)} problemas; no se escribe nada", file=sys.stderr)
        return 1

    print(f"z8: {len(t8)} casillas; z9: {len(t9)} casillas; "
          f"spawns {len(spawns)} ({sum(len(m) for _c, _z, m in spawns)} monstruos)")
    print(f"entrada {ENTRANCE[0]},{ENTRANCE[1]},7 -> {SHAFT_LAND[0]},{SHAFT_LAND[1]},8 -> "
          f"{DEPTHS_LAND[0]},{DEPTHS_LAND[1]},9")

    if args.preview:
        from mapdata import Renderer, png_bytes as png
        tiles = {}
        for src in (t8, t9):
            tiles.update(src)
        xs = [p[0] for p in tiles]; ys = [p[1] for p in tiles]
        w, h, rgba = Renderer().area(
            {p: ids for p, ids in tiles.items()},
            min(xs) - 1, min(ys) - 1, max(xs) + 2, max(ys) + 2, Z9)
        args.preview.write_bytes(png(w, h, rgba, scale=2))
        print(f"preview: {args.preview}")

    if args.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    # backup antes de tocar el mapa
    import shutil
    from datetime import datetime
    backup = Path("/private/var/folders/c8/k2dtzwbx3ml4l81234tng6vc0000gn/T/opencode") / \
        f"bamboo-depths-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAP, backup / "test.otbm")
    shutil.copy2(SPAWNS, backup / "test-spawn.xml")
    print(f"backup: {backup}")

    stackable = roomkit.Checker(m9).stackable
    # z7: solo la casilla de la escalera
    m7 = roomkit.Map()
    m7.ground((ENTRANCE[0], ENTRANCE[1], Z7), STAIR_DOWN)
    roomkit.write_map(MAP, m7, (ENTRANCE[0], ENTRANCE[1], ENTRANCE[0], ENTRANCE[1]), Z7, stackable)
    roomkit.write_map(MAP, m8, BOX8, Z8, stackable)
    roomkit.write_map(MAP, m9, BOX9, Z9, stackable)
    write_spawns(spawns, write=True)
    print(f"escrito: {MAP} y {SPAWNS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
