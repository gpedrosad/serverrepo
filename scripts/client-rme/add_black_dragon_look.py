#!/usr/bin/env python3
"""Agrega el look del Black Dragon (looktype 230) a un par Tibia.dat / Tibia.spr 7.6.

Copia la estructura del Dragon (looktype 34: 2x2 tiles, 4 direcciones, 3 cuadros) al
looktype vacío 230 con sus 48 sprites recoloreados a negro con brillo violeta y ojos rojos.
El recoloreado es por píxel: conserva exacto el pixel art original.

Uso:
  python3 scripts/client-rme/add_black_dragon_look.py DIR_THINGS [--preview salida.png]

DIR_THINGS es la carpeta con Tibia.dat y Tibia.spr; se modifican en el lugar (con copia
.bak-blackdragon). Hay que aplicarlo a:
  - devtools/rme/rme-client-760/            (RME, versionado en git)
  - client-local/data/things/760/            (base de build_zagan_test_assets.py)
  - el cliente que se reparte a los jugadores (updater), si no se regenera desde la base.
Es idempotente: si el looktype 230 ya tiene sprites, no hace nada.
Ver docs/gameplay/BLACK_DRAGON.md.
"""
from __future__ import annotations

import argparse
import colorsys
import shutil
import struct
import sys
import zlib
from pathlib import Path

SOURCE_LOOK = 34   # Dragon
TARGET_LOOK = 230  # vacío en el cliente 7.6; el protocolo 7.6 manda el looktype en 1 byte (máx. 255)
THING_LAST_ATTR = 0xFF


# ---------- Tibia.dat ----------

def _skip_attr(data: bytes, pos: int, attr: int) -> int:
    if attr in (0, 8, 9, 25, 28, 29, 32, 34):
        return pos + 2
    if attr in (21, 24):
        return pos + 4
    if attr == 33:
        pos += 6
        name_len = struct.unpack_from("<H", data, pos)[0]
        return pos + 2 + name_len + 4
    return pos


def _read_thing(data: bytes, pos: int) -> dict:
    start = pos
    while True:
        attr = data[pos]
        pos += 1
        if attr == THING_LAST_ATTR:
            break
        if attr == 23:  # 7.55+: floor change
            attr = 252
        pos = _skip_attr(data, pos, attr)
    width, height = data[pos], data[pos + 1]
    pos += 2
    if width > 1 or height > 1:
        pos += 1  # exact size
    layers, pat_x, pat_y, pat_z, anim = data[pos:pos + 5]
    pos += 5
    total = width * height * layers * pat_x * pat_y * pat_z * anim
    sprite_pos = pos
    ids = list(struct.unpack_from(f"<{total}H", data, pos))
    pos += 2 * total
    return {"start": start, "sprite_pos": sprite_pos, "end": pos, "ids": ids}


def read_outfits(data: bytes) -> tuple[list[dict], tuple[int, int, int, int]]:
    _sig, items, outfits, effects, missiles = struct.unpack_from("<IHHHH", data, 0)
    pos = 12
    for _ in range(items - 99):  # los ítems van del id 100 al 'items'
        pos = _read_thing(data, pos)["end"]
    result = []
    for _ in range(outfits):
        thing = _read_thing(data, pos)
        result.append(thing)
        pos = thing["end"]
    for _ in range(effects + missiles):
        pos = _read_thing(data, pos)["end"]
    if pos != len(data):
        raise SystemExit(f"Tibia.dat no se leyó completo ({pos} de {len(data)} bytes): formato inesperado")
    return result, (items, outfits, effects, missiles)


# ---------- Tibia.spr ----------

def read_spr(data: bytes) -> tuple[int, list[int]]:
    count = struct.unpack_from("<H", data, 4)[0]
    return count, [struct.unpack_from("<I", data, 6 + i * 4)[0] for i in range(count)]


def decode_sprite(data: bytes, offsets: list[int], sprite_id: int) -> list[tuple[int, int, int, int]]:
    pixels = [(0, 0, 0, 0)] * 1024
    if sprite_id == 0 or offsets[sprite_id - 1] == 0:
        return pixels
    off = offsets[sprite_id - 1]
    size = struct.unpack_from("<H", data, off + 3)[0]
    pos, end, i = off + 5, off + 5 + size, 0
    while pos < end and i < 1024:
        transparent, colored = struct.unpack_from("<HH", data, pos)
        pos += 4
        i += transparent
        for _ in range(colored):
            if i >= 1024:
                break
            pixels[i] = (data[pos], data[pos + 1], data[pos + 2], 255)
            pos += 3
            i += 1
    return pixels


def encode_sprite(pixels: list[tuple[int, int, int, int]]) -> bytes:
    payload = bytearray()
    i, total = 0, len(pixels)
    while i < total:
        transparent = 0
        while i < total and pixels[i][3] == 0:
            transparent += 1
            i += 1
        colored = bytearray()
        while i < total and pixels[i][3] != 0:
            colored += bytes(pixels[i][:3])
            i += 1
        if not colored and i >= total:
            break
        payload += struct.pack("<HH", transparent, len(colored) // 3) + colored
    return b"\xff\x00\xff" + struct.pack("<H", len(payload)) + bytes(payload)


def write_spr(signature: int, offsets: list[int], original: bytes, new_records: list[bytes]) -> bytes:
    old_count = len(offsets)
    new_count = old_count + len(new_records)
    if new_count > 0xFFFF:
        raise SystemExit("Tibia.spr se pasaría del máximo de 65535 sprites")
    shift = 4 * len(new_records)
    old_payload_start = 6 + 4 * old_count
    out = bytearray(struct.pack("<IH", signature, new_count))
    for off in offsets:
        out += struct.pack("<I", off + shift if off else 0)
    tail = 6 + 4 * new_count + (len(original) - old_payload_start)
    for record in new_records:
        out += struct.pack("<I", tail)
        tail += len(record)
    out += original[old_payload_start:]
    for record in new_records:
        out += record
    return bytes(out)


# ---------- recoloreado ----------

def recolor(pixel: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    r, g, b, a = pixel
    if a == 0:
        return pixel
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if (h < 0.09 or h > 0.95) and s > 0.6 and v > 0.5:  # ojos y lengua
        return (235, 40, 30, 255)
    k = ((0.30 * r + 0.59 * g + 0.11 * b) / 255) ** 0.85
    return (int(14 + 120 * k), int(10 + 104 * k), int(22 + 160 * k), 255)


def write_preview(path: Path, frames: list[list[tuple[int, int, int, int]]], scale: int = 3, size: int = 64) -> None:
    """Grilla 4 direcciones x 3 cuadros; cada cuadro de size x size (64 = 2x2 sprites, 32 = 1x1)."""
    cols, rows = 4, 3
    width, height = cols * size * scale, rows * size * scale
    canvas = [(60, 60, 70)] * (width * height)
    for index, frame in enumerate(frames):
        cx, cy = (index % cols) * size * scale, (index // cols) * size * scale
        for y in range(size):
            for x in range(size):
                p = frame[y * size + x]
                if p[3]:
                    for dy in range(scale):
                        row = (cy + y * scale + dy) * width + cx + x * scale
                        for dx in range(scale):
                            canvas[row + dx] = p[:3]
    raw = b"".join(b"\x00" + bytes(c for px in canvas[r * width:(r + 1) * width] for c in px) for r in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("things_dir", type=Path)
    ap.add_argument("--preview", type=Path)
    args = ap.parse_args()

    dat_path, spr_path = args.things_dir / "Tibia.dat", args.things_dir / "Tibia.spr"
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    outfits, counts = read_outfits(dat)
    if counts[1] < TARGET_LOOK:
        raise SystemExit(f"El dat tiene {counts[1]} looktypes; se esperaba al menos {TARGET_LOOK}")
    source, target = outfits[SOURCE_LOOK - 1], outfits[TARGET_LOOK - 1]
    if any(target["ids"]):
        print(f"El looktype {TARGET_LOOK} ya tiene sprites; no se cambia nada.")
        return

    spr_signature = struct.unpack_from("<I", spr, 0)[0]
    spr_count, offsets = read_spr(spr)

    # Recolorea los 48 sprites del Dragon. Los ids nuevos van al final del .spr.
    new_records, new_ids, decoded = [], [], {}
    for sid in source["ids"]:
        pixels = [recolor(p) for p in decode_sprite(spr, offsets, sid)]
        decoded[len(new_ids)] = pixels
        new_records.append(encode_sprite(pixels))
        new_ids.append(spr_count + len(new_records))

    # Entrada nueva del dat: misma cabecera que el Dragon, ids nuevos.
    entry = dat[source["start"]:source["sprite_pos"]] + struct.pack(f"<{len(new_ids)}H", *new_ids)
    new_dat = dat[:target["start"]] + entry + dat[target["end"]:]
    new_spr = write_spr(spr_signature, offsets, spr, new_records)

    # Comprobación: el dat nuevo se lee completo y el look 230 apunta a los sprites nuevos.
    check, _ = read_outfits(new_dat)
    assert check[TARGET_LOOK - 1]["ids"] == new_ids

    for path, data in ((dat_path, new_dat), (spr_path, new_spr)):
        backup = path.with_name(path.name + ".bak-blackdragon")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_bytes(data)
    print(f"Looktype {TARGET_LOOK} = Black Dragon; sprites {new_ids[0]}-{new_ids[-1]} agregados "
          f"({spr_count} -> {spr_count + len(new_records)}).")

    if args.preview:
        # Sprite index en el dat: anim, dirección (pattern x), luego 2x2 tiles empezando por abajo-derecha.
        frames = []
        for anim in range(3):
            for direction in range(4):
                frame = [(0, 0, 0, 0)] * (64 * 64)
                base = (anim * 4 + direction) * 4
                for tile in range(4):
                    pixels = decoded[base + tile]
                    ox, oy = (1 - tile % 2) * 32, (1 - tile // 2) * 32
                    for i, p in enumerate(pixels):
                        if p[3]:
                            frame[(oy + i // 32) * 64 + ox + i % 32] = p
                frames.append(frame)
        write_preview(args.preview, frames)
        print(f"Vista previa: {args.preview}")


if __name__ == "__main__":
    sys.exit(main())
