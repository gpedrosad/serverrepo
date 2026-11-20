#!/usr/bin/env python3
"""Prepara e instala 11 piezas exclusivas para la plaza arcana de teleports.

  python3.11 scripts/client-rme/portal_citadel_assets.py --prepare --apply
  python3.11 scripts/client-rme/portal_citadel_assets.py           # dry-run

Las murallas usan las máscaras nativas exactas; no se reemplazan las del depot.
Fuentes y prompts: custom-sprites/portal-citadel/. Ver PLAZA_ARCANA.md.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from lib.project_root import project_root
import add_custom_items as A

ROOT = project_root(HERE)
ART = ROOT / 'devtools/zagan-test/custom-sprites/portal-citadel'
FLOOR, CONDUIT, DAIS = 20214, 20215, 20216
POST, HORIZONTAL, VERTICAL, CORNER, WINDOW_H, WINDOW_V = range(20217, 20223)
BEACON, OBELISK = 20223, 20224
PROTOTYPES = (1027,1028,1030,1033,1265,1266)
CLIENT_IDS = (3379,3368,3365,3363,3342,3253,3247,3246,3245,3244,3243)
ITEMS = [
    dict(name='arcane basalt paving', server_id=FLOOR, prototype=965, png='basalt.png'),
    dict(name='arcane conduit paving', server_id=CONDUIT, prototype=965, png='conduit.png'),
    dict(name='arcane portal foundation', server_id=DAIS, prototype=965, png='dais.png'),
] + [dict(name='arcane tower window' if sid in (WINDOW_H,WINDOW_V) else 'arcane tower wall',
          server_id=sid, prototype=proto, png=f'wall-{proto}.png',tiles=2)
     for sid,proto in zip(range(POST,WINDOW_V+1),PROTOTYPES)] + [
    dict(name='arcane crystal beacon', server_id=BEACON, prototype=1445, png='beacon.png', tiles=2, light=(6,71)),
    dict(name='arcane rune obelisk', server_id=OBELISK, prototype=1445, png='obelisk.png', tiles=2, light=(4,71)),
]
for item,cid in zip(ITEMS,CLIENT_IDS):
    item.update(client_id=cid,decor=True,descr='Basalt and electric cyan stonework made for the teleport plaza.')
    item['png']='portal-citadel/'+item['png']


def prepare():
    from PIL import Image
    atlas=Image.open(ART/'walls-generated.png').convert('RGBA').resize((192,128),Image.Resampling.NEAREST)
    for i,proto in enumerate(PROTOTYPES):
        x,y=(i%3)*64,(i//3)*64
        piece=atlas.crop((x,y,x+64,y+64))
        piece.putalpha(Image.open(ART/f'template-{proto}.png').getchannel('A'))
        piece.save(ART/f'wall-{proto}.png')
    for name in ('basalt','conduit','dais'):
        im=Image.open(ART/f'{name}-generated.png').convert('RGB').resize((32,32),Image.Resampling.NEAREST)
        im.convert('RGBA').save(ART/f'{name}.png')
    for name in ('beacon','obelisk'):
        im=Image.open(ART/f'{name}-generated.png').convert('RGBA')
        alpha=im.getchannel('A').point(lambda a:255 if a>=128 else 0)
        im.putalpha(alpha)
        crop=im.crop(alpha.getbbox())
        # Mantener la proporción y un margen de 3 px; el pie apoya abajo del sprite.
        factor=min(58/crop.width,58/crop.height)
        crop=crop.resize((round(crop.width*factor),round(crop.height*factor)),Image.Resampling.NEAREST)
        out=Image.new('RGBA',(64,64));out.alpha_composite(crop,((64-crop.width)//2,61-crop.height))
        out.save(ART/f'{name}.png')
    print('Arte preparado: 3 pisos, 6 murallas, beacon y obelisco')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--things',type=Path,default=ROOT/'devtools/rme/rme-client-760')
    ap.add_argument('--otb',type=Path,default=ROOT/'server/YurOTS/ots/data/items/items-zagan-test.otb')
    ap.add_argument('--prepare',action='store_true')
    ap.add_argument('--apply',action='store_true')
    args=ap.parse_args()
    if args.prepare:prepare()
    _,root=A.load_otb(args.otb)
    nodes={A.node_ids(n)[0]:n for n in root.children}
    for item in ITEMS:
        node=nodes.get(item['server_id'])
        if node and A.node_ids(node)[1:]!=(item['client_id'],item['name']):
            raise SystemExit(f'ID ocupado: {item["server_id"]}')
        if any(A.node_ids(n)[0]>=20100 and A.node_ids(n)[1]==item['client_id']
               and A.node_ids(n)[0]!=item['server_id'] for n in root.children if A.node_ids(n)[0]):
            raise SystemExit(f'Client ID ocupado: {item["client_id"]}')
    free={r[0] for r in A.candidates(args.things,args.otb,exclude_paths=(__file__,))}
    if any(i['server_id'] not in nodes and i['client_id'] not in free for i in ITEMS):
        raise SystemExit('Un client ID ya tiene usos en el proyecto')
    A.NEW_ITEMS=ITEMS
    print('\n'.join(A.apply_things(args.things,root,not args.apply)))
    print('\n'.join(A.apply_otb(args.otb,not args.apply)))


if __name__=='__main__':main()
