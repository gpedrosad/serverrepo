"""Paleta de Dark Spider sobre los cuadros de Giant Spider del cliente."""

from sprite_kit import gradient, hsv, luma

OBSIDIAN = (
    (0, (0, 0, 0)), (0.15, (17, 15, 24)), (0.35, (39, 33, 52)),
    (0.60, (73, 65, 91)), (0.82, (115, 105, 130)), (1, (172, 161, 181)),
)
EMBER = (
    (0, (32, 6, 15)), (0.35, (101, 15, 37)), (0.65, (185, 34, 54)),
    (0.85, (235, 65, 64)), (1, (255, 140, 90)),
)
EYES = (
    (0, (72, 9, 32)), (0.45, (180, 29, 52)),
    (0.72, (255, 100, 80)), (1, (255, 210, 163)),
)


def recolor(pixel):
    alpha = pixel[3]
    if not alpha:
        return pixel
    hue, saturation, value = hsv(pixel)
    if 0.24 < hue < 0.48 and saturation > 0.35 and value > 0.18:
        rgb = gradient(EYES, (value - 0.15) * 1.75)
    elif 0.10 <= hue < 0.20 and saturation > 0.55 and value > 0.35:
        rgb = gradient(EMBER, value)
    elif (hue < 0.045 or hue > 0.96) and saturation > 0.70 and value > 0.25:
        rgb = gradient(EMBER, value * 0.78)
    else:
        light = (0.72 * luma(pixel) + 0.28 * value) ** 0.90
        rgb = gradient(OBSIDIAN, light)
    return (*rgb, alpha)


PRESET = dict(name="Dark Spider", source=38, target=190, recolor=recolor)
