#!/usr/bin/env python3
"""Cripta Imperial: pasillo de caza bajo el pantano, con la guarnición imperial.

v2 (19 nov 2026): pasillo en U, más largo (fila norte y94 de x106 a x64, bajada por x64 y fila sur y106
de vuelta a x106), unido al túnel del Spot del Dragón Negro por un ramal de 1 de ancho en x99 (el ramal
y88 para arriba es del dragon spot; de y89 para abajo, de esta cripta). Dos entradas: la bajada propia de
la orilla sur del pantano (94,92,7: plataforma de piedra, bajada 432 y cartel) y el túnel del dragón.
Caja z8 56-113 x 89-112. Receta de ZONAS_DE_CAZA.md: Imperial Squire y Archer al frente, Court Mage más
adentro e Imperial Hero de a 2 al fondo — sin variantes rage.

Paredes: todo piso tiene pared de cueva al lado (nunca la roca lisa 101 pegada): el núcleo del pasillo se
recorta a la zona cavable menos 2 (en la v1 el núcleo se salía de la zona y el piso llegaba al borde de la
caja, pegado a la roca de afuera, sin pieza) y el generador revisa las paredes también fuera de la caja.

  python3 scripts/map/generate-imperial-crypt.py --dry-run --preview /tmp/cripta.png
  python3 scripts/map/generate-imperial-crypt.py

Después: check-map-load.py, check-upper-view.py, scan-map-depots.py y sync-houses-with-map.py
--dry-run. Doc: docs/items-and-map/MAPEAR_CATACUMBA_IMPERIAL.md.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, Renderer  # noqa: E402
from mapdata import parse_tree, serialize_tree, png_bytes, load_otb, load_tiles  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


NP = _load("generate-north-pass")          # carve_cave, cave_tiles, decorate_cave, piezas, Blocking
BV = _load("generate-beast-valley")        # ribbon, rooms_along, place_stages, slices_by, place_props

carve_cave, cave_tiles, decorate_cave = NP.carve_cave, NP.cave_tiles, NP.decorate_cave
Noise, reach, Blocking = NP.Noise, NP.reach, NP.Blocking
neighbors_in, pieces_for, grow, stamp = NP.neighbors_in, NP.pieces_for, BV.grow, BV.stamp
ribbon, rooms_along = BV.ribbon, BV.rooms_along
place_stages, slices_by, place_props = BV.place_stages, BV.slices_by, BV.place_props
CAVE_FLOORS, ROCK = NP.CAVE_FLOORS, NP.ROCK
WALL_SIDE, WALL_CORNER, WALL_INNER = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER
CAVE_FLOOR, CAVE_FLOOR_ALT, CAVE_MUD = NP.CAVE_FLOOR, NP.CAVE_FLOOR_ALT, NP.CAVE_MUD
STAIR_DOWN, STAIRS_UP = NP.STAIR_DOWN, NP.STAIRS_UP
STAIR_CLEAR = BV.STAIR_CLEAR                       # sin spawns a 6 de la escalera
NEEDS_COUNT = NP.NEEDS_COUNT

Z7, Z8 = 7, 8
MOUTH = (94, 92)                                   # la boca, orilla sur del pantano (94,86 es del dragon spot)
BX, BY, BW, BH = 56, 89, 58, 24                    # caja z8: x 56-113, y 89-112
LINK_X = 99                                        # ramal al túnel del dragon spot (x99, y86-88 es suyo)
VIEW = (9, 7)                                      # media pantalla: lava a la vista -> roca
STONE, SIGN = 415, 1429                            # plataforma de piedra y cartel
PILLAR, BROKEN_PILLAR, STATUE, ALTAR_BASIN, BONES = 1515, 3767, 1442, 2602, 2248
LAVA = {598, 599, 600, 601}
STRAY_WALLS = {374, 381}                           # pared de tierra vieja suelta en la roca (x90, y82-88)
CUT_DRAGON_PIECES = {2247: 2248, 3125: 2320, 3122: 2248}   # red de seguridad: nunca piezas cortadas

# recorrido en U (global): fila norte y94 (la boca 94,92 y el ramal x99 cuelgan de ella), bajada por x64 y
# fila sur y106 (12 de eje: las franjas de ±5 no se tocan; el piso queda en y92-108 y deja 4 filas de roca
# sobre las salas del sur, pared en y113)
PATH = [(106, 94), (64, 94), (64, 106), (106, 106)]
# zona cavable (global); carve_cave deja un bloque de margen adentro, así la pared también cabe
ALLOWED = (59, 90, 110, 110)
ROOMS = rooms_along(PATH)
MIN_FLOOR = 380

# (nombres, por spawn, spawntime s, separación mínima entre centros) — de fácil a duro, sin rage
STAGES = (
    (("Imperial Squire", "Imperial Archer"), 1, 100, 12),
    (("Imperial Archer", "Court Mage"), 1, 120, 12),
    (("Court Mage", "Imperial Squire"), 1, 140, 11),
    (("Court Mage", "Imperial Hero"), 2, 170, 11),
    (("Imperial Hero",), 2, 235, 11),
)

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MANIFEST = WORLD / "generated-imperial-crypt.json"
SIGN_TEXT = ('IMPERIAL CRYPT\nSquires and archers guard the entrance.\nImperial Heroes await at the far end.\nA tunnel connects to the Black Dragon Hunt.')


def allowed_zone() -> set:
    """Zona cavable (ALLOWED, global). v2: ya no se le resta la lava (el borde del lago de lava de z8 queda
    dentro de la caja y se vuelve roca; si se restara, la segunda pasada cavaba distinto: no idempotente)."""
    x1, y1, x2, y2 = ALLOWED
    return {(x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)}


def item_node(iid: int, tele=None):
    props = bytearray(struct.pack("<H", iid))
    if iid in NEEDS_COUNT:
        props.append(1)
    if tele is not None:
        props += bytes([NP.ATTR_TELE_DEST]) + struct.pack("<HHB", *tele)
    return [T_ITEM, props, []]


def new_tile(x, y, bx, by, items):
    props = bytearray([x - bx, y - by, 9]) + struct.pack("<H", items[0])
    return [T_TILE, props, [item_node(i) for i in items[1:]]]


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def render_preview(path: Path, z8: dict, platform: dict):
    """Dos PNG: <path> (z8, la cripta y el túnel del dragon spot) y <path>-z7.png (la boca)."""
    tiles = load_tiles()
    for (x, y), it in z8.items():
        tiles[(x, y, Z8)] = it
    for (x, y), it in platform.items():
        tiles[(x, y, Z7)] = it
    r = Renderer()
    W, H, img = r.area(tiles, BX - 2, 80, BX + BW + 1, BY + BH + 2, Z8, highlight=MOUTH)
    path.write_bytes(png_bytes(W, H, img))
    W2, H2, img2 = r.area(tiles, 84, 80, 106, 96, Z7, highlight=MOUTH)
    path.with_name(path.stem + "-z7.png").write_bytes(png_bytes(W2, H2, img2))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()

    bl = Blocking()
    box = {(x, y) for x in range(BX, BX + BW) for y in range(BY, BY + BH)}
    allowed = allowed_zone()
    tiles_now = load_tiles()
    # piso que ya existe pegado a la caja (el ramal del dragon spot): cuenta para elegir las piezas de pared
    ext_floor = {(x, y) for (x, y, z), it in tiles_now.items()
                 if z == Z8 and (x, y) not in box and it[0] in CAVE_FLOORS and (x, y) in grow(box, 1)}
    # núcleo recortado a la zona cavable menos 2: nada de piso pegado al borde (bug de la v1)
    inner = {c for c in allowed if all((c[0] + dx, c[1] + dy) in allowed for dx in range(-2, 3) for dy in range(-2, 3))}
    core = {(MOUTH[0] + dx, MOUTH[1] + dy) for dx in (-1, 0, 1) for dy in (0, 1, 2)}
    band, ribbon_core = ribbon(PATH, ROOMS, a.seed)
    floor = carve_cave(a.seed, allowed & band, core | (ribbon_core & inner), (MOUTH[0], MOUTH[1] + 1), MIN_FLOOR)
    # ramal de 1 de ancho al túnel del dragon spot: de la caja (y89) hasta el primer piso del pasillo
    link = set()
    y = BY
    while (LINK_X, y) not in floor:
        link.add((LINK_X, y))
        y += 1
        if y > BY + 8:
            raise SystemExit(f"el ramal x{LINK_X} no encuentra el pasillo")
    floor |= link

    t8 = cave_tiles(floor | ext_floor, box, a.seed)
    paint = Noise(a.seed + 515)
    for c in floor:                                 # paleta de la cripta: piedra, sin barro
        v = paint.fbm(c[0] / 5, c[1] / 5, 3, 10)
        t8[c] = [CAVE_FLOOR_ALT if v < 0.38 else CAVE_FLOOR]
    t8[MOUTH].append(STAIRS_UP)

    keep = grow({MOUTH}, 2) | grow(link, 1)
    decorate_cave(t8, floor, (MOUTH[0], MOUTH[1] + 1), keep, a.seed + 1, 0.04, bl)
    place_props(t8, floor, (MOUTH[0], MOUTH[1] + 1),
                (PILLAR, BROKEN_PILLAR, STATUE, ALTAR_BASIN, BONES), 0.08, a.seed + 2, keep)
    for c, it in t8.items():                        # red de seguridad: nada de piezas cortadas
        t8[c] = it[:1] + [CUT_DRAGON_PIECES.get(i, i) for i in it[1:]]

    platform = {}
    for x in range(MOUTH[0] - 1, MOUTH[0] + 2):
        for y in range(MOUTH[1] - 1, MOUTH[1] + 2):
            platform[(x, y)] = [STONE]
    platform[MOUTH].append(STAIR_DOWN)
    platform[(MOUTH[0] + 1, MOUTH[1] - 1)].append(SIGN)

    errors = []
    d8 = reach({c for c in floor if bl.walkable(t8[c])}, (MOUTH[0], MOUTH[1] + 1), NP.CARD)
    walk8 = {c for c, it in t8.items() if it[0] in CAVE_FLOORS and bl.walkable(it)} & d8.keys()
    if len(d8) < MIN_FLOOR * 0.75:
        errors.append(f"piso corto: {len(d8)} caminables de {MIN_FLOOR} mínimos")
    if not link or min(link) not in d8 or (LINK_X, BY) not in d8:
        errors.append(f"el ramal al dragon spot (x{LINK_X}) no se camina desde la boca")
    if not (floor <= box):
        errors.append(f"piso fuera de la caja: {sorted(floor - box)[:5]}")

    # escaleras: bajada arriba, escalera de mano abajo, salidas pisables
    if t8[MOUTH][0] not in CAVE_FLOORS or STAIRS_UP not in t8[MOUTH]:
        errors.append(f"la boca {MOUTH} no tiene escalera de mano sobre piso de cueva")
    if platform[MOUTH] != [STONE, STAIR_DOWN]:
        errors.append(f"la plataforma {MOUTH} no tiene la bajada")
    if not bl.walkable(platform.get((MOUTH[0], MOUTH[1] - 1), [ROCK])):
        errors.append("al subir no se puede pisar el norte de la boca")
    if (MOUTH[0], MOUTH[1] + 1) not in d8:
        errors.append("al bajar no se puede salir al sur de la escalera")

    # paredes: cada casilla que no es piso tiene su pieza exacta (o roca), también las de afuera de la
    # caja que tocan este piso (si no, el piso queda pegado a la roca lisa: "falta de pared")
    fl = {c for c, it in t8.items() if it[0] in CAVE_FLOORS} | ext_floor
    for c, it in t8.items():
        if c in fl:
            continue
        want = pieces_for(neighbors_in(fl, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
        if want is None or len(want) > 1 or (want and it[0] != want[0]) or (not want and it[0] != ROCK):
            errors.append(f"pared {c}: quiere {want} tiene {it[0]}")
    for c in grow(floor - link, 1) - box:
        errors.append(f"el pasillo toca afuera de la caja en {c}")
    for c in grow(link, 1) - box - ext_floor:
        it = tiles_now.get((c[0], c[1], Z8)) or [0]
        want = pieces_for(neighbors_in(fl, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
        if c[1] == BY - 1 and want and it[0] != want[0]:
            print(f"aviso: {c} es del dragon spot y quiere la pared {want} (tiene {it[0]}): "
                  "correr generate-dragon-spot.py --replace después de esta cripta")

    # lava a la vista del piso (el lago de lava de z8 bajo el pantano) -> roca, como en el dragon spot
    view = {(x + dx, y + dy) for (x, y) in walk8 for dx in range(-VIEW[0], VIEW[0] + 1)
            for dy in range(-VIEW[1], VIEW[1] + 1)}
    lava_rock = {c for c in view - box
                 if (it := tiles_now.get((c[0], c[1], Z8))) and it[0] in LAVA}
    # restos de pared de tierra en medio de la roca (sin ningún piso al lado): se veían como una grieta
    all_floor = {(x, y) for (x, y, z), it in tiles_now.items() if z == Z8 and it[0] in CAVE_FLOORS} | floor
    stray = {c for c in view - box
             if (it := tiles_now.get((c[0], c[1], Z8))) and it[0] in STRAY_WALLS and len(it) == 1
             and not any((c[0] + dx, c[1] + dy) in all_floor for dx in (-1, 0, 1) for dy in (-1, 0, 1))}
    lava_rock |= stray
    for c in lava_rock:
        t8[c] = [ROCK]

    # nada de vacío a la vista: media pantalla alrededor de cada pisable tiene que tener tile;
    # los huecos que queden se llenan de roca (solo casillas vacías, como en la Dark Cathedral)
    # OJO: todo en 2D (x, y) de z8 — comparar contra tiles existentes de z8, no contra (x,y,z)
    existing8 = {(x, y) for (x, y, z) in tiles_now if z == Z8}
    final8 = (existing8 - box) | set(t8)
    holes = sorted((c for c in grow(walk8, 9) - final8), key=lambda c: (c[1], c[0]))
    for c in holes:
        t8[c] = [ROCK]
    final8 = (existing8 - box) | set(t8)
    if holes:
        print(f"relleno de roca: {len(holes)} huecos (creaba vacío a la vista)")
    if lava_rock:
        print(f"lava a la vista -> roca: {len(lava_rock) - len(stray)}; pared de tierra suelta -> roca: {len(stray)}")
    if grow(walk8, 7) - final8:
        errors.append("quedan huecos a la vista del piso de la cripta")

    # spawns: etapas por distancia caminando desde la boca
    avoid = grow({MOUTH}, STAIR_CLEAR) | grow(link, STAIR_CLEAR)
    rng = random.Random(f"{a.seed}-imperial-crypt")
    spawns = place_stages(STAGES, slices_by(walk8 - avoid, lambda c: d8[c], len(STAGES)),
                          walk8, avoid, Z8, rng)
    n_mon = sum(len(m) for _c, _z, m in spawns)
    density = len(walk8) / max(n_mon, 1)
    if n_mon == 0:
        errors.append("no entró ningún monstruo")
    elif density < 22:
        errors.append(f"demasiados juntos: 1 cada {density:.0f} casillas")
    counts: dict = {}
    for _c, _z, mons in spawns:
        for name, _p, _t in mons:
            counts[name] = counts.get(name, 0) + 1

    if errors:
        print("\n".join(f"ERROR: {e}" for e in errors[:40]), file=sys.stderr)
        if a.preview:
            render_preview(a.preview, t8, platform)
        return 1

    print(f"cripta {BX}-{BX + BW - 1} x, {BY}-{BY + BH - 1} y, z8: {len(walk8)} casillas caminables; "
          f"boca {MOUTH[0]},{MOUTH[1]},7 (plataforma de piedra + bajada)")
    print(f"  {len(spawns)} spawns, {n_mon} monstruos, 1 cada {density:.0f} casillas: "
          + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if a.preview:
        render_preview(a.preview, t8, platform)
        print(f"preview: {a.preview}")
    if a.dry_run:
        print("dry-run: validación OK, no se escribió nada")
        return 0

    # --- mapa: fuera la caja de z8 y la plataforma de z7; adentro la cripta ---
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    md = root[2][0]

    def gone(gx, gy, z):
        return z == Z8 and (BX <= gx < BX + BW and BY <= gy < BY + BH or (gx, gy) in lava_rock) or \
               z == Z7 and MOUTH[0] - 1 <= gx <= MOUTH[0] + 1 and MOUTH[1] - 1 <= gy <= MOUTH[1] + 1

    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        area[2] = [t for t in area[2] if not (t[0] in (T_TILE, T_HOUSETILE) and gone(ax + t[1][0], ay + t[1][1], az))]
        if not area[2]:
            md[2].remove(area)
    buckets: dict = {}
    for (x, y), it in t8.items():
        buckets.setdefault((x & ~0xFF, y & ~0xFF, Z8), []).append((x, y, it))
    for (x, y), it in platform.items():
        buckets.setdefault((x & ~0xFF, y & ~0xFF, Z7), []).append((x, y, it))
    for (bx, by, zz), lst in sorted(buckets.items()):
        area = [T_AREA, bytearray(struct.pack("<HHB", bx, by, zz)), []]
        for gx, gy, it in sorted(lst, key=lambda t: (t[1], t[0])):
            area[2].append(new_tile(gx, gy, bx, by, it))
        md[2].append(area)
    MAP.write_bytes(serialize_tree(root, raw[:4]))

    # --- spawns ---
    sp = SPAWNS.read_text(encoding="latin-1")
    block = "\t<!-- BEGIN IMPERIAL_CRYPT_SPAWNS (scripts/map/generate-imperial-crypt.py) -->\n" + \
        spawn_xml(spawns) + "\n\t<!-- END IMPERIAL_CRYPT_SPAWNS -->\n"
    old = re.search(r"[ \t]*<!-- BEGIN IMPERIAL_CRYPT_SPAWNS.*?<!-- END IMPERIAL_CRYPT_SPAWNS -->\n?", sp, flags=re.S)
    if old:
        sp = sp[:old.start()] + "\x00BLOCK\x00" + sp[old.end():]
    sp = re.sub(r'[ \t]*<spawn centerx="(\d+)" centery="(\d+)" centerz="(\d+)"[^>]*>.*?</spawn>\n?',
                lambda m: "" if gone(int(m.group(1)), int(m.group(2)), int(m.group(3))) else m.group(0),
                sp, flags=re.S)
    sp = sp.replace("\x00BLOCK\x00", block) if old else sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")

    # --- cartel ---
    rd = READABLES.read_text(encoding="latin-1")
    lines = ["\t<!-- BEGIN IMPERIAL_CRYPT_SIGNS -->",
             f'\t<readable x="{MOUTH[0] + 1}" y="{MOUTH[1] - 1}" z="7" '
             f'text="{SIGN_TEXT.replace(chr(10), chr(92) + "n")}"/>',
             "\t<!-- END IMPERIAL_CRYPT_SIGNS -->\n"]
    old = re.search(r"\t?<!-- BEGIN IMPERIAL_CRYPT_SIGNS -->.*?<!-- END IMPERIAL_CRYPT_SIGNS -->\n?",
                    rd, flags=re.S)
    if old:
        rd = rd[:old.start()] + "\n".join(lines) + rd[old.end():]
    else:
        rd = rd.replace("</readables>", "\n".join(lines) + "</readables>")
    READABLES.write_text(rd, encoding="latin-1")

    MANIFEST.write_text(json.dumps({
        "name": "generated-imperial-crypt", "seed": a.seed, "version": 2,
        "box": {"x1": BX, "y1": BY, "x2": BX + BW - 1, "y2": BY + BH - 1, "z": [Z8]},
        "mouth": {"x": MOUTH[0], "y": MOUTH[1], "z": 7, "platform": [STONE], "sign": [SIGN]},
        "walkable": len(walk8), "spawns": len(spawns), "monsters": n_mon,
        "monstersByKind": dict(sorted(counts.items())),
        "densityTilesPerMonster": round(density),
        "rockFilled": len(holes), "lavaToRock": len(lava_rock - stray), "strayWallsToRock": len(stray),
        "link": {"x": LINK_X, "y": [min(c[1] for c in link), max(c[1] for c in link)], "z": Z8,
                 "to": "túnel del Spot del Dragón Negro (generate-dragon-spot.py, BRANCH)"},
        "stages": [{"names": list(n), "per": per, "spawntime": st, "gap": gap}
                   for n, per, st, gap in STAGES],
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK carteles {READABLES}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
