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


def apply_river_style(cells, reference, otb, floor, helpers, spawn_positions):
    before = {p: list(ids) for p, ids in cells.items()}
    reserve = {(x, y) for (x, y, z), ids in cells.items() if z == 12 and 1386 in ids}
    reserve = {(x + dx, y + dy) for x, y in reserve
               for dx in range(-3, 4) for dy in range(-3, 4)}
    plant_reserve = reserve | set(spawn_positions)
    eligible = {p for p in floor - reserve
                if all((p[0] + dx, p[1] + dy) in floor for dx, dy in helpers.ALL8)}
    water = set()
    for x in range(146, 197, 2):
        for y in range(20, 77, 2):
            block = {(x + dx, y + dy) for dx in (0, 1) for dy in (0, 1)}
            if block <= eligible and any(((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 < 1
                                         for cx, cy, rx, ry in POOLS):
                water |= block
    water = helpers.fix_until_valid(water, eligible, SHORE_SIDE, SHORE_CORNER, SHORE_INNER, single=True)
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
            if z == 10 and y in range(60, 68):
                ids[0] = WATER if x == 175 else 4633
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
        if z == 12 and (x, y) not in water and len(ids) > 1 and any(
                "block_solid" in otb[i]["flags"] for i in ids[1:]):
            ids[0] = SAND
        if coral:
            ids.append(coral)

    plants = []
    for p in sorted(floor - plant_reserve, key=lambda p: (p[1], p[0])):
        x, y = p
        ids = cells[x, y, 12]
        if len(ids) != 1 or (x * 17 + y * 23) % 11 or any(
                abs(x - px) + abs(y - py) < 4 for px, py in plants):
            continue
        if p in water or p in shores:
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
    return {"style": "river-shallows-v2", "shallowWater": len(water),
            "shoreTiles": len(shores), "reefPlants": len(plants)}
