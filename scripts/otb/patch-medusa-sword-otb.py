#!/usr/bin/env python3
"""Patch server id 20105 from selenite prism (ring) to medusa sword (weapon)."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_zagan_test_assets import (  # noqa: E402
    ITEM_ATTR_CLIENTID,
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

ITEM_GROUP_WEAPON = 3
TARGET_SERVER_ID = 20105
TARGET_CLIENT_ID = 4852
PROTOTYPE_SERVER_ID = 2446
ITEM_NAME = "medusa sword"
ITEM_DESCR = (
    "A cursed blade with a petrifying gaze. "
    "Every hit against a player paralyzes them in PvP."
)
ATTACK = 42
DEFENCE = 23

OTB_PATHS = (
    ROOT / "zagan-test" / "server-items" / "items.otb",
    ROOT / "server" / "YurOTS" / "ots" / "data" / "items" / "items-zagan-test.otb",
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
    nodes: list[Node] = [child for child in root_node.children]

    prototype = None
    target_idx = None
    for idx, node in enumerate(nodes):
        server_id = _server_id_from_props(node.props)
        if server_id == PROTOTYPE_SERVER_ID:
            prototype = node
        if server_id == TARGET_SERVER_ID:
            target_idx = idx

    if prototype is None:
        raise SystemExit(f"prototype {PROTOTYPE_SERVER_ID} not found in {path}")
    if target_idx is None:
        raise SystemExit(f"target {TARGET_SERVER_ID} not found in {path}")

    flags, blocks = parse_item_props(prototype.props)
    blocks = [
        block
        for block in blocks
        if block[0]
        not in (ITEM_ATTR_SERVERID, ITEM_ATTR_CLIENTID, ITEM_ATTR_NAME, ITEM_ATTR_DESCR)
    ]
    blocks = upsert_block(blocks, ITEM_ATTR_SERVERID, struct.pack("<H", TARGET_SERVER_ID))
    blocks = upsert_block(blocks, ITEM_ATTR_CLIENTID, struct.pack("<H", TARGET_CLIENT_ID))
    blocks = upsert_block(blocks, ITEM_ATTR_NAME, ITEM_NAME.encode("latin-1"))
    blocks = upsert_block(blocks, ITEM_ATTR_DESCR, ITEM_DESCR.encode("latin-1"))
    blocks = upsert_block(
        blocks,
        ITEM_ATTR_WEAPON2,
        bytes([1, 0, 0, ATTACK, DEFENCE]),
    )

    nodes[target_idx] = Node(
        node_type=ITEM_GROUP_WEAPON,
        props=build_item_props(flags, blocks),
        children=[],
    )

    root_node.children = nodes
    path.write_bytes(b"\x00\x00\x00\x00" + write_node(root_node))
    print(f"patched {path}")
    return True


def main() -> None:
    patched = sum(1 for path in OTB_PATHS if patch_otb(path))
    if patched == 0:
        raise SystemExit("no OTB files patched")


if __name__ == "__main__":
    main()
