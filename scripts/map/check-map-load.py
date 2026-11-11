#!/usr/bin/env python3
"""Lee test.otbm igual que el server (IOMapOTBM::loadMap de YurOTS) y avisa lo que lo haría fallar.

El server corta toda la carga ("FATAL: couldnt determine the map format! exiting2") ante el primer
item que no puede leer. Lo más común: un item apilable, salpicadura o fluido escrito sin su byte de
cantidad (el server lo exige según el items.otb que use, ver YUROTS_ITEMS_OTB). Pasó con las
calaveras 2320 que ponían los generadores de mapa (nov 2026).

Uso:
    python3 scripts/map/check-map-load.py                 # revisa con items-zagan-test.otb (prod)
    python3 scripts/map/check-map-load.py --otb data/items/items.otb
    python3 scripts/map/check-map-load.py --fix           # agrega count=1 a los items que lo piden

Sale con código 1 si queda algún error.
"""
from __future__ import annotations

import argparse
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kb"))
from mapdata import parse_tree, serialize_tree  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "server/YurOTS/ots/data"
T_AREA, T_TILE, T_ITEM = 4, 5, 6
G_CONTAINER, G_TELEPORT, G_SPLASH, G_FLUID = 2, 7, 11, 12
FLAG_STACKABLE = 1 << 7


def load_otb(path: Path) -> dict[int, tuple[int, int]]:
    """server id -> (grupo, flags), como Items::loadFromOtb."""
    out = {}
    for group, props, _ in parse_tree(path.read_bytes())[2]:
        props = bytes(props)
        flags, pos, sid = struct.unpack_from("<I", props, 0)[0], 4, None
        while pos + 3 <= len(props):
            size = struct.unpack_from("<H", props, pos + 1)[0]
            if props[pos] == 0x10:
                sid = struct.unpack_from("<H", props, pos + 3)[0]
            pos += 3 + size
        if sid is not None:
            out[sid] = (group, flags)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", type=Path, default=DATA / "world/test.otbm")
    ap.add_argument("--otb", type=Path, default=DATA / "items/items-zagan-test.otb")
    ap.add_argument("--fix", action="store_true")
    args = ap.parse_args()

    items = load_otb(args.otb)

    def needs_count(i: int) -> bool:
        g, f = items.get(i, (0, 0))
        return bool(f & FLAG_STACKABLE) or g in (G_SPLASH, G_FLUID)

    def check_item(node) -> str | None:
        p = bytes(node[1])
        if len(p) < 2:
            return "item sin id"
        i = struct.unpack_from("<H", p)[0]
        if i not in items:
            return f"id {i} no existe en el otb"
        pos = 2
        if needs_count(i):
            if len(p) == 2 and args.fix:
                node[1] += b"\x01"
                fixed[i] += 1
                return None
            if pos >= len(p):
                return f"id {i} apilable/fluido sin byte de cantidad"
            pos += 1
        while pos < len(p):
            a = p[pos]
            pos += 1
            if a in (4, 5, 10):                       # actionId, uniqueId, depotId
                if a == 10 and items[i][0] != G_CONTAINER:
                    return f"id {i} con depotId sin ser contenedor"
                pos += 2
            elif a in (6, 7):                         # texto, descripción
                pos += 2 + struct.unpack_from("<H", p, pos)[0]
            elif a == 8:                              # destino de teleport
                if items[i][0] != G_TELEPORT:
                    return f"id {i} con destino sin ser teleport"
                pos += 5
            elif a == 12:                             # cargas de runa
                pos += 1
            else:
                return f"id {i} con atributo desconocido {a}"
            if pos > len(p):
                return f"id {i} con atributo {a} cortado"
        for child in node[2]:
            if child[0] == T_ITEM:
                err = check_item(child)
                if err:
                    return err
        return None

    raw = args.map.read_bytes()
    root = parse_tree(raw)
    errors: list[tuple[tuple[int, int, int], str]] = []
    fixed: Counter = Counter()
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        bx, by, bz = struct.unpack_from("<HHB", bytes(area[1]))
        for tile in area[2]:
            if tile[0] != T_TILE:                     # las house tiles el server las saltea
                continue
            tp = bytes(tile[1])
            where, pos = (bx + tp[0], by + tp[1], bz), 2
            while pos < len(tp):
                a = tp[pos]
                pos += 1
                if a == 3:
                    pos += 4
                elif a == 9:
                    i = struct.unpack_from("<H", tp, pos)[0]
                    pos += 2 + (1 if needs_count(i) else 0)
                else:
                    errors.append((where, f"atributo de casilla desconocido {a}"))
                    break
            for it in tile[2]:
                if it[0] == T_ITEM:
                    err = check_item(it)
                    if err:
                        errors.append((where, err))

    if fixed:
        args.map.write_bytes(serialize_tree(root, raw[:4]))
        print("corregidos:", ", ".join(f"{n} x id {i}" for i, n in fixed.items()))
    print(f"{args.map.name} con {args.otb.name}: {len(errors)} errores")
    for msg, n in Counter(e for _, e in errors).most_common():
        first = next(w for w, e in errors if e == msg)
        print(f"  {n:4d}  {msg}  (primero en {first[0]},{first[1]},{first[2]})")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
