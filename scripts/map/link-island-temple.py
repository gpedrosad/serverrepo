#!/usr/bin/env python3
"""Portal de vuelta isla natural -> templo + spawns de cyclops en la isla.

El portal del templo y su cartel los maneja scripts/map/temple-portals.py (plaza, 156,47,7).
Isla:   TP de vuelta al sur de la llegada -> llegada del portal de la isla en la plaza.
Spawns: bloque NATURAL_ISLAND_SURFACE en test-spawn.xml (Cyclops).

Idempotente: reemplaza solo esa casilla y ese bloque.
Uso: python3 scripts/map/link-island-temple.py [--dry-run]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import struct
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import DIRS, MAP, REPO, WORLD, load_otb, load_tiles, parse_dat  # noqa: E402

_spec = importlib.util.spec_from_file_location("generate_maze", HERE / "generate-maze.py")
_maze = importlib.util.module_from_spec(_spec)
sys.modules["generate_maze"] = _maze
_spec.loader.exec_module(_maze)

MANIFEST = WORLD / "generated-natural-island.json"
SPAWN_XML = WORLD / "test-spawn.xml"

TELEPORT = 1387
SIGN = 1429
TEMPLE_FLOOR = 407
GRASS = 4756
WATER = 4608
HOLE = 469

TEMPLE_TP = (156, 47, 7)       # lo escribe temple-portals.py
TEMPLE_LANDING = (156, 48, 7)  # llegada al volver (plaza)

CYCLOPS = "Cyclops"
CYCLOPS_PER_TILES = 90
SPAWNTIME = 90
SAFE_FROM_LANDING = 7

S_BEGIN, S_END = "<!-- BEGIN NATURAL_ISLAND_SURFACE -->", "<!-- END NATURAL_ISLAND_SURFACE -->"


def pick_landing(tiles, box, z, hole) -> tuple[int, int]:
    """Pasto liso con 5x5 libre, a 10-20 casillas del agujero, lo más central posible."""
    def plain(x, y):
        return tiles.get((x, y, z)) == [GRASS]
    cands = []
    for (x, y, tz) in tiles:
        if tz != z or not (box["x1"] <= x <= box["x2"] and box["y1"] <= y <= box["y2"]):
            continue
        if all(plain(x + dx, y + dy) for dx in range(-2, 3) for dy in range(-2, 3)):
            d = max(abs(x - hole[0]), abs(y - hole[1]))
            if 10 <= d <= 20:
                cands.append((x, y))
    if not cands:
        raise SystemExit("ERROR: no hay un claro de pasto 5x5 para la llegada")
    land = [(x, y) for (x, y, tz), it in tiles.items()
            if tz == z and box["x1"] <= x <= box["x2"] and box["y1"] <= y <= box["y2"] and it[0] != WATER]
    cx = sum(x for x, _ in land) / len(land)
    cy = sum(y for _, y in land) / len(land)
    return min(cands, key=lambda c: ((c[0] - cx) ** 2 + (c[1] - cy) ** 2, c))


def encode_tile(x, y, z, ground, tele=None, items=()) -> bytes:
    bx, by = x & ~0xFF, y & ~0xFF
    out = bytearray([_maze.NODE_START, _maze.OTBM_TILE_AREA])
    _maze.write_props(out, struct.pack("<HHB", bx, by, z))
    out += bytes([_maze.NODE_START, _maze.OTBM_TILE])
    _maze.write_props(out, struct.pack("<BBBH", x - bx, y - by, _maze.OTBM_ATTR_ITEM, ground))
    if tele:
        out += bytes([_maze.NODE_START, _maze.OTBM_ITEM])
        _maze.write_props(out, struct.pack("<HBHHB", TELEPORT, _maze.OTBM_ATTR_TELE_DEST, *tele))
        out.append(_maze.NODE_END)
    for it in items:
        out += bytes([_maze.NODE_START, _maze.OTBM_ITEM])
        _maze.write_props(out, struct.pack("<H", it))
        out.append(_maze.NODE_END)
    out += bytes([_maze.NODE_END, _maze.NODE_END])
    return bytes(out)


def replace_block(text: str, begin: str, end: str, block: str, closing: str) -> str:
    if begin in text:
        return re.sub(rf"\t?{re.escape(begin)}.*?{re.escape(end)}", lambda _: block, text, flags=re.S)
    return text.replace(closing, block + "\n" + closing)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--seed", type=int, default=9)
    a = ap.parse_args()

    m = json.loads(MANIFEST.read_text())
    box, z = m["box"], m["z"]
    hole = (m["cave"]["hole"]["x"], m["cave"]["hole"]["y"])
    tiles = load_tiles()

    if "portal" in m:
        landing = (m["portal"]["islandLanding"]["x"], m["portal"]["islandLanding"]["y"])
    else:
        landing = pick_landing(tiles, box, z, hole)
    ret_tp = (landing[0], landing[1] + 1)

    # seguridad: solo pisamos casillas vacías o nuestro propio portal
    expect = {(*ret_tp, z): [GRASS]}
    for pos, base in expect.items():
        cur = tiles.get(pos)
        if cur not in (base, base + [TELEPORT], base + [SIGN]):
            raise SystemExit(f"ERROR: {pos} tiene {cur}, esperaba {base}: no lo piso")
    if tiles.get(TEMPLE_LANDING) != [406]:
        raise SystemExit(f"ERROR: la llegada del templo {TEMPLE_LANDING} no está libre: {tiles.get(TEMPLE_LANDING)}")

    # cyclops: pasto caminable conectado con la llegada
    otb, dat = load_otb(), parse_dat()
    blocking = {s for s, r in otb.items() if r.get("cid") in dat and 0x0C in dat[r["cid"]]["flags"]}
    walk = {(x, y) for (x, y, tz), it in tiles.items()
            if tz == z and box["x1"] <= x <= box["x2"] and box["y1"] <= y <= box["y2"]
            and it[0] not in (WATER, HOLE) and not any(i in blocking for i in it)}
    walk.discard(ret_tp)
    reach = {landing}
    q = deque([landing])
    while q:
        x, y = q.popleft()
        for dx, dy in DIRS.values():
            n = (x + dx, y + dy)
            if n in walk and n not in reach:
                reach.add(n)
                q.append(n)
    rng = random.Random(a.seed)
    cells = sorted(c for c in reach
                   if max(abs(c[0] - landing[0]), abs(c[1] - landing[1])) > SAFE_FROM_LANDING
                   and max(abs(c[0] - hole[0]), abs(c[1] - hole[1])) > 2)
    rng.shuffle(cells)
    want = len(reach) // CYCLOPS_PER_TILES
    spawns = []
    for c in cells:
        if len(spawns) >= want:
            break
        if all(max(abs(c[0] - s[0]), abs(c[1] - s[1])) >= 5 for s in spawns):
            spawns.append(c)

    print(f"templo {TEMPLE_TP} -> isla {landing[0]},{landing[1]},{z}; vuelta {ret_tp[0]},{ret_tp[1]},{z} -> {TEMPLE_LANDING}")
    print(f"isla: {len(reach)} casillas caminables desde la llegada; {len(spawns)} {CYCLOPS}")
    if a.dry_run:
        return 0

    raw = MAP.read_bytes()
    body = raw[4:]
    body = _maze.filter_tiles_in_bbox(body, ret_tp[0], ret_tp[1], ret_tp[0], ret_tp[1], z)
    patch = encode_tile(*ret_tp, z, GRASS, tele=TEMPLE_LANDING)
    at = _maze.find_map_data_insert(body)
    MAP.write_bytes(raw[:4] + body[:at] + patch + body[at:])

    lines = [f"\t{S_BEGIN}"]
    for x, y in sorted(spawns, key=lambda c: (c[1], c[0])):
        lines += [f'\t<spawn centerx="{x}" centery="{y}" centerz="{z}" radius="2">',
                  f'\t\t<monster name="{CYCLOPS}" x="0" y="0" z="{z}" spawntime="{SPAWNTIME}" />',
                  "\t</spawn>"]
    lines.append(f"\t{S_END}")
    xml = SPAWN_XML.read_text(encoding="utf-8")
    SPAWN_XML.write_text(replace_block(xml, S_BEGIN, S_END, "\n".join(lines), "</spawns>"), encoding="utf-8")

    m["portal"] = {"templeTp": dict(zip("xyz", TEMPLE_TP)),
                   "templeLanding": dict(zip("xyz", TEMPLE_LANDING)),
                   "islandLanding": {"x": landing[0], "y": landing[1], "z": z},
                   "islandReturnTp": {"x": ret_tp[0], "y": ret_tp[1], "z": z}}
    m["surfaceSpawns"] = [{"x": x, "y": y, "z": z, "monster": CYCLOPS, "spawntime": SPAWNTIME} for x, y in spawns]
    MANIFEST.write_text(json.dumps(m, indent=2) + "\n")
    print("OK mapa, test-spawn.xml y manifiesto")
    return 0


if __name__ == "__main__":
    sys.exit(main())
