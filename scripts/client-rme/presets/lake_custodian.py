"""Custodio del Lago: Stone Golem (67) -> 229; piedra azul, nucleo y grietas de luz.
Doc: docs/gameplay/PETRIFIED_SANCTUARY.md. Los doce cuadros conservan la silueta de piedra.
"""
from sprite_kit import *  # noqa: F401,F403

parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("gray", lambda h, s, v: v >= 0.13 and s < 0.18),
    ("rest", None),
)
palettes = {
    "dark": [(6, 13, 19), (17, 28, 37), (32, 46, 57)],
    "gray": [(30, 44, 57), (66, 88, 108), (120, 148, 166), (207, 222, 224)],
    "rest": [(16, 41, 42), (45, 86, 80), (106, 145, 122)],
}
CORE = ((28, 24), (30, 27), (29, 28), (26, 27))


def detail(f):
    cx, cy = CORE[f.direction]
    cy += (0, -1, 0)[f.anim]
    # Ramificaciones quebradas; solo se pintan dentro de la piedra, sin lineas flotantes.
    for branch in (((0, 0), (-4, -5), (-3, -10), (-7, -13)),
                   ((0, 0), (5, 3), (5, 8), (10, 12)),
                   ((0, 0), (-5, 4), (-9, 4), (-12, 9))):
        for (ax, ay), (bx, by) in zip(branch, branch[1:]):
            n = max(abs(bx - ax), abs(by - ay))
            for k in range(n + 1):
                x = cx + round(ax + (bx - ax) * k / n)
                y = cy + round(ay + (by - ay) * k / n)
                if f.opaque(x, y):
                    f.set(x, y, (76, 220, 232))
                    if f.opaque(x + 1, y):
                        f.set(x + 1, y, (18, 88, 108))
    # Cavidad oscura y diamante luminoso: el nucleo late al caminar.
    radius = (3.4, 4.0, 3.7)[f.anim]
    f.glow(cx, cy, radius, 4, (42, 212, 228), strength=0.7)
    for dy in range(-6, 7):
        for dx in range(-5, 6):
            if abs(dx) / 5 + abs(dy) / 6 <= 1 and f.opaque(cx + dx, cy + dy):
                f.set(cx + dx, cy + dy, (9, 32, 46))
    for dy in range(-4, 5):
        for dx in range(-3, 4):
            d = abs(dx) + abs(dy) * 0.75
            if d <= radius and f.opaque(cx + dx, cy + dy):
                f.set(cx + dx, cy + dy, (220, 255, 250) if d < 1.7 else (59, 216, 233))


PRESET = dict(name="Custodio del Lago", source=67, target=229,
              parts=parts, palettes=palettes, detail=detail)
