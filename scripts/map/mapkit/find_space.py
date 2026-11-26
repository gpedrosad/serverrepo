#!/usr/bin/env python3
"""Busca huecos libres del mapa para una zona nueva y escribe `box`/`land` (y la entrada de una cueva) listos
para pegar en la ficha. Reemplaza el paso de "medir a mano" de docs/items-and-map/MAPAS.md#ficha.

  # isla de superficie de 78x131 lo más cerca posible de un punto (vacía en z7 y en todos los pisos de arriba)
  python3.11 scripts/map/mapkit/find_space.py --kind island --size 78x131 --near 220,300
  # cueva en z8 con la bajada en un piso caminable de z7 cerca de un punto (radio 40)
  python3.11 scripts/map/mapkit/find_space.py --kind cave --z 8 --size 64x56 --near 300,200
  opciones: --top N (5)  --gap G (casillas vacías alrededor de la caja, 2)  --radius R (cueva, 40)
            --json (para scripts)  --ascii (mapa chico del piso con las cajas numeradas)

Reglas (las mismas que valida mapkit al escribir):
  island  la caja está vacía en z y en todos los pisos de arriba (lo de arriba se vería encima de la isla)
  cave    la caja está vacía en z. La bajada `432` va en z-1 sobre una casilla de solo suelo caminable,
          con la de su norte caminable (al subir por la 1385 se llega al norte); en la cueva la 1385 va en la
          misma x, y, que tiene que caer en la zona de boca (land menos 4 y 6 abajo). El piso de arriba sin
          nada encima de la cueva se tapa con roca (techo) al escribir; se informa cuánto hay que poner.
  land    caja menos (10, 8): nada de vacío a media pantalla de lo caminable.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mapkit as K  # noqa: E402

MARGIN = (10, 8)              # caja -> land (VIEW + 1)
MOUTH = (4, 4, 6)             # boca de cueva: dentro de land, 4 de los costados/arriba y 6 abajo
TEMPLE = (130, 53)
W, H = 760, 480               # el mapa llega a x 752, y 476


class Grid:
    """Ocupación de un conjunto de pisos con tabla de sumas: cualquier caja se cuenta en O(1)."""

    def __init__(self, tiles, floors):
        occ = [[0] * (W + 1) for _ in range(H + 1)]
        for (x, y, z) in tiles:
            if z in floors and 0 <= x < W and 0 <= y < H:
                occ[y + 1][x + 1] = 1
        for y in range(1, H + 1):
            row, up, run = occ[y], occ[y - 1], 0
            for x in range(1, W + 1):
                run += row[x]
                row[x] = run + up[x]
        self.s = occ

    def count(self, x0, y0, x1, y1) -> int:
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, W - 1), min(y1, H - 1)
        if x1 < x0 or y1 < y0:
            return 0
        s = self.s
        return s[y1 + 1][x1 + 1] - s[y0][x1 + 1] - s[y1 + 1][x0] + s[y0][x0]


def land_of(box):
    x0, y0, x1, y1 = box
    return [x0 + MARGIN[0], y0 + MARGIN[1], x1 - MARGIN[0], y1 - MARGIN[1]]


def overlap(a, b) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0]) + 1
    h = min(a[3], b[3]) - max(a[1], b[1]) + 1
    if w <= 0 or h <= 0:
        return 0.0
    return w * h / ((a[2] - a[0] + 1) * (a[3] - a[1] + 1))


def pick(cands, top):
    """Las mejores que no se pisan más de un 30 % entre sí (cuevas: bajadas a 12+ una de otra), para que las
    opciones sean distintas."""
    out = []

    def apart(c, o):
        if "entrance" in c:
            return math.dist(c["entrance"][:2], o["entrance"][:2]) >= 12
        return overlap(c["box"], o["box"]) < 0.3
    for c in sorted(cands, key=lambda c: c["dist"]):
        if all(apart(c, o) for o in out):
            out.append(c)
        if len(out) == top:
            break
    return out


def islands(tiles, z, w, h, near, gap, top):
    g = Grid(tiles, set(range(0, z + 1)))
    cands = []
    for y0 in range(gap, H - h - gap, 2):
        for x0 in range(gap, W - w - gap, 2):
            box = [x0, y0, x0 + w - 1, y0 + h - 1]
            cx, cy = x0 + w / 2, y0 + h / 2
            if g.count(x0 - gap, y0 - gap, box[2] + gap, box[3] + gap):
                continue
            cands.append({"box": box, "land": land_of(box), "dist": round(math.hypot(cx - near[0], cy - near[1]))})
    return pick(cands, top)


def owners():
    """Casilla -> manifiesto de la zona generada que la escribió (rehacer esa zona pisaría la bajada)."""
    out = {}
    for f in sorted(K.WORLD.glob("generated-*.json")):
        try:
            for key in json.loads(f.read_text()).get("cells", {}):
                out[key] = f.name
        except (ValueError, AttributeError):
            continue
    return out


def caves(tiles, z, w, h, near, gap, top, radius):
    otb = K.Otb()
    here = Grid(tiles, {z})
    above = Grid(tiles, {z - 1})

    def plain(p):
        ids = tiles.get(p)
        return bool(ids) and len(ids) == 1 and otb.is_ground(ids[0]) and otb.walkable(ids)

    ex = [(x, y) for (x, y, zz) in tiles if zz == z - 1 and math.hypot(x - near[0], y - near[1]) <= radius
          and plain((x, y, z - 1)) and plain((x, y - 1, z - 1)) and (x, y, z) not in tiles]
    mx0, my0 = MARGIN[0] + MOUTH[0], MARGIN[1] + MOUTH[1]
    mx1, my1 = MARGIN[0] + MOUTH[0], MARGIN[1] + MOUTH[2]
    cands = []
    for (ex_, ey) in sorted(ex, key=lambda p: math.hypot(p[0] - near[0], p[1] - near[1])):
        best = None
        # la boca puede quedar en cualquier lugar de la zona de boca: probar varias posiciones de la caja
        for fx in (0.5, 0.25, 0.75, 0.1, 0.9):
            for fy in (0.15, 0.5, 0.85):
                x0 = round(ex_ - mx0 - fx * (w - mx0 - mx1 - 1))
                y0 = round(ey - my0 - fy * (h - my0 - my1 - 1))
                box = [x0, y0, x0 + w - 1, y0 + h - 1]
                if x0 - gap < 0 or y0 - gap < 0 or box[2] + gap >= W or box[3] + gap >= H:
                    continue
                if here.count(x0 - gap, y0 - gap, box[2] + gap, box[3] + gap):
                    continue
                roof = above.count(*box) / (w * h)
                if best is None or roof > best[0]:
                    best = (roof, box)
        if best:
            roof, box = best
            cands.append({"box": box, "land": land_of(box), "entrance": [ex_, ey, z - 1],
                          "dist": round(math.hypot(ex_ - near[0], ey - near[1])), "roof": round(100 * roof)})
        if len(cands) >= top * 40:
            break
    found = pick(cands, top)
    own = owners()
    for f in found:
        f["owner"] = own.get(",".join(map(str, f["entrance"])))
    return found


def ascii_overview(tiles, z, found, scale=8):
    occ = {(x // scale, y // scale) for (x, y, zz) in tiles if zz == z}
    rows = []
    for gy in range(0, H // scale):
        row = []
        for gx in range(0, W // scale):
            ch = "#" if (gx, gy) in occ else "."
            for i, f in enumerate(found, 1):
                x0, y0, x1, y1 = f["box"]
                if x0 // scale <= gx <= x1 // scale and y0 // scale <= gy <= y1 // scale:
                    ch = str(i % 10)
            row.append(ch)
        rows.append("".join(row).rstrip("."))
    while rows and not rows[-1]:
        rows.pop()
    return f"(1 carácter = {scale}x{scale} casillas de z{z}; # ocupado, número = opción)\n" + "\n".join(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kind", choices=("island", "cave"), required=True)
    ap.add_argument("--size", required=True, help="ancho x alto de la caja, ej. 78x131")
    ap.add_argument("--z", type=int)
    ap.add_argument("--near", default=f"{TEMPLE[0]},{TEMPLE[1]}")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--gap", type=int, default=2)
    ap.add_argument("--radius", type=int, default=40)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ascii", action="store_true")
    a = ap.parse_args()
    w, h = (int(v) for v in a.size.lower().split("x"))
    near = tuple(int(v) for v in a.near.split(","))
    z = a.z if a.z is not None else (7 if a.kind == "island" else 8)
    if w < 2 * MARGIN[0] + 12 or h < 2 * MARGIN[1] + 12:
        raise SystemExit(f"caja demasiado chica: land = caja menos {MARGIN} de cada lado")
    tiles = K.load_tiles()
    found = (islands(tiles, z, w, h, near, a.gap, a.top) if a.kind == "island"
             else caves(tiles, z, w, h, near, a.gap, a.top, a.radius))
    if a.json:
        print(json.dumps(found))
        return 0 if found else 1
    if not found:
        print(f"no hay hueco de {w}x{h} libre en z{z}" + (f" con bajada a {a.radius} de {near}" if a.kind == "cave" else ""))
        return 1
    print(f"{len(found)} hueco(s) de {w}x{h} en z{z}, del más cercano a {near}:")
    for i, f in enumerate(found, 1):
        extra = (f"  bajada 432 en {tuple(f['entrance'])} (1385 abajo en la misma x,y)  techo existente {f['roof']} %"
                 + (f"  OJO: la bajada pisa una casilla de {f['owner']}" if f.get("owner") else "")
                 if a.kind == "cave" else "")
        print(f"  {i}. distancia {f['dist']:4d}{extra}")
        frag = {"z": z, "box": f["box"], "land": f["land"]}
        if a.kind == "cave":
            frag["entrance"] = f["entrance"][:2]
        print("     " + json.dumps(frag)[1:-1])
    if a.ascii:
        print(ascii_overview(tiles, z, found))
    return 0


if __name__ == "__main__":
    sys.exit(main())
