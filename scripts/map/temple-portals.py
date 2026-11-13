#!/usr/bin/env python3
"""Templo: plaza de mármol con todos los portales (dueño único de los portales del templo).

Hace, en una pasada e idempotente:
  1. Plaza 155,43 - 169,52 z7: mármol 406, marco y camino 407 (puerta norte x159-162 ->
     fila vieja), braseros en las esquinas. Conserva rejas 1543/1544/1545 y faroles 1480.
  2. Portales en la plaza (y=47), cartel al norte (y=46), llegada al sur (y=48).
     Izquierda = hunts, derecha = eventos.
  3. Fila vieja 155-169, 53-55: saca portales 1387 y carteles 1429 (queda de pasillo).
  4. Reapunta los portales de vuelta: todo teleport fuera del templo que apunte al templo
     pasa a la llegada del portal de su zona.
  5. Carteles en readables.xml (bloque TEMPLE_PORTAL_SIGNS); borra los carteles viejos
     de la fila que tenían otros bloques.

Si se regenera una zona (generate-crucible / -wave-arena / -beast-valley / -sand-clock),
volver a correr este script: limpia lo que el generador ponga en la fila vieja.

Uso: python3 scripts/map/temple-portals.py [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import (MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE,  # noqa: E402
                     parse_tree, serialize_tree)

READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
Z = 7
X1, Y1, X2, Y2 = 155, 43, 169, 52            # plaza
ROW = (155, 53, 169, 55)                      # fila vieja de portales
TEMPLE_AREA = (150, 40, 172, 60)              # un TP que apunte acá es "vuelta al templo"
PATH_X = range(159, 163)
WHITE, BLACK = 406, 407
TELEPORT, SIGN, BRAZIER = 1387, 1429, 1486
KEEP = {1543, 1544, 1545, 1480}
BRAZIERS = [(157, 44), (168, 44), (157, 51), (168, 51)]
PORTAL_Y = 47
ROW_GROUND_FIX = {(160, 53): WHITE, (160, 54): WHITE, (160, 55): WHITE}  # base del portal viejo del maze

# (clave, x del portal, destino, cartel, zonas cuyas vueltas llegan a este portal)
PORTALS = [
    ("isla", 156, (147, 462, 7), "ISLA NATURAL\nSendero: 3 campamentos Cyclops\nAl final, cueva y Grorlam",
     [(124, 426, 187, 483, 7), (124, 426, 187, 483, 8)]),
    ("valle", 158, (312, 360, 7), "VALLE DE LAS BESTIAS\nCaza mid-hard en 3 pisos\nDe Minotauros a Demonios",
     [(262, 232, 361, 378, 7), (262, 232, 361, 378, 8), (262, 232, 361, 378, 9), (449, 39, 489, 80, 7)]),
    ("crisol", 164, (83, 85, 0), "CRISOL\n3 puertas. Boss diario.\nBronce / Plata / Oro",
     [(70, 70, 195, 105, 0)]),
    ("wave", 166, (176, 403, 7), "WAVE ARENA\nClaro de la Selva: 20 oleadas\nEn grupo. Premio semanal",
     [(165, 380, 190, 410, 7)]),
    ("reloj", 168, (338, 395, 6), "RELOJ DE ARENA\n6 oleadas que suben de nivel\nEntra en el descanso",
     [(328, 383, 348, 401, 6), (328, 383, 348, 401, 5)]),
]
S_BEGIN, S_END = "<!-- BEGIN TEMPLE_PORTAL_SIGNS -->", "<!-- END TEMPLE_PORTAL_SIGNS -->"


def in_box(x, y, z, b) -> bool:
    return (len(b) == 4 or b[4] == z) and b[0] <= x <= b[2] and b[1] <= y <= b[3]


def item_node(iid: int, tele=None):
    props = bytearray(struct.pack("<H", iid))
    if tele:
        props += struct.pack("<BHHB", 8, *tele)
    return [T_ITEM, props, []]


def tele_offset(props: bytes) -> int | None:
    """Offset del atributo TELE_DEST (8) dentro de las props de un ítem, o None."""
    pos = 2
    try:
        while pos < len(props):
            a = props[pos]
            if a == 8:
                return pos + 1 if pos + 6 <= len(props) else None
            if a in (4, 5):        # action id / unique id
                pos += 3
            elif a == 15:          # count
                pos += 2
            elif a == 6:           # text
                pos += 3 + struct.unpack_from("<H", props, pos + 1)[0]
            else:
                return None
    except struct.error:
        return None
    return None


def plan_tiles() -> dict[tuple[int, int], list]:
    """Casillas de la plaza: (ground, [ítems], destino_tp)."""
    spec = {}
    for x in range(X1, X2 + 1):
        for y in range(Y1, Y2 + 1):
            edge = x in (X1, X2) or y == Y1
            spec[(x, y)] = [BLACK if edge or x in PATH_X else WHITE, [], None]
    for x, y in BRAZIERS:
        spec[(x, y)][1].append(BRAZIER)
    for _k, px, dest, _t, _z in PORTALS:
        spec[(px, PORTAL_Y)] = [BLACK, [], dest]
        spec[(px, PORTAL_Y - 1)] = [BLACK, [SIGN], None]
        spec[(px, PORTAL_Y + 1)] = [WHITE, [], None]
    return spec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    raw = MAP.read_bytes()
    root = parse_tree(raw)
    spec = plan_tiles()
    landing = {k: (px, PORTAL_Y + 1, Z) for k, px, _d, _t, _z in PORTALS}

    plaza_done, row_fixed, retargeted, unknown = 0, 0, [], []
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        keep_children = []
        for tile in area[2]:
            if tile[0] not in (T_TILE, T_HOUSETILE):
                keep_children.append(tile)
                continue
            p = bytes(tile[1])
            x, y = ax + p[0], ay + p[1]
            if az == Z and (x, y) in spec:
                if tile[0] != T_TILE:
                    raise SystemExit(f"ERROR: {x},{y} es casilla de casa, no la piso")
                kept = [ch for ch in tile[2] if ch[0] == T_ITEM
                        and struct.unpack_from("<H", bytes(ch[1]), 0)[0] in KEEP]
                ground, items, tele = spec[(x, y)]
                props = bytearray(p[:2]) + struct.pack("<BH", 9, ground)
                children = kept + [item_node(i) for i in items]
                if tele:
                    children.insert(0, item_node(TELEPORT, tele))
                keep_children.append([T_TILE, props, children])
                plaza_done += 1
                continue
            if az == Z and in_box(x, y, Z, ROW):
                before = len(tile[2])
                tile[2] = [ch for ch in tile[2] if ch[0] != T_ITEM or
                           struct.unpack_from("<H", bytes(ch[1]), 0)[0] not in (TELEPORT, SIGN)]
                row_fixed += before - len(tile[2])
                if (x, y) in ROW_GROUND_FIX and len(p) == 5 and p[2] == 9:
                    tile[1] = bytearray(p[:3]) + struct.pack("<H", ROW_GROUND_FIX[(x, y)])
            # vueltas al templo -> llegada del portal de su zona
            for ch in tile[2]:
                if ch[0] != T_ITEM:
                    continue
                off = tele_offset(bytes(ch[1]))
                if off is None:
                    continue
                dx, dy, dz = struct.unpack_from("<HHB", bytes(ch[1]), off)
                if not in_box(dx, dy, dz, (*TEMPLE_AREA, Z)) or in_box(x, y, az, (*TEMPLE_AREA, Z)):
                    continue
                key = next((k for k, _px, _d, _t, zones in PORTALS
                            if any(in_box(x, y, az, b) for b in zones)), None)
                if key is None:
                    unknown.append(((x, y, az), (dx, dy, dz)))
                    continue
                if (dx, dy, dz) != landing[key]:
                    ch[1][off:off + 5] = struct.pack("<HHB", *landing[key])
                    retargeted.append(((x, y, az), (dx, dy, dz), landing[key], key))
            keep_children.append(tile)
        area[2] = keep_children

    if plaza_done != len(spec):
        raise SystemExit(f"ERROR: la plaza tiene {plaza_done}/{len(spec)} casillas en el mapa")
    # control: no se pierde ni se agrega ninguna casilla
    def count_tiles(r):
        return sum(1 for ar in r[2][0][2] if ar[0] == T_AREA
                   for t in ar[2] if t[0] in (T_TILE, T_HOUSETILE))
    before, after = count_tiles(parse_tree(raw)), count_tiles(root)
    if before != after:
        raise SystemExit(f"ERROR interno: {before} casillas antes y {after} después; no escribo nada")

    print(f"plaza: {plaza_done} casillas; fila vieja: {row_fixed} portales/carteles sacados")
    for k, px, dest, _t, _z in PORTALS:
        print(f"  {k:10s} portal {px},{PORTAL_Y},{Z} -> {dest}; llegada {landing[k]}")
    for src, old, new, k in retargeted:
        print(f"  vuelta {src} {old} -> {new} ({k})")
    for src, d in unknown:
        print(f"  AVISO: teleport {src} -> {d} va al templo pero no sé de qué zona es (sin tocar)")
    if a.dry_run:
        return 0

    MAP.write_bytes(serialize_tree(root, raw[:4]))

    rd = READABLES.read_text(encoding="utf-8")
    # carteles viejos de la fila (los ponían otros generadores)
    rd = re.sub(r'[ \t]*<readable x="1(5[5-9]|6[0-9])" y="53" z="7"[^>]*/>\n', "", rd)
    rd = re.sub(r"[ \t]*<!-- BEGIN NATURAL_ISLAND_SIGNS -->\s*<!-- END NATURAL_ISLAND_SIGNS -->\n?", "", rd)
    lines = [f"\t{S_BEGIN}"]
    for _k, px, _d, text, _z in PORTALS:
        lines.append(f'\t<readable x="{px}" y="{PORTAL_Y - 1}" z="{Z}" text="{text.replace(chr(10), chr(92) + "n")}"/>')
    lines.append(f"\t{S_END}")
    block = "\n".join(lines)
    if S_BEGIN in rd:
        rd = re.sub(rf"\t?{re.escape(S_BEGIN)}.*?{re.escape(S_END)}", lambda _: block, rd, flags=re.S)
    else:
        rd = rd.replace("</readables>", block + "\n</readables>")
    READABLES.write_text(rd, encoding="utf-8")
    print(f"OK {MAP} y {READABLES.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
