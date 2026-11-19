"""Orc Warchief (Orc Warlord recoloreado): armadura de hierro oscuro, pintura de guerra y ojos rojos.
Jefe de la torreta SO de Elvenbane: docs/items-and-map/ELVENBANE.md#jefes-de-las-cimas
"""
from sprite_kit import *  # noqa: F401,F403

# Partes del base, por familia de color (h, s, v de 0 a 1). Gana la primera regla que se cumple.
# Es un primer corte automático: ajustar o separar partes mirando `sprite_tool.py inspect orc-warchief`.
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
    "gray": [(20, 16, 18), (60, 44, 44), (120, 84, 78), (190, 150, 130)],    # armadura de hierro oscuro
    "green": [(20, 50, 10), (50, 100, 20), (110, 150, 40)],                  # piel verde oscura
    "yellow": [(100, 70, 0), (200, 150, 20), (255, 230, 100)],               # adornos dorados
    "orange": [(80, 0, 0), (170, 20, 10), (240, 80, 50)],                    # pintura de guerra roja
}


def detail(f):
    """Ojos rojos que brillan en la cara (la mancha verde más grande)."""
    face = f.biggest("green")
    if face:
        f.eyes(face, (255, 40, 20), halo=(140, 0, 0))

PRESET = dict(name="Orc Warchief", source=2, target=224, parts=parts, palettes=palettes, detail=detail)
