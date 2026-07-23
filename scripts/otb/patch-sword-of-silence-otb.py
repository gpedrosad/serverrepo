#!/usr/bin/env python3
"""Patch server id 20139: dawnbreak falchion -> sword of silence (atk 42).

Only upserts name/descr/weapon2 on the existing node (no prototype rebuild).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.project_root import project_root  # noqa: E402

ROOT = project_root(Path(__file__))

from build_zagan_test_assets import (  # noqa: E402
    ITEM_ATTR_DESCR,
    ITEM_ATTR_NAME,
    ITEM_ATTR_SERVERID,
    Node,
    build_item_props,
    get_block_payload,
    parse_item_props,
    parse_node,
    upsert_block,
    write_node,
)

ITEM_ATTR_WEAPON2 = 0x26

TARGET_SERVER_ID = 20139
ITEM_NAME = "sword of silence"
ITEM_DESCR = (
    "A blade that steals the voice. 10% chance to silence a player "
    "for 2-3s (spoken spells only). 12s cooldown per target."
)
ATTACK = 42
DEFENCE = 30

OTB_PATHS = (
    ROOT / "server" / "YurOTS" / "ots" / "data" / "items" / "items-zagan-test.otb",
    ROOT / "zagan-test" / "server-items" / "items.otb",
    ROOT / "rme-zagan-test-root" / "data" / "760" / "items.otb",
)


def _server_id_from_props(props: bytes) -> int | None:
    _, blocks = parse_item_props(props)
    payload = get_block_payload(blocks, ITEM_ATTR_SERVERID)
    if not payload or len(payload) != 2:
        return None
    server_id = struct.unpack("<H", payload)[0]
    if 20000 < server_id < 20100:
        server_id -= 20000
    return server_id


def patch_otb(path: Path) -> bool:
    if not path.is_file():
        print(f"skip missing {path}")
        return False

    data = path.read_bytes()
    root_node, _ = parse_node(data, 4)
    target_idx = None
    for idx, node in enumerate(root_node.children):
        if _server_id_from_props(node.props) == TARGET_SERVER_ID:
            target_idx = idx
            break

    if target_idx is None:
        raise SystemExit(f"target {TARGET_SERVER_ID} not found in {path}")

    node = root_node.children[target_idx]
    flags, blocks = parse_item_props(node.props)
    blocks = upsert_block(blocks, ITEM_ATTR_NAME, ITEM_NAME.encode("latin-1"))
    blocks = upsert_block(blocks, ITEM_ATTR_DESCR, ITEM_DESCR.encode("latin-1"))
    blocks = upsert_block(
        blocks,
        ITEM_ATTR_WEAPON2,
        bytes([1, 0, 0, ATTACK, DEFENCE]),
    )
    root_node.children[target_idx] = Node(
        node_type=node.node_type,
        props=build_item_props(flags, blocks),
        children=[],
    )

    out = b"\x00\x00\x00\x00" + write_node(root_node)
    path.write_bytes(out)
    print(f"patched {path} ({len(data)} -> {len(out)} bytes)")
    return True


def main() -> None:
    patched = sum(1 for path in OTB_PATHS if patch_otb(path))
    if patched == 0:
        raise SystemExit("no OTB files patched")


if __name__ == "__main__":
    main()
