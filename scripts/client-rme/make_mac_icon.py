#!/usr/bin/env python3
"""Arma el ícono de la app de Mac del cliente Retro76 (Retro76.icns) con sprites del propio Tibia.spr.

Crown Shield (2519) sobre Magic Sword (2400), ampliados sin suavizar, en un cuadrado redondeado oscuro con
borde dorado (los colores de la web: --bg #0d0d0c, --accent #e0aa48). Necesita Pillow.

  python3 scripts/client-rme/make_mac_icon.py ~/apps/clienteretro/mac/Retro76.app/Contents/Resources/Retro76.icns \
      --window-icon ~/apps/clienteretro/mac/data/images/clienticon.png   # (y copiar a windows/)

--window-icon escribe el mismo dibujo en 64x64: es el ícono de la ventana del cliente (client.lua lo carga
con g_window.setIcon) en Mac y Windows.

Doc: docs/CLIENT_UPDATER_RETRO76.md (sección "App de Mac").
"""
from __future__ import annotations

import argparse
import io
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "map" / "kb"))
from add_black_dragon_look import decode_sprite, read_spr  # noqa: E402
from extract_client_sprites import otb_server_to_client, read_dat_items  # noqa: E402

THINGS = ROOT / "devtools/rme/rme-client-760"
OTB = ROOT / "server/YurOTS/ots/data/items/items.otb"
SWORD, SHIELD = 2400, 2519  # magic sword, crown shield (server ids)
BG_TOP, BG_BOTTOM, GOLD = (44, 34, 22), (13, 13, 12), (224, 170, 72)
# icns: tipo -> lado en px (PNG adentro, macOS 10.7+)
ICNS_TYPES = [(b"icp4", 16), (b"icp5", 32), (b"icp6", 64), (b"ic07", 128), (b"ic08", 256),
              (b"ic09", 512), (b"ic10", 1024), (b"ic11", 32), (b"ic12", 64), (b"ic13", 256), (b"ic14", 512)]


def item_image(server_id: int) -> Image.Image:
    dat = (THINGS / "Tibia.dat").read_bytes()
    spr = (THINGS / "Tibia.spr").read_bytes()
    client_id = otb_server_to_client(OTB)[server_id]
    sprite_id = read_dat_items(dat)[client_id]["sprites"][0]
    _, offsets = read_spr(spr)
    im = Image.new("RGBA", (32, 32))
    im.putdata([tuple(p) for p in decode_sprite(spr, offsets, sprite_id)])
    return im


def icon(size: int = 1024) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # cuadrado redondeado de la grilla de íconos de macOS: 824 de 1024, radio ~185
    box = round(size * 824 / 1024)
    off = (size - box) // 2
    radius = round(box * 0.225)
    grad = Image.new("RGBA", (box, box))
    gd = ImageDraw.Draw(grad)
    for y in range(box):
        t = y / (box - 1)
        gd.line([(0, y), (box, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)) + (255,))
    mask = Image.new("L", (box, box), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, box - 1, box - 1], radius, fill=255)
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 110), (off, off + size // 64), mask)
    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(size / 80)))
    canvas.paste(grad, (off, off), mask)
    rim = size // 100
    ImageDraw.Draw(canvas).rounded_rectangle([off + rim, off + rim, off + box - 1 - rim, off + box - 1 - rim],
                                             radius - rim, outline=GOLD + (255,), width=max(1, size // 128))

    def put(im: Image.Image, scale: int, cx: float, cy: float) -> None:
        big = im.resize((32 * scale, 32 * scale), Image.NEAREST)
        canvas.alpha_composite(big, (round(cx - big.width / 2), round(cy - big.height / 2)))

    unit = size / 1024
    put(item_image(SWORD), round(18 * unit) or 1, size * 0.5, size * 0.5)
    put(item_image(SHIELD), round(14 * unit) or 1, size * 0.5, size * 0.53)
    return canvas


def write_icns(master: Image.Image, out: Path) -> None:
    chunks = []
    for kind, side in ICNS_TYPES:
        buf = io.BytesIO()
        master.resize((side, side), Image.LANCZOS if side < 256 else Image.NEAREST).save(buf, "PNG")
        data = buf.getvalue()
        chunks.append(kind + struct.pack(">I", len(data) + 8) + data)
    body = b"".join(chunks)
    out.write_bytes(b"icns" + struct.pack(">I", len(body) + 8) + body)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", type=Path, help="archivo .icns a escribir")
    ap.add_argument("--png", type=Path, help="además, el ícono en PNG 1024x1024")
    ap.add_argument("--window-icon", type=Path, help="además, el ícono de la ventana (PNG 64x64)")
    a = ap.parse_args()
    master = icon(1024)
    write_icns(master, a.out)
    if a.png:
        master.save(a.png)
    if a.window_icon:
        master.resize((64, 64), Image.LANCZOS).save(a.window_icon)
    print(f"ícono: {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
