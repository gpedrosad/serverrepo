#!/usr/bin/env python3
"""Original Azure Sunstone and a seamless, animated crust for the blue lava."""
from __future__ import annotations

from math import pi, sin, sqrt
from pathlib import Path
from random import Random

from PIL import Image, ImageDraw

SPRITES = Path(__file__).resolve().parents[2] / "devtools/zagan-test/custom-sprites"
LAVA_WIDTH, LAVA_HEIGHT = 128, 64


def sunstone() -> Image.Image:
    image = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(image)
    # Bent brass prongs cradle the crystal and make the artifact read separately from gems.
    d.polygon([(5, 13), (6, 8), (12, 4), (16, 2), (19, 5), (24, 6), (27, 9),
               (27, 13), (29, 16), (26, 20), (25, 24), (21, 28), (17, 29),
               (13, 27), (8, 26), (5, 22), (4, 18), (2, 16)], fill="#211c2b")
    d.polygon([(6, 13), (7, 9), (13, 5), (16, 3), (19, 6), (23, 7), (26, 10),
               (26, 14), (28, 16), (25, 19), (24, 23), (21, 27), (17, 28),
               (13, 26), (8, 25), (6, 22), (5, 18), (3, 16)], fill="#765046")
    d.polygon([(5, 16), (8, 11), (10, 7), (15, 6), (16, 4), (19, 7), (23, 8),
               (24, 12), (27, 16), (23, 17), (21, 23), (17, 26), (14, 24),
               (10, 25), (10, 22), (6, 20)], fill="#c49161")
    d.line([(5, 16), (8, 13), (10, 8), (15, 6), (16, 4)], fill="#f2d3a3")
    d.line([(19, 7), (23, 8), (25, 13)], fill="#e8b47d")
    d.line([(8, 22), (10, 24), (13, 25), (17, 27)], fill="#e2ac77")
    d.polygon([(9, 13), (13, 8), (18, 8), (22, 11), (24, 16), (21, 21),
               (17, 24), (12, 22), (9, 19), (8, 16)], fill="#243451")
    d.polygon([(10, 13), (13, 9), (18, 9), (21, 12), (23, 16), (20, 20),
               (17, 23), (12, 21), (9, 17)], fill="#2d5d82")
    d.polygon([(10, 13), (13, 9), (18, 9), (17, 13), (14, 16), (9, 17)],
              fill="#3d91a6")
    d.line([(11, 13), (13, 10), (16, 10)], fill="#87d1d7")
    d.polygon([(16, 10), (18, 14), (21, 16), (17, 17), (16, 21), (14, 18),
               (11, 16), (14, 14)], fill="#6dd3d4")
    d.polygon([(16, 12), (17, 15), (19, 16), (16, 17), (16, 19), (15, 17),
               (13, 16), (15, 15)], fill="#d3f7e8")
    d.point([(16, 16), (13, 11)], fill="#fff4d7")
    d.line([(20, 22), (22, 18), (24, 16), (27, 16)], fill="#f2d3a3")
    d.point([(6, 16), (17, 26), (25, 17)], fill="#ffebbd")
    return image


def lava_frames() -> list[Image.Image]:
    """A periodic field of basalt slabs above moving seams of cold fire."""
    random = Random(4217)
    w, h = LAVA_WIDTH, LAVA_HEIGHT
    sites = [(col * w / 6 + random.uniform(-8, 8), row * h / 3 + random.uniform(-7, 7),
              random.randrange(5)) for row in range(3) for col in range(6)]
    slab = ("#30283b", "#312a42", "#332c43", "#382d46", "#3e3047")
    cracks = ("#315978", "#427494", "#57a2af", "#78c8cb", "#bdede1")
    frames = [Image.new("RGB", (w, h)) for _ in range(4)]
    pixels = [frame.load() for frame in frames]
    for y in range(h):
        for x in range(w):
            u = x + 2.9 * sin(2 * pi * y / h) + 1.1 * sin(2 * pi * (2 * x / w + 3 * y / h))
            v = y + 2.6 * sin(4 * pi * x / w) + 1.5 * sin(2 * pi * (5 * x / w - y / h))
            distances = []
            for sx, sy, variation in sites:
                dx = (u - sx + w / 2) % w - w / 2
                dy = (v - sy + h / 2) % h - h / 2
                distances.append((dx * dx + dy * dy, dx, dy, variation))
            (near, dx, dy, variation), (far, *_rest) = sorted(distances)[:2]
            gap = sqrt(far) - sqrt(near)
            channel = sin(2 * pi * (3 * x / w - y / h)) + sin(2 * pi * (x / w + 2 * y / h))
            seam = 0.9 + max(0.0, channel - 0.6)
            speckle = (x * 9 + y * 7 + (x * y) % 31) % 121
            for phase, output in enumerate(pixels):
                heat = sin(2 * pi * (2 * x / w + 3 * y / h - phase / 4))
                if gap < seam:
                    color = cracks[2 + (heat > 0.05) + (heat > 0.62 and gap < seam / 3)]
                elif gap < seam + 0.8:
                    color = cracks[int(heat > 0.05)]
                elif gap < seam + 1.7:
                    color = "#29384e" if dx + dy > 0 else "#4b4d6b"
                    if heat > 0.6 and speckle == 0:
                        color = cracks[3]
                else:
                    band = variation + int(dx + dy < -3) - int(dx + dy > 8)
                    color = slab[max(0, min(4, band))]
                    if speckle < 4:
                        color = "#534258" if dx + dy < 0 else "#27243a"
                output[x, y] = RGB[color]
    return frames


# Convert the small palette once, outside the texture loop.
RGB = {color: tuple(bytes.fromhex(color[1:])) for color in
       ("#30283b", "#312a42", "#332c43", "#382d46", "#3e3047",
        "#315978", "#427494", "#57a2af", "#78c8cb", "#bdede1",
        "#29384e", "#4b4d6b", "#534258", "#27243a")}


def lava_sheet() -> Image.Image:
    sheet = Image.new("RGBA", (32, 32 * 32))
    for phase, frame in enumerate(lava_frames()):
        for pattern in range(8):
            x, y = 32 * (pattern % 4), 32 * (pattern // 4)
            sheet.paste(frame.crop((x, y, x + 32, y + 32)), (0, 32 * (phase * 8 + pattern)))
    return sheet


def main() -> None:
    sunstone().save(SPRITES / "azure_sunstone.png")
    lava_sheet().save(SPRITES / "blue_lava.png")


if __name__ == "__main__":
    main()
