#!/usr/bin/env python3
"""Sprites 32x32 de los items Zagan que tienen uso real en el juego, dibujados por código.

Los sprites originales del pack Zagan (~/Downloads/Zagan+Square) se perdieron con el VPS: no
están en git, ni en el cliente publicado (gpedrosad/clienteretro), ni en la ThinkPad. Este
script los redibuja de cero para los items que tienen lógica, loot o sistema detrás (ver
docs/items-and-map/ZAGAN_TEST_ITEMS.md, sección "Sprites redibujados").

Cómo dibuja: cada pieza (hoja, guarda, mango, gema...) es una máscara a 4x de resolución con un
mapa de altura (bisel, arista, cúpula, cilindro) y un material (rampa de color con cambio de tono
en sombras y luces, brillo especular). Se ilumina desde arriba a la izquierda, se reduce a 32x32
promediando, y se le pone un contorno oscuro selectivo (más claro del lado de la luz) y líneas
de separación entre piezas. Al final van los destellos a mano.

Uso (Pillow + numpy; en esta Mac: python3.11):
  python3.11 scripts/client-rme/draw_zagan_items.py --preview hoja.png     # vista previa
  python3.11 scripts/client-rme/draw_zagan_items.py --png-dir DIR           # un PNG 32x32 por item
  python3.11 scripts/client-rme/draw_zagan_items.py --apply DIR_THINGS      # escribe Tibia.dat/.spr

--apply pone cada sprite en el client id que el item ya tiene en items-zagan-test.otb (el OTB
no se toca) y le copia los flags del .dat de un item vanilla del mismo tipo. Si el item ya
tiene un sprite propio agregado por este script, lo reemplaza en el lugar (no crece el .spr).
"""
from __future__ import annotations

import argparse
import math
import shutil
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build_zagan_test_assets as B  # noqa: E402

ZAGAN_OTB = REPO / "server/YurOTS/ots/data/items/items-zagan-test.otb"
BASE_OTB = REPO / "server/YurOTS/ots/data/items/items.otb"

W = 32          # tamaño del sprite
SS = 4          # supermuestreo
N = W * SS
Color = tuple[int, int, int]
Canvas = dict[tuple[int, int], Color]

_c = (np.arange(N) + 0.5) / SS
GX, GY = np.meshgrid(_c, _c)  # coordenadas del sprite (0..32) de cada submuestra

_L = np.array([-0.55, -0.72, 0.95])
LIGHT = _L / np.linalg.norm(_L)
_H = LIGHT + np.array([0.0, 0.0, 1.0])
HALF = _H / np.linalg.norm(_H)


# ================================================================ geometría

class Frame:
    """Ejes locales: t a lo largo del arma, s de costado (s < 0 = lado de la luz si apunta arriba)."""

    def __init__(self, ox: float, oy: float, dx: float, dy: float) -> None:
        length = math.hypot(dx, dy)
        self.ox, self.oy = ox, oy
        self.dx, self.dy = dx / length, dy / length
        self.nx, self.ny = -self.dy, self.dx
        px, py = GX - ox, GY - oy
        self.t = px * self.dx + py * self.dy
        self.s = px * self.nx + py * self.ny

    def xy(self, t: float, s: float) -> tuple[float, float]:
        return self.ox + t * self.dx + s * self.nx, self.oy + t * self.dy + s * self.ny


def poly_in(pts: list[tuple[float, float]], U: np.ndarray, V: np.ndarray) -> np.ndarray:
    """Punto en polígono (ray casting) sobre arrays de coordenadas."""
    hit = np.zeros(U.shape, bool)
    n = len(pts)
    for i in range(n):
        u1, v1 = pts[i]
        u2, v2 = pts[(i + 1) % n]
        if v1 == v2:
            continue
        cross = (v1 > V) != (v2 > V)
        ux = u1 + (V - v1) * (u2 - u1) / (v2 - v1)
        hit ^= cross & (U < ux)
    return hit


def poly_xy(pts):
    return poly_in(pts, GX, GY)


def poly_ts(fr: Frame, pts, ds: float = 0.0, dt: float = 0.0):
    return poly_in(pts, fr.t - dt, fr.s - ds)


def disc(cx, cy, r, ry=None):
    ry = ry or r
    return ((GX - cx) / r) ** 2 + ((GY - cy) / ry) ** 2 <= 1.0


def capsule(x0, y0, x1, y1, r):
    vx, vy = x1 - x0, y1 - y0
    L2 = vx * vx + vy * vy
    k = np.clip(((GX - x0) * vx + (GY - y0) * vy) / L2, 0, 1)
    return (GX - (x0 + k * vx)) ** 2 + (GY - (y0 + k * vy)) ** 2 <= r * r


def polyline(pts, r):
    m = np.zeros((N, N), bool)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        m |= capsule(x0, y0, x1, y1, r)
    return m


def strip(fr: Frame, t0, t1, width, curve=None):
    """Banda a lo largo de t con ancho width(u) y desplazamiento lateral curve(u)."""
    u = (fr.t - t0) / (t1 - t0)
    uc = np.clip(u, 0, 1)
    w = width(uc)
    c = curve(uc) if curve else 0.0
    return (u >= 0) & (u <= 1) & (np.abs(fr.s - c) <= w)


def erode(m: np.ndarray, diag: bool) -> np.ndarray:
    p = np.pad(m, 1)
    out = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    if diag:
        out &= p[:-2, :-2] & p[:-2, 2:] & p[2:, :-2] & p[2:, 2:]
    return out


def dist(m: np.ndarray, limit: int = 48) -> np.ndarray:
    d = np.zeros(m.shape, float)
    cur = m.copy()
    k = 0
    while cur.any() and k < limit:
        d += cur
        cur = erode(cur, diag=bool(k % 2))
        k += 1
    return d


def blur(a: np.ndarray) -> np.ndarray:
    p = np.pad(a, 1, mode="edge")
    return sum(p[1 + dy:N + 1 + dy, 1 + dx:N + 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9.0


# ================================================================ materiales

@dataclass
class Mat:
    ramp: list[Color]           # de sombra profunda a luz (con cambio de tono)
    spec: float = 0.55          # fuerza del brillo especular
    power: float = 28.0
    spec_color: Color = (255, 255, 255)
    mid: float = 0.5            # tono de una superficie plana
    gain: float = 1.5           # contraste de la iluminación


def ramp_eval(ramp: list[Color], I: np.ndarray) -> np.ndarray:
    arr = np.array(ramp, float)
    stops = np.linspace(0, 1, len(ramp))
    return np.stack([np.interp(I, stops, arr[:, k]) for k in range(3)], -1)


STEEL = Mat([(34, 36, 58), (70, 76, 102), (120, 130, 152), (176, 186, 202), (226, 232, 240), (255, 255, 255)], 0.7, 40)
DARK_STEEL = Mat([(18, 16, 28), (40, 38, 54), (70, 68, 86), (110, 108, 126), (160, 158, 176)], 0.6, 36)
GOLD = Mat([(70, 30, 10), (140, 72, 18), (206, 136, 34), (246, 196, 70), (255, 236, 150), (255, 252, 220)], 0.8, 30, (255, 250, 220))
SILVER = Mat([(40, 40, 64), (96, 100, 130), (160, 166, 190), (214, 220, 236), (250, 252, 255)], 0.8, 36)
WOOD = Mat([(46, 22, 12), (92, 48, 24), (138, 82, 42), (184, 124, 70), (220, 170, 110)], 0.25, 14)
DARK_WOOD = Mat([(28, 14, 10), (58, 30, 20), (92, 52, 32), (130, 80, 50), (170, 118, 80)], 0.25, 14)
LEATHER_RED = Mat([(36, 8, 12), (84, 20, 26), (132, 40, 40), (176, 74, 64), (214, 120, 100)], 0.3, 16)
LEATHER_BROWN = Mat([(30, 14, 10), (70, 38, 22), (112, 66, 38), (152, 100, 62), (196, 146, 100)], 0.3, 16)
BONE = Mat([(62, 46, 52), (118, 98, 90), (176, 160, 130), (222, 210, 176), (248, 242, 220), (255, 255, 246)], 0.35, 18)
IVORY = Mat([(70, 54, 60), (130, 112, 100), (196, 182, 150), (236, 228, 200), (255, 252, 236)], 0.5, 24)
VENOM = Mat([(10, 40, 30), (24, 96, 40), (62, 168, 48), (140, 226, 70), (214, 255, 150)], 0.7, 30, (240, 255, 220))
OBSIDIAN = Mat([(14, 10, 18), (34, 26, 36), (58, 48, 60), (92, 80, 92), (150, 136, 150)], 0.85, 50)
CRIMSON = Mat([(48, 4, 22), (106, 10, 34), (170, 24, 44), (222, 62, 64), (255, 130, 120), (255, 214, 206)], 0.75, 34)
RUBY = Mat([(60, 0, 16), (140, 8, 30), (220, 30, 50), (255, 96, 110), (255, 200, 210)], 1.0, 40)
ICE = Mat([(30, 60, 140), (60, 120, 210), (110, 186, 246), (176, 228, 255), (232, 250, 255), (255, 255, 255)], 0.95, 40)
SAPPHIRE = Mat([(10, 20, 80), (24, 60, 170), (60, 130, 240), (150, 210, 255), (230, 248, 255)], 1.0, 40)
STORM = Mat([(18, 22, 52), (40, 52, 98), (72, 92, 146), (116, 142, 192), (176, 198, 232), (232, 242, 255)], 0.65, 32)
IRON = Mat([(16, 16, 24), (40, 40, 52), (72, 72, 86), (112, 112, 126), (164, 164, 178), (220, 220, 230)], 0.55, 30)
NECRO = Mat([(30, 6, 50), (72, 20, 110), (130, 50, 190), (186, 110, 240), (236, 196, 255)], 0.9, 30)
AMETHYST = Mat([(36, 8, 60), (90, 26, 140), (160, 70, 220), (214, 150, 255), (250, 230, 255)], 1.0, 40)
WINDSTEEL = Mat([(10, 50, 60), (22, 96, 104), (48, 150, 150), (110, 206, 196), (190, 246, 236), (250, 255, 255)], 0.8, 34)
JADE = Mat([(10, 40, 34), (24, 82, 62), (52, 132, 98), (106, 190, 146), (184, 236, 200), (240, 255, 246)], 0.75, 32)
EMERALD = Mat([(0, 40, 20), (10, 100, 50), (40, 180, 90), (140, 240, 170), (230, 255, 240)], 1.0, 40)
MOONSTEEL = Mat([(30, 30, 62), (72, 76, 120), (128, 134, 176), (186, 192, 226), (232, 236, 252), (255, 255, 255)], 0.8, 40)
INDIGO = Mat([(14, 12, 34), (30, 28, 68), (52, 50, 108), (86, 84, 150), (130, 128, 196)], 0.4, 20)
NIGHTGLASS = Mat([(10, 6, 26), (34, 20, 70), (70, 44, 130), (120, 90, 200), (190, 166, 255), (246, 240, 255)], 1.0, 44)
CLOTH_RED = Mat([(30, 4, 12), (78, 10, 24), (138, 22, 34), (190, 44, 40), (230, 90, 60)], 0.12, 10)
CLOTH_FIRE = Mat([(90, 16, 10), (170, 46, 16), (230, 104, 26), (255, 168, 50), (255, 226, 120)], 0.15, 10)
STONE_BLUE = Mat([(10, 16, 46), (24, 40, 96), (40, 70, 150), (76, 112, 196), (140, 170, 230)], 0.45, 24)
STONE_BROWN = Mat([(30, 18, 12), (70, 44, 28), (116, 78, 50), (162, 118, 78), (206, 166, 120)], 0.3, 18)


# ================================================================ lienzo

class Sprite:
    def __init__(self) -> None:
        self.col = np.zeros((N, N, 3))
        self.pid = np.full((N, N), -1)
        self.lines = {}
        self.n = 0
        self.fx: list[tuple[int, int, Color]] = []

    def add(self, mask, mat: Mat, bevel: float = 1.5, profile: str = "round", height: float = 1.0,
            hmap=None, pattern=None, mix=None, lines: bool = True):
        """Agrega una pieza. bevel en unidades del sprite. profile: round | ridge | flat."""
        mask = mask.astype(bool)
        if not mask.any():
            return
        if hmap is None:
            b = max(bevel * SS, 1.0)
            x = np.clip(dist(mask) / b, 0, 1)
            if profile == "round":
                x = np.sqrt(np.clip(1 - (1 - x) ** 2, 0, 1))
            elif profile == "flat":
                x = np.minimum(x * 1.0, 1.0)
            h = x * b * height
        else:
            h = np.where(mask, hmap * SS, 0.0)
        h = blur(h)
        gy, gx = np.gradient(h)
        nrm = np.stack([-gx, -gy, np.ones_like(h)], -1)
        nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
        # lo plano (mirando al frente) queda en el tono medio; lo que gira hacia la luz se aclara
        ndl = nrm @ LIGHT
        I = mat.mid + mat.gain * (ndl - LIGHT[2])
        if pattern is not None:
            I = I * pattern
        I = np.clip(I, 0, 1)
        base = ramp_eval(mat.ramp, I)
        if mix is not None:  # (otro material, peso por submuestra)
            mat2, wgt = mix
            base = base * (1 - wgt[..., None]) + ramp_eval(mat2.ramp, I) * wgt[..., None]
        spec = (np.clip(nrm @ HALF, 0, 1) ** mat.power) * mat.spec
        col = base + spec[..., None] * (np.array(mat.spec_color, float) - base)
        self.col[mask] = col[mask]
        self.pid[mask] = self.n
        self.lines[self.n] = lines
        self.n += 1

    def glow(self, mask, inner: Color, outer: Color | None = None):
        """Brillo emisivo (no se ilumina): inner en el centro, outer en el borde."""
        mask = mask.astype(bool)
        if not mask.any():
            return
        if outer is None:
            col = np.broadcast_to(np.array(inner, float), (N, N, 3))
        else:
            d = dist(mask)
            k = np.clip(d / max(d.max(), 1), 0, 1)[..., None]
            col = np.array(outer, float) * (1 - k) + np.array(inner, float) * k
        self.col[mask] = col[mask]
        self.pid[mask] = self.n
        self.lines[self.n] = False
        self.n += 1

    def dot(self, x: int, y: int, c: Color):
        self.fx.append((x, y, c))

    def finish(self) -> Canvas:
        pid = self.pid.reshape(W, SS, W, SS).transpose(0, 2, 1, 3).reshape(W, W, SS * SS)
        col = self.col.reshape(W, SS, W, SS, 3).transpose(0, 2, 1, 3, 4).reshape(W, W, SS * SS, 3)
        cov = (pid >= 0).mean(-1)
        cv: Canvas = {}
        owner: dict[tuple[int, int], int] = {}
        for y in range(W):
            for x in range(W):
                if cov[y, x] < 0.42:
                    continue
                ids = pid[y, x]
                sel = ids >= 0
                c = col[y, x][sel].mean(0)
                cv[(x, y)] = tuple(int(round(v)) for v in np.clip(c, 0, 255))  # type: ignore[assignment]
                vals, counts = np.unique(ids[sel], return_counts=True)
                owner[(x, y)] = int(vals[np.argmax(counts)])
        # líneas de separación: la pieza de abajo se oscurece donde la toca una pieza de arriba
        dark: set[tuple[int, int]] = set()
        for (x, y), o in owner.items():
            if not self.lines.get(o, True):
                continue
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if q in owner and owner[q] > o and self.lines.get(owner[q], True):
                    dark.add((x, y))
                    break
        for p in dark:
            cv[p] = shade(cv[p], 0.62)
        # contorno selectivo: oscuro y frío; un poco más claro del lado de la luz (arriba/izq.)
        add: Canvas = {}
        for y in range(W):
            for x in range(W):
                if (x, y) in cv:
                    continue
                nb = [(q, cv[q]) for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if q in cv]
                if not nb:
                    continue
                avg = np.mean([c for _, c in nb], 0)
                lit_side = any(q in ((x + 1, y), (x, y + 1)) for q, _ in nb) and not any(
                    q in ((x - 1, y), (x, y - 1)) for q, _ in nb)
                k = 0.36 if lit_side else 0.2
                c = avg * k + np.array([10, 6, 22]) * (1 - k) * 0.9
                c = np.maximum(c, 0)
                if c.max() < 34:  # el builder borra píxeles con canal máximo <= 30
                    c = c + (34 - c.max())
                add[(x, y)] = tuple(int(v) for v in c)  # type: ignore[assignment]
        cv.update(add)
        for x, y, c in self.fx:
            if 0 <= x < W and 0 <= y < W:
                cv[(x, y)] = c
        return cv


def shade(c: Color, k: float) -> Color:
    # oscurece corriendo el tono hacia violeta frío (sombra con cambio de tono)
    return (int(c[0] * k + 6 * (1 - k)), int(c[1] * k + 2 * (1 - k)), int(c[2] * k + 16 * (1 - k)))


def sparkle(sp: Sprite, x: int, y: int, big: bool = False, c: Color = (255, 255, 255)):
    sp.dot(x, y, c)
    if big:
        soft = (int(c[0] * 0.75 + 40), int(c[1] * 0.75 + 40), int(c[2] * 0.8 + 50))
        soft = tuple(min(255, v) for v in soft)  # type: ignore[assignment]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sp.dot(x + dx, y + dy, soft)  # type: ignore[arg-type]


# ================================================================ piezas comunes

def cylinder_h(fr: Frame, r: float):
    return np.sqrt(np.clip(r * r - fr.s ** 2, 0, None))


def wrap_pattern(fr: Frame, period: float, depth: float = 0.35, slant: float = 0.6):
    phase = (fr.t + fr.s * slant) / period
    return 1 - depth * (np.abs(np.sin(phase * math.pi)) ** 6)


def sword_grip(sp: Sprite, fr: Frame, t0, t1, mat: Mat, r=1.15, period=1.25):
    m = (fr.t >= t0) & (fr.t <= t1) & (np.abs(fr.s) <= r)
    sp.add(m, mat, hmap=cylinder_h(fr, r) * 1.2, pattern=wrap_pattern(fr, period))


def gem(sp: Sprite, x, y, r, mat: Mat):
    sp.add(disc(x, y, r), mat, bevel=r, profile="round", height=1.3)


def blade(sp: Sprite, fr: Frame, t0, t1, half, mat: Mat, taper=0.78, curve=None, profile="ridge",
          bevel=None, fuller=None, wave=None):
    def width(u):
        w = np.where(u < taper, 1.0 - 0.12 * u, (1 - u) / (1 - taper) * (1.0 - 0.12 * taper))
        if wave:
            w = w * (1 + wave * np.sin(u * math.pi * 7))
        return half * np.clip(w, 0, None)

    m = strip(fr, t0, t1, width, curve)
    pat = None
    if fuller:
        u = np.clip((fr.t - t0) / (t1 - t0), 0, 1)
        c = curve(u) if curve else 0.0
        on = (u < fuller) & (u > 0.03)
        pat = np.where(on, 1 - 0.42 * np.exp(-((fr.s - c) / 0.42) ** 2), 1.0)
    sp.add(m, mat, bevel=bevel or half, profile=profile, height=0.9, pattern=pat)
    return m


# ================================================================ items

def sword_frame() -> Frame:
    return Frame(2.6, 29.4, 1, -1)  # pomo abajo a la izquierda, punta arriba a la derecha


def venomqueen_fang() -> Canvas:
    sp = Sprite()
    fr = sword_frame()
    curve = lambda u: -1.5 * np.sin(u * math.pi * 0.85)  # noqa: E731
    u = np.clip((fr.t - 11.5) / 25.5, 0, 1)
    # colmillo de marfil que se vuelve verde veneno hacia la punta
    m = strip(fr, 11.5, 37.0, lambda u: 2.6 * (1 - u ** 1.25), curve)
    sp.add(m, IVORY, bevel=2.2, profile="ridge", height=0.8, mix=(VENOM, np.clip((u - 0.42) / 0.3, 0, 1)))
    # canal de veneno que brilla
    ch = m & (np.abs(fr.s - curve(u) - 0.9) < 0.28) & (u > 0.12) & (u < 0.7)
    sp.glow(ch, (190, 255, 120), (80, 200, 60))
    # guarda: dos colmillos curvos de obsidiana que se abren hacia la hoja
    for side in (-1, 1):
        prong = [fr.xy(10.6, 1.0 * side), fr.xy(10.4, 3.0 * side), fr.xy(11.4, 4.6 * side), fr.xy(13.2, 5.4 * side)]
        sp.add(polyline(prong, 0.8), OBSIDIAN, bevel=0.8)
        tipx, tipy = fr.xy(13.4, 5.4 * side)
        sp.add(disc(tipx, tipy, 0.6), VENOM, bevel=0.6)
    gc = fr.xy(11.0, 0)
    sp.add(disc(gc[0], gc[1], 2.1), OBSIDIAN, bevel=1.4)
    gem(sp, gc[0], gc[1], 1.25, EMERALD)
    sword_grip(sp, fr, 3.4, 9.6, Mat([(20, 8, 30), (50, 22, 70), (90, 46, 120), (140, 90, 170)], 0.3, 14))
    p = fr.xy(1.8, 0)
    sp.add(disc(p[0], p[1], 2.0), OBSIDIAN, bevel=1.2)
    gem(sp, p[0], p[1], 1.1, EMERALD)
    out = sp
    tip = fr.xy(36.0, curve(0.96) + 0.4)
    sparkle(out, int(gc[0]) - 1, int(gc[1]) - 1)
    out.dot(int(tip[0]) - 1, int(tip[1]) + 3, (160, 255, 110))
    out.dot(int(tip[0]) - 1, int(tip[1]) + 4, (70, 190, 60))
    return out.finish()


def ashlord_emberblade() -> Canvas:
    sp = Sprite()
    fr = sword_frame()
    m = blade(sp, fr, 12.0, 37.4, 2.35, OBSIDIAN, taper=0.8, wave=0.12, bevel=1.6, profile="ridge")
    # grietas de brasa (dos venas que serpentean por la hoja)
    u = (fr.t - 12.0) / 25.4
    for k, ph in ((0.85, 0.0), (-0.8, 1.7)):
        vein = m & (np.abs(fr.s - k * np.sin(fr.t * 0.9 + ph) * 0.7) < 0.36) & (u > 0.04) & (u < 0.86)
        sp.glow(vein, (255, 236, 150), (255, 110, 30))
    # guarda con cuernos
    horns = []
    for side in (-1, 1):
        horns.append([fr.xy(11.0, 1.0 * side), fr.xy(10.4, 3.4 * side), fr.xy(11.8, 5.2 * side), fr.xy(13.6, 5.4 * side)])
    for h in horns:
        sp.add(polyline(h, 0.75), DARK_STEEL, bevel=0.7)
    gc = fr.xy(10.9, 0)
    sp.add(disc(gc[0], gc[1], 2.2), DARK_STEEL, bevel=1.4)
    gem(sp, gc[0], gc[1], 1.2, Mat([(80, 10, 0), (200, 60, 10), (255, 150, 40), (255, 230, 140)], 1.0, 40))
    sword_grip(sp, fr, 3.4, 9.4, LEATHER_RED)
    p = fr.xy(1.8, 0)
    sp.add(disc(p[0], p[1], 2.0), DARK_STEEL, bevel=1.2)
    sp.glow(disc(p[0], p[1], 0.8), (255, 220, 120), (255, 120, 30))
    sparkle(sp, int(gc[0]) - 1, int(gc[1]) - 1, c=(255, 240, 200))
    for x, y in ((24, 3), (28, 7), (21, 1)):
        sp.dot(x, y, (255, 170, 60))
    return sp.finish()


def bloodreaver_saber() -> Canvas:
    sp = Sprite()
    fr = sword_frame()
    curve = lambda u: 2.4 * u * u  # noqa: E731
    m = blade(sp, fr, 12.0, 37.0, 1.9, CRIMSON, taper=0.84, curve=curve, profile="flat", bevel=0.9,
              fuller=0.72)
    # filo claro del lado de afuera (curvo)
    u = np.clip((fr.t - 12.0) / 25.0, 0, 1)
    edge = m & (fr.s - curve(u) < -1.25)
    sp.add(edge, Mat([(140, 40, 50), (220, 120, 120), (255, 200, 196), (255, 245, 240)], 0.9, 30), bevel=0.4,
           lines=False)
    # guarda de sable: travesaño dorado + arco de mano
    a = fr.xy(11.0, -3.6)
    b = fr.xy(11.0, 3.4)
    sp.add(capsule(a[0], a[1], b[0], b[1], 0.85), GOLD, bevel=0.85)
    bow = [fr.xy(11.0, 3.4), fr.xy(8.6, 4.3), fr.xy(5.6, 4.3), fr.xy(3.0, 3.0), fr.xy(2.6, 1.4)]
    sp.add(polyline(bow, 0.6), GOLD, bevel=0.6)
    sword_grip(sp, fr, 3.2, 10.2, Mat([(20, 6, 10), (50, 14, 20), (90, 30, 34), (140, 60, 60)], 0.3, 14))
    p = fr.xy(1.8, 0)
    sp.add(disc(p[0], p[1], 1.8), GOLD, bevel=1.1)
    gc = fr.xy(11.0, 0)
    gem(sp, gc[0], gc[1], 1.3, RUBY)
    sparkle(sp, int(gc[0]) - 1, int(gc[1]) - 1)
    tip = fr.xy(30.0, curve((30 - 12) / 25) - 1.6)
    sparkle(sp, int(tip[0]), int(tip[1]), big=True)
    return sp.finish()


def frostwarden_chillblade() -> Canvas:
    sp = Sprite()
    fr = sword_frame()
    m = blade(sp, fr, 11.6, 37.6, 2.35, ICE, taper=0.74, profile="ridge", bevel=2.35)
    _ = m
    # escarcha: cristales que nacen de la guarda
    for side in (-1, 1):
        for t, s, r in ((13.2, 3.1, 0.9), (14.6, 3.8, 0.7), (12.4, 4.4, 0.75)):
            x, y = fr.xy(t, s * side)
            tip = fr.xy(t + 2.2, (s + 0.6) * side)
            sp.add(capsule(x, y, tip[0], tip[1], r * 0.8), ICE, bevel=0.6, profile="ridge")
    # guarda de plata con alas
    wing = [fr.xy(10.6, -5.2), fr.xy(11.8, -3.0), fr.xy(11.2, 0), fr.xy(11.8, 3.0), fr.xy(10.6, 5.2),
            fr.xy(9.6, 3.2), fr.xy(10.0, 0), fr.xy(9.6, -3.2)]
    sp.add(poly_xy(wing), SILVER, bevel=0.9)
    gc = fr.xy(10.6, 0)
    gem(sp, gc[0], gc[1], 1.35, SAPPHIRE)
    sword_grip(sp, fr, 3.4, 9.4, Mat([(14, 24, 60), (30, 56, 120), (60, 100, 180), (120, 170, 230)], 0.4, 20))
    p = fr.xy(1.8, 0)
    sp.add(disc(p[0], p[1], 1.9), SILVER, bevel=1.2)
    gem(sp, p[0], p[1], 0.9, SAPPHIRE)
    sparkle(sp, int(gc[0]) - 1, int(gc[1]) - 1)
    for t in (20.0, 31.0):
        x, y = fr.xy(t, -1.0)
        sparkle(sp, int(x), int(y), big=(t > 25))
    for x, y in ((29, 9), (22, 2)):
        sp.dot(x, y, (220, 246, 255))
    return sp.finish()


def medusa_sword() -> Canvas:
    sp = Sprite()
    fr = sword_frame()
    blade(sp, fr, 12.0, 37.4, 2.0, JADE, taper=0.8, profile="ridge", bevel=2.0, fuller=0.65)
    # guarda: dos serpientes doradas enroscadas, con la cabeza mirando a la hoja
    for side in (-1, 1):
        body = [fr.xy(11.2, 0.6 * side), fr.xy(10.2, 2.4 * side), fr.xy(10.6, 4.2 * side),
                fr.xy(12.2, 5.0 * side), fr.xy(13.8, 4.4 * side), fr.xy(14.6, 3.2 * side)]
        sp.add(polyline(body, 0.72), GOLD, bevel=0.72)
        hx, hy = fr.xy(14.8, 3.0 * side)
        sp.add(disc(hx, hy, 1.15), JADE, bevel=0.9)
        sp.dot(int(hx), int(hy), (255, 60, 40))
    gc = fr.xy(11.0, 0)
    sp.add(disc(gc[0], gc[1], 2.1), GOLD, bevel=1.3)
    gem(sp, gc[0], gc[1], 1.25, Mat([(80, 40, 0), (200, 140, 0), (255, 220, 40), (255, 250, 190)], 1.0, 40))
    sword_grip(sp, fr, 3.4, 9.4, Mat([(8, 30, 20), (20, 66, 44), (40, 110, 74), (90, 170, 120)], 0.4, 18),
               period=0.9)
    p = fr.xy(1.8, 0)
    sp.add(disc(p[0], p[1], 2.0), GOLD, bevel=1.2)
    sp.dot(int(p[0]), int(p[1]), (255, 70, 40))
    sparkle(sp, int(gc[0]) - 1, int(gc[1]) - 1)
    x, y = fr.xy(30.0, -0.9)
    sparkle(sp, int(x), int(y), big=True)
    return sp.finish()


def sword_of_silence() -> Canvas:
    sp = Sprite()
    fr = sword_frame()
    m = blade(sp, fr, 12.0, 37.6, 2.05, MOONSTEEL, taper=0.82, profile="flat", bevel=1.0, fuller=0.75)
    # runas apagadas en el canal
    for t in (15.0, 18.4, 21.8, 25.2):
        x, y = fr.xy(t, 0)
        sp.glow(disc(x, y, 0.45) & m, (190, 210, 255))
    # guarda alada, plata
    wing = [fr.xy(11.6, -5.6), fr.xy(12.4, -2.0), fr.xy(11.8, 0), fr.xy(12.4, 2.0), fr.xy(11.6, 5.6),
            fr.xy(10.0, 4.6), fr.xy(10.4, 0), fr.xy(10.0, -4.6)]
    sp.add(poly_xy(wing), SILVER, bevel=0.9)
    gc = fr.xy(11.0, 0)
    gem(sp, gc[0], gc[1], 1.3, Mat([(30, 40, 90), (80, 110, 190), (160, 196, 255), (240, 248, 255)], 1.0, 44))
    sword_grip(sp, fr, 3.4, 9.6, INDIGO, period=1.0)
    p = fr.xy(1.8, 0)
    sp.add(disc(p[0], p[1], 2.0), SILVER, bevel=1.2)
    sparkle(sp, int(gc[0]) - 1, int(gc[1]) - 1)
    x, y = fr.xy(33.0, -0.8)
    sparkle(sp, int(x), int(y), big=True)
    return sp.finish()


def nightglass_dagger() -> Canvas:
    sp = Sprite()
    fr = Frame(5.0, 27.0, 1, -1)
    # hoja corta y ondulada de vidrio negro
    blade(sp, fr, 10.0, 29.0, 2.3, NIGHTGLASS, taper=0.62, wave=0.14, profile="ridge", bevel=2.3)
    gc = fr.xy(9.0, 0)
    wing = [fr.xy(9.2, -4.2), fr.xy(10.2, -1.6), fr.xy(10.2, 1.6), fr.xy(9.2, 4.2), fr.xy(8.0, 2.4), fr.xy(8.0, -2.4)]
    sp.add(poly_xy(wing), SILVER, bevel=0.8)
    gem(sp, gc[0], gc[1], 1.2, AMETHYST)
    sword_grip(sp, fr, 3.0, 7.8, Mat([(10, 8, 18), (28, 22, 44), (52, 44, 76), (90, 80, 120)], 0.3, 16), period=1.0)
    p = fr.xy(1.6, 0)
    sp.add(disc(p[0], p[1], 1.8), SILVER, bevel=1.1)
    gem(sp, p[0], p[1], 0.8, AMETHYST)
    sparkle(sp, int(gc[0]) - 1, int(gc[1]) - 1)
    for t, big in ((16.0, False), (22.5, True)):
        x, y = fr.xy(t, -1.0)
        sparkle(sp, int(x), int(y), big=big, c=(236, 226, 255))
    return sp.finish()


def axe_frame() -> Frame:
    return Frame(29.4, 29.6, -1, -1)  # mango abajo a la derecha, cabeza arriba a la izquierda (s>0 = arriba-der.)


def wood_handle(sp: Sprite, fr: Frame, t0, t1, mat: Mat, r=1.05, wrap: Mat | None = None, wrap_t=(1.0, 6.5)):
    m = (fr.t >= t0) & (fr.t <= t1) & (np.abs(fr.s) <= r)
    grain = 1 - 0.12 * (np.sin(fr.t * 2.3 + fr.s * 5.0) > 0.6)
    sp.add(m, mat, hmap=cylinder_h(fr, r) * 1.1, pattern=grain)
    if wrap is not None:
        m2 = (fr.t >= wrap_t[0]) & (fr.t <= wrap_t[1]) & (np.abs(fr.s) <= r + 0.25)
        sp.add(m2, wrap, hmap=cylinder_h(fr, r + 0.25) * 1.2, pattern=wrap_pattern(fr, 1.1))


def stormcaller_maul() -> Canvas:
    sp = Sprite()
    fr = axe_frame()
    wood_handle(sp, fr, 0.0, 22.0, DARK_WOOD, r=1.1, wrap=LEATHER_BROWN, wrap_t=(0.8, 7.0))
    for t in (10.5, 16.5):  # anillos de acero
        sp.add((np.abs(fr.t - t) <= 0.55) & (np.abs(fr.s) <= 1.5), STEEL, bevel=0.5)
    # cabeza: bloque con biseles y chaflanes
    head = [(20.4, -6.4), (21.4, -7.6), (29.6, -7.6), (30.6, -6.4), (30.6, 6.4), (29.6, 7.6), (21.4, 7.6), (20.4, 6.4)]
    sp.add(poly_ts(fr, head), STORM, bevel=1.4, profile="round", height=0.9)
    # caras de golpe de acero
    for side in (-1, 1):
        cap = [(21.0, 5.9 * side), (30.0, 5.9 * side), (30.0, 7.9 * side), (21.0, 7.9 * side)]
        sp.add(poly_ts(fr, cap) & poly_ts(fr, head), STEEL, bevel=0.6)
    # banda central y remaches
    band = (np.abs(fr.t - 25.5) <= 4.2) & (np.abs(np.abs(fr.s) - 3.9) <= 0.45)
    sp.add(band, STEEL, bevel=0.4)
    for t in (22.4, 28.6):
        for s in (-3.9, 3.9):
            x, y = fr.xy(t, s)
            sp.add(disc(x, y, 0.65), SILVER, bevel=0.65)
    # rayo grabado que brilla
    bolt = [fr.xy(28.8, -2.6), fr.xy(26.4, -0.4), fr.xy(26.0, -1.6), fr.xy(23.0, 1.8), fr.xy(24.6, 0.4),
            fr.xy(22.2, 2.6)]
    sp.glow(polyline(bolt, 0.75), (150, 230, 255))
    sp.glow(polyline(bolt, 0.32), (255, 252, 200))
    for x, y in ((3, 13), (12, 2), (2, 5), (14, 6)):
        sp.dot(x, y, (180, 236, 255))
    return sp.finish()


def ironhide_crusher() -> Canvas:
    sp = Sprite()
    fr = axe_frame()
    wood_handle(sp, fr, 0.0, 22.0, IRON, r=1.1, wrap=LEATHER_BROWN, wrap_t=(0.8, 8.0))
    hx, hy = fr.xy(25.6, 0)
    # púas cónicas (detrás del cuerpo)
    for ang in range(0, 360, 45):
        a = math.radians(ang + 22.5)
        ca, sa = math.cos(a), math.sin(a)
        tri = [(hx + ca * 4.8 - sa * 1.5, hy + sa * 4.8 + ca * 1.5), (hx + ca * 9.4, hy + sa * 9.4),
               (hx + ca * 4.8 + sa * 1.5, hy + sa * 4.8 - ca * 1.5)]
        sp.add(poly_xy(tri), IRON, bevel=0.9, profile="ridge")
    sp.add(disc(hx, hy, 6.2), IRON, bevel=6.2, profile="round", height=0.8)
    # aro de refuerzo con remaches
    ring = (np.hypot(GX - hx, GY - hy) <= 4.6) & (np.hypot(GX - hx, GY - hy) >= 3.6)
    sp.add(ring, DARK_STEEL, bevel=0.5)
    for ang in range(0, 360, 60):
        a = math.radians(ang + 10)
        sp.add(disc(hx + math.cos(a) * 4.1, hy + math.sin(a) * 4.1, 0.7), SILVER, bevel=0.7)
    # collar donde entra el mango
    x, y = fr.xy(19.6, 0)
    sp.add(disc(x, y, 1.9), DARK_STEEL, bevel=1.2)
    return sp.finish()


def axe_blade(sp: Sprite, fr: Frame, poly, mat: Mat, edge_mat: Mat, edge_w=1.2):
    m = poly_ts(fr, poly)
    sp.add(m, mat, bevel=1.6, profile="round", height=0.7)
    edge = m & ~poly_ts(fr, poly, ds=-edge_w)  # banda donde el borde mira hacia afuera (s+)
    sp.add(edge, edge_mat, bevel=0.6, profile="ridge", lines=False)
    return m


def windsting_axe() -> Canvas:
    sp = Sprite()
    fr = axe_frame()
    wood_handle(sp, fr, 0.0, 27.5, WOOD, r=1.0,
                wrap=Mat([(8, 40, 44), (20, 84, 90), (40, 136, 136), (100, 200, 190)], 0.4, 18), wrap_t=(0.8, 6.8))
    blade_poly = [(20.4, 0.6), (18.4, 2.4), (15.6, 4.6), (13.4, 7.4), (14.2, 9.8), (17.6, 11.0), (21.6, 11.4),
                  (25.6, 11.0), (29.0, 9.8), (32.2, 7.8), (30.0, 5.6), (27.8, 3.2), (26.0, 0.6)]
    wsteel = Mat([(6, 30, 40), (14, 62, 74), (28, 104, 112), (62, 156, 156), (140, 214, 206), (230, 255, 250)], 0.8, 34)
    m = axe_blade(sp, fr, blade_poly, wsteel,
                  Mat([(60, 150, 150), (160, 236, 226), (236, 255, 252), (255, 255, 255)], 1.0, 30), edge_w=1.4)
    # remolino de viento grabado
    cx, cy = fr.xy(22.8, 6.0)
    ang = np.arctan2(GY - cy, GX - cx)
    r = np.hypot(GX - cx, GY - cy)
    swirl = m & (r < 3.6) & (np.abs(((r - ang * 0.62) % 1.95) - 0.97) < 0.36)
    sp.glow(swirl, (210, 255, 248), (120, 220, 210))
    back = [(24.4, -0.6), (21.8, -0.6), (22.2, -3.4), (23.8, -4.2)]
    sp.add(poly_ts(fr, back), wsteel, bevel=0.8, profile="ridge")
    x, y = fr.xy(23.0, 0)
    sp.add(disc(x, y, 1.6), SILVER, bevel=1.0)
    for x, y, c in ((2, 8, (210, 255, 248)), (3, 8, (150, 230, 220)), (4, 7, (210, 255, 248)),
                    (1, 12, (150, 230, 220)), (2, 12, (210, 255, 248)), (7, 2, (210, 255, 248)), (8, 2, (150, 230, 220))):
        sp.dot(x, y, c)
    return sp.finish()


def bonepriest_reaver() -> Canvas:
    sp = Sprite()
    fr = axe_frame()
    # mango de vértebras
    m = (fr.t >= 0.0) & (fr.t <= 28.0) & (np.abs(fr.s) <= 1.15)
    vert = 1 - 0.38 * (np.abs(np.sin(fr.t * math.pi / 1.5)) ** 8)
    sp.add(m, BONE, hmap=cylinder_h(fr, 1.15) * 1.2, pattern=vert)
    # media luna: dos cuernos y filo convexo entre ellos
    blade_poly = [(20.4, 0.6), (18.8, 2.4), (16.2, 4.0), (13.2, 5.4), (11.6, 7.6), (13.4, 10.4), (17.6, 12.4),
                  (22.4, 13.0), (27.0, 12.2), (30.8, 9.8), (32.4, 6.6), (30.0, 5.0), (27.6, 3.2), (26.0, 0.6)]
    bone_dark = Mat([(40, 26, 36), (92, 72, 70), (150, 132, 108), (204, 190, 156), (240, 232, 206), (255, 252, 240)], 0.35, 18)
    bm = axe_blade(sp, fr, blade_poly, bone_dark, NECRO, edge_w=1.5)
    # grietas que salen del encastre hacia el filo
    for ang in (-0.55, -0.1, 0.4):
        pts = [fr.xy(23.0 + k * math.sin(ang) * 2.4, 2.6 + k * 2.4) for k in range(5)]
        sp.glow(polyline(pts, 0.32) & bm & poly_ts(fr, blade_poly, ds=-1.6), (190, 120, 250))
    back = [(24.2, -0.6), (21.6, -0.6), (22.0, -4.0), (23.2, -5.6)]
    sp.add(poly_ts(fr, back), bone_dark, bevel=0.8, profile="ridge")
    # calavera en el encastre
    sx, sy = fr.xy(23.0, 1.2)
    sp.add(disc(sx, sy, 2.5, 2.3), IVORY, bevel=2.0, height=0.9)
    for ex in (-0.95, 0.95):
        sp.glow(disc(sx + ex, sy - 0.1, 0.6), (210, 140, 255))
    sp.glow(disc(sx, sy + 1.3, 0.35) | disc(sx - 0.65, sy + 1.5, 0.3) | disc(sx + 0.65, sy + 1.5, 0.3), (40, 20, 50))
    return sp.finish()


def fury_cape() -> Canvas:
    sp = Sprite()
    # silueta: cuello, hombros redondeados, cae y termina en lenguas de fuego
    y = GY
    half = np.where(y <= 5.5, 4.2, np.where(y <= 11, 4.2 + 7.2 * np.sin(np.clip((y - 5.5) / 5.5, 0, 1) * math.pi / 2),
                                            11.4 + (y - 11) * 0.16))
    hem = 26.8 + 2.4 * np.sin(GX * 1.15) + 0.9 * np.sin(GX * 2.6 + 1.0)
    m = (np.abs(GX - 16) <= half) & (y >= 2.8) & (y <= hem)
    folds = 0.9 * np.sin((GX - 16) * 1.05) * np.clip((y - 6) / 10, 0, 1)
    edge = np.clip(dist(m) / (1.4 * SS), 0, 1)
    h = (np.sqrt(np.clip(1 - (1 - edge) ** 2, 0, 1)) * 1.4 + folds + 0.8) * 1.0
    fire = np.clip((y - 14) / 12, 0, 1)
    sp.add(m, CLOTH_RED, hmap=h, mix=(CLOTH_FIRE, fire))
    # lenguas de fuego en el ruedo
    flame = m & (y >= hem - 2.6) & (y >= 20)
    sp.glow(flame, (255, 236, 140), (255, 120, 30))
    tips = m & (y >= hem - 1.0) & (y >= 22)
    sp.glow(tips, (255, 250, 210))
    # forro oscuro en el cuello y cordón dorado
    collar = (np.abs(GX - 16) <= 3.4 - (GY - 2.8) * 0.8) & (GY >= 2.8) & (GY <= 5.4)
    sp.add(collar, Mat([(20, 2, 8), (44, 6, 16), (70, 12, 24)], 0.1, 8), bevel=0.5)
    cord = polyline([(11.6, 6.0), (14.0, 7.2), (16.0, 7.4), (18.0, 7.2), (20.4, 6.0)], 0.55)
    sp.add(cord, GOLD, bevel=0.55)
    sp.add(disc(16.0, 7.4, 1.5), GOLD, bevel=1.0)
    gem(sp, 16.0, 7.4, 0.8, RUBY)
    sparkle(sp, 15, 7)
    for x, yy in ((6, 20), (25, 18), (4, 26)):
        sp.dot(x, yy, (255, 190, 80))
    return sp.finish()


def crimson_wand() -> Canvas:
    sp = Sprite()
    fr = Frame(4.0, 29.0, 1, -1)
    rod = (fr.t >= 0.0) & (fr.t <= 26.0) & (np.abs(fr.s) <= 0.95 - fr.t * 0.008)
    sp.add(rod, Mat([(16, 2, 8), (44, 6, 16), (84, 12, 26), (130, 28, 40), (190, 80, 84)], 0.8, 36),
           hmap=cylinder_h(fr, 0.95) * 1.2)
    # espiral dorada y empuñadura
    spiral = rod & (np.abs(((fr.t * 0.9 + fr.s * 1.6) % 3.2) - 1.6) < 0.35) & (fr.t > 6) & (fr.t < 22)
    sp.add(spiral, GOLD, hmap=cylinder_h(fr, 1.0) * 1.3, lines=False)
    sp.add((fr.t >= 0.4) & (fr.t <= 5.8) & (np.abs(fr.s) <= 1.25), GOLD, hmap=cylinder_h(fr, 1.25) * 1.2,
           pattern=wrap_pattern(fr, 1.2, 0.3))
    # garras que sostienen el cristal
    for side in (-1, 1):
        claw = [fr.xy(25.2, 0.6 * side), fr.xy(26.6, 2.4 * side), fr.xy(28.4, 2.2 * side)]
        sp.add(polyline(claw, 0.5), GOLD, bevel=0.5)
    cryst = [(26.0, 0.0), (29.6, -2.4), (34.6, 0.0), (29.6, 2.4)]
    sp.add(poly_ts(fr, cryst), RUBY, bevel=2.4, profile="ridge", height=1.2)
    x, y = fr.xy(30.2, -0.8)
    sparkle(sp, int(x), int(y), big=True)
    for x, y, c in ((28, 1, (255, 200, 200)), (31, 5, (255, 150, 150)), (24, 0, (255, 180, 180)), (30, 2, (255, 240, 240))):
        sp.dot(x, y, c)
    return sp.finish()


def crimson_helmet() -> Canvas:
    sp = Sprite()
    cx = 16.0
    dome = ((GX - cx) / 10.4) ** 2 + ((GY - 14.0) / 11.0) ** 2 <= 1
    body = (np.abs(GX - cx) <= 10.4 - np.clip(GY - 22, 0, None) * 0.55) & (GY >= 14) & (GY <= 28.6)
    shell = (dome & (GY < 14.2)) | body
    hm = np.sqrt(np.clip(1 - ((GX - cx) / 10.6) ** 2 - (np.clip(14 - GY, 0, None) / 11.2) ** 2, 0, 1)) * 7.0
    sp.add(shell, CRIMSON, hmap=hm)
    # cresta dorada
    crest = (np.abs(GX - cx) <= 1.05) & (GY >= 2.6) & (GY <= 14.5) & shell
    sp.add(crest, GOLD, hmap=hm + 1.0 - np.abs(GX - cx))
    # visor: ribete dorado en T
    trim = ((np.abs(GY - 14.6) <= 0.85) & (np.abs(GX - cx) <= 8.6)) | ((np.abs(GX - cx) <= 1.0) & (GY >= 14) & (GY <= 25.2))
    sp.add(trim & shell, GOLD, hmap=hm * 0.2 + 1.0)
    # rendijas de los ojos (huecos oscuros)
    for side in (-1, 1):
        slit = (np.abs(GY - 16.6) <= 0.75) & (np.abs(GX - cx - side * 4.9) <= 3.4)
        sp.glow(slit, (24, 4, 12))
    mouth = (GY >= 18.4) & (GY <= 25.0) & (np.abs(GX - cx) >= 1.5) & (np.abs(GX - cx) <= 4.2 - (GY - 18.4) * 0.12)
    breaths = mouth & (np.abs(((GY - 18.4) % 1.6) - 0.8) < 0.42)
    sp.glow(breaths, (30, 6, 14))
    # borde inferior dorado y remaches
    rim = shell & (GY >= 27.0)
    sp.add(rim, GOLD, hmap=hm * 0.3 + 0.8)
    for x, y in ((7.6, 21.0), (24.4, 21.0), (7.8, 25.6), (24.2, 25.6)):
        sp.add(disc(x, y, 0.7), GOLD, bevel=0.7)
    sparkle(sp, 10, 7, big=True)
    return sp.finish()


def train_wand() -> Canvas:
    sp = Sprite()
    fr = Frame(6.0, 28.0, 1, -1)
    wood_handle(sp, fr, 0.0, 21.0, WOOD, r=0.9, wrap=LEATHER_BROWN, wrap_t=(0.5, 5.5))
    for t in (8.0, 15.0):
        sp.add((np.abs(fr.t - t) <= 0.45) & (np.abs(fr.s) <= 1.2), Mat(SILVER.ramp, 0.6, 30), bevel=0.4)
    x, y = fr.xy(23.2, 0)
    sp.add(disc(x, y, 2.6), AMETHYST, bevel=2.6, profile="round", height=1.2)
    sparkle(sp, int(x) - 1, int(y) - 1)
    return sp.finish()


def rune_stone(sp: Sprite, mat: Mat):
    shape = [(6.0, 7.0), (10.0, 4.6), (21.0, 4.2), (26.0, 6.6), (27.4, 12.0), (27.0, 23.0), (24.6, 28.0),
             (14.0, 28.8), (7.4, 27.2), (5.0, 21.0), (4.8, 12.0)]
    m = poly_xy(shape)
    tex = 1 - 0.1 * ((np.sin(GX * 3.1 + GY * 1.7) * np.sin(GY * 2.3 - GX * 0.9)) > 0.45)
    sp.add(m, mat, bevel=2.4, profile="round", height=0.9, pattern=tex)
    return m


def experience_recovery_rune() -> Canvas:
    sp = Sprite()
    m = rune_stone(sp, STONE_BLUE)
    # grabado: flecha hacia arriba dentro de un anillo (recuperar lo perdido)
    ring = (np.abs(np.hypot(GX - 16, GY - 16.6) - 7.4) <= 0.75) & m
    arrow = polyline([(16, 22.4), (16, 11.2)], 0.8) | polyline([(11.8, 15.4), (16, 11.0), (20.2, 15.4)], 0.8)
    groove = ring | arrow
    sp.glow(polyline([(16, 22.4), (16, 11.2)], 1.3) | polyline([(11.8, 15.4), (16, 11.0), (20.2, 15.4)], 1.3) |
            ((np.abs(np.hypot(GX - 16, GY - 16.6) - 7.4) <= 1.3) & m), (14, 10, 40))
    sp.glow(groove, (255, 236, 150), (255, 140, 40))
    sparkle(sp, 8, 7, big=True)
    return sp.finish()


def training_extension_rune() -> Canvas:
    sp = Sprite()
    m = rune_stone(sp, STONE_BROWN)
    # grabado: reloj de arena (más tiempo de training)
    glass = [(10.6, 9.4), (21.4, 9.4), (16.8, 16.4), (21.4, 23.6), (10.6, 23.6), (15.2, 16.4)]
    outline_m = poly_xy(glass) & ~poly_in(glass, 16 + (GX - 16) * 1.35, 16.5 + (GY - 16.5) * 1.18)
    caps = (np.abs(GY - 9.2) <= 0.7) | (np.abs(GY - 23.8) <= 0.7)
    caps &= (np.abs(GX - 16) <= 6.6)
    sand = poly_xy([(12.6, 21.8), (19.4, 21.8), (16.0, 18.4)]) | poly_xy([(13.2, 11.0), (18.8, 11.0), (16.0, 14.2)])
    sp.glow((outline_m | caps) & m, (220, 250, 255), (90, 180, 230))
    sp.glow(sand & m, (255, 220, 120), (230, 150, 50))
    sparkle(sp, 8, 7, big=True)
    return sp.finish()


# server id -> (archivo, función, server id vanilla cuyo .dat se copia)
ITEMS: dict[int, tuple[str, object, int]] = {
    20100: ("venomqueen_fang", venomqueen_fang, 2407),
    20110: ("stormcaller_maul", stormcaller_maul, 2391),
    20112: ("ashlord_emberblade", ashlord_emberblade, 2407),
    20121: ("ironhide_crusher", ironhide_crusher, 2391),
    20122: ("bloodreaver_saber", bloodreaver_saber, 2407),
    20138: ("frostwarden_chillblade", frostwarden_chillblade, 2407),
    20154: ("bonepriest_reaver", bonepriest_reaver, 2430),
    20105: ("medusa_sword", medusa_sword, 2407),
    20139: ("sword_of_silence", sword_of_silence, 2407),
    20130: ("windsting_axe", windsting_axe, 2430),
    20114: ("fury_cape", fury_cape, 2654),
    20123: ("crimson_wand", crimson_wand, 2162),
    20137: ("nightglass_dagger", nightglass_dagger, 2383),
    20113: ("crimson_helmet", crimson_helmet, 2457),
    20126: ("train_wand", train_wand, 2162),
    20131: ("experience_recovery_rune", experience_recovery_rune, 2260),
    20132: ("training_extension_rune", training_extension_rune, 2268),
}

_CACHE: dict[int, Image.Image] = {}


def render(sid: int) -> Image.Image:
    if sid not in _CACHE:
        cv = ITEMS[sid][1]()  # type: ignore[operator]
        img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        px = img.load()
        for (x, y), c in cv.items():
            px[x, y] = (*c, 255)
        _CACHE[sid] = img
    return _CACHE[sid]


# ================================================================ vista previa

def preview(path: Path, names: dict[int, str], only: list[int] | None = None) -> None:
    sids = only or list(ITEMS)
    scale, cols = 5, 5
    cw, ch = W * scale + W + 14, W * scale + 18
    rows = (len(sids) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cw, rows * ch), (40, 40, 44, 255))
    draw = ImageDraw.Draw(sheet)
    for i, sid in enumerate(sids):
        img = render(sid)
        x, y = (i % cols) * cw + 4, (i // cols) * ch + 4
        draw.rectangle([x, y, x + W * scale - 1, y + W * scale - 1], fill=(92, 92, 98, 255))
        sheet.alpha_composite(img.resize((W * scale, W * scale), Image.NEAREST), (x, y))
        bx = x + W * scale + 6
        for k, bg in enumerate(((58, 56, 54, 255), (70, 120, 50, 255), (150, 140, 120, 255))):
            draw.rectangle([bx, y + k * (W + 6), bx + W - 1, y + k * (W + 6) + W - 1], fill=bg)
            sheet.alpha_composite(img, (bx, y + k * (W + 6)))
        draw.text((x, y + W * scale + 2), f"{sid} {names.get(sid, ITEMS[sid][0])}"[:32], fill=(235, 235, 235, 255))
    sheet.save(path)


# ================================================================ aplicar al cliente

def otb_index(path: Path) -> dict[int, dict]:
    data = path.read_bytes()
    root, _ = B.parse_node(data, 4)
    out = {}
    for node in root.children:
        _, blocks = B.parse_item_props(node.props)
        sid = B.get_block_payload(blocks, B.ITEM_ATTR_SERVERID)
        cid = B.get_block_payload(blocks, B.ITEM_ATTR_CLIENTID)
        name = B.get_block_payload(blocks, B.ITEM_ATTR_NAME)
        if sid and cid and len(sid) == 2 and len(cid) == 2:
            out[struct.unpack("<H", sid)[0]] = {
                "cid": struct.unpack("<H", cid)[0],
                "name": name.decode("latin-1") if name else "",
            }
    return out


def apply(things: Path) -> None:
    dat_path, spr_path = things / "Tibia.dat", things / "Tibia.spr"
    dat_reader = B.DatReader(dat_path.read_bytes())
    entries, tail = dat_reader.read_item_entries()
    spr = B.SprReader(spr_path.read_bytes())
    by_cid = {e.client_id: i for i, e in enumerate(entries)}
    zagan, base = otb_index(ZAGAN_OTB), otb_index(BASE_OTB)

    records: list[bytes | None] = [None] + [spr.sprite_raw(i) for i in range(1, spr.sprite_count + 1)]
    raws = [e.raw for e in entries]
    original_count = spr.sprite_count
    for sid, (fname, _, proto_sid) in ITEMS.items():
        cid = zagan[sid]["cid"]
        entry = entries[by_cid[cid]]
        proto = entries[by_cid[base[proto_sid]["cid"]]]
        if len(proto.sprite_ids) != 1:
            raise SystemExit(f"{proto_sid}: el prototipo no es de 1 sprite")
        record = B.encode_sprite_record(render(sid))
        # reusar el sprite si ya es uno agregado por nosotros (único dueño, flags del prototipo)
        current = entry.sprite_ids[0] if len(entry.sprite_ids) == 1 else 0
        owners = sum(1 for e in entries if current in e.sprite_ids)
        if current > 0 and owners == 1 and entry.prefix == proto.prefix:
            sprite_id = current
            records[sprite_id] = record
        else:
            records.append(record)
            sprite_id = len(records) - 1
        raws[by_cid[cid]] = proto.prefix + struct.pack("<H", sprite_id)
        print(f"{sid} cid {cid} {zagan[sid]['name']!r}: sprite {sprite_id} (dat de {proto_sid})")

    dat_path.write_bytes(B.write_dat(
        signature=dat_reader.signature, item_count=dat_reader.item_count,
        outfit_count=dat_reader.outfit_count, effect_count=dat_reader.effect_count,
        missile_count=dat_reader.missile_count, item_entries=raws, tail=tail))
    spr_path.write_bytes(B.write_spr(signature=spr.signature, sprite_records=records))
    print(f"sprites: {original_count} -> {len(records) - 1}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--only", type=int, nargs="*", help="server ids para la vista previa")
    ap.add_argument("--png-dir", type=Path)
    ap.add_argument("--apply", type=Path, metavar="DIR_THINGS")
    args = ap.parse_args()
    names = {sid: v["name"] for sid, v in otb_index(ZAGAN_OTB).items()}
    if args.preview:
        preview(args.preview, names, args.only)
        print(f"vista previa: {args.preview}")
    if args.png_dir:
        args.png_dir.mkdir(parents=True, exist_ok=True)
        for sid, (fname, _, _) in ITEMS.items():
            render(sid).save(args.png_dir / f"{fname}.png")
        print(f"{len(ITEMS)} PNG en {args.png_dir}")
    if args.apply:
        apply(args.apply)
    if not (args.preview or args.png_dir or args.apply):
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
