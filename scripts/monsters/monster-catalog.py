#!/usr/bin/env python3
"""Catálogo de todos los monstruos: originales de YurOTS, traídos de 8.60, creados acá y variantes rage.

  python3 scripts/monsters/monster-catalog.py            # imprime el resumen
  python3 scripts/monsters/monster-catalog.py --write    # regenera docs/gameplay/MONSTRUOS.md

Lee monsters.xml, cada XML de monstruo (look, vida, exp, cadáver), test-spawn.xml (cuántos hay en el mapa y
en qué zona, por los bloques BEGIN/END de cada generador), los presets de sprites y git (fecha en que se
agregó cada XML y la lista original de YurOTS, commit 2491c60). Solo python3, sin dependencias.
Volver a correrlo después de crear, borrar o spawnear un monstruo.
"""
from __future__ import annotations

import argparse
import collections
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OTS = ROOT / "server/YurOTS/ots/data"
MON = OTS / "monster"
SPAWNS = OTS / "world/test-spawn.xml"
PRESETS = ROOT / "scripts/client-rme/presets"
DOCS = ROOT / "docs/gameplay"
OUT = DOCS / "MONSTRUOS.md"
ORIGINAL_COMMIT = "2491c60"            # primer commit del repo: el monsters.xml de YurOTS tal cual
RAGE = ("Angry ", "Furious ", "Enraged ")
# Looks de criaturas traídas de Tibia 8.60 (docs/gameplay/IMPORTAR_CRIATURA_DE_OTRA_VERSION.md)
LOOKS_860 = {20, 46, 47, 72, 77, 93, 96, 97, 98, *range(161, 185), *range(197, 201), *range(245, 252)}
# Docs que no son de un monstruo aunque lo nombren
RENAMED = {"Dworc Voodoomaster": "Dworf Voodoomaster"}   # nombre de hoy -> nombre en el commit original
SKIP_DOCS = {"INDEX.md", "THINKPAD_TEST_SERVER.md", "MONSTRUOS.md", "SPRITE_BASES.md", "RAGE_MONSTERS.md", "DAILY_TASK.md", "GEMS.md",
             "RESPAWN_SYSTEM.md", "MONSTER_KITS.md", "SPRITE_RECOLOR_GUIDE.md", "GM_COMANDOS.md"}


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, errors="replace").stdout


def registered() -> dict[str, str]:
    text = (MON / "monsters.xml").read_text(encoding="latin-1")
    return dict(re.findall(r'<monster name="([^"]+)" file="([^"]+)"', text))


def monster_data(file: str) -> dict:
    s = (MON / file).read_text(encoding="latin-1")
    look = re.search(r'<look\b[^>]*\btype="(\d+)"', s)
    corpse = re.search(r'<look\b[^>]*\bcorpse="(\d+)"', s)
    hp = re.search(r'<health\b[^>]*\bmax="(\d+)"', s)
    exp = re.search(r'\bexperience="(\d+)"', s)
    return dict(look=int(look.group(1)) if look else 0, corpse=int(corpse.group(1)) if corpse else 0,
                hp=int(hp.group(1)) if hp else 0, exp=int(exp.group(1)) if exp else 0)


def spawn_info() -> dict[str, collections.Counter]:
    """nombre en minúscula -> Counter(zona -> cantidad). Zona = bloque BEGIN X_SPAWNS que lo contiene."""
    text = SPAWNS.read_text(encoding="latin-1")
    marks = [(m.start(), m.group(1)) for m in re.finditer(r"<!-- (?:BEGIN|END) ([A-Z_]+?)(?:_SPAWNS)?\b", text)]
    begins = {m.start(): m.group(1) for m in re.finditer(r"<!-- BEGIN ([A-Z_]+?)(?:_SPAWNS)? ", text)}
    out: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for m in re.finditer(r'<monster name="([^"]+)"', text):
        zone = "mapa base"
        for pos, tag in marks:
            if pos > m.start():
                break
            zone = tag.replace("_", " ").title() if pos in begins else "mapa base"
        out[m.group(1).lower()][zone] += 1
    return out


def preset_looks() -> dict[int, str]:
    looks = {}
    for p in PRESETS.glob("*.py"):
        t = re.search(r"target\s*=\s*(\d+)", p.read_text())
        if t:
            looks[int(t.group(1))] = p.name
    return looks


def added_dates() -> dict[str, str]:
    """archivo XML -> fecha (AAAA-MM-DD) del commit que lo agregó."""
    log = git("log", "--diff-filter=A", "--format=@%ad", "--date=short", "--name-only", "--",
              "server/YurOTS/ots/data/monster/")
    dates, current = {}, ""
    for line in log.splitlines():
        if line.startswith("@"):
            current = line[1:]
        elif line.strip():
            dates[Path(line.strip()).name] = current      # el log va del más nuevo al más viejo
    return dates


def doc_for(name: str, docs: dict[str, str]) -> str:
    """Doc del monstruo: el que se llama como él, si no el primero que lo nombra (gameplay primero)."""
    if name.startswith("Crucible "):
        return "CRUCIBLE.md"
    key = name.upper().replace(" ", "_").replace("THE_", "")
    for fname in docs:
        if Path(fname).name.startswith(key):
            return fname
    pat = re.compile(r"\b" + re.escape(name) + r"\b")
    for fname, text in docs.items():
        if pat.search(text):
            return fname
    return ""


def build() -> tuple[str, str]:
    reg = registered()
    original = set(re.findall(r'<monster name="([^"]+)"', git("show", f"{ORIGINAL_COMMIT}:server/YurOTS/ots/data/monster/monsters.xml")))
    spawns, presets, dates = spawn_info(), preset_looks(), added_dates()
    paths = sorted(DOCS.glob("*.md")) + sorted(p for p in (ROOT / "docs").rglob("*.md") if p.parent != DOCS)
    docs = {("" if p.parent == DOCS else "../" + str(p.parent.relative_to(ROOT / "docs")) + "/") + p.name:
            p.read_text(encoding="utf-8", errors="replace") for p in paths if p.name not in SKIP_DOCS}
    bases = [n for n in reg if not n.startswith(RAGE)]
    rage = [n for n in reg if n.startswith(RAGE)]
    rage_bases = {n.split(" ", 1)[1] for n in rage}
    corpse_users = collections.Counter(monster_data(reg[n])["corpse"] for n in bases)
    groups = {"creado": [], "860": [], "original": []}
    rows = {}
    for name in sorted(bases, key=str.lower):
        d = monster_data(reg[name])
        sp = spawns.get(name.lower(), collections.Counter())
        sp_rage = sum(sum(spawns.get((p + name).lower(), {}).values()) for p in RAGE)
        if name in original or RENAMED.get(name) in original:
            kind = "original"
        elif d["look"] in LOOKS_860 and d["look"] not in presets:
            kind = "860"
        else:
            kind = "creado"
        sprite = (f"propio, look {d['look']} (`{presets[d['look']]}`)" if d["look"] in presets
                  else f"look {d['look']}" + (" (8.60)" if d["look"] in LOOKS_860 else ""))
        corpse = d["corpse"]
        corpse_txt = (f"`{corpse}` propio" if corpse >= 20000 else f"`{corpse}` de 7.6") + \
            (" (compartido)" if corpse_users[corpse] > 1 and corpse >= 20000 else "")
        zones = ", ".join(f"{z} {c}" for z, c in sp.most_common()) or "—"
        total = sum(sp.values())
        doc = ("" if kind == "original" else
               "IMPORTAR_CRIATURA_DE_OTRA_VERSION.md" if kind == "860" else doc_for(name, docs))
        rows[name] = dict(kind=kind, d=d, sprite=sprite, corpse=corpse_txt, total=total, zones=zones,
                          rage="sí" if name in rage_bases else "no", sp_rage=sp_rage,
                          date=dates.get(Path(reg[name]).name, ""), doc=doc)
        groups[kind].append(name)

    def table(names, cols):
        head = "| " + " | ".join(c for c, _ in cols) + " |\n|" + "|".join("---" for _ in cols) + "|\n"
        return head + "\n".join("| " + " | ".join(f(n, rows[n]) for _c, f in cols) + " |" for n in names) + "\n"

    link = lambda r: f"[{Path(r['doc']).stem}]({r['doc']})" if r["doc"] else "—"
    full = [("Monstruo", lambda n, r: f"**{n}**"), ("Agregado", lambda n, r: r["date"]),
            ("Vida", lambda n, r: str(r["d"]["hp"])), ("Exp", lambda n, r: str(r["d"]["exp"])),
            ("Sprite", lambda n, r: r["sprite"]), ("Cadáver", lambda n, r: r["corpse"]),
            ("En el mapa", lambda n, r: f"{r['total']}: {r['zones']}" if r["total"] else "sin spawn"),
            ("Rage", lambda n, r: r["rage"]), ("Doc", lambda n, r: link(r))]
    short = [("Monstruo", lambda n, r: n), ("Vida", lambda n, r: str(r["d"]["hp"])),
             ("Exp", lambda n, r: str(r["d"]["exp"])), ("Look", lambda n, r: str(r["d"]["look"])),
             ("En el mapa", lambda n, r: str(r["total"]) if r["total"] else "sin spawn"),
             ("Rage", lambda n, r: r["rage"])]
    no_spawn = [n for n in bases if rows[n]["total"] == 0 and rows[n]["kind"] != "original"]
    summary = (f"{len(bases)} monstruos (sin contar variantes rage): {len(groups['original'])} originales de YurOTS, "
               f"{len(groups['860'])} traídos de 8.60 y {len(groups['creado'])} creados acá; además "
               f"{len(rage)} variantes rage de {len(rage_bases)} familias.")
    md = f"""# Monstruos: catálogo completo

> Generado con `python3 scripts/monsters/monster-catalog.py --write`: **no editar a mano**, volver a correrlo
> después de crear, borrar o spawnear un monstruo. Lee `monsters.xml`, los XML, `test-spawn.xml`, los presets
> de sprites y la historia de git.

{summary}

- **Originales**: los {len(groups['original'])} del `monsters.xml` del primer commit (`{ORIGINAL_COMMIT}`, YurOTS 7.6).
- **Traídos de 8.60**: sprite original de Tibia 8.60 (looks 20, 46–47, 72, 77, 93, 96–98, 161–184, 197–200,
  245–251). Ver [IMPORTAR_CRIATURA_DE_OTRA_VERSION.md](IMPORTAR_CRIATURA_DE_OTRA_VERSION.md).
- **Creados acá**: monstruos nuevos de este servidor. Los que tienen "sprite propio" se hicieron
  recoloreando una criatura de 7.6 con un preset ([SPRITE_RECOLOR_GUIDE.md](SPRITE_RECOLOR_GUIDE.md)); los
  demás reutilizan un look existente (outfit coloreado o el de su original).
- **Variantes rage** (Angry / Furious / Enraged): copias más fuertes que aparecen al matar al original
  ([RAGE_MONSTERS.md](RAGE_MONSTERS.md)). No se listan una por una.
- **Cadáver**: `propio` = ítem nuestro (20000+, con los colores del monstruo); `de 7.6` = el de una criatura
  del cliente original. Cómo se hacen: [Cadáveres](#cadáveres).
- **En el mapa**: cuántos hay en `test-spawn.xml` y en qué zona (bloque del generador que los escribe;
  `mapa base` = fuera de esos bloques). No cuenta las variantes rage puestas a mano.
- Para crear uno: [CUSTOM_MONSTER_WORKFLOW.md](CUSTOM_MONSTER_WORKFLOW.md).

## Creados acá ({len(groups['creado'])})

{table(groups['creado'], full)}
## Traídos de 8.60 ({len(groups['860'])})

{table(groups['860'], full)}
## Sin spawn

Monstruos agregados que hoy no aparecen en el mapa (jefes de evento, invocaciones, trainers o pendientes):
{", ".join(sorted(no_spawn, key=str.lower)) or "ninguno"}.

## Cadáveres

Cada monstruo nuevo tiene su cadáver con sus colores (nov 2026), salvo los que ya coinciden con uno de 7.6.

- **Monstruos con preset** (sprite recoloreado): el cadáver del monstruo base pasa por la misma receta del
  preset (`recolor`, o `parts` + `palettes`). Los Metal cambian además la sangre por el color de su neón.
- **Criaturas de 8.60** sin cadáver propio: un cadáver de 7.6 de forma parecida (cyclops para los gigantes,
  stone golem para el Ice Golem, giant spider para la Crystal Spider, rotworm para el Bog Raider, dragon
  para el Wyvern, dog para el Husky, ghoul para los chakoyas) con la gama de colores del look: la luz de
  cada píxel del cadáver elige un color del sprite ordenado por luz; la sangre roja queda igual.
- **Sin cadáver nuevo** porque ya combina: Dragon Hatchling (dragon), Dragon Lord Hatchling (dragon lord),
  Mutated Human/Rat/Bat/Tiger (ghoul, rat, bat, tiger: se probó y salían iguales). El Frost Dragon Hatchling
  usa el del Frost Dragon (`20171`) y el Dark Monk el humano (`3128`; antes tenía el del Demon).
- Las variantes rage usan el mismo cadáver que su original.
- Como todos los cadáveres custom, al pudrirse pasan a la etapa siguiente del cadáver base (verde, rojo, etc.).

Script: `python3.11 scripts/client-rme/creature_corpses.py --preview /tmp/cadaveres.png` escribe los PNG
(`devtools/zagan-test/custom-sprites/`); `--entries` imprime las líneas para `NEW_ITEMS` de
`add_custom_items.py`, que los instala en el `.dat`/`.spr` y en `items-zagan-test.otb`. Ids: server
`20225`–`20249`, client ids sacrificados (runas sin uso y adornos sueltos, de `--candidates`).

**Ojo con los client ids:** `--candidates` revisa mapa, loot, NPC y scripts, pero **no los personajes**. Antes
de sacrificar uno, buscar su server id en `players/*.xml` y `houseitems.xml` de la ThinkPad (solo lectura).
Pasó el 19 nov 2026: el cadáver de la Metal Hydra se puso en el client 3236 y la "music piece" (2349) que
tiene el GM pasó a verse como el cadáver; se movió al 3216 y el 3236 volvió a ser el original.

![Cadáveres: arriba el base, abajo el nuevo](img/cadaveres-nuevos.png)

## Originales de YurOTS ({len(groups['original'])})

{table(groups['original'], short)}"""
    return md, summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    md, summary = build()
    if a.write:
        OUT.write_text(md, encoding="utf-8")
        print(f"escrito {OUT.relative_to(ROOT)}")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
