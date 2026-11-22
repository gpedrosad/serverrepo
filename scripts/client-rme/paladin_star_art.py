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


def draw_storm_star() -> Image.Image:
    """Storm Star minimalista estilo Tibia 7.6: shuriken diagonal en X (22x22, 10 colores).

    Contorno oscuro de 1 px, cuatro cuchillas biseladas con luz arriba-izquierda en acero
    cobalto y núcleo romboidal violeta eléctrico; sin ruido de downsampling.
    """
    outline = (10, 10, 18, 255)
    cobalt = {
        '1': (30, 48, 108, 255),
        '2': (54, 84, 158, 255),
        '3': (98, 138, 212, 255),
        '4': (166, 200, 244, 255),
        '5': (232, 244, 255, 255),
    }
    violet = {
        'd': (58, 32, 126, 255),
        'v': (132, 82, 234, 255),
        'l': (198, 170, 255, 255),
        'w': (248, 244, 255, 255),
    }
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    pix = img.load()
    cx, cy = 15.5, 15.5
    inv = 1.0 / math.sqrt(2)
    inside: set[tuple[int, int]] = set()
    for y in range(4, 28):
        for x in range(4, 28):
            dx, dy = x - cx, y - cy
            u = (dx + dy) * inv
            v = (-dx + dy) * inv
            au, av = abs(u), abs(v)
            on_u = au <= 13.6 and av <= max(0.0, (13.6 - au) * 0.34)
            on_v = av <= 13.6 and au <= max(0.0, (13.6 - av) * 0.34)
            hub = (au + av) <= 4.5
            if on_u or on_v or hub:
                inside.add((x, y))

    for x, y in inside:
        dx, dy = x - cx, y - cy
        u = (dx + dy) * inv
        v = (-dx + dy) * inv
        au, av = abs(u), abs(v)
        if abs(dx) + abs(dy) <= 2.4:
            if dx < 0 and dy < 0:
                col = violet['w']
            elif dx + dy <= 0:
                col = violet['l']
            else:
                col = violet['v']
        elif abs(dx) + abs(dy) <= 3.6:
            col = violet['d']
        elif au >= av:
            if u < 0:
                if abs(v) < 0.55 and au < 7.5:
                    col = violet['l'] if au < 5.3 else violet['v']
                elif v > 0:
                    col = cobalt['5'] if au > 5.0 else cobalt['4']
                else:
                    col = cobalt['4'] if au > 6.5 else cobalt['3']
            else:
                if abs(v) < 0.55 and au < 6.5:
                    col = violet['d']
                elif v > 0:
                    col = cobalt['3'] if au > 7.5 else cobalt['2']
                else:
                    col = cobalt['2'] if au > 9.5 else cobalt['1']
        else:
            if abs(u) < 0.55 and av < 6.8:
                col = violet['v'] if av < 5.0 else violet['d']
            elif u < 0:
                col = cobalt['5'] if av > 6.5 else cobalt['4']
            else:
                col = cobalt['2'] if av > 7.5 else cobalt['1']
        pix[x, y] = col

    for x, y in inside:
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if (nx, ny) not in inside and 0 <= nx < 32 and 0 <= ny < 32:
                pix[nx, ny] = outline
    return img


def prepare(art: Path) -> None:
    for name in PALETTES:
        if name == 'storm':
            draw_storm_star().save(art / 'storm.png')
            continue
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
