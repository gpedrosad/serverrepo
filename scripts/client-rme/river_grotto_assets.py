#!/usr/bin/env python3
"""Native animated terrain skins, exclusive to Submerged River Grotto.

Copy the original pixels/pattern order; the installer changes ground to border.
The original ground stays underneath, preserving its movement speed.
"""
from pathlib import Path

SOURCES = (231, 3258, 4632, 4633, 4634, 4635, 4636, 4637, 4638, 4639,
           4640, 4641, 4642, 4643, 104)
NAMES = ("sand", "shallows", "shore north", "shore west", "shore south", "shore east",
         "bank northwest", "bank northeast", "bank southwest", "bank southeast",
         "inlet southeast", "inlet southwest", "inlet northeast", "inlet northwest", "gravel")
SKINS = {source: 20400 + i for i, source in enumerate(SOURCES)}


def river_items():
    return [dict(name="river " + name, server_id=SKINS[source], client_id=5112 + i,
                 prototype=1794, appearance=source, ground_overlay=True,
                 png=f"river_grotto_{source}.png", decor=True, fixed=True,
                 frames=128 if source == 3258 else 16 if source in (231, 104) else 8,
                 descr="Native terrain skin for Submerged River Grotto.")
            for i, (source, name) in enumerate(zip(SOURCES, NAMES))]


def main():
    from PIL import Image
    import build_zagan_test_assets as B
    from recolor_crimson_cage import tile, read_spr
    from add_custom_items import load_otb, node_ids, SPRITES
    root = Path(__file__).resolve().parents[2]
    things = root / "devtools/rme/rme-client-760"
    entries, _ = B.DatReader((things / "Tibia.dat").read_bytes()).read_item_entries()
    entries = {e.client_id: e for e in entries}
    _, otb = load_otb(root / "server/YurOTS/ots/data/items/items-zagan-test.otb")
    s2c = {sid: cid for sid, cid, _ in map(node_ids, otb.children)}
    spr = (things / "Tibia.spr").read_bytes()
    _, offsets = read_spr(spr)
    for item in river_items():
        sprites = entries[s2c[item["appearance"]]].sprite_ids
        assert len(sprites) == item["frames"]
        image = Image.new("RGBA", (32, 32 * len(sprites)))
        for frame, sprite in enumerate(sprites):
            image.paste(tile(spr, offsets, sprite, None), (0, 32 * frame))
        image.save(SPRITES / item["png"])
        print(item["png"], len(sprites))


if __name__ == "__main__":
    main()
