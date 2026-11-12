#!/usr/bin/env python3
"""Castillo Imperial: rehace el castillo de la isla al noroeste del templo (antes una casa vacía).

Seis pisos, de más fácil a más difícil. Se entra por la puerta sur de la planta baja y se sube:

  z8  Cripta (opcional, baja desde la planta baja): Ghoul, Mummy, Crypt Shambler, Demon Skeleton, Vampire
  z7  Planta baja, patio de armas y cuartel: Wild Warrior, Amazon, Valkyrie, Hunter
  z6  Salón y capilla: Monk, Dark Monk, Witch, Priestess, Stone Golem
  z5  Biblioteca: Necromancer, Priestess, Lich, Banshee
  z4  Guardia real: Hero, Black Knight
  z3  Sala del trono: Imperial Hero (nuevo, look 240) y la tesorería con 2 cofres de quest
      (quest.lua: uid = id del premio; crown legs 2488 y royal helmet 2498)

Caja: x 88-112, y 25-39 (25x15) en z3-z7; la cripta ocupa y 25-34 en z8 (debajo, desde y 36, hay una cueva
que no se toca). El castillo viejo llegaba hasta x 116: esa franja queda como pasto. El puente de z6 (x >= 113,
y >= 37) y su bajada a la isla no se tocan.

Cada piso es un plano de texto (PLANS): '#' pared, 'W' ventana, 't' antorcha, 'p' tapiz, '.' piso,
':' piso de mármol, '<' escalera que sube (se llega una casilla al norte, un piso arriba), '>' hueco que baja
(se llega una casilla al sur, un piso abajo) y letras de decorado (DECOR). La pieza de pared sale sola de sus
vecinas. Valida antes de escribir: escaleras encadenadas, todo el piso alcanzable y cofres con acceso.

Uso (desde la raíz del repo):
  python3.11 scripts/map/generate-imperial-castle.py --dry-run --preview /tmp/castillo.png
  python3.11 scripts/map/generate-imperial-castle.py          # escribe mapa, spawns y cartel
Re-ejecutable: borra la caja y reemplaza los bloques IMPERIAL_CASTLE de spawns y carteles.
Doc: docs/gameplay/IMPERIAL_CASTLE.md.
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
sys.path.insert(0, str(HERE / "kb"))
sys.path.insert(0, str(HERE))
from mapdata import MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, load_otb, load_tiles, parse_tree, serialize_tree  # noqa: E402

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MONSTERS = REPO / "server/YurOTS/ots/data/monster"
MANIFEST = WORLD / "generated-imperial-castle.json"

X0, Y0, W, H = 88, 25, 25, 15                 # caja del castillo: x 88-112, y 25-39
OLD_BOX = (88, 25, 116, 40)                   # lo que ocupaba el castillo viejo (y el margen oeste nuevo)
ATTR_UNIQUE_ID = 5

# --- piezas -------------------------------------------------------------------------------------
WALL_V, WALL_H, WALL_POST, WALL_CORNER = 1049, 1050, 1051, 1053   # pared de piedra gris
WINDOW_H, WINDOW_V = 1267, 1268
TORCH_H, TORCH_V = 2059, 2061
TAPESTRY_H, TAPESTRY_V = 1857, 1856           # tapiz morado
STAIRS_UP, HOLE, CHEST, SIGN = 1385, 432, 1740, 1429
GRASS, EARTH = 4526, 101
TILE, MARBLE, BLACK_MARBLE, WOOD, STONE = 3152, 406, 407, 405, 431
# piso y piso de acento (':') de cada nivel
FLOOR = {8: (STONE, BLACK_MARBLE), 7: (TILE, MARBLE), 6: (WOOD, TILE), 5: (WOOD, TILE),
         4: (TILE, BLACK_MARBLE), 3: (MARBLE, BLACK_MARBLE)}
# Muebles de varias piezas (ver docs/items-and-map/PIEZAS_DE_MAPA.md): el ataúd es cabecera (k, K) + pie (j)
# en la casilla de abajo; el sarcófago, q + Q; el banco, e + E a su derecha. Las sillas miran a la mesa:
# 'v' mira al sur (va al norte de la mesa) y '^' mira al norte. 'T' es una mesa entera de una casilla.
DECOR = {"b": 1774, "c": 1739, "T": 1614, "v": 1652, "^": 1650, "k": 1410, "K": 1413, "j": 1411, "q": 1417, "Q": 1418,
         "e": 1662, "E": 1663, "x": 3060, "s": 1442, "f": 1484, "a": 1643, "l": 2041, "o": 1718, "R": 1654,
         "P": 1515, "d": 1716}
PAIRS = {"k": ("j", 0, 1), "K": ("j", 0, 1), "q": ("Q", 0, 1), "e": ("E", 1, 0)}   # pieza -> (la que sigue, dx, dy)
CHESTS = {"A": 2488, "B": 2498}               # crown legs, royal helmet
NEEDS_COUNT = {2320}

PLANS = {
    8: ["###t#####t#####t#####t###",
        "#...k.#.k.k.#.K.K.#..q..#",
        "#...j.#.j.j.#.j.j.#..Q..#",
        "#.<...#...x.#.x...#.....#",
        "#.....#.....#.....#f...f#",
        "##.#####.#####.#####.####",
        "#.......................#",
        "#...k......k.....k......#",
        "#...j......j.....j......#",
        "#########################"],
    7: ["###W###t###W###t####W#t##",
        "#b..vv....#f......f#....#",
        "#c..TT....#...::...#..<.#",
        "#.>.^^....#...::...#....#",
        "W.........#...::...#....W",
        "#.........#...::........#",
        "#.............::...#....#",
        "###.#######...::...#....#",
        "#.........#...::...#....#",
        "#.............::........#",
        "W.........#...::...#....W",
        "#.......cb#...::...#.dd.#",
        "#......bcc#.s.::.s.#....#",
        "#.........#..i::...#....#",
        "###W###t######..###t#W###"],
    6: ["###W###t###W###t####W#t##",
        "#.s.a.s..#l.vvvvv.l#....#",
        "#........#..TTTTT..#..>.#",
        "#........#..^^^^^..#....#",
        "W.eE.eE.................W",
        "#........#.........#....#",
        "#.eE.eE..#.........######",
        "#........#..............#",
        "####.#####..............#",
        "#........#....P....P....#",
        "W.......................W",
        "#........#..............#",
        "#.<......#....P....P....#",
        "#b.......#..............#",
        "###W###t###W###t###W#t###"],
    5: ["###W###t###W###t####W#t##",
        "#.....#.ooooooooo.#.....#",
        "#.....#...........#.....#",
        "#....................<..#",
        "W.....#..vv...vv..#.....W",
        "#.....#..TT...TT..#.....#",
        "###.###..^^...^^..###.###",
        "#.......................#",
        "#.......................#",
        "###.###..vv...vv..###.###",
        "W.....#..TT...TT..#.....W",
        "#.....#..^^...^^..#.....#",
        "#.>..................d..#",
        "#.....#...l.....l.#.....#",
        "###W###t###W###t###W#t###"],
    4: ["                         ",
        "  ###W###t###W###t###W#  ",
        "  #.s.....s.....s.....#  ",
        "  #..................>#  ",
        "  #...................#  ",
        "  W...f...........f...W  ",
        "  #...................#  ",
        "  #######.....#########  ",
        "  #...................#  ",
        "  W...f...........f...W  ",
        "  #.....<.............#  ",
        "  #...................#  ",
        "  #.s.....s.....s.....#  ",
        "  ###W###t###W###t###W#  ",
        "                         "],
    3: ["                         ",
        "                         ",
        "      #t##W###W##t#      ",
        "      #..A.....B..#      ",
        "      #...........#      ",
        "      ##########.##      ",
        "      #..f..R..f..#      ",
        "      W.....:.....W      ",
        "      #..P..:..P..#      ",
        "      #.....:.....#      ",
        "      #.>...:.....#      ",
        "      #..P..:..P..#      ",
        "      ###W##t##W###      ",
        "                         ",
        "                         "],
}
ORDER = (7, 8, 6, 5, 4, 3)                    # de más fácil a más difícil
NAMES = {8: "Cripta", 7: "Planta baja: patio de armas", 6: "Salón y capilla", 5: "Biblioteca",
         4: "Guardia real", 3: "Sala del trono"}
# (monstruo, cantidad, segundos de respawn)
MONSTERS_BY_FLOOR = {
    7: [("Wild Warrior", 4, 60), ("Amazon", 3, 60), ("Valkyrie", 3, 75), ("Hunter", 3, 75)],
    8: [("Ghoul", 3, 75), ("Mummy", 3, 90), ("Crypt Shambler", 3, 90), ("Demon Skeleton", 3, 120), ("Vampire", 2, 150)],
    6: [("Monk", 4, 90), ("Dark Monk", 3, 90), ("Witch", 2, 100), ("Stone Golem", 2, 100), ("Priestess", 2, 120),
        ("Imperial Archer", 2, 120)],
    5: [("Necromancer", 3, 150), ("Court Mage", 3, 150), ("Imperial Archer", 2, 120), ("Priestess", 2, 120),
        ("Lich", 2, 240), ("Banshee", 1, 300)],
    4: [("Hero", 5, 240), ("Black Knight", 2, 300)],
    3: [("Imperial Hero", 3, 600)],
}
# en una casilla fija (coordenadas del plano): el jefe, frente al trono, cada 2 horas
FIXED = {3: [("The Fallen Emperor", (12, 7), 7200)]}
# afuera del castillo, en el campo del sur de la isla: caza fácil pegada a la ciudad
OUTSIDE = ("Imperial Squire", 8, 60)
OUTSIDE_BOX = (86, 41, 116, 46)               # x1, y1, x2, y2 en z7
OUTSIDE_AVOID = [(102, 40), (103, 40), (115, 39)]   # la puerta y la bajada del puente
SIGN_TEXT = "CASTILLO IMPERIAL\nCada piso es mas duro que el anterior.\nArriba esperan los Imperial Heroes y el tesoro."
WALLS = "#Wtp"
CARD = ((1, 0), (-1, 0), (0, 1), (0, -1))
ALL8 = CARD + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def cell(z, x, y) -> str:
    plan = PLANS[z]
    return plan[y][x] if 0 <= y < len(plan) and 0 <= x < W else " "


def wall_piece(z, x, y) -> tuple[int, str]:
    """Las paredes van en el borde sur y este de la casilla: la pieza depende de si sigue al oeste y al norte."""
    west, north = cell(z, x - 1, y) in WALLS, cell(z, x, y - 1) in WALLS
    if west and north:
        return WALL_CORNER, "c"
    if west:
        return WALL_H, "h"
    if north:
        return WALL_V, "v"
    return WALL_POST, "p"


def build_floor(z, old) -> dict:
    """(x, y) locales -> lista de ids. `old` = casillas actuales del mapa (para el pasto bajo la pared norte)."""
    floor, accent = FLOOR[z]
    tiles = {}
    for y, row in enumerate(PLANS[z]):
        for x, ch in enumerate(row):
            if ch == " ":
                continue
            if ch in WALLS:
                piece, kind = wall_piece(z, x, y)
                outside = cell(z, x - 1, y) == " " or cell(z, x, y - 1) == " "    # fila norte o columna oeste
                if not outside:
                    base = [floor]
                elif z == 7:
                    base = [i for i in old.get((X0 + x, Y0 + y, 7), []) if i in KEEP_GROUND] or [GRASS]
                elif z == 8:
                    base = [EARTH]
                else:
                    base = []
                items = base + [piece]
                if ch == "W" and kind in "hv":
                    items[-1] = WINDOW_H if kind == "h" else WINDOW_V
                elif ch == "t" and kind in "hv":
                    items.append(TORCH_H if kind == "h" else TORCH_V)
                elif ch == "p" and kind in "hv":
                    items.append(TAPESTRY_H if kind == "h" else TAPESTRY_V)
                tiles[(x, y)] = items
            elif ch == ">":
                tiles[(x, y)] = [HOLE]
            elif ch == "<":
                tiles[(x, y)] = [floor, STAIRS_UP]
            elif ch == ":":
                tiles[(x, y)] = [accent]
            elif ch == "i":
                tiles[(x, y)] = [floor, SIGN]
            elif ch in CHESTS:
                tiles[(x, y)] = [floor, CHEST]
            elif ch in DECOR:
                tiles[(x, y)] = [floor, DECOR[ch]]
            else:
                tiles[(x, y)] = [floor]
    return tiles


KEEP_GROUND: set = set()


def find(z, ch):
    return [(x, y) for y, row in enumerate(PLANS[z]) for x, c in enumerate(row) if c == ch]


def reach(walk: set, start, steps=ALL8) -> dict:
    dist, q = {start: 0}, deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in steps:
            n = (x + dx, y + dy)
            if n in walk and n not in dist:
                dist[n] = dist[(x, y)] + 1
                q.append(n)
    return dist


def place_monsters(z, walk, avoid, rng):
    out = [(name, c, st) for name, c, st in FIXED.get(z, [])]
    taken = [c for _n, c, _s in out]
    for name, count, spawntime in MONSTERS_BY_FLOOR[z]:
        cands = sorted(walk - avoid)
        rng.shuffle(cands)
        placed = 0
        for c in cands:
            if placed >= count:
                break
            if any(max(abs(c[0] - o[0]), abs(c[1] - o[1])) < (2 if z == 8 else 3) for o in taken):   # la cripta es más chica
                continue
            taken.append(c)
            out.append((name, c, spawntime))
            placed += 1
        if placed < count:
            print(f"aviso: {name} z{z}: {placed}/{count}", file=sys.stderr)
    return out


def new_tile(x, y, bx, by, items, uid=None):
    """Casilla con su primer ítem en el lugar del suelo y el resto como hijos; el cofre lleva uniqueId."""
    props = bytearray([x - bx, y - by, 9]) + struct.pack("<H", items[0])
    kids = []
    for i in items[1:]:
        p = bytearray(struct.pack("<H", i))
        if i in NEEDS_COUNT:
            p.append(1)
        if i == CHEST and uid is not None:
            p += bytes([ATTR_UNIQUE_ID]) + struct.pack("<H", uid)
        kids.append([T_ITEM, p, []])
    return [T_TILE, props, kids]


def monster_looks() -> dict:
    looks = {}
    extra = [[(n, 0, 0) for n, _c, _s in lst] for lst in FIXED.values()] + [[OUTSIDE]]
    for names in list(MONSTERS_BY_FLOOR.values()) + extra:
        for name, _n, _s in names:
            f = MONSTERS / f"{name.lower()}.xml"
            m = re.search(r"<look\s+([^>]*)>", f.read_text(encoding="latin-1")) if f.exists() else None
            if m:
                looks[name] = {k: int(v) for k, v in re.findall(r'(\w+)="(\d+)"', m.group(1))}
    return looks


def write_preview(path: Path, floors, monsters, old):
    """Una imagen con los 6 pisos (orden de dificultad), con los sprites reales y los monstruos en su lugar."""
    from PIL import Image, ImageDraw, ImageFont
    from game_render import LAYER_RANK, Sprites, compose, creature_image, layer_of, parse_dat_all
    otb = load_otb()
    items, outfits = parse_dat_all()
    spr = Sprites()
    entry = {sid: items.get(e.get("cid")) for sid, e in otb.items() if e.get("cid")}
    looks = monster_looks()
    cache, mcache = {}, {}
    M = 2                                                     # margen de contexto (solo z7 tiene isla alrededor)

    def draw_floor(z, bounds=None):
        x0, y0, cols, rows = bounds or (X0 - M, Y0 - M, W + 2 * M, H + 2 * M)
        t = {(X0 + x, Y0 + y): it for (x, y), it in floors[z].items()}
        if z == 7:
            for (x, y, zz), it in old.items():
                if zz == 7 and (x, y) not in t and x0 <= x < x0 + cols + 3 and y0 <= y < y0 + rows + 3:
                    yard = X0 + W <= x <= OLD_BOX[2] and Y0 <= y <= 36      # franja este: queda como pasto
                    t[(x, y)] = ([i for i in it if i in KEEP_GROUND] or [GRASS]) if yard else it
        mons = {(X0 + c[0], Y0 + c[1]): name for name, c, _s in monsters[z]}
        if z == 7:
            mons.update({c: name for name, c, _s in monsters.get("outside", [])})
        canvas = Image.new("RGBA", (cols * 32 + 64, rows * 32 + 64), (14, 14, 18, 255))
        for ty in range(y0, y0 + rows + 2):
            for tx in range(x0, x0 + cols + 2):
                draw = []
                for sid in t.get((tx, ty), []):
                    e = entry.get(sid)
                    if e is None:
                        continue
                    key = (sid, tx % e["px"], ty % e["py"])
                    im = cache.get(key) or cache.setdefault(key, compose(e, spr, key[1], key[2]))
                    draw.append((LAYER_RANK[layer_of(e)], im, e))
                draw.sort(key=lambda d: d[0])
                elev = 0
                for _r, im, e in draw:
                    dx = dy = 0
                    if 0x18 in e["flags"]:
                        dx, dy = struct.unpack("<HH", e["flags"][0x18])
                    canvas.paste(im, ((tx - x0) * 32 - (e["w"] - 1) * 32 - dx - elev,
                                      (ty - y0) * 32 - (e["h"] - 1) * 32 - dy - elev), im)
                    if 0x19 in e["flags"]:
                        elev = min(24, elev + struct.unpack("<H", e["flags"][0x19])[0])
                name = mons.get((tx, ty))
                if name and name in looks:
                    im = mcache.get(name) or mcache.setdefault(name, creature_image(looks[name], outfits, spr))
                    if im is not None:
                        canvas.paste(im, ((tx - x0) * 32 + 32 - im.width, (ty - y0) * 32 + 32 - im.height), im)
        return canvas.crop((0, 0, cols * 32, rows * 32)).convert("RGB")

    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
    small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15)
    imgs = [(z, draw_floor(z)) for z in ORDER]
    fw, fh, head = imgs[0][1].width, imgs[0][1].height, 62
    sheet = Image.new("RGB", (fw * 3 + 40, (fh + head) * 2 + 30), (24, 24, 30))
    d = ImageDraw.Draw(sheet)
    for i, (z, im) in enumerate(imgs):
        ox, oy = 10 + (i % 3) * (fw + 10), 10 + (i // 3) * (fh + head + 10)
        d.text((ox + 4, oy + 2), f"{i + 1}. {NAMES[z]} (piso {z})", font=font, fill=(255, 226, 120))
        names = [f"{n} (jefe)" for n, _c, _s in FIXED.get(z, [])] + [f"{n} x{c}" for n, c, _s in MONSTERS_BY_FLOOR[z]]
        d.text((ox + 4, oy + 32), ", ".join(names), font=small, fill=(220, 220, 228))
        sheet.paste(im, (ox, oy + head))
    sheet.save(path)
    isle = draw_floor(7, (84, 23, 35, 25))                    # la isla entera, con los de afuera
    out = Image.new("RGB", (isle.width, isle.height + 40), (24, 24, 30))
    ImageDraw.Draw(out).text((8, 8), f"La isla: {OUTSIDE[0]} x{OUTSIDE[1]} afuera, en el campo del sur", font=font, fill=(255, 226, 120))
    out.paste(isle, (0, 40))
    out.save(path.with_name(path.stem + "-isla" + path.suffix))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()

    otb = load_otb()
    blocks = lambda sid: "block_solid" in otb.get(sid, {}).get("flags", [])
    walkable = lambda items: bool(items) and not any(blocks(i) for i in items)
    old = load_tiles()
    KEEP_GROUND.update(sid for sid, e in otb.items() if e.get("name") in ("grass", "shallow water", "dirt", "sand"))

    errors = []
    for z, plan in PLANS.items():
        for y, row in enumerate(plan):
            if len(row) != W:
                errors.append(f"z{z} fila {y}: mide {len(row)}, tiene que medir {W}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    floors = {z: build_floor(z, old) for z in PLANS}
    walk = {z: {c for c, it in t.items() if walkable(it) and it[0] != HOLE and STAIRS_UP not in it} for z, t in floors.items()}

    for z in PLANS:                                     # muebles de dos piezas: nunca una sola
        for ch, (mate, dx, dy) in PAIRS.items():
            for (x, y) in find(z, ch):
                if cell(z, x + dx, y + dy) != mate:
                    errors.append(f"z{z}: a la pieza '{ch}' de {(x, y)} le falta su par '{mate}'")
        for mate, dx, dy in set(PAIRS.values()):
            for (x, y) in find(z, mate):
                if cell(z, x - dx, y - dy) not in [c for c, v in PAIRS.items() if v == (mate, dx, dy)]:
                    errors.append(f"z{z}: la pieza '{mate}' de {(x, y)} está suelta")
        for ch, dy in (("v", 1), ("^", -1)):               # las sillas miran a una mesa
            for (x, y) in find(z, ch):
                if cell(z, x, y + dy) != "T":
                    errors.append(f"z{z}: la silla de {(x, y)} no mira a una mesa")
    # escaleras: '<' en z con '>' en z-1 en la misma casilla; se llega al norte (arriba) y al sur (abajo)
    for z in PLANS:
        for (x, y) in find(z, "<"):
            if z - 1 not in PLANS or cell(z - 1, x, y) != ">":
                errors.append(f"z{z}: la escalera {(x, y)} no tiene hueco arriba")
            elif (x, y - 1) not in walk[z - 1]:
                errors.append(f"z{z}: al subir por {(x, y)} se llega a {(x, y - 1)}, que no es piso libre")
            if (x, y + 1) not in walk[z]:
                errors.append(f"z{z}: no se puede pisar al sur de la escalera {(x, y)}")
        for (x, y) in find(z, ">"):
            if z + 1 not in PLANS or cell(z + 1, x, y) != "<":
                errors.append(f"z{z}: el hueco {(x, y)} no tiene escalera abajo")
    # alcanzable: desde la puerta (z7) y, en cada piso, desde donde se llega
    gate = find(7, ".")
    gate = [c for c in gate if c[1] == H - 1]
    starts = {7: gate[0]} if gate else {}
    if not gate:
        errors.append("z7: no hay puerta en la pared sur")
    for z in PLANS:
        for (x, y) in find(z, ">"):
            starts.setdefault(z, (x, y - 1))            # se sube y se llega al norte del hueco
        for (x, y) in find(z, "<"):
            if z > 7:
                starts.setdefault(z, (x, y + 1))        # la cripta: se baja y se llega al sur de la escalera
    arrivals = {z: set() for z in PLANS}
    for z in PLANS:
        arrivals[z] |= {(x, y - 1) for (x, y) in find(z, ">")} | {(x, y + 1) for (x, y) in find(z, "<")}
        arrivals[z] |= set(find(z, ">")) | set(find(z, "<"))
    for z in PLANS:
        if z not in starts:
            errors.append(f"z{z}: no sé por dónde se entra")
            continue
        seen = set(reach(walk[z], starts[z]))
        lost = walk[z] - seen
        if lost:
            errors.append(f"z{z}: {len(lost)} casillas de piso sin acceso, ej. {sorted(lost)[0]}")
        for (x, y) in find(z, "<") + find(z, ">"):
            if not any((x + dx, y + dy) in seen for dx, dy in CARD):
                errors.append(f"z{z}: la escalera {(x, y)} no se alcanza")
        for ch in CHESTS:
            for (x, y) in find(z, ch):
                if not any((x + dx, y + dy) in seen for dx, dy in CARD):
                    errors.append(f"z{z}: el cofre {ch} {(x, y)} no tiene acceso")
    # monstruos registrados y uids libres
    registry = (MONSTERS / "monsters.xml").read_text(encoding="latin-1")
    every = [n for lst in MONSTERS_BY_FLOOR.values() for n, _c, _s in lst] + [n for lst in FIXED.values() for n, _c, _s in lst] + [OUTSIDE[0]]
    for z, lst in [(0, [(n, 0, 0) for n in sorted(set(every))])]:
        for name, _n, _s in lst:
            if f'name="{name}"' not in registry:
                errors.append(f"monstruo sin registrar en monsters.xml: {name}")
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    md = root[2][0]
    in_box = lambda x, y, z: (z in PLANS and X0 <= x < X0 + W and Y0 <= y < Y0 + H)
    for area in md[2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        for t in area[2]:
            if t[0] not in (T_TILE, T_HOUSETILE) or in_box(ax + t[1][0], ay + t[1][1], az):
                continue
            for ch in t[2]:
                p = bytes(ch[1])
                for uid in CHESTS.values():
                    if ch[0] == T_ITEM and p[2:5] == bytes([ATTR_UNIQUE_ID]) + struct.pack("<H", uid):
                        errors.append(f"el uniqueId {uid} ya está en {(ax + t[1][0], ay + t[1][1], az)}")

    rng = random.Random(a.seed)
    plain = {z: {c for c in walk[z] if len(floors[z][c]) == 1} for z in PLANS}   # sin sillas ni bancos debajo
    monsters = {z: place_monsters(z, plain[z], {c for c in walk[z] if any(max(abs(c[0] - s[0]), abs(c[1] - s[1])) < 3
                                                                           for s in arrivals[z] | {starts.get(z, (0, 0))})}, rng)
                for z in PLANS}
    # afuera: casillas libres del campo del sur (del mapa actual), lejos de la puerta y de la bajada del puente
    ox1, oy1, ox2, oy2 = OUTSIDE_BOX
    field = sorted((x, y) for (x, y, zz), it in old.items() if zz == 7 and ox1 <= x <= ox2 and oy1 <= y <= oy2
                   and walkable(it) and not any(max(abs(x - ax), abs(y - ay)) < 4 for ax, ay in OUTSIDE_AVOID))
    rng.shuffle(field)
    outside = []
    for c in field:
        if len(outside) >= OUTSIDE[1]:
            break
        if all(max(abs(c[0] - o[1][0]), abs(c[1] - o[1][1])) >= 4 for o in outside):
            outside.append((OUTSIDE[0], c, OUTSIDE[2]))
    if len(outside) < OUTSIDE[1]:
        errors.append(f"afuera: solo entran {len(outside)} de {OUTSIDE[1]} {OUTSIDE[0]}")
    n_mon = sum(len(m) for m in monsters.values()) + len(outside)
    monsters["outside"] = outside
    if a.preview:
        write_preview(a.preview, floors, monsters, old)
        print(f"preview: {a.preview}")
    if errors:
        print("\n".join(errors[:40]), file=sys.stderr)
        print(f"ERROR: {len(errors)} problemas; no se escribe nada", file=sys.stderr)
        return 1
    print(f"castillo imperial x{X0}-{X0 + W - 1} y{Y0}-{Y0 + H - 1}: " +
          ", ".join(f"z{z} {len(walk[z])} caminables" for z in sorted(PLANS)) + f"; {n_mon} monstruos")
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    # --- mapa ---
    backup = MAP.with_name(MAP.name + ".bak-castle")
    if not backup.exists():
        shutil.copy2(MAP, backup)
    ox0, oy0, ox1, oy1 = OLD_BOX
    bridge = lambda x, y: x >= 113 and y >= 37                       # puente de z6 y su bajada: no se tocan

    def doomed(x, y, z):
        if in_box(x, y, z) and (z != 8 or y < Y0 + len(PLANS[8])):
            return True
        if z in (5, 6) and ox0 <= x <= ox1 and oy0 <= y <= oy1 and not bridge(x, y):
            return True                                              # restos del castillo viejo
        return z == 7 and X0 + W <= x <= ox1 and Y0 <= y <= 36      # franja este: vuelve a ser pasto

    yard = {}                                                        # franja este de z7, limpia
    for (x, y, z), it in old.items():
        if z == 7 and X0 + W <= x <= ox1 and Y0 <= y <= 36:
            yard[(x, y)] = [i for i in it if i in KEEP_GROUND] or [GRASS]
    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        area[2] = [t for t in area[2] if not (t[0] in (T_TILE, T_HOUSETILE) and doomed(ax + t[1][0], ay + t[1][1], az))]
        if not area[2]:
            md[2].remove(area)
    buckets = {}
    for z, t in floors.items():
        for (x, y), it in t.items():
            uid = CHESTS.get(cell(z, x, y))
            buckets.setdefault(((X0 + x) & ~0xFF, (Y0 + y) & ~0xFF, z), []).append((X0 + x, Y0 + y, it, uid))
    for (x, y), it in yard.items():
        buckets.setdefault((x & ~0xFF, y & ~0xFF, 7), []).append((x, y, it, None))
    for (bx, by, z), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, z)), []]
        for gx, gy, it, uid in sorted(lst, key=lambda t: (t[1], t[0])):
            area[2].append(new_tile(gx, gy, bx, by, it, uid=uid))
        md[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    # --- spawns: fuera los del castillo viejo; adentro el bloque nuevo ---
    sp = SPAWNS.read_text(encoding="latin-1")
    sp = re.sub(r"\t?<!-- BEGIN IMPERIAL_CASTLE_SPAWNS.*?<!-- END IMPERIAL_CASTLE_SPAWNS -->\n?", "", sp, flags=re.S)

    def old_spawn(m):
        x, y, z = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return ox0 <= x <= ox1 and oy0 <= y <= oy1 and 3 <= z <= 7 or in_box(x, y, z) and y < Y0 + len(PLANS.get(z, []))

    sp = re.sub(r'[ \t]*<spawn centerx="(\d+)" centery="(\d+)" centerz="(\d+)"[^>]*>.*?</spawn>\n?',
                lambda m: "" if old_spawn(m) else m.group(0), sp, flags=re.S)
    lines = ["\t<!-- BEGIN IMPERIAL_CASTLE_SPAWNS (scripts/map/generate-imperial-castle.py) -->"]
    for z in ORDER:
        for name, (x, y), st in monsters[z]:
            lines.append(f'\t<spawn centerx="{X0 + x}" centery="{Y0 + y}" centerz="{z}" radius="2">')
            lines.append(f'\t\t<monster name="{name}" x="0" y="0" z="{z}" spawntime="{st}" />')
            lines.append("\t</spawn>")
    for name, (x, y), st in outside:
        lines.append(f'\t<spawn centerx="{x}" centery="{y}" centerz="7" radius="3">')
        lines.append(f'\t\t<monster name="{name}" x="0" y="0" z="7" spawntime="{st}" />')
        lines.append("\t</spawn>")
    lines.append("\t<!-- END IMPERIAL_CASTLE_SPAWNS -->\n")
    SPAWNS.write_text(sp.replace("</spawns>", "\n".join(lines) + "</spawns>"), encoding="latin-1")

    # --- cartel de la entrada ---
    rd = READABLES.read_text(encoding="latin-1")
    rd = re.sub(r"\t?<!-- BEGIN IMPERIAL_CASTLE_SIGNS -->.*?<!-- END IMPERIAL_CASTLE_SIGNS -->\n?", "", rd, flags=re.S)
    lines = ["\t<!-- BEGIN IMPERIAL_CASTLE_SIGNS -->"]
    for (x, y) in find(7, "i"):
        lines.append(f'\t<readable x="{X0 + x}" y="{Y0 + y}" z="7" text="{SIGN_TEXT.replace(chr(10), chr(92) + "n")}"/>')
    lines.append("\t<!-- END IMPERIAL_CASTLE_SIGNS -->\n")
    READABLES.write_text(rd.replace("</readables>", "\n".join(lines) + "</readables>"), encoding="latin-1")

    stairs = {f"z{z}": [{"x": X0 + x, "y": Y0 + y} for (x, y) in find(z, "<")] for z in sorted(PLANS)}
    MANIFEST.write_text(json.dumps({
        "name": "generated-imperial-castle", "seed": a.seed,
        "box": {"x1": X0, "y1": Y0, "x2": X0 + W - 1, "y2": Y0 + H - 1, "z": sorted(PLANS)},
        "gate": {"x": X0 + gate[0][0], "y": Y0 + gate[0][1], "z": 7},
        "stairsUp": stairs,
        "chests": [{"x": X0 + x, "y": Y0 + y, "z": 3, "uid": uid} for ch, uid in CHESTS.items() for (x, y) in find(3, ch)],
        "monsters": {f"z{z}": [[n, c] for n, c, _s in MONSTERS_BY_FLOOR[z]] for z in ORDER},
        "boss": [{"name": n, "x": X0 + c[0], "y": Y0 + c[1], "z": z, "spawntime": s} for z, lst in FIXED.items() for n, c, s in lst],
        "outside": {"name": OUTSIDE[0], "spots": [[x, y] for _n, (x, y), _s in outside]}, "total": n_mon,
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK cartel {READABLES}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
