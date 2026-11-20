#!/usr/bin/env python3
"""Catálogo de las armas propias del servidor (ítems 20000+ con bloque de arma en el OTB, más wands y crystal arrow).

  python3.11 scripts/items/weapon-catalog.py            # resumen
  python3.11 scripts/items/weapon-catalog.py --write    # docs/gameplay/ARMAS.md + docs/gameplay/img/armas.png

Lee del OTB (items-zagan-test.otb) el tipo, ataque y defensa; del cliente de RME el sprite; de los XML de
monstruos (sin variantes rage) dónde cae y con qué chance. Lo que hace cada arma y su doc salen de NOTES
(abajo): al crear un arma nueva, agregar su fila ahí y volver a correrlo. Necesita Pillow (python3.11).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/client-rme"))
import add_custom_items as A  # noqa: E402
import build_zagan_test_assets as B  # noqa: E402
from add_black_dragon_look import decode_sprite, read_spr  # noqa: E402

OTB = ROOT / "server/YurOTS/ots/data/items/items-zagan-test.otb"
THINGS = ROOT / "devtools/rme/rme-client-760"
MON = ROOT / "server/YurOTS/ots/data/monster"
OUT = ROOT / "docs/gameplay/ARMAS.md"
SHEET = ROOT / "docs/gameplay/img/armas.png"
TYPES = {1: "espada", 2: "maza", 3: "hacha", 5: "distancia", 6: "wand"}
RAGE = ("angry ", "furious ", "enraged ")

# server id -> (grupo, qué hace, de dónde sale además del loot, doc)
NOTES = {
    20250: ("Melee Relics", "1200 ms. Cada 3er golpe al mismo blanco suma 22–34 de energía (mitad en PvP); grieta violeta", "", "MELEE_RELICS.md"),
    20251: ("Melee Relics", "1333 ms. Devuelve 12% del daño a vida como maná (máx. 10 por golpe, 5 en PvP); espirales turquesa", "", "MELEE_RELICS.md"),
    20252: ("Melee Relics", "2 manos, 1600 ms. 25%: suma 12 + armadura/2 (máx. 42) de daño físico; anillo ámbar", "", "MELEE_RELICS.md"),
    20211: ("Paladin Stars", "Reutilizable, 85% hit, 900 ms; estela de viento", "", "PALADIN_STARS.md"),
    20212: ("Paladin Stars", "Reutilizable, 85% hit; veneno", "", "PALADIN_STARS.md"),
    20213: ("Paladin Stars", "Reutilizable, 85% hit; descarga de energía", "", "PALADIN_STARS.md"),
    20112: ("El Crisol", "1100 ms. Estela de fuego; 20% quemadura", "", "CRUCIBLE.md"),
    20138: ("El Crisol", "1200 ms. 18% frío (lentitud 4 s en PvP)", "", "CRUCIBLE.md"),
    20154: ("El Crisol", "15% drena maná", "", "CRUCIBLE.md"),
    20121: ("El Crisol", "1700 ms. 22% raíz 2,5 s en PvP", "", "CRUCIBLE.md"),
    20100: ("El Crisol", "950 ms. 25% veneno", "", "CRUCIBLE.md"),
    20110: ("El Crisol", "1000 ms. Estela de energía; 20% estallido", "", "CRUCIBLE.md"),
    20122: ("El Crisol", "1200 ms. 30%: roba vida (25% del daño)", "", "CRUCIBLE.md"),
    20105: ("Armas PvP", "Paraliza en PvP al golpear", "", "../items-and-map/ZAGAN_TEST_ITEMS.md"),
    20139: ("Armas PvP", "10%: silencio PvP 2–3 s (solo hechizos hablados); 12 s por blanco", "", "../items-and-map/ZAGAN_TEST_ITEMS.md"),
    20130: ("Armas PvP", "20%: emborracha 6 s en PvP", "", "../items-and-map/ZAGAN_TEST_ITEMS.md"),
    20137: ("Armas PvP", "Ataque más rápido; proyectil de fuego al pegar", "", "../items-and-map/ZAGAN_TEST_ITEMS.md"),
    20157: ("Armas de 8.x", "Sprite de 8.x", "Cámara de las Armas (Pozos del Infierno, elegir una)", "../items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md"),
    20158: ("Armas de 8.x", "Sprite de 8.x", "Cámara de las Armas (Pozos del Infierno, elegir una)", "../items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md"),
    20159: ("Armas de 8.x", "Sprite de 8.x, 2 manos", "Cámara de las Armas (Pozos del Infierno, elegir una)", "../items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md"),
    20160: ("Armas de 8.x", "Ballesta; el ataque lo da el bolt", "Cámara de las Armas (Pozos del Infierno, elegir una)", "../items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md"),
    20156: ("Otras", "Lanza que vuelve; proyectil propio", "Hoy no se consigue (solo `/i`)", "ENCHANTED_SPEAR.md"),
    20163: ("Otras", "Sin efecto", "", "ROOT_COLOSSUS.md"),
    20164: ("Otras", "2 manos, sin efecto", "", "ROOT_COLOSSUS.md"),
    20193: ("Otras", "Fire sword de fuego negro, sin efecto; luz violeta", "", "../items-and-map/ZAGAN_TEST_ITEMS.md"),
    20111: ("Sin fuente", "Sin efecto", "Hoy no se consigue (solo `/i`)", "../items-and-map/ZAGAN_TEST_ITEMS.md"),
    20115: ("Sin fuente", "Sin efecto", "Hoy no se consigue (solo `/i`)", "../items-and-map/ZAGAN_TEST_ITEMS.md"),
    20119: ("Sin fuente", "Sin efecto", "Hoy no se consigue (solo `/i`)", "../items-and-map/ZAGAN_TEST_ITEMS.md"),
    20120: ("Sin fuente", "Sin efecto", "Hoy no se consigue (solo `/i`)", "../items-and-map/ZAGAN_TEST_ITEMS.md"),
}
# Armas sin bloque de arma en el OTB o que no son 20000+
EXTRA = [
    (20123, "crimson wand", "wand", "55–65", "Wands", "Sorcerer/Druid nivel 33+: 13 maná, rango 5, 667 ms; imbue de ML hasta +4", "Quest Isla del Hielo: guarida", "WANDS.md"),
    (20126, "train wand", "wand", "1", "Wands", "Solo contra trainers: 0 maná, entrena magic level", "Hoy no se consigue (solo `/i`)", "WANDS.md"),
    (2352, "crystal arrow", "distancia", "35", "Otras", "Se tira como una spear, 85% hit, no se gasta; Blue Gem: hasta +25% de velocidad", "", "CRYSTAL_ARROW.md"),
]
GROUPS = ["Melee Relics", "El Crisol", "Paladin Stars", "Armas PvP", "Wands", "Armas de 8.x", "Otras", "Sin fuente"]


def loot_sources() -> dict[int, list[str]]:
    """item -> ["Monstruo chance%", ...]. Las variantes rage solo si su monstruo base no lo suelta."""
    out: dict[int, list[str]] = {}
    base_drops: dict[str, set] = {}
    files = sorted(p for p in MON.glob("*.xml") if p.name != "monsters.xml")
    files.sort(key=lambda p: p.name.startswith(RAGE))           # primero los base
    for p in files:
        rage = p.name.startswith(RAGE)
        base = p.name.split(" ", 1)[1] if rage else p.name
        s = p.read_text(encoding="latin-1")
        name = re.search(r'<monster name="([^"]+)"', s)
        for m in re.finditer(r'<item id="(\d+)"[^>]*?chance="(\d+)"', s):
            item = int(m.group(1))
            if rage and item in base_drops.get(base, set()):
                continue
            if not rage:
                base_drops.setdefault(base, set()).add(item)
            pct = int(m.group(2)) / 1000
            out.setdefault(int(m.group(1)), []).append(f"{name.group(1) if name else p.stem} {pct:g}%")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    _d, root = A.load_otb(OTB)
    rows, client = [], {}
    for n in root.children:
        sid, cid, name = A.node_ids(n)
        if sid:
            client[sid] = cid
        if not sid or sid < 20000:
            continue
        _flags, blocks = B.parse_item_props(n.props)
        w = B.get_block_payload(blocks, 0x26)
        if not w or w[0] == 4:          # 4 = escudo
            continue
        group, effect, source, doc = NOTES.get(sid, ("Otras", "", "", ""))
        rows.append(dict(sid=sid, name=name, kind=TYPES.get(w[0], str(w[0])),
                         atk=str(w[3]) + (f" / {w[4]}" if w[4] else ""), group=group, effect=effect,
                         source=source, doc=doc))
    for sid, name, kind, atk, group, effect, source, doc in EXTRA:
        rows.append(dict(sid=sid, name=name, kind=kind, atk=atk, group=group, effect=effect, source=source, doc=doc))
    loot = loot_sources()
    for r in rows:
        drops = loot.get(r["sid"], [])
        r["where"] = "; ".join(x for x in [", ".join(drops), r["source"]] if x) or "—"
    rows.sort(key=lambda r: (GROUPS.index(r["group"]) if r["group"] in GROUPS else 99, r["sid"]))
    print(f"{len(rows)} armas propias")
    if not a.write:
        return 0

    # hoja de imágenes: 32x32 x3 con nombre e id
    things_spr = (THINGS / "Tibia.spr").read_bytes()
    _c, offsets = read_spr(things_spr)
    entries, _t = B.DatReader((THINGS / "Tibia.dat").read_bytes()).read_item_entries()
    cols, cw, ch = 8, 120, 132
    sheet = B.Image.new("RGBA", (cols * cw, ((len(rows) + cols - 1) // cols) * ch), (34, 40, 46, 255))
    draw = B.ImageDraw.Draw(sheet) if hasattr(B, "ImageDraw") else __import__("PIL.ImageDraw").ImageDraw.Draw(sheet)
    for i, r in enumerate(rows):
        cid = client.get(r["sid"])
        x, y = (i % cols) * cw, (i // cols) * ch
        if cid:
            px = decode_sprite(things_spr, offsets, entries[cid - 100].sprite_ids[0])
            img = B.Image.new("RGBA", (32, 32))
            img.putdata(px)
            sheet.alpha_composite(img.resize((96, 96), B.Image.NEAREST), (x + 12, y + 4))
        draw.text((x + 4, y + 102), r["name"][:20], fill=(235, 235, 235, 255))
        draw.text((x + 4, y + 116), str(r["sid"]), fill=(150, 170, 190, 255))
    sheet.save(SHEET)

    link = lambda r: f"[{Path(r['doc']).stem}]({r['doc']})" if r["doc"] else "—"
    parts = [f"""# Armas propias

> Generado con `python3.11 scripts/items/weapon-catalog.py --write`: **no editar a mano**. Al crear un arma,
> agregar su fila en `NOTES` del script (grupo, efecto, fuente y doc) y volver a correrlo. El tipo, ataque y
> defensa salen del OTB (`items-zagan-test.otb`); el loot, de los XML de monstruos (sin variantes rage, que
> suelen tener la misma chance o más).

{len(rows)} armas propias (sin contar escudos ni las armas comunes de 7.6). GM: `/i ID 1` o `/i nombre`.
Para crear una: [IMPORTAR_ITEM_DESDE_IMAGEN.md](../items-and-map/IMPORTAR_ITEM_DESDE_IMAGEN.md),
[IMPORTAR_ITEM_DE_OTRA_VERSION.md](../items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md); gameplay en C++: `AGENTS.md` §8.

![Todas las armas propias, con su server id](img/armas.png)
"""]
    for g in GROUPS:
        sub = [r for r in rows if r["group"] == g]
        if not sub:
            continue
        parts.append(f"\n## {g}\n\n| Arma | ID | Tipo | Atq / def | Qué hace | Dónde sale | Doc |\n|---|---:|---|---|---|---|---|\n")
        parts.append("\n".join(f"| **{r['name']}** | `{r['sid']}` | {r['kind']} | {r['atk']} | {r['effect'] or '—'} | "
                               f"{r['where']} | {link(r)} |" for r in sub) + "\n")
    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"escrito {OUT.relative_to(ROOT)} y {SHEET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
