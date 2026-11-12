"""Emerald Scarab: Ancient Scarab (79, 2x2) -> look 242. Caparazon esmeralda,
patas de bronce y gema facetada con marco dorado en el lomo. Doc: docs/gameplay/EMERALD_SCARAB.md.
"""
from sprite_kit import *  # noqa: F401,F403

parts = BASE_PARTS[79]
palettes = {
    "outline": [(1, 7, 5), (5, 17, 12), (13, 31, 20)],
    "shell": [(7, 38, 27), (12, 88, 59), (31, 149, 99), (85, 210, 146), (193, 249, 206)],
    "legs": [(38, 25, 9), (99, 69, 22), (170, 129, 48), (231, 197, 101)],
    "eyes": (245, 244, 143),
}


def detail(f):
    """Rombo de 7x9 sobre el caparazon superior, sin pintar fuera de la criatura."""
    shell = f.points("shell")
    top = min(y for x, y in shell)
    back = f.thick([(x, y) for x, y in shell if y < top + 19])
    if not back:
        return
    cx, cy = (round(v) for v in centroid(back))
    for dy in range(-4, 5):
        for dx in range(-3, 4):
            edge = abs(dx) * 4 + abs(dy) * 3
            if edge > 12 or not f.opaque(cx + dx, cy + dy):
                continue
            color = (227, 186, 75) if edge >= 9 else ((187, 255, 220) if dx <= 0 else (25, 160, 112))
            f.set(cx + dx, cy + dy, color)


PRESET = dict(name="Emerald Scarab", source=79, target=242, parts=parts, palettes=palettes, detail=detail)
