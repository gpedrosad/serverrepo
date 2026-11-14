#!/usr/bin/env python3
"""Genera (y audita) las variantes rage Angry/Furious/Enraged de los monstruos nuevos.

El sistema rage es data pura: `game.cpp` -> `trySpawnRageMonster` busca "Angry <Nombre>",
"Furious <Nombre>" y "Enraged <Nombre>" en `monsters.xml` al morir un monstruo. Las 42 familias
historicas se escribieron a mano (jun 2026) y los monstruos agregados despues (jul-nov 2026)
quedaron sin variantes. Este script las crea con las mismas formulas por tramo de experiencia.

  python3 scripts/monsters/rage-variants.py            # auditoria (no escribe)
  python3 scripts/monsters/rage-variants.py --write    # genera XMLs + registra en monsters.xml
  python3 scripts/monsters/rage-variants.py --write --only "Wyrm" "Zombie"

Formulas (derivadas de las 42 familias originales, ver docs/gameplay/RAGE_MONSTERS.md):

  tramo (exp base)   nivel/mag   armor/def   speed     HP            exp           dano
  < 50               +4/+8/+12   +2/+4/+6    +10/16/22 1.44/1.8/2.2  1.75/2.2/2.8  1.30/1.60/1.90
  50 - 149           +5/+10/+15  +3/+5/+7    +12/18/24 1.55/1.95/2.35 1.9/2.4/3.05 1.40/1.75/2.10
  150 - 699          +7/+13/+19  +4/+6/+8    +14/20/26 1.7/2.1/2.55   2.1/2.7/3.4   1.50/1.90/2.30
  700 - 1999         +9/+16/+24  +5/+7/+10   +16/22/30 1.85/2.3/2.8   2.3/3.0/3.8   1.60/2.05/2.50
  >= 2000            +12/+20/+30 +6/+8/+12   +18/24/34 2.0/2.5/3.05   2.5/3.3/4.2   1.70/2.20/2.70

  (los tres valores de cada celda son Angry / Furious / Enraged)

Ademas: pushable=0, canpushitems=1, runonhealth=0, grito extra en <voices> y bloque de gemas
pequenas por tramo al final del loot. Los multiplicadores de gemas por prefijo (x2.4 furious,
x3.2 enraged) los aplica el motor en monsters.cpp; aca van las chances base como en las
variantes historicas.

No toca jefes, trainers, mascotas ni crias (ver EXCLUDED). Doc: docs/gameplay/RAGE_MONSTERS.md.
"""
from __future__ import annotations

import argparse
import copy
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MON = REPO / "server/YurOTS/ots/data/monster"
REGISTRY = MON / "monsters.xml"

STAGES = (
    ("angry", "Angry", "GRAAAH!"),
    ("furious", "Furious", "RAAAARGH!"),
    ("enraged", "Enraged", "SKREEEAAAH!"),
)
PREFIXES = {display + " ": slug for slug, display, _yell in STAGES}

# exp maxima del tramo, (nivel/maglevel, armor/defense, speed), (hp, exp, dano)
TIERS = (
    (50, (4, 8, 12), (2, 4, 6), (10, 16, 22), (1.45, 1.80, 2.20), (1.75, 2.20, 2.80), (1.30, 1.60, 1.90)),
    (150, (5, 10, 15), (3, 5, 7), (12, 18, 24), (1.55, 1.95, 2.35), (1.90, 2.40, 3.05), (1.40, 1.75, 2.10)),
    (700, (7, 13, 19), (4, 6, 8), (14, 20, 26), (1.70, 2.10, 2.55), (2.10, 2.70, 3.40), (1.50, 1.90, 2.30)),
    (2000, (9, 16, 24), (5, 7, 10), (16, 22, 30), (1.85, 2.30, 2.80), (2.30, 3.00, 3.80), (1.60, 2.05, 2.50)),
    (None, (12, 20, 30), (6, 8, 12), (18, 24, 34), (2.00, 2.50, 3.05), (2.50, 3.30, 4.20), (1.70, 2.20, 2.70)),
)

# id, countmax, chance1 (base; el motor multiplica por prefijo)
GEMS = (
    (((2150, 1, 1250), (2149, 1, 625)),
     ((2150, 1, 12000), (2149, 1, 8000), (2147, 1, 5000), (2146, 1, 2500)),
     ((2150, 1, 12000), (2149, 1, 8000), (2147, 1, 5000), (2146, 1, 2500))),
    (((2150, 1, 2000), (2149, 1, 1375)),
     ((2150, 1, 18000), (2149, 1, 13000), (2147, 1, 9000), (2146, 1, 6000), (2145, 1, 2500)),
     ((2150, 1, 18000), (2149, 1, 13000), (2147, 1, 9000), (2146, 1, 6000), (2145, 1, 2500))),
    (((2150, 1, 3000), (2149, 1, 2250)),
     ((2150, 3, 26000), (2149, 3, 21000), (2147, 2, 16000), (2146, 2, 11000), (2145, 1, 6000)),
     ((2150, 3, 26000), (2149, 3, 21000), (2147, 2, 16000), (2146, 2, 11000), (2145, 1, 6000))),
    (((2150, 2, 9000), (2149, 2, 7000), (2147, 1, 5000), (2146, 1, 3750), (2145, 1, 2250)),
     ((2150, 4, 36000), (2149, 4, 30000), (2147, 3, 24000), (2146, 3, 18000), (2145, 2, 10000)),
     ((2150, 4, 36000), (2149, 4, 30000), (2147, 3, 24000), (2146, 3, 18000), (2145, 2, 10000))),
    (((2150, 2, 12000), (2149, 2, 10000), (2147, 2, 8000), (2146, 2, 6000), (2145, 1, 3500)),
     ((2150, 5, 46000), (2149, 5, 40000), (2147, 4, 32000), (2146, 4, 25000), (2145, 3, 14000)),
     ((2150, 5, 46000), (2149, 5, 40000), (2147, 4, 32000), (2146, 4, 25000), (2145, 3, 14000))),
)
# Furious de tramo alto agrega Gold Nugget (2157), como las variantes historicas.
GOLD_NUGGET = {3: 1500, 4: 3000}

# Monstruos nuevos cazables (jul-nov 2026) que deben tener las tres variantes.
CURATED = (
    # custom / bosses de zona (no jefes)
    "Black Dragon", "Frost Dragon", "Blue Elf Arcanist", "Drowned Sailor", "Ice Monk", "Ice Spider",
    "Tide Priest", "Hellhound", "Court Mage", "Dark Hydra", "Emerald Scarab", "Root Colossus",
    "Imperial Squire", "Imperial Archer", "Imperial Hero", "Serpent Spawn",
    # 8.60: piratas, isla helada, valle, etc.
    "Pirate Marauder", "Pirate Cutthroat", "Pirate Buccaneer", "Pirate Corsair",
    "Barbarian Headsplitter", "Barbarian Skullhunter", "Barbarian Brutetamer", "Barbarian Bloodwalker",
    "Chakoya Tribewarden", "Chakoya Toolshaper", "Chakoya Windcaller",
    "Frost Giant", "Frost Giantess", "Ice Golem", "Crystal Spider", "Bog Raider",
    "Tortoise", "Thornback Tortoise", "Mammoth", "Blood Crab",
    "Quara Constrictor", "Quara Hydromancer", "Quara Mantassin", "Quara Pincher", "Quara Predator",
    "Cyclops Drone", "Cyclops Smith", "Wyrm", "Earth Elemental", "Water Elemental", "Zombie",
    "Vampire Bride", "Worker Golem", "Undead Gladiator", "Nightstalker",
    "Mutated Human", "Mutated Rat", "Mutated Bat", "Mutated Tiger", "Wyvern",
    # variante especial de orco (Bamboo)
    "Orc Berserker Pot Thrower",
)

# Quedan afuera a proposito (se listan para que la auditoria no los marque como error).
EXCLUDED = {
    "Ashen Lord": "jefe de Hell Quest",
    "The Fallen Emperor": "jefe del Castillo Imperial",
    "Crucible Ashlord": "jefe diario (El Crisol)",
    "Crucible Bloodreaver": "jefe diario (El Crisol)",
    "Crucible Bonepriest": "jefe diario (El Crisol)",
    "Crucible Frostwarden": "jefe diario (El Crisol)",
    "Crucible Ironhide": "jefe diario (El Crisol)",
    "Crucible Stormcaller": "jefe diario (El Crisol)",
    "Crucible Venomqueen": "jefe diario (El Crisol)",
    "Private Trainer Dummy": "training",
    "Mini Trainer Monk": "training",
    "Trainer Monk": "training",
    "Elite Trainer Monk": "training",
    "Husky": "mascota",
    "Dragon Hatchling": "cria",
    "Dragon Lord Hatchling": "cria",
    "Frost Dragon Hatchling": "cria",
    "Fury": "elite custom (ya es furia)",
    "Wrath": "jefe de la Gauntlet",
}


def esc(value: str) -> str:
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def fmt_el(el: ET.Element, depth: int) -> str:
    pad = "\t" * depth
    attrs = "".join(f' {k}="{esc(v)}"' for k, v in el.attrib.items())
    kids = list(el)
    if not kids:
        return f"{pad}<{el.tag}{attrs} />\n"
    out = f"{pad}<{el.tag}{attrs}>\n"
    for kid in kids:
        out += fmt_el(kid, depth + 1)
    return out + f"{pad}</{el.tag}>\n"


def tier_index(experience: int) -> int:
    for i, tier in enumerate(TIERS):
        if tier[0] is None or experience < tier[0]:
            return i
    raise AssertionError("tramo no encontrado")


def scale(value: str, factor: float) -> str:
    return str(int(round(int(value) * factor)))


def build_variant(base: ET.Element, name: str, stage: int) -> str:
    root = copy.deepcopy(base)
    exp = int(root.get("experience"))
    tier = tier_index(exp)
    _limit, lv_delta, ad_delta, sp_delta, hp_ratio, exp_ratio, dmg_ratio = TIERS[tier]

    root.set("name", name)
    root.set("level", str(int(root.get("level", 0)) + lv_delta[stage]))
    root.set("maglevel", str(int(root.get("maglevel", 0)) + lv_delta[stage]))
    root.set("experience", str(int(round(exp * exp_ratio[stage]))))
    root.set("pushable", "0")
    root.set("canpushitems", "1")
    if root.get("armor") is not None:
        root.set("armor", str(int(root.get("armor")) + ad_delta[stage]))
    if root.get("defense") is not None:
        root.set("defense", str(int(root.get("defense")) + ad_delta[stage]))
    if root.get("speed") is not None:
        root.set("speed", str(int(root.get("speed")) + sp_delta[stage]))

    health = root.find("health")
    if health is not None:
        hp = int(round(int(health.get("max", health.get("now", 100))) * hp_ratio[stage]))
        health.set("now", str(hp))
        health.set("max", str(hp))

    combat = root.find("combat")
    if combat is not None:
        combat.set("runonhealth", "0")

    for attack in root.iter("attack"):
        for attr in ("mindamage", "maxdamage"):
            value = attack.get(attr)
            if value is not None and value.isdigit():
                attack.set(attr, scale(value, dmg_ratio[stage]))

    voices = root.find("voices")
    if voices is None:
        voices = ET.Element("voices")
        loot = root.find("loot")
        root.insert(list(root).index(loot) if loot is not None else len(root), voices)
    ET.SubElement(voices, "voice", {"sentence": STAGES[stage][2]})

    loot = root.find("loot")
    if loot is None:
        loot = ET.SubElement(root, "loot")
    for item_id, countmax, chance in GEMS[tier][stage]:
        ET.SubElement(loot, "item", {
            "id": str(item_id), "countmax": str(countmax),
            "chance1": str(chance), "chancemax": "0",
        })
    if stage == 1 and tier in GOLD_NUGGET:
        ET.SubElement(loot, "item", {
            "id": "2157", "countmax": "1",
            "chance1": str(GOLD_NUGGET[tier]), "chancemax": "0",
        })

    header = "<?xml version='1.0' encoding='utf-8'?>\n"
    body = "".join(fmt_el(kid, 1) for kid in root)
    attrs = " ".join(f'{k}="{esc(v)}"' for k, v in root.attrib.items())
    return header + f"<monster {attrs}>\n" + body + "</monster>\n"


def strip_prefix(name: str) -> str | None:
    for prefix in PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):]
    return None


def load_registry() -> list[tuple[str, str]]:
    return [(m.get("name"), m.get("file")) for m in ET.parse(REGISTRY).getroot().findall("monster")]


def audit(registry: list[tuple[str, str]]) -> int:
    bases = [n for n, _f in registry if strip_prefix(n) is None]
    registered = {n for n, _f in registry}
    missing = {}
    for name in bases:
        lacking = [slug for slug, display, _y in STAGES
                   if display + " " + name not in registered
                   or not (MON / f"{slug} {name.lower()}.xml").exists()]
        if lacking:
            missing[name] = lacking
    complete = len(bases) - len(missing)

    print(f"Monstruos base: {len(bases)} | con rage completo: {complete} | sin variantes: {len(missing)}")
    print(f"Familias nuevas curadas: {len(CURATED)}\n")

    pending = [(n, l) for n, l in missing.items() if n in CURATED]
    for name, lacking in pending:
        print(f"  FALTA {name}: {', '.join(lacking)}")
    if not pending:
        print("  Todas las familias nuevas tienen Angry/Furious/Enraged.")

    known = set(bases)
    unknown = [n for n in CURATED if n not in known]
    if unknown:
        print("\nEn CURATED pero no en monsters.xml: " + ", ".join(unknown), file=sys.stderr)
        return 1

    rest = [n for n in missing if n not in CURATED and n not in EXCLUDED]
    if rest:
        print(f"\nOtras familias sin rage ({len(rest)}, fuera de alcance): " + ", ".join(sorted(rest)))
    return 1 if pending else 0


def update_registry(text: str, plans: dict[str, list[tuple[str, str]]]) -> str:
    variant_names = {vn for entries in plans.values() for vn, _vf in entries}
    out = []
    for line in text.splitlines(keepends=True):
        match = re.search(r'<monster name="([^"]+)"', line)
        if match and match.group(1) in variant_names and strip_prefix(match.group(1)):
            continue  # re-generacion: se reinsertan junto al base
        out.append(line)
        if match and match.group(1) in plans:
            indent = line[:len(line) - len(line.lstrip())]
            for vname, vfile in plans[match.group(1)]:
                out.append(f'{indent}<monster name="{vname}" file="{vfile}" />\n')
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="escribe los XML y monsters.xml")
    parser.add_argument("--only", nargs="+", metavar="MONSTER", help="limita a estos monstruos base")
    args = parser.parse_args()

    registry = load_registry()
    by_name = dict(registry)

    if not args.write:
        return audit(registry)

    targets = list(args.only) if args.only else list(CURATED)
    unknown = [n for n in targets if n not in by_name]
    if unknown:
        print("No estan en monsters.xml: " + ", ".join(unknown), file=sys.stderr)
        return 1

    plans: dict[str, list[tuple[str, str]]] = {}
    for name in targets:
        base_file = by_name[name]
        base_path = MON / base_file
        base = ET.parse(base_path).getroot()
        prefix = strip_prefix(name)
        if prefix is not None:
            print(f"{name}: ya es una variante, se omite", file=sys.stderr)
            continue
        entries = []
        for stage, (slug, display, _yell) in enumerate(STAGES):
            variant_name = f"{display} {name}"
            variant_file = f"{slug} {base_file}"
            entries.append((variant_name, variant_file))
            (MON / variant_file).write_text(build_variant(base, variant_name, stage), encoding="utf-8")

        exp = int(base.get("experience"))
        hp = int(base.find("health").get("max"))
        tier = tier_index(exp)
        ratios = TIERS[tier]
        print(f"{name:28} tramo {tier + 1} exp {exp}->{int(round(exp*ratios[5][0]))}/"
              f"{int(round(exp*ratios[5][1]))}/{int(round(exp*ratios[5][2]))} "
              f"hp {hp}->{int(round(hp*ratios[4][0]))}/{int(round(hp*ratios[4][1]))}/{int(round(hp*ratios[4][2]))}")
        plans[name] = entries

    REGISTRY.write_text(update_registry(REGISTRY.read_text(encoding="utf-8"), plans), encoding="utf-8")
    print(f"\n{len(plans)} familias, {len(plans) * 3} variantes escritas y registradas en monsters.xml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
