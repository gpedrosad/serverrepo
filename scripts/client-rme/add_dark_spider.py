#!/usr/bin/env python3
"""Draw and install the original 2×2 Dark Spider outfit (four directions, three frames)."""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from add_black_dragon_look import decode_sprite, encode_sprite, read_outfits, read_spr, write_spr
from add_recolor_look import frames_to_sprites

ROOT = Path(__file__).resolve().parents[2]
LOOK = 190
DIRS = ('north', 'east', 'south', 'west')
PREFIX = bytes((0xff, 2, 2, 64, 1, 4, 1, 1, 3))
OUTLINE = '#14101c'
SHADOW = '#251d32'
CHITIN = '#3c334d'
RIDGE = '#635777'
GLINT = '#877696'
SCAR = '#83334d'
EYE = '#ff6b50'


def spider(direction: str, frame: int, corpse: bool = False) -> Image.Image:
    image = Image.new('RGBA', (64, 64))
    draw = ImageDraw.Draw(image)

    def xy(point):
        x, y = point
        if direction == 'north':
            x, y = -x, -y
        elif direction == 'east':
            x, y = y, -x
        elif direction == 'west':
            x, y = -y, x
        return round(32 + x * 0.94), round(33 + y * (0.60 if corpse else 0.90) + (5 if corpse else 0))

    def shape(points, fill, outline=None):
        draw.polygon([xy(p) for p in points], fill=fill, outline=outline)

    def line(points, fill, width=1):
        draw.line([xy(p) for p in points], fill=fill, width=width)

    roots = ((6, -5), (7, -2), (7, 2), (6, 5))
    knees = ((15, -14), (20, -9), (21, 2), (18, 10))
    toes = ((23, -24), (27, -13), (27, 8), (22, 23))
    for side in (-1, 1):
        for i, ((rx, ry), (kx, ky), (tx, ty)) in enumerate(zip(roots, knees, toes)):
            stride = 0 if frame == 0 else 3 * (-1 if (i + frame + (side == 1)) % 2 else 1)
            if corpse:
                kx, tx = kx - 3, tx - 8
                ty = ky + (3 if i < 2 else -4)
            root = (rx * side, ry)
            knee = (kx * side, ky + stride // 2)
            shin = ((tx - 3) * side, ty - (3 if i < 2 else 4) + stride)
            toe = (tx * side, ty + stride)
            line((root, knee, shin, toe), OUTLINE, 6)
            line((root, knee, shin), SHADOW, 4)
            line((root, knee), RIDGE if side == -1 and not corpse else CHITIN, 2)
            line((knee, shin), CHITIN, 2)
            line((shin, toe), CHITIN)
            mark = xy(knee)
            draw.point(mark, fill=GLINT if side == -1 and not corpse else RIDGE)
            if not corpse:
                line((shin, toe), '#60526e')

    if corpse:
        shape(((-15, -7), (-10, -16), (1, -20), (15, -11), (17, 3), (9, 14),
               (-5, 18), (-15, 10)), '#4e2544')
    # Ridged abdomen: broad at the rear, tapering into the thorax.
    shape(((-6, -23), (4, -24), (12, -17), (13, -8), (9, -1), (4, 3), (-5, 3),
           (-10, -2), (-13, -9), (-12, -16)), CHITIN, OUTLINE)
    shape(((-6, -22), (1, -23), (8, -19), (9, -15), (1, -18), (-8, -15), (-11, -11),
           (-10, -16)), RIDGE)
    shape(((5, -16), (11, -14), (12, -8), (8, -2), (4, 1), (1, -3), (6, -10)), SHADOW)
    line(((-8, -15), (-4, -19), (1, -20)), GLINT)
    for y, width in ((-16, 7), (-11, 8), (-6, 7)):
        line(((-width, y - 1), (-3, y), (0, y + 2), (3, y), (width, y - 1)), SHADOW, 2)
        line(((-width+1, y), (-3, y+1), (0, y+3), (4, y+1)), SCAR if not corpse else RIDGE)
    shape(((-8, -4), (-4, -5), (5, -5), (9, 0), (8, 8), (2, 13), (-4, 12), (-9, 6)),
          CHITIN, OUTLINE)
    shape(((-7, -1), (-4, -4), (4, -4), (7, 0), (0, 2), (-5, 4)), RIDGE)

    if direction != 'north':
        shape(((-7, 5), (-5, 12), (-2, 17), (-3, 19), (-8, 16), (-9, 11)), OUTLINE)
        shape(((7, 5), (5, 12), (2, 17), (3, 19), (8, 16), (9, 11)), OUTLINE)
        line(((-7, 10), (-6, 14), (-3, 17)), RIDGE if corpse else '#a296a9', 2)
        line(((7, 10), (6, 14), (3, 17)), RIDGE if corpse else '#c2a5a5', 2)
        for x, y in ((-5, 7), (-2, 9), (2, 9), (5, 7)):
            cx, cy = xy((x, y))
            draw.rectangle((cx, cy, cx + 1, cy + 1), fill=SCAR if corpse else EYE)
            if not corpse:
                draw.point((cx, cy), fill='#ffd18f')
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


def install(things: Path, frames: list[Image.Image]) -> None:
    dat_path, spr_path = things/'Tibia.dat', things/'Tibia.spr'
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    outfits, header = read_outfits(dat)
    count, offsets = read_spr(spr)
    target = outfits[LOOK-1]
    tiles = frames_to_sprites([list(im.getdata()) for im in frames], 64)
    if any(target['ids']):
        same = (len(target['ids']) == len(tiles)
                and all(decode_sprite(spr, offsets, sid) == tiles[i] for i,sid in enumerate(target['ids'])))
        if not same:
            raise SystemExit(f'Looktype {LOOK} ya está ocupado por otro dibujo.')
        print(f'Looktype {LOOK} ya instalado.')
        return
    if count + len(tiles) > 65535:
        raise SystemExit('No hay espacio para los sprites de Dark Spider.')
    ids = list(range(count+1, count+1+len(tiles)))
    entry = PREFIX + struct.pack(f'<{len(ids)}H', *ids)
    new_dat = dat[:target['start']] + entry + dat[target['end']:]
    new_spr = write_spr(struct.unpack_from('<I', spr)[0], offsets, spr,
                        [encode_sprite(tiles[i]) for i in range(len(tiles))])
    outfits2, header2 = read_outfits(new_dat)
    _, offsets2 = read_spr(new_spr)
    assert header2 == header and outfits2[LOOK-1]['ids'] == ids
    assert all(decode_sprite(new_spr, offsets2, sid) == tiles[i] for i,sid in enumerate(ids))
    for path, content in ((dat_path,new_dat),(spr_path,new_spr)):
        backup = path.with_name(path.name + '.bak-dark-spider')
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
        path.write_bytes(content)
    print(f'Dark Spider look {LOOK}: sprites {ids[0]}–{ids[-1]}.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--things', type=Path, default=ROOT/'devtools/rme/rme-client-760')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--preview', type=Path)
    parser.add_argument('--corpse', type=Path)
    args = parser.parse_args()
    frames = [spider(direction, f) for f in range(3) for direction in DIRS]
    if args.preview:
        render_preview(args.preview, frames)
    if args.corpse:
        spider('south', 0, corpse=True).save(args.corpse)
    if args.apply:
        install(args.things, frames)


if __name__ == '__main__':
    main()
