#!/usr/bin/env python3
"""Agrega / actualiza el Enchanted Spear (server id 20156) en items-zagan-test.otb.

  enchanted spear   arma a distancia arrojadiza (como la spear), ataque 36 (spear 30),
                    no se apila, no se gasta al tirarla. Proyectil: el de la spear por ahora.
  client id 3576    sprite propio (scripts/client-rme/add_enchanted_spear.py); antes era
                    "post officers hat" (2665), que no se usa en ningún lado.

El nodo va AL FINAL del OTB: el servidor arma client id -> server id con "el último gana",
así el cliente que manda 3576 queda apuntando a 20156.
La puntería (80%, spear 70%) y la descripción extra están en C++ (const76.h, player.cpp,
item.cpp). Idempotente. Ver docs/gameplay/ENCHANTED_SPEAR.md.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OTB_PATHS = (
    ROOT / "server/YurOTS/ots/data/items/items-zagan-test.otb",
    ROOT / "zagan-test/server-items/items.otb",
    ROOT / "rme-zagan-test-root/data/760/items.otb",
)

SERVER_ID = 20156
CLIENT_ID = 3576
PROTOTYPE_ID = 2389          # spear: peso y casillas de equipo
NAME = "enchanted spear"
DESCR = "Its crystal head hums with arcane power."
ATTACK, DEFENSE = 36, 0
DIST, AMMO_NONE, SHOOT_SPEAR = 5, 0, 14

GROUP_WEAPON = 3
FLAGS = 0x20 | 0x40          # agarrable + movible (la spear además es apilable: 0x80)
A_SERVER, A_CLIENT, A_NAME, A_DESCR, A_WEAPON = 0x10, 0x11, 0x12, 0x13, 0x26
NODE_START, NODE_END, ESCAPE = 0xFE, 0xFF, 0xFD


class Node:
    def __init__(self, kind: int, props: bytes, children: list["Node"]):
        self.kind, self.props, self.children = kind, props, children


def parse(data: bytes, pos: int) -> tuple[Node, int]:
    assert data[pos] == NODE_START
    kind, pos = data[pos + 1], pos + 2
    props, children = bytearray(), []
    while True:
        b = data[pos]
        if b == ESCAPE:
            props.append(data[pos + 1])
            pos += 2
        elif b == NODE_START:
            child, pos = parse(data, pos)
            children.append(child)
        elif b == NODE_END:
            return Node(kind, bytes(props), children), pos + 1
        else:
            props.append(b)
            pos += 1


def escape(raw: bytes) -> bytes:
    out = bytearray()
    for b in raw:
        if b in (NODE_START, NODE_END, ESCAPE):
            out.append(ESCAPE)
        out.append(b)
    return bytes(out)


def write(node: Node) -> bytes:
    return (bytes([NODE_START, node.kind]) + escape(node.props)
            + b"".join(write(c) for c in node.children) + bytes([NODE_END]))


def blocks(props: bytes) -> tuple[bytes, list[tuple[int, bytes]]]:
    out, p = [], 4
    while p + 3 <= len(props):
        attr, size = props[p], struct.unpack_from("<H", props, p + 1)[0]
        out.append((attr, props[p + 3:p + 3 + size]))
        p += 3 + size
    return props[:4], out


def build(flags: bytes, items: list[tuple[int, bytes]]) -> bytes:
    return flags + b"".join(bytes([a]) + struct.pack("<H", len(v)) + v for a, v in items)


def server_id(node: Node) -> int | None:
    for attr, val in blocks(node.props)[1]:
        if attr == A_SERVER and len(val) == 2:
            return struct.unpack("<H", val)[0]
    return None


def make_node(proto: Node) -> Node:
    _flags, proto_blocks = blocks(proto.props)
    keep = {a: v for a, v in proto_blocks}
    items = [
        (A_SERVER, struct.pack("<H", SERVER_ID)),
        (A_CLIENT, struct.pack("<H", CLIENT_ID)),
        (A_NAME, NAME.encode("latin-1")),
        (A_DESCR, DESCR.encode("latin-1")),
    ]
    for attr in (0x17, 0x15):            # peso y casillas, igual que la spear
        if attr in keep:
            items.append((attr, keep[attr]))
    items.append((A_WEAPON, bytes([DIST, AMMO_NONE, SHOOT_SPEAR, ATTACK, DEFENSE])))
    return Node(GROUP_WEAPON, build(struct.pack("<I", FLAGS), items), [])


def patch(path: Path) -> bool:
    if not path.is_file():
        print(f"(no existe, se saltea) {path}")
        return False
    data = path.read_bytes()
    root, end = parse(data, 4)
    if end != len(data):
        raise SystemExit(f"{path}: quedaron bytes sin leer ({end} de {len(data)})")
    proto = next((c for c in root.children if server_id(c) == PROTOTYPE_ID), None)
    if proto is None:
        raise SystemExit(f"{path}: no está la spear ({PROTOTYPE_ID})")
    for c in root.children:
        sid = server_id(c)
        if sid is not None and sid >= 20000 and sid != SERVER_ID:
            cid = dict(blocks(c.props)[1]).get(A_CLIENT)
            if cid and struct.unpack("<H", cid)[0] == CLIENT_ID:
                raise SystemExit(f"{path}: el client id {CLIENT_ID} ya lo usa el ítem {sid}")
    root.children = [c for c in root.children if server_id(c) != SERVER_ID] + [make_node(proto)]
    out = data[:4] + write(root)
    check, _ = parse(out, 4)
    assert server_id(check.children[-1]) == SERVER_ID
    if out == data:
        print(f"sin cambios {path}")
    else:
        path.write_bytes(out)
        print(f"actualizado {path}")
    return True


def main() -> int:
    if not any([patch(p) for p in OTB_PATHS]):
        raise SystemExit("no se encontró ningún OTB")
    print(f"  {SERVER_ID} {NAME}: distancia, ataque {ATTACK}, client id {CLIENT_ID}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
