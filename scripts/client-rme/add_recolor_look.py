#!/usr/bin/env python3
"""Crea un looktype nuevo recoloreando una criatura existente del cliente 7.6 (genérico).

Mismo método que add_black_dragon_look.py (que queda como referencia): copia la estructura
de la criatura base (tamaño, direcciones, cuadros) a un looktype vacío y le pone sprites
nuevos recoloreados por píxel, así la animación queda idéntica a la original.

Presets:
  black-dragon   Dragon (34) -> 230, negro con brillo violeta, ojos rojos
  frost-dragon   Dragon (34) -> 231, hielo: cuerpo azul acero a blanco, panza y alas
                 blanco hielo, ojos celestes brillantes (estilo Frost Dragon de versiones nuevas)
  ice-monk       Monk (57) -> 232, túnica azul profundo a blanco hielo, cinturón celeste
                 brillante y la cara en sombra bajo la capucha con ojos celestes que brillan

Uso:
  python3 scripts/client-rme/add_recolor_look.py --preset frost-dragon DIR_THINGS [--preview x.png]
  python3 scripts/client-rme/add_recolor_look.py --preset frost-dragon --preview x.png   # solo vista previa

DIR_THINGS = carpeta con Tibia.dat y Tibia.spr (se modifican en el lugar, con copia
.bak-<preset>). Idempotente: si el looktype destino ya tiene sprites, no cambia nada.
Aplicar a devtools/rme/rme-client-760/ (RME, en git) y a la base del cliente de jugadores
antes de build_zagan_test_assets.py. Ver docs/gameplay/CUSTOM_MONSTER_WORKFLOW.md.
"""
from __future__ import annotations

import argparse
import colorsys
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from add_black_dragon_look import (decode_sprite, encode_sprite, read_outfits, read_spr,  # noqa: E402
                                   recolor as recolor_black, write_preview, write_spr)

RME_THINGS = HERE.parents[1] / "devtools/rme/rme-client-760"


def gradient(stops, k):
    k = max(0.0, min(1.0, k))
    for (k0, c0), (k1, c1) in zip(stops, stops[1:]):
        if k <= k1:
            t = (k - k0) / (k1 - k0) if k1 > k0 else 0
            return tuple(int(a + (b - a) * t) for a, b in zip(c0, c1))
    return stops[-1][1]


FROST_BODY = [(0, (10, 16, 40)), (0.22, (36, 64, 120)), (0.45, (92, 142, 206)),
              (0.72, (176, 210, 240)), (1, (248, 252, 255))]
FROST_PALE = [(0, (26, 46, 82)), (0.35, (118, 174, 216)), (0.7, (196, 232, 246)), (1, (252, 255, 255))]


def recolor_frost(pixel):
    r, g, b, a = pixel
    if a == 0:
        return pixel
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if (h < 0.09 or h > 0.95) and s > 0.6 and v > 0.5:      # ojos, lengua, garras rojas
        return (120, 245, 255, 255)
    lum = (0.30 * r + 0.59 * g + 0.11 * b) / 255
    if 0.06 < h < 0.2 and s > 0.35:                          # panza y membranas (amarillo/naranja)
        return gradient(FROST_PALE, (lum ** 0.75) * 1.15) + (255,)
    return gradient(FROST_BODY, (lum ** 0.7) * 1.25) + (255,)  # cuerpo verde -> hielo


ICE_ROBE = [(0, (6, 10, 28)), (0.2, (18, 38, 88)), (0.45, (40, 88, 166)),
            (0.7, (110, 172, 228)), (0.9, (200, 232, 250)), (1, (245, 252, 255))]
ICE_SKIN = [(0, (70, 96, 120)), (0.55, (190, 214, 228)), (1, (240, 248, 252))]


def recolor_ice_monk(pixel):
    """Monk (57): túnica marrón -> azul profundo a blanco hielo, piel -> celeste pálido helado,
    cinturón dorado -> celeste brillante (parece que brilla)."""
    r, g, b, a = pixel
    if a == 0:
        return pixel
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    lum = (0.30 * r + 0.59 * g + 0.11 * b) / 255
    if 0.06 <= h <= 0.10 and 0.28 <= s <= 0.47 and v > 0.74:      # cara y manos
        return gradient(ICE_SKIN, lum * 1.05) + (255,)
    if 0.095 <= h <= 0.13 and s > 0.47 and v > 0.76:               # cinturón
        return gradient([(0, (60, 170, 220)), (1, (190, 250, 255))], (v - 0.76) / 0.24) + (255,)
    return gradient(ICE_ROBE, (lum ** 0.85) * 1.2) + (255,)       # túnica y sombras


def _is_skin(pixel):
    r, g, b, a = pixel
    if a == 0:
        return False
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return 0.06 <= h <= 0.10 and 0.28 <= s <= 0.47 and v > 0.74


def _clusters(points):
    points, seen, out = set(points), set(), []
    for start in sorted(points, key=lambda t: (t[1], t[0])):
        if start in seen:
            continue
        seen.add(start)
        stack, comp = [start], []
        while stack:
            x, y = stack.pop()
            comp.append((x, y))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in points and q not in seen:
                        seen.add(q)
                        stack.append(q)
        out.append(comp)
    return out


HOOD_SHADOW = (14, 22, 48, 255)
EYE_GLOW = (150, 248, 255, 255)
EYE_HALO = (50, 130, 196, 255)


def ice_monk_eyes(original, recolored):
    """Cara en sombra bajo la capucha con ojos celestes que brillan (rasgo del Ice Monk).

    La cara es el grupo de piel más grande del cuadro (las manos tienen 1-3 píxeles). De frente
    (más ancha que alta) lleva dos ojos en su fila de arriba; de perfil, uno hacia donde mira.
    De espaldas no hay cara visible y el cuadro queda igual."""
    out = []
    for index, (orig, new) in enumerate(zip(original, recolored)):
        new = list(new)
        skin = [(i % 64, i // 64) for i, p in enumerate(orig) if _is_skin(p)]
        faces = [c for c in _clusters(skin) if len(c) >= 6]
        for face in faces:
            for x, y in face:
                new[y * 64 + x] = HOOD_SHADOW
            xs = [x for x, _ in face]
            ys = [y for _, y in face]
            top = sorted(x for x, y in face if y == min(ys))
            if max(xs) - min(xs) >= max(ys) - min(ys):          # de frente
                eyes = [(top[0], min(ys)), (top[-1], min(ys))] if len(top) >= 3 else [(top[-1], min(ys))]
            else:                                                 # de perfil: mira hacia el lado del cuadro
                facing_east = index % 4 == 1
                eyes = [(max(xs) if facing_east else min(xs), min(ys) + 1)]
            face_set = set(face)
            for x, y in eyes:
                new[y * 64 + x] = EYE_GLOW
                if (x, y + 1) in face_set:                        # brillo suave debajo del ojo
                    new[(y + 1) * 64 + x] = EYE_HALO
        out.append(new)
    return out


PRESETS = {
    "black-dragon": dict(source=34, target=230, recolor=recolor_black, name="Black Dragon"),
    "frost-dragon": dict(source=34, target=231, recolor=recolor_frost, name="Frost Dragon"),
    "ice-monk": dict(source=57, target=232, recolor=recolor_ice_monk, name="Ice Monk", frames_post=ice_monk_eyes),
}


def frames_2x2(decoded: dict[int, list]) -> list[list]:
    """Cuadros 64x64 en orden anim -> dirección; tiles 2x2 empezando por abajo-derecha."""
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


def split_2x2(frames: list[list]) -> dict[int, list]:
    """Inverso de frames_2x2: vuelve a los 48 sprites de 32x32 en el orden del .dat."""
    decoded = {}
    for anim in range(3):
        for direction in range(4):
            frame = frames[anim * 4 + direction]
            base = (anim * 4 + direction) * 4
            for tile in range(4):
                ox, oy = (1 - tile % 2) * 32, (1 - tile // 2) * 32
                decoded[base + tile] = [frame[(oy + i // 32) * 64 + ox + i % 32] for i in range(1024)]
    return decoded


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("things_dir", type=Path, nargs="?")
    ap.add_argument("--preset", choices=sorted(PRESETS), required=True)
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()
    p = PRESETS[a.preset]

    src_dir = a.things_dir or RME_THINGS
    dat_path, spr_path = src_dir / "Tibia.dat", src_dir / "Tibia.spr"
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    outfits, counts = read_outfits(dat)
    if counts[1] < p["target"]:
        raise SystemExit(f"El dat tiene {counts[1]} looktypes; se esperaba al menos {p['target']}")
    source, target = outfits[p["source"] - 1], outfits[p["target"] - 1]
    spr_count, offsets = read_spr(spr)
    original = {i: decode_sprite(spr, offsets, sid) for i, sid in enumerate(source["ids"])}
    decoded = {i: [p["recolor"](px) for px in pixels] for i, pixels in original.items()}
    if p.get("frames_post"):                      # retoque por cuadro completo (ej. ojos del Ice Monk)
        if len(source["ids"]) != 48:
            raise SystemExit("frames_post asume una criatura 2x2, 4 direcciones y 3 cuadros")
        decoded = split_2x2(p["frames_post"](frames_2x2(original), frames_2x2(decoded)))

    if a.preview:
        if len(source["ids"]) != 48:
            raise SystemExit("La vista previa asume una criatura 2x2, 4 direcciones y 3 cuadros")
        write_preview(a.preview, frames_2x2(decoded))
        print(f"Vista previa: {a.preview}")
    if a.things_dir is None:
        return 0

    if any(target["ids"]):
        print(f"El looktype {p['target']} ya tiene sprites; no se cambia nada.")
        return 0
    new_records = [encode_sprite(decoded[i]) for i in range(len(source["ids"]))]
    new_ids = [spr_count + 1 + i for i in range(len(new_records))]
    entry = dat[source["start"]:source["sprite_pos"]] + struct.pack(f"<{len(new_ids)}H", *new_ids)
    new_dat = dat[:target["start"]] + entry + dat[target["end"]:]
    new_spr = write_spr(struct.unpack_from("<I", spr, 0)[0], offsets, spr, new_records)

    check, _ = read_outfits(new_dat)
    assert check[p["target"] - 1]["ids"] == new_ids
    _c, new_offsets = read_spr(new_spr)
    assert decode_sprite(new_spr, new_offsets, new_ids[0]) == decoded[0]

    for path, data in ((dat_path, new_dat), (spr_path, new_spr)):
        backup = path.with_name(f"{path.name}.bak-{a.preset}")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_bytes(data)
    print(f"Looktype {p['target']} = {p['name']}; sprites {new_ids[0]}-{new_ids[-1]} agregados "
          f"({spr_count} -> {spr_count + len(new_records)}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
