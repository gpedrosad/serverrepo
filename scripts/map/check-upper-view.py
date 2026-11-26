#!/usr/bin/env python3
"""Casillas bajo tierra desde donde el cliente ve el piso de arriba ("se ve lo de arriba").

El cliente (OTClient, calcFirstVisibleFloor) bajo tierra dibuja hasta 2 pisos arriba, salvo que la casilla
de arriba (x, y, z-1) o la de arriba en diagonal (x+1, y+1, z-1) —del jugador o de sus 4 vecinas que no
tapan la vista— tenga suelo. Si arriba no hay tile (vacío), se ven encima las cuevas o casas de los pisos
de arriba, corridas en diagonal. Arreglo: roca (101) en el piso de arriba donde no hay nada. Ejemplo: el
techo de El Foso Olvidado (generate-forgotten-pit.py, ceiling_tiles). Ver docs/items-and-map/MAPAS.md.

  python3 scripts/map/check-upper-view.py                       # todo el mapa, z8-z15, agrupado por zona
  python3 scripts/map/check-upper-view.py --box 200 0 275 90 --z 10 11 12
  python3 scripts/map/check-upper-view.py --fix                 # pone el techo de roca y vuelve a revisar
Sale con código 1 si alguna casilla ve algo arriba. --fix solo agrega tiles en casillas vacías (no toca las
que existen) y no pone roca pegada a un piso caminable del piso de arriba (quedaría roca pelada sin borde):
esas las informa para arreglarlas a mano.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kb"))
from mapdata import load_otb, load_tiles, parse_dat  # noqa: E402


class View:
    def __init__(self):
        self.tiles = load_tiles()
        otb, dat = load_otb(), parse_dat()
        self.f = {}
        for sid, e in otb.items():
            d = dat.get(e.get("cid")) if e.get("cid") else None
            fl = d["flags"] if d else {}
            self.f[sid] = (0x00 in fl, 0x02 in fl, 0x16 in fl,
                           "block_solid" in e["flags"], "block_projectile" in e["flags"])

    def _f(self, sid):
        return self.f.get(sid, (False, False, False, False, False))

    def limits(self, pos, free) -> bool:
        it = self.tiles.get(pos)
        if not it:
            return False
        ground, bottom, dont_hide, _solid, proj = self._f(it[0])
        return not dont_hide and (ground or (bottom and (free or proj)))

    def look_possible(self, pos) -> bool:
        return not any(self._f(i)[4] for i in self.tiles.get(pos, ()))

    def walkable(self, pos) -> bool:
        it = self.tiles.get(pos)
        return bool(it) and self._f(it[0])[0] and not any(self._f(i)[3] for i in it)

    def first_floor(self, x, y, z) -> int:
        ff = max(z - 2, 8)
        for ix in (-1, 0, 1):
            for iy in (-1, 0, 1):
                p = (x + ix, y + iy, z)
                if ff >= z or not ((ix == 0 and iy == 0) or (abs(ix) != abs(iy) and self.look_possible(p))):
                    continue
                free = not self.look_possible(p)
                for k in range(1, z - ff + 1):
                    if self.limits((p[0], p[1], z - k), free):
                        ff = z - k + 1
                        break
                    if self.limits((p[0] + k, p[1] + k, z - k), free):
                        ff = z - k + 1
                        break
        return ff

    def sees_above(self, x, y, z) -> int:
        """Cuántas casillas de los pisos de arriba entran en pantalla (0 = nada)."""
        ff = self.first_floor(x, y, z)
        n = 0
        for uz in range(ff, z):
            off = z - uz
            n += sum((x + dx - off, y + dy - off, uz) in self.tiles for dx in range(-8, 10) for dy in range(-6, 8))
        return n


ROCK = 101


def ceiling_for(v: View, bad) -> tuple[set, set]:
    """Casillas del piso de arriba que necesitan roca: encima del jugador y de sus 8 vecinas, si están
    vacías. Devuelve (se pueden poner, pegadas a piso caminable de arriba)."""
    want = {(x + dx, y + dy, z - 1) for x, y, z, _n in bad for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    want = {p for p in want if p not in v.tiles}
    near = {p for p in want if any(v.walkable((p[0] + dx, p[1] + dy, p[2]))
                                   for dx in (-1, 0, 1) for dy in (-1, 0, 1))}
    return want - near, near


def write_rock(cells: set):
    import roomkit
    from mapdata import MAP
    by_z: dict = {}
    for x, y, z in cells:
        by_z.setdefault(z, roomkit.Map()).ground((x, y, z), ROCK)
    for z, m in sorted(by_z.items()):   # caja vacía (1, 1, 0, 0): no borra nada
        roomkit.write_map(MAP, m, (1, 1, 0, 0), z, set())


def scan(v: View, a) -> list:
    bad = []
    for (x, y, z) in sorted(v.tiles):
        if z not in a.z or (a.box and not (a.box[0] <= x <= a.box[2] and a.box[1] <= y <= a.box[3])):
            continue
        if v.walkable((x, y, z)) and (n := v.sees_above(x, y, z)):
            bad.append((x, y, z, n))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--box", type=int, nargs=4, metavar=("X0", "Y0", "X1", "Y1"))
    ap.add_argument("--z", type=int, nargs="+", default=list(range(8, 16)))
    ap.add_argument("--fix", action="store_true", help="poner roca arriba donde no hay nada")
    a = ap.parse_args()
    v = View()
    bad = scan(v, a)
    # El techo nuevo puede quedar a la vista de casillas que antes no veían nada arriba (el piso de arriba
    # estaba vacío): se repite hasta que no quede ninguna.
    for _round in range(6):
        if not (a.fix and bad):
            break
        ok, near = ceiling_for(v, bad)
        if not ok:
            break
        write_rock(ok)
        print(f"techo: {len(ok)} casillas de roca nuevas" + (f"; {len(near)} sin poner, pegadas a piso de arriba: "
                                                            f"{sorted(near)[:8]}" if near else ""))
        v = View()
        bad = scan(v, a)
    # agrupar en bloques de 32x32 por piso para que el informe sea legible
    groups: dict = {}
    for x, y, z, n in bad:
        groups.setdefault((x // 32 * 32, y // 32 * 32, z), []).append((x, y))
    for (gx, gy, z), cells in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        xs, ys = [c[0] for c in cells], [c[1] for c in cells]
        print(f"z{z} x {min(xs)}-{max(xs)} y {min(ys)}-{max(ys)}: {len(cells)} casillas ven el piso de arriba")
    print(f"total: {len(bad)} casillas" if bad else "OK: desde ninguna casilla se ve el piso de arriba")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
