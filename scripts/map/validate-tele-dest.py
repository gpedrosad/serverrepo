#!/usr/bin/env python3
"""Valida que items con TELE_DEST sean teleport 1387.

Uso: python3 validate-tele-dest.py <file.otbm>

Detecta el caso específico donde un item non-teleport tiene OTBM_ATTR_TELE_DEST,
lo que causa que iomapotbm.cpp:371 haga delete item; return NULL;
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

NODE_START = 0xFE
NODE_END = 0xFF
ESCAPE_CHAR = 0xFD

OTBM_TILE_AREA = 4
OTBM_TILE = 5
OTBM_ITEM = 6
OTBM_ATTR_TELE_DEST = 8

TELEPORT_ITEM_ID = 1387


def read_props(data: bytes, pos: int) -> tuple[bytes, int]:
    """Decode OTBM escaped props."""
    out = bytearray()
    while pos < len(data):
        b = data[pos]
        pos += 1
        if b in (NODE_START, NODE_END):
            pos -= 1
            break
        if b == ESCAPE_CHAR:
            if pos >= len(data):
                raise ValueError("truncated escape")
            out.append(data[pos])
            pos += 1
        else:
            out.append(b)
    return bytes(out), pos


def skip_node(data: bytes, pos: int) -> int:
    """Skip a full OTBM node including children."""
    if pos >= len(data) or data[pos] != NODE_START:
        return pos
    pos += 1  # NODE_START
    if pos < len(data):
        pos += 1  # type
    _, pos = read_props(data, pos)
    depth = 1
    while pos < len(data) and depth > 0:
        if data[pos] == NODE_START:
            depth += 1
        elif data[pos] == NODE_END:
            depth -= 1
        pos += 1
    return pos


def check_item_node(data: bytes, pos: int, tile_x: int, tile_y: int, tile_z: int) -> tuple[int, list[str]]:
    """Check a single OTBM_ITEM node for TELE_DEST on non-teleport."""
    if pos >= len(data) or data[pos] != NODE_START:
        return pos, []
    start_pos = pos
    pos += 1
    
    if pos >= len(data):
        return pos, []
    node_type = data[pos]
    pos += 1
    
    if node_type != OTBM_ITEM:
        return skip_node(data, start_pos), []
    
    props, pos = read_props(data, pos)
    
    if len(props) < 2:
        return skip_node(data, start_pos), []
    
    item_id = struct.unpack("<H", props[:2])[0]
    
    # Scan props for TELE_DEST
    has_tele_dest = False
    attr_pos = 2
    while attr_pos < len(props):
        attr_type = props[attr_pos]
        attr_pos += 1
        
        if attr_type == OTBM_ATTR_TELE_DEST:
            has_tele_dest = True
            if attr_pos + 4 < len(props):
                dest_x, dest_y, dest_z = struct.unpack("<HHB", props[attr_pos:attr_pos+5])
                if item_id != TELEPORT_ITEM_ID:
                    errors = [
                        f"ERROR: Item {item_id} at tile ({tile_x},{tile_y},{tile_z}) "
                        f"has TELE_DEST (→{dest_x},{dest_y},{dest_z}) but is NOT teleport {TELEPORT_ITEM_ID}. "
                        f"This will cause iomapotbm.cpp:371 to return NULL."
                    ]
                    return skip_node(data, start_pos), errors
            break
        
        # Skip other attributes (simplified)
        if attr_type in (4, 5):  # ACTION_ID, UNIQUE_ID
            attr_pos += 2
        elif attr_type in (6, 7):  # TEXT, DESC
            if attr_pos + 1 < len(props):
                slen = struct.unpack("<H", props[attr_pos:attr_pos+2])[0]
                attr_pos += 2 + slen
            else:
                break
        elif attr_type == 10:  # DEPOT_ID
            attr_pos += 2
        elif attr_type == 12:  # RUNE_CHARGES
            attr_pos += 1
        else:
            # Unknown, stop scanning
            break
    
    # Check children
    errors = []
    while pos < len(data) and data[pos] == NODE_START:
        child_pos, child_errs = check_item_node(data, pos, tile_x, tile_y, tile_z)
        errors.extend(child_errs)
        pos = child_pos
    
    if pos < len(data) and data[pos] == NODE_END:
        pos += 1
    
    return pos, errors


def check_tile_node(data: bytes, pos: int, area_x: int, area_y: int, area_z: int) -> tuple[int, list[str]]:
    """Check a single OTBM_TILE node."""
    if pos >= len(data) or data[pos] != NODE_START:
        return pos, []
    start_pos = pos
    pos += 1
    
    if pos >= len(data):
        return pos, []
    node_type = data[pos]
    pos += 1
    
    if node_type != OTBM_TILE:
        return skip_node(data, start_pos), []
    
    props, pos = read_props(data, pos)
    if len(props) < 2:
        return skip_node(data, start_pos), []
    
    tile_x = area_x + props[0]
    tile_y = area_y + props[1]
    tile_z = area_z
    
    errors = []
    
    # Check item children
    while pos < len(data) and data[pos] == NODE_START:
        child_pos, child_errs = check_item_node(data, pos, tile_x, tile_y, tile_z)
        errors.extend(child_errs)
        pos = child_pos
    
    if pos < len(data) and data[pos] == NODE_END:
        pos += 1
    
    return pos, errors


def check_tile_area(data: bytes, pos: int) -> tuple[int, list[str]]:
    """Check a single OTBM_TILE_AREA node."""
    if pos >= len(data) or data[pos] != NODE_START:
        return pos, []
    start_pos = pos
    pos += 1
    
    if pos >= len(data):
        return pos, []
    node_type = data[pos]
    pos += 1
    
    if node_type != OTBM_TILE_AREA:
        return skip_node(data, start_pos), []
    
    props, pos = read_props(data, pos)
    if len(props) < 5:
        return skip_node(data, start_pos), []
    
    area_x, area_y, area_z = struct.unpack("<HHB", props[:5])
    
    errors = []
    
    while pos < len(data) and data[pos] == NODE_START:
        child_pos, child_errs = check_tile_node(data, pos, area_x, area_y, area_z)
        errors.extend(child_errs)
        pos = child_pos
    
    if pos < len(data) and data[pos] == NODE_END:
        pos += 1
    
    return pos, errors


def validate_otbm(path: Path) -> list[str]:
    """Validate OTBM for teleport attribute issues."""
    raw = path.read_bytes()
    if len(raw) < 4:
        return ["ERROR: file too short"]
    
    body = raw[4:]
    pos = 0
    
    # Skip root node
    if pos >= len(body) or body[pos] != NODE_START:
        return ["ERROR: no root node"]
    pos += 1
    pos += 1  # type
    _, pos = read_props(body, pos)
    
    # MAP_DATA
    if pos >= len(body) or body[pos] != NODE_START:
        return ["ERROR: no map_data"]
    pos += 1
    map_data_type = body[pos]
    pos += 1
    if map_data_type != 2:
        return [f"ERROR: expected MAP_DATA type 2, got {map_data_type}"]
    _, pos = read_props(body, pos)
    
    errors = []
    
    # Check all tile areas
    while pos < len(body) and body[pos] == NODE_START:
        pos, area_errs = check_tile_area(body, pos)
        errors.extend(area_errs)
    
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: validate-tele-dest.py <map.otbm>", file=sys.stderr)
        return 1
    
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"ERROR: {path} no existe", file=sys.stderr)
        return 1
    
    print(f"Validando {path}...")
    errors = validate_otbm(path)
    
    if errors:
        print(f"\n✗ ENCONTRADOS {len(errors)} ERRORES:\n")
        for err in errors:
            print(err)
        print("\nEste mapa FALLARÁ al cargar con 'couldnt determine the map format! exiting2'")
        return 1
    else:
        print("✓ OK: no se encontraron items con TELE_DEST incorrectos")
        return 0


if __name__ == "__main__":
    sys.exit(main())
