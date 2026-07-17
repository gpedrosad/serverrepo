#!/usr/bin/env python3
"""Patch crystal arrow (2352) into a reusable DIST weapon (spear-like).

Converts ITEM_GROUP_AMMUNITION + AMU2 into ITEM_GROUP_WEAPON + WEAPON2:
  weaponType=DIST, amuType=NONE, shootType=ARROW, attack=35, defence=0.

Keeps non-stackable flags so Blue Gem actionid imbuements stay on one item.
Patches both items.otb and items-zagan-test.otb when the id exists.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OTBS = [
    ROOT / "server/YurOTS/ots/data/items/items.otb",
    ROOT / "server/YurOTS/ots/data/items/items-zagan-test.otb",
]

SERVER_ID = 2352
GROUP_WEAPON = 3
# pickupable | moveable (non-stackable — imbue-friendly)
FLAGS = 0x60
WEAPON2 = bytes([0x26, 0x05, 0x00, 0x05, 0x00, 0x02, 35, 0x00])  # DIST, NONE, ARROW, 35, 0
OLD_AMU2 = bytes([0x27, 0x03, 0x00, 0x02, 0x02, 0x00])  # ARROW amu, ARROW shoot, atk 0


def find_server_id(data: bytes | bytearray, server_id: int) -> int:
    needle = bytes([0x10, 0x02, 0x00]) + struct.pack("<H", server_id)
    return data.find(needle)


def patch_one(path: Path) -> int:
    if not path.exists():
        print(f"SKIP missing {path}")
        return 0

    data = bytearray(path.read_bytes())
    idx = find_server_id(data, SERVER_ID)
    if idx < 0:
        print(f"SKIP id {SERVER_ID} not in {path.name}")
        return 0

    # Node layout: FE <group> <flags:u32> <attrs...>
    group_at = idx - 5
    flags_at = idx - 4
    if data[group_at - 1] != 0xFE:
        print(f"ERROR: expected NODE_START before group in {path.name}", file=sys.stderr)
        return 1

    end = min(len(data), idx + 80)
    amu_at = data.find(OLD_AMU2, idx, end)
    weap_at = data.find(bytes([0x26, 0x05, 0x00]), idx, end)

    data[group_at] = GROUP_WEAPON
    struct.pack_into("<I", data, flags_at, FLAGS)

    if weap_at >= 0 and data[weap_at : weap_at + 8] == WEAPON2:
        print(f"OK already patched {path.name} id={SERVER_ID}")
        return 0

    if amu_at >= 0:
        # Replace 6-byte AMU2 with 8-byte WEAPON2 (bytearray grows by 2).
        data[amu_at : amu_at + 6] = WEAPON2
    elif weap_at >= 0:
        data[weap_at : weap_at + 8] = WEAPON2
    else:
        print(f"ERROR: neither AMU2 nor WEAPON2 found for {SERVER_ID} in {path.name}", file=sys.stderr)
        return 1

    path.write_bytes(data)
    print(
        f"OK {path.name} id={SERVER_ID} -> WEAPON DIST atk=35 shoot=ARROW "
        f"group={GROUP_WEAPON} flags=0x{FLAGS:X} non-stackable"
    )
    return 0


def main() -> int:
    rc = 0
    for otb in OTBS:
        r = patch_one(otb)
        if r != 0:
            rc = r
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
