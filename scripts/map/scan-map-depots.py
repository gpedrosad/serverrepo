#!/usr/bin/env python3
"""Lista depot lockers (items 2589-2592) en un OTBM con posición y depotid."""
from __future__ import annotations

import struct
import sys
from collections import Counter
from pathlib import Path

NODE_START = 0xFE
NODE_END = 0xFF
ESCAPE_CHAR = 0xFD

OTBM_TILE_AREA = 4
OTBM_TILE = 5
OTBM_ITEM = 6

OTBM_ATTR_TILE_FLAGS = 3
OTBM_ATTR_ITEM = 9
OTBM_ATTR_DEPOT_ID = 10

LOCKER_IDS = {2589, 2590, 2591, 2592}


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
        self.read_byte()
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
        self.read_byte()
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


def parse_item_attrs(ps: PropStream, item_id: int) -> int | None:
  depot_id = None
  while ps.remaining():
    attr = ps.get_uchar()
    if attr is None:
      break
    if attr == OTBM_ATTR_DEPOT_ID:
      depot_id = ps.get_ushort()
    elif attr == OTBM_ATTR_TILE_FLAGS:
      ps.get_ulong()
    elif attr in (1, 2):
      ps.get_string()
    elif attr in (4, 5, 12):
      ps.get_ushort()
    elif attr in (6, 7):
      ps.get_string()
    elif attr == 8:
      ps.get_struct("<HHB")
    elif attr == OTBM_ATTR_ITEM:
      sub = ps.get_ushort()
      if sub is not None:
        ps.get_uchar()
      break
    else:
      break
  if item_id in LOCKER_IDS:
    return depot_id
  return None


def parse_item_node(reader: OTBMReader, node: int) -> tuple[int, int | None] | None:
  props = reader.get_props(node)
  if not props:
    return None
  ps = PropStream(props)
  item_id = ps.get_ushort()
  if item_id is None:
    return None
  ps.get_uchar()  # count/subtype for stackables; harmless for lockers
  depot_id = None
  while ps.remaining():
    attr = ps.get_uchar()
    if attr is None:
      break
    if attr == OTBM_ATTR_DEPOT_ID:
      depot_id = ps.get_ushort()
    elif attr in (4, 5, 12):
      ps.get_ushort()
    elif attr in (6, 7):
      ps.get_string()
    elif attr == 8:
      ps.get_struct("<HHB")
    else:
      break
  return item_id, depot_id


def scan_depots(otbm_path: Path) -> list[dict]:
  reader = OTBMReader(otbm_path)
  found: list[dict] = []

  root, _ = reader.get_child_node(None)
  if root is None:
    raise ValueError("sin nodo raiz")
  map_data, _ = reader.get_child_node(root)
  if map_data is None:
    raise ValueError("sin map_data")

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
                  x, y, z = base_x + ox, base_y + oy, base_z
                  while tps.remaining():
                    attr = tps.get_uchar()
                    if attr is None:
                      break
                    if attr == OTBM_ATTR_ITEM:
                      iid = tps.get_ushort()
                      tps.get_uchar()
                      if iid in LOCKER_IDS:
                        found.append({"x": x, "y": y, "z": z, "item": iid, "depotid": None})
                    elif attr == OTBM_ATTR_TILE_FLAGS:
                      tps.get_ulong()
                    else:
                      break
                  item_node, item_type = reader.get_child_node(tile_node)
                  while item_node is not None:
                    if item_type == OTBM_ITEM:
                      parsed = parse_item_node(reader, item_node)
                      if parsed:
                        iid, depot_id = parsed
                        if iid in LOCKER_IDS:
                          found.append({"x": x, "y": y, "z": z, "item": iid, "depotid": depot_id})
                    item_node, item_type = reader.get_next_node(item_node)
            tile_node, tile_type = reader.get_next_node(tile_node)
    area, area_type = reader.get_next_node(area)
  return found


def main():
  if len(sys.argv) < 2:
    print(f"Uso: {sys.argv[0]} <map.otbm> [map2.otbm]", file=sys.stderr)
    sys.exit(1)

  for path in sys.argv[1:]:
    p = Path(path)
    depots = scan_depots(p)
    ids = Counter(d["depotid"] for d in depots)
    print(f"\n{p.name}: {len(depots)} lockers")
    print("  depotids:", dict(sorted(ids.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))))
    for d in sorted(depots, key=lambda r: (r["z"], r["y"], r["x"])):
      print(f"  ({d['x']},{d['y']},{d['z']}) item={d['item']} depotid={d['depotid']}")

  if len(sys.argv) == 3:
    a = {(d["x"], d["y"], d["z"]): d for d in scan_depots(Path(sys.argv[1]))}
    b = {(d["x"], d["y"], d["z"]): d for d in scan_depots(Path(sys.argv[2]))}
    only_a = set(a) - set(b)
  only_b = set(b) - set(a)
  changed = [pos for pos in set(a) & set(b) if a[pos]["depotid"] != b[pos]["depotid"]]
  print("\n--- diff ---")
  print(f"solo en {Path(sys.argv[1]).name}: {len(only_a)}")
  for pos in sorted(only_a)[:20]:
    print(f"  {pos} -> {a[pos]}")
  print(f"solo en {Path(sys.argv[2]).name}: {len(only_b)}")
  for pos in sorted(only_b)[:20]:
    print(f"  {pos} -> {b[pos]}")
  print(f"mismo tile, distinto depotid: {len(changed)}")
  for pos in sorted(changed)[:20]:
    print(f"  {pos}: {a[pos]['depotid']} -> {b[pos]['depotid']}")


if __name__ == "__main__":
  main()
