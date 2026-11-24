#!/usr/bin/env python3
"""Duskweb Hollow: coastal trail and Dark Spider cave west of (25,128,7)."""

import argparse
import json
import math
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kb"))
from epstein_cave_repair import NP, ROCK, index
from mapdata import MAP, REPO, Renderer, load_otb, parse_tree, serialize_tree

WORLD = MAP.parent
SPAWNS = WORLD / "test-spawn.xml"
READABLES = WORLD.parent / "readables.xml"
REGISTRY = WORLD.parent / "monster/monsters.xml"
MANIFEST = WORLD / "generated-duskweb-hollow.json"
GRASS, DIRT, COAST, WATER = 4756, 103, 4526, 4609
WATERS = set(range(4608, 4626)) | {4664, 4665, 4666}
SIDES = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
CORNERS = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}
ORIGIN = (25, 128)
MOUTH, SIGN = (17, 136), (19, 135)
EXIT = (MOUTH[0], MOUTH[1] + 1)
HOLE, LADDER = 383, 1386
# The footprint follows the old shore, then extends southwest into the sea.
CAPE = (
    (18, 21, 119, 119), (15, 23, 120, 121), (13, 24, 122, 123),
    (11, 25, 124, 127), (10, 26, 128, 131), (11, 25, 132, 134),
    (12, 24, 135, 137), (13, 23, 138, 140), (14, 21, 141, 142),
    (16, 20, 143, 143),
)
TRAIL = ((33, 125), (30, 124), (27, 124), (25, 126), ORIGIN,
         (23, 130), (20, 131), (19, 133), (17, 134), MOUTH, EXIT)
SURFACE_PROPS = {
    (14, 125): (2709,), (17, 122): (2718,), (21, 123): (2706,),
    (14, 129): (2710,), (20, 127): (2700,), (16, 131): (2713,),
    (23, 132): (2705,), (14, 135): (2719,), (23, 136): (2717,),
    (15, 139): (2709,), (20, 140): (2720,),
    (15, 126): (4171,), (20, 125): (4179,), (15, 130): (2248,),
    (20, 134): (4171,), (20, 137): (1336,), (21, 138): (4179,),
    SIGN: (1429,),
}
# Chambers follow a U. Coordinates are inclusive, in two-tile blocks.
PASSAGES = (
    (14, 29, 107, 110), (12, 33, 111, 114), (12, 17, 115, 120),
    (10, 17, 121, 124), (12, 19, 125, 128), (14, 19, 129, 138),
    (28, 33, 115, 120), (30, 33, 121, 124), (28, 33, 125, 128),
    (26, 33, 129, 134), (28, 33, 135, 138), (26, 35, 139, 144),
    (28, 33, 145, 146),
)
CAVE_SPAWNS = (
    ("Tarantula", (16, 129), 130), ("Poison Spider", (13, 122), 135),
    ("Tarantula", (15, 115), 140), ("Giant Spider", (19, 110), 170),
    ("Giant Spider", (28, 110), 180), ("Tarantula", (31, 116), 150),
    ("Giant Spider", (32, 123), 185), ("Dark Spider", (29, 132), 235),
    ("Giant Spider", (32, 135), 190), ("Dark Spider", (31, 143), 255),
)
SURFACE_SPAWNS = (("Tarantula", (15, 124), 120), ("Tarantula", (20, 139), 130))


def footprints(ranges):
    return {(x, y) for x0, x1, y0, y1 in ranges for x in range(x0, x1 + 1)
            for y in range(y0, y1 + 1)}


def view(center):
    return {(x + dx, y + dy) for x, y in center for dx in range(-8, 10)
            for dy in range(-6, 8) if x + dx >= 0}


def walkable(ids, otb):
    return bool(ids) and otb[ids[0]]["group"] == "ground" and not any(
        "block_solid" in otb[i]["flags"] for i in ids
    )


def surface(values, otb, cave_floor):
    coast_ids = set(range(4644, 4656))
    dirt_edges = (NP.DIRT_SIDE, NP.DIRT_CORNER, NP.DIRT_INNER)
    dirt_ids = {sid for table in dirt_edges for sid in table.values()}
    footprint = footprints(CAPE)
    old = {(x, y): ids for (x, y, z), ids in values.items() if z == 7}
    new_land = {p for p in footprint if old.get(p, [WATER])[0] in WATERS}
    if any(old.get(p) not in (None, [WATER], [4608]) for p in new_land):
        raise ValueError("El cabo pisaría objetos existentes en el agua")
    old_coast = {p for p in old if old[p][0] == COAST and set(old[p][1:]) <= coast_ids}
    repair = {p for p in old_coast
              if NP.neighbors_in(new_land, *p)}
    join = view(footprint | {(24, 119), (24, 132), ORIGIN}) | footprints(((0, 24, 109, 153),))
    water = {p for p in join if p not in new_land and old.get(p, [WATER])[0] in WATERS}
    tiles = {p: [WATER] for p in (join | cave_floor) if p not in old}
    for p in new_land | repair:
        border = NP.pieces_for(NP.neighbors_in(water, *p), SIDES, CORNERS, INNER)
        if border is None or len(border) > 1:
            raise ValueError(f"Borde de costa ambiguo: {p} {border}")
        tiles[p] = [COAST, *border] if border else [GRASS]

    samples = set()
    for a, b in zip(TRAIL, TRAIL[1:]):
        steps = max(abs(b[0] - a[0]), abs(b[1] - a[1])) * 4
        samples.update((a[0] + (b[0] - a[0]) * i / steps,
                        a[1] + (b[1] - a[1]) * i / steps) for i in range(steps + 1))
    local = old | tiles
    can_pave = {p for p in view(TRAIL) if (ids := local.get(p))
                and ids[0] in {GRASS, DIRT} | dirt_ids and walkable(ids, otb)}
    road = {p for p in can_pave if any(math.dist(p, s) <= 1.28 for s in samples)}
    for p in road:
        tiles[p] = [DIRT, *local[p][1:]]
    road_near = {p for p in can_pave - road if local[p][0] == GRASS
                 and NP.neighbors_in(road, *p)}
    for p in road_near:
        edge = NP.pieces_for(NP.neighbors_in(road, *p), *dirt_edges)
        if edge and len(edge) == 1:
            tiles[p] = [edge[0], *local[p][1:]]
    if MOUTH not in road or EXIT not in road or ORIGIN not in road:
        raise ValueError("Falta conectar la bajada, el rellano o la posición solicitada")
    if tiles[MOUTH] != [DIRT]:
        raise ValueError("La boca tiene objetos arriba")
    tiles[MOUTH] = [HOLE]
    for p, items in SURFACE_PROPS.items():
        ids = tiles.get(p)
        if not ids or ids[0] not in {GRASS, DIRT} | dirt_ids or len(ids) != 1:
            raise ValueError(f"Decoración fuera de suelo seguro: {p} {ids}")
        if p in road:
            raise ValueError(f"Decoración sobre el sendero: {p}")
        ids.extend(items)

    merged = old | tiles
    local_walk = {p for p in join | road_near if walkable(merged.get(p), otb)} - {MOUTH}
    reached = NP.reach(local_walk, TRAIL[0], NP.CARD)
    if any(p not in reached for p in (ORIGIN, EXIT, (MOUTH[0], MOUTH[1] - 1))):
        raise ValueError("El camino no enlaza con el sendero viejo y la cueva")
    if view(p for p in new_land | road if p in local_walk) - merged.keys():
        raise ValueError("Se ve el vacío desde el cabo")
    return tiles, local_walk, new_land, road


def underground(values, otb, floor):
    walls = {(x + dx, y + dy) for x, y in floor for dx, dy in NP.ALL8} - floor
    boxes = view(floor) | footprints(((7, 39, 104, 149),))
    stone = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER
    tiles = {p: [ROCK] for p in boxes if (*p, 8) not in values}
    for p in walls:
        border = NP.pieces_for(NP.neighbors_in(floor, *p), *stone)
        if border is None or len(border) != 1:
            raise ValueError(f"Pared de cueva incompleta: {p}")
        tiles[p] = border
        if border == [357] and (p[0] * 7 + p[1] * 3) % 8 == 0:
            tiles[p].append(1906)
        if border == [359] and (p[0] * 5 + p[1]) % 7 == 0:
            tiles[p].append(1907)
    tiles.update(NP.cave_tiles(floor, floor, 251288, mud_bias=0.08))
    for p, item in {
        (15, 136): 1336, (15, 131): 2248, (11, 122): 1336, (15, 112): 2248,
        (23, 108): 1336, (32, 112): 1336, (29, 127): 2248,
        (27, 131): 2248, (32, 137): 1336, (27, 142): 2248, (32, 145): 2248,
    }.items():
        if p not in floor or "block_solid" in otb[item]["flags"]:
            raise ValueError(f"Decoración de cueva bloquea o queda afuera: {p}")
        tiles[p].append(item)
    tiles[MOUTH].append(LADDER)
    for p in floor | walls:
        if values.get((*p, 8)) not in (None, [ROCK]):
            raise ValueError(f"Rocalla de otra cueva protegida: {p}")
    near = view(floor)
    foreign_walk = {p for p in near if walkable(values.get((*p, 8)), otb)}
    if any(max(abs(x - a), abs(y - b)) < 4 for x, y in floor for a, b in foreign_walk):
        raise ValueError("La cueva quedaría pegada a otro pasaje")
    if len(NP.reach(floor, MOUTH, NP.CARD)) != len(floor) or EXIT not in floor:
        raise ValueError("El rellano o un tramo de la cueva quedó aislado")
    return tiles


def with_block(raw, key, body, close):
    text = raw.decode("latin-1")
    pattern = rf"\t<!-- BEGIN {key} -->.*?\t<!-- END {key} -->\n"
    clean, count = re.subn(pattern, "", text, flags=re.S)
    if count > 1 or key in clean or clean.count(close) != 1:
        raise ValueError(f"Bloque {key} o cierre duplicado")
    block = f"\t<!-- BEGIN {key} -->\n{body}\n\t<!-- END {key} -->\n"
    if count:
        return re.sub(pattern, lambda _: block, text, flags=re.S).encode("latin-1")
    return clean.replace(close, block + close).encode("latin-1")


def spawn_block(raw, surface_walk, cave_floor):
    registry = {e.get("name").lower(): e.get("file") for e in ET.parse(REGISTRY).getroot()}
    existing = ET.fromstring(raw)
    occupied = set()
    for center in existing.findall("spawn"):
        if center.find("monster") is None and center.find("npc") is None:
            continue
        x, y, z = (int(center.get(f"center{axis}")) for axis in "xyz")
        for e in center:
            if e.tag in {"monster", "npc"}:
                occupied.add((x + int(e.get("x")), y + int(e.get("y")), z))
    distance = NP.reach(cave_floor, MOUTH, NP.CARD)
    lines = []
    for z, entries in ((7, SURFACE_SPAWNS), (8, CAVE_SPAWNS)):
        for name, p, seconds in entries:
            x, y = p
            if name.lower() not in registry or (*p, z) in occupied:
                raise ValueError(f"Spawn desconocido u ocupado: {name} {(*p, z)}")
            if z == 8 and (distance.get(p, 0) < 6
                           or any((x + a, y + b) not in cave_floor for a in (-1, 0) for b in (-1, 0))):
                raise ValueError(f"Spawn sobre pared o cerca de la escalera: {name} {p}")
            if z == 7 and (p not in surface_walk or max(abs(x - MOUTH[0]), abs(y - MOUTH[1])) < 3):
                raise ValueError(f"Spawn exterior inválido: {name} {p}")
            occupied.add((*p, z))
            lines.extend((
                f'\t<spawn centerx="{x}" centery="{y}" centerz="{z}" radius="3">',
                f'\t\t<monster name="{name}" x="0" y="0" z="{z}" spawntime="{seconds}" />',
                "\t</spawn>",
            ))
    return "\n".join(lines)


def render(prefix, tiles, otb):
    from PIL import Image
    from game_render import Sprites, creature_image, parse_dat_all

    renderer = Renderer(otb=otb)
    _, outfits = parse_dat_all()
    sprites = Sprites()
    registry = {e.get("name").lower(): e.get("file") for e in ET.parse(REGISTRY).getroot()}
    for z, box, spawns in ((7, (5, 115, 39, 148), SURFACE_SPAWNS),
                           (8, (7, 104, 39, 149), CAVE_SPAWNS)):
        width, height, rgba = renderer.area(tiles, *box, z)
        frame = Image.frombytes("RGBA", (width, height), bytes(rgba))
        for name, (x, y), _ in spawns:
            look = ET.parse(REGISTRY.parent / registry[name.lower()]).getroot().find("look")
            sprite = creature_image({k: int(v) for k, v in look.attrib.items()}, outfits, sprites)
            if sprite is None:
                raise ValueError(f"Falta el sprite de {name}")
            frame.alpha_composite(sprite, (32 * (x - box[0] + 1) - sprite.width,
                                           32 * (y - box[1] + 1) - sprite.height))
        frame.convert("RGB").save(prefix.with_name(f"{prefix.name}-z{z}.png"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--preview", type=Path, help="Prefijo de dos PNG de vista previa (Pillow)")
    args = parser.parse_args()
    raw = MAP.read_bytes()
    tree = parse_tree(raw)
    otb = load_otb()
    nodes, values, areas = index(tree, otb)
    prior = json.loads(MANIFEST.read_text())["tiles"] if MANIFEST.exists() else {}
    baseline = values.copy()
    for key, (before, after) in prior.items():
        p = tuple(map(int, key.split(",")))
        if values.get(p) != after:
            raise ValueError(f"Otra edición modificó {p}")
        if before is None:
            baseline.pop(p)
        else:
            baseline[p] = before

    floor = footprints(PASSAGES)
    surf, surface_walk, new_land, road = surface(baseline, otb, floor)
    cave = underground(baseline, otb, floor)
    all_tiles = {(*p, z): ids for z, layer in ((7, surf), (8, cave)) for p, ids in layer.items()}
    changes = {p: ids for p, ids in all_tiles.items() if baseline.get(p) != ids}
    changed = {p: ids for p, ids in changes.items() if values.get(p) != ids}
    if any(tuple(map(int, key.split(","))) not in changes for key in prior):
        raise ValueError("El plano dejaría casillas de una versión anterior sin administrar")
    for p in changed:
        candidates = nodes.get(p, [])
        if len(candidates) > 1:
            raise ValueError(f"Casilla duplicada: {p}")
        for kind, props, children in candidates:
            simple = len(props) == 2 or (len(props) == 5 and props[2] == 9)
            if kind != 5 or not simple or any(t != 6 or len(a) != 2 or c for t, a, c in children):
                raise ValueError(f"Casa, flags o atributos protegidos: {p}")

    spawn_raw = SPAWNS.read_bytes()
    spawn_key = "DUSKWEB_HOLLOW_SPAWNS"
    other_spawns = re.sub(rb"\t<!-- BEGIN DUSKWEB_HOLLOW_SPAWNS -->.*?\t<!-- END DUSKWEB_HOLLOW_SPAWNS -->\n",
                         b"", spawn_raw, flags=re.S)
    spawn_data = with_block(spawn_raw, spawn_key, spawn_block(other_spawns, surface_walk, floor), "</spawns>")
    sign_raw = READABLES.read_bytes()
    sign = (f'\t<readable x="{SIGN[0]}" y="{SIGN[1]}" z="7" text="DUSKWEB HOLLOW\\n'
            'Tarantulas along the coast. Giant Spiders and Dark Spiders below. Level 65+."/>')
    sign_data = with_block(sign_raw, "DUSKWEB_HOLLOW_SIGN", sign, "</readables>")
    merged = values | changes
    if any(p not in merged or otb[merged[p][0]]["group"] != "ground"
           for p in ((*p, 7) for p in floor)):
        raise ValueError("Quedó vacío en la cubierta de la cueva")
    if any((*p, 8) not in merged for p in view(floor)):
        raise ValueError("Quedó vacío visible abajo")
    print(json.dumps(dict(new_land=len(new_land), road=len(road), cave_floor=len(floor),
                          changed=len(changed), spawns_changed=spawn_data != spawn_raw,
                          creatures=len(SURFACE_SPAWNS) + len(CAVE_SPAWNS))))
    if args.preview:
        render(args.preview, merged, otb)
    if not args.apply or (not changed and spawn_data == spawn_raw and sign_data == sign_raw):
        return

    backup = REPO / "backups/map" / ("duskweb-hollow-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    for file in (MAP, SPAWNS, READABLES, MANIFEST):
        if file.exists():
            shutil.copy2(file, backup / file.name)
    for p, ids in sorted(changed.items()):
        x, y, z = p
        bx, by = x // 256 * 256, y // 256 * 256
        new_tile = NP.new_tile_node(x, y, bx, by, ids)
        if p in nodes:
            nodes[p][0][:] = new_tile
        else:
            areas[bx, by, z][2].append(new_tile)
    MAP.write_bytes(serialize_tree(tree, raw[:4]))
    SPAWNS.write_bytes(spawn_data)
    READABLES.write_bytes(sign_data)
    manifest = {",".join(map(str, p)): [baseline.get(p), ids] for p, ids in sorted(changes.items())}
    MANIFEST.write_text(json.dumps(dict(entry=[*MOUTH, 7], tiles=manifest), separators=(",", ":")) + "\n")
    print(f"Respaldo: {backup.relative_to(REPO)}")


if __name__ == "__main__":
    main()
