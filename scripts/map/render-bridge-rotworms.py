#!/usr/bin/env python3
"""Native previews of the small riverbank and the main bridge above it."""
from pathlib import Path
import json
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'kb')]
from mapdata import REPO, Renderer, load_tiles
from game_render import parse_dat_all, Sprites, creature_image
from bridge_rotworm_bank import MANIFEST, MONSTERS

OUT = REPO / 'docs/items-and-map/img/main-bridge'


def main():
    if json.loads(MANIFEST.read_text()).get('removed'):
        raise SystemExit('Riverbank removed; use render-main-bridge.py for the current bridge.')
    OUT.mkdir(parents=True, exist_ok=True)
    renderer, tiles = Renderer(), load_tiles()
    box = (129, 60, 149, 77)
    w, h, rgba = renderer.area(tiles, *box, 7)
    river = Image.frombytes('RGBA', (w, h), bytes(rgba))
    _, outfits = parse_dat_all()
    actor = creature_image(dict(type=26), outfits, Sprites())
    for x, y in sorted(MONSTERS, key=lambda p: (p[1], p[0])):
        river.alpha_composite(actor, ((x - box[0] + 1) * 32 - actor.width,
                                     (y - box[1] + 1) * 32 - actor.height))
    river.convert('RGB').save(OUT / 'rotworm-bank.png')
    above = bytearray(w * h * 4)
    renderer._floor(above, w, h, tiles, *box, 6, 1)
    bridge = river.copy()
    bridge.alpha_composite(Image.frombytes('RGBA', (w, h), bytes(above)))
    bridge.convert('RGB').save(OUT / 'rotworm-bridge.png')
    canvas = Image.new('RGB', (1392, 680), '#101c23')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
    draw.text((16, 12), 'IRONBOUND · ROTWORM RIVERBANK', font=font, fill='#d5e5ea')
    draw.text((16, 40), 'Native preview outside the game · entrance 135,73,7', font=font, fill='#a3b3bd')
    draw.text((16, 72), 'Riverbank · four rotworms', font=font, fill='#edc78d')
    draw.text((704, 72), 'Main bridge above · PvP layout preserved', font=font, fill='#edc78d')
    canvas.paste(river.convert('RGB'), (16, 104))
    canvas.paste(bridge.convert('RGB'), (704, 104))
    canvas.save(OUT / 'rotworm-overview.png')
    print(OUT / 'rotworm-overview.png')


if __name__ == '__main__':
    main()
