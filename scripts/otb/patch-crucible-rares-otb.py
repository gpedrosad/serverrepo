#!/usr/bin/env python3
"""El Crisol rares: 7 armas Zagan con stats + nombres exclusivos.

IDs (ya son WEAPON en OTB; solo upsert name/descr/weapon2):
  20112 ashlord emberblade   sword  44/28
  20138 frostwarden chillblade sword 42/34
  20154 bonepriest reaver    axe    43/24
  20121 ironhide crusher     club   50/16
  20100 venomqueen fang      sword  39/22
  20110 stormcaller maul     club   46/14
  20122 bloodreaver saber    sword  46/28
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
ITEM_GROUP_WEAPON = 3

# weaponType: 1 sword, 2 club, 3 axe
RARES = {
    20112: ("ashlord emberblade", "Crucible rare. Fast fire sword: fire trail, 20% burn DoT.", 1, 44, 28),
    20138: ("frostwarden chillblade", "Crucible rare. 18% chill (slow) for 4s in PvP.", 1, 42, 34),
    20154: ("bonepriest reaver", "Crucible rare. 15% mana drain on hit.", 3, 43, 24),
    20121: ("ironhide crusher", "Crucible rare. Slow heavy club: 22% root 2.5s in PvP.", 2, 50, 16),
    20100: ("venomqueen fang", "Crucible rare. Very fast: 25% poison DoT.", 1, 39, 22),
    20110: ("stormcaller maul", "Crucible rare. Fast club: energy trail, 20% energy burst.", 2, 46, 14),
    20122: ("bloodreaver saber", "Crucible rare. 30% life leech (25% of damage).", 1, 46, 28),
}

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
    changed = 0
    for idx, node in enumerate(root_node.children):
        sid = _server_id_from_props(node.props)
        if sid not in RARES:
            continue
        name, descr, wtype, atk, defence = RARES[sid]
        flags, blocks = parse_item_props(node.props)
        blocks = upsert_block(blocks, ITEM_ATTR_NAME, name.encode("latin-1"))
        blocks = upsert_block(blocks, ITEM_ATTR_DESCR, descr.encode("latin-1"))
        blocks = upsert_block(
            blocks,
            ITEM_ATTR_WEAPON2,
            bytes([wtype, 0, 0, atk, defence]),
        )
        root_node.children[idx] = Node(
            node_type=ITEM_GROUP_WEAPON,
            props=build_item_props(flags, blocks),
            children=[],
        )
        changed += 1

    if changed != len(RARES):
        raise SystemExit(f"{path}: patched {changed}/{len(RARES)}")

    out = b"\x00\x00\x00\x00" + write_node(root_node)
    path.write_bytes(out)
    print(f"patched {path} ({changed} rares)")
    return True


def main() -> None:
    if sum(1 for path in OTB_PATHS if patch_otb(path)) == 0:
        raise SystemExit("no OTB files patched")
    for sid, (name, _, wtype, atk, defence) in sorted(RARES.items()):
        kind = {1: "sword", 2: "club", 3: "axe"}[wtype]
        print(f"  {sid} {name} ({kind} {atk}/{defence})")


if __name__ == "__main__":
    main()
