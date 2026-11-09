"""Render "como en el juego" para build-monster-map.py: mosaicos del mapa con sprites y criaturas.

Necesita Pillow (python3 -m pip install pillow). Usa el Tibia.dat/.spr de RME
(devtools/rme/rme-client-760), así que los ítems Zagan que reutilizan ids se ven con el sprite
vanilla (igual que en map-kb).

Mosaicos: t/{z}/{L}/{i}_{j}.webp de 512x512 px. En el nivel L cada casilla mide 32/2^L px y un
mosaico cubre 16*2^L casillas (L0 = tamaño real del juego, L5 = 1 px por casilla).
"""
from __future__ import annotations

import struct
from pathlib import Path

from PIL import Image

from mapdata import DAT, SPR, iter_tiles, load_otb, parse_tree

CHUNK = 16          # casillas por mosaico en L0
LEVELS = 6          # L0..L5
TILE_PX = 512
BG = (10, 10, 13, 255)
DAT_ARGS = {0x00: 2, 0x08: 2, 0x09: 2, 0x15: 4, 0x18: 4, 0x19: 2, 0x1C: 2, 0x1D: 2}
LAYER_RANK = {"ground": 0, "border": 1, "bottom": 2, "common": 3, "top": 4}


# --- Tibia.dat completo (ítems y outfits) ------------------------------------------------------

def _read_thing(d: bytes, pos: int):
    flags = {}
    while True:
        f = d[pos]
        pos += 1
        if f == 0xFF:
            break
        n = DAT_ARGS.get(f, 0)
        flags[f] = d[pos:pos + n]
        pos += n
    w, h = d[pos], d[pos + 1]
    pos += 2
    if w > 1 or h > 1:
        pos += 1
    layers, px, py, pz, frames = d[pos:pos + 5]
    pos += 5
    n = w * h * layers * px * py * pz * frames
    sprites = list(struct.unpack_from(f"<{n}H", d, pos))
    pos += 2 * n
    return dict(flags=flags, w=w, h=h, layers=layers, px=px, py=py, pz=pz, frames=frames, sprites=sprites), pos


def parse_dat_all(path: Path = DAT):
    d = path.read_bytes()
    _sig, ni, no, _ne, _nm = struct.unpack_from("<IHHHH", d, 0)
    pos, items, outfits = 12, {}, {}
    for cid in range(100, ni + 1):
        items[cid], pos = _read_thing(d, pos)
    for look in range(1, no + 1):
        outfits[look], pos = _read_thing(d, pos)
    return items, outfits


def layer_of(e) -> str:
    fl = e["flags"]
    return "ground" if 0x00 in fl else "border" if 0x01 in fl else "bottom" if 0x02 in fl else \
        "top" if 0x03 in fl else "common"


class Sprites:
    def __init__(self, path: Path = SPR):
        self.d = path.read_bytes()
        self.count = struct.unpack_from("<H", self.d, 4)[0]
        self.cache: dict[int, Image.Image | None] = {}

    def get(self, sid: int):
        if sid in self.cache:
            return self.cache[sid]
        img = None
        if 0 < sid <= self.count:
            off = struct.unpack_from("<I", self.d, 6 + (sid - 1) * 4)[0]
            if off:
                buf = bytearray(32 * 32 * 4)
                size = struct.unpack_from("<H", self.d, off + 3)[0]
                p, end, i = off + 5, off + 5 + size, 0
                while p < end and i < 1024:
                    t, c = struct.unpack_from("<HH", self.d, p)
                    p += 4
                    i += t
                    for _ in range(c):
                        if i < 1024:
                            buf[i * 4:i * 4 + 4] = bytes((self.d[p], self.d[p + 1], self.d[p + 2], 255))
                        p += 3
                        i += 1
                img = Image.frombytes("RGBA", (32, 32), bytes(buf))
        self.cache[sid] = img
        return img


def compose(e, spr: Sprites, xp=0, yp=0, layer=None, frame=0) -> Image.Image:
    """Imagen w*32 x h*32 de un thing del .dat (patrón xp, yp; todas las capas o una)."""
    w, h = e["w"], e["h"]
    out = Image.new("RGBA", (w * 32, h * 32), (0, 0, 0, 0))
    layers = range(e["layers"]) if layer is None else [layer]
    for L in layers:
        for hy in range(h):
            for wx in range(w):
                idx = ((((frame * e["pz"]) * e["py"] + yp) * e["px"] + xp) * e["layers"] + L)
                idx = (idx * h + hy) * w + wx
                if idx >= len(e["sprites"]):
                    continue
                im = spr.get(e["sprites"][idx])
                if im is not None:
                    out.alpha_composite(im, ((w - 1 - wx) * 32, (h - 1 - hy) * 32))
    return out


# --- colores de outfit (misma fórmula que el cliente) --------------------------------------------

def outfit_color(color: int) -> tuple[int, int, int]:
    H_STEPS, SI_VALUES = 19, 7
    if color >= H_STEPS * SI_VALUES:
        color = 0
    if color % H_STEPS != 0:
        h = color % H_STEPS / 18.0
        s, i = {0: (0.25, 1.0), 1: (0.25, 0.75), 2: (0.5, 0.75), 3: (0.667, 0.75),
                4: (1.0, 1.0), 5: (1.0, 0.75), 6: (1.0, 0.5)}[color // H_STEPS]
    else:
        h, s, i = 0.0, 0.0, 1 - color / H_STEPS / SI_VALUES
    if i == 0:
        return 0, 0, 0
    if s == 0:
        v = int(i * 255)
        return v, v, v
    if h < 1 / 6:
        r, b = i, i * (1 - s); g = b + (i - b) * 6 * h
    elif h < 2 / 6:
        g, b = i, i * (1 - s); r = g - (i - b) * (6 * h - 1)
    elif h < 3 / 6:
        g, r = i, i * (1 - s); b = r + (i - r) * (6 * h - 2)
    elif h < 4 / 6:
        b, r = i, i * (1 - s); g = b - (i - r) * (6 * h - 3)
    elif h < 5 / 6:
        b, g = i, i * (1 - s); r = g + (i - g) * (6 * h - 4)
    else:
        r, g = i, i * (1 - s); b = r - (i - g) * (6 * h - 5)
    return int(r * 255), int(g * 255), int(b * 255)


def creature_image(look: dict, outfits: dict, spr: Sprites) -> Image.Image | None:
    """Criatura mirando al sur, cuadro 0, con colores de outfit si tiene máscara."""
    e = outfits.get(look.get("type", 0))
    if not e or not any(e["sprites"]):
        return None
    south = 2 if e["px"] >= 4 else 0
    base = compose(e, spr, south, 0, layer=0)
    if e["layers"] >= 2:
        mask = compose(e, spr, south, 0, layer=1)
        cols = {(255, 255, 0): outfit_color(look.get("head", 0)), (255, 0, 0): outfit_color(look.get("body", 0)),
                (0, 255, 0): outfit_color(look.get("legs", 0)), (0, 0, 255): outfit_color(look.get("feet", 0))}
        bp, mp = base.load(), mask.load()
        for y in range(base.height):
            for x in range(base.width):
                m = mp[x, y]
                if m[3] and m[:3] in cols:
                    c, p = cols[m[:3]], bp[x, y]
                    bp[x, y] = (p[0] * c[0] // 255, p[1] * c[1] // 255, p[2] * c[2] // 255, p[3])
    return base


# --- mosaicos del mapa -------------------------------------------------------------------------

def render_tiles(map_path: Path, out: Path, log=print) -> dict:
    otb = load_otb()
    items, _ = parse_dat_all()
    spr = Sprites()
    entry = {sid: items.get(e.get("cid")) for sid, e in otb.items() if e.get("cid")}
    cache: dict[tuple, Image.Image] = {}

    def item_img(sid, x, y):
        e = entry.get(sid)
        if e is None:
            return None, None
        key = (sid, x % e["px"], y % e["py"])
        im = cache.get(key)
        if im is None:
            im = cache[key] = compose(e, spr, key[1], key[2])
        return im, e

    floors: dict[int, dict] = {}
    for x, y, z, its in iter_tiles(parse_tree(map_path.read_bytes())):
        floors.setdefault(z, {})[(x, y)] = its

    index: dict[str, dict[str, list[str]]] = {}
    for z, tiles in sorted(floors.items()):
        chunks = {(x // CHUNK, y // CHUNK) for (x, y) in tiles}
        zdir = out / "t" / str(z)
        for L in range(LEVELS):
            (zdir / str(L)).mkdir(parents=True, exist_ok=True)
        done = []
        for (ci, cj) in sorted(chunks):
            x0, y0 = ci * CHUNK, cj * CHUNK
            M = 2  # los ítems grandes se dibujan hacia arriba-izquierda: incluir 2 casillas de más
            canvas = Image.new("RGBA", ((CHUNK + M) * 32, (CHUNK + M) * 32), BG)
            for ty in range(y0, y0 + CHUNK + M):
                for tx in range(x0, x0 + CHUNK + M):
                    its = tiles.get((tx, ty))
                    if not its:
                        continue
                    draw = []
                    for sid in its:
                        im, e = item_img(sid, tx, ty)
                        if im is not None:
                            draw.append((LAYER_RANK[layer_of(e)], im, e))
                    draw.sort(key=lambda t: t[0])
                    elev = 0
                    for _r, im, e in draw:
                        dx = dy = 0
                        if 0x18 in e["flags"]:
                            dx, dy = struct.unpack("<HH", e["flags"][0x18])
                        px = (tx - x0) * 32 - (e["w"] - 1) * 32 - dx - elev
                        py = (ty - y0) * 32 - (e["h"] - 1) * 32 - dy - elev
                        canvas.paste(im, (px, py), im)
                        if 0x19 in e["flags"]:
                            elev = min(24, elev + struct.unpack("<H", e["flags"][0x19])[0])
            tile = canvas.crop((0, 0, CHUNK * 32, CHUNK * 32)).convert("RGB")
            tile.save(zdir / "0" / f"{ci}_{cj}.webp", quality=80, method=4)
            done.append((ci, cj))
        idx = {"0": [f"{i}_{j}" for i, j in done]}
        prev = set(done)
        for L in range(1, LEVELS):
            parents = {(i // 2, j // 2) for i, j in prev}
            for (pi, pj) in parents:
                big = Image.new("RGB", (TILE_PX * 2, TILE_PX * 2), BG[:3])
                for di in (0, 1):
                    for dj in (0, 1):
                        c = (pi * 2 + di, pj * 2 + dj)
                        if c in prev:
                            big.paste(Image.open(zdir / str(L - 1) / f"{c[0]}_{c[1]}.webp"), (di * TILE_PX, dj * TILE_PX))
                big.reduce(2).save(zdir / str(L) / f"{pi}_{pj}.webp", quality=80, method=4)
            idx[str(L)] = [f"{i}_{j}" for i, j in sorted(parents)]
            prev = parents
        index[str(z)] = idx
        log(f"  z{z}: {len(done)} mosaicos L0")
    return {"chunk": CHUNK, "levels": LEVELS, "px": TILE_PX, "index": index}


def render_creatures(looks: dict[str, dict], out: Path) -> dict[str, dict]:
    """looks: nombre -> {type, head, body, legs, feet}. Devuelve nombre -> {img, w, h}."""
    _, outfits = parse_dat_all()
    spr = Sprites()
    (out / "look").mkdir(parents=True, exist_ok=True)
    res = {}
    for name, look in looks.items():
        im = creature_image(look, outfits, spr)
        if im is None:
            continue
        slug = "".join(ch if ch.isalnum() else "-" for ch in name.lower())
        im.save(out / "look" / f"{slug}.png")
        res[name] = {"img": f"look/{slug}.png", "w": im.width // 32, "h": im.height // 32}
    return res
