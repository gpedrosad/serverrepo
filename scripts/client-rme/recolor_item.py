#!/usr/bin/env python3
"""Saca el sprite de un ítem del cliente y lo recolorea (cambio de tono que respeta las sombras).

Lo usa la imperial crown armor (20161): la crown armor del cliente con las placas en violeta imperial y el
oro intacto. El PNG resultante (32x32) se agrega con add_custom_items.py.

  python3.11 scripts/client-rme/recolor_item.py --client-id 3381 --hue 258 --sat 0.85 --val 0.78 --gamma 1.05 \\
      --out devtools/zagan-test/custom-sprites/imperial_crown_armor.png --preview /tmp/crown.png

Qué cambia: los píxeles de la placa (todo lo que no es oro ni brillo) toman el tono `--hue` (grados), con la
saturación por `--sat` y el brillo por `--val` (después de elevarlo a `--gamma`). El oro (tono 24-75° y
claro) y los brillos casi blancos quedan iguales; con `--trim-hue` el oro pasa a plata de ese tono.
Solo ítems de 1 sprite. Doc: docs/items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md.
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


def item_pixels(things: Path, client_id: int) -> list[tuple[int, int, int, int]]:
    entries, _tail = B.DatReader((things / "Tibia.dat").read_bytes()).read_item_entries()
    entry = next((e for e in entries if e.client_id == client_id), None)
    if entry is None or len(entry.sprite_ids) != 1:
        raise SystemExit(f"client id {client_id}: no existe o no es de 1 sprite")
    spr = (things / "Tibia.spr").read_bytes()
    _n, offsets = read_spr(spr)
    return decode_sprite(spr, offsets, entry.sprite_ids[0])


def recolor(pixels, hue: float, sat: float, val: float, gamma: float, trim_hue: float | None):
    out = []
    for r, g, b, a in pixels:
        if not a:
            out.append((0, 0, 0, 0))
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        hd = h * 360
        if (24 <= hd <= 75 and v > 0.5) or (s < 0.25 and v > 0.8):      # oro y brillos
            if trim_hue is None:
                out.append((r, g, b, 255))
                continue
            nh, ns, nv = trim_hue / 360, s * 0.15, min(1, v * 1.02)
        elif v < 0.14:                                                   # contorno: solo el tono
            nh, ns, nv = hue / 360, min(1, s * sat), v * 0.9
        else:
            nh, ns, nv = hue / 360, min(1, s * sat), min(1, (v ** gamma) * val)
        rr, gg, bb = colorsys.hsv_to_rgb(nh, ns, nv)
        out.append((int(rr * 255), int(gg * 255), int(bb * 255), 255))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--things", type=Path, default=ROOT / "devtools/rme/rme-client-760")
    ap.add_argument("--client-id", type=int, required=True)
    ap.add_argument("--hue", type=float, required=True)
    ap.add_argument("--sat", type=float, default=1.0)
    ap.add_argument("--val", type=float, default=1.0)
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--trim-hue", type=float)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--preview", type=Path, help="PNG con el original y el nuevo a 8x")
    a = ap.parse_args()
    src = item_pixels(a.things, a.client_id)
    new = recolor(src, a.hue, a.sat, a.val, a.gamma, a.trim_hue)
    img = Image.new("RGBA", (32, 32))
    img.putdata(new)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    img.save(a.out)
    print(f"{a.out}")
    if a.preview:
        old = Image.new("RGBA", (32, 32))
        old.putdata(src)
        sheet = Image.new("RGB", (2 * 264, 264), (40, 40, 46))
        for i, im in enumerate((old, img)):
            big = im.resize((256, 256), Image.NEAREST)
            sheet.paste(big, (i * 264 + 4, 4), big)
        sheet.save(a.preview)
        print(f"vista previa: {a.preview}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
