#!/usr/bin/env python3
"""Cadáveres propios para los monstruos nuevos: el cadáver de 7.6 más parecido, con los colores de la criatura.

Dos formas, según de dónde sale el sprite de la criatura:
  - preset (recoloreados nuestros, presets/*.py): el cadáver del monstruo base pasa por la misma
    receta del preset (`recolor`, o `parts` + `palettes`), así el muerto combina con el vivo.
  - look (criaturas traídas de 8.60 sin cadáver propio): se toma un cadáver de 7.6 de forma parecida y
    se le pasa la gama de colores del sprite (luminosidad del cadáver -> colores del look ordenados por
    luz). La sangre roja se deja igual.

  python3.11 scripts/client-rme/creature_corpses.py [--preview /tmp/cadaveres.png] [--only NOMBRE ...]
  python3.11 scripts/client-rme/creature_corpses.py --entries   # líneas para NEW_ITEMS de add_custom_items.py

Escribe los PNG en devtools/zagan-test/custom-sprites/ (64x64, 64x32 o 32x32 según el cadáver base) y
add_custom_items.py los instala (corpse=True). Doc: docs/gameplay/MONSTRUOS.md#cadáveres.
"""
from __future__ import annotations

import argparse
import colorsys
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(HERE / "presets")]
import add_custom_items as A  # noqa: E402
import build_zagan_test_assets as B  # noqa: E402
from add_black_dragon_look import decode_sprite  # noqa: E402
from add_recolor_look import PRESETS, load_things  # noqa: E402
from sprite_kit import gradient, luma, palette_recolor, stops_of  # noqa: E402

THINGS = ROOT / "devtools/rme/rme-client-760"
OTB = ROOT / "server/YurOTS/ots/data/items/items-zagan-test.otb"
OUT = A.SPRITES

NEON_CYAN = [(0, 70, 96), (0, 190, 236), (150, 248, 255)]
NEON_GREEN = [(16, 90, 10), (70, 230, 40), (200, 255, 150)]

# name, server id, client id sacrificado, cadáver base (server id), fuente, monstruos que lo usan, extra.
# fuente: ("preset", nombre) o ("look", looktype). extra: paletas que cambian respecto del preset.
CORPSES = [
    # --- recoloreados con preset ---
    ("metal dragon corpse", 20225, 3242, 3104, ("preset", "metal-dragon"), ["Metal Dragon"], {"eyes": NEON_CYAN}),
    ("metal hydra corpse", 20226, 3216, 4283, ("preset", "metal-hydra"), ["Metal Hydra"], {"eyes": NEON_GREEN}),
    ("metal demon corpse", 20227, 3234, 2916, ("preset", "metal-demon"), ["Metal Demon"],
     {"seams": [(140, 0, 10), (255, 40, 40)]}),
    ("dead hellhound", 20228, 3202, 2969, ("preset", "hellhound"), ["Hellhound"], {}),
    ("dead dark hydra", 20229, 3201, 4283, ("preset", "dark-hydra"), ["Dark Hydra"], {}),
    ("dead emerald scarab", 20230, 3196, 3004, ("preset", "emerald-scarab"), ["Emerald Scarab"], {}),
    ("remains of a root colossus", 20231, 3194, 2931, ("preset", "root-colossus"), ["Root Colossus"], {}),
    ("dead red kongra", 20232, 3193, 4268, ("preset", "red-kongra"), ["Red Kongra"], {}),
    ("dead river troll", 20233, 3186, 2806, ("preset", "river-troll"), ["River Troll"], {}),
    ("dead stone troll", 20234, 3185, 2806, ("preset", "stone-troll"), ["Stone Troll"], {}),
    ("dead thornwarden", 20235, 3184, 4280, ("preset", "thornwarden"), ["Thornwarden"], {}),
    ("dead orc warchief", 20236, 3181, 2967, ("preset", "orc-warchief"), ["Orc Warchief"], {}),
    ("dead elvenbane ranger", 20237, 3175, 2981, ("preset", "elvenbane-ranger"), ["Elvenbane Ranger"], {}),
    ("dead elven archmage", 20238, 3171, 2979, ("preset", "elven-archmage"), ["Elven Archmage"], {}),
    ("dead imperial hero", 20239, 3170, 3128, ("preset", "imperial-hero"), ["Imperial Hero"], {}),
    ("dead lord of elvenbane", 20240, 3169, 3128, ("preset", "lord-of-elvenbane"), ["Lord of Elvenbane"], {}),
    ("ashes of the ashen lord", 20241, 3168, 2916, ("preset", "ashen-lord"), ["Ashen Lord"], {}),
    ("remains of the fallen emperor", 20242, 3167, 3025, ("preset", "fallen-emperor"), ["The Fallen Emperor"], {}),
    # --- criaturas de 8.60: cadáver de 7.6 parecido con los colores del look ---
    ("dead chakoya", 20243, 3163, 3113, ("look", 161), ["Chakoya Tribewarden", "Chakoya Toolshaper",
                                                         "Chakoya Windcaller"], {}),
    ("dead frost giant", 20244, 3162, 3069, ("look", 169), ["Frost Giant", "Frost Giantess"], {}),
    ("remains of an ice golem", 20245, 3161, 2952, ("look", 171), ["Ice Golem"], {}),
    ("dead crystal spider", 20246, 3159, 2857, ("look", 172), ["Crystal Spider"], {}),
    ("dead bog raider", 20247, 3231, 2824, ("look", 174), ["Bog Raider"], {}),
    ("dead wyvern", 20248, 3218, 3104, ("look", 245), ["Wyvern"], {}),
    ("dead husky", 20249, 3209, 2839, ("look", 164), ["Husky"], {}),
]
# Sin cadáver nuevo: ya hay uno que sirve.
POINT_ONLY = {"Frost Dragon Hatchling": 20171,   # el del Frost Dragon
              "Dark Monk": 3128}                  # usaba el del Demon (2916): un monje muere como humano
# Se probaron y salen casi iguales a su cadáver de 7.6 (mismos colores): siguen con ese.
SAME_COLORS = {"Mutated Human": 3113, "Mutated Rat": 2813, "Mutated Bat": 4298, "Mutated Tiger": 4292,
               "Dragon Hatchling": 3104, "Dragon Lord Hatchling": 2881}


def png_name(name: str) -> str:
    return name.replace(" ", "_") + ".png"


def client_ids() -> dict[int, int]:
    _data, root = A.load_otb(OTB)
    out = {}
    for node in root.children:
        sid, cid, _name = A.node_ids(node)
        if sid:
            out[sid] = cid
    return out


def corpse_image(things: dict, entries, client_id: int):
    """El cadáver base: (ancho, alto, píxeles). 1 sprite = 32x32; 2 = 64x32 (der, izq); 4 = 64x64
    (abajo-der, abajo-izq, arriba-der, arriba-izq), el orden del .dat."""
    ids = entries[client_id - 100].sprite_ids
    tiles = [decode_sprite(things["spr"], things["offsets"], s) for s in ids]
    layout = {1: (32, 32, [(0, 0)]), 2: (64, 32, [(32, 0), (0, 0)]),
              4: (64, 64, [(32, 32), (0, 32), (32, 0), (0, 0)])}
    if len(tiles) not in layout:
        raise SystemExit(f"client {client_id}: {len(tiles)} sprites (solo 1, 2 o 4)")
    w, h, offs = layout[len(tiles)]
    img = [(0, 0, 0, 0)] * (w * h)
    for tile, (ox, oy) in zip(tiles, offs):
        for i, p in enumerate(tile):
            img[(oy + i // 32) * w + ox + i % 32] = p
    return w, h, img


def look_palette(things: dict, look: int):
    """Gama del look: sus colores (sin contorno) ordenados por luz, en 7 escalones."""
    ids = things["outfits"][look - 1]["ids"]
    pixels = [p for sid in ids for p in decode_sprite(things["spr"], things["offsets"], sid) if p[3]]
    body = sorted((p for p in pixels if max(p[:3]) > 30), key=luma)
    qs = (0.02, 0.15, 0.32, 0.5, 0.68, 0.85, 0.985)
    return [(q, body[int(q * (len(body) - 1))][:3]) for q in qs]


def is_blood(p) -> bool:
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in p[:3]))
    return (h < 0.035 or h > 0.96) and s > 0.6 and v > 0.3


def recolor_by_look(img, stops):
    lumas = sorted(luma(p) for p in img if p[3] and not is_blood(p))
    lo, hi = lumas[int(0.01 * len(lumas))], lumas[int(0.99 * len(lumas)) - 1]
    out = []
    for p in img:
        if not p[3] or is_blood(p):
            out.append(p)
            continue
        k = min(1.0, max(0.0, (luma(p) - lo) / (hi - lo))) if hi > lo else 0.5
        out.append(gradient(stops, k) + (255,))
    return out


def build(things, entries, cids, row):
    name, _sid, _cid, base, (kind, src), _monsters, extra = row
    w, h, img = corpse_image(things, entries, cids[base])
    if kind == "preset":
        p = PRESETS[src]
        recolor = p.get("recolor") or palette_recolor(p["parts"], {**p["palettes"], **extra}, [img])
        new = [recolor(px) if px[3] else px for px in img]
    else:
        new = recolor_by_look(img, look_palette(things, src))
    image = B.Image.new("RGBA", (w, h))
    image.putdata([tuple(px) for px in new])
    image.save(OUT / png_name(name))
    orig = B.Image.new("RGBA", (w, h))
    orig.putdata(img)
    return orig, image


def descr(name: str, monster: str) -> str:
    if name.startswith(("remains", "ashes")):
        return f"The {name}."
    return f"The corpse of {'an' if monster[0] in 'AEIOU' else 'a'} {monster.lower()}."


def entries_text(skip=()) -> str:
    lines = []
    for name, sid, cid, base, _src, monsters, _extra in CORPSES:
        if name in skip:
            continue
        lines.append(f'    dict(name="{name}", server_id={sid}, client_id={cid}, prototype={base},\n'
                     f'         png="{png_name(name)}", corpse=True, tiles=TILES_{sid},\n'
                     f'         descr="{descr(name, monsters[0])}"),')
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", type=Path, help="hoja: arriba el cadáver base, abajo el nuevo, x3")
    ap.add_argument("--only", nargs="+", help="nombres de cadáver")
    ap.add_argument("--entries", action="store_true", help="imprimir las líneas para NEW_ITEMS")
    a = ap.parse_args()
    things = load_things(THINGS)
    entries, _tail = B.DatReader(things["dat"]).read_item_entries()
    cids = client_ids()
    rows = [r for r in CORPSES if not a.only or r[0] in a.only]
    if a.entries:
        text = entries_text(skip=("metal dragon corpse", "metal hydra corpse", "metal demon corpse"))
        for row in CORPSES:
            w, h, _img = corpse_image(things, entries, cids[row[3]])
            text = text.replace(f"TILES_{row[1]}", {(64, 64): "2", (64, 32): '"2x1"', (32, 32): "1"}[(w, h)])
        print(text)
        return 0
    pairs = []
    for row in rows:
        pairs.append(build(things, entries, cids, row))
        print(f"{png_name(row[0])}: base {row[3]}, {row[4][0]} {row[4][1]}")
    if a.preview:
        cols = 10
        n_rows = (len(pairs) + cols - 1) // cols
        sheet = B.Image.new("RGBA", (64 * cols, 128 * n_rows), (40, 48, 52, 255))
        for i, (orig, new) in enumerate(pairs):
            x, y = 64 * (i % cols), 128 * (i // cols)
            sheet.alpha_composite(orig, (x + 64 - orig.width, y + 64 - orig.height))
            sheet.alpha_composite(new, (x + 64 - new.width, y + 128 - new.height))
        sheet.resize((sheet.width * 3, sheet.height * 3), B.Image.NEAREST).save(a.preview)
        print(f"hoja: {a.preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
