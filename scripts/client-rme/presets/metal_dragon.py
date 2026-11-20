"""Metal Dragon: Dragon (34, 2x2) -> look 186. Dragón cyborg: cuerpo de acero pavonado con placas y remaches
cromados, panza de neón celeste que late, garras cromadas y óptica roja.
Doc: docs/gameplay/METAL_MONSTERS.md.
"""
from sprite_kit import *  # noqa: F401,F403

parts = parts_by_rules(
    ("eyes", lambda h, s, v: (h < 0.045 or h > 0.95) and s > 0.6 and v > 0.5),  # ojos y lengua
    ("claws", lambda h, s, v: 0.045 <= h < 0.09 and s > 0.6 and v > 0.5),         # garras
    ("outline", lambda h, s, v: v < 0.13),
    ("membrane", lambda h, s, v: 0.06 < h < 0.2 and s > 0.35),                   # panza y alas
    ("body", None),
)

palettes = {
    "outline": [(3, 4, 7), (10, 12, 18)],
    "body": ([(10, 12, 16), (30, 34, 42), (62, 68, 80), (120, 130, 146), (214, 222, 234)], 1.15),
    "membrane": [(0, 60, 84), (0, 160, 210), (60, 225, 255), (190, 252, 255)],
    "claws": [(60, 66, 76), (170, 178, 190), (240, 244, 250)],
    "eyes": (255, 46, 40),
}

def detail(f):
    """Juntas de placas en el cuerpo, panza de neón que late y halo rojo en la óptica."""
    for x, y in f.thick(f.points("body")):
        if (x + 2 * y) % 11 == 0:
            f.set(x, y, (8, 10, 14))
    for x, y in f.points("membrane"):
        if (x + y) % 4 == f.anim:
            f.set(x, y, (210, 255, 255))
    for eye in f.groups("eyes", min_size=1):
        cx, cy = (round(v) for v in centroid(eye))
        f.glow(cx, cy, 1, 2, (255, 60, 40), 0.45)


PRESET = dict(name="Metal Dragon", source=34, target=186, parts=parts, palettes=palettes, detail=detail)
