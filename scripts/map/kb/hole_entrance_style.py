"""Native entrance variants by terrain. Shared by generators and the map review pass."""
from collections import Counter

HOLES = frozenset((294, 383, 469, 470, 479, 480, 482, 484, 485, 489, 20368))
STYLE = {"grass": 470, "soil": 383, "stone": 479, "wood": 409, "sand": 482, "snow": 20368, "ice": 485}


def material(sid, otb):
    if sid in HOLES or sid in (409, 428):
        return None
    item = otb.get(sid, {})
    if item.get("group") != "ground" or "block_solid" in item.get("flags", []):
        return None
    # Several legacy names are misleading: 104 is gray gravel, 234 is pale sand.
    if sid in (104, 105, 4566):
        return "stone"
    if sid == 234:
        return "sand"
    name = item.get("name", "").lower()
    if "wooden floor" in name:
        return "wood"
    if "snow" in name:
        return "snow"
    if name == "ice":
        return "ice"
    if "grass" in name:
        return "grass"
    if "sand" in name:
        return "sand"
    if any(word in name for word in ("dirt", "mud", "earth")):
        return "soil"
    if any(word in name for word in ("stone", "marble", "pavement", "gravel", "tile", "rocks")):
        return "stone"
    return None


def choose(tiles, pos, otb, current):
    x, y, z = pos
    votes = Counter()
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if not (dx or dy):
                continue
            for sid in tiles.get((x + dx, y + dy, z), [])[:1]:
                family = material(sid, otb)
                if family:
                    votes[family] += 3 if abs(dx) + abs(dy) == 1 else 1
    if not votes:
        return current, "unknown"
    family = max(votes, key=lambda k: (votes[k], k))
    # Four inward mountain borders enclose dirt, despite their legacy "grass" names.
    cardinal = [tiles.get((x + a, y + b, z), [0])[0] for a, b in ((0, -1), (0, 1), (-1, 0), (1, 0))]
    if set(cardinal) == {110, 111, 112, 113}:
        family = "soil"
    target = STYLE[family]
    assert otb[target]["group"] == otb[current]["group"] == "ground"
    assert set(otb[target]["flags"]) == set(otb[current]["flags"]), (current, target)
    return target, family


def style_cells(cells, reference, otb):
    """Style a generator's 3D tile plan after its geometry checks, before writing its manifest."""
    merged = reference | cells
    for pos, ids in cells.items():
        for i, sid in enumerate(ids):
            if sid in HOLES:
                ids[i] = choose(merged, pos, otb, sid)[0]
