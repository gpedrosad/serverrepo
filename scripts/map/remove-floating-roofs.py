#!/usr/bin/env python3
"""Saca los techos que flotan: grupos de casillas de techo (suelo con "roof" en el nombre, en cualquier piso)
donde ninguna casilla tiene pared, puerta, ventana, arco o columna ni en sí misma ni en el piso de abajo.

Quedaron al borrar casas sin borrar su techo (las casas de bambú del Bamboo Camp, nov 2026, y una casa de tejas
al oeste en 71-79,217-224). Un techo sin casa debajo se ve flotando sobre el pasto y, al pararse debajo, el
cliente esconde los pisos de arriba como si se estuviera adentro.

  python3 scripts/map/remove-floating-roofs.py            # lista los grupos (dry-run)
  python3 scripts/map/remove-floating-roofs.py --apply    # los borra del test.otbm

Solo borra casillas que son todo techo (el suelo y, si tiene, sus bordes de techo); si hay otra cosa encima se
informa y no se toca. Doc: docs/items-and-map/MAPAS.md (errores que ya pasaron).
"""
from __future__ import annotations

import argparse
import struct
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kb"))
from mapdata import MAP, T_AREA, T_HOUSETILE, T_TILE, load_otb, load_tiles, parse_tree, serialize_tree  # noqa: E402

STRUCTURAL = ("wall", "door", "window", "archway", "pillar", "gate")


def floating_groups(tiles, otb):
    name = lambda i: otb.get(i, {}).get("name", "")  # noqa: E731
    roofs = {p for p, it in tiles.items() if it and "roof" in name(it[0])}
    structural = lambda it: any(any(w in name(i) for w in STRUCTURAL) for i in it)  # noqa: E731
    seen, out = set(), []
    for r in sorted(roofs):
        if r in seen:
            continue
        comp, q = [], deque([r])
        seen.add(r)
        while q:
            c = q.popleft()
            comp.append(c)
            x, y, z = c
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    n = (x + dx, y + dy, z)
                    if n in roofs and n not in seen:
                        seen.add(n)
                        q.append(n)
        if any(structural(tiles[c][1:]) or structural(tiles.get((c[0], c[1], c[2] + 1)) or []) for c in comp):
            continue
        out.append(sorted(comp))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    otb, tiles = load_otb(), load_tiles()
    groups = floating_groups(tiles, otb)
    gone, kept = set(), []
    for g in groups:
        xs, ys = [c[0] for c in g], [c[1] for c in g]
        print(f"techo flotante z{g[0][2]}: {len(g)} casillas, x{min(xs)}-{max(xs)} y{min(ys)}-{max(ys)}")
        for c in g:
            if all("roof" in otb.get(i, {}).get("name", "") for i in tiles[c]):   # techo y sus bordes de techo
                gone.add(c)
            else:
                kept.append(c)
    if kept:
        print(f"  con algo encima (no se tocan): {kept[:10]}")
    print(f"total: {len(gone)} casillas de techo a borrar")
    if not a.apply or not gone:
        print("(dry-run)" if not a.apply else "nada que borrar")
        return 0
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    md = root[2][0]
    removed = 0
    for area in list(md[2]):
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        before = len(area[2])
        area[2] = [t for t in area[2] if not (t[0] in (T_TILE, T_HOUSETILE)
                                               and (ax + t[1][0], ay + t[1][1], az) in gone)]
        removed += before - len(area[2])
        if not area[2]:
            md[2].remove(area)
    if removed != len(gone):
        print(f"ERROR: se esperaban {len(gone)} casillas y se encontraron {removed}; no se escribe", file=sys.stderr)
        return 1
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    print(f"OK: {removed} casillas de techo borradas de {MAP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
