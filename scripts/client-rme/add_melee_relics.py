#!/usr/bin/env python3
"""Instala sword, axe, club e impactos 47-49. Sin --apply solo inspecciona."""
import argparse
import shutil
import struct
from pathlib import Path
import add_custom_items as A
from add_paladin_stars import ROOT, entry
from add_recolor_effects import read_sections
from add_black_dragon_look import encode_sprite, read_spr, write_spr
from melee_relic_art import LIGHT, impacts, prepare, preview

ART = ROOT/'devtools/zagan-test/custom-sprites/melee-relics'
ITEMS = [
    dict(name='riftblade', server_id=20225, client_id=3242, prototype=2407,
         png='melee-relics/riftblade.png', attack=46, defence=28, light=(2,161),
         descr='An obsidian blade that tears a violet rift on every third strike.'),
    dict(name='aethercleaver', server_id=20226, client_id=3238, prototype=2430,
         png='melee-relics/aethercleaver.png', attack=48, defence=26, light=(2,71),
         descr='Its turquoise core converts a fraction of wounds into mana.'),
    dict(name='graviton maul', server_id=20227, client_id=3235, prototype=2391,
         png='melee-relics/graviton.png', attack=55, defence=22, light=(2,187),
         descr='A heavy gravity core turns the enemy armor against its wearer.'),
]


def effects(things, dry):
    dat_path, spr_path = things/'Tibia.dat', things/'Tibia.spr'
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    counts, fx, missiles = read_sections(dat)
    n, offsets = read_spr(spr)
    images = [impacts(i) for i in range(3)]
    if counts[2] >= 50:
        for i, frames in enumerate(images):
            t = fx[47+i]
            assert dat[t['start']:t['end']] == entry(t['ids'], light=LIGHT[i]), 'Effect slot occupied'
            for sid, frame in zip(t['ids'], frames):
                off = offsets[sid-1]
                assert spr[off:off+5+struct.unpack_from('<H',spr,off+3)[0]] == encode_sprite(list(frame.getdata()))
        print('Impactos 47-49: instalados y verificados'); return
    if counts[2:] != (47, 21):
        raise SystemExit(f'Se necesitan 47 efectos y 21 proyectiles; hay {counts[2:]}')
    records, entries = [], b''
    for i, frames in enumerate(images):
        ids = []
        for frame in frames:
            ids.append(n+len(records)+1); records.append(encode_sprite(list(frame.getdata())))
        entries += entry(ids, light=LIGHT[i])
    boundary = fx[-1]['end']
    new_dat = dat[:4]+struct.pack('<4H',*counts[:2],50,21)+dat[12:boundary]+entries+dat[boundary:]
    check, fx2, missiles2 = read_sections(new_dat)
    assert check == (*counts[:2],50,21)
    for old, new in [(fx,fx2[:47]), (missiles,missiles2)]:
        assert [dat[t['start']:t['end']] for t in old] == [new_dat[t['start']:t['end']] for t in new]
    print('Impactos 47-49: +24 sprites, proyectiles intactos')
    if not dry:
        dat_path.write_bytes(new_dat)
        spr_path.write_bytes(write_spr(struct.unpack_from('<I',spr)[0],offsets,spr,records))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--things',type=Path,default=ROOT/'devtools/rme/rme-client-760')
    ap.add_argument('--otb',type=Path,default=ROOT/'server/YurOTS/ots/data/items/items-zagan-test.otb')
    ap.add_argument('--prepare',action='store_true'); ap.add_argument('--apply',action='store_true')
    ap.add_argument('--preview',type=Path); args=ap.parse_args()
    if args.prepare: prepare(ART)
    if args.preview: preview(ART,args.preview)
    _, root = A.load_otb(args.otb); by_sid={A.node_ids(n)[0]:n for n in root.children}
    free={r[0] for r in A.candidates(args.things,args.otb,exclude_paths=(__file__,))}
    for item in ITEMS:
        sid=item['server_id']
        if sid in by_sid:
            assert A.node_ids(by_sid[sid])[1:]==(item['client_id'],item['name']), 'Server ID occupied'
        else:
            assert item['client_id'] in free, 'Client ID occupied'
    effects(args.things, True)  # Refuse occupied effect slots before writing items.
    if args.apply:
        backup=ROOT/'backups/map/melee-relics-before';backup.mkdir(parents=True,exist_ok=True)
        for p in [args.things/'Tibia.dat',args.things/'Tibia.spr',args.otb]:
            if not (backup/p.name).exists(): shutil.copy2(p,backup/p.name)
    A.NEW_ITEMS=ITEMS
    print('\n'.join(A.apply_things(args.things,root,not args.apply)))
    print('\n'.join(A.apply_otb(args.otb,not args.apply)))
    effects(args.things,not args.apply)


if __name__=='__main__': main()
