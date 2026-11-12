"""Imperial Hero: Hero (73) -> look 240. Guardia de élite del Castillo Imperial: capa y pañuelo morado
imperial, cota plateada en vez de la túnica beige y pantalón violeta oscuro. Pelo, piel y botas quedan igual.
Doc: docs/gameplay/IMPERIAL_CASTLE.md.
"""
from sprite_kit import *  # noqa: F401,F403


ROYAL_PURPLE = [(0, (14, 4, 34)), (0.35, (58, 20, 128)), (0.65, (120, 52, 214)), (0.88, (178, 120, 255)), (1, (228, 200, 255))]
SILVER = [(0, (34, 42, 60)), (0.4, (104, 120, 146)), (0.7, (172, 188, 210)), (0.9, (222, 232, 244)), (1, (250, 252, 255))]
DARK_VIOLET = [(0, (8, 4, 18)), (0.5, (34, 18, 62)), (1, (80, 54, 128))]


def recolor_imperial_hero(pixel):
    """Rojo (capa, pañuelo) -> morado imperial; beige de la túnica -> plata; verde azulado del pantalón -> violeta oscuro."""
    r, g, b, a = pixel
    if a == 0:
        return pixel
    h, s, v = hsv(pixel)
    if (h < 0.035 or h > 0.93) and s > 0.45:                     # capa y pañuelo
        return gradient(ROYAL_PURPLE, min(1.0, v * 1.3)) + (255,)
    if 0.45 <= h <= 0.66 and s > 0.2:                            # pantalón
        return gradient(DARK_VIOLET, v * 1.25) + (255,)
    if 0.085 <= h <= 0.15 and s < 0.44 and 0.3 < v < 0.86:       # túnica beige
        return gradient(SILVER, (v - 0.3) / 0.5) + (255,)
    return pixel


PRESET = dict(name="Imperial Hero", source=73, target=240, recolor=recolor_imperial_hero)
