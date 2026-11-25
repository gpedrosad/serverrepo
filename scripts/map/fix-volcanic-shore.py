#!/usr/bin/env python3
"""Isla volcánica del noroeste: el mar de lava deja de ser un bloque cuadrado (24 nov 2026).

Antes: la lava era un rectángulo (x 20-82, y 20-96) que al oeste terminaba en vacío negro (el mapa
llega hasta x=0) y al este chocaba contra el agua en escalones, sin orilla.

Ahora: lava -> franja de tierra de 2-3 casillas (bordes de lava 4667-4678 del lado de la lava) ->
costa de roca (4644-4655 sobre la tierra, como la isla natural) -> mar 4608 hasta el borde del mapa.
La lava queda como una caldera de forma orgánica a 7-11 casillas de las islas volcánicas.

Qué se puede cambiar: solo casillas de lava (con o sin sus bordes), de agua sin nada encima o vacías,
dentro de la caja 0,0-96,114 z7. Nada a menos de 3 casillas de otra tierra (las islas del este y del sur
conservan su agua y su costa). La lava a 5 o menos de las islas volcánicas no se toca (sus bordes quedan
iguales).

  python3.11 scripts/map/fix-volcanic-shore.py --dry-run --png /tmp/volcan.png
  python3.11 scripts/map/fix-volcanic-shore.py --replace     # una sola vez (después dice 'ya aplicado')
Doc: docs/items-and-map/ISLA_VOLCANICA.md.
"""
from __future__ import annotations

import argparse
import importlib.util
import struct
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
sys.path.insert(0, str(HERE))
import mapdata  # noqa: E402
from roomkit import Checker, Map, areas, _maze  # noqa: E402


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ember = _load("ember", "generate-ember-field.py")
_np = _load("north_pass", "generate-north-pass.py")
lava_borders = _ember.lava_borders
pieces_for, neighbors_in = _np.pieces_for, _np.neighbors_in

Z = 7
BOX = (0, 0, 96, 114)
LAVA = {598, 599, 600, 601}
LAVA_BORDERS = set(range(4667, 4679))
WATER, DIRT = 4608, 103
WATERS = set(range(4608, 4626))   # 'shallow water' con sus variantes (4609 en el sudoeste)
COAST_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
COAST_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
COAST_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}
DEAD_TREES = (2709, 2717, 2720)
FREEZE_LAVA = 5          # lava a esta distancia de las islas volcánicas no se toca
FOREIGN_GAP = 3          # agua intacta alrededor de la otra tierra
EDGE = 3                 # ni lava ni tierra a menos de esto del borde del mapa


def h(x, y, k=0):
    n = (x * 73856093) ^ (y * 19349663) ^ (k * 83492791)
    n = (n ^ (n >> 13)) * 1274126177
    return (n ^ (n >> 16)) & 0xFFFFFFFF


def vnoise(x, y, k, step=9):
    """Ruido suave en 2D (0 a 1)."""
    gx, gy = x // step, y // step
    tx, ty = (x % step) / step, (y % step) / step
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    v = lambda a, b: (h(a, b, k) % 1000) / 1000                       # noqa: E731
    top = v(gx, gy) + (v(gx + 1, gy) - v(gx, gy)) * tx
    bot = v(gx, gy + 1) + (v(gx + 1, gy + 1) - v(gx, gy + 1)) * tx
    return top + (bot - top) * ty


N8 = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
N4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def cheb_dist(seeds, limit=40):
    dist = {s: 0 for s in seeds}
    q = deque(seeds)
    while q:
        x, y = q.popleft()
        d = dist[(x, y)]
        if d >= limit:
            continue
        for dx, dy in N8:
            n = (x + dx, y + dy)
            if BOX[0] <= n[0] <= BOX[2] and BOX[1] <= n[1] <= BOX[3] and n not in dist:
                dist[n] = d + 1
                q.append(n)
    return dist


def classify(t):
    cells = [(x, y) for x in range(BOX[0], BOX[2] + 1) for y in range(BOX[1], BOX[3] + 1)]
    lava, water, void, fixed = set(), set(), set(), set()
    for c in cells:
        v = t.get(c + (Z,))
        if v is None:
            void.add(c)
        elif v[0] in LAVA and all(i in LAVA_BORDERS for i in v[1:]):
            lava.add(c)
        elif v[0] in WATERS and len(v) == 1:
            water.add(c)
        else:
            fixed.add(c)
    # tierra volcánica = componentes de lo fijo que tocan lava
    comp_of, comps = {}, []
    for c in fixed:
        if c in comp_of:
            continue
        comp, todo = [c], [c]
        comp_of[c] = len(comps)
        while todo:
            x, y = todo.pop()
            for dx, dy in N8:
                n = (x + dx, y + dy)
                if n in fixed and n not in comp_of:
                    comp_of[n] = len(comps)
                    comp.append(n)
                    todo.append(n)
        comps.append(comp)
    volcanic, foreign = set(), set()
    for comp in comps:
        touches = any((x + dx, y + dy) in lava for x, y in comp for dx, dy in N8)
        (volcanic if touches else foreign).update(comp)
    return lava, water, void, volcanic, foreign


def design(lava, water, void, volcanic, foreign):
    changeable = lava | water | void
    d_vol = cheb_dist(volcanic)
    d_for = cheb_dist(foreign)
    frozen = {c for c in lava if d_vol.get(c, 99) <= FREEZE_LAVA}
    new_lava = set(frozen)
    for c in changeable:
        x, y = c
        r = 7 + 4 * vnoise(x, y, 1)
        if (d_vol.get(c, 99) <= r and d_for.get(c, 99) >= 7
                and BOX[0] + EDGE + 3 <= x <= BOX[2] and BOX[1] + EDGE + 3 <= y):
            new_lava.add(c)
    # suavizar la lava (sin tocar la congelada)
    for _ in range(3):
        for c in sorted(changeable - frozen):
            k = sum((c[0] + dx, c[1] + dy) in new_lava for dx, dy in N8)
            if c not in new_lava and k >= 6 and d_for.get(c, 99) >= 7:
                new_lava.add(c)
            elif c in new_lava and k <= 2:
                new_lava.discard(c)
    land = volcanic | foreign
    for _ in range(50):
        d_lava = cheb_dist(new_lava, limit=4)
        rim = set()
        for c in changeable - new_lava:
            width = 2 + (vnoise(*c, 2) > 0.6)
            if d_lava.get(c, 99) <= width and d_for.get(c, 99) > FOREIGN_GAP and \
                    BOX[0] + EDGE <= c[0] and BOX[1] + EDGE <= c[1]:
                rim.add(c)
        sea = changeable - new_lava - rim
        # costa válida: el agua de 1 de ancho se rellena y la tierra que no tiene pieza pasa a agua
        sea = _np.fix_until_valid(sea, rim | sea, COAST_SIDE, COAST_CORNER, COAST_INNER)
        rim = changeable - new_lava - sea
        changed = False
        # la lava nunca toca el agua (ni en diagonal)
        for c in list(new_lava):
            if any((c[0] + dx, c[1] + dy) in sea for dx, dy in N8):
                if c in frozen:
                    raise SystemExit(f"la lava congelada {c} quedaría tocando el agua")
                new_lava.discard(c)
                changed = True
        # lava de 1 casilla entre tierras -> tierra
        dirt = rim | land
        for c in list(new_lava - frozen):
            x, y = c
            if ((x - 1, y) in dirt and (x + 1, y) in dirt) or ((x, y - 1) in dirt and (x, y + 1) in dirt):
                new_lava.discard(c)
                changed = True
        if not changed:
            return new_lava, rim, sea, frozen
    raise SystemExit("la orilla no converge")


def build_tiles(t, new_lava, rim, sea, volcanic, foreign):
    """Casilla -> [suelo, ítems...] para todo lo que cambia."""
    dirt = rim | volcanic | foreign
    isdirt = lambda x, y: (x, y) in dirt                     # noqa: E731
    out = {}
    for c in new_lava:
        want = [t.get(c + (Z,), [598])[0] if t.get(c + (Z,), [0])[0] in LAVA else 598]
        want += lava_borders(isdirt, *c)
        out[c] = want
    for c in rim:
        coast = pieces_for(neighbors_in(sea, *c), COAST_SIDE, COAST_CORNER, COAST_INNER) or []
        items = list(coast)
        if not coast and not any((c[0] + dx, c[1] + dy) in new_lava for dx, dy in N8) and h(*c, 3) % 100 < 6:
            items.append(DEAD_TREES[h(*c, 4) % 3])
        out[c] = [DIRT] + items
    for c in sea:
        cur = t.get(c + (Z,))
        out[c] = cur if cur and len(cur) == 1 and cur[0] in WATERS else [WATER]
    return {c: v for c, v in out.items() if t.get(c + (Z,)) != v}


def write(raw, changes, t):
    root = mapdata.parse_tree(raw)
    if mapdata.serialize_tree(root, raw[:4]) != raw:
        raise SystemExit("el OTBM no se reescribe idéntico: no toco nada")
    nodes = {}
    for area in root[2][0][2]:
        if area[0] != mapdata.T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        if az != Z:
            continue
        for tile in area[2]:
            if tile[0] == mapdata.T_TILE:
                nodes[(ax + tile[1][0], ay + tile[1][1])] = tile
    new_tiles = Map()
    for c, ids in changes.items():
        tile = nodes.get(c)
        if tile is None:
            new_tiles.ground(c + (Z,), ids[0])
            for i in ids[1:]:
                new_tiles.add(c + (Z,), i)
            continue
        p = bytes(tile[1])
        flags = bytearray(p[2:7]) if len(p) >= 7 and p[2] == 3 else bytearray()
        tile[1] = bytearray(p[:2]) + flags
        tile[2] = [[mapdata.T_ITEM, bytearray(struct.pack("<H", i)), []] for i in ids]
    out = mapdata.serialize_tree(root, raw[:4])
    if new_tiles.t:
        body = out[4:]
        at = _maze.find_map_data_insert(body)
        out = out[:4] + body[:at] + areas(new_tiles, set()) + body[at:]
    return out, len(changes) - len(new_tiles.t), len(new_tiles.t)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--png", type=Path)
    a = ap.parse_args()

    t = mapdata.load_tiles()
    lava, water, void, volcanic, foreign = classify(t)
    if not void:
        # Se aplica una sola vez: después la orilla nueva cuenta como tierra volcánica y la caldera crecería
        # otra vez. Para rehacerla, partir del test.otbm anterior a este arreglo (git log del script).
        print("ya aplicado: no queda vacío en la caja; no se toca nada")
        return 0
    new_lava, rim, sea, frozen = design(lava, water, void, volcanic, foreign)
    changes = build_tiles(t, new_lava, rim, sea, volcanic, foreign)
    print(f"antes: lava {len(lava)}, agua {len(water)}, vacío {len(void)}; tierra volcánica {len(volcanic)}, "
          f"otra tierra {len(foreign)}")
    print(f"ahora: lava {len(new_lava)} ({len(frozen)} sin tocar), orilla {len(rim)}, mar {len(sea)}; "
          f"cambian {len(changes)} casillas")
    # validación
    errs = []
    m = Map()
    for c, ids in changes.items():
        m.ground(c + (Z,), ids[0])
        for i in ids[1:]:
            m.add(c + (Z,), i)
    ck = Checker(m)
    ck.tiles()
    errs += ck.errs
    for c in new_lava:
        if any((c[0] + dx, c[1] + dy) in sea for dx, dy in N8):
            errs.append(f"lava {c} toca el agua")
    for c in rim:
        if pieces_for(neighbors_in(sea, *c), COAST_SIDE, COAST_CORNER, COAST_INNER) is None:
            errs.append(f"orilla {c} sin pieza de costa válida")
    touched_land = [c for c in changes if c in volcanic or c in foreign]
    if touched_land:
        errs.append(f"se tocaría tierra existente: {touched_land[:5]}")
    if a.png:
        full = dict(t)
        for c, ids in changes.items():
            full[c + (Z,)] = ids
        w, hh, rgba = mapdata.Renderer().area({k: v for k, v in full.items() if k[2] == Z}, 0, 0, 100, 116, Z)
        a.png.write_bytes(mapdata.png_bytes(w, hh, rgba))
        print(f"PNG {a.png}")
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs[:20]))
        return 1
    if not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0
    raw = mapdata.MAP.read_bytes()
    out, edited, added = write(raw, changes, t)
    mapdata.MAP.write_bytes(out)
    print(f"OK {mapdata.MAP}: {edited} casillas cambiadas, {added} nuevas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
