#!/usr/bin/env python3
"""Render the four depot floors and its connected north wing with native sprites."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'kb')]
from mapdata import REPO, Renderer, load_tiles

OUT = REPO / 'docs/items-and-map/img/depot-electric'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    renderer, tiles = Renderer(), load_tiles()
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
    overview = Image.new('RGB', (1472, 792), '#101c23')
    draw = ImageDraw.Draw(overview)
    draw.text((16, 12), 'DEPOT · consistent cyan masonry on every floor', font=font, fill='#b7f4f4')
    draw.text((16, 40), 'Native map preview outside the game', font=font, fill='#9aadb7')
    for i, z in enumerate((4, 5, 6, 7)):
        w, h, rgba = renderer.area(tiles, 125, 40, 135, 60, z)
        image = Image.frombytes('RGBA', (w, h), bytes(rgba)).convert('RGB')
        image.save(OUT / f'complete-z{z}.png')
        x = 16 + i * 364
        draw.text((x, 72), f'Floor {z}', font=font, fill='#d7e3e9')
        overview.paste(image, (x, 104))
    overview.save(OUT / 'complete-floors.png')
    w, h, rgba = renderer.client_view(tiles, 125, 40, 135, 60, 7)
    Image.frombytes('RGBA', (w, h), bytes(rgba)).save(OUT / 'complete-client-z7.png')
    print(OUT / 'complete-floors.png')


if __name__ == '__main__':
    main()
