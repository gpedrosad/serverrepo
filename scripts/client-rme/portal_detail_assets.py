#!/usr/bin/env python3
"""Entrada, faroles y rejas del templo arcano; sin --apply solo prepara el plan."""
import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from lib.project_root import project_root
import add_custom_items as A

ROOT = project_root(HERE)
ART = ROOT/'devtools/zagan-test/custom-sprites/portal-details'
ITEMS = [
    dict(name='arcane entrance left', server_id=20253, client_id=3229, prototype=1120,
         png='entrance-left.png', tiles=2, light=(3,71)),
    dict(name='arcane entrance right', server_id=20254, client_id=3228, prototype=1121,
         png='entrance-right.png', tiles=2, light=(3,71)),
    dict(name='arcane crystal lantern', server_id=20255, client_id=3227, prototype=1480,
         png='streetlamp.png', tiles=2, frames=2, light=(7,71)),
    dict(name='arcane railing vertical', server_id=20256, client_id=3226, prototype=1543,
         png='rail-vertical.png', tiles=2),
    dict(name='arcane railing horizontal', server_id=20257, client_id=3225, prototype=1544,
         png='rail-horizontal.png', tiles=2),
    dict(name='arcane railing corner', server_id=20258, client_id=3224, prototype=1545,
         png='rail-corner.png', tiles=2),
    dict(name='arcane crystal wall light', server_id=20259, client_id=3223, prototype=2038,
         png='wall-lamp.png', tiles='1x2', frames=2, light=(5,71)),
]
for item in ITEMS:
    item.update(decor=True, descr='Dark metal, basalt and cyan crystal made for the teleport temple.')
    item['png'] = 'portal-details/'+item['png']


def prepare():
    from PIL import Image
    # Cada imagen generada se adapta a los límites y al ancla de su pieza nativa.
    def adapt(source, target, template, columns=1, rows=1, column=0):
        native = Image.open(ART/template).convert('RGBA')
        frame_height = native.height//rows
        result = Image.new('RGBA', native.size)
        generated = Image.open(ART/source).convert('RGBA')
        for frame in range(rows):
            cell = generated.crop((generated.width*column//columns, generated.height*frame//rows,
                                   generated.width*(column+1)//columns, generated.height*(frame+1)//rows))
            cell.putalpha(cell.getchannel('A').point(lambda a: 255 if a >= 128 else 0))
            bounds = cell.getbbox()
            reference = native.crop((0,frame*frame_height,native.width,(frame+1)*frame_height))
            anchor = reference.getbbox()
            if bounds is None or anchor is None:
                raise ValueError(f'Celda vacía: {source}/{frame}')
            cell = cell.crop(bounds).resize((anchor[2]-anchor[0],anchor[3]-anchor[1]),Image.Resampling.NEAREST)
            result.alpha_composite(cell,(anchor[0],frame*frame_height+anchor[1]))
        result.save(ART/target)
    for col,side in enumerate(('left','right')):
        adapt('entrance-generated.png',f'entrance-{side}.png',f'template-{1120+col}.png',columns=2,column=col)
    adapt('streetlamp-generated.png','streetlamp.png','template-1480.png',rows=2)
    for name,proto in [('rail-vertical',1543),('rail-horizontal',1544),('rail-corner',1545)]:
        adapt(f'{name}-generated.png',f'{name}.png',f'template-{proto}.png')
    adapt('wall-lamp-generated.png','wall-lamp.png','template-2038.png',rows=2)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepare',action='store_true');ap.add_argument('--apply',action='store_true')
    args=ap.parse_args()
    if args.prepare:prepare()
    things=ROOT/'devtools/rme/rme-client-760'
    otb=ROOT/'server/YurOTS/ots/data/items/items-zagan-test.otb'
    _,root=A.load_otb(otb);nodes={A.node_ids(n)[0]:n for n in root.children}
    free={r[0] for r in A.candidates(things,otb,exclude_paths=(__file__,))}
    for item in ITEMS:
        node=nodes.get(item['server_id'])
        if node and A.node_ids(node)[1:]!=(item['client_id'],item['name']):
            raise SystemExit(f'ID ocupado: {item["server_id"]}')
        if not node and item['client_id'] not in free:
            raise SystemExit(f'Client ID ocupado: {item["client_id"]}')
    if args.apply:
        backup=ROOT/'backups/map/portal-details-before';backup.mkdir(parents=True,exist_ok=True)
        for p in [things/'Tibia.dat',things/'Tibia.spr',otb,ROOT/'server/YurOTS/ots/data/world/test.otbm']:
            if not (backup/p.name).exists():shutil.copy2(p,backup/p.name)
    A.NEW_ITEMS=ITEMS
    print('\n'.join(A.apply_things(things,root,not args.apply)))
    print('\n'.join(A.apply_otb(otb,not args.apply)))


if __name__=='__main__':main()
