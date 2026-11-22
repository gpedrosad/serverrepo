"""Native river-grotto palette. Preserve every tile's collision and all shaft links."""
from hole_entrance_style import HOLES, style_cells
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "client-rme"))
from river_grotto_assets import SKINS

SAND, GRAVEL, WATER, WISP = 231, 104, 3258, 1397
SHORE_SIDE = {"n": 4632, "w": 4633, "s": 4634, "e": 4635}
# Native corner pictures are copied into nonblocking decorative skins.
SHORE_CORNER = {("s", "e"): 4636, ("s", "w"): 4637,
                ("n", "e"): 4638, ("n", "w"): 4639}
SHORE_INNER = {"se": 4640, "sw": 4641, "ne": 4642, "nw": 4643}
# Centers follow the existing serpent; these are visual shallows, never new paths.
POOLS = ((164, 68, 10, 3.2), (154, 60, 3.2, 8), (172, 54, 13, 3.2),
         (188, 46, 3.2, 9), (174, 40, 12, 3.2), (154, 31, 3.2, 8), (176, 26, 13, 3.2))


def collision(ids, otb):
    return (any(otb[i]["group"] == "ground" for i in ids),
            frozenset(f for i in ids for f in otb[i]["flags"]
                      if f.startswith(("block_", "floorchange_"))))


def clean_shallows(water, floor, helpers):
    """Shrink shores into valid single pieces; never grow into a dry reserve."""
    water = set(water)
    while water:
        thin = {p for p in water if any(
            all((p[0] + dx, p[1] + dy) not in water for dx, dy in axis)
            for axis in (((1, 0), (-1, 0)), ((0, 1), (0, -1))))}
        water -= thin
        bad = {p for p in floor - water if (pieces := helpers.pieces_for(
            helpers.neighbors_in(water, *p), SHORE_SIDE, SHORE_CORNER, SHORE_INNER)) is None
            or len(pieces) > 1}
        remove = {(x + dx, y + dy) for x, y in bad for dx, dy in helpers.ALL8} & water
        if not thin and not remove:
            break
        water -= remove
    # Tiny isolated pools read as broken terrain rather than a river.
    pending = set(water)
    while pending:
        component, todo = set(), [min(pending)]
        while todo:
            p = todo.pop()
            if p not in pending:
                continue
            pending.remove(p)
            component.add(p)
            todo.extend((p[0] + dx, p[1] + dy) for dx, dy in helpers.CARD)
        if len(component) < 12:
            water -= component
    return water


def apply_river_style(cells, reference, otb, floor, helpers, spawn_positions):
    before = {p: list(ids) for p, ids in cells.items()}
    reserve = {(x, y) for (x, y, z), ids in cells.items() if z == 12 and 1386 in ids}
    reserve = {(x + dx, y + dy) for x, y in reserve
               for dx in range(-3, 4) for dy in range(-3, 4)}
    # The complete arrival corridor stays dry; oversized rocks also need room
    # for their NW sprite footprint and an uninterrupted shoreline around it.
    reserve |= {p for p in floor if p[1] >= 60}
    plant_reserve = reserve | set(spawn_positions)
    rocks = {(x, y) for (x, y, z), ids in before.items() if z == 12
             and any("block_solid" in otb[i]["flags"] for i in ids[1:])}
    rock_reserve = {(x + dx, y + dy) for x, y in rocks
                    for dx in range(-2, 3) for dy in range(-2, 3)}
    dry_margin = {(x + dx, y + dy) for x, y in reserve
                  for dx in range(-1, 2) for dy in range(-1, 2)}
    eligible = {p for p in floor - dry_margin - rock_reserve
                if all((p[0] + dx, p[1] + dy) in floor for dx, dy in helpers.ALL8)}
    water = set()
    for x in range(146, 197, 2):
        for y in range(20, 77, 2):
            block = {(x + dx, y + dy) for dx in (0, 1) for dy in (0, 1)}
            if block <= eligible and any(((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 < 1
                                         for cx, cy, rx, ry in POOLS):
                water |= block
    water = clean_shallows(water, floor, helpers)
    shores = {}
    for p in floor - water:
        pieces = helpers.pieces_for(helpers.neighbors_in(water, *p),
                                    SHORE_SIDE, SHORE_CORNER, SHORE_INNER)
        assert pieces is not None and len(pieces) <= 1, ("Ambiguous shore", p, pieces)
        if pieces:
            shores[p] = pieces[0]

    for (x, y, z), ids in cells.items():
        if not 8 <= z <= 12 or otb[ids[0]]["group"] != "ground":
            continue
        if ids[0] in HOLES or "block_solid" in otb[ids[0]]["flags"]:
            continue
        if z == 12:
            ids[0] = WATER if (x, y) in water else shores.get((x, y), SAND)
        else:
            ids[0] = GRAVEL
        coral = None
        for i, sid in enumerate(ids[1:], 1):
            if sid == 1423:
                ids[i] = WISP
            elif sid == 2602:
                ids[i] = 1285
                coral = 4138 if (x + y) % 2 else 4139
            elif sid == 3767:
                ids[i] = (1285, 1309, 1353, 2772)[(x * 3 + y) % 4]
            elif sid == 2248:
                ids[i] = 1336
        if coral and z == 12 and (x, y) not in plant_reserve:
            ids.append(coral)

    wet = water | set(shores)
    wet_buffer = {(x + dx, y + dy) for x, y in wet
                  for dx in range(-1, 2) for dy in range(-1, 2)}
    for x, y in wet:
        ids = cells[x, y, 12]
        assert not any("block_solid" in otb[i]["flags"] for i in ids[1:]), (x, y, ids)
        # Old nonblocking bones/mushrooms must not show through the water either.
        ids[1:] = []
    plants = []
    for p in sorted(floor - plant_reserve - wet_buffer, key=lambda p: (p[1], p[0])):
        x, y = p
        ids = cells[x, y, 12]
        if len(ids) != 1 or (x * 17 + y * 23) % 11 or any(
                abs(x - px) + abs(y - py) < 4 for px, py in plants):
            continue
        ids.append((4138, 4139)[(x + y) % 2])
        plants.append(p)

    # The entry is in a dirt road. Neighboring legacy grass-edge names mislead the vote.
    style_cells(cells, reference, otb)
    cells[176, 58, 7][0] = 383
    for p, ids in before.items():
        if 8 <= p[2] <= 12 and cells[p][0] in SKINS:
            skin = SKINS[cells[p][0]]
            cells[p][0] = ids[0]
            cells[p].insert(1, skin)
        assert collision(ids, otb) == collision(cells[p], otb), ("Collision changed", p, ids, cells[p])
    assert not (water & reserve) and not (set(shores) & reserve)
    assert all(cells[x, y, 12][1:] == [SKINS[WATER if (x, y) in water else shores[x, y]]]
               for x, y in wet), "Decoration on the water or shoreline"
    return {"style": "river-shallows-v3-dry-arrival", "shallowWater": len(water),
            "shoreTiles": len(shores), "reefPlants": len(plants)}
