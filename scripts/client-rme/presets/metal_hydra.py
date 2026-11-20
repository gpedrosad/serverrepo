"""Metal Hydra: Hydra (121, 2x2) -> look 187. Hidra cyborg: escamas de acero oscuro con juntas de placas,
cuellos con anillos de neón verde ácido, colmillos cromados y ópticas rojas.
Doc: docs/gameplay/METAL_MONSTERS.md.
"""
from sprite_kit import *  # noqa: F401,F403

parts = BASE_PARTS[121]
palettes = {
    "outline": [(3, 4, 6), (9, 12, 12), (16, 20, 20)],
    "scales": ([(10, 12, 14), (28, 33, 36), (60, 68, 72), (116, 126, 130), (200, 210, 212)], 1.15),
    "eyes": (255, 40, 30),
    "claws": [(70, 76, 84), (168, 176, 186), (240, 244, 250)],
}

NEON = [(0, (16, 90, 10)), (0.5, (70, 230, 40)), (1, (200, 255, 150))]


def detail(f):
    """Anillos de neón en diagonal (siguen los cuellos), juntas de placas y halo rojo en cada óptica."""
    scales = f.thick(f.points("scales"))
    for x, y in scales:
        if (x + y) % 9 == 0:
            k = luma(f.orig[y * f.w + x])
            f.set(x, y, gradient(NEON, min(1.0, 0.35 + k * 1.3 + 0.15 * (f.anim == 1))))
        elif (x - y) % 10 == 0:
            f.set(x, y, (14, 16, 18))
    for eye in f.groups("eyes", min_size=1):
        cx, cy = (round(v) for v in centroid(eye))
        f.glow(cx, cy, 1, 2, (255, 50, 30), 0.5)


PRESET = dict(name="Metal Hydra", source=121, target=187, parts=parts, palettes=palettes, detail=detail)
