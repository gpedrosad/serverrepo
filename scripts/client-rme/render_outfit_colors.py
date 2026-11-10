#!/usr/bin/env python3
"""Renderiza una vista previa de un outfit 7.6 con colores head/body/legs/feet.

No modifica Tibia.dat ni Tibia.spr: solo lee el looktype y aproxima la
colorización del cliente 7.6 (los píxeles de cada canal se multiplican por el
color de la paleta elegido). Sirve para elegir paletas de variantes de monstruos
humanoides sin crear un looktype nuevo ni tocar el cliente.

La paleta es la tabla clásica de 133 colores de outfit de Tibia 7.6:
0=FFFFFF, 33=AF8FBF (violeta apagado), 68=3F6ABF (azul acero),
106=003FBF (azul real profundo), 124=00547F (azul verdoso oscuro), etc.

Uso:
  python3 scripts/client-rme/render_outfit_colors.py \
      --looktype 63 --colors 33,106,68,124 \
      --preview docs/gameplay/img/blue-elf-arcanist.png

  # Solo 1x1 (12 sprites: 4 direcciones x 3 cuadros). Para 2x2 (48 sprites)
  # también compone los 4 tiles de cada cuadro.
"""
from __future__ import annotations

import argparse
import colorsys
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from add_black_dragon_look import decode_sprite, read_outfits, read_spr  # noqa: E402

RME_THINGS = HERE.parents[1] / "devtools/rme/rme-client-760"

# Paleta clásica de outfits 7.6 (133 colores). Índice = valor de head/body/legs/feet.
PALETTE = [
    "FFFFFF", "FFD4BF", "FFE9BF", "FFFFBF", "E9FFBF", "D4FFBF", "BFFFBF", "BFFFD4",
    "BFFFE9", "BFFFFF", "BFE9FF", "BFD4FF", "BFBFFF", "D4BFFF", "E9BFFF", "FFBFFF",
    "FFBFE9", "FFBFD4", "FFBFBF", "DADADA", "BF9F8F", "BFAF8F", "BFBF8F", "AFBF8F",
    "9FBF8F", "8FBF8F", "8FBF9F", "8FBFAF", "8FBFBF", "8FAFBF", "8F9FBF", "8F8FBF",
    "9F8FBF", "AF8FBF", "BF8FBF", "BF8FAF", "BF8F9F", "BF8F8F", "B6B6B6", "BF7F5F",
    "BFAF8F", "BFBF5F", "9FBF5F", "7FBF5F", "5FBF5F", "5FBF7F", "5FBF9F", "5FBFBF",
    "5F9FBF", "5F7FBF", "5F5FBF", "7F5FBF", "9F5FBF", "BF5FBF", "BF5F9F", "BF5F7F",
    "BF5F5F", "919191", "BF6A3F", "BF943F", "BFBF3F", "94BF3F", "6ABF3F", "3FBF3F",
    "3FBF6A", "3FBF94", "3FBFBF", "3F94BF", "3F6ABF", "3F3FBF", "6A3FBF", "943FBF",
    "BF3FBF", "BF3F94", "BF3F6A", "BF3F3F", "6D6D6D", "FF5500", "FFAA00", "FFFF00",
    "AAFF00", "54FF00", "00FF00", "00FF54", "00FFAA", "00FFFF", "00A9FF", "0055FF",
    "0000FF", "5500FF", "A900FF", "FE00FF", "FF00AA", "FF0055", "FF0000", "484848",
    "BF3F00", "BF7F00", "BFBF00", "7FBF00", "3FBF00", "00BF00", "00BF3F", "00BF7F",
    "00BFBF", "007FBF", "003FBF", "0000BF", "3F00BF", "7F00BF", "BF00BF", "BF007F",
    "BF003F", "BF0000", "242424", "7F2A00", "7F5500", "7F7F00", "557F00", "2A7F00",
    "007F00", "007F2A", "007F55", "007F7F", "00547F", "002A7F", "00007F", "2A007F",
    "54007F", "7F007F", "7F0055", "7F002A", "7F0000",
]


def palette_color(index: int) -> tuple[int, int, int]:
    if not 0 <= index < len(PALETTE):
        raise SystemExit(f"Color {index} fuera de la paleta 7.6 (0-{len(PALETTE) - 1})")
    c = PALETTE[index]
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def classify(r: int, g: int, b: int) -> str:
    """Canal de outfit según el color del sprite plantilla.

    En los outfits 7.6 el rojo es body, el amarillo/dorado head, el verde legs
    y el azul feet. Piel y blancos/grises quedan fijos.
    """
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if v < 0.10:
        return "black"
    if s < 0.16:
        return "fixed"
    if (h < 0.045 or h > 0.96) and s > 0.55:
        return "body"
    if 0.08 < h < 0.18 and s > 0.45:
        return "head"
    if 0.24 < h < 0.45 and s > 0.4:
        return "legs"
    if 0.5 < h < 0.78 and s > 0.4:
        return "feet"
    if 0.04 < h < 0.09 and s < 0.55:
        return "skin"
    if 0.03 < h < 0.12 and s >= 0.55:
        return "head"
    return "fixed"


def colorize_pixel(pixel: tuple[int, int, int, int], colors: dict[str, tuple[int, int, int]]) -> tuple[int, int, int, int]:
    r, g, b, a = pixel
    if not a:
        return pixel
    kind = classify(r, g, b)
    if kind in ("black", "fixed", "skin"):
        return pixel
    base = colors[kind]
    value = max(r, g, b) / 255
    # Sombra mínima para no perder detalle sobre fondos oscuros.
    k = 0.30 + 0.70 * (value ** 0.85)
    return (
        min(255, int(base[0] * k)),
        min(255, int(base[1] * k)),
        min(255, int(base[2] * k)),
        255,
    )


def frames_1x1(decoded: list[list[tuple[int, int, int, int]]]) -> list[list[tuple[int, int, int, int]]]:
    """12 sprites en orden anim -> dirección, cada uno 32x32."""
    if len(decoded) != 12:
        raise SystemExit(f"Se esperaban 12 sprites 1x1 y hay {len(decoded)}")
    return decoded


def frames_2x2(decoded: list[list[tuple[int, int, int, int]]]) -> list[list[tuple[int, int, int, int]]]:
    """48 sprites en orden anim -> dirección -> tile 2x2 (abajo-derecha primero)."""
    if len(decoded) != 48:
        raise SystemExit(f"Se esperaban 48 sprites 2x2 y hay {len(decoded)}")
    frames = []
    for anim in range(3):
        for direction in range(4):
            frame = [(0, 0, 0, 0)] * (64 * 64)
            base = (anim * 4 + direction) * 4
            for tile in range(4):
                ox, oy = (1 - tile % 2) * 32, (1 - tile // 2) * 32
                for i, p in enumerate(decoded[base + tile]):
                    if p[3]:
                        frame[(oy + i // 32) * 64 + ox + i % 32] = p
            frames.append(frame)
    return frames


def write_png(path: Path, width: int, height: int, canvas: list[tuple[int, int, int]]) -> None:
    raw = b"".join(
        b"\x00" + bytes(c for px in canvas[r * width:(r + 1) * width] for c in px)
        for r in range(height)
    )

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--looktype", type=int, default=63)
    ap.add_argument("--colors", required=True, help="head,body,legs,feet (índices 0-132), ej. 33,106,68,124")
    ap.add_argument("--preview", type=Path, required=True)
    ap.add_argument("--things", type=Path, default=RME_THINGS)
    ap.add_argument("--scale", type=int, default=6)
    a = ap.parse_args()

    try:
        indices = [int(x.strip()) for x in a.colors.split(",")]
    except ValueError:
        raise SystemExit("--colors debe ser head,body,legs,feet con números enteros")
    if len(indices) != 4:
        raise SystemExit("--colors debe tener exactamente 4 valores: head,body,legs,feet")
    colors = {
        "head": palette_color(indices[0]),
        "body": palette_color(indices[1]),
        "legs": palette_color(indices[2]),
        "feet": palette_color(indices[3]),
    }

    dat = (a.things / "Tibia.dat").read_bytes()
    spr = (a.things / "Tibia.spr").read_bytes()
    outfits, counts = read_outfits(dat)
    if not 1 <= a.looktype <= counts[1]:
        raise SystemExit(f"Looktype {a.looktype} fuera de rango (1-{counts[1]})")
    outfit = outfits[a.looktype - 1]
    _, offsets = read_spr(spr)
    decoded = [decode_sprite(spr, offsets, sid) for sid in outfit["ids"]]
    decoded = [[colorize_pixel(p, colors) for p in frame] for frame in decoded]

    if len(outfit["ids"]) == 12:
        frames, size = frames_1x1(decoded), 32
    elif len(outfit["ids"]) == 48:
        frames, size = frames_2x2(decoded), 64
    else:
        raise SystemExit(f"Looktype {a.looktype} tiene {len(outfit['ids'])} sprites; solo se soportan 12 (1x1) o 48 (2x2)")

    cols, rows = 4, 3
    width, height = cols * size * a.scale, rows * size * a.scale
    canvas = [(40, 40, 48)] * (width * height)
    for index, frame in enumerate(frames):
        cx, cy = (index % cols) * size * a.scale, (index // cols) * size * a.scale
        for y in range(size):
            for x in range(size):
                p = frame[y * size + x]
                if p[3]:
                    for dy in range(a.scale):
                        row = (cy + y * a.scale + dy) * width
                        for dx in range(a.scale):
                            canvas[row + cx + x * a.scale + dx] = p[:3]

    a.preview.parent.mkdir(parents=True, exist_ok=True)
    write_png(a.preview, width, height, canvas)
    print(f"Looktype {a.looktype}: head={indices[0]} body={indices[1]} legs={indices[2]} feet={indices[3]}")
    print(f"Vista previa: {a.preview} ({width}x{height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
