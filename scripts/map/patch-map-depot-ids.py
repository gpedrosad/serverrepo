#!/usr/bin/env python3
"""Agrega OTBM_ATTR_DEPOT_ID=1 a lockers 2589 en nodos OTBM_ITEM hijos.

Nota: lockers colocados como OTBM_ATTR_ITEM inline en el tile (export RME típico)
NO los parchea este script. Para esos, el servidor usa resolveMapDepotId() en
actions.cpp (fallback depotid=1). Ver AGENTS.md § Depots en mapa.
"""
from __future__ import annotations

import argparse
import shutil
import struct
from pathlib import Path

LOCKER_ITEM_ID = 2589
LOCKER_PROPS = struct.pack("<H", LOCKER_ITEM_ID)          # 1d0a
LOCKER_PROPS_WITH_DEPOT = LOCKER_PROPS + bytes([10, 1, 0])  # + depotid 1

NODE_START = 0xFE
NODE_END = 0xFF
ESCAPE = 0xFD
OTBM_ITEM = 6


def read_props(data: bytes, start: int) -> tuple[bytes, int]:
    j = start
    props = bytearray()
    while j < len(data):
        b = data[j]
        if b in (NODE_START, NODE_END):
            break
        if b == ESCAPE:
            j += 1
            if j >= len(data):
                break
            props.append(data[j])
            j += 1
        else:
            props.append(b)
            j += 1
    return bytes(props), j


def patch_otbm(data: bytearray) -> int:
    patched = 0
    i = 4
    while i < len(data) - 2:
        if data[i] == NODE_START and data[i + 1] == OTBM_ITEM:
            props, end = read_props(data, i + 2)
            if props == LOCKER_PROPS:
                new_props = LOCKER_PROPS_WITH_DEPOT
                data[i + 2 : end] = new_props
                delta = len(new_props) - len(props)
                i = end + delta
                patched += 1
                continue
        i += 1
    return patched


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("map", type=Path, help="test.otbm a parchear")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = args.map.read_bytes()
    buf = bytearray(src)
    n = patch_otbm(buf)
    print(f"{args.map.name}: {n} locker(s) 2589 parcheados con depotid=1")
    if n == 0:
        return
    if args.dry_run:
        print("(dry-run, sin escribir)")
        return

    backup = args.map.with_suffix(args.map.suffix + ".pre-depot-patch.bak")
    if not backup.exists():
        shutil.copy2(args.map, backup)
        print(f"backup → {backup}")
    args.map.write_bytes(buf)
    print(f"OK → {args.map}")


if __name__ == "__main__":
    main()
