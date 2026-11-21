#!/usr/bin/env python3
"""Dibuja las 6 cajas de regalo de nivel (docs/gameplay/LEVEL_UP_REWARDS.md) recoloreando el "present"
de 7.6 (server 1990, client 2856): la caja y el moño se pasan, por luminosidad, a la rampa de cada rango.

  python3.11 scripts/client-rme/make_level_gifts.py                 # escribe los PNG
  python3.11 scripts/client-rme/make_level_gifts.py --preview x.png # hoja con las 6 sobre 3 fondos

Los PNG van a devtools/zagan-test/custom-sprites/level_gift_*.png y los instala add_custom_items.py
(server ids 20354-20359).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from add_black_dragon_look import decode_sprite, read_spr  # noqa: E402

CLIENT = ROOT / "devtools" / "rme" / "rme-client-760"
OUT = ROOT / "devtools" / "zagan-test" / "custom-sprites"
PRESENT_SPRITE = 2160          # client 2856 (present 1990), 1x1, un cuadro

# Rampas de oscuro a claro: (caja, moño)
GREEN = [(6, 40, 10), (20, 92, 28), (44, 150, 52), (96, 204, 92), (176, 240, 160)]
BLUE = [(2, 4, 64), (40, 46, 146), (66, 72, 176), (120, 128, 236), (170, 176, 252)]
PURPLE = [(36, 6, 58), (86, 30, 128), (128, 60, 180), (176, 110, 226), (226, 180, 252)]
SILVER = [(50, 56, 68), (112, 120, 136), (164, 172, 186), (210, 216, 226), (246, 248, 252)]
GOLD = [(84, 44, 0), (166, 104, 0), (220, 160, 16), (250, 206, 60), (255, 244, 170)]
CRIMSON = [(40, 0, 8), (96, 6, 22), (150, 16, 36), (200, 40, 56), (240, 110, 110)]
RED = [(70, 0, 6), (130, 10, 24), (176, 24, 40), (222, 60, 70), (255, 140, 140)]
WHITE = [(90, 90, 100), (160, 160, 172), (206, 206, 216), (236, 236, 244), (255, 255, 255)]

GIFTS = [
    ("level_gift_novice.png", GREEN, RED),
    ("level_gift_adventurer.png", BLUE, GOLD),
    ("level_gift_veteran.png", PURPLE, WHITE),
    ("level_gift_champion.png", SILVER, CRIMSON),
    ("level_gift_heroic.png", GOLD, RED),
    ("level_gift_legendary.png", CRIMSON, GOLD),
]


def ramp_at(ramp, t):
    t = min(max(t, 0.0), 1.0) * (len(ramp) - 1)
    i = min(int(t), len(ramp) - 2)
    f = t - i
    return tuple(round(a + (b - a) * f) for a, b in zip(ramp[i], ramp[i + 1]))


def recolor(pixels, box, ribbon):
    """La caja original es azul (b manda) y el moño rojo (r manda). Se mapea la luminosidad de cada
    píxel, normalizada en su grupo, a la rampa nueva; así se conservan sombras, brillo y contorno."""
    def lum(p):
        return 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]

    groups = {"box": [], "ribbon": []}
    for p in pixels:
        if p[3]:
            groups["ribbon" if p[0] > p[2] else "box"].append(lum(p))
    span = {k: (min(v), max(v)) for k, v in groups.items()}
    out = []
    for p in pixels:
        if not p[3]:
            out.append((0, 0, 0, 0))
            continue
        key = "ribbon" if p[0] > p[2] else "box"
        lo, hi = span[key]
        t = (lum(p) - lo) / max(hi - lo, 1e-6)
        out.append(ramp_at(ribbon if key == "ribbon" else box, t) + (255,))
    return out


def gift_images():
    spr = (CLIENT / "Tibia.spr").read_bytes()
    _count, offsets = read_spr(spr)
    base = decode_sprite(spr, offsets, PRESENT_SPRITE)
    for name, box, ribbon in GIFTS:
        im = Image.new("RGBA", (32, 32))
        im.putdata(recolor(base, box, ribbon))
        yield name, im


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()
    images = list(gift_images())
    if a.preview:
        scale = 4
        sheet = Image.new("RGB", (len(images) * 34 * scale, 3 * 34 * scale))
        for row, bg in enumerate(((38, 38, 44), (226, 222, 210), (70, 110, 60))):
            for col, (_name, im) in enumerate(images):
                tile = Image.new("RGB", (34 * scale, 34 * scale), bg)
                big = im.resize((32 * scale, 32 * scale), Image.NEAREST)
                tile.paste(big, (scale, scale), big)
                sheet.paste(tile, (col * 34 * scale, row * 34 * scale))
        sheet.save(a.preview)
        print(f"Vista previa: {a.preview}")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for name, im in images:
        im.save(OUT / name)
        print(f"  {OUT / name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
