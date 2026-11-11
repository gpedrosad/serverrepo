"""Ashen Lord: Demon (35, 2x2) -> look 239, boss de la Hell Quest. Piel de ceniza con grietas de magma,
cuernos y alas de obsidiana, fuego de lava. Doc: docs/gameplay/HELL_QUEST.md.
"""
from sprite_kit import *  # noqa: F401,F403


ASH_SKIN = [(0, (12, 10, 12)), (0.3, (46, 40, 42)), (0.6, (98, 90, 88)), (0.85, (150, 140, 132)), (1, (196, 186, 174))]
MAGMA = [(0, (120, 20, 0)), (0.5, (236, 96, 10)), (1, (255, 226, 110))]
OBSIDIAN_HORN = [(0, (8, 4, 12)), (0.5, (40, 24, 52)), (1, (110, 80, 130))]


def recolor_ashen_lord(pixel):
    """Demon (35) -> Ashen Lord: piel de ceniza, brillos de la piel como magma, cuernos y alas de
    obsidiana, lo amarillo y verde (fuego, ojos) a lava."""
    r, g, b, a = pixel
    if a == 0:
        return pixel
    h, s, v = hsv(pixel)
    lum = luma(pixel)
    if v < 0.16:
        return (8, 4, 6, 255)
    if 0.11 <= h <= 0.33 and s > 0.3:                            # amarillo y verde: fuego y ojos
        return gradient(MAGMA, 0.15 + 0.55 * v) + (255,)
    if 0.04 <= h < 0.11 and s > 0.2:                             # naranja/piel: cuernos, alas, garras
        return gradient(OBSIDIAN_HORN, v) + (255,)
    if (h < 0.04 or h > 0.9) and s > 0.45 and v > 0.86:          # luces de la piel roja: grietas de magma
        return gradient(MAGMA, (v - 0.86) / 0.14) + (255,)
    return gradient(ASH_SKIN, min(1.0, lum * 1.9)) + (255,)


PRESET = dict(name="Ashen Lord", source=35, target=239, recolor=recolor_ashen_lord)
