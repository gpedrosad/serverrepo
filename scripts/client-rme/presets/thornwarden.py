"""Thornwarden (Carniphila recoloreada): planta morada oscura con espinas rojas y savia venenosa.
Jefe de la torreta SE de Elvenbane: docs/items-and-map/ELVENBANE.md#jefes-de-las-cimas
"""
from sprite_kit import *  # noqa: F401,F403

# Partes del base, por familia de color (h, s, v de 0 a 1). Gana la primera regla que se cumple.
# Es un primer corte automático: ajustar o separar partes mirando `sprite_tool.py inspect thornwarden`.
parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("red", lambda h, s, v: v >= 0.13 and s >= 0.18 and (h < 0.04 or h >= 0.95)),
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("yellow", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.11 <= h < 0.20),
    ("green", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.20 <= h < 0.45),
    ("rest", None),
)

# Colores nuevos de cada parte, de oscuro a claro (3 a 5 colores). Una parte comentada queda igual que
# en el base. `(paleta, 0.8)` aclara y `(paleta, 1.2)` oscurece; un solo color `(r, g, b)` la pinta pareja.
# Al lado de cada parte: sus colores de hoy (oscuro, medio, claro) y cuánto ocupa del base.
palettes = {
    "green": [(20, 6, 26), (60, 20, 70), (110, 50, 120), (170, 110, 170)],   # cuerpo morado oscuro
    "orange": [(70, 0, 0), (160, 10, 20), (230, 60, 60)],                    # espinas rojas
    "yellow": [(60, 90, 0), (150, 210, 20), (230, 255, 120)],                # savia venenosa
    "red": [(60, 0, 10), (150, 0, 30), (240, 40, 70)],
}


def detail(f):
    """Espinas rojas sueltas sobre el cuerpo (posición fija por fórmula, no cambian entre cuadros)."""
    for x, y in f.points("green"):
        if (x * 7 + y * 13 + f.direction * 3) % 31 == 0:
            f.set(x, y, (230, 30, 40))
            f.set(x + 1, y - 1, (255, 120, 110))

PRESET = dict(name="Thornwarden", source=120, target=226, parts=parts, palettes=palettes, detail=detail)
