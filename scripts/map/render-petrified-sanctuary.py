#!/usr/bin/env python3
"""Vistas nativas del santuario y sus spawns; no requiere abrir el juego."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "kb")]
from mapdata import REPO, Renderer, load_tiles
from game_render import Sprites, creature_image, parse_dat_all

DATA = REPO / "server/YurOTS/ots/data"
OUT = REPO / "docs/items-and-map/img/petrified-sanctuary"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tiles = load_tiles()
    renderer = Renderer()
    _, outfits = parse_dat_all()
    spr = Sprites()
    registry = ET.parse(DATA / "monster/monsters.xml").getroot()
    looks = {}
    for m in registry:
        name = m.get("name")
        if name not in ("Gargoyle", "Stone Golem", "Crystal Spider", "Lake Custodian"):
            continue
        look = ET.parse(DATA / "monster" / m.get("file")).getroot().find("look")
        looks[name] = {k: int(v) for k, v in look.attrib.items() if k != "corpse"}
    monsters = []
    for spawn in ET.parse(DATA / "world/test-spawn.xml").getroot():
        x, y, z = [int(spawn.get(k, "0")) for k in ("centerx", "centery", "centerz")]
        for m in spawn:
            if m.get("name") in looks:
                monsters.append((m.get("name"), x + int(m.get("x", "0")), y + int(m.get("y", "0")), z))

    def view(box, z):
        x0, y0, x1, y1 = box
        render = renderer.client_view if z == 7 else renderer.area
        w, h, rgba = render(tiles, *box, z)
        im = Image.frombytes("RGBA", (w, h), bytes(rgba))
        for name, x, y, mz in sorted(monsters, key=lambda m: (m[2], m[1])):
            if mz != z or not (x0 <= x <= x1 and y0 <= y <= y1):
                continue
            actor = creature_image(looks[name], outfits, spr)
            im.alpha_composite(actor, ((x - x0 + 1) * 32 - actor.width, (y - y0 + 1) * 32 - actor.height))
        return im.convert("RGB")

    panels = [
        ("entrada", "Entrada en la orilla del lago", (85, 67, 103, 77), 7),
        ("galeria", "Galeria de las gargolas", (46, 72, 64, 82), 9),
        ("cristales", "Camaras de cristal", (45, 35, 63, 45), 9),
        ("custodio", "Lake Custodian", (16, 35, 34, 45), 9),
    ]
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
    small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    canvas = Image.new("RGB", (1264, 884), "#101c23")
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 12), "SANTUARIO PETRIFICADO", font=font, fill="#b7f4f4")
    draw.text((16, 43), "Mapa y criaturas con sus sprites reales · vista previa fuera del juego", font=small, fill="#9aadb7")
    for i, (name, title, box, z) in enumerate(panels):
        im = view(box, z)
        im.save(OUT / f"{name}.png")
        x, y = 16 + (i % 2) * 624, 80 + (i // 2) * 400
        draw.text((x, y), title, font=font, fill="#d7e3e9")
        canvas.paste(im, (x, y + 32))
    canvas.save(OUT / "santuario.png")
    view((14, 31, 102, 86), 9).resize((1424, 896), Image.Resampling.NEAREST).save(OUT / "recorrido.png")
    print(OUT / "santuario.png")


if __name__ == "__main__":
    main()
