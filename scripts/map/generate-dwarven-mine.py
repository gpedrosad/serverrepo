#!/usr/bin/env python3
"""Aplica Mina Enana y sus spawns sin alterar cuevas/lockers/casas existentes.

python3.11 scripts/map/generate-dwarven-mine.py [--dry-run]
Doc: docs/gameplay/DWARVEN_MINE.md. Sin instancias ni clientes de prueba.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import sys
from datetime import datetime

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "kb")]
from mapdata import MAP, REPO, load_otb, parse_tree, serialize_tree
from epstein_cave_repair import index
from portal_citadel_layout import tile_flags
from dwarven_mine_layout import build, C, MOUTH, SHAFT, DOWN, BOSS

module_spec = importlib.util.spec_from_file_location("mine_markers", HERE / "generate-petrified-sanctuary.py")
markers = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(markers)
MANIFEST = MAP.parent / "generated-dwarven-mine.json"
SPAWNS = MAP.parent / "test-spawn.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    otb = load_otb()
    nodes, values, areas = index(root, otb)
    assert all(len(ns) == 1 for ns in nodes.values()), "Mapa con duplicados"
    previous = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    baseline = dict(values)
    for key, old in previous.get("original", {}).items():
        p = tuple(map(int, key.split(",")))
        if old is None:
            baseline.pop(p, None)
        else:
            baseline[p] = old
    cells, spawns, report = build(baseline, otb)
    surface = {tuple(p) for p in report["surface"]}
    expected_surface = {(195, 59, 7): [4756], (195, 60, 7): [4756], (195, 61, 7): [4756],
                        (194, 58, 7): [113], (197, 60, 7): [4756], (194, 60, 7): [113]}
    assert set(previous.get("cells", {})) <= {",".join(map(str, p)) for p in cells}, "La receta deja restos"
    for p, ids in cells.items():
        old = values.get(p)
        key = ",".join(map(str, p))
        owned = key in previous.get("cells", {}) and previous["cells"][key] == old
        if key in previous.get("cells", {}) and not owned:
            raise ValueError(f"Otra sesion cambio {p}; no sobrescribir")
        lava = (p[2] == 8 and 186 <= p[0] <= 205 and 49 <= p[1] <= 69
                and old == [598] and "block_solid" in otb[598]["flags"])
        if not owned and p not in surface and old not in (None, [101]) and not lava:
            raise ValueError(f"Terreno ajeno protegido: {p}: {old}")
        if p in surface and not owned and old != expected_surface[p]:
            raise ValueError(f"Entrada ocupada: {p}: {old}")
        for t in nodes.get(p, []):
            assert t[0] == 5 and not tile_flags(t[1]), f"Casa/flags protegidos: {p}"
            assert all(c[0] == 6 and len(c[1]) == 2 and not c[2] for c in t[2]), f"Atributos protegidos: {p}"
    changed = sum(values.get(p) != ids for p, ids in cells.items())
    report["changed"] = changed
    print(json.dumps(report, ensure_ascii=False))
    spawn_text = markers.block(SPAWNS.read_text(encoding="latin-1"), "DWARVEN_MINE_SPAWNS",
                              C.spawn_xml(spawns), "</spawns>").replace(
                                  "DWARVEN_MINE_SPAWNS (scripts/map/generate-petrified-sanctuary.py)",
                                  "DWARVEN_MINE_SPAWNS (scripts/map/generate-dwarven-mine.py)")
    sign_text = markers.block(READABLES.read_text(encoding="latin-1"), "DWARVEN_MINE_SIGNS",
        '\t<readable x="194" y="60" z="7" text="MINA ENANA\\nDwarfs y soldados arriba.\\nGuardias, geomancers y el Capataz de Hierro al fondo."/>',
        "</readables>").replace("DWARVEN_MINE_SIGNS (scripts/map/generate-petrified-sanctuary.py)",
                                "DWARVEN_MINE_SIGNS (scripts/map/generate-dwarven-mine.py)")
    if args.dry_run:
        return
    backup = REPO / "backups/map" / ("dwarven-mine-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    for f in (MAP, SPAWNS, READABLES):
        shutil.copy2(f, backup / f.name)
    for (x, y, z), ids in sorted(cells.items()):
        key = x // 256 * 256, y // 256 * 256, z
        if key not in areas:
            areas[key] = [4, bytearray(struct.pack("<HHB", *key)), []]
            root[2][0][2].append(areas[key])
        if (x, y, z) in nodes:
            tile = nodes[x, y, z][0]
        else:
            tile = [5, bytearray([x % 256, y % 256]), []]
            areas[key][2].append(tile)
        ground = otb[ids[0]]["group"] == "ground"
        tile[1] = bytearray([x % 256, y % 256]) + (struct.pack("<BH", 9, ids[0]) if ground else b"")
        tile[2] = [C.item_node(i) for i in ids[1 if ground else 0:]]
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    SPAWNS.write_text(spawn_text, encoding="latin-1")
    READABLES.write_text(sign_text, encoding="latin-1")
    MANIFEST.write_text(json.dumps(dict(name="dwarven-mine", version=2, entry=[*MOUTH, 7],
        shaft=[*SHAFT, 8], down=[*DOWN, 9], boss=[*BOSS, 10], report=report,
        cells={",".join(map(str, p)): ids for p, ids in sorted(cells.items())},
        original={",".join(map(str, p)): baseline.get(p) for p in sorted(cells)}), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
