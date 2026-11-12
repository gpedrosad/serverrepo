"""Root Colossus: Behemoth (55, 2x2) -> look 243. Corteza surcada, rostro de tronco,
corona de ramas, musgo, hongos y dedos/raices que cambian la silueta en los 12 cuadros.
Doc: docs/gameplay/ROOT_COLOSSUS.md.
"""
from sprite_kit import *  # noqa: F401,F403

parts = BASE_PARTS[55]
palettes = {
    "outline": [(6, 10, 6), (18, 20, 11), (36, 30, 16)],
    "skin": [(29, 21, 12), (65, 46, 23), (106, 79, 39), (157, 121, 67), (199, 166, 102)],
    "bone": [(43, 33, 18), (112, 86, 43), (195, 164, 95)],
    "eyes": [(26, 55, 20), (100, 172, 51), (201, 247, 117)],
}

BARK_DARK = (29, 24, 12)
BARK_MID = (103, 77, 38)
BARK_LIGHT = (174, 138, 72)
MOSS = ((26, 50, 20), (55, 87, 28), (92, 125, 40), (141, 162, 65))
# La cabeza se traslada como mucho un pixel por cuadro; los brazos tienen anclas propias.
SHIFT = (((0, 0), (-1, -1), (0, -1)), ((0, 0), (-1, -1), (-1, 0)),
         ((0, 0), (-1, -1), (0, -1)), ((0, 0), (-1, -1), (-1, 0)))
HEAD = ((17, 12), (16, 16), (16, 16), (11, 13))
SHOULDER = ((34, 15), (35, 18), (38, 16), (30, 15))
HANDS = (((16, 38), (17, 35), (13, 40)), ((26, 42), (27, 40), (28, 45)),
         ((12, 36), (10, 35), (8, 40)), ((41, 39), (41, 37), (47, 34)))


def line(f, start, end, color, width=0):
    """Trazo entero sin suavizado: el contorno nunca depende del azar."""
    x1, y1 = start
    x2, y2 = end
    steps = max(abs(x2 - x1), abs(y2 - y1), 1)
    for step in range(steps + 1):
        x = round(x1 + (x2 - x1) * step / steps)
        y = round(y1 + (y2 - y1) * step / steps)
        for dy in range(-width, width + 1):
            for dx in range(-width, width + 1):
                f.set(x + dx, y + dy, color)


def branch(f, points):
    points = [(max(2, min(f.w - 3, x)), max(2, min(f.w - 3, y))) for x, y in points]
    for a, b in zip(points, points[1:]):
        line(f, a, b, BARK_DARK, 1)
    for a, b in zip(points, points[1:]):
        line(f, a, b, BARK_MID)
        line(f, (a[0], a[1] - 1), (b[0], b[1] - 1), BARK_LIGHT)


def moss(f, cx, cy, rx, ry, grow=False):
    for y in range(cy - ry, cy + ry + 1):
        for x in range(cx - rx, cx + rx + 1):
            distance = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if distance > 1 or not (grow or f.opaque(x, y) or any(f.opaque(x + dx, y + dy) for dx, dy in CARD4)):
                continue
            shade = 0 if distance > 0.8 else (2 if y < cy else 1)
            if distance < 0.65 and ((x - cx) // 2 * 7 + (y - cy) // 2 * 11) % 7 == 0:
                shade = min(3, shade + 1)
            f.set(x, y, MOSS[shade])


def detail(f):
    sx, sy = SHIFT[f.direction][f.anim]
    hx, hy = HEAD[f.direction]
    hx, hy = hx + sx, hy + sy
    bx, by = SHOULDER[f.direction]
    bx, by = bx + sx, by + sy

    # Placas longitudinales: reemplazan el acabado liso de los musculos por corteza.
    for x, y in f.points("skin", "bone"):
        u, v = x - sx, y - sy
        groove = (u + v // 8 + (u // 9) % 3) % 7
        if groove == 0 and v % 13 < 10:
            f.set(x, y, BARK_DARK)
        elif groove == 1 and v % 13 < 10:
            old = f.get(x, y)
            f.set(x, y, tuple((a * 2 + b) // 3 for a, b in zip(old[:3], BARK_LIGHT)))

    # Mascara de madera: borra la boca y la expresion del Behemoth.
    rx, ry = (9, 10) if f.direction in (1, 2) else (7, 8)
    for y in range(hy - ry, hy + ry + 1):
        for x in range(hx - rx, hx + rx + 1):
            d = ((x - hx) / rx) ** 2 + ((y - hy) / ry) ** 2
            if d <= 1 and f.opaque(x, y):
                edge = abs(x - hx) / rx
                k = 0 if edge < 0.35 else 1
                color = ((39, 39, 20), (88, 74, 34))[k]
                if (x - hx + (y - hy) // 5) % 5 == 0:
                    color = (20, 26, 13)
                f.set(x, y, color)
    if f.direction in (1, 2):
        eye_xs = (hx - 4, hx + 3) if f.direction == 2 else (hx + 2,)
        for x in eye_xs:
            line(f, (x - 1, hy - 1), (x + 1, hy - 1), (192, 247, 102))
            f.set(x, hy, (82, 151, 42))
        line(f, (hx, hy + 3), (hx - 1, hy + 7), (13, 23, 11))

    # Cuernos convertidos en una corona bifurcada, con puntas nuevas fuera del original.
    branch(f, [(hx - 5, hy - 5), (hx - 8, 5 + sy), (hx - 11, 1)])
    branch(f, [(hx - 8, 5 + sy), (hx - 13, 4), (max(1, hx - 15), 1)])
    branch(f, [(hx + 4, hy - 6), (hx + 7, 4 + sy), (hx + 12, 1)])
    branch(f, [(hx + 7, 4 + sy), (hx + 6, 1)])
    branch(f, [(bx, by + 1), (bx + 8, by - 5), (bx + 14, by - 11)])
    branch(f, [(bx + 8, by - 5), (bx + 8, by - 12), (bx + 5, by - 15)])
    moss(f, bx, by + 1, 9, 5)
    moss(f, bx - 4, by + 5, 5, 4)
    # Brotes conectados a las ramas, con margen para no cortar hojas en el cuadro.
    for cx, cy in ((bx + 8, by - 10), (bx + 13, by - 9), (hx - 10, 4)):
        moss(f, max(4, min(f.w - 5, cx)), max(4, cy), 3, 2, grow=True)

    # Hongos de repisa que sobresalen del hombro.
    for dx, dy in ((5, 3), (9, 0)):
        cx, cy = bx + dx, by + dy
        line(f, (cx, cy + 1), (cx, cy + 3), (150, 125, 70))
        line(f, (cx - 2, cy), (cx + 2, cy), (115, 57, 26))
        line(f, (cx - 1, cy - 1), (cx + 1, cy - 1), (204, 147, 66))

    # Raices en dedos y pies, ancladas a cada pose de la animacion.
    ax, ay = HANDS[f.direction][f.anim]
    if any(f.opaque(ax + dx, ay - 2) for dx in range(-2, 3)):
        for dx in (-2, 1, 4):
            branch(f, [(ax + dx, ay - 2), (ax + dx + 1, ay + 2), (ax + dx + 3, ay + 4)])
    underside = f.underside()
    bottom = max(y for x, y in underside)
    feet = [(x, y) for x, y in underside if y >= bottom - 4 and (x - sx) % 6 == 0]
    for x, y in feet[:4]:
        branch(f, [(x, y - 1), (x - 2, min(f.w - 2, y + 2)), (x - 4, min(f.w - 1, y + 3))])


PRESET = dict(name="Root Colossus", source=55, target=243, parts=parts, palettes=palettes, detail=detail)
