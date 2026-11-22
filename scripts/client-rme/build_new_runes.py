#!/usr/bin/env python3
"""Recolor native 7.6 runes to produce sprites for Wild Growth, Icicle, Avalanche,
Stone Shower and Thunderstorm (whose original client IDs were repurposed for map/corpse assets).

Install with:
  python3.11 scripts/client-rme/add_custom_items.py --only 2269 2271 2274 2288 2315 \
      --things devtools/rme/rme-client-760 \
      --otb server/YurOTS/ots/data/items/items-zagan-test.otb \
      --otb server/YurOTS/ots/data/items/items.otb
"""
from __future__ import annotations

import colorsys
import sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "map/kb")]
import build_zagan_test_assets as B  # noqa: E402
from mapdata import load_otb, REPO  # noqa: E402
from recolor_crimson_cage import tile  # noqa: E402
from add_black_dragon_look import read_spr  # noqa: E402


def make_recolor(stone_hue_deg: float, stone_sat_cap: float, glyph_hue_deg: float, glyph_sat_min: float, val_boost: float = 1.0):
    def fn(r: int, g: int, b: int) -> tuple[int, int, int]:
        _, sat, val = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        if sat >= 0.22:
            # Rune glyph / elemental accent
            h = glyph_hue_deg / 360.0
            s = min(1.0, max(glyph_sat_min, sat))
            v = min(1.0, val * val_boost)
        else:
            # Stone body / outline: keep dark outlines crisp, lightly tint stone
            h = stone_hue_deg / 360.0
            s = min(stone_sat_cap, max(0.10, sat + 0.12)) if val > 0.16 else sat
            v = val
        rgb = colorsys.hsv_to_rgb(h, s, v)
        return tuple(round(c * 255) for c in rgb)
    return fn


SPECS = [
    ("wild_growth_rune.png",  2285, make_recolor(135, 0.34, 128, 0.78, 1.08)),  # emerald / nature green
    ("icicle_rune.png",       2311, make_recolor(205, 0.36, 198, 0.72, 1.12)),  # glacier ice-blue
    ("avalanche_rune.png",    2304, make_recolor(202, 0.42, 194, 0.80, 1.12)),  # frost-cyan AoE
    ("stone_shower_rune.png", 2304, make_recolor(32,  0.34, 28,  0.65, 0.96)),  # warm stone / earth ochre
    ("thunderstorm_rune.png", 2262, make_recolor(260, 0.38, 272, 0.82, 1.10)),  # electric storm violet
]


def main() -> None:
    things = REPO / "devtools/rme/rme-client-760"
    entries, _ = B.DatReader((things / "Tibia.dat").read_bytes()).read_item_entries()
    by_cid = {e.client_id: e for e in entries}
    otb = load_otb()
    spr = (things / "Tibia.spr").read_bytes()
    _, offsets = read_spr(spr)
    out = REPO / "devtools/zagan-test/custom-sprites"
    out.mkdir(parents=True, exist_ok=True)

    for filename, proto_sid, fn in SPECS:
        e = by_cid[otb[proto_sid]["cid"]]
        assert len(e.sprite_ids) == 1, f"Prototype {proto_sid} has {len(e.sprite_ids)} sprites"
        img = tile(spr, offsets, e.sprite_ids[0], fn)
        img.save(out / filename)
        print(f"wrote {out / filename} (from server {proto_sid}, spr {e.sprite_ids[0]})")


if __name__ == "__main__":
    main()
