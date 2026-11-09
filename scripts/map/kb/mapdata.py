"""Lectura de test.otbm, items OTB, Tibia.dat y Tibia.spr (7.6) sin dependencias.

Lo usan extract_facts.py, label_deepseek.py y build_kb.py.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
WORLD = REPO / "server/YurOTS/ots/data/world"
MAP = WORLD / "test.otbm"
OTB = REPO / "server/YurOTS/ots/data/items/items-zagan-test.otb"
DAT = REPO / "devtools/rme/rme-client-760/Tibia.dat"
SPR = REPO / "devtools/rme/rme-client-760/Tibia.spr"
KB_DIR = REPO / "docs/items-and-map/map-kb"

NODE_START, NODE_END, ESC = 0xFE, 0xFF, 0xFD
T_AREA, T_TILE, T_ITEM, T_HOUSETILE = 4, 5, 6, 14

OTB_GROUPS = ["none", "ground", "container", "weapon", "ammunition", "armor", "rune",
              "teleport", "magicfield", "writeable", "key", "splash", "fluid"]
OTB_FLAGS = {
    1: "block_solid", 2: "block_projectile", 4: "block_pathfind", 8: "has_height",
    16: "useable", 32: "pickupable", 64: "moveable", 128: "stackable",
    256: "floorchange_down", 512: "floorchange_north", 1024: "floorchange_east",
    2048: "floorchange_south", 4096: "floorchange_west", 8192: "always_on_top",
    16384: "readable", 32768: "rotable", 65536: "hangable", 131072: "vertical",
    262144: "horizontal", 524288: "cannot_decay",
}

# Flags del .dat 7.55–7.72
DAT_FLAGS = {
    0x00: "ground", 0x01: "ground_border", 0x02: "on_bottom", 0x03: "on_top",
    0x04: "container", 0x05: "stackable", 0x06: "force_use", 0x07: "multi_use",
    0x08: "writable", 0x09: "writable_once", 0x0A: "fluid_container", 0x0B: "fluid",
    0x0C: "unpassable", 0x0D: "unmoveable", 0x0E: "block_missile", 0x0F: "block_pathfind",
    0x10: "pickupable", 0x11: "hangable", 0x12: "hook_south", 0x13: "hook_east",
    0x14: "rotatable", 0x15: "light", 0x16: "dont_hide", 0x17: "floor_change",
    0x18: "offset", 0x19: "elevation", 0x1A: "lying_object", 0x1B: "animate_always",
    0x1C: "minimap", 0x1D: "lens_help", 0x1E: "full_ground", 0x1F: "ignore_look",
}
DAT_ARGS = {0x00: 2, 0x08: 2, 0x09: 2, 0x15: 4, 0x18: 4, 0x19: 2, 0x1C: 2, 0x1D: 2}

DIRS = {"n": (0, -1), "ne": (1, -1), "e": (1, 0), "se": (1, 1),
        "s": (0, 1), "sw": (-1, 1), "w": (-1, 0), "nw": (-1, -1)}


def parse_tree(data: bytes):
    """Árbol OTBM/OTB sin escapes: [type, props, children]. Iterativo."""
    pos = 4
    assert data[pos] == NODE_START
    root = [data[pos + 1], bytearray(), []]
    pos += 2
    stack = [root]
    n = len(data)
    while pos < n and stack:
        b = data[pos]
        if b == ESC:
            stack[-1][1].append(data[pos + 1])
            pos += 2
        elif b == NODE_START:
            node = [data[pos + 1], bytearray(), []]
            stack[-1][2].append(node)
            stack.append(node)
            pos += 2
        elif b == NODE_END:
            stack.pop()
            pos += 1
        else:
            stack[-1][1].append(b)
            pos += 1
    return root


def load_otb() -> dict[int, dict]:
    """server_id -> {cid, group, flags, name, descr}."""
    root = parse_tree(OTB.read_bytes())
    out = {}
    for group, props, _ in root[2]:
        props = bytes(props)
        flags = struct.unpack_from("<I", props, 0)[0] if len(props) >= 4 else 0
        pos = 4
        rec = {"group": OTB_GROUPS[group] if group < len(OTB_GROUPS) else f"g{group}",
               "flags": [v for k, v in OTB_FLAGS.items() if flags & k]}
        sid = None
        while pos + 3 <= len(props):
            attr = props[pos]
            size = struct.unpack_from("<H", props, pos + 1)[0]
            payload = props[pos + 3: pos + 3 + size]
            if attr == 0x10:
                sid = struct.unpack("<H", payload)[0]
            elif attr == 0x11:
                rec["cid"] = struct.unpack("<H", payload)[0]
            elif attr == 0x12:
                rec["name"] = payload.decode("latin-1")
            elif attr == 0x13:
                rec["descr"] = payload.decode("latin-1")
            pos += 3 + size
        if sid is None:
            continue
        if 20000 < sid < 20100:
            sid -= 20000
        out[sid] = rec
    return out


def parse_dat(path: Path = DAT) -> dict[int, dict]:
    d = path.read_bytes()
    _sig, items = struct.unpack_from("<IH", d, 0)
    pos = 12
    out = {}
    for cid in range(100, items + 1):
        flags = {}
        while True:
            f = d[pos]
            pos += 1
            if f == 0xFF:
                break
            if f >= 0x20:
                raise ValueError(f"bad dat flag {f:#x} at cid {cid}")
            n = DAT_ARGS.get(f, 0)
            flags[f] = d[pos:pos + n]
            pos += n
        w, h = d[pos], d[pos + 1]
        pos += 2
        if w > 1 or h > 1:
            pos += 1
        layers, px, py, pz, frames = d[pos:pos + 5]
        pos += 5
        n = w * h * layers * px * py * pz * frames
        sprites = list(struct.unpack_from(f"<{n}H", d, pos))
        pos += 2 * n
        out[cid] = dict(flags=flags, w=w, h=h, layers=layers, px=px, py=py, pz=pz,
                        frames=frames, sprites=sprites)
    return out


def dat_facts(e: dict) -> dict:
    fl = e["flags"]
    facts = {"dat_flags": [DAT_FLAGS[f] for f in sorted(fl)],
             "size_tiles": [e["w"], e["h"]], "pattern": [e["px"], e["py"]],
             "frames": e["frames"]}
    if 0x00 in fl:
        facts["ground_speed"] = struct.unpack("<H", fl[0x00])[0]
    if 0x1C in fl:
        facts["minimap_color"] = struct.unpack("<H", fl[0x1C])[0]
    if 0x15 in fl:
        lvl, col = struct.unpack("<HH", fl[0x15])
        facts["light"] = [lvl, col]
    if 0x19 in fl:
        facts["elevation"] = struct.unpack("<H", fl[0x19])[0]
    return facts


def layer_of(e: dict) -> str:
    fl = e["flags"]
    if 0x00 in fl:
        return "ground"
    if 0x01 in fl:
        return "border"
    if 0x02 in fl:
        return "bottom"
    if 0x03 in fl:
        return "top"
    return "common"


LAYER_RANK = {"ground": 0, "border": 1, "bottom": 2, "common": 3, "top": 4}


class Spr:
    def __init__(self, path: Path = SPR):
        self.d = path.read_bytes()
        _sig, self.count = struct.unpack_from("<IH", self.d, 0)
        self.cache: dict[int, list] = {}

    def pixels(self, sid: int):
        if sid in self.cache:
            return self.cache[sid]
        px = [[None] * 32 for _ in range(32)]
        if 0 < sid <= self.count:
            off = struct.unpack_from("<I", self.d, 6 + (sid - 1) * 4)[0]
            if off:
                size = struct.unpack_from("<H", self.d, off + 3)[0]
                p, end, i = off + 5, off + 5 + size, 0
                while p < end:
                    t, c = struct.unpack_from("<HH", self.d, p)
                    p += 4
                    i += t
                    for _ in range(c):
                        if i < 1024:
                            px[i // 32][i % 32] = (self.d[p], self.d[p + 1], self.d[p + 2])
                        p += 3
                        i += 1
        self.cache[sid] = px
        return px


def iter_tiles(root):
    """(x, y, z, [server ids en orden del archivo])."""
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        for tile in area[2]:
            if tile[0] not in (T_TILE, T_HOUSETILE):
                continue
            p = bytes(tile[1])
            x, y = ax + p[0], ay + p[1]
            pos = 2 + (4 if tile[0] == T_HOUSETILE else 0)
            items = []
            while pos < len(p):
                attr = p[pos]
                pos += 1
                if attr == 3:
                    pos += 4
                elif attr == 9:
                    items.append(struct.unpack_from("<H", p, pos)[0])
                    pos += 2
                else:
                    break
            for child in tile[2]:
                if child[0] == T_ITEM and len(child[1]) >= 2:
                    items.append(struct.unpack_from("<H", bytes(child[1]), 0)[0])
            yield x, y, az, items


def load_tiles() -> dict[tuple[int, int, int], list[int]]:
    return {(x, y, z): items for x, y, z, items in iter_tiles(parse_tree(MAP.read_bytes()))}


class Renderer:
    """Dibuja ítems sueltos o recortes del mapa a RGBA."""

    def __init__(self, otb=None, dat=None, spr=None):
        self.otb = otb or load_otb()
        self.dat = dat or parse_dat()
        self.spr = spr or Spr()

    def entry(self, sid: int):
        cid = self.otb.get(sid, {}).get("cid")
        return self.dat.get(cid) if cid else None

    def _blit(self, img, W, H, e, tx, ty, ox0, oy0):
        w, h, px, py = e["w"], e["h"], e["px"], e["py"]
        xp, yp = tx % px, ty % py
        for hy in range(h):
            for wx in range(w):
                for L in range(e["layers"]):
                    idx = ((yp * px + xp) * e["layers"] + L)
                    idx = (idx * h + hy) * w + wx
                    if idx >= len(e["sprites"]):
                        continue
                    pix = self.spr.pixels(e["sprites"][idx])
                    ox, oy = ox0 - wx * 32, oy0 - hy * 32
                    for yy in range(32):
                        Y = oy + yy
                        if not 0 <= Y < H:
                            continue
                        row = pix[yy]
                        for xx in range(32):
                            c = row[xx]
                            if c is not None and 0 <= ox + xx < W:
                                o = (Y * W + ox + xx) * 4
                                img[o:o + 4] = bytes((c[0], c[1], c[2], 255))

    def item(self, sid: int, bg=(40, 40, 46)):
        e = self.entry(sid)
        if e is None:
            return None
        W, H = 32 * e["w"], 32 * e["h"]
        img = bytearray(bytes((*bg, 255)) * (W * H))
        self._blit(img, W, H, e, 0, 0, (e["w"] - 1) * 32, (e["h"] - 1) * 32)
        return W, H, img

    def area(self, tiles, x1, y1, x2, y2, z, highlight=None):
        W, H = (x2 - x1 + 1) * 32, (y2 - y1 + 1) * 32
        img = bytearray(b"\x1c\x1c\x20\xff" * (W * H))
        for ty in range(y1, y2 + 3):
            for tx in range(x1, x2 + 3):
                items = tiles.get((tx, ty, z))
                if not items:
                    continue
                draw = []
                for sid in items:
                    e = self.entry(sid)
                    if e is not None:
                        draw.append((LAYER_RANK[layer_of(e)], e))
                draw.sort(key=lambda t: t[0])
                for _r, e in draw:
                    self._blit(img, W, H, e, tx, ty, (tx - x1) * 32, (ty - y1) * 32)
        if highlight:
            hx, hy = (highlight[0] - x1) * 32, (highlight[1] - y1) * 32
            for i in range(32):
                for X, Y in ((hx + i, hy), (hx + i, hy + 31), (hx, hy + i), (hx + 31, hy + i)):
                    if 0 <= X < W and 0 <= Y < H:
                        o = (Y * W + X) * 4
                        img[o:o + 4] = b"\xff\x30\x30\xff"
        return W, H, img


def png_bytes(w: int, h: int, rgba: bytes, scale: int = 1) -> bytes:
    if scale > 1:
        rows = []
        for y in range(h):
            row = rgba[y * w * 4:(y + 1) * w * 4]
            big = b"".join(row[i:i + 4] * scale for i in range(0, len(row), 4))
            rows.extend([big] * scale)
        w, h = w * scale, h * scale
    else:
        rows = [rgba[y * w * 4:(y + 1) * w * 4] for y in range(h)]
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(t, b):
        return struct.pack(">I", len(b)) + t + b + struct.pack(">I", zlib.crc32(t + b) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def serialize_tree(root, header: bytes = b"\x00\x00\x00\x00") -> bytes:
    """Inverso de parse_tree: escapa props y escribe nodos (iterativo)."""
    out = bytearray(header)

    def esc(b):
        for v in b:
            if v in (NODE_START, NODE_END, ESC):
                out.append(ESC)
            out.append(v)

    stack = [(root, 0)]
    while stack:
        node, i = stack.pop()
        if i == 0:
            out.append(NODE_START)
            out.append(node[0])
            esc(node[1])
        if i < len(node[2]):
            stack.append((node, i + 1))
            stack.append((node[2][i], 0))
        else:
            out.append(NODE_END)
    return bytes(out)
