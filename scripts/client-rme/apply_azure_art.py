#!/usr/bin/env python3
"""Install the Azure Caldera artwork in its existing sprite slots."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import add_custom_items as items
from add_black_dragon_look import decode_sprite, encode_sprite
from add_paladin_stars import _sprite_refs
from add_recolor_look import PRESETS, build_preset, frames_to_sprites, load_things, look_frames
from add_recolor_look import replace_sprites, sprite_record
from draw_azure_items import lava_sheet, sunstone

PRESET_NAMES = ("azure-skeleton", "azure-devil", "azure-bonebeast", "azure-lich", "azhurak")
ITEMS = (20124, 20680)
THINGS = items.ROOT / "devtools/rme/rme-client-760"
OTB = items.ROOT / "server/YurOTS/ots/data/items/items-zagan-test.otb"


def image(pixels, width):
    result = Image.new("RGBA", (width, width))
    result.putdata(pixels)
    return result


def mosaic(tiles):
    region = Image.new("RGBA", (128, 64))
    for pattern, tile in enumerate(tiles[:8]):
        region.alpha_composite(tile, (32 * (pattern % 4), 32 * (pattern // 4)))
    return region


def save_preview(path: Path, subjects, lava):
    sheet = Image.new("RGB", (870, 548), "#23242c")
    draw = ImageDraw.Draw(sheet)
    heading = ImageFont.load_default(size=20)
    label = ImageFont.load_default(size=13)
    draw.text((16, 12), "Retro76  /  Caldera Azul", fill="#eef2ef", font=heading)
    draw.text((16, 128), "Antes", fill="#bbbcc2", font=label)
    draw.text((16, 273), "Nuevo", fill="#f1f1eb", font=label)
    draw.text((16, 400), "Lava azul", fill="#f1f1eb", font=label)
    for i, (name, old, new) in enumerate(subjects):
        x = 66 + i * 133
        draw.text((x + 2, 50), name, fill="#eef2ef", font=label)
        for y, sprite in ((70, old), (216, new)):
            draw.rectangle((x, y, x + 128, y + 128), fill="#383842", outline="#51525d")
            size = 128 if sprite.width == 64 else 96
            zoom = sprite.resize((size, size), Image.Resampling.NEAREST)
            margin = (128 - size) // 2
            sheet.paste(zoom, (x + margin, y + margin), zoom)
    for x, text, surface in ((188, "Antes", lava[0]), (486, "Nuevo", lava[1])):
        draw.text((x, 378), text, fill="#eef2ef", font=label)
        sheet.paste(surface.resize((256, 128), Image.Resampling.NEAREST), (x, 400))
    sheet.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--things", type=Path, default=THINGS)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()

    things = load_things(args.things)
    dat, spr, offsets = things["dat"], things["spr"], things["offsets"]
    refs = _sprite_refs(dat)
    patches = {}

    def register(owner, ids, frames):
        if len(ids) != len(frames) or len(set(ids)) != len(ids):
            raise SystemExit(f"{owner}: forma inesperada")
        for sid, pixels in zip(ids, frames, strict=True):
            if refs.get(sid) != {owner} or not offsets[sid - 1]:
                raise SystemExit(f"{owner}: sprite ausente o compartido ({sid})")
            record = encode_sprite(pixels)
            if sprite_record(spr, offsets, sid) != record:
                patches[sid] = record

    subjects = []
    for name in PRESET_NAMES:
        preset = PRESETS[name]
        look = preset["target"]
        _, art, size = build_preset(things, preset)
        ids = things["outfits"][look - 1]["ids"]
        register(f"outfit:{look}", ids, list(frames_to_sprites(art, size).values()))
        if args.preview:
            old, _ = look_frames(things, look)
            direction = 1 if name == "azure-bonebeast" else 2
            subjects.append((preset["name"], image(old[direction], size), image(art[direction], size)))

    _, root = items.load_otb(OTB)
    entries, _ = items.B.DatReader(dat).read_item_entries()
    by_client = {entry.client_id: entry for entry in entries}
    catalog = {sid: cid for sid, cid, _ in map(items.node_ids, root.children) if sid in ITEMS}
    stone, lava = sunstone(), lava_sheet()
    pattern_tiles = [lava.crop((0, 32 * i, 32, 32 * (i + 1))) for i in range(32)]
    stone_ids = by_client[catalog[ITEMS[0]]].sprite_ids
    lava_ids = by_client[catalog[ITEMS[1]]].sprite_ids
    register(f"item:{catalog[ITEMS[0]]}", stone_ids, [list(stone.getdata())])
    register(f"item:{catalog[ITEMS[1]]}", lava_ids, [list(tile.getdata()) for tile in pattern_tiles])

    if args.preview:
        old_stone = image(decode_sprite(spr, offsets, stone_ids[0]), 32)
        old_tiles = [image(decode_sprite(spr, offsets, i), 32) for i in lava_ids[:8]]
        subjects.append(("Azure Sunstone", old_stone, stone))
        save_preview(args.preview, subjects, (mosaic(old_tiles), mosaic(pattern_tiles)))
    if args.apply:
        stone.save(items.SPRITES / "azure_sunstone.png")
        lava.save(items.SPRITES / "blue_lava.png")
        if patches:
            target = things["spr_path"]
            backup = target.with_name("Tibia.spr.bak-azure-art")
            if not backup.exists():
                shutil.copy2(target, backup)
            target.write_bytes(replace_sprites(spr, offsets, patches))
    print(f"{len(patches)} registros {'actualizados' if args.apply else 'distintos'}")


if __name__ == "__main__":
    main()
