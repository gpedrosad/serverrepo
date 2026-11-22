#!/usr/bin/env python3
"""Instala tres stars reutilizables, proyectiles 18-20 e impactos 44-46.

  python3.11 scripts/client-rme/add_paladin_stars.py --prepare --preview /tmp/stars.png
  python3.11 scripts/client-rme/add_paladin_stars.py --apply

Sin --apply solo inspecciona. Trabaja sobre el cliente canónico y OTB actual;
no necesita el pack Zagan original. El gameplay requiere el C++ de PALADIN_STARS.md.
"""
from __future__ import annotations

import argparse
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from lib.project_root import project_root
import add_custom_items as A
from add_recolor_effects import read_sections
from add_black_dragon_look import _read_thing, encode_sprite, read_spr, write_spr
from paladin_star_art import LIGHT, impacts, missiles, prepare, preview

ROOT = project_root(HERE)
ART = ROOT / 'devtools/zagan-test/custom-sprites/paladin-stars'
BASE_FX, BASE_MISSILES = 44, 18
ITEMS = [
    dict(name='gale star', server_id=20211, client_id=3396, prototype=2352,
         png='paladin-stars/gale.png', attack=30, defence=0,
         descr='A swift silver star cut by cyan winds. Paladins only. Reusable.'),
    dict(name='venom star', server_id=20212, client_id=3395, prototype=2352,
         png='paladin-stars/venom.png', attack=38, defence=0,
         descr='Its serrated edges carry emerald venom. Paladins only. Reusable.'),
    dict(name='storm star', server_id=20213, client_id=3393, prototype=2352,
         png='paladin-stars/storm.png', attack=40, defence=0,
         descr='A cobalt star charged with violet lightning. Paladins only. Reusable.'),
]


def entry(ids: list[int], *, missile=False, light=71) -> bytes:
    dimensions = [1, 1, 1, 3, 3, 1, 1] if missile else [1, 1, 1, 1, 1, 1, len(ids)]
    return b'\x15' + struct.pack('<HH', 3, light) + bytes([255, *dimensions]) + struct.pack(f'<{len(ids)}H', *ids)


def _sprite_refs(dat: bytes) -> dict[int, set[str]]:
    """Mapa sprite_id -> conjunto de entradas DAT que lo referencian."""
    reader = A.B.DatReader(dat)
    entries, tail = reader.read_item_entries()
    counts, fx, mi = read_sections(dat)
    refs: dict[int, set[str]] = {}
    for e in entries:
        for sid in e.sprite_ids:
            if sid:
                refs.setdefault(sid, set()).add(f'item:{e.client_id}')
    pos = len(dat) - len(tail)
    for oid in range(1, counts[1] + 1):
        t = _read_thing(dat, pos)
        pos = t['end']
        for sid in t['ids']:
            if sid:
                refs.setdefault(sid, set()).add(f'outfit:{oid}')
    assert pos == fx[0]['start']
    for idx, t in enumerate(fx):
        for sid in t['ids']:
            if sid:
                refs.setdefault(sid, set()).add(f'fx:{idx}')
    for idx, t in enumerate(mi):
        for sid in t['ids']:
            if sid:
                refs.setdefault(sid, set()).add(f'missile:{idx}')
    return refs


def _replace_spr_records(spr_path: Path, updates: dict[int, bytes], dry: bool) -> None:
    spr = spr_path.read_bytes()
    spr_reader = A.B.SprReader(spr)
    records = [None] + [spr_reader.sprite_raw(i) for i in range(1, spr_reader.sprite_count + 1)]
    for sid, rec in updates.items():
        records[sid] = rec
    if not dry:
        spr_path.write_bytes(A.B.write_spr(spr_reader.signature, records))


def update_item_sprites_in_place(things: Path, dry: bool) -> None:
    """Reemplaza en el lugar los sprites de los ítems ya instalados sin tocar Tibia.dat."""
    dat_path, spr_path = things / 'Tibia.dat', things / 'Tibia.spr'
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    entries, _ = A.B.DatReader(dat).read_item_entries()
    by_cid = {e.client_id: e for e in entries}
    spr_reader = A.B.SprReader(spr)
    refs = _sprite_refs(dat)
    updates: dict[int, bytes] = {}
    for item in ITEMS:
        cid = item['client_id']
        cur = by_cid.get(cid)
        if cur is None or len(cur.sprite_ids) != 1 or cur.sprite_ids[0] == 0:
            continue
        sid = cur.sprite_ids[0]
        rec = A.sprite_records(A.SPRITES / item['png'], 1, 1)[0]
        if spr_reader.sprite_raw(sid) == rec:
            continue
        owners = refs.get(sid, set())
        if owners != {f'item:{cid}'}:
            raise SystemExit(f'Sprite {sid} compartido por {sorted(owners)}; no se actualiza en el lugar')
        updates[sid] = rec
    if updates:
        print(f'Ítems actualizados en el lugar en Tibia.spr: {sorted(updates)}')
        _replace_spr_records(spr_path, updates, dry)


def install_effects(things: Path, dry: bool, *, update_sprites: bool = False) -> None:
    dat_path, spr_path = things / 'Tibia.dat', things / 'Tibia.spr'
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    counts, fx, mi = read_sections(dat)
    n, offsets = read_spr(spr)
    generated = [(name, impacts(name), missiles(name, ART)) for name in LIGHT]
    if counts[2] >= BASE_FX + 3 and counts[3] >= BASE_MISSILES + 3:
        # No basta con contar: evitar confundir otro pack con éste.
        updates: dict[int, bytes] = {}
        expected_owner: dict[int, str] = {}
        for i, (name, hits, shots) in enumerate(generated):
            for owner, t, images, missile in (
                (f'fx:{BASE_FX + i}', fx[BASE_FX + i], hits, False),
                (f'missile:{BASE_MISSILES + i}', mi[BASE_MISSILES + i], shots, True),
            ):
                expected = entry(t['ids'], missile=missile, light=LIGHT[name])
                if dat[t['start']:t['end']] != expected:
                    raise SystemExit(f'El slot {name} está ocupado por otra apariencia')
                for sid, image in zip(t['ids'], images):
                    if image is None:
                        assert sid == 0
                    else:
                        off = offsets[sid - 1]
                        rec = spr[off:off+5+struct.unpack_from('<H', spr, off+3)[0]]
                        want = encode_sprite(list(image.getdata()))
                        if rec != want:
                            if not update_sprites:
                                raise SystemExit(f'El sprite {name}/{sid} difiere de la fuente')
                            updates[sid] = want
                            expected_owner[sid] = owner
        if updates:
            refs = _sprite_refs(dat)
            for sid, owner in expected_owner.items():
                owners = refs.get(sid, set())
                if owners != {owner}:
                    raise SystemExit(f'Sprite {sid} compartido por {sorted(owners)}; no se actualiza en el lugar')
            print(f'Efectos/proyectiles actualizados en el lugar en Tibia.spr: {sorted(updates)}')
            _replace_spr_records(spr_path, updates, dry)
            return
        print('Impactos 44-46 y proyectiles 18-20: ya instalados y verificados')
        return
    if counts[2:] != (BASE_FX, BASE_MISSILES):
        raise SystemExit(f'Contadores ocupados: {counts[2:]}; se necesitan (44,18)')
    records, new_fx, new_mi = [], b'', b''
    def append(images):
        ids = []
        for image in images:
            if image is None:
                ids.append(0)
            else:
                ids.append(n + len(records) + 1)
                records.append(encode_sprite(list(image.getdata())))
        return ids
    for name, hits, shots in generated:
        new_fx += entry(append(hits), light=LIGHT[name])
        new_mi += entry(append(shots), missile=True, light=LIGHT[name])
    fx_end = fx[-1]['end']
    new_dat = (dat[:4] + struct.pack('<4H', counts[0], counts[1], BASE_FX+3, BASE_MISSILES+3)
               + dat[12:fx_end] + new_fx + dat[fx_end:] + new_mi)
    new_spr = write_spr(struct.unpack_from('<I', spr)[0], offsets, spr, records)
    c2, fx2, mi2 = read_sections(new_dat)
    assert c2 == (*counts[:2], BASE_FX+3, BASE_MISSILES+3)
    assert [dat[t['start']:t['end']] for t in fx] == [new_dat[t['start']:t['end']] for t in fx2[:BASE_FX]]
    assert [dat[t['start']:t['end']] for t in mi] == [new_dat[t['start']:t['end']] for t in mi2[:BASE_MISSILES]]
    print(f'Impactos 44-46, proyectiles 18-20: {len(records)} sprites nuevos')
    if not dry:
        dat_path.write_bytes(new_dat)
        spr_path.write_bytes(new_spr)


def patch_weapon_shoot(otb: Path) -> None:
    data, root = A.load_otb(otb)
    changed = False
    for node in root.children:
        sid, _, _ = A.node_ids(node)
        if sid not in {item['server_id'] for item in ITEMS}:
            continue
        flags, blocks = A.B.parse_item_props(node.props)
        weapon = A.B.get_block_payload(blocks, A.ITEM_ATTR_WEAPON2)
        # DIST, AMU_NONE, throwing star de respaldo; el C++ envía los custom.
        blocks = A.B.upsert_block(blocks, A.ITEM_ATTR_WEAPON2, weapon[:2] + bytes([7]) + weapon[3:])
        props = A.B.build_item_props(flags, blocks)
        changed |= props != node.props
        node.props = props
    if changed:
        otb.write_bytes(data[:4] + A.B.write_node(root))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--things', type=Path, default=ROOT/'devtools/rme/rme-client-760')
    ap.add_argument('--otb', type=Path, default=ROOT/'server/YurOTS/ots/data/items/items-zagan-test.otb')
    ap.add_argument('--prepare', action='store_true')
    ap.add_argument('--preview', type=Path)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--update-sprites', action='store_true',
                    help='reemplaza en el lugar sprites ya instalados que difieran de la fuente')
    args = ap.parse_args()
    if args.prepare:
        prepare(ART)
    if args.preview:
        preview(ART, args.preview)
    _, root = A.load_otb(args.otb)
    by_sid = {A.node_ids(node)[0]: node for node in root.children}
    if any(item['server_id'] in by_sid and A.node_ids(by_sid[item['server_id']])[1:]
           != (item['client_id'], item['name']) for item in ITEMS):
        raise SystemExit('Un server ID reservado está ocupado')
    # Nuestra propia declaración reserva los IDs; no cuenta como uso de gameplay.
    free = {row[0] for row in A.candidates(args.things, args.otb, exclude_paths=(__file__,))}
    if any(item['client_id'] not in free and item['server_id'] not in by_sid for item in ITEMS):
        raise SystemExit('Un client ID reservado está ocupado')
    if args.apply:
        backup = ROOT / 'backups/map/paladin-stars-before'
        backup.mkdir(parents=True, exist_ok=True)
        for path in (args.things/'Tibia.dat', args.things/'Tibia.spr', args.otb):
            dest = backup/path.name
            if not dest.exists():
                shutil.copy2(path, dest)
    A.NEW_ITEMS = ITEMS
    if args.update_sprites:
        update_item_sprites_in_place(args.things, not args.apply)
    print('\n'.join(A.apply_things(args.things, root, not args.apply)))
    # El importador no acepta un árbol ya cargado: usar un archivo temporal,
    # luego comparar bytes, para que el OTB real sea idempotente.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='paladin-stars-') as temp:
        target = Path(temp)/'items.otb'
        target.write_bytes(args.otb.read_bytes())
        print('\n'.join(A.apply_otb(target, False)))
        patch_weapon_shoot(target)
        if args.apply and target.read_bytes() != args.otb.read_bytes():
            args.otb.write_bytes(target.read_bytes())
    install_effects(args.things, not args.apply, update_sprites=args.update_sprites)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
