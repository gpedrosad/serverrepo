"""Glass buckler, ridged pauldron and bone-white limbs. See CALDERA_AZUL.md."""
from azure_ornaments import skeleton as detail
from sprite_kit import parts_by_rules

parts = parts_by_rules(
    ("dark", lambda h, s, v: v < 0.13),
    ("gray", lambda h, s, v: v >= 0.13 and s < 0.18),
    ("red", lambda h, s, v: v >= 0.13 and s >= 0.18 and (h < 0.04 or h >= 0.95)),
    ("rest", None),
)


palettes = {
    "red": [(20, 31, 52), (36, 102, 121), (137, 221, 224)],
    "dark": [(0, 0, 0), (3, 4, 16), (10, 14, 44)],
    "gray": [(41, 48, 65), (124, 136, 152), (210, 213, 199), (248, 243, 217)],
}


PRESET = dict(name="Azure Skeleton", source=37, target=145, parts=parts, palettes=palettes, detail=detail)
