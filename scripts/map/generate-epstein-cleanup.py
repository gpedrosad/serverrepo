#!/usr/bin/env python3
"""Limpia Epstein Island: saca los NPCs, el Oracle y la tienda de Sally, y deja un portal de salida.

- Borra la tienda de Sally (x71-79, y217-223, z7): paredes, puertas, mesas, pizarras y piso de
  madera; el piso vuelve a pasto.
- Saca de `world/npc.xml` a Nimral (85,210,7), The Oracle (donde esté) y Sally (74,220,7).
- No reemplaza el Oracle: si se saca, los jugadores sin vocación no pueden elegir vocación.
- Agrega un portal en la llegada del barco (85,210,7) que lleva al templo (130,53,6).

Uso:
  python3 scripts/map/generate-epstein-cleanup.py --dry-run
  python3 scripts/map/generate-epstein-cleanup.py
"""
from __future__ import annotations

import argparse
import re
import shutil
import struct
import sys
from datetime import datetime
from pathlib import Path

REPO = Path("/Users/gonzalo/proyectos/serverrepo")
DATA = REPO / "server/YurOTS/ots/data"
MAP = DATA / "world/test.otbm"
NPCS = DATA / "world/npc.xml"
READABLES = DATA / "readables.xml"
OTB = DATA / "items/items-zagan-test.otb"

T_AREA, T_TILE, T_ITEM = 4, 5, 6
SHOP_BOX = (71, 217, 79, 223, 7)
PORTAL = (85, 210, 7)
TEMPLE = (130, 53, 6)
GRASS = 4756
PORTAL_ID = 1387


def parse_tree(data: bytes):
    pos = 4
    assert data[pos] == 0xFE
    root = [data[pos + 1], bytearray(), []]
    pos += 2
    stack = [root]
    while pos < len(data) and stack:
        b = data[pos]
        if b == 0xFD:
            stack[-1][1].append(data[pos + 1]); pos += 2
        elif b == 0xFE:
            node = [data[pos + 1], bytearray(), []]
            stack[-1][2].append(node); stack.append(node); pos += 2
        elif b == 0xFF:
            stack.pop(); pos += 1
        else:
            stack[-1][1].append(b); pos += 1
    return root


def serialize_tree(root, header: bytes) -> bytes:
    out = bytearray(header)

    def esc(b):
        for v in b:
            if v in (0xFE, 0xFF, 0xFD):
                out.append(0xFD)
            out.append(v)

    stack = [(root, 0)]
    while stack:
        node, i = stack.pop()
        if i == 0:
            out.append(0xFE); out.append(node[0]); esc(node[1])
        if i < len(node[2]):
            stack.append((node, i + 1)); stack.append((node[2][i], 0))
        else:
            out.append(0xFF)
    return bytes(out)


def load_otb():
    root = parse_tree(OTB.read_bytes())
    out = {}
    for group, props, _ in root[2]:
        props = bytes(props)
        if len(props) < 4:
            continue
        flags = struct.unpack_from("<I", props, 0)[0]
        pos, sid = 4, None
        while pos + 3 <= len(props):
            attr = props[pos]
            size = struct.unpack_from("<H", props, pos + 1)[0]
            payload = props[pos + 3:pos + 3 + size]
            if attr == 0x10 and len(payload) >= 2:
                sid = struct.unpack("<H", payload)[0]
            pos += 3 + size
        if sid is not None:
            out[sid] = (group, flags)
    return out


def needs_count(sid, otb):
    group, flags = otb.get(sid, (0, 0))
    return bool(flags & (1 << 7)) or group in (11, 12)


def parse_tile(p: bytes):
    xoff, yoff = p[0], p[1]
    pos = 2
    flags = None
    inline = []
    while pos < len(p):
        a = p[pos]; pos += 1
        if a == 3:
            flags = struct.unpack_from("<I", p, pos)[0]; pos += 4
        elif a == 9:
            start = pos
            sid = struct.unpack_from("<H", p, pos)[0]; pos += 2
            if needs_count(sid, OTB):
                pos += 1
            inline.append(bytes(p[start:pos]))
        else:
            break
    return xoff, yoff, flags, inline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    global OTB
    OTB = load_otb()
    raw = MAP.read_bytes()
    root = parse_tree(raw)

    shop = 0
    portal_done = False
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        for tile in area[2]:
            if tile[0] != T_TILE:
                continue
            p = bytes(tile[1])
            x, y = ax + p[0], ay + p[1]
            pos = (x, y, az)
            if pos == PORTAL:
                # portal 1387 con destino al templo
                exists = any(c[0] == T_ITEM and len(c[1]) >= 2
                             and struct.unpack_from("<H", bytes(c[1]), 0)[0] == PORTAL_ID
                             for c in tile[2])
                if not exists:
                    props = struct.pack("<H", PORTAL_ID) + struct.pack("<BHHB", 8, *TEMPLE)
                    tile[2].append([T_ITEM, bytearray(props), []])
                portal_done = True
                continue
            if not (SHOP_BOX[0] <= x <= SHOP_BOX[2] and SHOP_BOX[1] <= y <= SHOP_BOX[3] and az == SHOP_BOX[4]):
                continue
            xoff, yoff, flags, inline = parse_tile(p)
            if not inline:
                raise SystemExit(f"tienda {pos} sin suelo inline")
            ground = struct.unpack_from("<H", inline[0])[0]
            gname = (OTB.get(ground) or (0, 0))
            # wooden floor/roof -> pasto; el resto del terreno se conserva
            if ground in (3139, 405):
                new_inline = [struct.pack("<H", GRASS)]
            else:
                new_inline = [inline[0]]
            newp = bytearray([xoff, yoff])
            if flags is not None:
                newp += bytes([3]) + struct.pack("<I", flags)
            for ib in new_inline:
                newp += bytes([9]) + ib
            tile[1] = newp
            tile[2] = []
            shop += 1

    if not portal_done:
        raise SystemExit("no encontré la casilla del portal (85,210,7)")
    print(f"tienda: {shop} tiles limpiados; portal en {PORTAL}")

    # npc.xml: sacar Nimral de Epstein, cualquier The Oracle y Sally; sin reemplazo
    npc = NPCS.read_text(encoding="utf-8")
    for pat in [
        r'\n<npc name="Nimral" x="85" y="210" z="7"[^>]*/>',
        r'\n<npc name="The Oracle"[^>]*/>',
        r'\n<npc name="Sally" x="74" y="220" z="7"[^>]*/>',
    ]:
        npc, n = re.subn(pat, "", npc)
        if n > 1:
            raise SystemExit(f"esperaba 0 o 1 NPC para {pat}, encontré {n}")
    print("npc.xml: Nimral/Oracle/Sally fuera; sin Oracle de reemplazo")

    # readable del portal (opcional, si el sistema de readables lo permite)
    rd = READABLES.read_text(encoding="utf-8")
    rd = re.sub(r"\t?<!-- BEGIN EPSTEIN_PORTAL.*?<!-- END EPSTEIN_PORTAL -->\n?", "", rd, flags=re.S)
    block = ("\t<!-- BEGIN EPSTEIN_PORTAL -->\n"
             f'\t<readable x="{PORTAL[0]}" y="{PORTAL[1]}" z="{PORTAL[2]}" text="Portal to the mainland (temple)"/>\n'
             "\t<!-- END EPSTEIN_PORTAL -->\n")
    rd = rd.replace("</readables>", block + "\t</readables>") if "</readables>" in rd else rd
    print("readables.xml: cartel del portal")

    if args.dry_run:
        print("dry-run: no se escribió nada")
        return 0

    backup = Path("/private/var/folders/c8/k2dtzwbx3ml4l81234tng6vc0000gn/T/opencode") / \
        f"epstein-cleanup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    for f in (MAP, NPCS, READABLES):
        shutil.copy2(f, backup / f.name)
    print(f"backup: {backup}")

    MAP.write_bytes(serialize_tree(root, raw[:4]))
    NPCS.write_text(npc, encoding="utf-8")
    READABLES.write_text(rd, encoding="utf-8")
    print("escrito mapa, npc.xml y readables.xml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
