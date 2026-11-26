"""A fractured crown and a swinging brass funeral lantern. See CALDERA_AZUL.md."""
from azure_ornaments import lich as detail
from sprite_kit import parts_by_rules

parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("gray", lambda h, s, v: v >= 0.13 and s < 0.18),
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("yellow", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.11 <= h < 0.20),
    ("green", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.20 <= h < 0.45),
    ("rest", None),
)


palettes = {
    "gray": [(30, 32, 58), (130, 140, 190), (240, 244, 255)],
    "orange": [(49, 30, 42), (126, 68, 66), (238, 177, 113)],
    "green": [(19, 50, 60), (42, 127, 151), (120, 211, 212)],
    "yellow": [(62, 40, 44), (154, 106, 80), (230, 181, 120)],
    "rest": [(25, 23, 43), (63, 51, 84), (128, 103, 138)],
}


PRESET = dict(name="Azure Lich", source=99, target=148, parts=parts, palettes=palettes, detail=detail)
