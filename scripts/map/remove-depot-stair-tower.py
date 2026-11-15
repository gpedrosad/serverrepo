#!/usr/bin/env python3
"""Elimina la torre de escaleras de piedra que está a la derecha del depot del templo.

La torre ocupa x137-139, y53-55 y sube desde la calle (z7) hasta z2:

  z7  entrada: ladder 428 en (138,53) y ladder 1386 en (139,53)
  z6  piso de piedra 424 + ladders 1386/3135
  z5  piso de piedra 424 + ladders 3135/1386
  z4  piso de piedra 424 + ladders 1386/3135
  z3  piso de piedra 424 + ladders 3135/1386
  z2  piso de piedra 424 + ladder 3135 (último piso, Angry Ancient Scarab)

La torre está flotando en el vacío: al borrar los pisos z2-z6 no hace falta rellenar
nada. En z7 se restaura el suelo de la calle (724) en (138,53) y se saca el ladder
1386 de (139,53), conservando el pasto 4547.

También se borran los 5 bloques de spawn que quedaban dentro de la torre:

  (138,54,2) Angry Ancient Scarab
  (138,55,3) Furious Hunter x2
  (138,54,4) Furious Mummy
  (138,54,5) Furious Scarab
  (137,55,6) Furious Rotworm x2

No toca el depot (x126-134, z6) ni el edificio de la derecha (x141-142).

Uso:
  python3 scripts/map/remove-depot-stair-tower.py            # dry-run
  python3 scripts/map/remove-depot-stair-tower.py --replace  # escribe
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "kb"))
import roomkit  # noqa: E402
from mapdata import REPO, load_otb, load_tiles  # noqa: E402

WORLD = REPO / "server/YurOTS/ots/data/world"
MAP = WORLD / "test.otbm"
SPAWNS = WORLD / "test-spawn.xml"

TOWER_BOX = (137, 53, 139, 55)
FLOORS = (2, 3, 4, 5, 6)
SURFACE_A = (138, 53, 7)          # ladder 428, sin ground
SURFACE_B = (139, 53, 7)          # 724 + pasto 4547 + ladder 1386
SURFACE_GROUND = 724
SURFACE_GRASS = 4547
LADDER_IDS = {428, 1386, 3135}

# center -> (monster, cantidad)
SPAWN_BLOCKS = {
    (138, 54, 2): (("Angry Ancient Scarab", 1),),
    (138, 55, 3): (("Furious Hunter", 2),),
    (138, 54, 4): (("Furious Mummy", 1),),
    (138, 54, 5): (("Furious Scarab", 1),),
    (137, 55, 6): (("Furious Rotworm", 2),),
}


def tower_positions():
    x0, y0, x1, y1 = TOWER_BOX
    for z in FLOORS:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                yield (x, y, z)


def tower_present(tiles: dict) -> bool:
    return any(pos in tiles for pos in tower_positions())


def spawn_pattern(center: tuple[int, int, int]) -> re.Pattern:
    x, y, z = center
    return re.compile(
        r'[ \t]*<spawn centerx="%d" centery="%d" centerz="%d" radius="\d+"[^>]*>.*?</spawn>\n?'
        % (x, y, z),
        re.S,
    )


def remove_spawn_blocks(text: str) -> tuple[str, list[tuple[int, int, int]]]:
    removed = []
    for center, expected in SPAWN_BLOCKS.items():
        pat = spawn_pattern(center)
        found = pat.findall(text)
        if not found:
            continue
        if len(found) > 1:
            raise SystemExit(f"ERROR: {center} aparece {len(found)} veces en test-spawn.xml")
        block = found[0]
        names = re.findall(r'<monster name="([^"]+)"', block)
        got = sorted(names)
        want = sorted(name for name, count in expected for _ in range(count))
        if got != want:
            raise SystemExit(
                f"ERROR: el bloque {center} cambió (esperaba {want}, encontré {got}); no lo borro"
            )
        text = pat.sub("", text, count=1)
        removed.append(center)
    return text, removed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()

    tiles = load_tiles()
    present = list(tower_positions())
    existing = [p for p in present if p in tiles]
    missing = [p for p in present if p not in tiles]

    if existing and missing:
        print("ERROR: la torre está a medias; faltan casillas:", missing[:12], file=sys.stderr)
        return 1

    print(f"torre x{TOWER_BOX[0]}-{TOWER_BOX[2]}, y{TOWER_BOX[1]}-{TOWER_BOX[3]}, z{min(FLOORS)}-z{max(FLOORS)}")
    if existing:
        print(f"  casillas de la torre: {len(existing)} (se borran)")
    else:
        print("  la torre ya no está en el mapa")
    print(f"  entrada z7: {SURFACE_A} -> ground {SURFACE_GROUND}; {SURFACE_B} sin ladder 1386")

    before_a, before_b = tiles.get(SURFACE_A, []), tiles.get(SURFACE_B, [])
    print(f"  antes: {SURFACE_A} {before_a} / {SURFACE_B} {before_b}")

    spawn_text = SPAWNS.read_text(encoding="latin-1")
    _, removed = remove_spawn_blocks(spawn_text)
    print(f"  spawns a borrar: {removed if removed else 'ninguno (ya estaban)'}")

    if a.dry_run or not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    backup = Path("/private/var/folders/c8/k2dtzwbx3ml4l81234tng6vc0000gn/T/opencode") / \
        f"remove-depot-stair-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAP, backup / "test.otbm")
    shutil.copy2(SPAWNS, backup / "test-spawn.xml")
    print(f"backup: {backup}")

    stackable = {sid for sid, rec in load_otb().items() if "stackable" in rec["flags"]}
    for z in FLOORS:
        roomkit.write_map(MAP, roomkit.Map(), TOWER_BOX, z, stackable)

    surface = roomkit.Map()
    surface.ground(SURFACE_A, SURFACE_GROUND)
    surface.ground(SURFACE_B, SURFACE_GROUND)
    surface.add(SURFACE_B, SURFACE_GRASS)
    roomkit.write_map(
        MAP, surface,
        (SURFACE_A[0], SURFACE_A[1], SURFACE_B[0], SURFACE_B[1]),
        SURFACE_A[2], stackable,
    )

    SPAWNS.write_text(remove_spawn_blocks(spawn_text)[0], encoding="latin-1")

    # Verificación post-escritura
    after = load_tiles()
    left = [p for p in tower_positions() if p in after]
    a_ids, b_ids = after.get(SURFACE_A, []), after.get(SURFACE_B, [])
    errs = []
    if left:
        errs.append(f"quedaron casillas de la torre: {left[:12]}")
    if a_ids != [SURFACE_GROUND]:
        errs.append(f"{SURFACE_A} quedó {a_ids}, esperaba [{SURFACE_GROUND}]")
    if sorted(b_ids) != sorted([SURFACE_GROUND, SURFACE_GRASS]):
        errs.append(f"{SURFACE_B} quedó {b_ids}, esperaba [{SURFACE_GROUND}, {SURFACE_GRASS}]")
    final_spawns = SPAWNS.read_text(encoding="latin-1")
    cleaned_spawns, _ = remove_spawn_blocks(final_spawns)
    if cleaned_spawns != final_spawns:
        errs.append("quedaron bloques de spawn de la torre")
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 1

    print(f"OK: torre eliminada, z7 restaurado y {len(removed)} spawns borrados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
