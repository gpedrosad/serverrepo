#!/usr/bin/env python3
"""Claro de los Lobos: isla de pasto aislada, z7, en el vacío al sureste de la city.

Caja de agua x 187–261, y 265–339 (antes sin tiles, sin casas, sin spawns, sin NPC).
Sendero de tierra de 2 de ancho en zigzag y un claro al fondo. Lo que no es sendero
es bosque (bloquea) o costa (las piezas 4644–4655 bloquean). Lobos al entrar, War Wolf
y Bear en el claro.

No toca ciudad, templos, portales ni casas. No hay agujero: no hace falta style-hole-entrances.

Uso (desde la raíz del repo):
  python3.11 scripts/map/generate-wolf-grove.py --dry-run --preview /tmp/claro-lobos.png
  python3.11 scripts/map/generate-wolf-grove.py
  python3 scripts/map/check-map-load.py
  python3 scripts/scan-map-depots.py server/YurOTS/ots/data/world/test.otbm
  python3 scripts/sync-houses-with-map.py --dry-run

Doc: docs/items-and-map/MAPEAR_CLARO_DE_LOS_LOBOS.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import shutil
import struct
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "kb")]
from mapdata import MAP, REPO, load_otb, parse_tree, png_bytes, serialize_tree  # noqa: E402
from epstein_cave_repair import index  # noqa: E402
from portal_citadel_layout import tile_flags  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C = _load("generate-imperial-crypt")
NP = _load("generate-north-pass")

WORLD = MAP.parent
MANIFEST = WORLD / "generated-wolf-grove.json"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MONSTERS = REPO / "server/YurOTS/ots/data/monster/monsters.xml"

# Vacío medido en test.otbm (nov 2026): x 184–261, y 250–380, todos los pisos, sin spawns ni casas.
# La caja queda adentro, con margen de pantalla (±9, ±7) de agua propia.
EMPTY = (184, 250, 261, 380)
ALLOWED = (196, 274, 252, 330)          # la tierra solo puede crecer acá
BOX = (187, 265, 261, 339)              # agua + tierra; ±9 desde ALLOWED
VIEW = (9, 7)

WATER, GRASS, GRASS_COAST, DIRT = 4608, 4756, 4526, 103
COAST_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
COAST_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
COAST_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}
DIRT_SIDE, DIRT_CORNER, DIRT_INNER = NP.DIRT_SIDE, NP.DIRT_CORNER, NP.DIRT_INNER

BLOCKERS = (2768, 2767, 2786, 1285)     # pino chico, arbusto, arándano, piedra: bloquean, 1x1
FOREST_TREES = (4009, 2700, 2707, 2701)  # 2x2, ancla abajo-derecha, dibujo arriba-izquierda
FLOWERS = (4158, 2740)
CAMPFIRE, LOGS, SIGN = 1423, 3873, 1429

# Recorrido (esquina noroeste del sendero de 2). Claro al este del último tramo.
PATH = [(206, 286), (228, 286), (228, 314), (240, 314)]
CLEAR = {(x, y) for x in range(232, 245) for y in range(308, 319)}
CAMP = (240, 314)
Z = 7

STAGES = (
    (("Wolf",), 1, 90, 11),
    (("Wolf", "War Wolf"), 1, 110, 11),
    (("War Wolf", "Bear"), 2, 140, 10),
)


def box_cells(b):
    x0, y0, x1, y1 = b
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def widen(points) -> set:
    """Sendero de 2 de ancho, solo tramos ortogonales (bordes de tierra de una pieza)."""
    cells = set()
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if y0 == y1:
            for x in range(min(x0, x1), max(x0, x1) + 1):
                cells.add((x, y0))
                cells.add((x, y0 + 1))
        elif x0 == x1:
            for y in range(min(y0, y1), max(y0, y1) + 1):
                cells.add((x0, y))
                cells.add((x0 + 1, y))
        else:
            raise ValueError(f"tramo diagonal {x0, y0} -> {x1, y1}")
    return cells


def coast_piece(land, c):
    near = {d for d, (dx, dy) in NP.DIRS.items() if (c[0] + dx, c[1] + dy) not in land}
    pcs = NP.pieces_for(near, COAST_SIDE, COAST_CORNER, COAST_INNER)
    if pcs is None or len(pcs) != 1:
        raise RuntimeError(f"Costa ambigua en {c}: {sorted(near)} -> {pcs}")
    return pcs[0]


def dirt_ground(dirt, c):
    pcs = NP.pieces_for(NP.neighbors_in(dirt, *c), DIRT_SIDE, DIRT_CORNER, DIRT_INNER)
    if pcs is None or len(pcs) != 1:
        raise RuntimeError(f"Borde de tierra ambiguo en {c}: {pcs}")
    return pcs[0]


def build():
    bl = C.Blocking()
    rng = random.Random("wolf-grove-v1")
    known = set(re.findall(r'name="([^"]+)"', MONSTERS.read_text(encoding="latin-1")))
    for stage in STAGES:
        for name in stage[0]:
            if name not in known:
                raise RuntimeError(f"Monstruo inexistente: {name}")

    allowed = box_cells(ALLOWED)
    area = box_cells(BOX)
    seed = widen(PATH) | CLEAR
    if not seed <= allowed:
        raise RuntimeError(f"Sendero fuera de la zona permitida: {sorted(seed - allowed)[:4]}")
    land0 = C.grow(seed, 5)
    if not land0 <= allowed:
        raise RuntimeError(f"Tierra inicial fuera de la zona: {sorted(land0 - allowed)[:4]}")
    land = NP.fix_until_valid(land0, allowed, COAST_SIDE, COAST_CORNER, COAST_INNER, single=True)
    if not land <= allowed:
        raise RuntimeError("La costa creció fuera de la zona permitida")

    shore = {c for c in land if any((c[0] + dx, c[1] + dy) not in land for dx, dy in NP.DIRS.values())}
    deep = land - C.grow(shore, 1)
    if not seed <= deep:
        raise RuntimeError(f"El sendero toca la costa: {sorted(seed - deep)[:6]}")
    dirt = NP.fix_until_valid(set(seed), deep, DIRT_SIDE, DIRT_CORNER, DIRT_INNER, single=True)
    if CAMP not in dirt:
        raise RuntimeError(f"La fogata {CAMP} no quedó en tierra")

    tiles = {c: [WATER] for c in area}
    for c in land:
        if c in dirt:
            tiles[c] = [DIRT]
        elif c in shore:
            tiles[c] = [GRASS_COAST, coast_piece(land, c)]
        elif NP.neighbors_in(dirt, *c):
            tiles[c] = [dirt_ground(dirt, c)]
        else:
            tiles[c] = [GRASS]

    entry = min(dirt)
    sign = None
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        c = (entry[0] + dx, entry[1] + dy)
        if c in land and c not in dirt and c not in shore:
            sign = c
            break
    if sign is None:
        raise RuntimeError(f"No hay pasto para el cartel junto a {entry}")

    grass = land - shore - dirt
    for c in sorted(grass):
        if c == sign:
            tiles[c].append(SIGN)
        else:
            tiles[c].append(rng.choice(BLOCKERS))
    # pinos 2x2 solo donde el dibujo (ancla y arriba-izquierda) cae en bosque, nunca en el sendero
    for c in sorted(grass):
        if c == sign or rng.random() > 0.22:
            continue
        x, y = c
        foot = {(x - dx, y - dy) for dx in (0, 1) for dy in (0, 1)}
        if foot <= grass and sign not in foot:
            tiles[c].append(rng.choice(FOREST_TREES))

    tiles[CAMP].append(CAMPFIRE)
    for c in ((CAMP[0] + 1, CAMP[1] + 1), (CAMP[0] - 1, CAMP[1] + 1)):
        if c in dirt and c != entry:
            tiles[c].append(LOGS)
    for c in sorted(dirt):
        if c in (entry, CAMP) or LOGS in tiles[c] or CAMPFIRE in tiles[c]:
            continue
        if rng.random() < 0.04:
            tiles[c].append(rng.choice(FLOWERS))

    def walk_set():
        return {c for c, ids in tiles.items() if c in area and bl.walkable(ids)}

    walk = walk_set()
    if not dirt <= walk:
        blocked = sorted(dirt - walk)[:6]
        raise RuntimeError(f"Tierra que no se pisa: {blocked}")
    # el bosque y la costa no son atajo: lo caminable es el sendero (la fogata no bloquea sólido)
    extra = walk - dirt
    if extra:
        raise RuntimeError(f"Atajo fuera del sendero: {sorted(extra)[:6]}")
    dist = C.reach(walk, entry, C.NP.CARD)
    if set(dist) != walk:
        raise RuntimeError(f"Sendero cortado: {sorted(walk - set(dist))[:6]}")

    for x, y in land:
        for dx in range(-VIEW[0], VIEW[0] + 1):
            for dy in range(-VIEW[1], VIEW[1] + 1):
                if (x + dx, y + dy) not in tiles:
                    raise RuntimeError(f"Vacío a la vista desde {(x, y)} en {(x + dx, y + dy)}")

    avoid = C.grow({entry}, 6) | C.grow({CAMP}, 1)
    spawns = C.place_stages(
        STAGES,
        C.slices_by(walk - avoid, dist.__getitem__, len(STAGES)),
        walk, avoid, Z, random.Random("wolf-grove-spawns-v1"),
    )
    positions = [p for _, _, ms in spawns for _, p, _ in ms]
    if len(positions) != len(set(positions)) or not set(positions) <= walk - avoid:
        raise RuntimeError("Spawn fuera del sendero o repetido")
    counts = Counter(n for _, _, ms in spawns for n, _, _ in ms)
    if not counts.get("Wolf") or not counts.get("Bear"):
        raise RuntimeError(f"Faltan etapas: {dict(counts)}")
    density = round(len(walk) / max(1, sum(counts.values())), 1)

    cells = {(x, y, Z): ids for (x, y), ids in tiles.items()}
    report = dict(
        box=list(BOX), entry=[*entry, Z], sign=[*sign, Z], campfire=[*CAMP, Z],
        walkable=len(walk), land=len(land), water=len(area - land),
        spawns=len(spawns), monsters=dict(counts), density=density,
    )
    return cells, spawns, sign, report


def block(text, key, body, close):
    marked = f"\t<!-- BEGIN {key} (scripts/map/generate-wolf-grove.py) -->\n{body}\n\t<!-- END {key} -->\n"
    pattern = rf"[ \t]*<!-- BEGIN {key}(?: \([^>]*\))? -->.*?<!-- END {key} -->\n?"
    if re.search(pattern, text, re.S):
        return re.sub(pattern, lambda _: marked, text, count=1, flags=re.S)
    return text.replace(close, marked + close, 1)


def write_preview(path: Path, cells, spawns):
    x0, y0, x1, y1 = BOX
    w, h = x1 - x0 + 1, y1 - y0 + 1
    rgba = bytearray(b"\x10\x18\x28\xff" * (w * h))
    colors = {
        WATER: (32, 72, 128), GRASS: (48, 110, 48), GRASS_COAST: (70, 130, 78), DIRT: (122, 96, 58),
    }
    for border in list(DIRT_SIDE.values()) + list(DIRT_CORNER.values()) + list(DIRT_INNER.values()):
        colors[border] = (64, 120, 52)
    monsters = {(x, y) for _, _, ms in spawns for _, (x, y), _ in ms}
    for (x, y, _z), ids in cells.items():
        col = colors.get(ids[0], (90, 90, 90))
        if any(i in BLOCKERS or i in FOREST_TREES for i in ids):
            col = (24, 72, 32)
        if CAMPFIRE in ids:
            col = (210, 110, 30)
        if SIGN in ids:
            col = (230, 200, 80)
        if (x, y) in monsters:
            col = (190, 40, 40)
        o = ((y - y0) * w + (x - x0)) * 4
        rgba[o:o + 4] = bytes((*col, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes(w, h, bytes(rgba), scale=6))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    args = ap.parse_args()

    ex, ey, ex1, ey1 = EMPTY
    bx0, by0, bx1, by1 = BOX
    if not (ex <= bx0 and ey <= by0 and bx1 <= ex1 and by1 <= ey1):
        raise SystemExit(f"La caja {BOX} se sale del vacío medido {EMPTY}")

    raw = MAP.read_bytes()
    root = parse_tree(raw)
    otb = load_otb()
    nodes, values, areas = index(root, otb)
    dup = [p for p, ns in nodes.items() if len(ns) != 1]
    if dup:
        raise SystemExit(f"Casillas duplicadas: {dup[:4]}")

    cells, spawns, sign, report = build()
    previous = json.loads(MANIFEST.read_text())["cells"] if MANIFEST.exists() else {}
    for p, ids in cells.items():
        old = values.get(p)
        owned = previous.get(",".join(map(str, p))) == old
        if old is not None and not owned:
            raise SystemExit(f"Tile ajeno protegido: {p}: {old}")
        for tile in nodes.get(p, []):
            if tile[0] != 5 or tile_flags(tile[1]):
                raise SystemExit(f"Casa o flags protegidos: {p}")
            if any(c[0] != 6 or len(c[1]) != 2 or c[2] for c in tile[2]):
                raise SystemExit(f"Atributos protegidos: {p}")
    for key, ids in previous.items():
        p = tuple(int(n) for n in key.split(","))
        if p not in cells and values.get(p) == ids:
            cells[p] = [WATER]

    sx, sy = sign
    sz = Z
    sign_line = (
        f'\t<readable x="{sx}" y="{sy}" z="{sz}" '
        'text="WOLF GROVE\\nLevel 8-25.\\nWolves along the trail. War wolves and bears at the clearing."/>'
    )
    spawn_text = block(SPAWNS.read_text(encoding="latin-1"), "WOLF_GROVE_SPAWNS", C.spawn_xml(spawns), "</spawns>")
    sign_text = block(READABLES.read_text(encoding="latin-1"), "WOLF_GROVE_SIGNS", sign_line, "</readables>")
    changed = sum(values.get(p) != ids for p, ids in cells.items())
    print(json.dumps(report | dict(changed=changed), ensure_ascii=False))
    if args.preview:
        write_preview(args.preview, cells, spawns)
        print(args.preview)
    if args.dry_run or args.preview:
        return

    backup = REPO / "backups/map" / ("wolf-grove-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    for f in (MAP, SPAWNS, READABLES):
        shutil.copy2(f, backup / f.name)
    for (x, y, z), ids in sorted(cells.items()):
        key = (x // 256 * 256, y // 256 * 256, z)
        if key not in areas:
            areas[key] = [4, bytearray(struct.pack("<HHB", *key)), []]
            root[2][0][2].append(areas[key])
        if (x, y, z) in nodes:
            tile = nodes[(x, y, z)][0]
        else:
            tile = [5, bytearray([x % 256, y % 256]), []]
            areas[key][2].append(tile)
            nodes[(x, y, z)] = [tile]
        ground = otb[ids[0]]["group"] == "ground"
        tile[1] = bytearray([x % 256, y % 256]) + (struct.pack("<BH", 9, ids[0]) if ground else b"")
        tile[2] = [C.item_node(i) for i in ids[1 if ground else 0:]]
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    SPAWNS.write_text(spawn_text, encoding="latin-1")
    READABLES.write_text(sign_text, encoding="latin-1")
    MANIFEST.write_text(json.dumps(dict(
        name="wolf-grove", version=1, **report,
        cells={",".join(map(str, p)): ids for p, ids in sorted(cells.items())},
    ), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
