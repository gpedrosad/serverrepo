"""Elven Archmage (Elf Arcanist recoloreada): túnica azul real, ribete plateado y orbe de energía.
Jefa de la torreta NE de Elvenbane: docs/items-and-map/ELVENBANE.md#jefes-de-las-cimas
"""
from sprite_kit import *  # noqa: F401,F403

# Partes del base, por familia de color (h, s, v de 0 a 1). Gana la primera regla que se cumple.
# Es un primer corte automático: ajustar o separar partes mirando `sprite_tool.py inspect elven-archmage`.
parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("gray", lambda h, s, v: v >= 0.13 and s < 0.18),
    ("red", lambda h, s, v: v >= 0.13 and s >= 0.18 and (h < 0.04 or h >= 0.95)),
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("yellow", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.11 <= h < 0.20),
    ("rest", None),
)

# Colores nuevos de cada parte, de oscuro a claro (3 a 5 colores). Una parte comentada queda igual que
# en el base. `(paleta, 0.8)` aclara y `(paleta, 1.2)` oscurece; un solo color `(r, g, b)` la pinta pareja.
# Al lado de cada parte: sus colores de hoy (oscuro, medio, claro) y cuánto ocupa del base.
palettes = {
    "red": [(10, 20, 70), (30, 60, 170), (90, 140, 240), (180, 210, 255)],   # túnica azul real
    "gray": [(120, 130, 150), (200, 210, 225), (250, 252, 255)],             # ribete plateado
    "yellow": [(20, 90, 120), (60, 190, 230), (200, 245, 255)],              # adornos celestes
}


def detail(f):
    """Orbe de energía que late sobre el objeto claro más grande (el báculo), con resplandor celeste."""
    obj = f.biggest("gray")
    if obj:
        cx, cy = centroid(obj)
        f.orb(cx, cy - 1, (2.0, 2.4, 2.2)[f.anim], [(255, 255, 255), (150, 230, 255), (30, 110, 220)])
        f.glow(cx, cy - 1, 3, 2, (90, 190, 255))

PRESET = dict(name="Elven Archmage", source=63, target=223, parts=parts, palettes=palettes, detail=detail)
