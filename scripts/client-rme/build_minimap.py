#!/usr/bin/env python3
"""Arma el minimapa COMPLETO del cliente (data/minimap.otmm) desde el test.otbm del servidor.

El cliente (game_minimap/minimap.lua) carga primero `/data/minimap.otmm` si existe, antes que el
minimapa que cada jugador va descubriendo (`minimap760.otmm` en su carpeta). Con este archivo en el
cliente el mapa se ve entero desde el principio, todos los pisos.

Formato (leído de un minimap760.otmm que guardó el propio cliente, nov 2026):
  cabecera: u32 'OTMM', u16 inicio de los datos (22), u16 versión (1), u32 flags (0), string "OTMM 1.0"
  bloques:  u16 x, u16 y, u8 z (esquina del bloque de 64x64), u16 largo, datos con zlib
            (64*64 casillas de 3 bytes: marcas, color, velocidad; casilla = (y%64)*64 + x%64)
  fin:      u16 0xFFFF, u16 0xFFFF, u8 0xFF
  marcas:   1 vista, 2 no se puede pasar por el pathfinding, 4 no caminable. Sin ver: 0 / 255 / 10.

El color de una casilla es el último color de minimapa (atributo 0x1C del .dat) entre su suelo,
bordes, ítems de abajo y de arriba, como `Tile::getMinimapColorByte` del cliente.

Uso:
  python3 scripts/client-rme/build_minimap.py                    # escribe <tmp>/retro76-minimap.otmm
  python3 scripts/client-rme/build_minimap.py --out ruta.otmm
  python3 scripts/client-rme/build_minimap.py --compare minimap760.otmm   # contra lo que vio un cliente
Doc: docs/CLIENT.md (minimapa completo).
"""
from __future__ import annotations

import argparse
import math
import struct
import sys
import tempfile
import zlib
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "map" / "kb"))
import mapdata  # noqa: E402

BLOCK = 64
SEEN, NOT_PATHABLE, NOT_WALKABLE = 1, 2, 4
PRIORITY = {0x00: 0, 0x01: 1, 0x02: 2, 0x03: 3}      # suelo, borde, abajo, arriba (el resto corta)


def tile_bytes(items: list[int], otb: dict, dat: dict) -> tuple[int, int, int]:
    things = []
    for order, sid in enumerate(items):
        cid = otb.get(sid, {}).get("cid")
        e = dat.get(cid) if cid else None
        if not e:
            continue
        fl = e["flags"]
        prio = next((p for f, p in PRIORITY.items() if f in fl), 5)
        things.append((prio, order, fl))
    things.sort(key=lambda t: (t[0], t[1]))
    # sin suelo el cliente cuenta velocidad 100 (Tile::getGroundSpeed)
    color, ground_speed, has_ground, walkable, pathable = 255, 100, False, True, True
    for prio, _o, fl in things:
        if 0x00 in fl:
            has_ground = True
            ground_speed = struct.unpack("<H", fl[0x00])[0]
        if 0x0C in fl:
            walkable = False
        if 0x0F in fl:
            pathable = False
    for prio, _o, fl in things:
        if prio > 3:
            break
        if 0x1C in fl:
            c = struct.unpack("<H", fl[0x1C])[0]
            if c:
                color = c & 0xFF
    flags = SEEN
    if not has_ground or not walkable:
        flags |= NOT_WALKABLE
    if not pathable:
        flags |= NOT_PATHABLE
    speed = min(int(math.ceil(ground_speed / 10.0)), 255)
    return flags, color, speed


def build(tiles: dict) -> dict:
    otb, dat = mapdata.load_otb(), mapdata.parse_dat()
    blocks: dict = defaultdict(lambda: bytearray(b"\x00\xff\x0a" * (BLOCK * BLOCK)))
    for (x, y, z), items in tiles.items():
        b = blocks[(x - x % BLOCK, y - y % BLOCK, z)]
        i = ((y % BLOCK) * BLOCK + x % BLOCK) * 3
        b[i:i + 3] = bytes(tile_bytes(items, otb, dat))
    return blocks


def write(blocks: dict, path: Path) -> None:
    desc = b"OTMM 1.0"
    out = bytearray(struct.pack("<IHHI", 0x4D4D544F, 0, 1, 0) + struct.pack("<H", len(desc)) + desc)
    struct.pack_into("<H", out, 4, len(out))
    for (x, y, z) in sorted(blocks, key=lambda k: (k[2], k[1], k[0])):
        data = zlib.compress(bytes(blocks[(x, y, z)]), 9)
        out += struct.pack("<HHBH", x, y, z, len(data)) + data
    out += struct.pack("<HHB", 0xFFFF, 0xFFFF, 0xFF)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))


def read(path: Path) -> dict:
    d = path.read_bytes()
    sig, start = struct.unpack_from("<IH", d, 0)
    assert sig == 0x4D4D544F, "no es un .otmm"
    blocks, p = {}, start
    while True:
        x, y, z = struct.unpack_from("<HHB", d, p)
        p += 5
        if (x, y, z) == (0xFFFF, 0xFFFF, 0xFF):
            return blocks
        n = struct.unpack_from("<H", d, p)[0]
        blocks[(x, y, z)] = zlib.decompress(d[p + 2:p + 2 + n])
        p += 2 + n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path(tempfile.gettempdir()) / "retro76-minimap.otmm")
    ap.add_argument("--compare", type=Path, help="minimapa guardado por un cliente: cuántas casillas vistas coinciden")
    a = ap.parse_args()
    tiles = mapdata.load_tiles()
    blocks = build(tiles)
    write(blocks, a.out)
    print(f"{a.out}: {len(tiles)} casillas, {len(blocks)} bloques, {a.out.stat().st_size // 1024} KB")
    if a.compare:
        seen = same = same_color = 0
        diffs: dict = defaultdict(int)
        for k, raw in read(a.compare).items():
            mine = blocks.get(k)
            for i in range(0, len(raw), 3):
                if not raw[i] & SEEN:
                    continue
                seen += 1
                got = bytes(mine[i:i + 3]) if mine else b"\x00\xff\x0a"
                if got == raw[i:i + 3]:
                    same += 1
                if got[1] == raw[i + 1]:
                    same_color += 1
                else:
                    diffs[(raw[i + 1], got[1])] += 1
        print(f"comparado con {a.compare.name}: {seen} casillas vistas, iguales {same} "
              f"({100 * same / max(seen, 1):.1f} %), mismo color {same_color} ({100 * same_color / max(seen, 1):.1f} %)")
        for (theirs, mine), n in sorted(diffs.items(), key=lambda kv: -kv[1])[:8]:
            print(f"   color cliente {theirs} / generado {mine}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
