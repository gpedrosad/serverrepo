#!/usr/bin/env python3
"""Assemble native snow (670) and the native ice-opening overlay (485, layer 1).

Both native 32x32 layers are copied unchanged and stacked for the existing importer.
The ground's flags and the opening's foreground remain the native 485 prototype.
"""
from pathlib import Path
import sys
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "map"), str(HERE.parent / "map/kb")]
from mapdata import load_otb, REPO
from game_render import parse_dat_all, Sprites, compose


def main():
    otb = load_otb();items, _ = parse_dat_all();spr = Sprites()
    snow = compose(items[otb[670]["cid"]], spr)
    opening = compose(items[otb[485]["cid"]], spr, layer=1)
    im = Image.new("RGBA", (32, 64))
    im.paste(snow, (0, 0));im.paste(opening, (0, 32))
    out = REPO / "devtools/zagan-test/custom-sprites/snow_cave_entrance.png"
    out.parent.mkdir(parents=True, exist_ok=True);im.save(out)
    print(out, "two unchanged native layers")


if __name__ == "__main__":
    main()
