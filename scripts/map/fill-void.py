#!/usr/bin/env python3
"""Rellena con un suelo las casillas VACÍAS (sin tile) de una caja de un piso. No toca las que existen.

Para tapar huecos de vacío negro a la vista (mar al lado de una costa, roca dentro de una cueva). Por
defecto es dry-run; con --replace escribe test.otbm.

  python3.11 scripts/map/fill-void.py 262 0 262 19 7 --ground 4608            # mostrar
  python3.11 scripts/map/fill-void.py 262 0 262 19 7 --ground 4608 --replace  # escribir

Doc: docs/items-and-map/PIEZAS_DE_MAPA.md (errores que ya pasaron).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
sys.path.insert(0, str(HERE))
import mapdata  # noqa: E402
from roomkit import Checker, Map, _maze, areas  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("x0", type=int)
    ap.add_argument("y0", type=int)
    ap.add_argument("x1", type=int)
    ap.add_argument("y1", type=int)
    ap.add_argument("z", type=int)
    ap.add_argument("--ground", type=int, required=True)
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()

    t = mapdata.load_tiles()
    m = Map()
    for x in range(a.x0, a.x1 + 1):
        for y in range(a.y0, a.y1 + 1):
            if (x, y, a.z) not in t:
                m.ground((x, y, a.z), a.ground)
    ck = Checker(m)
    ck.tiles()
    if ck.errs:
        print("ERRORES:", ck.errs[:5])
        return 1
    print(f"{len(m.t)} casillas vacías -> {a.ground} en {a.x0},{a.y0}-{a.x1},{a.y1} z{a.z}")
    if not m.t or not a.replace:
        print("(dry-run)" if m.t else "nada que hacer")
        return 0
    raw = mapdata.MAP.read_bytes()
    body = raw[4:]
    at = _maze.find_map_data_insert(body)
    mapdata.MAP.write_bytes(raw[:4] + body[:at] + areas(m, set()) + body[at:])
    print(f"OK {mapdata.MAP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
