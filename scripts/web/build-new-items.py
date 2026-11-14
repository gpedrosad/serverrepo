#!/usr/bin/env python3
"""Arma web/site/src/data/new-items.json: la lista pública de ítems custom con sus stats.

Lee web/data/items_catalog.json (la misma lista curada de /items, con stats del OTB) y le suma
la ficha de cada ítem (grupo, tipo, efecto y dónde se consigue). Las imágenes salen de
web/assets/items/custom/<serverId>.png, que genera scripts/web/build-items-catalog.py.

  python3 scripts/web/build-new-items.py
  python3 scripts/web/build-new-items.py --check   # solo valida, no escribe

Al agregar un ítem al catálogo, sumarlo también a META o no aparece en la página.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "web/data/items_catalog.json"
OUT = ROOT / "web/site/src/data/new-items.json"
IMG_DIR = ROOT / "web/assets/items/custom"

GROUPS = [
    ("armas", "Armas"),
    ("escudos", "Escudos"),
    ("armaduras", "Armaduras"),
    ("cascos", "Cascos"),
    ("accesorios", "Accesorios"),
    ("crisol", "El Crisol"),
    ("sistemas", "Sistemas"),
]

# serverId -> (grupo, tipo, efecto, dónde se consigue)
META: dict[int, tuple[str, str, str, str]] = {
    1954: ("sistemas", "scroll", "7 días de premium en el personaje indicado.", "Tienda premium de la web."),
    2130: ("accesorios", "amulet", "El oro del botín va directo a tu cuenta bancaria.", "Extra de premium en la web."),
    2179: ("accesorios", "ring", "+20% de oro de monstruos mientras lo llevas equipado.", "Extra de premium en la web."),
    2345: ("sistemas", "scroll", "14 días de premium. Mejor valor que 2× semanal.", "Tienda premium de la web."),
    20100: ("crisol", "sword · 1H", "Espada muy rápida 39/22 (950 ms): 25% poison DoT.", "El Crisol, día 5 (Venomqueen)."),
    20105: ("armas", "sword · 1H", "42/23. Paraliza al jugador en cada golpe en PvP.", "Rara de Angry, Furious y Enraged Demon."),
    20110: ("crisol", "club · 2H", "Club rápido 46/14: trail de energía, 20% burst.", "El Crisol, día 6 (Stormcaller)."),
    20112: ("crisol", "sword · 1H", "Espada rápida 44/28: trail de fuego, 20% burn DoT.", "El Crisol, día 1 (Ashlord)."),
    20113: ("cascos", "head", "Armadura 9. Knights y paladins: +1 sword, club, axe y distance.", "Cofre de la guarida de la Isla del Hielo Eterno."),
    20114: ("armaduras", "body", "Armadura 1. Sorcerers y druids: +1 magic level.", "Cofre del TP Gauntlet; loot de Fury y Wrath."),
    20121: ("crisol", "club · 2H", "Club pesado 50/16 (1700 ms): 22% root 2,5 s en PvP.", "El Crisol, día 4 (Ironhide)."),
    20122: ("crisol", "sword · 1H", "Espada 46/28: 30% life leech (25% del daño).", "El Crisol, día 7 (Bloodreaver)."),
    20123: ("armas", "wand", "55–65 de daño, 13 de maná, ataca el doble de rápido. Imbue hasta +4 ML.", "Cofre de la guarida de la Isla del Hielo Eterno."),
    20126: ("armas", "wand", "Entrena magic level despacio en los trainers sin gastar maná.", "Sin forma de conseguirlo (solo GM)."),
    20130: ("armas", "axe · 1H", "43/22. 20% de emborrachar al jugador 6 s en PvP.", "Rara de Enraged Behemoth, Black Knight, Dwarf Guard y Orc Berserker."),
    20131: ("sistemas", "runa", "Recupera 60–80% de la exp perdida en tu última muerte.", "Objeto de sistema (una por muerte)."),
    20132: ("sistemas", "runa", "+12 horas de training ese día (una vez por personaje).", "Objeto de sistema."),
    20137: ("armas", "sword · 1H", "24/21. Acepta hasta 5 Big Ruby: cada una suma velocidad de ataque.", "Rara de Serpent Spawn (0,45%)."),
    20138: ("crisol", "sword · 1H", "Espada 42/34: 18% chill (slow) 4 s en PvP.", "El Crisol, día 2 (Frostwarden)."),
    20139: ("armas", "sword · 1H", "42/30. 10% de silenciar al jugador 2–3 s en PvP (solo hechizos hablados; 12 s de espera por objetivo).", "Loot de Fury (0,4%) y Wrath (0,55%)."),
    20154: ("crisol", "axe · 1H", "Hacha 43/24: 15% mana drain al golpear.", "El Crisol, día 3 (Bonepriest)."),
    20155: ("sistemas", "objeto", "Muñeco de entrenamiento para colocar en tu casa (1 por house, solo el dueño).", "Tienda premium de la web."),
    20156: ("armas", "spear · 1H", "36 de ataque, 80% de puntería, brilla y vuela con proyectil propio.", "Solo GM (/i 20156 1)."),
    20157: ("armas", "sword · 1H", "49/33. Espada 1H de gema esmeralda.", "Solo GM (/i 20157 1); quest pendiente."),
    20158: ("armas", "sword · 2H", "50/38. Espada sagrada de dos manos.", "Solo GM (/i 20158 1); quest pendiente."),
    20159: ("armas", "club · 2H", "50/30. Bastón mágico de dos manos.", "Solo GM (/i 20159 1); quest pendiente."),
    20160: ("armas", "crossbow · 2H", "+2 al ataque de los bolts.", "Solo GM (/i 20160 1); quest pendiente."),
    20161: ("armaduras", "body", "Armadura 14. −10% daño mágico (fuego, energía, veneno y life drain).", "Loot de Demon, Warlock, Orshabaal, Imperial Hero, Fallen Emperor y Ashen Lord."),
    20162: ("armaduras", "body", "Armadura 14. −10% daño físico.", "Loot de Behemoth, Demodras y Ashen Lord."),
    20163: ("armas", "axe · 1H", "49/31. Hacha 1H de jade y raíz.", "Root Colossus."),
    20164: ("armas", "club · 2H", "52/28. Mazo 2H de madera ancestral.", "Root Colossus."),
    20165: ("escudos", "shield", "Defensa 30. Borde dorado y campo violeta.", "Ice Monk (0,25%)."),
}


def stats(row: dict) -> dict:
    return {
        "attack": row.get("attack"),
        "defence": row.get("defence"),
        "armor": row.get("armor"),
        "weight": row.get("weight"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="solo valida, no escribe")
    args = ap.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    by_id = {int(row["serverId"]): row for row in catalog}

    missing = sorted(set(META) - set(by_id))
    if missing:
        print("en META pero no en el catálogo:", ", ".join(map(str, missing)), file=sys.stderr)
        return 1

    unknown = sorted(set(by_id) - set(META))
    if unknown:
        print("en el catálogo pero sin ficha en META (no se publican):", ", ".join(map(str, unknown)), file=sys.stderr)

    items = []
    for server_id, (group, kind, effect, source) in META.items():
        row = by_id[server_id]
        image = IMG_DIR / f"{server_id}.png"
        if not image.is_file():
            print(f"falta la imagen {image.relative_to(ROOT)}; corré build-items-catalog.py", file=sys.stderr)
            return 1
        item = {
            "id": server_id,
            "name": row["name"],
            "group": group,
            "type": kind,
            "effect": effect,
            "source": source,
            "image": f"/assets/items/custom/{server_id}.png",
            **stats(row),
        }
        items.append(item)

    order = {key: i for i, (key, _label) in enumerate(GROUPS)}
    items.sort(key=lambda it: (order[it["group"]], it["id"]))
    payload = {"groups": [{"key": key, "label": label} for key, label in GROUPS], "items": items}

    if args.check:
        print(f"ok: {len(items)} ítems en {OUT.relative_to(ROOT)}")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(items)} ítems en {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
