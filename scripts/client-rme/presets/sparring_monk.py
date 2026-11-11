"""Trainer Monk: Monk (57, guardado 2x2) -> look 236. Gambesón de entrenamiento color lino con costuras
en rombo, capucha roja y cinturón negro con puntas rojas. Doc: docs/gameplay/PRIVATE_TRAINER_DUMMY.md.
"""
from sprite_kit import *  # noqa: F401,F403


LINEN = [(0, (40, 30, 26)), (0.25, (112, 96, 78)), (0.5, (178, 160, 128)), (0.75, (226, 212, 178)),
         (1, (252, 246, 224))]
HOOD_RED = [(0, (40, 6, 10)), (0.3, (104, 16, 22)), (0.6, (170, 36, 36)), (1, (236, 100, 84))]
BLACK_BELT = [(0, (16, 14, 20)), (0.6, (44, 40, 50)), (1, (98, 92, 108))]


def _darker(pixel, k):
    r, g, b, _a = pixel
    return (int(r * k), int(g * k), int(b * k), 255)


def recolor_sparring_monk(pixel):
    """Trainer Monk: gambesón de entrenamiento color crudo y cinturón negro (la capucha va aparte)."""
    part = monk_part(pixel)
    if part in (None, "skin"):
        return pixel
    if part == "outline":
        return _darker(pixel, 0.8)
    lum = luma(pixel)
    if part == "belt":
        return gradient(BLACK_BELT, (lum - 0.55) / 0.4) + (255,)
    return gradient(LINEN, (lum ** 0.85) * 1.25) + (255,)


def _hood(orig):
    """Píxeles de túnica que forman la capucha: el tramo de arriba a la izquierda de la silueta
    (la figura va en diagonal), medido sobre x + y."""
    robe = [i for i, px in enumerate(orig) if monk_part(px) == "robe"]
    if not robe:
        return set()
    diag = [(i % 64) + (i // 64) for i in robe]
    lo, hi = min(diag), max(diag)
    return {i for i, d in zip(robe, diag) if d <= lo + (hi - lo) * 0.3}


def sparring_monk_details(original, recolored):
    """Capucha roja acolchada, costuras en rombo del gambesón y puntas rojas del cinturón."""
    out = []
    for orig, new in zip(original, recolored):
        new = list(new)
        hood = _hood(orig)
        for i, px in enumerate(orig):
            if monk_part(px) != "robe":
                continue
            x, y = i % 64, i // 64
            if i in hood:
                new[i] = gradient(HOOD_RED, (luma(px) ** 0.85) * 1.25) + (255,)
            elif (x + y) % 6 == 0 or (x - y) % 6 == 0:
                new[i] = _darker(new[i], 0.8)
        belt = [i for i, px in enumerate(orig) if monk_part(px) == "belt"]
        if belt:
            for i in sorted(belt, key=lambda i: (i % 64) + (i // 64))[-2:]:   # el extremo que cuelga
                new[i] = (196, 34, 38, 255)
        out.append(new)
    return out


PRESET = dict(name="Trainer Monk", source=57, target=236, recolor=recolor_sparring_monk,
              frames_post=sparring_monk_details, parts=monk_part)
