#!/usr/bin/env python3
"""El Crisol v2 — hub (PZ) + 3 arenas temáticas en z0 (nov 2026).

  Hub "Sala del Crisol"   mármol, alfombra roja, columnas, 3 plataformas de grupo
  Bronce "Foso de Arena"  arena + paredes de arenisca, columnas y escombros como cobertura
  Plata "Coliseo"         piedra gris, columnas, estatuas de perro en la salida
  Oro "Trono de Fuego"    mármol negro, pozos de lava, alfombra al trono, obeliscos dorados

Cada puerta tiene una plataforma 3x2 frente a la palanca: todos los jugadores parados en
ella (más el que tira) entran juntos. Llegada al sur de la arena, monstruos en la mitad
norte, TP de salida al sur. La lógica vive en data/actions/scripts/crucible.lua; este
script reescribe ahí el bloque LAYOUT (coordenadas) para que nunca se desincronicen.

Paredes según el patrón medido en test.otbm (kb/wall_sets + vecinos):
  esquina NO = poste, NE = horizontal, SO = vertical, SE = esquina en L.

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
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("generate_maze", HERE / "generate-maze.py")
_maze = importlib.util.module_from_spec(_spec)
sys.modules["generate_maze"] = _maze
_spec.loader.exec_module(_maze)

REPO = HERE.parents[1]
WORLD = REPO / "server/YurOTS/ots/data/world"
LUA = REPO / "server/YurOTS/ots/data/actions/scripts/crucible.lua"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"

Z = 0
CLEAR_BOX = (70, 70, 195, 105)          # todo el Crisol (z0 no tiene otra cosa)
TEMPLE_LANDING = (164, 48, 7)           # llegada del portal Crisol en la plaza

NODE_START, NODE_END = _maze.NODE_START, _maze.NODE_END
OTBM_TILE_AREA, OTBM_TILE, OTBM_ITEM = _maze.OTBM_TILE_AREA, _maze.OTBM_TILE, _maze.OTBM_ITEM
ATTR_TILE_FLAGS, ATTR_UID, ATTR_TEXT, ATTR_TELE, ATTR_ITEM = 3, 5, 6, 8, 9
# Items apilables según items-zagan-test.otb: el server exige su byte de cantidad o no carga el mapa
# (ver scripts/map/check-map-load.py). 2320 = calavera.
NEEDS_COUNT = {2320}
TILE_PZ = 1

TELEPORT, LEVER, SIGN = 1387, 1945, 1429
# alfombra roja (patrón medido en test.otbm): filas arriba / medio / abajo, columnas oeste / centro / este
CARPET = ((4394, 4395, 4396),
          (4397, 4398, 4399),
          (4400, 4401, 4402))
TORCH_V, LAMP_H = 2061, 2040            # colgables: en pared vertical (oeste) / horizontal (norte)

# poste NO, horizontal, vertical, L SE
WALLS = {
    "stone": dict(post=1051, h=1050, v=1049, se=1053),
    "sand": dict(post=1062, h=1063, v=1060, se=1066),
    "brick": dict(post=1027, h=1028, v=1030, se=1033),
}

# ---------------------------------------------------------------- disposición
HUB = dict(x0=76, y0=79, x1=94, y1=95, floor=406, frame=407, walls="stone")
LANDING = (85, 92, Z)
RETURN_TP = (85, 95, Z)
PADS = {   # plataforma 3x2 (x0, y0) y suelo; palanca al norte del centro, cartel al norte-oeste
    "bronze": dict(x0=78, y0=80, floor=467, uid=7200, sign="PUERTA DE BRONCE\nFoso de Arena\nRiesgo bajo. Grupo: pisen la plataforma."),
    "silver": dict(x0=84, y0=80, floor=425, uid=7201, sign="PUERTA DE PLATA\nColiseo de Piedra\nRiesgo medio. Grupo: pisen la plataforma."),
    "gold": dict(x0=90, y0=80, floor=415, uid=7202, sign="PUERTA DE ORO\nTrono de Fuego\nBoss diario + arma rara."),
}
INFO_LEVER, INFO_SIGN, INFO_UID = (77, 88, Z), (77, 87, Z), 7203
INFO_TEXT = "EL CRISOL\nPalanca: bosses de hoy y arenas ocupadas.\nSalida al templo: TP sur."

ARENAS = {
    "bronze": dict(x0=104, y0=80, x1=118, y1=92, floor=231, walls="sand", name="Foso de Arena"),
    "silver": dict(x0=128, y0=79, x1=144, y1=93, floor=424, walls="stone", name="Coliseo de Piedra"),
    "gold": dict(x0=154, y0=78, x1=172, y1=94, floor=407, walls="brick", name="Trono de Fuego"),
}


def arena_points(a: dict) -> dict:
    cx = (a["x0"] + a["x1"]) // 2
    return {"cx": cx, "exit": (cx, a["y1"], Z), "entry": (cx, a["y1"] - 2, Z)}


def spawn_spots(a: dict) -> list[tuple[int, int, int]]:
    """Elite arriba al centro; el pack repartido en la mitad norte (lejos de la llegada)."""
    cx, y0, x0, x1 = arena_points(a)["cx"], a["y0"], a["x0"], a["x1"]
    w = x1 - x0
    return [(cx, y0 + 2, Z),
            (x0 + w // 4, y0 + 3, Z), (x1 - w // 4, y0 + 3, Z),
            (cx - 2, y0 + 5, Z), (cx + 2, y0 + 5, Z),
            (x0 + 2, y0 + 6, Z), (x1 - 2, y0 + 6, Z)]


# ---------------------------------------------------------------- construcción
class Map:
    def __init__(self):
        self.t: dict[tuple[int, int, int], dict] = {}

    def ground(self, x, y, g, pz=False):
        self.t[(x, y, Z)] = {"ground": g, "items": [], "pz": pz}

    def add(self, x, y, iid, **kw):
        self.t[(x, y, Z)]["items"].append({"id": iid, **kw})

    def items(self, x, y):
        return [i["id"] for i in self.t[(x, y, Z)]["items"]]


def room(m: Map, box: dict, floor: int, walls: str, pz=False):
    W = WALLS[walls]
    x0, y0, x1, y1 = box["x0"], box["y0"], box["x1"], box["y1"]
    for y in range(y0 - 1, y1 + 2):
        for x in range(x0 - 1, x1 + 2):
            m.ground(x, y, floor, pz)
    for x in range(x0, x1 + 1):
        m.add(x, y0 - 1, W["h"])
        m.add(x, y1 + 1, W["h"])
    for y in range(y0, y1 + 1):
        m.add(x0 - 1, y, W["v"])
        m.add(x1 + 1, y, W["v"])
    m.add(x0 - 1, y0 - 1, W["post"])
    m.add(x1 + 1, y0 - 1, W["h"])
    m.add(x0 - 1, y1 + 1, W["v"])
    m.add(x1 + 1, y1 + 1, W["se"])


def carpet(m: Map, xc: int, ya: int, yb: int):
    """Alfombra de 3 de ancho de ya a yb, con flecos y esquinas en las puntas."""
    for y in range(ya, yb + 1):
        row = CARPET[0] if y == ya else CARPET[2] if y == yb else CARPET[1]
        for dx, cid in zip((-1, 0, 1), row):
            m.add(xc + dx, y, cid)


def build_hub(m: Map):
    h = HUB
    room(m, h, h["floor"], h["walls"], pz=True)
    # marco de mármol negro por dentro de la pared
    for y in range(h["y0"], h["y1"] + 1):
        for x in range(h["x0"], h["x1"] + 1):
            if x in (h["x0"], h["x1"]) or y in (h["y0"], h["y1"]):
                m.t[(x, y, Z)]["ground"] = h["frame"]
    for key, p in PADS.items():
        for y in range(p["y0"], p["y0"] + 2):
            for x in range(p["x0"], p["x0"] + 3):
                m.t[(x, y, Z)]["ground"] = p["floor"]
        cx = p["x0"] + 1
        m.add(cx, h["y0"], LEVER, uid=p["uid"])
        m.add(p["x0"], h["y0"], SIGN)
        m.add(cx, h["y0"] - 1, LAMP_H)               # farol en la pared norte, sobre la palanca
    carpet(m, LANDING[0], PADS["silver"]["y0"] + 2, RETURN_TP[1] - 1)
    for x, y in ((81, 84), (81, 90), (89, 84), (89, 90)):
        m.add(x, y, 1515)                             # columnas de mármol
    for x, y in ((h["x0"] + 1, h["y1"] - 1), (h["x1"] - 1, h["y1"] - 1)):
        m.add(x, y, 1482)                             # braseros junto a la salida
    m.add(h["x1"] - 1, 87, 1448)                      # estatua de ángel frente al cartel info
    for y in (84, 91):
        m.add(h["x0"] - 1, y, TORCH_V)
    m.add(*INFO_LEVER[:2], LEVER, uid=INFO_UID)
    m.add(*INFO_SIGN[:2], SIGN)
    m.add(*RETURN_TP[:2], TELEPORT, tele=TEMPLE_LANDING)


def arena_common(m: Map, key: str):
    a = ARENAS[key]
    room(m, a, a["floor"], a["walls"])
    pts = arena_points(a)
    m.add(*pts["exit"][:2], TELEPORT, tele=LANDING)
    for y in range(a["y0"] + 3, a["y1"] - 1, 5):
        m.add(a["x0"] - 1, y, TORCH_V)
    for x in range(a["x0"] + 3, a["x1"] - 1, 6):
        m.add(x, a["y0"] - 1, LAMP_H)
    for x, y in ((a["x0"], a["y0"]), (a["x1"], a["y0"]), (a["x0"], a["y1"]), (a["x1"], a["y1"])):
        m.add(x, y, 1482)                             # braseros en las 4 esquinas
    return a, pts


def build_bronze(m: Map):
    a, p = arena_common(m, "bronze")
    cx = p["cx"]
    for dx, dy in ((-4, 4), (4, 4), (-4, 8), (4, 8)):
        m.add(cx + dx, a["y0"] + dy, 1549)            # columnas de arenisca (cobertura)
    for x, y in ((a["x0"] + 1, a["y0"] + 5), (a["x1"] - 1, a["y0"] + 9)):
        m.add(x, y, 1323)                             # escombros
    for x, y in ((cx - 1, a["y0"] + 6), (cx + 3, a["y0"] + 2), (a["x0"] + 3, a["y1"] - 2)):
        m.add(x, y, 2320)                             # calaveras (pisables)
    m.add(cx - 2, a["y1"], 1451)                      # guerreros de arenisca a los lados de la salida
    m.add(cx + 2, a["y1"], 1451)


def build_silver(m: Map):
    a, p = arena_common(m, "silver")
    cx, cy = p["cx"], (a["y0"] + a["y1"]) // 2
    for y in range(cy - 2, cy + 1):                   # círculo central de baldosas enmarcadas
        for x in range(cx - 2, cx + 3):
            m.t[(x, y, Z)]["ground"] = 426
    for dx, dy in ((-5, -4), (5, -4), (-5, 3), (5, 3)):
        m.add(cx + dx, cy + dy, 1515)                 # columnas de mármol
    m.add(cx - 2, a["y1"], 1450)                      # perros guardianes en la salida
    m.add(cx + 2, a["y1"], 1450)


def build_gold(m: Map):
    a, p = arena_common(m, "gold")
    cx = p["cx"]
    for y in range(a["y0"] + 1, a["y0"] + 4):         # estrado dorado del boss
        for x in range(cx - 2, cx + 3):
            m.t[(x, y, Z)]["ground"] = 415
    carpet(m, cx, a["y0"] + 4, a["y1"] - 1)
    for bx, by in ((cx - 6, a["y0"] + 5), (cx + 5, a["y0"] + 5), (cx - 6, a["y0"] + 11), (cx + 5, a["y0"] + 11)):
        for dy in (0, 1):
            for dx in (0, 1):
                m.t[(bx + dx, by + dy, Z)]["ground"] = 598   # pozos de lava 2x2 (no pisables)
    for x in (cx - 3, cx + 3):
        m.add(x, a["y0"] + 1, 1551)                   # obeliscos dorados junto al estrado
    for x in (a["x0"] + 2, a["x1"] - 2):
        m.add(x, a["y0"], 1435)                       # banderas de dragón
    for dx in (-3, 3):
        m.add(cx + dx, a["y1"] - 4, 1551)


def build() -> Map:
    m = Map()
    build_hub(m)
    build_bronze(m)
    build_silver(m)
    build_gold(m)
    return m


# ---------------------------------------------------------------- validación
def validate(m: Map) -> list[str]:
    errs = []
    blocking = {1515, 1482, 1448, 1549, 1323, 1451, 1514, 1450, 1551, 1435, SIGN} | {
        v for w in WALLS.values() for v in w.values()}

    def walkable(x, y):
        t = m.t.get((x, y, Z))
        return t and t["ground"] != 598 and not (set(i["id"] for i in t["items"]) & blocking)

    def reach(start, box):
        seen, todo = {start[:2]}, [start[:2]]
        while todo:
            x, y = todo.pop()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in seen and box[0] <= nx <= box[2] and box[1] <= ny <= box[3] and walkable(nx, ny):
                    seen.add((nx, ny))
                    todo.append((nx, ny))
        return seen

    hb = (HUB["x0"], HUB["y0"], HUB["x1"], HUB["y1"])
    r = reach(LANDING, hb)
    for key, p in PADS.items():
        for y in range(p["y0"], p["y0"] + 2):
            for x in range(p["x0"], p["x0"] + 3):
                if (x, y) not in r:
                    errs.append(f"hub: plataforma {key} {x},{y} inaccesible")
        if (p["x0"] + 1, p["y0"]) not in r:
            errs.append(f"hub: palanca {key} sin casilla al lado")
    for pos in (RETURN_TP, (INFO_LEVER[0] + 1, INFO_LEVER[1], Z)):
        if pos[:2] not in r:
            errs.append(f"hub: {pos} inaccesible")
    for key, a in ARENAS.items():
        p = arena_points(a)
        box = (a["x0"], a["y0"], a["x1"], a["y1"])
        r = reach(p["entry"], box)
        free = sum(1 for y in range(a["y0"], a["y1"] + 1) for x in range(a["x0"], a["x1"] + 1) if walkable(x, y))
        if len(r) != free:
            errs.append(f"{key}: {free - len(r)} casillas libres aisladas")
        if p["exit"][:2] not in r:
            errs.append(f"{key}: salida inaccesible")
        for s in spawn_spots(a):
            if s[:2] not in r:
                errs.append(f"{key}: spawn {s} no pisable")
    return errs


LUA_BEGIN, LUA_END = "-- BEGIN LAYOUT (generado por scripts/map/generate-crucible.py)", "-- END LAYOUT"


def lua_layout(meta: dict) -> str:
    def pos(p):
        return f"{{x = {p[0]}, y = {p[1]}, z = {p[2]}}}"

    h = meta["hub"]
    out = [LUA_BEGIN,
           f"HUB = {{x0 = {h['x0']}, y0 = {h['y0']}, x1 = {h['x1']}, y1 = {h['y1']}, z = {Z}}}",
           f"HUB_LANDING = {pos(meta['landing'])}",
           "PADS = {"]
    for k, p in meta["pads"].items():
        out.append(f"\t{k} = {{x0 = {p['x0']}, y0 = {p['y0']}, x1 = {p['x0'] + 2}, y1 = {p['y0'] + 1}, z = {Z}}},")
    out.append("}")
    out.append("ARENAS = {")
    for k, a in meta["arenas"].items():
        out.append(f"\t{k} = {{")
        out.append(f"\t\tname = \"{a['name']}\",")
        out.append(f"\t\tx0 = {a['x0']}, y0 = {a['y0']}, x1 = {a['x1']}, y1 = {a['y1']}, z = {Z},")
        out.append(f"\t\tentry = {pos(a['entry'])},")
        out.append("\t\t-- spawns[1] = elite/boss; el resto, pack")
        out.append("\t\tspawns = {" + ", ".join(pos(s) for s in a["spawns"]) + "},")
        out.append("\t},")
    out.append("}")
    out.append(LUA_END)
    return "\n".join(out) + "\n"


def patch_lua(meta: dict, write: bool) -> bool:
    """Devuelve True si crucible.lua ya tenía este bloque."""
    src = LUA.read_text(encoding="utf-8")
    pat = re.compile(re.escape(LUA_BEGIN) + r".*?" + re.escape(LUA_END) + r"\n", re.DOTALL)
    if not pat.search(src):
        raise SystemExit(f"ERROR: {LUA} no tiene el bloque {LUA_BEGIN!r}")
    block = lua_layout(meta)
    new = pat.sub(lambda _m: block, src, count=1)
    if write and new != src:
        LUA.write_text(new, encoding="utf-8")
    return new == src


# ---------------------------------------------------------------- OTBM
def item_node(it: dict) -> bytes:
    props = struct.pack("<H", it["id"])
    if it["id"] in NEEDS_COUNT:                   # el server exige el byte de cantidad
        props += b"\x01"
    if it.get("uid"):
        props += struct.pack("<BH", ATTR_UID, it["uid"])
    if it.get("tele"):
        props += struct.pack("<BHHB", ATTR_TELE, *it["tele"])
    buf = bytearray([NODE_START, OTBM_ITEM])
    _maze.write_props(buf, props)
    buf.append(NODE_END)
    return bytes(buf)


def tile_node(ox: int, oy: int, t: dict) -> bytes:
    props = struct.pack("<BB", ox, oy)
    if t["pz"]:
        props += struct.pack("<BI", ATTR_TILE_FLAGS, TILE_PZ)
    props += struct.pack("<BH", ATTR_ITEM, t["ground"])
    buf = bytearray([NODE_START, OTBM_TILE])
    _maze.write_props(buf, props)
    for it in t["items"]:
        buf.extend(item_node(it))
    buf.append(NODE_END)
    return bytes(buf)


def areas(m: Map) -> bytes:
    from collections import defaultdict
    buckets = defaultdict(list)
    for (x, y, z), t in m.t.items():
        buckets[(x & ~0xFF, y & ~0xFF, z)].append((x & 0xFF, y & 0xFF, t))
    out = bytearray()
    for (bx, by, bz), rel in sorted(buckets.items()):
        out += bytes([NODE_START, OTBM_TILE_AREA])
        a = bytearray()
        _maze.write_props(a, struct.pack("<HHB", bx, by, bz))
        out += a
        for ox, oy, t in sorted(rel, key=lambda r: (r[0], r[1])):
            out += tile_node(ox, oy, t)
        out.append(NODE_END)
    return bytes(out)


def render_png(m: Map, path: Path):
    sys.path.insert(0, str(HERE / "kb"))
    from mapdata import Renderer, png_bytes
    tiles = {k: [t["ground"]] + [i["id"] for i in t["items"]] for k, t in m.t.items()}
    w, h, rgba = Renderer().area(tiles, CLEAR_BOX[0] + 3, CLEAR_BOX[1] + 5, CLEAR_BOX[2] - 20, CLEAR_BOX[3] - 8, Z)
    path.write_bytes(png_bytes(w, h, rgba))


def patch_readables(meta: dict):
    begin, end = "<!-- BEGIN CRUCIBLE_SIGNS -->", "<!-- END CRUCIBLE_SIGNS -->"
    lines = [f"\t{begin}"]
    for s in meta["signs"]:
        lines.append(f'\t<readable x="{s["x"]}" y="{s["y"]}" z="{Z}" text="{s["text"].replace(chr(10), chr(92) + "n")}"/>')
    lines.append(f"\t{end}")
    block = "\n".join(lines) + "\n"
    raw = READABLES.read_text(encoding="utf-8")
    pat = re.compile(r"[ \t]*" + re.escape(begin) + r".*?" + re.escape(end) + r"\n?", re.DOTALL)
    raw = pat.sub(lambda _m: block, raw, count=1) if pat.search(raw) else raw.replace("</readables>", block + "</readables>")
    READABLES.write_text(raw, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", type=Path, default=WORLD / "test.otbm")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--png", type=Path)
    a = ap.parse_args()

    m = build()
    meta = {
        "name": "generated-crucible", "version": 2, "tileCount": len(m.t),
        "clearBox": {"fromX": CLEAR_BOX[0], "fromY": CLEAR_BOX[1], "toX": CLEAR_BOX[2], "toY": CLEAR_BOX[3], "z": Z},
        "landing": LANDING, "returnTp": RETURN_TP, "templeLanding": TEMPLE_LANDING,
        "hub": {k: HUB[k] for k in ("x0", "y0", "x1", "y1")},
        "pads": {k: {"x0": p["x0"], "y0": p["y0"], "lever": (p["x0"] + 1, HUB["y0"], Z), "uid": p["uid"]}
                 for k, p in PADS.items()},
        "info": {"lever": INFO_LEVER, "uid": INFO_UID},
        "arenas": {k: {**{c: a_[c] for c in ("x0", "y0", "x1", "y1")}, "z": Z, "name": a_["name"],
                       "entry": arena_points(a_)["entry"], "exit": arena_points(a_)["exit"],
                       "spawns": spawn_spots(a_)} for k, a_ in ARENAS.items()},
        "signs": [{"x": p["x0"], "y": HUB["y0"], "text": p["sign"]} for p in PADS.values()]
                 + [{"x": INFO_SIGN[0], "y": INFO_SIGN[1], "text": INFO_TEXT}],
    }
    errs = validate(m)
    print(f"El Crisol v2: {len(m.t)} casillas; hub PZ {sum(1 for t in m.t.values() if t['pz'])}")
    for k, ar in meta["arenas"].items():
        print(f"  {k:6s} {ar['name']:18s} caja {ar['x0']},{ar['y0']}-{ar['x1']},{ar['y1']} entrada {ar['entry']} salida {ar['exit']}")
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
    a.map.write_bytes(raw[:4] + body[:at] + areas(m) + body[at:])
    patch_readables(meta)
    patch_lua(meta, write=True)
    (WORLD / "generated-crucible.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"OK {a.map}, readables, crucible.lua (LAYOUT) y generated-crucible.json")
    print("Después: python3 scripts/map/temple-portals.py (portal del templo -> LANDING)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
