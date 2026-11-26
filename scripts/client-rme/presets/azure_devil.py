"""Angular wings and a cold porcelain mask. See CALDERA_AZUL.md."""
from azure_ornaments import devil as detail
from sprite_kit import parts_by_rules

parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("red", lambda h, s, v: v >= 0.13 and s >= 0.18 and (h < 0.04 or h >= 0.95)),
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("rest", None),
)


palettes = {
    "red": [(23, 19, 37), (57, 47, 78), (122, 103, 140), (192, 160, 167)],
    "dark": [(0, 0, 0), (4, 3, 14), (12, 10, 36)],
    "orange": [(14, 40, 80), (40, 170, 255), (190, 245, 255)],
    "rest": [(20, 20, 40), (60, 160, 220), (200, 250, 255)],
}


PRESET = dict(name="Azure Devil", source=40, target=146, parts=parts, palettes=palettes, detail=detail)
