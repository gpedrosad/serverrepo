"""Private 3D masonry/metal material for the main bridge; other docks stay wooden."""
import importlib.util
from pathlib import Path


def material():
    spec = importlib.util.spec_from_file_location('ironbound_drawing', Path(__file__).with_name('dock_bridge_art.py'))
    d = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(d)
    stone = ((81, 94, 109), (49, 61, 77), (28, 38, 53))
    dark = ((31, 41, 55), (20, 29, 41), (12, 19, 29))
    coping = ((181, 193, 194), (112, 133, 143), (66, 88, 103))
    bronze = ((207, 155, 77), (135, 89, 43), (81, 50, 25))
    d.GLASS_S, d.GLASS_E = (255, 232, 149), (242, 166, 60)
    d.OUTLINE = (12, 20, 29)

    def rail_line(axis, fixed, a, b, posts):
        boxes = []
        def box(p0, p1, q0, q1, h0, h1, colors):
            args = (p0, p1, q0, q1) if axis == 'x' else (q0, q1, p0, p1)
            boxes.append(d.Box(*args, h0, h1, *colors))
        box(a, b, fixed, fixed + 4, 0, 9, dark)
        for row, shift in ((0, 0), (4, 8)):
            for start in range(a - shift, b, 16):
                lo, hi = max(a, start + 1), min(b, start + 16)
                if lo < hi:
                    box(lo, hi, fixed, fixed + 4, row + 1, row + 4, stone)
        box(a, b, fixed - 1, fixed + 5, 8, 11, coping)
        for p in posts[::2]:
            box(p - 1, p + 2, fixed + 1, fixed + 4, 11, 17, dark)
            box(p - 2, p + 3, fixed, fixed + 5, 12, 14, bronze)
        box(a, b, fixed, fixed + 4, 16, 18, bronze)
        return boxes

    def newel(x, y, lantern):
        boxes = [d.Box(x, x + 6, y, y + 6, 0, 14, *stone),
                 d.Box(x, x + 6, y, y + 6, 3, 5, *bronze),
                 d.Box(x - 1, x + 7, y - 1, y + 7, 14, 17, *coping)]
        if lantern:
            boxes += [d.Box(x, x + 6, y, y + 6, 17, 25, d.GLASS_S, d.GLASS_S, d.GLASS_E),
                      d.Box(x - 1, x + 7, y - 1, y + 7, 25, 27, *dark)]
        else:
            boxes.append(d.Box(x + 1, x + 5, y + 1, y + 5, 17, 19, *bronze))
        return boxes

    d.rail_line, d.newel = rail_line, newel
    d.STONE, d.DARK, d.COPING, d.BRONZE = stone, dark, coping, bronze
    return d
