#!/usr/bin/env python3
"""Draw the Caldera loot and install the Devilwing Rune missile."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from add_throwing_fireball import ANGLES, THINGS, install_missile

SPRITES = Path(__file__).resolve().parents[2] / "devtools/zagan-test/custom-sprites"
DEVILWING_MISSILE = 22
INK = "#1b1c2b"
LOW = "#293751"
TEAL = "#235d72"
BLUE = "#388ba0"
ICE = "#6ccbd1"
WHITE = "#e4f8ea"
BRONZE = "#936351"
GOLD = "#e1b97f"


def rimeglass_buckler():
    image = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(image)
    d.polygon([(7, 6), (16, 2), (23, 5), (27, 10), (26, 18), (22, 25),
               (17, 30), (12, 27), (7, 22), (5, 14), (5, 10)], fill=INK)
    d.polygon([(8, 7), (16, 3), (22, 6), (26, 10), (25, 18), (21, 25),
               (17, 29), (12, 26), (8, 22), (6, 14), (6, 10)], fill="#5d6e83")
    d.polygon([(9, 8), (16, 5), (21, 7), (24, 11), (24, 16), (20, 24),
               (17, 27), (13, 24), (9, 21), (8, 14)], fill=TEAL)
    d.polygon([(9, 8), (16, 5), (20, 8), (17, 13), (17, 25), (15, 24),
               (10, 21), (8, 14)], fill=BLUE)
    d.polygon([(9, 10), (15, 7), (16, 9), (14, 12), (10, 17)], fill=ICE)
    d.polygon([(17, 22), (20, 16), (23, 13), (23, 17), (20, 23), (17, 27)], fill="#33758c")
    d.line([(8, 7), (13, 5), (16, 3), (21, 6), (24, 8)], fill=WHITE)
    d.line([(7, 10), (6, 13), (8, 19)], fill="#b2d2cb")
    d.polygon([(13, 14), (17, 10), (21, 14), (20, 17), (17, 21), (14, 18)], fill=INK)
    d.polygon([(14, 14), (17, 11), (20, 14), (19, 17), (17, 20), (15, 17)], fill=BLUE)
    d.line([(15, 14), (17, 12), (18, 13), (17, 15)], fill=WHITE)
    d.point([(8, 21), (17, 27), (24, 17)], fill=GOLD)
    return image


def devilwing_rune():
    image = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(image)
    d.polygon([(8, 11), (14, 6), (20, 7), (24, 11), (25, 18), (22, 23),
               (17, 26), (10, 24), (7, 20), (6, 15)], fill=INK)
    d.polygon([(8, 12), (14, 7), (20, 8), (23, 11), (24, 18), (21, 23),
               (17, 25), (10, 23), (8, 20), (7, 15)], fill="#4d455c")
    d.polygon([(9, 12), (14, 8), (20, 9), (22, 12), (21, 18),
               (15, 22), (10, 22), (8, 17)], fill="#6f6375")
    d.line([(8, 13), (11, 10), (14, 8), (18, 8)], fill="#a9a0ac")
    d.polygon([(10, 13), (15, 14), (21, 10), (22, 11), (20, 15), (22, 18),
               (18, 17), (15, 22), (13, 21), (14, 17)], fill=LOW)
    d.polygon([(11, 13), (15, 15), (21, 11), (19, 15), (20, 17),
               (17, 16), (14, 20), (15, 17)], fill=TEAL)
    d.line([(12, 14), (15, 15), (18, 13), (21, 11)], fill=ICE)
    d.line([(15, 19), (16, 16), (18, 15)], fill=WHITE)
    d.point([(12, 10), (19, 22), (9, 18)], fill="#87768f")
    return image


def ridgecarver():
    image = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(image)
    d.line([(12, 12), (27, 28)], fill=INK, width=6)
    d.line([(12, 12), (27, 28)], fill="#5b434b", width=4)
    d.line([(12, 11), (26, 26)], fill=BRONZE, width=2)
    for x, y in ((21, 22), (23, 24), (25, 26)):
        d.line([(x - 1, y), (x + 1, y - 2)], fill=LOW, width=2)
        d.point((x, y - 1), fill="#b0c4bd")
    d.polygon([(23, 26), (26, 24), (30, 27), (31, 30), (28, 31), (25, 30)], fill=INK)
    d.polygon([(25, 27), (27, 26), (29, 28), (29, 30), (27, 30)], fill=BRONZE)
    d.point((27, 27), fill=GOLD)
    d.polygon([(8, 2), (11, 6), (17, 3), (18, 8), (24, 9), (22, 13),
               (18, 15), (15, 16), (13, 22), (8, 23), (5, 22), (3, 19),
               (2, 15), (3, 10), (5, 6)], fill=INK)
    d.polygon([(8, 3), (10, 7), (16, 5), (17, 9), (22, 10), (21, 12),
               (17, 14), (14, 16), (12, 21), (8, 22), (5, 21), (4, 18),
               (3, 15), (4, 10), (6, 6)], fill=TEAL)
    d.polygon([(8, 3), (9, 7), (6, 11), (5, 16), (6, 19), (9, 20),
               (12, 19), (11, 21), (8, 22), (5, 21), (4, 18), (3, 15),
               (4, 10), (6, 6)], fill="#bad6cf")
    d.line([(8, 3), (6, 7), (4, 12), (4, 16), (6, 20), (8, 21)], fill=WHITE)
    d.polygon([(8, 14), (11, 10), (16, 6), (16, 9), (13, 13), (10, 18),
               (8, 19), (7, 17)], fill=BLUE)
    d.line([(8, 17), (11, 13), (14, 10), (16, 6)], fill=ICE)
    d.line([(14, 13), (17, 11), (22, 10)], fill=ICE)
    d.polygon([(12, 12), (15, 11), (18, 13), (17, 16), (14, 18), (11, 16)], fill=LOW)
    d.line([(12, 13), (15, 12), (17, 13)], fill="#acaaa4")
    d.point((14, 14), fill=GOLD)
    return image


def wake_lantern(phase):
    image = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(image)
    d.line([(12, 8), (12, 5), (14, 3), (18, 3), (21, 5), (21, 8)], fill=INK, width=3)
    d.line([(13, 7), (13, 5), (15, 3), (18, 4), (20, 6), (20, 8)], fill=GOLD)
    d.polygon([(13, 7), (20, 7), (24, 10), (26, 13), (24, 17), (24, 23),
               (21, 27), (18, 29), (12, 28), (8, 25), (7, 18), (6, 13), (9, 10)], fill=INK)
    d.polygon([(13, 8), (20, 8), (23, 11), (25, 13), (23, 17), (23, 23),
               (20, 27), (17, 28), (12, 27), (9, 24), (8, 18), (7, 13), (10, 11)], fill=BRONZE)
    d.polygon([(11, 13), (16, 11), (21, 12), (22, 15), (21, 22), (18, 25),
               (14, 25), (10, 23), (9, 18)], fill=TEAL)
    d.polygon([(11, 16), (14, 13), (19, 13), (21, 16), (20, 22), (17, 24),
               (14, 24), (11, 21)], fill=BLUE)
    tip = ((0, -7), (1, -8), (0, -6), (-1, -8))[phase]
    flame = [(-4, 0), (-3, -4), (-2, -2), tip, (2, -5), (2, -3),
             (4, -1), (3, 1), (0, 3), (-2, 2)]
    d.polygon([(x + 16, y + 21) for x, y in flame], fill=ICE)
    d.line([(15, 22), (17, 19), (16 + tip[0], 22 + tip[1])], fill=WHITE)
    d.line([(8, 13), (12, 10), (17, 9), (22, 11)], fill="#ffe2aa")
    d.line([(9, 15), (10, 22), (13, 26), (18, 27), (22, 24)], fill=GOLD)
    d.line([(22, 14), (21, 23)], fill="#edc592")
    d.point([(12, 12), (19, 25)], fill=WHITE)
    return image


def azhurak_crown():
    image = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(image)
    d.polygon([(4, 7), (9, 10), (11, 14), (13, 10), (14, 6), (18, 2),
               (19, 9), (22, 12), (25, 8), (29, 5), (29, 11), (27, 16),
               (26, 23), (22, 27), (13, 29), (7, 26), (5, 20), (4, 15)], fill=INK)
    d.polygon([(5, 9), (9, 12), (12, 16), (14, 11), (15, 7), (17, 4),
               (18, 10), (22, 14), (26, 9), (28, 7), (28, 11), (25, 17),
               (25, 23), (21, 26), (13, 28), (8, 25), (6, 20), (5, 15)], fill="#4e3e52")
    d.polygon([(6, 11), (9, 13), (13, 18), (13, 23), (9, 22), (7, 18)], fill=TEAL)
    d.line([(6, 11), (9, 15), (12, 18)], fill=ICE)
    d.polygon([(14, 12), (16, 6), (17, 5), (18, 10), (21, 15),
               (19, 18), (14, 17)], fill=BLUE)
    d.line([(14, 14), (16, 10), (17, 6)], fill=WHITE)
    d.polygon([(23, 15), (27, 10), (28, 9), (27, 14), (24, 19)], fill=TEAL)
    d.line([(23, 16), (26, 13), (27, 10)], fill=ICE)
    d.polygon([(7, 19), (12, 21), (18, 20), (23, 18), (25, 17), (25, 22),
               (22, 25), (14, 27), (9, 25)], fill=BRONZE)
    d.line([(8, 19), (12, 21), (18, 20), (24, 18)], fill=GOLD)
    d.line([(10, 24), (14, 26), (21, 24)], fill="#b28063")
    d.polygon([(13, 21), (16, 17), (20, 20), (18, 23), (15, 24)], fill=INK)
    d.polygon([(14, 21), (16, 18), (18, 20), (17, 22), (15, 23)], fill=BLUE)
    d.line([(15, 21), (16, 19), (17, 20)], fill=WHITE)
    d.point([(10, 22), (21, 22), (23, 20)], fill=GOLD)
    return image


def projectile_frames():
    east = Image.new("RGBA", (32, 32))
    d = ImageDraw.Draw(east)
    d.polygon([(2, 3), (12, 6), (20, 10), (27, 11), (31, 15), (27, 19), (21, 20),
               (14, 24), (3, 27), (7, 21), (12, 16), (7, 11)], fill=LOW)
    d.polygon([(4, 4), (13, 8), (20, 12), (26, 12), (30, 15), (26, 18), (19, 18),
               (13, 22), (5, 25), (9, 20), (14, 16), (10, 12)], fill=BLUE)
    d.polygon([(8, 7), (15, 10), (20, 13), (26, 13), (29, 15), (25, 17), (19, 17),
               (14, 20), (9, 22), (15, 16), (13, 13)], fill=ICE)
    d.line([(11, 9), (16, 11), (21, 14), (27, 15), (22, 16), (17, 18), (13, 20)], fill=WHITE)
    d.line([(13, 14), (17, 16), (20, 15)], fill="#bc9fd0")
    d.point([(1, 12), (5, 16), (2, 20), (11, 2), (10, 26)], fill="#9d91c0")
    return [None if angle is None else east.rotate(angle, resample=Image.Resampling.NEAREST)
            for angle in ANGLES]


def item_art():
    return [
        ("Rimeglass Buckler", [rimeglass_buckler()]),
        ("Devilwing Rune", [devilwing_rune()]),
        ("Ridgecarver", [ridgecarver()]),
        ("Wake Lantern", [wake_lantern(i) for i in range(4)]),
        ("Azhurak's Crown", [azhurak_crown()]),
    ]


def save_items(art):
    for name, frames in art:
        name = name.lower().replace(" ", "_").replace("'", "")
        sheet = Image.new("RGBA", (32, 32 * len(frames)))
        for i, frame in enumerate(frames):
            sheet.alpha_composite(frame, (0, 32 * i))
        sheet.save(SPRITES / f"{name}.png")


def save_preview(path: Path, art, shots):
    title = ImageFont.load_default(size=19)
    label = ImageFont.load_default(size=13)
    frames = []
    for step in range(36):
        image = Image.new("RGB", (662, 264), "#1d202a")
        d = ImageDraw.Draw(image)
        d.text((14, 12), "Retro76  /  Tesoros de la Caldera Azul", fill=WHITE, font=title)
        for i, (name, icons) in enumerate(art):
            x = 14 + i * 129
            d.rectangle((x, 43, x + 116, 155), fill="#353640", outline="#575762")
            icon = icons[(step // 3) % len(icons)].resize((96, 96), Image.Resampling.NEAREST)
            image.paste(icon, (x + 10, 51), icon)
            d.text((x, 162), name, fill=WHITE, font=label)
        d.text((14, 194), "Proyectil de Devilwing", fill=WHITE, font=label)
        d.rectangle((178, 188, 646, 250), fill="#292c36", outline="#575762")
        x = 186 + (step % 18) * 23
        y = 203
        shot = shots[5]
        if step >= 18:
            x = 603 - (step % 18) * 23
            shot = shots[3]
        image.paste(shot, (x, y), shot)
        frames.append(image)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=60, loop=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--things", type=Path, default=THINGS)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    art, shots = item_art(), projectile_frames()
    if args.prepare:
        save_items(art)
    if args.preview:
        save_preview(args.preview, art, shots)
    install_missile(args.things, args.apply, DEVILWING_MISSILE, shots)


if __name__ == "__main__":
    main()
