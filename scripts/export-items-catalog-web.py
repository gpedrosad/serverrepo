#!/usr/bin/env python3
"""Genera el catálogo web de TODOS los items del items.otb con sprite.

Salidas:
  web/assets/items/items-atlas.png  — atlas de sprites (celdas de 64x64)
  web/data/items_all.json           — metadatos de items ordenados por server id

Cada item se dibuja como en el juego (compuesto width x height, anclado
abajo-derecha en la celda). La web ubica el sprite por índice de celda.

Uso:
  python3 scripts/export-items-catalog-web.py
  python3 scripts/export-items-catalog-web.py --dat X --spr Y --otb Z
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Falta Pillow: pip install pillow") from exc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.project_root import project_root  # noqa: E402

ROOT = project_root(Path(__file__))
SPRITE_SIZE = 32
CELL_SIZE = 64
ATLAS_COLS = 80
THING_LAST_ATTR = 0xFF

NODE_START, NODE_END, ESCAPE = 0xFE, 0xFF, 0xFD

GROUP_NAMES = {
    0: "none",
    1: "ground",
    2: "container",
    3: "weapon",
    4: "ammunition",
    5: "armor",
    6: "changes",
    7: "teleport",
    8: "magicfield",
    9: "writable",
    10: "key",
    11: "splash",
    12: "fluid",
    13: "door",
}

FLAG_LABELS = [
    (1 << 0, "blockSolid"),
    (1 << 1, "blockProjectile"),
    (1 << 2, "blockPathFind"),
    (1 << 3, "hasHeight"),
    (1 << 4, "useable"),
    (1 << 5, "pickupable"),
    (1 << 6, "moveable"),
    (1 << 7, "stackable"),
    (1 << 8, "floorChangeDown"),
    (1 << 9, "floorChangeNorth"),
    (1 << 10, "floorChangeEast"),
    (1 << 11, "floorChangeSouth"),
    (1 << 12, "floorChangeWest"),
    (1 << 13, "alwaysOnTop"),
    (1 << 14, "readable"),
    (1 << 15, "rotable"),
    (1 << 16, "hangable"),
    (1 << 17, "vertical"),
    (1 << 18, "horizontal"),
    (1 << 26, "lookThrough"),
]


# ---------------------------------------------------------------- items.otb

def _read_node(data: bytes, i: int):
    assert data[i] == NODE_START
    i += 1
    node_type = data[i]
    i += 1
    props = bytearray()
    children = []
    while True:
        b = data[i]
        if b == ESCAPE:
            props.append(data[i + 1])
            i += 2
        elif b == NODE_START:
            child, i = _read_node(data, i)
            children.append(child)
        elif b == NODE_END:
            i += 1
            return (node_type, bytes(props), children), i
        else:
            props.append(b)
            i += 1


def parse_otb(path: Path) -> list[dict]:
    data = path.read_bytes()
    root, _ = _read_node(data, 4)
    items = []
    for node_type, props, _children in root[2]:
        if len(props) < 4:
            continue
        flags = struct.unpack("<I", props[:4])[0]
        p = 4
        sid = cid = None
        name = ""
        while p + 3 <= len(props):
            attr = props[p]
            dl = struct.unpack("<H", props[p + 1:p + 3])[0]
            p += 3
            val = props[p:p + dl]
            p += dl
            if attr == 0x10:
                sid = struct.unpack("<H", val)[0]
            elif attr == 0x11:
                cid = struct.unpack("<H", val)[0]
            elif attr == 0x12:
                name = val.decode("latin1")
        if sid is not None:
            items.append({
                "sid": sid,
                "cid": cid,
                "name": name,
                "group": GROUP_NAMES.get(node_type, str(node_type)),
                "flags": flags,
            })
    items.sort(key=lambda it: it["sid"])
    return items


# ------------------------------------------------------------- Tibia.dat/spr

class DatReader:
    """Parser Tibia.dat 7.6 (items). Devuelve dimensiones + sprite ids."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0
        self.signature = self._u32()
        self.item_count, self.outfit_count, self.effect_count, self.missile_count = (
            struct.unpack_from("<HHHH", self.data, self.pos))
        self.pos += 8
        self._cache: dict[int, dict] = {}
        self._next_item_id = 100

    def thing(self, client_id: int) -> dict:
        last_item = 100 + self.item_count - 1
        if client_id < 100 or client_id > last_item:
            raise KeyError(f"client_id {client_id} fuera de rango (max {last_item})")
        while self._next_item_id <= client_id:
            self._cache[self._next_item_id] = self._read_thing()
            self._next_item_id += 1
        return self._cache[client_id]

    def _u8(self) -> int:
        v = self.data[self.pos]
        self.pos += 1
        return v

    def _u16(self) -> int:
        v = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return v

    def _u32(self) -> int:
        v = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return v

    def _skip_attr_payload(self, attr: int) -> None:
        if attr in (0, 8, 9, 25, 28, 29, 32, 34):
            self.pos += 2
        elif attr == 21:  # Light
            self.pos += 4
        elif attr == 24:  # Displacement (>=7.55)
            self.pos += 4
        elif attr == 33:  # Market (defensivo)
            self.pos += 6
            name_len = struct.unpack_from("<H", self.data, self.pos)[0]
            self.pos += name_len + 4

    def _read_thing(self) -> dict:
        while True:
            attr = self._u8()
            if attr == THING_LAST_ATTR:
                break
            self._skip_attr_payload(attr)

        width = self._u8()
        height = self._u8()
        if width > 1 or height > 1:
            self._u8()  # realSize
        layers = self._u8()
        pattern_x = self._u8()
        pattern_y = self._u8()
        pattern_z = self._u8()
        phases = self._u8()

        total = width * height * layers * pattern_x * pattern_y * pattern_z * phases
        sprites = [self._u16() for _ in range(total)]
        return {
            "width": width,
            "height": height,
            "layers": layers,
            "px": pattern_x,
            "py": pattern_y,
            "pz": pattern_z,
            "phases": phases,
            "sprites": sprites,
        }


class SprReader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.sprite_count = struct.unpack_from("<H", data, 4)[0]
        self._cache: dict[int, Image.Image] = {}

    def decode(self, sprite_id: int) -> Image.Image | None:
        if sprite_id < 1 or sprite_id > self.sprite_count:
            return None
        if sprite_id in self._cache:
            return self._cache[sprite_id]
        addr = struct.unpack_from("<I", self.data, 6 + (sprite_id - 1) * 4)[0]
        if addr == 0:
            return None

        pos = addr + 3  # color key RGB
        pixel_data_size = struct.unpack_from("<H", self.data, pos)[0]
        pos += 2

        pixels = bytearray(SPRITE_SIZE * SPRITE_SIZE * 4)
        write_pos = 0
        read = 0
        while read < pixel_data_size and write_pos < len(pixels):
            transparent = struct.unpack_from("<H", self.data, pos)[0]
            pos += 2
            colored = struct.unpack_from("<H", self.data, pos)[0]
            pos += 2
            write_pos += 4 * min(transparent, (len(pixels) - write_pos) // 4)
            for _ in range(colored):
                if write_pos + 4 > len(pixels):
                    break
                r, g, b = self.data[pos], self.data[pos + 1], self.data[pos + 2]
                pos += 3
                pixels[write_pos:write_pos + 4] = bytes((r, g, b, 255))
                write_pos += 4
            read += 4 + 3 * colored

        img = Image.frombytes("RGBA", (SPRITE_SIZE, SPRITE_SIZE), bytes(pixels))
        self._cache[sprite_id] = img
        return img


def compose_item(thing: dict, spr: SprReader) -> Image.Image | None:
    """Compone el frame 0 / patrón 0 del item, como lo dibuja el cliente."""
    w, h, layers = thing["width"], thing["height"], thing["layers"]
    canvas = Image.new("RGBA", (w * SPRITE_SIZE, h * SPRITE_SIZE), (0, 0, 0, 0))
    got_any = False
    for layer in range(layers):
        for sy in range(h):
            for sx in range(w):
                # index = (((((phase*pz + z)*py + y)*px + x)*layers + l)*h + sy)*w + sx
                idx = (layer * h + sy) * w + sx
                if idx >= len(thing["sprites"]):
                    continue
                sprite_id = thing["sprites"][idx]
                if sprite_id == 0:
                    continue
                img = spr.decode(sprite_id)
                if img is None:
                    continue
                # sprite (0,0) es la esquina inferior derecha
                dest_x = (w - 1 - sx) * SPRITE_SIZE
                dest_y = (h - 1 - sy) * SPRITE_SIZE
                canvas.paste(img, (dest_x, dest_y), img)
                got_any = True
    return canvas if got_any else None


def flag_list(flags: int) -> list[str]:
    return [label for bit, label in FLAG_LABELS if flags & bit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Catálogo web de items OTB con sprites")
    parser.add_argument("--dat", type=Path, default=ROOT / "rme-client-760/Tibia.dat")
    parser.add_argument("--spr", type=Path, default=ROOT / "rme-client-760/Tibia.spr")
    parser.add_argument("--otb", type=Path,
                        default=ROOT / "server/YurOTS/ots/data/items/items.otb")
    parser.add_argument("--out-atlas", type=Path,
                        default=ROOT / "web/assets/items/items-atlas.png")
    parser.add_argument("--out-json", type=Path,
                        default=ROOT / "web/data/items_all.json")
    args = parser.parse_args()

    for p in (args.dat, args.spr, args.otb):
        if not p.is_file():
            raise SystemExit(f"No existe: {p}")

    items = parse_otb(args.otb)
    dat = DatReader(args.dat.read_bytes())
    spr = SprReader(args.spr.read_bytes())

    print(f"otb: {args.otb} ({len(items)} items)")
    print(f"dat: {args.dat} (items={dat.item_count})")
    print(f"spr: {args.spr} (sprites={spr.sprite_count})")

    rows = (len(items) + ATLAS_COLS - 1) // ATLAS_COLS
    atlas = Image.new("RGBA", (ATLAS_COLS * CELL_SIZE, rows * CELL_SIZE), (0, 0, 0, 0))

    out_items = []
    missing = 0
    for index, it in enumerate(items):
        sprite_ok = False
        if it["cid"]:
            try:
                thing = dat.thing(it["cid"])
                img = compose_item(thing, spr)
            except KeyError:
                img = None
            if img is not None:
                if img.width > CELL_SIZE or img.height > CELL_SIZE:
                    img.thumbnail((CELL_SIZE, CELL_SIZE), Image.Resampling.NEAREST)
                cx = (index % ATLAS_COLS) * CELL_SIZE
                cy = (index // ATLAS_COLS) * CELL_SIZE
                # anclado abajo-derecha, como renderiza el cliente
                atlas.paste(img, (cx + CELL_SIZE - img.width, cy + CELL_SIZE - img.height), img)
                sprite_ok = True
        if not sprite_ok:
            missing += 1
        out_items.append({
            "sid": it["sid"],
            "cid": it["cid"],
            "name": it["name"],
            "group": it["group"],
            "flags": flag_list(it["flags"]),
            "img": sprite_ok,
        })

    args.out_atlas.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(args.out_atlas, "PNG", optimize=True)

    payload = {
        "generated": "scripts/export-items-catalog-web.py",
        "atlas": {"cell": CELL_SIZE, "cols": ATLAS_COLS, "count": len(out_items)},
        "items": out_items,
    }
    args.out_json.write_text(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8")

    size_mb = args.out_atlas.stat().st_size / 1024 / 1024
    print(f"atlas: {args.out_atlas} ({atlas.width}x{atlas.height}, {size_mb:.1f} MB)")
    print(f"json:  {args.out_json} ({len(out_items)} items, {missing} sin sprite)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
