#!/usr/bin/env python3.11
"""Tapestries con banderas, estandartes de guerra y trofeos de jefes, a partir del purple tapestry (1857).

Trofeos: terciopelo oscuro con borde dorado y el jefe de frente (cuadro quieto mirando al sur de su looktype,
recortado y centrado). Los sueltan los jefes como rare (docs/gameplay/HANGABLES.md).

El tapestry de 7.6 es 2x2 con 3 patrones: 0 enrollado (en el suelo), 1 colgado en pared horizontal (la tela
es un paralelogramo: cada fila se corre a la derecha) y 2 colgado en pared vertical (cada columna se corre
hacia abajo). Para cada píxel de tela se calcula (u, v) dentro de la bandera según esa inclinación, se pinta
el color del diseño y se le aplica la sombra del original (los pliegues). El contorno negro queda igual y la
vara de arriba (o de la izquierda) pasa a madera.

  python3.11 scripts/client-rme/make_flag_tapestries.py [--preview /tmp/flags.png]

Escribe devtools/zagan-test/custom-sprites/<nombre>.png (64x192: los 3 patrones apilados), que instala
add_custom_items.py (NEW_ITEMS, prototype=1857, tiles=2, frames=3). Doc: docs/gameplay/HANGABLES.md.
"""
from __future__ import annotations

import argparse
import colorsys
import math
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts/map/kb"))
import mapdata  # noqa: E402

OUT = ROOT / "devtools" / "zagan-test" / "custom-sprites"
POS = [(32, 32), (0, 32), (32, 0), (0, 0)]   # orden .dat de un 2x2: abajo-der, abajo-izq, arriba-der, arriba-izq
ROD = (150, 100, 50)                          # vara de madera


def base_stack() -> Image.Image:
    r = mapdata.Renderer()
    e = r.entry(1857)
    img = Image.new("RGBA", (64, 192), (0, 0, 0, 0))
    for p in range(3):
        for sid, (x, y) in zip(e["sprites"][p * 4:(p + 1) * 4], POS):
            px = r.spr.pixels(sid)
            for yy in range(32):
                for xx in range(32):
                    if px[yy][xx]:
                        img.putpixel((x + xx, 64 * p + y + yy), (*px[yy][xx], 255))
    return img


# --- diseños: (u, v) en 0..1, u de izquierda a derecha y v de arriba abajo -> (r, g, b) -------------
def brazil(u, v):
    if math.hypot((u - 0.5) * 1.4, v - 0.5) < 0.2:
        return (40, 60, 160) if abs(v - 0.5 - (u - 0.5) * 0.3) > 0.04 else (240, 240, 240)
    if abs(u - 0.5) / 0.44 + abs(v - 0.5) / 0.4 < 1:
        return (250, 215, 30)
    return (0, 150, 60)


def chile(u, v):
    if v < 0.5:
        if u < 0.38:
            return (250, 250, 250) if abs(u - 0.19) + abs(v - 0.25) < 0.09 else (0, 57, 166)
        return (245, 245, 245)
    return (213, 43, 30)


def usa(u, v):
    if u < 0.45 and v < 7 / 13:
        return (250, 250, 250) if (int(u * 14) + int(v * 13)) % 2 == 0 and int(u * 14) % 2 == 0 else (40, 50, 130)
    return (200, 30, 40) if int(v * 13) % 2 == 0 else (245, 245, 245)


def argentina(u, v):
    if 1 / 3 <= v < 2 / 3:
        return (250, 190, 40) if math.hypot((u - 0.5) * 1.4, v - 0.5) < 0.1 else (245, 245, 245)
    return (110, 170, 225)


def pirate(u, v):
    head = math.hypot((u - 0.5) * 1.2, v - 0.36) < 0.2
    eye = math.hypot((u - 0.42) * 1.2, v - 0.36) < 0.06 or math.hypot((u - 0.58) * 1.2, v - 0.36) < 0.06
    jaw = 0.42 < u < 0.58 and 0.5 < v < 0.6
    bones = 0.62 < v < 0.9 and (abs((u - 0.5) - (v - 0.76) * 1.3) < 0.06 or abs((u - 0.5) + (v - 0.76) * 1.3) < 0.06)
    if (head and not eye) or jaw or bones:
        return (235, 235, 225)
    return (20, 20, 24)


def war_swords(u, v):
    if u < 0.08 or u > 0.92 or v < 0.06 or v > 0.94:
        return (220, 170, 40)                                   # borde dorado
    for d in (u - v, (1 - u) - v):
        if abs(d) < 0.06 and 0.18 < v < 0.82:
            return (225, 225, 235) if v < 0.66 else (220, 170, 40)  # hoja plateada, empuñadura dorada
    return (130, 10, 10)


def royal(u, v):
    if u < 0.08 or u > 0.92 or v < 0.06 or v > 0.94:
        return (220, 170, 40)
    base = 0.25 < u < 0.75 and 0.5 < v < 0.62
    spikes = 0.32 < v <= 0.5 and any(abs(u - c) < 0.06 + (v - 0.32) * 0.15 for c in (0.3, 0.5, 0.7))
    jewel = math.hypot((u - 0.5) * 1.2, v - 0.56) < 0.04
    if jewel:
        return (200, 20, 40)
    if base or spikes:
        return (245, 200, 50)
    return (70, 20, 110)


def trophy(look: int, velvet):
    """Diseño: el jefe (looktype, mirando al sur, quieto) centrado sobre terciopelo, con borde dorado."""
    sys.path.insert(0, str(HERE))
    import add_recolor_look as L
    things = L.load_things(ROOT / "devtools/rme/rme-client-760")
    frames, size = L.look_frames(things, look)
    frame = frames[2]                                    # anim 0, dirección 2 (sur)
    pts = [(i % size, i // size) for i, p in enumerate(frame) if p[3]]
    x0, x1 = min(x for x, _ in pts), max(x for x, _ in pts)
    y0, y1 = min(y for _, y in pts), max(y for _, y in pts)
    w, h = x1 - x0 + 1, y1 - y0 + 1
    side = max(w, h)
    ox, oy = x0 - (side - w) / 2, y0 - (side - h) / 2   # cuadrado centrado sobre la figura

    def design(u, v):
        if u < 0.07 or u > 0.93 or v < 0.05 or v > 0.95:
            return (220, 170, 40)
        iu, iv = (u - 0.1) / 0.8, (v - 0.12) / 0.8
        if 0 <= iu < 1 and 0 <= iv < 1:
            x, y = int(ox + iu * side), int(oy + iv * side)
            if 0 <= x < size and 0 <= y < size and frame[y * size + x][3]:
                return frame[y * size + x][:3]
        return velvet
    return design


TROPHIES = {   # nombre del PNG -> (looktype del jefe, color del terciopelo: que contraste con el jefe)
    "demodras_trophy": (39, (22, 28, 52)),            # dragón rojo sobre azul pizarra
    "orshabaal_trophy": (35, (18, 22, 44)),           # demonio rojo sobre azul noche
    "old_widow_trophy": (38, (40, 18, 48)),           # araña naranja sobre violeta oscuro
    "ashen_lord_trophy": (239, (12, 38, 44)),         # ceniza y brasas sobre verde azulado
    "fallen_emperor_trophy": (244, (16, 38, 22)),     # violeta sobre verde oscuro
    "lord_of_elvenbane_trophy": (185, (18, 22, 52)),  # dorado y esmeralda sobre azul real
    # monstruos nuevos (rare 0,5 %, también sus variantes rage) y jefes de las torres de Elvenbane (5 %)
    "black_dragon_trophy": (230, (70, 18, 18)),
    "dark_hydra_trophy": (241, (44, 48, 20)),
    "root_colossus_trophy": (243, (16, 22, 48)),
    "emerald_scarab_trophy": (242, (52, 16, 24)),
    "frost_dragon_trophy": (231, (36, 16, 44)),
    "hellhound_trophy": (238, (78, 72, 60)),
    "imperial_hero_trophy": (240, (16, 40, 24)),
    "red_kongra_trophy": (254, (12, 40, 44)),
    "elvenbane_ranger_trophy": (222, (50, 16, 20)),
    "elven_archmage_trophy": (223, (40, 36, 14)),
    "orc_warchief_trophy": (224, (14, 40, 40)),
    "thornwarden_trophy": (226, (16, 40, 20)),
}

DESIGNS = {
    "brazil_tapestry": brazil,
    "chile_tapestry": chile,
    "usa_tapestry": usa,
    "argentina_tapestry": argentina,
    "pirate_banner": pirate,
    "war_banner": war_swords,
    "royal_banner": royal,
}


def lum(c):
    return colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)[2]


def paint(base: Image.Image, design) -> Image.Image:
    out = base.copy()
    for p in range(3):
        y0 = 64 * p
        cloth = {(x, y) for y in range(64) for x in range(64)
                 if base.getpixel((x, y0 + y))[3] and lum(base.getpixel((x, y0 + y))) > 0.18}
        if not cloth:
            continue
        mean = sum(lum(base.getpixel((x, y0 + y))) for x, y in cloth) / len(cloth)
        xs = [x for x, _ in cloth]
        ys = [y for _, y in cloth]
        top, bottom, left, right = min(ys), max(ys), min(xs), max(xs)
        rows = {y: [x for x, yy in cloth if yy == y] for y in set(ys)}
        cols = {x: [y for xx, y in cloth if xx == x] for x in set(xs)}
        for x, y in cloth:
            if p == 1:          # pared horizontal: vara arriba, filas corridas
                if y <= top + 1:
                    color = ROD
                else:
                    r = rows[y]
                    color = design((x - min(r)) / max(1, max(r) - min(r)), (y - top - 2) / max(1, bottom - top - 2))
            elif p == 2:        # pared vertical: vara a la izquierda, columnas corridas
                if x <= left + 1:
                    color = ROD
                else:
                    c = cols[x]
                    color = design((x - left - 2) / max(1, right - left - 2), (y - min(c)) / max(1, max(c) - min(c)))
            else:               # enrollado: el cuadrado entero
                color = design((x - left) / max(1, right - left), (y - top) / max(1, bottom - top))
            k = max(0.65, min(1.2, lum(base.getpixel((x, y0 + y))) / mean))
            out.putpixel((x, y0 + y), tuple(min(255, int(ch * k)) for ch in color) + (255,))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()
    base = base_stack()
    OUT.mkdir(parents=True, exist_ok=True)
    sheets = []
    designs = dict(DESIGNS)
    designs.update({name: trophy(look, velvet) for name, (look, velvet) in TROPHIES.items()})
    for name, design in designs.items():
        img = paint(base, design)
        img.save(OUT / f"{name}.png")
        sheets.append(img)
        print(f"OK {OUT / (name + '.png')}")
    if a.preview:
        prev = Image.new("RGBA", (len(sheets) * 74, 64 * 3 + 20), (70, 70, 76, 255))
        for i, img in enumerate(sheets):
            for p in range(3):
                prev.alpha_composite(img.crop((0, 64 * p, 64, 64 * p + 64)), (i * 74, p * 70))
        prev.resize((prev.width * 3, prev.height * 3), Image.NEAREST).save(a.preview)
        print(f"preview {a.preview}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
