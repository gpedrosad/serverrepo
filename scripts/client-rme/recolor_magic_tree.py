#!/usr/bin/env python3
"""Saca los 8 sprites del magic tree del cliente y pasa su efecto a rojo.

El magic tree de 7.6 (server id 2699, client id 3613) es un árbol 2x2 animado en 2 cuadros:
el efecto son 480 píxeles de sparkles azul-lavanda puro (tono 240, r=g, brillo máximo)
repartidos por toda la copa. Pasarlo a rojo sin tocar el árbol es intercambiar los canales
rojo/azul de esos píxeles: (121,121,255) -> (255,121,121), con la misma saturación y brillo
(los centros casi blancos quedan igual porque no son azul-dominantes). La luz la cambia
add_custom_items.py (nivel 6, azul 143 -> rojo 187), en el flag .dat 0x15 y el attr OTB 0x2A.

  python3.11 scripts/client-rme/recolor_magic_tree.py --preview /tmp/red_tree.png

Escribe devtools/zagan-test/custom-sprites/red_magic_tree.png (64x128: cuadro 0 arriba,
cuadro 1 abajo; cada cuadro se parte en los 4 sprites del .dat). Doc:
docs/items-and-map/ZAGAN_TEST_ITEMS.md. Necesita Pillow (en la Mac mini: python3.11).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build_zagan_test_assets as B  # noqa: E402
from add_black_dragon_look import decode_sprite, read_spr  # noqa: E402

CLIENT_ID = 3613          # magic tree
OUT = ROOT / "devtools/zagan-test/custom-sprites/red_magic_tree.png"


def blue_to_red(r: int, g: int, b: int) -> tuple[int, int, int]:
    return (b, g, r) if b > r + 40 and b > g + 40 else (r, g, b)


def build(entry, spr, offsets, frame: int, swap: bool) -> Image.Image:
    """Un cuadro 64x64 del árbol. Orden del .dat por cuadro: abajo-derecha,
    abajo-izquierda, arriba-derecha, arriba-izquierda."""
    img = Image.new("RGBA", (64, 64))
    for q, (x, y) in enumerate(((32, 32), (0, 32), (32, 0), (0, 0))):
        pixels = decode_sprite(spr, offsets, entry.sprite_ids[frame * 4 + q])
        tile = Image.new("RGBA", (32, 32))
        tile.putdata([(0, 0, 0, 0) if not p[3] else
                      ((blue_to_red(*p[:3]) if swap else p[:3]) + (255,))
                      for p in pixels])
        img.paste(tile, (x, y))
    return img


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--things", type=Path, default=ROOT / "devtools/rme/rme-client-760")
    ap.add_argument("--preview", type=Path, help="PNG con el original y el rojo (2 cuadros cada uno, a 4x)")
    a = ap.parse_args()

    entries, _tail = B.DatReader((a.things / "Tibia.dat").read_bytes()).read_item_entries()
    entry = next((e for e in entries if e.client_id == CLIENT_ID), None)
    if entry is None or len(entry.sprite_ids) != 8:
        raise SystemExit(f"client id {CLIENT_ID}: no existe o no tiene 8 sprites (2x2 x 2 cuadros)")
    spr = (a.things / "Tibia.spr").read_bytes()
    _n, offsets = read_spr(spr)

    out = Image.new("RGBA", (64, 128))
    for f in range(2):
        out.paste(build(entry, spr, offsets, f, swap=True), (0, 64 * f))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT)
    reds = sum(1 for p in out.getdata() if p[3] and p[0] > p[2] + 40)
    print(f"{OUT} ({reds} píxeles rojo-dominantes)")
    if a.preview:
        sheet = Image.new("RGB", (4 * 264 + 8, 268), (40, 40, 46))
        for i, swap in enumerate((False, True)):
            for f in range(2):
                big = build(entry, spr, offsets, f, swap).resize((256, 256), Image.NEAREST)
                sheet.paste(big, (4 + (i * 2 + f) * 264, 4), big)
        sheet.save(a.preview)
        print(f"vista previa: {a.preview}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
