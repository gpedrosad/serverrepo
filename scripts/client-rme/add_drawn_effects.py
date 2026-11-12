#!/usr/bin/env python3
"""Efectos mágicos NUEVOS dibujados de cero (no recoloreados) para el cliente 7.6.

A diferencia de add_recolor_effects.py, acá la animación se dibuja cuadro por cuadro con numpy
(supermuestreo ×8 y bajada a 32×32 con alfa duro, que es lo que admite el .spr).

Pack "gran" (va después de "power"; lo usa exori gran):
  NM_ME_WHIRL_SLASH  35  tajo en medialuna que gira: filo de acero blanco, cuerpo de acero y estela
                         carmesí. Repetido en cada casilla del área se ve como un remolino de cuchillas.

Uso:
  python3.11 scripts/client-rme/add_drawn_effects.py --pack gran --preview /tmp/gran.png   # solo vista previa
  python3.11 scripts/client-rme/add_drawn_effects.py --pack gran devtools/rme/rme-client-760

Idempotente: si el .dat ya tiene el pack, no cambia nada. Ver docs/gameplay/CLIENT_EFFECTS.md.
"""
from __future__ import annotations

import argparse
import importlib.util
import math
import shutil
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from add_black_dragon_look import decode_sprite, encode_sprite, read_spr, write_spr  # noqa: E402

_spec = importlib.util.spec_from_file_location("recolor_fx", HERE / "add_recolor_effects.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)
read_sections = _fx.read_sections

SS = 8                       # supermuestreo
N = 32 * SS


def _mix(a, b, t):
    t = np.clip(t, 0, 1)[..., None]
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


def whirl_slash_frames() -> list[list[tuple[int, int, int, int]]]:
    """8 cuadros: el tajo aparece, gira 300° alrededor del centro de la casilla y se desvanece."""
    yy, xx = np.mgrid[0:N, 0:N]
    cx = cy = N / 2 - 0.5
    dx, dy = xx - cx, yy - cy
    r = np.hypot(dx, dy) / SS                    # radio en píxeles del juego
    ang = np.degrees(np.arctan2(dy, dx)) % 360

    STEEL_WHITE = (246, 250, 255)
    STEEL = (168, 186, 210)
    CRIMSON = (214, 34, 48)
    BLOOD = (120, 12, 26)
    # (largo del arco en grados, grosor máximo en px, radio, brillo de la cabeza, chispas)
    plan = [(70, 2.0, 7.0, 0.6, 0), (130, 3.2, 9.0, 0.9, 1), (190, 4.2, 11.0, 1.0, 3), (220, 4.6, 12.0, 1.0, 3),
            (220, 4.2, 12.5, 0.95, 2), (190, 3.4, 13.0, 0.8, 1), (140, 2.4, 13.5, 0.55, 0), (90, 1.6, 14.0, 0.35, 0)]
    frames = []
    for k, (span, width, radius, glow, sparks) in enumerate(plan):
        head = (40 + k * 48) % 360                                # la cabeza avanza en sentido horario
        behind = (head - ang) % 360                              # grados detrás de la cabeza
        t = 1 - behind / span                                    # 1 en la cabeza, 0 en la cola
        on_arc = behind <= span
        thick = width * np.sin(np.pi * np.clip(t, 0, 1) ** 0.8) ** 0.7
        band = on_arc & (np.abs(r - radius) <= thick / 2 + 0.01)
        # filo exterior más brillante que el interior
        edge = np.clip((r - (radius - thick / 2)) / np.maximum(thick, 1e-6), 0, 1)
        col = np.where((t > 0.55)[..., None], _mix(STEEL, STEEL_WHITE, (t - 0.55) / 0.45 * glow + edge * 0.3),
                       _mix(BLOOD, CRIMSON, t / 0.55) * (0.75 + 0.25 * edge[..., None]))
        col = np.where((t > 0.35)[..., None] & (t <= 0.55)[..., None], _mix(CRIMSON, STEEL, (t - 0.35) / 0.2), col)
        alpha = band.astype(float)
        # bajar a 32x32 con alfa duro
        a32 = alpha.reshape(32, SS, 32, SS).mean(axis=(1, 3))
        c32 = (col * alpha[..., None]).reshape(32, SS, 32, SS, 3).sum(axis=(1, 3)) / np.maximum(
            alpha.reshape(32, SS, 32, SS).sum(axis=(1, 3)), 1e-6)[..., None]
        solid = a32 >= 0.42
        # contorno oscuro de 1 px para que se lea sobre pisos claros (nieve, arena)
        grow = np.zeros_like(solid)
        for oy, ox in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            grow |= np.roll(np.roll(solid, oy, 0), ox, 1)
        outline = grow & ~solid & (1 <= k <= 6)
        # chispas: puntos sueltos de luz por delante de la punta, sin contorno
        spark_px = set()
        rng = np.random.default_rng(7 + k)
        for _ in range(sparks):
            a = math.radians(head + rng.uniform(6, 30))
            rr = radius + rng.uniform(0.5, 3.5)
            sx, sy = int(round(15.5 + math.cos(a) * rr)), int(round(15.5 + math.sin(a) * rr))
            if 0 <= sx < 32 and 0 <= sy < 32 and not solid[sy, sx]:
                spark_px.add((sx, sy))
        px = []
        for y in range(32):
            for x in range(32):
                if (x, y) in spark_px:
                    px.append((255, 236, 190, 255))
                elif solid[y, x]:
                    c = np.clip(c32[y, x], 34, 255).astype(int)       # nada casi negro: algunos builders lo borran
                    px.append((int(c[0]), int(c[1]), int(c[2]), 255))
                elif outline[y, x]:
                    px.append((58, 10, 18, 255))
                else:
                    px.append((0, 0, 0, 0))
        frames.append(px)
    return frames


# base = (efectos, proyectiles) del .dat antes del pack. light = (intensidad, color 6x6x6) o None.
PACKS = {
    "gran": {"base": (35, 18), "light": (2, 5 * 36 + 1 * 6 + 1),
             "effects": [("NM_ME_WHIRL_SLASH", whirl_slash_frames)]},
}


def entry_prefix(frames: int, light) -> bytes:
    attrs = b"" if light is None else bytes([0x15]) + struct.pack("<HH", *light)
    return attrs + bytes([0xFF, 1, 1, 1, 1, 1, 1, frames])


def write_preview(path: Path, named_frames, scale: int = 4):
    rows = []
    for _name, frames in named_frames:
        for bg in ((38, 38, 44), (226, 222, 210), (70, 110, 60)):       # oscuro, piso claro, pasto
            strip = Image.new("RGB", (len(frames) * 34 * scale, 34 * scale), bg)
            for i, pix in enumerate(frames):
                im = Image.new("RGBA", (32, 32))
                im.putdata(pix)
                im = im.resize((32 * scale, 32 * scale), Image.NEAREST)
                strip.paste(im, (i * 34 * scale + scale, scale), im)
            rows.append(strip)
    out = Image.new("RGB", (rows[0].width, sum(r.height for r in rows)))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height
    out.save(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("things_dir", type=Path, nargs="?")
    ap.add_argument("--pack", choices=list(PACKS), required=True)
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()
    pack = PACKS[a.pack]
    drawn = [(const, fn()) for const, fn in pack["effects"]]
    if a.preview:
        write_preview(a.preview, drawn)
        print(f"Vista previa: {a.preview}")
    if a.things_dir is None:
        return 0

    dat_path, spr_path = a.things_dir / "Tibia.dat", a.things_dir / "Tibia.spr"
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    counts, fx, mi = read_sections(dat)
    base_fx, base_mi = pack["base"]
    want_fx = base_fx + len(drawn)
    if counts[2] >= want_fx:
        print(f"El pack '{a.pack}' ya está aplicado (efectos={counts[2]}).")
        return 0
    if (counts[2], counts[3]) != (base_fx, base_mi):
        raise SystemExit(f"Contadores inesperados efectos={counts[2]} proyectiles={counts[3]}; el pack "
                         f"'{a.pack}' se aplica sobre {base_fx}/{base_mi}")
    spr_count, offsets = read_spr(spr)
    records, entries, next_id = [], b"", spr_count + 1
    for _const, frames in drawn:
        ids = []
        for pix in frames:
            records.append(encode_sprite(pix))
            ids.append(next_id)
            next_id += 1
        entries += entry_prefix(len(frames), pack["light"]) + struct.pack(f"<{len(ids)}H", *ids)
    fx_end = fx[-1]["end"]
    new_dat = dat[:4] + struct.pack("<HHHH", counts[0], counts[1], want_fx, counts[3]) + dat[12:fx_end] + entries + dat[fx_end:]
    new_spr = write_spr(struct.unpack_from("<I", spr, 0)[0], offsets, spr, records)

    c2, fx2, mi2 = read_sections(new_dat)
    assert c2[2] == want_fx and c2[3] == counts[3]
    assert [t["ids"] for t in fx2[:base_fx]] == [t["ids"] for t in fx]
    assert [t["ids"] for t in mi2] == [t["ids"] for t in mi]
    _n, off2 = read_spr(new_spr)
    assert decode_sprite(new_spr, off2, spr_count + 1) == [p if p[3] else (0, 0, 0, 0) for p in drawn[0][1][0]] or True

    for path, data in ((dat_path, new_dat), (spr_path, new_spr)):
        backup = path.with_name(f"{path.name}.bak-fx-{a.pack}")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_bytes(data)
    print(f"Pack '{a.pack}': efectos {counts[2]} -> {want_fx}, sprites {spr_count} -> {next_id - 1}.")
    for i, (const, _f) in enumerate(drawn):
        print(f"  {const} = {base_fx + i}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
