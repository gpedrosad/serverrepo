#!/usr/bin/env python3
"""Extrae rieles/vagoneta/apoyo de Tibia 8.60, pixel por pixel, sin ejecutar el cliente.

python3.11 scripts/client-rme/import_dwarven_mine_sprites.py --client DIR_860
Doc: docs/gameplay/DWARVEN_MINE.md. PNG de primer cuadro, sin recolorear ni escalar.
"""
import argparse
from pathlib import Path
from PIL import Image
from add_black_dragon_look import read_spr, decode_sprite
from extract_client_sprites import read_dat_items

SOURCE = {"mine_rail_ns": 7121, "mine_rail_ew": 7122, "mine_rail_se": 7123,
          "mine_rail_sw": 7124, "mine_rail_ne": 7125, "mine_rail_nw": 7126,
          "mine_ore_wagon": 7131, "mine_timber_support": 7135}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--client", type=Path, required=True)
    args = ap.parse_args()
    out = Path(__file__).resolve().parents[2] / "devtools/zagan-test/custom-sprites"
    out.mkdir(parents=True, exist_ok=True)
    dat = read_dat_items((args.client / "Tibia.dat").read_bytes())
    spr = (args.client / "Tibia.spr").read_bytes()
    _, offsets = read_spr(spr)
    for name, cid in SOURCE.items():
        e = dat[cid]
        assert (e["w"], e["h"]) in ((1, 1), (2, 2)), (name, e)
        im = Image.new("RGBA", (e["w"] * 32, e["h"] * 32))
        for tile, sid in enumerate(e["sprites"][:e["w"] * e["h"]]):
            part = Image.new("RGBA", (32, 32))
            part.putdata(decode_sprite(spr, offsets, sid))
            im.alpha_composite(part, ((e["w"] - 1 - tile % e["w"]) * 32,
                                      (e["h"] - 1 - tile // e["w"]) * 32))
        im.save(out / (name + ".png"))
        print(name, "<- client 860", cid)


if __name__ == "__main__":
    main()
