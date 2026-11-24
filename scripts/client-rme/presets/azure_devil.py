"""Azure Devil: Fire Devil (40) -> look 146. Cuerpo índigo, brillos y ojos cian.

Creado con `sprite_tool.py new`. Receta: docs/gameplay/SPRITE_RECOLOR_GUIDE.md.
Doc del monstruo: docs/items-and-map/CALDERA_AZUL.md.
"""
from sprite_kit import *  # noqa: F401,F403

# Partes del base, por familia de color (h, s, v de 0 a 1). Gana la primera regla que se cumple.
# Es un primer corte automático: ajustar o separar partes mirando `sprite_tool.py inspect azure-devil`.
parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("red", lambda h, s, v: v >= 0.13 and s >= 0.18 and (h < 0.04 or h >= 0.95)),
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("rest", None),
)

# Colores nuevos de cada parte, de oscuro a claro (3 a 5 colores). Una parte comentada queda igual que
# en el base. `(paleta, 0.8)` aclara y `(paleta, 1.2)` oscurece; un solo color `(r, g, b)` la pinta pareja.
# Al lado de cada parte: sus colores de hoy (oscuro, medio, claro) y cuánto ocupa del base.
palettes = {
    "red": [(10, 6, 46), (40, 30, 140), (90, 120, 255)],
    "dark": [(0, 0, 0), (4, 3, 14), (12, 10, 36)],
    "orange": [(14, 40, 80), (40, 170, 255), (190, 245, 255)],
    "rest": [(20, 20, 40), (60, 160, 220), (200, 250, 255)],
}


def detail(f):
    """Rasgo propio, cuadro por cuadro. f.anim 0-2 (0 quieto), f.direction 0 norte, 1 este, 2 sur, 3 oeste.
    f.w = 32. Pintar sobre f.px con f.set / f.fill / f.orb / f.glow / f.eyes / f.hang (sprite_kit.Frame)."""
    # Ejemplo: el grupo más grande de una parte es un objeto o la cara.
    # obj = f.biggest("rest")
    # if obj:
    #     cx, cy = centroid(obj)
    #     f.orb(cx, cy, (2.6, 3.1, 2.8)[f.anim], [(255, 255, 255), (150, 240, 255), (20, 90, 190)])
    #     f.glow(cx, cy, 3, 3, (60, 190, 240))


PRESET = dict(name="Azure Devil", source=40, target=146, parts=parts, palettes=palettes, detail=detail)
