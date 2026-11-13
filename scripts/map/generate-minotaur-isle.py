#!/usr/bin/env python3
"""Islote del Minotauro: caza para subir de nivel al lado del muelle de la ciudad (nov 2026).

  z7   Islote en el canal entre el Castillo Imperial y la isla de los elfos (x 99-119, y 49-58).
       Puente de madera al muelle; minotauros comunes. La lava del oeste queda fuera de pantalla.
       Entrada de cueva (portal) a la Cueva del Minotauro.
  z10  Cueva del Minotauro: Minotaur y Archer -> Guard.
  z11  Galerías: Guard y Archer -> Mage.
  z12  Cámara del Rey: Guard y Mage, más por spawn. Portal al fondo de vuelta al islote.

Bajo el islote, z8 y z9 ya tienen las cuevas de rotworms y otras zonas: no se tocan. Por eso la
entrada es un portal a z10; de z10 a z12 se baja por escaleras reales. La dificultad sube con el
piso y, dentro de cada piso, con la distancia a la entrada.

Valida antes de escribir (si algo falla no escribe nada):
  - el rectángulo del islote es solo agua (o ya lo generó este script); costa con una pieza por casilla;
  - del puente se llega a la ciudad, al portal de la cueva y a todo el islote;
  - desde ninguna casilla caminable del islote ni del puente se ve lava;
  - cuevas: escaleras y portal final alcanzables, paredes con pieza única, sin ver el borde negro.

Uso:
  python3 scripts/map/generate-minotaur-isle.py --dry-run [--png /tmp/islote.png]
  python3 scripts/map/generate-minotaur-isle.py --replace
Doc: docs/items-and-map/MAPEAR_ISLOTE_MINOTAURO.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "kb"))
from mapdata import load_tiles  # noqa: E402
from roomkit import REPO, WORLD, Map, patch_readables, render_png, write_map  # noqa: E402

_spec = importlib.util.spec_from_file_location("north_pass", HERE / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)

SPAWNS_XML = WORLD / "test-spawn.xml"
MONSTERS_XML = REPO / "server/YurOTS/ots/data/monster/monsters.xml"
MANIFEST = WORLD / "generated-minotaur-isle.json"

# --- superficie -----------------------------------------------------------------------------------
Z7 = 7
RECT = (97, 49, 120, 58)                   # se reescribe entero (solo agua + 2 casillas del borde del muelle)
ISLE = (109.5, 53.2, 10.6, 3.7)             # elipse: centro x, y y radios
BRIDGE_X = (113, 114)                      # puente de 2 de ancho hasta el muelle (fila 59, piso 405)
BRIDGE = {(x, y) for x in BRIDGE_X for y in range(RECT[3] - 2, RECT[3] + 1)}   # entra 1 al islote
DOCK_Y = 59
CITY = (164, 48)                           # plaza de portales del templo: se llega caminando
LAVA = 598
WATER = {4608, 4609}
PIER_EDGE = {434, 442, 443}                # borde del muelle (bloquea): se reemplaza solo bajo el puente
GRASS, WOOD = 4756, 405
WATER_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}           # medido en la costa del canal
WATER_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
WATER_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}
VIEW = (9, 7)                              # media pantalla del cliente 7.6 (+1 de margen)

# --- cuevas ---------------------------------------------------------------------------------------
Z10, Z11, Z12 = 10, 11, 12
CAVE_BOX = (80, 24, 140, 80)               # z10-z12 vacíos acá; 9x7 de roca alrededor del piso
CAVE_SIZE = {Z10: 900, Z11: 800, Z12: 700}
CAVE_START = (108, 52)                     # llegada del portal del islote en z10

TELEPORT, STONE, SIGN = NP.TELEPORT, NP.STONE, NP.SIGN
STAIR_DOWN, STAIRS_UP, CAVE_FLOORS = NP.STAIR_DOWN, NP.STAIRS_UP, NP.CAVE_FLOORS
CAMPFIRE, BARREL, CRATE, LANTERN = NP.CAMPFIRE, 1770, 1739, NP.LANTERN
BUSHES, SMALL_TREE, FLOWERS, BONES, PEBBLES = NP.BUSHES, NP.FOREST_SMALL_TREE, NP.FLOWERS, NP.BONES, NP.PEBBLES
CARD = NP.CARD

# --- caza: (monstruos, por spawn, spawntime), en orden de dificultad ------------------------------
STAGES = {
    Z7: [(("Minotaur",), 2, 60), (("Minotaur", "Minotaur Archer"), 2, 60)],
    Z10: [(("Minotaur", "Minotaur Archer"), 2, 60), (("Minotaur Archer", "Minotaur", "Minotaur Guard"), 2, 60),
          (("Minotaur Guard", "Minotaur Archer"), 2, 70)],
    Z11: [(("Minotaur Guard", "Minotaur Archer"), 2, 70), (("Minotaur Guard", "Minotaur Mage"), 2, 80),
          (("Minotaur Mage", "Minotaur Guard"), 2, 80)],
    Z12: [(("Minotaur Mage", "Minotaur Guard"), 2, 80), (("Minotaur Guard", "Minotaur Mage"), 3, 90),
          (("Minotaur Mage", "Minotaur Guard"), 3, 90)],
}
GAP = {Z7: 4, Z10: 7, Z11: 7, Z12: 7}


def grow(cells, r: int) -> set:
    return {(x + dx, y + dy) for (x, y) in cells for dx in range(-r, r + 1) for dy in range(-r, r + 1)}


# --- islote ---------------------------------------------------------------------------------------
def island_shape(seed: int) -> set:
    """Elipse con borde irregular, achicada hasta que toda casilla de costa tenga una sola pieza."""
    nz = NP.Noise(seed)
    cx, cy, rx, ry = ISLE
    land = set()
    for x in range(RECT[0] + 1, RECT[2]):
        for y in range(RECT[1] + 1, RECT[3] - 1):
            d = ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2
            if d <= 1 + 0.35 * (nz.fbm(x / 3, y / 3, 2, 5) - 0.5):
                land.add((x, y))
    anchor = {(x, y) for x in range(BRIDGE_X[0] - 2, BRIDGE_X[1] + 3) for y in range(RECT[3] - 5, RECT[3] - 2)}
    land |= anchor                                          # el islote es ancho donde llega el puente
    for _ in range(50):
        bad = {c for c in land - BRIDGE
               if (p := NP.pieces_for(NP.neighbors_in(set(RECT_CELLS) - land - BRIDGE, *c), WATER_SIDE,
                                      WATER_CORNER, WATER_INNER)) is None or len(p) > 1}
        if not bad:
            break
        land -= bad - anchor
    big = max(({c for c in NP.reach(land, s, CARD)} for s in sorted(land)), key=len)
    return big


RECT_CELLS = [(x, y) for x in range(RECT[0], RECT[2] + 1) for y in range(RECT[1], RECT[3] + 1)]


def build_surface(seed: int, existing: dict, bl) -> tuple[dict, dict]:
    rng = random.Random(seed)
    land = island_shape(seed) - BRIDGE
    bridge = set(BRIDGE)
    water = set(RECT_CELLS) - land - bridge
    tiles = {}
    for c in RECT_CELLS:
        if c in bridge:
            tiles[c] = [WOOD]
        elif c in land:
            edge = NP.pieces_for(NP.neighbors_in(water, *c), WATER_SIDE, WATER_CORNER, WATER_INNER)
            tiles[c] = [GRASS] + (edge or [])
        else:
            tiles[c] = list(existing.get((c[0], c[1], Z7), [4608]))   # agua (y el borde del muelle) como estaba

    # entrada de la cueva: portal en la casilla interior más al oeste, piedras al N, O y S,
    # acceso libre por el este; se vuelve de la cueva a 2 casillas al este del portal
    interior = {c for c in land if len(tiles[c]) == 1}
    entry = min((c for c in interior if (c[0] + 1, c[1]) in interior and (c[0] + 2, c[1]) in interior),
                key=lambda c: (c[0], abs(c[1] - ISLE[1]), c[1]))
    access = (entry[0] + 1, entry[1])
    landing = (entry[0] + 2, entry[1])
    tiles[entry].append(TELEPORT)
    for c in ((entry[0] - 1, entry[1] - 1), (entry[0], entry[1] - 1), (entry[0] - 1, entry[1]),
              (entry[0] - 1, entry[1] + 1), (entry[0], entry[1] + 1)):
        if c in interior:
            tiles[c].append(STONE)
    keep = grow({entry, access, landing}, 1) | grow(BRIDGE, 1)

    # campamento minotauro: fogata con barril, cajón y piedras al centro-este
    camp = (int(ISLE[0]) + 3, int(ISLE[1]) - 1)
    for c, it in {camp: CAMPFIRE, (camp[0] + 1, camp[1]): BARREL, (camp[0] - 1, camp[1] - 1): CRATE,
                  (camp[0] + 1, camp[1] + 1): STONE}.items():
        if c in land and len(tiles[c]) == 1 and c not in keep:
            tiles[c].append(it)
    keep |= grow({camp}, 1)

    # vegetación: arbustos y pinos chicos en la costa, flores y huesos adentro (sin cortar el paso)
    walk = {c for c in land if bl.walkable(tiles[c])}
    start = (BRIDGE_X[0], RECT[3] - 3)                      # pasto justo al norte del puente
    for c in sorted(land, key=lambda c: (c[1], c[0])):
        if c in keep or len(tiles[c]) > 1 or c not in walk:
            continue
        coast = len(NP.neighbors_in(water, *c)) > 0
        r = rng.random()
        if coast and r < 0.12:
            item = rng.choice(BUSHES + (SMALL_TREE,))
            if len(NP.reach(walk - {c}, start, CARD)) == len(NP.reach(walk, start, CARD)) - 1:
                tiles[c].append(item)
                walk.discard(c)
        elif r < 0.10:
            tiles[c].append(rng.choice(FLOWERS))
        elif r < 0.13:
            tiles[c].append(rng.choice(BONES[:2] + (PEBBLES,)))
    # cartel: pasto sin borde junto al acceso, en diagonal (nunca sobre la costa ni en el paso)
    cands = [c for c in land if len(tiles[c]) == 1 and c not in (entry, access, landing)
             and abs(c[0] - access[0]) == 1 and abs(c[1] - access[1]) == 1]
    spot = min(cands, key=lambda c: (c[1] > access[1], c[0], c))
    signs = {spot: "CUEVA DEL MINOTAURO\nAbajo, minotauros mas fuertes en cada piso.\n"
                   "Al fondo del tercer piso, portal de vuelta."}
    tiles[spot].append(SIGN)
    return tiles, {"land": land, "bridge": bridge, "entry": entry, "landing": landing, "camp": camp,
                   "signs": signs, "start": start}


# --- cuevas ---------------------------------------------------------------------------------------
def build_caves(seed: int, bl):
    x0, y0, x1, y1 = CAVE_BOX
    box = {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    allowed = {(x, y) for x in range(x0 + VIEW[0], x1 - VIEW[0] + 1) for y in range(y0 + VIEW[1], y1 - VIEW[1] + 1)}
    out, start = {}, CAVE_START
    for i, z in enumerate((Z10, Z11, Z12)):
        sx, sy = start
        core = {(sx + dx, sy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1, 2)}
        floor = NP.carve_cave(seed + 10 * z, allowed, core, (sx, sy + 1), CAVE_SIZE[z])
        tiles = NP.cave_tiles(floor, box, seed + 10 * z, mud_bias=0.08 * i)
        d = NP.reach(floor, (sx, sy + 1), CARD)
        if z == Z10:
            back = (sx + 1, sy + 1)                          # portal de vuelta al islote, al lado de la llegada
        else:
            tiles[(sx, sy)].append(STAIRS_UP)
            back = None
        cands = [c for c in floor if all((c[0] + dx, c[1] + dy) in floor for dx in (-1, 0, 1) for dy in (-2, -1, 0, 1, 2))]
        far = max(cands, key=lambda c: (d[c], c))
        if z == Z12:
            tiles[far].append(TELEPORT)
            exit_ = far
        else:
            tiles[far] = [STAIR_DOWN]
            exit_ = far
        if back:
            tiles[back].append(TELEPORT)
        keep = grow({(sx, sy), (sx, sy + 1), exit_} | ({back} if back else set()), 2)
        NP.decorate_cave(tiles, floor, (sx, sy + 1), keep, seed + 10 * z, 0.05 + 0.02 * i, bl)
        out[z] = {"tiles": tiles, "floor": floor, "start": (sx, sy + 1), "exit": exit_, "back": back,
                  "down_from": start}
        start = far
    return out


# --- spawns ---------------------------------------------------------------------------------------
def place_stages(stages, walk: set, order: dict, avoid: set, z: int, rng, gap: int):
    """Parte `walk` en franjas por `order` (distancia a la entrada) y llena cada franja con spawns."""
    cells = sorted(walk, key=lambda c: (order.get(c, 0), c))
    size = len(cells) / len(stages)
    out, centers = [], []
    for k, (names, per, st) in enumerate(stages):
        pool = [c for c in cells[int(k * size):int((k + 1) * size)] if c not in avoid]
        rng.shuffle(pool)
        n = 0
        for c in pool:
            if any(abs(c[0] - o[0]) + abs(c[1] - o[1]) < gap for o in centers):
                continue
            spots = [(c[0] + dx, c[1] + dy) for dx in range(-2, 3) for dy in range(-2, 3)
                     if (c[0] + dx, c[1] + dy) in walk and (c[0] + dx, c[1] + dy) not in avoid]
            if len(spots) < per + 3:
                continue
            rng.shuffle(spots)
            centers.append(c)
            out.append((c, z, [(names[(n + j) % len(names)], s, st) for j, s in enumerate(spots[:per])]))
            n += per
    return out


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


# --- validación -----------------------------------------------------------------------------------
def validate(existing: dict, surf: dict, info: dict, caves: dict, bl, regenerating: bool) -> list[str]:
    errs = []
    for c in RECT_CELLS:
        old = existing.get((c[0], c[1], Z7))
        ok = old is None or (old[0] in WATER and set(old[1:]) <= PIER_EDGE)
        if not ok and not regenerating:
            errs.append(f"z7 {c}: no es agua ({old}); no se pisa")
    land = info["land"]
    water = set(RECT_CELLS) - land - info["bridge"]
    for c in land:
        p = NP.pieces_for(NP.neighbors_in(water, *c), WATER_SIDE, WATER_CORNER, WATER_INNER)
        if p is None or len(p) > 1:
            errs.append(f"costa {c}: pieza {p}")
    # caminable: mapa existente + islote; del puente a la ciudad, a la cueva y a todo el islote
    world = {(x, y): v for (x, y, z), v in existing.items() if z == Z7 and 90 <= x <= 175 and 30 <= y <= 75}
    world.update(surf)
    walk = {c for c, it in world.items() if bl.walkable(it)}
    d = NP.reach(walk, info["start"], CARD)
    if CITY not in d:
        errs.append(f"z7: del puente no se llega a la ciudad {CITY}")
    if not any((info["entry"][0] + a, info["entry"][1] + b) in d for a, b in CARD):
        errs.append("z7: la entrada de la cueva no se alcanza")
    isle_walk = {c for c in land | info["bridge"] if bl.walkable(surf[c])}
    lost = isle_walk - set(d)
    if lost:
        errs.append(f"z7: {len(lost)} casillas del islote aisladas")
    lava = {(x, y) for (x, y, z), v in existing.items() if z == Z7 and v and v[0] == LAVA}
    for (x, y) in sorted(isle_walk):
        if any((x + dx, y + dy) in lava for dx in range(-VIEW[0], VIEW[0] + 1) for dy in range(-VIEW[1], VIEW[1] + 1)):
            errs.append(f"z7 {(x, y)}: se ve la lava")
            break
    for (x, y, z) in existing:
        if z in (Z10, Z11, Z12) and CAVE_BOX[0] <= x <= CAVE_BOX[2] and CAVE_BOX[1] <= y <= CAVE_BOX[3] and not regenerating:
            errs.append(f"z{z} {(x, y)}: la caja de las cuevas no está vacía")
            break
    for z, cv in caves.items():
        t = cv["tiles"]
        wk = {c for c, it in t.items() if bl.walkable(it) and it[0] in CAVE_FLOORS}
        dz = NP.reach(wk, cv["start"], CARD)
        ex = cv["exit"]
        if not any((ex[0] + a, ex[1] + b) in dz for a, b in CARD + ((0, 0),)):
            errs.append(f"z{z}: la salida {ex} no se alcanza")
        if cv["back"] and not any((cv["back"][0] + a, cv["back"][1] + b) in dz for a, b in CARD):
            errs.append(f"z{z}: el portal de vuelta no se alcanza")
        fl = {c for c, it in t.items() if it[0] in CAVE_FLOORS}
        for c, it in t.items():
            if c in fl:
                continue
            want = NP.pieces_for(NP.neighbors_in(fl, *c), NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER)
            if want is None or len(want) > 1 or (want and it[0] != want[0]) or (not want and it[0] != NP.ROCK):
                errs.append(f"pared z{z} {c}: quiere {want} tiene {it[0]}")
                break
        for (x, y) in wk:
            if x - VIEW[0] < CAVE_BOX[0] or x + VIEW[0] > CAVE_BOX[2] or y - VIEW[1] < CAVE_BOX[1] or y + VIEW[1] > CAVE_BOX[3]:
                errs.append(f"z{z} {(x, y)}: se ve el borde negro")
                break
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--map", type=Path, default=WORLD / "test.otbm")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--png", type=Path)
    a = ap.parse_args()

    import mapdata
    mapdata.MAP = a.map
    existing = load_tiles()
    regenerating = MANIFEST.exists()
    bl = NP.Blocking()
    surf, info = build_surface(a.seed, existing, bl)
    caves = build_caves(a.seed, bl)
    errs = validate(existing, surf, info, caves, bl, regenerating)

    # spawns: islote lejos del puente y de la cueva; cuevas por distancia a la entrada
    rng = random.Random(a.seed + 99)
    isle_walk = {c for c in info["land"] if bl.walkable(surf[c])}
    avoid7 = grow({info["entry"], info["landing"], info["start"]}, 2) | grow({info["camp"]}, 1)
    spawns = place_stages(STAGES[Z7], isle_walk, {c: -c[0] for c in isle_walk}, avoid7, Z7, rng, GAP[Z7])
    for z, cv in caves.items():
        t = cv["tiles"]
        wk = {c for c, it in t.items() if bl.walkable(it) and it[0] in CAVE_FLOORS}
        dz = NP.reach(wk, cv["start"], CARD)
        avoid = grow({cv["start"], cv["exit"]} | ({cv["back"]} if cv["back"] else set()), 4)
        spawns += place_stages(STAGES[z], set(dz), dz, avoid, z, rng, GAP[z])
    known = set(re.findall(r'<monster name="([^"]+)"', MONSTERS_XML.read_text(encoding="latin-1")))
    for _c, _z, mons in spawns:
        for name, _p, _t in mons:
            if name not in known:
                errs.append(f"monstruo inexistente: {name}")

    counts: dict = {}
    for _c, z, mons in spawns:
        for name, _p, _t in mons:
            counts.setdefault(z, {}).setdefault(name, 0)
            counts[z][name] += 1
    entry, landing = info["entry"], info["landing"]
    print(f"islote: {len(info['land'])} casillas de pasto, entrada cueva {entry}, puente x{BRIDGE_X} y{RECT[3] - 2}-{RECT[3]}")
    for z in (Z7, Z10, Z11, Z12):
        size = len(caves[z]["floor"]) if z in caves else len(isle_walk)
        print(f"  z{z}: {size} casillas, " + ", ".join(f"{k} {v}" for k, v in sorted(counts.get(z, {}).items())))
    if a.png:
        m = Map()
        for (x, y), it in surf.items():
            m.ground((x, y, Z7), it[0])
            for i in it[1:]:
                m.add((x, y, Z7), i)
        world ={k: v for k, v in existing.items() if k[2] == Z7 and 88 <= k[0] <= 128 and 42 <= k[1] <= 64}
        for (x, y, z), v in world.items():
            if (x, y) not in surf and v:
                m.ground((x, y, z), v[0])
                for i in v[1:]:
                    m.add((x, y, z), i)
        render_png(m, a.png, Z7)
        for z, cv in caves.items():
            mz = Map()
            for (x, y), it in cv["tiles"].items():
                mz.ground((x, y, z), it[0])
                for i in it[1:]:
                    mz.add((x, y, z), i)
            render_png(mz, a.png.with_name(f"{a.png.stem}_z{z}{a.png.suffix}"), z)
        print(f"PNG {a.png} (+ _z10/_z11/_z12)")
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs[:40]))
        return 1
    if a.dry_run or not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    # --- mapa ---
    stackable = NP.NEEDS_COUNT
    m7 = Map()
    for (x, y), it in surf.items():
        m7.ground((x, y, Z7), it[0])
        for i in it[1:]:
            m7.add((x, y, Z7), i, **({"tele": (*caves[Z10]["start"], Z10)} if i == TELEPORT else {}))
    write_map(a.map, m7, RECT, Z7, stackable)
    final_back = (landing[0], landing[1], Z7)
    for z, cv in caves.items():
        mz = Map()
        for (x, y), it in cv["tiles"].items():
            mz.ground((x, y, z), it[0])
            for i in it[1:]:
                mz.add((x, y, z), i, **({"tele": final_back} if i == TELEPORT else {}))
        write_map(a.map, mz, CAVE_BOX, z, stackable)

    # --- spawns ---
    sp = SPAWNS_XML.read_text(encoding="latin-1")
    sp = re.sub(r"[ \t]*<!-- BEGIN MINOTAUR_ISLE_SPAWNS.*?<!-- END MINOTAUR_ISLE_SPAWNS -->\n?", "", sp, flags=re.S)
    block = "\t<!-- BEGIN MINOTAUR_ISLE_SPAWNS (scripts/map/generate-minotaur-isle.py) -->\n" + \
        spawn_xml(spawns) + "\n\t<!-- END MINOTAUR_ISLE_SPAWNS -->\n"
    SPAWNS_XML.write_text(sp.replace("</spawns>", block + "</spawns>"), encoding="latin-1")

    # --- carteles y manifiesto ---
    patch_readables("<!-- BEGIN MINOTAUR_ISLE_SIGNS -->", "<!-- END MINOTAUR_ISLE_SIGNS -->",
                    [dict(x=x, y=y, z=Z7, text=t) for (x, y), t in info["signs"].items()])
    MANIFEST.write_text(json.dumps({
        "name": "generated-minotaur-isle", "seed": a.seed,
        "surface": {"rect": RECT, "z": Z7, "bridge": sorted(info["bridge"]), "caveEntry": [*entry, Z7],
                    "landing": [*landing, Z7]},
        "caves": {f"z{z}": {"start": [*cv["start"], z], "exit": [*cv["exit"], z], "tiles": len(cv["floor"])}
                  for z, cv in caves.items()},
        "caveBox": CAVE_BOX,
        "spawns": len(spawns), "monsters": {f"z{z}": c for z, c in sorted(counts.items())},
    }, indent=2) + "\n")
    print(f"OK {a.map}, test-spawn.xml (MINOTAUR_ISLE_SPAWNS), readables y {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
