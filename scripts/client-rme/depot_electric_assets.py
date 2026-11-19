#!/usr/bin/env python3
"""Instala las 11 piezas eléctricas del depot sin reemplazar paredes originales.

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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--things', type=Path, default=ROOT / 'devtools/rme/rme-client-760')
    ap.add_argument('--otb', type=Path, default=ROOT / 'server/YurOTS/ots/data/items/items-zagan-test.otb')
    ap.add_argument('--prepare', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    if args.prepare:
        prepare(args.things)
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
    A.NEW_ITEMS = WALL_ITEMS  # usar el importador canónico solo para esta familia
    print('\n'.join(A.apply_things(args.things, root, args.dry_run)))
    print('\n'.join(A.apply_otb(args.otb, args.dry_run)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
