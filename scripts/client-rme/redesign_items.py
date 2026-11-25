#!/usr/bin/env python3
"""Rediseño de los ítems que eran un recolor de un ítem vanilla (24 nov 2026).

Gonzalo: "hay muchos items que solo les cambiaste el color, y quedaron cambios mínimos como la nueva dragon
lance". Este script reemplaza el sprite de 35 de esos 44 ítems por uno con forma propia. Volvieron a su dibujo por
pedido de Gonzalo: aurora shield 20165, starbinder hood 20118, imperial crown armor 20161, sapphire crown armor 20162
y las 5 armas (reachbrand lance 20119, rift hammer 20111, granite mace 20115, boltworker crossbow 20120, black fire
sword 20193). Dos maneras:

- Desde cero con el motor de draw_zagan_items.py (piezas a 4x con volumen, luz arriba-izquierda, contorno):
  runas, gemas, orbe y amuletos.
- Híbrido: el sprite viejo (el recolor) como cuerpo, más piezas nuevas encima o detrás (alas, púas, gemas,
  hombreras, llamas, grabados) y recortes que cambian la silueta. Armaduras, piernas, cascos, escudos, botas.

Fuente del sprite viejo: docs/items-and-map/img/items-redesign/old/<sid>.png (copia del cliente antes del
cambio; así el script se puede repetir sin acumular). La lista sale de find_recolor_items.py.

  python3.11 scripts/client-rme/redesign_items.py --sheets DIR        # hojas original / viejo / nuevo (x8)
  python3.11 scripts/client-rme/redesign_items.py --png-dir DIR       # PNG nuevos
  python3.11 scripts/client-rme/redesign_items.py --apply devtools/rme/rme-client-760

--apply reemplaza en el lugar los sprites que ya tiene cada client id (todos tienen un único dueño): no cambia
el .dat, ni la cantidad de sprites del .spr, ni el OTB, ni ningún id. También escribe los PNG de
devtools/zagan-test/custom-sprites que usa add_custom_items.py (crimson cage rune, frost
mine rune) para que reinstalar no vuelva al dibujo viejo.
Doc: docs/items-and-map/ITEMS_REDESIGN_2026_11_24.md
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build_zagan_test_assets as B  # noqa: E402
import draw_zagan_items as Z  # noqa: E402
from draw_zagan_items import (GX, GY, N, SS, Frame, Mat, Sprite, capsule, disc, poly_in, poly_ts,  # noqa: E402
                              poly_xy, polyline, sparkle, strip)

IMG = REPO / "docs/items-and-map/img/items-redesign"
SPRITES = REPO / "devtools/zagan-test/custom-sprites"

# ------------------------------------------------------------------ materiales propios
HOT = Mat([(70, 6, 6), (150, 20, 10), (220, 70, 20), (255, 150, 40), (255, 220, 110), (255, 252, 210)], 0.8, 30,
          (255, 250, 200))
SAND = Mat([(64, 40, 22), (118, 82, 48), (170, 130, 82), (210, 176, 120), (240, 216, 166)], 0.3, 18)
GRANITE = Mat([(30, 30, 38), (66, 66, 76), (106, 104, 112), (150, 146, 150), (200, 196, 196)], 0.35, 20)
PINK_GRANITE = Mat([(46, 26, 30), (92, 58, 60), (140, 98, 94), (186, 144, 134), (226, 194, 180)], 0.35, 20)
VIOLET_METAL = Mat([(24, 10, 40), (56, 24, 90), (100, 50, 150), (150, 100, 206), (210, 180, 250), (255, 250, 255)],
                   0.8, 34)
TEAL = Mat([(6, 40, 46), (16, 86, 92), (36, 142, 146), (100, 204, 200), (190, 246, 240)], 0.6, 30)
ROSE = Mat([(60, 12, 34), (120, 30, 70), (186, 70, 120), (230, 130, 170), (255, 210, 230)], 0.45, 24)
OLIVE = Mat([(26, 30, 10), (56, 64, 24), (96, 108, 44), (140, 152, 72), (190, 200, 120)], 0.3, 18)
STEELGREY = Mat([(30, 34, 46), (66, 74, 90), (110, 120, 138), (160, 170, 186), (214, 222, 234)], 0.5, 26)
MAGENTA = Mat([(50, 6, 40), (110, 20, 90), (176, 46, 150), (226, 110, 206), (255, 200, 245)], 0.5, 26)
AMBER_STONE = Mat([(70, 30, 6), (140, 70, 16), (206, 120, 30), (246, 176, 70), (255, 226, 150)], 0.4, 22)
FROST_STONE = Mat([(20, 40, 80), (44, 84, 140), (86, 136, 196), (150, 192, 236), (220, 240, 255)], 0.6, 30)
CRIMSON_STONE = Mat([(34, 4, 10), (74, 10, 20), (124, 24, 34), (170, 52, 56), (214, 110, 104)], 0.45, 24)
LEAF = Mat([(6, 40, 14), (16, 92, 30), (40, 150, 50), (110, 210, 90), (200, 250, 170)], 0.5, 24)

Color = tuple[int, int, int]


# ------------------------------------------------------------------ utilidades
def P(*pts):
    return poly_xy(list(pts))


def mirror(pts, cx):
    return [(2 * cx - x, y) for x, y in pts]


def up4(m32: np.ndarray) -> np.ndarray:
    return np.repeat(np.repeat(m32, SS, 0), SS, 1)


def down4(m: np.ndarray) -> np.ndarray:
    return m.reshape(32, SS, 32, SS).mean((1, 3)) >= 0.5


def erode32(m: np.ndarray, k: int = 1) -> np.ndarray:
    for _ in range(k):
        p = np.pad(m, 1)
        m = m & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return m


def canvas_to_arr(cv) -> np.ndarray:
    a = np.zeros((32, 32, 4), np.uint8)
    for (x, y), c in cv.items():
        a[y, x, :3] = c
        a[y, x, 3] = 255
    return a


def star(cx, cy, r_out, r_in, n=4, rot=-math.pi / 2):
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = rot + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return poly_xy(pts)


def ring(cx, cy, r, w):
    return np.abs(np.hypot(GX - cx, GY - cy) - r) <= w


def flame_tongues(y_base, x0, x1, n, h, w, phase=0.0, jitter=0.0):
    m = np.zeros((N, N), bool)
    step = (x1 - x0) / n
    for i in range(n):
        cx = x0 + step * (i + 0.5)
        hh = h * (0.75 + 0.25 * math.sin(i * 2.1 + phase))
        lean = jitter * math.sin(i * 1.7 + phase)
        m |= P((cx - w, y_base), (cx + lean, y_base - hh), (cx + w, y_base))
    return m


class Hybrid:
    """Sprite viejo como cuerpo + piezas nuevas detrás (back) y delante (front)."""

    def __init__(self, sid: int):
        self.base = np.array(Image.open(IMG / "old" / f"{sid}.png").convert("RGBA"))[:32].copy()
        self.back = Sprite()
        self.front = Sprite()
        self.paint = Sprite()  # dibujos planos sobre el cuerpo: sin contorno propio
        self.fx: list[tuple[int, int, Color]] = []

    @property
    def alpha4(self) -> np.ndarray:
        return up4(self.base[..., 3] > 0)

    def inner(self, k: int = 1) -> np.ndarray:
        return up4(erode32(self.base[..., 3] > 0, k))

    def erase(self, mask4: np.ndarray) -> None:
        m = down4(mask4)
        before = self.base[..., 3] > 0
        self.base[m] = 0
        # contorno nuevo en los bordes que quedaron expuestos
        now = self.base[..., 3] > 0
        out = self.base.copy()
        for y in range(32):
            for x in range(32):
                if now[y, x] or not before[y, x]:
                    continue
                nb = [self.base[q[1], q[0]] for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                      if 0 <= q[0] < 32 and 0 <= q[1] < 32 and now[q[1], q[0]]]
                if not nb:
                    continue
                avg = np.mean([c[:3] for c in nb], 0)
                if max(c[:3].astype(int).sum() for c in nb) < 90:
                    continue  # ya es contorno
                c = avg * 0.22 + np.array([10, 6, 22]) * 0.78 * 0.9
                out[y, x] = (*np.clip(c, 0, 255).astype(np.uint8), 255)
        self.base = out

    def tint(self, fn) -> None:
        """fn(r,g,b) -> (r,g,b) sobre los píxeles del cuerpo."""
        for y in range(32):
            for x in range(32):
                if self.base[y, x, 3]:
                    self.base[y, x, :3] = fn(*[int(v) for v in self.base[y, x, :3]])

    def dot(self, x, y, c):
        self.fx.append((x, y, c))

    def render(self) -> Image.Image:
        out = np.zeros((32, 32, 4), np.uint8)
        if self.back.n:
            b = canvas_to_arr(self.back.finish())
            out[b[..., 3] > 0] = b[b[..., 3] > 0]
        m = self.base[..., 3] > 0
        out[m] = self.base[m]
        if self.paint.n:
            cov = (self.paint.pid.reshape(32, SS, 32, SS) >= 0).mean((1, 3)) >= 0.42
            p = canvas_to_arr(self.paint.finish())
            sel = cov & m & (p[..., 3] > 0)
            out[sel] = p[sel]
        if self.front.n or self.front.fx:
            f = canvas_to_arr(self.front.finish())
            out[f[..., 3] > 0] = f[f[..., 3] > 0]
        for x, y, c in self.fx:
            if 0 <= x < 32 and 0 <= y < 32:
                out[y, x] = (*c, 255)
        return Image.fromarray(out)


def from_canvas(cv) -> Image.Image:
    return Image.fromarray(canvas_to_arr(cv))


def glowline(sp: Sprite, pts, r, inner: Color, outer: Color | None = None, clip=None):
    m = polyline(pts, r)
    if clip is not None:
        m &= clip
    sp.glow(m, inner, outer)


# ARMAS: las 5 (reachbrand lance 20119, rift hammer 20111, granite mace 20115, boltworker crossbow 20120 y
# black fire sword 20193) volvieron a su dibujo anterior por pedido de Gonzalo (25 nov 2026); sus funciones se
# borraron. El dibujo nuevo está en la historia de git (93e90ebd).


# ================================================================== RUNAS (desde cero)

RUNE_SHAPES = {
    "round": [(8.6, 10.0), (12.0, 7.6), (19.6, 7.2), (23.8, 10.4), (24.8, 16.4), (23.4, 22.6), (19.0, 26.0),
              (12.4, 26.2), (8.4, 23.0), (7.2, 16.0)],
    "tall": [(10.6, 7.4), (14.4, 5.4), (19.8, 6.0), (22.4, 9.4), (23.0, 17.0), (21.8, 24.4), (17.6, 27.6),
             (12.6, 27.0), (9.6, 23.4), (9.2, 14.0)],
    "wide": [(6.0, 13.4), (9.2, 9.8), (16.0, 9.0), (23.4, 10.0), (26.8, 14.0), (25.8, 20.0), (21.2, 23.8),
             (12.4, 24.2), (7.0, 20.8)],
    "shard": [(9.4, 7.8), (17.8, 5.6), (24.6, 9.4), (25.4, 17.0), (21.0, 26.0), (14.2, 26.8), (8.0, 22.4),
              (6.8, 13.6)],
    "drop": [(15.8, 5.4), (20.6, 10.0), (24.2, 15.8), (23.6, 22.4), (19.0, 26.4), (12.8, 26.4), (8.4, 22.4),
             (8.2, 15.8), (11.8, 9.6)],
    "kite": [(16.0, 5.4), (24.2, 11.6), (22.8, 21.6), (16.0, 27.2), (9.2, 21.6), (7.8, 11.6)],
    "chunk": [(8.6, 9.0), (14.0, 7.0), (21.6, 7.8), (25.0, 11.6), (24.4, 19.4), (21.4, 25.0), (13.6, 26.4),
              (8.6, 23.6), (7.0, 15.0)],
}


def rune_base(sp: Sprite, shape: str, mat: Mat):
    m = poly_xy(RUNE_SHAPES[shape])
    tex = 1 - 0.1 * ((np.sin(GX * 3.1 + GY * 1.7) * np.sin(GY * 2.3 - GX * 0.9)) > 0.45)
    sp.add(m, mat, bevel=2.4, profile="round", height=0.9, pattern=tex)
    return m


def engrave(sp: Sprite, groove: np.ndarray, glow_in: Color, glow_out: Color, halo: np.ndarray | None = None):
    if halo is not None:
        sp.glow(halo, (20, 10, 30))
    sp.glow(groove, glow_in, glow_out)


def rune_lifewell():
    sp = Sprite()
    m = rune_base(sp, "drop", ROSE)
    heart = (disc(13.6, 15.0, 3.2) | disc(18.6, 15.0, 3.2) | P((10.6, 16.2), (21.6, 16.2), (16.1, 23.4))) & m
    inner = (disc(13.6, 15.0, 2.0) | disc(18.6, 15.0, 2.0) | P((12.0, 16.0), (20.2, 16.0), (16.1, 21.6)))
    cross = (polyline([(16.1, 13.6), (16.1, 19.4)], 0.6) | polyline([(13.4, 16.6), (18.8, 16.6)], 0.6))
    sp.glow(heart & ~inner, (255, 200, 220), (210, 40, 100))
    sp.glow(cross, (255, 255, 255), (255, 170, 210))
    sparkle(sp, 10, 9, big=True)
    return from_canvas(sp.finish())


def rune_emberstorm():
    sp = Sprite()
    m = rune_base(sp, "wide", AMBER_STONE)
    fl = np.zeros((N, N), bool)
    for cx, h in ((11.0, 8.0), (16.4, 11.0), (21.8, 8.0)):
        fl |= P((cx - 2.6, 21.6), (cx - 1.4, 21.6 - h * 0.55), (cx + 0.4, 21.6 - h), (cx + 1.2, 21.6 - h * 0.45),
                (cx + 2.6, 21.6))
    sp.glow(polyline([(7.6, 21.8), (25.4, 21.8)], 1.6) & m, (20, 8, 4))
    sp.glow(fl & m, (255, 244, 170), (230, 70, 20))
    sparkle(sp, 9, 10, big=True)
    return from_canvas(sp.finish())


def rune_shattercall():
    sp = Sprite()
    m = rune_base(sp, "shard", STEELGREY)
    burst = star(16.4, 16.6, 6.8, 2.0, n=6, rot=-math.pi / 2 + 0.2) & m
    core = star(16.4, 16.6, 3.6, 1.2, n=6, rot=-math.pi / 2 + 0.2)
    sp.glow(burst & ~core, (210, 236, 255), (60, 110, 190))
    sp.glow(core, (255, 255, 255))
    cracks = polyline([(6.4, 12.0), (9.6, 13.0), (10.6, 11.0)], 0.35) | polyline([(22.6, 26.0), (21.0, 23.6)], 0.35)
    sp.glow(cracks & m, (30, 34, 46))
    sparkle(sp, 10, 7, big=True)
    return from_canvas(sp.finish())


def rune_arcflash():
    sp = Sprite()
    m = rune_base(sp, "tall", Mat([(70, 50, 6), (140, 110, 16), (206, 176, 40), (246, 226, 90), (255, 250, 190)],
                                  0.5, 24))
    bolt = [(19.0, 8.0), (13.2, 16.4), (17.6, 16.6), (13.0, 25.4)]
    sp.glow(polyline(bolt, 1.9) & m, (36, 24, 8))
    sp.glow(polyline(bolt, 1.1) & m, (255, 255, 230), (110, 190, 255))
    sparkle(sp, 11, 8, big=True)
    return from_canvas(sp.finish())


def rune_flamecoil():
    sp = Sprite()
    m = rune_base(sp, "round", MAGENTA)
    pts = [(16.2 + (0.5 + 0.5 * a) * math.cos(a * 1.0), 16.6 + (0.5 + 0.5 * a) * math.sin(a * 1.0))
           for a in np.linspace(0.3, 13.2, 60)]
    sp.glow(polyline(pts, 1.5) & m, (30, 6, 26))
    sp.glow(polyline(pts, 0.85) & m, (255, 220, 250), (255, 80, 170))
    sp.glow((P((21.0, 10.0), (23.4, 5.6), (22.8, 11.0)) | P((22.6, 12.4), (26.0, 9.6), (23.8, 13.8))) & m, (255, 170, 230))
    sparkle(sp, 10, 9, big=True)
    return from_canvas(sp.finish())


def rune_mireveil():
    sp = Sprite()
    m = rune_base(sp, "wide", OLIVE)
    g = np.zeros((N, N), bool)
    for x, y, r in ((11.6, 13.4, 2.6), (19.0, 12.0, 2.0), (22.4, 16.6, 1.4), (15.6, 18.0, 1.6)):
        g |= ring(x, y, r, 0.55)
    waves = [(6.6 + i * 0.5, 21.6 + 1.1 * math.sin(i * 0.9)) for i in range(40)]
    g |= polyline(waves, 0.6)
    sp.glow(g & m, (220, 255, 150), (90, 150, 40))
    sparkle(sp, 9, 10, big=True)
    return from_canvas(sp.finish())


def rune_stonelock():
    sp = Sprite()
    m = rune_base(sp, "chunk", Z.STONE_BROWN)
    shackle = ring(16.0, 13.4, 3.6, 0.75) & (GY <= 14.0)
    shackle |= (np.abs(GX - 12.4) <= 0.75) & (GY >= 13.4) & (GY <= 16.0)
    shackle |= (np.abs(GX - 19.6) <= 0.75) & (GY >= 13.4) & (GY <= 16.0)
    body = P((10.4, 15.6), (21.6, 15.6), (21.6, 24.0), (10.4, 24.0))
    hole = disc(16.0, 18.8, 1.1) | P((15.4, 19.2), (16.6, 19.2), (16.8, 22.0), (15.2, 22.0))
    sp.glow(shackle, (255, 226, 160), (200, 140, 60))
    sp.add(body, Z.IRON, bevel=1.2)
    sp.glow(hole, (30, 16, 10))
    sparkle(sp, 9, 9, big=True)
    return from_canvas(sp.finish())


def rune_venomthread():
    sp = Sprite()
    m = rune_base(sp, "kite", TEAL)
    pts = [(16.0 + 4.4 * math.sin(t * 1.15), 8.6 + t * 1.6) for t in np.linspace(0, 10.6, 50)]
    sp.glow(polyline(pts, 1.6) & m, (6, 26, 22))
    sp.glow(polyline(pts, 0.9) & m, (210, 255, 200), (60, 200, 110))
    sp.glow(disc(*pts[0], 1.7) & m, (210, 255, 200), (60, 200, 110))
    sp.dot(int(pts[0][0]) - 1, int(pts[0][1]), (230, 30, 30))
    sp.dot(int(pts[0][0]) + 1, int(pts[0][1]), (230, 30, 30))
    sparkle(sp, 10, 10, big=True)
    return from_canvas(sp.finish())


def rune_crimson_cage():
    sp = Sprite()
    m = rune_base(sp, "shard", CRIMSON_STONE)
    def bars(w):
        c = np.zeros((N, N), bool)
        for x in (12.6, 16.2, 19.8):
            c |= (np.abs(GX - x) <= w) & (GY >= 10.0 - w) & (GY <= 24.0 + w)
        for y in (13.6, 20.4):
            c |= (np.abs(GY - y) <= w) & (GX >= 9.4 - w) & (GX <= 23.0 + w)
        return c
    sp.glow(bars(1.5) & m, (24, 2, 8))
    sp.glow(bars(0.7) & m, (255, 244, 236), (255, 120, 110))
    sparkle(sp, 9, 9, big=True)
    return from_canvas(sp.finish())


def rune_frost_mine():
    sp = Sprite()
    m = rune_base(sp, "round", FROST_STONE)
    fl = np.zeros((N, N), bool)
    cx, cy = 16.2, 16.6
    for i in range(6):
        a = i * math.pi / 3 + math.pi / 6
        ex, ey = cx + 6.4 * math.cos(a), cy + 6.4 * math.sin(a)
        fl |= polyline([(cx, cy), (ex, ey)], 0.62)
        mx, my = cx + 4.0 * math.cos(a), cy + 4.0 * math.sin(a)
        for d in (-0.75, 0.75):
            fl |= polyline([(mx, my), (mx + 2.0 * math.cos(a + d), my + 2.4 * math.sin(a + d))], 0.5)
    sp.glow(fl & m, (255, 255, 255), (110, 200, 255))
    sparkle(sp, 10, 9, big=True)
    return from_canvas(sp.finish())


# ================================================================== GEMAS, ORBE, AMULETOS, RELIQUIA

def sunstone(gem_mat: Mat, ray_mat: Mat, leafy: bool, glow: Color) -> Image.Image:
    sp = Sprite()
    cx, cy = 16.4, 17.0
    rays = np.zeros((N, N), bool)
    for i in range(8):
        a = -math.pi / 2 + i * math.pi / 4
        r1 = 12.6 if i % 2 == 0 else 9.8
        w = 0.42 if not leafy else 0.55
        if leafy:
            pts = [(cx + 5.0 * math.cos(a - w), cy + 5.0 * math.sin(a - w)),
                   (cx + (r1 - 2.6) * math.cos(a - 0.22), cy + (r1 - 2.6) * math.sin(a - 0.22)),
                   (cx + r1 * math.cos(a), cy + r1 * math.sin(a)),
                   (cx + (r1 - 2.6) * math.cos(a + 0.22), cy + (r1 - 2.6) * math.sin(a + 0.22)),
                   (cx + 5.0 * math.cos(a + w), cy + 5.0 * math.sin(a + w))]
        else:
            pts = [(cx + 5.0 * math.cos(a - w), cy + 5.0 * math.sin(a - w)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a)),
                   (cx + 5.0 * math.cos(a + w), cy + 5.0 * math.sin(a + w))]
        rays |= poly_xy(pts)
    sp.add(rays, ray_mat, bevel=1.0, profile="ridge")
    oct_ = [(cx + 6.0 * math.cos(a), cy + 6.0 * math.sin(a)) for a in np.linspace(math.pi / 8, 2 * math.pi + math.pi / 8, 8,
                                                                                    endpoint=False)]
    sp.add(poly_xy(oct_), gem_mat, bevel=3.2, profile="ridge", height=1.2)
    sp.glow(star(cx, cy, 2.6, 0.8, n=4), glow)
    sparkle(sp, int(cx) - 3, int(cy) - 3, big=True)
    return from_canvas(sp.finish())


def hollow_orb() -> Image.Image:
    """Crystal ball -> orbe hueco: vidrio oscuro con un vórtice vacío adentro, grietas y garras de hueso que lo
    sostienen."""
    sp = Sprite()
    cx, cy, r = 15.6, 13.6, 9.4
    sp.add(P((8.0, 30.0), (24.0, 30.0), (22.0, 26.6), (10.0, 26.6)), Z.DARK_WOOD, bevel=1.0)
    orb = disc(cx, cy, r)
    sp.add(orb, Mat([(16, 10, 28), (40, 28, 66), (76, 60, 116), (126, 110, 170), (200, 190, 236)], 0.9, 40),
           bevel=r, profile="round", height=1.0)
    pts = [(cx + 0.5 * a * math.cos(a * 1.25), cy + 0.5 * a * math.sin(a * 1.25)) for a in np.linspace(0.4, 13.0, 60)]
    sp.glow(polyline(pts, 0.75) & disc(cx, cy, r - 1.2), (170, 140, 255), (60, 30, 120))
    sp.glow(disc(cx, cy, 1.6), (8, 4, 14))
    sp.glow(polyline([(cx + 3.0, cy - 8.6), (cx + 4.0, cy - 5.6), (cx + 6.6, cy - 4.6)], 0.32), (230, 220, 255))
    for sx in (-1, 1):
        sp.add(P((cx + 7.6 * sx, 27.0), (cx + 10.2 * sx, 19.6), (cx + 8.6 * sx, 14.0), (cx + 7.0 * sx, 19.4),
                 (cx + 5.6 * sx, 27.0)), Z.BONE, bevel=1.0, profile="ridge")
    sp.add(P((cx - 1.4, 27.4), (cx, 21.6), (cx + 1.4, 27.4)), Z.BONE, bevel=0.8, profile="ridge")
    sparkle(sp, int(cx - 4), int(cy - 4), big=True)
    return from_canvas(sp.finish())


def venomqueen_heart() -> Image.Image:
    h = Hybrid(20107)
    h.erase(disc(15.6, 26.6, 4.4))
    f = h.front
    heart = disc(13.2, 23.8, 3.0) | disc(18.0, 23.8, 3.0) | P((10.2, 24.6), (21.0, 24.6), (15.6, 30.6))
    f.add(heart, Z.VENOM, bevel=2.6, profile="round", height=1.2)
    f.add(disc(15.6, 20.4, 1.8) | P((13.4, 20.6), (17.8, 20.6), (15.6, 22.4)), Z.JADE, bevel=1.0)  # cabeza de víbora
    f.dot(14, 20, (255, 40, 40))
    f.dot(17, 20, (255, 40, 40))
    sparkle(f, 12, 23)
    for x, y in ((9, 28), (22, 27), (7, 24)):
        f.dot(x, y, (150, 255, 110))
    return h.render()


def bonepriest_phylactery() -> Image.Image:
    h = Hybrid(20108)
    h.erase(disc(15.6, 23.6, 6.0))
    f = h.front
    f.add(disc(15.6, 22.0, 4.8), Z.BONE, bevel=3.0, profile="round")
    f.add(P((12.6, 24.6), (18.6, 24.6), (18.0, 28.8), (13.2, 28.8)), Z.BONE, bevel=1.0)
    for x in (13.4, 17.8):
        f.glow(disc(x, 22.2, 1.25), (230, 160, 255), (120, 40, 200))
    f.glow(P((15.0, 24.4), (16.2, 24.4), (15.6, 23.2)), (40, 20, 40))
    for x in (14.2, 15.6, 17.0):
        f.glow((np.abs(GX - x) <= 0.3) & (GY >= 26.0) & (GY <= 28.6), (70, 50, 60))
    f.add(P((11.2, 18.6), (12.8, 15.6), (14.2, 18.0)) | P((17.0, 18.0), (18.4, 15.6), (20.0, 18.6)), Z.AMETHYST,
          bevel=0.8, profile="ridge")
    return h.render()


def relic_of_ulm() -> Image.Image:
    h = Hybrid(20144)
    b = h.back
    for sx in (-1, 1):
        cx = 15.5
        wing = [(cx + 9.0 * sx, 18.6), (cx + 14.4 * sx, 13.0), (cx + 16.0 * sx, 7.6), (cx + 13.6 * sx, 10.0),
                (cx + 14.0 * sx, 6.0), (cx + 11.6 * sx, 9.6), (cx + 11.0 * sx, 6.4), (cx + 9.4 * sx, 11.4),
                (cx + 7.0 * sx, 15.4)]
        b.add(poly_xy(wing), Z.IVORY, bevel=1.2, profile="ridge")
        for k in range(3):
            b.glow(polyline([(cx + (9.6 + k * 1.6) * sx, 16.0 - k * 1.2), (cx + (12.4 + k * 1.2) * sx, 10.6 - k * 1.4)],
                            0.28), (150, 130, 110))
    f = h.front
    f.add(disc(15.6, 7.6, 3.2), Z.JADE, bevel=3.0, height=1.3)
    sparkle(f, 14, 6, big=True)
    f.glow(ring(15.6, 7.6, 5.6, 0.32) & (GY < 6.0), (200, 255, 220))
    return h.render()


# ================================================================== ESCUDOS (híbridos)

def quarry_ward():
    h = Hybrid(20101)
    ang = [0.15, 1.2, 2.2, 3.1, 4.1, 5.2]
    rad = [14.4, 14.8, 14.0, 14.6, 14.2, 14.8]
    h.erase(~poly_xy([(16 + r * math.cos(a), 15.4 + r * math.sin(a)) for a, r in zip(ang, rad)]))
    f = h.front
    band = (GY >= 13.8) & (GY <= 16.8) & h.inner(2)
    f.add(band, Z.IRON, bevel=0.9)
    for x in (5.6, 26.4):
        f.add(disc(x, 15.3, 0.9), Z.SILVER, bevel=0.9)
    tex = 1 - 0.14 * ((np.sin(GX * 2.7 + GY * 1.3) * np.sin(GY * 2.9 - GX * 1.1)) > 0.4)
    boss = [(16 + 5.2 * math.cos(a), 15.3 + 5.2 * math.sin(a)) for a in np.linspace(0.3, 2 * math.pi + 0.3, 7, endpoint=False)]
    f.add(poly_xy(boss), SAND, bevel=2.8, profile="round", height=1.2, pattern=tex)
    f.glow(polyline([(14.2, 11.4), (16.4, 14.2), (15.0, 16.6), (17.6, 19.2)], 0.42), (255, 196, 90), (230, 120, 30))
    for x, y in ((9.4, 6.8), (22.8, 6.4), (24.2, 24.0), (8.6, 23.6)):
        f.add(disc(x, y, 1.5), SAND, bevel=1.5)
    return h.render()


def ironhide_bulwark():
    h = Hybrid(20128)
    f = h.front
    c = (16.0, 15.6)
    for a in (-3 * math.pi / 4, -math.pi / 4, math.pi / 4, 3 * math.pi / 4):
        tip = (c[0] + 19.6 * math.cos(a), c[1] + 19.6 * math.sin(a))
        l = (c[0] + 11.0 * math.cos(a - 0.22), c[1] + 11.0 * math.sin(a - 0.22))
        r = (c[0] + 11.0 * math.cos(a + 0.22), c[1] + 11.0 * math.sin(a + 0.22))
        f.add(P(l, tip, r), Z.STEEL, bevel=1.2, profile="ridge")
    f.add(ring(*c, 9.6, 0.9) & h.inner(1), Z.DARK_STEEL, bevel=0.6)
    for i in range(8):
        a = i * math.pi / 4 + math.pi / 8
        f.add(disc(c[0] + 9.6 * math.cos(a), c[1] + 9.6 * math.sin(a), 1.0), Z.SILVER, bevel=1.0)
    f.add(disc(*c, 4.4), Z.STEEL, bevel=4.4, height=1.1)
    f.add(star(c[0], c[1], 3.4, 1.0, n=4, rot=-math.pi / 4), Z.SILVER, bevel=1.0, profile="ridge")
    sparkle(f, 14, 13, big=True)
    return h.render()


def mosaic_shield():
    h = Hybrid(20149)
    f = h.front
    field = disc(15.0, 16.0, 10.6) & h.inner(1)
    cols = [(46, 196, 190), (236, 246, 240), (26, 110, 170), (214, 170, 60)]
    for j in range(8):
        for i in range(8):
            x0, y0 = 4.0 + i * 3.0, 5.0 + j * 3.0
            cell = (GX >= x0 + 0.5) & (GX < x0 + 3.0) & (GY >= y0 + 0.5) & (GY < y0 + 3.0) & field
            if cell.any():
                f.glow(cell, cols[(i * 3 + j * 5 + (i * j) % 3) % 4])
    grout = field & ~np.zeros_like(field)
    f.glow(field & ((((GX - 4.0) % 3.0) < 0.5) | (((GY - 5.0) % 3.0) < 0.5)), (24, 50, 56))
    _ = grout
    f.add(P((15.0, 10.0), (20.0, 16.0), (15.0, 22.0), (10.0, 16.0)), Z.GOLD, bevel=2.4, profile="ridge")
    f.add(disc(15.0, 16.0, 1.4), Z.SAPPHIRE, bevel=1.4)
    for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
        x, y = 15.0 + 13.6 * math.cos(a), 16.0 + 13.6 * math.sin(a)
        f.add(P((x - 1.8, y), (x, y - 1.8), (x + 1.8, y), (x, y + 1.8)), Z.GOLD, bevel=1.2, profile="ridge")
    return h.render()


def bloodreaver_aegis():
    h = Hybrid(20150)
    b = h.back
    for sx in (-1, 1):
        cx = 15.0
        wing = [(cx + 2.6 * sx, 10.0), (cx + 3.4 * sx, 3.0), (cx + 7.0 * sx, 0.2), (cx + 10.4 * sx, 2.0),
                (cx + 14.6 * sx, 0.2), (cx + 15.6 * sx, 4.6), (cx + 13.4 * sx, 4.4), (cx + 12.6 * sx, 7.6),
                (cx + 10.0 * sx, 6.0), (cx + 8.4 * sx, 9.0)]
        b.add(poly_xy(wing), Z.CRIMSON, bevel=1.0, profile="ridge")
        b.glow(polyline([(cx + 5.2 * sx, 3.0), (cx + 8.6 * sx, 6.4)], 0.3) |
               polyline([(cx + 8.8 * sx, 1.0), (cx + 9.4 * sx, 6.4)], 0.3) |
               polyline([(cx + 12.0 * sx, 2.0), (cx + 11.4 * sx, 7.4)], 0.3), (60, 10, 18))
    f = h.front
    f.add(disc(15.0, 17.6, 2.8), Z.RUBY, bevel=2.8, height=1.3)
    sparkle(f, 14, 16)
    f.add(P((12.2, 20.6), (13.6, 20.6), (12.9, 24.4)) | P((16.4, 20.6), (17.8, 20.6), (17.1, 24.4)), Z.IVORY,
          bevel=0.6, profile="ridge")
    for x, y0 in ((7.0, 22.0), (23.0, 21.0), (15.0, 29.0)):
        f.glow(capsule(x, y0, x, y0 + 2.0, 0.55) | disc(x, y0 + 2.4, 0.9), (220, 30, 40), (120, 0, 10))
    return h.render()


def sunforge_shield():
    h = Hybrid(20151)
    c = (15.6, 16.2)
    h.erase(~disc(*c, 9.8))
    b = h.back
    rays = np.zeros((N, N), bool)
    for i in range(12):
        a = -math.pi / 2 + i * math.pi / 6
        r1 = 15.6 if i % 2 == 0 else 12.6
        rays |= P((c[0] + 8.6 * math.cos(a - 0.26), c[1] + 8.6 * math.sin(a - 0.26)),
                  (c[0] + r1 * math.cos(a), c[1] + r1 * math.sin(a)),
                  (c[0] + 8.6 * math.cos(a + 0.26), c[1] + 8.6 * math.sin(a + 0.26)))
    b.add(rays, Z.GOLD, bevel=1.2, profile="ridge")
    f = h.front
    f.add(ring(*c, 9.4, 0.85), Z.GOLD, bevel=0.85)
    f.glow(disc(*c, 4.2), (255, 250, 200), (255, 150, 40))
    for i in range(8):
        a = i * math.pi / 4
        f.glow(polyline([(c[0] + 4.6 * math.cos(a), c[1] + 4.6 * math.sin(a)),
                         (c[0] + 7.0 * math.cos(a), c[1] + 7.0 * math.sin(a))], 0.4), (255, 220, 120))
    return h.render()


def frostwarden_aegis():
    h = Hybrid(20153)
    f = h.front
    cx = 15.5
    for sx in (-1, 1):
        for (t0, t1, tipx, tipy) in ((7.0, 12.4, 11.6, 4.6), (14.0, 18.8, 10.6, 15.6), (21.0, 24.6, 8.4, 25.0)):
            f.add(P((cx + 6.4 * sx, t0), (cx + tipx * sx, tipy), (cx + 6.0 * sx, t1)), Z.ICE, bevel=1.0, profile="ridge")
    f.add(P((cx - 1.2, 3.6), (cx, -0.4), (cx + 1.2, 3.6)), Z.ICE, bevel=0.8, profile="ridge")
    fl = np.zeros((N, N), bool)
    for i in range(6):
        a = i * math.pi / 3 + math.pi / 2
        ex, ey = cx + 4.6 * math.cos(a), 14.6 + 4.6 * math.sin(a)
        fl |= polyline([(cx, 14.6), (ex, ey)], 0.5)
        mx, my = cx + 2.8 * math.cos(a), 14.6 + 2.8 * math.sin(a)
        for d in (-0.8, 0.8):
            fl |= polyline([(mx, my), (mx + 1.6 * math.cos(a + d), my + 1.6 * math.sin(a + d))], 0.4)
    f.glow(fl, (255, 255, 255), (120, 210, 255))
    for x, y in ((3, 10), (28, 20), (4, 22), (27, 7)):
        f.dot(x, y, (220, 250, 255))
    return h.render()


# ================================================================== CASCOS

def morlen_crest():
    h = Hybrid(20102)
    b = h.back
    cx = 15.5
    for sx in (-1, 1):
        wing = [(cx + 6.6 * sx, 9.0), (cx + 13.4 * sx, 2.0), (cx + 15.6 * sx, 2.6), (cx + 13.0 * sx, 6.4),
                (cx + 15.2 * sx, 7.0), (cx + 12.4 * sx, 10.4), (cx + 14.0 * sx, 11.6), (cx + 8.0 * sx, 15.0)]
        b.add(poly_xy(wing), Z.SILVER, bevel=1.1, profile="ridge")
    b.add(P((13.2, 4.0), (15.5, -0.6), (17.8, 4.0)), Z.JADE, bevel=1.0, profile="ridge")
    f = h.front
    f.add(P((15.5, 4.4), (17.4, 6.6), (15.5, 8.8), (13.6, 6.6)), Z.EMERALD, bevel=1.4, profile="ridge")
    sparkle(f, 15, 5)
    return h.render()


def fox_machina_helmet():
    h = Hybrid(20152)
    b = h.back
    for pts in ([(7.0, 9.6), (7.2, 0.4), (13.4, 5.4)], [(18.0, 5.4), (24.4, 0.4), (24.6, 9.6)]):
        b.add(poly_xy(pts), Z.SILVER, bevel=1.4, profile="ridge")
    f = h.front
    f.glow(P((8.4, 7.0), (8.6, 2.6), (11.4, 5.2)) | P((20.2, 5.2), (23.2, 2.6), (23.2, 7.0)), (255, 150, 60), (200, 80, 20))
    for x in (7.6, 23.6):
        f.add(P((x - 1.2, 18.0), (x + 1.2, 18.0), (x + 0.8, 22.4), (x - 0.8, 22.4)), Z.DARK_STEEL, bevel=0.6)
        f.glow(disc(x, 20.2, 0.6), (120, 255, 150))
    return h.render()


# ================================================================== ARMADURAS

def ashlar_plate():
    h = Hybrid(20103)
    f = h.front
    chest = h.inner(2) & P((9.0, 12.0), (23.0, 12.0), (23.0, 28.0), (9.0, 28.0))
    seams = np.zeros((N, N), bool)
    for k, y in enumerate((15.0, 19.0, 23.0, 27.0)):
        seams |= (np.abs(GY - y) <= 0.4)
        off = 0.0 if k % 2 else 2.5
        for x in np.arange(9.0 + off, 24.0, 5.0):
            seams |= (np.abs(GX - x) <= 0.4) & (GY >= y - 4.0) & (GY <= y)
    h.paint.glow(seams & chest, (150, 110, 64))
    for pts in ([(0.6, 4.4), (8.6, 2.6), (10.0, 10.4), (1.8, 12.0)], [(22.0, 2.6), (30.6, 4.4), (29.6, 12.0), (21.6, 10.4)]):
        f.add(poly_xy(pts), SAND, bevel=1.6, profile="round")
    f.glow(polyline([(1.4, 8.2), (9.0, 6.8)], 0.35) | polyline([(22.6, 6.8), (30.0, 8.2)], 0.35), (110, 76, 40))
    f.add(disc(16.0, 16.4, 2.0), AMBER_STONE, bevel=2.0, height=1.3)
    sparkle(f, 15, 15)
    return h.render()


def rubbleguard_mail():
    h = Hybrid(20109)
    zig = np.zeros((N, N), bool)
    for x in np.arange(6.0, 27.0, 4.0):
        zig |= P((x, 30.5), (x + 2.0, 26.6), (x + 4.0, 30.5))
    h.erase(zig)
    f = h.front
    tex = 1 - 0.16 * ((np.sin(GX * 2.7 + GY * 1.3) * np.sin(GY * 2.9 - GX * 1.1)) > 0.4)
    for pts in ([(0.6, 8.0), (2.4, 2.6), (6.6, 0.6), (11.0, 2.4), (10.4, 7.6), (5.6, 10.0)],):
        for p in (pts, mirror(pts, 16.0)):
            f.add(poly_xy(p), Z.STONE_BROWN, bevel=2.2, profile="round", pattern=tex)
    f.add((GY >= 19.0) & (GY <= 21.4) & h.inner(1), Z.LEATHER_BROWN, bevel=0.8)
    f.add(disc(16.0, 20.2, 1.8), GRANITE, bevel=1.8)
    for x, y in ((9.0, 13.0), (22.0, 14.0), (13.0, 25.0), (20.0, 24.6)):
        f.add(disc(x, y, 1.2), Z.STONE_BROWN, bevel=1.2)
    return h.render()


def ashlord_mantle():
    h = Hybrid(20127)
    gaps = np.zeros((N, N), bool)
    for x in np.arange(3.0, 30.0, 4.4):
        gaps |= P((x, 31.0), (x + 2.2, 25.4), (x + 4.4, 31.0))
    h.erase(gaps & (GY > 24.0))
    f = h.front
    f.glow(flame_tongues(30.4, 2.0, 30.0, 7, 7.0, 1.7, jitter=0.8) & (GY > 22.0) & ~gaps, (255, 230, 120), (230, 70, 20))
    for pts in ([(4.6, 6.4), (0.6, 0.6), (7.6, 4.2)], [(27.4, 6.4), (31.4, 0.6), (24.4, 4.2)]):
        f.add(poly_xy(pts), Z.OBSIDIAN, bevel=0.9, profile="ridge")
    f.add(disc(16.0, 9.6, 1.6), Z.RUBY, bevel=1.6)
    for x, y in ((6, 18), (25, 14), (12, 22), (21, 20), (9, 12)):
        f.dot(x, y, (255, 180, 60))
    return h.render()


def tiled_breastplate():
    h = Hybrid(20145)
    f = h.front
    chest = h.inner(2) & P((8.6, 9.6), (23.4, 9.6), (24.0, 23.0), (16.0, 29.0), (8.0, 23.0))
    cols = [(56, 200, 200), (230, 244, 240), (30, 96, 170)]
    for j in range(7):
        for i in range(6):
            x0, y0 = 8.0 + i * 2.7, 9.6 + j * 2.7
            cell = (GX >= x0 + 0.45) & (GX < x0 + 2.7) & (GY >= y0 + 0.45) & (GY < y0 + 2.7) & chest
            if cell.any():
                f.glow(cell, cols[(i + j) % 3])
    f.glow(chest & ((((GX - 8.0) % 2.7) < 0.45) | (((GY - 9.6) % 2.7) < 0.45)), (20, 48, 60))
    f.add(disc(16.0, 15.0, 2.8), Z.GOLD, bevel=2.8, height=1.2)
    f.add(disc(16.0, 15.0, 1.2), Z.SAPPHIRE, bevel=1.2)
    for pts in ([(0.4, 9.0), (4.6, 2.0), (6.2, 8.0)], [(31.6, 9.0), (27.4, 2.0), (25.8, 8.0)]):
        f.add(poly_xy(pts), Z.GOLD, bevel=0.9, profile="ridge")
    return h.render()


def quarryguard_armor():
    h = Hybrid(20146)
    f = h.front
    tex = 1 - 0.16 * ((np.sin(GX * 2.7 + GY * 1.3) * np.sin(GY * 2.9 - GX * 1.1)) > 0.4)
    for cx in (4.8, 27.2):
        f.add(disc(cx, 6.0, 5.2) | P((cx - 3.6, 3.0), (cx, -0.4), (cx + 3.6, 3.0)), GRANITE, bevel=3.0, profile="round",
              pattern=tex)
    f.glow(polyline([(16.0, 12.0), (16.0, 25.0)], 0.5) | P((16.0, 14.6), (18.4, 17.6), (16.0, 20.6), (13.6, 17.6)) &
           ~P((16.0, 16.0), (17.0, 17.6), (16.0, 19.2), (15.0, 17.6)), (150, 240, 255), (40, 140, 200))
    return h.render()


def obsidian_regalia():
    h = Hybrid(20147)
    b = h.back
    shards = [[(3.0, 9.0), (3.4, 0.2), (7.2, 8.0)], [(6.4, 8.4), (9.4, 1.4), (11.0, 8.6)],
              [(29.0, 9.0), (28.6, 0.2), (24.8, 8.0)], [(25.6, 8.4), (22.6, 1.4), (21.0, 8.6)]]
    for s in shards:
        b.add(poly_xy(s), Z.NIGHTGLASS, bevel=1.2, profile="ridge")
    f = h.front
    f.add(P((16.0, 11.6), (19.0, 15.6), (16.0, 19.6), (13.0, 15.6)), Z.AMETHYST, bevel=2.2, profile="ridge")
    f.glow(ring(16.0, 15.6, 5.0, 0.35) & h.inner(2), (210, 160, 255))
    sparkle(f, 15, 13)
    return h.render()


# ================================================================== PIERNAS Y BOTAS

def basalt_greaves():
    h = Hybrid(20104)
    f = h.front
    for pts in ([(4.2, 12.6), (0.2, 15.0), (4.2, 17.6)], [(26.6, 12.6), (31.6, 15.0), (26.6, 17.6)]):
        f.add(poly_xy(pts), Z.DARK_STEEL, bevel=0.9, profile="ridge")
    for xs in ((8.2, 7.0, 9.2, 8.0), (22.4, 23.6, 21.6, 22.8)):
        pts = [(xs[0], 7.0), (xs[1], 12.0), (xs[2], 19.0), (xs[3], 27.0)]
        glowline(f, pts, 0.5, (255, 214, 110), (210, 110, 30), clip=h.inner(1))
    f.add((GY >= 1.8) & (GY <= 4.6) & (GX >= 4.0) & (GX <= 27.0) & h.alpha4, Z.GOLD, bevel=0.9)
    f.add(P((15.4, 1.6), (17.6, 3.2), (15.4, 4.8), (13.2, 3.2)), Z.RUBY, bevel=0.9, profile="ridge")
    return h.render()


def marcher_leggings():
    h = Hybrid(20116)
    f = h.front
    f.add((GY >= 2.0) & (GY <= 4.8) & h.alpha4, Z.LEATHER_BROWN, bevel=0.8)
    f.add(P((14.0, 1.6), (18.0, 1.6), (18.0, 5.2), (14.0, 5.2)), Z.GOLD, bevel=0.7)
    for cx in (9.2, 22.4):
        f.add(P((cx - 2.6, 14.0), (cx, 12.4), (cx + 2.6, 14.0), (cx + 2.0, 17.6), (cx, 19.0), (cx - 2.0, 17.6)),
              Z.IRON, bevel=1.4, profile="ridge")
        f.add(P((cx - 2.2, 22.0), (cx + 2.2, 22.0), (cx + 1.8, 28.0), (cx - 1.8, 28.0)), Z.IRON, bevel=1.0,
              profile="ridge")
        f.add(disc(cx, 15.4, 0.8), Z.GOLD, bevel=0.8)
    return h.render()


def cordovan_leggings():
    h = Hybrid(20117)
    f = h.front
    f.add((GY >= 3.0) & (GY <= 5.4) & h.alpha4, Z.DARK_WOOD, bevel=0.8)
    f.add(P((15.0, 2.4), (19.0, 2.4), (19.0, 6.0), (15.0, 6.0)), Z.GOLD, bevel=0.7)
    lace = np.zeros((N, N), bool)
    for cx in (10.6, 22.6):
        for y in (8.0, 12.0, 16.0):
            lace |= polyline([(cx - 1.8, y), (cx + 1.8, y + 3.4)], 0.32) | polyline([(cx + 1.8, y), (cx - 1.8, y + 3.4)], 0.32)
    h.paint.glow(lace & h.inner(1), (240, 200, 110))
    for pts in ([(4.4, 30.6), (5.4, 25.4), (15.4, 25.4), (16.4, 30.6)], [(17.0, 30.6), (18.0, 25.4), (28.0, 25.4),
                                                                         (29.4, 30.6)]):
        f.add(poly_xy(pts), Mat([(30, 6, 10), (70, 16, 22), (118, 32, 40), (164, 62, 66), (206, 110, 104)], 0.3, 16),
              bevel=1.0)
    return h.render()


def kilnfire_leggings():
    h = Hybrid(20148)
    f = h.front
    for x0, x1 in ((5.0, 16.0), (16.0, 28.0)):
        f.glow(flame_tongues(30.6, x0, x1, 3, 9.0, 2.0, jitter=0.9), (255, 236, 140), (220, 60, 16))
    for cx in (10.4, 21.6):
        f.add(disc(cx, 14.0, 2.6), Z.OBSIDIAN, bevel=1.4)
        f.glow(disc(cx, 14.0, 1.2), (255, 200, 80), (230, 90, 20))
    f.add((GY >= 1.0) & (GY <= 3.6) & h.alpha4, Z.IRON, bevel=0.8)
    return h.render()


def wayfarer_boots():
    h = Hybrid(20129)
    b = h.back
    lw = [(6.0, 11.0), (0.6, 3.6), (2.2, 7.8), (0.2, 8.6), (2.2, 11.4), (0.2, 12.6), (2.8, 14.6), (6.0, 15.6)]
    b.add(poly_xy(lw), Z.IVORY, bevel=1.0, profile="ridge")
    b.add(poly_xy(mirror(lw, 15.6)), Z.IVORY, bevel=1.0, profile="ridge")
    f = h.front
    for x0, x1 in ((5.2, 13.6), (17.6, 26.0)):
        f.add(P((x0, 5.0), (x1, 5.0), (x1 + 0.4, 8.2), (x0 - 0.4, 8.2)), Z.LEATHER_BROWN, bevel=0.8)
        f.add(disc((x0 + x1) / 2, 6.6, 1.1), Z.GOLD, bevel=1.1)
    return h.render()


# ================================================================== tabla

ITEMS: dict[int, tuple[str, object, str]] = {
    20133: ("lifewell_rune", rune_lifewell, "Piedra en gota, corazón brillante con cruz."),
    20134: ("emberstorm_rune", rune_emberstorm, "Piedra ancha ámbar, tres llamas."),
    20135: ("shattercall_rune", rune_shattercall, "Piedra astillada gris acero, estallido de seis puntas y grietas."),
    20136: ("arcflash_rune", rune_arcflash, "Piedra alta amarilla, rayo."),
    20140: ("flamecoil_rune", rune_flamecoil, "Piedra redonda magenta, espiral de fuego."),
    20141: ("mireveil_rune", rune_mireveil, "Piedra ancha oliva, burbujas de pantano y ola."),
    20142: ("stonelock_rune", rune_stonelock, "Losa parda, candado de hierro."),
    20143: ("venomthread_rune", rune_venomthread, "Piedra en rombo verde agua, víbora con ojos rojos."),
    20273: ("crimson_cage_rune", rune_crimson_cage, "Losa carmesí, jaula de barrotes."),
    20369: ("frost_mine_rune", rune_frost_mine, "Piedra redonda helada, copo de nieve."),
    20124: ("azure_sunstone", lambda: sunstone(Z.ICE, Z.SAPPHIRE, False, (255, 255, 255)), "Gema octogonal con ocho rayos de sol en zafiro (antes: yellow gem azul)."),
    20125: ("verdant_sunstone", lambda: sunstone(Z.EMERALD, LEAF, True, (240, 255, 220)), "Gema octogonal con ocho rayos en forma de hoja (antes: yellow gem verde)."),
    20106: ("hollow_orb", hollow_orb, "Orbe de vidrio oscuro con vórtice vacío, grieta y garras de hueso sobre base de madera."),
    20107: ("venomqueen_heart", venomqueen_heart, "Colgante en forma de corazón de veneno con cabeza de víbora de ojos rojos."),
    20108: ("bonepriest_phylactery", bonepriest_phylactery, "Colgante de calavera con ojos violetas y cuernos de amatista."),
    20144: ("relic_of_ulm", relic_of_ulm, "Alas de marfil detrás del travesaño, orbe de jade en el lazo y halo."),
    20101: ("quarry_ward", quarry_ward, "Silueta facetada (losa tallada), banda de hierro con remaches, umbo de arenisca con grieta ámbar."),
    20128: ("ironhide_bulwark", ironhide_bulwark, "Cuatro púas de acero salientes, anillo de remaches y umbo con estrella."),
    20149: ("mosaic_shield", mosaic_shield, "Campo de azulejos (turquesa/blanco/cobalto/oro), rombo dorado con zafiro, cuatro puntas de oro."),
    20150: ("bloodreaver_aegis", bloodreaver_aegis, "Alas de murciélago, rubí central, colmillos y gotas de sangre."),
    20151: ("sunforge_shield", sunforge_shield, "Sol: disco más chico con doce rayos dorados alrededor y núcleo encendido."),
    20153: ("frostwarden_aegis", frostwarden_aegis, "Esquirlas de hielo a los lados y arriba, copo de nieve brillante."),
    20102: ("morlen_crest", morlen_crest, "Alas plateadas a los costados, cresta de jade y gema en la frente."),
    20152: ("fox_machina_helmet", fox_machina_helmet, "Orejas de zorro con interior naranja y respiraderos con luz verde."),
    20103: ("ashlar_plate", ashlar_plate, "Hombreras de bloque de arenisca, juntas de sillar en el pecho y gema ámbar."),
    20109: ("rubbleguard_mail", rubbleguard_mail, "Hombreras de roca, cinturón con piedra, piedras incrustadas y borde inferior en zigzag."),
    20127: ("ashlord_mantle", ashlord_mantle, "Ruedo en lenguas de fuego que brillan, púas de obsidiana en los hombros, broche de rubí y brasas."),
    20145: ("tiled_breastplate", tiled_breastplate, "Pecho de azulejos, medallón de oro con zafiro, púas de oro en las hombreras."),
    20146: ("quarryguard_armor", quarryguard_armor, "Hombreras de granito con punta y runa cian brillante en el pecho."),
    20147: ("obsidian_regalia", obsidian_regalia, "Cristales de obsidiana saliendo de los hombros y núcleo de amatista con anillo de luz."),
    20104: ("basalt_greaves", basalt_greaves, "Púas en las rodillas, vetas de lava dorada, cinturón de oro con rubí."),
    20116: ("marcher_leggings", marcher_leggings, "Rodilleras y canilleras de acero, cinturón de cuero con hebilla de oro."),
    20117: ("cordovan_leggings", cordovan_leggings, "Cinturón con hebilla, cordones dorados cruzados y puños anchos."),
    20148: ("kilnfire_leggings", kilnfire_leggings, "Llamas que suben desde abajo, rodilleras de obsidiana con brasa, cinturón de hierro."),
    20129: ("wayfarer_boots", wayfarer_boots, "Alas de marfil a los costados, puños doblados con hebilla de oro."),
}

# PNG que instala add_custom_items.py
CUSTOM_PNG = {20273: "crimson_cage_rune.png", 20369: "frost_mine_rune.png"}

_CACHE: dict[int, list[Image.Image]] = {}


def frames(sid: int) -> list[Image.Image]:
    if sid not in _CACHE:
        fn = ITEMS[sid][1]
        _CACHE[sid] = [fn()]  # type: ignore[operator]
    return _CACHE[sid]


def render(sid: int) -> Image.Image:
    return frames(sid)[0]


def strip_png(sid: int) -> Image.Image:
    fs = frames(sid)
    out = Image.new("RGBA", (32, 32 * len(fs)))
    for k, f in enumerate(fs):
        out.paste(f, (0, 32 * k))
    return out


# ------------------------------------------------------------------ hojas de comparación
def sheet(sid: int, names: dict[int, str], scale: int = 8) -> Image.Image:
    base = Image.open(IMG / "base" / f"{sid}.png").convert("RGBA")
    old = Image.open(IMG / "old" / f"{sid}.png").convert("RGBA")
    new = strip_png(sid)
    nf = new.height // 32
    cw = 32 * scale + 24
    sh = Image.new("RGBA", (cw * 3 + 20, 32 * scale * nf + 70 + 50), (52, 60, 66, 255))
    d = ImageDraw.Draw(sh)
    for col, (title, im) in enumerate((("original 7.6", base), ("version vieja (recolor)", old), ("version nueva", new))):
        for k in range(nf):
            fr = im.crop((0, 32 * min(k, im.height // 32 - 1), 32, 32 * min(k, im.height // 32 - 1) + 32))
            sh.alpha_composite(fr.resize((32 * scale, 32 * scale), Image.NEAREST), (10 + col * cw, 36 + 32 * scale * k))
        d.text((10 + col * cw, 12), title, fill=(255, 255, 255, 255))
        # tamaño real sobre un piso
        y = 36 + 32 * scale * nf + 10
        d.rectangle([10 + col * cw, y, 10 + col * cw + 31, y + 31], fill=(96, 120, 70, 255))
        sh.alpha_composite(im.crop((0, 0, 32, 32)), (10 + col * cw, y))
        d.rectangle([60 + col * cw, y, 60 + col * cw + 31, y + 31], fill=(70, 66, 60, 255))
        sh.alpha_composite(im.crop((0, 0, 32, 32)), (60 + col * cw, y))
    d.text((120, 36 + 32 * scale * nf + 22), f"{sid} {names.get(sid, ITEMS[sid][0])}", fill=(255, 230, 150, 255))
    return sh


def overview(names: dict[int, str]) -> Image.Image:
    sids = list(ITEMS)
    cols, cw, ch, s = 6, 236, 104, 2
    rows = (len(sids) + cols - 1) // cols
    sh = Image.new("RGBA", (cols * cw, rows * ch), (52, 60, 66, 255))
    d = ImageDraw.Draw(sh)
    for i, sid in enumerate(sids):
        x, y = (i % cols) * cw, (i // cols) * ch
        old = Image.open(IMG / "old" / f"{sid}.png").convert("RGBA").crop((0, 0, 32, 32))
        sh.alpha_composite(old.resize((64, 64), Image.NEAREST), (x + 6, y + 6))
        d.text((x + 74, y + 30), "->", fill=(255, 255, 255, 255))
        sh.alpha_composite(render(sid).resize((64 * s // 2 * 2 // 2 * 1, 64), Image.NEAREST) if False else
                           render(sid).resize((64, 64), Image.NEAREST), (x + 96, y + 6))
        sh.alpha_composite(render(sid), (x + 166, y + 22))
        d.text((x + 6, y + 76), f"{sid} {names.get(sid, '')[:26]}", fill=(255, 255, 255, 255))
    return sh


# ------------------------------------------------------------------ aplicar al cliente
def apply(things: Path, only: list[int] | None = None) -> None:
    dat_path, spr_path = things / "Tibia.dat", things / "Tibia.spr"
    entries, _tail = B.DatReader(dat_path.read_bytes()).read_item_entries()
    spr = B.SprReader(spr_path.read_bytes())
    by_cid = {e.client_id: e for e in entries}
    owners: dict[int, int] = {}
    for e in entries:
        for s in e.sprite_ids:
            owners[s] = owners.get(s, 0) + 1
    otb = Z.otb_index(Z.ZAGAN_OTB)
    records: list[bytes | None] = [None] + [spr.sprite_raw(i) for i in range(1, spr.sprite_count + 1)]
    for sid in only or list(ITEMS):
        cid = otb[sid]["cid"]
        e = by_cid[cid]
        fs = frames(sid)
        if len(e.sprite_ids) != len(fs):
            raise SystemExit(f"{sid}: el .dat tiene {len(e.sprite_ids)} sprites y el dibujo {len(fs)}")
        for spr_id, img in zip(e.sprite_ids, fs):
            if owners.get(spr_id, 0) != 1 or spr_id <= 0:
                raise SystemExit(f"{sid}: el sprite {spr_id} lo comparten {owners.get(spr_id)} ítems; no se toca")
            records[spr_id] = B.encode_sprite_record(img)
        print(f"{sid} cid {cid} {otb[sid]['name']!r}: sprites {e.sprite_ids}")
        if sid in CUSTOM_PNG:
            strip_png(sid).save(SPRITES / CUSTOM_PNG[sid])
    spr_path.write_bytes(B.write_spr(signature=spr.signature, sprite_records=records))
    print(f"sprites reemplazados en el lugar; total sin cambios: {spr.sprite_count}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheets", type=Path, help="carpeta para las hojas por ítem y la general")
    ap.add_argument("--png-dir", type=Path)
    ap.add_argument("--only", type=int, nargs="*")
    ap.add_argument("--apply", type=Path, metavar="DIR_THINGS")
    a = ap.parse_args()
    names = {sid: v["name"] for sid, v in Z.otb_index(Z.ZAGAN_OTB).items()}
    sids = a.only or list(ITEMS)
    if a.sheets:
        a.sheets.mkdir(parents=True, exist_ok=True)
        for sid in sids:
            sheet(sid, names).save(a.sheets / f"{sid}_{ITEMS[sid][0]}.png")
        overview(names).save(a.sheets / "00_todos.png")
        print(f"{len(sids)} hojas en {a.sheets}")
    if a.png_dir:
        a.png_dir.mkdir(parents=True, exist_ok=True)
        for sid in sids:
            strip_png(sid).save(a.png_dir / f"{sid}.png")
    if a.apply:
        apply(a.apply, a.only)
    if not (a.sheets or a.png_dir or a.apply):
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
