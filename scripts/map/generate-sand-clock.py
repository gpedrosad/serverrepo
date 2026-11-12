#!/usr/bin/env python3
"""Reloj de Arena: sala chica de oleadas que suben de nivel (la maneja el NPC Chronos).

Sala de arena con paredes de arenisca, 11x9 por dentro (z6), en el mismo lugar que la sala vieja
(17x15 de piso blanco). La lógica de las oleadas está en data/npc/scripts/chronos.lua; este script
solo dibuja la sala y escribe su cartel:

  - al norte, Chronos en el centro y 6 braseros que se encienden según la oleada (3 a cada lado);
  - dos columnas de arenisca de cobertura; antorchas y faroles en las paredes;
  - al sur, la llegada, el portal de salida al templo entre dos estatuas y el cartel con las reglas.

Alrededor de la sala, tierra (bloquea) hasta media pantalla, y techo de madera en z5 encima: desde
adentro nunca se ve negro. Coordenadas: chronos.lua (ROOM, BRAZIERS, SPAWN_SPOTS) debe coincidir.

Uso (desde la raíz del repo):
  python3 scripts/map/generate-sand-clock.py --dry-run
  python3 scripts/map/generate-sand-clock.py            # escribe mapa, cartel y manifiesto
  python3 scripts/map/temple-portals.py                 # después: portal y cartel de la plaza
Doc: docs/gameplay/SAND_CLOCK.md.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, load_otb, parse_tree, serialize_tree  # noqa: E402

WORLD = REPO / "server/YurOTS/ots/data/world"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MANIFEST = WORLD / "generated-sand-clock.json"

Z_PLAY, Z_ROOF = 6, 5
ROOM = dict(x0=333, y0=388, x1=343, y1=396)          # piso caminable (11x9)
CLEAR = (325, 381, 351, 403)                          # z5-z6: sala vieja + media pantalla alrededor
TEMPLE_LANDING = (168, 48, 7)                         # llegada del portal del Reloj en la plaza
CX = 338
CHRONOS = (CX, ROOM["y0"])
LANDING = (CX, ROOM["y1"] - 1)
EXIT_TP = (CX, ROOM["y1"])
BRAZIERS = [(333, 388), (334, 388), (335, 388), (341, 388), (342, 388), (343, 388)]   # oleadas 1-6
PILLARS = [(335, 392), (341, 392)]
STATUES = [(CX - 2, ROOM["y1"]), (CX + 2, ROOM["y1"])]
SIGN_POS = (CX + 1, ROOM["y1"])
SPAWN_SPOTS = [(334, 390), (338, 390), (342, 390), (336, 391), (340, 391), (334, 393), (342, 393),
               (337, 392), (339, 392), (336, 393), (340, 393)]

SAND, EARTH, WOOD = 231, 101, 405
WALL = dict(post=1062, h=1063, v=1060, se=1066)       # arenisca: poste NO, horizontal, vertical, L SE
TELEPORT, SIGN = 1387, 1429
PILLAR, STATUE, BRAZIER = 1549, 1451, 1482
TORCH_V, LAMP_H = 2061, 2040                          # colgables: pared oeste/este (vertical) y norte
ATTR_TELE_DEST = 8

SIGN_TEXT = ("RELOJ DE ARENA\nDescanso de 30 s y despues 6 oleadas de 60 s,\ncada una mas fuerte. "
             "Los braseros marcan la oleada.\nEntra en el descanso para empezar desde la 1.\nSalida: portal al sur.")


def build() -> dict:
    t: dict[tuple[int, int, int], list[int]] = {}
    x0, y0, x1, y1 = ROOM["x0"], ROOM["y0"], ROOM["x1"], ROOM["y1"]
    for x in range(CLEAR[0], CLEAR[2] + 1):
        for y in range(CLEAR[1], CLEAR[3] + 1):
            t[(x, y, Z_ROOF)] = [WOOD]
            t[(x, y, Z_PLAY)] = [EARTH]
    for x in range(x0 - 1, x1 + 2):
        for y in range(y0 - 1, y1 + 2):
            t[(x, y, Z_PLAY)] = [SAND]

    def add(c, item):
        t[(c[0], c[1], Z_PLAY)].append(item)

    for x in range(x0, x1 + 1):
        add((x, y0 - 1), WALL["h"])
        add((x, y1 + 1), WALL["h"])
    for y in range(y0, y1 + 1):
        add((x0 - 1, y), WALL["v"])
        add((x1 + 1, y), WALL["v"])
    add((x0 - 1, y0 - 1), WALL["post"])
    add((x1 + 1, y0 - 1), WALL["h"])
    add((x0 - 1, y1 + 1), WALL["v"])
    add((x1 + 1, y1 + 1), WALL["se"])
    for y in (y0 + 2, y1 - 2):
        add((x0 - 1, y), TORCH_V)
        add((x1 + 1, y), TORCH_V)
    for x in (CX - 2, CX + 2):
        add((x, y0 - 1), LAMP_H)
    for c in BRAZIERS:
        add(c, BRAZIER)
    for c in PILLARS:
        add(c, PILLAR)
    for c in STATUES:
        add(c, STATUE)
    add(SIGN_POS, SIGN)
    add(EXIT_TP, TELEPORT)
    return t


def validate(t: dict) -> list[str]:
    otb = load_otb()
    blocks = lambda c: any("block_solid" in otb.get(i, {}).get("flags", []) for i in t[c][1:])  # noqa: E731
    walk = {c for c in t if c[2] == Z_PLAY and t[c][0] == SAND and not blocks(c)}
    errors = []
    start = (LANDING[0], LANDING[1], Z_PLAY)
    seen, todo = {start}, [start]
    while todo:
        x, y, z = todo.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy, z)
            if n in walk and n not in seen:
                seen.add(n)
                todo.append(n)
    for label, c in [("Chronos", CHRONOS), ("salida", EXIT_TP)] + [("spawn", s) for s in SPAWN_SPOTS]:
        if (c[0], c[1], Z_PLAY) not in seen:
            errors.append(f"{label} {c}: no se llega desde la llegada")
    for c in walk:
        if not (CLEAR[0] + 8 <= c[0] <= CLEAR[2] - 8 and CLEAR[1] + 6 <= c[1] <= CLEAR[3] - 6):
            errors.append(f"{c}: se ve el borde negro")
    return errors


def item_node(iid: int, tele=None):
    props = bytearray(struct.pack("<H", iid))
    if tele is not None:
        props += bytes([ATTR_TELE_DEST]) + struct.pack("<HHB", *tele)
    return [T_ITEM, props, []]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    t = build()
    errors = validate(t)
    if errors:
        print("\n".join(errors[:30]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        return 1
    print(f"Reloj de Arena: sala {ROOM['x0']}-{ROOM['x1']}, {ROOM['y0']}-{ROOM['y1']} z{Z_PLAY} (11x9); "
          f"llegada {LANDING[0]},{LANDING[1]},{Z_PLAY}; salida {EXIT_TP[0]},{EXIT_TP[1]},{Z_PLAY}; Chronos {CHRONOS}")
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    raw = MAP.read_bytes()
    root = parse_tree(raw)
    md = root[2][0]
    backup = MAP.with_name(MAP.name + ".bak-sand-clock")
    if not backup.exists():
        shutil.copy2(MAP, backup)
    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        if az not in (Z_PLAY, Z_ROOF):
            continue
        area[2] = [n for n in area[2] if not (n[0] in (T_TILE, T_HOUSETILE)
                                              and CLEAR[0] <= ax + n[1][0] <= CLEAR[2]
                                              and CLEAR[1] <= ay + n[1][1] <= CLEAR[3])]
        if not area[2]:
            md[2].remove(area)
    buckets: dict = {}
    for (x, y, z), items in t.items():
        buckets.setdefault((x & ~0xFF, y & ~0xFF, z), []).append((x, y, items))
    for (bx, by, z), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, z)), []]
        for x, y, items in sorted(lst, key=lambda e: (e[1], e[0])):
            props = bytearray([x - bx, y - by, 9]) + struct.pack("<H", items[0])
            kids = [item_node(i, TEMPLE_LANDING if i == TELEPORT else None) for i in items[1:]]
            area[2].append([T_TILE, props, kids])
        md[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    rd = READABLES.read_text(encoding="latin-1")
    rd = re.sub(r"[ \t]*<!-- BEGIN SAND_CLOCK_SIGNS -->.*?<!-- END SAND_CLOCK_SIGNS -->\n?", "", rd, flags=re.S)
    block = ("\t<!-- BEGIN SAND_CLOCK_SIGNS -->\n"
             f'\t<readable x="{SIGN_POS[0]}" y="{SIGN_POS[1]}" z="{Z_PLAY}" text="{SIGN_TEXT.replace(chr(10), chr(92) + "n")}"/>\n'
             "\t<!-- END SAND_CLOCK_SIGNS -->\n")
    rd = rd.replace("</readables>", block + "</readables>")
    READABLES.write_text(rd, encoding="latin-1")

    MANIFEST.write_text(json.dumps({
        "name": "generated-sand-clock",
        "room": {**ROOM, "z": Z_PLAY},
        "clearBox": {"x1": CLEAR[0], "y1": CLEAR[1], "x2": CLEAR[2], "y2": CLEAR[3], "z": [Z_ROOF, Z_PLAY]},
        "landing": {"x": LANDING[0], "y": LANDING[1], "z": Z_PLAY},
        "returnTp": {"x": EXIT_TP[0], "y": EXIT_TP[1], "z": Z_PLAY, "to": list(TEMPLE_LANDING)},
        "chronos": {"x": CHRONOS[0], "y": CHRONOS[1], "z": Z_PLAY},
        "braziers": [{"x": x, "y": y, "z": Z_PLAY} for x, y in BRAZIERS],
        "spawnSpots": [{"x": x, "y": y, "z": Z_PLAY} for x, y in SPAWN_SPOTS],
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK cartel {READABLES}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
