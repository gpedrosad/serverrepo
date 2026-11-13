#!/usr/bin/env python3
"""Desierto de las Ruinas: la ciudad del desierto pasa a ser una zona de caza con siete lugares distintos.

La isla de arena al este de la ciudad (x 198-262, y 68-120, z7) tenía casas (Desert Street I-VI y la Sand
Mansion) y un NPC. Este generador saca todo eso y arma, sobre la misma costa:

  1. Ruinas de la ciudad vieja   hienas, leones, cobras, escorpiones           (entrada, lo más fácil)
  2. Campamento de bandidos      smugglers, bandits, wild warriors, hunters
  3. Nido de escarabajos         larvas, scarabs, ancient scarabs + jefe
  4. Templo de los lagartos      sentinels, templars, snakecharmers + cofre
  5. Oasis y laguna              cocodrilos, cobras, tarántulas (y la bajada a las tumbas, que no se toca)
  6. Campo de huesos             ghouls, momias, bone beasts + jefe Omruc + cofre
  7. Santuario de los djinn      green djinns y efreets                         (lo más difícil)

Qué toca:
  - test.otbm: la superficie de la isla (z7) y los pisos altos de las casas (z4-z6). El oasis, los pozos de
    alquitrán, la costa, el barco del sur y las tumbas de abajo (z8+) quedan como están.
  - test-spawn.xml: saca los monstruos viejos de la superficie y escribe el bloque DESERT_HUNTS_SPAWNS.
  - npc.xml: saca al Seller de la ciudad vieja.  houses.xml y houses/: saca Desert Street y Sand Mansion.
  - readables.xml: cartel de la entrada.  generated-desert-hunts.json: manifiesto.

Los lugares son planos de texto (STAMPS) pegados sobre la arena; los caminos son rectángulos (ROADS) y los
monstruos, listas por zona (ZONES). Valida antes de escribir: que cada plano caiga en tierra, que todo se
alcance caminando desde la entrada (cofres, jefes, el muelle, la bajada del oasis) y que los monstruos existan.

  python3.11 scripts/map/generate-desert-hunts.py --dry-run          # valida, no escribe
  python3.11 scripts/map/generate-desert-hunts.py --preview /tmp/desierto.png
  python3.11 scripts/map/generate-desert-hunts.py                    # escribe
  python3 scripts/map/check-map-load.py

Se puede volver a correr: rehace la superficie entera cada vez. Doc: docs/gameplay/DESERT_HUNTS.md.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import struct
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "kb"))
from mapdata import MAP, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, load_otb, load_tiles, parse_tree, serialize_tree  # noqa: E402

DATA = REPO / "server/YurOTS/ots/data"
WORLD = DATA / "world"
SPAWNS = WORLD / "test-spawn.xml"
NPCS = WORLD / "npc.xml"
HOUSES = DATA / "houses.xml"
HOUSE_DIR = DATA / "houses"
READABLES = DATA / "readables.xml"
MONSTERS = DATA / "monster"
MANIFEST = WORLD / "generated-desert-hunts.json"

Z = 7
BOX = (198, 68, 262, 120)                     # la isla en z7
UPPER = (200, 66, 228, 114)                   # pisos altos de las casas (z4-z6): se borran
ENTRANCE = (198, 74)                          # llegada desde el camino de la ciudad
DOCK = (237, 120)                             # arranque del muelle del barco
OASIS_STAIR = (251, 98)                       # bajada a las tumbas
OLD_HOUSES = ("Desert Street", "Sand Mansion")
OLD_NPC = ("Seller", 208, 80)

SAND, CRACKED, PAVE, PAVE_DARK, MARBLE = 231, 836, 790, 777, 406
CHEST, SIGN = 1740, 1429
ATTR_UNIQUE_ID = 5
WALLS = {"#": dict(v=1067, h=1069, corner=1070, post=1062),      # arenisca
         "B": dict(v=3423, h=3426, corner=3429, post=3425)}      # bambú
# carácter -> (suelo o None, ítems encima)
LEGEND = {
    ".": (None, []), "O": (None, []),
    ":": (PAVE, []), ";": (PAVE_DARK, []), ",": (CRACKED, []), "m": (MARBLE, []),
    "x": (None, [1085]), "X": (None, [1087]),                    # restos de pared
    "p": (PAVE, [1549]), "P": (None, [1551]), "o": (None, [1561]), "c": (None, [1560]), "t": (PAVE, [1451]),
    "f": (None, [1423]), "k": (None, [1739]), "b": (None, [1774]),
    "n": (None, [2248]), "N": (None, [2247]), "q": (None, [1417]), "Q": (None, [1418]),
    "h": (MARBLE, [1482]), "r": (MARBLE, [1798]), "R": (None, [1357]), "T": (None, [2725]),
    "A": (PAVE, [CHEST]), "V": (None, [CHEST]), "S": (None, [SIGN]),
    "u": (3264, []), "U": (3265, []), "z": (3264, [2775]), "Z": (3265, [2774]), "y": (3264, [2709]),   # ciénaga
}
CHESTS = {"A": 2476, "V": 2534}               # knight armor (templo), vampire shield (campo de huesos)
PAIRS = {"q": ("Q", 0, 1)}                    # sarcófago: cabecera y pie

STAMPS = {
    "cartel": (199, 73, ["S"]),
    "ruinas": (204, 70, [
        "###x  ::: #x ## ",
        "#::.  :::    :# ",
        "X::.  p:p   .:X ",
        "  ..  :::   ..  ",
        "#..   :::     # ",
        "##x#  :::  #x## ",
        "      :::       ",
        "  p    o    p   ",
        "#x##      ##x#  ",
        "#::.      .::#  ",
        "X::.  ..  .::X  ",
        "##x   ..   x##  ",
    ]),
    "campamento": (212, 101, [
        "BBB..BBBBBBBB",
        "B..........kB",
        "B.kb.....f..B",
        "B...........B",
        "B.f..........",
        "B............",
        "B.......BBB.B",
        "B..f....Bkb.B",
        "B.......B...B",
        "BBBBBBBBBBBBB",
    ]),
    "nido": (224, 74, [
        "    ,,,    R ",
        "  ,,,,,,,    ",
        " ,,,n,,,,,, R",
        " ,,,,,R,,,,, ",
        "R ,,,,O,,n,, ",
        "  ,,,,,,,,,, ",
        "   ,,n,,,R,  ",
        "    ,,,,,,   ",
        " R    ,,,    ",
    ]),
    "templo": (238, 77, [
        "##########",
        "#:t:A::t:#",
        "#::::::::#",
        "x:p::::p:#",
        ".::::::::.",
        "#::::::::x",
        "#:p::::p:#",
        "#::::::::#",
        "###x..x###",
    ]),
    "huesos": (242, 108, [
        "n   q   o  N  n   ",
        "  N Q      n     ",
        " n     P . P    q",
        "    n  .....  n Q",
        "  o    P.O.P     ",
        "N   n  .....  N  ",
        "   q   P . P   V ",
        " n Q  n   N  n   ",
        "   n      o    n ",
    ]),
    "cienaga": (242, 87, [
        "  uuUuu  ",
        " uUzuuUu ",
        "uuuuUuzuu",
        "uUuyuuuUu",
        "uuZuuUuu ",
        " uuUuy   ",
    ]),
    "santuario": (226, 99, [
        "P  mmmmm  P",
        "  mmmmmmm  ",
        " mmhmmmhmm ",
        " mmmrrrmmm ",
        " mmmrrrmmm ",
        " mmmrrrmmm ",
        " mmhmmmhmm ",
        "  mmmmmmm  ",
        "P  mmmmm  P",
    ]),
}
# caminos de piedra (x1, y1, x2, y2): no pisan lo que ya puso un plano
ROADS = [
    (198, 74, 202, 75), (201, 74, 202, 85),       # de la entrada hacia el sur
    (201, 84, 240, 85),                           # calle principal, hacia el este
    (215, 86, 216, 100),                          # baja al campamento
    (239, 84, 240, 97), (238, 97, 239, 119),      # entre la laguna y el oasis, hasta el muelle
    (240, 106, 244, 107),                         # desvío al campo de huesos
]
# zona -> (nombre, nivel sugerido, caja x1 y1 x2 y2, [(monstruo, cantidad, respawn s)])
ZONES = [
    ("ruinas", "Ruinas de la ciudad vieja", "8-20", (203, 69, 221, 82),
     [("Hyaena", 5, 60), ("Lion", 4, 60), ("Cobra", 4, 60), ("Scorpion", 3, 60), ("Snake", 3, 60)]),
    ("campamento", "Campamento de bandidos", "20-40", (210, 99, 225, 112),
     [("Smuggler", 3, 90), ("Bandit", 4, 90), ("Wild Warrior", 3, 90), ("Stalker", 2, 90), ("Assassin", 2, 90),
      ("Hunter", 2, 90)]),
    ("nido", "Nido de escarabajos", "30-60", (223, 72, 237, 83),
     [("Larva", 6, 90), ("Scarab", 6, 120), ("Ancient Scarab", 2, 240)]),
    ("templo", "Templo de los lagartos", "40-70", (238, 77, 248, 88),
     [("Lizard Sentinel", 4, 120), ("Lizard Templar", 3, 120), ("Lizard Snakecharmer", 2, 150)]),
    ("laguna", "Laguna", "15-30", (223, 86, 240, 97), [("Crocodile", 4, 90)]),
    ("oasis", "Oasis", "15-30", (240, 93, 260, 106), [("Cobra", 3, 90), ("Tarantula", 2, 120), ("Scorpion", 3, 90)]),
    ("huesos", "Campo de huesos", "45-80", (241, 107, 258, 118),
     [("Ghoul", 3, 120), ("Mummy", 5, 150), ("Crypt Shambler", 3, 150), ("Demon Skeleton", 3, 150),
      ("Bone Beast", 2, 240)]),
    ("santuario", "Santuario de los djinn", "60-90", (225, 98, 237, 108), [("Green Djinn", 5, 180), ("Efreet", 3, 240)]),
    ("cienaga", "Ciénaga", "50-70", (242, 87, 250, 92), [("Bog Raider", 3, 180)]),
    ("dunas", "Dunas del sur", "10-25", (214, 113, 233, 119), [("Scorpion", 3, 60), ("Larva", 3, 60), ("Lion", 2, 60)]),
]
# barco del muelle del sur (no se toca el mapa, solo se le ponen monstruos): piratas en la cubierta (z7).
# La bodega (z8) ya tenía fantasmas y esqueletos y queda como estaba.
# (piso, casilla de llegada, [(monstruo, cantidad, respawn s)]). Los looks vienen del cliente 8.60.
SHIP_BOX = (229, 124, 247, 129)
SHIP = [
    (7, (237, 124), [("Pirate Marauder", 4, 90), ("Pirate Cutthroat", 3, 120), ("Pirate Buccaneer", 2, 150),
                     ("Pirate Corsair", 1, 240)]),
]
# jefes en la casilla 'O' de su plano
BOSSES = {"nido": ("Furious Ancient Scarab", 1800), "huesos": ("Omruc", 3600)}
SIGN_TEXT = ("DESIERTO DE LAS RUINAS\n"
             "Ruinas (8+), dunas del sur (10+), laguna y oasis (15+),\n"
             "campamento de bandidos (20+), nido de escarabajos (30+),\n"
             "templo de los lagartos (40+), campo de huesos (45+),\n"
             "cienaga (50+), santuario de los djinn (60+).\nSigue el camino de piedra.\n"
             "En el barco del muelle: piratas en cubierta (25+).")
SCATTER = [2725, 2725, 2726, 2723, 2724, 2728, 2731, 2732, 2735, 1357, 1358, 2784]   # palmas, cactus, piedras, mata seca
SCATTER_EVERY = 24                            # una decoración cada tantas casillas de arena libre
CARD = ((1, 0), (-1, 0), (0, 1), (0, -1))
ALL8 = CARD + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def stamp_cells():
    for name, (x0, y0, rows) in STAMPS.items():
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch != " ":
                    yield name, x0 + dx, y0 + dy, ch


def build(old, otb, rng):
    """(casillas nuevas {(x, y): [ítems]}, protegidas, errores, info)."""
    name = lambda sid: otb.get(sid, {}).get("name", "")
    x1, y1, x2, y2 = BOX
    land = {(x, y): it for (x, y, z), it in old.items()
            if z == Z and x1 <= x <= x2 and y1 <= y <= y2 and it and "water" not in name(it[0])}
    grass = {c for c, it in land.items() if name(it[0]) == "grass"}
    protected = {c for c in land if name(land[c][0]) == "tar"
                 or any((c[0] + dx, c[1] + dy) in grass for dx in (-1, 0, 1) for dy in (-1, 0, 1))}
    errors = []
    new = {c: [it[0] if name(it[0]) == "sand" and it[0] != CRACKED else SAND] for c, it in land.items() if c not in protected}
    fixed, walls, chests, marks = set(), {k: set() for k in WALLS}, {}, {}
    for stamp, x, y, ch in stamp_cells():
        c = (x, y)
        if c not in new:
            errors.append(f"plano '{stamp}': la casilla {c} ('{ch}') no es arena de la isla")
            continue
        fixed.add(c)
        if ch in WALLS:
            walls[ch].add(c)
            continue
        if ch not in LEGEND:
            errors.append(f"plano '{stamp}': carácter desconocido '{ch}' en {c}")
            continue
        ground, items = LEGEND[ch]
        new[c] = [ground or new[c][0]] + items
        if ch in CHESTS:
            chests[c] = CHESTS[ch]
        if ch == "O":
            marks[stamp] = c
    for ch, (mate, dx, dy) in PAIRS.items():              # muebles de dos piezas: nunca una sola
        cells = {(x, y): k for _s, x, y, k in stamp_cells()}
        for (x, y), k in cells.items():
            if k == ch and cells.get((x + dx, y + dy)) != mate:
                errors.append(f"a la pieza '{ch}' de {(x, y)} le falta su par '{mate}'")
            if k == mate and cells.get((x - dx, y - dy)) != ch:
                errors.append(f"la pieza '{mate}' de {(x, y)} está suelta")
    for ch, cells in walls.items():                       # pared según vecinas al oeste y al norte
        p = WALLS[ch]
        for (x, y) in cells:
            w, n = (x - 1, y) in cells, (x, y - 1) in cells
            new[(x, y)].append(p["corner"] if w and n else p["h"] if w else p["v"] if n else p["post"])
    roads = set()
    for rx1, ry1, rx2, ry2 in ROADS:
        for y in range(ry1, ry2 + 1):
            for x in range(rx1, rx2 + 1):
                c = (x, y)
                if c in new and c not in fixed:
                    new[c] = [PAVE_DARK if rng.random() < 0.18 else PAVE]
                    roads.add(c)
    # restos de la ciudad apoyados en casillas de agua (una pared en la orilla): se limpian
    shore = {}
    for (x, y, z), it in old.items():
        if z == Z and x1 <= x <= x2 and y1 <= y <= y2 and it and "water" in name(it[0]):
            keep = [i for i in it if not any(k in name(i) for k in ("wall", "window", "door", "lamp"))]
            if keep != it:
                shore[(x, y)] = keep
    return new, protected, land, fixed, roads, chests, marks, shore, errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()

    otb = load_otb()
    old = load_tiles()
    rng = random.Random(a.seed)
    solid = lambda sid: "block_solid" in otb.get(sid, {}).get("flags", [])
    new, protected, land, fixed, roads, chests, marks, shore, errors = build(old, otb, rng)

    def items_at(c):
        return new[c] if c in new else old.get((c[0], c[1], Z), [])

    def walkable(c):
        it = items_at(c)
        return bool(it) and "water" not in otb.get(it[0], {}).get("name", "") and not any(solid(i) for i in it)

    # --- decoración suelta: solo donde no puede tapar un paso (las 8 vecinas libres) ---
    free = sorted(c for c in new if c not in fixed and c not in roads and len(new[c]) == 1)
    rng.shuffle(free)
    decor = set()
    for c in free:
        if len(decor) >= len(free) // SCATTER_EVERY:
            break
        near = [(c[0] + dx, c[1] + dy) for dx, dy in ALL8]
        if all(n in new and walkable(n) and n not in roads for n in near) \
                and all(max(abs(c[0] - d[0]), abs(c[1] - d[1])) >= 3 for d in decor) \
                and max(abs(c[0] - ENTRANCE[0]), abs(c[1] - ENTRANCE[1])) > 3:
            new[c].append(rng.choice(SCATTER))
            decor.add(c)

    # --- alcanzable desde la entrada ---
    seen, queue = {ENTRANCE}, deque([ENTRANCE])
    while queue:
        cx, cy = queue.popleft()
        for dx, dy in ALL8:
            n = (cx + dx, cy + dy)
            if n not in seen and (n in new or n in protected) and walkable(n):
                seen.add(n)
                queue.append(n)
    if not walkable(ENTRANCE):
        errors.append(f"la entrada {ENTRANCE} no se puede pisar")
    for label, c in (("el muelle", DOCK), ("la bajada del oasis", OASIS_STAIR)):
        if not any((c[0] + dx, c[1] + dy) in seen for dx, dy in ALL8 + ((0, 0),)):
            errors.append(f"no se llega a {label} {c}")
    for c, uid in chests.items():
        if not any((c[0] + dx, c[1] + dy) in seen for dx, dy in CARD):
            errors.append(f"el cofre {uid} de {c} no tiene acceso")
    lost = [c for c in new if walkable(c) and c not in seen]
    if len(lost) > 12:
        errors.append(f"{len(lost)} casillas de arena sin acceso, ej. {sorted(lost)[:3]}")

    # --- monstruos ---
    registry = (MONSTERS / "monsters.xml").read_text(encoding="latin-1").lower()
    for n in sorted({m[0] for z in ZONES for m in z[4]} | {b[0] for b in BOSSES.values()} | {m[0] for d in SHIP for m in d[2]}):
        if f'name="{n.lower()}"' not in registry:
            errors.append(f"monstruo sin registrar en monsters.xml: {n}")
    placed = []                                            # (nombre, (x, y), respawn, zona)
    for stamp, (boss, st) in BOSSES.items():
        if stamp not in marks:
            errors.append(f"el plano '{stamp}' no tiene la casilla 'O' del jefe")
        elif marks[stamp] not in seen:
            errors.append(f"el jefe {boss} quedaría en una casilla sin acceso {marks[stamp]}")
        else:
            placed.append((boss, marks[stamp], st, stamp))
    for key, _title, _lvl, (zx1, zy1, zx2, zy2), mons in ZONES:
        spots = sorted(c for c in seen if zx1 <= c[0] <= zx2 and zy1 <= c[1] <= zy2 and len(items_at(c)) == 1
                       and max(abs(c[0] - ENTRANCE[0]), abs(c[1] - ENTRANCE[1])) >= 6)
        rng.shuffle(spots)
        for mname, count, st in mons:
            got = 0
            for sep in (3, 2):
                for c in spots:
                    if got >= count:
                        break
                    if all(max(abs(c[0] - p[1][0]), abs(c[1] - p[1][1])) >= sep for p in placed):
                        placed.append((mname, c, st, key))
                        got += 1
            if got < count:
                errors.append(f"zona '{key}': solo entran {got} de {count} {mname}")

    # --- barco pirata: casillas libres de cada piso, alcanzables desde donde se llega ---
    ship = []                                              # (nombre, (x, y, z), respawn)
    bx1, by1, bx2, by2 = SHIP_BOX
    for z, start, mons in SHIP:
        deck = {(x, y): it for (x, y, zz), it in old.items() if zz == z and bx1 <= x <= bx2 and by1 <= y <= by2 and it
                and "water" not in otb.get(it[0], {}).get("name", "") and not any(solid(i) for i in it)
                and otb.get(it[0], {}).get("name") != "ladder"}
        reach, queue = {start} & set(deck), deque([start] if start in deck else [])
        while queue:
            cx, cy = queue.popleft()
            for dx, dy in ALL8:
                n = (cx + dx, cy + dy)
                if n in deck and n not in reach:
                    reach.add(n)
                    queue.append(n)
        if not reach:
            errors.append(f"barco z{z}: la llegada {start} no se puede pisar")
        spots = sorted(c for c in reach if len(deck[c]) == 1 and max(abs(c[0] - start[0]), abs(c[1] - start[1])) >= 2)
        rng.shuffle(spots)
        for mname, count, st in mons:
            got = 0
            for c in spots:
                if got >= count:
                    break
                if all(p[1][2] != z or max(abs(c[0] - p[1][0]), abs(c[1] - p[1][1])) >= 2 for p in ship):
                    ship.append((mname, (c[0], c[1], z), st))
                    got += 1
            if got < count:
                errors.append(f"barco z{z}: solo entran {got} de {count} {mname}")

    # --- uids de los cofres libres en el resto del mapa ---
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    md = root[2][0]
    ux1, uy1, ux2, uy2 = UPPER

    def doomed(x, y, z):
        return (z == Z and ((x, y) in new or (x, y) in shore)) or (z in (4, 5, 6) and ux1 <= x <= ux2 and uy1 <= y <= uy2)

    for area in md[2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        for t in area[2]:
            if t[0] not in (T_TILE, T_HOUSETILE) or doomed(ax + t[1][0], ay + t[1][1], az):
                continue
            for ch in t[2]:
                p = bytes(ch[1])
                for uid in CHESTS.values():
                    if ch[0] == T_ITEM and p[2:5] == bytes([ATTR_UNIQUE_ID]) + struct.pack("<H", uid):
                        errors.append(f"el uniqueId {uid} ya está en {(ax + t[1][0], ay + t[1][1], az)}")

    if a.preview:
        write_preview(a.preview, old, {**new, **shore}, placed, otb)
        print(f"preview: {a.preview}")
    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        return 1
    print(f"desierto x{BOX[0]}-{BOX[2]} y{BOX[1]}-{BOX[3]}: {len(new)} casillas rehechas, {len(protected)} protegidas, "
          f"{len(seen)} caminables, {len(decor)} decoraciones, {len(placed)} monstruos + {len(ship)} piratas en el barco")
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    # --- mapa ---
    backup = MAP.with_name(MAP.name + ".bak-desert")
    if not backup.exists():
        shutil.copy2(MAP, backup)
    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        area[2] = [t for t in area[2] if not (t[0] in (T_TILE, T_HOUSETILE) and doomed(ax + t[1][0], ay + t[1][1], az))]
        if not area[2]:
            md[2].remove(area)
    buckets = {}
    for (x, y), it in {**new, **shore}.items():
        buckets.setdefault((x & ~0xFF, y & ~0xFF), []).append((x, y, it))
    for (bx, by), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, Z)), []]
        for x, y, it in sorted(lst, key=lambda t: (t[1], t[0])):
            props = bytearray([x - bx, y - by, 9]) + struct.pack("<H", it[0])
            kids = []
            for i in it[1:]:
                p = bytearray(struct.pack("<H", i))
                if i == CHEST and (x, y) in chests:
                    p += bytes([ATTR_UNIQUE_ID]) + struct.pack("<H", chests[(x, y)])
                kids.append([T_ITEM, p, []])
            area[2].append([T_TILE, props, kids])
        md[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    # --- spawns: fuera los monstruos viejos de la superficie; adentro el bloque nuevo ---
    sp = SPAWNS.read_text(encoding="latin-1")
    sp = re.sub(r"\t?<!-- BEGIN DESERT_HUNTS_SPAWNS.*?<!-- END DESERT_HUNTS_SPAWNS -->\n?", "", sp, flags=re.S)
    removed = 0

    def clean(m):
        nonlocal removed
        cx, cy = int(m.group(2)), int(m.group(3))

        def keep(mm):
            nonlocal removed
            x, y, z = cx + int(mm.group(1)), cy + int(mm.group(2)), int(mm.group(3))
            gone = (z == Z and ((x, y) in new or (x, y) in protected)) or doomed(x, y, z)
            gone = gone or (z in {d[0] for d in SHIP} and bx1 <= x <= bx2 and by1 <= y <= by2)   # la cubierta del barco
            removed += gone
            return "" if gone else mm.group(0)

        body = re.sub(r'[ \t]*<monster [^>]*?x="(-?\d+)" y="(-?\d+)" z="(\d+)"[^>]*/>\n?', keep, m.group(4))
        return "" if "<monster" not in body else m.group(1) + body + m.group(5)

    sp = re.sub(r'([ \t]*<spawn centerx="(\d+)" centery="(\d+)"[^>]*>\n?)(.*?)([ \t]*</spawn>\n?)', clean, sp, flags=re.S)
    lines = ["\t<!-- BEGIN DESERT_HUNTS_SPAWNS (scripts/map/generate-desert-hunts.py) -->"]
    for mname, (x, y), st, _key in placed:
        lines.append(f'\t<spawn centerx="{x}" centery="{y}" centerz="{Z}" radius="3">')
        lines.append(f'\t\t<monster name="{mname}" x="0" y="0" z="{Z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    for mname, (x, y, z), st in ship:
        lines.append(f'\t<spawn centerx="{x}" centery="{y}" centerz="{z}" radius="2">')
        lines.append(f'\t\t<monster name="{mname}" x="0" y="0" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    lines.append("\t<!-- END DESERT_HUNTS_SPAWNS -->\n")
    SPAWNS.write_text(sp.replace("</spawns>", "\n".join(lines) + "</spawns>"), encoding="latin-1")

    # --- NPC y casas de la ciudad vieja ---
    npc = NPCS.read_text(encoding="latin-1")
    npc2 = re.sub(rf'[ \t]*<npc name="{OLD_NPC[0]}" x="{OLD_NPC[1]}" y="{OLD_NPC[2]}" z="{Z}"[^>]*/>\n?', "", npc)
    if npc2 != npc:
        NPCS.write_text(npc2, encoding="latin-1")
    hs = HOUSES.read_text(encoding="utf-8")
    hs2 = re.sub(r'<house name="(?:%s)[^"]*">.*?</house>\n?' % "|".join(OLD_HOUSES), "", hs, flags=re.S)
    if hs2 != hs:
        HOUSES.write_text(hs2, encoding="utf-8")
    gone_files = [f for f in sorted(HOUSE_DIR.glob("*.xml")) if f.stem.startswith(OLD_HOUSES)]
    for f in gone_files:
        f.unlink()

    # --- cartel ---
    rd = READABLES.read_text(encoding="latin-1")
    rd = re.sub(r"\t?<!-- BEGIN DESERT_HUNTS_SIGNS -->.*?<!-- END DESERT_HUNTS_SIGNS -->\n?", "", rd, flags=re.S)
    sx, sy, _rows = STAMPS["cartel"]
    lines = ["\t<!-- BEGIN DESERT_HUNTS_SIGNS -->",
             f'\t<readable x="{sx}" y="{sy}" z="{Z}" text="{SIGN_TEXT.replace(chr(10), chr(92) + "n")}"/>',
             "\t<!-- END DESERT_HUNTS_SIGNS -->\n"]
    READABLES.write_text(rd.replace("</readables>", "\n".join(lines) + "</readables>"), encoding="latin-1")

    count = {}
    for mname, _c, _st, key in placed:
        count.setdefault(key, {}).setdefault(mname, 0)
        count[key][mname] += 1
    MANIFEST.write_text(json.dumps({
        "name": "generated-desert-hunts", "seed": a.seed,
        "box": {"x1": BOX[0], "y1": BOX[1], "x2": BOX[2], "y2": BOX[3], "z": Z},
        "entrance": {"x": ENTRANCE[0], "y": ENTRANCE[1], "z": Z},
        "zones": [{"key": k, "name": t, "level": lvl, "box": list(b), "monsters": count.get(k, {})} for k, t, lvl, b, _m in ZONES],
        "bosses": [{"name": n, "x": c[0], "y": c[1], "z": Z, "spawntime": st} for n, c, st, _k in placed if n in {b[0] for b in BOSSES.values()}],
        "chests": [{"x": c[0], "y": c[1], "z": Z, "uid": uid} for c, uid in sorted(chests.items())],
        "ship": [{"name": n, "x": c[0], "y": c[1], "z": c[2], "spawntime": st} for n, c, st in ship],
        "total": len(placed) + len(ship),
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS} ({removed} monstruos viejos fuera)\nOK casas: {len(gone_files)} archivos fuera"
          f"\nOK cartel {READABLES}\nOK {MANIFEST}")
    return 0


def write_preview(path: Path, old, new, placed, otb):
    """La isla con los sprites reales y cada monstruo en su lugar."""
    from PIL import Image
    from game_render import LAYER_RANK, Sprites, compose, creature_image, layer_of, parse_dat_all
    items, outfits = parse_dat_all()
    spr = Sprites()
    x0, y0, x1, y1 = BOX[0] - 4, BOX[1] - 2, BOX[2] + 2, BOX[3] + 4
    t = {(x, y): it for (x, y, z), it in old.items() if z == Z and x0 <= x <= x1 + 2 and y0 <= y <= y1 + 2}
    t.update(new)
    W, H = (x1 - x0 + 1) * 32, (y1 - y0 + 1) * 32
    img = Image.new("RGBA", (W, H), (14, 14, 18, 255))

    def paste(im, px, py):
        if px < 0 or py < 0:
            im = im.crop((max(0, -px), max(0, -py), im.width, im.height))
            px, py = max(0, px), max(0, py)
        if im.width > 0 and im.height > 0:
            img.alpha_composite(im, (px, py))

    mons = {c: n for n, c, _s, _k in placed}
    looks = {}
    for n in set(mons.values()):
        f = MONSTERS / f"{n.lower()}.xml"
        m = re.search(r"<look\s+([^>]*)>", f.read_text(encoding="latin-1")) if f.exists() else None
        if m:
            looks[n] = creature_image({k: int(v) for k, v in re.findall(r'(\w+)="(\d+)"', m.group(1))}, outfits, spr)
    for y in range(y0, y1 + 3):
        for x in range(x0, x1 + 3):
            stack = [(LAYER_RANK[layer_of(items[otb[s]["cid"]])], i, items[otb[s]["cid"]])
                     for i, s in enumerate(t.get((x, y), [])) if s in otb and otb[s].get("cid") in items]
            for _r, _i, e in sorted(stack, key=lambda v: (v[0], v[1])):
                im = compose(e, spr, x % e["px"], y % e["py"])
                paste(im, (x - x0 + 1) * 32 - im.width, (y - y0 + 1) * 32 - im.height)
            im = looks.get(mons.get((x, y)))
            if im is not None:
                paste(im, (x - x0 + 1) * 32 - im.width - 8, (y - y0 + 1) * 32 - im.height - 8)
    img.convert("RGB").save(path)


if __name__ == "__main__":
    sys.exit(main())
