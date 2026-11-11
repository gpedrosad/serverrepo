"""Frost Dragon: Dragon (34) -> look 231. Cuerpo azul acero a blanco, panza y alas blanco hielo,
ojos celestes brillantes. Doc: docs/gameplay/FROST_DRAGON.md.
"""
from sprite_kit import *  # noqa: F401,F403


FROST_BODY = [(0, (10, 16, 40)), (0.22, (36, 64, 120)), (0.45, (92, 142, 206)),
              (0.72, (176, 210, 240)), (1, (248, 252, 255))]
FROST_PALE = [(0, (26, 46, 82)), (0.35, (118, 174, 216)), (0.7, (196, 232, 246)), (1, (252, 255, 255))]


def recolor_frost(pixel):
    r, g, b, a = pixel
    if a == 0:
        return pixel
    h, s, v = hsv(pixel)
    if (h < 0.09 or h > 0.95) and s > 0.6 and v > 0.5:      # ojos, lengua, garras rojas
        return (120, 245, 255, 255)
    lum = (0.30 * r + 0.59 * g + 0.11 * b) / 255
    if 0.06 < h < 0.2 and s > 0.35:                          # panza y membranas (amarillo/naranja)
        return gradient(FROST_PALE, (lum ** 0.75) * 1.15) + (255,)
    return gradient(FROST_BODY, (lum ** 0.7) * 1.25) + (255,)  # cuerpo verde -> hielo


PRESET = dict(name="Frost Dragon", source=34, target=231, recolor=recolor_frost)
