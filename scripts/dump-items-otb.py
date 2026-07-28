#!/usr/bin/env python3
"""Vuelca todos los items de un items.otb a texto, ordenados por server id.

Uso:
    python3 scripts/dump-items-otb.py [ruta/items.otb] [salida.txt]

Por defecto lee server/YurOTS/ots/data/items/items.otb y escribe
docs/items-and-map/ITEMS_OTB_DUMP.txt.
"""

import struct
import sys
from pathlib import Path

NODE_START, NODE_END, ESCAPE = 0xFE, 0xFF, 0xFD

ATTR_SERVERID = 0x10
ATTR_CLIENTID = 0x11
ATTR_NAME = 0x12
ATTR_DESCR = 0x13

GROUP_NAMES = {
    0: "none",
    1: "ground",
    2: "container",
    3: "weapon",
    4: "ammunition",
    5: "armor",
    6: "changes",
    7: "teleport",
    8: "magicfield",
    9: "writable",
    10: "key",
    11: "splash",
    12: "fluid",
    13: "door",
}

FLAG_LABELS = [
    (1 << 0, "blockSolid"),
    (1 << 1, "blockProjectile"),
    (1 << 2, "blockPathFind"),
    (1 << 3, "hasHeight"),
    (1 << 4, "useable"),
    (1 << 5, "pickupable"),
    (1 << 6, "moveable"),
    (1 << 7, "stackable"),
    (1 << 8, "floorChangeDown"),
    (1 << 9, "floorChangeNorth"),
    (1 << 10, "floorChangeEast"),
    (1 << 11, "floorChangeSouth"),
    (1 << 12, "floorChangeWest"),
    (1 << 13, "alwaysOnTop"),
    (1 << 14, "readable"),
    (1 << 15, "rotable"),
    (1 << 16, "hangable"),
    (1 << 17, "vertical"),
    (1 << 18, "horizontal"),
    (1 << 26, "lookThrough"),
]


def read_node(data, i):
    assert data[i] == NODE_START
    i += 1
    node_type = data[i]
    i += 1
    props = bytearray()
    children = []
    while True:
        b = data[i]
        if b == ESCAPE:
            props.append(data[i + 1])
            i += 2
        elif b == NODE_START:
            child, i = read_node(data, i)
            children.append(child)
        elif b == NODE_END:
            i += 1
            return (node_type, bytes(props), children), i
        else:
            props.append(b)
            i += 1


def parse_items(path):
    data = path.read_bytes()
    root, _ = read_node(data, 4)  # salta los 4 bytes de version
    items = []
    for node_type, props, _ in root[2]:
        if len(props) < 4:
            continue
        flags = struct.unpack("<I", props[:4])[0]
        p = 4
        sid = cid = None
        name = descr = ""
        while p + 3 <= len(props):
            attr = props[p]
            dl = struct.unpack("<H", props[p + 1:p + 3])[0]
            p += 3
            val = props[p:p + dl]
            p += dl
            if attr == ATTR_SERVERID:
                sid = struct.unpack("<H", val)[0]
            elif attr == ATTR_CLIENTID:
                cid = struct.unpack("<H", val)[0]
            elif attr == ATTR_NAME:
                name = val.decode("latin1")
            elif attr == ATTR_DESCR:
                descr = val.decode("latin1")
        if sid is not None:
            items.append({
                "sid": sid,
                "cid": cid,
                "name": name,
                "descr": descr,
                "group": node_type,
                "flags": flags,
            })
    items.sort(key=lambda it: it["sid"])
    return items


def flag_str(flags):
    labels = [label for bit, label in FLAG_LABELS if flags & bit]
    return ",".join(labels) if labels else "-"


def main():
    otb_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "server/YurOTS/ots/data/items/items.otb")
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
        "docs/items-and-map/ITEMS_OTB_DUMP.txt")

    items = parse_items(otb_path)

    lines = [
        f"# Dump de {otb_path} — {len(items)} items ordenados por server id",
        "# Generado con scripts/dump-items-otb.py",
        "# sid | cid | grupo | nombre | flags",
        "",
    ]
    for it in items:
        group = GROUP_NAMES.get(it["group"], str(it["group"]))
        cid = it["cid"] if it["cid"] is not None else "-"
        name = it["name"] or "-"
        lines.append(
            f"{it['sid']:>5} | {cid:>5} | {group:<10} | {name:<40} | {flag_str(it['flags'])}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: {len(items)} items -> {out_path}")


if __name__ == "__main__":
    main()
