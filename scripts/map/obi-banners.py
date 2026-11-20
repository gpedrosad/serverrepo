#!/usr/bin/env python3
"""Cuelga las banderas y estandartes de exhibición en las paredes del local de Obi (173,46,7).

Usa las versiones FIJAS (server 20320-20326: sin moveable/pickupable, mismo dibujo que las que vende Obi), así
nadie se las lleva aunque la pared esté al alcance desde la calle. Agrega el ítem al nodo de la casilla del
OTBM sin tocar el resto (flags de la casilla, otros ítems). Re-ejecutable: si la pared ya tiene algo colgado,
no la toca.

  z7, pared norte por dentro del local (gancho al sur): Brasil, Chile, USA (la 176,43 tiene una antorcha)
  z7, pared oeste por dentro (gancho al este):          Argentina
  z7, pared sur mirando a la calle (gancho al sur):      los 3 estandartes de guerra

  python3.11 scripts/map/obi-banners.py --dry-run
  python3.11 scripts/map/obi-banners.py
Doc: docs/gameplay/HANGABLES.md.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
import mapdata  # noqa: E402

MAP = HERE.parents[1] / "server/YurOTS/ots/data/world/test.otbm"
PLACES = {
    (173, 43, 7): 20320,   # brazil
    (174, 43, 7): 20321,   # chile
    (177, 43, 7): 20322,   # usa
    (172, 44, 7): 20323,   # argentina (pared oeste, gancho al este)
    (173, 49, 7): 20324,   # pirate banner (hacia la calle)
    (174, 49, 7): 20325,   # war banner
    (176, 49, 7): 20326,   # royal banner
}
T_AREA, T_TILE, T_HOUSETILE, T_ITEM = 4, 5, 14, 6


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    raw = MAP.read_bytes()
    root = mapdata.parse_tree(raw)
    if mapdata.serialize_tree(root, raw[:4]) != raw:
        raise SystemExit("el OTBM no se reescribe idéntico: no toco nada")
    otb = mapdata.load_otb()
    hooks = {i for i, r in otb.items() if "horizontal" in r["flags"] or "vertical" in r["flags"]}
    hangable = {i for i, r in otb.items() if "hangable" in r["flags"]}
    for iid in PLACES.values():
        if iid not in hangable or "moveable" in otb[iid]["flags"]:
            raise SystemExit(f"{iid} no es una bandera fija (falta en el OTB o se puede mover)")

    found, added = {}, []
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        for tile in area[2]:
            if tile[0] not in (T_TILE, T_HOUSETILE):
                continue
            pos = (ax + tile[1][0], ay + tile[1][1], az)
            if pos in PLACES:
                found[pos] = tile
    errs = []
    for pos, iid in PLACES.items():
        tile = found.get(pos)
        if tile is None:
            errs.append(f"{pos}: no hay casilla")
            continue
        ids = [struct.unpack_from("<H", bytes(c[1]), 0)[0] for c in tile[2] if c[0] == T_ITEM]
        if any(i in hangable for i in ids):
            continue                                   # ya tiene algo colgado
        if not any(i in hooks for i in ids):
            errs.append(f"{pos}: la pared no tiene gancho ({ids})")
            continue
        tile[2].append([T_ITEM, bytearray(struct.pack("<H", iid)), []])
        added.append((pos, iid))
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 1
    for pos, iid in added:
        print(f"  {pos}: {iid} {otb[iid]['name']}")
    print(f"{len(added)} colgadas, {len(PLACES) - len(added)} ya estaban")
    if added and not a.dry_run:
        MAP.write_bytes(mapdata.serialize_tree(root, raw[:4]))
        print(f"OK {MAP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
