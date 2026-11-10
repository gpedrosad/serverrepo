#!/usr/bin/env python3
"""Agrega efectos mágicos y proyectiles NUEVOS al cliente 7.6 recoloreando los existentes.

El servidor manda el efecto como `type + 1` en un byte (protocol76.cpp), así que admite hasta
255 efectos y 255 proyectiles; el Tibia.dat 7.6 base trae 25 y 15. Este script agrega entradas
al final de cada sección (sube los contadores del encabezado del .dat) con sprites recoloreados:
la animación y los patrones quedan idénticos a la original.

Pack "ice" (constantes Lua en data/spells/lib/spells.lua):
  NM_ME_ICE_AREA       25  <- fuego en área (NM_ME_FIRE_AREA)
  NM_ME_ICE_HIT        26  <- llamarada (NM_ME_HITBY_FIRE)
  NM_ME_ICE_EXPLOSION  27  <- explosión en área (NM_ME_EXPLOSION_AREA)
  NM_ME_ICE_SHATTER    28  <- explosión de daño (NM_ME_EXPLOSION_DAMAGE)
  NM_ANI_FROSTBALL     15  <- bola de fuego (NM_ANI_FIRE)

Uso:
  python3 scripts/client-rme/add_recolor_effects.py --pack ice --preview x.png      # solo vista previa
  python3 scripts/client-rme/add_recolor_effects.py --pack ice DIR_THINGS           # aplica

Idempotente: si el .dat ya tiene los contadores del pack aplicado, no cambia nada. Los packs se
aplican en orden (los números de constante dependen de eso); hoy existe solo "ice".
Ver docs/gameplay/CLIENT_EFFECTS.md.
"""
from __future__ import annotations

import argparse
import colorsys
import shutil
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from add_black_dragon_look import _read_thing, _skip_attr, decode_sprite, encode_sprite, read_spr, write_spr  # noqa: E402

RME_THINGS = HERE.parents[1] / "devtools/rme/rme-client-760"
BASE_EFFECTS, BASE_MISSILES = 25, 15


def gradient(stops, k):
    k = max(0.0, min(1.0, k))
    for (k0, c0), (k1, c1) in zip(stops, stops[1:]):
        if k <= k1:
            t = (k - k0) / (k1 - k0) if k1 > k0 else 0
            return tuple(int(a + (b - a) * t) for a, b in zip(c0, c1))
    return stops[-1][1]


ICE = [(0, (8, 18, 52)), (0.25, (30, 80, 170)), (0.5, (70, 160, 235)), (0.75, (165, 225, 255)), (1, (250, 254, 255))]


def recolor_ice(p):
    """Fuego -> hielo: rojo oscuro = azul noche, naranja = celeste, amarillo = blanco."""
    r, g, b, a = p
    if a == 0:
        return p
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    lum = (0.30 * r + 0.59 * g + 0.11 * b) / 255
    if s < 0.25:                               # grises/blancos (humo, chispas): leve tinte frío
        return (int(r * 0.85), int(g * 0.93), min(255, int(b * 1.05) + 12), 255)
    return gradient(ICE, lum ** 0.8 * 1.15) + (255,)


# (sección, número de cliente de origen, constante nueva, función)
PACKS = {
    "ice": {
        # color de luz (paleta 6x6x6: r*36 + g*6 + b): celeste frío. Los originales de fuego
        # traen luz naranja (206/208); sin esto el hielo "brillaba" naranja.
        "light": 3 * 36 + 4 * 6 + 5,
        "effects": [(7, "NM_ME_ICE_AREA", recolor_ice), (16, "NM_ME_ICE_HIT", recolor_ice),
                    (5, "NM_ME_ICE_EXPLOSION", recolor_ice), (6, "NM_ME_ICE_SHATTER", recolor_ice)],
        "missiles": [(4, "NM_ANI_FROSTBALL", recolor_ice)],
    },
}


def read_sections(dat: bytes):
    _sig, items, outfits, effects, missiles = struct.unpack_from("<IHHHH", dat, 0)
    pos = 12
    for _ in range(items - 99 + outfits):
        pos = _read_thing(dat, pos)["end"]
    fx, mi = [], []
    for _ in range(effects):
        t = _read_thing(dat, pos)
        fx.append(t)
        pos = t["end"]
    for _ in range(missiles):
        t = _read_thing(dat, pos)
        mi.append(t)
        pos = t["end"]
    if pos != len(dat):
        raise SystemExit(f"Tibia.dat no se leyó completo ({pos} de {len(dat)} bytes)")
    return (items, outfits, effects, missiles), fx, mi


def relight(prefix: bytes, color: int) -> bytes:
    """Cambia el color del atributo de luz (0x15) de una entrada del .dat, si lo tiene."""
    out, pos = bytearray(prefix), 0
    while out[pos] != 0xFF:
        attr = out[pos]
        if attr == 0x15:
            struct.pack_into("<H", out, pos + 3, color)
        pos = _skip_attr(bytes(out), pos + 1, attr)
    return bytes(out)


def png(path: Path, w: int, h: int, rows: list[bytes]):
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(k, d):
        return struct.pack(">I", len(d)) + k + d + struct.pack(">I", zlib.crc32(k + d) & 0xFFFFFFFF)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def write_preview(path: Path, pairs: list[tuple[str, list, list]], scale: int = 3):
    """Una fila por recurso: cuadros originales arriba, recoloreados abajo (1 sprite por cuadro)."""
    cols = max(len(o) for _n, o, _r in pairs)
    W, H = cols * 34 * scale, len(pairs) * 2 * 34 * scale
    img = bytearray(b"\x26\x26\x2c\xff" * (W * H))
    for row, (_name, orig, new) in enumerate(pairs):
        for half, frames in enumerate((orig, new)):
            for c, pix in enumerate(frames):
                ox, oy = c * 34 * scale, (row * 2 + half) * 34 * scale
                for i, p in enumerate(pix):
                    if not p[3]:
                        continue
                    for dy in range(scale):
                        for dx in range(scale):
                            o = ((oy + (i // 32) * scale + dy) * W + ox + (i % 32) * scale + dx) * 4
                            img[o:o + 4] = bytes(p)
    png(path, W, H, [bytes(img[y * W * 4:(y + 1) * W * 4]) for y in range(H)])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("things_dir", type=Path, nargs="?")
    ap.add_argument("--pack", choices=sorted(PACKS), required=True)
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()
    pack = PACKS[a.pack]

    src = a.things_dir or RME_THINGS
    dat_path, spr_path = src / "Tibia.dat", src / "Tibia.spr"
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    counts, fx, mi = read_sections(dat)
    want_fx, want_mi = BASE_EFFECTS + len(pack["effects"]), BASE_MISSILES + len(pack["missiles"])
    if counts[2] >= want_fx and counts[3] >= want_mi:      # puede haber más después (ej. enchanted spear)
        applied = True
    elif (counts[2], counts[3]) == (BASE_EFFECTS, BASE_MISSILES):
        applied = False
    else:
        raise SystemExit(f"Contadores inesperados efectos={counts[2]} proyectiles={counts[3]}")
    spr_count, offsets = read_spr(spr)

    # sprites recoloreados de cada recurso nuevo
    plan, preview = [], []
    for section, lst in (("effects", fx), ("missiles", mi)):
        for client_id, const, fn in pack[section]:
            t = lst[client_id - 1]
            orig = [decode_sprite(spr, offsets, s) for s in t["ids"]]
            new = [[fn(p) for p in pix] for pix in orig]
            plan.append((section, t, new))
            preview.append((const, orig, new))
    if a.preview:
        write_preview(a.preview, preview)
        print(f"Vista previa: {a.preview}")
    if a.things_dir is None:
        return 0
    if applied:
        # Solo corrige la luz si quedó con el color del original (versiones viejas del script).
        new_dat = bytearray(dat)
        for t in fx[BASE_EFFECTS:want_fx] + mi[BASE_MISSILES:want_mi]:
            fixed = relight(dat[t["start"]:t["sprite_pos"]], pack["light"])
            new_dat[t["start"]:t["sprite_pos"]] = fixed
        if bytes(new_dat) == dat:
            print(f"El pack '{a.pack}' ya está aplicado (efectos={counts[2]}, proyectiles={counts[3]}).")
        else:
            c2, fx2, mi2 = read_sections(bytes(new_dat))
            assert [t["ids"] for t in fx2] == [t["ids"] for t in fx] and [t["ids"] for t in mi2] == [t["ids"] for t in mi]
            dat_path.write_bytes(bytes(new_dat))
            print(f"El pack '{a.pack}' ya estaba aplicado; luz corregida al color {pack['light']}.")
        return 0

    records, next_id = [], spr_count + 1
    entries = {"effects": b"", "missiles": b""}
    for section, t, new in plan:
        ids = []
        for pix in new:
            records.append(encode_sprite(pix))
            ids.append(next_id)
            next_id += 1
        entries[section] += relight(dat[t["start"]:t["sprite_pos"]], pack["light"]) + struct.pack(f"<{len(ids)}H", *ids)
    fx_end = fx[-1]["end"]
    header = dat[:4] + struct.pack("<HHHH", counts[0], counts[1], want_fx, want_mi)
    new_dat = header + dat[12:fx_end] + entries["effects"] + dat[fx_end:] + entries["missiles"]
    new_spr = write_spr(struct.unpack_from("<I", spr, 0)[0], offsets, spr, records)

    c2, fx2, mi2 = read_sections(new_dat)
    assert (c2[2], c2[3]) == (want_fx, want_mi)
    assert [t["ids"] for t in fx2[:BASE_EFFECTS]] == [t["ids"] for t in fx]
    assert [t["ids"] for t in mi2[:BASE_MISSILES]] == [t["ids"] for t in mi]
    _n, off2 = read_spr(new_spr)
    assert decode_sprite(new_spr, off2, spr_count + 1) == plan[0][2][0]

    for path, data in ((dat_path, new_dat), (spr_path, new_spr)):
        backup = path.with_name(f"{path.name}.bak-fx-{a.pack}")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_bytes(data)
    print(f"Pack '{a.pack}': efectos {counts[2]} -> {want_fx}, proyectiles {counts[3]} -> {want_mi}, "
          f"sprites {spr_count} -> {next_id - 1}.")
    for section, lst, base in (("effects", pack["effects"], BASE_EFFECTS), ("missiles", pack["missiles"], BASE_MISSILES)):
        for i, (_c, const, _f) in enumerate(lst):
            print(f"  {const} = {base + i}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
