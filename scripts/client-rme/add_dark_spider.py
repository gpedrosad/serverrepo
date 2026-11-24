#!/usr/bin/env python3
"""Draw and install the original 2×2 Dark Spider outfit (four directions, three frames)."""
from __future__ import annotations

import argparse
import math
import struct
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from add_black_dragon_look import _read_thing, decode_sprite, encode_sprite, read_outfits, read_spr, write_spr
from add_recolor_look import frames_to_sprites, replace_sprites

ROOT = Path(__file__).resolve().parents[2]
LOOK = 190
CORPSE_CLIENT_ID = 6063
DIRS = ('north', 'east', 'south', 'west')
PREFIX = bytes((0xff, 2, 2, 64, 1, 4, 1, 1, 3))
OUTLINE = (10, 9, 11)
PALETTE = ((18, 19, 23), (28, 30, 35), (41, 44, 49), (57, 61, 66),
           (74, 79, 82), (97, 101, 100), (126, 127, 117), (156, 153, 137))


def tone(light):
    """Interpolate the charcoal palette without flattening short highlights."""
    position = max(0.0, min(len(PALETTE) - 1, light))
    index = int(position)
    left, right = PALETTE[index], PALETTE[min(index + 1, len(PALETTE) - 1)]
    return tuple(round(a + (b - a) * (position - index)) for a, b in zip(left, right))


def segment(draw, start, stop, widths, light):
    """Tapered leg segment with a lit ridge and a dark lower edge."""
    dx, dy = stop[0] - start[0], stop[1] - start[1]
    length = math.hypot(dx, dy)
    if not length:
        return
    nx, ny = dy / length, -dx / length
    if nx + 1.4 * ny > 0:
        nx, ny = -nx, -ny

    def band(low, high, color):
        a, b = widths
        draw.polygon([(round(x + nx * r), round(y + ny * r)) for (x, y), r in (
            (start, low * a), (stop, low * b), (stop, high * b), (start, high * a),
        )], fill=color)

    band(-1.0, 1.0, OUTLINE)
    band(-0.63, 0.68, tone(light - 1.0))
    band(0.04, 0.64, tone(light + 0.6))
    band(0.29, 0.53, tone(light + 1.7))


def carapace(draw, center, heading, width, length, light):
    """Shade an independent oval plate as a convex surface."""
    fx, fy = heading
    sx, sy = fy, -fx
    cx, cy = center
    edge = math.ceil(max(width, length)) + 1
    for y in range(cy - edge, cy + edge + 1):
        for x in range(cx - edge, cx + edge + 1):
            u = ((x - cx) * sx + (y - cy) * sy) / width
            v = ((x - cx) * fx + (y - cy) * fy) / length
            radius = u * u + v * v
            if radius > 1:
                continue
            height = math.sqrt(1 - radius)
            if height < 0.31:
                draw.point((x, y), fill=OUTLINE)
                continue
            nx, ny = sx * u + fx * v, sy * u + fy * v
            diffuse = max(0, 0.53 * height - 0.33 * nx - 0.51 * ny)
            specular = max(0, 0.86 * height - 0.26 * nx - 0.43 * ny) ** 19
            grain = ((x * 17 + y * 31) % 7 - 3) * 0.12
            draw.point((x, y), fill=tone(light + 3.05 * diffuse + 3.6 * specular + grain))


def spider(direction: str, frame: int, corpse: bool = False) -> Image.Image:
    image = Image.new('RGBA', (64, 64))
    draw = ImageDraw.Draw(image)
    angle = (DIRS.index(direction) - 2) * math.pi / 2
    cos, sin = math.cos(angle), math.sin(angle)
    lift = 0.34 if corpse else 0.85
    body_shift = (0, -0.6, 0.6)[frame]
    lighting = -0.7 if corpse else 0.0
    center_x = 31 if direction == 'west' else 33

    def project(x, y, z):
        px, py = cos * x - sin * y, sin * x + cos * y
        return (round(center_x + 0.83 * px - 0.26 * py),
                round(36 + 0.17 * px + 0.75 * py - z * lift))

    # Legs rise at the knees and turn back toward their points of contact.
    anchors = ((5, -4), (6, 0), (6, 4), (5, 8))
    knees = ((17, -14, 12), (20, -6, 15), (20, 6, 14), (17, 15, 11))
    feet = ((22, -26), (28, -16), (29, 7), (24, 24))
    legs = []
    for side in (-1, 1):
        for i, ((ax, ay), (kx, ky, kz), (tx, ty)) in enumerate(zip(anchors, knees, feet)):
            stride = 0 if frame == 0 else (3 if (frame + i + (side > 0)) % 2 else -3)
            if corpse:
                kx, tx, ty = kx - 2, tx - 9, 0.62 * ty
            heel = (tx - 3) * side
            legs.append((
                project(ax * side, ay + body_shift, 7),
                project(kx * side, ky + stride * 0.5, kz),
                project(heel, ty * 0.84 + stride, 4),
                project(tx * side, ty + stride, 0),
            ))
    for root, knee, ankle, toe in sorted(legs, key=lambda leg: leg[-1][1]):
        light = lighting + (1.45 if toe[0] >= root[0] else 2.35)
        segment(draw, root, knee, (3.1, 2.7), light)
        segment(draw, knee, ankle, (2.85, 1.55), light + 0.35)
        segment(draw, ankle, toe, (1.65, 0.65), light - 0.2)
        x, y = knee
        draw.ellipse((x - 2, y - 2, x + 2, y + 1), fill=tone(light + 0.7))
        draw.point((x - 1, y - 1), fill=tone(light + 3.0))

    rear = project(0, -10 + body_shift, 10)
    thorax = project(0, 7 + body_shift, 8)
    direction_length = math.dist(rear, thorax)
    heading = tuple((b - a) / direction_length for a, b in zip(rear, thorax))
    carapace(draw, rear, heading, 10.8, 12.8, lighting + 0.4)
    carapace(draw, thorax, heading, 8.0, 8.6, lighting + 0.7)

    if direction != 'north':
        for side in (-1, 1):
            root = project(side * 3.0, 12 + body_shift, 7)
            joint = project(side * 5.5, 16 + body_shift, 5)
            point = project(side * 3.5, 20 + body_shift, 4)
            segment(draw, root, joint, (2.5, 1.8), lighting + 2.0)
            segment(draw, joint, point, (1.8, 0.6), lighting + 4.8)
        if not corpse:
            for x, y in ((-3, 11), (-1, 13), (2, 13), (4, 11)):
                cx, cy = project(x, y + body_shift, 9)
                draw.line((cx, cy, cx + 1, cy + 1), fill='#893426', width=2)
                draw.point((cx, cy), fill='#f07b54')
    return image


def render_preview(path: Path, frames: list[Image.Image]) -> None:
    board = Image.new('RGB', (578, 452), '#263039')
    draw = ImageDraw.Draw(board)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 16)
    draw.text((12, 8), 'DARK SPIDER · four directions and three walk frames', '#f0d8ce', font=font)
    for i, direction in enumerate(DIRS):
        draw.text((12 + 142*i, 33), direction.title(), '#d1c7d8', font=font)
    for i, img in enumerate(frames):
        sprite = img.resize((128, 128), Image.Resampling.NEAREST)
        ox, oy = 12+142*(i % 4), 54+130*(i // 4)
        draw.rectangle((ox,oy,ox+127,oy+127), fill='#44414a')
        board.paste(sprite, (ox,oy), sprite)
    board.save(path)


def install(things: Path, frames: list[Image.Image], corpse: Image.Image) -> None:
    dat_path, spr_path = things/'Tibia.dat', things/'Tibia.spr'
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    outfits, header = read_outfits(dat)
    count, offsets = read_spr(spr)
    target = outfits[LOOK-1]
    tiles = frames_to_sprites([list(im.getdata()) for im in frames], 64)
    references = Counter()
    corpse_ids = []
    pos = 12
    for i in range(header[0] - 99 + sum(header[1:])):
        thing = _read_thing(dat, pos)
        pos = thing['end']
        references.update(thing['ids'])
        if i + 100 == CORPSE_CLIENT_ID <= header[0]:
            corpse_ids = thing['ids']

    new_dat = dat
    new_spr = spr
    replacements = {}
    ids = target['ids']
    existing = any(ids)
    if existing:
        if dat[target['start']:target['sprite_pos']] != PREFIX:
            raise SystemExit(f'El formato del looktype {LOOK} no corresponde a Dark Spider.')
        replacements.update(zip(ids, tiles.values()))
    elif count + len(tiles) > 65535:
        raise SystemExit('No hay espacio para los sprites de Dark Spider.')

    if any(corpse_ids):
        if len(corpse_ids) != 4:
            raise SystemExit(f'El cadáver {CORPSE_CLIENT_ID} no tiene formato 2×2.')
        boxes = ((32, 32, 64, 64), (0, 32, 32, 64), (32, 0, 64, 32), (0, 0, 32, 32))
        replacements.update((sid, list(corpse.crop(box).getdata()))
                            for sid, box in zip(corpse_ids, boxes))

    if replacements:
        if any(not 0 < sid <= count or references[sid] != 1 for sid in replacements):
            raise SystemExit('Los sprites de Dark Spider deben tener IDs propios.')
        encoded = {sid: encode_sprite(px) for sid, px in replacements.items()
                   if decode_sprite(spr, offsets, sid) != px}
        if encoded:
            new_spr = replace_sprites(spr, offsets, encoded)
    if not existing:
        ids = list(range(count + 1, count + 1 + len(tiles)))
        entry = PREFIX + struct.pack(f'<{len(ids)}H', *ids)
        new_dat = dat[:target['start']] + entry + dat[target['end']:]
        new_spr = write_spr(struct.unpack_from('<I', new_spr)[0], read_spr(new_spr)[1], new_spr,
                            [encode_sprite(tiles[i]) for i in range(len(tiles))])
    outfits2, header2 = read_outfits(new_dat)
    _, offsets2 = read_spr(new_spr)
    assert header2 == header and outfits2[LOOK-1]['ids'] == ids
    assert all(decode_sprite(new_spr, offsets2, sid) == tiles[i] for i,sid in enumerate(ids))
    assert all(decode_sprite(new_spr, offsets2, sid) == px for sid, px in replacements.items())
    for path, content, old in ((dat_path, new_dat, dat), (spr_path, new_spr, spr)):
        if content == old:
            continue
        backup = path.with_name(path.name + '.bak-dark-spider-v2')
        if not backup.exists():
            backup.write_bytes(old)
        path.write_bytes(content)
    corpse_status = f'{corpse_ids[0]}–{corpse_ids[-1]}' if any(corpse_ids) else 'pendiente'
    print(f'Dark Spider look {LOOK}: sprites {ids[0]}–{ids[-1]}; cadáver {corpse_status}.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--things', type=Path, default=ROOT/'devtools/rme/rme-client-760')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--preview', type=Path)
    parser.add_argument('--corpse', type=Path)
    args = parser.parse_args()
    frames = [spider(direction, f) for f in range(3) for direction in DIRS]
    corpse = spider('south', 0, corpse=True)
    if args.preview:
        render_preview(args.preview, frames)
    if args.apply:
        install(args.things, frames, corpse)
    if args.corpse:
        corpse.save(args.corpse)


if __name__ == '__main__':
    main()
