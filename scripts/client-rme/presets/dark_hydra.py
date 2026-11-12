"""Dark Hydra: Hydra (121, 2x2) -> look 241. Escamas de carbon con luces violetas,
ojos fucsia y marcas arcanas en los cuellos. Doc: docs/gameplay/DARK_HYDRA.md.
"""
from sprite_kit import *  # noqa: F401,F403

parts = BASE_PARTS[121]
palettes = {
    "outline": [(4, 3, 9), (13, 10, 24), (25, 18, 39)],
    "scales": [(16, 14, 27), (38, 30, 58), (73, 55, 101), (124, 101, 153), (175, 157, 195)],
    "eyes": (255, 100, 210),
    "claws": [(72, 59, 84), (167, 151, 175), (235, 223, 225)],
}


def detail(f):
    """Chevrones luminosos bajo cada cabeza, anclados a sus ojos originales."""
    for eye in f.groups("eyes", min_size=1):
        cx, cy = (round(v) for v in centroid(eye))
        f.glow(cx, cy, 1, 2, (177, 46, 155))
        for dx, dy in ((-3, -6), (-2, -5), (-1, -4), (0, -3), (1, -4), (2, -5), (3, -6)):
            x, y = cx + dx, cy + dy
            if f.opaque(x, y) and f.parts[y * f.w + x] == "scales":
                f.set(x, y, (194, 110, 224))


PRESET = dict(name="Dark Hydra", source=121, target=241, parts=parts, palettes=palettes, detail=detail)
