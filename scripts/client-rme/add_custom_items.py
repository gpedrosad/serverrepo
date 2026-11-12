#!/usr/bin/env python3
"""Agrega ítems nuevos (sprite PNG de 32x32) al cliente y al servidor, sobre los archivos actuales.

Para ítems traídos de otras versiones (ej. armas de 8.x) o dibujados (Root Colossus), sin el builder viejo (build_zagan_test_assets.py,
que necesita el pack Zagan perdido y client-local). Cada ítem de NEW_ITEMS:

  - Cliente (Tibia.dat / Tibia.spr, en cada --things): agrega el sprite al final del .spr y hace que su
    client id (uno "sacrificado": un ítem viejo que el servidor nunca da) se vea como el prototipo pero
    con el sprite nuevo. El client id es fijo, así es el mismo en el cliente de RME y en el de jugadores.
  - Servidor (items-zagan-test.otb, en cada --otb): nodo nuevo con su server id fijo, copiado del
    prototipo (slot, peso, tipo de arma) con nombre, descripción, ataque y defensa propios.

Re-ejecutable: si el ítem ya está (mismo sprite en el .dat, nodo con ese server id), no cambia nada.
Elegir client ids nuevos: `--candidates` lista los que se pueden sacrificar sin riesgo (ni en el mapa,
ni en loot, NPC, acciones o scripts, ni destino de una pudrición, ni suelos, cadáveres o decoración).

  python3.11 scripts/client-rme/add_custom_items.py --candidates
  python3.11 scripts/client-rme/add_custom_items.py --things devtools/rme/rme-client-760 \\
      --otb server/YurOTS/ots/data/items/items-zagan-test.otb [--things OTRO_CLIENTE/data/things/760]

Necesita Pillow (en la Mac mini: python3.11). Los PNG están en devtools/zagan-test/custom-sprites/
(los saca extract_client_sprites.py). Doc: docs/items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md.
"""
from __future__ import annotations

import argparse
import re
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build_zagan_test_assets as B  # noqa: E402

SPRITES = ROOT / "devtools" / "zagan-test" / "custom-sprites"
ITEM_ATTR_WEAPON2 = 0x26
ITEM_ATTR_ARMOR2 = 0x28   # u16 armor, double weight, u16 slot
ITEM_ATTR_DECAY = 0x1F
ITEM_ATTR_ROTATETO = 0x1E
ITEM_ATTR_DECAY2 = 0x25
FLAG_PICKUPABLE = 1 << 5

# server_id y client_id fijos: no cambiarlos una vez repartido el cliente. Prototipos (server ids de 7.6):
# 2407 bright sword (espada 1 mano), 2393 giant sword (espada 2 manos), 2391 war hammer (maza 2 manos),
# 2455 crossbow (ballesta). Los cuatro primeros usan stats de Tibia 8.60 (items.xml de RME data/860).
NEW_ITEMS = [
    dict(name="emerald sword", server_id=20157, client_id=3348, prototype=2407, png="emerald_sword.png",
         attack=49, defence=33, descr="A sword with a blade of polished emerald."),
    dict(name="avenger", server_id=20158, client_id=3346, prototype=2393, png="the_avenger.png",
         attack=50, defence=38, descr="This holy blade was forged of shattered dreams."),
    dict(name="arcane staff", server_id=20159, client_id=3345, prototype=2391, png="arcane_staff.png",
         attack=50, defence=30, descr="It is enchanted with ancient magic that renders a weak staff into a powerful weapon."),
    dict(name="arbalest", server_id=20160, client_id=3575, prototype=2455, png="arbalest.png",
         attack=2, defence=0, descr="It is a bit heavy due to the iron mounting, but very precise. Adds +2 to bolts."),
    # Armaduras: `armor` en vez de attack/defence (peso y slot, los del prototipo). 2487 crown armor (arm 13).
    # Sprites: la crown armor del cliente recoloreada con scripts/client-rme/recolor_item.py (comandos en
    # docs/items-and-map/CROWN_ARMORS.md). Ventaja propia en C++ (GameState::applyAmulets).
    dict(name="imperial crown armor", server_id=20161, client_id=3570, prototype=2487,
         png="imperial_crown_armor.png", armor=14,
         descr="Forged for the emperors of old, its violet plates still shine with royal gold."),
    dict(name="sapphire crown armor", server_id=20162, client_id=3564, prototype=2487,
         png="sapphire_crown_armor.png", armor=14,
         descr="Sapphire plates bound in gold. Blades and claws slide off it."),
    # Root Colossus: armas fisicas, sin procs ni cambios de C++. Sprites reproducibles con draw_root_weapons.py.
    dict(name="rootcleaver", server_id=20163, client_id=3573, prototype=2430,
         png="rootcleaver.png", attack=49, defence=31,
         descr="A jade-edged axe bound to a living root. Claimed from a Root Colossus."),
    dict(name="heartwood maul", server_id=20164, client_id=3561, prototype=2391,
         png="heartwood_maul.png", attack=52, defence=28,
         descr="Ancient heartwood held together by twisted roots. Claimed from a Root Colossus."),
]


def u16(payload: bytes | None) -> int | None:
    return struct.unpack("<H", payload)[0] if payload and len(payload) == 2 else None


def load_otb(path: Path):
    data = path.read_bytes()
    root, end = B.parse_node(data, 4)
    if end != len(data):
        raise SystemExit(f"{path}: bytes de más al final del items.otb")
    return data, root


def node_ids(node) -> tuple[int | None, int | None, str]:
    _flags, blocks = B.parse_item_props(node.props)
    name = B.get_block_payload(blocks, B.ITEM_ATTR_NAME) or b""
    return (u16(B.get_block_payload(blocks, B.ITEM_ATTR_SERVERID)), u16(B.get_block_payload(blocks, B.ITEM_ATTR_CLIENTID)),
            name.decode("latin-1"))


def sprite_record(png: Path) -> bytes:
    """El PNG tal cual, píxel a píxel: tiene que medir 32x32 (no se recorta ni se reescala, porque un sprite
    sacado de otro cliente se arruina). Lo semitransparente queda opaco y lo transparente, transparente."""
    image = B.Image.open(png).convert("RGBA")
    if image.size != (32, 32):
        raise SystemExit(f"{png.name}: mide {image.size}, tiene que ser 32x32")
    image.putdata([(0, 0, 0, 0) if p[3] == 0 else (p[0], p[1], p[2], 255) for p in image.getdata()])
    return B.encode_sprite_record(image)


# ---------- candidatos a sacrificar ----------

def candidates(things: Path, otb: Path) -> list[tuple[int, list[int], str]]:
    entries, _tail = B.DatReader((things / "Tibia.dat").read_bytes()).read_item_entries()
    item_count = B.DatReader((things / "Tibia.dat").read_bytes()).item_count
    _data, root = load_otb(otb)
    c2s, s2c, c2n, c2flags, used_custom, targets = {}, {}, {}, {}, set(), set()
    for node in root.children:
        flags, blocks = B.parse_item_props(node.props)
        for attr, payload in blocks:
            if attr in (ITEM_ATTR_DECAY, ITEM_ATTR_DECAY2, ITEM_ATTR_ROTATETO) and len(payload) >= 2:
                targets.add(struct.unpack_from("<H", payload)[0])
        sid, cid, name = node_ids(node)
        if sid is None or cid is None:
            continue
        if sid >= 20100:
            used_custom.add(cid)
        c2s.setdefault(cid, set()).add(sid)
        s2c[sid] = cid
        c2flags[cid] = struct.unpack("<I", flags[:4])[0] if len(flags) >= 4 else 0
        if name:
            c2n[cid] = name
    map_ids = B.load_map_server_ids(B.MAP_OTBM)
    protected = B.build_protected_client_ids(map_ids, s2c, c2n)
    data, refs = ROOT / "server/YurOTS/ots/data", set()
    files = (list(data.glob("monster/*.xml")) + list(data.glob("npc/**/*.lua")) + list(data.glob("actions/**/*.lua"))
             + list(data.glob("actions/*.xml")) + list(data.glob("spells/**/*.lua")) + list((ROOT / "scripts").rglob("*.py"))
             + [data / "items/items.xml", data / "items/items-zagan-test.xml"])
    for f in files:
        if f.is_file():
            refs |= {int(x) for x in re.findall(r"\b(\d{3,5})\b", f.read_text(errors="replace")) if 100 <= int(x) <= 20000}
    bad_name = re.compile(r"dead|skeleton|corpse|remains|body|blood|pool|fire|burning|slime|puddle|trail|ash|bones|carcass")
    taken = set(B.CORE_RESERVED_CLIENT_IDS) | set(B.EXTERNAL_CLIENT_IDS) | used_custom | {i["client_id"] for i in NEW_ITEMS}
    out = []
    for e in entries:
        c = e.client_id
        if c > item_count or c in taken or c in protected or len(e.sprite_ids) != 1:
            continue
        if not c2flags.get(c, 0) & FLAG_PICKUPABLE:
            continue
        sids, name = c2s.get(c, set()), c2n.get(c, "?")
        if not sids or bad_name.search(name.lower()) or c in refs:
            continue
        if any(s in refs or s in map_ids or s in targets for s in sids):
            continue
        out.append((c, sorted(sids), name))
    return sorted(out, reverse=True)


# ---------- aplicar ----------

def apply_things(things: Path, otb_root, dry: bool) -> list[str]:
    dat_path, spr_path = things / "Tibia.dat", things / "Tibia.spr"
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    reader = B.DatReader(dat)
    entries, tail = reader.read_item_entries()
    by_cid = {e.client_id: i for i, e in enumerate(entries)}
    spr_reader = B.SprReader(spr)
    records = [None] + [spr_reader.sprite_raw(i) for i in range(1, spr_reader.sprite_count + 1)]
    s2c = {}
    for node in otb_root.children:
        sid, cid, _name = node_ids(node)
        if sid is not None and cid is not None:
            s2c.setdefault(sid, cid)
    new_entries, log, changed = [e.raw for e in entries], [], False
    for item in NEW_ITEMS:
        record = sprite_record(SPRITES / item["png"])
        idx = by_cid.get(item["client_id"])
        proto_cid = s2c.get(item["prototype"])
        if idx is None or proto_cid not in by_cid:
            raise SystemExit(f"{things}: falta el client id {item['client_id']} o el del prototipo {item['prototype']}")
        proto = entries[by_cid[proto_cid]]
        if len(proto.sprite_ids) != 1:
            raise SystemExit(f"prototipo {item['prototype']} no es de 1 sprite")
        current = entries[idx]
        if (len(current.sprite_ids) == 1 and current.prefix == proto.prefix
                and records[current.sprite_ids[0]] == record):
            log.append(f"  {item['name']}: ya está (client {item['client_id']}, sprite {current.sprite_ids[0]})")
            continue
        records.append(record)
        sprite_id = len(records) - 1
        new_entries[idx] = B.patch_item_sprite(current, proto.prefix, sprite_id)
        changed = True
        log.append(f"  {item['name']}: client {item['client_id']} -> sprite nuevo {sprite_id}")
    if changed and not dry:
        for path in (dat_path, spr_path):
            backup = path.with_name(path.name + ".bak-custom-items")
            if not backup.exists():
                shutil.copy2(path, backup)
        dat_path.write_bytes(B.write_dat(reader.signature, reader.item_count, reader.outfit_count, reader.effect_count,
                                         reader.missile_count, new_entries, tail))
        spr_path.write_bytes(B.write_spr(spr_reader.signature, records))
    return log


def apply_otb(path: Path, dry: bool) -> list[str]:
    data, root = load_otb(path)
    by_sid = {}
    for node in root.children:
        sid, _cid, _name = node_ids(node)
        if sid is not None:
            by_sid.setdefault(sid, node)
    log, changed = [], False
    for item in NEW_ITEMS:
        proto = by_sid.get(item["prototype"])
        if proto is None:
            raise SystemExit(f"{path}: no está el prototipo {item['prototype']}")
        flags, blocks = B.parse_item_props(proto.props)
        if "armor" in item:
            armor = B.get_block_payload(blocks, ITEM_ATTR_ARMOR2)
            if not armor or len(armor) != 12:
                raise SystemExit(f"prototipo {item['prototype']} sin bloque de armadura")
            blocks = B.upsert_block(blocks, ITEM_ATTR_ARMOR2, struct.pack("<H", item["armor"]) + armor[2:])
        else:
            weapon = B.get_block_payload(blocks, ITEM_ATTR_WEAPON2)
            if not weapon or len(weapon) != 5:
                raise SystemExit(f"prototipo {item['prototype']} sin bloque de arma")
            blocks = B.upsert_block(blocks, ITEM_ATTR_WEAPON2, weapon[:3] + bytes([item["attack"], item["defence"]]))
        descr = item["descr"].encode("latin-1")
        if len(descr) >= 128:
            raise SystemExit(f"descripción de {item['name']} demasiado larga ({len(descr)} bytes, máximo 127)")
        blocks = B.upsert_block(blocks, B.ITEM_ATTR_SERVERID, struct.pack("<H", item["server_id"]))
        blocks = B.upsert_block(blocks, B.ITEM_ATTR_CLIENTID, struct.pack("<H", item["client_id"]))
        blocks = B.upsert_block(blocks, B.ITEM_ATTR_NAME, item["name"].encode("latin-1"))
        blocks = B.upsert_block(blocks, B.ITEM_ATTR_DESCR, descr)
        new_node = B.Node(node_type=proto.node_type, props=B.build_item_props(flags, blocks), children=[])
        old = by_sid.get(item["server_id"])
        if old is not None and old.props == new_node.props:
            log.append(f"  {item['name']}: ya está (server {item['server_id']})")
            continue
        if old is not None:
            root.children[root.children.index(old)] = new_node
            log.append(f"  {item['name']}: server {item['server_id']} actualizado")
        else:
            root.children.append(new_node)
            stats = (f"arm {item['armor']}" if "armor" in item else f"atk {item['attack']} def {item['defence']}")
            log.append(f"  {item['name']}: server {item['server_id']} nuevo (client {item['client_id']}, "
                       f"prototipo {item['prototype']}, {stats})")
        changed = True
    if changed and not dry:
        backup = path.with_name(path.name + ".bak-custom-items")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_bytes(data[:4] + B.write_node(root))
    return log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--things", type=Path, action="append", default=[], help="carpeta con Tibia.dat y Tibia.spr (repetible)")
    ap.add_argument("--otb", type=Path, action="append", default=[], help="items.otb del servidor (repetible)")
    ap.add_argument("--candidates", action="store_true", help="listar client ids que se pueden sacrificar")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    otbs = a.otb or [ROOT / "server/YurOTS/ots/data/items/items-zagan-test.otb"]
    if a.candidates:
        rows = candidates(ROOT / "devtools/rme/rme-client-760", otbs[0])
        print(f"{len(rows)} client ids se pueden sacrificar (client, server ids, nombre):")
        for row in rows[:40]:
            print(" ", *row)
        return 0
    _data, otb_root = load_otb(otbs[0])
    for things in a.things:
        print(f"{things}:")
        print("\n".join(apply_things(things, otb_root, a.dry_run)))
    for otb in otbs:
        print(f"{otb}:")
        print("\n".join(apply_otb(otb, a.dry_run)))
    if a.dry_run:
        print("dry-run: no se escribió nada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
