#!/usr/bin/env python3
"""Amplía la cueva de Necromancer y Hero de (82,117,8) en roca o vacío.

Sin --apply valida y muestra el plano de cambios, sin escribir al mapa.
"""

import argparse
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kb"))
from epstein_cave_repair import NP, ROCK, index
from mapdata import MAP, REPO, Renderer, load_otb, parse_tree, serialize_tree

SPAWN_FILE = MAP.with_name("test-spawn.xml")
MANIFEST = MAP.with_name("generated-necromancer-cave-extension.json")
MONSTERS = MAP.parent.parent / "monster/monsters.xml"
SPAWN_KEY = "NECROMANCER_CAVE_EXTENSION_SPAWNS"
START = (82, 117)
Z = 8
SEAM = {(x, 132) for x in range(89, 93)}
# Inclusive ranges (x from, x to, y from, y to). Steps follow two-tile blocks.
SECTIONS = (
    (90, 91, 132, 133), (90, 93, 134, 135), (88, 95, 136, 137),
    (90, 103, 138, 139), (94, 103, 140, 141), (98, 103, 142, 145),
    (100, 103, 146, 149), (98, 105, 150, 153), (100, 105, 154, 155),
    (100, 103, 156, 161), (98, 103, 162, 163), (96, 105, 164, 167),
    (98, 103, 168, 169),
)
SPAWNS = (
    ("Crypt Shambler", (92, 137), 145),
    ("Bone Beast", (99, 139), 155),
    ("Vampire", (102, 146), 165),
    ("Bone Beast", (99, 152), 165),
    ("Undead Gladiator", (104, 154), 180),
    ("Vampire Bride", (102, 160), 200),
    ("Lich", (99, 166), 225),
    ("Undead Gladiator", (103, 168), 200),
)
# Torches and webs are anchored to straight walls and stay out of the passage.
DECOR = {
    (88, 138): (357, 2059),
    (104, 141): (359, 2061),
    (99, 147): (358, 1907),
    (106, 153): (359, 2061),
    (104, 158): (359, 1907),
    (106, 166): (359, 2061),
}


def cave_plan(values, otb):
    floor = {
        (x, y) for x0, x1, y0, y1 in SECTIONS
        for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)
    }
    walk = {
        (x, y) for (x, y, z), ids in values.items()
        if z == Z and ids and otb[ids[0]]["group"] == "ground"
        and not any("block_solid" in otb[i]["flags"] for i in ids)
    }
    if START not in walk:
        raise ValueError(f"No se reconoce la entrada original {(*START, Z)}")
    original_cave = set(NP.reach(walk, START))
    near = {(x + dx, y + dy) for x, y in floor for dx, dy in NP.ALL8} - floor
    if near & walk != {(x, 131) for x in range(89, 93)}:
        raise ValueError("La abertura tiene que dar solo a la sala antigua de los Hero")
    if set(NP.reach(walk | floor, START)) != original_cave | floor:
        raise ValueError("El ramal no es conexo o se cruza con otra cueva")
    if any(not (ids := values.get((x, y, Z - 1))) or otb[ids[0]]["group"] != "ground"
           for x, y in floor):
        raise ValueError("Falta terreno arriba del ramal")

    cells = NP.cave_tiles(floor, floor, seed=821178, mud_bias=0.06)
    stone = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER
    for p in near - walk:
        wall = NP.pieces_for(NP.neighbors_in(floor | walk, *p), *stone)
        if wall is None or len(wall) != 1:
            raise ValueError(f"No hay una pieza de pared única en {p}")
        cells[p] = wall
    for p, (wall_id, art_id) in DECOR.items():
        if cells[p] != [wall_id]:
            raise ValueError(f"La decoración quedaría mal orientada en {p}")
        cells[p].append(art_id)

    for x, y in floor:
        for dx in range(-8, 10):
            for dy in range(-6, 8):
                p = (x + dx, y + dy)
                if (*p, Z) not in values:
                    cells.setdefault(p, [ROCK])
    return {(*p, Z): ids for p, ids in cells.items()}, floor


def add_spawns(raw, floor):
    text = raw.decode("latin-1")
    pattern = rf"\t<!-- BEGIN {SPAWN_KEY} -->.*?<!-- END {SPAWN_KEY} -->\n"
    baseline, count = re.subn(pattern, "", text, flags=re.S)
    if count > 1 or SPAWN_KEY in baseline or baseline.count("</spawns>") != 1:
        raise ValueError("Marcadores del archivo de spawns inválidos")
    registry = {e.attrib["name"].lower() for e in ET.parse(MONSTERS).getroot()}
    occupied = set()
    for spawn in ET.fromstring(baseline.encode("latin-1")).findall("spawn"):
        if int(spawn.attrib["centerz"]) == Z:
            x, y = int(spawn.attrib["centerx"]), int(spawn.attrib["centery"])
            occupied.update((x + int(e.attrib["x"]), y + int(e.attrib["y"]))
                            for e in spawn if e.tag in {"monster", "npc"})
    if occupied & floor:
        raise ValueError(f"Spawns ajenos en el ramal: {occupied & floor}")

    distance = NP.reach(floor, (90, 132), NP.CARD)
    lines = [f"\t<!-- BEGIN {SPAWN_KEY} -->"]
    for name, (x, y), seconds in SPAWNS:
        footprint = {(x + dx, y + dy) for dx in (0, -1) for dy in (0, -1)}
        if (name.lower() not in registry or (x, y) in occupied
                or footprint - floor or distance.get((x, y), 0) < 6):
            raise ValueError(f"Spawn inválido: {name} en {x},{y},{Z}")
        occupied.add((x, y))
        lines.extend((
            f'\t<spawn centerx="{x}" centery="{y}" centerz="{Z}" radius="3">',
            f'\t\t<monster name="{name}" x="0" y="0" z="{Z}" spawntime="{seconds}" />',
            "\t</spawn>",
        ))
    lines.extend((f"\t<!-- END {SPAWN_KEY} -->", ""))
    block = "\n".join(lines)
    if count:
        return re.sub(pattern, lambda _: block, text, flags=re.S).encode("latin-1")
    return baseline.replace("</spawns>", block + "</spawns>").encode("latin-1")


def render_preview(path, tiles, otb):
    from PIL import Image
    from game_render import Sprites, creature_image, parse_dat_all

    x0, y0 = 86, 129
    width, height, rgba = Renderer(otb=otb).area(tiles, x0, y0, 107, 171, Z)
    image = Image.frombytes("RGBA", (width, height), bytes(rgba))
    _, outfits = parse_dat_all()
    sprites = Sprites()
    files = {e.attrib["name"].lower(): e.attrib["file"] for e in ET.parse(MONSTERS).getroot()}
    for name, (x, y), _ in SPAWNS:
        look = ET.parse(MONSTERS.parent / files[name.lower()]).getroot().find("look")
        creature = creature_image({k: int(v) for k, v in look.attrib.items()}, outfits, sprites)
        if creature is None:
            raise ValueError(f"Falta el sprite de {name}")
        image.alpha_composite(creature, ((x - x0 + 1) * 32 - creature.width,
                                        (y - y0 + 1) * 32 - creature.height))
    image.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--preview", type=Path, help="Render PNG con criaturas (requiere Pillow)")
    args = parser.parse_args()

    raw = MAP.read_bytes()
    map_tree = parse_tree(raw)
    otb = load_otb()
    nodes, values, areas = index(map_tree, otb)
    previous = json.loads(MANIFEST.read_text())["cells"] if MANIFEST.exists() else {}
    owned = {tuple(map(int, key.split(","))): ids for key, ids in previous.items()}
    if any(values.get(p) != ids for p, ids in owned.items()):
        raise ValueError("Otra edición modificó casillas del ramal")

    baseline = values.copy()
    for p in owned:
        baseline.pop(p)
        if p[:2] in SEAM:
            baseline[p] = [357]
    cells, floor = cave_plan(baseline, otb)
    if set(owned) - cells.keys():
        raise ValueError("El nuevo plano dejaría casillas del ramal anterior sin administrar")

    changed = {p: ids for p, ids in cells.items() if values.get(p) != ids}
    for p in changed:
        allowed = (None, [ROCK], [357]) if p[:2] in SEAM else (None, [ROCK])
        if p not in owned and values.get(p) not in allowed:
            raise ValueError(f"Casilla ajena protegida en {p}: {values[p]}")
        at_position = nodes.get(p, [])
        if len(at_position) > 1:
            raise ValueError(f"Casilla duplicada: {p}")
        for kind, props, children in at_position:
            plain_ground = len(props) == 2 or (len(props) == 5 and props[2] == 9)
            if (kind != 5 or not plain_ground
                    or any(t != 6 or len(a) != 2 or c for t, a, c in children)):
                raise ValueError(f"Casa, flags o atributos protegidos en {p}")

    spawn_before = SPAWN_FILE.read_bytes()
    spawn_after = add_spawns(spawn_before, floor)
    counts = Counter(name for name, _, _ in SPAWNS)
    print(json.dumps(dict(floor=len(floor), changed=len(changed),
                          spawns_changed=spawn_before != spawn_after, monsters=counts)))
    if args.preview:
        render_preview(args.preview, values | cells, otb)
    if not args.apply or (not changed and spawn_after == spawn_before):
        return

    backup = REPO / "backups/map" / ("necromancer-cave-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    for path in (MAP, SPAWN_FILE, MANIFEST):
        if path.exists():
            shutil.copy2(path, backup / path.name)
    for p, ids in sorted(changed.items()):
        x, y, z = p
        area = areas[x // 256 * 256, y // 256 * 256, z]
        tile = NP.new_tile_node(x, y, x // 256 * 256, y // 256 * 256, ids)
        if p in nodes:
            nodes[p][0][:] = tile
        else:
            area[2].append(tile)
    MAP.write_bytes(serialize_tree(map_tree, raw[:4]))
    SPAWN_FILE.write_bytes(spawn_after)
    payload = {",".join(map(str, p)): ids for p, ids in sorted(cells.items())}
    MANIFEST.write_text(json.dumps(dict(source=[*START, Z], floor=len(floor), cells=payload),
                                   separators=(",", ":")) + "\n")
    print(f"Respaldo: {backup.relative_to(REPO)}")


if __name__ == "__main__":
    main()
