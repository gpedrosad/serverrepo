#!/usr/bin/env python3
"""El Crisol v3 — hub (PZ) + 3 arenas compactas en z0 (nov 2026).

  Hub "Sala del Crisol"   11x8, mármol, 3 plataformas de grupo contra la pared norte
  Bronce "Foso de Arena"  11x9, arena y arenisca, calaveras y sangre
  Plata "Coliseo"         11x9, piedra gris, círculo central, perros guardianes
  Oro "Trono de Fuego"    11x9, mármol negro, estrado del boss, alfombra, ríos de lava

Las tres arenas comparten forma (ARENA_W x ARENA_H): mismos puntos de llegada, spawns y
salida; solo cambia el tema. Todo se escribe en coordenadas locales de cada sala, así
mover una sala es cambiar su origen. Piezas comunes en scripts/map/roomkit.py.

Cada puerta tiene una plataforma 3x2 frente a la palanca: todos los jugadores parados en
ella (más el que tira) entran juntos, hasta len(ARRIVALS). La lógica vive en
data/actions/scripts/crucible.lua; este script reescribe ahí el bloque LAYOUT.

El portal del templo lo maneja scripts/map/temple-portals.py (destino LANDING).

Uso:
  python3 scripts/map/generate-crucible.py --dry-run [--png salida.png]
  python3 scripts/map/generate-crucible.py --replace
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roomkit import (LEVER, REPO, SIGN, TELEPORT, WORLD, Checker, Map, Room,  # noqa: E402
                     build_room, lua_box, lua_pos, patch_block, patch_readables, render_png, write_map)

LUA = REPO / "server/YurOTS/ots/data/actions/scripts/crucible.lua"

Z = 0
CLEAR_BOX = (70, 70, 195, 105)          # se borra entero (incluye la v2, más grande)
TEMPLE_LANDING = (164, 48, 7)           # llegada del portal Crisol en la plaza

# ---------------------------------------------------------------- piezas
TORCH_W, LAMP_N = 2061, 2040            # colgables: pared oeste (vertical) / pared norte (horizontal)
LAVA = 598
SKULLS, BLOOD = (5016, 5018), (1903, 1905)
# alfombra roja: filas arriba / medio / abajo; columnas oeste / centro / este (medido en test.otbm)
CARPET = ((4394, 4395, 4396), (4397, 4398, 4399), (4400, 4401, 4402))

# ---------------------------------------------------------------- disposición
HUB = Room(78, 80, 11, 8, Z)
HUB_STYLE = dict(floor=406, frame=407, walls="stone")
LANDING = HUB.at(5, 5)
RETURN_TP = HUB.at(5, 7)
INFO_SIGN, INFO_LEVER, INFO_UID = HUB.at(0, 4), HUB.at(0, 5), 7203
INFO_TEXT = "EL CRISOL\nPalanca: bosses de hoy y arenas ocupadas.\nSalida al templo: TP sur."
PADS = {   # columna izquierda de la plataforma 3x2 (filas 1-2); cartel y palanca en la fila 0
    "bronze": dict(dx=0, floor=467, uid=7200, sign="PUERTA DE BRONCE\nFoso de Arena\nRiesgo bajo. Grupo: pisen la plataforma."),
    "silver": dict(dx=4, floor=425, uid=7201, sign="PUERTA DE PLATA\nColiseo de Piedra\nRiesgo medio. Grupo: pisen la plataforma."),
    "gold": dict(dx=8, floor=415, uid=7202, sign="PUERTA DE ORO\nTrono de Fuego\nBoss diario + arma rara."),
}

ARENA_W, ARENA_H = 11, 9
ARENA_Y0 = 80
EXIT = (5, 8)
# llegada del grupo (el primero es el que tira); define el tamaño máximo del grupo
ARRIVALS = [(5, 6), (4, 6), (6, 6), (5, 5), (4, 5), (6, 5), (3, 6)]   # = plataforma 3x2 + el que tira
# SPAWNS[0] = elite/boss sobre el estrado; el resto, el pack en la mitad norte
SPAWNS = [(5, 1), (3, 2), (7, 2), (1, 1), (9, 1), (4, 3), (6, 3)]
ARENAS = {
    "bronze": dict(room=Room(93, ARENA_Y0, ARENA_W, ARENA_H, Z), name="Foso de Arena",
                   floor=231, walls="sand", pillar=1549, guard=1451, brazier=1482, banner=None),
    "silver": dict(room=Room(108, ARENA_Y0, ARENA_W, ARENA_H, Z), name="Coliseo de Piedra",
                   floor=424, walls="stone", pillar=1515, guard=1450, brazier=1482, banner=1870),
    "gold": dict(room=Room(123, ARENA_Y0, ARENA_W, ARENA_H, Z), name="Trono de Fuego",
                 floor=407, walls="brick", pillar=None, guard=1551, brazier=1486, banner=1812),
}


# ---------------------------------------------------------------- construcción
def carpet(m: Map, r: Room, cx: int, ya: int, yb: int):
    """Alfombra de 3 de ancho centrada en cx, de la fila ya a la yb (locales)."""
    for y in range(ya, yb + 1):
        row = CARPET[0] if y == ya else CARPET[2] if y == yb else CARPET[1]
        for dx, cid in zip((-1, 0, 1), row):
            m.add(r.at(cx + dx, y), cid)


def build_hub(m: Map):
    r, s = HUB, HUB_STYLE
    build_room(m, r, s["floor"], s["walls"], pz=True)
    for x, y, z in r.cells():                               # marco de mármol negro
        if x in (r.x0, r.x1) or y in (r.y0, r.y1):
            m.floor((x, y, z), s["frame"])
    for p in PADS.values():
        for dy in (1, 2):
            for dx in range(3):
                m.floor(r.at(p["dx"] + dx, dy), p["floor"])
        m.add(r.at(p["dx"], 0), SIGN)
        m.add(r.at(p["dx"] + 1, 0), LEVER, uid=p["uid"])
        m.add(r.north_wall(p["dx"] + 1), LAMP_N)
    for dx in (3, 7):
        m.add(r.at(dx, 0), 1515)                            # columnas entre plataformas
    carpet(m, r, 5, 3, 6)
    m.add(INFO_SIGN, SIGN)
    m.add(INFO_LEVER, LEVER, uid=INFO_UID)
    m.add(r.west_wall(2), TORCH_W)
    m.add(r.west_wall(6), TORCH_W)
    m.add(r.at(10, 4), 1448)                                # ángel frente al cartel de info
    for dx in (0, 10):
        m.add(r.at(dx, 7), 1486)                            # braseros junto a la salida
    m.add(RETURN_TP, TELEPORT, tele=TEMPLE_LANDING)


def build_arena(m: Map, key: str):
    a = ARENAS[key]
    r: Room = a["room"]
    build_room(m, r, a["floor"], a["walls"])
    m.add(r.at(*EXIT), TELEPORT, tele=LANDING)
    for dx in (4, 6):
        m.add(r.at(dx, 8), a["guard"])                      # guardianes a los lados de la salida
    for dx, dy in ((0, 0), (10, 0), (0, 8), (10, 8)):
        m.add(r.at(dx, dy), a["brazier"])
    for dy in (2, 6):
        m.add(r.west_wall(dy), TORCH_W)
    for dx in (2, 8):
        m.add(r.north_wall(dx), a["banner"] or LAMP_N)
    m.add(r.north_wall(5), LAMP_N)
    if a["pillar"]:
        for dx in (2, 8):
            m.add(r.at(dx, 4), a["pillar"])

    if key == "bronze":
        for (dx, dy), iid in zip(((2, 1), (8, 3), (1, 6), (9, 6)), SKULLS + SKULLS):
            m.add(r.at(dx, dy), iid)
        for (dx, dy), iid in zip(((6, 2), (3, 4), (7, 5)), BLOOD + BLOOD[:1]):
            m.add(r.at(dx, dy), iid)
    elif key == "silver":
        for dy in (2, 3, 4):                                # círculo central de baldosa enmarcada
            for dx in (4, 5, 6):
                m.floor(r.at(dx, dy), 426)
    elif key == "gold":
        for dy in (0, 1):                                   # estrado dorado del boss
            for dx in (4, 5, 6):
                m.floor(r.at(dx, dy), 415)
        carpet(m, r, 5, 2, 7)
        for dx in (3, 7):
            m.add(r.at(dx, 0), 1551)                        # obeliscos junto al estrado
        for dx in (0, 1, 9, 10):                            # ríos de lava a los costados
            for dy in (3, 4):
                m.floor(r.at(dx, dy), LAVA)


def build() -> Map:
    m = Map()
    build_hub(m)
    for key in ARENAS:
        build_arena(m, key)
    return m


# ---------------------------------------------------------------- validación
def validate(c: Checker) -> list[str]:
    c.tiles()
    c.rooms([HUB] + [a["room"] for a in ARENAS.values()], CLEAR_BOX)
    hub = c.reach(LANDING, HUB)
    must = {"llegada": LANDING, "TP al templo": RETURN_TP, "palanca info": INFO_LEVER}
    for key, p in PADS.items():
        must[f"palanca {key}"] = HUB.at(p["dx"] + 1, 0)
        for dy in (1, 2):
            for dx in range(3):
                must[f"plataforma {key} +{dx},{dy}"] = HUB.at(p["dx"] + dx, dy)
    c.need("hub", hub, must)
    for key, a in ARENAS.items():
        r = a["room"]
        seen = c.connected(key, r, r.at(*ARRIVALS[0]))
        pts = {"salida": r.at(*EXIT)}
        pts.update({f"spawn {d}": r.at(*d) for d in SPAWNS})
        pts.update({f"llegada {d}": r.at(*d) for d in ARRIVALS})
        c.need(key, seen, pts)
    if EXIT in SPAWNS + ARRIVALS or len(set(SPAWNS) | set(ARRIVALS)) != len(SPAWNS) + len(ARRIVALS):
        c.errs.append("SPAWNS, ARRIVALS y EXIT repiten casillas")
    return c.errs


# ---------------------------------------------------------------- crucible.lua
LUA_BEGIN, LUA_END = "-- BEGIN LAYOUT (generado por scripts/map/generate-crucible.py)", "-- END LAYOUT"


def lua_layout(meta: dict) -> str:
    out = [LUA_BEGIN,
           f"HUB = {{{lua_box(meta['hub'], Z)}}}",
           "PADS = {"]
    out += [f"\t{k} = {{{lua_box(p, Z)}}}," for k, p in meta["pads"].items()]
    out += ["}", "ARENAS = {"]
    for k, a in meta["arenas"].items():
        out += [f"\t{k} = {{",
                f"\t\tname = \"{a['name']}\", {lua_box(a, Z)},",
                "\t\t-- arrivals[1] = el que tira; la cantidad es el tope del grupo",
                "\t\tarrivals = {" + ", ".join(lua_pos(p) for p in a["arrivals"]) + "},",
                "\t\t-- spawns[1] = elite/boss; el resto, pack",
                "\t\tspawns = {" + ", ".join(lua_pos(p) for p in a["spawns"]) + "},",
                "\t},"]
    out += ["}", LUA_END]
    return "\n".join(out) + "\n"


def metadata(m: Map) -> dict:
    def pts(r: Room, local):
        return [r.at(*d) for d in local]

    return {
        "name": "generated-crucible", "version": 3, "tileCount": len(m.t),
        "clearBox": {"fromX": CLEAR_BOX[0], "fromY": CLEAR_BOX[1], "toX": CLEAR_BOX[2], "toY": CLEAR_BOX[3], "z": Z},
        "landing": LANDING, "returnTp": RETURN_TP, "templeLanding": TEMPLE_LANDING,
        "hub": HUB.box(),
        "pads": {k: dict(x0=HUB.x0 + p["dx"], y0=HUB.y0 + 1, x1=HUB.x0 + p["dx"] + 2, y1=HUB.y0 + 2,
                         lever=HUB.at(p["dx"] + 1, 0), uid=p["uid"]) for k, p in PADS.items()},
        "info": {"lever": INFO_LEVER, "uid": INFO_UID},
        "arenas": {k: {**a["room"].box(), "z": Z, "name": a["name"], "exit": a["room"].at(*EXIT),
                       "arrivals": pts(a["room"], ARRIVALS), "spawns": pts(a["room"], SPAWNS)}
                   for k, a in ARENAS.items()},
        "signs": [{"x": HUB.x0 + p["dx"], "y": HUB.y0, "text": p["sign"]} for p in PADS.values()]
                 + [{"x": INFO_SIGN[0], "y": INFO_SIGN[1], "text": INFO_TEXT}],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", type=Path, default=WORLD / "test.otbm")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--png", type=Path)
    a = ap.parse_args()

    m = build()
    meta = metadata(m)
    c = Checker(m)
    errs = validate(c)
    print(f"El Crisol v3: {len(m.t)} casillas; hub PZ {sum(1 for t in m.t.values() if t['pz'])}; "
          f"grupo máx {len(ARRIVALS)}")
    for k, ar in meta["arenas"].items():
        print(f"  {k:6s} {ar['name']:18s} caja {ar['x0']},{ar['y0']}-{ar['x1']},{ar['y1']} salida {ar['exit']}")
    if a.png:
        render_png(m, a.png, Z)
        print(f"PNG {a.png}")
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs))
        return 1
    block = lua_layout(meta)
    if a.dry_run or not a.replace:
        print("crucible.lua:", "al día" if patch_block(LUA, LUA_BEGIN, LUA_END, block, write=False)
              else "se actualizaría el bloque LAYOUT")
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    write_map(a.map, m, CLEAR_BOX, Z, c.stackable)
    patch_readables("<!-- BEGIN CRUCIBLE_SIGNS -->", "<!-- END CRUCIBLE_SIGNS -->",
                    [dict(s, z=Z) for s in meta["signs"]])
    patch_block(LUA, LUA_BEGIN, LUA_END, block, write=True)
    (WORLD / "generated-crucible.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"OK {a.map}, readables, crucible.lua (LAYOUT) y generated-crucible.json")
    print("Después: python3 scripts/map/temple-portals.py (portal del templo -> LANDING)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
