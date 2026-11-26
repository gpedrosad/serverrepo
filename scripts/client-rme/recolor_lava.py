#!/usr/bin/env python3
"""Genera los 32 sprites de lava azul y los compara con la lava 598 del cliente.

La lava de 7.6 (server id 598, client id 727) es un suelo 1x1 con 8 patrones (4x2, el mosaico
cambia según la casilla) y 4 cuadros de animación: 32 sprites. Por defecto genera la corteza de
basalto de draw_azure_items.py. Si se indica un parámetro de color, aplica el recolor histórico:
cada tono pasa a uno frío con el mismo brillo, del rojo del
fondo a violeta índigo (--hot, 255°), el amarillo de las vetas a cian (--cold, 188°) y el naranja
queda en el medio (azul). Las vetas más claras se blanquean un poco (--glow).

Primero se probó intercambiar los canales rojo y azul como el blue bassin (recolor_basin.py): queda
un azul parejo que se confunde con el agua.

  python3.11 scripts/client-rme/recolor_lava.py --preview /tmp/blue_lava.png

Escribe devtools/zagan-test/custom-sprites/blue_lava.png (32x1024: los 32 sprites apilados en el orden
del .dat: cuadro, después patrón). La instala add_custom_items.py (server 20680, luz azul).
Doc: docs/items-and-map/CALDERA_AZUL.md. Necesita Pillow (en la Mac: python3.11).
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
from draw_azure_items import lava_sheet  # noqa: E402

CLIENT_ID = 727           # lava (server 598)
SPRITES = 32              # 8 patrones x 4 cuadros
OUT = ROOT / "devtools/zagan-test/custom-sprites/blue_lava.png"
THINGS = ROOT / "devtools/rme/rme-client-760"


def recolor(p, hot: float, cold: float, sat: float, glow: float):
    """Tono del fuego -> tono frío: rojo (0°) pasa a `hot` (violeta índigo), amarillo (60°) a `cold`
    (cian), lineal en el medio. Brillo igual; las vetas claras se blanquean un poco más (`glow`)."""
    r, g, b, a = p
    if not a:
        return (0, 0, 0, 0)
    h, s_, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hd = h * 360
    if hd > 300:                         # rojos que dan la vuelta (330-360°) cuentan como 0°
        hd = 0
    t = min(1.0, hd / 60)
    nh = (hot + (cold - hot) * t) / 360
    ns = s_ * sat
    nv = v
    if v > 0.75:                         # vetas: más blancas
        ns *= 1 - glow * (v - 0.75) / 0.25
    rr, gg, bb = colorsys.hsv_to_rgb(nh, ns, nv)
    return (int(rr * 255), int(gg * 255), int(bb * 255), 255)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--things", type=Path, default=THINGS)
    ap.add_argument("--hot", type=float, help="recolor histórico, tono del rojo (255 por defecto)")
    ap.add_argument("--cold", type=float, help="recolor histórico, tono del amarillo (188 por defecto)")
    ap.add_argument("--sat", type=float, help="recolor histórico, saturación (0.95 por defecto)")
    ap.add_argument("--glow", type=float, help="recolor histórico, blanco de las vetas (0.35 por defecto)")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--preview", type=Path, help="mosaico 8x4 casillas: lava original arriba, azul abajo")
    a = ap.parse_args()

    entries, _tail = B.DatReader((a.things / "Tibia.dat").read_bytes()).read_item_entries()
    entry = next(e for e in entries if e.client_id == CLIENT_ID)
    if len(entry.sprite_ids) != SPRITES:
        raise SystemExit(f"client {CLIENT_ID}: tiene {len(entry.sprite_ids)} sprites, se esperaban {SPRITES}")
    spr = (a.things / "Tibia.spr").read_bytes()
    _n, offsets = read_spr(spr)
    legacy = any(value is not None for value in (a.hot, a.cold, a.sat, a.glow))
    colors = tuple(value if value is not None else fallback
                   for value, fallback in zip((a.hot, a.cold, a.sat, a.glow), (255, 188, 0.95, 0.35)))
    sheet = Image.new("RGBA", (32, 32 * SPRITES)) if legacy else lava_sheet()
    orig = Image.new("RGBA", (32, 32 * SPRITES))
    for i, sid in enumerate(entry.sprite_ids):
        px = decode_sprite(spr, offsets, sid)
        if legacy:
            im = Image.new("RGBA", (32, 32))
            im.putdata([recolor(p, *colors) for p in px])
            sheet.paste(im, (0, 32 * i))
        o = Image.new("RGBA", (32, 32))
        o.putdata([tuple(p) for p in px])
        orig.paste(o, (0, 32 * i))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out)
    print(f"OK {a.out}")
    if a.preview:
        # cuadro 0, los 8 patrones como los pone el cliente (x % 4, y % 2), en un mosaico de 8x4 casillas
        view = Image.new("RGBA", (32 * 8, 32 * 8))
        for src, oy in ((orig, 0), (sheet, 4)):
            for y in range(4):
                for x in range(8):
                    pat = (y % 2) * 4 + (x % 4)
                    view.paste(src.crop((0, 32 * pat, 32, 32 * pat + 32)), (32 * x, 32 * (y + oy)))
        view.resize((view.width * 2, view.height * 2), Image.NEAREST).save(a.preview)
        print(f"preview {a.preview}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
