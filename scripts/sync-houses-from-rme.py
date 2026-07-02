#!/usr/bin/env python3
"""Importa tiles de casas desde test.otbm (RME) a data/houses.xml para el servidor."""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import struct
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

NODE_START = 0xFE
NODE_END = 0xFF
ESCAPE_CHAR = 0xFD

OTBM_TILE_AREA = 4
OTBM_TILE = 5
OTBM_HOUSETILE = 14


def load_sync_module(project: Path):
    spec = importlib.util.spec_from_file_location(
        "sync_houses_with_map", project / "scripts/sync-houses-with-map.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


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


def collect_housetiles(
    data: bytes,
    pos: int,
    area_base: tuple[int, int, int],
    by_id: dict[int, list[tuple[int, int, int]]],
) -> tuple[int, int]:
    if pos >= len(data) or data[pos] != NODE_START:
        return pos, 0

    pos += 1
    node_type = data[pos]
    pos += 1
    props, pos = read_props(data, pos)

    local_base = area_base
    count = 0

    if node_type == OTBM_TILE_AREA and len(props) >= 5:
        bx, by, bz = struct.unpack_from("<HHB", props, 0)
        local_base = (bx, by, bz)
    elif node_type == OTBM_HOUSETILE and len(props) >= 6:
        hid = struct.unpack_from("<I", props, 2)[0]
        abs_pos = (local_base[0] + props[0], local_base[1] + props[1], local_base[2])
        by_id[hid].append(abs_pos)
        count += 1

    depth = 1
    while pos < len(data) and depth > 0:
        if data[pos] == NODE_START:
            pos, cm = collect_housetiles(data, pos, local_base, by_id)
            count += cm
        elif data[pos] == NODE_END:
            pos += 1
            depth -= 1
        else:
            pos += 1

    return pos, count


def write_props(buf: bytearray, props: bytes):
    for b in props:
        if b in (NODE_START, NODE_END, ESCAPE_CHAR):
            buf.append(ESCAPE_CHAR)
        buf.append(b)


def strip_housetile_props(node_type: int, props: bytes) -> tuple[int, bytes, bool]:
    """Convierte OTBM_HOUSETILE (RME) a OTBM_TILE (servidor YurOTS)."""
    if node_type != OTBM_HOUSETILE or len(props) < 6:
        return node_type, props, False
    x_off, y_off = props[0], props[1]
    rest = props[2:]
    if len(rest) >= 4:
        rest = rest[4:]
    return OTBM_TILE, bytes([x_off, y_off]) + rest, True


def strip_node(data: bytes, pos: int, area_base: tuple[int, int, int]) -> tuple[bytes, int, int]:
    if pos >= len(data) or data[pos] != NODE_START:
        return b"", pos, 0

    out = bytearray()
    out.append(NODE_START)
    pos += 1
    node_type = data[pos]
    pos += 1
    props, pos = read_props(data, pos)

    local_base = area_base
    stripped = 0
    new_type, new_props, changed = strip_housetile_props(node_type, props)

    if node_type == OTBM_TILE_AREA and len(props) >= 5:
        bx, by, bz = struct.unpack_from("<HHB", props, 0)
        local_base = (bx, by, bz)

    if changed:
        stripped += 1

    out.append(new_type)
    write_props(out, new_props)

    depth = 1
    while pos < len(data) and depth > 0:
        if data[pos] == NODE_START:
            child, pos, sc = strip_node(data, pos, local_base)
            out.extend(child)
            stripped += sc
        elif data[pos] == NODE_END:
            out.append(NODE_END)
            pos += 1
            depth -= 1
        else:
            out.append(data[pos])
            pos += 1

    return bytes(out), pos, stripped


def strip_otbm_for_server(data: bytes) -> tuple[bytes, int]:
    if len(data) < 4:
        raise ValueError("OTBM demasiado corto")
    header, body = data[:4], data[4:]
    if not body or body[0] != NODE_START:
        raise ValueError("OTBM sin nodo raíz")
    patched, end_pos, stripped = strip_node(body, 0, (0, 0, 0))
    if end_pos < len(body):
        patched += body[end_pos:]
    return header + patched, stripped


def housetile_count(data: bytes) -> int:
    return data.count(bytes([NODE_START, OTBM_HOUSETILE]))


def load_rme_house_meta(path: Path) -> dict[int, dict]:
    root = ET.parse(path).getroot()
    meta: dict[int, dict] = {}
    for el in root.findall("house"):
        hid = int(el.get("houseid", 0))
        meta[hid] = {
            "name": el.get("name", f"House #{hid}"),
            "entry": (
                int(el.get("entryx", 0)),
                int(el.get("entryy", 0)),
                int(el.get("entryz", 0)),
            ),
        }
    return meta


def write_houses_xml(path: Path, houses: list[tuple[str, list[tuple[int, int, int]]]], compress_tiles):
    root = ET.Element("houses")
    for name, coords in houses:
        el = ET.SubElement(root, "house", {"name": name})
        for child in compress_tiles(sorted(coords)):
            el.append(child)
    tree = ET.ElementTree(root)
    if hasattr(ET, "indent"):
        ET.indent(tree, space="")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def update_frontdoor(path: Path, entry: tuple[int, int, int], dry_run: bool) -> bool:
    if not path.is_file():
        return False
    root = ET.parse(path).getroot()
    door = root.find("frontdoor")
    if door is None:
        door = ET.SubElement(root, "frontdoor")
    ex, ey, ez = entry
    cur = (int(door.get("x", 0)), int(door.get("y", 0)), int(door.get("z", 0)))
    if cur == (ex, ey, ez):
        return False
    door.set("x", str(ex))
    door.set("y", str(ey))
    door.set("z", str(ez))
    if not dry_run:
        ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    project = Path(__file__).resolve().parents[1]
    mod = load_sync_module(project)

    otbm_path = project / "server/YurOTS/ots/data/world/test.otbm"
    rme_otbm = project / "server/YurOTS/ots/data/world/test-rme.otbm"
    rme_houses = project / "server/YurOTS/ots/data/world/test-house.xml"
    houses_xml = project / "server/YurOTS/ots/data/houses.xml"
    owners_dir = project / "server/YurOTS/ots/data/houses"

    meta = load_rme_house_meta(rme_houses)
    if not meta:
        print("ERROR: test-house.xml vacío — guardá el mapa desde RME primero.", file=sys.stderr)
        return 1

    # Leer mapa RME (con HOUSETILE) antes de convertir para el servidor.
    source = rme_otbm if rme_otbm.is_file() else otbm_path
    raw = source.read_bytes()
    if housetile_count(raw) == 0 and source != otbm_path:
        raw = otbm_path.read_bytes()
        source = otbm_path
    body = raw[4:]
    if not body or body[0] != NODE_START:
        print("ERROR: OTBM inválido", file=sys.stderr)
        return 1

    by_id: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    _, total = collect_housetiles(body, 0, (0, 0, 0), by_id)
    print(f"HOUSETILE en OTBM: {total} tiles, {len(by_id)} house ids")

    houses_out: list[tuple[str, list[tuple[int, int, int]]]] = []
    missing_meta = []
    empty = []
    for hid in sorted(meta):
        coords = by_id.get(hid, [])
        name = meta[hid]["name"]
        if not coords:
            empty.append(name)
            continue
        houses_out.append((name, coords))

    for hid in sorted(by_id):
        if hid not in meta:
            missing_meta.append(hid)

    if missing_meta:
        print(f"AVISO: {len(missing_meta)} house id(s) en OTBM sin test-house.xml (ej. {missing_meta[0]})")
    if empty:
        print(f"AVISO: {len(empty)} casa(s) sin tiles en OTBM: {', '.join(empty[:5])}")

    if not houses_out:
        print("ERROR: ninguna casa con tiles — ¿guardaste casas en RME?", file=sys.stderr)
        return 1

    print(f"Casas a escribir en houses.xml: {len(houses_out)}")

    if args.dry_run:
        print("(dry-run — no se escriben archivos)")
        return 0

    if housetile_count(raw) > 0:
        shutil.copy2(source, rme_otbm)
        print(f"Copia RME: {rme_otbm}")
        server_otbm, stripped = strip_otbm_for_server(raw)
        otbm_path.write_bytes(server_otbm)
        print(f"OK — test.otbm listo para servidor ({stripped} HOUSETILE → TILE)")
    else:
        print("AVISO: OTBM sin HOUSETILE — se asume ya compatible con el servidor")

    backup = houses_xml.with_suffix(".xml.bak")
    if houses_xml.exists() and not backup.exists():
        shutil.copy2(houses_xml, backup)
        print(f"Backup: {backup}")

    write_houses_xml(houses_xml, houses_out, mod.compress_tiles)
    doors_updated = 0
    for hid, info in sorted(meta.items()):
        owner = owners_dir / f"{info['name']}.xml"
        if update_frontdoor(owner, info["entry"], dry_run=False):
            doors_updated += 1

    print(f"OK — houses.xml actualizado ({sum(len(c) for _, c in houses_out)} tiles)")
    if doors_updated:
        print(f"OK — {doors_updated} frontdoor(s) actualizados en data/houses/")

    removed = mod.sync_houses(otbm_path, houses_xml, dry_run=True)
    if removed:
        print(f"ERROR: quedaron {removed} tiles inválidos tras importar", file=sys.stderr)
        return 1
    print("Validación mapa ↔ casas: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
