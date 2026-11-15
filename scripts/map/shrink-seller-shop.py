#!/usr/bin/env python3
"""Achica la tienda del Seller recortando el fondo sur (2 filas).

La tienda está a la derecha del depot del templo:

  z7  salón de venta abierto (piso de piedra 431, mostrador y mesas)
  z6  piso de displays raros (stone floor 431, mesas 1622/1623 y counter 1620)
  z5  terraza + cuarto de armas (wooden floor 405, mesas 1626/1623/1627)
  z4  techo plano sobre el cuarto sur

Se sacan las filas y54-y55 en todos los pisos y el muro sur y56. El nuevo muro
sur queda en y54, así que la tienda pasa de 11 a 9 filas (y46-y54).

Los displays de z6 (11 raros + 10 small sapphires) se reubican en la franja
oeste x142-143, y48-53 (dejando libre x142,y51 para el blackboard). Las armas
de z5 (spear, arrow, bolt, crossbow, bow) se ponen sobre las mesas de y53.

Las casas Small Street (x143-144/x146, y43-45) no se tocan.

El NPC Perac estaba en 144,54,5 (z5), justo en la fila que se recorta; se mueve a
144,52,5 (terraza, detrás de las mesas) para que no quede sin piso.

Uso:
  python3 scripts/map/shrink-seller-shop.py            # dry-run
  python3 scripts/map/shrink-seller-shop.py --replace  # escribe
"""
from __future__ import annotations

import argparse
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
NPCS = WORLD / "npc.xml"
PERAC_OLD = '<npc name="Perac" x="144" y="54" z="5" dir="0"/>'
PERAC_NEW = '<npc name="Perac" x="144" y="52" z="5" dir="2"/>'

STONE, WOOD, GRASS = 431, 405, 4756
WALL_SW, WALL_S, WINDOW_S, WALL_SE, TORCH = 1043, 1045, 1263, 1042, 2061
SAPPHIRE = 2146

# (x, y) en z6 -> (item, ¿lleva sapphire?)
RELOCATED = {
    (142, 48): (2487, True),    # crown armor
    (142, 49): (2656, True),    # blue robe
    (142, 50): (20110, True),   # stormcaller maul
    (142, 52): (20154, False),  # bonepriest reaver (compartía sapphire con stormcaller)
    (142, 53): (2516, True),    # dragon shield, sobre mesa 1626
    (143, 48): (20104, True),   # basalt greaves
    (143, 49): (20100, True),   # venomqueen fang
    (143, 50): (20121, True),   # ironhide crusher
    (143, 51): (20139, True),   # sword of silence
    (143, 52): (20129, True),   # wayfarer boots
    (143, 53): (20102, True),   # morlen crest, sobre mesa 1623
}

# (x, y) en z5 -> (mesa, arma)
WEAPONS = {
    (142, 53): (1626, 2389),  # spear
    (143, 53): (1623, 2544),  # arrow
    (144, 53): (1623, 2543),  # bolt
    (145, 53): (1623, 2455),  # crossbow
    (146, 53): (1627, 2456),  # bow
}

# Fila del muro sur que se mueve de y56 a y54 (x141..x147).
SOUTH_WALL = {
    141: WALL_SW,
    142: WALL_S,
    143: WINDOW_S,
    144: WALL_S,
    145: WALL_S,
    146: WINDOW_S,
    147: WALL_SE,
}


def shop_is_original(tiles: dict) -> bool:
    return (
        (142, 55, 6) in tiles
        and 2487 in tiles.get((142, 54, 6), [])
        and (142, 56, 6) in tiles
        and 1045 in tiles.get((142, 56, 6), [])
    )


def shop_is_shrunk(tiles: dict) -> bool:
    return (
        (142, 55, 6) not in tiles
        and 1045 in tiles.get((142, 54, 6), [])
        and tiles.get((142, 54, 7)) == [GRASS]
        and (142, 55, 4) not in tiles
    )


def wall_row(z: int, ground: int) -> roomkit.Map:
    m = roomkit.Map()
    for x, item in SOUTH_WALL.items():
        pos = (x, 54, z)
        if x == 141:
            m.t[pos] = {"ground": None, "items": [{"id": item}], "pz": False}
        else:
            # x147 es la esquina SE: igual que el muro original de y56, lleva ground.
            m.ground(pos, ground)
            m.add(pos, item)
    m.add((141, 54, z), TORCH)
    return m


def west_strip() -> roomkit.Map:
    m = roomkit.Map()
    for x in (142, 143):
        for y in range(48, 54):
            m.ground((x, y, 6), STONE, pz=True)
    # Mesas que ya estaban en y53.
    m.add((142, 53, 6), 1626)
    m.add((143, 53, 6), 1623)
    for (x, y), (item, with_sapphire) in RELOCATED.items():
        pos = (x, y, 6)
        m.add(pos, item)
        if with_sapphire:
            m.add(pos, SAPPHIRE)
    return m


def weapon_tables() -> roomkit.Map:
    m = roomkit.Map()
    for (x, y), (table, weapon) in WEAPONS.items():
        pos = (x, y, 5)
        m.ground(pos, WOOD, pz=True)
        m.add(pos, table)
        m.add(pos, weapon)
    return m


def grass_outside() -> roomkit.Map:
    m = roomkit.Map()
    for x in range(142, 148):
        for y in (54, 55):
            m.ground((x, y, 7), GRASS)
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()

    tiles = load_tiles()
    map_shrunk = shop_is_shrunk(tiles)
    map_original = shop_is_original(tiles)
    if not map_shrunk and not map_original:
        print("ERROR: la tienda no está en el estado esperado; aborto para no romperla", file=sys.stderr)
        return 1

    npc_text = NPCS.read_text(encoding="utf-8")
    if PERAC_NEW in npc_text:
        npc_state = "moved"
    elif PERAC_OLD in npc_text:
        npc_state = "original"
    else:
        print("ERROR: no encuentro a Perac en npc.xml (ni en 144,54,5 ni en 144,52,5)", file=sys.stderr)
        return 1

    if map_shrunk and npc_state == "moved":
        print("la tienda ya está achicada y Perac ya está en 144,52,5")
        return 0

    rares: list[int] = []
    sapphires = 0
    weapons: list[int] = []
    if map_original:
        # Los 11 raros y 10 sapphires tienen que estar antes de moverlos.
        for x in (142, 143, 144, 145, 146):
            for y in (54, 55):
                ids = tiles.get((x, y, 6), [])
                rares += [i for i in ids if i not in (STONE, 1620, 1617, 1618, SAPPHIRE)]
                sapphires += ids.count(SAPPHIRE)
        if len(rares) != 11 or sapphires != 10:
            print(f"ERROR: displays de z6 inesperados (rares={len(rares)}, sapphires={sapphires})", file=sys.stderr)
            return 1

        weapons = [i for x in range(142, 147) for i in tiles.get((x, 55, 5), [])
                   if i not in (WOOD, 1617, 1618)]
        if sorted(weapons) != sorted([2389, 2544, 2543, 2455, 2456]):
            print(f"ERROR: armas de z5 inesperadas: {weapons}", file=sys.stderr)
            return 1

    print("tienda Seller x141-147, y46-56 -> y46-54")
    if map_original:
        print(f"  z6: se mueven {len(rares)} raros y {sapphires} sapphires a x142-143,y48-53")
        print("  z5: se mueven 5 armas a las mesas de y53")
        print("  z7: y54-55 pasa a pasto 4756")
        print("  z4: se saca el techo de y55-56")
    if npc_state == "original":
        print("  NPC Perac: 144,54,5 -> 144,52,5 (la fila vieja se recorta)")

    if a.dry_run or not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    backup = Path("/private/var/folders/c8/k2dtzwbx3ml4l81234tng6vc0000gn/T/opencode") / \
        f"shrink-seller-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAP, backup / "test.otbm")
    shutil.copy2(NPCS, backup / "npc.xml")
    print(f"backup: {backup}")

    stackable = {sid for sid, rec in load_otb().items() if "stackable" in rec["flags"]}

    if map_original:
        # z6: muro sur en y54, y55-56 quedan vacíos.
        roomkit.write_map(MAP, wall_row(6, STONE), (141, 54, 147, 56), 6, stackable)
        # z6: reubicar los displays en la franja oeste.
        roomkit.write_map(MAP, west_strip(), (142, 48, 143, 53), 6, stackable)
        # z5: muro sur en y54, y55-56 quedan vacíos.
        roomkit.write_map(MAP, wall_row(5, WOOD), (141, 54, 147, 56), 5, stackable)
        # z5: armas sobre las mesas de y53.
        roomkit.write_map(MAP, weapon_tables(), (142, 53, 146, 53), 5, stackable)
        # z7: el fondo sur pasa a pasto.
        roomkit.write_map(MAP, grass_outside(), (142, 54, 147, 55), 7, stackable)
        # z4: sacar el techo del fondo recortado.
        roomkit.write_map(MAP, roomkit.Map(), (141, 55, 147, 56), 4, stackable)

    if npc_state == "original":
        NPCS.write_text(npc_text.replace(PERAC_OLD, PERAC_NEW, 1), encoding="utf-8")

    # Verificación
    after = load_tiles()
    errs = []
    for x in range(141, 148):
        if x in (141, 147):
            if (x, 54, 6) not in after or (x, 54, 5) not in after:
                errs.append(f"falta esquina del muro sur en x{x}")
        else:
            if 1045 not in after.get((x, 54, 6), []) and WINDOW_S not in after.get((x, 54, 6), []):
                errs.append(f"falta muro sur z6 en x{x}")
            if 1045 not in after.get((x, 54, 5), []) and WINDOW_S not in after.get((x, 54, 5), []):
                errs.append(f"falta muro sur z5 en x{x}")
        for z in (5, 6):
            if (x, 55, z) in after or (x, 56, z) in after:
                errs.append(f"quedó piso viejo en x{x},z{z}")
    for x in range(142, 148):
        for y in (54, 55):
            if after.get((x, y, 7)) != [GRASS]:
                errs.append(f"z7 {x},{y} no quedó pasto: {after.get((x, y, 7))}")
    for x in range(141, 148):
        for y in (55, 56):
            if (x, y, 4) in after:
                errs.append(f"quedó techo en {x},{y},z4")

    got_rares = [i for (x, y) in RELOCATED for i in after.get((x, y, 6), []) if i == RELOCATED[(x, y)][0]]
    if len(got_rares) != 11:
        errs.append(f"rares reubicados: {len(got_rares)}/11")
    got_sapphires = sum(1 for (x, y), (_, s) in RELOCATED.items() if s and SAPPHIRE in after.get((x, y, 6), []))
    if got_sapphires != 10:
        errs.append(f"sapphires reubicados: {got_sapphires}/10")
    for (x, y), (table, weapon) in WEAPONS.items():
        ids = after.get((x, y, 5), [])
        if table not in ids or weapon not in ids:
            errs.append(f"arma/mesa faltante en {x},{y},z5: {ids}")

    # Las casas Small Street y los NPC no se tocan.
    for x in (143, 144, 146):
        for y in (43, 44, 45):
            if (x, y, 7) not in after:
                errs.append(f"se perdió casa Small Street en {x},{y},z7")
    if 431 not in after.get((145, 50, 7), []):
        errs.append("se perdió el piso del NPC Seller en 145,50,7")

    npc_after = NPCS.read_text(encoding="utf-8")
    if PERAC_OLD in npc_after or PERAC_NEW not in npc_after:
        errs.append("Perac no quedó movido a 144,52,5 en npc.xml")
    perac_tile = after.get((144, 52, 5), [])
    solid = {sid for sid, rec in load_otb().items() if "block_solid" in rec["flags"]}
    if STONE not in perac_tile or any(i in solid for i in perac_tile):
        errs.append(f"la casilla de Perac 144,52,5 no es piso libre: {perac_tile}")

    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 1

    print("OK: tienda achicada, displays reubicados, Perac movido y casas intactas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
