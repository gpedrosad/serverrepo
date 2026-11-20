#!/usr/bin/env python3
"""Lista grupos de madera transitable que tocan agua: puentes, muelles, barcos y pisos junto al río.

Sirve para encontrar puentes a los que ponerles barandas (BRIDGES en scripts/client-rme/dock_bridge_art.py).
Hay que mirarlos (render) antes: los barcos y las casas junto al agua también salen.

  python3 scripts/map/find-wood-bridges.py [--z 7]

Columnas: casillas, cuántas tocan agua, z, caja x/y, suelos más comunes, barandas propias ya puestas.
Doc: docs/items-and-map/TRANSICIONES_DEPOT.md.
"""
import argparse
import sys
from collections import Counter, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'kb')]
from mapdata import load_otb, load_tiles  # noqa: E402

OURS = range(20282, 20301)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--z', type=int)
    a = ap.parse_args()
    t, o = load_tiles(), load_otb()

    def ground(ids):
        return next((i for i in ids if o.get(i, {}).get('group') == 'ground'), None)

    def name(i):
        return (o.get(i, {}).get('name') or '').lower()

    water = {i for i, v in o.items() if v.get('group') == 'ground' and 'water' in name(i)}
    woodg = {i for i, v in o.items() if v.get('group') == 'ground'
             and any(k in name(i) for k in ('wood', 'bridge', 'plank'))}
    blocked = lambda ids: any('block_solid' in o.get(i, {}).get('flags', []) for i in ids)
    wet = lambda p: p in t and ground(t[p]) in water
    wood = {p for p, ids in t.items() if ground(ids) in woodg and not blocked(ids) and (a.z is None or p[2] == a.z)}
    edge = {p for p in wood if any(wet((p[0] + dx, p[1] + dy, p[2])) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    seen, comps = set(), []
    for p in edge:
        if p in seen:
            continue
        q, comp = deque([p]), []
        seen.add(p)
        while q:
            c = q.popleft()
            comp.append(c)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (c[0] + dx, c[1] + dy, c[2])
                if nb in wood and nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        comps.append(comp)
    for comp in sorted(comps, key=len, reverse=True):
        xs, ys = [c[0] for c in comp], [c[1] for c in comp]
        rails = sum(1 for c in comp for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
                    for i in t.get((c[0] + dx, c[1] + dy, c[2]), []) if i in OURS)
        grounds = Counter(ground(t[c]) for c in comp).most_common(2)
        print(f"{len(comp):4} agua {sum(c in edge for c in comp):3}  z{comp[0][2]}  x{min(xs)}-{max(xs)} "
              f"y{min(ys)}-{max(ys)}  {grounds}  barandas {rails}")


if __name__ == '__main__':
    main()
