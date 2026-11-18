"""River Troll: Troll (15) -> look 252. Piel de agua turbia verdosa, penacho de juncos secos,
ojos pálidos de pez, brillo mojado, parche de algas en el hombro y gotas que caen al caminar.
Doc: docs/gameplay/RIVER_STONE_TROLLS.md.
"""
from sprite_kit import *  # noqa: F401,F403

# Partes del base (primer corte automático por familia de color, revisado con `inspect`):
# orange 72 % (piel h 0.04-0.09), dark 22 % (contorno v < 0.13), red 6 % (penacho y ojos),
# rest 0.2 % (el diente amarillo, queda igual).
parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("red", lambda h, s, v: v >= 0.13 and s >= 0.18 and (h < 0.04 or h >= 0.95)),
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("rest", None),
)

# Agua turbia con algas: de oscuro a claro, verdoso para no confundirse con el Swamp Troll
# (verde puro) ni con el Frost Troll (cian brillante).
RIVER_SKIN = [(14, 28, 24), (32, 72, 56), (62, 130, 98), (106, 186, 142), (172, 232, 190)]
# Penacho de juncos secos; los ojos (también parte "red") quedan pálidos, como de pez.
REEDS = [(92, 62, 18), (168, 128, 48), (228, 196, 110)]
RIVER_DARK = [(0, 5, 5), (0, 8, 8), (16, 30, 26)]

palettes = {
    "orange": RIVER_SKIN,
    "dark": RIVER_DARK,
    "red": REEDS,
    # "rest": queda igual (el diente).
}

# Algas del hombro y agua que gotea.
ALGAE = [(20, 44, 22, 255), (36, 70, 34, 255), (62, 100, 44, 255)]
WET_GLINT = (198, 240, 238, 255)
DRIP_LIGHT, DRIP_DARK = (170, 230, 240, 255), (96, 180, 200, 255)


def detail(f):
    """Rasgos del troll de río, cuadro por cuadro:

    - Brillo mojado: dos destellos pálidos en el lomo/cabeza que se mueven 1 px con la animación.
    - Algas: un parchito de tres tonos colgado del hombro (arriba a la izquierda de la silueta).
    - Goteo: dos gotas desde el borde de abajo que cambian de largo con el paso.
    """
    body = f.points("orange")
    if body:
        # brillo mojado: los puntos del cuerpo más arriba y a la izquierda, con fórmula fija
        top = sorted((x, y) for x, y in body if y <= 10)[:14]
        for n, (x, y) in enumerate(top):
            if (x * 7 + y * 13 + f.direction * 3 + f.anim) % 9 == 0 and n < 6:
                f.set(x, y, WET_GLINT)
        # parche de algas en el hombro: un punto semilla y sus vecinos de abajo
        seed = [p for p in body if p[1] >= 6 and p[0] <= 12 and (p[0] * 5 + p[1] * 11) % 23 == 0]
        for x, y in seed[:2]:
            for k in range(3):
                if f.opaque(x, y + k):
                    f.set(x, y + k, ALGAE[k])

    # gotas desde el borde de abajo (solo de la mitad inferior de la silueta), que se estiran con el paso
    edge = [p for p in f.underside() if p[1] >= 16]
    drips = 0
    for x, y in edge:
        if drips >= 2:
            break
        if (x * 3 + y + f.anim * 5 + f.direction) % 13 == 0:
            length = 2 + (x + f.anim) % 2
            f.hang(x, y, [DRIP_LIGHT] + [DRIP_DARK] * (length - 1))
            drips += 1


PRESET = dict(name="River Troll", source=15, target=252, parts=parts, palettes=palettes, detail=detail)
