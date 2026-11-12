"""The Fallen Emperor: Lich (99) -> look 244, jefe del Castillo Imperial. Túnica negra a morado imperial,
la armadura naranja a oro brillante y la serpiente verde del báculo a violeta que brilla. El pelo blanco y
la calavera quedan igual. Doc: docs/gameplay/IMPERIAL_CASTLE.md.
"""
from sprite_kit import *  # noqa: F401,F403


IMPERIAL_ROBE = [(0, (12, 2, 26)), (0.45, (58, 20, 108)), (0.8, (104, 52, 170)), (1, (150, 96, 214))]
GOLD = [(0, (70, 40, 0)), (0.45, (206, 150, 26)), (0.8, (250, 214, 84)), (1, (255, 244, 170))]
VIOLET_GLOW = [(0, (44, 0, 70)), (0.5, (176, 44, 226)), (1, (244, 180, 255))]


def recolor_fallen_emperor(pixel):
    """Negro y gris oscuro de la túnica -> morado; naranja -> oro; verde (serpiente) -> violeta brillante."""
    r, g, b, a = pixel
    if a == 0:
        return pixel
    h, s, v = hsv(pixel)
    if 0.22 <= h <= 0.45 and s > 0.3:                            # serpiente del báculo
        return gradient(VIOLET_GLOW, v) + (255,)
    if 0.045 <= h <= 0.15 and s > 0.45:                          # armadura naranja
        return gradient(GOLD, v) + (255,)
    if 0.09 <= v < 0.42 and s < 0.4:                             # túnica (el contorno casi negro queda)
        return gradient(IMPERIAL_ROBE, (v - 0.09) / 0.33) + (255,)
    return pixel


PRESET = dict(name="The Fallen Emperor", source=99, target=244, recolor=recolor_fallen_emperor)
