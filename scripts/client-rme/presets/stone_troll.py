"""Stone Troll: Troll (15) -> look 253. Piel de granito gris azulado con grietas, penacho y ojos
de brasa, musgo que le crece en la cabeza y el hombro.
Doc: docs/gameplay/RIVER_STONE_TROLLS.md.
"""
from sprite_kit import *  # noqa: F401,F403

# Partes del base (igual que river_troll: piel orange 72 %, contorno dark, penacho/ojos red, diente rest).
parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("red", lambda h, s, v: v >= 0.13 and s >= 0.18 and (h < 0.04 or h >= 0.95)),
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("rest", None),
)

# Granito gris azulado; el extremo claro alto para que no se pierda sobre piso de piedra.
GRANITE = [(30, 34, 40), (78, 84, 94), (128, 134, 142), (176, 180, 186), (222, 224, 226)]
# Penacho y ojos de brasa: óxido oscuro -> naranja -> dorado vivo.
EMBER = [(96, 40, 8), (188, 96, 20), (255, 176, 60)]
STONE_DARK = [(4, 4, 6), (4, 4, 6), (30, 32, 38)]

palettes = {
    "orange": GRANITE,
    "dark": STONE_DARK,
    "red": EMBER,
    # "rest": queda igual (el diente).
}

MOSS = [(30, 62, 24), (54, 100, 38), (88, 146, 56)]
CRACK = (44, 48, 54)


def detail(f):
    """Rasgos del troll de piedra, cuadro por cuadro:

    - Musgo: matas en la cabeza (arriba a la izquierda) y una en el hombro, de tres tonos.
    - Grietas: píxeles de granito oscurecidos en diagonal, como fisuras de la piedra.
    """
    body = f.points("orange")
    if body:
        # musgo de la cabeza: puntos del cuerpo de la franja de arriba, con fórmula fija
        crown = sorted((x, y) for x, y in body if y <= 7)[:24]
        seeds = [(x, y) for x, y in crown if (x * 7 + y * 11 + f.direction * 3) % 19 == 0]
        for x, y in seeds[:2]:
            for k in range(3):
                if f.opaque(x, y + k):
                    f.set(x, y + k, MOSS[k])
        # mata del hombro (lado este de la silueta)
        shoulder = [p for p in body if 8 <= p[1] <= 13 and (p[0] * 5 + p[1] * 7) % 29 == 0]
        for x, y in shoulder[:1]:
            for k in range(3):
                if f.opaque(x, y + k):
                    f.set(x, y + k, MOSS[min(2, k + 1)])
        # grietas: diagonal de granito oscuro sobre el cuerpo grueso
        thick_body = f.thick(body)
        for x, y in thick_body:
            if (x + y * 2 + f.direction) % 17 == 0:
                f.set(x, y, CRACK)


PRESET = dict(name="Stone Troll", source=15, target=253, parts=parts, palettes=palettes, detail=detail)
