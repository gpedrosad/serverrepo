#!/usr/bin/env python3
"""Spawns de bichos poco comunes en la cueva de la isla natural.

Lee generated-natural-island.json + test.otbm, reparte monstruos por distancia
(caminando) desde la escalera y reescribe el bloque NATURAL_ISLAND_CAVE de
test-spawn.xml (idempotente: se puede correr de nuevo).

Uso: python3 scripts/map/spawn-island-cave.py [--dry-run] [--seed 5]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kb"))
from mapdata import DIRS, WORLD, load_otb, load_tiles, parse_dat  # noqa: E402

SPAWN_XML = WORLD / "test-spawn.xml"
MANIFEST = WORLD / "generated-natural-island.json"
BEGIN, END = "<!-- BEGIN NATURAL_ISLAND_CAVE -->", "<!-- END NATURAL_ISLAND_CAVE -->"

# ninguno tenía spawn en el mapa (nov 2026); exp entre paréntesis
BANDS = [  # (fracción de distancia desde la escalera, monstruos posibles, cada cuántas casillas)
    (0.35, ["Gazer", "Stalker"], 30),                                   # 120, 90
    (0.70, ["Angry Crypt Shambler", "Angry Stone Golem", "Gazer"], 24),  # 410, 336
    (1.01, ["Furious Stone Golem", "Angry Crypt Shambler"], 22),        # 432, 410
]
BOSS = "Grorlam"   # golem de piedra jefe, 1600 exp, en la sala más lejana
SAFE_RADIUS = 6    # sin bichos cerca de la escalera
SPAWNTIME, BOSS_SPAWNTIME = 90, 1800


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--seed", type=int, default=5)
    a = ap.parse_args()

    m = json.loads(MANIFEST.read_text())
    cave, box = m["cave"], m["box"]
    z = cave["z"]
    lx, ly = cave["ladder"]["x"], cave["ladder"]["y"]
    otb, dat = load_otb(), parse_dat()
    blocking = {s for s, r in otb.items() if r.get("cid") in dat and 0x0C in dat[r["cid"]]["flags"]}
    tiles = load_tiles()
    walk = {(x, y) for (x, y, tz), items in tiles.items()
            if tz == z and box["x1"] <= x <= box["x2"] and box["y1"] <= y <= box["y2"]
            and not any(i in blocking for i in items)}
    if (lx, ly) not in walk:
        print("ERROR: la escalera no está en piso caminable", file=sys.stderr)
        return 1

    dist = {(lx, ly): 0}
    q = deque([(lx, ly)])
    while q:
        x, y = q.popleft()
        for dx, dy in DIRS.values():
            n = (x + dx, y + dy)
            if n in walk and n not in dist:
                dist[n] = dist[(x, y)] + 1
                q.append(n)
    far = max(dist.values())
    boss_pos = max(dist, key=lambda c: (dist[c], c))

    rng = random.Random(a.seed)
    spawns = [(boss_pos, BOSS, BOSS_SPAWNTIME)]
    taken = {boss_pos}
    lo = 0.0
    for hi, names, per in BANDS:
        cells = [c for c in dist if lo * far <= dist[c] < hi * far and dist[c] > SAFE_RADIUS]
        want = max(1, len(cells) // per)
        rng.shuffle(cells)
        for c in cells:
            if want == 0:
                break
            if all(max(abs(c[0] - t[0]), abs(c[1] - t[1])) >= 3 for t in taken):
                spawns.append((c, rng.choice(names), SPAWNTIME))
                taken.add(c)
                want -= 1
        lo = hi

    lines = [f"\t{BEGIN}"]
    for (x, y), name, st in sorted(spawns, key=lambda s: (s[0][1], s[0][0])):
        lines += [f'\t<spawn centerx="{x}" centery="{y}" centerz="{z}" radius="1">',
                  f'\t\t<monster name="{name}" x="0" y="0" z="{z}" spawntime="{st}" />',
                  "\t</spawn>"]
    lines.append(f"\t{END}")
    block = "\n".join(lines)

    xml = SPAWN_XML.read_text(encoding="utf-8")
    if BEGIN in xml:
        xml = re.sub(rf"\t?{re.escape(BEGIN)}.*?{re.escape(END)}", lambda _: block, xml, flags=re.S)
    else:
        xml = xml.replace("</spawns>", block + "\n</spawns>")

    count = {}
    for _p, n, _s in spawns:
        count[n] = count.get(n, 0) + 1
    print(f"cueva z{z}: {len(walk)} casillas caminables, distancia máx {far} pasos desde la escalera")
    print(f"{len(spawns)} spawns: " + ", ".join(f"{n} x{c}" for n, c in sorted(count.items())))
    print(f"jefe {BOSS} en {boss_pos[0]},{boss_pos[1]},{z} ({dist[boss_pos]} pasos)")
    if a.dry_run:
        return 0
    SPAWN_XML.write_text(xml, encoding="utf-8")
    m["cave"]["spawns"] = [{"x": x, "y": y, "z": z, "monster": n, "spawntime": s} for (x, y), n, s in spawns]
    MANIFEST.write_text(json.dumps(m, indent=2) + "\n")
    print(f"OK {SPAWN_XML}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
