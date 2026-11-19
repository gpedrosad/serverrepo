#!/usr/bin/env python3
"""Calavera cian con el dibujo exacto de skull_red.png, sin redibujar píxeles.

  python3.11 scripts/client-rme/recolor_cyan_skull.py --client RUTA_CLIENTERETRO

Conserva máscara, contorno, ojos y sombreado originales. Solo transforma el rojo
en cian (#FF0000 -> #00E5FF); grises/blancos/negros y alpha quedan iguales.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'devtools/zagan-test/custom-sprites/depot-electric'


def recolor(source: Image.Image) -> Image.Image:
    source = source.convert('RGBA')
    if source.size != (11, 11):
        raise ValueError(f'La calavera original debe medir 11x11, no {source.size}')
    if any(a and (g != b or r < g) for r, g, b, a in source.getdata()):
        raise ValueError('La base debe usar la paleta roja original')
    out = Image.new('RGBA', source.size)
    out.putdata([(r, g, b, a) if not a else
                 (g, g + round((r - g) * 229 / 255), r, a)
                 for r, g, b, a in source.getdata()])
    assert out.getchannel('A').tobytes() == source.getchannel('A').tobytes()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--client', type=Path, required=True)
    args = ap.parse_args()
    rel = Path('data/images/game/skulls')
    source = Image.open(args.client / 'mac' / rel / 'skull_red.png').convert('RGBA')
    windows = Image.open(args.client / 'windows' / rel / 'skull_red.png').convert('RGBA')
    if source.tobytes() != windows.tobytes():
        raise SystemExit('Las calaveras rojas base de Mac/Windows son distintas')
    result = recolor(source)
    ART.mkdir(parents=True, exist_ok=True)
    source.save(ART / 'skull-template-red.png')
    result.save(ART / 'skull_cyan.png')
    for platform in ('mac', 'windows'):
        result.save(args.client / platform / rel / 'skull_cyan.png')
    print('OK: cian 11x11, máscara exacta de la roja y paridad Mac/Windows')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
