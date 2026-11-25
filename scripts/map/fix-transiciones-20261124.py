#!/usr/bin/env python3
"""Arregla transiciones de terreno pasto <-> tierra (24 nov 2026, v3).

Doc: docs/items-and-map/TRANSICIONES_TERRENO_2026_11_24.md

  python3.11 scripts/map/fix-transiciones-20261124.py             # dry-run
  python3.11 scripts/map/fix-transiciones-20261124.py --replace   # escribe test.otbm

Punto de partida: la transición que se ve mal en (186,76,7), junto a la puerta del
edificio al sur del puente rio_182.

FASE 1 (suelos 110-121, convención de los generadores del repo):
  La tierra real es el suelo 103. El pasto que la toca reemplaza su suelo por la pieza
  "pasto con borde de tierra" 110-121 (generate-natural-island.py, etc.):
      SIDE   = {"n": 111, "e": 112, "s": 110, "w": 113}
      CORNER = {("n","w"): 120, ("n","e"): 121, ("s","w"): 119, ("s","e"): 118}
      INNER  = {"nw": 116, "ne": 117, "sw": 115, "se": 114}
  Corrige piezas colgadas (sin tierra real al lado -> pasto liso 4756), piezas con el
  lado o la esquina equivocados y pasto pelado pegado a la tierra.

FASE 2 (borde suave, la convención real de RME 7.6 - UNA sola capa):
  Por z-order de grounds.xml, el pasto (3000) va arriba de la tierra (1200): el borde
  lo pinta SOLO el pasto, sobre las tiles de tierra pegadas al pasto. Son los items
  apilados "grass border" 4542-4553 (flag ground_border, puramente visuales, sin
  block_solid):

      lados:        n=4542, e=4543, s=4544, w=4545
      interiores (pasto en diagonal y en los dos lados):  nw=4546, ne=4547, sw=4548, se=4549
      exteriores (pasto solo en diagonal):                nw=4550, ne=4551, sw=4552, se=4553

  El set "dirt border" 4667-4678 son piezas de TEXTURA DE TIERRA para el caso
  tierra>lava: no van sobre el pasto (estampaban bloques de tierra rectangulares).

Qué NO toca (conservador):
  - El pasto: no recibe ninguna pieza (la orilla la pinta la tierra).
  - Tiles de tierra pegadas al agua (shallow water / water): no se tocan para no
    tapar la orilla de agua.
  - Tiles con paredes, muros, arcos, puertas, ventanas, rejas, antorchas, fuego,
    fogatas ni decoración de campo: se informan.
  - Tiles con tierra en dos lados opuestos (franja de pasto de 1 casilla): dudosos.
  - El sistema de costa (4644-4663): bloquea el paso; agregarlo cambiaría la
    caminabilidad, así que no se toca.
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
    MAP, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, load_otb, parse_dat, parse_tree,
    serialize_tree,
)

ATTR_FLAGS, ATTR_ITEM = 3, 9
DIRT = 103
GRASS_PLAIN = 4756
GB = set(range(110, 122))
DIRT_LIKE = {DIRT} | GB
SIDE = {"n": 111, "e": 112, "s": 110, "w": 113}
CORNER = {("n", "w"): 120, ("n", "e"): 121, ("s", "w"): 119, ("s", "e"): 118}
INNER = {"nw": 116, "ne": 117, "sw": 115, "se": 114}
DIRS = {"n": (0, -1), "ne": (1, -1), "e": (1, 0), "se": (1, 1),
        "s": (0, 1), "sw": (-1, 1), "w": (-1, 0), "nw": (-1, -1)}
DIAG_SIDES = {"nw": ("n", "w"), "ne": ("n", "e"), "sw": ("s", "w"), "se": ("s", "e")}
# borde de PASTO (verde) que la tierra lleva mirando hacia el pasto (borders.xml id 2)
GRASS_BORDER = {"side": {"n": 4542, "e": 4543, "s": 4544, "w": 4545},
                "concave": {"nw": 4546, "ne": 4547, "sw": 4548, "se": 4549},
                "diag": {"nw": 4550, "ne": 4551, "sw": 4552, "se": 4553}}
WATER_FAM = {"shallow water", "water"}
# ítems que pueden ir sobre el suelo sin que se saltee el tile (rampas; el suelo se
# cambia debajo y la rampa queda igual)
BENIGN_EXTRA = {1388, 1389, 1390, 1391}
# tiles que no se tocan: nombres de ítems de edificios / campo
SKIP_NAME_PARTS = ("wall", "window", "door", "arch", "rail", "bars", "gate", "pillar",
                   "fence", "palis", "torch", "stair", "ladder", "ramp", "rope", "trunk",
                   "fountain", "well", "statue", "chest", "box", "crate", "barrel", "candle")


def skip_item(sid: int, otb: dict) -> bool:
    """True si el ítem es de edificio/fuego y su tile no debería recibir bordes."""
    name = (otb.get(sid, {}).get("name") or "").lower()
    if any(part in name for part in SKIP_NAME_PARTS):
        return True
    if "tree" in name or "bush" in name or "mushroom" in name:
        return False  # vegetación, aunque el nombre diga "fire"
    return " fire" in name or name == "fire" or name.endswith("fire")


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


def neighbors_in(grounds, x, y, z, mask: set) -> set[str]:
    return {d for d, (dx, dy) in DIRS.items()
            if grounds.get((x + dx, y + dy, z)) in mask}


def pieces_for_ground(grounds, x, y, z) -> list[int] | None:
    """FASE 1: pieza de suelo 110-121 que le toca a un tile de pasto según la tierra."""
    other = neighbors_in(grounds, x, y, z, {DIRT})
    card = other & {"n", "e", "s", "w"}
    if {"n", "s"} <= card or {"e", "w"} <= card:
        return None
    out = []
    if len(card) == 2:
        key = (next(c for c in card if c in "ns"), next(c for c in card if c in "ew"))
        out.append(CORNER[key])
    elif len(card) == 1:
        out.append(SIDE[next(iter(card))])
    for diag, (a, b) in DIAG_SIDES.items():
        if diag in other and a not in card and b not in card:
            out.append(INNER[diag])
    return out


def border_pieces(grounds, x, y, z, mask: set, setdef: dict) -> list[int]:
    """Items de borde apilados del set `setdef` mirando hacia los vecinos de `mask`
    (borders.xml de RME: piezas de lado + esquinas interiores/exteriores)."""
    other = neighbors_in(grounds, x, y, z, mask)
    out = []
    for d in ("n", "e", "s", "w"):
        if d in other:
            out.append(setdef["side"][d])
    for diag, (a, b) in DIAG_SIDES.items():
        if diag in other:
            if a in other and b in other:
                out.append(setdef["concave"][diag])
            elif a not in other and b not in other:
                out.append(setdef["diag"][diag])
    return out


def apply(root, border_sids: set[int], log: list[str]) -> dict:
    nodes = index_nodes(root)
    grounds = {p: (items_of(t) or [None])[0] for p, t in nodes.items()}
    otb = load_otb()
    grass_plain = {sid for sid, r in otb.items() if r.get("name") == "grass"} - GB

    stats = Counter()
    dubious: list[tuple] = []
    skip_items: Counter = Counter()
    skip_ex: dict = {}
    added: Counter = Counter()
    added_ex: dict = {}
    for (x, y, z), tile in sorted(nodes.items()):
        ids = items_of(tile)
        if not ids:
            continue
        g = ids[0]

        # ---- FASE 1: suelos 110-121 ----
        if g in GB or g in grass_plain:
            want = pieces_for_ground(grounds, x, y, z)
            if want is None:
                if g in grass_plain and tile_is_simple(tile) and not [
                        i for i in ids[1:] if i not in border_sids and i not in BENIGN_EXTRA]:
                    stats["opuestos"] += 1
                    dubious.append(((x, y, z), ids))
                continue
            if g in GB:
                target = want[0] if want else GRASS_PLAIN
                if target == g:
                    target = None
            else:
                target = want[0] if want else None
            if target is not None:
                if not tile_is_simple(tile):
                    stats["atributos"] += 1
                    continue
                extras = [i for i in ids[1:] if i not in border_sids and i not in BENIGN_EXTRA]
                if extras:
                    stats["decorado"] += 1
                    continue
                stats["arreglados"] += 1
                set_items(tile, [target] + ids[1:])
                log.append(f"  suelo ({x},{y},{z}): {g} -> {target}")
                ids = items_of(tile)

        # ---- FASE 2: UNA capa — el borde de PASTO sobre la tierra (z-order de RME) ----
        if g not in DIRT_LIKE:
            continue
        # nunca junto al agua: la orilla de agua no se tapa
        if any(grounds.get((x + dx, y + dy, z)) is not None
               and (otb.get(grounds[(x + dx, y + dy, z)], {}).get("name") or "") in WATER_FAM
               for dx, dy in DIRS.values()):
            stats["junto_agua"] += 1
            continue
        want = border_pieces(grounds, x, y, z, grass_plain, GRASS_BORDER)
        if not want:
            continue
        missing = [p for p in want if p not in ids]
        if not missing:
            continue
        if not tile_is_simple(tile):
            stats["atributos_borde"] += 1
            continue
        extras = [i for i in ids[1:] if i not in border_sids and i not in BENIGN_EXTRA]
        if extras and any(skip_item(i, otb) for i in extras):
            stats["decorado_borde"] += 1
            key = tuple(extras)
            skip_items[key] += 1
            skip_ex.setdefault(key, (x, y, z, ids))
            continue
        stats["bordes_agregados"] += len(missing)
        stats["tiles_borde"] += 1
        set_items(tile, ids + missing)
        key = tuple(missing)
        added[key] += 1
        added_ex.setdefault(key, (x, y, z, ids, missing))

    for key, n in sorted(added.items(), key=lambda kv: -kv[1]):
        x, y, z, ids, missing = added_ex[key]
        log.append(f"  borde x{n} (+{list(key)}; ej. ({x},{y},{z}) {ids} -> {ids + list(missing)})")
    for key, n in sorted(skip_items.items(), key=lambda kv: -kv[1]):
        x, y, z, ids = skip_ex[key]
        log.append(f"  aviso-borde x{n}: ítems {list(key)} (no se toca; ej. ({x},{y},{z}) {ids})")
    for p, ids in dubious:
        log.append(f"  dudoso ({p[0]},{p[1]},{p[2]}): tierra en lados opuestos ({ids})")
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replace", action="store_true", help="escribe test.otbm")
    args = ap.parse_args()

    dat = parse_dat()
    border_sids = {sid for sid, r in load_otb().items() if r.get("cid") is not None
                   and 0x01 in dat.get(r["cid"], {}).get("flags", {})}
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    log: list[str] = []
    stats = apply(root, border_sids, log)
    print("Cambios:")
    print("\n".join(log))
    print(f"{len(log)} líneas; resumen: {dict(stats)}")
    if not args.replace:
        print("dry-run: usá --replace para escribir")
        return 0
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    print(f"OK: escrito {MAP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
