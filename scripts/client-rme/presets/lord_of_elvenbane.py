"""Lord of Elvenbane (Hero recoloreado): armadura dorada, capa esmeralda y corona con puntas.
Jefe final de Elvenbane (cima de la torre central): docs/items-and-map/ELVENBANE.md#jefes-de-las-cimas
"""
from sprite_kit import *  # noqa: F401,F403

# Partes del base, por familia de color (h, s, v de 0 a 1). Gana la primera regla que se cumple.
# Es un primer corte automático: ajustar o separar partes mirando `sprite_tool.py inspect lord-of-elvenbane`.
parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("gray", lambda h, s, v: v >= 0.13 and s < 0.18),
    ("red", lambda h, s, v: v >= 0.13 and s >= 0.18 and (h < 0.04 or h >= 0.95)),
    ("skin", lambda h, s, v: 0.03 <= h < 0.12 and 0.18 <= s < 0.55 and v > 0.55),   # cara y manos: quedan igual
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("cyan", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.45 <= h < 0.55),
    ("rest", None),
)

# Colores nuevos de cada parte, de oscuro a claro (3 a 5 colores). Una parte comentada queda igual que
# en el base. `(paleta, 0.8)` aclara y `(paleta, 1.2)` oscurece; un solo color `(r, g, b)` la pinta pareja.
# Al lado de cada parte: sus colores de hoy (oscuro, medio, claro) y cuánto ocupa del base.
palettes = {
    "orange": [(60, 40, 0), (150, 110, 20), (225, 185, 60), (255, 240, 160)],  # armadura dorada
    "red": [(0, 40, 20), (10, 90, 50), (40, 150, 90)],                          # capa verde esmeralda
    "gray": [(110, 115, 125), (190, 196, 205), (245, 248, 255)],                # plata
    "cyan": [(60, 20, 90), (120, 60, 170), (190, 140, 240)],                    # gemas violetas
}


def crown(f, colors):
    """Corona: banda dorada en la parte de arriba de la silueta, con puntas alternadas."""
    pts = [(x, y) for y in range(f.w) for x in range(f.w) if f.opaque(x, y)]
    if not pts:
        return
    top = min(y for _x, y in pts)
    xs = sorted(x for x, y in pts if y <= top + 1)
    for x in range(xs[0], xs[-1] + 1):
        f.set(x, top, colors[1])
        f.set(x, top + 1, colors[0])
        if (x - xs[0]) % 2 == 0:
            f.set(x, top - 1, colors[2])


def detail(f):
    """Corona dorada con puntas sobre la cabeza."""
    crown(f, [(150, 110, 20), (230, 190, 60), (255, 245, 170)])

PRESET = dict(name="Lord Of Elvenbane", source=73, target=185, parts=parts, palettes=palettes, detail=detail)
