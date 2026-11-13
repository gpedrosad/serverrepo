#!/usr/bin/env python3
"""Les da a los monstruos nuevos un "kit" de ataques acorde a su nivel, con efectos y hechizos de su tema.

Solo para los monstruos agregados en nov 2026 (Castillo Imperial y criaturas de 8.60) que pegaban solo cuerpo a
cuerpo o con un proyectil común: les suma 1 o 2 ataques temáticos (hielo a los del norte, cañonazos a los
piratas, rugido a los bárbaros...) con el daño escalado a cada uno. Los monstruos de siempre no se tocan.

  python3 scripts/monsters/apply-monster-kits.py --dry-run     # muestra qué le toca a cada uno
  python3 scripts/monsters/apply-monster-kits.py               # escribe

Qué escribe:
  - data/spells/instant/k_*.lua y data/spells/runes/k_*.lua: un hechizo por elemento, forma y escalón de daño.
  - el bloque MONSTER_KITS de data/spells/spells.xml (runas con id 6000+, libres en el items.otb).
  - las líneas <attack ... kit="1"/> de cada monstruo de KITS (el servidor ignora el atributo `kit`; sirve para que el
    script las reemplace al volver a correrlo). No toca los ataques que ya tenía.

Daño: se toma el golpe máximo del monstruo (cuerpo a cuerpo o proyectil) y se elige el escalón (TIERS) cuyo
máximo queda más cerca del 75 % de ese golpe. KITS dice qué le toca a cada monstruo; "-1"/"+1" corre el
escalón. Para sumar otro monstruo, agregarlo a KITS. Doc: docs/gameplay/MONSTER_KITS.md.
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "server/YurOTS/ots/data"
MON = DATA / "monster"
SPELLS = DATA / "spells"
RUNE_ID0 = 6000

# escalones de daño (mínimo, máximo)
TIERS = {1: (5, 20), 2: (10, 35), 3: (20, 55), 4: (35, 80), 5: (50, 110), 6: (70, 150), 7: (100, 200),
         8: (140, 270), 9: (190, 350), 10: (250, 450)}
# elemento -> tipo de daño, proyectil, efecto del área, efecto al pegar, efecto de daño, color, sangre
ELEMENTS = {
    "fire": ("ATTACK_FIRE", "NM_ANI_FIRE", "NM_ME_FIRE_AREA", "NM_ME_FIRE_AREA", "NM_ME_HITBY_FIRE", "FIRE", False),
    "burst": ("ATTACK_FIRE", "NM_ANI_BURSTARROW", "NM_ME_FIRE_AREA", "NM_ME_FIRE_AREA", "NM_ME_HITBY_FIRE", "FIRE", False),
    "energy": ("ATTACK_ENERGY", "NM_ANI_ENERGY", "NM_ME_ENERGY_AREA", "NM_ME_ENERGY_AREA", "NM_ME_ENERGY_DAMAGE", "ENERGY", False),
    "poison": ("ATTACK_POISON", "NM_ANI_FLYPOISONFIELD", "NM_ME_POISONCLOUD", "NM_ME_POISEN_RINGS", "NM_ME_POISEN_RINGS", "GREEN", False),
    "venom": ("ATTACK_POISON", "NM_ANI_POISONARROW", "NM_ME_POISONCLOUD", "NM_ME_POISEN_RINGS", "NM_ME_POISEN_RINGS", "GREEN", True),
    "blade": ("ATTACK_POISON", "NM_ANI_THROWINGKNIFE", "NM_ME_POISONCLOUD", "NM_ME_POISEN_RINGS", "NM_ME_POISEN_RINGS", "GREEN", True),
    "ice": ("ATTACK_PHYSICAL", "NM_ANI_FROSTBALL", "NM_ME_ICE_AREA", "NM_ME_ICE_HIT", "NM_ME_ICE_SHATTER", "LIGHT_BLUE", False),
    "death": ("ATTACK_PHYSICAL", "NM_ANI_SUDDENDEATH", "NM_ME_MORT_AREA", "NM_ME_MORT_AREA", "NM_ME_MORT_AREA", "GREY", False),
    "drain": ("ATTACK_LIFEDRAIN", "NM_ANI_SHADOWBALL", "NM_ME_MAGIC_BLOOD", "NM_ME_MAGIC_BLOOD", "NM_ME_MAGIC_BLOOD", "RED", False),
    "earth": ("ATTACK_PHYSICAL", "NM_ANI_LARGEROCK", "NM_ME_EXPLOSION_AREA", "NM_ME_HIT_AREA", "NM_ME_DRAW_BLOOD", "RED", True),
    "cannon": ("ATTACK_PHYSICAL", "NM_ANI_SMALLSTONE", "NM_ME_EXPLOSION_AREA", "NM_ME_EXPLOSION_DAMAGE", "NM_ME_DRAW_BLOOD", "RED", True),
    "roar": ("ATTACK_PHYSICAL", "NM_ANI_NONE", "NM_ME_SOUND_RED", "NM_ME_SOUND_RED", "NM_ME_DRAW_BLOOD", "RED", True),
}
# forma -> (tipo, multiplicador del daño, descripción)
SHAPES = {
    "strike": ("rune", 1.0, "proyectil al blanco"),
    "touch": ("rune", 1.0, "golpe sin proyectil (mordida, picadura)"),
    "ball": ("rune", 0.8, "proyectil que estalla en 3x3"),
    "wave": ("instant", 1.0, "onda en cono hacia adelante"),
    "burst": ("instant", 0.8, "anillo alrededor suyo"),
}
HASTE = "orcb_haste"

# monstruo -> ataques. "elemento:forma[+-n]", "+haste", "+heal", "dist:proyectil". Solo monstruos nuevos.
KITS = {
    # Castillo Imperial
    "Imperial Squire": ["earth:touch"],
    "Imperial Archer": ["burst:ball"],
    # criaturas de 8.60 (import_client_look.py)
    "Pirate Marauder": ["burst:ball-1"],
    "Pirate Cutthroat": ["blade:strike"],
    "Pirate Buccaneer": ["cannon:ball"],
    "Pirate Corsair": ["cannon:ball", "+haste"],
    "Chakoya Tribewarden": ["ice:strike"],
    "Chakoya Toolshaper": ["ice:strike-1"],
    "Husky": ["ice:touch-1", "+haste"],
    "Barbarian Headsplitter": ["roar:burst", "+haste"],
    "Barbarian Skullhunter": ["roar:burst", "+haste"],
    "Barbarian Bloodwalker": ["roar:burst"],
    "Frost Giant": ["ice:burst"],
    "Frost Giantess": ["ice:burst"],
    "Mutated Tiger": ["roar:burst", "+haste"],
}


def area_lua(shape: str) -> str:
    if shape == "ball":
        rows = ["0,0,0,0,0", "0,1,1,1,0", "0,1,1,1,0", "0,1,1,1,0", "0,0,0,0,0"]
    elif shape == "burst":
        rows = ["0,0,0,0,0", "0,1,1,1,0", "0,1,0,1,0", "0,1,1,1,0", "0,0,0,0,0"]
    else:
        a = [[0] * 17 for _ in range(17)]
        for d in range(1, 5):
            hw = 0 if d < 3 else 1
            for o in range(-hw, hw + 1):
                a[8 - d][8 + o], a[8 + d][8 + o], a[8 + o][8 - d], a[8 + o][8 + d] = 1, 4, 2, 3
        rows = [",".join(map(str, r)) for r in a]
    return "area = {\n" + ",\n".join("{" + r + "}" for r in rows) + "\n}\n"


def spell_lua(elem: str, shape: str, tier: int) -> str:
    at, ani, area_fx, hit, dmg, color, blood = ELEMENTS[elem]
    lo, hi = TIERS[tier]
    k = SHAPES[shape][1]
    lo, hi = max(1, round(lo * k)), max(2, round(hi * k))
    if shape == "touch":
        ani = "NM_ANI_NONE"
    obj = "KitObject"
    head = (f"-- Generado por scripts/monsters/apply-monster-kits.py: {elem}, {SHAPES[shape][2]}, escalon {tier} "
            f"({lo}-{hi}). No editar a mano.\n")
    body = (f"attackType = {at}\nanimationEffect = {ani if shape in ('strike', 'touch', 'ball') else 'NM_ANI_NONE'}\n"
            f"hitEffect = {hit}\ndamageEffect = {dmg}\nanimationColor = {color}\noffensive = true\n"
            f"drawblood = {'true' if blood else 'false'}\n\n"
            f"{obj} = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, "
            f"offensive, drawblood, 0, 0)\n\n"
            "function onCast(cid, creaturePos, level, maglv, var)\n"
            "centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}\n"
            f"{obj}.minDmg = {lo}\n{obj}.maxDmg = {hi}\n")
    if shape in ("strike", "touch"):
        return head + body + f"return doTargetMagic(cid, centerpos, {obj}:ordered())\nend\n"
    direction = "true" if shape == "wave" else "false"
    return (head + area_lua(shape) + f"\nneedDirection = {direction}\nareaEffect = {area_fx}\n" + body +
            f"return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, {obj}:ordered())\nend\n")


def heal_lua(tier: int) -> str:
    lo, hi = TIERS[tier]
    return (f"-- Generado por scripts/monsters/apply-monster-kits.py: cura propia, escalon {tier}. No editar a mano.\n"
            "attackType = ATTACK_NONE\nanimationEffect = NM_ANI_NONE\nhitEffect = NM_ME_NONE\n"
            "damageEffect = NM_ME_MAGIC_ENERGIE\nanimationColor = GREEN\noffensive = false\ndrawblood = false\n\n"
            "KitHealObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, "
            "offensive, drawblood, 0, 0)\n\n"
            "function onCast(cid, creaturePos, level, maglv, var)\n"
            "centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}\n"
            f"KitHealObject.minDmg = {lo}\nKitHealObject.maxDmg = {hi}\n"
            "return doTargetMagic(cid, centerpos, KitHealObject:ordered())\nend\n")


def pick_tier(ref: int, shift: int) -> int:
    target = 0.75 * max(ref, 8)
    best = min(TIERS, key=lambda t: (abs(TIERS[t][1] - target), t))
    return max(1, min(len(TIERS), best + shift))


def timing(tier: int) -> tuple[int, int]:
    """(probabilidad, cycleticks) según el escalón: los débiles tiran menos seguido."""
    return (25, 4000) if tier <= 2 else (30, 3500) if tier <= 4 else (35, 3000) if tier <= 6 else (40, 2500)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    registry = {m.get("name"): m.get("file") for m in ET.parse(MON / "monsters.xml").getroot()}
    missing = [n for n in KITS if n not in registry]
    if missing:
        print("en KITS pero no en monsters.xml:", ", ".join(missing), file=sys.stderr)
        return 1
    plans = {}
    for name, kit in KITS.items():
        path = MON / registry[name]
        raw = path.read_text(encoding="latin-1")
        clean = re.sub(r"[ \t]*<attack [^>]*kit=\"1\"[^>]*/>\n", "", raw)
        root = ET.fromstring(clean.encode("latin-1"))
        ref = max([int(x.get("maxdamage", 0)) for x in root.iter("attack")] or [0])
        if ref <= 0:
            ref = int(root.find("health").get("max")) // 5
        plans[name] = (path, raw, clean, ref, kit)

    spells_needed, lines_by_monster = {}, {}
    for name, (path, raw, clean, ref, kit) in sorted(plans.items()):
        lines, desc = [], []
        for entry in kit:
            if entry == "+haste":
                lines.append(f'<attack type="instant" name="{HASTE}" exhaustion="500" cycleticks="6000" probability="15" kit="1"/>')
                desc.append("prisa")
                continue
            if entry == "+heal":
                t = pick_tier(ref, -1)
                sname = f"k_heal_{t}"
                spells_needed[sname] = ("instant", heal_lua(t))
                lines.append(f'<attack type="instant" name="{sname}" exhaustion="1000" cycleticks="6000" probability="20" kit="1"/>')
                desc.append(f"cura {TIERS[t][0]}-{TIERS[t][1]}")
                continue
            if entry.startswith("dist:"):
                proj = entry[5:]
                lo, hi = max(1, round(ref * 0.3)), max(3, round(ref * 0.8))
                lines.append(f'<attack type="distance" name="{proj}" mindamage="{lo}" maxdamage="{hi}" cycleticks="3000" probability="35" kit="1"/>')
                desc.append(f"{proj} {lo}-{hi}")
                continue
            m = re.fullmatch(r"(\w+):(\w+)([+-]\d+)?", entry)
            if not m or m.group(1) not in ELEMENTS or m.group(2) not in SHAPES:
                raise SystemExit(f"{name}: entrada de kit inválida {entry!r}")
            elem, shape, shift = m.group(1), m.group(2), int(m.group(3) or 0)
            t = pick_tier(ref, shift)
            sname = f"k_{elem}_{shape}_{t}"
            kind = SHAPES[shape][0]
            spells_needed[sname] = (kind, spell_lua(elem, shape, t))
            prob, cyc = timing(t)
            lines.append(f'<attack type="{kind}" name="{sname}" exhaustion="1000" cycleticks="{cyc}" probability="{prob}" kit="1"/>')
            desc.append(sname[2:])
        lines_by_monster[name] = lines
        print(f"{name:<26} golpe {ref:>4}: {', '.join(desc)}")

    runes = sorted(n for n, (k, _l) in spells_needed.items() if k == "rune")
    instants = sorted(n for n, (k, _l) in spells_needed.items() if k == "instant")
    print(f"\n{len(plans)} monstruos, {len(instants)} hechizos instantáneos y {len(runes)} runas")
    if a.dry_run:
        print("dry-run: no se escribió nada")
        return 0

    # --- hechizos ---
    for d in ("instant", "runes"):
        for f in (SPELLS / d).glob("k_*.lua"):
            if f.stem not in spells_needed:
                f.unlink()
    for n, (kind, lua) in spells_needed.items():
        (SPELLS / ("instant" if kind == "instant" else "runes") / f"{n}.lua").write_text(lua, encoding="latin-1")
    sx = (SPELLS / "spells.xml").read_text(encoding="latin-1")
    sx = re.sub(r"<!-- BEGIN MONSTER_KITS -->.*?<!-- END MONSTER_KITS -->\n?", "", sx, flags=re.S)
    block_i = "<!-- BEGIN MONSTER_KITS -->\n" + "".join(
        f'<spell name="{n}" words="{n}" maglv="4000" mana="800" enabled="1"></spell>\n' for n in instants)
    block_r = "".join(f'<rune name="{n}" id="{RUNE_ID0 + i}" charges="1" maglv="4000" mana="0" enabled="1"></rune>\n'
                      for i, n in enumerate(runes)) + "<!-- END MONSTER_KITS -->\n"
    anchor = "<!--\\\\ End Runes //-->"
    if anchor not in sx:
        raise SystemExit("spells.xml: no encuentro el final de las runas")
    sx = sx.replace(anchor, block_i + block_r + anchor)
    (SPELLS / "spells.xml").write_text(sx, encoding="latin-1")

    # --- monstruos ---
    for name, (path, raw, clean, _ref, _kit) in plans.items():
        add = "".join(f"\t{line}\n" for line in lines_by_monster[name])
        new, n = re.subn(r"([ \t]*)</attacks>", lambda m: add + m.group(0), clean, count=1)
        if n != 1:
            raise SystemExit(f"{name}: no encuentro </attacks>")
        if new != raw:
            path.write_text(new, encoding="latin-1")
    print("escrito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
