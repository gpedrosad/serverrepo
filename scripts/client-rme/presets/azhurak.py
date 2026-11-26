"""Crowned basalt horns and a massive asymmetrical pauldron. See CALDERA_AZUL.md."""
from azure_ornaments import azhurak as detail
from sprite_kit import parts_by_rules

parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("red", lambda h, s, v: v >= 0.13 and s >= 0.18 and (h < 0.04 or h >= 0.95)),
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("yellow", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.11 <= h < 0.20),
    ("rest", None),
)


palettes = {
    "red": [(23, 18, 38), (65, 42, 72), (116, 76, 101), (175, 128, 139)],
    "dark": [(2, 0, 8), (10, 4, 24), (20, 12, 40)],
    "orange": [(54, 37, 49), (141, 92, 86), (226, 181, 133)],
    "yellow": [(20, 60, 110), (80, 200, 255), (220, 255, 255)],
    "rest": [(10, 40, 90), (60, 210, 255), (230, 255, 255)],
}


PRESET = dict(name="Azhurak", source=35, target=149, parts=parts, palettes=palettes, detail=detail)
