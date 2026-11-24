#!/usr/bin/env python3
"""Soft Boots "in use" (24 nov 2026): las botas brillan puestas, igual que los anillos.

En 7.6 un anillo puesto pasa a su versión "in use" (time ring 2169 -> 2206), que en el cliente tiene 4 cuadros:
el anillo y unos destellos dorados que cambian de lugar. Las Soft Boots no tenían esa versión. Este script arma
la tira de 4 cuadros x 2 capas (32x256, como el anillo) con el sprite de las Soft Boots (client 3549) y, encima, los mismos destellos del
time ring in use (client 3090, sprites 1, 3, 5 y 7), corridos para que caigan sobre la caña de las botas.

  python3.11 scripts/client-rme/make_soft_boots_glow.py [--preview /tmp/botas.png]

Escribe devtools/zagan-test/custom-sprites/soft_boots_in_use.png; lo instala add_custom_items.py (server 20670,
client 6070, apariencia del anillo in use 2206: 2 capas x 4 cuadros). Doc: docs/gameplay/SOFT_BOOTS.md#brillo-puestas.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT / "scripts" / "map" / "kb")]
from extract_client_sprites import read_dat_items  # noqa: E402
from add_black_dragon_look import decode_sprite, read_spr  # noqa: E402

OUT = ROOT / "devtools" / "zagan-test" / "custom-sprites" / "soft_boots_in_use.png"
BOOTS_CID, RING_IN_USE_CID = 3549, 3090
SPARKLE_SHIFT = (2, 2)          # los destellos del anillo quedan arriba al centro; en las botas, un poco más abajo


def sprites():
    d = ROOT / "devtools/rme/rme-client-760"
    dat, spr = (d / "Tibia.dat").read_bytes(), (d / "Tibia.spr").read_bytes()
    things = read_dat_items(dat)
    _count, offs = read_spr(spr)

    def img(sid):
        im = Image.new("RGBA", (32, 32))
        im.putdata(decode_sprite(spr, offs, sid))
        return im

    boots = img(things[BOOTS_CID]["sprites"][0])
    ring = things[RING_IN_USE_CID]["sprites"]
    assert len(ring) == 8, "El time ring in use tenía 8 sprites (anillo + destellos, 4 cuadros)"
    return boots, [img(ring[i]) for i in (1, 3, 5, 7)]


def strip() -> Image.Image:
    """Mismo formato que el anillo in use: por cuadro, capa 0 (botas) y capa 1 (destellos), apiladas."""
    boots, sparkles = sprites()
    out = Image.new("RGBA", (32, 64 * len(sparkles)))
    for i, sp in enumerate(sparkles):
        out.alpha_composite(boots, (0, 64 * i))
        out.alpha_composite(sp, (SPARKLE_SHIFT[0], 64 * i + 32 + SPARKLE_SHIFT[1]),
                            (0, 0, 32 - SPARKLE_SHIFT[0], 32 - SPARKLE_SHIFT[1]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", type=Path, help="los 4 cuadros en fila, x6, sobre el fondo del inventario")
    a = ap.parse_args()
    im = strip()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT)
    print(OUT)
    if a.preview:
        row = Image.new("RGBA", (32 * 5, 32), (52, 52, 52, 255))
        row.alpha_composite(sprites()[0], (0, 0))
        for i in range(4):
            for layer in (0, 1):
                row.alpha_composite(im.crop((0, 64 * i + 32 * layer, 32, 64 * i + 32 * layer + 32)), (32 * (i + 1), 0))
        row.resize((row.width * 6, row.height * 6), Image.NEAREST).save(a.preview)
        print(a.preview)


if __name__ == "__main__":
    main()
