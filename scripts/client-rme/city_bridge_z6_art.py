#!/usr/bin/env python3
"""Ironbound: puente principal de basalto, hierro y bronce (z6, 141,65).

Conserva los dos pasos de 1 sqm, las plataformas, cuatro trampillas y las 50
anclas de baranda originales. El material 3D es privado: no modifica los otros
puentes de madera. Las piezas de 64x64 se reparten sin costuras en esas anclas.

  python3.11 scripts/client-rme/city_bridge_z6_art.py --preview /tmp/ironbound.png

Genera cbz6_*.png, los pavimentos y el pilar. Instalar con add_custom_items.py
solo esta familia y aplicar bridge-trap-steps.py antes de publicar el cliente.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ironbound_bridge_material import material  # noqa: E402
from functools import lru_cache
D = material()

T = D.T
ROOT = HERE.parents[1]
OUT_DIR = ROOT / "devtools/zagan-test/custom-sprites"
SERVER_BASE, CLIENT_BASE = 20490, 5210          # reservado hasta 50 piezas
PROTOTYPE = 1517                                # baranda de madera 2x2 (bloquea), como las del muelle
LIGHT = D.LIGHT
# Keep every original air anchor: same collision, missile clearance and trap layout.
RAIL_ANCHORS = frozenset(((139, 56), (139, 57), (139, 58), (139, 59), (139, 60), (139, 61), (139, 65), (139, 66),
 (139, 67), (139, 71), (139, 72), (139, 73), (139, 74), (139, 75), (140, 56), (140, 62),
 (140, 63), (140, 64), (140, 65), (140, 68), (140, 69), (140, 70), (140, 71), (140, 76),
 (141, 56), (141, 76), (142, 56), (142, 62), (142, 63), (142, 64), (142, 65), (142, 68),
 (142, 69), (142, 70), (142, 71), (142, 76), (143, 56), (143, 57), (143, 58), (143, 59),
 (143, 60), (143, 61), (143, 65), (143, 66), (143, 67), (143, 71), (143, 72), (143, 73),
 (143, 74), (143, 75)))

TRAPDOORS = {(141, 59), (142, 59), (141, 74), (142, 74)}
NARROW = [(62, 65), (68, 71)]
DECK = ({(x, y) for x in (140, 141, 142) for y in range(57, 76)
         if not any(a <= y <= b for a, b in NARROW)}
        | {(141, y) for a, b in NARROW for y in range(a, b + 1)})


def runs():
    """Tramos rectos del borde del tablero: (lado, línea, desde, hasta). Lados w/e corren de norte a sur
    (línea = x del borde), n/s de oeste a este (línea = y del borde)."""
    out = []
    xs = sorted({x for x, _ in DECK})
    ys = sorted({y for _, y in DECK})
    for side, (dx, dy) in (("w", (-1, 0)), ("e", (1, 0)), ("n", (0, -1)), ("s", (0, 1))):
        edges = sorted((x, y) for x, y in DECK if (x + dx, y + dy) not in DECK)
        if side in "we":
            by_line = {}
            for x, y in edges:
                by_line.setdefault(x if side == "w" else x + 1, []).append(y)
        else:
            by_line = {}
            for x, y in edges:
                by_line.setdefault(y if side == "n" else y + 1, []).append(x)
        for line, vals in by_line.items():
            vals.sort()
            start = prev = vals[0]
            for v in vals[1:] + [None]:
                if v is not None and v == prev + 1:
                    prev = v
                    continue
                out.append((side, line, start, prev))
                if v is not None:
                    start = prev = v
    return out


def lantern_corners():
    """Esquinas con farol: las 4 puntas del puente y las 4 de cada paso angosto (de su lado ancho)."""
    out = {(140, 57), (143, 57), (140, 76), (143, 76)}
    for a, b in NARROW:
        out |= {(140, a), (143, a), (140, b + 1), (143, b + 1)}
    return out


def structure():
    """Cajas y anclas con su región. Devuelve (cajas, [(ancla, región)])."""
    boxes, regions = [], {}
    lamps = lantern_corners()
    newels = set()

    def region(anchor, rect):
        regions.setdefault(anchor, []).append(rect)

    for side, line, a, b in runs():
        if side in "we":
            fixed = line * T - 4
            boxes += D.rail_line("y", fixed, a * T + 3, (b + 1) * T - 3, D.every(a * T + 24, b * T + 9))
            ax = line - 1 if side == "w" else line
            for y in range(a, b + 1):
                region((ax, y), (line * T - 8, line * T + 8, y * T, y * T + T))
            nx = line * T - 6 if side == "w" else line * T - 4
            for gy, cy in ((a * T, a), ((b + 1) * T - 6, b + 1)):
                newels.add((nx, gy, (line, cy)))
        else:
            fixed = line * T - 6 if side == "n" else line * T - 4
            boxes += D.rail_line("x", fixed, a * T + 3, (b + 1) * T - 3, D.every(a * T + 24, b * T + 9))
            ay = line - 1 if side == "n" else line
            for x in range(a, b + 1):
                region((x, ay), (x * T, x * T + T, line * T - T, line * T + 8) if side == "n"
                       else (x * T, x * T + T, line * T - T, line * T + T))
    # un poste por esquina (los de los tramos verticales); con farol donde corresponde
    seen = set()
    for nx, gy, corner in sorted(newels):
        if corner in seen:
            continue
        seen.add(corner)
        boxes += D.newel(nx, gy, corner in lamps)
    # las puntas de los postes de esquina caen en la casilla de aire de ese rincón: se le da región
    return boxes, regions


def anchor_regions(regions):
    """Una sola región rectangular por ancla (la que cubre todas sus franjas), ampliada 8 px en los extremos
    para que los postes de esquina entren enteros."""
    out = {}
    for anchor, rects in regions.items():
        x0 = min(r[0] for r in rects) - 8
        x1 = max(r[1] for r in rects) + 8
        y0 = min(r[2] for r in rects) - 8
        y1 = max(r[3] for r in rects) + 8
        out[anchor] = (x0, x1, y0, y1)
    return out


def build():
    """[(ancla, sprite 64x64)] sin regiones solapadas: cada píxel del suelo va a una sola ancla."""
    from PIL import Image
    boxes, regions = structure()
    rects = anchor_regions(regions)
    # también las casillas de aire en diagonal (rincones): ahí caen los remates de los faroles de esquina
    for x, y in DECK:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                c = (x + dx, y + dy)
                if c not in DECK and c not in rects:
                    rects[c] = (c[0] * T - 8, c[0] * T + T + 8, c[1] * T - 8, c[1] * T + T + 8)
    rects = {a: rects[a] for a in RAIL_ANCHORS}
    # partir el suelo en celdas de 2 px y asignar cada celda a la ancla más cercana cuya región la contiene
    # y que la pueda dibujar (el sprite de una casilla se extiende solo hacia arriba y a la izquierda)
    cells, lost = {}, []
    xs0 = min(r[0] for r in rects.values())
    xs1 = max(r[1] for r in rects.values())
    ys0 = min(r[2] for r in rects.values())
    ys1 = max(r[3] for r in rects.values())
    step = 2
    for gx in range(xs0, xs1, step):
        for gy in range(ys0, ys1, step):
            fs = D.faces(boxes, (gx, gx + step, gy, gy + step))
            if not fs:
                continue
            # caja en pantalla de lo que se dibuja en esta celda (el contorno pinta encima, no agrega píxeles)
            sx0 = min(p[0] - p[2] for _d, pts, _c in fs for p in pts)
            sy0 = min(p[1] - p[2] for _d, pts, _c in fs for p in pts)
            sx1 = max(p[0] - p[2] for _d, pts, _c in fs for p in pts) + 1
            sy1 = max(p[1] - p[2] for _d, pts, _c in fs for p in pts) + 1
            best = None
            for (ax, ay), (x0, x1, y0, y1) in rects.items():
                if not (x0 <= gx < x1 and y0 <= gy < y1):
                    continue
                if sx0 < (ax - 1) * T or sy0 < (ay - 1) * T or sx1 > (ax + 1) * T or sy1 > (ay + 1) * T:
                    continue
                d = max(abs(gx - (ax * T + 16)), abs(gy - (ay * T + 16)))
                key = (d, ay, ax)
                if best is None or key < best[0]:
                    best = (key, (ax, ay))
            if best:
                cells.setdefault(best[1], []).append((gx, gy))
            else:
                lost.append((gx, gy))
    orphan = lost
    if orphan:
        raise SystemExit(f"{len(orphan)} celdas de baranda sin ancla, p. ej. {orphan[:4]}")
    anchors = sorted(rects)
    origin = ((min(x for x, _ in anchors) - 2) * T, (min(y for _, y in anchors) - 2) * T)
    size = ((max(x for x, _ in anchors) + 2) * T - origin[0], (max(y for _, y in anchors) + 2) * T - origin[1])
    layers = []
    for anchor in anchors:
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        # celdas contiguas en columnas: agrupar por filas para no renderizar 2x2 px uno por uno
        rows = {}
        for gx, gy in cells.get(anchor, []):
            rows.setdefault(gy, []).append(gx)
        for gy, gxs in rows.items():
            gxs.sort()
            start = prev = gxs[0]
            for v in gxs[1:] + [None]:
                if v is not None and v == prev + step:
                    prev = v
                    continue
                img.alpha_composite(D.render_piece(boxes, (start, prev + step, gy, gy + step), origin, size))
                if v is not None:
                    start = prev = v
        layers.append((anchor, img))
    union = Image.new("RGBA", size, (0, 0, 0, 0))
    for _a, img in layers:
        union.alpha_composite(img)
    alpha = union.getchannel("A").load()
    W, Hh = size

    def edge(x, y):
        return any(not (0 <= x + dx < W and 0 <= y + dy < Hh) or alpha[x + dx, y + dy] == 0
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))

    out = []
    for (ax, ay), img in layers:
        px = img.load()
        for y in range(Hh):
            for x in range(W):
                r, g, b, a = px[x, y]
                if not a or (r, g, b) in (D.GLASS_S, D.GLASS_E):
                    continue
                if edge(x, y):
                    px[x, y] = D.OUTLINE + (255,)
                else:
                    k = D.grain((x + origin[0]) % T, (y + origin[1]) % T)
                    px[x, y] = (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)), 255)
        cx, cy = (ax - 1) * T - origin[0], (ay - 1) * T - origin[1]
        bbox = img.getbbox()
        if bbox and (bbox[0] < cx or bbox[1] < cy or bbox[2] > cx + 64 or bbox[3] > cy + 64):
            raise SystemExit(f"{ax},{ay}: el dibujo se sale del 2x2 ({bbox} vs {cx},{cy})")
        sprite = img.crop((cx, cy, cx + 64, cy + 64))
        lit = any(p[:3] in (D.GLASS_S, D.GLASS_E) for p in sprite.getdata() if p[3])
        out.append(((ax, ay), sprite, lit))
    return out


@lru_cache(maxsize=1)
def pieces():
    """Sprites únicos: {clave: (sprite, con luz)} y {ancla: clave}."""
    uniq, keys, place = {}, {}, {}
    for anchor, sprite, lit in build():
        raw = sprite.tobytes()
        if raw not in keys:
            keys[raw] = f"cbz6_{len(keys):02d}"
            uniq[keys[raw]] = (sprite, lit)
        place[anchor] = keys[raw]
    assert len(uniq) <= 50, "Ironbound rail IDs exceed reserved range"
    assert set(place) == RAIL_ANCHORS
    return uniq, place


def server_ids():
    uniq, _ = pieces()
    return {k: SERVER_BASE + i for i, k in enumerate(sorted(uniq))}


def cbz6_items():
    uniq, _ = pieces()
    out = []
    for i, key in enumerate(sorted(uniq)):
        lit = uniq[key][1]
        item = dict(name="ironbound bridge beacon" if lit else "basalt parapet", server_id=SERVER_BASE + i,
                    client_id=CLIENT_BASE + i, prototype=PROTOTYPE, png=f"{key}.png", decor=True, tiles=2,
                    descr="An amber beacon on a basalt parapet." if lit else "Basalt masonry braced with bronze and iron.")
        if lit:
            item["light"] = LIGHT
        out.append(item)
    return out


def placements():
    """{(x, y): server id} de las anclas (casillas de aire alrededor del tablero, z6)."""
    ids = server_ids()
    _, place = pieces()
    return {a: ids[k] for a, k in place.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()
    from PIL import Image
    uniq, place = pieces()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, (img, _lit) in uniq.items():
        img.save(OUT_DIR / f"{key}.png")
    from ironbound_bridge_deck import prepare
    prepare()
    print(f"{len(uniq)} piezas únicas, {len(place)} anclas")
    if a.preview:
        sys.path[:0] = [str(ROOT / "scripts/map"), str(ROOT / "scripts/map/kb")]
        from mapdata import load_tiles, Renderer
        from ironbound_bridge_deck import floor_pieces, floor_placements, PIER_POSITIONS, PIER_ID
        tiles = load_tiles()
        for x, y in PIER_POSITIONS:
            tiles[x, y, 7] = [s for s in tiles[x, y, 7] if s not in (1277, PIER_ID)]
        x0, y0, x1, y1 = 135, 54, 148, 79
        r = Renderer()
        w, h, b7 = r.area(tiles, x0, y0, x1, y1, 7)
        im = Image.frombytes("RGBA", (w, h), bytes(b7))
        def it(sid):
            W, H, b = r.item(sid)
            return Image.frombytes("RGBA", (W, H), bytes(b))
        wood, trap = it(405), it(429)
        pier = Image.open(OUT_DIR / 'ironbound_pier.png').convert('RGBA')
        for x, y in sorted(PIER_POSITIONS, key=lambda p: (p[1], p[0])):
            im.alpha_composite(pier, ((x - 1 - x0) * T, (y - 1 - y0) * T))
        floor_images = {i + 20540: img for i, (_, img) in enumerate(floor_pieces())}
        paving = floor_placements()
        # z6 se dibuja una casilla arriba-izquierda de z7
        for (x, y) in sorted(DECK, key=lambda c: (c[1], c[0])):
            xy = ((x - 1 - x0) * T, (y - 1 - y0) * T)
            im.alpha_composite(trap if (x, y) in TRAPDOORS else wood, xy)
            if (x, y) in paving:
                im.alpha_composite(floor_images[paving[x, y]], xy)
        for (x, y), key in sorted(place.items(), key=lambda c: (c[0][1], c[0][0])):
            im.alpha_composite(uniq[key][0], ((x - 2 - x0) * T, (y - 2 - y0) * T))
        im.convert("RGB").resize((im.width * 2, im.height * 2), Image.NEAREST).save(a.preview)
        print(a.preview)


if __name__ == "__main__":
    main()
