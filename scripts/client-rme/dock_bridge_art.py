#!/usr/bin/env python3
"""Puentes y muelles de madera: barandas con faroles y la rampa de escalones del muelle del depot.

Reemplaza piezas nativas que se veían rotas (barandas 1516-1519 finitas y torcidas, puentes de cuerda
3758-3791, faroles 3744 que parecían calaveras, rampa de piedra gris pegada a la madera). Cada estructura se
dibuja en 3D con la proyección de Tibia (un punto a altura h se ve h px más arriba y h px más a la
izquierda) y se corta en una pieza 2x2 por casilla: así las barandas empalman sin costuras entre casillas.

Cada pieza es la parte de la estructura cuya base cae en la región de su casilla "ancla". El ancla de las
barandas es la casilla de agua/orilla del borde (bloqueada), así se dibujan en el orden correcto respecto de
los jugadores; la rampa usa las mismas casillas que la de piedra.

Estructuras:
  - DOCK: muelle del depot (x112-124, y56-62), con piezas propias (esquina, rampa).
  - BRIDGES: puentes de la ciudad y alrededores, con barandas genéricas por lado (inicio con farol, tramo,
    fin con farol). Todas las casillas de una misma pieza dan el mismo sprite (el script lo verifica).

  python3.11 scripts/client-rme/dock_bridge_art.py --preview /tmp/puentes   # una vista previa por estructura

Escribe devtools/zagan-test/custom-sprites/dock_*.png (64x64). Los instala add_custom_items.py (NEW_ITEMS
importa dock_items() de acá) y los pone en el mapa scripts/map/city-bridge-transitions.py.
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
Z = 7

# --- piezas: server id, client id sacrificado (server viejo entre paréntesis) ----------------------------
# prototype 1517 (baranda de madera 2x2, bloquea) para barandas; 1390/1391 (rampa al oeste, 2x2) para la rampa.
# Lados: n/s = barandas de puentes que corren de oeste a este; w/e = de norte a sur.
PIECES = [
    # key,             server, client, proto, luz
    ("rail_n_corner",   20282, 2863, 1517, None),    # bag (1997)          solo muelle
    ("rail_n",          20283, 2859, 1517, None),    # bag (1993)
    ("rail_n_end",      20284, 2858, 1517, LIGHT),   # bag (1992)
    ("rail_s_start",    20285, 2855, 1517, None),    # basket (1989)       solo muelle (sin farol)
    ("rail_s",          20286, 2847, 1517, None),    # book (1981)
    ("rail_s_end",      20287, 2846, 1517, LIGHT),   # book (1980)
    ("rail_e_top",      20288, 3101, 1517, LIGHT),   # book (2217)
    ("rail_e",          20289, 2996, 1517, None),    # damage piggy bank (2115)
    ("rail_w_top",      20290, 2988, 1517, LIGHT),   # exotic flower (2107)
    ("rail_w",          20291, 2974, 1517, None),    # water-pipe (2093)
    ("rail_w_end",      20292, 2884, 1517, None),    # cup (3942)          solo muelle (sin farol)
    ("ramp_w_n",        20293, 2883, 1390, None),    # cup (3941)
    ("ramp_w_s",        20294, 3058, 1390, None),    # strange symbol (2174)
    ("ramp_e_n",        20295, 3024, 1391, None),    # eagle amulet (2141)
    ("ramp_e_s",        20296, 3023, 1391, None),    # holy scarab (2140)
    ("rail_n_start",    20297, 2845, 1517, LIGHT),   # book (1979)
    ("rail_s_west",     20298, 2844, 1517, LIGHT),   # book (1978)
    ("rail_w_bot",      20299, 2840, 1517, LIGHT),   # book (1974)
    ("rail_e_bot",      20300, 2836, 1517, LIGHT),   # book (1970)
]
NAMES = {"rail": "wooden railing", "ramp": "wooden ramp"}
DESCR = {"rail": "Sturdy railing of tarred oak.", "ramp": "Wooden steps leading up the bank."}

# Puentes con barandas genéricas. v: corre de norte a sur (deck = columnas x0..x1; w/e = filas con baranda a
# cada lado). h: corre de oeste a este (deck = filas y0..y1; n/s = columnas con baranda arriba y abajo).
# Las filas/columnas son las casillas de agua u orilla bloqueadas junto al tablero.
BRIDGES = {
    "camino_norte_134": dict(kind="v", deck=(134, 136), w=(109, 116), e=(109, 116)),
    "rio_182":          dict(kind="v", deck=(182, 183), w=(80, 87), e=(80, 87)),
    "arroyo_146":       dict(kind="v", deck=(146, 147), w=(104, 107), e=(104, 107)),
    "islote_50":        dict(kind="v", deck=(50, 50), w=(148, 154), e=(148, 153)),
    "rio_153":          dict(kind="v", deck=(153, 153), w=(66, 72), e=(66, 72)),
    "rio_103":          dict(kind="v", deck=(103, 104), w=(48, 50), e=(48, 50)),
    "islotes_87":       dict(kind="h", deck=(87, 87), n=(87, 92), s=(87, 93)),
    "arroyo_89":        dict(kind="h", deck=(104, 105), n=(89, 92), s=(89, 92)),
}


def dock_items() -> list[dict]:
    """Entradas para NEW_ITEMS de add_custom_items.py."""
    out = []
    for key, sid, cid, proto, light in PIECES:
        kind = key.split("_")[0]
        item = dict(name=NAMES[kind] if not light else "dock lantern", server_id=sid, client_id=cid,
                    prototype=proto, png=f"dock_{key}.png", decor=True, tiles=2,
                    descr="A lantern on a railing post." if light else DESCR[kind])
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


def every(a, b):
    return list(range(a, b, 16))


def dock():
    """Muelle del depot: tramo largo, brazo norte al islote y rampa a los elfos. Devuelve grupos
    (cajas, [(pieza, ancla, región)])."""
    n_y, s_y = 59 * T - 6, 62 * T - 4          # borde norte (franja 434) y sur del muelle
    e_x, w_x = 115 * T - 4, 113 * T - 4        # bordes este y oeste del brazo norte
    rails = []
    rails += rail_line("x", n_y, 115 * T, 123 * T - 3, every(115 * T + 8, 122 * T + 9))
    rails += rail_line("x", s_y, 115 * T, 123 * T - 3, every(115 * T + 8, 122 * T + 9))
    rails += rail_line("y", e_x, 56 * T + 3, 59 * T - 6, every(56 * T + 24, 58 * T + 25))
    rails += rail_line("y", w_x, 56 * T + 3, 59 * T - 3, every(56 * T + 24, 58 * T + 9))
    rails += newel(115 * T - 4, 59 * T - 7, False)   # esquina brazo / tramo norte
    rails += newel(123 * T - 6, 59 * T - 7, True)    # fin norte, junto a la orilla del depot
    rails += newel(115 * T - 4, 62 * T - 5, False)   # inicio sur, al pie de la rampa
    rails += newel(123 * T - 6, 62 * T - 5, True)    # fin sur
    rails += newel(115 * T - 4, 56 * T, True)        # cabeza del brazo, este
    rails += newel(113 * T - 6, 56 * T, True)        # cabeza del brazo, oeste
    rails += newel(113 * T - 6, 59 * T - 6, False)   # fin del brazo, oeste (sigue pasto)
    pieces = [("rail_n_corner", (115, 58), (115 * T - 8, 116 * T, 58 * T, 59 * T + 8))]
    pieces += [("rail_n", (x, 58), (x * T, x * T + T, 58 * T, 59 * T + 8)) for x in range(116, 122)]
    pieces += [("rail_n_end", (122, 58), (122 * T, 123 * T + 8, 58 * T, 59 * T + 8))]
    pieces += [("rail_s_start", (115, 62), (115 * T - 8, 116 * T, 61 * T, 63 * T))]
    pieces += [("rail_s", (x, 62), (x * T, x * T + T, 61 * T, 63 * T)) for x in range(116, 122)]
    pieces += [("rail_s_end", (122, 62), (122 * T, 123 * T + 8, 61 * T, 63 * T))]
    pieces += [("rail_e_top", (115, 56), (115 * T - 8, 115 * T + 8, 56 * T - 8, 57 * T)),
               ("rail_e", (115, 57), (115 * T - 8, 115 * T + 8, 57 * T, 58 * T)),
               ("rail_w_top", (112, 56), (113 * T - 8, 113 * T + 8, 56 * T - 8, 57 * T)),
               ("rail_w", (112, 57), (113 * T - 8, 113 * T + 8, 57 * T, 58 * T)),
               ("rail_w_end", (112, 58), (113 * T - 8, 113 * T + 8, 58 * T, 59 * T + 8))]
    ramps = [(f"ramp_{'w' if x == 113 else 'e'}_{'n' if y == 60 else 's'}", (x, y), (x * T, x * T + T, y * T, y * T + T))
             for x in (113, 114) for y in (60, 61)]
    return [(rails, pieces), (ramp(), ramps)]


def vrun(side, line, ya, yb):
    """Baranda de un puente norte-sur sobre el borde x = line (w: borde oeste del tablero, ancla en line-1;
    e: borde este, line = primera columna fuera del tablero y ancla). Farol en las dos puntas."""
    fixed = line * T - 4
    nx = line * T - 6 if side == "w" else line * T - 4
    boxes = rail_line("y", fixed, ya * T + 3, (yb + 1) * T - 3, every(ya * T + 24, yb * T + 9))
    boxes += newel(nx, ya * T, True) + newel(nx, (yb + 1) * T - 6, True)
    ax = line - 1 if side == "w" else line
    pieces = []
    for y in range(ya, yb + 1):
        key = f"rail_{side}_top" if y == ya else f"rail_{side}_bot" if y == yb else f"rail_{side}"
        reg = (line * T - 8, line * T + 8, y * T - (8 if y == ya else 0), y * T + T + (8 if y == yb else 0))
        pieces.append((key, (ax, y), reg))
    return boxes, pieces


def hrun(side, line, xa, xb):
    """Baranda de un puente oeste-este sobre el borde y = line (n: borde norte del tablero, ancla en line-1;
    s: borde sur, line = primera fila fuera del tablero y ancla)."""
    fixed, ny = (line * T - 6, line * T - 7) if side == "n" else (line * T - 4, line * T - 5)
    boxes = rail_line("x", fixed, xa * T + 3, (xb + 1) * T - 3, every(xa * T + 24, xb * T + 9))
    boxes += newel(xa * T, ny, True) + newel((xb + 1) * T - 6, ny, True)
    ay = line - 1 if side == "n" else line
    gy = (line * T - T, line * T + 8) if side == "n" else (line * T - T, line * T + T)
    start, end = ("rail_n_start", "rail_n_end") if side == "n" else ("rail_s_west", "rail_s_end")
    pieces = []
    for x in range(xa, xb + 1):
        key = start if x == xa else end if x == xb else f"rail_{side}"
        pieces.append((key, (x, ay), (x * T - (8 if x == xa else 0), x * T + T + (8 if x == xb else 0)) + gy))
    return boxes, pieces


def bridge(spec):
    boxes, pieces = [], []
    if spec["kind"] == "v":
        x0, x1 = spec["deck"]
        for side, line in (("w", x0), ("e", x1 + 1)):
            b, p = vrun(side, line, *spec[side])
            boxes += b
            pieces += p
    else:
        y0, y1 = spec["deck"]
        for side, line in (("n", y0), ("s", y1 + 1)):
            b, p = hrun(side, line, *spec[side])
            boxes += b
            pieces += p
    return [(boxes, pieces)]


def structures():
    """{nombre: grupos}. Cada grupo es (cajas, [(pieza, (x, y), región del suelo)])."""
    out = {"muelle_depot": dock()}
    for name, spec in BRIDGES.items():
        out[name] = bridge(spec)
    return out


def placements() -> dict[tuple[int, int, int], str]:
    """(x, y, z) -> pieza, para el script del mapa."""
    out = {}
    for groups in structures().values():
        for _boxes, pieces in groups:
            for key, (x, y), _reg in pieces:
                if (x, y, Z) in out:
                    raise SystemExit(f"Dos piezas en {x},{y}")
                out[(x, y, Z)] = key
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


# --- dibujo ----------------------------------------------------------------------------------------------
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


def render_piece(boxes, reg, origin, size):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for _d, pts, color in faces(boxes, reg):
        poly = [(gx - h - origin[0], gy - h - origin[1]) for gx, gy, h in pts]
        draw.polygon(poly, fill=color + (255,))
    return img


def grain(x, y):
    """Ruido fijo por píxel dentro de la casilla (así las casillas repetidas dan el mismo sprite)."""
    n = (x * 73856093) ^ (y * 19349663)
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFF
    return 0.93 + 0.10 * (n / 0xFFFF)


def build_structure(groups):
    """Dibuja una estructura: devuelve [(pieza, ancla, sprite 64x64)] y el lienzo completo."""
    from PIL import Image
    anchors = [a for _b, pieces in groups for _k, a, _r in pieces]
    origin = ((min(x for x, _ in anchors) - 2) * T, (min(y for _, y in anchors) - 2) * T)
    size = ((max(x for x, _ in anchors) + 2) * T - origin[0], (max(y for _, y in anchors) + 2) * T - origin[1])
    layers = [(key, a, render_piece(boxes, reg, origin, size)) for boxes, pieces in groups for key, a, reg in pieces]
    union = Image.new("RGBA", size, (0, 0, 0, 0))
    for _k, _a, img in layers:
        union.alpha_composite(img)
    alpha = union.getchannel("A").load()
    W, Hh = size

    def edge(x, y):
        return any(not (0 <= x + dx < W and 0 <= y + dy < Hh) or alpha[x + dx, y + dy] == 0
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))

    out = []
    for key, (ax, ay), img in layers:
        px = img.load()
        for y in range(Hh):
            for x in range(W):
                r, g, b, a = px[x, y]
                if not a or (r, g, b) in (GLASS_S, GLASS_E):
                    continue          # el vidrio del farol va sin contorno ni veta
                if edge(x, y):
                    px[x, y] = OUTLINE + (255,)
                else:
                    k = grain((x + origin[0]) % T, (y + origin[1]) % T)
                    px[x, y] = (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)), 255)
        cx, cy = (ax - 1) * T - origin[0], (ay - 1) * T - origin[1]
        box = img.getbbox()
        if box and (box[0] < cx or box[1] < cy or box[2] > cx + 64 or box[3] > cy + 64):
            raise SystemExit(f"{key} en {ax},{ay}: el dibujo se sale del 2x2 ({box} vs {cx},{cy})")
        out.append((key, (ax, ay), img.crop((cx, cy, cx + 64, cy + 64))))
    return out


def build():
    """{pieza: sprite}; verifica que todas las casillas de una pieza (en todas las estructuras) coincidan."""
    sprites, where = {}, {}
    for name, groups in structures().items():
        for key, a, img in build_structure(groups):
            if key in sprites and sprites[key].tobytes() != img.tobytes():
                raise SystemExit(f"{key}: {name} {a} no da el mismo sprite que {where[key]}")
            sprites.setdefault(key, img)
            where.setdefault(key, f"{name} {a}")
    missing = {k for k, *_ in PIECES} - set(sprites)
    if missing:
        raise SystemExit(f"Piezas sin usar: {sorted(missing)}")
    return sprites


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", type=Path, help="carpeta: una vista previa por estructura, a 2x")
    a = ap.parse_args()
    from PIL import Image
    sprites = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, img in sprites.items():
        img.save(OUT_DIR / f"dock_{key}.png")
    print(f"{len(sprites)} sprites en {OUT_DIR}")
    if a.preview:
        a.preview.mkdir(parents=True, exist_ok=True)
        for name, groups in structures().items():
            anchors = sorted({a for _b, p in groups for _k, a, _r in p}, key=lambda t: (t[1], t[0]))
            keys = {a: k for _b, p in groups for k, a, _r in p}
            x0, y0 = min(x for x, _ in anchors) - 2, min(y for _, y in anchors) - 2
            x1, y1 = max(x for x, _ in anchors) + 2, max(y for _, y in anchors) + 2
            sheet = Image.new("RGBA", ((x1 - x0) * T, (y1 - y0) * T), (40, 40, 46, 255))
            for ax, ay in anchors:
                sheet.alpha_composite(sprites[keys[(ax, ay)]], ((ax - 1 - x0) * T, (ay - 1 - y0) * T))
            sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(a.preview / f"{name}.png")
        print(f"vistas previas en {a.preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
