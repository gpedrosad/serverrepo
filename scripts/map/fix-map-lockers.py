#!/usr/bin/env python3
"""Acomoda los lockers de depot (2589-2592) de un OTBM: orientación, apoyo y depot id.

Por cada tile con locker:
  1. Orientación: el frente del locker (el lado de los herrajes) mira hacia donde se para el
     jugador. 2589 = frente al sur, 2590 = oeste, 2591 = norte, 2592 = este. El lado se elige
     entre los vecinos caminables (piso sin nada sólido); si hay varios, el opuesto a una pared.
  2. Apoyo: saca el mostrador (counter 1617/1618) que tenga debajo. El cliente dibuja lo que va
     sobre un mostrador corrido 8 px (altura del mostrador) y el locker queda "flotando".
  3. Depot id: lo deja como item hijo del tile con OTBM_ATTR_DEPOT_ID = 1 (temple), así el
     server no depende del fallback de resolveMapDepotId() en actions.cpp.

Uso:
  python3.11 scripts/map/fix-map-lockers.py MAPA.otbm            # muestra qué cambiaría
  python3.11 scripts/map/fix-map-lockers.py MAPA.otbm --write    # escribe el mapa

Después: python3 scripts/map/scan-map-depots.py MAPA.otbm y probar los depots en el juego
(AGENTS.md, regla de oro de depots) antes de publicar el mapa.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "scripts" / "client-rme"))
import build_zagan_test_assets as B  # noqa: E402

OTB = REPO / "server/YurOTS/ots/data/items/items-zagan-test.otb"
LOCKERS = {2589: "S", 2590: "W", 2591: "N", 2592: "E"}
LOCKER_FOR = {v: k for k, v in LOCKERS.items()}
COUNTERS = {1617, 1618}
DEPOT_ID = 1
OTBM_TILE_AREA, OTBM_TILE, OTBM_ITEM, OTBM_HOUSETILE = 4, 5, 6, 14
ATTR_TILE_FLAGS, ATTR_ITEM, ATTR_DEPOT_ID = 3, 9, 10
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
STEP = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}


def solid_ids() -> tuple[set[int], set[int]]:
    root, _ = B.parse_node(OTB.read_bytes(), 4)
    solid, ground = set(), set()
    for n in root.children:
        flags, blocks = B.parse_item_props(n.props)
        sid = B.get_block_payload(blocks, B.ITEM_ATTR_SERVERID)
        if sid and len(sid) == 2:
            sid = struct.unpack("<H", sid)[0]
            if struct.unpack("<I", flags)[0] & 1:
                solid.add(sid)
            if n.node_type == 1:
                ground.add(sid)
    return solid, ground


def split_tile_props(node):
    """(cabecera, [(attr, payload)]) de un tile; None si trae algo que no sabemos leer."""
    head = 2 + (4 if node.node_type == OTBM_HOUSETILE else 0)
    props = node.props
    attrs, i = [], head
    while i < len(props):
        a = props[i]
        if a == ATTR_TILE_FLAGS:
            attrs.append((a, props[i + 1:i + 5]))
            i += 5
        elif a == ATTR_ITEM:
            attrs.append((a, props[i + 1:i + 3]))
            i += 3
        else:
            return None
    return props[:head], attrs


def tile_items(node, parsed) -> list[int]:
    _, attrs = parsed
    ids = [struct.unpack("<H", p)[0] for a, p in attrs if a == ATTR_ITEM]
    ids += [struct.unpack("<H", c.props[:2])[0] for c in node.children if c.node_type == OTBM_ITEM]
    return ids


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("map", type=Path)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    data = args.map.read_bytes()
    root, end = B.parse_node(data, 4)
    if end != len(data) or data[:4] + B.write_node(root) != data:
        raise SystemExit("El mapa no se reescribe idéntico: no lo toco")
    solid, ground = solid_ids()

    tiles = {}
    for mapdata in root.children:
        for area in mapdata.children:
            if area.node_type != OTBM_TILE_AREA:
                continue
            bx, by, bz = struct.unpack_from("<HHB", area.props, 0)
            for t in area.children:
                if t.node_type in (OTBM_TILE, OTBM_HOUSETILE):
                    tiles[(bx + t.props[0], by + t.props[1], bz)] = t

    def walkable(pos) -> bool:
        node = tiles.get(pos)
        if node is None:
            return False
        parsed = split_tile_props(node)
        if parsed is None:
            return False
        ids = tile_items(node, parsed)
        return any(i in ground for i in ids) and not any(i in solid for i in ids)

    def is_solid(pos) -> bool:
        node = tiles.get(pos)
        if node is None:
            return False
        parsed = split_tile_props(node)
        return parsed is not None and any(i in solid for i in tile_items(node, parsed))

    changes = 0
    for pos, node in sorted(tiles.items(), key=lambda kv: (kv[0][2], kv[0][1], kv[0][0])):
        parsed = split_tile_props(node)
        if parsed is None:
            continue
        ids = tile_items(node, parsed)
        lockers = [i for i in ids if i in LOCKERS]
        if not lockers:
            continue
        if len(lockers) > 1:
            print(f"{pos}: {len(lockers)} lockers en el mismo tile, lo salteo")
            continue
        old = lockers[0]
        x, y, z = pos
        # los mostradores de abajo todavía cuentan como sólidos en el propio tile, no en los vecinos
        free = [d for d, (dx, dy) in STEP.items() if walkable((x + dx, y + dy, z))]
        if len(free) > 1:
            backed = [d for d in free if is_solid((x + STEP[OPPOSITE[d]][0], y + STEP[OPPOSITE[d]][1], z))]
            free = backed or free
        if len(free) != 1:
            print(f"{pos}: no queda claro hacia dónde mira (libre: {free}); dejo {old}")
            new = old
        else:
            new = LOCKER_FOR[free[0]]

        head, attrs = parsed
        already = (new == old and not any(i in COUNTERS for i in ids) and any(
            c.node_type == OTBM_ITEM and c.props[:2] == struct.pack("<H", old) and c.props[2:3] == bytes([ATTR_DEPOT_ID])
            for c in node.children))
        if already:
            continue
        removed = [struct.unpack("<H", p)[0] for a, p in attrs if a == ATTR_ITEM and struct.unpack("<H", p)[0] in COUNTERS]
        removed += [struct.unpack("<H", c.props[:2])[0] for c in node.children
                    if c.node_type == OTBM_ITEM and struct.unpack("<H", c.props[:2])[0] in COUNTERS]
        # el locker inline (si estaba así) pasa a hijo con depot id; los mostradores se van
        attrs = [(a, p) for a, p in attrs
                 if not (a == ATTR_ITEM and struct.unpack("<H", p)[0] in COUNTERS | set(LOCKERS))]
        kids = []
        locker_done = False
        for c in node.children:
            cid = struct.unpack("<H", c.props[:2])[0] if c.node_type == OTBM_ITEM else None
            if cid in COUNTERS:
                continue
            if cid in LOCKERS:
                rest = c.props[2:]
                if not rest:
                    rest = bytes([ATTR_DEPOT_ID]) + struct.pack("<H", DEPOT_ID)
                elif rest[0] != ATTR_DEPOT_ID:
                    print(f"{pos}: el locker ya trae otros atributos ({rest.hex()}); no le agrego depot id")
                c = B.Node(OTBM_ITEM, struct.pack("<H", new) + rest, c.children)
                locker_done = True
            kids.append(c)
        if not locker_done:
            kids.append(B.Node(OTBM_ITEM, struct.pack("<H", new) + bytes([ATTR_DEPOT_ID]) + struct.pack("<H", DEPOT_ID), []))
        node.props = head + b"".join(bytes([a]) + p for a, p in attrs)
        node.children = kids
        changes += 1
        print(f"{pos}: {old} -> {new} (frente {LOCKERS[new]}), saca {removed or 'nada'}, depotid {DEPOT_ID}")

    if args.write and changes:
        args.map.write_bytes(data[:4] + B.write_node(root))
        print(f"escrito {args.map} ({changes} lockers)")
    elif changes:
        print(f"{changes} lockers para cambiar (agregar --write para escribir)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
