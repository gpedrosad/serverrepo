#!/usr/bin/env python3
"""Sprites originales del kit de ceniza: visor, escudo cometa y flail.

Geometría dibujada píxel a píxel. No parte de un sprite vanilla ni cambia su paleta.
32x32, sin suavizado. Los PNG los instala add_custom_items.py.

  python3.11 scripts/client-rme/draw_cinder_kit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.project_root import project_root

ROOT = project_root()
OUT = ROOT / "devtools/zagan-test/custom-sprites"
PREVIEW = ROOT / "docs/items-and-map/img/cinder-kit.png"

INK = (12, 10, 14, 255)
IRON = (92, 96, 108, 255)
IRON_DK = (48, 50, 58, 255)
IRON_LT = (176, 180, 192, 255)
GLASS = (36, 28, 22, 255)
AMBER = (232, 146, 28, 255)
AMBER_LT = (255, 214, 112, 255)
SOOT = (36, 28, 30, 255)
SOOT_LT = (78, 56, 48, 255)
COPPER = (186, 102, 42, 255)
COPPER_LT = (236, 168, 78, 255)
EMBER = (214, 72, 28, 255)
EMBER_LT = (255, 168, 64, 255)


def blank() -> Image.Image:
    return Image.new("RGBA", (32, 32), (0, 0, 0, 0))


def outline(image: Image.Image) -> None:
    """Borde de 1 px sobre los píxeles que tocan transparencia. Sin antialias."""
    src = image.copy()
    sp, dp = src.load(), image.load()
    for y in range(32):
        for x in range(32):
            if sp[x, y][3] == 0:
                continue
            if any(
                nx < 0 or ny < 0 or nx >= 32 or ny >= 32 or sp[nx, ny][3] == 0
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
            ):
                dp[x, y] = INK


def visor() -> Image.Image:
    """Casco frontal cerrado: cilindro, ranura ámbar y carrilleras. No es un steel helmet de perfil."""
    image = blank()
    d = ImageDraw.Draw(image)
    d.polygon([(16, 4), (23, 8), (23, 14), (16, 17), (9, 14), (9, 8)], fill=IRON)
    d.polygon([(16, 5), (21, 8), (21, 12), (16, 14), (11, 12), (11, 8)], fill=IRON_LT)
    d.polygon([(10, 14), (22, 14), (24, 20), (20, 26), (12, 26), (8, 20)], fill=IRON_DK)
    d.rectangle((11, 17, 20, 19), fill=GLASS)
    d.rectangle((12, 18, 19, 18), fill=AMBER)
    d.point((13, 18), fill=AMBER_LT)
    d.rectangle((12, 13, 13, 14), fill=COPPER)
    d.rectangle((18, 13, 19, 14), fill=COPPER)
    d.polygon([(8, 18), (11, 18), (12, 24), (9, 24)], fill=IRON)
    d.polygon([(21, 18), (24, 18), (23, 24), (20, 24)], fill=IRON)
    d.rectangle((13, 24, 18, 26), fill=COPPER_LT)
    outline(image)
    return image


def kite() -> Image.Image:
    """Escudo cometa alto, con chevron de cobre. No es el rectángulo redondeado de un guardian/crown shield."""
    image = blank()
    d = ImageDraw.Draw(image)
    d.polygon([(16, 2), (26, 12), (16, 30), (6, 12)], fill=SOOT)
    d.polygon([(16, 6), (22, 12), (16, 26), (10, 12)], fill=SOOT_LT)
    d.polygon([(16, 8), (22, 14), (16, 18), (10, 14)], fill=COPPER)
    d.polygon([(16, 10), (20, 14), (16, 16), (12, 14)], fill=COPPER_LT)
    d.line([(16, 18), (16, 24)], fill=EMBER, width=1)
    d.point((16, 24), fill=EMBER_LT)
    outline(image)
    return image


def flail() -> Image.Image:
    """Mango corto, tres eslabones separados y una bola con púas. La cadena lo separa de una maza."""
    image = blank()
    px = image.load()

    def blob(cx: int, cy: int, color) -> None:
        for y in range(cy - 1, cy + 2):
            for x in range(cx - 1, cx + 2):
                px[x, y] = color
        px[cx, cy] = IRON_LT

    for x, y in ((8, 29), (9, 29), (9, 28), (10, 28), (10, 27), (11, 27), (11, 26), (12, 26), (12, 25)):
        px[x, y] = COPPER
        px[x + 1, y] = COPPER_LT
    # Tres eslabones con un hueco transparente entre cada uno.
    blob(14, 22, IRON)
    blob(17, 18, IRON)
    blob(20, 14, IRON)
    for y in range(6, 15):
        for x in range(20, 29):
            if (x - 24) ** 2 + (y - 10) ** 2 <= 12:
                px[x, y] = EMBER
            if (x - 23) ** 2 + (y - 9) ** 2 <= 3:
                px[x, y] = EMBER_LT
    for x, y in ((24, 4), (24, 5), (29, 9), (29, 10), (24, 15), (24, 16), (19, 9), (19, 10)):
        px[x, y] = AMBER_LT
    outline(image)
    return image


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    images = {"ashglass_visor.png": visor(), "cinder_kite.png": kite(), "cinder_flail.png": flail()}
    for name, image in images.items():
        if image.size != (32, 32):
            raise SystemExit(name)
        image.save(OUT / name)
    sheet = Image.new("RGBA", (32 * 3 * 4 + 16, 32 * 4), (40, 44, 48, 255))
    for i, image in enumerate(images.values()):
        sheet.alpha_composite(image.resize((128, 128), Image.NEAREST), (8 + i * 128, 0))
    sheet.save(PREVIEW)
    print(f"png en {OUT}")
    print(f"preview {PREVIEW}")


if __name__ == "__main__":
    main()
