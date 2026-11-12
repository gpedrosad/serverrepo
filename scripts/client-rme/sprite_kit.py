"""Piezas para escribir un preset de sprite en pocas líneas. Sin dependencias.

Un preset es un archivo en scripts/client-rme/presets/ (lo crea `sprite_tool.py new`). Empieza con
`from sprite_kit import *` y usa lo de acá:

  parts_by_rules(...)   clasificador de partes del base a partir de reglas sobre (h, s, v)
  paletas               en el preset: `palettes = {"parte": [colores de oscuro a claro]}`
  Frame                 lo que recibe `detail(f)`: un cuadro con sus partes y ayudas para pintar
  BASE_PARTS            clasificadores de las bases ya estudiadas: BASE_PARTS[57] es el del Monk
  gradient, hsv, luma, clusters, centroid, part_points, CARD4   las piezas sueltas

Receta: docs/gameplay/SPRITE_RECOLOR_GUIDE.md.
"""
from __future__ import annotations

import colorsys
import math

__all__ = ["BASE_PARTS", "CARD4", "FAMILIES", "Frame", "centroid", "clusters", "color_family", "gradient", "hsv", "luma",
           "math", "palette_recolor", "parts_by_rules", "part_points", "stops_of",
           "crypt_shambler_part", "ghoul_part", "monk_part", "necromancer_part"]

CARD4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

# Familias de color para un primer corte automático de partes (`sprite_tool.py new` y `catalog`).
# Cada condición es texto Python sobre h, s, v (0-1) y vale sola, sin depender del orden.
FAMILIES = (
    ("dark", "v < 0.13"),
    ("gray", "v >= 0.13 and s < 0.18"),
    ("red", "v >= 0.13 and s >= 0.18 and (h < 0.04 or h >= 0.95)"),
    ("orange", "v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11"),
    ("yellow", "v >= 0.13 and s >= 0.18 and 0.11 <= h < 0.20"),
    ("green", "v >= 0.13 and s >= 0.18 and 0.20 <= h < 0.45"),
    ("cyan", "v >= 0.13 and s >= 0.18 and 0.45 <= h < 0.55"),
    ("blue", "v >= 0.13 and s >= 0.18 and 0.55 <= h < 0.72"),
    ("violet", "v >= 0.13 and s >= 0.18 and 0.72 <= h < 0.85"),
    ("magenta", "v >= 0.13 and s >= 0.18 and 0.85 <= h < 0.95"),
)
_FAMILY_TESTS = [(name, eval(f"lambda h, s, v: {rule}")) for name, rule in FAMILIES]


def hsv(pixel):
    """Tono, saturación y brillo (0-1) de un píxel (r, g, b, a)."""
    return colorsys.rgb_to_hsv(pixel[0] / 255, pixel[1] / 255, pixel[2] / 255)


def luma(pixel):
    """Luminosidad percibida de 0 a 1."""
    return (0.30 * pixel[0] + 0.59 * pixel[1] + 0.11 * pixel[2]) / 255


def color_family(pixel):
    """Familia de color de un píxel opaco: dark, gray, red, orange, yellow, green, cyan, blue, violet o magenta."""
    h, s, v = hsv(pixel)
    return next(name for name, test in _FAMILY_TESTS if test(h, s, v))


def stops_of(palette):
    """Paleta -> [(posición, (r, g, b)), …]. Acepta esa forma o una lista de colores de oscuro a claro,
    que se reparten parejo entre 0 y 1."""
    if isinstance(palette[0][0], (int, float)) and len(palette[0]) == 2:
        return palette
    if len(palette) == 1:
        return [(0, palette[0]), (1, palette[0])]
    return [(i / (len(palette) - 1), color) for i, color in enumerate(palette)]


def gradient(stops, k):
    """Color de una paleta con posiciones para k entre 0 y 1."""
    k = max(0.0, min(1.0, k))
    for (k0, c0), (k1, c1) in zip(stops, stops[1:]):
        if k <= k1:
            t = (k - k0) / (k1 - k0) if k1 > k0 else 0
            return tuple(int(a + (b - a) * t) for a, b in zip(c0, c1))
    return stops[-1][1]


def part_points(parts, name, w):
    """Coordenadas (x, y) de los píxeles de una parte, a partir de la lista de partes de un cuadro."""
    return [(i % w, i // w) for i, part in enumerate(parts) if part == name]


def centroid(points):
    """Centro (x, y) con decimales de una lista de puntos."""
    return sum(x for x, _y in points) / len(points), sum(y for _x, y in points) / len(points)


def clusters(points):
    """Agrupa puntos que se tocan (también en diagonal). Devuelve una lista de grupos, de arriba abajo."""
    points, seen, out = set(points), set(), []
    for start in sorted(points, key=lambda t: (t[1], t[0])):
        if start in seen:
            continue
        seen.add(start)
        stack, comp = [start], []
        while stack:
            x, y = stack.pop()
            comp.append((x, y))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in points and q not in seen:
                        seen.add(q)
                        stack.append(q)
        out.append(comp)
    return out


def parts_by_rules(*rules):
    """Clasificador de partes: `parts_by_rules(("dark", lambda h, s, v: v < 0.13), …, ("body", None))`.

    Gana la primera regla que se cumple, así que va primero lo más específico (ojos, piel) y al final
    el resto con `None`. Devuelve una función `parte(pixel)` que da el nombre, o None si es transparente."""
    def part(pixel):
        if pixel[3] == 0:
            return None
        h, s, v = hsv(pixel)
        for name, test in rules:
            if test is None or test(h, s, v):
                return name
        return rules[-1][0]
    return part


def palette_recolor(parts_of, palettes, frames):
    """Función `recolor(pixel)` a partir de `palettes = {parte: paleta}`.

    Paleta = lista de colores de oscuro a claro (o con posiciones). También vale `(paleta, exponente)`
    para el contraste (menor que 1 aclara, mayor oscurece) o un color fijo `(r, g, b)`. Una parte que no
    figura queda como en el base. La posición en la paleta sale de la luminosidad del píxel llevada a 0-1
    dentro de su parte (se mide en los 12 cuadros), así cada parte usa su paleta entera."""
    spans: dict = {}
    for frame in frames:
        for pixel in set(frame):
            if pixel[3]:
                name, value = parts_of(pixel), luma(pixel)
                lo, hi = spans.get(name, (value, value))
                spans[name] = (min(lo, value), max(hi, value))
    cache: dict = {}

    def recolor(pixel):
        if pixel[3] == 0:
            return pixel
        if pixel not in cache:
            name = parts_of(pixel)
            spec = palettes.get(name)
            if spec is None:
                cache[pixel] = pixel
            elif isinstance(spec[0], int):
                cache[pixel] = tuple(spec[:3]) + (255,)
            else:
                palette, power = spec if isinstance(spec, tuple) else (spec, 1.0)
                lo, hi = spans[name]
                k = (luma(pixel) - lo) / (hi - lo) if hi > lo else 0.5
                cache[pixel] = gradient(stops_of(palette), k ** power) + (255,)
        return cache[pixel]
    return recolor


class Frame:
    """Un cuadro mientras se retoca; es lo que recibe `detail(f)` de un preset.

    Datos: `f.anim` (0 quieto, 1 y 2 caminar), `f.direction` (0 norte, 1 este, 2 sur, 3 oeste), `f.w`
    (32 o 64), `f.orig` (píxeles del base), `f.px` (píxeles nuevos, ya recoloreados; es lo que se guarda)
    y `f.parts` (parte de cada píxel del base). Las coordenadas son (x, y) con (0, 0) arriba a la izquierda.
    Todo lo que pinta ignora lo que cae fuera del cuadro."""

    def __init__(self, index, orig, px, w, parts_of=None):
        self.index, self.anim, self.direction = index, index // 4, index % 4
        self.orig, self.px, self.w = orig, list(px), w
        self.parts = [parts_of(p) if parts_of else ("all" if p[3] else None) for p in orig]

    def inside(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.w

    def opaque(self, x, y):
        """¿El base tiene un píxel ahí? (la silueta original)"""
        return self.inside(x, y) and self.orig[y * self.w + x][3] != 0

    def get(self, x, y):
        return self.px[y * self.w + x]

    def set(self, x, y, color):
        if self.inside(x, y):
            self.px[y * self.w + x] = tuple(color[:3]) + (255,)

    def points(self, *names):
        """Puntos de una o más partes."""
        return [(i % self.w, i // self.w) for i, part in enumerate(self.parts) if part in names]

    def groups(self, *names, min_size=1):
        """Grupos de píxeles que se tocan de esas partes, del más grande al más chico."""
        return sorted((g for g in clusters(self.points(*names)) if len(g) >= min_size), key=len, reverse=True)

    def biggest(self, *names):
        """El grupo más grande de esas partes (un objeto, la cara), o [] si no hay."""
        groups = self.groups(*names)
        return groups[0] if groups else []

    def thick(self, points):
        """Solo los puntos con sus 4 vecinos dentro del conjunto: saca brazos y bordes finos."""
        inside = set(points)
        return [(x, y) for x, y in points if all((x + dx, y + dy) in inside for dx, dy in CARD4)]

    def fill(self, points, paint, gain=1.0, power=1.0):
        """Pinta puntos con un color fijo `(r, g, b)` o con una paleta según la luz del píxel del base."""
        fixed = isinstance(paint[0], int)
        stops = None if fixed else stops_of(paint)
        for x, y in points:
            if fixed:
                self.set(x, y, paint)
            elif self.inside(x, y):
                self.set(x, y, gradient(stops, luma(self.orig[y * self.w + x]) ** power * gain))

    def orb(self, cx, cy, radius, palette, power=1.3):
        """Disco con degradé desde el centro (primer color) al borde (último). Tapa lo que haya debajo.
        Para que lata, variar el radio con `f.anim`, ej. `(2.6, 3.1, 2.8)[f.anim]`."""
        stops = stops_of(palette)
        for y in range(self.w):
            for x in range(self.w):
                d = math.hypot(x - cx, y - cy)
                if d <= radius:
                    self.set(x, y, gradient(stops, (d / radius) ** power))

    def glow(self, cx, cy, radius, width, color, strength=0.55):
        """Resplandor: mezcla hacia `color` los píxeles de la silueta entre `radius` y `radius + width`
        del centro, con más fuerza cuanto más cerca. No pinta sobre transparente."""
        for y in range(self.w):
            for x in range(self.w):
                d = math.hypot(x - cx, y - cy)
                if radius < d <= radius + width and self.opaque(x, y):
                    k = (1 - (d - radius) / width) * strength
                    self.set(x, y, tuple(int(c + (g - c) * k) for c, g in zip(self.get(x, y)[:3], color)))

    def eyes(self, face, color, halo=None, directions=(1, 2)):
        """Ojos que brillan sobre un grupo de puntos (la cara): dos de frente (sur) y uno de perfil, en
        el borde hacia donde mira. Van en la fila a un tercio de la cara desde arriba. Por omisión solo
        mirando al este y al sur, porque de espaldas y al oeste casi nunca se ve la cara.
        `halo` pinta el píxel de abajo de cada ojo. Devuelve los puntos pintados."""
        if not face or self.direction not in directions or self.direction == 0:
            return []
        ys = sorted({y for _x, y in face})
        row = ys[len(ys) // 3]
        xs = sorted(x for x, y in face if y == row)
        if self.direction == 2:
            spots = [xs[0] + 1, xs[-1] - 1] if len(xs) >= 5 else ([xs[0], xs[-1]] if len(xs) >= 3 else [xs[0]])
        else:
            spots = [xs[-1] if self.direction == 1 else xs[0]]
        for x in spots:
            self.set(x, row, color)
            if halo and (x, row + 1) in set(face):
                self.set(x, row + 1, halo)
        return [(x, row) for x in spots]

    def underside(self):
        """Puntos de la silueta que tienen transparente justo abajo, de izquierda a derecha y de arriba
        abajo: de ahí cuelgan algas, gotas, flecos."""
        return sorted(((i % self.w, i // self.w) for i, p in enumerate(self.orig)
                       if p[3] and self.inside(i % self.w, i // self.w + 1) and not self.opaque(i % self.w, i // self.w + 1)),
                      key=lambda t: (t[1], t[0]))

    def hang(self, x, y, colors):
        """Cuelga una tira hacia abajo desde (x, y): un color por píxel, solo sobre transparente."""
        for k, color in enumerate(colors, 1):
            if self.inside(x, y + k) and not self.opaque(x, y + k):
                self.set(x, y + k, color)

    def around(self, cx, cy, distance, angle):
        """Punto (x, y) a cierta distancia y ángulo (radianes) de un centro: para chispas que giran,
        ej. `f.set(*f.around(cx, cy, 5, 2.1 * n + 0.9 * f.anim), color)`."""
        return round(cx + math.cos(angle) * distance), round(cy + math.sin(angle) * distance)


# ---------- bases ya estudiadas ----------
# Clasificadores probados. Para un preset sobre una de estas bases: `parts = BASE_PARTS[57]`.
# Al estudiar una base nueva, agregar acá su clasificador y una fila en la tabla de bases de la guía.

def monk_part(pixel):
    """Monk (57, guardado 2x2): skin (cara y manos), belt (cinturón dorado), outline o robe (túnica)."""
    if pixel[3] == 0:
        return None
    h, s, v = hsv(pixel)
    if 0.06 <= h <= 0.10 and 0.28 <= s <= 0.47 and v > 0.74:
        return "skin"
    if 0.095 <= h <= 0.13 and s > 0.47 and v > 0.76:
        return "belt"
    if v < 0.22:
        return "outline"
    return "robe"


def crypt_shambler_part(pixel):
    """Crypt Shambler (100, 1x1): dark (contorno), pants (pantalón verde), wound (heridas rojas) o skin."""
    if pixel[3] == 0:
        return None
    h, s, v = hsv(pixel)
    if v < 0.13:
        return "dark"
    if 0.2 < h < 0.55 and s > 0.25:
        return "pants"
    if (h < 0.04 or h > 0.93) and s > 0.6:
        return "wound"
    return "skin"


def necromancer_part(pixel):
    """Necromancer (9, 1x1): skin (cara), light (calavera, manos, botas, ribete) o robe (túnica casi negra,
    brillo solo de 0 a 0.3). El brillo violeta de la capucha es túnica: por eso `h < 0.5` en light."""
    if pixel[3] == 0:
        return None
    h, s, v = hsv(pixel)
    if 0.03 < h < 0.13 and s > 0.3 and v > 0.35:
        return "skin"
    return "light" if v >= 0.3 and h < 0.5 else "robe"


def ghoul_part(pixel):
    """Ghoul (18, 1x1): dark (contorno), wound (heridas rojas) o body."""
    if pixel[3] == 0:
        return None
    h, s, v = hsv(pixel)
    if v < 0.13:
        return "dark"
    if h < 0.04 and s > 0.6:
        return "wound"
    return "body"


def hydra_part(pixel):
    """Hydra (121, 2x2): contorno, ojos rojos, detalles claros o escamas verdes."""
    if pixel[3] == 0:
        return None
    h, s, v = hsv(pixel)
    if v < 0.13:
        return "outline"
    if h < 0.05 and s > 0.7 and v > 0.35:
        return "eyes"
    if h < 0.21 or s < 0.18:
        return "claws"
    return "scales"


def ancient_scarab_part(pixel):
    """Ancient Scarab (79, 2x2): contorno, ojos, patas verdes o caparazon violeta/gris/azul."""
    if pixel[3] == 0:
        return None
    h, s, v = hsv(pixel)
    if v < 0.13:
        return "outline"
    if s > 0.7 and (h < 0.04 or 0.14 < h < 0.20):
        return "eyes"
    if 0.20 <= h < 0.45 and s >= 0.18:
        return "legs"
    return "shell"


def behemoth_part(pixel):
    """Behemoth (55, 2x2): contorno, verdes de la cara, hueso claro o piel marron."""
    if pixel[3] == 0:
        return None
    h, s, v = hsv(pixel)
    if v < 0.13:
        return "outline"
    if 0.20 < h < 0.45 and s > 0.35:
        return "eyes"
    if s < 0.25 and v > 0.35:
        return "bone"
    return "skin"


BASE_PARTS = {9: necromancer_part, 18: ghoul_part, 55: behemoth_part, 57: monk_part, 79: ancient_scarab_part,
              100: crypt_shambler_part, 121: hydra_part}
