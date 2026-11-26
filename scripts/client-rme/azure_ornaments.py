"""Directional pixel artwork for the five Azure Caldera outfits."""
from __future__ import annotations

INK = "#182032"
DARK = "#263449"
TEAL = "#295b72"
GLASS = "#388da3"
CYAN = "#68d1dc"
WHITE = "#d7f5eb"
BRASS_DARK = "#71444b"
BRASS = "#b97f65"
GOLD = "#ebba82"
CREAM = "#ffe3ad"


def canvas(frame):
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (frame.w, frame.w))
    image.putdata(frame.px)
    return image, ImageDraw.Draw(image)


def polygon(draw, anchor, points, color):
    x, y = anchor
    draw.polygon([(x + dx, y + dy) for dx, dy in points], fill=color)


def line(draw, anchor, points, color):
    x, y = anchor
    draw.line([(x + dx, y + dy) for dx, dy in points], fill=color)


def shard(draw, root, tip, width):
    """A shard rooted at a plate, with an opaque outline and two polished faces."""
    x, y = root
    tx, ty = tip
    skew = (tx > x) - (tx < x)
    rim = [(x - width, y), (tx, ty), (x + width, y - 2),
           (x + width - 1, y + 2), (x, y + 4), (x - width + 1, y + 2)]
    draw.polygon(rim, fill=INK)
    draw.polygon([(x - width + 1, y), (tx, ty + 2), (x + width - 1, y - 2),
                  (x + width - 2, y + 2), (x, y + 3)], fill=TEAL)
    draw.polygon([(x - width + 1, y), (tx, ty + 2), (x + skew, y + 1), (x, y + 2)],
                 fill=GLASS)
    draw.line([(tx, ty + 2), (x - width + 2, y - 1)], fill=CYAN)
    draw.point((tx, ty + 2), fill=WHITE)


def skeleton(frame):
    image, draw = canvas(frame)
    shift = (0, -1, 0)[frame.anim]
    shoulder_x, shoulder_y = ((14, 11), (11, 12), (11, 10), (13, 12))[frame.direction]
    shoulder = shoulder_x, shoulder_y + shift
    polygon(draw, shoulder, [(-5, 1), (-4, -3), (0, -5), (3, -4), (5, -1),
                             (4, 3), (0, 5), (-3, 4)], INK)
    polygon(draw, shoulder, [(-4, 1), (-3, -2), (0, -4), (3, -3), (4, 0),
                             (3, 2), (0, 4), (-2, 3)], DARK)
    line(draw, shoulder, [(-3, -1), (0, -4), (3, -3), (4, -1)], "#afc0c5")
    line(draw, shoulder, [(-1, 2), (1, 1), (3, -1)], TEAL)

    # Elongated crystal buckler on the near forearm. Each pose shows a different facet.
    bx, by = ((10, 18), (13, 17), (7, 16), (7, 18))[frame.direction]
    by += (0, -2, 1)[frame.anim]
    shield = bx, by
    lean = (1, 1, -1, -1)[frame.direction]
    polygon(draw, shield, [(-5, -3), (-1, -6), (4, -4), (5, -1), (3, 4),
                            (lean, 8), (-3, 5), (-5, 1)], INK)
    polygon(draw, shield, [(-4, -3), (-1, -5), (3, -3), (4, 0), (2, 4),
                            (lean, 7), (-2, 4), (-4, 0)], TEAL)
    polygon(draw, shield, [(-4, -3), (-1, -5), (1, -3), (0, 1), (lean, 7),
                            (-2, 4), (-4, 0)], GLASS)
    line(draw, shield, [(-3, -3), (-1, -5), (2, -3)], WHITE)
    line(draw, shield, [(-2, 2), (0, 0), (2, -1)], CYAN)
    draw.point((bx, by), fill=WHITE)
    frame.px[:] = list(image.getdata())


WINGS = (
    (((12, 16), (7, 9), (2, 7), (1, 1), (9, 4), (14, 7), (17, 12)),
     ((15, 13), (21, 6), (30, 1), (28, 9), (24, 10), (23, 17), (20, 15), (17, 18))),
    (((17, 16), (13, 6), (9, 1), (16, 3), (23, 7), (24, 11)),
     ((19, 17), (22, 9), (31, 2), (29, 10), (27, 12), (30, 14), (26, 16), (25, 21))),
    (((13, 16), (9, 11), (3, 10), (1, 3), (8, 5), (13, 8), (16, 12)),
     ((17, 12), (23, 5), (30, 2), (29, 10), (25, 10), (28, 14), (23, 14), (22, 19))),
    (((12, 15), (7, 11), (3, 12), (1, 4), (6, 5), (11, 9)),
     ((16, 15), (22, 7), (29, 2), (30, 5), (27, 10), (30, 12), (25, 14), (23, 19))),
)


def devil(frame):
    from PIL import Image, ImageDraw

    body, _ = canvas(frame)
    wings = Image.new("RGBA", body.size)
    draw = ImageDraw.Draw(wings)
    wing_beat = (0, -1, 1)[frame.anim]
    for i, wing in enumerate(WINGS[frame.direction]):
        points = [(x, y + (wing_beat if y <= 11 else 0)) for x, y in wing]
        draw.polygon(points, fill=("#343655", "#435276")[i], outline=INK)
        root, ridge, *tips = points
        draw.line([root, ridge, tips[0], tips[1]], fill=GLASS)
        draw.line([ridge, tips[0], tips[1]], fill=CYAN)
        draw.line([root, tips[-2]], fill="#587ca0")
        draw.point(tips[1], fill=WHITE)

    wings.alpha_composite(body)
    draw = ImageDraw.Draw(wings)
    # The near membrane crosses the shoulder so it stays visible over the body.
    anchor = (21 if frame.direction == 0 else 22), 11 + wing_beat
    polygon(draw, anchor, [(-6, 6), (-5, -1), (-1, -6), (7, -10), (9, -10),
                           (8, -5), (4, -2), (7, 2), (2, 2), (4, 6), (0, 5),
                           (-3, 9)], INK)
    polygon(draw, anchor, [(-5, 5), (-4, 0), (0, -5), (8, -9), (7, -5),
                           (3, -2), (5, 1), (1, 1), (2, 5), (-1, 4),
                           (-3, 7)], "#50668a")
    polygon(draw, anchor, [(-4, 5), (-3, 1), (1, -5), (7, -8), (5, -5), (1, -2),
                           (1, 1), (-2, 3)], "#638aa8")
    line(draw, anchor, [(-5, 4), (-4, 0), (0, -5), (8, -9)], CYAN)
    line(draw, anchor, [(0, -4), (-1, 0), (1, 1)], TEAL)
    line(draw, anchor, [(-3, 6), (-1, 3), (2, 5)], "#a8a1b8")
    if frame.direction != 0:
        mask_x, mask_y = ((0, 0), (12, 10), (9, 11), (9, 10))[frame.direction]
        mask = mask_x, mask_y + wing_beat
        polygon(draw, mask, [(-4, -2), (-3, -5), (0, -3), (3, -5), (4, -1),
                             (3, 3), (0, 5), (-3, 2)], INK)
        polygon(draw, mask, [(-3, -2), (-2, -3), (0, -2), (2, -3), (3, -1),
                             (2, 2), (0, 4), (-2, 2)], "#6e7289")
        line(draw, mask, [(-3, -1), (-1, 0), (1, 0), (3, -1)], "#b9d6d0")
        line(draw, mask, [(-2, 0), (-1, 1), (1, 1), (2, 0)], "#34526d")
        line(draw, mask, [(-2, 0), (-1, 0)], WHITE)
        if frame.direction == 2:
            line(draw, mask, [(1, 0), (2, 0)], WHITE)
    frame.px[:] = list(wings.getdata())


BONE_RIDGES = (
    (((49, 24), (45, 13), 4), ((47, 33), (40, 23), 6), ((49, 42), (44, 33), 5)),
    (((20, 43), (15, 33), 5), ((30, 39), (26, 26), 6), ((40, 43), (39, 33), 6)),
    (((48, 22), (41, 15), 4), ((45, 34), (38, 25), 5), ((51, 43), (47, 31), 6)),
    (((25, 43), (25, 33), 6), ((35, 39), (38, 26), 6), ((44, 44), (49, 35), 5)),
)


def bonebeast(frame):
    image, draw = canvas(frame)
    rise = (0, -1, 1)[frame.anim]
    for (x, y), (tx, ty), width in BONE_RIDGES[frame.direction]:
        shard(draw, (x, y + rise), (tx, ty + rise), width)
    x, y = ((56, 14), (52, 52), (53, 50), (15, 52))[frame.direction]
    sense = (1, 1, -1, -1)[frame.direction]
    y += rise
    polygon(draw, (x, y), [(-6, 1), (-5, -4), (0, -6), (5, -4), (7*sense, 0),
                           (3*sense, 4), (-3*sense, 4)], INK)
    polygon(draw, (x, y), [(-5, 0), (-4, -3), (0, -5), (4, -3), (5*sense, 0),
                           (3*sense, 3), (-3*sense, 2)], "#49677c")
    line(draw, (x, y), [(-4, -1), (0, -4), (4, -2)], "#97c4c6")
    line(draw, (x, y), [(sense, 0), (3*sense, -1)], WHITE)
    frame.px[:] = list(image.getdata())


def lich(frame):
    image, draw = canvas(frame)
    rise = (0, -2, 1)[frame.anim]
    # Crown and lamp are articulated independently with the robe's walk.
    hx, hy = ((31, 23), (28, 24), (31, 23), (30, 25))[frame.direction]
    head = hx, hy + rise
    polygon(draw, head, [(-10, -1), (-11, -10), (-6, -6), (-3, -14),
                         (1, -8), (6, -13), (7, -7), (11, -9), (9, -1), (5, 3), (-5, 3)], INK)
    polygon(draw, head, [(-9, -2), (-10, -8), (-6, -5), (-3, -12),
                         (1, -7), (5, -11), (6, -6), (10, -7), (8, -2), (4, 2), (-5, 2)], BRASS_DARK)
    line(draw, head, [(-9, -6), (-6, -4), (-3, -11), (0, -6), (3, -6), (5, -10),
                      (6, -5), (9, -6)], GOLD)
    line(draw, head, [(-6, 0), (-2, -2), (3, -2), (7, 0)], BRASS)
    draw.point((hx - 3, hy + rise - 10), fill=CREAM)
    if frame.direction != 0:
        line(draw, head, [(-3, 1), (-2, 1)], WHITE)
        if frame.direction == 2:
            line(draw, head, [(2, 1), (3, 1)], WHITE)

    lx, ly = ((14, 23), (36, 14), (46, 24), (16, 37))[frame.direction]
    lantern = lx + (0, 1, -1)[frame.anim], ly + rise
    polygon(draw, lantern, [(-7, -3), (-4, -7), (0, -10), (4, -7), (7, -3),
                            (6, 5), (2, 8), (-2, 8), (-6, 5)], INK)
    polygon(draw, lantern, [(-6, -3), (-3, -6), (0, -8), (4, -6), (6, -3),
                            (5, 4), (2, 7), (-2, 7), (-5, 4)], BRASS)
    polygon(draw, lantern, [(-4, -2), (0, -5), (4, -2), (3, 4), (0, 6), (-3, 4)], TEAL)
    polygon(draw, lantern, [(-3, 2), (-2, -1), (-1, 1), (1, -4), (2, -1),
                            (3, 1), (2, 4), (0, 5), (-2, 4)], CYAN)
    line(draw, lantern, [(0, 3), (1, 0), (1, -2)], WHITE)
    line(draw, lantern, [(-5, -3), (-3, -6), (0, -8), (3, -6)], CREAM)
    line(draw, lantern, [(-5, 4), (-2, 7), (2, 7), (5, 4)], GOLD)
    frame.px[:] = list(image.getdata())


def azhurak(frame):
    image, draw = canvas(frame)
    rise = (0, -1, 1)[frame.anim]
    # Upright basalt fins and a large, banded near-side pauldron.
    ax, ay = ((34, 24), (39, 17), (37, 19), (29, 17))[frame.direction]
    plate = ax, ay + rise
    shard(draw, (ax + 14, ay + rise + 1), (min(63, ax + 25), ay + rise - 12), 6)
    polygon(draw, plate, [(-13, 2), (-12, -5), (-14, -13), (-10, -11),
                          (-5, -19), (-2, -12), (4, -15), (7, -12), (8, -7),
                          (13, -5), (15, 0), (13, 7), (9, 12), (2, 12),
                          (-5, 9), (-10, 6)], INK)
    polygon(draw, plate, [(-11, 2), (-10, -5), (-12, -11), (-7, -8),
                          (-5, -17), (-1, -10), (4, -13), (6, -11), (7, -6),
                          (12, -4), (14, 0), (12, 7), (8, 11), (2, 11), (-5, 8), (-9, 5)],
              "#3c3046")
    polygon(draw, plate, [(-10, 0), (-8, -5), (-4, -9), (2, -9), (8, -6),
                          (12, -2), (10, 3), (6, 7), (0, 8), (-6, 5)], "#615067")
    line(draw, plate, [(-10, 0), (-8, -5), (-4, -9), (2, -9), (9, -6), (12, -3)], GOLD)
    line(draw, plate, [(-9, 2), (-5, 6), (0, 8), (7, 7), (12, 3), (13, 0)], BRASS)
    line(draw, plate, [(-9, -4), (-5, -17), (-2, -11)], GLASS)
    line(draw, plate, [(1, -10), (4, -13), (7, -8)], CYAN)
    line(draw, plate, [(-6, -2), (-2, -5), (3, -5), (8, -2), (5, 0)], BRASS)
    line(draw, plate, [(-5, 2), (0, 5), (5, 4), (9, 1)], BRASS_DARK)
    polygon(draw, plate, [(-3, -1), (1, -4), (5, -1), (2, 4), (0, 4)], INK)
    polygon(draw, plate, [(-1, -1), (1, -3), (3, -1), (2, 2), (0, 3)], GLASS)
    line(draw, plate, [(0, 1), (1, -2), (2, -1)], WHITE)
    draw.point((ax + 9, ay + rise - 5), fill=CREAM)

    hx, hy = ((18, 7), (25, 13), (18, 11), (15, 12))[frame.direction]
    horn_y = max(7, hy + rise)
    shard(draw, (hx - 4, horn_y), (hx - 8, max(0, horn_y - 10)), 4)
    shard(draw, (hx + 6, horn_y - 1), (hx + 10, max(0, horn_y - 10)), 4)
    frame.px[:] = list(image.getdata())
