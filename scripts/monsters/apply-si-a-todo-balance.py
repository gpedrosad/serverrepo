#!/usr/bin/env python3
"""Aplica balance de monstruos nuevos, correcciones de loot y loots propuestos ("sí a todo").

Valida cada item ID contra items-zagan-test.otb (sintaxis stackable vs no-stackable,
countmax <= 100, cero duplicados, cero id=0). Es idempotente.
"""
from __future__ import annotations

import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MON_DIR = ROOT / "server/YurOTS/ots/data/monster"
OTB_PATH = ROOT / "server/YurOTS/ots/data/items/items-zagan-test.otb"
sys.path.insert(0, str(ROOT / "scripts/client-rme"))
import build_zagan_test_assets as B  # noqa: E402


def load_otb_info() -> dict[int, dict]:
    data = OTB_PATH.read_bytes()
    root, _ = B.parse_node(data, 4)
    out = {}
    for node in root.children:
        fl_b, blocks = B.parse_item_props(node.props)
        sb = B.get_block_payload(blocks, 0x10)
        if not sb:
            continue
        sid = struct.unpack("<H", sb)[0]
        fl = struct.unpack("<I", fl_b)[0]
        name = (B.get_block_payload(blocks, 0x12) or b"").decode("latin-1", "replace")
        out[sid] = {"name": name, "stackable": bool(fl & 128)}
    return out


def make_loot_el(otb: dict, item_id: int, chance: int, countmax: int | None = None) -> ET.Element:
    assert item_id in otb, f"Item ID {item_id} no existe en OTB"
    info = otb[item_id]
    if info["stackable"]:
        cm = countmax if countmax is not None else 1
        assert 1 <= cm <= 100, f"countmax invalido {cm} para {item_id}"
        return ET.Element("item", {"id": str(item_id), "countmax": str(cm), "chance1": str(chance), "chancemax": "0"})
    assert countmax is None, f"item no-stackable {item_id} ({info['name']}) no debe llevar countmax"
    return ET.Element("item", {"id": str(item_id), "chance": str(chance)})


def get_loot_target(root: ET.Element, inside_bag: bool = False) -> ET.Element:
    loot = root.find("loot")
    assert loot is not None
    if inside_bag:
        for it in loot.findall("item"):
            if it.attrib.get("id") == "1987":
                ins = it.find("inside")
                if ins is not None:
                    return ins
    return loot


def remove_loot_ids(root: ET.Element, ids: set[int]) -> int:
    removed = 0
    loot = root.find("loot")
    if loot is None:
        return 0
    for parent in [loot] + loot.findall(".//inside"):
        for ch in list(parent):
            if ch.tag == "item" and int(ch.attrib.get("id", "-1")) in ids:
                parent.remove(ch)
                removed += 1
    return removed


def dedup_loot(root: ET.Element, keep_multi_ids: set[int] = {2148}) -> int:
    """Elimina duplicados exactos de item ID (excepto gold coins 2148 que se parten en stacks <= 100)."""
    seen: set[int] = set()
    removed = 0
    loot = root.find("loot")
    if loot is None:
        return 0
    for parent in [loot] + loot.findall(".//inside"):
        for ch in list(parent):
            if ch.tag != "item":
                continue
            iid = int(ch.attrib.get("id", "0"))
            if iid == 1987 or iid in keep_multi_ids:
                continue
            if iid in seen:
                parent.remove(ch)
                removed += 1
            else:
                seen.add(iid)
    return removed


def split_big_gold(root: ET.Element) -> int:
    """Parte cualquier stack de gold coin (2148) con countmax > 100 en stacks <= 100."""
    changed = 0
    loot = root.find("loot")
    if loot is None:
        return 0
    for parent in [loot] + loot.findall(".//inside"):
        for idx, ch in enumerate(list(parent)):
            if ch.tag == "item" and ch.attrib.get("id") == "2148":
                cm = int(ch.attrib.get("countmax", "0") or "0")
                if cm > 100:
                    rem = cm - 100
                    ch.attrib["countmax"] = "100"
                    chance1 = ch.attrib.get("chance1", "100000")
                    while rem > 0:
                        part = min(100, rem)
                        rem -= part
                        extra = ET.Element("item", {
                            "id": "2148",
                            "countmax": str(part),
                            "chance1": chance1,
                            "chancemax": "0",
                        })
                        parent.insert(idx + 1, extra)
                    changed += 1
    return changed


def upsert_loot(root: ET.Element, otb: dict, item_id: int, chance: int,
                countmax: int | None = None, inside_bag: bool = False) -> None:
    """Actualiza si ya existe el item_id en el loot, o lo agrega al contenedor elegido."""
    loot = root.find("loot")
    assert loot is not None
    for el in loot.findall(".//item"):
        if int(el.attrib.get("id", "0")) == item_id:
            if otb[item_id]["stackable"]:
                el.attrib.pop("chance", None)
                el.attrib["countmax"] = str(countmax if countmax is not None else 1)
                el.attrib["chance1"] = str(chance)
                el.attrib["chancemax"] = "0"
            else:
                el.attrib.pop("chance1", None)
                el.attrib.pop("chancemax", None)
                el.attrib.pop("countmax", None)
                el.attrib["chance"] = str(chance)
            return
    target = get_loot_target(root, inside_bag=inside_bag)
    target.append(make_loot_el(otb, item_id, chance, countmax))


def set_stats(root: ET.Element, **kwargs) -> None:
    for k in ("experience", "armor", "defense", "speed"):
        if k in kwargs:
            root.attrib[k] = str(kwargs[k])
    if "health" in kwargs:
        hp = root.find("health")
        assert hp is not None
        hp.attrib["now"] = str(kwargs["health"])
        hp.attrib["max"] = str(kwargs["health"])
    if "melee" in kwargs:
        mn, mx = kwargs["melee"]
        for a in root.findall(".//attacks/attack"):
            if a.attrib.get("type") == "melee":
                a.attrib["mindamage"] = str(mn)
                a.attrib["maxdamage"] = str(mx)
                break


def indent_xml(elem: ET.Element, level: int = 0) -> None:
    i = "\n" + ("\t" * level)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "\t"
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for sub in elem:
            indent_xml(sub, level + 1)
        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def save_monster(path: Path, root: ET.Element) -> None:
    indent_xml(root)
    xml_body = ET.tostring(root, encoding="unicode")
    path.write_text('<?xml version="1.0"?>\n' + xml_body + "\n", encoding="utf-8")


# Especificación de cambios por archivo base
# Campos: stats, remove_ids, dedup (bool), adds [(id, chance, countmax_or_None, inside_bag)]
CHANGES: dict[str, dict] = {
    # --- Fixes críticos y balance de monstruos nuevos/8.60 ---
    "quara predator.xml": dict(
        stats=dict(armor=38, defense=38, experience=1800, melee=(40, 270)),
        remove_ids={2390, 2496, 2654},  # sacar Magic Longsword, Horned Helmet y cape rara
        dedup=True,
        adds=[
            (2152, 12000, 2, False),   # platinum coin
            (2547, 5000, 6, False),    # power bolt
            (2274, 3500, None, False), # avalanche rune
            (2475, 900, None, False),  # warrior helmet
            (2528, 600, None, False),  # tower shield
            (20102, 450, None, False), # morlen crest
            (2393, 350, None, False),  # giant sword
        ],
    ),
    "thornback tortoise.xml": dict(
        stats=dict(armor=22, defense=24),
        remove_ids={2391},  # sacar War Hammer (16% bug!)
        dedup=True,
        adds=[
            (2510, 3500, None, False), # plate shield
            (2513, 900, None, False),  # battle shield
        ],
    ),
    "tortoise.xml": dict(
        stats=dict(armor=16, defense=18),
    ),
    "earth elemental.xml": dict(
        remove_ids={2546},  # sacar 30 burst arrows al 20%
        dedup=True,
        adds=[
            (1294, 22000, 12, False),  # small stone limpio
            (2288, 2500, None, False), # stone shower rune
            (2149, 2000, 1, False),    # small emerald
            (2483, 2500, None, False), # scale armor
            (2510, 2500, None, False), # plate shield
        ],
    ),
    "worker golem.xml": dict(
        dedup=True,
        adds=[
            (2391, 900, None, False),  # war hammer (único)
            (2164, 400, None, False),  # might ring (único)
            (2145, 2500, 2, False),    # small diamond (único)
            (2288, 3500, None, False), # stone shower rune
            (2509, 4000, None, False), # steel shield
            (20120, 350, None, False), # boltworker crossbow
        ],
    ),
    "zombie.xml": dict(
        remove_ids={2205},  # active life ring -> normal life ring
        dedup=True,
        adds=[
            (2168, 1000, None, False), # life ring
        ],
    ),
    "chakoya windcaller.xml": dict(
        remove_ids={2656},  # sacar blue robe de mob 84 HP
        adds=[
            (2654, 2000, None, False), # cape
            (2271, 1200, None, False), # icicle rune
        ],
    ),
    "elder beholder.xml": dict(
        stats=dict(health=700, experience=580, armor=25, defense=25, melee=(0, 110)),
        fix_summon=("baby beholder", "gazer"),
        adds=[
            (2175, 4500, None, False), # spellbook
            (2311, 3000, None, False), # heavy magic missile
            (2150, 2500, 2, False),    # small amethyst
            (2518, 1200, None, True),  # beholder shield
            (2188, 700, None, True),   # wand of plague
            (2323, 350, None, True),   # hat of the mad
        ],
    ),
    "ice spider.xml": dict(
        stats=dict(armor=32, defense=34, experience=1550, melee=(100, 260)),
        remove_ids={0},
        adds=[
            (2271, 4000, None, False), # icicle rune
            (2274, 3500, None, True),  # avalanche rune
            (20372, 350, None, True),  # aurora blade
        ],
    ),
    "red kongra.xml": dict(
        stats=dict(health=550, experience=340, armor=18, defense=20),
    ),
    "undead gladiator.xml": dict(
        stats=dict(armor=32, defense=34),
    ),
    "quara pincher.xml": dict(
        stats=dict(armor=38, defense=38, experience=1350),
        dedup=True,
        adds=[
            (2274, 2500, None, False), # avalanche rune
            (20153, 250, None, False), # frostwarden aegis
        ],
    ),
    "quara mantassin.xml": dict(
        stats=dict(experience=500, armor=18, defense=18),
        dedup=True,
    ),
    "quara constrictor.xml": dict(
        dedup=True,
        adds=[
            (2271, 2000, None, False), # icicle rune
        ],
    ),
    "quara hydromancer.xml": dict(
        dedup=True,
        adds=[
            (2271, 3500, None, False), # icicle rune
            (2315, 3500, None, False), # thunderstorm rune
            (2183, 600, None, False),  # tempest rod
            (20149, 300, None, False), # mosaic shield
        ],
    ),
    "water elemental.xml": dict(
        adds=[
            (2152, 15000, 2, False),   # platinum coin
            (2271, 3500, None, False), # icicle rune
            (2274, 2000, None, False), # avalanche rune
        ],
    ),
    "pirate corsair.xml": dict(
        stats=dict(experience=450),
    ),
    "dragon hatchling.xml": dict(
        stats=dict(experience=230, armor=16, defense=18),
    ),
    "bog raider.xml": dict(
        stats=dict(experience=950),
        adds=[
            (2149, 3500, 2, False),    # small emerald
            (2269, 1500, None, False), # wild growth rune
        ],
    ),
    "mutated tiger.xml": dict(
        stats=dict(experience=850, melee=(65, 220)),
    ),
    "nightstalker.xml": dict(
        remove_ids={2391},  # war hammer mal mapeado
        adds=[
            (2656, 300, None, False),  # blue robe
            (2165, 800, None, False),  # stealth ring
        ],
    ),
    "vampire bride.xml": dict(
        dedup=True,
        adds=[
            (2197, 400, None, False),  # stone skin amulet
            (2323, 350, None, False),  # hat of the mad
            (20129, 350, None, False), # wayfarer boots
        ],
    ),
    "wyrm.xml": dict(
        remove_ids={2455, 2456, 2654, 2657},  # mal mapeados de 8.60
        dedup=True,
        adds=[
            (2315, 4500, None, False), # thunderstorm rune
            (2189, 1200, None, False), # wand of cosmic energy
            (2167, 1200, None, False), # energy ring
            (2154, 800, None, False),  # yellow gem
            (2436, 500, None, False),  # skull staff
            (2171, 500, None, False),  # platinum amulet
            (20156, 500, None, False), # enchanted spear
            (20129, 450, None, False), # wayfarer boots
            (20102, 400, None, False), # morlen crest
            (20120, 350, None, False), # boltworker crossbow
        ],
    ),
    # --- Limpiar id="0" muertos ---
    "gargoyle.xml": dict(remove_ids={0}),
    "giant spider.xml": dict(remove_ids={0}),
    "minotaur archer.xml": dict(remove_ids={0}),
    "minotaur guard.xml": dict(remove_ids={0}),
    "demon skeleton.xml": dict(remove_ids={0}),
    "orc rider.xml": dict(remove_ids={0}),
    "murius.xml": dict(remove_ids={0}),
    # --- Familias fuertes: Frost / Ice ---
    "frost dragon.xml": dict(
        dedup=True,
        adds=[
            (2271, 5000, None, False), # icicle rune
            (2274, 4500, None, False), # avalanche rune
            (2154, 1000, None, True),  # yellow gem
            (20153, 550, None, True),  # frostwarden aegis
            (20129, 500, None, True),  # wayfarer boots
            (20372, 450, None, True),  # aurora blade
            (20373, 450, None, True),  # aurora axe
            (20374, 400, None, True),  # frostbound bow
        ],
    ),
    "crystal spider.xml": dict(
        adds=[
            (2271, 4000, None, False), # icicle rune
            (2274, 3500, None, False), # avalanche rune
            (20153, 350, None, False), # frostwarden aegis
            (20373, 250, None, False), # aurora axe
            (20374, 250, None, False), # frostbound bow
        ],
    ),
    "ice monk.xml": dict(
        adds=[
            (2271, 3500, None, False), # icicle rune
            (20373, 300, None, True),  # aurora axe
        ],
    ),
    # --- Familia Metal (identidad endgame propia + gemas para imbuir) ---
    "metal dragon.xml": dict(
        adds=[
            (2547, 6000, 8, False),    # power bolt
            (2146, 10000, 3, False),   # small sapphire boost
            (2147, 6000, 2, False),    # small ruby
            (2150, 5000, 2, False),    # small amethyst
            (2201, 1500, None, True),  # dragon necklace
            (20152, 450, None, True),  # fox machina helmet
            (20148, 450, None, True),  # kilnfire leggings
            (20151, 400, None, True),  # sunforge shield
        ],
    ),
    "metal hydra.xml": dict(
        adds=[
            (2274, 3500, None, False), # avalanche rune
            (2149, 10000, 3, False),   # small emerald boost
            (2146, 7000, 3, True),     # small sapphire boost
            (2150, 5000, 2, False),    # small amethyst
            (2197, 800, None, True),   # stone skin amulet
            (20149, 450, None, True),  # mosaic shield
            (20104, 450, None, True),  # basalt greaves
        ],
    ),
    "metal demon.xml": dict(
        adds=[
            (2315, 4500, None, False), # thunderstorm rune
            (2147, 10000, 3, False),   # small ruby
            (2149, 7000, 3, True),     # small emerald boost
            (2145, 6000, 3, False),    # small diamond
            (2197, 1000, None, True),  # stone skin amulet
            (20152, 600, None, True),  # fox machina helmet
            (20104, 550, None, True),  # basalt greaves
            (20147, 400, None, True),  # obsidian regalia
        ],
    ),
    # --- Hydras, Behemoth, Root Colossus ---
    "dark hydra.xml": dict(
        adds=[
            (2197, 1000, None, True),  # stone skin amulet
            (2154, 1000, None, True),  # yellow gem
            (2183, 600, None, True),   # tempest rod
            (20149, 350, None, True),  # mosaic shield
        ],
    ),
    "hydra.xml": dict(
        adds=[
            (2197, 700, None, True),   # stone skin amulet
        ],
    ),
    "behemoth.xml": dict(
        adds=[
            (2288, 4500, None, False), # stone shower rune
            (2547, 6000, 8, False),    # power bolt
            (2208, 1800, None, True),  # axe ring
            (2197, 900, None, True),   # stone skin amulet
            (20104, 250, None, True),  # basalt greaves
        ],
    ),
    "root colossus.xml": dict(
        adds=[
            (2288, 5000, None, False), # stone shower rune
            (2269, 2000, None, True),  # wild growth rune
            (2197, 1000, None, True),  # stone skin amulet
            (20102, 600, None, True),  # morlen crest
        ],
    ),
    # --- Magos, Warlock, Banshee, Fury, Wrath, Hellhound ---
    "warlock.xml": dict(
        adds=[
            (2268, 3500, None, False), # sudden death rune
            (2293, 1800, None, True),  # magic wall rune
            (2296, 1500, None, True),  # anchor rune
            (2197, 1200, None, True),  # stone skin amulet
            (2323, 900, None, True),   # hat of the mad
            (20118, 300, None, True),  # starbinder hood
        ],
    ),
    "dark mage.xml": dict(
        adds=[
            (2293, 2000, None, True),  # magic wall rune
            (2296, 1800, None, True),  # anchor rune
            (20273, 1200, None, True), # crimson cage rune
            (2323, 1200, None, True),  # hat of the mad
            (2197, 1000, None, True),  # stone skin amulet
            (20118, 450, None, True),  # starbinder hood
        ],
    ),
    "banshee.xml": dict(
        adds=[
            (2197, 800, None, True),   # stone skin amulet
            (2323, 600, None, True),   # hat of the mad
        ],
    ),
    "fury.xml": dict(
        adds=[
            (2547, 6000, 10, False),   # power bolt
            (2293, 1800, None, True),  # magic wall rune
            (20273, 1500, None, True), # crimson cage rune
            (20148, 400, None, True),  # kilnfire leggings
        ],
    ),
    "wrath.xml": dict(
        adds=[
            (20273, 2000, None, True), # crimson cage rune
            (20124, 500, None, True),  # azure sunstone
            (20147, 250, None, True),  # obsidian regalia
        ],
    ),
    "hellhound.xml": dict(
        adds=[
            (2201, 1800, None, False), # dragon necklace
            (2293, 1200, None, False), # magic wall rune
            (20273, 1000, None, False),# crimson cage rune
            (20148, 250, None, False), # kilnfire leggings
        ],
    ),
    # --- Dragones, Imperiales, Serpent Spawn ---
    "dragon lord.xml": dict(
        adds=[
            (2547, 5500, 6, False),    # power bolt
            (2201, 1500, None, True),  # dragon necklace
        ],
    ),
    "black dragon.xml": dict(
        adds=[
            (2547, 6500, 8, False),    # power bolt
            (2201, 1800, None, True),  # dragon necklace
            (2154, 800, None, True),   # yellow gem
        ],
    ),
    "imperial hero.xml": dict(
        adds=[
            (2547, 6000, 8, False),    # power bolt
            (2295, 4500, None, False), # holy missile rune
            (20156, 550, None, True),  # enchanted spear
            (20120, 450, None, True),  # boltworker crossbow
        ],
    ),
    "the fallen emperor.xml": dict(
        adds=[
            (2295, 8000, None, False), # holy missile rune
            (2154, 3000, None, True),  # yellow gem
            (20125, 2000, None, True), # verdant sunstone
            (20124, 1200, None, True), # azure sunstone
        ],
    ),
    "serpent spawn.xml": dict(
        adds=[
            (2269, 1500, None, True),  # wild growth rune
            (2197, 700, None, True),   # stone skin amulet
            (20156, 500, None, True),  # enchanted spear
        ],
    ),
    # --- Elfos, Orcos, Enanos ---
    "elven archmage.xml": dict(
        adds=[
            (2198, 2500, None, True),  # elven amulet
            (2293, 2000, None, True),  # magic wall rune
            (2352, 800, None, True),   # crystal arrow
            (20118, 500, None, True),  # starbinder hood
        ],
    ),
    "elvenbane ranger.xml": dict(
        adds=[
            (2547, 7000, 10, False),   # power bolt
            (2198, 2500, None, True),  # elven amulet
            (20374, 800, None, True),  # frostbound bow
        ],
    ),
    "blue elf arcanist.xml": dict(
        adds=[
            (2198, 1200, None, True),  # elven amulet
        ],
    ),
    "elf arcanist.xml": dict(
        adds=[
            (2198, 1200, None, True),  # elven amulet
        ],
    ),
    "orc warlord.xml": dict(
        adds=[
            (2208, 1500, None, True),  # axe ring
            (2352, 350, None, True),   # crystal arrow (segunda fuente)
        ],
    ),
    "dwarf guard.xml": dict(
        adds=[
            (2208, 900, None, True),   # axe ring
        ],
    ),
    "capataz de hierro.xml": dict(
        adds=[
            (2208, 2500, None, True),  # axe ring
            (20125, 1000, None, True), # verdant sunstone
        ],
    ),
    # --- Bosses (consumibles especiales, sin pisar premium 20131/20132) ---
    "ashen lord.xml": dict(
        adds=[
            (20125, 2500, None, True), # verdant sunstone
            (20124, 1500, None, True), # azure sunstone (soft boots recharge)
            (20151, 1000, None, True), # sunforge shield
        ],
    ),
    "orshabaal.xml": dict(
        adds=[
            (20125, 2500, None, True), # verdant sunstone
            (20124, 1500, None, True), # azure sunstone
        ],
    ),
    "lord of elvenbane.xml": dict(
        adds=[
            (20125, 2000, None, True), # verdant sunstone
            (2352, 1500, None, True),  # crystal arrow
            (20124, 1200, None, True), # azure sunstone
        ],
    ),
    "demodras.xml": dict(
        adds=[
            (20125, 1500, None, True), # verdant sunstone
            (20124, 1000, None, True), # azure sunstone
        ],
    ),
    "custodio del lago.xml": dict(
        adds=[
            (20125, 1200, None, True), # verdant sunstone
        ],
    ),
    "emerald scarab.xml": dict(),  # solo split gold > 100
}


def main() -> int:
    otb = load_otb_info()
    updated = 0
    for fname, spec in CHANGES.items():
        path = MON_DIR / fname
        assert path.exists(), f"No existe {path}"
        tree = ET.parse(path)
        root = tree.getroot()
        if "stats" in spec:
            set_stats(root, **spec["stats"])
        if "fix_summon" in spec:
            old_s, new_s = spec["fix_summon"]
            for s in root.findall(".//summon"):
                if s.attrib.get("name", "").lower() == old_s.lower():
                    s.attrib["name"] = new_s
        if "remove_ids" in spec:
            remove_loot_ids(root, spec["remove_ids"])
        if spec.get("dedup"):
            dedup_loot(root)
        split_big_gold(root)
        for iid, ch, cm, in_bag in spec.get("adds", []):
            upsert_loot(root, otb, iid, ch, cm, inside_bag=in_bag)
        save_monster(path, root)
        updated += 1
        print(f"  [ok] {fname}")

    # Limpiar id="0" en variantes rage históricas de gargoyle/giant spider/minotaur
    for fname in ("angry gargoyle.xml", "furious gargoyle.xml", "enraged gargoyle.xml",
                  "angry giant spider.xml", "furious giant spider.xml", "enraged giant spider.xml",
                  "angry minotaur archer.xml", "furious minotaur archer.xml", "enraged minotaur archer.xml",
                  "angry minotaur guard.xml", "furious minotaur guard.xml", "enraged minotaur guard.xml"):
        path = MON_DIR / fname
        if path.exists():
            tree = ET.parse(path)
            root = tree.getroot()
            if remove_loot_ids(root, {0}):
                save_monster(path, root)
                print(f"  [clean id=0] {fname}")

    print(f"Actualizados {updated} monstruos base.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
