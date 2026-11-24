#!/usr/bin/env python3
"""Recolor the Giant Spider outfit and corpse for Dark Spider."""
from __future__ import annotations

import argparse
import struct
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from add_black_dragon_look import _read_thing, decode_sprite, encode_sprite, read_outfits, read_spr, write_spr
from add_recolor_look import PRESETS, build_preset, frames_to_sprites, load_things, replace_sprites

ROOT = Path(__file__).resolve().parents[2]
LOOK = 190
CORPSE_CLIENT_ID = 6063
DIRS = ('north', 'east', 'south', 'west')
PREFIX = bytes((0xff, 2, 2, 64, 1, 4, 1, 1, 3))
GIANT_SPIDER_CORPSE = 4038
CORPSE_BOXES = ((32, 32, 64, 64), (0, 32, 32, 64), (32, 0, 64, 32), (0, 0, 32, 32))


def recolor_corpse(things, recolor):
    pos = 12
    for _ in range(100, GIANT_SPIDER_CORPSE + 1):
        entry = _read_thing(things['dat'], pos)
        pos = entry['end']
    if len(entry['ids']) != len(CORPSE_BOXES):
        raise SystemExit('El cadáver base de Giant Spider no tiene formato 2×2.')
    image = Image.new('RGBA', (64, 64))
    for sid, (x, y, _, _) in zip(entry['ids'], CORPSE_BOXES):
        tile = Image.new('RGBA', (32, 32))
        pixels = decode_sprite(things['spr'], things['offsets'], sid)
        tile.putdata([recolor(pixel) for pixel in pixels])
        image.paste(tile, (x, y))
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


def install(things, frames: list[list], corpse: Image.Image) -> None:
    dat, spr = things['dat'], things['spr']
    header, count, offsets = things['counts'], things['spr_count'], things['offsets']
    target = things['outfits'][LOOK-1]
    tiles = frames_to_sprites(frames, 64)
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
        replacements.update((sid, list(corpse.crop(box).getdata()))
                            for sid, box in zip(corpse_ids, CORPSE_BOXES))

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
    for path, content, old in ((things['dat_path'], new_dat, dat), (things['spr_path'], new_spr, spr)):
        if content == old:
            continue
        backup = path.with_name(path.name + '.bak-dark-spider-palette')
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
    things = load_things(args.things)
    preset = PRESETS['dark-spider']
    original, frames, size = build_preset(things, preset)
    if size != 64 or any(a[3] != b[3] for base, recolored in zip(original, frames)
                         for a, b in zip(base, recolored)):
        raise SystemExit('La paleta debe conservar todos los píxeles del molde 2×2.')
    corpse = recolor_corpse(things, preset['recolor'])
    if args.preview:
        images = [Image.new('RGBA', (size, size)) for _ in frames]
        for image, pixels in zip(images, frames):
            image.putdata(pixels)
        render_preview(args.preview, images)
    if args.apply:
        install(things, frames, corpse)
    if args.corpse:
        corpse.save(args.corpse)


if __name__ == '__main__':
    main()
