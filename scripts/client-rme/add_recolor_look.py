#!/usr/bin/env python3
"""Crea un looktype nuevo recoloreando una criatura existente del cliente 7.6 (genérico).

Mismo método que add_black_dragon_look.py (que queda como referencia): copia la estructura
de la criatura base (tamaño, direcciones, cuadros) a un looktype vacío y le pone sprites
nuevos recoloreados por píxel, así la animación queda idéntica a la original.

Presets:
  black-dragon   Dragon (34) -> 230, negro con brillo violeta, ojos rojos
  frost-dragon   Dragon (34) -> 231, hielo: cuerpo azul acero a blanco, panza y alas
                 blanco hielo, ojos celestes brillantes (estilo Frost Dragon de versiones nuevas)
  ice-monk       Monk (57) -> 232, túnica azul profundo a blanco hielo, cinturón celeste
                 brillante y la cara en sombra bajo la capucha con ojos celestes que brillan
  drowned-sailor Crypt Shambler (100) -> 233, marinero ahogado: piel hinchada gris verdosa,
                 pantalón azul marino, camiseta rayada, pañuelo rojo desteñido, algas que
                 cuelgan, percebes y gotas de agua que cambian en cada cuadro
  tide-priest    Necromancer (9) -> 234, sacerdote de la marea: túnica verde mar con ribete de
                 bronce, cara en sombra con ojos celestes y, en vez de la calavera, una bola de
                 fuego de San Telmo que late, con lengua de fuego, resplandor y chispas
  ice-spider     Giant Spider (38) -> 235, hielo: cuerpo azul acero oscuro,
                 patas celeste/blanco y ojos cian

Uso:
  python3 scripts/client-rme/add_recolor_look.py --preset frost-dragon DIR_THINGS [--preview x.png]
  python3 scripts/client-rme/add_recolor_look.py --preset frost-dragon --preview x.png   # solo vista previa
  python3 scripts/client-rme/add_recolor_look.py --preset frost-dragon DIR_THINGS --replace  # rehacer el look

DIR_THINGS = carpeta con Tibia.dat y Tibia.spr (se modifican en el lugar, con copia
.bak-<preset>). Idempotente: si el looktype destino ya tiene sprites, no cambia nada, salvo con
--replace, que vuelve a generar esos mismos sprites con el preset actual (para editar un look
que ya existe; los ids de sprites no cambian).
Aplicar a devtools/rme/rme-client-760/ (RME, en git) y a la base del cliente de jugadores
antes de build_zagan_test_assets.py.

Receta paso a paso para crear o editar un sprite: docs/gameplay/SPRITE_RECOLOR_GUIDE.md.
Para mirar, comparar y verificar: scripts/client-rme/sprite_tool.py.
"""
from __future__ import annotations

import argparse
import colorsys
import math
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from add_black_dragon_look import (decode_sprite, encode_sprite, read_outfits, read_spr,  # noqa: E402
                                   recolor as recolor_black, write_preview, write_spr)

RME_THINGS = HERE.parents[1] / "devtools/rme/rme-client-760"


def gradient(stops, k):
    k = max(0.0, min(1.0, k))
    for (k0, c0), (k1, c1) in zip(stops, stops[1:]):
        if k <= k1:
            t = (k - k0) / (k1 - k0) if k1 > k0 else 0
            return tuple(int(a + (b - a) * t) for a, b in zip(c0, c1))
    return stops[-1][1]


def hsv(pixel):
    """Tono, saturación y brillo (0-1) de un píxel (r, g, b, a)."""
    return colorsys.rgb_to_hsv(pixel[0] / 255, pixel[1] / 255, pixel[2] / 255)


def part_points(parts, name, w):
    """Coordenadas (x, y) de los píxeles de una parte, a partir de la lista de partes de un cuadro."""
    return [(i % w, i // w) for i, part in enumerate(parts) if part == name]


def centroid(points):
    """Centro (x, y) con decimales de una lista de puntos."""
    return sum(x for x, _y in points) / len(points), sum(y for _x, y in points) / len(points)


FROST_BODY = [(0, (10, 16, 40)), (0.22, (36, 64, 120)), (0.45, (92, 142, 206)),
              (0.72, (176, 210, 240)), (1, (248, 252, 255))]
FROST_PALE = [(0, (26, 46, 82)), (0.35, (118, 174, 216)), (0.7, (196, 232, 246)), (1, (252, 255, 255))]


def recolor_frost(pixel):
    r, g, b, a = pixel
    if a == 0:
        return pixel
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if (h < 0.09 or h > 0.95) and s > 0.6 and v > 0.5:      # ojos, lengua, garras rojas
        return (120, 245, 255, 255)
    lum = (0.30 * r + 0.59 * g + 0.11 * b) / 255
    if 0.06 < h < 0.2 and s > 0.35:                          # panza y membranas (amarillo/naranja)
        return gradient(FROST_PALE, (lum ** 0.75) * 1.15) + (255,)
    return gradient(FROST_BODY, (lum ** 0.7) * 1.25) + (255,)  # cuerpo verde -> hielo


ICE_ROBE = [(0, (6, 10, 28)), (0.2, (18, 38, 88)), (0.45, (40, 88, 166)),
            (0.7, (110, 172, 228)), (0.9, (200, 232, 250)), (1, (245, 252, 255))]
ICE_SKIN = [(0, (70, 96, 120)), (0.55, (190, 214, 228)), (1, (240, 248, 252))]


def recolor_ice_monk(pixel):
    """Monk (57): túnica marrón -> azul profundo a blanco hielo, piel -> celeste pálido helado,
    cinturón dorado -> celeste brillante (parece que brilla)."""
    r, g, b, a = pixel
    if a == 0:
        return pixel
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    lum = (0.30 * r + 0.59 * g + 0.11 * b) / 255
    if 0.06 <= h <= 0.10 and 0.28 <= s <= 0.47 and v > 0.74:      # cara y manos
        return gradient(ICE_SKIN, lum * 1.05) + (255,)
    if 0.095 <= h <= 0.13 and s > 0.47 and v > 0.76:               # cinturón
        return gradient([(0, (60, 170, 220)), (1, (190, 250, 255))], (v - 0.76) / 0.24) + (255,)
    return gradient(ICE_ROBE, (lum ** 0.85) * 1.2) + (255,)       # túnica y sombras


def _is_skin(pixel):
    r, g, b, a = pixel
    if a == 0:
        return False
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return 0.06 <= h <= 0.10 and 0.28 <= s <= 0.47 and v > 0.74


def _clusters(points):
    points, seen, out = set(points), set(), []
    for start in sorted(points, key=lambda t: (t[1], t[0])):
        if start in seen:
            continue
        seen.add(start)
        stack, comp = [start], []
        while stack:
            x, y = stack.pop()
            comp.append((x, y))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in points and q not in seen:
                        seen.add(q)
                        stack.append(q)
        out.append(comp)
    return out


HOOD_SHADOW = (14, 22, 48, 255)
EYE_GLOW = (150, 248, 255, 255)
EYE_HALO = (50, 130, 196, 255)


def ice_monk_eyes(original, recolored):
    """Cara en sombra bajo la capucha con ojos celestes que brillan (rasgo del Ice Monk).

    La cara es el grupo de piel más grande del cuadro (las manos tienen 1-3 píxeles). De frente
    (más ancha que alta) lleva dos ojos en su fila de arriba; de perfil, uno hacia donde mira.
    De espaldas no hay cara visible y el cuadro queda igual."""
    out = []
    for index, (orig, new) in enumerate(zip(original, recolored)):
        new = list(new)
        skin = [(i % 64, i // 64) for i, p in enumerate(orig) if _is_skin(p)]
        faces = [c for c in _clusters(skin) if len(c) >= 6]
        for face in faces:
            for x, y in face:
                new[y * 64 + x] = HOOD_SHADOW
            xs = [x for x, _ in face]
            ys = [y for _, y in face]
            top = sorted(x for x, y in face if y == min(ys))
            if max(xs) - min(xs) >= max(ys) - min(ys):          # de frente
                eyes = [(top[0], min(ys)), (top[-1], min(ys))] if len(top) >= 3 else [(top[-1], min(ys))]
            else:                                                 # de perfil: mira hacia el lado del cuadro
                facing_east = index % 4 == 1
                eyes = [(max(xs) if facing_east else min(xs), min(ys) + 1)]
            face_set = set(face)
            for x, y in eyes:
                new[y * 64 + x] = EYE_GLOW
                if (x, y + 1) in face_set:                        # brillo suave debajo del ojo
                    new[(y + 1) * 64 + x] = EYE_HALO
        out.append(new)
    return out


DROWNED_SKIN = [(0, (10, 24, 30)), (0.25, (40, 72, 76)), (0.5, (96, 134, 124)), (0.75, (160, 186, 168)),
                (1, (214, 226, 206))]
DROWNED_ALGAE = [(0, (14, 30, 18)), (0.5, (46, 84, 42)), (1, (98, 136, 66))]
NAVY = [(0, (6, 10, 28)), (0.5, (28, 46, 96)), (1, (78, 104, 160))]
SHIRT_WHITE = [(0, (120, 126, 120)), (1, (222, 226, 214))]
BANDANA = [(0, (70, 14, 14)), (0.5, (150, 40, 34)), (1, (212, 96, 74))]
SEAWEED = [(20, 44, 22, 255), (36, 70, 34, 255), (62, 100, 44, 255)]
DRIP_LIGHT, DRIP_DARK = (190, 232, 240, 255), (120, 190, 210, 255)
BARNACLE_LIGHT, BARNACLE_DARK = (214, 212, 192, 255), (150, 146, 128, 255)


def _lum(pixel):
    r, g, b, _a = pixel
    return (0.30 * r + 0.59 * g + 0.11 * b) / 255


def _shambler_part(pixel):
    """Partes del Crypt Shambler (100): contorno, pantalón verde, heridas rojas o piel."""
    r, g, b, a = pixel
    if a == 0:
        return None
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if v < 0.13:
        return "dark"
    if 0.2 < h < 0.55 and s > 0.25:
        return "pants"
    if (h < 0.04 or h > 0.93) and s > 0.6:
        return "wound"
    return "skin"


def recolor_drowned(pixel):
    """Crypt Shambler -> ahogado: piel gris verdosa, heridas -> manchas de algas, pantalón azul marino."""
    part = _shambler_part(pixel)
    if part is None:
        return pixel
    r, g, b, _a = pixel
    if part == "dark":                                   # contorno con un toque azul de agua
        tint = 4 if (g or b) else 0
        return (r // 2, g // 2 + tint, b // 2 + tint + tint // 2, 255)
    if part == "pants":
        return gradient(NAVY, _lum(pixel) * 1.6) + (255,)
    if part == "wound":
        return gradient(DROWNED_ALGAE, _lum(pixel) * 1.8) + (255,)
    return gradient(DROWNED_SKIN, _lum(pixel) ** 1.15) + (255,)


def drowned_sailor_details(original, recolored):
    """Rasgos del Marinero Ahogado sobre cada cuadro 32x32 (criatura 1x1).

    - Pañuelo rojo: la cabeza es el grupo de piel gruesa (sin brazos finos) más alto del cuadro;
      cubre la mitad de arriba, y de espaldas casi toda.
    - Camiseta rayada: la piel gruesa entre la cabeza y el pantalón, en franjas blanco / azul que
      siguen la diagonal de la perspectiva. Los brazos (finos) quedan con piel.
    - Algas que cuelgan del borde de abajo del cuerpo, gotas que cambian de lugar en cada cuadro
      de la animación y tres percebes en el cuerpo."""
    w = 32
    n = w * w

    def near(i):
        x, y = i % w, i // w
        for dx, dy in CARD4:
            if 0 <= x + dx < w and 0 <= y + dy < w:
                yield (y + dy) * w + x + dx

    out = []
    for index, (orig, new) in enumerate(zip(original, recolored)):
        anim, direction = index // 4, index % 4
        new = list(new)
        parts = [_shambler_part(p) for p in orig]
        skin = {i for i, part in enumerate(parts) if part == "skin"}
        core = [i for i in skin if all(j in skin for j in near(i))]
        blobs = [c for c in _clusters({(i % w, i // w) for i in core}) if len(c) >= 5]
        head = set()
        if blobs:
            top = min(blobs, key=lambda c: min(y for _x, y in c))
            head = {y * w + x for x, y in top}
            head |= {j for i in list(head) for j in near(i) if j in skin}
            ys = [i // w for i in head]
            share = 0.7 if direction == 0 else 0.45               # de espaldas el pañuelo tapa más
            cut = min(ys) + max(1, int((max(ys) - min(ys) + 1) * share))
            for i in head:
                if i // w <= cut:
                    new[i] = gradient(BANDANA, _lum(orig[i]) * 1.15) + (255,)
        pants = [i for i, part in enumerate(parts) if part == "pants"]
        if head and pants:
            head_bottom, pants_top = max(i // w for i in head), min(i // w for i in pants)
            around_head = head | {j for i in head for j in near(i)}
            for i, part in enumerate(parts):
                y = i // w
                if not (head_bottom < y <= pants_top) or part not in ("skin", "wound") or i in around_head:
                    continue
                if sum(1 for j in near(i) if parts[j] in ("skin", "wound")) < 3:   # brazo fino
                    continue
                stripe = ((y + (i % w) // 3) // 2) % 2
                new[i] = gradient(SHIRT_WHITE if stripe == 0 else NAVY, _lum(orig[i]) * (1.3 if stripe == 0 else 1.5)) + (255,)

        opaque = {i for i, p in enumerate(orig) if p[3]}
        bottom = sorted(i for i in opaque if i + w < n and i + w not in opaque)
        lowest = max(i // w for i in opaque)
        weeds = [i for i in bottom if i // w < lowest - 5 and ((i % w) * 7 + (i // w) * 13 + direction * 3) % 9 == 0]
        for i in weeds[:4]:
            length = 2 + (i * 5 + anim) % 3
            for k in range(1, length + 1):
                j = i + w * k
                if j < n and j not in opaque:
                    new[j] = SEAWEED[min(2, k - 1)] if k < length else SEAWEED[2]
        drops = [i for i in bottom if ((i % w) * 3 + i // w + anim * 5 + direction) % 11 == 0][:2]
        for i in drops:
            j = i + w * (2 + anim % 2)
            if j < n and j not in opaque:
                new[j] = DRIP_LIGHT
                if j + w < n and j + w not in opaque:
                    new[j + w] = DRIP_DARK
        body = [i for i in core if i not in head and parts[i] == "skin"]
        for i in body[::max(1, len(body) // 3)][:3]:
            new[i] = BARNACLE_LIGHT
            if i + 1 in opaque:
                new[i + 1] = BARNACLE_DARK
        out.append(new)
    return out


TIDE_ROBE = [(0, (2, 10, 14)), (0.3, (8, 40, 46)), (0.6, (20, 84, 86)), (0.85, (52, 136, 124)), (1, (120, 196, 172))]
TIDE_SKIN = [(0, (16, 30, 40)), (0.6, (70, 104, 116)), (1, (132, 168, 170))]
TIDE_GOLD = [(0, (58, 38, 10)), (0.45, (150, 108, 34)), (0.8, (226, 186, 84)), (1, (255, 240, 170))]
ELMO_FIRE = [(0, (250, 255, 255)), (0.45, (150, 244, 255)), (0.8, (44, 168, 236)), (1, (20, 92, 190))]
ELMO_SPARK = [(200, 250, 255, 255), (96, 204, 248, 255)]


def _necro_part(pixel):
    """Partes del Necromancer (9): túnica (casi negra), cara (piel) o claro (calavera, manos, botas, ribete)."""
    r, g, b, a = pixel
    if a == 0:
        return None
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if 0.03 < h < 0.13 and s > 0.3 and v > 0.35:
        return "skin"
    return "light" if v >= 0.3 and h < 0.5 else "robe"            # el brillo violeta de la capucha es túnica


def recolor_tide_priest(pixel):
    """Necromancer -> Tide Priest: túnica negra -> verde mar profundo, piel -> pálida de ahogado,
    manos, botas y ribete grises -> bronce dorado."""
    part = _necro_part(pixel)
    if part is None:
        return pixel
    _h, _s, v = hsv(pixel)
    if part == "skin":
        return gradient(TIDE_SKIN, (v - 0.35) / 0.65) + (255,)
    if part == "light":
        return gradient(TIDE_GOLD, (v - 0.3) / 0.6) + (255,)
    return gradient(TIDE_ROBE, (v / 0.3) ** 0.8) + (255,)


def tide_priest_details(original, recolored):
    """Rasgos del Tide Priest sobre cada cuadro 32x32 (criatura 1x1).

    - Fuego de San Telmo: la calavera que lleva el Necromancer (el grupo claro más grande del
      cuadro) pasa a ser una bola de fuego celeste, con el centro blanco, que late con la animación.
    - Resplandor: la túnica cerca de la bola se aclara hacia el celeste.
    - Lengua de fuego: 2 o 3 píxeles sobre la bola, que se inclinan distinto en cada cuadro.
    - Chispas: tres chispas giran alrededor de la bola y cambian de lugar en cada cuadro.
    - Ojos: la cara lleva ojos celestes que brillan, dos de frente y uno mirando al este. De
      espaldas y mirando al oeste no se ve la cara."""
    w = 32
    out = []
    for index, (orig, new) in enumerate(zip(original, recolored)):
        anim, direction = index // 4, index % 4
        new = list(new)
        parts = [_necro_part(p) for p in orig]
        groups = _clusters(part_points(parts, "light", w))
        if groups:
            cx, cy = centroid(max(groups, key=len))                             # la calavera
            radius = (2.6, 3.1, 2.8)[anim]
            for y in range(w):
                for x in range(w):
                    d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                    i = y * w + x
                    if d <= radius:
                        new[i] = gradient(ELMO_FIRE, (d / radius) ** 1.3) + (255,)
                    elif d <= radius + 3 and parts[i] is not None:             # resplandor sobre el cuerpo
                        k = (1 - (d - radius) / 3) * 0.55
                        new[i] = tuple(int(c + (g - c) * k) for c, g in zip(new[i][:3], (60, 190, 240))) + (255,)
            tip = round(cx + (0, 1, -1)[anim]), round(cy - radius)              # lengua de fuego que se mueve
            length = (2, 3, 2)[anim]
            for k in range(length):
                x, y = tip[0] + (k * (1, -1, 1)[anim]) // 2, tip[1] - 1 - k
                if 0 <= x < w and 0 <= y < w:
                    new[y * w + x] = (44, 168, 236, 255) if k == length - 1 else (150, 244, 255, 255)
            for n in range(3):                                                   # chispas
                angle = 2.1 * n + 0.9 * anim + direction
                r = radius + 2.2 + (n + anim) % 2
                x, y = round(cx + math.cos(angle) * r), round(cy + math.sin(angle) * r)
                if 0 <= x < w and 0 <= y < w:
                    new[y * w + x] = ELMO_SPARK[(n + anim) % 2]
        faces = [c for c in _clusters(part_points(parts, "skin", w)) if len(c) >= 6]
        if faces and direction in (1, 2):
            f = max(faces, key=len)
            ys = sorted({y for _x, y in f})
            row = ys[len(ys) // 3]                                               # un tercio desde arriba
            xs = sorted(x for x, y in f if y == row)
            eyes = [xs[0] + 1, xs[-1] - 1] if direction == 2 and len(xs) >= 5 else [xs[-1] if direction == 1 else xs[0]]
            for x in eyes:
                new[row * w + x] = (170, 250, 255, 255)
        out.append(new)
    return out


ICE_DARK = [(0, (12, 18, 34)), (0.3, (30, 50, 85)), (0.6, (60, 95, 145)),
            (0.85, (105, 150, 200)), (1, (170, 205, 235))]
ICE_HOT = [(0, (30, 70, 110)), (0.3, (60, 130, 180)), (0.6, (110, 190, 225)),
           (0.8, (175, 225, 245)), (1, (245, 255, 255))]


def recolor_ice(pixel):
    r, g, b, a = pixel
    if a == 0:
        return pixel
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    lum = (0.30 * r + 0.59 * g + 0.11 * b) / 255
    if 0.25 < h < 0.48 and s > 0.35:                         # ojos verdes -> cian blanco
        return (220, 255, 255, 255)
    if 0.10 < h < 0.20 and s > 0.55 and v > 0.55:            # articulaciones amarillas -> hielo
        return gradient(ICE_HOT, 0.55 + 0.45 * lum) + (255,)
    if (h < 0.045 or h > 0.96) and s > 0.6:                  # rayas rojas -> hielo
        return gradient(ICE_HOT, 0.35 + 0.65 * lum) + (255,)
    if 0.03 < h < 0.14 and s > 0.35:                         # cuerpo marrón -> azul acero
        return gradient(ICE_DARK, lum ** 0.85) + (255,)
    if h > 0.5 and s > 0.3:                                  # sombras azules -> azul acero
        return gradient(ICE_DARK, lum * 0.9) + (255,)
    k = lum ** 0.85
    return (int(15 + 80 * k), int(25 + 100 * k), int(45 + 150 * k), 255)


CARD4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


# Un preset = criatura base (source), looktype vacío de destino (target), paleta por píxel (recolor) y,
# opcionales, el retoque por cuadro (frames_post) y el clasificador de partes del base (parts), que
# sprite_tool.py usa para mostrar el mapa de partes. Guía: docs/gameplay/SPRITE_RECOLOR_GUIDE.md.
PRESETS = {
    "black-dragon": dict(source=34, target=230, recolor=recolor_black, name="Black Dragon"),
    "frost-dragon": dict(source=34, target=231, recolor=recolor_frost, name="Frost Dragon"),
    "ice-monk": dict(source=57, target=232, recolor=recolor_ice_monk, name="Ice Monk", frames_post=ice_monk_eyes),
    "drowned-sailor": dict(source=100, target=233, recolor=recolor_drowned, name="Drowned Sailor",
                           frames_post=drowned_sailor_details, parts=_shambler_part),
    "tide-priest": dict(source=9, target=234, recolor=recolor_tide_priest, name="Tide Priest",
                        frames_post=tide_priest_details, parts=_necro_part),
    "ice-spider": dict(source=38, target=235, recolor=recolor_ice, name="Ice Spider"),
}


def frames_2x2(decoded: dict[int, list]) -> list[list]:
    """Cuadros 64x64 en orden anim -> dirección; tiles 2x2 empezando por abajo-derecha."""
    frames = []
    for anim in range(3):
        for direction in range(4):
            frame = [(0, 0, 0, 0)] * (64 * 64)
            base = (anim * 4 + direction) * 4
            for tile in range(4):
                ox, oy = (1 - tile % 2) * 32, (1 - tile // 2) * 32
                for i, p in enumerate(decoded[base + tile]):
                    if p[3]:
                        frame[(oy + i // 32) * 64 + ox + i % 32] = p
            frames.append(frame)
    return frames


def split_2x2(frames: list[list]) -> dict[int, list]:
    """Inverso de frames_2x2: vuelve a los 48 sprites de 32x32 en el orden del .dat."""
    decoded = {}
    for anim in range(3):
        for direction in range(4):
            frame = frames[anim * 4 + direction]
            base = (anim * 4 + direction) * 4
            for tile in range(4):
                ox, oy = (1 - tile % 2) * 32, (1 - tile // 2) * 32
                decoded[base + tile] = [frame[(oy + i // 32) * 64 + ox + i % 32] for i in range(1024)]
    return decoded


def load_things(things_dir: Path) -> dict:
    """Lee Tibia.dat / Tibia.spr de una carpeta: bytes, looktypes y tabla de sprites."""
    dat_path, spr_path = things_dir / "Tibia.dat", things_dir / "Tibia.spr"
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    outfits, counts = read_outfits(dat)
    spr_count, offsets = read_spr(spr)
    return dict(dat_path=dat_path, spr_path=spr_path, dat=dat, spr=spr, outfits=outfits, counts=counts,
                spr_count=spr_count, offsets=offsets)


def look_frames(things: dict, look: int) -> tuple[list[list], int]:
    """Los 12 cuadros de un looktype (índice = anim * 4 + dirección) y su lado en píxeles:
    32 si la criatura es 1x1 (12 sprites) o 64 si es 2x2 (48 sprites)."""
    ids = things["outfits"][look - 1]["ids"]
    if len(ids) not in (12, 48):
        raise SystemExit(f"Look {look}: se espera una criatura 1x1 o 2x2 con 4 direcciones y 3 cuadros "
                         f"(12 o 48 sprites); tiene {len(ids)}")
    decoded = {i: decode_sprite(things["spr"], things["offsets"], sid) for i, sid in enumerate(ids)}
    return (frames_2x2(decoded), 64) if len(ids) == 48 else ([decoded[i] for i in range(12)], 32)


def build_preset(things: dict, p: dict) -> tuple[list[list], list[list], int]:
    """Cuadros del base, cuadros nuevos (paleta + retoque por cuadro) y lado del cuadro."""
    original, size = look_frames(things, p["source"])
    new = [[p["recolor"](px) for px in frame] for frame in original]
    if p.get("frames_post"):                      # retoque por cuadro completo (ej. ojos del Ice Monk)
        new = p["frames_post"](original, new)
    return original, new, size


def frames_to_sprites(frames: list[list], size: int) -> dict[int, list]:
    """Cuadros -> sprites de 32x32 en el orden del .dat."""
    return split_2x2(frames) if size == 64 else dict(enumerate(frames))


def sprite_record(spr: bytes, offsets: list[int], sprite_id: int) -> bytes:
    """Bytes tal cual de un sprite en el .spr (vacío si el id no tiene datos)."""
    off = offsets[sprite_id - 1] if 0 < sprite_id <= len(offsets) else 0
    if not off:
        return b""
    return spr[off:off + 5 + struct.unpack_from("<H", spr, off + 3)[0]]


def replace_sprites(spr: bytes, offsets: list[int], replacements: dict[int, bytes]) -> bytes:
    """Reescribe el .spr cambiando solo los sprites de `replacements` (id -> registro nuevo).
    Los demás quedan byte a byte iguales y en el mismo orden; solo se corren los offsets."""
    order = sorted((off, sid) for sid, off in enumerate(offsets, 1) if off)
    missing = [sid for sid in replacements if not offsets[sid - 1]]
    if missing:
        raise SystemExit(f"Sprites sin datos, no se pueden reemplazar: {missing}")
    start = 6 + 4 * len(offsets)
    if order and order[0][0] != start:
        raise SystemExit("Tibia.spr con formato inesperado: los sprites no empiezan después de la tabla")
    body, new_offsets = bytearray(), [0] * len(offsets)
    for off, sid in order:
        new_offsets[sid - 1] = start + len(body)
        body += replacements.get(sid) or sprite_record(spr, offsets, sid)
    return spr[:6] + struct.pack(f"<{len(offsets)}I", *new_offsets) + bytes(body)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("things_dir", type=Path, nargs="?")
    ap.add_argument("--preset", choices=sorted(PRESETS), required=True)
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--replace", action="store_true",
                    help="si el looktype destino ya existe, rehacer sus sprites con el preset actual")
    a = ap.parse_args()
    p = PRESETS[a.preset]

    things = load_things(a.things_dir or RME_THINGS)
    dat, spr, offsets, spr_count = things["dat"], things["spr"], things["offsets"], things["spr_count"]
    if things["counts"][1] < p["target"]:
        raise SystemExit(f"El dat tiene {things['counts'][1]} looktypes; se esperaba al menos {p['target']}")
    source, target = things["outfits"][p["source"] - 1], things["outfits"][p["target"] - 1]
    _original, frames, size = build_preset(things, p)
    decoded = frames_to_sprites(frames, size)

    if a.preview:
        write_preview(a.preview, frames, scale=3 if size == 64 else 6, size=size)
        print(f"Vista previa: {a.preview}")
    if a.things_dir is None:
        return 0

    new_records = [encode_sprite(decoded[i]) for i in range(len(source["ids"]))]
    if any(target["ids"]):
        if not a.replace:
            print(f"El looktype {p['target']} ya tiene sprites; no se cambia nada "
                  f"(--replace los rehace con el preset actual).")
            return 0
        new_ids = target["ids"]
        if len(new_ids) != len(new_records) or not all(new_ids):
            raise SystemExit(f"El looktype {p['target']} no tiene la forma del base {p['source']}; no se reemplaza")
        new_dat = dat
        new_spr = replace_sprites(spr, offsets, dict(zip(new_ids, new_records)))
        if new_spr == spr:
            print(f"El looktype {p['target']} ya es igual al preset; no se cambia nada.")
            return 0
        done = f"sprites {new_ids[0]}-{new_ids[-1]} rehechos"
    else:
        new_ids = [spr_count + 1 + i for i in range(len(new_records))]
        entry = dat[source["start"]:source["sprite_pos"]] + struct.pack(f"<{len(new_ids)}H", *new_ids)
        new_dat = dat[:target["start"]] + entry + dat[target["end"]:]
        new_spr = write_spr(struct.unpack_from("<I", spr, 0)[0], offsets, spr, new_records)
        done = f"sprites {new_ids[0]}-{new_ids[-1]} agregados ({spr_count} -> {spr_count + len(new_records)})"

    check, _ = read_outfits(new_dat)
    assert check[p["target"] - 1]["ids"] == new_ids
    _c, new_offsets = read_spr(new_spr)
    assert all(decode_sprite(new_spr, new_offsets, sid) == decoded[i] for i, sid in enumerate(new_ids))

    for path, data, before in ((things["dat_path"], new_dat, dat), (things["spr_path"], new_spr, spr)):
        if data == before:
            continue
        backup = path.with_name(f"{path.name}.bak-{a.preset}")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_bytes(data)
    print(f"Looktype {p['target']} = {p['name']}; {done}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
