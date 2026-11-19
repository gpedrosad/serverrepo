"""Elvenbane Ranger (Elf Scout recoloreado): capa verde bosque, pelo plateado y hojas colgando.
Jefe de la torreta NO de Elvenbane: docs/items-and-map/ELVENBANE.md#jefes-de-las-cimas
"""
from sprite_kit import *  # noqa: F401,F403

# Partes del base, por familia de color (h, s, v de 0 a 1). Gana la primera regla que se cumple.
# Es un primer corte automático: ajustar o separar partes mirando `sprite_tool.py inspect elvenbane-ranger`.
parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("red", lambda h, s, v: v >= 0.13 and s >= 0.18 and (h < 0.04 or h >= 0.95)),
    ("skin", lambda h, s, v: 0.03 <= h < 0.12 and 0.18 <= s < 0.55 and v > 0.55),   # cara y manos: quedan igual
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("yellow", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.11 <= h < 0.20),
    ("green", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.20 <= h < 0.45),
    ("rest", None),
)

# Colores nuevos de cada parte, de oscuro a claro (3 a 5 colores). Una parte comentada queda igual que
# en el base. `(paleta, 0.8)` aclara y `(paleta, 1.2)` oscurece; un solo color `(r, g, b)` la pinta pareja.
# Al lado de cada parte: sus colores de hoy (oscuro, medio, claro) y cuánto ocupa del base.
palettes = {
    "orange": [(10, 34, 14), (34, 84, 36), (92, 150, 70), (170, 210, 120)],   # cuero y capa: verde bosque
    "yellow": [(90, 96, 104), (176, 184, 196), (236, 240, 248)],             # pelo plateado
    "red": [(20, 70, 40), (40, 150, 80), (120, 230, 150)],                   # detalles esmeralda
    "green": [(96, 70, 10), (190, 150, 30), (250, 220, 90)],                 # adornos dorados
}


def detail(f):
    """Hojas que cuelgan del borde de abajo de la capa (verde claro y oscuro, fijas por posición)."""
    for x, y in f.underside()[1::7][:4]:
        f.hang(x, y, [(60, 140, 60), (30, 90, 40)][:1 + (x + y) % 2])

PRESET = dict(name="Elvenbane Ranger", source=64, target=222, parts=parts, palettes=palettes, detail=detail)
