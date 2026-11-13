#!/usr/bin/env python3
"""Trae criaturas (looktypes) de otro cliente de Tibia a nuestro Tibia.dat / Tibia.spr.

Para sumar monstruos de versiones nuevas (piratas, wyvern, dragon hatchling, mutated...) con su dibujo
original: copia los sprites tal cual, sin recolorear. Se probó con el cliente 8.60.

  # hoja con todos los looks del otro cliente, para encontrar el número
  python3.11 scripts/client-rme/import_client_look.py --catalog /tmp/looks.png
  # hoja de lo que se va a importar (4 direcciones x cuadros de animación)
  python3.11 scripts/client-rme/import_client_look.py --sheet /tmp/import.png
  # importar (agrega lo que falte; lo que ya está no se toca)
  python3.11 scripts/client-rme/import_client_look.py --apply

Qué va en IMPORTS: nombre, `source` (looktype en el otro cliente) y `target` (looktype libre en el nuestro;
`sprite_tool.py looks` los lista). El protocolo 7.6 manda el looktype en un byte: el destino no pasa de 255.

Cómo funciona: la entrada del .dat (flags, tamaño, direcciones, cuadros) se copia igual, porque el formato
de 7.6 y el de 8.60 comparten esos campos y los flags que usan las criaturas (24 = corrimiento, 27 = animar
siempre). Los sprites se agregan al final del .spr con ids nuevos. Solo se aceptan criaturas sin addons ni
monturas (patrón Y y Z en 1). El cliente de origen (--client, por omisión devtools/tibia-860) no va a git.
Doc: docs/gameplay/IMPORTAR_CRIATURA_DE_OTRA_VERSION.md.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from add_black_dragon_look import _skip_attr, decode_sprite, read_outfits, read_spr, write_spr  # noqa: E402
from add_recolor_look import sprite_record  # noqa: E402

CLIENT = REPO / "devtools/tibia-860"
THINGS = REPO / "devtools/rme/rme-client-760"

# Los piratas conservan su número de 8.60 (93, 96-98 estaban vacíos en 7.6). El resto pasa de 255 en 8.60.
IMPORTS = [
    dict(name="Pirate Marauder", source=93, target=93),
    dict(name="Pirate Cutthroat", source=96, target=96),
    dict(name="Pirate Buccaneer", source=97, target=97),
    dict(name="Pirate Corsair", source=98, target=98),
    dict(name="Wyvern", source=239, target=245),
    dict(name="Dragon Hatchling", source=271, target=246),
    dict(name="Dragon Lord Hatchling", source=272, target=247),
    dict(name="Mutated Human", source=323, target=248),
    dict(name="Mutated Rat", source=305, target=249),
    dict(name="Mutated Bat", source=307, target=250),
    dict(name="Mutated Tiger", source=318, target=251),
    # Isla del Hielo Eterno y Bog Raider (nov 2026): destinos 161-174, libres en 7.6 y en 8.60.
    dict(name="Chakoya Tribewarden", source=260, target=161),
    dict(name="Chakoya Toolshaper", source=259, target=162),
    dict(name="Chakoya Windcaller", source=249, target=163),
    dict(name="Husky", source=258, target=164),
    dict(name="Barbarian Headsplitter", source=253, target=165),
    dict(name="Barbarian Skullhunter", source=254, target=166),
    dict(name="Barbarian Brutetamer", source=264, target=167),
    dict(name="Barbarian Bloodwalker", source=255, target=168),
    dict(name="Frost Giant", source=257, target=169),
    dict(name="Frost Giantess", source=265, target=170),
    dict(name="Ice Golem", source=261, target=171),
    dict(name="Crystal Spider", source=263, target=172),
    dict(name="Frost Dragon Hatchling", source=283, target=173),
    dict(name="Bog Raider", source=295, target=174),
    # Resto del catalogo 8.60 (nov 2026): criaturas que faltaban.
    dict(name="Tortoise", source=197, target=197),
    dict(name="Thornback Tortoise", source=198, target=198),
    dict(name="Mammoth", source=199, target=199),
    dict(name="Blood Crab", source=200, target=200),
    dict(name="Quara Constrictor", source=20, target=20),
    dict(name="Quara Hydromancer", source=46, target=46),
    dict(name="Quara Mantassin", source=47, target=47),
    dict(name="Quara Pincher", source=72, target=72),
    dict(name="Quara Predator", source=77, target=77),
    dict(name="Cyclops Smith", source=277, target=175),
    dict(name="Cyclops Drone", source=280, target=176),
    dict(name="Wyrm", source=291, target=177),
    dict(name="Earth Elemental", source=301, target=178),
    dict(name="Water Elemental", source=286, target=179),
    dict(name="Zombie", source=311, target=180),
    dict(name="Vampire Bride", source=312, target=181),
    dict(name="Worker Golem", source=304, target=182),
    dict(name="Undead Gladiator", source=306, target=183),
    dict(name="Nightstalker", source=320, target=184),
]


def load(folder: Path) -> dict:
    dat, spr = (folder / "Tibia.dat").read_bytes(), (folder / "Tibia.spr").read_bytes()
    outfits, counts = read_outfits(dat)
    _n, offsets = read_spr(spr)
    return dict(dat=dat, spr=spr, outfits=outfits, counts=counts, offsets=offsets, folder=folder)


def shape(things: dict, look: int) -> tuple[int, int, int, int, int, int, int]:
    """(ancho, alto, capas, direcciones, patrón Y, patrón Z, cuadros) de un looktype."""
    d, p = things["dat"], things["outfits"][look - 1]["start"]
    while d[p] != 0xFF:
        p = _skip_attr(d, p + 1, 252 if d[p] == 23 else d[p])
    p += 1
    w, h = d[p], d[p + 1]
    p += 2 + (1 if w > 1 or h > 1 else 0)
    return (w, h, *d[p:p + 5])


def frame(things: dict, look: int, direction: int = 2, anim: int = 0):
    """Imagen de un cuadro (por omisión mirando al sur), o None si el look está vacío."""
    from PIL import Image
    ids = things["outfits"][look - 1]["ids"]
    w, h, layers, px, py, pz, an = shape(things, look)
    if not any(ids):
        return None
    img = Image.new("RGBA", (w * 32, h * 32))
    for hy in range(h):
        for wx in range(w):
            idx = (((anim % an) * pz * py * px + (direction if px >= 4 else 0)) * layers * h + hy) * w + wx
            sp = Image.new("RGBA", (32, 32))
            sp.putdata(decode_sprite(things["spr"], things["offsets"], ids[idx]))
            img.alpha_composite(sp, ((w - 1 - wx) * 32, (h - 1 - hy) * 32))
    return img


def catalog(things: dict, out: Path) -> None:
    from PIL import Image, ImageDraw
    n, cols, cw, ch = len(things["outfits"]), 16, 92, 88
    sheet = Image.new("RGBA", (cols * cw, ((n + cols - 1) // cols) * ch), (58, 78, 84, 255))
    draw = ImageDraw.Draw(sheet)
    for i in range(n):
        x, y = (i % cols) * cw, (i // cols) * ch
        img = frame(things, i + 1)
        if img is not None:
            sheet.alpha_composite(img if img.width == 64 else img.resize((64, 64), Image.NEAREST), (x + 14, y + 2))
        draw.text((x + 4, y + 70), str(i + 1), fill=(255, 255, 255, 255))
    sheet.save(out)


def sheet(things: dict, looks: list[tuple[str, int]], out: Path) -> None:
    """Una fila por criatura: norte, este, sur, oeste de cada cuadro de animación."""
    from PIL import Image, ImageDraw
    cell, label = 72, 170
    cols = max(shape(things, look)[6] for _n, look in looks) * 4
    img = Image.new("RGBA", (label + cols * cell, len(looks) * cell), (58, 78, 84, 255))
    draw = ImageDraw.Draw(img)
    for row, (name, look) in enumerate(looks):
        w, h, _l, _px, _py, _pz, an = shape(things, look)
        draw.text((6, row * cell + 20), name, fill=(255, 255, 255, 255))
        draw.text((6, row * cell + 36), f"look {look} · {w}x{h} · {an} cuadros", fill=(190, 210, 215, 255))
        for a in range(an):
            for d in range(4):
                f = frame(things, look, d, a)
                if f is not None:
                    img.alpha_composite(f, (label + (a * 4 + d) * cell + (cell - f.width) // 2, row * cell + (cell - f.height) // 2))
    img.save(out)


def apply(client: dict, ours: dict, dry: bool) -> int:
    dat, spr, offsets = ours["dat"], ours["spr"], ours["offsets"]
    count = len(offsets)
    records, patches, log = [], [], []
    for item in IMPORTS:
        src_look, dst_look, name = item["source"], item["target"], item["name"]
        if dst_look > 255:
            raise SystemExit(f"{name}: el destino {dst_look} pasa de 255 (el protocolo 7.6 no lo puede mandar)")
        if dst_look > len(ours["outfits"]):
            raise SystemExit(f"{name}: nuestro .dat tiene {len(ours['outfits'])} looks; no existe el {dst_look}")
        src, dst = client["outfits"][src_look - 1], ours["outfits"][dst_look - 1]
        w, h, layers, px, py, pz, an = shape(client, src_look)
        if py != 1 or pz != 1 or px != 4:
            raise SystemExit(f"{name}: look {src_look} con addons o montura (patrones {px}x{py}x{pz}); no se importa")
        pixels = [decode_sprite(client["spr"], client["offsets"], sid) for sid in src["ids"]]
        if any(dst["ids"]):
            same = len(dst["ids"]) == len(pixels) and all(
                decode_sprite(spr, offsets, sid) == pixels[i] for i, sid in enumerate(dst["ids"]))
            if not same:
                raise SystemExit(f"{name}: el look {dst_look} ya tiene otros sprites; elegir otro destino")
            log.append(f"  {name}: ya está en el look {dst_look}")
            continue
        new_ids = []
        for sid in src["ids"]:
            rec = sprite_record(client["spr"], client["offsets"], sid)
            if not rec:
                new_ids.append(0)
                continue
            records.append(rec)
            new_ids.append(count + len(records))
        prefix = client["dat"][src["start"]:src["sprite_pos"]]
        patches.append((dst["start"], dst["end"], prefix + struct.pack(f"<{len(new_ids)}H", *new_ids), dst_look, new_ids, pixels))
        log.append(f"  {name}: look {src_look} -> {dst_look} ({w}x{h}, {an} cuadros, {sum(1 for i in new_ids if i)} sprites)")
    print("\n".join(log))
    if not patches:
        print("nada para importar")
        return 0
    new_dat = dat
    for start, end, entry, *_rest in sorted(patches, reverse=True):
        new_dat = new_dat[:start] + entry + new_dat[end:]
    new_spr = write_spr(struct.unpack_from("<I", spr, 0)[0], offsets, spr, records)
    check, counts = read_outfits(new_dat)                       # se lee entero y cada look quedó como se pidió
    _n, new_offsets = read_spr(new_spr)
    assert counts == ours["counts"]
    for _s, _e, _entry, look, ids, pixels in patches:
        assert check[look - 1]["ids"] == ids
        assert all(decode_sprite(new_spr, new_offsets, sid) == pixels[i] for i, sid in enumerate(ids))
    print(f"sprites: {count} -> {count + len(records)}")
    if dry:
        print("dry-run: no se escribió nada")
        return 0
    (ours["folder"] / "Tibia.dat").write_bytes(new_dat)
    (ours["folder"] / "Tibia.spr").write_bytes(new_spr)
    print(f"escrito {ours['folder']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", type=Path, default=CLIENT, help="carpeta con el Tibia.dat y Tibia.spr de origen")
    ap.add_argument("--things", type=Path, default=THINGS, help="carpeta con nuestro Tibia.dat y Tibia.spr")
    ap.add_argument("--catalog", type=Path, help="hoja con todos los looks del cliente de origen")
    ap.add_argument("--sheet", type=Path, help="hoja de los looks de IMPORTS, tomados del cliente de origen")
    ap.add_argument("--check", type=Path, help="hoja de los looks de IMPORTS, ya en nuestro cliente")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.check:
        sheet(load(a.things), [(i["name"], i["target"]) for i in IMPORTS], a.check)
        print(f"hoja: {a.check}")
    if not (a.catalog or a.sheet or a.apply or a.dry_run):
        if not a.check:
            ap.print_help()
        return 0
    if not (a.client / "Tibia.dat").exists():
        raise SystemExit(f"falta el cliente de origen en {a.client} (Tibia.dat y Tibia.spr)")
    client = load(a.client)
    if a.catalog:
        catalog(client, a.catalog)
        print(f"catálogo: {a.catalog}")
    if a.sheet:
        sheet(client, [(i["name"], i["source"]) for i in IMPORTS], a.sheet)
        print(f"hoja: {a.sheet}")
    if a.apply or a.dry_run:
        return apply(client, load(a.things), dry=not a.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
