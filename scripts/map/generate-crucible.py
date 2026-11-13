#!/usr/bin/env python3
"""El Crisol v3 — hub (PZ) + 3 arenas compactas en z0 (nov 2026).

  Hub "Sala del Crisol"   11x8, mármol, 3 plataformas de grupo contra la pared norte
  Bronce "Foso de Arena"  11x9, arena y arenisca, calaveras y sangre
  Plata "Coliseo"         11x9, piedra gris, círculo central, perros guardianes
  Oro "Trono de Fuego"    11x9, mármol negro, estrado del boss, alfombra, ríos de lava

Las tres arenas comparten forma (ARENA_W x ARENA_H): mismos puntos de llegada, spawns y
salida; solo cambia el tema. Todo se escribe en coordenadas locales de cada sala, así
mover una sala es cambiar su origen.

Cada puerta tiene una plataforma 3x2 frente a la palanca: todos los jugadores parados en
ella (más el que tira) entran juntos, hasta len(ARRIVALS). La lógica vive en
data/actions/scripts/crucible.lua; este script reescribe ahí el bloque LAYOUT.

La validación usa los flags reales del .otb (block_solid, stackable): sin listas a mano.
El portal del templo lo maneja scripts/map/temple-portals.py (destino LANDING).

Uso:
  python3 scripts/map/generate-crucible.py --dry-run [--png salida.png]
  python3 scripts/map/generate-crucible.py --replace
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("generate_maze", HERE / "generate-maze.py")
_maze = importlib.util.module_from_spec(_spec)
sys.modules["generate_maze"] = _maze
_spec.loader.exec_module(_maze)
sys.path.insert(0, str(HERE / "kb"))
from mapdata import load_otb  # noqa: E402

REPO = HERE.parents[1]
WORLD = REPO / "server/YurOTS/ots/data/world"
LUA = REPO / "server/YurOTS/ots/data/actions/scripts/crucible.lua"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"

Z = 0
CLEAR_BOX = (70, 70, 195, 105)          # se borra entero (incluye la v2, más grande)
TEMPLE_LANDING = (164, 48, 7)           # llegada del portal Crisol en la plaza

NODE_START, NODE_END = _maze.NODE_START, _maze.NODE_END
OTBM_TILE_AREA, OTBM_TILE, OTBM_ITEM = _maze.OTBM_TILE_AREA, _maze.OTBM_TILE, _maze.OTBM_ITEM
ATTR_TILE_FLAGS, ATTR_UID, ATTR_TELE, ATTR_ITEM = 3, 5, 8, 9
TILE_PZ = 1

# ---------------------------------------------------------------- piezas
TELEPORT, LEVER, SIGN = 1387, 1945, 1429
TORCH_W, LAMP_N = 2061, 2040            # colgables: pared oeste (vertical) / pared norte (horizontal)
LAVA = 598
SKULLS, BLOOD = (5016, 5018), (1903, 1905)
# alfombra roja: filas arriba / medio / abajo; columnas oeste / centro / este (medido en test.otbm)
CARPET = ((4394, 4395, 4396), (4397, 4398, 4399), (4400, 4401, 4402))
# poste NO, horizontal (N, S y esquina NE), vertical (O, E y esquina SO), L (esquina SE)
WALLS = {
    "stone": dict(post=1051, h=1050, v=1049, se=1053),
    "sand": dict(post=1062, h=1063, v=1060, se=1066),
    "brick": dict(post=1027, h=1028, v=1030, se=1033),
}


class Room:
    """Caja interior w x h con origen (x0, y0); el anillo de paredes va por fuera."""

    def __init__(self, x0: int, y0: int, w: int, h: int):
        self.x0, self.y0, self.w, self.h = x0, y0, w, h
        self.x1, self.y1 = x0 + w - 1, y0 + h - 1

    def at(self, dx: int, dy: int) -> tuple[int, int, int]:
        assert 0 <= dx < self.w and 0 <= dy < self.h, f"({dx},{dy}) fuera de la sala {self.w}x{self.h}"
        return (self.x0 + dx, self.y0 + dy, Z)

    def box(self) -> dict:
        return dict(x0=self.x0, y0=self.y0, x1=self.x1, y1=self.y1)

    def cells(self):
        return [(x, y) for y in range(self.y0, self.y1 + 1) for x in range(self.x0, self.x1 + 1)]


# ---------------------------------------------------------------- disposición
HUB = Room(78, 80, 11, 8)
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
    "bronze": dict(room=Room(93, ARENA_Y0, ARENA_W, ARENA_H), name="Foso de Arena",
                   floor=231, walls="sand", pillar=1549, guard=1451, brazier=1482, banner=None),
    "silver": dict(room=Room(108, ARENA_Y0, ARENA_W, ARENA_H), name="Coliseo de Piedra",
                   floor=424, walls="stone", pillar=1515, guard=1450, brazier=1482, banner=1870),
    "gold": dict(room=Room(123, ARENA_Y0, ARENA_W, ARENA_H), name="Trono de Fuego",
                 floor=407, walls="brick", pillar=None, guard=1551, brazier=1486, banner=1812),
}


# ---------------------------------------------------------------- construcción
class Map:
    def __init__(self):
        self.t: dict[tuple[int, int, int], dict] = {}

    def ground(self, pos, g, pz=False):
        self.t[pos] = {"ground": g, "items": [], "pz": pz}

    def floor(self, pos, g):
        self.t[pos]["ground"] = g

    def add(self, pos, iid, **kw):
        assert pos in self.t, f"item {iid} en {pos}: casilla sin suelo"
        self.t[pos]["items"].append({"id": iid, **kw})


def build_room(m: Map, r: Room, floor: int, walls: str, pz=False):
    W = WALLS[walls]
    for y in range(r.y0 - 1, r.y1 + 2):
        for x in range(r.x0 - 1, r.x1 + 2):
            m.ground((x, y, Z), floor, pz)
    for x in range(r.x0, r.x1 + 1):
        m.add((x, r.y0 - 1, Z), W["h"])
        m.add((x, r.y1 + 1, Z), W["h"])
    for y in range(r.y0, r.y1 + 1):
        m.add((r.x0 - 1, y, Z), W["v"])
        m.add((r.x1 + 1, y, Z), W["v"])
    m.add((r.x0 - 1, r.y0 - 1, Z), W["post"])
    m.add((r.x1 + 1, r.y0 - 1, Z), W["h"])
    m.add((r.x0 - 1, r.y1 + 1, Z), W["v"])
    m.add((r.x1 + 1, r.y1 + 1, Z), W["se"])


def north_wall(r: Room, dx: int):
    return (r.x0 + dx, r.y0 - 1, Z)


def west_wall(r: Room, dy: int):
    return (r.x0 - 1, r.y0 + dy, Z)


def carpet(m: Map, r: Room, cx: int, ya: int, yb: int):
    """Alfombra de 3 de ancho centrada en cx, de la fila ya a la yb (locales)."""
    for y in range(ya, yb + 1):
        row = CARPET[0] if y == ya else CARPET[2] if y == yb else CARPET[1]
        for dx, cid in zip((-1, 0, 1), row):
            m.add(r.at(cx + dx, y), cid)


def build_hub(m: Map):
    r, s = HUB, HUB_STYLE
    build_room(m, r, s["floor"], s["walls"], pz=True)
    for x, y in r.cells():                                  # marco de mármol negro
        if x in (r.x0, r.x1) or y in (r.y0, r.y1):
            m.floor((x, y, Z), s["frame"])
    for p in PADS.values():
        for dy in (1, 2):
            for dx in range(3):
                m.floor(r.at(p["dx"] + dx, dy), p["floor"])
        m.add(r.at(p["dx"], 0), SIGN)
        m.add(r.at(p["dx"] + 1, 0), LEVER, uid=p["uid"])
        m.add(north_wall(r, p["dx"] + 1), LAMP_N)
    for dx in (3, 7):
        m.add(r.at(dx, 0), 1515)                            # columnas entre plataformas
    carpet(m, r, 5, 3, 6)
    m.add(INFO_SIGN, SIGN)
    m.add(INFO_LEVER, LEVER, uid=INFO_UID)
    m.add(west_wall(r, 2), TORCH_W)
    m.add(west_wall(r, 6), TORCH_W)
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
        m.add(west_wall(r, dy), TORCH_W)
    for dx in (2, 8):
        m.add(north_wall(r, dx), a["banner"] or LAMP_N)
    m.add(north_wall(r, 5), LAMP_N)
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
def validate(m: Map, otb: dict) -> list[str]:
    errs = []
    solid = {sid for sid, rec in otb.items() if "block_solid" in rec["flags"]}
    wall_ids = {v for w in WALLS.values() for v in w.values()}

    for k in [HUB] + [a["room"] for a in ARENAS.values()]:
        if not (CLEAR_BOX[0] < k.x0 - 1 and k.x1 + 1 < CLEAR_BOX[2] and CLEAR_BOX[1] < k.y0 - 1 and k.y1 + 1 < CLEAR_BOX[3]):
            errs.append(f"sala {k.box()} fuera de CLEAR_BOX")
    rooms = [HUB] + [a["room"] for a in ARENAS.values()]
    for i, p in enumerate(rooms):
        for q in rooms[i + 1:]:
            if p.x0 - 1 <= q.x1 + 1 and q.x0 - 1 <= p.x1 + 1 and p.y0 - 1 <= q.y1 + 1 and q.y0 - 1 <= p.y1 + 1:
                errs.append(f"salas {p.box()} y {q.box()} se pisan")

    for pos, t in m.t.items():
        ids = [i["id"] for i in t["items"]]
        unknown = [i for i in ids + [t["ground"]] if i not in otb]
        if unknown:
            errs.append(f"{pos}: ids que no están en el .otb {unknown}")
        if len([i for i in ids if i in solid and i not in wall_ids]) > 1:
            errs.append(f"{pos}: dos piezas sólidas en la misma casilla {ids}")

    def walkable(pos):
        t = m.t.get(pos)
        return bool(t) and t["ground"] not in solid and not any(i["id"] in solid for i in t["items"])

    def reach(start, r: Room):
        seen, todo = {start}, [start]
        while todo:
            x, y, z = todo.pop()
            for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z)):
                if n not in seen and r.x0 <= n[0] <= r.x1 and r.y0 <= n[1] <= r.y1 and walkable(n):
                    seen.add(n)
                    todo.append(n)
        return seen

    hub = reach(LANDING, HUB)
    must = {"llegada": LANDING, "TP al templo": RETURN_TP, "palanca info": INFO_LEVER}
    for key, p in PADS.items():
        must[f"palanca {key}"] = HUB.at(p["dx"] + 1, 0)
        for dy in (1, 2):
            for dx in range(3):
                must[f"plataforma {key} +{dx},{dy}"] = HUB.at(p["dx"] + dx, dy)
    errs += [f"hub: {what} {pos} inaccesible" for what, pos in must.items() if pos not in hub]

    for key, a in ARENAS.items():
        r = a["room"]
        seen = reach(r.at(*ARRIVALS[0]), r)
        free = sum(1 for x, y in r.cells() if walkable((x, y, Z)))
        if len(seen) != free:
            errs.append(f"{key}: {free - len(seen)} casillas libres aisladas")
        if r.at(*EXIT) not in seen:
            errs.append(f"{key}: salida inaccesible")
        for what, pts in (("spawn", SPAWNS), ("llegada", ARRIVALS)):
            for d in pts:
                if r.at(*d) not in seen or r.at(*d) == r.at(*EXIT):
                    errs.append(f"{key}: {what} {d} no pisable")
    if len(set(SPAWNS) | set(ARRIVALS)) != len(SPAWNS) + len(ARRIVALS):
        errs.append("SPAWNS y ARRIVALS repiten casillas")
    return errs


# ---------------------------------------------------------------- crucible.lua / readables
LUA_BEGIN, LUA_END = "-- BEGIN LAYOUT (generado por scripts/map/generate-crucible.py)", "-- END LAYOUT"


def lua_pos(p) -> str:
    return f"{{x = {p[0]}, y = {p[1]}, z = {p[2]}}}"


def lua_box(b: dict) -> str:
    return f"x0 = {b['x0']}, y0 = {b['y0']}, x1 = {b['x1']}, y1 = {b['y1']}, z = {Z}"


def lua_layout(meta: dict) -> str:
    out = [LUA_BEGIN,
           f"HUB = {{{lua_box(meta['hub'])}}}",
           "PADS = {"]
    out += [f"\t{k} = {{{lua_box(p)}}}," for k, p in meta["pads"].items()]
    out += ["}", "ARENAS = {"]
    for k, a in meta["arenas"].items():
        out += [f"\t{k} = {{",
                f"\t\tname = \"{a['name']}\", {lua_box(a)},",
                "\t\t-- arrivals[1] = el que tira; la cantidad es el tope del grupo",
                "\t\tarrivals = {" + ", ".join(lua_pos(p) for p in a["arrivals"]) + "},",
                "\t\t-- spawns[1] = elite/boss; el resto, pack",
                "\t\tspawns = {" + ", ".join(lua_pos(p) for p in a["spawns"]) + "},",
                "\t},"]
    out += ["}", LUA_END]
    return "\n".join(out) + "\n"


def patch_lua(meta: dict, write: bool) -> bool:
    """Devuelve True si crucible.lua ya tenía este bloque."""
    src = LUA.read_text(encoding="utf-8")
    pat = re.compile(re.escape(LUA_BEGIN) + r".*?" + re.escape(LUA_END) + r"\n", re.DOTALL)
    if not pat.search(src):
        raise SystemExit(f"ERROR: {LUA} no tiene el bloque {LUA_BEGIN!r}")
    new = pat.sub(lambda _m: lua_layout(meta), src, count=1)
    if write and new != src:
        LUA.write_text(new, encoding="utf-8")
    return new == src


def patch_readables(meta: dict):
    begin, end = "<!-- BEGIN CRUCIBLE_SIGNS -->", "<!-- END CRUCIBLE_SIGNS -->"
    lines = [f"\t{begin}"]
    for s in meta["signs"]:
        text = s["text"].replace("\n", "\\n")
        lines.append(f'\t<readable x="{s["x"]}" y="{s["y"]}" z="{Z}" text="{text}"/>')
    lines.append(f"\t{end}")
    block = "\n".join(lines) + "\n"
    raw = READABLES.read_text(encoding="utf-8")
    pat = re.compile(r"[ \t]*" + re.escape(begin) + r".*?" + re.escape(end) + r"\n?", re.DOTALL)
    raw = pat.sub(lambda _m: block, raw, count=1) if pat.search(raw) else raw.replace("</readables>", block + "</readables>")
    READABLES.write_text(raw, encoding="utf-8")


# ---------------------------------------------------------------- OTBM
def item_node(it: dict, stackable: set[int]) -> bytes:
    props = struct.pack("<H", it["id"])
    if it["id"] in stackable:                     # el server exige el byte de cantidad
        props += b"\x01"
    if it.get("uid"):
        props += struct.pack("<BH", ATTR_UID, it["uid"])
    if it.get("tele"):
        props += struct.pack("<BHHB", ATTR_TELE, *it["tele"])
    buf = bytearray([NODE_START, OTBM_ITEM])
    _maze.write_props(buf, props)
    buf.append(NODE_END)
    return bytes(buf)


def tile_node(ox: int, oy: int, t: dict, stackable: set[int]) -> bytes:
    props = struct.pack("<BB", ox, oy)
    if t["pz"]:
        props += struct.pack("<BI", ATTR_TILE_FLAGS, TILE_PZ)
    props += struct.pack("<BH", ATTR_ITEM, t["ground"])
    buf = bytearray([NODE_START, OTBM_TILE])
    _maze.write_props(buf, props)
    for it in t["items"]:
        buf.extend(item_node(it, stackable))
    buf.append(NODE_END)
    return bytes(buf)


def areas(m: Map, stackable: set[int]) -> bytes:
    buckets = defaultdict(list)
    for (x, y, z), t in m.t.items():
        buckets[(x & ~0xFF, y & ~0xFF, z)].append((x & 0xFF, y & 0xFF, t))
    out = bytearray()
    for (bx, by, bz), rel in sorted(buckets.items()):
        out += bytes([NODE_START, OTBM_TILE_AREA])
        head = bytearray()
        _maze.write_props(head, struct.pack("<HHB", bx, by, bz))
        out += head
        for ox, oy, t in sorted(rel, key=lambda r: (r[0], r[1])):
            out += tile_node(ox, oy, t, stackable)
        out.append(NODE_END)
    return bytes(out)


def render_png(m: Map, path: Path):
    from mapdata import Renderer, png_bytes
    tiles = {k: [t["ground"]] + [i["id"] for i in t["items"]] for k, t in m.t.items()}
    xs = [k[0] for k in tiles]
    ys = [k[1] for k in tiles]
    w, h, rgba = Renderer().area(tiles, min(xs) - 1, min(ys) - 1, max(xs) + 2, max(ys) + 2, Z)
    path.write_bytes(png_bytes(w, h, rgba))


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

    otb = load_otb()
    stackable = {sid for sid, rec in otb.items() if "stackable" in rec["flags"]}
    m = build()
    meta = metadata(m)
    errs = validate(m, otb)
    print(f"El Crisol v3: {len(m.t)} casillas; hub PZ {sum(1 for t in m.t.values() if t['pz'])}; "
          f"grupo máx {len(ARRIVALS)}")
    for k, ar in meta["arenas"].items():
        print(f"  {k:6s} {ar['name']:18s} caja {ar['x0']},{ar['y0']}-{ar['x1']},{ar['y1']} salida {ar['exit']}")
    if a.png:
        render_png(m, a.png)
        print(f"PNG {a.png}")
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs))
        return 1
    if a.dry_run or not a.replace:
        print("crucible.lua:", "al día" if patch_lua(meta, write=False) else "se actualizaría el bloque LAYOUT")
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    raw = a.map.read_bytes()
    body = _maze.filter_tiles_in_bbox(raw[4:], CLEAR_BOX[0], CLEAR_BOX[1], CLEAR_BOX[2], CLEAR_BOX[3], Z)
    at = _maze.find_map_data_insert(body)
    a.map.write_bytes(raw[:4] + body[:at] + areas(m, stackable) + body[at:])
    patch_readables(meta)
    patch_lua(meta, write=True)
    (WORLD / "generated-crucible.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"OK {a.map}, readables, crucible.lua (LAYOUT) y generated-crucible.json")
    print("Después: python3 scripts/map/temple-portals.py (portal del templo -> LANDING)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
