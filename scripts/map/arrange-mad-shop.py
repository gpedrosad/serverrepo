#!/usr/bin/env python3
"""Ordena la tienda de Mad (z6 del edificio del Seller, al lado del depot del templo).

Saca los small sapphires (2146) que había debajo de cada raro y pone los 25 ítems de exhibición sobre
mesas y mostradores, agrupados, sin dejar nada en el piso ni fuera del salón (x142-146, y47-53, z6):

  x142        x143       x144 (mesa larga)    x145 (mesitas)       x146 (mostrador)
  47 trampilla escalera   crown armor          stormcaller maul     bloodreaver saber
  48 (llegada) pasillo    blue robe            ironhide crusher     ashlord emberblade
  49 vampire sh.          obsidian regalia     rift hammer          bright sword
  50 dragon sh.           knight legs          bonepriest reaver    sword of silence
  51 (pizarrón)           basalt greaves       MAD                  venomqueen fang
  52 mosaic sh.           boots of haste       flamecoil rune       windsting axe
  53 quarry ward morlen   wayfarer boots       relic of ulm         fire axe

Se agregan 9 mesitas (1619) en x142 (49, 50, 52) y x145 (todo menos la casilla de Mad). Quedan libres
142,48 (ahí llega la escalera de mano de 142,47,7), el pasillo x143 (48-52) y 142,51 (para leer el
pizarrón de 141,51). Mad queda en 145,51 y se lo atiende desde el pasillo (a 2 casillas; habla a < 4).

Uso:
  python3 scripts/map/arrange-mad-shop.py            # dry-run: muestra lo que haría
  python3 scripts/map/arrange-mad-shop.py --replace  # escribe test.otbm
Doc: docs/items-and-map/MAPEAR_TIENDA_SELLER.md (sección "Tienda de Mad").
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import MAP, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, load_otb, parse_tree, serialize_tree  # noqa: E402

Z = 6
ROOM = (142, 47, 146, 53)                    # salón: paredes en x141/x147 e y46/y54
SAPPHIRE = 2146
SMALL_TABLE = 1619
FURNITURE = {1619, 1620, 1621, 1622, 1623, 1624, 1626, 1629, 1386}   # se dejan donde están
LAYOUT = {
    # x142 y x143 (lado oeste): escudos y morlen crest
    (142, 49): 2534, (142, 50): 2516, (142, 52): 20149, (142, 53): 20101, (143, 53): 20102,
    # x144, mesa larga: armadura de la cabeza a los pies
    (144, 47): 2487, (144, 48): 2656, (144, 49): 20147, (144, 50): 2477, (144, 51): 20104,
    (144, 52): 2195, (144, 53): 20129,
    # x145, mesitas: mazas, reaver, runa y reliquia (145,51 es de Mad)
    (145, 47): 20110, (145, 48): 20121, (145, 49): 20111, (145, 50): 20154, (145, 52): 20140,
    (145, 53): 20144,
    # x146, mostrador: espadas y hachas
    (146, 47): 20122, (146, 48): 20112, (146, 49): 2407, (146, 50): 20139, (146, 51): 20100,
    (146, 52): 20130, (146, 53): 2432,
}
NEW_TABLES = {(142, 49), (142, 50), (142, 52), (145, 47), (145, 48), (145, 49), (145, 50), (145, 52), (145, 53)}
KEEP_FREE = {(142, 48), (142, 51), (143, 48), (143, 49), (143, 50), (143, 51), (143, 52), (145, 51)}


def room_tiles(root):
    """(x, y) -> nodo de tile, para las casillas del salón en z6."""
    out = {}
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        if az != Z:
            continue
        for t in area[2]:
            if t[0] in (T_TILE, T_HOUSETILE):
                x, y = ax + t[1][0], ay + t[1][1]
                if ROOM[0] <= x <= ROOM[2] and ROOM[1] <= y <= ROOM[3]:
                    out[(x, y)] = t
    return out


def ids(tile) -> list[int]:
    return [struct.unpack_from("<H", bytes(k[1]), 0)[0] for k in tile[2] if k[0] == T_ITEM]


def item(iid: int):
    return [T_ITEM, bytearray(struct.pack("<H", iid)), []]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()
    otb = load_otb()
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    tiles = room_tiles(root)

    display = set(LAYOUT.values())
    found = {}
    for c, t in tiles.items():
        for i in ids(t):
            if i in display:
                found.setdefault(i, []).append(c)
    if sorted(found) != sorted(display) or any(len(v) != 1 for v in found.values()):
        print(f"ERROR: no están los 25 ítems de exhibición una vez cada uno en el salón: {found}")
        return 1
    done = all(found[i] == [c] for c, i in LAYOUT.items()) and not any(SAPPHIRE in ids(t) for t in tiles.values())
    if done:
        print("La tienda de Mad ya está ordenada; no hay nada que hacer.")
        return 0

    errors, sapphires = [], 0
    for c, t in sorted(tiles.items()):
        keep = []
        for k in t[2]:
            if k[0] != T_ITEM:
                keep.append(k)
                continue
            iid = struct.unpack_from("<H", bytes(k[1]), 0)[0]
            if iid == SAPPHIRE:
                sapphires += 1
            elif iid not in display:
                if iid not in FURNITURE:
                    errors.append(f"{c}: ítem inesperado {iid} {otb.get(iid, {}).get('name')}")
                keep.append(k)
        if c in NEW_TABLES:
            if any(struct.unpack_from("<H", bytes(k[1]), 0)[0] in FURNITURE for k in keep if k[0] == T_ITEM):
                errors.append(f"{c}: ya tiene mueble, no va mesita")
            keep.append(item(SMALL_TABLE))
        if c in LAYOUT:
            keep.append(item(LAYOUT[c]))
        t[2] = keep
    for c in KEEP_FREE:
        if any(k[0] == T_ITEM for k in tiles[c][2]):
            errors.append(f"{c}: tiene que quedar libre y tiene {ids(tiles[c])}")
    for c in LAYOUT:
        rest = [i for i in ids(tiles[c]) if i != LAYOUT[c]]
        if not any(i in FURNITURE and i != 1386 for i in rest):
            errors.append(f"{c}: {otb.get(LAYOUT[c], {}).get('name')} sin mesa ni mostrador debajo ({rest})")
    if errors:
        print("ERROR:\n  " + "\n  ".join(errors))
        return 1

    print(f"small sapphires sacados: {sapphires}; mesitas nuevas: {len(NEW_TABLES)}")
    for y in range(ROOM[1], ROOM[3] + 1):
        row = []
        for x in range(ROOM[0], ROOM[2] + 1):
            it = [i for i in ids(tiles[(x, y)]) if i in display]
            row.append((otb.get(it[0], {}).get("name", "?") if it else "-")[:18].ljust(18))
        print(f"  y{y} " + " ".join(row))
    if not a.replace:
        print("dry-run: usá --replace para escribir")
        return 0
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    print(f"OK {MAP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
