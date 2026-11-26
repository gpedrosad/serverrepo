"""Dorsal crystal plates and armored muzzle. See CALDERA_AZUL.md."""
from azure_ornaments import bonebeast as detail
from sprite_kit import parts_by_rules

parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("gray", lambda h, s, v: v >= 0.13 and s < 0.18),
    ("orange", lambda h, s, v: v >= 0.13 and s >= 0.18 and 0.04 <= h < 0.11),
    ("rest", None),
)


palettes = {
    "gray": [(33, 41, 60), (98, 119, 140), (181, 194, 182), (243, 231, 191)],
    "orange": [(29, 49, 60), (79, 106, 110), (164, 210, 194)],
    "rest": [(4, 30, 70), (40, 200, 255), (200, 255, 255)],
}


PRESET = dict(name="Azure Bonebeast", source=101, target=147, parts=parts, palettes=palettes, detail=detail)
