#!/usr/bin/env python3
"""Patch windsting (20130) in items-zagan-test.otb: axe atk 43 / def 22, 1H."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OTB = ROOT / "server/YurOTS/ots/data/items/items-zagan-test.otb"
SERVER_ID = 20130
AXE = 3
ATTACK = 43
DEFENCE = 22
SLOT_HAND = 10  # OTB_SLOT_HAND


def main() -> int:
    data = bytearray(OTB.read_bytes())
    marker = struct.pack("<BHH", 0x10, 2, SERVER_ID)  # ATTR_SERVERID, len, id
    # ATTR layout is: attr(1) + len(2 LE) + payload
    needle = bytes([0x10, 0x02, 0x00]) + struct.pack("<H", SERVER_ID)
    idx = data.find(needle)
    if idx < 0:
        print(f"ERROR: server id {SERVER_ID} not found in {OTB}", file=sys.stderr)
        return 1

    end = min(len(data), idx + 220)
    chunk = memoryview(data)[idx:end]

    # Rename bow -> axe in name/descr (same length)
    old = b"windsting bow"
    new = b"windsting axe"
    replaced = 0
    search_from = idx
    while True:
        pos = data.find(old, search_from, end)
        if pos < 0:
            break
        data[pos : pos + len(old)] = new
        replaced += 1
        search_from = pos + len(new)
    if replaced < 1:
        # Already renamed is OK
        if data.find(new, idx, end) < 0:
            print("ERROR: neither windsting bow nor windsting axe name found", file=sys.stderr)
            return 1

    # SLOT attr 0x15
    slot_at = data.find(bytes([0x15, 0x02, 0x00]), idx, end)
    # WEAPON2 attr 0x26
    weap_at = data.find(bytes([0x26, 0x05, 0x00]), idx, end)
    if slot_at < 0 or weap_at < 0:
        print(f"ERROR: slot/weapon attrs missing (slot={slot_at}, weap={weap_at})", file=sys.stderr)
        return 1

    data[slot_at + 3 : slot_at + 5] = struct.pack("<H", SLOT_HAND)
    data[weap_at + 3] = AXE
    data[weap_at + 4] = 0  # amu
    data[weap_at + 5] = 0  # shoot
    data[weap_at + 6] = ATTACK
    data[weap_at + 7] = DEFENCE

    OTB.write_bytes(data)
    print(
        f"OK: {OTB.name} id={SERVER_ID} -> axe atk={ATTACK} def={DEFENCE} "
        f"slot=HAND name replacements={replaced}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
