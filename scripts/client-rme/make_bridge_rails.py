#!/usr/bin/env python3
"""Barandas del puente de madera de la ciudad (nov 2026): ítems de decoración que no bloquean, dibujados
DENTRO de la tabla del borde (encima del suelo de madera 405).

Por qué: en 7.6 la baranda 1518 se dibuja en el borde oeste de su casilla y la bloquea, así que el puente
a la vista era una casilla más ancho que el caminable y no se podía angostar a 1 sqm sin que quedara mal
(docs/items-and-map/PIEZAS_DE_MAPA.md#puente-de-madera-elevado-z6). Con estas piezas cada tabla lleva la
baranda en los lados que dan al agua y al costado no hay casilla: se ve el río.

Piezas: una por combinación de lados (L oeste, T norte, R este, B sur). R y B llevan además la cara lateral
del puente (madera oscura), para que se vea elevado. Colores sacados de las tablas 405 y la baranda 1518.

  python3.11 scripts/client-rme/make_bridge_rails.py            # escribe los PNG
  python3.11 scripts/client-rme/make_bridge_rails.py --scene /tmp/puente.png

Los PNG van a devtools/zagan-test/custom-sprites/bridge_rail_<lados>.png y los instala add_custom_items.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "devtools" / "zagan-test" / "custom-sprites"

OUTLINE = (40, 22, 6, 255)
RAIL_HI, RAIL, RAIL_SH, RAIL_DK = (255, 214, 140, 255), (214, 160, 98, 255), (160, 106, 52, 255), (96, 52, 24, 255)
FACE = [(150, 104, 50, 255), (118, 74, 28, 255), (92, 52, 14, 255), (70, 34, 6, 255), (20, 10, 0, 255)]
DECK_SHADOW = (120, 84, 40, 110)
POSTS = (1, 14, 27)                            # cada cuántos px va un poste sobre la viga

# combinaciones que se instalan: server id 20480 + i, client id 5200 + i (add_custom_items.py)
COMBOS = ["L", "R", "T", "B", "LR", "LT", "TR", "LB", "BR"]
SERVER_BASE, CLIENT_BASE = 20480, 5200
FLOWER_PROTOTYPE = 4158                        # decoración en la capa de abajo: no bloquea ni se mueve


def server_id(combo: str) -> int:
    return SERVER_BASE + COMBOS.index(combo)


def bridge_items():
    return [dict(name="wooden railing", server_id=SERVER_BASE + i, client_id=CLIENT_BASE + i,
                 prototype=FLOWER_PROTOTYPE, png=f"bridge_rail_{c}.png", decor=True, descr="")
            for i, c in enumerate(COMBOS)]


def put(im, x, y, c):
    if 0 <= x < 32 and 0 <= y < 32:
        base = im.getpixel((x, y))
        if c[3] == 255 or base[3] == 0:
            im.putpixel((x, y), c if c[3] == 255 else (c[0], c[1], c[2], c[3]))
        else:
            a = c[3] / 255
            im.putpixel((x, y), tuple(round(c[i] * a + base[i] * (1 - a)) for i in range(3)) + (255,))


def beam(im, side, inset):
    """Viga de 4 px a lo largo de `side`, a `inset` px del borde, con postes y sombra hacia la tabla."""
    shades = [RAIL_DK, RAIL_HI, RAIL, RAIL_SH]
    for k in range(32):
        for d, c in enumerate(shades):
            off = inset + d
            if side == "L":
                put(im, off, k, c)
            elif side == "R":
                put(im, 31 - off, k, shades[3 - d])
            elif side == "T":
                put(im, k, off, c)
            else:
                put(im, k, 31 - off, shades[3 - d])
        sh = inset + 4
        if side == "L":
            put(im, sh, k, DECK_SHADOW)
        elif side == "T":
            put(im, k, sh, DECK_SHADOW)
    for p in POSTS:                            # postes: tapita clara con contorno
        for a in range(-1, 3):
            for b in range(4):
                c = OUTLINE if a in (-1, 2) else RAIL_HI if b == 1 else RAIL
                if side == "L":
                    put(im, inset + b, p + a, c)
                elif side == "R":
                    put(im, 31 - inset - b, p + a, c)
                elif side == "T":
                    put(im, p + a, inset + b, c)
                else:
                    put(im, p + a, 31 - inset - b, c)


def face(im, side):
    """Cara lateral del puente (5 px) en el borde este o sur."""
    for k in range(32):
        for d, c in enumerate(FACE):
            if side == "R":
                put(im, 27 + d, k, c)
            else:
                put(im, k, 27 + d, c)
    # vetas de la madera en la cara
    for k in range(3, 32, 8):
        for d in range(1, 4):
            if side == "R":
                put(im, 27 + d, k + d, FACE[3])
            else:
                put(im, k + d, 27 + d, FACE[3])


def sprite(combo: str) -> Image.Image:
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    for s in "RB":
        if s in combo:
            face(im, s)
    for s in "LT":
        if s in combo:
            for k in range(32):
                put(im, 0, k, OUTLINE) if s == "L" else put(im, k, 0, OUTLINE)
            beam(im, s, 1)
    for s in "RB":
        if s in combo:
            beam(im, s, 5)
    return im


def scene(path: Path):
    """Puente de prueba: 3 de ancho con dos tramos de 1 sqm, sobre agua."""
    sys.path[:0] = [str(HERE), str(ROOT / "scripts" / "map" / "kb")]
    from extract_client_sprites import read_dat_items
    from add_black_dragon_look import decode_sprite, read_spr
    d = ROOT / "devtools/rme/rme-client-760"
    dat, spr = (d / "Tibia.dat").read_bytes(), (d / "Tibia.spr").read_bytes()
    things = read_dat_items(dat)
    _c, offs = read_spr(spr)

    def cid_img(cid, idx=0):
        im = Image.new("RGBA", (32, 32))
        im.putdata(decode_sprite(spr, offs, things[cid]["sprites"][idx]))
        return im

    water, wood = cid_img(4597), cid_img(408)
    rows = ["LT T TR", "L . R", "L . R", "LB . BR", "  LR  ", "  LR  ", "  LR  ", "LT . TR", "LB . BR",
            "  LR  ", "  LR  ", "LT . TR", "L . R", "LB B BR"]
    W, H = 7, len(rows) + 2
    canvas = Image.new("RGBA", (W * 32, H * 32))
    for y in range(H):
        for x in range(W):
            canvas.alpha_composite(water, (x * 32, y * 32))
    for r, row in enumerate(rows):
        cells = row.split() if not row.startswith("  ") else [None, row.strip(), None]
        for i, c in enumerate(cells):
            if c is None:
                continue
            x, y = (2 + i) * 32, (1 + r) * 32
            canvas.alpha_composite(wood, (x, y))
            if c != ".":
                canvas.alpha_composite(sprite(c), (x, y))
    canvas.resize((canvas.width * 3, canvas.height * 3), Image.NEAREST).save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", type=Path)
    a = ap.parse_args()
    if a.scene:
        scene(a.scene)
        print(a.scene)
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for c in COMBOS:
        sprite(c).save(OUT / f"bridge_rail_{c}.png")
    print(f"{len(COMBOS)} PNG en {OUT}")


if __name__ == "__main__":
    main()
