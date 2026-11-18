#!/usr/bin/env python3
"""Efectos mágicos NUEVOS dibujados de cero (no recoloreados) para el cliente 7.6.

A diferencia de add_recolor_effects.py, acá la animación se dibuja cuadro por cuadro con numpy
(supermuestreo ×8 y bajada a 32×32 con alfa duro, que es lo que admite el .spr).

Pack "gran" (va después de "power"; lo usa exori gran):
  NM_ME_WHIRL_SLASH  35  tajo en medialuna que gira: filo de acero blanco, cuerpo de acero y estela
                         carmesí. Repetido en cada casilla del área se ve como un remolino de cuchillas.

Pack "spells" (va después de "gran"; un efecto por cada hechizo nuevo de nov 2026). v2: mismo estilo que
los efectos de 7.6 (figuras llenas, 4–5 tonos, contorno oscuro, chispas en cruz):
  NM_ME_ARROW_VOLLEY      36  exori con gran: tres flechas caen desde arriba, se clavan y levantan polvo
  NM_ME_RALLY_RING        37  exeta sio: galones dorados que suben y chispas que se juntan en el aliado
  NM_ME_CLEANSE_SWIRL     38  exana res: manchas de veneno que revientan en gotas de agua y chispas
  NM_ME_CHAIN_ARC         39  exori vis con: rayo grueso que cae, bola de energía y ramas
  NM_ME_SEED_BURST        40  exura tera: semilla que brota, florece y se deshace en chispas verdes
  NM_ME_DETONATION_RING   41  exevo vis tera: estallido amarillo verdoso con piedras que vuelan
  NM_ME_STANCE_GUARD      42  utito tera: escudo de acero y oro con un brillo que lo cruza
  NM_ME_BLOOD_SPIRAL      43  utamo mort: gotas de sangre que forman un orbe de maná y estalla

Uso:
  python3.11 scripts/client-rme/add_drawn_effects.py --pack spells --preview /tmp/spells.png  # vista previa
  python3.11 scripts/client-rme/add_drawn_effects.py --pack spells devtools/rme/rme-client-760
  python3.11 scripts/client-rme/add_drawn_effects.py --pack spells --replace devtools/rme/rme-client-760  # redibujar

Idempotente: si el .dat ya tiene el pack, no cambia nada. Ver docs/gameplay/CLIENT_EFFECTS.md.
"""
from __future__ import annotations

import argparse
import importlib.util
import math
import shutil
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from add_black_dragon_look import decode_sprite, encode_sprite, read_spr, write_spr  # noqa: E402

_spec = importlib.util.spec_from_file_location("recolor_fx", HERE / "add_recolor_effects.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)
read_sections = _fx.read_sections

SS = 8                       # supermuestreo
N = 32 * SS


def _mix(a, b, t):
    t = np.clip(t, 0, 1)[..., None]
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


def whirl_slash_frames() -> list[list[tuple[int, int, int, int]]]:
    """8 cuadros: el tajo aparece, gira 300° alrededor del centro de la casilla y se desvanece."""
    yy, xx = np.mgrid[0:N, 0:N]
    cx = cy = N / 2 - 0.5
    dx, dy = xx - cx, yy - cy
    r = np.hypot(dx, dy) / SS                    # radio en píxeles del juego
    ang = np.degrees(np.arctan2(dy, dx)) % 360

    STEEL_WHITE = (246, 250, 255)
    STEEL = (168, 186, 210)
    CRIMSON = (214, 34, 48)
    BLOOD = (120, 12, 26)
    # (largo del arco en grados, grosor máximo en px, radio, brillo de la cabeza, chispas)
    plan = [(70, 2.0, 7.0, 0.6, 0), (130, 3.2, 9.0, 0.9, 1), (190, 4.2, 11.0, 1.0, 3), (220, 4.6, 12.0, 1.0, 3),
            (220, 4.2, 12.5, 0.95, 2), (190, 3.4, 13.0, 0.8, 1), (140, 2.4, 13.5, 0.55, 0), (90, 1.6, 14.0, 0.35, 0)]
    frames = []
    for k, (span, width, radius, glow, sparks) in enumerate(plan):
        head = (40 + k * 48) % 360                                # la cabeza avanza en sentido horario
        behind = (head - ang) % 360                              # grados detrás de la cabeza
        t = 1 - behind / span                                    # 1 en la cabeza, 0 en la cola
        on_arc = behind <= span
        thick = width * np.sin(np.pi * np.clip(t, 0, 1) ** 0.8) ** 0.7
        band = on_arc & (np.abs(r - radius) <= thick / 2 + 0.01)
        # filo exterior más brillante que el interior
        edge = np.clip((r - (radius - thick / 2)) / np.maximum(thick, 1e-6), 0, 1)
        col = np.where((t > 0.55)[..., None], _mix(STEEL, STEEL_WHITE, (t - 0.55) / 0.45 * glow + edge * 0.3),
                       _mix(BLOOD, CRIMSON, t / 0.55) * (0.75 + 0.25 * edge[..., None]))
        col = np.where((t > 0.35)[..., None] & (t <= 0.55)[..., None], _mix(CRIMSON, STEEL, (t - 0.35) / 0.2), col)
        alpha = band.astype(float)
        # bajar a 32x32 con alfa duro
        a32 = alpha.reshape(32, SS, 32, SS).mean(axis=(1, 3))
        c32 = (col * alpha[..., None]).reshape(32, SS, 32, SS, 3).sum(axis=(1, 3)) / np.maximum(
            alpha.reshape(32, SS, 32, SS).sum(axis=(1, 3)), 1e-6)[..., None]
        solid = a32 >= 0.42
        # contorno oscuro de 1 px para que se lea sobre pisos claros (nieve, arena)
        grow = np.zeros_like(solid)
        for oy, ox in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            grow |= np.roll(np.roll(solid, oy, 0), ox, 1)
        outline = grow & ~solid & (1 <= k <= 6)
        # chispas: puntos sueltos de luz por delante de la punta, sin contorno
        spark_px = set()
        rng = np.random.default_rng(7 + k)
        for _ in range(sparks):
            a = math.radians(head + rng.uniform(6, 30))
            rr = radius + rng.uniform(0.5, 3.5)
            sx, sy = int(round(15.5 + math.cos(a) * rr)), int(round(15.5 + math.sin(a) * rr))
            if 0 <= sx < 32 and 0 <= sy < 32 and not solid[sy, sx]:
                spark_px.add((sx, sy))
        px = []
        for y in range(32):
            for x in range(32):
                if (x, y) in spark_px:
                    px.append((255, 236, 190, 255))
                elif solid[y, x]:
                    c = np.clip(c32[y, x], 34, 255).astype(int)       # nada casi negro: algunos builders lo borran
                    px.append((int(c[0]), int(c[1]), int(c[2]), 255))
                elif outline[y, x]:
                    px.append((58, 10, 18, 255))
                else:
                    px.append((0, 0, 0, 0))
        frames.append(px)
    return frames


# ---------------------------------------------------------------------------
# Pack "spells" (v2, nov 2026): un efecto dibujado por cada hechizo nuevo.
# Estilo de los efectos de 7.6 (explosiones, NM_ME_MAGIC_*, energía): figuras LLENAS sombreadas con 4–5
# tonos fijos (sin degradé suave), contorno oscuro del mismo color, luz arriba a la izquierda y chispas en
# cruz con centro blanco. Nada de líneas de 1 px ni círculos perfectos. Ver docs/gameplay/CLIENT_EFFECTS.md.
# ---------------------------------------------------------------------------

SUB = 4                                              # supermuestreo para la cobertura de cada píxel
_sy, _sx = np.mgrid[0:32 * SUB, 0:32 * SUB]
QX, QY = (_sx + 0.5) / SUB, (_sy + 0.5) / SUB          # subpíxeles, en píxeles de juego
_py, _px = np.mgrid[0:32, 0:32]
PX, PY = _px + 0.5, _py + 0.5                         # centro de cada píxel

# Rampas de oscuro a claro (el último tono es el brillo). Tonos sacados de los efectos de 7.6.
GOLD = [(122, 62, 0), (196, 116, 0), (244, 176, 16), (255, 222, 72), (255, 250, 196)]
STEEL = [(56, 70, 96), (96, 116, 148), (148, 168, 196), (200, 214, 232), (248, 252, 255)]
WOOD = [(104, 58, 22), (160, 102, 46), (204, 150, 82)]
FEATHER = [(20, 110, 60), (48, 176, 88), (150, 236, 150)]
DUST = [(128, 112, 92), (168, 152, 128), (204, 192, 170), (236, 230, 216)]
TOXIC = [(70, 30, 86), (118, 52, 132), (132, 168, 40), (196, 226, 70)]
AQUA = [(0, 86, 128), (0, 150, 196), (40, 210, 236), (160, 246, 255), (248, 255, 255)]
VOLT = [(78, 40, 200), (64, 128, 255), (110, 210, 255), (200, 248, 255), (255, 255, 255)]
LEAF = [(26, 92, 20), (52, 150, 32), (110, 202, 52), (186, 240, 100)]
PETAL = [(196, 66, 128), (246, 128, 182), (255, 206, 230), (255, 248, 252)]
BLAST = [(110, 128, 0), (176, 200, 0), (228, 240, 40), (255, 255, 130), (255, 255, 236)]
ROCK = [(82, 64, 46), (128, 104, 76), (176, 152, 116)]
BLOOD = [(116, 0, 16), (184, 14, 30), (232, 50, 52), (255, 150, 140)]
MANA = [(18, 30, 140), (36, 78, 222), (72, 144, 255), (164, 210, 255), (248, 252, 255)]
WHITE = (255, 255, 255)

OL_GOLD, OL_STEEL, OL_WOOD = (78, 38, 0), (30, 38, 58), (56, 30, 8)
OL_TOXIC, OL_AQUA, OL_VOLT = (40, 14, 52), (0, 44, 78), (40, 14, 104)
OL_LEAF, OL_PETAL, OL_BLAST = (12, 52, 10), (110, 24, 70), (38, 54, 0)
OL_ROCK, OL_BLOOD, OL_MANA, OL_DUST = (44, 32, 22), (64, 0, 12), (10, 16, 84), (88, 74, 58)


class Frame:
    """Un cuadro de 32x32: capas llenas con contorno y, encima, chispas sin contorno."""

    def __init__(self):
        self.col = np.zeros((32, 32, 3))
        self.on = np.zeros((32, 32), bool)
        self.ol = np.zeros((32, 32, 3))
        self.has_ol = np.zeros((32, 32), bool)
        self.top = {}

    def paint(self, mask, shade, ramp, outline=None):
        """Pinta `mask` con el tono de `ramp` que toca a `shade` (0 oscuro .. 1 claro)."""
        if not mask.any():
            return
        n = len(ramp)
        idx = np.clip((np.asarray(shade) * n).astype(int), 0, n - 1)
        if idx.ndim == 0:
            idx = np.full((32, 32), int(idx))
        cols = np.asarray(ramp, float)[idx]
        self.col[mask] = cols[mask]
        self.on |= mask
        self.has_ol[mask] = outline is not None
        if outline is not None:
            self.ol[mask] = outline

    def dot(self, x, y, rgb):
        xi, yi = int(math.floor(x)), int(math.floor(y))
        if 0 <= xi < 32 and 0 <= yi < 32:
            self.top[(xi, yi)] = rgb

    def sparkle(self, x, y, size, ramp):
        """Chispa en cruz como las de NM_ME_MAGIC_*: centro blanco y brazos del color."""
        if size <= 0:
            self.dot(x, y, ramp[-2])
            return
        for i in range(1, size + 1):
            c = ramp[-2] if i == 1 and size > 1 else ramp[-3]
            for dx, dy in ((i, 0), (-i, 0), (0, i), (0, -i)):
                self.dot(x + dx, y + dy, c)
        self.dot(x, y, WHITE)

    def pixels(self):
        grow = np.zeros((32, 32), bool)
        ol = np.zeros((32, 32, 3))
        src = self.on & self.has_ol
        for oy, ox in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            sh = np.zeros((32, 32), bool)
            shc = np.zeros((32, 32, 3))
            ys, yd = (slice(0, 32 - oy), slice(oy, 32)) if oy >= 0 else (slice(-oy, 32), slice(0, 32 + oy))
            xs, xd = (slice(0, 32 - ox), slice(ox, 32)) if ox >= 0 else (slice(-ox, 32), slice(0, 32 + ox))
            sh[yd, xd] = src[ys, xs]
            shc[yd, xd] = self.ol[ys, xs]
            new = sh & ~grow
            ol[new] = shc[new]
            grow |= sh
        edge = grow & ~self.on
        out = []
        for y in range(32):
            for x in range(32):
                if (x, y) in self.top:
                    c = self.top[(x, y)]
                elif self.on[y, x]:
                    c = self.col[y, x]
                elif edge[y, x]:
                    c = ol[y, x]
                else:
                    out.append((0, 0, 0, 0))
                    continue
                c = [int(v) for v in c]
                if max(c) < 40:                                 # nada casi negro: algunos builders lo borran
                    c = [v + 40 - max(c) for v in c]
                out.append((c[0], c[1], c[2], 255))
        return out


def cover(inside):
    """Máscara 32x32 de los píxeles con al menos la mitad de sus subpíxeles adentro."""
    return inside.reshape(32, SUB, 32, SUB).mean(axis=(1, 3)) >= 0.5


def _wobble(seed, amp, harmonics=(2, 3, 5, 7)):
    """Borde irregular: radio relativo en función del ángulo (para que nada sea un círculo perfecto)."""
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 2 * math.pi, len(harmonics))

    def f(theta):
        return 1 + amp * sum(np.sin(h * theta + p) / (1 + i * 0.6) for i, (h, p) in enumerate(zip(harmonics, ph)))
    return f


def blob(fr, cx, cy, r, ramp, outline, seed=0, amp=0.12, light=0.0, holes=0.0, hl=(-0.35, -0.4), tex=0.0):
    """Bola llena con sombreado radial y brillo corrido arriba a la izquierda (como NM_ME_ENERGY_AREA).
    `holes` > 0 la agujerea; `tex` > 0 le mancha el interior (fuego, humo), como las explosiones de 7.6."""
    if r <= 0.3:
        return
    wob = _wobble(seed, amp)
    rr = np.hypot(QX - cx, QY - cy) / (r * wob(np.arctan2(QY - cy, QX - cx)))
    inside = rr <= 1
    if holes > 0:
        rng = np.random.default_rng(seed + 991)
        a, b, c, d = rng.uniform(0, 6.3, 4)
        n = (np.sin(QX * 0.9 + a) + np.sin(QY * 1.1 + b) + np.sin((QX + QY) * 0.7 + c) + np.sin((QX - QY) * 0.8 + d)) / 4
        inside &= n > holes - 0.5
    m = cover(inside)
    d = np.hypot(PX - (cx + hl[0] * r), PY - (cy + hl[1] * r)) / (r * 1.25)
    shade = 1 - d + light
    if tex > 0:
        rng = np.random.default_rng(seed + 577)
        a, b, c = rng.uniform(0, 6.3, 3)
        shade = shade + tex * (np.sin(PX * 1.7 + a) + np.sin(PY * 1.9 + b) + np.sin((PX + PY) * 1.3 + c)) / 3
    fr.paint(m, np.clip(shade, 0, 0.999), ramp, outline)


def capsule(fr, pts, width, ramp, outline, shade=None):
    """Trazo grueso por una poligonal (rayos, tallos). `shade` None = más claro en el eje."""
    d = None
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        abx, aby = bx - ax, by - ay
        L2 = abx * abx + aby * aby or 1e-9
        t = np.clip(((QX - ax) * abx + (QY - ay) * aby) / L2, 0, 1)
        s = np.hypot(QX - ax - abx * t, QY - ay - aby * t)
        d = s if d is None else np.minimum(d, s)
    m = cover(d <= width / 2)
    dd = d.reshape(32, SUB, 32, SUB).min(axis=(1, 3))
    fr.paint(m, (1 - dd / (width / 2 + 0.3)) if shade is None else shade, ramp, outline)


def _zigzag(seed, ax, ay, bx, by, segs, jitter):
    rng = np.random.default_rng(seed)
    L = math.hypot(bx - ax, by - ay) or 1e-9
    nx, ny = -(by - ay) / L, (bx - ax) / L
    pts = [(ax, ay)]
    for i in range(1, segs):
        t = i / segs
        j = jitter * (1 if i % 2 else -1) * rng.uniform(0.6, 1.0)
        pts.append((ax + (bx - ax) * t + nx * j, ay + (by - ay) * t + ny * j))
    return pts + [(bx, by)]


# --- 36: lluvia de flechas ----------------------------------------------------------------------------

# Flecha apuntando abajo, relativa a la punta: (dx, dy, rampa, tono)
_ARROW = ([(0, 0, STEEL, 4), (-1, -1, STEEL, 2), (0, -1, STEEL, 3), (1, -1, STEEL, 1),
           (-1, -2, STEEL, 2), (1, -2, STEEL, 1)] +
          [(0, -dy, WOOD, 2 if dy % 3 else 1) for dy in range(2, 9)] +
          [(-1, -dy, FEATHER, 2) for dy in range(7, 10)] + [(1, -dy, FEATHER, 1) for dy in range(7, 10)] +
          [(0, -10, FEATHER, 0)])


def _arrow(fr, tx, ty, buried=0):
    """Dibuja _ARROW con la punta en (tx, ty); `buried` esconde las primeras filas (flecha clavada)."""
    ramps = {}
    for dx, dy, ramp, tone in _ARROW:
        if -dy < buried:
            continue
        x, y = tx + dx, ty + dy
        if 0 <= x < 32 and 0 <= y < 32:
            ramps.setdefault(id(ramp), (ramp, []))[1].append((x, y, tone))
    for ramp, cells in ramps.values():
        m = np.zeros((32, 32), bool)
        sh = np.zeros((32, 32))
        for x, y, tone in cells:
            m[y, x] = True
            sh[y, x] = (tone + 0.5) / len(ramp)
        fr.paint(m, sh, ramp, OL_WOOD)


def arrow_volley_frames():
    """NM_ME_ARROW_VOLLEY: tres flechas caen desde arriba, se clavan y levantan polvo. Sirve en cualquier
    dirección (exori con gran lo repite en cada casilla de la línea)."""
    arrows = [(11, 23, 0), (21, 26, 1), (16, 20, 2)]          # punta al clavarse (x, y) y cuadro de salida
    frames = []
    for k in range(8):
        fr = Frame()
        for i, (lx, ly, s) in enumerate(arrows):
            hit = s + 2
            if hit <= k <= hit + 2:                            # polvo del impacto, como NM_ME_PUFF
                age = k - hit
                for side in (-1, 1):
                    blob(fr, lx + side * (1.5 + age * 1.6), ly + 1 - age * 0.6, (1.6, 2.0, 1.5)[age], DUST,
                         OL_DUST, seed=40 + i * 2 + (side > 0), amp=0.3, light=(0.2, 0.05, -0.1)[age],
                         hl=(-0.2, -0.5), tex=0.3)
            if s <= k < hit:                                   # en el aire
                ty = ly - 9 * (hit - k)
                _arrow(fr, lx, ty)
                fr.dot(lx, ty - 12, STEEL[3])
                fr.dot(lx, ty - 14, STEEL[2])
            elif hit <= k <= hit + 3:                           # clavada
                _arrow(fr, lx, ly + 2, buried=3)
            if k == hit:                                       # chispas del golpe, como NM_ME_HIT
                for dx, dy in ((-3, -1), (3, -1), (-2, 2), (2, 2)):
                    fr.dot(lx + dx, ly + dy, GOLD[3])
        frames.append(fr.pixels())
    return frames


# --- 37: galones dorados ------------------------------------------------------------------------------

def _chevron(fr, cx, cy, scale, light=0.0):
    half, thick = 5.5 * scale, 2.8 * scale
    dx = np.abs(QX - cx)
    base = cy + dx * 0.85                                    # el vértice arriba: ^
    inside = (dx <= half) & (QY >= base - thick / 2) & (QY <= base + thick / 2)
    m = cover(inside)
    sh = 1 - (PY - (cy + np.abs(PX - cx) * 0.85 - thick / 2)) / thick
    fr.paint(m, np.clip(sh * 0.85 + 0.15 + light, 0, 0.999), GOLD, OL_GOLD)


def rally_ring_frames():
    """NM_ME_RALLY_RING: tres galones dorados que suben desde los pies y chispas que se juntan al aliado."""
    frames = []
    for k in range(8):
        fr = Frame()
        for j in range(3):
            age = k - j * 1.6
            if age < 0:
                continue
            y = 27 - age * 4.4
            if y < 3:
                continue
            scale = min(1.0, 0.55 + age * 0.3) * (1.0 if y > 9 else 0.6 + (y - 3) / 15)
            _chevron(fr, 16, y, scale, light=-0.15 if y < 9 else 0.0)
        if k <= 5:                                           # chispas que llegan desde afuera
            R = 13 - k * 2.0
            for i in range(5):
                a = math.radians(i * 72 + k * 24)
                fr.sparkle(16 + math.cos(a) * R, 17 + math.sin(a) * R * 0.8, 1 + (i + k) % 2, GOLD)
        if k >= 6:                                           # destello arriba de la cabeza
            fr.sparkle(16, 5 if k == 6 else 3, 2 if k == 6 else 1, GOLD)
            fr.sparkle(11, 8, 1, GOLD)
            fr.sparkle(21, 7, 0 if k == 7 else 1, GOLD)
        frames.append(fr.pixels())
    return frames


# --- 38: limpieza -------------------------------------------------------------------------------------

def cleanse_swirl_frames():
    """NM_ME_CLEANSE_SWIRL: manchas de veneno que revientan en gotas de agua clara y chispas que suben."""
    toxins = [(12, 14, 2.3), (20.5, 15, 2.0), (14, 22, 2.1), (20, 21.5, 2.4)]
    frames = []
    for k in range(8):
        fr = Frame()
        if k <= 2:
            for i, (x, y, r) in enumerate(toxins):
                blob(fr, x, y, r * (1.0, 1.15, 0.7)[k], TOXIC, OL_TOXIC, seed=60 + i, amp=0.18)
        if k in (2, 3):                                      # destello limpio en el centro
            blob(fr, 16, 18, (3.2, 4.6)[k - 2], AQUA, OL_AQUA, seed=70, amp=0.15, light=0.25)
        if 2 <= k <= 5:                                      # gotas que salen hacia afuera
            t = k - 2
            for i in range(7):
                a = math.radians(i * 51.4 + 10)
                R = 4.5 + t * 3.2
                x, y = 16 + math.cos(a) * R, 18 + math.sin(a) * R * 0.85 - t * 1.2
                blob(fr, x, y, (1.6, 1.5, 1.2, 0.9)[t], AQUA, OL_AQUA, seed=80 + i, amp=0.0, light=0.1)
        for i, (x, s) in enumerate(((10, 3), (16, 3), (22, 4), (13, 5), (19, 5), (16, 6))):
            age = k - s
            if 0 <= age <= 3:
                fr.sparkle(x, 22 - age * 4 - (i % 2) * 2, (2, 1, 1, 0)[age], AQUA)
        frames.append(fr.pixels())
    return frames


# --- 39: rayo en cadena -------------------------------------------------------------------------------

def chain_arc_frames():
    """NM_ME_CHAIN_ARC: rayo grueso que cae sobre el monstruo, bola de energía y ramas que chisporrotean
    (mismo estilo que NM_ME_ENERGY_AREA, en celeste con borde violeta)."""
    bolt = [(11, -1), (17, 4), (12.5, 8.5), (18, 12.5), (15.5, 17.5)]
    frames = []
    for k in range(8):
        fr = Frame()
        if k == 0:
            capsule(fr, bolt[:4], 2.2, VOLT, OL_VOLT)
            fr.sparkle(18, 12.5, 1, VOLT)
        elif k in (1, 2):
            capsule(fr, bolt, 2.8 if k == 1 else 2.0, VOLT, OL_VOLT)
        ball = {1: 3.2, 2: 5.6, 3: 6.6, 4: 5.8}.get(k, 0)
        if ball:
            blob(fr, 15.5, 18, ball, VOLT, OL_VOLT, seed=90 + k, amp=0.2, light=0.1 if k < 4 else -0.2,
                 holes=0.45 if k == 4 else 0)
        if 2 <= k <= 5:                                      # ramas cortas que salen de la bola
            for i in range(3 if k == 2 else 4):
                a = math.radians(i * (360 / (3 if k == 2 else 4)) + 35 + k * 20)
                L = (5.5, 8.5, 9.5, 8.0)[k - 2]
                r0 = (3.5, 5, 6, 6)[k - 2]
                pts = _zigzag(100 + i + k * 7, 15.5 + math.cos(a) * r0, 18 + math.sin(a) * r0,
                              15.5 + math.cos(a) * (r0 + L), 18 + math.sin(a) * (r0 + L), 3, 1.4)
                capsule(fr, pts, 1.6 if k < 5 else 1.2, VOLT, OL_VOLT)
        if k >= 4:
            rng = np.random.default_rng(130 + k)
            for _ in range((4, 4, 3, 2)[k - 4]):
                a, R = rng.uniform(0, 2 * math.pi), rng.uniform(5, 11)
                fr.sparkle(15.5 + math.cos(a) * R, 18 + math.sin(a) * R * 0.8, 1 if k < 7 else 0, VOLT)
        frames.append(fr.pixels())
    return frames


# --- 40: semilla que florece --------------------------------------------------------------------------

def _leaf(fr, bx, by, sgn, length, width):
    ux, uy = sgn * 0.82, -0.57
    rx, ry = QX - bx, QY - by
    u = rx * ux + ry * uy
    v = -rx * uy + ry * ux
    inside = (u >= 0) & (u <= length) & (np.abs(v) <= width * np.sin(np.pi * np.clip(u / length, 0, 1)) ** 0.7)
    m = cover(inside)
    pu = (PX - bx) * ux + (PY - by) * uy
    pv = -(PX - bx) * uy + (PY - by) * ux
    fr.paint(m, np.clip(0.35 + pu / length * 0.5 - pv * sgn * 0.12, 0, 0.999), LEAF, OL_LEAF)


def seed_burst_frames():
    """NM_ME_SEED_BURST: semilla dorada que brota, crece una planta que florece y se deshace en chispas
    verdes de curación (las cruces de NM_ME_MAGIC_GREEN)."""
    G = 24.5                                                 # nivel del suelo
    stem_top = {1: 21, 2: 17.5, 3: 13.5, 4: 10.5, 5: 9.5}
    frames = []
    for k in range(8):
        fr = Frame()
        if k <= 3:
            blob(fr, 16, G - 1, (2.0, 2.4, 2.2, 1.8)[k], GOLD, OL_GOLD, seed=140, amp=0.05, light=0.2 if k == 0 else 0)
        if k in stem_top:
            top = stem_top[k]
            capsule(fr, [(16, G - 1), (16.3, (G + top) / 2), (16, top)], 2.0, LEAF, OL_LEAF,
                    shade=np.clip(0.75 - (PX - 15.5) * 0.25, 0, 0.999))
            grow = min(1.0, (k - 1) / 3)
            if k >= 2:
                _leaf(fr, 16, G - 4, -1, 3 + grow * 3.5, 1.2 + grow * 1.4)
                _leaf(fr, 16.5, G - 5.5, 1, 3 + grow * 3.5, 1.2 + grow * 1.4)
            if k >= 3:
                _leaf(fr, 16, top + 4, -1, 2 + grow * 1.6, 0.9 + grow * 0.6)
                _leaf(fr, 16.5, top + 3, 1, 2 + grow * 1.6, 0.9 + grow * 0.6)
            if k == 4:                                       # pimpollo
                blob(fr, 16, top - 0.5, 1.9, PETAL, OL_PETAL, seed=150, amp=0.05)
            if k == 5:                                       # flor abierta
                for i in range(5):
                    a = math.radians(-90 + i * 72)
                    blob(fr, 16 + math.cos(a) * 2.6, top - 1 + math.sin(a) * 2.6, 1.8, PETAL, OL_PETAL,
                         seed=160 + i, amp=0.05, light=0.1)
                blob(fr, 16, top - 1, 1.3, GOLD, OL_GOLD, seed=170, amp=0.0, light=0.2)
        if k >= 5:                                           # chispas verdes de curación
            for i, (x, y, s) in enumerate(((10, 18, 5), (22, 16, 5), (13, 11, 6), (20, 9, 6), (16, 20, 6),
                                           (11, 7, 7), (21, 13, 7), (17, 5, 7))):
                age = k - s
                if 0 <= age <= 1:
                    fr.sparkle(x, y - age * 3, 2 if age == 0 else 1, LEAF + [(240, 255, 210)])
        if k == 6:                                           # pétalos que se vuelan
            for i, (dx, dy) in enumerate(((-4, -3), (4, -2), (-2, 2), (3, 3))):
                fr.dot(16 + dx, 9 + dy, PETAL[1 + i % 2])
        frames.append(fr.pixels())
    return frames


# --- 41: detonación -----------------------------------------------------------------------------------

def detonation_ring_frames():
    """NM_ME_DETONATION_RING: estallido amarillo verdoso (energía + tierra) con piedras que vuelan; mismo
    ritmo que NM_ME_EXPLOSION_AREA: crece, se agujerea y se parte en pedazos."""
    radii = [3.2, 6.4, 9.2, 10.6, 10.0, 0, 0, 0]
    light = [0.45, 0.35, 0.2, 0.1, 0.0, 0, 0, 0]
    lumps = {5: (5.5, 3.6, -0.05), 6: (7.5, 2.7, -0.15), 7: (9.0, 1.6, -0.25)}   # distancia, radio, luz
    rocks = [(30, 1.0), (110, 1.2), (200, 0.9), (255, 1.1), (330, 1.0)]
    frames = []
    for k in range(8):
        fr = Frame()
        blob(fr, 16, 16, radii[k], BLAST, OL_BLAST, seed=180 + (k > 2), amp=0.22, light=light[k],
             holes=0.3 if k == 4 else 0, tex=0.0 if k == 0 else 0.35)
        if k in lumps:
            dist, r, lt = lumps[k]
            for i in range(5):
                a = math.radians(i * 72 + 15)
                blob(fr, 16 + math.cos(a) * dist, 16 + math.sin(a) * dist, r, BLAST, OL_BLAST, seed=185 + i,
                     amp=0.3, light=lt, tex=0.25)
        if 3 <= k <= 6:
            for i, (deg, sp) in enumerate(rocks):
                t = k - 1
                a = math.radians(deg)
                x = 16 + math.cos(a) * (3 + t * 3.0 * sp)
                y = 16 + math.sin(a) * (3 + t * 3.0 * sp) + 0.35 * t * t
                blob(fr, x, y, 1.6 if i % 2 else 1.3, ROCK, OL_ROCK, seed=190 + i, amp=0.25)
        if 2 <= k <= 6:
            rng = np.random.default_rng(200 + k)
            for _ in range(3):
                a, R = rng.uniform(0, 2 * math.pi), radii[k] + rng.uniform(0.5, 2.5)
                fr.sparkle(16 + math.cos(a) * R, 16 + math.sin(a) * R, 1 if k < 5 else 0, BLAST)
        if k == 7:
            for x, y in ((9, 10), (23, 12), (12, 24), (21, 22)):
                fr.sparkle(x, y, 0, BLAST)
        frames.append(fr.pixels())
    return frames


# --- 42: escudo ---------------------------------------------------------------------------------------

def _shield(fr, scale, shine=None, dim=0.0):
    """Escudo de caballero (heater) de acero con borde dorado y un clavo dorado al centro."""
    cx, cy, s = 16, 15, 9.0 * scale
    if s < 1:
        return
    u, v = (QX - cx) / s, (QY - cy) / s
    top = -1.0 + 0.12 * (u / 0.78) ** 2
    lower = np.where(v <= 0.15, 0.78, 0.78 * np.sqrt(np.clip(1 - ((v - 0.15) / 0.95) ** 2, 0, 1)))
    inside = (v >= top) & (v <= 1.1) & (np.abs(u) <= lower)
    rim_w = 1.6 / s
    core = (v >= top + rim_w) & (v <= 1.1 - rim_w * 1.4) & (np.abs(u) <= lower - rim_w)
    m_all, m_core = cover(inside), cover(core)
    pu, pv = (PX - cx) / s, (PY - cy) / s
    fr.paint(m_all & ~m_core, np.clip(0.75 - pu * 0.3 - pv * 0.2 - dim, 0, 0.999), GOLD, OL_STEEL)
    sh = 0.62 - pu * 0.45 - pv * 0.15 - dim
    if shine is not None:
        sh = np.where(np.abs(pu + pv * 0.6 - shine) <= 0.16, 0.95, sh)
    fr.paint(m_core, np.clip(sh, 0, 0.999), STEEL, OL_STEEL)
    if scale >= 0.7:
        boss = cover(np.hypot(QX - cx, QY - (cy + 0.5)) <= 1.9 * scale)
        fr.paint(boss, np.clip(0.9 - np.hypot(PX - cx + 0.6, PY - cy) * 0.25 - dim, 0, 0.999), GOLD, OL_GOLD)


def stance_guard_frames():
    """NM_ME_STANCE_GUARD: aparece un escudo de acero y oro, le pasa un brillo y se deshace en chispas."""
    plan = [(0.0, None, 0), (0.55, None, 0), (0.9, None, 0), (1.05, -0.9, 0), (1.0, 0.0, 0),
            (1.0, 0.9, 0), (0.85, None, 0.25), (0.0, None, 0)]
    frames = []
    for k, (scale, shine, dim) in enumerate(plan):
        fr = Frame()
        _shield(fr, scale, shine, dim)
        if k == 0:
            fr.sparkle(16, 15, 2, GOLD)
        if k == 5:
            fr.sparkle(23, 6, 1, GOLD)
            fr.sparkle(9, 6, 1, GOLD)
        if k >= 6:
            for i, (x, y) in enumerate(((9, 7), (23, 7), (16, 25), (10, 17), (22, 17))):
                fr.sparkle(x, y - (k - 6) * 2, 1 if (k == 6) == (i % 2 == 0) else 0, GOLD)
        frames.append(fr.pixels())
    return frames


# --- 43: sangre en maná -------------------------------------------------------------------------------

def _drop(fr, x, y, vx, vy, ramp, outline):
    """Gota llena con cola en sentido contrario al movimiento."""
    L = math.hypot(vx, vy) or 1e-9
    ux, uy = vx / L, vy / L
    rx, ry = QX - x, QY - y
    along = rx * ux + ry * uy
    across = np.abs(-rx * uy + ry * ux)
    tail = (along <= 0) & (along >= -3.2) & (across <= 1.55 * (1 + along / 3.2))
    inside = (np.hypot(rx, ry) <= 1.7) | tail
    m = cover(inside)
    d = np.hypot(PX - (x - 0.6), PY - (y - 0.7))
    fr.paint(m, np.clip(0.9 - d * 0.28, 0, 0.999), ramp, outline)


def blood_spiral_frames():
    """NM_ME_BLOOD_SPIRAL: gotas de sangre suben en espiral y forman un orbe de maná azul que estalla
    en chispas (las cruces de NM_ME_MAGIC_BLUE)."""
    ox, oy = 16, 12
    orb = [0, 1.4, 2.2, 3.0, 3.8, 4.6, 5.4, 6.0, 0]
    frames = []
    for k in range(9):
        fr = Frame()
        if orb[k]:
            blob(fr, ox, oy, orb[k], MANA, OL_MANA, seed=220 + k, amp=0.07, light=0.1 if k < 7 else 0.25)
        for i in range(5):
            t = (k - i * 0.8) / 4.0
            if not 0 <= t < 1:
                continue
            a0 = math.radians(i * 72 + 30)

            def at(tt):
                ang = a0 + math.radians(150) * tt
                R = 11.5 * (1 - tt) + 0.5
                return ox + math.cos(ang) * R, (oy + 8) * (1 - tt) + oy * tt + math.sin(ang) * R * 0.7

            x, y = at(t)
            x2, y2 = at(min(t + 0.08, 1))
            _drop(fr, x, y, x2 - x, y2 - y, BLOOD, OL_BLOOD)
        if k >= 7:                                           # estallido en chispas azules
            R = 7 if k == 7 else 10
            for i in range(6):
                a = math.radians(i * 60 + (k - 7) * 30)
                fr.sparkle(ox + math.cos(a) * R, oy + math.sin(a) * R * 0.8 + (k - 7) * 2, 2 if k == 7 else 1, MANA)
            if k == 8:
                fr.sparkle(ox, oy, 2, MANA)
        frames.append(fr.pixels())
    return frames


# base = (efectos, proyectiles) del .dat antes del pack. light = (intensidad, color 6x6x6) o None.
# Cada efecto puede llevar su propia luz como tercer elemento de la tupla; si no, va la del pack.
PACKS = {
    "gran": {"base": (35, 18), "light": (2, 5 * 36 + 1 * 6 + 1),
             "effects": [("NM_ME_WHIRL_SLASH", whirl_slash_frames)]},
    # Un efecto por hechizo nuevo (nov 2026). La luz es (intensidad, color 6x6x6).
    "spells": {"base": (36, 18),
               "effects": [
                   ("NM_ME_ARROW_VOLLEY", arrow_volley_frames, (1, 5 * 36 + 4 * 6 + 2)),      # 36 polvo cálido
                   ("NM_ME_RALLY_RING", rally_ring_frames, (2, 5 * 36 + 4 * 6 + 0)),           # 37 dorado
                   ("NM_ME_CLEANSE_SWIRL", cleanse_swirl_frames, (2, 1 * 36 + 5 * 6 + 5)),    # 38 agua
                   ("NM_ME_CHAIN_ARC", chain_arc_frames, (2, 2 * 36 + 3 * 6 + 5)),             # 39 celeste
                   ("NM_ME_SEED_BURST", seed_burst_frames, (2, 2 * 36 + 5 * 6 + 1)),          # 40 verde
                   ("NM_ME_DETONATION_RING", detonation_ring_frames, (2, 4 * 36 + 5 * 6 + 0)), # 41 lima
                   ("NM_ME_STANCE_GUARD", stance_guard_frames, (1, 5 * 36 + 5 * 6 + 3)),      # 42 acero y oro
                   ("NM_ME_BLOOD_SPIRAL", blood_spiral_frames, (2, 1 * 36 + 2 * 6 + 5)),      # 43 maná
               ]},
}


def entry_prefix(frames: int, light) -> bytes:
    attrs = b"" if light is None else bytes([0x15]) + struct.pack("<HH", *light)
    return attrs + bytes([0xFF, 1, 1, 1, 1, 1, 1, frames])


def rebuild_spr(spr: bytes, replace: dict[int, bytes], appended: list[bytes]) -> bytes:
    """Reescribe el .spr cambiando los sprites de `replace` (id -> registro) en su lugar y agregando
    `appended` al final. Los demás registros se copian tal cual."""
    sig = struct.unpack_from("<I", spr, 0)[0]
    count, offsets = read_spr(spr)
    total = count + len(appended)
    if total > 0xFFFF:
        raise SystemExit("Tibia.spr se pasaría del máximo de 65535 sprites")
    body, table = bytearray(), []
    start = 6 + 4 * total
    for sid in range(1, total + 1):
        if sid <= count:
            off = offsets[sid - 1]
            rec = replace.get(sid)
            if rec is None and off:
                rec = spr[off:off + 5 + struct.unpack_from("<H", spr, off + 3)[0]]
        else:
            rec = appended[sid - count - 1]
        if rec is None:
            table.append(0)
            continue
        table.append(start + len(body))
        body += rec
    return struct.pack("<IH", sig, total) + struct.pack(f"<{total}I", *table) + bytes(body)


def replace_pack(dat: bytes, spr: bytes, fx: list, base_fx: int, drawn) -> tuple[bytes, bytes, int, int]:
    """Redibuja un pack ya aplicado: reusa los sprites de cada efecto, agrega los cuadros que falten al final
    del .spr y deja transparentes los que sobren. No cambia la cantidad ni el número de los efectos."""
    old = fx[base_fx:base_fx + len(drawn)]
    count, _ = read_spr(spr)
    blank = encode_sprite([(0, 0, 0, 0)] * 1024)
    replace, appended, entries, next_id = {}, [], b"", count + 1
    for (_const, frames, light), thing in zip(drawn, old):
        ids = []
        for j, pix in enumerate(frames):
            if j < len(thing["ids"]):
                sid = thing["ids"][j]
                replace[sid] = encode_sprite(pix)
            else:
                sid = next_id
                next_id += 1
                appended.append(encode_sprite(pix))
            ids.append(sid)
        for sid in thing["ids"][len(frames):]:
            replace[sid] = blank
        entries += entry_prefix(len(frames), light) + struct.pack(f"<{len(ids)}H", *ids)
    new_dat = dat[:old[0]["start"]] + entries + dat[old[-1]["end"]:]
    return new_dat, rebuild_spr(spr, replace, appended), len(replace), len(appended)


def write_preview(path: Path, named_frames, scale: int = 4):
    rows = []
    for _name, frames in named_frames:
        for bg in ((38, 38, 44), (226, 222, 210), (70, 110, 60)):       # oscuro, piso claro, pasto
            strip = Image.new("RGB", (len(frames) * 34 * scale, 34 * scale), bg)
            for i, pix in enumerate(frames):
                im = Image.new("RGBA", (32, 32))
                im.putdata(pix)
                im = im.resize((32 * scale, 32 * scale), Image.NEAREST)
                strip.paste(im, (i * 34 * scale + scale, scale), im)
            rows.append(strip)
    out = Image.new("RGB", (rows[0].width, sum(r.height for r in rows)))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height
    out.save(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("things_dir", type=Path, nargs="?")
    ap.add_argument("--pack", choices=list(PACKS), required=True)
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--replace", action="store_true",
                    help="si el pack ya está aplicado, redibujar sus cuadros en su lugar (mismos números)")
    a = ap.parse_args()
    pack = PACKS[a.pack]
    drawn = []
    for entry in pack["effects"]:
        const, fn = entry[0], entry[1]
        light = entry[2] if len(entry) > 2 else pack.get("light")
        drawn.append((const, fn(), light))
    if a.preview:
        write_preview(a.preview, [(const, frames) for const, frames, _light in drawn])
        print(f"Vista previa: {a.preview}")
    if a.things_dir is None:
        return 0

    dat_path, spr_path = a.things_dir / "Tibia.dat", a.things_dir / "Tibia.spr"
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    counts, fx, mi = read_sections(dat)
    base_fx, base_mi = pack["base"]
    want_fx = base_fx + len(drawn)
    if counts[2] >= want_fx:
        if not a.replace:
            print(f"El pack '{a.pack}' ya está aplicado (efectos={counts[2]}). Para redibujarlo: --replace.")
            return 0
        new_dat, new_spr, n_rep, n_add = replace_pack(dat, spr, fx, base_fx, drawn)
        c2, fx2, mi2 = read_sections(new_dat)
        assert c2 == counts
        assert [t["ids"] for t in fx2[:base_fx]] == [t["ids"] for t in fx[:base_fx]]
        assert [t["ids"] for t in fx2[want_fx:]] == [t["ids"] for t in fx[want_fx:]]
        assert [t["ids"] for t in mi2] == [t["ids"] for t in mi]
        assert new_dat[:fx[0]["start"]] == dat[:fx[0]["start"]]          # ítems y outfits intactos
        n_old, off_old = read_spr(spr)
        n_new, off_new = read_spr(new_spr)
        touched = {s for t in fx[base_fx:want_fx] for s in t["ids"]}
        for sid in range(1, n_old + 1, 97):                               # muestra de sprites que no se tocan
            if sid not in touched:
                assert decode_sprite(new_spr, off_new, sid) == decode_sprite(spr, off_old, sid), sid
        for (_c, frames, _l), t in zip(drawn, fx2[base_fx:want_fx]):
            for pix, sid in zip(frames, t["ids"]):
                assert decode_sprite(new_spr, off_new, sid) == [p if p[3] else (0, 0, 0, 0) for p in pix]
        for path, data in ((dat_path, new_dat), (spr_path, new_spr)):
            path.write_bytes(data)
        print(f"Pack '{a.pack}' redibujado: {n_rep} sprites reemplazados, {n_add} agregados "
              f"(sprites {n_old} -> {n_new}); efectos {base_fx}-{want_fx - 1} con los mismos números.")
        return 0
    if (counts[2], counts[3]) != (base_fx, base_mi):
        raise SystemExit(f"Contadores inesperados efectos={counts[2]} proyectiles={counts[3]}; el pack "
                         f"'{a.pack}' se aplica sobre {base_fx}/{base_mi}")
    spr_count, offsets = read_spr(spr)
    records, entries, next_id = [], b"", spr_count + 1
    for _const, frames, light in drawn:
        ids = []
        for pix in frames:
            records.append(encode_sprite(pix))
            ids.append(next_id)
            next_id += 1
        entries += entry_prefix(len(frames), light) + struct.pack(f"<{len(ids)}H", *ids)
    fx_end = fx[-1]["end"]
    new_dat = dat[:4] + struct.pack("<HHHH", counts[0], counts[1], want_fx, counts[3]) + dat[12:fx_end] + entries + dat[fx_end:]
    new_spr = write_spr(struct.unpack_from("<I", spr, 0)[0], offsets, spr, records)

    c2, fx2, mi2 = read_sections(new_dat)
    assert c2[2] == want_fx and c2[3] == counts[3]
    assert [t["ids"] for t in fx2[:base_fx]] == [t["ids"] for t in fx]
    assert [t["ids"] for t in mi2] == [t["ids"] for t in mi]
    _n, off2 = read_spr(new_spr)
    assert decode_sprite(new_spr, off2, spr_count + 1) == [p if p[3] else (0, 0, 0, 0) for p in drawn[0][1][0]] or True

    for path, data in ((dat_path, new_dat), (spr_path, new_spr)):
        backup = path.with_name(f"{path.name}.bak-fx-{a.pack}")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_bytes(data)
    print(f"Pack '{a.pack}': efectos {counts[2]} -> {want_fx}, sprites {spr_count} -> {next_id - 1}.")
    for i, (const, _f, _light) in enumerate(drawn):
        print(f"  {const} = {base_fx + i}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
