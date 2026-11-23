#!/usr/bin/env python3
"""¿Se llega caminando desde el templo a una casilla del mismo piso? (23 nov 2026)

Recorre las casillas pisables de z7 (con suelo y sin `block_solid`, incluidas diagonales) desde el templo
(162,50,7) y dice si llega a cada destino. Si no llega, dibuja la zona: o = se llega, . = pisable pero
aislada, # = bloqueada, ~ = sin casilla, X = destino.

Sirve para no dejar una entrada encerrada (pasó con Demona Local: la franja de pasto de la entrada quedó entre
el río y la Torre del Mago Oscuro).

  python3.11 scripts/map/check-reachable.py 119,129 176,58
"""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "kb")]
from mapdata import MAP, load_otb, parse_tree  # noqa: E402
from epstein_cave_repair import index  # noqa: E402

TEMPLE, Z = (162, 50), 7


def main():
    targets = [tuple(map(int, a.split(",")[:2])) for a in sys.argv[1:]]
    if not targets:
        sys.exit(__doc__)
    otb = load_otb()
    _nodes, values, _areas = index(parse_tree(MAP.read_bytes()), otb)

    def walk(p):
        ids = values.get((*p, Z))
        return bool(ids) and any(otb.get(i, {}).get("group") == "ground" for i in ids) and not any(
            "block_solid" in otb.get(i, {}).get("flags", ()) for i in ids)

    seen, todo = {TEMPLE}, deque([TEMPLE])
    while todo:
        x, y = todo.popleft()
        for p in ((x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            if p not in seen and walk(p):
                seen.add(p)
                todo.append(p)
    bad = 0
    for t in targets:
        # el destino puede ser un agujero o escalera: basta con llegar a una casilla vecina
        ok = t in seen or any((t[0] + dx, t[1] + dy) in seen for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        print(f"{t[0]},{t[1]},{Z}: {'se llega' if ok else 'NO se llega'}")
        if ok:
            continue
        bad += 1
        for y in range(t[1] - 6, t[1] + 7):
            print(f"{y:4d} " + "".join(
                "X" if (x, y) == t else "o" if (x, y) in seen else "." if walk((x, y))
                else "~" if values.get((x, y, Z)) is None else "#" for x in range(t[0] - 12, t[0] + 13)))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
