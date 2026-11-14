#!/usr/bin/env python3
"""Dungeon de la city: 3 pisos bajo el distrito este (entrada 185,58,7).

  z8  Smuggler's Den  (caja 181-198, 39-59)
  z9  Deeper Den      (caja 181-198, 39-65)
  z10 Flooded Vault   (caja 181-198, 39-70)

La zona está en el hueco negro del este de la city, sin pisar las cloacas, la cueva central
ni el dungeon de lava. Reutiliza el tallador procedural de generate-epstein-caves.py.

Uso:
  python3 scripts/map/generate-city-depths.py --dry-run --preview-dir /tmp/city-depths
  python3 scripts/map/generate-city-depths.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
import roomkit  # noqa: E402
from mapdata import REPO  # noqa: E402

_spec = importlib.util.spec_from_file_location("epstein_caves", HERE / "generate-epstein-caves.py")
ep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ep)

WORLD = REPO / "server/YurOTS/ots/data/world"
MAP = WORLD / "test.otbm"
MANIFEST = WORLD / "generated-city-depths.json"
Z7, Z8, Z9, Z10 = 7, 8, 9, 10
ENTRANCE = (185, 58)

Z8_SPEC = dict(box=(181, 39, 198, 59), start=ENTRANCE, seed=401, steps=70, room_every=10,
               floor=ep.CAVE_MUD)
Z9_SPEC = dict(box=(181, 39, 198, 65), seed=402, steps=70, room_every=10,
               floor=ep.CAVE_FLOOR_ALT)
Z10_SPEC = dict(box=(181, 39, 198, 70), seed=403, steps=60, room_every=10,
                floor=ep.CAVE_FLOOR)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preview-dir", type=Path)
    args = ap.parse_args()

    maps = {}
    meta = {}
    floors = {}

    tiles8, floor8, hole8 = ep.build_zone(Z8_SPEC, Z8_SPEC["start"], Z8)
    maps["den"] = ep.to_map(tiles8); floors["den"] = floor8
    meta["den"] = {"z": Z8, "box": list(Z8_SPEC["box"]),
                   "start": [ENTRANCE[0], ENTRANCE[1], Z8], "hole": list(hole8)}
    print(f"den: z8 piso {len(floor8)}, agujero a z9 {hole8}")

    tiles9, floor9, hole9 = ep.build_zone(Z9_SPEC, hole8, Z9)
    maps["deeper"] = ep.to_map(tiles9); floors["deeper"] = floor9
    meta["deeper"] = {"z": Z9, "box": list(Z9_SPEC["box"]),
                      "start": [hole8[0], hole8[1], Z9], "hole": list(hole9)}
    print(f"deeper: z9 piso {len(floor9)}, agujero a z10 {hole9}")

    tiles10, floor10, hole10 = ep.build_zone(Z10_SPEC, hole9, Z10)
    maps["vault"] = ep.to_map(tiles10); floors["vault"] = floor10
    meta["vault"] = {"z": Z10, "box": list(Z10_SPEC["box"]),
                     "start": [hole9[0], hole9[1], Z10], "hole": list(hole10)}
    print(f"vault: z10 piso {len(floor10)}")

    # agujeros entre pisos
    maps["den"].t[(hole8[0], hole8[1], Z8)] = {"ground": ep.HOLE, "items": [], "pz": False}
    maps["deeper"].t[(hole9[0], hole9[1], Z9)] = {"ground": ep.HOLE, "items": [], "pz": False}

    for name, cave in (("den", Z8_SPEC), ("deeper", Z9_SPEC), ("vault", Z10_SPEC)):
        z = meta[name]["z"]
        errs = ep.validate(maps[name], floors[name], tuple(meta[name]["start"][:2]), z)
        if errs:
            print("\n".join(errs[:20]), file=sys.stderr)
            return 1
        if args.preview_dir:
            args.preview_dir.mkdir(parents=True, exist_ok=True)
            roomkit.render_png(maps[name], args.preview_dir / f"{name}.png", z)

    if args.dry_run:
        print("dry-run: no se escribió nada")
        return 0

    MANIFEST.write_text(json.dumps({"zones": meta}, indent=2) + "\n", encoding="utf-8")
    print(f"manifiesto: {MANIFEST}")

    backup = Path("/private/var/folders/c8/k2dtzwbx3ml4l81234tng6vc0000gn/T/opencode") / \
        f"city-depths-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAP, backup / "test.otbm")
    print(f"backup: {backup}")

    stackable = roomkit.Checker(maps["den"]).stackable
    roomkit.write_map(MAP, maps["den"], Z8_SPEC["box"], Z8, stackable)
    roomkit.write_map(MAP, maps["deeper"], Z9_SPEC["box"], Z9, stackable)
    roomkit.write_map(MAP, maps["vault"], Z10_SPEC["box"], Z10, stackable)
    # agujero de entrada en la superficie
    m7 = roomkit.Map()
    m7.ground((ENTRANCE[0], ENTRANCE[1], Z7), ep.HOLE)
    roomkit.write_map(MAP, m7, (ENTRANCE[0], ENTRANCE[1], ENTRANCE[0], ENTRANCE[1]), Z7, stackable)
    print(f"escrito: {MAP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
