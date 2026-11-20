#!/usr/bin/env python3
"""Muelle del depot (x113-124, y56-62, z7): barandas de madera con faroles y rampa de escalones.

Reemplaza las piezas nativas que se veían rotas (barandas 1516-1519 finitas y torcidas, faroles 3744 que
parecían calaveras, rampa de piedra gris pegada a la madera). Todo se dibuja como una sola estructura 3D
con la proyección de Tibia (un punto a altura h se ve h px más arriba y h px más a la izquierda) y se corta
en una pieza 2x2 por casilla: así las barandas empalman sin costuras entre casillas.

Cada pieza es la parte de la estructura cuya base cae en la región de su casilla "ancla". El ancla de las
barandas es la casilla de agua del borde (se dibujan después de los jugadores parados en el muelle, que
quedan delante o detrás según corresponde); la rampa usa las mismas casillas que la de piedra.

  python3.11 scripts/client-rme/dock_bridge_art.py --preview /tmp/muelle.png

Escribe devtools/zagan-test/custom-sprites/dock_*.png (64x64). Los instala add_custom_items.py (NEW_ITEMS
importa DOCK_ITEMS de acá) y los pone en el mapa scripts/map/city-bridge-transitions.py.
Doc: docs/items-and-map/TRANSICIONES_DEPOT.md. Necesita Pillow (python3.11).
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1].parent
OUT_DIR = ROOT / "devtools/zagan-test/custom-sprites"
T = 32
H = 16            # alto del pasamanos
NEWEL = 17        # alto de los postes de las esquinas
LIGHT = (4, 206)  # faroles: nivel 4, cálido

# --- piezas: server id, client id sacrificado (server viejo entre paréntesis), anclas -------------------
# prototype 1517 (baranda de madera 2x2, bloquea) para barandas; 1390/1391 (rampa al oeste, 2x2) para la rampa.
PIECES = [
    # key,             server, client, proto, anclas,                                   luz
    ("rail_n_corner",   20282, 2863, 1517, [(115, 58)],                                 None),   # bag (1997)
    ("rail_n",          20283, 2859, 1517, [(x, 58) for x in range(116, 122)],          None),   # bag (1993)
    ("rail_n_end",      20284, 2858, 1517, [(122, 58)],                                 LIGHT),  # bag (1992)
    ("rail_s_start",    20285, 2855, 1517, [(115, 62)],                                 None),   # basket (1989)
    ("rail_s",          20286, 2847, 1517, [(x, 62) for x in range(116, 122)],          None),   # book (1981)
    ("rail_s_end",      20287, 2846, 1517, [(122, 62)],                                 LIGHT),  # book (1980)
    ("rail_e_top",      20288, 3101, 1517, [(115, 56)],                                 LIGHT),  # book (2217)
    ("rail_e",          20289, 2996, 1517, [(115, 57)],                                 None),   # damage piggy bank (2115)
    ("rail_w_top",      20290, 2988, 1517, [(112, 56)],                                 LIGHT),  # exotic flower (2107)
    ("rail_w",          20291, 2974, 1517, [(112, 57)],                                 None),   # water-pipe (2093)
    ("rail_w_end",      20292, 2884, 1517, [(112, 58)],                                 None),   # cup (3942)
    ("ramp_w_n",        20293, 2883, 1390, [(113, 60)],                                 None),   # cup (3941)
    ("ramp_w_s",        20294, 3058, 1390, [(113, 61)],                                 None),   # strange symbol (2174)
    ("ramp_e_n",        20295, 3024, 1391, [(114, 60)],                                 None),   # eagle amulet (2141)
    ("ramp_e_s",        20296, 3023, 1391, [(114, 61)],                                 None),   # holy scarab (2140)
]
NAMES = {"rail": "wooden railing", "ramp": "wooden ramp"}
DESCR = {"rail": "Sturdy dock railing of tarred oak.", "ramp": "Wooden steps leading up the bank."}


def dock_items() -> list[dict]:
    """Entradas para NEW_ITEMS de add_custom_items.py."""
    out = []
    for key, sid, cid, proto, _anchors, light in PIECES:
        kind = key.split("_")[0]
        item = dict(name=NAMES[kind] if not light else "dock lantern", server_id=sid, client_id=cid,
                    prototype=proto, png=f"dock_{key}.png", decor=True, tiles=2,
                    descr="A lantern on a dock post." if light else DESCR[kind])
        if light:
            item["light"] = light
        out.append(item)
    return out


# --- geometría (coordenadas de píxel globales: gx = x*32 + offset; h = altura) -------------------------
RAIL_TOP, RAIL_S, RAIL_E = (232, 190, 122), (184, 134, 76), (146, 100, 52)
POST_TOP, POST_S, POST_E = (204, 154, 90), (158, 110, 60), (122, 82, 44)
TREAD, TREAD_ALT, RISER, STRINGER = (230, 188, 120), (214, 170, 104), (128, 84, 42), (104, 68, 34)
GLASS_S, GLASS_E, CAP, CAP_TOP = (255, 240, 160), (252, 196, 84), (122, 80, 40), (168, 116, 62)
OUTLINE = (62, 38, 18)


class Box:
    """Caja [x0,x1) x [y0,y1) x [h0,h1); caras visibles: arriba, sur (y1) y este (x1)."""

    def __init__(self, x0, x1, y0, y1, h0, h1, top, south, east):
        self.b = (x0, x1, y0, y1, h0, h1)
        self.colors = (top, south, east)

    def clip(self, rx0, rx1, ry0, ry1):
        x0, x1, y0, y1, h0, h1 = self.b
        cx0, cx1, cy0, cy1 = max(x0, rx0), min(x1, rx1), max(y0, ry0), min(y1, ry1)
        if cx0 >= cx1 or cy0 >= cy1:
            return None
        # una cara cortada por el borde de la región no es la cara real: no se dibuja
        return (cx0, cx1, cy0, cy1, h0, h1), cx1 == x1, cy1 == y1


def rail_line(axis, fixed0, a0, a1, posts):
    """Baranda: zócalo, postes, travesaño medio y pasamanos. axis 'x' corre de oeste a este (fixed = gy del
    borde), 'y' de norte a sur (fixed = gx)."""
    out = []

    def box(p0, p1, q0, q1, h0, h1, c):
        if axis == "x":
            out.append(Box(p0, p1, q0, q1, h0, h1, *c))
        else:
            out.append(Box(q0, q1, p0, p1, h0, h1, *c))

    box(a0, a1, fixed0, fixed0 + 4, 0, 3, (POST_TOP, POST_S, POST_E))
    for p in posts:
        box(p - 2, p + 2, fixed0, fixed0 + 4, 3, H - 3, (POST_TOP, POST_S, POST_E))
    box(a0, a1, fixed0 + 1, fixed0 + 4, 6, 9, (RAIL_TOP, RAIL_S, RAIL_E))
    box(a0, a1, fixed0, fixed0 + 4, H - 4, H, (RAIL_TOP, RAIL_S, RAIL_E))
    return out


def newel(x0, y0, lantern):
    """Poste de esquina. Con farol el poste es 2 px más bajo, así el conjunto (27 px) entra en el 2x2."""
    top = NEWEL - 2 if lantern else NEWEL
    out = [Box(x0, x0 + 6, y0, y0 + 6, 0, top, POST_TOP, POST_S, POST_E),
           Box(x0 - 1, x0 + 7, y0 - 1, y0 + 7, top, top + 2, RAIL_TOP, RAIL_S, RAIL_E)]
    if lantern:
        out += [Box(x0, x0 + 6, y0, y0 + 6, top + 2, top + 10, GLASS_S, GLASS_S, GLASS_E),
                Box(x0 - 1, x0 + 7, y0 - 1, y0 + 7, top + 10, top + 12, CAP_TOP, CAP, CAP)]
    return out


def rails() -> list[Box]:
    n_y, s_y = 59 * T - 6, 62 * T - 4          # borde norte (franja 434) y sur del muelle
    e_x, w_x = 115 * T - 4, 113 * T - 4        # bordes este y oeste del brazo norte
    every = lambda a, b: [p for p in range(a, b, 16)]
    out = []
    out += rail_line("x", n_y, 115 * T, 123 * T - 3, every(115 * T + 8, 122 * T + 9))
    out += rail_line("x", s_y, 115 * T, 123 * T - 3, every(115 * T + 8, 122 * T + 9))
    out += rail_line("y", e_x, 56 * T + 3, 59 * T - 6, every(56 * T + 24, 58 * T + 25))
    out += rail_line("y", w_x, 56 * T + 3, 59 * T - 3, every(56 * T + 24, 58 * T + 9))
    out += newel(115 * T - 4, 59 * T - 7, False)   # esquina brazo / tramo norte
    out += newel(123 * T - 6, 59 * T - 7, True)    # fin norte, junto a la orilla del depot
    out += newel(115 * T - 4, 62 * T - 5, False)   # inicio sur, al pie de la rampa
    out += newel(123 * T - 6, 62 * T - 5, True)    # fin sur
    out += newel(115 * T - 4, 56 * T, True)        # cabeza del brazo, este
    out += newel(113 * T - 6, 56 * T, True)        # cabeza del brazo, oeste
    out += newel(113 * T - 6, 59 * T - 6, False)   # fin del brazo, oeste (sigue pasto)
    return out


def ramp() -> list[Box]:
    """8 escalones de 8 px de huella y 4 de alto: de 32 (piso de arriba, oeste) a 0 (muelle, este). Cada
    escalón son 4 tablas de 16 px a lo ancho, en dos tonos, para que se lean como peldaños de madera."""
    out = []
    for k in range(8):
        for j in range(4):
            tread = TREAD if (j + k) % 2 == 0 else TREAD_ALT
            out.append(Box(113 * T + 8 * k, 113 * T + 8 * k + 8, 60 * T + 16 * j, 60 * T + 16 * j + 16,
                           0, 32 - 4 * k, tread, STRINGER, RISER))
    return out


def region(key, ax, ay):
    """Región del suelo que dibuja cada ancla (las barandas caen en la casilla vecina del muelle)."""
    if key.startswith("ramp"):
        return ax * T, ax * T + T, ay * T, ay * T + T
    if key in ("rail_e_top", "rail_e"):
        return 115 * T - 8, 115 * T + 8, ay * T - (8 if key == "rail_e_top" else 0), ay * T + T
    if key == "rail_n_corner":
        return 115 * T - 8, 116 * T, 58 * T, 59 * T + 8
    if key.startswith("rail_n"):
        return ax * T, ax * T + T, 58 * T, 59 * T + 8
    if key == "rail_s_start":
        return 115 * T - 8, 116 * T, 61 * T, 63 * T
    if key.startswith("rail_s"):
        return ax * T, ax * T + T, 61 * T, 63 * T
    if key.startswith("rail_w"):
        y0 = ay * T - (8 if key == "rail_w_top" else 0)
        return 113 * T - 8, 113 * T + 8, y0, ay * T + T + (8 if key == "rail_w_end" else 0)
    raise KeyError(key)


# --- dibujo ----------------------------------------------------------------------------------------------
ORIGIN = (110 * T, 53 * T)        # esquina del lienzo global
SIZE = (16 * T, 12 * T)


def faces(boxes, reg):
    out = []
    for b in boxes:
        clipped = b.clip(*reg)
        if not clipped:
            continue
        (x0, x1, y0, y1, h0, h1), east_ok, south_ok = clipped
        x1, y1, h1 = x1 - 1, y1 - 1, h1 - 1        # cajas inclusivas en píxeles
        top, south, east = b.colors
        quads = [((x0, y0, h1), (x1, y0, h1), (x1, y1, h1), (x0, y1, h1), top)]
        if south_ok:
            quads.append(((x0, y1, h0), (x1, y1, h0), (x1, y1, h1), (x0, y1, h1), south))
        if east_ok:
            quads.append(((x1, y0, h0), (x1, y1, h0), (x1, y1, h1), (x1, y0, h1), east))
        for q in quads:
            pts = q[:4]
            depth = sum(p[0] + p[1] + p[2] for p in pts) / 4
            out.append((depth, pts, q[4]))
    out.sort(key=lambda f: f[0])
    return out


def render_piece(boxes, reg):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for _d, pts, color in faces(boxes, reg):
        poly = [(gx - h - ORIGIN[0], gy - h - ORIGIN[1]) for gx, gy, h in pts]
        draw.polygon(poly, fill=color + (255,))
    return img


def grain(x, y):
    """Ruido fijo por píxel dentro de la casilla (así las casillas repetidas dan el mismo sprite)."""
    n = (x * 73856093) ^ (y * 19349663)
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFF
    return 0.93 + 0.10 * (n / 0xFFFF)


def build():
    from PIL import Image
    rail_boxes, ramp_boxes = rails(), ramp()
    layers = {}
    for key, *_rest in PIECES:
        anchors = _rest[3]
        boxes = ramp_boxes if key.startswith("ramp") else rail_boxes
        layers[key] = [(a, render_piece(boxes, region(key, *a))) for a in anchors]
    union = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    for inst in layers.values():
        for _a, img in inst:
            union.alpha_composite(img)
    alpha = union.getchannel("A").load()
    W, Hh = SIZE

    def edge(x, y):
        return any(not (0 <= x + dx < W and 0 <= y + dy < Hh) or alpha[x + dx, y + dy] == 0
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))

    sprites = {}
    for key, inst in layers.items():
        crops = []
        for (ax, ay), img in inst:
            px = img.load()
            for y in range(Hh):
                for x in range(W):
                    r, g, b, a = px[x, y]
                    if not a:
                        continue
                    if (r, g, b) in (GLASS_S, GLASS_E):
                        continue          # el vidrio del farol va sin contorno ni veta
                    if edge(x, y):
                        px[x, y] = OUTLINE + (255,)
                    else:
                        k = grain((x + ORIGIN[0]) % T, (y + ORIGIN[1]) % T)
                        px[x, y] = (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)), 255)
            cx, cy = (ax - 1) * T - ORIGIN[0], (ay - 1) * T - ORIGIN[1]
            box = img.getbbox()
            if box and (box[0] < cx or box[1] < cy or box[2] > cx + 64 or box[3] > cy + 64):
                raise SystemExit(f"{key} en {ax},{ay}: el dibujo se sale del 2x2 ({box} vs {cx},{cy})")
            crops.append(img.crop((cx, cy, cx + 64, cy + 64)))
        if any(c.tobytes() != crops[0].tobytes() for c in crops):
            raise SystemExit(f"{key}: las casillas repetidas no dan el mismo sprite")
        sprites[key] = crops[0]
    return sprites, union


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", type=Path, help="PNG con la estructura completa a 2x")
    a = ap.parse_args()
    from PIL import Image
    sprites, _union = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, img in sprites.items():
        img.save(OUT_DIR / f"dock_{key}.png")
    print(f"{len(sprites)} sprites en {OUT_DIR}")
    if a.preview:
        sheet = Image.new("RGBA", SIZE, (40, 40, 46, 255))
        for key, _s, _c, _p, anchors, _l in PIECES:
            for ax, ay in anchors:
                sheet.alpha_composite(sprites[key], ((ax - 1) * T - ORIGIN[0], (ay - 1) * T - ORIGIN[1]))
        sheet.resize((SIZE[0] * 2, SIZE[1] * 2), Image.NEAREST).save(a.preview)
        print(f"vista previa: {a.preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
