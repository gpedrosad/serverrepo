#!/usr/bin/env python3
"""Cuevas largas de Epstein Island: tres zonas por piso (z8, z9 y z10).

Cada zona es un recorrido procedural largo (pasillos de 2 de ancho + salas) dentro de una caja
reservada en el vacío bajo la isla. Las zonas de un mismo piso no se tocan; cada una baja a la
zona correspondiente del piso siguiente con un agujero 479 y una escalera de mano 1386.

  z8  Drowned Grotto (oeste) / Wyvern Roost (centro) / Murius Den (este)
  z9  Mutated Tiger Den / Tide Priest Sanctum / Bog Raider Bog
  z10 Deep Mutant Lab / Abyssal Grotto / Bog Raider Queen

La cueva existente de 82,190,8 (Mutant Burrow) no se toca. El generador escribe
`generated-epstein-caves.json` con caja/inicio de cada zona para que generate-epstein-hunts.py
coloque los spawns sin duplicar coordenadas.

Uso:
  python3 scripts/map/generate-epstein-caves.py --dry-run --preview-dir /tmp/epstein
  python3 scripts/map/generate-epstein-caves.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
import roomkit  # noqa: E402
from mapdata import REPO  # noqa: E402

_spec = importlib.util.spec_from_file_location("north_pass", HERE / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)
CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD = NP.CAVE_FLOOR, NP.CAVE_FLOOR_ALT, NP.CAVE_MUD
WALL_SIDE, WALL_CORNER, WALL_INNER = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER
ROCK = NP.ROCK

WORLD = REPO / "server/YurOTS/ots/data/world"
MAP = WORLD / "test.otbm"
MANIFEST = WORLD / "generated-epstein-caves.json"
Z7, Z8, Z9, Z10 = 7, 8, 9, 10
HOLE = 479
LADDER = 1386
CAMPFIRE = 1423

Z8_ZONES = {
    "drowned": dict(box=(40, 198, 70, 250), start=(66, 200), seed=101, steps=140, room_every=14, floor=CAVE_FLOOR_ALT),
    "wyvern": dict(box=(74, 200, 88, 250), start=(80, 201), seed=102, steps=140, room_every=14, floor=CAVE_FLOOR),
    "murius": dict(box=(92, 200, 122, 250), start=(97, 204), seed=103, steps=140, room_every=14, floor=CAVE_MUD),
}
Z9_ZONES = {
    "tiger": dict(box=(40, 205, 70, 255), seed=201, steps=140, room_every=14, floor=CAVE_MUD),
    "tide": dict(box=(74, 205, 88, 255), seed=202, steps=140, room_every=14, floor=CAVE_FLOOR_ALT),
    "bog": dict(box=(92, 205, 122, 255), seed=203, steps=140, room_every=14, floor=CAVE_MUD),
}
Z10_ZONES = {
    "lab": dict(box=(40, 200, 70, 260), seed=301, steps=140, room_every=14, floor=CAVE_FLOOR),
    "abyss": dict(box=(74, 200, 88, 260), seed=302, steps=140, room_every=14, floor=CAVE_FLOOR_ALT),
    "queen": dict(box=(92, 200, 122, 260), seed=303, steps=140, room_every=14, floor=CAVE_MUD),
}


def rect(x0: int, y0: int, x1: int, y1: int) -> set:
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def carve(seed: int, box: tuple[int, int, int, int], start: tuple[int, int], steps: int,
          room_every: int) -> tuple[set, list, tuple[int, int]]:
    x0, y0, x1, y1 = box
    minx, maxx, miny, maxy = x0 + 1, x1 - 1, y0 + 1, y1 - 1
    rng = random.Random(seed)
    floor: set = set()
    rooms: list = []

    def add_room(cx, cy, w=7, h=7):
        for x in range(max(minx, cx - w // 2), min(maxx, cx + w // 2) + 1):
            for y in range(max(miny, cy - h // 2), min(maxy, cy + h // 2) + 1):
                floor.add((x, y))
        rooms.append((cx, cy))

    def corridor(a, b):
        ax, ay = a
        bx, by = b
        for x in range(min(ax, bx), max(ax, bx) + 1):
            for dy in (0, 1):
                y = ay + dy
                if miny <= y <= maxy:
                    floor.add((x, y))
        for y in range(min(ay, by), max(ay, by) + 1):
            for dx in (0, 1):
                x = bx + dx
                if minx <= x <= maxx:
                    floor.add((x, y))

    add_room(*start, w=5, h=5)
    current = start
    direction = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
    for i in range(steps):
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        rng.shuffle(dirs)
        if rng.random() < 0.65:
            dirs.remove(direction)
            dirs.insert(0, direction)
        # evitar volver exactamente para atrás salvo que no haya otra
        options = [d for d in dirs if d != (-direction[0], -direction[1])]
        if not options:
            options = dirs
        moved = False
        for dx, dy in options:
            step = rng.randint(2, 4)
            nx, ny = current[0] + dx * step, current[1] + dy * step
            if minx <= nx <= maxx and miny <= ny <= maxy:
                corridor(current, (nx, ny))
                current = (nx, ny)
                direction = (dx, dy)
                moved = True
                break
        if not moved:
            break
        if (i + 1) % room_every == 0:
            add_room(*current, w=7, h=7)

    hole = None
    if (current[0], current[1] + 1) in floor and current[1] + 1 <= maxy:
        hole = current
    else:
        for cx, cy in reversed(rooms):
            if (cx, cy) in floor and (cx, cy + 1) in floor:
                hole = (cx, cy)
                break
    if hole is None:
        hole = current
    return floor, rooms, hole


def build_zone(spec, start: tuple[int, int], z: int):
    floor, rooms, hole = carve(spec["seed"], spec["box"], start, spec["steps"], spec["room_every"])
    box = rect(*spec["box"])
    tiles2 = NP.cave_tiles(floor, box, spec["seed"])
    for c in floor:
        if spec["floor"] == CAVE_MUD:
            tiles2[c] = [CAVE_MUD if (c[0] + c[1]) % 3 else CAVE_FLOOR]
        elif spec["floor"] == CAVE_FLOOR_ALT:
            tiles2[c] = [CAVE_FLOOR_ALT if (c[0] + c[1]) % 2 else CAVE_FLOOR]
        else:
            tiles2[c] = [CAVE_FLOOR if (c[0] + c[1]) % 3 else CAVE_FLOOR_ALT]
    out = {(x, y, z): ids for (x, y), ids in tiles2.items()}
    out[(start[0], start[1], z)] = [CAVE_FLOOR, LADDER]
    # una fogata en la primera sala, para que no esté todo a oscuras
    if rooms:
        cx, cy = rooms[0]
        p = (cx, cy, z)
        if p in out and (cx, cy) in floor:
            out[p].append(CAMPFIRE)
    return out, floor, hole


def to_map(tiles: dict) -> roomkit.Map:
    m = roomkit.Map()
    for pos, ids in tiles.items():
        m.ground(pos, ids[0])
        for iid in ids[1:]:
            m.add(pos, iid)
    return m


def validate(m: roomkit.Map, floor: set, start: tuple[int, int], z: int) -> list[str]:
    errs = []
    chk = roomkit.Checker(m)
    walk = {p for p in m.t if chk.walkable(p)}
    s = (start[0], start[1], z)
    seen = {s}
    todo = [s]
    while todo:
        x, y, zz = todo.pop()
        for dx, dy in NP.CARD:
            n = (x + dx, y + dy, zz)
            if n in walk and n not in seen:
                seen.add(n)
                todo.append(n)
    if len(seen) != len(walk):
        errs.append(f"{start}: {len(walk) - len(seen)} casillas aisladas")
    for x, y in floor:
        if (x, y, z) not in walk:
            errs.append(f"piso no caminable {x},{y}")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview-dir", type=Path)
    args = ap.parse_args()

    maps = {}
    floors = {}
    meta = {}
    holes8 = {}
    for name, spec in Z8_ZONES.items():
        tiles, floor, hole = build_zone(spec, spec["start"], Z8)
        maps[name] = to_map(tiles)
        floors[name] = floor
        holes8[name] = hole
        meta[name] = {"z": Z8, "box": list(spec["box"]), "start": [spec["start"][0], spec["start"][1], Z8],
                      "hole": list(hole)}
        print(f"{name}: z8 piso {len(floor)}, agujero a z9 {hole}")

    holes9 = {}
    for name, spec in Z9_ZONES.items():
        start = holes8[{"tiger": "drowned", "tide": "wyvern", "bog": "murius"}[name]]
        if not (spec["box"][0] <= start[0] <= spec["box"][2] and spec["box"][1] <= start[1] <= spec["box"][3]):
            raise SystemExit(f"{name}: el agujero {start} queda fuera de la caja {spec['box']}")
        tiles, floor, hole = build_zone(spec, start, Z9)
        maps[name] = to_map(tiles)
        floors[name] = floor
        holes9[name] = hole
        meta[name] = {"z": Z9, "box": list(spec["box"]), "start": [start[0], start[1], Z9],
                      "hole": list(hole)}
        print(f"{name}: z9 piso {len(floor)}, agujero a z10 {hole}")

    for name, spec in Z10_ZONES.items():
        start = holes9[{"lab": "tiger", "abyss": "tide", "queen": "bog"}[name]]
        if not (spec["box"][0] <= start[0] <= spec["box"][2] and spec["box"][1] <= start[1] <= spec["box"][3]):
            raise SystemExit(f"{name}: el agujero {start} queda fuera de la caja {spec['box']}")
        tiles, floor, hole = build_zone(spec, start, Z10)
        maps[name] = to_map(tiles)
        floors[name] = floor
        meta[name] = {"z": Z10, "box": list(spec["box"]), "start": [start[0], start[1], Z10],
                      "hole": list(hole)}
        print(f"{name}: z10 piso {len(floor)}")

    # agujeros: z8 -> z9 y z9 -> z10 (el piso de abajo ya tiene su escalera)
    for z8name, z9name in (("drowned", "tiger"), ("wyvern", "tide"), ("murius", "bog")):
        hx, hy = holes8[z8name]
        maps[z8name].t[(hx, hy, Z8)] = {"ground": HOLE, "items": [], "pz": False}
    for z9name, z10name in (("tiger", "lab"), ("tide", "abyss"), ("bog", "queen")):
        hx, hy = holes9[z9name]
        maps[z9name].t[(hx, hy, Z9)] = {"ground": HOLE, "items": [], "pz": False}

    for name, spec in {**Z8_ZONES, **Z9_ZONES, **Z10_ZONES}.items():
        z = meta[name]["z"]
        errs = validate(maps[name], floors[name], tuple(meta[name]["start"][:2]), z)
        if errs:
            print("\n".join(errs[:20]), file=sys.stderr)
            return 1
        if args.preview_dir:
            args.preview_dir.mkdir(parents=True, exist_ok=True)
            roomkit.render_png(maps[name], args.preview_dir / f"{name}.png", z)

    if args.dry_run:
        print("dry-run: no se escribió nada")
        return 0

    MANIFEST.write_text(json.dumps({"zones": meta}, indent=2) + "\n", encoding="utf-8")
    print(f"manifiesto: {MANIFEST}")

    backup = Path("/private/var/folders/c8/k2dtzwbx3ml4l81234tng6vc0000gn/T/opencode") / \
        f"epstein-long-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAP, backup / "test.otbm")
    print(f"backup: {backup}")

    stackable = roomkit.Checker(maps["drowned"]).stackable
    for name, spec in Z8_ZONES.items():
        roomkit.write_map(MAP, maps[name], spec["box"], Z8, stackable)
    for name, spec in Z9_ZONES.items():
        roomkit.write_map(MAP, maps[name], spec["box"], Z9, stackable)
    for name, spec in Z10_ZONES.items():
        roomkit.write_map(MAP, maps[name], spec["box"], Z10, stackable)
    # agujeros de superficie
    for name, spec in Z8_ZONES.items():
        x, y = spec["start"]
        m7 = roomkit.Map()
        m7.ground((x, y, Z7), HOLE)
        roomkit.write_map(MAP, m7, (x, y, x, y), Z7, stackable)
    print(f"escrito: {MAP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
