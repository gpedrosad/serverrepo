"""Tide Priest: Necromancer (9) -> look 234. Túnica verde mar con ribete de bronce, cara en sombra con
ojos celestes y, en vez de la calavera, una bola de fuego de San Telmo que late.
Doc: docs/gameplay/TIDE_PRIEST.md.
"""
from sprite_kit import *  # noqa: F401,F403


TIDE_ROBE = [(0, (2, 10, 14)), (0.3, (8, 40, 46)), (0.6, (20, 84, 86)), (0.85, (52, 136, 124)), (1, (120, 196, 172))]
TIDE_SKIN = [(0, (16, 30, 40)), (0.6, (70, 104, 116)), (1, (132, 168, 170))]
TIDE_GOLD = [(0, (58, 38, 10)), (0.45, (150, 108, 34)), (0.8, (226, 186, 84)), (1, (255, 240, 170))]
ELMO_FIRE = [(0, (250, 255, 255)), (0.45, (150, 244, 255)), (0.8, (44, 168, 236)), (1, (20, 92, 190))]
ELMO_SPARK = [(200, 250, 255, 255), (96, 204, 248, 255)]


def recolor_tide_priest(pixel):
    """Necromancer -> Tide Priest: túnica negra -> verde mar profundo, piel -> pálida de ahogado,
    manos, botas y ribete grises -> bronce dorado."""
    part = necromancer_part(pixel)
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
        parts = [necromancer_part(p) for p in orig]
        groups = clusters(part_points(parts, "light", w))
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
        faces = [c for c in clusters(part_points(parts, "skin", w)) if len(c) >= 6]
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


PRESET = dict(name="Tide Priest", source=9, target=234, recolor=recolor_tide_priest,
              frames_post=tide_priest_details, parts=necromancer_part)
