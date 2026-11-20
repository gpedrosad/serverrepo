"""Metal Demon: Demon (35, 2x2) -> look 188. Demonio cyborg: blindaje de acero negro, cuernos, alas y garras
cromados, las llamas pasan a plasma rojo que late, luces de la piel a brillo metálico y juntas con luces rojas.
Doc: docs/gameplay/METAL_MONSTERS.md.
"""
from sprite_kit import *  # noqa: F401,F403

parts = parts_by_rules(
    ("outline", lambda h, s, v: v < 0.16),
    ("plasma", lambda h, s, v: 0.11 <= h <= 0.33 and s > 0.3),                  # fuego y ojos
    ("chrome", lambda h, s, v: 0.04 <= h < 0.11 and s > 0.2),                    # cuernos, alas, garras
    ("seams", lambda h, s, v: (h < 0.04 or h > 0.9) and s > 0.45 and v > 0.86),  # luces de la piel
    ("armor", None),
)

palettes = {
    "outline": [(3, 3, 5), (10, 10, 14)],
    "armor": ([(10, 10, 14), (30, 31, 38), (62, 64, 74), (116, 120, 134), (196, 202, 214)], 1.1),
    "chrome": [(26, 28, 34), (90, 96, 108), (176, 184, 196), (246, 248, 252)],
    "plasma": [(110, 0, 10), (230, 20, 30), (255, 110, 90), (255, 220, 210)],
    "seams": [(150, 156, 170), (232, 236, 244)],
}


def detail(f):
    """Juntas de placas en el blindaje con luces de neón rojo en los cruces; el plasma late."""
    for x, y in f.thick(f.points("armor")):
        if (x + 2 * y) % 12 == 0:
            f.set(x, y, (255, 40, 40) if (2 * x - y) % 12 == 0 else (8, 8, 12))
    hot = (255, 236, 230) if f.anim == 1 else (255, 170, 150)
    for x, y in f.thick(f.points("plasma")):
        if luma(f.orig[y * f.w + x]) > 0.55:
            f.set(x, y, hot)


PRESET = dict(name="Metal Demon", source=35, target=188, parts=parts, palettes=palettes, detail=detail)
