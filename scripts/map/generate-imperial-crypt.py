#!/usr/bin/env python3
"""Cripta Imperial: túnel de caza bajo el pantano, con la guarnición imperial.

Boca en la orilla sur del pantano (94,92,7): plataforma de piedra con la bajada (432) y un cartel.
El 94,86 lo tomó el Spot del Dragon Negro (trampilla 93-95,85-87 y túnel z8 en 93-103,84-87); esta
cripta va más al sur y no lo toca: caja z8 90-113 x 91-112 y, con margen, los pisos empiezan en y94
(7 filas de roca debajo de su túnel). Abajo, un pasillo angosto que zigzaguea con la receta de
ZONAS_DE_CAZA.md: Imperial Squire y Archer al frente, Court Mage más adentro e Imperial Hero de a 2
al fondo — sin variantes rage.

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
BX, BY, BW, BH = 90, 91, 24, 22                    # caja z8: x 90-113, y 91-112
STONE, SIGN = 415, 1429                            # plataforma de piedra y cartel
PILLAR, BROKEN_PILLAR, STATUE, ALTAR_BASIN, BONES = 1515, 3767, 1442, 2602, 2248
CUT_DRAGON_PIECES = {2247: 2248, 3125: 2320, 3122: 2248}   # red de seguridad: nunca piezas cortadas

PATH = [(19, 3), (2, 3), (2, 17), (4, 17)]     # local a la caja: fila y93 (boca al norte), bajada x92, sala y107
# zona cavable (global): la fila norte, la bajada del oeste y el sur sin tocar la lava del lago
# (x98+ desde y103) ni el túnel del dragon spot (y84-87: con el wobble del ribbon quedan 4 filas
# de roca de margen)
ALLOWED = (92, 92, 109, 108)
MOUTH_LOCAL = (MOUTH[0] - BX, MOUTH[1] - BY)       # (4, 1): la boca cuelga del borde norte de la zona
ROOMS = rooms_along(PATH)
MIN_FLOOR = 170

# (nombres, por spawn, spawntime s, separación mínima entre centros) — de fácil a duro, sin rage
STAGES = (
    (("Imperial Squire", "Imperial Archer"), 1, 100, 12),
    (("Imperial Archer", "Court Mage"), 1, 120, 12),
    (("Court Mage", "Imperial Hero"), 2, 170, 11),
    (("Imperial Hero",), 2, 235, 11),
)

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MANIFEST = WORLD / "generated-imperial-crypt.json"
SIGN_TEXT = "CRIPTA IMPERIAL\nSquires y arqueros custodian la entrada.\nHeroes imperiales al fondo."


def allowed_zone() -> set:
    """Zona cavable (ALLOWED, global) sin las casillas que hoy son lava: nadie pisa lava."""
    otb, tiles = load_otb(), load_tiles()
    x1, y1, x2, y2 = ALLOWED
    allowed = {(x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)}
    lava = {c for c in allowed
            if (it := tiles.get((c[0], c[1], Z8))) and "lava" in otb.get(it[0], {}).get("name", "")}
    return allowed - lava


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
    tiles = load_tiles()
    for (x, y), it in z8.items():
        tiles[(x, y, Z8)] = it
    for (x, y), it in platform.items():
        tiles[(x, y, Z7)] = it
    r = Renderer()
    W, H, img = r.area(tiles, 84, 76, 118, 112, Z8, highlight=MOUTH)
    path.write_bytes(png_bytes(W, H, img, scale=2))
    W2, H2, img2 = r.area(tiles, 88, 80, 102, 94, Z7, highlight=MOUTH)
    with path.open("ab") as f:                     # dos imágenes, una al lado de la otra
        f.write(png_bytes(W2, H2, img2, scale=4))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()

    bl = Blocking()
    box = {(x, y) for x in range(BX, BX + BW) for y in range(BY, BY + BH)}
    allowed = allowed_zone()
    core = {(MOUTH[0] + dx, MOUTH[1] + dy) for dx in (-1, 0, 1) for dy in (0, 1, 2)}   # sin fila norte: no pisar el margen del dragon spot
    band, ribbon_core = ribbon([MOUTH] + [(BX + x, BY + y) for x, y in PATH],
                               [((BX + x, BY + y), r) for (x, y), r in ROOMS], a.seed)
    floor = carve_cave(a.seed, allowed & band, core | ribbon_core, (MOUTH[0], MOUTH[1] + 1), MIN_FLOOR)

    t8 = cave_tiles(floor, box, a.seed)
    paint = Noise(a.seed + 515)
    for c in floor:                                 # paleta de la cripta: piedra, sin barro
        v = paint.fbm(c[0] / 5, c[1] / 5, 3, 10)
        t8[c] = [CAVE_FLOOR_ALT if v < 0.38 else CAVE_FLOOR]
    t8[MOUTH].append(STAIRS_UP)

    decorate_cave(t8, floor, (MOUTH[0], MOUTH[1] + 1), grow({MOUTH}, 2), a.seed + 1, 0.04, bl)
    place_props(t8, floor, (MOUTH[0], MOUTH[1] + 1),
                (PILLAR, BROKEN_PILLAR, STATUE, ALTAR_BASIN, BONES), 0.08, a.seed + 2, grow({MOUTH}, 2))
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

    # escaleras: bajada arriba, escalera de mano abajo, salidas pisables
    if t8[MOUTH][0] not in CAVE_FLOORS or STAIRS_UP not in t8[MOUTH]:
        errors.append(f"la boca {MOUTH} no tiene escalera de mano sobre piso de cueva")
    if platform[MOUTH] != [STONE, STAIR_DOWN]:
        errors.append(f"la plataforma {MOUTH} no tiene la bajada")
    if not bl.walkable(platform.get((MOUTH[0], MOUTH[1] - 1), [ROCK])):
        errors.append("al subir no se puede pisar el norte de la boca")
    if (MOUTH[0], MOUTH[1] + 1) not in d8:
        errors.append("al bajar no se puede salir al sur de la escalera")

    # paredes: cada casilla que no es piso tiene su pieza exacta (o roca)
    fl = {c for c, it in t8.items() if it[0] in CAVE_FLOORS}
    for c, it in t8.items():
        if c in fl:
            continue
        want = pieces_for(neighbors_in(fl, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
        if want is None or len(want) > 1 or (want and it[0] != want[0]) or (not want and it[0] != ROCK):
            errors.append(f"pared {c}: quiere {want} tiene {it[0]}")

    # nada de vacío a la vista: media pantalla alrededor de cada pisable tiene que tener tile;
    # los huecos que queden se llenan de roca (solo casillas vacías, como en la Dark Cathedral)
    # OJO: todo en 2D (x, y) de z8 — comparar contra tiles existentes de z8, no contra (x,y,z)
    existing8 = {(x, y) for (x, y, z) in load_tiles() if z == Z8}
    final8 = (existing8 - box) | set(t8)
    holes = sorted((c for c in grow(walk8, 9) - final8), key=lambda c: (c[1], c[0]))
    for c in holes:
        t8[c] = [ROCK]
    final8 = (existing8 - box) | set(t8)
    if holes:
        print(f"relleno de roca: {len(holes)} huecos (creaba vacío a la vista)")
    if grow(walk8, 7) - final8:
        errors.append("quedan huecos a la vista del piso de la cripta")

    # spawns: etapas por distancia caminando desde la boca
    avoid = grow({MOUTH}, STAIR_CLEAR)
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
        return z == Z8 and BX <= gx < BX + BW and BY <= gy < BY + BH or \
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
        "name": "generated-imperial-crypt", "seed": a.seed, "version": 1,
        "box": {"x1": BX, "y1": BY, "x2": BX + BW - 1, "y2": BY + BH - 1, "z": [Z8]},
        "mouth": {"x": MOUTH[0], "y": MOUTH[1], "z": 7, "platform": [STONE], "sign": [SIGN]},
        "walkable": len(walk8), "spawns": len(spawns), "monsters": n_mon,
        "monstersByKind": dict(sorted(counts.items())),
        "densityTilesPerMonster": round(density),
        "rockFilled": len(holes),
        "stages": [{"names": list(n), "per": per, "spawntime": st, "gap": gap}
                   for n, per, st, gap in STAGES],
    }, indent=2) + "\n")
    print(f"OK mapa {MAP}\nOK spawns {SPAWNS}\nOK carteles {READABLES}\nOK {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
