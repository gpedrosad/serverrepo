"""Drowned Sailor: Crypt Shambler (100) -> look 233. Piel hinchada gris verdosa, pantalón azul marino,
camiseta rayada, pañuelo rojo desteñido, algas que cuelgan, percebes y gotas.
Doc: docs/gameplay/DROWNED_SAILOR.md.
"""
from sprite_kit import *  # noqa: F401,F403


DROWNED_SKIN = [(0, (10, 24, 30)), (0.25, (40, 72, 76)), (0.5, (96, 134, 124)), (0.75, (160, 186, 168)),
                (1, (214, 226, 206))]
DROWNED_ALGAE = [(0, (14, 30, 18)), (0.5, (46, 84, 42)), (1, (98, 136, 66))]
NAVY = [(0, (6, 10, 28)), (0.5, (28, 46, 96)), (1, (78, 104, 160))]
SHIRT_WHITE = [(0, (120, 126, 120)), (1, (222, 226, 214))]
BANDANA = [(0, (70, 14, 14)), (0.5, (150, 40, 34)), (1, (212, 96, 74))]
SEAWEED = [(20, 44, 22, 255), (36, 70, 34, 255), (62, 100, 44, 255)]
DRIP_LIGHT, DRIP_DARK = (190, 232, 240, 255), (120, 190, 210, 255)
BARNACLE_LIGHT, BARNACLE_DARK = (214, 212, 192, 255), (150, 146, 128, 255)


def recolor_drowned(pixel):
    """Crypt Shambler -> ahogado: piel gris verdosa, heridas -> manchas de algas, pantalón azul marino."""
    part = crypt_shambler_part(pixel)
    if part is None:
        return pixel
    r, g, b, _a = pixel
    if part == "dark":                                   # contorno con un toque azul de agua
        tint = 4 if (g or b) else 0
        return (r // 2, g // 2 + tint, b // 2 + tint + tint // 2, 255)
    if part == "pants":
        return gradient(NAVY, luma(pixel) * 1.6) + (255,)
    if part == "wound":
        return gradient(DROWNED_ALGAE, luma(pixel) * 1.8) + (255,)
    return gradient(DROWNED_SKIN, luma(pixel) ** 1.15) + (255,)


def drowned_sailor_details(original, recolored):
    """Rasgos del Marinero Ahogado sobre cada cuadro 32x32 (criatura 1x1).

    - Pañuelo rojo: la cabeza es el grupo de piel gruesa (sin brazos finos) más alto del cuadro;
      cubre la mitad de arriba, y de espaldas casi toda.
    - Camiseta rayada: la piel gruesa entre la cabeza y el pantalón, en franjas blanco / azul que
      siguen la diagonal de la perspectiva. Los brazos (finos) quedan con piel.
    - Algas que cuelgan del borde de abajo del cuerpo, gotas que cambian de lugar en cada cuadro
      de la animación y tres percebes en el cuerpo."""
    w = 32
    n = w * w

    def near(i):
        x, y = i % w, i // w
        for dx, dy in CARD4:
            if 0 <= x + dx < w and 0 <= y + dy < w:
                yield (y + dy) * w + x + dx

    out = []
    for index, (orig, new) in enumerate(zip(original, recolored)):
        anim, direction = index // 4, index % 4
        new = list(new)
        parts = [crypt_shambler_part(p) for p in orig]
        skin = {i for i, part in enumerate(parts) if part == "skin"}
        core = [i for i in skin if all(j in skin for j in near(i))]
        blobs = [c for c in clusters({(i % w, i // w) for i in core}) if len(c) >= 5]
        head = set()
        if blobs:
            top = min(blobs, key=lambda c: min(y for _x, y in c))
            head = {y * w + x for x, y in top}
            head |= {j for i in list(head) for j in near(i) if j in skin}
            ys = [i // w for i in head]
            share = 0.7 if direction == 0 else 0.45               # de espaldas el pañuelo tapa más
            cut = min(ys) + max(1, int((max(ys) - min(ys) + 1) * share))
            for i in head:
                if i // w <= cut:
                    new[i] = gradient(BANDANA, luma(orig[i]) * 1.15) + (255,)
        pants = [i for i, part in enumerate(parts) if part == "pants"]
        if head and pants:
            head_bottom, pants_top = max(i // w for i in head), min(i // w for i in pants)
            around_head = head | {j for i in head for j in near(i)}
            for i, part in enumerate(parts):
                y = i // w
                if not (head_bottom < y <= pants_top) or part not in ("skin", "wound") or i in around_head:
                    continue
                if sum(1 for j in near(i) if parts[j] in ("skin", "wound")) < 3:   # brazo fino
                    continue
                stripe = ((y + (i % w) // 3) // 2) % 2
                new[i] = gradient(SHIRT_WHITE if stripe == 0 else NAVY, luma(orig[i]) * (1.3 if stripe == 0 else 1.5)) + (255,)

        opaque = {i for i, p in enumerate(orig) if p[3]}
        bottom = sorted(i for i in opaque if i + w < n and i + w not in opaque)
        lowest = max(i // w for i in opaque)
        weeds = [i for i in bottom if i // w < lowest - 5 and ((i % w) * 7 + (i // w) * 13 + direction * 3) % 9 == 0]
        for i in weeds[:4]:
            length = 2 + (i * 5 + anim) % 3
            for k in range(1, length + 1):
                j = i + w * k
                if j < n and j not in opaque:
                    new[j] = SEAWEED[min(2, k - 1)] if k < length else SEAWEED[2]
        drops = [i for i in bottom if ((i % w) * 3 + i // w + anim * 5 + direction) % 11 == 0][:2]
        for i in drops:
            j = i + w * (2 + anim % 2)
            if j < n and j not in opaque:
                new[j] = DRIP_LIGHT
                if j + w < n and j + w not in opaque:
                    new[j + w] = DRIP_DARK
        body = [i for i in core if i not in head and parts[i] == "skin"]
        for i in body[::max(1, len(body) // 3)][:3]:
            new[i] = BARNACLE_LIGHT
            if i + 1 in opaque:
                new[i + 1] = BARNACLE_DARK
        out.append(new)
    return out


PRESET = dict(name="Drowned Sailor", source=100, target=233, recolor=recolor_drowned,
              frames_post=drowned_sailor_details, parts=crypt_shambler_part)
