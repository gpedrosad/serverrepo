"""Hellhound: War Wolf (3) -> look 238. Pelaje de carbón con luces de brasa y ojos que arden.
Doc: docs/gameplay/HELL_QUEST.md.
"""
from sprite_kit import *  # noqa: F401,F403


HELLHOUND_FUR = [(0, (8, 4, 6)), (0.3, (34, 14, 14)), (0.55, (92, 26, 16)), (0.75, (196, 70, 20)),
                 (0.9, (250, 150, 40)), (1, (255, 228, 140))]


def recolor_hellhound(pixel):
    """War Wolf (3) -> Hellhound: pelaje de carbón con las luces como brasas y ojos que arden."""
    r, g, b, a = pixel
    if a == 0:
        return pixel
    h, s, v = hsv(pixel)
    if s > 0.3 and 0.1 <= h <= 0.2 and v > 0.45:                 # ojos amarillos
        return (255, 236, 120, 255)
    lum = luma(pixel)
    if lum < 0.12:                                               # contorno
        return (6, 2, 4, 255)
    return gradient(HELLHOUND_FUR, ((lum - 0.12) / 0.82) ** 1.7) + (255,)


PRESET = dict(name="Hellhound", source=3, target=238, recolor=recolor_hellhound)
