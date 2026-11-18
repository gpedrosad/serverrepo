#!/usr/bin/env python3
"""Saca los 2 sprites del coal bassin del cliente y pasa su llama a azul.

El coal bassin de 7.6 (server id 1483, client id 2112) es un brasero 1x1 animado en
2 cuadros: media casilla de fuego (tonos 0-60 y 325-360, saturación > 0.5, brillo
> 0.15) sobre un basin de hierro con contorno negro y una mata verde en la base.
Pasarlo a azul sin tocar el hierro es intercambiar los canales rojo/azul de esos
píxeles, con la misma saturación y brillo: (207,4,4) -> (4,4,207) azul profundo,
(255,108,0) -> (0,108,255) celeste, (255,203,0) -> (0,203,255) cian. La luz la
cambia add_custom_items.py (nivel 8, cálida 206 -> azul 143, la del magic tree del
templo), en el flag .dat 0x15 y el attr OTB 0x2A.

  python3.11 scripts/client-rme/recolor_basin.py --preview /tmp/blue_basin.png

Escribe devtools/zagan-test/custom-sprites/blue_basin.png (32x64: cuadro 0 arriba,
cuadro 1 abajo). Doc: docs/items-and-map/ZAGAN_TEST_ITEMS.md. Necesita Pillow (en
la Mac: python3.11).
"""
from __future__ import annotations

import argparse
import colorsys
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build_zagan_test_assets as B  # noqa: E402
from add_black_dragon_look import decode_sprite, read_spr  # noqa: E402

CLIENT_ID = 2112          # coal bassin (server 1483)
OUT = ROOT / "devtools/zagan-test/custom-sprites/blue_basin.png"


def is_fire(r: int, g: int, b: int) -> bool:
    """Fuego del bassin: rojos, naranjas y amarillos saturados. El hierro (grises y
    negros, saturación baja o brillo muy bajo) y la mata verde de la base (tonos
    60-160) quedan afuera."""
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hd = h * 360
    return (hd <= 60 or hd >= 325) and s > 0.5 and v > 0.15


def fire_to_blue(r: int, g: int, b: int) -> tuple[int, int, int]:
    return (b, g, r) if is_fire(r, g, b) else (r, g, b)


def frame(entry, spr, offsets, index: int, swap: bool) -> Image.Image:
    """Un cuadro 32x32 del bassin."""
    pixels = decode_sprite(spr, offsets, entry.sprite_ids[index])
    img = Image.new("RGBA", (32, 32))
    img.putdata([(0, 0, 0, 0) if not p[3] else
                 ((fire_to_blue(*p[:3]) if swap else p[:3]) + (255,))
                 for p in pixels])
    return img


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--things", type=Path, default=ROOT / "devtools/rme/rme-client-760")
    ap.add_argument("--preview", type=Path, help="PNG con los 2 cuadros originales y azules, a 8x")
    a = ap.parse_args()

    entries, _tail = B.DatReader((a.things / "Tibia.dat").read_bytes()).read_item_entries()
    entry = next((e for e in entries if e.client_id == CLIENT_ID), None)
    if entry is None or len(entry.sprite_ids) != 2:
        raise SystemExit(f"client id {CLIENT_ID}: no existe o no tiene 2 sprites (1x1 x 2 cuadros)")
    spr = (a.things / "Tibia.spr").read_bytes()
    _n, offsets = read_spr(spr)

    out = Image.new("RGBA", (32, 64))
    for f in range(2):
        out.paste(frame(entry, spr, offsets, f, swap=True), (0, 32 * f))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT)
    blues = sum(1 for p in out.getdata() if p[3] and p[2] > p[0] + 40 and p[2] > p[1] + 40)
    print(f"{OUT} ({blues} píxeles azul-dominantes)")
    if a.preview:
        sheet = Image.new("RGB", (4 * 264 + 8, 268), (40, 40, 46))
        for i, swap in enumerate((False, True)):
            for f in range(2):
                big = frame(entry, spr, offsets, f, swap).resize((256, 256), Image.NEAREST)
                sheet.paste(big, (4 + (i * 2 + f) * 264, 4), big)
        sheet.save(a.preview)
        print(f"vista previa: {a.preview}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
