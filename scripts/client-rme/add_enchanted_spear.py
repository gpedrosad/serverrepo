#!/usr/bin/env python3
"""Enchanted Spear: sprite y luz propia en el cliente 7.6 (Tibia.dat / Tibia.spr).

El dibujo se arma a partir de la spear del cliente (client id 3277): se conserva el asta con
su contorno y se le pone una hoja de cristal más larga, una guarda dorada, runas que brillan
en el asta y un halo hacia la punta. Además el ítem emite LUZ de color en el juego (atributo
light del .dat), como una antorcha chica: así brilla distinto también de noche o en cuevas.

Proyectil propio NM_ANI_ENCHANTED_SPEAR = 16 (después de la bola de hielo del pack "ice", que
tiene que estar aplicado antes): 8 direcciones, las diagonales son el dibujo del ítem espejado y
las rectas la misma lanza derecha; vuela con luz del color del estilo.

Ids (ver docs/gameplay/ENCHANTED_SPEAR.md):
  server id 20156   items-zagan-test.otb  (scripts/otb/patch-enchanted-spear-otb.py)
  client id 3576    reutilizado: era "post officers hat" (server 2665), sin uso en mapa,
                    loot, NPCs ni scripts. Reservado en build_zagan_test_assets.py.

Estilos (--style): arcana (azul, por defecto), violeta, sagrada (dorada), esmeralda.

Uso:
  python3 scripts/client-rme/add_enchanted_spear.py --preview x.png              # vista previa de todos
  python3 scripts/client-rme/add_enchanted_spear.py DIR_THINGS --style arcana    # aplica
  python3 scripts/client-rme/add_enchanted_spear.py --png x.png --style arcana   # sprite 32x32 suelto
  python3 scripts/client-rme/add_enchanted_spear.py --missile-preview x.png       # proyectil, 8 direcciones

Aplicar DESPUÉS de build_zagan_test_assets.py (que rehace el .dat desde la base). Volver a
correrlo con otro --style cambia el dibujo y la luz en el lugar (no agrega sprites nuevos).
"""
from __future__ import annotations

import argparse
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from add_black_dragon_look import _read_thing, decode_sprite, encode_sprite, read_spr, write_spr  # noqa: E402
from add_recolor_effects import png, read_sections  # noqa: E402

RME_THINGS = HERE.parents[1] / "devtools/rme/rme-client-760"
SPEAR_CID = 3277
TARGET_CID = 3576
GRASS_CID = 102            # solo para la vista previa
LIGHT_LEVEL = 3            # antorcha = 7
MISSILE_LIGHT_LEVEL = 4    # en vuelo; la bola de fuego es 5
MISSILE_ID = 16            # NM_ANI_ENCHANTED_SPEAR: 15 base + bola de hielo (pack ice) = 16

SHAFT = {(140, 69, 16): 0, (173, 85, 16): 1, (206, 97, 25): 2}   # tonos del asta original
OUTLINE = (0, 0, 0)

# head: oscuro -> brillo de la hoja; shaft: 3 tonos del asta; aura: [lejos, cerca];
# light: color de la luz en la paleta 6x6x6 del cliente (r*36 + g*6 + b, cada uno 0..5)
STYLES = {
    "arcana": dict(label="Arcana (azul)", head=[(40, 70, 150), (80, 150, 230), (150, 215, 255), (235, 250, 255)],
                   shaft=[(40, 30, 80), (70, 52, 125), (100, 78, 170)], band=(240, 200, 70), rune=(120, 240, 255),
                   aura=[(30, 110, 190), (90, 200, 255)], spark=(220, 250, 255), light=1 * 36 + 4 * 6 + 5),
    "violeta": dict(label="Violeta", head=[(80, 30, 120), (150, 70, 210), (210, 140, 255), (250, 230, 255)],
                    shaft=[(35, 22, 40), (60, 40, 70), (90, 62, 100)], band=(200, 200, 215), rune=(230, 120, 255),
                    aura=[(110, 40, 170), (200, 110, 255)], spark=(255, 220, 255), light=4 * 36 + 2 * 6 + 5),
    "sagrada": dict(label="Sagrada (dorada)", head=[(150, 100, 20), (220, 170, 40), (255, 225, 110), (255, 255, 225)],
                    shaft=[(150, 140, 130), (200, 190, 175), (240, 235, 220)], band=(220, 170, 40), rune=(255, 240, 150),
                    aura=[(200, 150, 30), (255, 220, 90)], spark=(255, 255, 230), light=5 * 36 + 5 * 6 + 2),
    "esmeralda": dict(label="Esmeralda", head=[(20, 90, 50), (40, 170, 90), (120, 235, 150), (225, 255, 230)],
                      shaft=[(50, 35, 20), (85, 60, 30), (120, 88, 45)], band=(240, 200, 70), rune=(110, 255, 160),
                      aura=[(20, 140, 70), (90, 230, 130)], spark=(230, 255, 235), light=1 * 36 + 5 * 6 + 2),
}

Pixels = list  # 1024 tuplas RGBA


def design(base: Pixels, st: dict, s0: int = 12, prof=(1, 1, 2, 2, 2, 2, 1, 1, 0)) -> Pixels:
    """Coordenadas sobre la diagonal de la spear: s = x - y (a lo largo), q = x + y - 30 (de costado)."""
    out = [(0, 0, 0, 0)] * 1024

    def put(x, y, c):
        if 0 <= x < 32 and 0 <= y < 32:
            out[y * 32 + x] = c + (255,)

    def filled(x, y):
        return 0 <= x < 32 and 0 <= y < 32 and out[y * 32 + x][3]

    # asta original (con su contorno) hasta la guarda; bandas doradas y runas
    for i, p in enumerate(base):
        x, y = i % 32, i // 32
        s = x - y
        if not p[3] or s >= s0 - 2:
            continue
        if p[:3] in SHAFT:
            t = SHAFT[p[:3]]
            c = st["shaft"][t]
            if -9 <= s <= -8:
                c = st["band"] if t else tuple(v * 2 // 3 for v in st["band"])
            elif t == 2 and s % 4 == 1 and -7 < s < s0 - 3:
                c = st["rune"]
            put(x, y, c)
        else:
            put(x, y, p[:3])

    blade = {}
    for x in range(32):
        for y in range(32):
            q, k = x + y - 30, (x - y - s0) // 2
            if 0 <= k < len(prof) and abs(q) <= prof[k]:
                blade[(x, y)] = (q, k)
    guard = set()
    for q in range(-3, 4):
        s = s0 - 2 if (s0 - 2 + q) % 2 == 0 else s0 - 3
        guard.add(((s + q + 30) // 2, (q + 30 - s) // 2))
    solid = set(blade) | guard

    outline = set()
    for x, y in solid:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in solid and not (filled(*n) and out[n[1] * 32 + n[0]][:3] != OUTLINE):
                outline.add(n)
    halo = set()
    for x, y in outline:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n not in solid and n not in outline and 0 <= n[0] < 32 and 0 <= n[1] < 32 and not filled(*n):
                    halo.add(n)
    for x, y in halo:                       # halo: punteado cerca de la guarda, lleno hacia la punta
        k = (x - y - s0) // 2
        if k < 2 or (k < 5 and (x + y) % 2):
            continue
        put(x, y, st["aura"][1] if k >= 5 else st["aura"][0])
    for n in outline:
        put(*n, OUTLINE)
    h = st["head"]
    for (x, y), (q, k) in blade.items():
        if q == 0:
            c = h[3] if k >= 2 else h[2]     # filo central
        elif q < 0:
            c = h[2] if q == -1 else h[1]    # lado iluminado
        else:
            c = h[1] if q == 1 else h[0]     # lado en sombra
        put(x, y, c)
    for g in guard:
        put(*g, st["band"])
    for sx, sy, big in ((24, 2, True), (30, 7, False), (18, 6, False)):   # destellos
        put(sx, sy, st["spark"])
        if big:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if not filled(sx + dx, sy + dy):
                    put(sx + dx, sy + dy, st["aura"][1])
    return out


def design_straight(st: dict) -> Pixels:
    """Misma lanza en horizontal (punta a la derecha), para los proyectiles N/S/E/O.

    Asta de 2 px (filas 15 y 16) con contorno, como la spear original; hoja de cristal,
    guarda, bandas, runas y halo con las mismas reglas que design().
    """
    out = [(0, 0, 0, 0)] * 1024

    def put(x, y, c):
        if 0 <= x < 32 and 0 <= y < 32:
            out[y * 32 + x] = c + (255,)

    b0 = 19                                   # donde empieza la hoja
    prof = (1, 1, 1, 2, 1, 1, 1, 0, 0, 0, 0)  # filas extra arriba/abajo del asta, de la base a la punta
    tip = b0 + len(prof) - 1
    solid, blade = set(), {}
    for x in range(1, b0 - 1):                # asta
        for y in (15, 16):
            solid.add((x, y))
    for k, e in enumerate(prof):              # hoja
        for y in range(15 - e, 17 + e):
            blade[(b0 + k, y)] = (y - 15.5, k, e)
    guard = {(b0 - 1, y) for y in range(12, 20)}
    allsolid = solid | set(blade) | guard
    outline = set()
    for x, y in allsolid:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in allsolid:
                outline.add(n)
    halo = set()
    for x, y in outline:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n not in allsolid and n not in outline and 0 <= n[0] < 32 and 0 <= n[1] < 32:
                    halo.add(n)
    for x, y in halo:
        k = x - b0
        if k < 1 or (k < 5 and (x + y) % 2):
            continue
        put(x, y, st["aura"][1] if k >= 5 else st["aura"][0])
    for n in outline:
        put(*n, OUTLINE)
    for x, y in solid:
        c = st["shaft"][0] if y == 15 else st["shaft"][2]
        if 4 <= x <= 5:
            c = st["band"] if y == 16 else tuple(v * 2 // 3 for v in st["band"])
        elif y == 16 and x % 4 == 1 and 6 < x < b0 - 3:
            c = st["rune"]
        put(x, y, c)
    h = st["head"]
    for (x, y), (q, k, e) in blade.items():
        if abs(q) == 0.5:
            c = h[3] if k >= 2 and q < 0 else h[2]   # filo central
        elif q < 0:
            c = h[1]                                  # lado iluminado (arriba)
        else:
            c = h[0] if abs(q) > 1.5 else h[1]        # lado en sombra
        put(x, y, c)
    for g in guard:
        put(*g, st["band"])
    for sx, sy, big in ((tip - 3, 11, True), (tip + 1, 19, False), (b0 + 1, 20, False)):
        put(sx, sy, st["spark"])
        if big:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if not out[(sy + dy) * 32 + sx + dx][3]:
                    put(sx + dx, sy + dy, st["aura"][1])
    return out


def flip_x(p: Pixels) -> Pixels:
    return [p[y * 32 + 31 - x] for y in range(32) for x in range(32)]


def flip_y(p: Pixels) -> Pixels:
    return [p[(31 - y) * 32 + x] for y in range(32) for x in range(32)]


def to_north(east: Pixels) -> Pixels:
    """Gira 90° a la izquierda: la punta que miraba al este queda arriba."""
    return [east[x * 32 + 31 - y] for y in range(32) for x in range(32)]


def missile_frames(item: Pixels, east: Pixels) -> list[Pixels | None]:
    """Orden del proyectil 3x3 del .dat: NO, N, NE, O, (centro), E, SO, S, SE.
    Las diagonales son el dibujo del ítem espejado (igual que la spear original)."""
    north = to_north(east)
    return [flip_x(item), north, item, flip_x(east), None, east,
            flip_x(flip_y(item)), flip_y(north), flip_y(item)]


# ---------------------------------------------------------------- .dat

def read_items(dat: bytes) -> tuple[dict[int, dict], int]:
    items = struct.unpack_from("<H", dat, 4)[0]
    pos, things = 12, {}
    for cid in range(100, items + 1):
        t = _read_thing(dat, pos)
        things[cid] = t
        pos = t["end"]
    return things, items


def light_rgb(color: int) -> tuple[int, int, int]:
    return (color // 36 % 6 * 51, color // 6 % 6 * 51, color % 6 * 51)


def entry_bytes(dat: bytes, spear: dict, light: int, sprite_id: int) -> bytes:
    prefix = dat[spear["start"]:spear["sprite_pos"]]
    dims = prefix[prefix.index(0xFF) + 1:]               # ancho, alto, capas, patrones, animación
    attrs = b"\x10" + b"\x15" + struct.pack("<HH", LIGHT_LEVEL, light)   # agarrable + luz
    return attrs + b"\xff" + dims + struct.pack("<H", sprite_id)


def is_applied(dat: bytes, t: dict) -> bool:
    return dat[t["start"]:t["start"] + 2] == b"\x10\x15" and len(t["ids"]) == 1


def replace_sprites(spr: bytes, offsets: list[int], new: dict[int, bytes]) -> bytes:
    """Reescribe el .spr con algunos sprites cambiados (los demás quedan idénticos)."""
    count = len(offsets)
    records = []
    for i, off in enumerate(offsets):
        if i + 1 in new:
            records.append(new[i + 1])
        elif off == 0:
            records.append(None)
        else:
            size = struct.unpack_from("<H", spr, off + 3)[0]
            records.append(spr[off:off + 5 + size])
    out = bytearray(spr[:6])
    tail = 6 + 4 * count
    for r in records:
        out += struct.pack("<I", tail if r else 0)
        tail += len(r) if r else 0
    for r in records:
        if r:
            out += r
    return bytes(out)


# ---------------------------------------------------------------- vista previa

def scene(base_spr: bytes, offsets: list[int], dat_things: dict, sprites: list[tuple[str, Pixels, int | None]],
          path: Path, scale: int = 3) -> None:
    """Por cada sprite: grande (x6), en el piso de día, en el piso de noche con su luz y en el inventario."""
    grass = decode_sprite(base_spr, offsets, dat_things[GRASS_CID]["ids"][0])
    big, tile = 6, 32 * scale
    cell_w = max(32 * big, 3 * tile) + 24
    W = cell_w * len(sprites) + 24
    H = 32 * big + 3 * tile + 64 + 24
    img = [(36, 36, 44)] * (W * H)

    def blit(px, ox, oy, s, shade=None):
        for i, p in enumerate(px):
            if not p[3]:
                continue
            c = shade(i % 32, i // 32, p[:3]) if shade else p[:3]
            for dy in range(s):
                row = (oy + (i // 32) * s + dy) * W + ox + (i % 32) * s
                for dx in range(s):
                    img[row + dx] = c

    for n, (_name, px, light) in enumerate(sprites):
        ox = 24 + n * cell_w
        blit(px, ox, 12, big)
        # de día: 3x1 baldosas de pasto, el ítem en el medio
        y1 = 12 + 32 * big + 12
        for k in range(3):
            blit(grass, ox + k * tile, y1, scale)
        blit(px, ox + tile, y1, scale)
        # de noche: luz ambiente baja + luz del ítem (radio ~ nivel de luz en baldosas)
        y2 = y1 + tile + 8
        lr = light_rgb(light) if light is not None else None

        def night(x, y, c, k=0):
            gx, gy = (k * 32 + x) / 32 - 1.5, y / 32 - 0.5
            d = (gx * gx + gy * gy) ** 0.5
            amb = 0.22
            if lr is None:
                return tuple(int(v * amb) for v in c)
            f = max(0.0, 1 - d / (LIGHT_LEVEL * 0.55))
            return tuple(min(255, int(v * (amb + f * 0.9 * (0.35 + 0.65 * l / 255)))) for v, l in zip(c, lr))
        for k in range(3):
            blit(grass, ox + k * tile, y2, scale, lambda x, y, c, k=k: night(x, y, c, k))
        blit(px, ox + tile, y2, scale, lambda x, y, c: night(x + 32, y, c) if lr else tuple(int(v * 0.22) for v in c))
        # inventario: casilla gris con bisel
        y3 = y2 + tile + 8
        for yy in range(y3, y3 + 34 * 2):
            for xx in range(ox, ox + 34 * 2):
                e = xx - ox in (0, 1) or yy - y3 in (0, 1)
                f = xx - ox in (66, 67) or yy - y3 in (66, 67)
                img[yy * W + xx] = (30, 30, 30) if e else (90, 90, 90) if f else (62, 62, 66)
        blit(px, ox + 2, y3 + 2, 2)
    raw = [b"".join(bytes(c) + b"\xff" for c in img[y * W:(y + 1) * W]) for y in range(H)]
    png(path, W, H, raw)


def missile_sheet(base: Pixels, path: Path, scale: int = 3) -> None:
    """Rosa de 8 direcciones del proyectil para cada estilo (spear original primero)."""
    sets = [(name, missile_frames(design(base, st), design_straight(st))) for name, st in STYLES.items()]
    cell, gap = 3 * 32 * scale, 30
    W, H = len(sets) * (cell + gap) - gap, cell
    img = [(36, 36, 44)] * (W * H)
    for n, (_name, frames) in enumerate(sets):
        for k, px in enumerate(frames):
            if px is None:
                continue
            ox, oy = n * (cell + gap) + (k % 3) * 32 * scale, (k // 3) * 32 * scale
            for i, p in enumerate(px):
                if p[3]:
                    for dy in range(scale):
                        row = (oy + (i // 32) * scale + dy) * W + ox + (i % 32) * scale
                        for dx in range(scale):
                            img[row + dx] = p[:3]
    png(path, W, H, [b"".join(bytes(c) + b"\xff" for c in img[y * W:(y + 1) * W]) for y in range(H)])


def save_sprite_png(px: Pixels, path: Path) -> None:
    png(path, 32, 32, [b"".join(bytes(p) for p in px[y * 32:(y + 1) * 32]) for y in range(32)])


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("things_dir", type=Path, nargs="?")
    ap.add_argument("--style", choices=sorted(STYLES), default="arcana")
    ap.add_argument("--preview", type=Path, help="PNG con la spear y los 4 estilos en contexto")
    ap.add_argument("--png", type=Path, help="guarda el sprite 32x32 del estilo elegido")
    ap.add_argument("--missile-preview", type=Path, help="PNG con el proyectil en 8 direcciones, 4 estilos")
    ap.add_argument("--missile-png", type=Path, help="carpeta: un PNG 32x32 por dirección del estilo elegido")
    a = ap.parse_args()

    src = a.things_dir or RME_THINGS
    dat_path, spr_path = src / "Tibia.dat", src / "Tibia.spr"
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    things, item_count = read_items(dat)
    if TARGET_CID > item_count or SPEAR_CID > item_count:
        raise SystemExit(f"El .dat tiene {item_count} ítems; faltan los client ids {SPEAR_CID}/{TARGET_CID}")
    spr_count, offsets = read_spr(spr)
    base = decode_sprite(spr, offsets, things[SPEAR_CID]["ids"][0])
    st = STYLES[a.style]
    px = design(base, st)

    if a.preview:
        rows = [("spear", base, None)] + [(k, design(base, v), v["light"]) for k, v in STYLES.items()]
        scene(spr, offsets, things, rows, a.preview)
        print(f"Vista previa: {a.preview}  (spear, " + ", ".join(STYLES) + ")")
    if a.png:
        save_sprite_png(px, a.png)
        print(f"Sprite: {a.png}")
    if a.missile_preview:
        missile_sheet(base, a.missile_preview)
        print(f"Proyectil: {a.missile_preview}")
    if a.missile_png:
        a.missile_png.mkdir(parents=True, exist_ok=True)
        for name, f in zip(("nw", "n", "ne", "w", None, "e", "sw", "s", "se"), missile_frames(px, design_straight(st))):
            if f is not None:
                save_sprite_png(f, a.missile_png / f"{name}.png")
        print(f"Proyectil por dirección: {a.missile_png}")
    if a.things_dir is None:
        return 0

    target = things[TARGET_CID]
    item_applied = is_applied(dat, target)
    counts, _fx, missiles = read_sections(dat)
    if counts[3] == MISSILE_ID:                       # 15 base + bola de hielo: falta la lanza
        missile_applied = False
    elif counts[3] >= MISSILE_ID + 1 and item_applied and missiles[MISSILE_ID]["ids"][2] == target["ids"][0]:
        missile_applied = True                        # su NE comparte el sprite del ítem (puede haber packs después)
    else:
        raise SystemExit(f"El .dat tiene {counts[3]} proyectiles; se esperaban {MISSILE_ID} "
                         "(aplicar antes add_recolor_effects.py --pack ice) o este proyectil ya aplicado.")

    frames = missile_frames(px, design_straight(st))
    sig = struct.unpack_from("<I", spr, 0)[0]
    # sprites: [ítem, 7 del proyectil]; el NE del proyectil es el mismo sprite del ítem
    own = [px] + [f for i, f in enumerate(frames) if f is not None and i != 2]
    if item_applied and missile_applied:
        old_m = missiles[MISSILE_ID]["ids"]
        ids = [target["ids"][0]] + [old_m[i] for i in range(9) if i not in (2, 4)]
        new_spr = replace_sprites(spr, offsets, {sid: encode_sprite(f) for sid, f in zip(ids, own)})
    elif item_applied:
        ids = [target["ids"][0]] + list(range(spr_count + 1, spr_count + 8))
        tmp = replace_sprites(spr, offsets, {ids[0]: encode_sprite(px)})
        new_spr = write_spr(sig, read_spr(tmp)[1], tmp, [encode_sprite(f) for f in own[1:]])
    else:
        ids = list(range(spr_count + 1, spr_count + 9))
        new_spr = write_spr(sig, offsets, spr, [encode_sprite(f) for f in own])
    it = iter(ids[1:])
    m_ids = [ids[0] if i == 2 else 0 if i == 4 else next(it) for i in range(9)]

    # .dat: primero el proyectil (al final del archivo), después el ítem (más arriba)
    m_entry = (b"\x15" + struct.pack("<HH", MISSILE_LIGHT_LEVEL, st["light"])      # luz en vuelo
               + dat[missiles[0]["start"]:missiles[0]["sprite_pos"]] + struct.pack("<9H", *m_ids))
    if missile_applied:
        # reemplaza solo esta entrada: los proyectiles de packs posteriores (ej. "shadow") quedan detrás
        new_dat = dat[:missiles[MISSILE_ID]["start"]] + m_entry + dat[missiles[MISSILE_ID]["end"]:]
    else:
        new_dat = dat[:10] + struct.pack("<H", MISSILE_ID + 1) + dat[12:] + m_entry
    entry = entry_bytes(dat, things[SPEAR_CID], st["light"], ids[0])
    new_dat = new_dat[:target["start"]] + entry + new_dat[target["end"]:]

    things2, _ = read_items(new_dat)
    c2, fx2, mi2 = read_sections(new_dat)
    assert things2[TARGET_CID]["ids"] == [ids[0]] and is_applied(new_dat, things2[TARGET_CID])
    assert all(things2[c]["ids"] == things[c]["ids"] for c in things if c != TARGET_CID)
    assert c2[:3] == counts[:3] and c2[3] == max(counts[3], MISSILE_ID + 1)
    assert [t["ids"] for t in fx2] == [t["ids"] for t in _fx]
    assert [t["ids"] for t in mi2[:MISSILE_ID]] == [t["ids"] for t in missiles[:MISSILE_ID]]
    assert mi2[MISSILE_ID]["ids"] == m_ids
    assert [t["ids"] for t in mi2[MISSILE_ID + 1:]] == [t["ids"] for t in missiles[MISSILE_ID + 1:]]
    _n, off2 = read_spr(new_spr)
    clean = lambda f: [p if p[3] else (0, 0, 0, 0) for p in f]
    for sid, f in zip(ids, own):
        assert decode_sprite(new_spr, off2, sid) == clean(f)
    assert decode_sprite(new_spr, off2, things[SPEAR_CID]["ids"][0]) == base

    for path, data in ((dat_path, new_dat), (spr_path, new_spr)):
        backup = path.with_name(f"{path.name}.bak-enchanted-spear")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_bytes(data)
    verb = "estilo" if item_applied else "agregada con estilo"
    print(f"Enchanted Spear (client id {TARGET_CID}): {verb} '{a.style}', sprite {ids[0]}, luz {LIGHT_LEVEL}/{st['light']}.")
    print(f"Proyectil NM_ANI_ENCHANTED_SPEAR = {MISSILE_ID} "
          f"({'actualizado' if missile_applied else 'agregado'}, sprites {ids[1]}-{ids[-1]} + {ids[0]}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
