"""Iron Foreman: Dwarf Guard 70 -> 189, hierro, cobre y casco con lampara.
Doc: docs/gameplay/DWARVEN_MINE.md. Detalles animados en las cuatro direcciones.
"""
from sprite_kit import *  # noqa: F401,F403

parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("gray", lambda h, s, v: v >= 0.13 and s < 0.18),
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("yellow", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.11 <= h < 0.20),
    ("rest", None),
)
palettes = {
    "dark": [(7, 10, 13), (20, 24, 29), (35, 41, 47)],
    "gray": [(35, 42, 50), (92, 109, 121), (188, 202, 206)],
    "orange": [(59, 31, 20), (137, 76, 39), (218, 154, 93)],
    "yellow": [(70, 39, 22), (171, 103, 49), (249, 196, 112)],
}


def detail(f):
    # Placa de hierro remachada en el casco, siguiendo el bloque de cabeza de cada pose.
    face = f.biggest("orange")
    if not face:
        return
    x0, y0 = min(x for x, y in face), min(y for x, y in face)
    cx, cy = x0 + 4, y0 + 3
    for dy in range(-2, 1):
        for dx in range(-4, 5):
            if f.opaque(cx + dx, cy + dy):
                f.set(cx + dx, cy + dy, (86, 105, 119) if dy < 0 else (36, 47, 59))
    for dx in (-3, 3):
        f.set(cx + dx, cy - 1, (222, 163, 88))
    # Lampara frontal con carcasa de cobre; de espaldas se ve el soporte del casco.
    if f.direction in (1, 2, 3):
        f.orb(cx, cy, 2.1, [(255, 249, 191), (244, 185, 72), (113, 65, 27)])
        f.glow(cx, cy, 2, 3, (255, 186, 70), strength=0.45)
        f.set(cx, cy, ((255, 250, 211), (255, 215, 113), (255, 240, 170))[f.anim])
    else:
        for dx in (-1, 0, 1):
            f.set(cx + dx, cy, (171, 107, 53))


PRESET = dict(name="Iron Foreman", source=70, target=189,
              parts=parts, palettes=palettes, detail=detail)
