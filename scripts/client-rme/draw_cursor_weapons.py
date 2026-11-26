#!/usr/bin/env python3
"""Siluetas propias de obsidian falchion (20700) y coral cleaver (20701).

No recolorea un arma vanilla: el dibujo sale de polígonos nuevos.
  python3.11 scripts/client-rme/draw_cursor_weapons.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "devtools" / "zagan-test" / "custom-sprites"


def _solid(image: Image.Image) -> Image.Image:
    image.putdata([(0, 0, 0, 0) if p[3] < 128 else (p[0], p[1], p[2], 255) for p in image.getdata()])
    return image


def obsidian_falchion() -> Image.Image:
    image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    # Empuñadura envuelta y pomo de cobre, abajo a la derecha.
    d.line([(21, 23), (28, 30)], fill=(48, 30, 18), width=4)
    d.line([(22, 23), (27, 28)], fill=(122, 78, 42), width=2)
    d.ellipse([(26, 26), (31, 31)], fill=(150, 72, 34))
    d.ellipse([(27, 27), (29, 29)], fill=(214, 148, 70))
    # Guarda perpendicular a la hoja, con puntas de cobre.
    d.line([(15, 26), (26, 15)], fill=(28, 26, 34), width=3)
    d.polygon([(14, 27), (16, 25), (15, 23), (13, 25)], fill=(196, 112, 58))
    d.polygon([(25, 16), (27, 14), (29, 16), (27, 18)], fill=(196, 112, 58))
    # Hoja curva de obsidiana: panza ancha y punta en gancho. No es una espada recta.
    d.polygon([
        (20, 19), (15, 13), (10, 7), (6, 4), (4, 2),
        (7, 5), (6, 8), (9, 12), (13, 17), (18, 23),
    ], fill=(16, 14, 22))
    d.line([(18, 23), (13, 17), (9, 12), (6, 8), (7, 5), (4, 2)], fill=(214, 170, 112))
    d.line([(19, 18), (14, 12), (10, 7), (7, 4)], fill=(148, 28, 40))
    d.polygon([(4, 2), (2, 1), (3, 4), (6, 4)], fill=(16, 14, 22))
    d.line([(2, 1), (4, 2), (6, 4)], fill=(214, 170, 112))
    return _solid(image)


def coral_cleaver() -> Image.Image:
    image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    # Mango de madera de marea, con dos vueltas de cuerda.
    d.line([(17, 15), (29, 29)], fill=(42, 30, 22), width=4)
    d.line([(18, 15), (27, 26)], fill=(168, 128, 82), width=2)
    d.line([(21, 19), (24, 22)], fill=(232, 206, 140), width=2)
    d.line([(24, 23), (27, 26)], fill=(232, 206, 140), width=2)
    # Cabeza en medialuna de coral: dos quijadas y un hueco, no el perfil del knight axe.
    d.polygon([(5, 9), (9, 2), (17, 4), (16, 9), (11, 9), (7, 12)], fill=(188, 70, 66))
    d.polygon([(7, 14), (6, 20), (14, 19), (18, 13), (15, 10), (10, 12)], fill=(156, 52, 62))
    d.line([(9, 3), (15, 5), (16, 9)], fill=(244, 214, 176))
    d.line([(7, 18), (13, 18), (17, 13)], fill=(244, 214, 176))
    d.polygon([(10, 9), (14, 8), (15, 12), (11, 13)], fill=(24, 86, 92))
    d.polygon([(3, 7), (6, 5), (5, 10)], fill=(220, 108, 86))
    d.point([(12, 4), (8, 17), (15, 15)], fill=(92, 36, 48))
    return _solid(image)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, image in (("obsidian_falchion", obsidian_falchion()), ("coral_cleaver", coral_cleaver())):
        path = args.out_dir / f"{name}.png"
        image.save(path)
        print(path)


if __name__ == "__main__":
    main()
