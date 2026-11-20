#!/usr/bin/env python3
"""Adapta originales ImageGen y dibuja tres impactos pixel-art de ocho cuadros."""
import math
from pathlib import Path
from PIL import Image, ImageDraw
from add_drawn_effects import Frame, blob, capsule

NAMES = ('riftblade', 'aethercleaver', 'graviton')
LIGHT = (161, 71, 187)
RAMPS = (
    [(35, 12, 57), (90, 30, 150), (188, 55, 238), (242, 155, 255), (255, 242, 255)],
    [(9, 39, 47), (15, 108, 117), (38, 205, 202), (155, 255, 235), (244, 255, 250)],
    [(48, 27, 12), (112, 56, 15), (215, 115, 23), (255, 203, 80), (255, 249, 205)],
)


def prepare(art: Path):
    # Same crop/nearest-neighbor policy as the stars, with our own item names.
    for name in NAMES:
        source = Image.open(art/f'{name}-generated.png').convert('RGBA')
        alpha = source.getchannel('A').point(lambda v: 255 if v >= 128 else 0)
        bounds = alpha.getbbox()
        if not bounds:
            raise ValueError(f'{name}: empty image')
        source.putalpha(alpha)
        crop = source.crop(bounds)
        scale = min(30/crop.width, 30/crop.height)
        crop = crop.resize((max(1, round(crop.width*scale)), max(1, round(crop.height*scale))), Image.Resampling.NEAREST)
        sprite = Image.new('RGBA', (32, 32))
        sprite.alpha_composite(crop, ((32-crop.width)//2, (32-crop.height)//2))
        sprite.save(art/f'{name}.png')


def impacts(index):
    ramp = RAMPS[index]
    frames = []
    for k in range(8):
        fr = Frame()
        if index == 0:
            # Two jagged dimensional lips open, then pinch closed.
            gap = (0, 1, 3, 5, 4, 3, 1, 0)[k]
            length = (6, 9, 12, 13, 13, 11, 8, 4)[k]
            for side in (-1, 1):
                pts = [(16-length*.55+side*gap, 16+length),
                       (15+side*gap, 18), (17+side*gap, 13),
                       (16+length*.55+side*gap, 16-length)]
                capsule(fr, pts, 1.6 if k < 6 else .9, ramp, ramp[0])
            if 1 <= k <= 5:
                fr.sparkle(7+k*2, 10+k, 1, ramp)
        elif index == 1:
            # Mana ribbons converge inward, rather than exploding outward.
            radius = 13-k*1.4
            for j in range(3):
                angle = j*math.tau/3+k*.5
                pts = [(16+math.cos(angle+a)*radius*(1-a*.6),
                        16+math.sin(angle+a)*radius*(1-a*.6)) for a in (0, .4, .8)]
                capsule(fr, pts, 1.9, ramp, ramp[0])
            if k >= 4:
                blob(fr, 16, 16, max(1, 5-(k-4)), ramp, ramp[0], seed=9)
        else:
            # Ring collapses into a dense core, then throws heavy fragments.
            radius = (12, 10, 7, 4, 3, 7, 11, 14)[k]
            for j in range(6):
                angle = j*math.tau/6
                if k < 5:
                    capsule(fr, [(16+math.cos(angle+a)*radius, 16+math.sin(angle+a)*radius*.6)
                                 for a in (0, .35, .7)], 1.8, ramp, ramp[0])
                else:
                    blob(fr, 16+math.cos(angle)*radius, 16+math.sin(angle)*radius*.6,
                         max(.8, 2.5-(k-5)*.7), ramp, ramp[0], seed=j)
            if 2 <= k <= 5:
                blob(fr, 16, 16, (3, 5, 4, 2)[k-2], ramp, ramp[0], seed=3)
        image = Image.new('RGBA', (32, 32)); image.putdata(fr.pixels())
        frames.append(image)
    return frames


def preview(art: Path, output: Path):
    cell = 96
    sheet = Image.new('RGB', (9*cell, 3*(cell+28)), (37, 40, 49))
    draw = ImageDraw.Draw(sheet)
    for row, name in enumerate(NAMES):
        top = row*(cell+28)
        draw.text((5, top+7), name.upper()+' | item + impact animation', fill='white')
        for col, sprite in enumerate([Image.open(art/f'{name}.png').convert('RGBA')]+impacts(row)):
            enlarged = sprite.resize((cell, cell), Image.Resampling.NEAREST)
            sheet.paste(enlarged, (col*cell, top+28), enlarged)
    output.parent.mkdir(parents=True, exist_ok=True); sheet.save(output)
