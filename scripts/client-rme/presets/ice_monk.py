"""Ice Monk: Monk (57, guardado 2x2) -> look 232. Túnica azul profundo a blanco hielo, cinturón celeste
brillante y la cara en sombra bajo la capucha con ojos celestes. Doc: docs/gameplay/ICE_MONK.md.

`ice_monk_eyes` usa ancho 64 fijo: solo sirve para bases 2x2. En código nuevo, `f.w` o `f.eyes(...)`.
"""
from sprite_kit import *  # noqa: F401,F403


ICE_ROBE = [(0, (6, 10, 28)), (0.2, (18, 38, 88)), (0.45, (40, 88, 166)),
            (0.7, (110, 172, 228)), (0.9, (200, 232, 250)), (1, (245, 252, 255))]
ICE_SKIN = [(0, (70, 96, 120)), (0.55, (190, 214, 228)), (1, (240, 248, 252))]


def recolor_ice_monk(pixel):
    """Monk (57): túnica marrón -> azul profundo a blanco hielo, piel -> celeste pálido helado,
    cinturón dorado -> celeste brillante (parece que brilla)."""
    r, g, b, a = pixel
    if a == 0:
        return pixel
    h, s, v = hsv(pixel)
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
    h, s, v = hsv(pixel)
    return 0.06 <= h <= 0.10 and 0.28 <= s <= 0.47 and v > 0.74


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
        faces = [c for c in clusters(skin) if len(c) >= 6]
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


PRESET = dict(name="Ice Monk", source=57, target=232, recolor=recolor_ice_monk, frames_post=ice_monk_eyes,
              parts=monk_part)
