"""Mini Trainer Monk: Monk (57, guardado 2x2) -> look 237. Túnica de aprendiz verde bosque, cordón de
cuerda clara y dos parches cosidos. Doc: docs/gameplay/PRIVATE_TRAINER_DUMMY.md.
"""
from sprite_kit import *  # noqa: F401,F403


FOREST = [(0, (6, 18, 12)), (0.25, (22, 56, 34)), (0.5, (44, 98, 56)), (0.75, (88, 148, 84)),
          (1, (176, 214, 142))]
ROPE = [(0, (120, 100, 66)), (1, (244, 234, 204))]
PATCH = [(0, (90, 62, 34)), (0.5, (160, 118, 70)), (1, (214, 176, 118))]


def recolor_novice_monk(pixel):
    """Mini Trainer Monk: túnica de aprendiz verde bosque con cordón de cuerda clara."""
    part = monk_part(pixel)
    if part in (None, "skin"):
        return pixel
    lum = luma(pixel)
    if part == "belt":
        return gradient(ROPE, (lum - 0.55) / 0.4) + (255,)
    return gradient(FOREST, (lum ** 0.8) * 1.3) + (255,)


def novice_monk_details(original, recolored):
    """Dos parches de tela cosidos en la túnica (posición relativa a la silueta de cada cuadro)."""
    out = []
    for orig, new in zip(original, recolored):
        new = list(new)
        robe = {(i % 64, i // 64) for i, px in enumerate(orig) if monk_part(px) == "robe"}
        if robe:
            xs = [x for x, _ in robe]
            ys = [y for _, y in robe]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            for fx, fy in ((0.4, 0.55), (0.66, 0.8)):
                cx, cy = int(x0 + (x1 - x0) * fx), int(y0 + (y1 - y0) * fy)
                cells = [(cx + dx, cy + dy) for dx in range(-2, 2) for dy in range(-2, 2)]
                if all(c in robe for c in cells):
                    for x, y in cells:
                        corner = x in (cx - 2, cx + 1) and y in (cy - 2, cy + 1)
                        edge = x in (cx - 2, cx + 1) or y in (cy - 2, cy + 1)
                        lum = luma(orig[y * 64 + x])
                        if corner:
                            col = (70, 46, 26)                          # puntada
                        else:
                            col = gradient(PATCH, lum * 1.5 + (0.0 if edge else 0.15))
                        new[y * 64 + x] = col + (255,)
        out.append(new)
    return out


PRESET = dict(name="Mini Trainer Monk", source=57, target=237, recolor=recolor_novice_monk,
              frames_post=novice_monk_details, parts=monk_part)
