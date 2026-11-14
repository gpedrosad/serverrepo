#!/usr/bin/env python3
"""Reestructura las hunt zones de Epstein Island como isla de nivel medio/alto con 4 pisos.

Saca todos los spawns de la isla y sus cuevas (x40-130, y170-260, z6-10), incluidos los de nivel
alto originales y los monstruos débiles de la primera versión, y arma:

  z7  Mutant Camp, Terror Bird Nest, Dragon Roost
  z8  Mutant Burrow + Drowned Grotto / Wyvern Roost / Murius Den (largas)
  z9  Mutated Tiger Den / Tide Priest Sanctum / Bog Raider Bog (largas)
  z10 Deep Mutant Lab / Abyssal Grotto / Bog Raider Queen (largas)

Las cuevas largas se leen de `generated-epstein-caves.json` (caja/inicio de cada zona), que
escribe generate-epstein-caves.py. Solo toca `test-spawn.xml`; no cambia el mapa. Validación:
cada spawn queda en una casilla caminable, fuera de PZ, lejos de NPCs/escaleras, sin duplicados y
en la misma componente caminable de la entrada de su cueva.

Uso:
  python3 scripts/map/generate-epstein-hunts.py --dry-run
  python3 scripts/map/generate-epstein-hunts.py
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import REPO, load_otb, load_tiles  # noqa: E402

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"

BOX = (40, 170, 130, 260)
ZS = (6, 7, 8, 9, 10)
NPC_POS = {(85, 210, 7), (96, 207, 6), (74, 220, 7)}
PZ_BOX = (72, 207, 98, 223)          # PZ de la isla (z7)
HIGH_POWER = {
    "serpent spawn", "dragon lord", "hydra", "black knight", "demon skeleton",
    "demon", "fire devil", "wolf", "rabbit",
}

ZONES = {
    "mutant_camp": dict(box=(64, 207, 71, 216), z=7, ground="grass", seed=11, min_gap=2,
                        monsters=[("Mutated Human", 3, 175), ("Blue Elf Arcanist", 2, 240)]),
    "terror": dict(box=(75, 187, 85, 198), z=7, ground="grass", seed=12, min_gap=3,
                   monsters=[("Terror Bird", 3, 240), ("Dragon Hatchling", 1, 300)]),
    "roost": dict(box=(63, 191, 75, 204), z=7, ground="sand", seed=13, min_gap=2,
                  monsters=[("Dragon Hatchling", 2, 300), ("Wyvern", 1, 300)]),
    "mutant_burrow": dict(box=(74, 175, 110, 199), z=8, ground=None, seed=14, min_gap=3,
                          start=(82, 190, 8), clean=True,
                          monsters=[("Mutated Rat", 2, 300), ("Mutated Bat", 1, 300)]),
}

LONG_MONSTERS = {
    "drowned": [("Drowned Sailor", 4, 300), ("Blue Elf Arcanist", 2, 240)],
    "wyvern": [("Wyvern", 4, 300), ("Dragon Hatchling", 2, 300)],
    "murius": [("Murius", 2, 600), ("Mutated Bat", 4, 300)],
    "tiger": [("Mutated Tiger", 3, 600), ("Mutated Rat", 2, 300)],
    "tide": [("Tide Priest", 2, 600), ("Drowned Sailor", 3, 300)],
    "bog": [("Bog Raider", 3, 600), ("Mutated Bat", 2, 300)],
    "lab": [("Mutated Rat", 3, 300), ("Mutated Bat", 3, 300), ("Mutated Human", 3, 175)],
    "abyss": [("Tide Priest", 3, 600), ("Drowned Sailor", 3, 300)],
    "queen": [("Bog Raider", 3, 600), ("Mutated Tiger", 2, 600)],
}

MANIFEST = WORLD / "generated-epstein-caves.json"
if not MANIFEST.is_file():
    raise SystemExit(f"falta {MANIFEST}; corré generate-epstein-caves.py primero")
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
for i, (name, info) in enumerate(sorted(manifest["zones"].items())):
    if name not in LONG_MONSTERS:
        raise SystemExit(f"no hay lista de monstruos para la zona {name}")
    ZONES[name] = dict(
        box=tuple(info["box"]), z=info["z"], ground=None, seed=100 + i, min_gap=3,
        start=tuple(info["start"]), clean=True, monsters=LONG_MONSTERS[name],
    )


def cheb(a, b) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    otb = load_otb()
    tiles = load_tiles()

    def walkable(pos) -> bool:
        ids = tiles.get(pos)
        if not ids:
            return False
        if not any((otb.get(i) or {}).get("group") == "ground" for i in ids):
            return False
        return not any("block_solid" in (otb.get(i) or {}).get("flags", []) for i in ids)

    def ground(pos):
        ids = tiles.get(pos)
        return (otb.get(ids[0]) or {}).get("name") if ids else None

    def has_fc(pos) -> bool:
        for i in tiles.get(pos, []):
            flags = (otb.get(i) or {}).get("flags", [])
            if any(f.startswith("floorchange") for f in flags):
                return True
        return False

    stairs = {p for p, ids in tiles.items() if any(
        f.startswith("floorchange") for i in ids for f in (otb.get(i) or {}).get("flags", []))}

    # componentes z8: cada cueva se alcanza desde su propia entrada
    cave_walk = {p for p in tiles if p[2] in (8, 9, 10) and walkable(p)}
    components = {}
    for name, zone in ZONES.items():
        start = zone.get("start")
        if not start:
            continue
        comp = set()
        stack = [start]
        while stack:
            p = stack.pop()
            if p in comp or p not in cave_walk:
                continue
            comp.add(p)
            x, y, z = p
            stack += [(x + dx, y + dy, z) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        components[name] = comp

    placed = []
    used = set()
    for name, zone in ZONES.items():
        x0, y0, x1, y1 = zone["box"]
        z = zone["z"]
        cands = []
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                p = (x, y, z)
                if not walkable(p):
                    continue
                if zone["ground"] and ground(p) != zone["ground"]:
                    continue
                if z == 7 and PZ_BOX[0] <= x <= PZ_BOX[2] and PZ_BOX[1] <= y <= PZ_BOX[3]:
                    continue
                if zone.get("start") and p not in components.get(name, set()):
                    continue
                if zone.get("clean") and len(tiles.get(p, [])) > 1:
                    continue
                if any(cheb(p, n) < 3 for n in NPC_POS):
                    continue
                if any(cheb(p, s) < 2 for s in stairs):
                    continue
                if zone.get("start") and cheb(p, zone["start"]) < 3:
                    continue
                cands.append(p)
        rng = random.Random(zone["seed"])
        rng.shuffle(cands)
        for mname, count, st in zone["monsters"]:
            for _ in range(count):
                chosen = None
                for p in cands:
                    if p in used:
                        continue
                    if any(cheb(p, u) < zone["min_gap"] for u in used):
                        continue
                    chosen = p
                    break
                if chosen is None:
                    print(f"ERROR: {name}: no hay lugar para {mname}", file=sys.stderr)
                    return 1
                used.add(chosen)
                placed.append((chosen, mname, st))
        print(f"{name}: {len(cands)} casillas candidatas, "
              f"{sum(c for _n, c, _s in zone['monsters'])} monstruos")

    # validación final
    errs = []
    for p, name, _st in placed:
        if not walkable(p):
            errs.append(f"{name} en {p}: no caminable")
        if p[2] == 7 and PZ_BOX[0] <= p[0] <= PZ_BOX[2] and PZ_BOX[1] <= p[1] <= PZ_BOX[3]:
            errs.append(f"{name} en {p}: dentro de PZ")
        if has_fc(p):
            errs.append(f"{name} en {p}: sobre escalera/agujero")
        if any(cheb(p, n) < 3 for n in NPC_POS):
            errs.append(f"{name} en {p}: demasiado cerca de un NPC")
    if len({p for p, _n, _s in placed}) != len(placed):
        errs.append("hay posiciones duplicadas")
    if errs:
        print("\n".join(errs), file=sys.stderr)
        return 1

    # XML: sacar el bloque anterior y todos los spawns viejos de la isla
    text = SPAWNS.read_text(encoding="latin-1")
    text = re.sub(r"\t?<!-- BEGIN EPSTEIN_HUNTS.*?<!-- END EPSTEIN_HUNTS -->\n?", "", text, flags=re.S)
    spawn_re = re.compile(
        r'\t<spawn centerx="(\d+)" centery="(\d+)" centerz="(\d+)"[^>]*>.*?</spawn>\n?', re.S)

    def drop_old(m):
        x, y, z = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3] and z in ZS:
            return ""
        return m.group(0)

    text, _matches = spawn_re.subn(drop_old, text)
    lines = ["\t<!-- BEGIN EPSTEIN_HUNTS (scripts/map/generate-epstein-hunts.py) -->"]
    for (x, y, z), name, st in placed:
        lines.append(f'\t<spawn centerx="{x}" centery="{y}" centerz="{z}" radius="1">')
        lines.append(f'\t\t<monster name="{name}" x="0" y="0" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    lines.append("\t<!-- END EPSTEIN_HUNTS -->\n")
    block = "\n".join(lines)
    text = text.replace("</spawns>", block + "\t</spawns>")

    # que no quede ningún monstruo de nivel alto en la caja
    left = []
    for m in spawn_re.finditer(text):
        x, y, z = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not (BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3] and z in ZS):
            continue
        for mon in re.finditer(r'<monster name="([^"]+)"', m.group(0)):
            if mon.group(1).lower() in HIGH_POWER:
                left.append((x, y, z, mon.group(1)))
    if left:
        print(f"ERROR: quedan monstruos de nivel alto: {left[:10]}", file=sys.stderr)
        return 1

    print(f"spawns nuevos: {len(placed)}; bloque anterior reemplazado")
    if args.dry_run:
        print("dry-run: no se escribió nada")
        return 0
    SPAWNS.write_text(text, encoding="latin-1")
    print(f"escrito: {SPAWNS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
