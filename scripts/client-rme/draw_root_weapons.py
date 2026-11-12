#!/usr/bin/env python3
"""Sprites reproducibles de Rootcleaver y Heartwood Maul, a partir de armas vanilla.

  python3.11 scripts/client-rme/draw_root_weapons.py --preview docs/gameplay/img/root-weapons.png

Escribe PNG de 32x32, sin suavizado. Aplicar despues con add_custom_items.py.
"""
from __future__ import annotations

import argparse
import colorsys
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.project_root import project_root
from recolor_item import item_pixels

ROOT = project_root()
THINGS = ROOT / "devtools/rme/rme-client-760"
OUT = ROOT / "devtools/zagan-test/custom-sprites"


def rootcleaver(things):
    image = Image.new("RGBA", (32, 32))
    pixels = []
    for r, g, b, a in item_pixels(things, 3318):  # knight axe
        if not a:
            pixels.append((0, 0, 0, 0))
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.25:
            # Hoja de jade: conserva las luces y el filo del hacha original.
            rgb = (int(10 + 120 * v), int(24 + 215 * v), int(16 + 150 * v))
        else:
            rgb = (int(28 + 125 * v), int(18 + 86 * v), int(9 + 35 * v))
        pixels.append((*rgb, 255))
    image.putdata(pixels)
    d = ImageDraw.Draw(image)
    # Vides abrazan el mango; la base sigue siendo un axe reconocible de una mano.
    d.line([(15, 14), (13, 17), (16, 20), (13, 23), (16, 26), (15, 30)], fill=(22, 42, 13), width=2)
    d.line([(15, 14), (13, 17), (16, 20), (13, 23), (16, 26), (15, 30)], fill=(109, 148, 46))
    d.line([(13, 23), (10, 22), (9, 20)], fill=(111, 78, 32))
    d.polygon([(8, 19), (11, 20), (10, 22), (7, 21)], fill=(52, 108, 35))
    d.line([(9, 20), (10, 21)], fill=(148, 191, 72))
    d.polygon([(15, 8), (18, 11), (15, 14), (12, 11)], fill=(191, 145, 58))
    d.polygon([(15, 9), (17, 11), (15, 13), (13, 11)], fill=(24, 112, 73))
    d.line([(15, 9), (14, 11), (15, 12)], fill=(177, 249, 184))
    return image


def heartwood_maul(things):
    image = Image.new("RGBA", (32, 32))
    pixels = []
    for i, (r, g, b, a) in enumerate(item_pixels(things, 3279)):  # war hammer
        if not a:
            pixels.append((0, 0, 0, 0))
            continue
        x, y = i % 32, i // 32
        v = max(r, g, b) / 255
        rgb = (int(18 + 170 * v), int(14 + 118 * v), int(8 + 61 * v))
        # Vetas dentro de la cabeza del martillo, sin alterar el fondo transparente.
        if x + y < 30 and (x - y) % 6 == 0:
            rgb = (32, 27, 15)
        pixels.append((*rgb, 255))
    image.putdata(pixels)
    d = ImageDraw.Draw(image)
    # Aros de raiz que sujetan el bloque de madera, con un corazon verde en el centro.
    for pts in [[(9, 5), (13, 8), (15, 12)], [(4, 11), (8, 14), (10, 18)]]:
        d.line(pts, fill=(30, 37, 17), width=3)
        d.line(pts, fill=(101, 139, 42))
    d.polygon([(11, 8), (15, 10), (13, 14), (9, 12)], fill=(35, 49, 20))
    d.polygon([(11, 9), (14, 10), (12, 13), (10, 12)], fill=(39, 126, 64))
    d.line([(11, 9), (11, 11), (12, 12)], fill=(197, 241, 130))
    d.line([(18, 20), (21, 20), (22, 24), (26, 24), (27, 28)], fill=(34, 47, 18), width=2)
    d.line([(18, 20), (21, 20), (22, 24), (26, 24), (27, 28)], fill=(117, 148, 54))
    return image


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--things", type=Path, default=THINGS)
    ap.add_argument("--out-dir", type=Path, default=OUT)
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    images = [("rootcleaver", rootcleaver(a.things)), ("heartwood_maul", heartwood_maul(a.things))]
    for name, image in images:
        path = a.out_dir / (name + ".png")
        image.save(path)
        print(path)
    if a.preview:
        sheet = Image.new("RGB", (528, 264), (38, 42, 36))
        for i, (_name, image) in enumerate(images):
            big = image.resize((256, 256), Image.Resampling.NEAREST)
            sheet.paste(big, (i * 264 + 4, 4), big)
        a.preview.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(a.preview)
        print(a.preview)


if __name__ == "__main__":
    main()
