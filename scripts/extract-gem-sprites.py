#!/usr/bin/env python3
"""Extrae sprites de gemas Retro76 desde Tibia.dat + Tibia.spr (cliente 7.6).

Salida por defecto: web/assets/gems/

Set de archivos generados (10 gemas × variantes):

  Pequeñas (32px + 64px + opcional jpg):
    2145-small.png   Diamond
    2146-small.png   Sapphire  → Yellow Gem pequeño en juego
    2147-small.png   Ruby
    2149-small.png   Emerald
    2150-small.png   Amethyst

  Grandes (40px + 80px + opcional jpg):
    2153-large.png   Violet Gem
    2154-large.png   Yellow Gem
    2155-large.png   Big Emerald
    2156-large.png   Big Ruby
    2158-large.png   Blue Gem

  Índice:
    manifest.json    metadatos para la web (ids, nombres, rutas, spriteId)

Uso:
  ./scripts/extract-gem-sprites.py
  ./scripts/extract-gem-sprites.py --jpg          # también .jpg con fondo #0a0a0a
  ./scripts/extract-gem-sprites.py --out /tmp/gems
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Falta Pillow: pip install pillow") from exc

ROOT = Path(__file__).resolve().parents[1]
CLIENT_VERSION = 760
SPRITE_SIZE = 32
THING_LAST_ATTR = 0xFF

# Server item id → export spec (alineado con web/index.html GEMS_*)
@dataclass(frozen=True)
class GemExport:
    server_id: int
    slug: str
    display_name: str
    tier: str  # "small" | "large"
    export_px: int  # tamaño final en la web


GEM_EXPORTS: tuple[GemExport, ...] = (
    GemExport(2150, "amethyst", "Amethyst", "small", 32),
    GemExport(2149, "emerald", "Emerald", "small", 32),
    GemExport(2147, "ruby", "Ruby", "small", 32),
    GemExport(2146, "sapphire", "Sapphire", "small", 32),
    GemExport(2145, "diamond", "Diamond", "small", 32),
    GemExport(2153, "violet-gem", "Violet Gem", "large", 40),
    GemExport(2154, "yellow-gem", "Yellow Gem", "large", 40),
    GemExport(2155, "big-emerald", "Big Emerald", "large", 40),
    GemExport(2156, "big-ruby", "Big Ruby", "large", 40),
    GemExport(2158, "blue-gem", "Blue Gem", "large", 40),
)


class DatReader:
    """Parser Tibia.dat 7.6 (items) — basado en OTClient ThingType::unserialize."""

    def __init__(self, data: bytes, client_version: int = CLIENT_VERSION) -> None:
        self.data = data
        self.pos = 0
        self.client_version = client_version
        self.signature = self._u32()
        counts = struct.unpack_from("<HHHH", self.data, self.pos)
        self.pos += 8
        self.item_count, self.outfit_count, self.effect_count, self.missile_count = counts
        self._sprite_cache: dict[int, list[int]] = {}
        self._next_item_id = 100

    def sprite_ids_for_client_item(self, client_id: int) -> list[int]:
        if client_id < 100:
            raise ValueError(f"client_id inválido: {client_id}")
        last_item = 100 + self.item_count - 1
        if client_id > last_item:
            raise KeyError(f"item client_id {client_id} no encontrado en .dat (max {last_item})")
        while self._next_item_id <= client_id:
            sprites = self._read_thing(self._next_item_id)
            self._sprite_cache[self._next_item_id] = sprites
            self._next_item_id += 1
        return self._sprite_cache[client_id]

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
        # Payloads según ThingType::unserialize (OTClient, cliente 7.6)
        if attr in (0, 8, 9, 25, 28, 29, 32, 34):  # Ground, Writable*, Elevation, Minimap, Lens, Cloth, Usable
            self.pos += 2
        elif attr == 21:  # Light
            self.pos += 4
        elif attr == 24 and self.client_version >= 755:  # Displacement
            self.pos += 4
        elif attr == 33:  # Market (no en 7.6 habitual; skip defensivo)
            self.pos += 6
            name_len = struct.unpack_from("<H", self.data, self.pos)[0]
            self.pos += name_len + 4

    def _read_thing(self, client_id: int, category_items: bool = True) -> list[int]:
        done = False
        while not done:
            attr = self._u8()
            if attr == THING_LAST_ATTR:
                done = True
                break
            if self.client_version >= 755 and attr == 23:
                attr = 252  # ThingAttrFloorChange
            self._skip_attr_payload(attr)

        width = self._u8()
        height = self._u8()
        if width > 1 or height > 1:
            self._u8()  # realSize
        layers = self._u8()
        pattern_x = self._u8()
        pattern_y = self._u8()
        pattern_z = self._u8() if self.client_version >= 755 else 1
        anim_phases = self._u8()

        total = width * height * layers * pattern_x * pattern_y * pattern_z * anim_phases
        sprites = [self._u16() for _ in range(total)]
        return sprites


class SprReader:
    """Parser Tibia.spr 7.6 (u16 sprite count + tabla de offsets)."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.signature = struct.unpack_from("<I", data, 0)[0]
        self.sprite_count = struct.unpack_from("<H", data, 4)[0]
        self.offset_table_pos = 6

    def _sprite_offset(self, sprite_id: int) -> int:
        if sprite_id < 1 or sprite_id > self.sprite_count:
            raise ValueError(f"sprite_id fuera de rango: {sprite_id}")
        return struct.unpack_from("<I", self.data, self.offset_table_pos + (sprite_id - 1) * 4)[0]

    def decode(self, sprite_id: int) -> Image.Image:
        addr = self._sprite_offset(sprite_id)
        if addr == 0:
            raise ValueError(f"sprite {sprite_id} vacío")

        pos = addr + 3  # color key RGB
        pixel_data_size = struct.unpack_from("<H", self.data, pos)[0]
        pos += 2

        pixels = bytearray(SPRITE_SIZE * SPRITE_SIZE * 4)
        write_pos = 0
        read = 0
        channels = 3  # 7.6 sin alpha channel en spr

        while read < pixel_data_size and write_pos < len(pixels):
            transparent = struct.unpack_from("<H", self.data, pos)[0]
            pos += 2
            colored = struct.unpack_from("<H", self.data, pos)[0]
            pos += 2

            for _ in range(transparent):
                if write_pos >= len(pixels):
                    break
                pixels[write_pos : write_pos + 4] = b"\x00\x00\x00\x00"
                write_pos += 4

            for _ in range(colored):
                if write_pos + 4 > len(pixels):
                    break
                r, g, b = self.data[pos], self.data[pos + 1], self.data[pos + 2]
                pos += 3
                pixels[write_pos : write_pos + 4] = bytes((r, g, b, 255))
                write_pos += 4

            read += 4 + channels * colored

        while write_pos < len(pixels):
            pixels[write_pos : write_pos + 4] = b"\x00\x00\x00\x00"
            write_pos += 4

        return Image.frombytes("RGBA", (SPRITE_SIZE, SPRITE_SIZE), bytes(pixels))


def resolve_client_id(otb_path: Path, server_id: int) -> int:
    data = otb_path.read_bytes()
    needle = b"\x10\x02\x00" + struct.pack("<H", server_id)
    pos = 0
    while True:
        i = data.find(needle, pos)
        if i == -1:
            raise KeyError(f"server_id {server_id} no encontrado en {otb_path}")
        j = data.find(b"\x11\x02\x00", i, i + 24)
        if j != -1:
            return struct.unpack_from("<H", data, j + 3)[0]
        pos = i + 1


def find_assets() -> tuple[Path, Path, Path]:
    candidates = [
        ROOT / "rme-client-760",
        ROOT,
        Path.home() / "Downloads" / "tibia76",
    ]
    dat = spr = None
    for base in candidates:
        d, s = base / "Tibia.dat", base / "Tibia.spr"
        if d.is_file() and s.is_file():
            dat, spr = d, s
            break
    if not dat or not spr:
        raise SystemExit(
            "No encontré Tibia.dat + Tibia.spr. Copiá el cliente 7.6 a rme-client-760/ "
            "o ~/Downloads/tibia76/"
        )
    otb = ROOT / "server/YurOTS/ots/data/items/items.otb"
    if not otb.is_file():
        raise SystemExit(f"Falta {otb}")
    return dat, spr, otb


def trim_transparent(img: Image.Image) -> Image.Image:
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def export_gem(
    gem: GemExport,
    sprite_id: int,
    sprite: Image.Image,
    out_dir: Path,
    *,
    also_jpg: bool,
    jpg_bg: tuple[int, int, int],
) -> dict:
    base = f"{gem.server_id}-{gem.tier}"
    png_path = out_dir / f"{base}.png"
    png_2x_path = out_dir / f"{base}@2x.png"

    trimmed = trim_transparent(sprite)
    # Centrar en canvas cuadrado (pixel art nítido)
    canvas = Image.new("RGBA", (SPRITE_SIZE, SPRITE_SIZE), (0, 0, 0, 0))
    ox = (SPRITE_SIZE - trimmed.width) // 2
    oy = (SPRITE_SIZE - trimmed.height) // 2
    canvas.paste(trimmed, (ox, oy), trimmed)

    scaled = canvas.resize((gem.export_px, gem.export_px), Image.Resampling.NEAREST)
    scaled_2x = canvas.resize((gem.export_px * 2, gem.export_px * 2), Image.Resampling.NEAREST)

    scaled.save(png_path, "PNG")
    scaled_2x.save(png_2x_path, "PNG")

    entry = {
        "serverId": gem.server_id,
        "slug": gem.slug,
        "name": gem.display_name,
        "tier": gem.tier,
        "spriteId": sprite_id,
        "files": {
            "png": png_path.name,
            "png2x": png_2x_path.name,
        },
        "sizePx": gem.export_px,
    }

    if also_jpg:
        jpg_path = out_dir / f"{base}.jpg"
        jpg_2x_path = out_dir / f"{base}@2x.jpg"
        for src, dest in ((scaled, jpg_path), (scaled_2x, jpg_2x_path)):
            bg = Image.new("RGB", src.size, jpg_bg)
            bg.paste(src, mask=src.split()[3])
            bg.save(dest, "JPEG", quality=92)
        entry["files"]["jpg"] = jpg_path.name
        entry["files"]["jpg2x"] = jpg_2x_path.name

    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrae sprites de gemas para la web Retro76")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "web/assets/gems",
        help="Directorio de salida (default: web/assets/gems)",
    )
    parser.add_argument("--jpg", action="store_true", help="Generar también .jpg con fondo oscuro")
    parser.add_argument("--jpg-bg", default="0a0a0a", help="Color fondo JPG hex sin #")
    parser.add_argument("--dat", type=Path, help="Ruta Tibia.dat")
    parser.add_argument("--spr", type=Path, help="Ruta Tibia.spr")
    parser.add_argument("--otb", type=Path, help="Ruta items.otb")
    args = parser.parse_args()

    if args.dat and args.spr and args.otb:
        dat_path, spr_path, otb_path = args.dat, args.spr, args.otb
    else:
        dat_path, spr_path, otb_path = find_assets()

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    jpg_bg = tuple(int(args.jpg_bg[i : i + 2], 16) for i in (0, 2, 4))

    dat = DatReader(dat_path.read_bytes())
    spr = SprReader(spr_path.read_bytes())

    print(f"dat: {dat_path} (items={dat.item_count}, sig=0x{dat.signature:08x})")
    print(f"spr: {spr_path} (sprites={spr.sprite_count}, sig=0x{spr.signature:08x})")
    print(f"otb: {otb_path}")
    print(f"out: {out_dir}\n")

    manifest_gems: list[dict] = []

    for gem in GEM_EXPORTS:
        client_id = resolve_client_id(otb_path, gem.server_id)
        sprite_ids = dat.sprite_ids_for_client_item(client_id)
        sprite_id = sprite_ids[0]
        image = spr.decode(sprite_id)
        entry = export_gem(gem, sprite_id, image, out_dir, also_jpg=args.jpg, jpg_bg=jpg_bg)
        entry["clientId"] = client_id
        manifest_gems.append(entry)
        print(f"  ok {entry['files']['png']:16}  {gem.display_name:14}  srv={gem.server_id}  cli={client_id}  spr={sprite_id}")

    manifest = {
        "source": {
            "dat": str(dat_path.relative_to(ROOT)) if dat_path.is_relative_to(ROOT) else str(dat_path),
            "spr": str(spr_path.relative_to(ROOT)) if spr_path.is_relative_to(ROOT) else str(spr_path),
            "otb": str(otb_path.relative_to(ROOT)) if otb_path.is_relative_to(ROOT) else str(otb_path),
            "clientVersion": CLIENT_VERSION,
        },
        "gems": manifest_gems,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nmanifest: {manifest_path}")
    print(f"total: {len(manifest_gems)} gemas, {len(list(out_dir.glob('*.png')))} PNG")
    return 0


if __name__ == "__main__":
    sys.exit(main())
