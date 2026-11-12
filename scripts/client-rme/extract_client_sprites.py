#!/usr/bin/env python3
"""Saca sprites de ítems de un cliente de Tibia más nuevo (formato 7.55-8.60) a PNG de 32x32.

Para traer ítems de otras versiones (ej. la Emerald Sword de 8.x) sin bajar imágenes de wikis:
se lee el Tibia.dat / Tibia.spr de ese cliente y se guarda el primer cuadro de cada ítem.
Los nombres salen del items.otb + items.xml de esa versión (los trae RME en data/<versión>/).

  # buscar por nombre y ver una hoja con los candidatos
  python3 scripts/client-rme/extract_client_sprites.py --client DIR_860 --otb items.otb --xml items.xml \\
      --sheet /tmp/hoja.png "emerald sword" "the avenger" "arcane staff" "arbalest"
  # guardar los PNG donde los lee add_custom_items.py
  python3 scripts/client-rme/extract_client_sprites.py --client DIR_860 --otb items.otb --xml items.xml \\
      --out devtools/zagan-test/custom-sprites "emerald sword" ...

DIR_860 = carpeta con Tibia.dat y Tibia.spr. Solo lee esos dos archivos (nunca ejecuta nada del cliente).
Imprime el client id, el server id y los atributos del items.xml (ataque, defensa, tipo) de cada ítem.
Solo ítems de 1x1 (32x32): los de más casillas se avisan y se saltean.
Doc: docs/items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "map" / "kb"))
from add_black_dragon_look import decode_sprite, read_spr  # noqa: E402
from mapdata import parse_tree, png_bytes  # noqa: E402

# flags del .dat 7.55-8.60 que llevan datos: flag -> cantidad de u16 (como OTClient para esas versiones)
U16_FLAGS = {0: 1, 8: 1, 9: 1, 21: 2, 24: 2, 25: 1, 28: 1, 29: 1}
KEEP_ATTRS = ("attack", "defense", "extradef", "weaponType", "slotType", "range", "hitChance", "ammoType",
              "shootType", "weight", "description", "armor")


def read_dat_items(dat: bytes) -> dict[int, dict]:
    """client id -> {w, h, sprites} de los ítems; valida que el archivo se lea entero."""
    _sig, n_items, n_outfits, n_effects, n_missiles = struct.unpack_from("<IHHHH", dat, 0)
    pos, things = 12, {}
    for k in range((n_items - 99) + n_outfits + n_effects + n_missiles):
        while True:
            flag = dat[pos]
            pos += 1
            if flag == 0xFF:
                break
            pos += 2 * U16_FLAGS.get(flag, 0)
        w, h = dat[pos], dat[pos + 1]
        pos += 2
        if w > 1 or h > 1:
            pos += 1
        layers, px, py, pz, frames = struct.unpack_from("<5B", dat, pos)
        pos += 5
        count = w * h * layers * px * py * pz * frames
        sprites = list(struct.unpack_from(f"<{count}H", dat, pos))
        pos += 2 * count
        if 100 + k <= n_items:
            things[100 + k] = {"w": w, "h": h, "sprites": sprites}
    if pos != len(dat):
        raise SystemExit(f"Tibia.dat con formato inesperado (se leyeron {pos} de {len(dat)} bytes): ¿es 7.55-8.60?")
    return things


def otb_server_to_client(path: Path) -> dict[int, int]:
    root = parse_tree(path.read_bytes())
    out = {}
    for _group, props, _children in root[2]:
        props, pos, sid, cid = bytes(props), 4, None, None
        while pos + 3 <= len(props):
            attr, size = props[pos], struct.unpack_from("<H", props, pos + 1)[0]
            payload = props[pos + 3:pos + 3 + size]
            if attr == 0x10:
                sid = struct.unpack("<H", payload)[0]
            elif attr == 0x11:
                cid = struct.unpack("<H", payload)[0]
            pos += 3 + size
        if sid is not None and cid is not None:
            out[sid] = cid
    return out


def xml_items(path: Path) -> dict[str, tuple[int, dict]]:
    """nombre en minúsculas -> (server id, atributos)."""
    text = path.read_text(encoding="latin-1")
    out = {}
    for m in re.finditer(r'<item\s+id="(\d+)"[^>]*?name="([^"]*)"[^>]*?(/>|>(.*?)</item>)', text, re.S):
        attrs = dict(re.findall(r'<attribute\s+key="([^"]+)"\s+value="([^"]*)"', m.group(4) or ""))
        out.setdefault(m.group(2).lower(), (int(m.group(1)), attrs))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", type=Path, required=True, help="carpeta con Tibia.dat y Tibia.spr del cliente nuevo")
    ap.add_argument("--otb", type=Path, required=True, help="items.otb de esa versión")
    ap.add_argument("--xml", type=Path, required=True, help="items.xml de esa versión")
    ap.add_argument("--out", type=Path, help="carpeta donde guardar <nombre>.png")
    ap.add_argument("--sheet", type=Path, help="hoja PNG con todos los pedidos, x4")
    ap.add_argument("names", nargs="+", help="nombres de ítems como en el items.xml (ej. 'the avenger')")
    a = ap.parse_args()

    things = read_dat_items((a.client / "Tibia.dat").read_bytes())
    spr = (a.client / "Tibia.spr").read_bytes()
    _count, offsets = read_spr(spr)
    s2c, items = otb_server_to_client(a.otb), xml_items(a.xml)

    found = []
    for name in a.names:
        if name.lower() not in items:
            print(f"  ?? {name}: no está en el items.xml")
            continue
        sid, attrs = items[name.lower()]
        cid = s2c.get(sid)
        thing = things.get(cid)
        if thing is None:
            print(f"  ?? {name}: server {sid} sin client id en el items.otb")
            continue
        if thing["w"] != 1 or thing["h"] != 1:
            print(f"  -- {name}: ocupa {thing['w']}x{thing['h']} casillas; solo se importan ítems de 1x1")
            continue
        pixels = decode_sprite(spr, offsets, thing["sprites"][0])
        found.append((name, pixels))
        keep = {k: v for k, v in attrs.items() if k in KEEP_ATTRS}
        print(f"  {name}: server {sid}, client {cid} -> {keep}")
        if a.out:
            a.out.mkdir(parents=True, exist_ok=True)
            rgba = b"".join(bytes(p) if p[3] else b"\0\0\0\0" for p in pixels)
            path = a.out / (name.lower().replace(" ", "_").replace("'", "") + ".png")
            path.write_bytes(png_bytes(32, 32, rgba))
            print(f"     -> {path}")
    if a.sheet and found:
        cols = min(8, len(found))
        rows = (len(found) + cols - 1) // cols
        w, h = cols * 40 + 8, rows * 40 + 8
        img = bytearray(bytes((40, 44, 52, 255)) * (w * h))
        for k, (_name, pixels) in enumerate(found):
            ox, oy = 8 + (k % cols) * 40, 8 + (k // cols) * 40
            for i, p in enumerate(pixels):
                if p[3]:
                    o = ((oy + i // 32) * w + ox + i % 32) * 4
                    img[o:o + 4] = bytes((p[0], p[1], p[2], 255))
        a.sheet.write_bytes(png_bytes(w, h, bytes(img), scale=4))
        print(f"hoja: {a.sheet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
