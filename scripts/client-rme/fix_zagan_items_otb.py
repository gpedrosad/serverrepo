#!/usr/bin/env python3
"""Corrige en items-zagan-test.otb los ítems Zagan cuyo nombre o tipo no coincidía con lo que son.

  python3.11 scripts/client-rme/fix_zagan_items_otb.py [--dry-run]

Se puede correr varias veces: si ya está corregido no escribe nada.

- 20126: se llamaba "violet sunstone" y era un anillo, pero es la train wand (ITEM_TRAIN_WAND en C++). Pasa a
  llamarse "train wand" con los mismos datos que las demás wands (sin slot de anillo).
- 20148 kilnfire leggings: iba en el pecho (prototipo chain armor). Pasa a las piernas; el peso baja de 100 a 45.
- Descripciones de los que tienen uso y decían "A strange relic known as…".
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build_zagan_test_assets as B  # noqa: E402

OTB = ROOT / "server/YurOTS/ots/data/items/items-zagan-test.otb"
A_SID, A_CID, A_NAME, A_DESCR, A_SLOT, A_WEIGHT, A_ARMOR2 = 0x10, 0x11, 0x12, 0x13, 0x15, 0x17, 0x28
GROUP_NONE, SLOT_LEGS = 0, 3

DESCR = {
    20126: "A plain wand for apprentices. It only works on training dummies.",
    20130: "A light axe that whistles as it falls. Its blows leave the enemy dizzy.",
    20131: "Restores 60-80% of the experience lost in your last death.",
    20132: "Adds 12 hours of training for today. Once per character per day.",
    20137: "A dagger cut from black volcanic glass.",
    20148: "Leg plates fired red in a kiln.",
}


def fix(node, sid: int) -> None:
    flags, blocks = B.parse_item_props(node.props)
    if sid == 20126:
        cid = B.get_block_payload(blocks, A_CID)
        blocks = [(A_SID, struct.pack("<H", sid)), (A_CID, cid), (A_NAME, b"train wand"),
                  (A_WEIGHT, struct.pack("<d", 19.0))]
        node.node_type = GROUP_NONE
    if sid == 20148:
        armor = B.get_block_payload(blocks, A_ARMOR2)
        blocks = B.upsert_block(blocks, A_WEIGHT, struct.pack("<d", 45.0))
        blocks = B.upsert_block(blocks, A_SLOT, struct.pack("<H", SLOT_LEGS))
        blocks = B.upsert_block(blocks, A_ARMOR2, armor[:2] + struct.pack("<d", 45.0) + struct.pack("<H", SLOT_LEGS))
    blocks = B.upsert_block(blocks, A_DESCR, DESCR[sid].encode("latin-1"))
    node.props = B.build_item_props(flags, blocks)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    data = OTB.read_bytes()
    root, end = B.parse_node(data, 4)
    if end != len(data):
        raise SystemExit(f"{OTB}: bytes de más al final")
    seen, changed = set(), 0
    for node in root.children:
        _flags, blocks = B.parse_item_props(node.props)
        payload = B.get_block_payload(blocks, A_SID)
        sid = struct.unpack("<H", payload)[0] if payload and len(payload) == 2 else None
        if sid not in DESCR:
            continue
        seen.add(sid)
        before = (node.node_type, node.props)
        fix(node, sid)
        name = (B.get_block_payload(B.parse_item_props(node.props)[1], A_NAME) or b"").decode("latin-1")
        if (node.node_type, node.props) != before:
            changed += 1
            print(f"  {sid} {name}: corregido")
        else:
            print(f"  {sid} {name}: ya está")
    if seen != set(DESCR):
        raise SystemExit(f"faltan en el OTB: {sorted(set(DESCR) - seen)}")
    if changed and not a.dry_run:
        OTB.write_bytes(data[:4] + B.write_node(root))
    print(f"{changed} ítems cambiados" + (" (dry-run, no se escribió)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
