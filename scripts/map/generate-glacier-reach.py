#!/usr/bin/env python3
"""Glaciar del Este: la isla de hielo vieja (x205-262, y25-49: frost trolls, winter wolves, polar bears) se
alarga hacia el este con una zona de hunt larga de monstruos de hielo, y al final Frost Dragons e Ice Spiders.

  z7  sendero de nieve de 3 de ancho en serpentina desde la punta este de la isla (263,39):
        este por y39 hasta x276, norte hasta y25, este hasta x338, sur hasta y39, oeste hasta x292,
        sur hasta y53 y este hasta la guarida (x338, y53)
      claros en las curvas y a mitad de los tramos largos; guarida grande al final
      todo lo que no es sendero es bosque nevado y roca (pinos, piedras, estalagmitas: bloquea)
      orilla como la de la isla vieja: agua 4619 con el borde de nieve 4737-4748 encima; el resto agua 4608

Monstruos por distancia caminando desde la entrada (receta de docs/items-and-map/ZONAS_DE_CAZA.md): Chakoya,
Frost Giant / Giantess / Mammoth, Ice Golem / Ice Monk, Frost Dragon Hatchling / Crystal Spider y al fondo
Frost Dragon + Ice Spider de a 2. Nada a menos de 9 de la entrada (los de la isla vieja no se suman).

  python3.11 scripts/map/generate-glacier-reach.py --dry-run --preview /tmp/glaciar.png
  python3.11 scripts/map/generate-glacier-reach.py --replace
Doc: docs/items-and-map/MAPEAR_GLACIAR_DEL_ESTE.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "kb"))
import roomkit  # noqa: E402
from mapdata import REPO, load_tiles  # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


NP = _load("generate-north-pass")
BV = _load("generate-beast-valley")

WORLD = REPO / "server/YurOTS/ots/data/world"
MAP = WORLD / "test.otbm"
SPAWNS = WORLD / "test-spawn.xml"
MONSTERS = REPO / "server/YurOTS/ots/data/monster/monsters.xml"
MANIFEST = WORLD / "generated-glacier-reach.json"

BOX = (263, 6, 354, 72)                     # z7, se reescribe entera (la Isla del Hielo Eterno empieza en x356)
ENTRY = (263, 39)                           # junto a la punta este de la isla vieja (262,37-41 es nieve suya)
NECK = 3                                    # las primeras 3 columnas son un istmo de 3 de alto (filas de la junta)
JUNCTION_ROWS = range(38, 41)               # en x263 solo estas filas son tierra: empalman con la nieve vieja
                                            # (37 y 41 quedan agua: el agua vieja de 262,36 y 262,42 no cambia)
SEA = 9                                     # agua alrededor de la tierra nueva: no se ve el borde del mapa
PATH = [(263, 39), (276, 39), (276, 25), (338, 25), (338, 39), (292, 39), (292, 53), (334, 53)]
WIDTH = 3
CLEARINGS = [((276, 39), 3.2, 2.6), ((276, 25), 3.2, 2.6), ((307, 25), 4.0, 2.8), ((338, 25), 3.2, 2.6),
             ((338, 39), 3.2, 2.6), ((315, 39), 4.0, 2.8), ((292, 39), 3.2, 2.6), ((292, 53), 3.2, 2.6),
             ((313, 53), 4.0, 2.8)]
LAIR = ((335, 53), 6.5, 4.2)                # guarida del final
# La punta este de la isla vieja (x258-262, y33-44) quedaba encerrada entre el macizo de montaña (x252-257) y una
# roca 2x2 (1296-1299): solo se entraba por un paso en diagonal (259,45 -> 260,44). Se saca la roca: paso de 2.
OPEN_ROCK = {(258, 43): 1296, (259, 43): 1297, (258, 44): 1298, (259, 44): 1299}

WATER, WATER_EDGE, SNOW = 4608, 4619, 670
WATERS = set(range(4608, 4626)) | {4664, 4665, 4666}
PINE, DEAD_TREES = 2698, (2697, 2709, 2717, 2720)
STONE, RUBBLE, PEBBLES, STALAGMITE = 1285, 1309, 1336, 4995
BONES = (2248, 2320, 3121)
SIGN = 1429
STAGES = (
    (("Chakoya Tribewarden", "Chakoya Windcaller", "Chakoya Toolshaper"), 1, 100, 11),
    (("Frost Giant", "Frost Giantess", "Mammoth"), 1, 120, 11),
    (("Ice Golem", "Ice Monk"), 1, 150, 11),
    (("Frost Dragon Hatchling", "Crystal Spider"), 2, 180, 11),
    (("Frost Dragon", "Ice Spider"), 2, 240, 10),
)
ENTRY_CLEAR = 9
SIGN_TEXT = ('EASTERN GLACIER\nThe trail heads east, growing ever colder.\nIce Dragons and Ice Spiders await at the end.\nLevel 60+.')


def rect(b):
    return {(x, y) for x in range(b[0], b[2] + 1) for y in range(b[1], b[3] + 1)}


def ellipse(spec):
    (cx, cy), rx, ry = spec
    return {(x, y) for x in range(int(cx - rx) - 1, int(cx + rx) + 2) for y in range(int(cy - ry) - 1, int(cy + ry) + 2)
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0}


def brush(points, width):
    out, h = set(), width // 2
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                out |= {(x + dx, y + dy) for dx in range(-h, width - h) for dy in range(-h, width - h)}
    return out


def build(existing, seed):
    rng = random.Random(seed)
    nz = NP.Noise(seed)
    box = rect(BOX)
    walk = brush(PATH, WIDTH) | set().union(*(ellipse(c) for c in CLEARINGS)) | ellipse(LAIR)
    walk = {c for c in walk if c in box and (c[0] >= BOX[0] + NECK or c[1] in JUNCTION_ROWS)}
    # tierra: el sendero + bosque alrededor (3-5 casillas, con ruido), nunca a menos de SEA del borde de la caja
    inner = {(x, y) for (x, y) in box if BOX[0] + 1 <= x <= BOX[2] - SEA and BOX[1] + SEA <= y <= BOX[3] - SEA}
    land = set()
    near = {}
    for (wx, wy) in walk:
        for dx in range(-6, 7):
            for dy in range(-6, 7):
                c = (wx + dx, wy + dy)
                r = max(abs(dx), abs(dy))
                if r < near.get(c, 99):
                    near[c] = r
    for c, r in near.items():
        if c not in inner:
            continue
        if r <= 3 or (r <= 5 and nz.fbm(c[0] / 4, c[1] / 4, 3, 17) > 0.30 + 0.12 * (r - 3)):
            land.add(c)
    land |= walk
    # empalme: en x262 solo las filas de la junta; nada de tierra nueva en x263 fuera de la franja cerca de la isla
    land = {c for c in land if c[0] >= BOX[0] + NECK or c[1] in JUNCTION_ROWS}
    old_land = {(x, y) for (x, y, z), it in existing.items()
                if z == 7 and (x, y) not in box and it[0] not in WATERS and BOX[0] - 2 <= x <= BOX[0] - 1}
    allowed = inner - {(x, y) for x in range(BOX[0], BOX[0] + NECK) for y in range(BOX[1], BOX[3] + 1)
                       if y not in JUNCTION_ROWS}
    grown = NP.fix_until_valid(land | old_land, allowed | old_land, NP.SNOW_SIDE, NP.SNOW_CORNER, NP.SNOW_INNER,
                               single=True)
    land = (grown - old_land) & box
    land_all = land | old_land
    water = box - land

    tiles = {}
    bad = []
    for c in box:
        x, y = c
        if c in water:
            pcs = NP.pieces_for(NP.neighbors_in(land_all, x, y), NP.SNOW_SIDE, NP.SNOW_CORNER, NP.SNOW_INNER)
            if pcs is None or len(pcs) > 1:
                bad.append(c)
                pcs = (pcs or [])[:1]
            tiles[c] = [WATER_EDGE] + pcs if pcs else [WATER]
        else:
            tiles[c] = [SNOW]

    walk = walk & land
    big = set()
    filler = sorted(land - walk, key=lambda c: (c[1], c[0]))

    def covers_walk(c):
        x, y = c
        return any(q in walk for q in ((x - 1, y), (x, y - 1), (x - 1, y - 1)))

    for c in filler:                                   # bosque nevado y roca: siempre bloquea
        x, y = c
        r = rng.random()
        # (24 nov 2026) menos piedra chica y más pinos/rocas grandes: con una piedra por casilla se veía una grilla
        tiles[c].append(STONE if r < 0.22 else STALAGMITE if r < 0.7 else rng.choice(DEAD_TREES))
        if covers_walk(c) or any((x + dx, y + dy) in big for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            continue
        if rng.random() < 0.85 * (0.35 + nz.fbm(x / 7, y / 7, 2, 91)):
            tiles[c] = [SNOW, PINE if rng.random() < 0.85 else RUBBLE]
            big.add(c)
    for c in sorted(walk):                             # piedritas y huesos sueltos (no bloquean)
        if rng.random() < 0.025:
            tiles[c].append(rng.choice((PEBBLES,) + BONES[:2]))
    # cartel: filler pegado al sendero, cerca de la entrada
    cands = [c for c in filler if any((c[0] + dx, c[1] + dy) in walk for dx, dy in NP.CARD) and c[0] <= ENTRY[0] + 6]
    sign = min(cands, key=lambda c: (abs(c[0] - (ENTRY[0] + 3)) + abs(c[1] - (ENTRY[1] - 2)), c))
    tiles[sign] = [SNOW, SIGN]
    return tiles, land, water, walk, sign, bad, old_land


def spawn_xml(spawns):
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()

    existing = load_tiles()
    bl = NP.Blocking()
    regenerating = MANIFEST.exists()
    tiles, land, water, walk, sign, bad, old_land = build(existing, a.seed)
    errs = []
    if bad:
        errs.append(f"orilla sin pieza única: {sorted(bad)[:6]}")
    if not regenerating:
        for c in rect(BOX):
            it = existing.get((c[0], c[1], 7))
            if it and it[0] not in WATERS:
                errs.append(f"la caja pisa tierra {c} {it}")
                break
    # caminable real (pasa por los ítems) y conectado desde la isla vieja
    walk_real = {c for c in land if bl.walkable(tiles[c])}
    old_entry = (ENTRY[0] - 1, ENTRY[1])
    for c, rock in OPEN_ROCK.items():
        it = existing.get((c[0], c[1], 7))
        if it not in ([SNOW, rock], [SNOW]):
            errs.append(f"la roca a sacar {c} no es nieve + {rock}: {it}")
    # la punta vieja se camina en cruz (sin el paso en diagonal) desde la isla, con la roca afuera
    old_walk = {(x, y) for (x, y, z), it in existing.items() if z == 7 and 240 <= x <= 262 and 28 <= y <= 50
                and (x, y) not in OPEN_ROCK and bl.walkable(it)} | set(OPEN_ROCK)
    if (262, 39) not in NP.reach(old_walk, (245, 45), NP.CARD):
        errs.append("la punta este de la isla vieja no se alcanza caminando aun sin la roca")
    if not bl.walkable(existing.get((old_entry[0], old_entry[1], 7), [])):
        errs.append(f"la isla vieja no es caminable en {old_entry}")
    d = NP.reach(walk_real | {old_entry}, old_entry, NP.CARD)
    unreachable = walk_real - d.keys()
    if unreachable:
        errs.append(f"{len(unreachable)} casillas caminables sueltas, p. ej. {sorted(unreachable)[:4]}")
    if walk_real - walk:
        errs.append(f"hay bosque caminable fuera del sendero: {sorted(walk_real - walk)[:5]}")
    # la tierra nueva solo toca la vieja en la junta
    for (x, y) in land:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n in old_land and y not in JUNCTION_ROWS:
                    errs.append(f"tierra nueva {x, y} toca la isla vieja fuera de la junta ({n})")
    # el agua vieja de afuera no ve tierra nueva (su borde quedaría mal)
    for (x, y, z), it in existing.items():
        if z == 7 and it[0] in WATERS and (x, y) not in rect(BOX) and BOX[0] - 1 <= x <= BOX[0] - 1:
            if any((x + dx, y + dy) in land for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                errs.append(f"el agua vieja {x, y} queda pegada a tierra nueva")
    # vista: nada vacío a la vista
    view = {(x + dx, y + dy) for (x, y) in walk_real for dx in range(-9, 10) for dy in range(-7, 8)}
    void = {c for c in view - rect(BOX) if (c[0], c[1], 7) not in existing}
    if void:
        errs.append(f"{len(void)} casillas vacías a la vista, p. ej. {sorted(void)[:4]}")
    # monstruos
    known = set(re.findall(r'<monster name="([^"]+)"', MONSTERS.read_text(encoding="latin-1")))
    for names, *_r in STAGES:
        for n in names:
            if n not in known:
                errs.append(f"monstruo inexistente: {n}")
    dist = {c: d[c] for c in walk_real if c in d}
    avoid = BV.grow({ENTRY}, ENTRY_CLEAR) | {sign}
    rng = random.Random(f"{a.seed}-glacier")
    spawns = BV.place_stages(STAGES, BV.slices_by(set(dist) - avoid, lambda c: dist[c], len(STAGES)),
                             set(dist), avoid, 7, rng)
    n_mon = sum(len(m) for _c, _z, m in spawns)
    counts = {}
    for _c, _z, mons in spawns:
        for name, _p, _t in mons:
            counts[name] = counts.get(name, 0) + 1
    density = len(dist) / max(n_mon, 1)
    if n_mon == 0:
        errs.append("no entró ningún monstruo")
    elif density < 20:
        errs.append(f"demasiados juntos: 1 cada {density:.0f} casillas")
    last = BV.slices_by(set(dist) - avoid, lambda c: dist[c], len(STAGES))[-1]
    lair = ellipse(LAIR)
    final = [m for c, _z, ms in spawns for m in ms if m[0] in ("Frost Dragon", "Ice Spider")]
    if not any(m[1] in lair for m in final):
        errs.append("en la guarida del final no quedó ningún Frost Dragon / Ice Spider")

    longest = max(dist.values()) if dist else 0
    print(f"Glaciar del Este: tierra {len(land)}, sendero caminable {len(walk_real)} casillas, recorrido más largo "
          f"{longest} pasos; cartel {sign}")
    print(f"  {len(spawns)} spawns, {n_mon} monstruos, 1 cada {density:.0f} casillas: "
          + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if a.preview:
        m = roomkit.Map()
        x0, y0, x1, y1 = BOX[0] - 52, BOX[1], BOX[2] + 4, BOX[3]
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                ids = tiles.get((x, y)) or existing.get((x, y, 7))
                if ids:
                    m.ground((x, y, 7), ids[0])
                    for i in ids[1:]:
                        m.add((x, y, 7), i)
        roomkit.render_png(m, a.preview, 7)
        print(f"preview: {a.preview}")
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs[:40]), file=sys.stderr)
        return 1
    if a.dry_run or not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    backup = Path(tempfile.gettempdir()) / f"glacier-reach-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAP, backup / "test.otbm")
    shutil.copy2(SPAWNS, backup / "test-spawn.xml")
    print(f"backup: {backup}")
    m = roomkit.Map()
    for (x, y), ids in tiles.items():
        m.ground((x, y, 7), ids[0])
        for i in ids[1:]:
            m.add((x, y, 7), i)
    chk = roomkit.Checker(m)
    chk.tiles()
    if chk.errs:
        print("ERRORES de ítems:\n  " + "\n  ".join(chk.errs[:20]), file=sys.stderr)
        return 1
    roomkit.write_map(MAP, m, BOX, 7, chk.stackable)
    rock = roomkit.Map()
    for (x, y) in OPEN_ROCK:
        rock.ground((x, y, 7), SNOW)
    xs, ys = [c[0] for c in OPEN_ROCK], [c[1] for c in OPEN_ROCK]
    roomkit.write_map(MAP, rock, (min(xs), min(ys), max(xs), max(ys)), 7, chk.stackable)

    sp = SPAWNS.read_text(encoding="latin-1")
    block = ("\t<!-- BEGIN GLACIER_REACH_SPAWNS (scripts/map/generate-glacier-reach.py) -->\n" + spawn_xml(spawns)
             + "\n\t<!-- END GLACIER_REACH_SPAWNS -->\n")
    old = re.compile(r"[ \t]*<!-- BEGIN GLACIER_REACH_SPAWNS.*?<!-- END GLACIER_REACH_SPAWNS -->\n?", re.S)
    sp = old.sub(lambda _m: block, sp, count=1) if old.search(sp) else sp.replace("</spawns>", block + "</spawns>")
    SPAWNS.write_text(sp, encoding="latin-1")
    roomkit.patch_readables("<!-- BEGIN GLACIER_REACH_SIGNS -->", "<!-- END GLACIER_REACH_SIGNS -->",
                            [dict(x=sign[0], y=sign[1], z=7, text=SIGN_TEXT)])
    MANIFEST.write_text(json.dumps({
        "name": "Glaciar del Este", "seed": a.seed, "box": list(BOX), "entry": list(ENTRY), "path": PATH,
        "openedRock": sorted(OPEN_ROCK),
        "land": len(land), "walkable": len(walk_real), "longestWalk": longest, "sign": list(sign),
        "spawns": len(spawns), "monsters": n_mon, "monstersByKind": dict(sorted(counts.items())),
        "densityTilesPerMonster": round(density),
        "stages": [{"names": list(n), "per": p, "spawntime": st, "gap": g} for n, p, st, g in STAGES],
    }, indent=2) + "\n")
    print(f"OK {MAP}, {SPAWNS.name}, readables.xml y {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
