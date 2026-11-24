"""Azure Lich: Angry Lich, Enraged Lich, Furious Lich, Lich (99) -> look 148. Ribetes dorados a azul pervinca, la magia verde a cian, huesos gris lavanda.

Creado con `sprite_tool.py new`. Receta: docs/gameplay/SPRITE_RECOLOR_GUIDE.md.
Doc del monstruo: docs/items-and-map/CALDERA_AZUL.md.
"""
from sprite_kit import *  # noqa: F401,F403

# Partes del base, por familia de color (h, s, v de 0 a 1). Gana la primera regla que se cumple.
# Es un primer corte automático: ajustar o separar partes mirando `sprite_tool.py inspect azure-lich`.
parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("gray", lambda h, s, v: v >= 0.13 and s < 0.18),
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("yellow", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.11 <= h < 0.20),
    ("green", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.20 <= h < 0.45),
    ("rest", None),
)

# Colores nuevos de cada parte, de oscuro a claro (3 a 5 colores). Una parte comentada queda igual que
# en el base. `(paleta, 0.8)` aclara y `(paleta, 1.2)` oscurece; un solo color `(r, g, b)` la pinta pareja.
# Al lado de cada parte: sus colores de hoy (oscuro, medio, claro) y cuánto ocupa del base.
palettes = {
    "gray": [(30, 32, 58), (130, 140, 190), (240, 244, 255)],
    "orange": [(20, 22, 70), (60, 70, 170), (150, 170, 240)],
    "green": [(4, 40, 70), (20, 170, 240), (150, 245, 255)],
    "yellow": [(30, 30, 60), (90, 110, 170), (170, 230, 255)],
    "rest": [(0, 0, 40), (40, 20, 120), (160, 140, 255)],
}


def detail(f):
    """Rasgo propio, cuadro por cuadro. f.anim 0-2 (0 quieto), f.direction 0 norte, 1 este, 2 sur, 3 oeste.
    f.w = 64. Pintar sobre f.px con f.set / f.fill / f.orb / f.glow / f.eyes / f.hang (sprite_kit.Frame)."""
    # Ejemplo: el grupo más grande de una parte es un objeto o la cara.
    # obj = f.biggest("rest")
    # if obj:
    #     cx, cy = centroid(obj)
    #     f.orb(cx, cy, (2.6, 3.1, 2.8)[f.anim], [(255, 255, 255), (150, 240, 255), (20, 90, 190)])
    #     f.glow(cx, cy, 3, 3, (60, 190, 240))


PRESET = dict(name="Azure Lich", source=99, target=148, parts=parts, palettes=palettes, detail=detail)
