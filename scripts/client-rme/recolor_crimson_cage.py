#!/usr/bin/env python3
"""Sprites de la Crimson Cage Rune: la magic wall y su runa del cliente, pasadas a rojo.

- crimson_cage_wall.png (64x192): la magic wall de 7.6 (server 1498, client 2129) es 2x2 con 3 cuadros
  de animación. Se rota el tono del azul eléctrico al rojo sangre y se conservan saturación y brillo: los
  rayos claros quedan rosados y el fondo negro sigue negro.
- crimson_cage_rune.png (32x32): la runa de magic wall (server 2293, client 3180), con la piedra de
  arena teñida de carmesí y las marcas oscuras intactas.

  python3.11 scripts/client-rme/recolor_crimson_cage.py --preview /tmp/crimson_cage.png

Los PNG los instala add_custom_items.py (crimson cage rune 20273, crimson cage wall 20274). Doc:
docs/gameplay/CRIMSON_CAGE_RUNE.md. Necesita Pillow (en la Mac: python3.11).


REEMPLAZADO (24 nov 2026) para 20273: el PNG final lo escribe redesign_items.py --apply (forma propia).
Correr este script pisa ese PNG con el recolor viejo.
"""
from __future__ import annotations

import argparse
import colorsys
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build_zagan_test_assets as B  # noqa: E402
from add_black_dragon_look import decode_sprite, read_spr  # noqa: E402

WALL_CLIENT = 2129     # magic wall (server 1498): 2x2, 3 cuadros
RUNE_CLIENT = 3180     # runa de magic wall (server 2293)
OUT_DIR = ROOT / "devtools/zagan-test/custom-sprites"
WALL_PNG = OUT_DIR / "crimson_cage_wall.png"
RUNE_PNG = OUT_DIR / "crimson_cage_rune.png"
# Orden de los 4 sprites de un cuadro 2x2 en el .dat (el mismo que sprite_records de add_custom_items).
BOXES_2X2 = [(32, 32), (0, 32), (32, 0), (0, 0)]


def wall_pixel(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Azul eléctrico -> rojo sangre. El tono pasa de ~215° a ~355°; los rayos casi blancos
    (saturación baja) quedan rosados porque conservan su saturación."""
    _h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    rr, gg, bb = colorsys.hsv_to_rgb(355 / 360, min(1.0, s * 1.08), v)
    return int(rr * 255), int(gg * 255), int(bb * 255)


def rune_pixel(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Piedra arena -> carmesí; el contorno y las marcas (muy oscuros) solo cambian de tono."""
    _h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if v < 0.2:
        ns, nv = s, v
    else:
        ns, nv = min(1.0, 0.35 + s * 0.8), min(1.0, (v ** 1.15) * 0.92)
    rr, gg, bb = colorsys.hsv_to_rgb(355 / 360, ns, nv)
    return int(rr * 255), int(gg * 255), int(bb * 255)


def tile(spr, offsets, sprite_id: int, fn) -> Image.Image:
    img = Image.new("RGBA", (32, 32))
    img.putdata([(0, 0, 0, 0) if not p[3] else
                 ((fn(*p[:3]) if fn else tuple(p[:3])) + (255,))
                 for p in decode_sprite(spr, offsets, sprite_id)])
    return img


def wall_image(entry, spr, offsets, fn) -> Image.Image:
    frames = len(entry.sprite_ids) // 4
    out = Image.new("RGBA", (64, 64 * frames))
    for f in range(frames):
        for i, (x, y) in enumerate(BOXES_2X2):
            out.paste(tile(spr, offsets, entry.sprite_ids[4 * f + i], fn), (x, y + 64 * f))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--things", type=Path, default=ROOT / "devtools/rme/rme-client-760")
    ap.add_argument("--preview", type=Path, help="PNG con original y rojo lado a lado, a 4x")
    a = ap.parse_args()

    entries, _tail = B.DatReader((a.things / "Tibia.dat").read_bytes()).read_item_entries()
    by_cid = {e.client_id: e for e in entries}
    wall, rune = by_cid.get(WALL_CLIENT), by_cid.get(RUNE_CLIENT)
    if wall is None or len(wall.sprite_ids) != 12:
        raise SystemExit(f"client id {WALL_CLIENT}: no existe o no es 2x2 de 3 cuadros")
    if rune is None or len(rune.sprite_ids) != 1:
        raise SystemExit(f"client id {RUNE_CLIENT}: no existe o no es de 1 sprite")
    spr = (a.things / "Tibia.spr").read_bytes()
    _n, offsets = read_spr(spr)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    red_wall = wall_image(wall, spr, offsets, wall_pixel)
    red_rune = tile(spr, offsets, rune.sprite_ids[0], rune_pixel)
    red_wall.save(WALL_PNG)
    red_rune.save(RUNE_PNG)
    print(f"{WALL_PNG}\n{RUNE_PNG}")

    if a.preview:
        orig_wall = wall_image(wall, spr, offsets, None)
        sheet = Image.new("RGB", (8 + 6 * 264 + 2 * 136, 4 * 64 + 16), (40, 40, 46))
        x = 8
        for img in (orig_wall, red_wall):
            for f in range(3):
                big = img.crop((0, 64 * f, 64, 64 * (f + 1))).resize((256, 256), Image.NEAREST)
                sheet.paste(big, (x, 8), big)
                x += 264
        for img in (tile(spr, offsets, rune.sprite_ids[0], None), red_rune):
            big = img.resize((128, 128), Image.NEAREST)
            sheet.paste(big, (x, 8), big)
            x += 136
        sheet = sheet.crop((0, 0, x, sheet.height))
        sheet.save(a.preview)
        print(f"vista previa: {a.preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
