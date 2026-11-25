#!/usr/bin/env python3
"""Piedra, raíces y luz ámbar propias de la quest BoH; --prepare --apply."""
import argparse
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent)]
from lib.project_root import project_root
import add_custom_items as A

ROOT=project_root(HERE)
ART=ROOT/'devtools/zagan-test/custom-sprites/root-crypt'
# 6083 en vez de 3210 (25 nov 2026): 3210 es la magician hat 2323
CLIENTS=(3213,3212,6083,3208,3205,3158,3156,3154,3151,3130,3124)
PROTOS=(1038,1039,1043,1044,1263,1264)
ITEMS=[
    dict(name='root crypt flagstones',server_id=20262,prototype=405,png='floor.png'),
    dict(name='root crypt portal paving',server_id=20263,prototype=405,png='threshold.png'),
]+[dict(name='root crypt window' if p in (1263,1264) else 'root crypt wall',
        server_id=20264+i,prototype=p,png=f'wall-{p}.png',tiles=2)
   for i,p in enumerate(PROTOS)]+[
    dict(name='root crypt low partition',server_id=20270,prototype=1041,png='partition.png',tiles=2),
    dict(name='root crypt amber lantern',server_id=20271,prototype=2037,png='lamp.png',
         tiles='1x2',light=(5,198)),
    dict(name='root crypt level gate',server_id=20272,prototype=1245,png='gate.png',tiles=2,layers=2),
]
for spec,cid in zip(ITEMS,CLIENTS):
    spec.update(client_id=cid,decor=True,descr='Weathered stone, moss and roots from the crypt south of the depot.')
    spec['png']='root-crypt/'+spec['png']


def prepare():
    from PIL import Image
    atlas=Image.open(ART/'walls-generated.png').convert('RGBA').resize((192,128),Image.Resampling.NEAREST)
    for i,proto in enumerate(PROTOS):
        x,y=i%3*64,i//3*64
        im=atlas.crop((x,y,x+64,y+64))
        im.putalpha(Image.open(ART/f'template-{proto}.png').getchannel('A'))
        im.save(ART/f'wall-{proto}.png')
    # Bajar el perfil sin comprimir la proyección del suelo: cada columna conserva
    # su pie. Un resize de toda la pieza deja huecos entre segmentos consecutivos.
    part=Image.open(ART/'wall-1043.png');im=Image.new('RGBA',(64,64))
    for x in range(64):
        column=part.crop((x,0,x+1,64));box=column.getbbox()
        if box:
            height=min(33,box[3]-box[1])
            column=column.crop(box).resize((1,height),Image.Resampling.NEAREST)
            im.alpha_composite(column,(x,box[3]-height))
    im.save(ART/'partition.png')
    for name in ('floor','threshold'):
        Image.open(ART/f'{name}-generated.png').convert('RGB').resize(
            (32,32),Image.Resampling.NEAREST).convert('RGBA').save(ART/f'{name}.png')
    lamp=Image.open(ART/'lamp-generated.png').convert('RGBA')
    lamp.putalpha(lamp.getchannel('A').point(lambda a:255 if a>=128 else 0))
    lamp=lamp.crop(lamp.getbbox());factor=min(28/lamp.width,54/lamp.height)
    lamp=lamp.resize((round(lamp.width*factor),round(lamp.height*factor)),Image.Resampling.NEAREST)
    im=Image.new('RGBA',(32,64));im.alpha_composite(lamp,((32-lamp.width)//2,61-lamp.height))
    im.save(ART/'lamp.png')
    gate=Image.open(ART/'gate-generated.png').convert('RGBA')
    gate.putalpha(gate.getchannel('A').point(lambda a:255 if a>=128 else 0))
    box=Image.open(ART/'template-1245.png').getbbox()
    gate=gate.crop(gate.getbbox()).resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.NEAREST)
    # La puerta nativa tiene dos capas, no dos cuadros de animación.
    # Arte completo en la primera y segunda transparente para conservar el prefijo.
    im=Image.new('RGBA',(64,128));im.alpha_composite(gate,box[:2]);im.save(ART/'gate.png')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepare',action='store_true');ap.add_argument('--apply',action='store_true')
    args=ap.parse_args()
    if args.prepare:prepare()
    things=ROOT/'devtools/rme/rme-client-760';otb=ROOT/'server/YurOTS/ots/data/items/items-zagan-test.otb'
    _,tree=A.load_otb(otb);nodes={A.node_ids(n)[0]:n for n in tree.children}
    free={row[0] for row in A.candidates(things,otb,exclude_paths=(__file__,))}
    for spec in ITEMS:
        old=nodes.get(spec['server_id'])
        if old and A.node_ids(old)[1:]!=(spec['client_id'],spec['name']):
            raise SystemExit(f'ID ocupado: {spec["server_id"]}')
        if old is None and spec['client_id'] not in free:
            raise SystemExit(f'Client ID ocupado: {spec["client_id"]}')
    A.NEW_ITEMS=ITEMS
    print('\n'.join(A.apply_things(things,tree,not args.apply)))
    print('\n'.join(A.apply_otb(otb,not args.apply)))


if __name__=='__main__':main()
