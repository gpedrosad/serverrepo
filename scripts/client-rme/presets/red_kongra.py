"""Red Kongra: Kongra (116) -> look 254. Pelaje carmesí, piel oscura con tinte maroon
y los detalles brillantes del base (ojos, garras, hocico) pasan a ámbar dorado.

Rasgo propio: la mirada ámbar acentuada con halo (dos ojos de frente, uno de perfil).

Creado con `sprite_tool.py new`. Receta: docs/gameplay/SPRITE_RECOLOR_GUIDE.md.
Doc del monstruo: docs/gameplay/RED_KONGRA.md.
"""
from sprite_kit import *  # noqa: F401,F403

# Partes del base, por familia de color (h, s, v de 0 a 1). Gana la primera regla que se cumple.
# Corte automático de `new` para el Kongra: pelaje naranja (60 %), contorno/piel oscura (38 %) y
# los brillos rojos/amarillos del base (2 %: ojos, garras, hocico).
parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("rest", None),
)

# Colores nuevos de cada parte, de oscuro a claro.
palettes = {
    "orange": [(44, 8, 8), (96, 16, 12), (162, 30, 16), (214, 66, 26), (240, 128, 60)],  # pelaje carmesí
    "dark": [(0, 0, 0), (20, 5, 6), (36, 12, 12)],  # contorno/piel casi negro con tinte maroon
    "rest": [(140, 60, 6), (236, 140, 24), (255, 214, 110)],  # ojos, garras y hocico en ámbar
}


def _eyes(f):
    """Los ojos del Kongra base. De frente (sur): las dos manchas claras del pelaje arriba de la
    cara oscura (la nariz queda más abajo y no entra en la banda). De perfil (este/oeste): el
    brillo `rest` (no pelaje) más alto de la cabeza. De espaldas (norte) no se ve la cara."""
    ys = [y for _x, y in f.points("dark", "orange", "rest")]
    if not ys:
        return []
    y_top = min(ys)

    def bright(pixel):
        h, s, v = hsv(pixel)
        return v >= 0.5

    if f.direction == 2:
        band = [p for p in f.points("orange") if p[1] <= y_top + 2 and bright(f.orig[p[1] * f.w + p[0]])]
        return sorted((g for g in clusters(band) if len(g) >= 2), key=len, reverse=True)[:2]
    if f.direction in (1, 3):
        head = [p for p in f.points("rest") if p[1] <= y_top + 6 and bright(f.orig[p[1] * f.w + p[0]])]
        grupos = clusters(head)
        if not grupos:
            return []
        # este: el brillo más alto de la cabeza; oeste: el más a la izquierda (mira hacia allá).
        pick = (min(grupos, key=lambda g: min(y for _x, y in g)) if f.direction == 1
                else min(grupos, key=lambda g: min(x for x, _y in g)))
        return [pick]
    return []


EYE_AMBER = [(255, 216, 96), (255, 236, 150), (255, 226, 120)]  # parpadeo sutil con la animación
EYE_AURA = (208, 96, 20)


def detail(f):
    """Rasgo propio: los ojos pasan de pelaje a ámbar encendido, con un aura tibia alrededor."""
    for eye in _eyes(f):
        for x, y in eye:
            f.set(x, y, EYE_AMBER[f.anim])
        cx, cy = centroid(eye)
        f.glow(cx, cy, 1.3, 2.2, EYE_AURA, strength=0.4)


PRESET = dict(name="Red Kongra", source=116, target=254, parts=parts, palettes=palettes, detail=detail)
