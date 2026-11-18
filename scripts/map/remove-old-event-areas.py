#!/usr/bin/env python3
"""Borra las casillas viejas de El Crisol, Wave Arena y Reloj de Arena (nov 2026).

Los tres sistemas se generaron originalmente DENTRO del recuadro del mapa principal
(Crisol en z0 sobre la ciudad, Wave Arena en z7 y Reloj de Arena en z6/z5 sobre el
sur del mapa), así que en RME se veían superpuestos a las hunts y a la ciudad. Se
movieron al distrito de eventos (x>=560) cambiando el origen de sus generadores:

  Crisol        scripts/map/generate-crucible.py      -> hub 600,100 z0
  Wave Arena    scripts/map/generate-wave-arena.py    -> claro 600,205 z7
  Reloj         scripts/map/generate-sand-clock.py   -> sala 600,320 z6/z5

Este script borra las casillas que quedaron en las ubicaciones viejas (eran vacío
en el mapa original: backups/yurots-original.otbm no tiene nada en estas cajas,
así que el mapa queda como antes de los generadores):

  Crisol   (70, 70 - 195, 105)   z0    559 casillas
  Wave     (165, 380 - 190, 410) z7    272 casillas
  Reloj    (325, 381 - 351, 403) z6    621 casillas + techo z5

No toca nada más: sin spawns dentro de las cajas (los monstruos los invoca el Lua)
y el único NPC afectado es Chronos (npc.xml se actualiza aparte).

Uso:
  python3 scripts/map/remove-old-event-areas.py            # dry-run
  python3 scripts/map/remove-old-event-areas.py --replace  # escribe
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import roomkit  # noqa: E402
from mapdata import REPO, load_otb, load_tiles  # noqa: E402

MAP = REPO / "server/YurOTS/ots/data/world/test.otbm"

# (nombre, caja, pisos) — las ubicaciones viejas, previas al distrito de eventos
AREAS = [
    ("crisol", (70, 70, 195, 105), (0,)),
    ("wave", (165, 380, 190, 410), (7,)),
    ("reloj", (325, 381, 351, 403), (5, 6)),
]


def box_tiles(tiles: dict, box: tuple, z: int) -> list:
    x0, y0, x1, y1 = box
    return [p for p in tiles if p[2] == z and x0 <= p[0] <= x1 and y0 <= p[1] <= y1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()

    tiles = load_tiles()
    for name, box, zs in AREAS:
        for z in zs:
            pts = box_tiles(tiles, box, z)
            print(f"{name:7s} caja {box} z{z}: {len(pts)} casillas" + (" (se borran)" if pts else " (ya vacía)"))

    if a.dry_run or not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    backup = Path("/private/var/folders/c8/k2dtzwbx3ml4l81234tng6vc0000gn/T/opencode") / \
        f"remove-old-event-areas-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAP, backup / "test.otbm")
    print(f"backup: {backup}")

    stackable = {sid for sid, rec in load_otb().items() if "stackable" in rec["flags"]}
    for _name, box, zs in AREAS:
        for z in zs:
            roomkit.write_map(MAP, roomkit.Map(), box, z, stackable)

    after = load_tiles()
    errs = [f"{name} z{z}: quedan {len(box_tiles(after, box, z))} casillas"
            for name, box, zs in AREAS for z in zs if box_tiles(after, box, z)]
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 1
    print("OK: las tres cajas viejas quedaron vacías")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
