#!/usr/bin/env python3
"""Saca los 2 sprites de la fire sword del cliente y pasa su llama a fuego negro.

La fire sword de 7.6 (server id 2392, client id 3280) es un ítem 1x1 animado en 2 cuadros: una hoja de
llamas (rojos, naranjas y amarillos) con un filo plateado y una empuñadura roja abajo a la derecha.

Fuego negro = se invierte el brillo de la llama y se le da un tono violeta: lo que era amarillo brillante (el
corazón de la llama, pegado al filo) queda violeta oscuro, y lo que era rojo oscuro (las puntas de afuera) queda
violeta-magenta brillante. El filo plateado (grises claros) queda igual; la empuñadura (los rojos de abajo a la
derecha) pasa a violeta oscuro.

v2 (19 nov 2026): la v1 llevaba el corazón casi a negro (brillo 0.06) y la empuñadura a hierro casi negro, y en el
cliente la espada no se distinguía del suelo. Ahora el brillo mínimo de la llama es 0.30 y las puntas llegan a 1.0.
La luz (flag .dat 0x15 + attr OTB 0x2A) la pone add_custom_items.py: violeta tenue en vez de naranja.

  python3.11 scripts/client-rme/recolor_black_fire_sword.py --preview /tmp/black_fire_sword.png

Escribe devtools/zagan-test/custom-sprites/black_fire_sword.png (32x64: cuadro 0 arriba, cuadro 1 abajo).
Doc: docs/items-and-map/ZAGAN_TEST_ITEMS.md. Necesita Pillow (en la Mac: python3.11).
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

CLIENT_ID = 3280          # fire sword (server 2392)
OUT = ROOT / "devtools/zagan-test/custom-sprites/black_fire_sword.png"
FLAME_HUE = 300           # magenta de las puntas; el corazón baja 30° hacia el violeta
HILT_HUE = 275


def is_hilt(x: int, y: int) -> bool:
    """La empuñadura (guarda y mango) está abajo a la derecha del cuadro; la hoja baja en diagonal desde
    arriba a la izquierda y termina en la guarda."""
    return x >= 18 and y >= 18 and x + y >= 38


def recolor(x: int, y: int, r: int, g: int, b: int) -> tuple[int, int, int]:
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hd = h * 360
    warm = (hd <= 65 or hd >= 330) and s > 0.45
    if not warm:                                   # contorno negro y filo plateado: igual
        return r, g, b
    if is_hilt(x, y):                              # empuñadura: violeta oscuro
        nh, ns, nv = HILT_HUE / 360, 0.45, 0.16 + 0.50 * v
    else:                                          # llama: brillo invertido, de violeta oscuro a magenta
        heat = min(1.0, v * (0.55 + 0.45 * min(1.0, hd / 50)))   # amarillo = más caliente, rojo oscuro = menos
        nv = 0.30 + 0.70 * (1.0 - heat) ** 0.6
        ns = 0.50 + 0.45 * (1.0 - heat)
        nh = (FLAME_HUE - 30 * (1.0 - heat)) / 360
    rr, gg, bb = colorsys.hsv_to_rgb(nh, ns, nv)
    return int(rr * 255), int(gg * 255), int(bb * 255)


def frame(entry, spr, offsets, index: int, black: bool) -> Image.Image:
    pixels = decode_sprite(spr, offsets, entry.sprite_ids[index])
    img = Image.new("RGBA", (32, 32))
    img.putdata([(0, 0, 0, 0) if not p[3] else
                 ((recolor(i % 32, i // 32, *p[:3]) if black else p[:3]) + (255,))
                 for i, p in enumerate(pixels)])
    return img


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--things", type=Path, default=ROOT / "devtools/rme/rme-client-760")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--preview", type=Path, help="PNG con los 2 cuadros originales y negros, a 8x, sobre dos fondos")
    a = ap.parse_args()

    entries, _tail = B.DatReader((a.things / "Tibia.dat").read_bytes()).read_item_entries()
    entry = next((e for e in entries if e.client_id == CLIENT_ID), None)
    if entry is None or len(entry.sprite_ids) != 2:
        raise SystemExit(f"client id {CLIENT_ID}: no existe o no tiene 2 sprites (1x1 x 2 cuadros)")
    spr = (a.things / "Tibia.spr").read_bytes()
    _n, offsets = read_spr(spr)

    out = Image.new("RGBA", (32, 64))
    for f in range(2):
        out.paste(frame(entry, spr, offsets, f, black=True), (0, 32 * f))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    out.save(a.out)
    print(f"{a.out}")
    if a.preview:
        sheet = Image.new("RGB", (4 * 264 + 8, 2 * 264 + 8), (40, 40, 46))
        for row, bg in enumerate(((40, 40, 46), (96, 120, 70))):          # fondo oscuro y pasto
            for i, black in enumerate((False, True)):
                for f in range(2):
                    x0, y0 = 4 + (i * 2 + f) * 264, 4 + row * 264
                    sheet.paste(Image.new("RGB", (256, 256), bg), (x0, y0))
                    big = frame(entry, spr, offsets, f, black).resize((256, 256), Image.NEAREST)
                    sheet.paste(big, (x0, y0), big)
        sheet.save(a.preview)
        print(f"vista previa: {a.preview}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
