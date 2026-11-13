#!/usr/bin/env python3
"""Wave Arena v2 — "Claro de la Selva" (z7, nov 2026).

  Campamento (PZ)  9x5, bambú y piso de barro: plataforma de grupo 3x2, palanca de inicio,
                   palanca de ranking, fogatas. Llega el portal del templo.
  Claro            13x11, bambú y pasto: árboles en las esquinas, tocones y arbustos de
                   cobertura, barro al centro. Monstruos salen del borde de la selva
                   (norte y costados), el grupo llega al sur.

En el claro, al sur: palanca "siguiente oleada" (solo con la sala limpia) y palanca
"retirarse" (vuelve al campamento y guarda la marca). No hay TP de salida: así nadie se
va sin que la marca quede registrada.

La lógica vive en data/actions/scripts/wave_arena.lua; este script reescribe ahí el bloque
LAYOUT. El portal del templo lo maneja scripts/map/temple-portals.py (destino LANDING).

Uso:
  python3 scripts/map/generate-wave-arena.py --dry-run [--png salida.png]
  python3 scripts/map/generate-wave-arena.py --replace
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roomkit import (LEVER, REPO, SIGN, TELEPORT, WORLD, Checker, Map, Room,  # noqa: E402
                     build_room, lua_box, lua_pos, patch_block, patch_readables, render_png, write_map)

LUA = REPO / "server/YurOTS/ots/data/actions/scripts/wave_arena.lua"

Z = 7
CLEAR_BOX = (165, 380, 190, 410)        # incluye la arena vieja (172-182, 384-396)
TEMPLE_LANDING = (166, 48, 7)           # llegada del portal Wave en la plaza

UID_START, UID_RANK, UID_NEXT, UID_RETIRE = 7100, 7101, 7102, 7103

# ---------------------------------------------------------------- piezas
GRASS, GRASS_VARIANTS = 4526, (4527, 4529, 4532, 4535, 4538)
MUD, MUD_DARK, CAMP_FLOOR, PAD_FLOOR = 3264, 3265, 355, 405
JUNGLE_GRASS = 2781                      # mata baja, se pisa
BUSH, STUMPS = 2767, (4216, 4219)
TREES = (4026, 4031, 4025, 4030, 4008)
CAMPFIRE = 1428
TORCH_N, TORCH_W = 2059, 2061            # pared horizontal (norte) / vertical (oeste)

# ---------------------------------------------------------------- disposición
ARENA = Room(170, 385, 13, 11, Z)
CAMP = Room(172, 400, 9, 5, Z)
LANDING = CAMP.at(4, 3)
RETURN_TP = CAMP.at(4, 4)
PAD = dict(dx=3, dy=1, w=3, h=2)         # plataforma de grupo en el campamento
CAMP_SIGNS = {
    CAMP.at(3, 0): "WAVE ARENA\nClaro de la Selva. 20 oleadas, jefe cada 5.\n"
                   "Grupo: pisen la plataforma y tiren la palanca.",
    CAMP.at(6, 0): "RANKING SEMANAL\nCuenta la ultima oleada LIMPIA.\nPremio la primera vez en la semana: 5/10/15/20.",
    ARENA.at(6, 10): "Izquierda: siguiente oleada (sala limpia).\nDerecha: retirarse y guardar la marca.",
}
# llegada del grupo al sur del claro; el primero es el que tira (tope = plataforma 3x2 + 1)
ARRIVALS = [(6, 9), (5, 9), (7, 9), (6, 8), (5, 8), (7, 8), (4, 9)]
# SPAWNS[0] = jefe; el resto se reparte alternando norte / costados
SPAWNS = [(6, 1), (3, 0), (9, 0), (0, 3), (12, 3), (5, 0), (7, 0), (0, 5), (12, 5),
          (2, 1), (10, 1), (4, 2), (8, 2), (0, 7), (12, 7), (6, 3)]


def variant(x: int, y: int) -> int:
    """Pasto con algo de textura, determinista (mismo mapa en cada corrida)."""
    h = (x * 73856093) ^ (y * 19349663)
    return GRASS_VARIANTS[h % len(GRASS_VARIANTS)] if h % 4 == 0 else GRASS


# ---------------------------------------------------------------- construcción
def build_camp(m: Map):
    r = CAMP
    build_room(m, r, CAMP_FLOOR, "bamboo", pz=True)
    for dy in range(PAD["h"]):
        for dx in range(PAD["w"]):
            m.floor(r.at(PAD["dx"] + dx, PAD["dy"] + dy), PAD_FLOOR)
    for pos in CAMP_SIGNS:
        if pos[1] >= r.y0:                                  # el tercer cartel va en el claro
            m.add(pos, SIGN)
    m.add(r.at(4, 0), LEVER, uid=UID_START, desc="Start a run with your group")
    m.add(r.at(7, 0), LEVER, uid=UID_RANK, desc="Weekly ranking")
    for dx in (1, 7):
        m.add(r.at(dx, 3), CAMPFIRE)
    for dx in (0, 8):
        m.add(r.at(dx, 4), BUSH)
    m.add(r.west_wall(2), TORCH_W)
    m.add(r.north_wall(1), TORCH_N)
    m.add(RETURN_TP, TELEPORT, tele=TEMPLE_LANDING)


def build_arena(m: Map):
    r = ARENA
    build_room(m, r, GRASS, "bamboo")
    for x, y, z in r.cells():
        m.floor((x, y, z), variant(x, y))
    for dy in (4, 5, 6):                                    # claro de barro al centro
        for dx in (5, 6, 7):
            m.floor(r.at(dx, dy), MUD_DARK if (dx + dy) % 3 == 0 else MUD)
    corners = (((0, 0), (1, 0), (0, 1)), ((12, 0), (11, 0), (12, 1)),
               ((0, 10), (1, 10), (0, 9)), ((12, 10), (11, 10), (12, 9)))
    for i, (tree, side, bush) in enumerate(corners):        # selva cerrando las esquinas
        m.add(r.at(*tree), TREES[i % len(TREES)])
        m.add(r.at(*side), TREES[(i + 2) % len(TREES)])
        m.add(r.at(*bush), BUSH)
    for (dx, dy), iid in zip(((3, 4), (9, 4)), STUMPS):     # cobertura
        m.add(r.at(dx, dy), iid)
    for dx, dy in ((2, 7), (10, 7)):
        m.add(r.at(dx, dy), BUSH)
    for dx, dy in ((4, 2), (8, 6), (2, 5), (10, 3), (3, 8), (9, 8)):
        m.add(r.at(dx, dy), JUNGLE_GRASS)
    for dy in (3, 7):
        m.add(r.west_wall(dy), TORCH_W)
    for dx in (3, 9):
        m.add(r.north_wall(dx), TORCH_N)
    m.add(r.at(5, 10), LEVER, uid=UID_NEXT, desc="Next wave")
    m.add(r.at(6, 10), SIGN)
    m.add(r.at(7, 10), LEVER, uid=UID_RETIRE, desc="Retire and keep your mark")


def build() -> Map:
    m = Map()
    build_camp(m)
    build_arena(m)
    return m


# ---------------------------------------------------------------- validación
def validate(c: Checker) -> list[str]:
    c.tiles()
    c.rooms([ARENA, CAMP], CLEAR_BOX)
    camp = c.connected("campamento", CAMP, LANDING)
    pts = {"TP al templo": RETURN_TP, "palanca inicio": CAMP.at(4, 0), "palanca ranking": CAMP.at(7, 0)}
    pts.update({f"plataforma +{dx},{dy}": CAMP.at(PAD["dx"] + dx, PAD["dy"] + dy)
                for dx in range(PAD["w"]) for dy in range(PAD["h"])})
    c.need("campamento", camp, pts)
    arena = c.connected("claro", ARENA, ARENA.at(*ARRIVALS[0]))
    pts = {"palanca siguiente": ARENA.at(5, 10), "palanca retirarse": ARENA.at(7, 10)}
    pts.update({f"spawn {d}": ARENA.at(*d) for d in SPAWNS})
    pts.update({f"llegada {d}": ARENA.at(*d) for d in ARRIVALS})
    c.need("claro", arena, pts)
    if len(set(SPAWNS) | set(ARRIVALS)) != len(SPAWNS) + len(ARRIVALS):
        c.errs.append("SPAWNS y ARRIVALS repiten casillas")
    if len(ARRIVALS) < PAD["w"] * PAD["h"] + 1:
        c.errs.append("ARRIVALS no alcanza para la plataforma llena + el que tira")
    return c.errs


# ---------------------------------------------------------------- wave_arena.lua
LUA_BEGIN, LUA_END = "-- BEGIN LAYOUT (generado por scripts/map/generate-wave-arena.py)", "-- END LAYOUT"


def lua_layout() -> str:
    pad = dict(x0=CAMP.x0 + PAD["dx"], y0=CAMP.y0 + PAD["dy"],
               x1=CAMP.x0 + PAD["dx"] + PAD["w"] - 1, y1=CAMP.y0 + PAD["dy"] + PAD["h"] - 1)
    return "\n".join([
        LUA_BEGIN,
        f"ARENA = {{{lua_box(ARENA.box(), Z)}}}",
        f"CAMP = {{{lua_box(CAMP.box(), Z)}}}",
        f"PAD = {{{lua_box(pad, Z)}}}",
        f"CAMP_LANDING = {lua_pos(LANDING)}",
        "-- ARRIVALS[1] = el que tira; la cantidad es el tope del grupo",
        "ARRIVALS = {" + ", ".join(lua_pos(ARENA.at(*d)) for d in ARRIVALS) + "}",
        "-- SPAWNS[1] = jefe; el resto en orden de reparto",
        "SPAWNS = {" + ", ".join(lua_pos(ARENA.at(*d)) for d in SPAWNS) + "}",
        LUA_END,
    ]) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", type=Path, default=WORLD / "test.otbm")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--png", type=Path)
    a = ap.parse_args()

    m = build()
    c = Checker(m)
    errs = validate(c)
    print(f"Wave Arena v2: {len(m.t)} casillas; campamento PZ {sum(1 for t in m.t.values() if t['pz'])}; "
          f"claro {ARENA.w}x{ARENA.h} {ARENA.box()}; grupo máx {len(ARRIVALS)}; spawns {len(SPAWNS)}")
    if a.png:
        render_png(m, a.png, Z)
        print(f"PNG {a.png}")
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs))
        return 1
    block = lua_layout()
    if a.dry_run or not a.replace:
        print("wave_arena.lua:", "al día" if patch_block(LUA, LUA_BEGIN, LUA_END, block, write=False)
              else "se actualizaría el bloque LAYOUT")
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    write_map(a.map, m, CLEAR_BOX, Z, c.stackable)
    patch_readables("<!-- BEGIN WAVE_ARENA_SIGNS -->", "<!-- END WAVE_ARENA_SIGNS -->",
                    [dict(x=p[0], y=p[1], z=p[2], text=t) for p, t in CAMP_SIGNS.items()])
    patch_block(LUA, LUA_BEGIN, LUA_END, block, write=True)
    meta = {
        "name": "generated-wave-arena", "version": 2, "tileCount": len(m.t),
        "clearBox": {"fromX": CLEAR_BOX[0], "fromY": CLEAR_BOX[1], "toX": CLEAR_BOX[2], "toY": CLEAR_BOX[3], "z": Z},
        "arena": ARENA.box(), "camp": CAMP.box(), "landing": LANDING, "returnTp": RETURN_TP,
        "templeLanding": TEMPLE_LANDING,
        "levers": {"start": [CAMP.at(4, 0), UID_START], "rank": [CAMP.at(7, 0), UID_RANK],
                   "next": [ARENA.at(5, 10), UID_NEXT], "retire": [ARENA.at(7, 10), UID_RETIRE]},
        "arrivals": [ARENA.at(*d) for d in ARRIVALS], "spawns": [ARENA.at(*d) for d in SPAWNS],
    }
    (WORLD / "generated-wave-arena.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"OK {a.map}, readables, wave_arena.lua (LAYOUT) y generated-wave-arena.json")
    print("Después: python3 scripts/map/temple-portals.py (portal del templo -> LANDING)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
