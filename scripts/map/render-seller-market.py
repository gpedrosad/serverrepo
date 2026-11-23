#!/usr/bin/env python3
"""Render the current Seller district from the map and 7.6 assets."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'kb')]
from game_render import Sprites, creature_image, parse_dat_all
from mapdata import MAP, REPO, Renderer, load_tiles

OUT = REPO / 'docs/items-and-map/img/tienda-seller/small-street-market.png'
DETAIL = OUT.with_name('small-street-counters.png')
BOX = (139, 41, 151, 58)
CAPTIONS = (
    (7, 'Street level · Seller and Tonka'),
    (6, 'Small Street · Mad’s gallery'),
    (5, 'Small Street · Perac’s terrace'),
    (4, 'Terracotta roofs'),
)


def main():
    renderer, tiles = Renderer(), load_tiles()
    _, outfits = parse_dat_all()
    sprites = Sprites()
    actors = {n.get('name'): n for n in ET.parse(MAP.with_name('npc.xml')).getroot()}
    canvas = Image.new('RGB', (880, 1264), '#182522')
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 26)
    text = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 18)
    draw.text((16, 9), 'SMALL STREET MARKET', font=title, fill='#f0e0bb')
    draw.text((16, 40), 'Map preview · fieldstone, oak and terracotta', font=text, fill='#b4cfc4')
    for i, (z, caption) in enumerate(CAPTIONS):
        w, h, rgba = renderer.area(tiles, *BOX, z)
        panel = Image.frombytes('RGBA', (w, h), bytes(rgba))
        for name in ('Seller', 'Tonka', 'Mad', 'Perac'):
            npc = actors[name]
            if int(npc.get('z')) != z:
                continue
            file = MAP.parent.parent / 'npc' / (name.lower() + '.xml')
            look = {k: int(v) for k, v in ET.parse(file).getroot().find('look').attrib.items()}
            actor = creature_image(look, outfits, sprites)
            x, y = int(npc.get('x')), int(npc.get('y'))
            panel.alpha_composite(actor, ((x-BOX[0]+1)*32-actor.width, (y-BOX[1]+1)*32-actor.height))
        if z == 7:
            street = panel.convert('RGB')
        x, y = 16 + i % 2 * 432, 66 + i // 2 * 601
        draw.text((x, y), caption, font=text, fill='#f0e0bb')
        canvas.paste(panel.convert('RGB'), (x, y+25))
    canvas.save(OUT, optimize=True)
    detail = Image.new('RGB', (820, 466), '#182522')
    draw = ImageDraw.Draw(detail)
    draw.text((16, 9), 'SMALL STREET · SHOP COUNTERS', font=title, fill='#f0e0bb')
    for x, label, box in (
        (16, 'Seller · Oak counter', (142, 47, 147, 52)),
        (420, 'Tonka · Gem counter', (145, 53, 150, 58)),
    ):
        draw.text((x, 47), label, font=text, fill='#f0e0bb')
        left, top, right, bottom = box
        crop = street.crop(((left-BOX[0])*32, (top-BOX[1])*32,
                            (right-BOX[0]+1)*32, (bottom-BOX[1]+1)*32))
        detail.paste(crop.resize((crop.width*2, crop.height*2), Image.Resampling.NEAREST), (x, 73))
    detail.save(DETAIL, optimize=True)
    print(OUT)
    print(DETAIL)


if __name__ == '__main__':
    main()
