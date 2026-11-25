#!/usr/bin/env python3
"""Cueva en cruz de z9 (bajada desde 56,164,8): paredes completas, sin pasto y sin vacío (24 nov 2026).

La cueva (hecha a mano, sin generador) tenía paredes "dirt wall" solo en los lados norte y oeste del piso: en los
lados sur y este la tierra 101 tocaba el piso directo. Además, un cuadrado de pasto bajo la escalera de mano y
esquinas de vacío negro a la vista.

Las paredes 371-382 se ponen COMO SUELO de la casilla de tierra, una por casilla, según dónde está el piso
(medido en todo el mapa, z8+):
  371 s, 372 n, 373 e, 374 w            piso a ese lado
  379 s+e, 380 s+w, 381 n+w, 382 n+e    piso en dos lados (esquina)
  375 se, 376 sw, 377 nw, 378 ne        piso solo en diagonal

Qué hace, solo en la componente de piso que se alcanza desde la escalera (56,164,9):
  - recalcula la pared de toda casilla de tierra/pared que toca ese piso; si una combinación no tiene pieza
    (piso a los dos lados), esa casilla pasa a piso de tierra 103;
  - el pasto bajo la escalera pasa a tierra 103 (la escalera de mano se queda);
  - las casillas vacías a la vista del piso pasan a tierra 101.

  python3.11 scripts/map/fix-cross-cave.py            # dry-run
  python3.11 scripts/map/fix-cross-cave.py --replace
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
sys.path.insert(0, str(HERE))
import mapdata  # noqa: E402


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


NP = _load("north_pass", "generate-north-pass.py")
VS = _load("volcanic_shore", "fix-volcanic-shore.py")

Z = 9
START = (56, 164)
EARTH, DIRT = 101, 103
WALLS = set(range(371, 383))
SIDE = {"s": 371, "n": 372, "e": 373, "w": 374}
CORNER = {("s", "e"): 379, ("s", "w"): 380, ("n", "w"): 381, ("n", "e"): 382}
INNER = {"se": 375, "sw": 376, "nw": 377, "ne": 378}
GRASS = {4756, 4526} | set(range(110, 122))     # pasto y sus bordes


def is_rock(v):
    return v is not None and (v[0] == EARTH or v[0] in WALLS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()

    t = mapdata.load_tiles()
    get = lambda c: t.get((c[0], c[1], Z))                       # noqa: E731
    # piso alcanzable desde la escalera (todo lo que no es roca ni vacío)
    floor, todo = {START}, [START]
    while todo:
        x, y = todo.pop()
        for dx, dy in NP.ALL8:
            n = (x + dx, y + dy)
            if n not in floor and get(n) is not None and not is_rock(get(n)):
                floor.add(n)
                todo.append(n)
    changes = {}
    # paredes: hasta que toda roca pegada al piso tenga UNA pieza
    for _ in range(20):
        ring = {(x + dx, y + dy) for (x, y) in floor for dx, dy in NP.ALL8} - floor
        bad = set()
        for c in ring:
            if not is_rock(get(c)) and c not in changes:
                continue
            pcs = NP.pieces_for(NP.neighbors_in(floor, *c), SIDE, CORNER, INNER)
            if pcs is None or len(pcs) != 1:
                bad.add(c)
            else:
                changes[c] = [pcs[0]]
        if not bad:
            break
        for c in bad:
            floor.add(c)
            changes[c] = [DIRT]
    else:
        raise SystemExit("las paredes no convergen")
    # pasto -> tierra (conserva lo que tenga encima)
    for c in floor:
        v = get(c)
        if v and v[0] in GRASS:
            changes[c] = [DIRT] + v[1:]
    # vacío a la vista -> roca
    for (x, y) in floor:
        for dx in range(-9, 10):
            for dy in range(-7, 8):
                n = (x + dx, y + dy)
                if get(n) is None and n not in changes:
                    changes[n] = [EARTH]
    changes = {c: v for c, v in changes.items() if get(c) != v}
    from collections import Counter
    kinds = Counter("pared" if v[0] in WALLS else "piso" if v[0] == DIRT else "roca" for v in changes.values())
    print(f"piso de la cueva: {len(floor)} casillas; cambian {len(changes)}: {dict(kinds)}")
    if not a.replace:
        print("(dry-run)")
        return 0
    VS.Z = Z
    out, edited, added = VS.write(mapdata.MAP.read_bytes(), changes, t)
    mapdata.MAP.write_bytes(out)
    print(f"OK {mapdata.MAP}: {edited} cambiadas, {added} nuevas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
