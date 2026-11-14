#!/usr/bin/env python3
"""Genera las fotos de ruta para la wiki: mapa real + flechas rojas, desde el depot.

Lee `scripts/map/routes.json` y dibuja cada tramo en el mapa real (sprites del cliente), en
imágenes de 16 px por casilla. Cada ruta se parte en pasos; las imágenes van a
`web/assets/wiki/routes/<slug>/` y el índice a `web/assets/wiki/routes/manifest.json`.

Requiere Pillow:
  python3 -m pip install pillow
  python3 scripts/map/build-route-images.py
  python3 scripts/map/build-route-images.py --map OTRO.otbm
"""
from __future__ import annotations

import json
import math
import struct
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
sys.path.insert(0, str(HERE))
from mapdata import MAP, REPO, iter_tiles, load_otb, parse_tree  # noqa: E402
import game_render as GR  # noqa: E402

ROUTES = HERE / "routes.json"
OUT = REPO / "web/assets/wiki/routes"
MAP_PATH = MAP
SCALE = 16          # píxeles por casilla en la salida
SRC = 32            # píxeles por casilla del cliente
MARGIN = 6          # casillas de margen alrededor del tramo
BG = (10, 10, 13, 255)
RED = (220, 24, 24)
RED_DARK = (150, 10, 10)
WHITE = (255, 255, 255)
INK = (12, 12, 16)

FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def font(size: int):
    for path in FONTS:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                pass
    return ImageFont.load_default()


def load_map():
    floors = {}
    for x, y, z, items in iter_tiles(parse_tree(MAP_PATH.read_bytes())):
        floors.setdefault(z, {})[(x, y)] = items
    return floors


class Renderer:
    def __init__(self):
        self.otb = load_otb()
        self.items, _ = GR.parse_dat_all()
        self.spr = GR.Sprites()
        self.entry = {sid: self.items.get(e.get("cid")) for sid, e in self.otb.items() if e.get("cid")}
        self.cache = {}

    def item_img(self, sid, x, y):
        e = self.entry.get(sid)
        if e is None:
            return None, None
        key = (sid, x % e["px"], y % e["py"])
        im = self.cache.get(key)
        if im is None:
            im = self.cache[key] = GR.compose(e, self.spr, key[1], key[2])
        return im, e

    def crop(self, floors, z, x0, y0, x1, y1):
        w, h = x1 - x0 + 1, y1 - y0 + 1
        canvas = Image.new("RGBA", ((w + 2 * MARGIN) * SRC, (h + 2 * MARGIN) * SRC), BG)
        tiles = floors.get(z, {})
        for ty in range(y0 - MARGIN, y1 + MARGIN + 1):
            for tx in range(x0 - MARGIN, x1 + MARGIN + 1):
                its = tiles.get((tx, ty))
                if not its:
                    continue
                draw = []
                for sid in its:
                    im, e = self.item_img(sid, tx, ty)
                    if im is not None:
                        draw.append((GR.LAYER_RANK[GR.layer_of(e)], im, e))
                draw.sort(key=lambda t: t[0])
                elev = 0
                for _rank, im, e in draw:
                    dx = dy = 0
                    if 0x18 in e["flags"]:
                        dx, dy = struct.unpack("<HH", e["flags"][0x18])
                    px = (tx - (x0 - MARGIN)) * SRC - (e["w"] - 1) * SRC - dx - elev
                    py = (ty - (y0 - MARGIN)) * SRC - (e["h"] - 1) * SRC - dy - elev
                    canvas.paste(im, (px, py), im)
                    if 0x19 in e["flags"]:
                        elev = min(24, elev + struct.unpack("<H", e["flags"][0x19])[0])
        img = canvas.crop((MARGIN * SRC, MARGIN * SRC, (MARGIN + w) * SRC, (MARGIN + h) * SRC))
        return img.resize((w * SCALE, h * SCALE), Image.LANCZOS).convert("RGB")


def arrow(draw, p1, p2, size=9):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    tip = (mx + ux * size, my + uy * size)
    left = (mx - uy * size * .7 - ux * size * .6, my + ux * size * .7 - uy * size * .6)
    right = (mx + uy * size * .7 - ux * size * .6, my - ux * size * .7 - uy * size * .6)
    draw.polygon([tip, left, right], fill=RED, outline=WHITE)


def draw_path(img, points, x0, y0):
    draw = ImageDraw.Draw(img)
    pts = [((x - x0) * SCALE + SCALE // 2, (y - y0) * SCALE + SCALE // 2) for x, y in points]
    if len(pts) >= 2:
        draw.line(pts, fill=WHITE, width=8, joint="curve")
        draw.line(pts, fill=RED, width=5, joint="curve")
        for i in range(0, len(pts) - 1, 2):
            arrow(draw, pts[i], pts[i + 1], size=max(7, SCALE * .55))


def label(draw, xy, text, size=13, fg=WHITE, bg=INK, border=RED):
    f = font(size)
    box = draw.textbbox((0, 0), text, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    x, y = xy
    draw.rounded_rectangle([x - 4, y - 3, x + w + 4, y + h + 3], radius=4, fill=bg, outline=border, width=1)
    draw.text((x, y), text, font=f, fill=fg)
    return w + 8, h + 6


def draw_marker(img, x, y, x0, y0, text, size=13):
    draw = ImageDraw.Draw(img)
    px, py = (x - x0) * SCALE + SCALE // 2, (y - y0) * SCALE + SCALE // 2
    draw.ellipse([px - 8, py - 8, px + 8, py + 8], fill=RED, outline=WHITE, width=2)
    f = font(size)
    tw = draw.textlength(text, font=f)
    lx = px + 12 if px + tw + 20 < img.width else px - tw - 16
    ly = py - 10 if py > 64 else py + 14
    label(draw, (lx, ly), text, size=size)


def banner(img, title, subtitle):
    draw = ImageDraw.Draw(img)
    w = img.width
    draw.rectangle([0, 0, w, 46], fill=INK)
    draw.line([0, 46, w, 46], fill=RED, width=2)
    draw.text((10, 7), title, font=font(16), fill=WHITE)
    draw.text((10, 28), subtitle, font=font(12), fill=(200, 200, 208))


def chunks(points, max_points=24):
    if len(points) <= max_points:
        return [points]
    n = math.ceil(len(points) / max_points)
    size = math.ceil(len(points) / n)
    step = max(1, size - 3)
    out, i = [], 0
    while i < len(points):
        out.append(points[i:i + size])
        if i + size >= len(points):
            break
        i += step
    return out


def part_label(route, seg_index, segment, jump_from_idx=None, jump_to_idx=None):
    z = segment["z"]
    if route["kind"] == "walk":
        base = "Depot → destino"
    elif jump_from_idx is not None and seg_index <= jump_from_idx:
        base = "Depot → portal" if route["kind"] == "portal" else "Depot → barco"
    elif jump_to_idx is not None and seg_index >= jump_to_idx:
        base = "Llegada → destino"
    else:
        base = "Depot → destino"
    return f"{base} · piso z{z}"


def main() -> int:
    global MAP_PATH
    ap = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    ap.add_argument("--map", type=Path, default=MAP, help="OTBM a usar (por defecto test.otbm del repo)")
    args = ap.parse_args()
    MAP_PATH = args.map
    data = json.loads(ROUTES.read_text(encoding="utf-8"))
    routes = data["routes"]
    floors = load_map()
    rnd = Renderer()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}

    for route in routes:
        slug = route["slug"]
        rdir = OUT / slug
        rdir.mkdir(parents=True, exist_ok=True)
        for old in rdir.glob("*.jpg"):
            old.unlink()
        # armar todos los pasos antes de renderizar, para saber el total
        steps = []
        segments = route["segments"]
        jump_from_idx = jump_to_idx = None
        if route.get("jumps"):
            j = route["jumps"][0]
            for i, s in enumerate(segments):
                if jump_from_idx is None and s["z"] == j["from"][2] and s["points"][-1] == j["from"][:2]:
                    jump_from_idx = i
                if jump_to_idx is None and s["z"] == j["to"][2] and s["points"][0] == j["to"][:2]:
                    jump_to_idx = i
        for si, segment in enumerate(segments):
            for chunk in chunks(segment["points"]):
                steps.append((si, segment, chunk))
        total = len(steps)
        images = []
        for n, (si, segment, pts) in enumerate(steps, 1):
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            x0, x1 = max(0, min(xs) - MARGIN), min(511, max(xs) + MARGIN)
            y0, y1 = max(0, min(ys) - MARGIN), min(511, max(ys) + MARGIN)
            # tamaño mínimo para que entren el título y el contexto
            min_w, min_h = 40, 30
            cx, cy = (min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2
            if x1 - x0 + 1 < min_w:
                x0 = max(0, min(511 - min_w + 1, cx - min_w // 2))
                x1 = x0 + min_w - 1
            if y1 - y0 + 1 < min_h:
                y0 = max(0, min(511 - min_h + 1, cy - min_h // 2))
                y1 = y0 + min_h - 1
            img = rnd.crop(floors, segment["z"], x0, y0, x1, y1)
            draw_path(img, pts, x0, y0)
            part = part_label(route, si, segment, jump_from_idx, jump_to_idx)
            banner(img, f"Ruta desde el depot: {route['name']} — paso {n}/{total}",
                   f"{part} · flechas rojas = camino")
            # marcadores de la ruta que caen en esta imagen
            for m in route.get("markers", []):
                if m["z"] != segment["z"]:
                    continue
                if x0 <= m["x"] <= x1 and y0 <= m["y"] <= y1:
                    draw_marker(img, m["x"], m["y"], x0, y0, m["label"])
            name = f"{n:02d}-{part.split(' · ')[0].replace(' → ', '-').replace(' ', '-').lower()}.jpg"
            path = rdir / name
            img.save(path, quality=86, optimize=True)
            images.append({"file": f"{slug}/{name}", "caption": f"{route['name']}: {part}",
                           "z": segment["z"], "step": n})
        manifest[slug] = images
        print(f"{slug}: {total} imágenes")

    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"OK {OUT}: {sum(len(v) for v in manifest.values())} imágenes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
