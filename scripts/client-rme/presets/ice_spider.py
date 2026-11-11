"""Ice Spider: Giant Spider (38, 2x2) -> look 235. Cuerpo azul acero oscuro, patas celeste y blanco,
ojos cian. Doc: docs/gameplay/ICE_SPIDER.md.
"""
from sprite_kit import *  # noqa: F401,F403


ICE_DARK = [(0, (12, 18, 34)), (0.3, (30, 50, 85)), (0.6, (60, 95, 145)),
            (0.85, (105, 150, 200)), (1, (170, 205, 235))]
ICE_HOT = [(0, (30, 70, 110)), (0.3, (60, 130, 180)), (0.6, (110, 190, 225)),
           (0.8, (175, 225, 245)), (1, (245, 255, 255))]


def recolor_ice(pixel):
    r, g, b, a = pixel
    if a == 0:
        return pixel
    h, s, v = hsv(pixel)
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


PRESET = dict(name="Ice Spider", source=38, target=235, recolor=recolor_ice)
