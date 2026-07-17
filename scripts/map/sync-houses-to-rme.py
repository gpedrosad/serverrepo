#!/usr/bin/env python3
"""Sincroniza data/houses.xml -> test-house.xml + tiles OTBM para Remere's Map Editor."""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NODE_START = 0xFE
NODE_END = 0xFF
ESCAPE_CHAR = 0xFD

OTBM_TILE_AREA = 4
OTBM_TILE = 5
OTBM_HOUSETILE = 14

DEFAULT_TOWN_ID = 1
DEFAULT_RENT = 0


def load_sync_module(project: Path):
    spec = importlib.util.spec_from_file_location(
        "sync_houses_with_map", project / "scripts/sync-houses-with-map.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def load_house_entries(houses_xml: Path, owners_dir: Path, iter_tiles) -> list[dict]:
    root = ET.parse(houses_xml).getroot()
    entries: list[dict] = []
    for idx, house in enumerate(root.findall("house"), start=1):
        name = house.get("name", f"House #{idx}")
        tiles = list(iter_tiles(house))
        entry = load_frontdoor(owners_dir / f"{name}.xml")
        entries.append(
            {
                "id": idx,
                "name": name,
                "tiles": tiles,
                "entry": entry or (tiles[0] if tiles else (0, 0, 0)),
            }
        )
    return entries


def load_frontdoor(path: Path) -> tuple[int, int, int] | None:
    if not path.is_file():
        return None
    root = ET.parse(path).getroot()
    door = root.find("frontdoor")
    if door is None:
        return None
    return (
        int(door.get("x", 0)),
        int(door.get("y", 0)),
        int(door.get("z", 0)),
    )


def build_coord_map(entries: list[dict]) -> dict[tuple[int, int, int], int]:
    out: dict[tuple[int, int, int], int] = {}
    for entry in entries:
        for coord in entry["tiles"]:
            out[coord] = entry["id"]
    return out


def read_props(data: bytes, pos: int) -> tuple[bytes, int]:
    out = bytearray()
    while pos < len(data):
        b = data[pos]
        pos += 1
        if b in (NODE_START, NODE_END):
            pos -= 1
            break
        if b == ESCAPE_CHAR:
            if pos >= len(data):
                raise ValueError("OTBM truncado (escape)")
            out.append(data[pos])
            pos += 1
        else:
            out.append(b)
    return bytes(out), pos


def write_props(buf: bytearray, props: bytes):
    for b in props:
        if b in (NODE_START, NODE_END, ESCAPE_CHAR):
            buf.append(ESCAPE_CHAR)
        buf.append(b)


def patch_tile_props(
    node_type: int,
    props: bytes,
    coord_to_hid: dict[tuple[int, int, int], int],
    pos: tuple[int, int, int],
) -> tuple[int, bytes, bool]:
    if len(props) < 2:
        return node_type, props, False
    x_off, y_off = props[0], props[1]
    rest = props[2:]
    hid = coord_to_hid.get(pos)
    if hid is None:
        return node_type, props, False

    if node_type == OTBM_HOUSETILE and len(rest) >= 4:
        new_props = bytes([x_off, y_off]) + struct.pack("<I", hid) + rest[4:]
        changed = rest[0:4] != struct.pack("<I", hid)
    else:
        new_props = bytes([x_off, y_off]) + struct.pack("<I", hid) + rest
        changed = node_type != OTBM_HOUSETILE
    return OTBM_HOUSETILE, new_props, changed


def patch_node(
    data: bytes,
    pos: int,
    coord_to_hid: dict[tuple[int, int, int], int],
    area_base: tuple[int, int, int],
) -> tuple[bytes, int, int]:
    if pos >= len(data) or data[pos] != NODE_START:
        return b"", pos, 0

    out = bytearray()
    out.append(NODE_START)
    pos += 1
    node_type = data[pos]
    pos += 1
    props, pos = read_props(data, pos)

    local_base = area_base
    marked = 0
    new_type = node_type
    new_props = props

    if node_type == OTBM_TILE_AREA and len(props) >= 5:
        bx, by, bz = struct.unpack_from("<HHB", props, 0)
        local_base = (bx, by, bz)
    elif node_type in (OTBM_TILE, OTBM_HOUSETILE) and len(props) >= 2:
        abs_pos = (local_base[0] + props[0], local_base[1] + props[1], local_base[2])
        new_type, new_props, changed = patch_tile_props(
            node_type, props, coord_to_hid, abs_pos
        )
        if changed:
            marked += 1

    out.append(new_type)
    write_props(out, new_props)

    depth = 1
    while pos < len(data) and depth > 0:
        if data[pos] == NODE_START:
            child, pos, cm = patch_node(data, pos, coord_to_hid, local_base)
            out.extend(child)
            marked += cm
        elif data[pos] == NODE_END:
            out.append(NODE_END)
            pos += 1
            depth -= 1
        else:
            out.append(data[pos])
            pos += 1

    return bytes(out), pos, marked


def patch_otbm_file(data: bytes, coord_to_hid: dict[tuple[int, int, int], int]) -> tuple[bytes, int]:
    if len(data) < 4:
        raise ValueError("OTBM demasiado corto")
    header, body = data[:4], data[4:]
    if not body or body[0] != NODE_START:
        raise ValueError("OTBM sin nodo raíz")
    patched_body, end_pos, marked = patch_node(body, 0, coord_to_hid, (0, 0, 0))
    if end_pos < len(body):
        patched_body += body[end_pos:]
    return header + patched_body, marked


def write_rme_houses_xml(path: Path, entries: list[dict], town_id: int = DEFAULT_TOWN_ID):
    root = ET.Element("houses")
    for entry in entries:
        ex, ey, ez = entry["entry"]
        ET.SubElement(
            root,
            "house",
            {
                "name": entry["name"],
                "houseid": str(entry["id"]),
                "entryx": str(ex),
                "entryy": str(ey),
                "entryz": str(ez),
                "rent": str(DEFAULT_RENT),
                "townid": str(town_id),
                "size": str(len(entry["tiles"])),
            },
        )
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    project = Path(__file__).resolve().parents[1]
    mod = load_sync_module(project)

    otbm_path = project / "server/YurOTS/ots/data/world/test.otbm"
    houses_xml = project / "server/YurOTS/ots/data/houses.xml"
    rme_houses = project / "server/YurOTS/ots/data/world/test-house.xml"
    owners_dir = project / "server/YurOTS/ots/data/houses"

    entries = load_house_entries(houses_xml, owners_dir, mod.iter_house_tiles)
    coord_to_hid = build_coord_map(entries)
    map_tiles = mod.load_map_tiles(otbm_path)

    missing = [c for c in coord_to_hid if c not in map_tiles]
    if missing:
        print(f"AVISO: {len(missing)} tile(s) de casas no existen en el OTBM (ej. {missing[0]})")

    print(f"Casas: {len(entries)}")
    print(f"Tiles de casa: {len(coord_to_hid)}")
    print(f"Destino RME: {rme_houses}")

    if args.dry_run:
        print("(dry-run — no se escriben archivos)")
        return 0

    backup = otbm_path.with_suffix(".otbm.bak")
    if not backup.exists():
        shutil.copy2(otbm_path, backup)
        print(f"Backup OTBM: {backup}")

    house_backup = rme_houses.with_suffix(".xml.bak")
    if rme_houses.exists() and not house_backup.exists():
        shutil.copy2(rme_houses, house_backup)

    raw = otbm_path.read_bytes()
    patched, marked = patch_otbm_file(raw, coord_to_hid)
    otbm_path.write_bytes(patched)
    write_rme_houses_xml(rme_houses, entries)
    print(f"OK — {marked} tiles marcados como casa en OTBM")
    print(f"OK — {len(entries)} casas en test-house.xml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
