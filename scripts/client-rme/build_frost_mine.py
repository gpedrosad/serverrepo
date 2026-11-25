#!/usr/bin/env python3
"""Recolor native fire's two frames and its rune; preserve pixels, alpha and animation.

Install with add_custom_items.py --only 20369 20370 --things devtools/rme/rme-client-760.
Uses the current canonical DAT/SPR and OTB; never rebuilds old assets.


REEMPLAZADO (24 nov 2026) para la runa 20369: frost_mine_rune.png lo escribe redesign_items.py --apply
(forma propia). Correr este script pisa ese PNG con el recolor viejo; el fuego (frost_mine_fire.png) no cambia.
"""
from pathlib import Path
import colorsys
import sys
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "map/kb")]
import build_zagan_test_assets as B
from mapdata import load_otb, REPO
from recolor_crimson_cage import tile
from add_black_dragon_look import read_spr


def blue_fire(r, g, b):
    _, saturation, value = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    rgb = colorsys.hsv_to_rgb((225 - value * 28) / 360,
                             min(1, max(0.18, saturation * 0.95)), value)
    return tuple(round(c * 255) for c in rgb)


def blue_stone(r, g, b):
    _, saturation, value = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    rgb = colorsys.hsv_to_rgb(212 / 360, min(0.5, saturation * 0.55), value)
    return tuple(round(c * 255) for c in rgb)


def main():
    things = REPO / "devtools/rme/rme-client-760"
    entries, _ = B.DatReader((things / "Tibia.dat").read_bytes()).read_item_entries()
    by_cid = {e.client_id: e for e in entries}
    otb = load_otb()
    fire, rune = (by_cid[otb[sid]["cid"]] for sid in (1492, 2301))
    assert len(fire.sprite_ids) == 2 and len(rune.sprite_ids) == 1
    spr = (things / "Tibia.spr").read_bytes()
    _, offsets = read_spr(spr)
    frames = [tile(spr, offsets, sid, blue_fire) for sid in fire.sprite_ids]
    icon = tile(spr, offsets, rune.sprite_ids[0], blue_stone)
    out = REPO / "devtools/zagan-test/custom-sprites"
    out.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (32, 64))
    for i, frame in enumerate(frames):
        sheet.paste(frame, (0, i * 32))
    sheet.save(out / "frost_mine_fire.png")
    icon.save(out / "frost_mine_rune.png")
    preview = Image.new("RGB", (544, 176), "#202a39")
    draw = ImageDraw.Draw(preview)
    draw.text((12, 9), "FROST MINE - native rune and animated blue fire", fill="#d7f5ff")
    for i, im in enumerate([icon] + frames):
        preview.paste(im.resize((128, 128), Image.Resampling.NEAREST), (12 + i * 176, 36),
                      im.resize((128, 128), Image.Resampling.NEAREST))
    dest = REPO / "docs/gameplay/img/frost-mine.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    preview.save(dest)
    print(dest)


if __name__ == "__main__":
    main()
