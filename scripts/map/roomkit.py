"""Piezas comunes para generadores de salas cerradas (El Crisol, Wave Arena).

  Room      caja interior w x h con origen; at(dx, dy) da coordenadas absolutas
  Map       casillas {pos: {ground, items, pz}}
  build_room  suelo + anillo de paredes (patrón medido en test.otbm)
  Checker   validación con los flags reales del .otb (block_solid, stackable)
  write_map   borra una caja del OTBM e inserta las casillas generadas
  patch_block reescribe un bloque BEGIN/END en un archivo de texto (Lua, readables)

Las paredes de 7.6 se eligen por vecinos: esquina NO = poste, NE = horizontal,
SO = vertical, SE = esquina en L (docs/items-and-map/PIEZAS_DE_MAPA.md).
"""
from __future__ import annotations

import importlib.util
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
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"

NODE_START, NODE_END = _maze.NODE_START, _maze.NODE_END
OTBM_TILE_AREA, OTBM_TILE, OTBM_ITEM = _maze.OTBM_TILE_AREA, _maze.OTBM_TILE, _maze.OTBM_ITEM
ATTR_TILE_FLAGS, ATTR_UID, ATTR_DESC, ATTR_TELE, ATTR_ITEM = 3, 5, 7, 8, 9
TILE_PZ = 1

TELEPORT, LEVER, SIGN = 1387, 1945, 1429
# poste NO, horizontal (N, S y esquina NE), vertical (O, E y esquina SO), L (esquina SE)
WALLS = {
    "stone": dict(post=1051, h=1050, v=1049, se=1053),
    "sand": dict(post=1062, h=1063, v=1060, se=1066),
    "brick": dict(post=1027, h=1028, v=1030, se=1033),
    "bamboo": dict(post=3425, h=3426, v=3423, se=3429),
}


class Room:
    """Caja interior w x h con origen (x0, y0, z); el anillo de paredes va por fuera."""

    def __init__(self, x0: int, y0: int, w: int, h: int, z: int):
        self.x0, self.y0, self.w, self.h, self.z = x0, y0, w, h, z
        self.x1, self.y1 = x0 + w - 1, y0 + h - 1

    def at(self, dx: int, dy: int) -> tuple[int, int, int]:
        assert 0 <= dx < self.w and 0 <= dy < self.h, f"({dx},{dy}) fuera de la sala {self.w}x{self.h}"
        return (self.x0 + dx, self.y0 + dy, self.z)

    def box(self) -> dict:
        return dict(x0=self.x0, y0=self.y0, x1=self.x1, y1=self.y1)

    def cells(self):
        return [(x, y, self.z) for y in range(self.y0, self.y1 + 1) for x in range(self.x0, self.x1 + 1)]

    def north_wall(self, dx: int):
        return (self.x0 + dx, self.y0 - 1, self.z)

    def west_wall(self, dy: int):
        return (self.x0 - 1, self.y0 + dy, self.z)


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
    W, z = WALLS[walls], r.z
    for y in range(r.y0 - 1, r.y1 + 2):
        for x in range(r.x0 - 1, r.x1 + 2):
            m.ground((x, y, z), floor, pz)
    for x in range(r.x0, r.x1 + 1):
        m.add((x, r.y0 - 1, z), W["h"])
        m.add((x, r.y1 + 1, z), W["h"])
    for y in range(r.y0, r.y1 + 1):
        m.add((r.x0 - 1, y, z), W["v"])
        m.add((r.x1 + 1, y, z), W["v"])
    m.add((r.x0 - 1, r.y0 - 1, z), W["post"])
    m.add((r.x1 + 1, r.y0 - 1, z), W["h"])
    m.add((r.x0 - 1, r.y1 + 1, z), W["v"])
    m.add((r.x1 + 1, r.y1 + 1, z), W["se"])


# ---------------------------------------------------------------- validación
class Checker:
    def __init__(self, m: Map, otb: dict | None = None):
        self.m = m
        self.otb = otb or load_otb()
        self.solid = {sid for sid, rec in self.otb.items() if "block_solid" in rec["flags"]}
        self.stackable = {sid for sid, rec in self.otb.items() if "stackable" in rec["flags"]}
        self.wall_ids = {v for w in WALLS.values() for v in w.values()}
        self.errs: list[str] = []

    def walkable(self, pos) -> bool:
        t = self.m.t.get(pos)
        return bool(t) and t["ground"] not in self.solid and not any(i["id"] in self.solid for i in t["items"])

    def reach(self, start, r: Room) -> set:
        seen, todo = {start}, [start]
        while todo:
            x, y, z = todo.pop()
            for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z)):
                if n not in seen and r.x0 <= n[0] <= r.x1 and r.y0 <= n[1] <= r.y1 and self.walkable(n):
                    seen.add(n)
                    todo.append(n)
        return seen

    def tiles(self):
        """ids que existen y nunca dos piezas sólidas (que no sean pared) en la misma casilla."""
        for pos, t in self.m.t.items():
            ids = [i["id"] for i in t["items"]]
            unknown = [i for i in ids + [t["ground"]] if i not in self.otb]
            if unknown:
                self.errs.append(f"{pos}: ids que no están en el .otb {unknown}")
            if len([i for i in ids if i in self.solid and i not in self.wall_ids]) > 1:
                self.errs.append(f"{pos}: dos piezas sólidas en la misma casilla {ids}")

    def rooms(self, rooms: list[Room], clear_box: tuple[int, int, int, int]):
        """Salas (con su anillo de paredes) dentro de clear_box y sin pisarse."""
        for k in rooms:
            if not (clear_box[0] < k.x0 - 1 and k.x1 + 1 < clear_box[2] and clear_box[1] < k.y0 - 1 and k.y1 + 1 < clear_box[3]):
                self.errs.append(f"sala {k.box()} fuera de la caja que se borra")
        for i, p in enumerate(rooms):
            for q in rooms[i + 1:]:
                if p.z == q.z and p.x0 - 1 <= q.x1 + 1 and q.x0 - 1 <= p.x1 + 1 and p.y0 - 1 <= q.y1 + 1 and q.y0 - 1 <= p.y1 + 1:
                    self.errs.append(f"salas {p.box()} y {q.box()} se pisan")

    def connected(self, label: str, r: Room, start) -> set:
        """Todo el piso libre de la sala se alcanza desde start."""
        seen = self.reach(start, r)
        free = sum(1 for c in r.cells() if self.walkable(c))
        if len(seen) != free:
            self.errs.append(f"{label}: {free - len(seen)} casillas libres aisladas")
        return seen

    def need(self, label: str, seen: set, points: dict):
        self.errs += [f"{label}: {what} {pos} inaccesible" for what, pos in points.items() if pos not in seen]


# ---------------------------------------------------------------- OTBM
def item_node(it: dict, stackable: set[int]) -> bytes:
    props = struct.pack("<H", it["id"])
    if it["id"] in stackable:                     # el server exige el byte de cantidad
        props += b"\x01"
    if it.get("uid"):
        props += struct.pack("<BH", ATTR_UID, it["uid"])
    if it.get("desc"):                            # texto al mirar (ASCII, cliente 7.6)
        raw = it["desc"].encode("ascii")
        props += struct.pack("<BH", ATTR_DESC, len(raw)) + raw
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


def write_map(path: Path, m: Map, clear_box: tuple[int, int, int, int], z: int, stackable: set[int]):
    """Borra clear_box (piso z) del OTBM e inserta las casillas de m."""
    raw = path.read_bytes()
    body = _maze.filter_tiles_in_bbox(raw[4:], clear_box[0], clear_box[1], clear_box[2], clear_box[3], z)
    at = _maze.find_map_data_insert(body)
    path.write_bytes(raw[:4] + body[:at] + areas(m, stackable) + body[at:])


def render_png(m: Map, path: Path, z: int):
    from mapdata import Renderer, png_bytes
    tiles = {k: [t["ground"]] + [i["id"] for i in t["items"]] for k, t in m.t.items() if k[2] == z}
    xs = [k[0] for k in tiles]
    ys = [k[1] for k in tiles]
    w, h, rgba = Renderer().area(tiles, min(xs) - 1, min(ys) - 1, max(xs) + 2, max(ys) + 2, z)
    path.write_bytes(png_bytes(w, h, rgba))


# ---------------------------------------------------------------- Lua / readables
def patch_block(path: Path, begin: str, end: str, block: str, write: bool) -> bool:
    """Reemplaza el bloque begin..end (inclusive, con salto final). True si ya estaba igual."""
    src = path.read_text(encoding="utf-8")
    pat = re.compile(re.escape(begin) + r".*?" + re.escape(end) + r"\n", re.DOTALL)
    if not pat.search(src):
        raise SystemExit(f"ERROR: {path} no tiene el bloque {begin!r}")
    new = pat.sub(lambda _m: block, src, count=1)
    if write and new != src:
        path.write_text(new, encoding="utf-8")
    return new == src


def patch_readables(begin: str, end: str, signs: list[dict]):
    """Bloque de carteles en readables.xml: [{x, y, z, text}]. Lo agrega si no existe."""
    lines = [f"\t{begin}"]
    for s in signs:
        text = s["text"].replace("\n", "\\n")
        lines.append(f'\t<readable x="{s["x"]}" y="{s["y"]}" z="{s["z"]}" text="{text}"/>')
    lines.append(f"\t{end}")
    block = "\n".join(lines) + "\n"
    raw = READABLES.read_text(encoding="utf-8")
    pat = re.compile(r"[ \t]*" + re.escape(begin) + r".*?" + re.escape(end) + r"\n?", re.DOTALL)
    raw = pat.sub(lambda _m: block, raw, count=1) if pat.search(raw) else raw.replace("</readables>", block + "</readables>")
    READABLES.write_text(raw, encoding="utf-8")


def lua_pos(p) -> str:
    return f"{{x = {p[0]}, y = {p[1]}, z = {p[2]}}}"


def lua_box(b: dict, z: int) -> str:
    return f"x0 = {b['x0']}, y0 = {b['y0']}, x1 = {b['x1']}, y1 = {b['y1']}, z = {z}"
