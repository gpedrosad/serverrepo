#!/usr/bin/env python3
"""Draw the Snowball-based Fireball and append its eight-direction missile to 7.6."""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import build_zagan_test_assets as B
from add_recolor_effects import read_sections

ROOT = Path(__file__).resolve().parents[2]
ITEM_ART = ROOT / "devtools/zagan-test/custom-sprites/throwing_fireball.png"
THINGS = ROOT / "devtools/rme/rme-client-760"
MISSILE = 21
ANGLES = (135, 90, 45, 180, None, 0, 225, 270, 315)

OUTLINE = "#481b1a"
RED = "#a52c24"
SCARLET = "#e04a22"
ORANGE = "#ff842c"
GOLD = "#ffc34e"
YELLOW = "#ffe995"
WHITE = "#fff8d0"


def orb(phase: int, *, sparks: bool = True) -> Image.Image:
    image = Image.new("RGBA", (32, 32))
    draw = ImageDraw.Draw(image)
    tips = [
        ([-6, -7], [-3, -10], [0, -6], [3, -7]),
        ([-7, -5], [-5, -8], [-3, -6], [2, -9]),
        ([-6, -7], [-2, -7], [0, -10], [3, -6]),
        ([-7, -5], [-4, -9], [-2, -6], [4, -8]),
    ][phase]

    def polygon(points, color):
        draw.polygon([(x + 16, y + 16) for x, y in points], fill=color)

    polygon([(-8, 2), (-8, -3), *tips, (5, -5), (7, -2), (7, 2),
             (5, 5), (2, 7), (-3, 7), (-6, 5)], OUTLINE)
    polygon([(-7, 1), (-7, -3), *tips[1:3], (3, -5), (6, -2), (6, 2),
             (4, 5), (-2, 6), (-5, 4)], RED)
    polygon([(-6, 0), (-5, -3), tips[1], (-2, -4), (1, -5), tips[3],
             (4, -3), (5, 0), (4, 3), (1, 4), (-3, 4)], SCARLET)
    polygon([(-5, 0), (-4, -3), (-2, -2), (0, -4), (2, -3), (4, -1),
             (4, 1), (2, 3), (-2, 4)], ORANGE)
    polygon([(-4, 0), (-3, -2), (0, -3), (2, -2), (3, 0), (1, 2), (-2, 3)], GOLD)
    polygon([(-3, 0), (-2, -1), (0, -2), (1, -1), (1, 1), (-2, 2)], YELLOW)
    draw.point([(14, 16), (15, 15), (16, 15), (15 + phase % 2, 16)], fill=WHITE)
    draw.line([(14, 21), (17, 21), (19, 20)], fill=SCARLET)
    if sparks:
        first, second = [((11, 7), (23, 11)), ((14, 5), (24, 9)),
                         ((17, 4), (9, 10)), ((21, 6), (11, 6))][phase]
        draw.point(first, fill=GOLD)
        draw.point(second, fill=ORANGE)
    return image


def inventory_frame(phase: int, pattern: int) -> Image.Image:
    image = Image.new("RGBA", (32, 32))
    if pattern >= 2:
        rear = orb((phase + 1) % 4, sparks=False).resize((24, 24), Image.Resampling.NEAREST)
        if pattern >= 5:
            image.alpha_composite(rear, (10, 0))
        image.alpha_composite(rear, (1, 6))
    elif pattern == 1:
        image.alpha_composite(orb((phase + 1) % 4, sparks=False), (-4, 0))
    image.alpha_composite(orb(phase), (5, 5))
    return image


def projectiles() -> list[Image.Image | None]:
    east = Image.new("RGBA", (32, 32))
    draw = ImageDraw.Draw(east)
    draw.polygon([(1, 9), (10, 11), (16, 7), (22, 6), (27, 8), (30, 12),
                  (30, 18), (27, 23), (22, 25), (16, 23), (10, 24), (4, 27),
                  (9, 21), (3, 20), (0, 17), (11, 17), (6, 13)], fill=OUTLINE)
    draw.polygon([(3, 10), (11, 13), (16, 9), (21, 7), (27, 10), (29, 13),
                  (29, 17), (26, 22), (21, 24), (16, 21), (10, 23), (7, 25),
                  (12, 19), (6, 20), (3, 18), (14, 17)], fill=RED)
    draw.polygon([(6, 12), (14, 14), (18, 10), (23, 8), (27, 11), (28, 15),
                  (27, 19), (23, 22), (19, 22), (15, 20), (10, 22), (14, 17),
                  (7, 18), (12, 16)], fill=SCARLET)
    draw.polygon([(12, 14), (18, 13), (22, 10), (26, 12), (27, 15), (25, 19),
                  (21, 21), (17, 19), (13, 20), (16, 17), (12, 17)], fill=ORANGE)
    draw.polygon([(17, 15), (20, 13), (22, 11), (25, 12), (26, 15), (24, 18),
                  (21, 19), (18, 18), (16, 18), (19, 16)], fill=GOLD)
    draw.polygon([(20, 15), (22, 12), (25, 13), (25, 16), (23, 18), (20, 17)],
                 fill=YELLOW)
    draw.line([(22, 14), (23, 13), (24, 14), (24, 15)], fill=WHITE)
    draw.point([(2, 6), (6, 7), (1, 23), (3, 22), (5, 19)], fill=ORANGE)
    draw.point([(4, 6), (6, 25)], fill=GOLD)
    return [east.rotate(angle, resample=Image.Resampling.NEAREST) if angle is not None else None
            for angle in ANGLES]


def prepare_item() -> None:
    sheet = Image.new("RGBA", (32, 32 * 4 * 8))
    for phase in range(4):
        for pattern in range(8):
            sheet.alpha_composite(inventory_frame(phase, pattern), (0, 32 * (phase * 8 + pattern)))
    sheet.save(ITEM_ART)


def install_missile(things: Path, apply: bool, missile_id: int = MISSILE,
                    art: list[Image.Image | None] | None = None) -> None:
    dat_path, spr_path = things / "Tibia.dat", things / "Tibia.spr"
    dat = dat_path.read_bytes()
    reader = B.SprReader(spr_path.read_bytes())
    counts, _, missiles = read_sections(dat)
    records = [B.encode_sprite_record(image) if image is not None else None
               for image in (projectiles() if art is None else art)]
    # The Snowball already uses the native 3x3 direction grid, including its empty center.
    snowball = missiles[12]
    prefix = dat[snowball["start"]:snowball["sprite_pos"]]
    if len(snowball["ids"]) != len(records) or missiles[-1]["end"] != len(dat):
        raise SystemExit("Unexpected Snowball missile or DAT layout")
    if counts[3] > missile_id:
        installed = missiles[missile_id]
        existing = [reader.sprite_raw(sid) if sid else None for sid in installed["ids"]]
        if dat[installed["start"]:installed["sprite_pos"]] != prefix or existing != records:
            raise SystemExit(f"DAT missile {missile_id} is occupied by different artwork")
        print(f"Missile {missile_id}: already installed and verified")
        return
    if counts[3] != missile_id:
        raise SystemExit(f"Expected {missile_id} existing missiles, found {counts[3]}")

    sprites = [None, *(reader.sprite_raw(sid) for sid in range(1, reader.sprite_count + 1))]
    ids = []
    for record in records:
        ids.append(len(sprites) if record else 0)
        if record:
            sprites.append(record)
    new_dat = dat[:10] + struct.pack("<H", missile_id + 1) + dat[12:] + prefix + struct.pack("<9H", *ids)
    new_counts, _, new_missiles = read_sections(new_dat)
    if new_counts != (*counts[:3], missile_id + 1) or new_missiles[-1]["ids"] != ids:
        raise SystemExit(f"Could not verify missile {missile_id} in the DAT")
    new_spr = B.write_spr(reader.signature, sprites)
    if apply:
        spr_path.write_bytes(new_spr)
        dat_path.write_bytes(new_dat)
    print(f"Missile {missile_id}: eight directions ({'installed' if apply else 'ready'})")


def preview(path: Path) -> None:
    shots = projectiles()
    title = ImageFont.load_default(size=18)
    label = ImageFont.load_default(size=14)
    clips = ((5, 0, 1, 0), (2, -5, 1, -1), (3, 0, -1, 0), (6, 5, -1, 1))
    frames = []
    for i in range(48):
        image = Image.new("RGB", (530, 208), "#17171d")
        draw = ImageDraw.Draw(image)
        draw.text((18, 15), "Throwable Fireball", fill=WHITE, font=title)
        draw.text((20, 49), "Item", fill="#c4b4aa", font=label)
        draw.text((228, 49), "Projectile", fill="#c4b4aa", font=label)
        draw.rectangle((19, 72, 107, 160), fill="#343238", outline="#5d5354")
        draw.rectangle((119, 72, 207, 160), fill="#343238", outline="#5d5354")
        draw.rectangle((226, 72, 509, 160), fill="#221d24", outline="#5d5354")
        for x, pattern in ((24, 0), (124, 7)):
            tile = inventory_frame(i // 2 % 4, pattern).resize((80, 80), Image.Resampling.NEAREST)
            image.paste(tile, (x, 76), tile)
        draw.text((21, 171), "Single", fill="#c4b4aa", font=label)
        draw.text((121, 171), "Stack", fill="#c4b4aa", font=label)
        direction, y_offset, dx, dy = clips[i // 12]
        offset = i % 12 - 5.5
        shot = shots[direction].resize((48, 48), Image.Resampling.NEAREST)
        image.paste(shot, (344 + round(dx * offset * 15), 92 + y_offset + round(dy * offset * 3)),
                    shot)
        frames.append(image)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=55, loop=0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--things", type=Path, default=THINGS)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    if args.prepare:
        prepare_item()
    if args.preview:
        preview(args.preview)
    install_missile(args.things, args.apply)


if __name__ == "__main__":
    main()
