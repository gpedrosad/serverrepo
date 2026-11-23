#!/usr/bin/env python3
"""Native main-bridge preview; optional comparison against a full asset/map backup."""
import argparse
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'kb')]
import mapdata as M
from epstein_cave_repair import index

OUT = M.REPO / 'docs/items-and-map/img/main-bridge'


def view(renderer, tiles):
    w, h, rgba = renderer.client_view(tiles, 135, 54, 148, 79, 7)
    return Image.frombytes('RGBA', (w, h), bytes(rgba)).convert('RGB')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--before-dir', type=Path)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    image = view(M.Renderer(), M.load_tiles())
    image.save(OUT / 'ironbound.png')
    if args.before_dir:
        old_path, M.OTB = M.OTB, args.before_dir / 'items-zagan-test.otb'
        old_otb = M.load_otb()
        M.OTB = old_path
        _, old_tiles, _ = index(M.parse_tree((args.before_dir / 'test.otbm').read_bytes()), old_otb)
        before = view(M.Renderer(old_otb, M.parse_dat(args.before_dir / 'Tibia.dat'),
                                 M.Spr(args.before_dir / 'Tibia.spr')), old_tiles)
        before.save(OUT / 'before.png')
        canvas = Image.new('RGB', (944, 928), '#101c23')
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
        draw.text((16, 12), 'MAIN BRIDGE · IRONBOUND', font=font, fill='#d5e5ea')
        draw.text((16, 39), 'Native preview · same 41 tiles and two 1 sqm choke sections', font=font, fill='#a3b3bd')
        draw.text((16, 68), 'Before', font=font, fill='#a3b3bd')
        draw.text((480, 68), 'Basalt · iron · bronze', font=font, fill='#f0c481')
        canvas.paste(before, (16, 96))
        canvas.paste(image, (480, 96))
        canvas.save(OUT / 'comparison.png')
    print(OUT / 'ironbound.png')


if __name__ == '__main__':
    main()
