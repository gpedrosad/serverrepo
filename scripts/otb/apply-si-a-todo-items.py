#!/usr/bin/env python3
"""Instala/actualiza los ítems nuevos y el set endgame en items-zagan-test.otb.

Reutiliza únicamente client IDs ya existentes en el cliente 7.6 / Zagan (no modifica
Tibia.dat ni Tibia.spr ni inventa IDs inexistentes). Es idempotente.

Uso:
  python3.11 scripts/otb/apply-si-a-todo-items.py --dry-run
  python3.11 scripts/otb/apply-si-a-todo-items.py
"""
from __future__ import annotations

import argparse
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "client-rme"))
import build_zagan_test_assets as B  # noqa: E402

OTB = ROOT / "server/YurOTS/ots/data/items/items-zagan-test.otb"

A_SID = 0x10
A_CID = 0x11
A_NAME = 0x12
A_DESCR = 0x13
A_SLOT = 0x15
A_WEIGHT = 0x17
A_WEAPON2 = 0x26
A_ARMOR2 = 0x28

GROUP_NONE = 0
FLAG_USEABLE = 16
FLAG_PICKUPABLE = 32
FLAG_MOVEABLE = 64

# Actualizaciones sobre ítems Zagan existentes (ya tienen sprite recoloreado propio en el cliente)
UPDATES: dict[int, dict] = {
    # --- Set Endgame de Mago (Starbinder / Arcane) ---
    20118: dict(
        name="starbinder hood",
        armor=6, weight=18.0, slot=1,
        descr="A violet arcane hood woven for masters of magic.",
    ),
    20148: dict(
        name="kilnfire leggings",
        armor=8, weight=28.0, slot=3,
        descr="Lightweight arcane leggings tempered in kiln fire.",
    ),
    20129: dict(
        name="wayfarer boots",
        armor=2, weight=9.0, slot=7,
        descr="Enchanted boots worn by seasoned travelers across harsh realms.",
    ),
    20149: dict(
        name="mosaic shield",
        defence=33, weight=34.0,
        descr="A turquoise ward shield inlaid with energy-dampening tiles.",
    ),
    # --- Set Endgame de Metal (Machina / Forge) ---
    20152: dict(
        name="fox machina helmet",
        armor=10, weight=42.0, slot=1,
        descr="A reinforced alloy visor forged from fallen metal beasts.",
    ),
    20104: dict(
        name="basalt greaves",
        armor=9, weight=65.0, slot=3,
        descr="Heavy basalt leg plates built to absorb crushing blows.",
    ),
    20147: dict(
        name="obsidian regalia",
        armor=16, weight=78.0, slot=2,
        descr="Dark obsidian plate infused with elemental shielding.",
    ),
    20151: dict(
        name="sunforge shield",
        defence=36, weight=32.0,
        descr="A gilded shield forged to turn aside searing flames and bolts.",
    ),
    # --- Otros equipos Zagan activados ---
    20120: dict(
        name="boltworker crossbow",
        attack=1, defence=0, weight=38.0,
        descr="A precision steel-limbed crossbow (+1 attack to bolts).",
    ),
    20153: dict(
        name="frostwarden aegis",
        defence=32, weight=42.0,
        descr="A cold-forged shield rimmed with permafrost.",
    ),
    20102: dict(
        name="morlen crest",
        armor=9, weight=38.0, slot=1,
        descr="A jade-crested war helm prized by veteran hunters.",
    ),
    # --- Consumibles de bosses (reutilizan sprites Zagan propios) ---
    20124: dict(
        name="azure sunstone",
        usable_gem=True, weight=2.0,
        descr="A radiant azure crystal. Use it to recharge worn soft boots.",
    ),
    20125: dict(
        name="verdant sunstone",
        usable_gem=True, weight=2.0,
        descr="A living emerald crystal. Use it to fully restore health and mana.",
    ),
}

# Ítems nuevos (server_id >= 20372) que reutilizan client_id existentes en Tibia 7.6
NEW_ITEMS: list[dict] = [
    dict(
        server_id=20372,
        client_id=3284,  # ice rapier (hoja cristalina helada existente en 7.6)
        prototype=2407,  # bright sword (1H sword)
        name="aurora blade",
        attack=36,
        defence=30,
        weight=28.0,
        descr="A swift crystalline blade with a cold aurora edge (1250ms attack).",
    ),
    dict(
        server_id=20373,
        client_id=3335,  # twin axe (hacha doble existente en 7.6)
        prototype=2430,  # knight axe (1H axe)
        name="aurora axe",
        attack=34,
        defence=22,
        weight=52.0,
        descr="A balanced northern axe with a swift aurora edge (1250ms attack).",
    ),
    dict(
        server_id=20374,
        client_id=3350,  # bow (arco existente en 7.6)
        prototype=2456,  # bow (2H bow, AMU_ARROW)
        name="frostbound bow",
        attack=1,
        defence=0,
        weight=31.0,
        descr="A sinew-backed northern bow (+1 attack to arrows).",
    ),
]


def apply_update(node: B.Node, spec: dict) -> None:
    flags_b, blocks = B.parse_item_props(node.props)
    if spec.get("usable_gem"):
        cid = B.get_block_payload(blocks, A_CID)
        sid = B.get_block_payload(blocks, A_SID)
        flags_b = struct.pack("<I", FLAG_USEABLE | FLAG_PICKUPABLE | FLAG_MOVEABLE)
        blocks = [
            (A_SID, sid),
            (A_CID, cid),
            (A_NAME, spec["name"].encode("latin-1")),
            (A_DESCR, spec["descr"].encode("latin-1")),
            (A_WEIGHT, struct.pack("<d", spec["weight"])),
        ]
        node.node_type = GROUP_NONE
        node.props = B.build_item_props(flags_b, blocks)
        return

    blocks = B.upsert_block(blocks, A_NAME, spec["name"].encode("latin-1"))
    blocks = B.upsert_block(blocks, A_DESCR, spec["descr"].encode("latin-1"))
    if "weight" in spec:
        blocks = B.upsert_block(blocks, A_WEIGHT, struct.pack("<d", spec["weight"]))
    if "armor" in spec:
        slot = spec["slot"]
        wt = spec["weight"]
        blocks = B.upsert_block(blocks, A_SLOT, struct.pack("<H", slot))
        blocks = B.upsert_block(blocks, A_ARMOR2, struct.pack("<HdH", spec["armor"], wt, slot))
    if "attack" in spec or "defence" in spec:
        w2 = B.get_block_payload(blocks, A_WEAPON2)
        if not w2 or len(w2) != 5:
            raise SystemExit(f"{spec['name']}: falta bloque WEAPON2")
        atk = spec.get("attack", w2[3])
        dfn = spec.get("defence", w2[4])
        blocks = B.upsert_block(blocks, A_WEAPON2, w2[:3] + bytes([atk, dfn]))
    node.props = B.build_item_props(flags_b, blocks)


def build_new_node(proto: B.Node, spec: dict) -> B.Node:
    flags_b, blocks = B.parse_item_props(proto.props)
    w2 = B.get_block_payload(blocks, A_WEAPON2)
    if not w2 or len(w2) != 5:
        raise SystemExit(f"prototipo {spec['prototype']} sin bloque WEAPON2")
    blocks = B.upsert_block(blocks, A_WEAPON2, w2[:3] + bytes([spec["attack"], spec["defence"]]))
    blocks = B.upsert_block(blocks, A_WEIGHT, struct.pack("<d", spec["weight"]))
    blocks = B.upsert_block(blocks, A_SID, struct.pack("<H", spec["server_id"]))
    blocks = B.upsert_block(blocks, A_CID, struct.pack("<H", spec["client_id"]))
    blocks = B.upsert_block(blocks, A_NAME, spec["name"].encode("latin-1"))
    blocks = B.upsert_block(blocks, A_DESCR, spec["descr"].encode("latin-1"))
    return B.Node(node_type=proto.node_type, props=B.build_item_props(flags_b, blocks), children=[])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    data = OTB.read_bytes()
    root, end = B.parse_node(data, 4)
    if end != len(data):
        raise SystemExit(f"{OTB}: bytes sobrantes al final ({end} vs {len(data)})")

    by_sid: dict[int, B.Node] = {}
    valid_cids: set[int] = set()
    for node in root.children:
        _, blocks = B.parse_item_props(node.props)
        sb = B.get_block_payload(blocks, A_SID)
        cb = B.get_block_payload(blocks, A_CID)
        if sb and len(sb) == 2:
            by_sid[struct.unpack("<H", sb)[0]] = node
        if cb and len(cb) == 2:
            valid_cids.add(struct.unpack("<H", cb)[0])

    changed = 0
    for sid, spec in UPDATES.items():
        node = by_sid.get(sid)
        if node is None:
            raise SystemExit(f"No existe server_id {sid} en {OTB}")
        before = (node.node_type, node.props)
        apply_update(node, spec)
        if (node.node_type, node.props) != before:
            changed += 1
            print(f"  [update] {sid} {spec['name']}")
        else:
            print(f"  [ok]     {sid} {spec['name']} (sin cambios)")

    for spec in NEW_ITEMS:
        if spec["client_id"] not in valid_cids:
            raise SystemExit(f"client_id {spec['client_id']} no existe en el OTB actual")
        proto = by_sid.get(spec["prototype"])
        if proto is None:
            raise SystemExit(f"prototipo {spec['prototype']} no existe en {OTB}")
        new_node = build_new_node(proto, spec)
        old = by_sid.get(spec["server_id"])
        if old is not None:
            if old.node_type == new_node.node_type and old.props == new_node.props:
                print(f"  [ok]     {spec['server_id']} {spec['name']} (sin cambios)")
            else:
                root.children[root.children.index(old)] = new_node
                changed += 1
                print(f"  [update] {spec['server_id']} {spec['name']}")
        else:
            root.children.append(new_node)
            by_sid[spec["server_id"]] = new_node
            changed += 1
            print(f"  [new]    {spec['server_id']} {spec['name']} (cid={spec['client_id']})")

    if changed and not a.dry_run:
        backup = ROOT / "backups" / "items-zagan-test.otb.pre-si-a-todo"
        if not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(OTB, backup)
        out = data[:4] + B.write_node(root)
        # Re-parse verification before writing
        v_root, v_end = B.parse_node(out, 4)
        assert v_end == len(out) and len(v_root.children) == len(root.children)
        OTB.write_bytes(out)
        print(f"Escrito {OTB} ({changed} cambios; backup en {backup})")
    else:
        print(f"{changed} cambios" + (" (dry-run)" if a.dry_run else " (ya estaba actualizado)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
