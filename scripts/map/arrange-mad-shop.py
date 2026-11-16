#!/usr/bin/env python3
"""Ordena la tienda de Mad (z6 del edificio del Seller, al lado del depot del templo).

Los raros de exhibición quedan donde ningún jugador se puede parar al lado: para mover o agarrar un
ítem del piso hay que estar a 1 casilla (`Game::onPrepareMoveThing`, "Too far away..."). Los
clientes caminan por x142-143; la mesa larga x144 (y47-53) cierra el lado de Mad, así que solo el
piso de Mad (x145) y el mostrador (x146) quedan fuera de alcance: 13 casillas, un ítem en cada una.

  x142-143 (clientes)   x144 (mesa larga, vacía)   x145 (piso de Mad)    x146 (mostrador)
  47 trapdoor / ladder                             obsidian regalia      bloodreaver saber
  48 llegada                                       basalt greaves        ashlord emberblade
  49                                               mosaic shield         venomqueen fang
  50                                               quarry ward           sword of silence
  51 pizarrón                                      MAD                   stormcaller maul
  52                                               rift hammer           ironhide crusher
  53 (mesas del sur, vacías)                       windsting axe         bonepriest reaver

Saca: los small sapphires (2146), las mesitas 1619 (se pueden empujar y estaban del lado de los
clientes) y 12 ítems que ya no entran (los 8 comunes que Mad compra y 4 raros sin fuente de loot).
Valida con un flood fill desde la llegada de la escalera (142,48) que ningún ítem de exhibición
quede a 1 casilla de una casilla pisable y que la casilla de Mad no se pueda pisar.

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
ENTRY = (142, 48)                            # llega la escalera de mano de 142,47,7
MAD = (145, 51)
SAPPHIRE = 2146
SMALL_TABLE = 1619
LAYOUT = {
    # x145, piso de Mad: armadura y escudos, rift hammer y windsting axe
    (145, 47): 20147, (145, 48): 20104, (145, 49): 20149, (145, 50): 20101, (145, 52): 20111,
    (145, 53): 20130,
    # x146, mostrador: las 6 armas de El Crisol y la sword of silence
    (146, 47): 20122, (146, 48): 20112, (146, 49): 20100, (146, 50): 20139, (146, 51): 20110,
    (146, 52): 20121, (146, 53): 20154,
}
REMOVED = {
    2487, 2656, 2477, 2195, 2534, 2516, 2407, 2432,   # comunes: crown armor ... fire axe (Mad los compra)
    20140, 20144, 20129, 20102,                       # flamecoil rune, relic of ulm, wayfarer boots, morlen crest
}
FURNITURE = {1620, 1621, 1622, 1623, 1624, 1626, 1629, 1386}   # originales, se dejan donde están


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


def reachable(tiles, otb) -> set:
    """Casillas del salón que pisa un jugador entrando por la escalera (las paredes cierran el salón)."""
    def free(c):
        return c in tiles and not any("block_solid" in otb.get(i, {}).get("flags", []) for i in ids(tiles[c]))
    seen, todo = set(), [ENTRY]
    while todo:
        c = todo.pop()
        if c in seen or not free(c):
            continue
        seen.add(c)
        todo += [(c[0] + dx, c[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    return seen


def check(tiles, otb) -> list[str]:
    errors = []
    walk = reachable(tiles, otb)
    if MAD in walk:
        errors.append(f"{MAD}: la casilla de Mad se puede pisar")
    display = set(LAYOUT.values())
    for c, t in tiles.items():
        for i in ids(t):
            if i in display and any(abs(c[0] - w[0]) <= 1 and abs(c[1] - w[1]) <= 1 for w in walk):
                errors.append(f"{c}: {otb.get(i, {}).get('name')} queda al alcance de un jugador")
            if i in REMOVED or i in (SAPPHIRE, SMALL_TABLE):
                errors.append(f"{c}: sigue {i} {otb.get(i, {}).get('name')}")
    return errors


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
        print(f"ERROR: no están los 13 ítems de exhibición una vez cada uno en el salón: {found}")
        return 1
    if all(found[i] == [c] for c, i in LAYOUT.items()) and not check(tiles, otb):
        print("La tienda de Mad ya está ordenada; no hay nada que hacer.")
        return 0

    errors, removed = [], {}
    for c, t in sorted(tiles.items()):
        keep = []
        for k in t[2]:
            if k[0] != T_ITEM:
                keep.append(k)
                continue
            iid = struct.unpack_from("<H", bytes(k[1]), 0)[0]
            if iid in REMOVED or iid in (SAPPHIRE, SMALL_TABLE):
                removed[iid] = removed.get(iid, 0) + 1
            elif iid not in display:
                if iid not in FURNITURE:
                    errors.append(f"{c}: ítem inesperado {iid} {otb.get(iid, {}).get('name')}")
                keep.append(k)
        if c in LAYOUT:
            keep.append(item(LAYOUT[c]))
        t[2] = keep
    errors += check(tiles, otb)
    if errors:
        print("ERROR:\n  " + "\n  ".join(errors))
        return 1

    for iid, n in sorted(removed.items()):
        print(f"  saco {n} x {iid} {otb.get(iid, {}).get('name')}")
    print(f"pisables: {sorted(reachable(tiles, otb))}")
    for y in range(ROOM[1], ROOM[3] + 1):
        row = []
        for x in range(ROOM[0], ROOM[2] + 1):
            it = [i for i in ids(tiles[(x, y)]) if i in display]
            row.append(("MAD" if (x, y) == MAD else otb.get(it[0], {}).get("name", "?") if it else "-")[:18].ljust(18))
        print(f"  y{y} " + " ".join(row))
    if not a.replace:
        print("dry-run: usá --replace para escribir")
        return 0
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    print(f"OK {MAP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
