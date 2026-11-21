#!/usr/bin/env python3
"""Patch rune display names (ITEM_ATTR_NAME) in items.otb and items-zagan-test.otb.

Fixes Desintegrate (2310: 'annikilator rune' -> 'adito tera') and sets proper
spell words for Wild Growth (2269) and the 5 new runes (2271, 2274, 2288, 2295, 2315).
Self-contained (stdlib only, no PIL required).
"""
from __future__ import annotations

import struct
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.project_root import project_root  # noqa: E402

ROOT = project_root(Path(__file__))

NODE_START = 0xFE
NODE_END = 0xFF
ESCAPE_CHAR = 0xFD

ITEM_ATTR_SERVERID = 0x10
ITEM_ATTR_NAME = 0x12

RUNE_NAMES: dict[int, str] = {
    2269: "adevo grav vita",  # Wild Growth
    2271: "adori frigo",      # Icicle
    2274: "adori mas frigo",  # Avalanche
    2288: "adori mas tera",   # Stone Shower
    2295: "adori san",        # Holy Missile
    2310: "adito tera",       # Desintegrate (was 'annikilator rune')
    2315: "adori mas vis",    # Thunderstorm
}

OTB_PATHS = (
    ROOT / "server" / "YurOTS" / "ots" / "data" / "items" / "items.otb",
    ROOT / "server" / "YurOTS" / "ots" / "data" / "items" / "items-zagan-test.otb",
)


@dataclass
class Node:
    node_type: int
    props: bytes
    children: list["Node"]


def parse_node(data: bytes, pos: int) -> tuple[Node, int]:
    if data[pos] != NODE_START:
        raise ValueError(f"Expected NODE_START at {pos}")
    pos += 1
    node_type = data[pos]
    pos += 1
    props = bytearray()
    children: list[Node] = []
    n = len(data)
    while pos < n:
        b = data[pos]
        if b == NODE_START:
            child, pos = parse_node(data, pos)
            children.append(child)
        elif b == NODE_END:
            pos += 1
            return Node(node_type=node_type, props=bytes(props), children=children), pos
        elif b == ESCAPE_CHAR:
            pos += 1
            props.append(data[pos])
            pos += 1
        else:
            props.append(b)
            pos += 1
    raise ValueError("Unterminated OTB node")


def _escape(raw: bytes) -> bytes:
    out = bytearray()
    for b in raw:
        if b in (NODE_START, NODE_END, ESCAPE_CHAR):
            out.append(ESCAPE_CHAR)
        out.append(b)
    return bytes(out)


def write_node(node: Node) -> bytes:
    out = bytearray()
    out.append(NODE_START)
    out.append(node.node_type)
    out.extend(_escape(node.props))
    for child in node.children:
        out.extend(write_node(child))
    out.append(NODE_END)
    return bytes(out)


def parse_item_props(props: bytes) -> tuple[int, list[tuple[int, bytes]]]:
    flags = struct.unpack_from("<I", props, 0)[0]
    blocks: list[tuple[int, bytes]] = []
    idx = 4
    while idx + 3 <= len(props):
        attr = props[idx]
        idx += 1
        alen = struct.unpack_from("<H", props, idx)[0]
        idx += 2
        val = props[idx : idx + alen]
        idx += alen
        blocks.append((attr, val))
    return flags, blocks


def build_item_props(flags: int, blocks: list[tuple[int, bytes]]) -> bytes:
    out = bytearray(struct.pack("<I", flags))
    for attr, val in blocks:
        out.append(attr)
        out.extend(struct.pack("<H", len(val)))
        out.extend(val)
    return bytes(out)


def upsert_block(blocks: list[tuple[int, bytes]], attr: int, payload: bytes) -> list[tuple[int, bytes]]:
    replaced = False
    out: list[tuple[int, bytes]] = []
    for k, v in blocks:
        if k == attr:
            out.append((k, payload))
            replaced = True
        else:
            out.append((k, v))
    if not replaced:
        out.append((attr, payload))
    return out


def server_id_from_blocks(blocks: list[tuple[int, bytes]]) -> int | None:
    for k, v in blocks:
        if k == ITEM_ATTR_SERVERID and len(v) == 2:
            sid = struct.unpack("<H", v)[0]
            if 20000 < sid < 20100:
                sid -= 20000
            return sid
    return None


def patch_otb(path: Path) -> bool:
    if not path.is_file():
        print(f"skip missing {path}")
        return False

    data = path.read_bytes()
    header = data[:4]
    root_node, end_pos = parse_node(data, 4)
    assert end_pos == len(data), f"Trailing bytes in {path}: {end_pos} vs {len(data)}"

    found: set[int] = set()
    for idx, node in enumerate(root_node.children):
        if len(node.props) < 4:
            continue
        flags, blocks = parse_item_props(node.props)
        sid = server_id_from_blocks(blocks)
        if sid in RUNE_NAMES:
            blocks = upsert_block(blocks, ITEM_ATTR_NAME, RUNE_NAMES[sid].encode("latin-1"))
            root_node.children[idx] = Node(
                node_type=node.node_type,
                props=build_item_props(flags, blocks),
                children=node.children,
            )
            found.add(sid)

    missing = set(RUNE_NAMES) - found
    if missing:
        raise SystemExit(f"missing server ids {sorted(missing)} in {path}")

    out = header + write_node(root_node)
    # Round-trip sanity check before writing
    check_root, check_end = parse_node(out, 4)
    assert check_end == len(out) and len(check_root.children) == len(root_node.children)

    path.write_bytes(out)
    print(f"patched {path} ({len(data)} -> {len(out)} bytes, {len(found)} runes, {len(check_root.children)} total items)")
    return True


def main() -> None:
    patched = sum(1 for path in OTB_PATHS if patch_otb(path))
    if patched == 0:
        raise SystemExit("no OTB files patched")


if __name__ == "__main__":
    main()
