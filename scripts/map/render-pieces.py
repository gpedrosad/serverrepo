#!/usr/bin/env python3
"""Dibuja piezas de mapa con los sprites reales, para mirarlas ANTES de usarlas en un generador.

Muchos muebles de 7.6 son varias piezas (un ataúd son dos ids) o tienen un id por dirección (sillas). Con
solo el nombre del .otb no se sabe: hay que mirarlos. Ver docs/items-and-map/PIEZAS_DE_MAPA.md.

  python3.11 scripts/map/render-pieces.py --sheet /tmp/hoja.png 1410 1411 1412 1650-1657
      hoja con cada id suelto y su número (rangos con guion)
  python3.11 scripts/map/render-pieces.py --scene /tmp/escena.png "431 1410;431 1412" "431 1411;431 1411"
      escena: cada argumento es una fila; las casillas se separan con ';' y cada casilla es
      "suelo id id..." (así se prueba cómo queda una pieza junto a otra)
  python3.11 scripts/map/render-pieces.py --furniture docs/items-and-map/img/piezas-de-mapa.png
      la escena de referencia del doc (ataúdes, sarcófagos, sillas, tronos, mesas y bancos)
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "kb"))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from game_render import LAYER_RANK, Sprites, compose, layer_of, parse_dat_all  # noqa: E402
from mapdata import load_otb  # noqa: E402

STONE, WOOD = 431, 405
# escena de referencia: (título, filas de casillas)
FURNITURE = [
    ("Ataúd: cabecera (1410, o con gema 1412/1413/1414) + pie 1411 abajo. Sarcófago: 1417 + 1418 abajo, o 1419 + 1420 a la derecha",
     [[[STONE], [STONE, 1410], [STONE], [STONE, 1412], [STONE], [STONE, 1413], [STONE], [STONE, 1414], [STONE], [STONE, 1417], [STONE], [STONE, 1419], [STONE, 1420], [STONE]],
      [[STONE], [STONE, 1411], [STONE], [STONE, 1411], [STONE], [STONE, 1411], [STONE], [STONE, 1411], [STONE], [STONE, 1418], [STONE], [STONE], [STONE], [STONE]]]),
    ("Sillas: 1652 mira al sur, 1650 al norte, 1651 al este, 1653 al oeste. Mesas enteras: 1614 grande, 1615 chica, 1616 redonda, 1619 mesita",
     [[[WOOD], [WOOD, 1652], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD]],
      [[WOOD, 1651], [WOOD, 1614], [WOOD, 1653], [WOOD], [WOOD, 1652], [WOOD, 1651], [WOOD, 1650], [WOOD, 1653], [WOOD], [WOOD, 1615], [WOOD], [WOOD, 1616], [WOOD], [WOOD, 1619]],
      [[WOOD], [WOOD, 1650], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD]]]),
    ("Tronos: morado 1654 (mira al sur), 1655, 1656, 1657; marrón 1646-1649. Banco: 1662 + 1663 a la derecha; a lo largo: 1664 + 1665 abajo",
     [[[WOOD], [WOOD, 1654], [WOOD], [WOOD, 1655], [WOOD], [WOOD, 1656], [WOOD], [WOOD, 1657], [WOOD], [WOOD, 1662], [WOOD, 1663], [WOOD], [WOOD, 1664], [WOOD]],
      [[WOOD], [WOOD, 1646], [WOOD], [WOOD, 1647], [WOOD], [WOOD, 1648], [WOOD], [WOOD, 1649], [WOOD], [WOOD], [WOOD], [WOOD], [WOOD, 1665], [WOOD]]]),
]


class Painter:
    def __init__(self):
        self.otb = load_otb()
        items, _outfits = parse_dat_all()
        self.entry = {sid: items.get(e.get("cid")) for sid, e in self.otb.items() if e.get("cid")}
        self.spr = Sprites()

    def scene(self, rows, scale=3, labels=True) -> Image.Image:
        h, w = len(rows), max(len(r) for r in rows)
        canvas = Image.new("RGBA", (w * 32 + 64, h * 32 + 64), (30, 30, 36, 255))
        for ty, row in enumerate(rows):
            for tx, its in enumerate(row):
                draw = []
                for sid in its:
                    e = self.entry.get(sid)
                    if e:
                        draw.append((LAYER_RANK[layer_of(e)], compose(e, self.spr, tx % e["px"], ty % e["py"]), e))
                draw.sort(key=lambda d: d[0])
                elev = 0
                for _r, im, e in draw:
                    dx = dy = 0
                    if 0x18 in e["flags"]:
                        dx, dy = struct.unpack("<HH", e["flags"][0x18])
                    canvas.paste(im, (tx * 32 - (e["w"] - 1) * 32 - dx - elev + 32, ty * 32 - (e["h"] - 1) * 32 - dy - elev + 32), im)
                    if 0x19 in e["flags"]:
                        elev = min(24, elev + struct.unpack("<H", e["flags"][0x19])[0])
        canvas = canvas.crop((32, 32, 32 + w * 32, 32 + h * 32)).resize((w * 32 * scale, h * 32 * scale), Image.NEAREST)
        if labels:
            d = ImageDraw.Draw(canvas)
            font = ImageFont.load_default()
            for ty, row in enumerate(rows):
                for tx, its in enumerate(row):
                    if len(its) > 1:
                        text = ",".join(str(i) for i in its[1:])
                        x, y = tx * 32 * scale + 3, ty * 32 * scale + 3
                        d.rectangle((x - 2, y - 1, x + 6 * len(text) + 2, y + 11), fill=(0, 0, 0, 190))
                        d.text((x, y), text, fill=(255, 255, 120), font=font)
        return canvas.convert("RGB")


def parse_ids(args) -> list[int]:
    out = []
    for a in args:
        if "-" in a:
            lo, hi = a.split("-")
            out += list(range(int(lo), int(hi) + 1))
        else:
            out.append(int(a))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", type=Path)
    ap.add_argument("--scene", type=Path)
    ap.add_argument("--furniture", type=Path)
    ap.add_argument("--floor", type=int, default=WOOD, help="suelo de la hoja (--sheet)")
    ap.add_argument("spec", nargs="*")
    a = ap.parse_args()
    p = Painter()
    if a.sheet:
        ids = parse_ids(a.spec)
        rows, cols = [], 8
        for i in range(0, len(ids), cols):
            row = []
            for sid in ids[i:i + cols]:
                row += [[a.floor, sid], [a.floor]]
            rows += [row, [[a.floor]] * len(row)]
        p.scene(rows).save(a.sheet)
        print(a.sheet)
    if a.scene:
        rows = [[[int(x) for x in cell.split()] for cell in row.split(";")] for row in a.spec]
        p.scene(rows).save(a.scene)
        print(a.scene)
    if a.furniture:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 17) \
            if Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf").exists() else ImageFont.load_default()
        parts = [(title, p.scene(rows)) for title, rows in FURNITURE]
        width = max(im.width for _t, im in parts)
        sheet = Image.new("RGB", (width + 20, sum(im.height + 44 for _t, im in parts) + 10), (24, 24, 30))
        d, y = ImageDraw.Draw(sheet), 10
        for title, im in parts:
            d.text((10, y), title, font=font, fill=(255, 226, 120))
            sheet.paste(im, (10, y + 28))
            y += im.height + 44
        sheet.save(a.furniture)
        print(a.furniture)
    return 0


if __name__ == "__main__":
    sys.exit(main())
