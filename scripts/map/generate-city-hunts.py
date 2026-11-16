#!/usr/bin/env python3
"""Tripulación pirata del barco del este.

Los spawns del dungeon de la city (z8-z10, bloque CITY_DEPTHS_SPAWNS) ya no salen de acá: los pone
generate-city-depths.py, sala por sala, junto con la cueva.

- Reemplaza los 9 dragon lords del barco del este (x200-209, y43-57, z5-7) por:
    Pirate Corsair ×2, Buccaneer ×2, Cutthroat ×3, Marauder ×2
- Esconde un Dragon Lord Hatchling (respawn 900 s) en 203,55,5.

Solo toca `test-spawn.xml`.

Uso:
  python3 scripts/map/generate-city-hunts.py --dry-run
  python3 scripts/map/generate-city-hunts.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import REPO, load_otb, load_tiles  # noqa: E402

WORLD = REPO / "server/YurOTS/ots/data/world"
SPAWNS = WORLD / "test-spawn.xml"

BOAT = {
    (208, 56, 5): ["Pirate Cutthroat"],
    (204, 57, 5): ["Pirate Marauder"],
    (204, 47, 6): ["Pirate Buccaneer"],
    (200, 52, 6): ["Pirate Cutthroat"],
    (209, 55, 6): ["Pirate Cutthroat"],
    (203, 56, 6): ["Pirate Marauder"],
    (206, 43, 7): ["Pirate Corsair", "Pirate Corsair"],
    (206, 50, 7): ["Pirate Buccaneer"],
}


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

    text = SPAWNS.read_text(encoding="latin-1")

    # barco: reemplazar los puestos actuales por la tripulación pirata
    for (cx, cy, cz), names in BOAT.items():
        pat = re.compile(
            rf'(<spawn centerx="{cx}" centery="{cy}" centerz="{cz}"[^>]*>)(.*?)(</spawn>)', re.S)
        m = pat.search(text)
        if not m:
            print(f"ERROR: no encontré spawn del barco {cx},{cy},{cz}", file=sys.stderr)
            return 1
        body = m.group(2)
        idx = 0

        def repl_name(mm):
            nonlocal idx
            if idx >= len(names):
                return mm.group(0)
            name = names[idx]
            idx += 1
            return f'name="{name}"'

        body, n = re.subn(r'name="[^"]+"', repl_name, body)
        if n != len(names):
            print(f"ERROR: el spawn {cx},{cy},{cz} tiene {n} monstruos, esperaba {len(names)}", file=sys.stderr)
            return 1
        text = text[:m.start()] + m.group(1) + body + m.group(3) + text[m.end():]

    # validación: tripulación correcta y sin los reemplazos anteriores
    left = []
    for (cx, cy, cz), names in BOAT.items():
        m = re.search(rf'<spawn centerx="{cx}" centery="{cy}" centerz="{cz}"[^>]*>.*?</spawn>', text, re.S)
        block = m.group(0) if m else ""
        if not all(f'name="{name}"' in block for name in names):
            left.append((cx, cy, cz, "faltan piratas"))
        if any(old in block.lower() for old in ("dragon lord", "blue djinn", "dworc voodoomaster")):
            left.append((cx, cy, cz, "quedó un reemplazo viejo"))
    if left:
        print(f"ERROR: barco mal armado: {left}", file=sys.stderr)
        return 1

    # polizón escondido: cabina superior z5, acceso por trampilla/escalera de la bodega
    if not all(walkable((203 + dx, 55 + dy, 5)) for dx in (0, 1) for dy in (0, 1)):
        print("ERROR: la cabina 203,55,5 no tiene 2x2 libres para el polizón", file=sys.stderr)
        return 1
    text = re.sub(r"\t?<!-- BEGIN BOAT_STOWAWAY.*?<!-- END BOAT_STOWAWAY -->\n?", "", text, flags=re.S)
    stow = ("\t<!-- BEGIN BOAT_STOWAWAY (scripts/map/generate-city-hunts.py) -->\n"
            '\t<spawn centerx="203" centery="55" centerz="5" radius="1">\n'
            '\t\t<monster name="Dragon Lord Hatchling" x="0" y="0" z="5" spawntime="900" />\n'
            "\t</spawn>\n"
            "\t<!-- END BOAT_STOWAWAY -->\n")
    text = text.replace("</spawns>", stow + "\t</spawns>")

    print(f"barco: {sum(len(v) for v in BOAT.values())} puestos con tripulación pirata; "
          f"polizón Dragon Lord Hatchling en 203,55,5")
    if args.dry_run:
        print("dry-run: no se escribió nada")
        return 0
    SPAWNS.write_text(text, encoding="latin-1")
    print(f"escrito: {SPAWNS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
