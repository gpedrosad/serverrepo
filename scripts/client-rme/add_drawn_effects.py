#!/usr/bin/env python3
"""Efectos mágicos NUEVOS dibujados de cero (no recoloreados) para el cliente 7.6.

A diferencia de add_recolor_effects.py, acá la animación se dibuja cuadro por cuadro con numpy
(supermuestreo ×8 y bajada a 32×32 con alfa duro, que es lo que admite el .spr).

Pack "gran" (va después de "power"; lo usa exori gran):
  NM_ME_WHIRL_SLASH  35  tajo en medialuna que gira: filo de acero blanco, cuerpo de acero y estela
                         carmesí. Repetido en cada casilla del área se ve como un remolino de cuchillas.

Pack "spells" (va después de "gran"; un efecto por cada hechizo nuevo de nov 2026):
  NM_ME_ARROW_VOLLEY      36  exori con gran: tres flechas doradas que cruzan la casilla
  NM_ME_RALLY_RING        37  exeta sio: anillo dorado con chevrones que llaman al centro
  NM_ME_CLEANSE_SWIRL     38  exana res: burbujas menta que suben y revientan en chispas
  NM_ME_CHAIN_ARC         39  exori vis con: arcos eléctricos entrecortados
  NM_ME_SEED_BURST        40  exura tera: semilla que germina en un brote con dos hojas
  NM_ME_DETONATION_RING   41  exevo vis tera: destello violeta que se vuelve onda expansiva
  NM_ME_STANCE_GUARD      42  utito tera: arcos de acero que cierran un anillo con destellos
  NM_ME_BLOOD_SPIRAL      43  utamo mort: gotas carmesí que espiralan a una estrella de maná

Uso:
  python3.11 scripts/client-rme/add_drawn_effects.py --pack spells --preview /tmp/spells.png  # vista previa
  python3.11 scripts/client-rme/add_drawn_effects.py --pack spells devtools/rme/rme-client-760

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

_GYm, _GXm = np.mgrid[0:N, 0:N]
GX, GY = _GXm / SS, _GYm / SS   # coordenadas en píxeles de juego (0..32)


def _mix(a, b, t):
    t = np.clip(t, 0, 1)[..., None]
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


def _mix1(a, b, t):
    """_mix para un t escalar: devuelve una tupla de colores, no un grid."""
    t = min(1.0, max(0.0, float(t)))
    return tuple(float(x) * (1 - t) + float(y) * t for x, y in zip(a, b))


def _band(dist, half):
    """1 en el centro de la banda, 0 a `half` de distancia (borde suave)."""
    return np.clip(1 - np.abs(dist) / half, 0, 1)


def _angdist(ang, center):
    """Diferencia angular firmada (-180..180)."""
    return (ang - center + 180) % 360 - 180


def _spark(col, alpha, x, y, color):
    """Prende un píxel de juego entero (bloque SSxSS del supersampleado)."""
    xs, ys = int(round(x)) * SS, int(round(y)) * SS
    if 0 <= xs < N - SS + 1 and 0 <= ys < N - SS + 1:
        col[ys:ys + SS, xs:xs + SS] = color
        alpha[ys:ys + SS, xs:xs + SS] = 1.0


def _seg_dist(gx, gy, ax, ay, bx, by):
    """Distancia de cada punto del grid al segmento AB (px de juego)."""
    abx, aby = bx - ax, by - ay
    L2 = abx * abx + aby * aby or 1e-9
    t = np.clip(((gx - ax) * abx + (gy - ay) * aby) / L2, 0, 1)
    dx, dy = gx - (ax + abx * t), gy - (ay + aby * t)
    return np.hypot(dx, dy)


def _finalize(k, col, alpha, outline=(1, 6), outline_rgb=(26, 22, 34)):
    """Baja el cuadro supersampleado a 32x32 con alfa duro y contorno oscuro opcional."""
    a32 = alpha.reshape(32, SS, 32, SS).mean(axis=(1, 3))
    c32 = (col * alpha[..., None]).reshape(32, SS, 32, SS, 3).sum(axis=(1, 3)) / np.maximum(
        alpha.reshape(32, SS, 32, SS).sum(axis=(1, 3)), 1e-6)[..., None]
    solid = a32 >= 0.42
    if outline is not None:
        grow = np.zeros_like(solid)
        for oy, ox in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            grow |= np.roll(np.roll(solid, oy, 0), ox, 1)
        omask = grow & ~solid & (outline[0] <= k <= outline[1])
    else:
        omask = np.zeros_like(solid)
    px = []
    for y in range(32):
        for x in range(32):
            if solid[y, x]:
                c = np.clip(c32[y, x], 34, 255).astype(int)       # nada casi negro: algunos builders lo borran
                px.append((int(c[0]), int(c[1]), int(c[2]), 255))
            elif omask[y, x]:
                px.append((*outline_rgb, 255))
            else:
                px.append((0, 0, 0, 0))
    return px


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
# Pack "spells" (nov 2026): un efecto dibujado de cero por cada hechizo nuevo.
# Ver docs/gameplay/CLIENT_EFFECTS.md.
# ---------------------------------------------------------------------------

def arrow_volley_frames():
    """NM_ME_ARROW_VOLLEY: tres flechas doradas cruzan la casilla de oeste a este."""
    SHAFT = (176, 128, 48)
    GOLD = (255, 204, 62)
    TIP = (248, 251, 255)
    FLET = (206, 52, 44)
    TRAIL = (255, 226, 140)
    frames = []
    lanes = ((9.5, 0.0, 4.0), (16.0, 0.07, 7.2), (22.5, 0.14, 10.4))
    for k in range(7):
        t = (k + 0.2) / 7.2
        col = np.zeros((N, N, 3))
        alpha = np.zeros((N, N))
        for ly, delay, x0 in lanes:
            tt = t - delay
            if tt <= 0.0 or tt >= 1.25:
                continue
            hx = x0 + tt * 38.0
            tail = hx - 10.0
            dy = np.abs(GY - ly)
            # estela dorada
            tr = (GX >= hx - 17.0) & (GX < tail) & (dy <= 0.5)
            if tr.any():
                fade = np.clip(1 - (tail - GX) / 7.0, 0, 1) * 0.7
                col[tr] = TRAIL
                alpha[tr] = fade[tr]
            # astil (más dorado cerca de la punta)
            sh = (GX >= tail) & (GX <= hx - 0.8) & (dy <= 0.8)
            if sh.any():
                g = np.clip((GX - tail) / 10.0, 0, 1)
                col[sh] = _mix(SHAFT, GOLD, g)[sh]
                alpha[sh] = 1.0
            # plumas carmesí
            fl = (GX >= tail - 0.6) & (GX <= tail + 2.2) & \
                 (dy <= 0.9 + np.clip((tail + 0.8 - GX) * 0.9, 0, 1.2))
            if fl.any():
                col[fl] = FLET
                alpha[fl] = 0.95
            # punta de acero
            tipw = np.clip((hx + 2.6 - GX) * 0.85, 0, 1.7)
            tp = (GX >= hx - 0.8) & (GX <= hx + 2.6) & (dy <= tipw)
            if tp.any():
                col[tp] = TIP
                alpha[tp] = 1.0
        frames.append(_finalize(k, col, alpha, outline=(0, 6), outline_rgb=(44, 28, 8)))
    return frames


def rally_ring_frames():
    """NM_ME_RALLY_RING: anillo dorado que se expande con chevrones que llaman al centro."""
    GOLD = (255, 201, 62)
    AMBER = (188, 108, 10)
    WHITE = (255, 250, 232)
    frames = []
    dx, dy = GX - 15.5, GY - 15.5
    r = np.hypot(dx, dy)
    ang = np.degrees(np.arctan2(dy, dx)) % 360
    for k in range(8):
        p = (k + 0.55) / 8
        col = np.zeros((N, N, 3))
        alpha = np.zeros((N, N))
        bright = 1.0 - p * 0.35
        r1 = 3.4 + p * 10.2
        w1 = max(1.8 - p * 0.9, 0.5)
        band = _band(r - r1, w1)
        edge = np.clip((r - (r1 - w1)) / max(2 * w1, 1e-6), 0, 1)
        m = band > 0
        col[m] = _mix(AMBER, GOLD, edge ** 1.4)[m]
        alpha[m] = band[m] * bright
        if k >= 2:                                   # eco del anillo
            band2 = _band(r - (r1 - 2.6), 0.9) * 0.55 * bright
            m2 = band2 > 0.2
            col[m2] = AMBER
            alpha[m2] = band2[m2]
        if 1 <= k <= 5:                              # chevrones que apuntan al centro
            rc = min(r1 * 0.66, 8.5)
            a_chev = max(0.0, 1 - abs(k - 3) / 2.6) * 0.9
            for th in (0, 90, 180, 270):
                vv = r * np.sin(np.radians(_angdist(ang, th)))
                base = rc - 2.4
                tri = (r >= base) & (r <= rc + 0.6) & \
                      (np.abs(vv) <= 2.3 * (r - base) / 3.0 + 0.18)
                if tri.any():
                    col[tri] = GOLD
                    alpha[tri] = a_chev
        if k <= 2:                                   # cuerno central
            m0 = r <= 1.5 + (2 - k) * 0.4
            col[m0] = WHITE
            alpha[m0] = 0.95 - k * 0.2
        if 2 <= k <= 6:
            rng = np.random.default_rng(20 + k)
            for _ in range(2):
                a = rng.uniform(0, 360)
                _spark(col, alpha, 15.5 + math.cos(math.radians(a)) * (r1 + 1.6),
                       15.5 + math.sin(math.radians(a)) * (r1 + 1.6), GOLD)
        frames.append(_finalize(k, col, alpha, outline=(1, 6), outline_rgb=(46, 26, 6)))
    return frames


def cleanse_swirl_frames():
    """NM_ME_CLEANSE_SWIRL: burbujas menta que suben en zigzag y revientan en chispas."""
    MINT = (140, 250, 190)
    PALE = (222, 255, 238)
    WHITE = (255, 255, 255)
    frames = []
    dx, dy = GX - 15.5, GY - 15.5
    r = np.hypot(dx, dy)
    for k in range(8):
        col = np.zeros((N, N, 3))
        alpha = np.zeros((N, N))
        if k <= 3:                                   # anillo suave en los pies
            band = _band(r - (3.2 + k * 0.85), 1.1) * (0.85 - k * 0.18)
            m = band > 0.15
            col[m] = MINT
            alpha[m] = band[m]
        for i in range(5):                           # burbujas
            age = (k - i * 1.15) / 4.6
            if age <= 0 or age >= 1:
                continue
            bx = 16 + 3.4 * math.sin(i * 1.9 + age * 3.4)
            by = 27.5 - age * 20
            br = 2.35 - age * 0.5
            d = np.hypot(GX - bx, GY - by)
            m = d <= br
            if not m.any():
                continue
            fade = math.sin(math.pi * age) ** 0.55
            rim = np.clip(d / br, 0, 1)
            col[m] = _mix(PALE, MINT, rim * 0.9 + 0.05)[m]
            alpha[m] = fade
            _spark(col, alpha, bx - br * 0.35, by - br * 0.4, WHITE)
        if k >= 5:                                   # chispas al reventar
            rng = np.random.default_rng(50 + k)
            for _ in range(3):
                _spark(col, alpha, rng.uniform(10, 22), rng.uniform(5, 13), PALE)
        frames.append(_finalize(k, col, alpha, outline=(0, 5), outline_rgb=(10, 46, 30)))
    return frames


def _bolt_path(rng, ax, ay, bx, by, segs=5, jitter=2.4):
    """Poliólinea quebrada de un rayo: línea AB con desvíos perpendiculares."""
    pts = [(ax, ay)]
    L = math.hypot(bx - ax, by - ay) or 1e-9
    nx, ny = -(by - ay) / L, (bx - ax) / L
    for i in range(1, segs):
        t = i / segs
        j = rng.uniform(-jitter, jitter) * (1 - abs(t - 0.5) * 1.1)
        pts.append((ax + (bx - ax) * t + nx * j, ay + (by - ay) * t + ny * j))
    pts.append((bx, by))
    return pts


def _polyline_dist(pts):
    d = None
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        seg = _seg_dist(GX, GY, ax, ay, bx, by)
        d = seg if d is None else np.minimum(d, seg)
    return d


def chain_arc_frames():
    """NM_ME_CHAIN_ARC: arcos eléctricos que entrecruzan la casilla y se apagan."""
    CORE = (255, 255, 255)
    BLUE = (120, 196, 255)
    GLOW = (56, 118, 235)
    frames = []
    plan = {
        0: [(11, 2, 3, 30, 29, 1.0)],
        1: [(11, 2, 3, 30, 29, 0.85), (12, 16, 16, 29, 6, 0.75)],
        2: [(13, 29, 2, 3, 30, 1.0), (11, 2, 3, 30, 29, 0.5)],
        3: [(13, 29, 2, 3, 30, 0.85), (14, 16, 16, 4, 25, 0.7)],
        4: [(16, 16, 16, 30, 15, 0.85)],                # arco corto que queda centrado
        5: [(17, 16, 16, 28, 13, 0.8)],
        6: [(17, 16, 16, 24, 15, 0.55)],
    }
    for k in range(7):
        col = np.zeros((N, N, 3))
        alpha = np.zeros((N, N))
        for seed, ax, ay, bx, by, b in plan[k]:
            d = _polyline_dist(_bolt_path(np.random.default_rng(seed), ax, ay, bx, by))
            glow = np.clip(1 - d / 2.8, 0, 1) * 0.45 * b
            m = glow > 0.12
            col[m] = GLOW
            alpha[m] = glow[m]
            rim = _band(d, 1.3) * b
            m = rim > 0.2
            col[m] = BLUE
            alpha[m] = rim[m]
            core = _band(d, 0.7) * b
            m = core > 0.25
            col[m] = CORE
            alpha[m] = core[m]
        if 1 <= k <= 6:                              # chispas cerca del centro
            rng = np.random.default_rng(70 + k)
            for _ in range(2 + k % 3):
                a = rng.uniform(0, 360)
                rr = rng.uniform(3, 8)
                _spark(col, alpha, 15.5 + math.cos(math.radians(a)) * rr,
                       15.5 + math.sin(math.radians(a)) * rr, CORE)
        frames.append(_finalize(k, col, alpha, outline=None))
    return frames


def seed_burst_frames():
    """NM_ME_SEED_BURST: una semilla dorada germina en un brote con dos hojas."""
    SEED = (232, 186, 60)
    SEED_D = (150, 102, 16)
    STEM = (74, 176, 66)
    LEAF_D = (38, 128, 44)
    LEAF = (118, 226, 108)
    VEIN = (206, 255, 208)
    WHITE = (255, 255, 245)
    frames = []
    for k in range(8):
        col = np.zeros((N, N, 3))
        alpha = np.zeros((N, N))
        d = np.hypot(GX - 16, GY - 20.5)
        top_y = 20.5
        if k <= 5:                                   # semilla
            seed_r = 2.2 if k >= 1 else 1.9
            fade = 1.0 if k <= 3 else 1.0 - (k - 3) * 0.3
            m = d <= seed_r
            radial = np.clip(d / seed_r, 0, 1)
            col[m] = _mix(WHITE if k <= 1 else SEED, SEED_D, radial)[m]
            alpha[m] = 0.95 * fade
        if k >= 2:                                   # brote y hojas
            p = (k - 1) / 6.0
            top_y = 20.5 - p * 12.5
            m = (np.abs(GX - 16) <= 0.75) & (GY <= 20.5) & (GY >= top_y)
            col[m] = STEM
            alpha[m] = 0.95
            for sgn in (-1, 1):
                L = 1.2 + p * 4.6
                W = 0.55 + p * 1.25
                ux, uy = sgn * 0.72, -0.7
                nL = math.hypot(ux, uy)
                ux, uy = ux / nL, uy / nL
                relx, rely = GX - 16, GY - top_y
                u = relx * ux + rely * uy
                v = -relx * uy + rely * ux
                mleaf = (u >= -0.3) & (u <= L) & \
                        (np.abs(v) <= W * np.sin(np.pi * np.clip(u / L, 0, 1)) ** 0.75 + 0.12)
                if mleaf.any():
                    g = np.clip(u / L, 0, 1)
                    col[mleaf] = _mix(LEAF_D, LEAF, g)[mleaf]
                    alpha[mleaf] = 0.92
                    vein = mleaf & (np.abs(v) <= 0.32)
                    col[vein] = VEIN
        if k >= 4:                                   # motas de vida que suben
            for i, (mx, phase) in enumerate(((13, 0.0), (19, 1.7), (16, 3.1))):
                a = (k - 4 - i * 0.8) / 3.4
                if 0 < a < 1:
                    yy = top_y - 1 - a * 7
                    xx = mx + math.sin(phase + a * 2.5) * 1.2
                    _spark(col, alpha, xx, yy, WHITE if i == 0 else VEIN)
        if k >= 6:                                   # anillo de vida en la base
            band = _band(d - (3.4 + (k - 6) * 1.5), 0.9) * (0.55 if k == 6 else 0.35)
            m = band > 0.15
            col[m] = LEAF
            alpha[m] = band[m]
        frames.append(_finalize(k, col, alpha, outline=(1, 6), outline_rgb=(16, 52, 18)))
    return frames


def detonation_ring_frames():
    """NM_ME_DETONATION_RING: destello violeta que se vuelve una onda expansiva."""
    VIOLET = (152, 96, 255)
    MAGENTA = (255, 96, 228)
    WHITE = (255, 255, 255)
    frames = []
    dx, dy = GX - 15.5, GY - 15.5
    r = np.hypot(dx, dy)
    for k in range(8):
        col = np.zeros((N, N, 3))
        alpha = np.zeros((N, N))
        if k == 0:
            m = r <= 4.8
            radial = np.clip(r / 4.8, 0, 1)
            col[m] = _mix(WHITE, VIOLET, radial ** 1.6)[m]
            alpha[m] = 1.0
        else:
            p = k / 7
            r1 = 4.6 + p * 9.2
            w1 = max(1.9 - p * 0.7, 0.7)
            bright = 1.0 - p * 0.35
            band = _band(r - r1, w1) * bright
            edge = np.clip((r - (r1 - w1)) / max(2 * w1, 1e-6), 0, 1)
            c = _mix(VIOLET, MAGENTA, edge ** 1.5)
            if k <= 2:                               # borde interior blanco al principio
                inner = np.clip((r1 + w1 - r) / max(2 * w1, 1e-6), 0, 1)
                c = _mix(WHITE, c, np.clip(0.35 + inner * 2.2, 0, 1))
            m = band > 0.12
            col[m] = c[m]
            alpha[m] = band[m]
            if k >= 2:                               # eco de la onda
                band2 = _band(r - (r1 - 2.7), 0.8) * 0.5 * bright
                m2 = band2 > 0.15
                col[m2] = VIOLET
                alpha[m2] = band2[m2]
            if k <= 3:                               # rescoldo central
                m0 = r <= 1.6
                col[m0] = WHITE if k <= 1 else VIOLET
                alpha[m0] = 0.75 - k * 0.2
            if 2 <= k <= 6:                          # esquirlas violetas
                rng = np.random.default_rng(90 + k)
                for _ in range(4):
                    a = rng.uniform(0, 360)
                    rr = r1 + rng.uniform(1.2, 3.2)
                    _spark(col, alpha, 15.5 + math.cos(math.radians(a)) * rr,
                           15.5 + math.sin(math.radians(a)) * rr, VIOLET)
        frames.append(_finalize(k, col, alpha, outline=(1, 5), outline_rgb=(40, 14, 66)))
    return frames


def stance_guard_frames():
    """NM_ME_STANCE_GUARD: arcos de acero que orbitan y se cierran en un anillo con destellos."""
    STEEL = (150, 172, 198)
    STEEL_HI = (236, 246, 255)
    STEEL_D = (84, 102, 128)
    SPARK = (255, 224, 96)
    frames = []
    dx, dy = GX - 15.5, GY - 15.5
    r = np.hypot(dx, dy)
    ang = np.degrees(np.arctan2(dy, dx)) % 360
    for k in range(8):
        col = np.zeros((N, N, 3))
        alpha = np.zeros((N, N))
        rr = 8.0
        if k <= 4:                                   # tres arcos que orbitan y crecen
            p = k / 4
            rr = 9.6 - p * 1.6
            band = _band(r - rr, 1.5)
            span = 84 + p * 34
            for i in range(3):
                c0 = (i * 120 + k * 17) % 360
                d = np.abs(_angdist(ang, c0))
                m = (band > 0.1) & (d <= span / 2)
                if m.any():
                    edge = np.clip((r - (rr - 1.5)) / 3.0, 0, 1)
                    bright = (0.8 + 0.2 * p) * (1.0 if k < 4 else 0.4)
                    cc = _mix(STEEL_D, STEEL_HI, edge ** 1.3) * bright
                    col[m] = cc[m]
                    alpha[m] = band[m] * bright
        if k >= 4:                                   # el anillo se cierra
            p2 = (k - 4) / 3.0
            rr = 7.9 - p2 * 0.3
            band = _band(r - rr, 1.45)
            bright = 1.0 if k <= 5 else (0.85 if k == 6 else 0.6)
            edge = np.clip((r - (rr - 1.45)) / 2.9, 0, 1)
            cc = _mix(STEEL, STEEL_HI, edge ** 1.6) * bright
            m = band > 0.1
            col[m] = cc[m]
            alpha[m] = band[m] * bright
        if 4 <= k <= 6:                              # destellos de acero
            for th in (0, 90, 180, 270):
                a = math.radians(th)
                _spark(col, alpha, 15.5 + math.cos(a) * rr, 15.5 + math.sin(a) * rr, STEEL_HI)
        if 5 <= k <= 7:                              # chispas doradas al cerrar
            rng = np.random.default_rng(120 + k)
            for _ in range(2):
                _spark(col, alpha, rng.uniform(11, 20), rng.uniform(6, 12), SPARK)
        frames.append(_finalize(k, col, alpha, outline=(0, 6), outline_rgb=(30, 38, 52)))
    return frames


def blood_spiral_frames():
    """NM_ME_BLOOD_SPIRAL: gotas carmesí que espiralan hacia una estrella de maná violeta."""
    CRIMSON = (208, 30, 54)
    BLOOD_D = (112, 8, 22)
    VIOLET = (158, 98, 255)
    WHITE = (255, 250, 255)
    frames = []
    dx, dy = GX - 15.5, GY - 15.5
    r = np.hypot(dx, dy)
    for k in range(9):
        col = np.zeros((N, N, 3))
        alpha = np.zeros((N, N))
        if k <= 6:                                   # círculo del ritual
            band = _band(r - 13.2, 0.95) * (0.8 - k * 0.09)
            m = band > 0.14
            col[m] = BLOOD_D
            alpha[m] = band[m]
            for th in (45, 135, 225, 315):
                a = math.radians(th)
                m2 = np.hypot(GX - (15.5 + math.cos(a) * 13.2),
                              GY - (15.5 + math.sin(a) * 13.2)) <= 1.1
                col[m2] = CRIMSON
                alpha[m2] = max(0.0, 0.9 - k * 0.12)
        for i in range(5):                           # gotas que espiralan hacia adentro
            age = (k - i * 1.05) / 6.8
            if age <= 0 or age >= 1:
                continue
            th = i * 72 + age * 380
            R = 12.3 - age * 10.3
            hx = 15.5 + math.cos(math.radians(th)) * R
            hy = 15.5 + math.sin(math.radians(th)) * R
            d = np.hypot(GX - hx, GY - hy)
            head = d <= 1.6
            if head.any():
                col[head] = _mix1(CRIMSON, VIOLET, age)
                alpha[head] = 0.95
            tail = (d > 1.6) & (d <= 3.4) & (r > R)
            if tail.any():
                col[tail] = _mix1(BLOOD_D, CRIMSON, age)
                alpha[tail] = np.clip((3.4 - d) / 1.8, 0, 1)[tail] * 0.6
        if k >= 5:                                   # estrella de maná
            g = min((k - 4) / 4.0, 1.0) * 6.0
            adm = np.abs(dx) / max(g, 1e-6)
            adyv = np.abs(dy) / max(g, 1e-6)
            star = ((np.abs(dy) <= 0.6 * (1 - adm) + 0.15) & (np.abs(dx) <= g)) | \
                    ((np.abs(dx) <= 0.6 * (1 - adyv) + 0.15) & (np.abs(dy) <= g))
            if star.any():
                radial = np.clip(np.hypot(dx, dy) / max(g, 1e-6), 0, 1)
                col[star] = _mix(WHITE, VIOLET, radial ** 1.2)[star]
                alpha[star] = 0.55 + 0.4 * min((k - 4) / 3, 1)
            if k == 8:                               # destello final
                band = _band(r - 6.2, 0.8) * 0.5
                m = band > 0.12
                col[m] = VIOLET
                alpha[m] = band[m]
        frames.append(_finalize(k, col, alpha, outline=(1, 7), outline_rgb=(40, 8, 24)))
    return frames


# base = (efectos, proyectiles) del .dat antes del pack. light = (intensidad, color 6x6x6) o None.
# Cada efecto puede llevar su propia luz como tercer elemento de la tupla; si no, va la del pack.
PACKS = {
    "gran": {"base": (35, 18), "light": (2, 5 * 36 + 1 * 6 + 1),
             "effects": [("NM_ME_WHIRL_SLASH", whirl_slash_frames)]},
    # Un efecto por hechizo nuevo (nov 2026). La luz es (intensidad, color 6x6x6).
    "spells": {"base": (36, 18),
               "effects": [
                   ("NM_ME_ARROW_VOLLEY", arrow_volley_frames, (2, 5 * 36 + 3 * 6 + 0)),      # 36 dorado
                   ("NM_ME_RALLY_RING", rally_ring_frames, (2, 5 * 36 + 2 * 6 + 0)),           # 37 ambar
                   ("NM_ME_CLEANSE_SWIRL", cleanse_swirl_frames, (2, 2 * 36 + 5 * 6 + 3)),    # 38 menta
                   ("NM_ME_CHAIN_ARC", chain_arc_frames, (2, 1 * 36 + 3 * 6 + 5)),             # 39 electrico
                   ("NM_ME_SEED_BURST", seed_burst_frames, (2, 2 * 36 + 4 * 6 + 1)),          # 40 vida
                   ("NM_ME_DETONATION_RING", detonation_ring_frames, (2, 3 * 36 + 1 * 6 + 5)), # 41 violeta
                   ("NM_ME_STANCE_GUARD", stance_guard_frames, (1, 5 * 36 + 5 * 6 + 5)),      # 42 acero
                   ("NM_ME_BLOOD_SPIRAL", blood_spiral_frames, (2, 5 * 36 + 0 * 6 + 2)),      # 43 carmesi
               ]},
}


def entry_prefix(frames: int, light) -> bytes:
    attrs = b"" if light is None else bytes([0x15]) + struct.pack("<HH", *light)
    return attrs + bytes([0xFF, 1, 1, 1, 1, 1, 1, frames])


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
        print(f"El pack '{a.pack}' ya está aplicado (efectos={counts[2]}).")
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
