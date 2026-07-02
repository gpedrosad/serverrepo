#!/usr/bin/env python3
"""Valida data/houses.xml contra tiles presentes en test.otbm."""
from __future__ import annotations

import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NODE_START = 0xFE
NODE_END = 0xFF
ESCAPE_CHAR = 0xFD

OTBM_TILE_AREA = 4
OTBM_TILE = 5


class PropStream:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def remaining(self) -> int:
        return len(self.data) - self.pos

    def get_struct(self, fmt: str):
        size = struct.calcsize(fmt)
        if self.remaining() < size:
            return None
        val = struct.unpack_from(fmt, self.data, self.pos)[0]
        self.pos += size
        return val

    def get_ushort(self) -> int | None:
        return self.get_struct("<H")

    def get_uchar(self) -> int | None:
        return self.get_struct("<B")

    def get_ulong(self) -> int | None:
        return self.get_struct("<I")

    def get_string(self) -> str | None:
        ln = self.get_ushort()
        if ln is None or self.remaining() < ln:
            return None
        s = self.data[self.pos : self.pos + ln].decode("latin-1", errors="replace")
        self.pos += ln
        return s

    def skip_rest(self):
        self.pos = len(self.data)


class OTBMReader:
    def __init__(self, path: Path):
        self.raw = path.read_bytes()
        if len(self.raw) < 4:
            raise ValueError("archivo demasiado corto")
        version = struct.unpack_from("<I", self.raw, 0)[0]
        if version != 0:
            raise ValueError(f"version OTBM no soportada: {version}")
        self.pos = 4

    def read_byte(self) -> int | None:
        if self.pos >= len(self.raw):
            return None
        b = self.raw[self.pos]
        self.pos += 1
        return b

    def tell(self) -> int:
        return self.pos

    def seek(self, pos: int):
        self.pos = pos

    def get_props(self, node_pos: int) -> bytes | None:
        self.seek(node_pos)
        if self.read_byte() != NODE_START:
            return None
        self.read_byte()  # node type
        out = bytearray()
        while True:
            b = self.read_byte()
            if b is None:
                return None
            if b in (NODE_END, NODE_START):
                break
            if b == ESCAPE_CHAR:
                b = self.read_byte()
                if b is None:
                    return None
            out.append(b)
        return bytes(out)

    def get_child_node(self, parent: int | None):
        if parent is None:
            self.seek(4)
        else:
            self.seek(parent)
        node_pos = self.tell()
        if self.read_byte() != NODE_START:
            return None, None
        node_type = self.read_byte()
        if parent is None:
            return node_pos, node_type
        while True:
            b = self.read_byte()
            if b is None:
                return None, None
            if b == NODE_END:
                return None, None
            if b == NODE_START:
                child_pos = self.tell() - 1
                child_type = self.read_byte()
                return child_pos, child_type
            if b == ESCAPE_CHAR:
                self.read_byte()

    def get_next_node(self, prev: int):
        self.seek(prev)
        if self.read_byte() != NODE_START:
            return None, None
        self.read_byte()  # type
        level = 1
        while True:
            b = self.read_byte()
            if b is None:
                return None, None
            if b == NODE_END:
                level -= 1
                if level == 0:
                    b = self.read_byte()
                    if b is None:
                        return None, None
                    if b == NODE_END:
                        return None, None
                    if b != NODE_START:
                        return None, None
                    node_pos = self.tell() - 1
                    node_type = self.read_byte()
                    return node_pos, node_type
            elif b == NODE_START:
                level += 1
            elif b == ESCAPE_CHAR:
                self.read_byte()


def load_map_tiles(otbm_path: Path) -> set[tuple[int, int, int]]:
    reader = OTBMReader(otbm_path)
    tiles: set[tuple[int, int, int]] = set()

    root, _ = reader.get_child_node(None)
    if root is None:
        raise ValueError("sin nodo raiz")

    props = reader.get_props(root)
    if not props:
        raise ValueError("sin props raiz")

    map_data, map_data_type = reader.get_child_node(root)
    if map_data is None:
        raise ValueError("sin nodo map_data")

    area, area_type = reader.get_child_node(map_data)
    while area is not None:
        if area_type == OTBM_TILE_AREA:
            props = reader.get_props(area)
            if props:
                ps = PropStream(props)
                base_x = ps.get_ushort()
                base_y = ps.get_ushort()
                base_z = ps.get_uchar()
                if None not in (base_x, base_y, base_z):
                    tile_node, tile_type = reader.get_child_node(area)
                    while tile_node is not None:
                        if tile_type == OTBM_TILE:
                            tprops = reader.get_props(tile_node)
                            if tprops:
                                tps = PropStream(tprops)
                                ox = tps.get_uchar()
                                oy = tps.get_uchar()
                                if ox is not None and oy is not None:
                                    tiles.add((base_x + ox, base_y + oy, base_z))
                        tile_node, tile_type = reader.get_next_node(tile_node)
        area, area_type = reader.get_next_node(area)

    return tiles


def iter_house_tiles(house_el: ET.Element):
    for child in house_el:
        if child.tag == "tile":
            yield (
                int(child.get("x", 0)),
                int(child.get("y", 0)),
                int(child.get("z", 0)),
            )
        elif child.tag == "tiles":
            fx = int(child.get("fromx", 0))
            fy = int(child.get("fromy", 0))
            fz = int(child.get("fromz", 0))
            tx = int(child.get("tox", 0))
            ty = int(child.get("toy", 0))
            tz = int(child.get("toz", 0))
            if fx > tx:
                fx, tx = tx, fx
            if fy > ty:
                fy, ty = ty, fy
            if fz > tz:
                fz, tz = tz, fz
            for x in range(fx, tx + 1):
                for y in range(fy, ty + 1):
                    for z in range(fz, tz + 1):
                        yield (x, y, z)


def compress_tiles(coords: list[tuple[int, int, int]]) -> list[ET.Element]:
    if not coords:
        return []
    by_z: dict[int, set[tuple[int, int]]] = {}
    for x, y, z in coords:
        by_z.setdefault(z, set()).add((x, y))

    elements: list[ET.Element] = []
    for z in sorted(by_z):
        pts = sorted(by_z[z])
        i = 0
        while i < len(pts):
            x0, y0 = pts[i]
            x1, y1 = x0, y0
            j = i + 1
            while j < len(pts):
                x, y = pts[j]
                if y == y1 and x == x1 + 1:
                    x1 = x
                    j += 1
                else:
                    break
            if x0 == x1 and y0 == y1:
                el = ET.Element("tile")
                el.set("x", str(x0))
                el.set("y", str(y0))
                el.set("z", str(z))
            else:
                el = ET.Element("tiles")
                el.set("fromx", str(x0))
                el.set("fromy", str(y0))
                el.set("fromz", str(z))
                el.set("tox", str(x1))
                el.set("toy", str(y1))
                el.set("toz", str(z))
            elements.append(el)
            i = j
    return elements


def sync_houses(otbm_path: Path, houses_path: Path, dry_run: bool = False) -> int:
    tiles = load_map_tiles(otbm_path)
    tree = ET.parse(houses_path)
    root = tree.getroot()
    removed = 0
    changed_houses = 0

    for house in root.findall("house"):
        name = house.get("name", "?")
        valid = [c for c in iter_house_tiles(house) if c in tiles]
        invalid = [c for c in iter_house_tiles(house) if c not in tiles]
        if not invalid:
            continue
        changed_houses += 1
        removed += len(invalid)
        print(f"  {name}: quitar {len(invalid)} tile(s) invalidos (ej. {invalid[0]})")
        for child in list(house):
            if child.tag in ("tile", "tiles"):
                house.remove(child)
        for el in compress_tiles(valid):
            house.append(el)

    if changed_houses and not dry_run:
        tree.write(houses_path, encoding="utf-8", xml_declaration=True)
    return removed


def main():
    project = Path(__file__).resolve().parents[1]
    otbm = project / "server/YurOTS/ots/data/world/test.otbm"
    houses = project / "server/YurOTS/ots/data/houses.xml"
    dry_run = "--dry-run" in sys.argv

    print(f"Mapa: {otbm}")
    tiles = load_map_tiles(otbm)
    print(f"Tiles en mapa: {len(tiles)}")
    print(f"Casas: {houses}")
    if dry_run:
        print("(dry-run)")
    removed = sync_houses(otbm, houses, dry_run=dry_run)
    if removed:
        print(f"Total tiles invalidos: {removed}")
        if not dry_run:
            print("houses.xml actualizado.")
        elif dry_run:
            sys.exit(1)
    else:
        print("houses.xml ya coincide con el mapa.")


if __name__ == "__main__":
    main()
