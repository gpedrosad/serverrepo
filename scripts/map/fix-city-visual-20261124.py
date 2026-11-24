#!/usr/bin/env python3
"""Arreglos visuales de la city (24 nov 2026).

Rechequeados contra origin/main. Doc: docs/items-and-map/CITY_VISUAL_FIXES_2026_11_24.md.

  python3.11 scripts/map/fix-city-visual-20261124.py             # dry-run
  python3.11 scripts/map/fix-city-visual-20261124.py --replace   # escribe test.otbm

Qué hace:
  - Canoa de la ensenada del Barquero (171,62-66,7): secuencia 3587→3588→3589(+vela 3597)
    →3590→3591 y el casco sobre agua 4608, sin moverla (al oeste está el muelle). Actualiza
    los bordes de pasto de las casillas de orilla que quedan al lado.
  - Saca 1499 (wild growth) de las 22 casillas de cubierta 1284 del fuerte pirata.
  - Saca bordes de pasto 4542-4553 colgados sobre adoquín en la plaza oeste del templo
    (solo y=41-43, casillas abiertas; no toca 130-131,41 ni el borde real de y>=44).
  - Saca un duplicado de alfombra 4398 en el training, de 1499 en (160,7,7) y de la
    reja arcana 20257 en (163,42,7) (en el mapa viejo era 1544).
  - Saca todos los dead tree 2716 del mapa (el de 17,141,7 sobre pasto 4756 lo
    plantaba generate-duskweb-hollow.py; había 3 más). Si los arreglos de la city
    ya están aplicados, esa parte se saltea y solo se sacan los 2716.
    También: python3.11 scripts/map/fix-city-visual-20261124.py --dead-trees

Qué no toca:
  - El caminito 413 del cantero del templo (intencional).
  - La terraza z6 de las ruinas de los trolls (cambio estético de más riesgo).
  - La nieve en (211-215,25-30): en main no es un islote suelto, es la punta oeste de
    la isla de hielo (x205-262). Conserva la entrada 20368 y la escalera de z8.
  - Casas, lockers, spawns, tiles con atributos (depot, tele, count) y lo que no esté
    en las listas de arriba.
"""
from __future__ import annotations

import argparse
import struct
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import (  # noqa: E402
    MAP, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, load_otb, parse_tree, serialize_tree,
)

ATTR_FLAGS, ATTR_ITEM = 3, 9
WATER, GRASS_COAST = 4608, 4526
COAST_SIDE = {"n": 4644, "e": 4645, "s": 4646, "w": 4647}
COAST_CORNER = {("n", "w"): 4648, ("n", "e"): 4649, ("s", "w"): 4650, ("s", "e"): 4651}
COAST_INNER = {"nw": 4652, "ne": 4653, "sw": 4654, "se": 4655}
COAST_PIECES = set(range(4644, 4656))
GRASS_BORDERS = set(range(4542, 4554))
DIRS = {"n": (0, -1), "ne": (1, -1), "e": (1, 0), "se": (1, 1),
        "s": (0, 1), "sw": (-1, 1), "w": (-1, 0), "nw": (-1, -1)}
DIAG_SIDES = {"nw": ("n", "w"), "ne": ("n", "e"), "sw": ("s", "w"), "se": ("s", "e")}
BOAT_SEQ = [3587, 3588, 3589, 3590, 3591]
SAIL = 3597
BOAT_PARTS = set(BOAT_SEQ) | {SAIL}
BOAT_COL, BOAT_Y0, BOAT_Z = 171, 62, 7

# 1499 sobre cubierta 1284, reconfirmado en origin/main
PIRATE_WG = [
    (205, 40), (206, 40), (207, 40), (207, 41), (202, 44), (209, 44), (210, 44),
    (202, 45), (209, 45), (202, 49), (209, 49), (209, 50), (202, 54), (202, 55),
    (209, 55), (202, 56), (209, 56), (209, 57), (202, 60), (202, 61), (203, 61),
    (203, 62),
]
# Bordes colgados, y=41-43, sin las paredes de 130-131,41 ni el borde real de y>=44
DANGLING_GRASS = [
    (132, 41), (134, 41), (135, 41),
    (132, 42), (134, 42), (135, 42),
    (132, 43), (134, 43), (135, 43),
]
CARPET_DUPS = [
    (138, 11), (139, 11), (140, 11), (143, 12), (144, 12),
    (145, 13), (146, 12), (146, 13),  # 146,12 apareció en main
]
WG_DUP = (160, 7, 7)
RAILING_DUP = (163, 42, 7)  # 20257 x2 (antes 1544 en la copia vieja)
SNOW_HOLE = (213, 27, 7)
SNOW_LADDER = (213, 27, 8)
PATH_413 = [(140, y, 7) for y in range(33, 37)]


def neighbors_in(mask, x, y) -> set[str]:
    return {d for d, (dx, dy) in DIRS.items() if (x + dx, y + dy) in mask}


def pieces_for(other: set[str], side, corner, inner) -> list[int] | None:
    card = other & {"n", "e", "s", "w"}
    if {"n", "s"} <= card or {"e", "w"} <= card:
        return None
    out = []
    if len(card) == 2:
        key = (next(c for c in card if c in "ns"), next(c for c in card if c in "ew"))
        out.append(corner[key])
    elif len(card) == 1:
        out.append(side[next(iter(card))])
    for diag, (a, b) in DIAG_SIDES.items():
        if diag in other and a not in card and b not in card:
            out.append(inner[diag])
    return out


def tile_xy(area, tile) -> tuple[int, int, int]:
    ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
    p = bytes(tile[1])
    return ax + p[0], ay + p[1], az


def items_of(tile) -> list[int]:
    p = bytes(tile[1])
    pos = 2 + (4 if tile[0] == T_HOUSETILE else 0)
    items = []
    while pos < len(p):
        attr = p[pos]
        if attr == ATTR_FLAGS:
            pos += 5
        elif attr == ATTR_ITEM:
            items.append(struct.unpack_from("<H", p, pos + 1)[0])
            pos += 3
        else:
            break
    for k in tile[2]:
        if k[0] == T_ITEM and len(k[1]) >= 2:
            items.append(struct.unpack_from("<H", bytes(k[1]), 0)[0])
    return items


def tile_is_simple(tile) -> bool:
    """True si solo tiene flags e ítems de 2 bytes (sin depot/tele/count)."""
    if tile[0] == T_HOUSETILE:
        return False
    p = bytes(tile[1])
    pos = 2
    while pos < len(p):
        attr = p[pos]
        if attr == ATTR_FLAGS:
            pos += 5
        elif attr == ATTR_ITEM:
            pos += 3
        else:
            return False
    for k in tile[2]:
        if k[0] == T_ITEM and len(k[1]) != 2:
            return False
    return True


def flags_of(tile) -> bytes | None:
    p = bytes(tile[1])
    return bytes(p[3:7]) if len(p) >= 7 and p[2] == ATTR_FLAGS else None


def set_items(tile, ids: list[int]) -> None:
    assert tile[0] == T_TILE and ids, "solo tiles comunes, con al menos el suelo"
    fl = flags_of(tile)
    props = bytearray(tile[1][:2])
    if fl:
        props += bytes([ATTR_FLAGS]) + fl
    tile[1] = props
    tile[2] = [[T_ITEM, bytearray(struct.pack("<H", i)), []] for i in ids]


def drop_id_once(tile, sid: int) -> int:
    """Saca una sola aparición de sid que no sea el suelo."""
    p = bytes(tile[1])
    head = 2
    segs, pos, first, n = [], head, True, 0
    while pos < len(p):
        attr = p[pos]
        if attr == ATTR_FLAGS:
            segs.append(p[pos:pos + 5])
            pos += 5
        elif attr == ATTR_ITEM:
            iid = struct.unpack_from("<H", p, pos + 1)[0]
            if n == 0 and not first and iid == sid:
                n = 1
            else:
                segs.append(p[pos:pos + 3])
            first = False
            pos += 3
        else:
            segs.append(p[pos:])
            break
    out = p[:head] + b"".join(segs)
    if out != p:
        tile[1] = bytearray(out)
    keep = []
    for k in tile[2]:
        if n == 0 and k[0] == T_ITEM and len(k[1]) == 2 \
                and struct.unpack_from("<H", bytes(k[1]), 0)[0] == sid:
            n = 1
            continue
        keep.append(k)
    tile[2] = keep
    return n


def drop_ids(tile, drop: set[int]) -> int:
    p = bytes(tile[1])
    head = 2
    segs, pos, first, n = [], head, True, 0
    while pos < len(p):
        attr = p[pos]
        if attr == ATTR_FLAGS:
            segs.append(p[pos:pos + 5])
            pos += 5
        elif attr == ATTR_ITEM:
            iid = struct.unpack_from("<H", p, pos + 1)[0]
            if not first and iid in drop:
                n += 1
            else:
                segs.append(p[pos:pos + 3])
            first = False
            pos += 3
        else:
            segs.append(p[pos:])
            break
    out = p[:head] + b"".join(segs)
    if out != p:
        tile[1] = bytearray(out)
    keep = []
    for k in tile[2]:
        if k[0] == T_ITEM and len(k[1]) >= 2 \
                and struct.unpack_from("<H", bytes(k[1]), 0)[0] in drop:
            n += 1
            continue
        keep.append(k)
    tile[2] = keep
    return n


def index_nodes(root):
    out = {}
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        for tile in area[2]:
            if tile[0] not in (T_TILE, T_HOUSETILE):
                continue
            out[tile_xy(area, tile)] = tile
    return out


def require(nodes, pos, msg=""):
    tile = nodes.get(pos)
    if tile is None:
        raise SystemExit(f"ERROR: no está el tile {pos} {msg}")
    if not tile_is_simple(tile):
        raise SystemExit(f"ERROR: el tile {pos} es casa o tiene atributos; no se toca")
    return tile


def is_open_water(ids: list[int], otb) -> bool:
    if not ids:
        return False
    g = ids[0]
    if (otb.get(g) or {}).get("name") != "shallow water":
        return False
    for i in ids[1:]:
        n = (otb.get(i) or {}).get("name", "")
        if i in COAST_PIECES:
            continue
        if any(w in n for w in ("boat", "sail", "floor", "wall", "railing", "lantern", "door")):
            return False
    return True


DEAD_TREE = 2716


def city_fixes_pending(nodes) -> bool:
    """True si el mapa todavía tiene el estado previo a los arreglos de la city."""
    p0 = (BOAT_COL, BOAT_Y0, BOAT_Z)
    if p0 not in nodes:
        return True
    ids = items_of(nodes[p0])
    canoe_done = ids[:2] == [WATER, BOAT_SEQ[0]]
    pirate_left = any(
        1499 in items_of(nodes[(x, y, 7)])
        for x, y in PIRATE_WG
        if (x, y, 7) in nodes
    )
    return not canoe_done or pirate_left


def remove_dead_trees_2716(nodes, log: list[str]) -> int:
    """Saca item 2716 de casillas simples en todo el mapa."""
    hits = []
    for (x, y, z), tile in nodes.items():
        ids = items_of(tile)
        if DEAD_TREE not in ids:
            continue
        if not tile_is_simple(tile):
            raise SystemExit(
                f"ERROR: 2716 en casilla no simple {(x, y, z)}: {ids}"
            )
        hits.append((x, y, z, tile, ids))
    if not hits:
        log.append("  dead tree 2716: no había ninguno")
        return 0
    for x, y, z, tile, ids in sorted(hits):
        n = drop_ids(tile, {DEAD_TREE})
        after = items_of(tile)
        if DEAD_TREE in after or not after:
            raise SystemExit(f"ERROR: al sacar 2716 de {(x, y, z)} quedó {after}")
        log.append(f"  dead tree {(x, y, z)}: sacó {n}×2716, {ids} -> {after}")
    return len(hits)


def apply(root, otb, log: list[str], only_dead: bool = False) -> None:
    nodes = index_nodes(root)
    skip_city = only_dead or not city_fixes_pending(nodes)
    if skip_city and not only_dead:
        log.append("city visual ya aplicado; se saltea esa parte")
    if skip_city:
        # invariantes que no se tocan, igual que al final de los arreglos de city
        hole = items_of(nodes[SNOW_HOLE]) if SNOW_HOLE in nodes else []
        if 20368 not in hole:
            raise SystemExit(f"ERROR: se alteró la entrada de nieve {SNOW_HOLE}: {hole}")
        lad = items_of(nodes[SNOW_LADDER]) if SNOW_LADDER in nodes else []
        if 1386 not in lad:
            raise SystemExit(f"ERROR: falta la escalera {SNOW_LADDER}: {lad}")
        for p in PATH_413:
            ids = items_of(nodes[p]) if p in nodes else []
            if ids != [413]:
                raise SystemExit(f"ERROR: se alteró el caminito {p}: {ids}")
        remove_dead_trees_2716(nodes, log)
        return


    # --- 1. canoa ---
    col = [(BOAT_COL, BOAT_Y0 + i, BOAT_Z) for i in range(5)]
    before = {p: items_of(require(nodes, p, "canoa")) for p in col}
    for p, ids in before.items():
        if not any(i in BOAT_PARTS for i in ids):
            raise SystemExit(f"ERROR: no hay pieza de bote en {p}: {ids}")
    for i, p in enumerate(col):
        rest = [x for x in items_of(nodes[p]) if x not in BOAT_PARTS]
        # casco sobre agua: se descarta pasto y borde, queda 4608 + piezas
        set_items(nodes[p], [WATER] + ([BOAT_SEQ[i], SAIL] if BOAT_SEQ[i] == 3589 else [BOAT_SEQ[i]]))
        if rest and rest != [4526, 4647] and set(rest) - {4526, *COAST_PIECES}:
            # había algo más que orilla; no lo silenciamos
            log.append(f"  aviso canoa {p}: se descartó {rest} al poner el casco sobre agua")
        log.append(f"  canoa {p}: {before[p]} -> {items_of(nodes[p])}")

    # Solo se actualiza el anillo de 1 casilla alrededor de la canoa (si no, se
    # reescriben orillas lejanas con una máscara de agua que no cuenta el muelle).
    water = set()
    for (x, y, z), tile in nodes.items():
        if z != 7:
            continue
        ids = items_of(tile)
        if is_open_water(ids, otb) or (x, y, z) in col:
            water.add((x, y))
    ring = {(x + dx, y + dy, 7)
            for (x, y, z) in col
            for dx in range(-1, 2) for dy in range(-1, 2)}
    for p in sorted(ring):
        if p in col or p not in nodes:
            continue
        tile = nodes[p]
        if not tile_is_simple(tile):
            continue
        ids = items_of(tile)
        if not ids:
            continue
        gname = (otb.get(ids[0]) or {}).get("name", "")
        if gname != "grass":
            continue
        want = pieces_for(neighbors_in(water, p[0], p[1]), COAST_SIDE, COAST_CORNER, COAST_INNER)
        if want is None:
            continue
        extras = [i for i in ids[1:] if i not in COAST_PIECES]
        touches = any((p[0] + dx, p[1] + dy) in water for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)))
        had = [i for i in ids[1:] if i in COAST_PIECES]
        if not want and not had and not touches:
            continue
        new_ground = GRASS_COAST if (want or had or touches) else ids[0]
        new_ids = [new_ground] + (want or []) + extras
        if new_ids != ids:
            set_items(tile, new_ids)
            log.append(f"  orilla {p}: {ids} -> {new_ids}")

    # --- 2. maleza del fuerte ---
    for x, y in PIRATE_WG:
        p = (x, y, 7)
        tile = require(nodes, p, "fuerte pirata")
        ids = items_of(tile)
        if 1284 not in ids or 1499 not in ids:
            raise SystemExit(f"ERROR: se esperaba 1284+1499 en {p}, hay {ids}")
        n = drop_ids(tile, {1499})
        after = items_of(tile)
        if 1499 in after or 1284 not in after:
            raise SystemExit(f"ERROR: al sacar 1499 de {p} quedó {after}")
        log.append(f"  fuerte {p}: sacó {n}×1499, queda {after}")

    # --- 3. bordes de pasto colgados ---
    for x, y in DANGLING_GRASS:
        p = (x, y, 7)
        tile = require(nodes, p, "plaza oeste")
        ids = items_of(tile)
        have = [i for i in ids if i in GRASS_BORDERS]
        if not have:
            raise SystemExit(f"ERROR: no hay borde de pasto en {p}: {ids}")
        n = drop_ids(tile, GRASS_BORDERS)
        after = items_of(tile)
        if any(i in GRASS_BORDERS for i in after):
            raise SystemExit(f"ERROR: quedó borde de pasto en {p}: {after}")
        log.append(f"  adoquín {p}: sacó {n} bordes {have}, queda {after}")

    # --- 4. duplicados ---
    for x, y in CARPET_DUPS:
        p = (x, y, 7)
        tile = require(nodes, p, "alfombra")
        ids = items_of(tile)
        if ids.count(4398) < 2:
            raise SystemExit(f"ERROR: no hay alfombra duplicada en {p}: {ids}")
        n = drop_id_once(tile, 4398)
        after = items_of(tile)
        if after.count(4398) != 1 or n != 1:
            raise SystemExit(f"ERROR: alfombra en {p}: {ids} -> {after}")
        log.append(f"  alfombra {p}: 4398 x{ids.count(4398)} -> x{after.count(4398)}")

    tile = require(nodes, WG_DUP, "maleza duplicada")
    ids = items_of(tile)
    if ids.count(1499) < 2:
        raise SystemExit(f"ERROR: no hay 1499 x2 en {WG_DUP}: {ids}")
    drop_id_once(tile, 1499)
    after = items_of(tile)
    if after.count(1499) != 1:
        raise SystemExit(f"ERROR: 1499 en {WG_DUP}: {after}")
    log.append(f"  maleza {WG_DUP}: 1499 x{ids.count(1499)} -> x{after.count(1499)}")

    tile = require(nodes, RAILING_DUP, "reja")
    ids = items_of(tile)
    # en main es 20257; se acepta 1544 por si se corre sobre un mapa más viejo
    sid = 20257 if ids.count(20257) >= 2 else 1544 if ids.count(1544) >= 2 else None
    if sid is None:
        raise SystemExit(f"ERROR: no hay reja duplicada en {RAILING_DUP}: {ids}")
    drop_id_once(tile, sid)
    after = items_of(tile)
    if after.count(sid) != 1:
        raise SystemExit(f"ERROR: reja en {RAILING_DUP}: {after}")
    log.append(f"  reja {RAILING_DUP}: {sid} x{ids.count(sid)} -> x{after.count(sid)}")

    # invariantes que no se tocan
    hole = items_of(nodes[SNOW_HOLE]) if SNOW_HOLE in nodes else []
    if 20368 not in hole:
        raise SystemExit(f"ERROR: se alteró la entrada de nieve {SNOW_HOLE}: {hole}")
    lad = items_of(nodes[SNOW_LADDER]) if SNOW_LADDER in nodes else []
    if 1386 not in lad:
        raise SystemExit(f"ERROR: falta la escalera {SNOW_LADDER}: {lad}")
    for p in PATH_413:
        ids = items_of(nodes[p]) if p in nodes else []
        if ids != [413]:
            raise SystemExit(f"ERROR: se alteró el caminito {p}: {ids}")

    remove_dead_trees_2716(nodes, log)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replace", action="store_true", help="escribe test.otbm")
    ap.add_argument(
        "--dead-trees",
        action="store_true",
        help="solo saca dead tree 2716 (no reaplica los arreglos de la city)",
    )
    args = ap.parse_args()

    otb = load_otb()
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    log: list[str] = []
    apply(root, otb, log, only_dead=args.dead_trees)
    print("Cambios:")
    print("\n".join(log))
    print(f"{len(log)} líneas de cambio")
    if not args.replace:
        print("dry-run: usá --replace para escribir")
        return 0
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    print(f"OK: escrito {MAP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
