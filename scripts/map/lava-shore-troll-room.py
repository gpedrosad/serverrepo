#!/usr/bin/env python3
"""Orilla de roca para la sala de los troles y el pozo de Bambú (z8), en el lago de lava de los behemoths.

Las dos salas (troles 155-176 x 103-114 y el pozo de Bambú 166-178 x 93-102) eran cajas de pared de una
casilla apoyadas directo sobre el estanque de lava que rodean los pasillos de los behemoths (oeste x148,
norte y87, este x180): desde el pasillo (181,102) se veían como rectángulos flotando a 3 casillas. Este
script pasa a roca `101` la lava a 3 casillas de las salas, una costa irregular hasta 5 y las tiras finas de
lava que quedan contra un pasillo: las salas quedan dentro de un macizo de roca y quedan pozos de lava de
borde natural al norte y al sur.

Solo cambia casillas de lava (no se caminan: no cambia por dónde se anda ni los spawns). Las toma con
`claims` de mapkit: el manifiesto `generated-lava-shore-troll-room.json` guarda la lava original de cada
una, y si una casilla deja de estar en el plan vuelve a ser lava. Re-ejecutable (dos pasadas = 0 cambios).

  python3.11 scripts/map/lava-shore-troll-room.py --dry-run     # cuenta y deja la propuesta en JSON
  python3.11 scripts/map/lava-shore-troll-room.py

Doc: docs/items-and-map/MAPEAR_CUEVAS_BAMBU.md (sección "Orilla de roca").
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mapkit as K  # noqa: E402

Z = 8
AREA = (149, 88, 179, 118)          # el estanque de lava entre los pasillos (oeste x148, norte y87, este x180)
ROOMS = (153, 93, 178, 115)         # la sala de los troles y el pozo de Bambú: lo único que no es lava acá
LAVA = {598, 599, 600, 601}
ROCK = 101
SEED = 76
MANIFEST = K.WORLD / "generated-lava-shore-troll-room.json"


def neighbors8(c):
    return [(c[0] + dx, c[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def plan(tiles: dict) -> tuple[dict, dict]:
    def lava_at(c):
        ids = tiles.get((*c, Z))
        return bool(ids) and ids[0] in LAVA
    area = K.box_cells(AREA)
    lava = {c for c in area if lava_at(c)}
    rooms = {c for c in K.box_cells(ROOMS) if tiles.get((*c, Z)) and not lava_at(c)}
    solid = {c for c in K.grow(area, 1) if tiles.get((*c, Z)) and not lava_at(c)}   # salas, pasillos, roca
    noise = K.Noise(SEED)
    land = K.grow(rooms, 3)
    land |= {c for c in K.grow(rooms, 5) - land if noise.fbm(c[0] / 4, c[1] / 4, 3) > 0.5}
    land &= lava
    # suavizar: la lava que queda en tiras finas contra un pasillo o encerrada pasa a roca; sin lenguas sueltas
    for _ in range(4):
        land |= {c for c in lava - land if sum(n in land or n in solid for n in neighbors8(c)) >= 5}
        land -= {c for c in land if sum(n in land or n in solid for n in neighbors8(c)) <= 2}
    cells = {(*c, Z): [ROCK] for c in land}
    claims = {(*c, Z): list(tiles[(*c, Z)]) for c in land}
    return cells, claims


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cells-out", type=Path, help="JSON {\"x,y,z\": [ids]} para maprender --cells")
    a = ap.parse_args()
    tiles = K.load_tiles()
    # lo que ya es de este script vuelve a lava para recalcular igual en cada pasada
    if MANIFEST.exists():
        mf = json.loads(MANIFEST.read_text())
        for key, ids in mf.get("claimed", {}).items():
            p = tuple(int(n) for n in key.split(","))
            if tiles.get(p) == mf["cells"].get(key):
                tiles[p] = ids
    cells, claims = plan(tiles)
    if a.cells_out:
        a.cells_out.write_text(json.dumps({",".join(map(str, p)): ids for p, ids in cells.items()}))
    report = {}
    n = K.write_cells(cells, MANIFEST, [598], "lava-shore-troll-room", report, a.dry_run, claims=claims)
    print(f"orilla: {len(cells)} casillas de lava -> roca {ROCK}; cambian {n}" + (" (dry-run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
