#!/usr/bin/env python3
"""Sprites de vuelo e impacto de las stars, con las primitivas pixel-art del cliente.

El ítem proviene de ImageGen; aquí se adapta su tamaño y se componen las estelas.
No modifica los efectos existentes. Ver docs/gameplay/PALADIN_STARS.md.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

from add_drawn_effects import Frame, blob, capsule

PALETTES = {
    'gale': [(20, 55, 66), (30, 115, 139), (39, 199, 220), (164, 248, 255), (242, 255, 255)],
    'venom': [(19, 43, 17), (38, 99, 25), (65, 181, 28), (154, 239, 61), (231, 255, 173)],
    'storm': [(32, 20, 65), (68, 45, 137), (118, 78, 221), (181, 163, 255), (248, 245, 255)],
}
LIGHT = {'gale': 71, 'venom': 103, 'storm': 161}
DIRECTIONS = [(x, y) for y in (-1, 0, 1) for x in (-1, 0, 1)]


def prepare(art: Path) -> None:
    for name in PALETTES:
        source = Image.open(art / f'{name}-generated.png').convert('RGBA')
        alpha = source.getchannel('A').point(lambda a: 255 if a >= 128 else 0)
        bounds = alpha.getbbox()
        if bounds is None:
            raise ValueError(f'{name}: imagen vacía')
        source.putalpha(alpha)
        crop = source.crop(bounds)
        side = max(crop.size)
        square = Image.new('RGBA', (side, side))
        square.alpha_composite(crop, ((side - crop.width) // 2, (side - crop.height) // 2))
        sprite = Image.new('RGBA', (32, 32))
        sprite.alpha_composite(square.resize((28, 28), Image.Resampling.NEAREST), (2, 2))
        sprite.save(art / f'{name}.png')


def image(pixels) -> Image.Image:
    result = Image.new('RGBA', (32, 32))
    result.putdata(pixels)
    return result


def missiles(name: str, art: Path) -> list[Image.Image | None]:
    """Orden DAT: NO,N,NE,O,centro,E,SO,S,SE; estela siempre detrás del avance."""
    ramp = PALETTES[name]
    item = Image.open(art / f'{name}.png').convert('RGBA')
    blade = item.resize((18, 18), Image.Resampling.NEAREST)
    result = []
    for dx, dy in DIRECTIONS:
        if dx == dy == 0:
            result.append(None)
            continue
        length = math.hypot(dx, dy)
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux
        fr = Frame()
        if name == 'gale':
            for offset in (-4, 0, 4):
                capsule(fr, [(16 - ux * t + nx * offset, 16 - uy * t + ny * offset)
                             for t in (12, 7, 2)], 2.0, ramp, ramp[0])
        elif name == 'venom':
            for t, offset, radius in ((11, -3, 2.2), (9, 3, 1.8), (6, 0, 2.5)):
                blob(fr, 16 - ux * t + nx * offset, 16 - uy * t + ny * offset,
                     radius, ramp, ramp[0], seed=t)
        else:
            for offset in (-4, 4):
                capsule(fr, [(16 - ux * t + nx * (offset + jitter),
                              16 - uy * t + ny * (offset + jitter))
                             for t, jitter in ((13, 0), (9, 2), (6, -2), (2, 0))],
                        2.0, ramp, ramp[0])
        out = image(fr.pixels())
        # La cabeza usa el mismo ítem, con giro distinto según la dirección.
        angle = math.degrees(math.atan2(-dy, dx)) + (22 if name == 'storm' else 0)
        head = blade.rotate(angle, resample=Image.Resampling.NEAREST)
        out.alpha_composite(head, (round(7 + ux * 3), round(7 + uy * 3)))
        result.append(out)
    return result


def impacts(name: str) -> list[Image.Image]:
    """Ocho cuadros: tajo de viento, gotas de toxina o descarga ramificada."""
    ramp, frames = PALETTES[name], []
    for k in range(8):
        fr = Frame()
        if name == 'gale':
            for arm in range(3):
                angle = arm * math.tau / 3 + k * 0.5
                radius = 4 + k
                pts = [(16 + math.cos(angle + a) * radius,
                        16 + math.sin(angle + a) * radius) for a in (0, 0.35, 0.7)]
                capsule(fr, pts, max(1, 3 - k * 0.22), ramp, ramp[0])
        elif name == 'venom':
            for j in range(5):
                angle = j * math.tau / 5
                radius = 2 + k * 1.5
                blob(fr, 16 + math.cos(angle) * radius, 16 + math.sin(angle) * radius,
                     max(0.6, 3.8 - k * 0.4), ramp, ramp[0], seed=j, amp=0.2)
        else:
            if k < 5:
                blob(fr, 16, 16, 2 + k, ramp, ramp[0], seed=7, amp=0.2)
            for j in range(4):
                angle = j * math.tau / 4 + k * 0.12
                radius = min(13, 5 + k * 2)
                pts = [(16, 16), (16 + math.cos(angle + .3) * radius * .5,
                                  16 + math.sin(angle + .3) * radius * .5),
                       (16 + math.cos(angle) * radius, 16 + math.sin(angle) * radius)]
                capsule(fr, pts, max(1, 3 - k * .25), ramp, ramp[0])
        if 1 <= k <= 5:
            fr.sparkle(12 + k * 2, 8 + k, 1, ramp)
        frames.append(image(fr.pixels()))
    return frames


def preview(art: Path, output: Path) -> None:
    cell = 96
    sheet = Image.new('RGB', (9 * cell, 3 * (cell * 2 + 24)), (43, 44, 49))
    draw = ImageDraw.Draw(sheet)
    for row, name in enumerate(PALETTES):
        top = row * (cell * 2 + 24)
        draw.text((4, top + 4), name.upper() + ' | item + 8 directions / impact frames', fill='white')
        item = Image.open(art / f'{name}.png').convert('RGBA')
        for col, sprite in enumerate([item] + [m for m in missiles(name, art) if m is not None]):
            sheet.paste(sprite.resize((cell, cell), Image.Resampling.NEAREST),
                        (col * cell, top + 24), sprite.resize((cell, cell), Image.Resampling.NEAREST))
        for col, sprite in enumerate(impacts(name)):
            sprite = sprite.resize((cell, cell), Image.Resampling.NEAREST)
            sheet.paste(sprite, (col * cell, top + 24 + cell), sprite)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
