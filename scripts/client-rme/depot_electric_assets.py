#!/usr/bin/env python3
"""Instala las 30 piezas eléctricas del depot sin reemplazar paredes originales.

  python3.11 scripts/client-rme/depot_electric_assets.py --prepare
  python3.11 scripts/client-rme/depot_electric_assets.py --things devtools/rme/rme-client-760

--prepare adapta el atlas de ImageGen a 64x64 y aplica la máscara exacta de cada
prototipo: la ventana, los remates y las uniones conservan su geometría 7.6.
La calavera cian recolorea la roja nativa a 11x11, con su alpha exacto. Ver DEPOT_ELECTRICO.md.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT / 'scripts/map'), str(ROOT / 'scripts/map/kb')]

ART = ROOT / 'devtools/zagan-test/custom-sprites/depot-electric'
# Prototipos en el orden exacto de las celdas del atlas (4 columnas, 3 filas).
PROTOTYPES = (1028, 1030, 1032, 1033, 1034, 1035, 1205, 1206, 1207, 1208, 1266)
CLIENT_IDS = (3452, 3451, 3408, 3406, 3405, 3404, 3402, 3401, 3399, 3398, 3397)
WALL_ITEMS = [
    dict(name=('electric depot window' if proto == 1266 else 'electric depot brick wall'),
         server_id=20200 + i, client_id=CLIENT_IDS[i], prototype=proto,
         png=f'depot-electric/wall-{proto}.png', decor=True, tiles=2,
         descr='Electric cyan masonry made exclusively for the city depot.')
    for i, proto in enumerate(PROTOTYPES)
]
# North wing and stair vestibule: retain each original OTB/DAT behavior,
# while sharing the existing cyan textures. Only post/window need extra art.
COMPLETION = ((1037, 1034), (1038, 1027), (1039, 1034), (1041, 1030),
              (1043, 1030), (1044, 1033), (1045, 1034), (1049, 1030),
              (1050, 1034), (1051, 1027), (1053, 1033),
              (1263, 1265), (1264, 1266), (1268, 1266))
WALL_ITEMS += [
    dict(name='electric depot window' if source >= 1263 else 'electric depot brick wall',
         server_id=20420 + i, client_id=5127 + i, prototype=source,
         png=f'depot-electric/wall-{art}' + ('-patterns2' if source in (1049, 1050, 1268) else '') + '.png',
         decor=True, tiles=2, frames=2 if source in (1049, 1050, 1268) else 1,
         descr='Electric cyan masonry made exclusively for the city depot.')
    for i, (source, art) in enumerate(COMPLETION)
]
ROOF_COMPLETION = (1524, 1526, 1527, 1530, 1531)
WALL_ITEMS += [
    dict(name='electric depot stone railing', server_id=20434 + i, client_id=5141 + i,
         prototype=source, png=f'depot-electric/roof-{source}.png', decor=True,
         tiles='2x1' if source == 1524 else '1x2' if source == 1526 else 2,
         frames=2 if source in (1524, 1526, 1527) else 1,
         descr='Electric cyan masonry made exclusively for the city depot.')
    for i, source in enumerate(ROOF_COMPLETION)
]
WALL_MAP = {item['prototype']: item['server_id'] for item in WALL_ITEMS}


def prepare(things: Path) -> None:
    from PIL import Image
    from game_render import Sprites, compose, parse_dat_all
    from mapdata import load_otb
    entries, _ = parse_dat_all(things / 'Tibia.dat')
    spr = Sprites(things / 'Tibia.spr')
    otb = load_otb()
    atlas = Image.open(ART / 'walls-generated.png').convert('RGBA')
    atlas = atlas.resize((256, 192), Image.Resampling.NEAREST)
    for i, proto in enumerate(PROTOTYPES):
        original = compose(entries[otb[proto]['cid']], spr)
        if original.size != (64, 64):
            raise SystemExit(f'{proto}: cambió el tamaño del prototipo')
        x, y = (i % 4) * 64, (i // 4) * 64
        image = atlas.crop((x, y, x + 64, y + 64))
        # El motor solo admite alpha 0/255; conservar la silueta original sin halo.
        image.putalpha(original.getchannel('A'))
        image.save(ART / f'wall-{proto}.png')
    from recolor_cyan_skull import recolor
    skull = recolor(Image.open(ART / 'skull-template-red.png'))
    skull.save(ART / 'skull_cyan.png')
    print(f'Arte preparado: 11 piezas 64x64 y calavera 11x11 en {ART}')


def prepare_completion(things: Path) -> None:
    """Fit the two generated completion cells to the native 7.6 silhouettes."""
    from PIL import Image
    from game_render import Sprites, compose, parse_dat_all
    from mapdata import load_otb
    entries, _ = parse_dat_all(things / 'Tibia.dat')
    sprites, otb = Sprites(things / 'Tibia.spr'), load_otb()
    atlas = Image.open(ART / 'walls-completion-generated.png').convert('RGBA')
    atlas = atlas.resize((256, 128), Image.Resampling.NEAREST)
    for i, proto in enumerate((1027, 1265)):
        image = atlas.crop((i * 64, 0, (i + 1) * 64, 64))
        native = compose(entries[otb[proto]['cid']], sprites)
        assert native.size == image.size == (64, 64)
        # Restore the exact silhouette, including the window opening. Fill any
        # missing generated pixels from its nearest opaque texture pixel.
        opaque = [(x, y) for y in range(64) for x in range(64) if image.getpixel((x, y))[3] >= 128]
        assert opaque
        source = image.copy()
        for y in range(64):
            for x in range(64):
                if native.getpixel((x, y))[3] and source.getpixel((x, y))[3] < 128:
                    near = min(opaque, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
                    image.putpixel((x, y), source.getpixel(near))
        image.putalpha(native.getchannel('A'))
        image.save(ART / f'wall-{proto}.png')
    for proto in (1030, 1034, 1266):
        image = Image.open(ART / f'wall-{proto}.png').convert('RGBA')
        patterns = Image.new('RGBA', (64, 128))
        patterns.paste(image, (0, 0))
        patterns.paste(image, (0, 64))
        patterns.save(ART / f'wall-{proto}-patterns2.png')
    roof = Image.open(ART / 'roof-completion-generated.png').convert('RGBA')
    roof = roof.resize((192, 128), Image.Resampling.NEAREST)
    for i, proto in enumerate(ROOF_COMPLETION):
        native = compose(entries[otb[proto]['cid']], sprites)
        x, y = (i % 3) * 64, (i // 3) * 64
        image = roof.crop((x, y, x + native.width, y + native.height))
        opaque = [(px, py) for py in range(image.height) for px in range(image.width)
                  if image.getpixel((px, py))[3] >= 128]
        assert opaque
        source = image.copy()
        for py in range(image.height):
            for px in range(image.width):
                if native.getpixel((px, py))[3] and source.getpixel((px, py))[3] < 128:
                    near = min(opaque, key=lambda p: (p[0] - px) ** 2 + (p[1] - py) ** 2)
                    image.putpixel((px, py), source.getpixel(near))
        image.putalpha(native.getchannel('A'))
        count = 2 if proto in (1524, 1526, 1527) else 1
        patterns = Image.new('RGBA', (image.width, image.height * count))
        for frame in range(count):
            patterns.paste(image, (0, image.height * frame))
        patterns.save(ART / f'roof-{proto}.png')
    print('Preparados poste, ventana y cinco remates de azotea con máscaras nativas')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--things', type=Path, default=ROOT / 'devtools/rme/rme-client-760')
    ap.add_argument('--otb', type=Path, default=ROOT / 'server/YurOTS/ots/data/items/items-zagan-test.otb')
    ap.add_argument('--prepare', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--complete-only', action='store_true', help='instalar solo las 19 piezas del ala norte/azotea')
    ap.add_argument('--prepare-completion', action='store_true')
    args = ap.parse_args()
    if args.prepare:
        prepare(args.things)
        return 0
    if args.prepare_completion:
        prepare_completion(args.things)
        return 0
    import add_custom_items as A
    _, root = A.load_otb(args.otb)
    for node in root.children:
        sid, cid, _ = A.node_ids(node)
        for item in WALL_ITEMS:
            if sid == item['server_id'] and cid != item['client_id']:
                raise SystemExit(f'ID reservado ocupado: {sid} -> {cid}')
            if sid is not None and sid >= 20100 and cid == item['client_id'] and sid != item['server_id']:
                raise SystemExit(f'Client ID ocupado por otro custom: {cid} -> {sid}')
    A.NEW_ITEMS = [i for i in WALL_ITEMS if not args.complete_only or i['server_id'] >= 20420]
    print('\n'.join(A.apply_things(args.things, root, args.dry_run)))
    print('\n'.join(A.apply_otb(args.otb, args.dry_run)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
