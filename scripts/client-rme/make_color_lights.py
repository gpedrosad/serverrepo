#!/usr/bin/env python3.11
"""Luces de colores para las casas: candelabro (2042) y lámpara (2045) encendidos, con la llama recoloreada.

Cada base es 1x1 con 2 cuadros de animación. En el candelabro solo cambia la llama: los píxeles cálidos que
cambian entre los 2 cuadros y los cálidos muy brillantes pegados a ellos (la cruz dorada del cuerpo no). En la
lámpara todo el vidrio cálido toma el color, como un farol. Se conserva el brillo de cada píxel. add_custom_items.py los instala con frames=2, light=(nivel, color) y
nodecay=True (las bases se apagan solas a los 180 s; estas quedan siempre encendidas).

  python3.11 scripts/client-rme/make_color_lights.py [--preview /tmp/luces.png]
Doc: docs/gameplay/HANGABLES.md (sección Luces de colores).
"""
from __future__ import annotations

import argparse
import colorsys
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts/map/kb"))
import mapdata  # noqa: E402

OUT = ROOT / "devtools" / "zagan-test" / "custom-sprites"
# nombre del PNG -> (item base, tono de la llama 0..1)
LIGHTS = {
    "blue_candelabrum": (2042, 0.60),
    "green_candelabrum": (2042, 0.33),
    "violet_candelabrum": (2042, 0.78),
    "magenta_lamp": (2045, 0.88),
    "cyan_lamp": (2045, 0.52),
}


def base_frames(item: int) -> list[Image.Image]:
    r = mapdata.Renderer()
    e = r.entry(item)
    frames = []
    for sid in e["sprites"]:
        im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        px = r.spr.pixels(sid)
        for y in range(32):
            for x in range(32):
                if px[y][x]:
                    im.putpixel((x, y), (*px[y][x], 255))
        frames.append(im)
    return frames


def recolor(frames: list[Image.Image], hue: float, whole_glass: bool) -> list[Image.Image]:
    out = []
    for k, im in enumerate(frames):
        other = frames[1 - k] if len(frames) == 2 else im

        def warm(x, y, img=im):
            p = img.getpixel((x, y))
            if not p[3]:
                return None
            h, s, v = colorsys.rgb_to_hsv(p[0] / 255, p[1] / 255, p[2] / 255)
            return (h, s, v) if (h < 0.2 or h > 0.95) and s > 0.3 else None

        changed = {(x, y) for y in range(32) for x in range(32)
                   if im.getpixel((x, y))[3] and im.getpixel((x, y)) != other.getpixel((x, y)) and warm(x, y)}
        new = im.copy()
        for y in range(32):
            for x in range(32):
                hsv = warm(x, y)
                if not hsv:
                    continue
                h, s, v = hsv
                near = any((x + dx, y + dy) in changed for dx in (-1, 0, 1) for dy in (-1, 0, 1))
                flame = whole_glass or (x, y) in changed or (near and v > 0.8)
                if flame:
                    r, g, b = colorsys.hsv_to_rgb(hue, max(0.55, s), min(1.0, v * 1.05))
                    new.putpixel((x, y), (int(r * 255), int(g * 255), int(b * 255), 255))
        out.append(new)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    cache, sheets = {}, []
    for name, (item, hue) in LIGHTS.items():
        frames = recolor(cache.setdefault(item, base_frames(item)), hue, whole_glass=(item == 2045))
        stack = Image.new("RGBA", (32, 32 * len(frames)), (0, 0, 0, 0))
        for i, f in enumerate(frames):
            stack.paste(f, (0, 32 * i))
        stack.save(OUT / f"{name}.png")
        sheets.append(stack)
        print(f"OK {OUT / (name + '.png')}")
    if a.preview:
        prev = Image.new("RGBA", (len(sheets) * 40 + 80, 72), (40, 40, 46, 255))
        for i, item in enumerate((2042, 2045)):
            prev.alpha_composite(cache[item][0], (i * 40, 0))
        for i, s in enumerate(sheets):
            prev.alpha_composite(s.crop((0, 0, 32, 32)), (80 + i * 40, 0))
            prev.alpha_composite(s.crop((0, 32, 32, 64)), (80 + i * 40, 36))
        prev.resize((prev.width * 5, prev.height * 5), Image.NEAREST).save(a.preview)
    return 0


if __name__ == "__main__":
    sys.exit(main())
