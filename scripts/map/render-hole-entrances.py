#!/usr/bin/env python3
"""Native before/after views and a contact sheet of all reviewed entrances."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "kb")]
from mapdata import MAP, REPO, Renderer, load_tiles, parse_tree, iter_tiles

OUT = REPO / "docs/items-and-map/img/hole-entrances"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--before", default="29d5c03")
    args = ap.parse_args()
    old_raw = subprocess.check_output(["git", "show", args.before + ":server/YurOTS/ots/data/world/test.otbm"], cwd=REPO)
    before = {(x, y, z): ids for x, y, z, ids in iter_tiles(parse_tree(old_raw))}
    after = load_tiles()
    records = json.loads(MAP.with_name("generated-hole-entrances.json").read_text())["entrances"]
    r = Renderer()
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    font, small = ImageFont.truetype(font_path, 19), ImageFont.truetype(font_path, 14)
    OUT.mkdir(parents=True, exist_ok=True)

    def crop(tiles, pos, scale=2):
        x, y, z = pos
        render = r.client_view if z == 7 else r.area
        w, h, data = render(tiles, x - 1, y - 1, x + 1, y + 1, z)
        return Image.frombytes("RGBA", (w, h), bytes(data)).convert("RGB").resize((w * scale, h * scale), Image.Resampling.NEAREST)

    cases = [("Grass / mine", (195, 59, 7)), ("Soil / spider entrance", (105, 80, 7)),
             ("Soil / Epstein cave", (57, 222, 9)), ("Stone / crypt", (77, 23, 9)),
             ("Wood / mine landing", (197, 58, 8)), ("Frozen / tundra", (213, 27, 7))]
    im = Image.new("RGB", (832, 816), "#152027");d = ImageDraw.Draw(im)
    d.text((16, 10), "ENTRANCES MATCHED TO THEIR TERRAIN", font=font, fill="#cae3df")
    for i, (name, pos) in enumerate(cases):
        x, y = 16 + i % 2 * 408, 48 + i // 2 * 250
        d.text((x, y), name, font=font, fill="#d8e1e8")
        d.text((x, y + 25), "Before", font=small, fill="#a9b6bf")
        d.text((x + 200, y + 25), "After", font=small, fill="#a9b6bf")
        im.paste(crop(before, pos), (x, y + 45));im.paste(crop(after, pos), (x + 200, y + 45))
    im.save(OUT / "before-after.png")
    sheet = Image.new("RGB", (960, 48 + ((len(records) + 7) // 8) * 136), "#152027")
    d = ImageDraw.Draw(sheet);d.text((12, 10), f"{len(records)} ENTRANCES REVIEWED · NATIVE MAP PREVIEW", font=font, fill="#cae3df")
    for i, row in enumerate(records):
        x, y = 12 + i % 8 * 120, 48 + i // 8 * 136
        pos = row["position"]
        d.text((x, y), ",".join(map(str, pos)), font=small, fill="#a9b6bf")
        sheet.paste(crop(after, pos, 1), (x, y + 22))
    sheet.save(OUT / "all-entrances.png")
    print(OUT / "before-after.png")


if __name__ == "__main__":
    main()
