"""Azure Bonebeast: Bone Beast (101) -> look 147. Huesos gris azulado; las vetas ocres pasan a brasas cian y el ojo rojo a cian.

Creado con `sprite_tool.py new`. Receta: docs/gameplay/SPRITE_RECOLOR_GUIDE.md.
Doc del monstruo: docs/items-and-map/CALDERA_AZUL.md.
"""
from sprite_kit import *  # noqa: F401,F403

# Partes del base, por familia de color (h, s, v de 0 a 1). Gana la primera regla que se cumple.
# Es un primer corte automático: ajustar o separar partes mirando `sprite_tool.py inspect azure-bonebeast`.
parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("gray", lambda h, s, v: v >= 0.13 and s < 0.18),
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("rest", None),
)

# Colores nuevos de cada parte, de oscuro a claro (3 a 5 colores). Una parte comentada queda igual que
# en el base. `(paleta, 0.8)` aclara y `(paleta, 1.2)` oscurece; un solo color `(r, g, b)` la pinta pareja.
# Al lado de cada parte: sus colores de hoy (oscuro, medio, claro) y cuánto ocupa del base.
palettes = {
    "gray": [(22, 28, 72), (112, 144, 214), (210, 230, 255)],
    "orange": [(16, 40, 70), (50, 150, 230), (170, 240, 255)],
    "rest": [(4, 30, 70), (40, 200, 255), (200, 255, 255)],
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


PRESET = dict(name="Azure Bonebeast", source=101, target=147, parts=parts, palettes=palettes, detail=detail)
