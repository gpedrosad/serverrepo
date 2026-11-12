#!/usr/bin/env python3
"""Crea las cuentas y personajes de prueba que usa exercise-server.py, en una COPIA de los datos del servidor.

  python3 scripts/ot/make-test-bots.py ~/build/asan-run/ots/data 150 86 6

Deja la cuenta 111111 (Bot Sorc, Bot Druid, Bot Pally, Bot Knight, Bot Mage, Bot Tank) y la 111112 (Bot GM,
access 3), todos parados en X Y Z, con runas, comida y equipo. La contraseña es de prueba ("asantest", se puede
cambiar con --password): estas cuentas no tienen que existir en el servidor donde se juega, por eso el script
se niega a escribir dentro de un repo git (los datos reales viven en el repo). Ver docs/systems/SANITIZER_TESTS.md.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

RUNES = [2268, 2311, 2273, 2304, 2313, 2305, 2293, 2261, 2262, 2265, 2266, 2277, 2278, 2279, 2285, 2286, 2301, 2303]
# nombre, vocación, nivel, vida, maná, nivel mágico, runa en el slot de munición
CHARS = [("Bot Sorc", 1, 60, 500, 2500, 70, 2268), ("Bot Druid", 2, 60, 500, 2500, 70, 2311),
         ("Bot Pally", 3, 60, 800, 1200, 25, 2313), ("Bot Knight", 4, 60, 1200, 600, 9, 2304),
         ("Bot Mage", 1, 20, 185, 500, 30, 2273), ("Bot Tank", 4, 120, 2500, 900, 10, 2305)]
ACCOUNT, GM_ACCOUNT = 111111, 111112


def player(name, account, voc, access, level, hp, mana, mlvl, ammo, pos, spells):
    x, y, z = pos
    bp = ("".join(f'<item id="{r}" count="50"/>' for r in RUNES)
          + '<item id="2152" count="50"/><item id="2674" count="10"/><item id="2120"/><item id="2554"/>'
            '<item id="1988"><inside><item id="2400"/><item id="2544" count="100"/></inside></item>')
    skills = "".join(f'<skill skillid="{i}" level="{60 if voc in (3, 4) else 20}" tries="0"/>' for i in range(7))
    return (f'<?xml version="1.0"?>\n<player name="{name}" account="{account}" sex="1" lookdir="2" '
            f'exp="{50 * level ** 3}" voc="{voc}" level="{level}" access="{access}" cap="5000" maglevel="{mlvl}" '
            f'soul="100" lastlogin="0" premticks="0" promoted="0" banned="0">'
            f'<spawn x="{x}" y="{y}" z="{z}"/><temple x="{x}" y="{y}" z="{z}"/>'
            f'<skull type="0" kills="0" ticks="0" absolve="0"/>'
            f'<health now="{hp}" max="{hp}" food="600"/><mana now="{mana}" max="{mana}" spent="0"/>'
            f'<look type="{128 + voc}" head="20" body="30" legs="40" feet="50"/><skills>{skills}</skills>{spells}<deaths/>'
            f'<inventory><slot slotid="1"><item id="2457"/></slot>'
            f'<slot slotid="3"><item id="1988"><inside>{bp}</inside></item></slot>'
            f'<slot slotid="4"><item id="2463"/></slot><slot slotid="5"><item id="2383"/></slot>'
            f'<slot slotid="6"><item id="2516"/></slot><slot slotid="7"><item id="2647"/></slot>'
            f'<slot slotid="8"><item id="2643"/></slot>'
            f'<slot slotid="10"><item id="{ammo}" count="100"/></slot></inventory><depots/><storage/></player>\n')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("data", type=Path, help="carpeta data/ de la COPIA (tiene players/ y accounts/)")
    ap.add_argument("x", type=int)
    ap.add_argument("y", type=int)
    ap.add_argument("z", type=int)
    ap.add_argument("--password", default="asantest")
    args = ap.parse_args()

    data = args.data.resolve()
    if not (data / "players").is_dir() or not (data / "accounts").is_dir():
        ap.error(f"{data} no tiene players/ y accounts/")
    if any((parent / ".git").exists() for parent in (data, *data.parents)):
        ap.error(f"{data} está dentro de un repo git: ahí viven los datos reales. Usar una copia fuera del repo.")

    # La lista de hechizos aprendidos se copia de un personaje que ya exista en la copia.
    spells = "<spells/>"
    for sample in sorted((data / "players").glob("*.xml")):
        found = re.search(r"<spells>.*?</spells>", sample.read_text(encoding="latin-1"), re.S)
        if found:
            spells = found.group(0)
            break

    pos = (args.x, args.y, args.z)
    for name, voc, level, hp, mana, mlvl, ammo in CHARS:
        (data / "players" / f"{name.lower()}.xml").write_text(
            player(name, ACCOUNT, voc, 0, level, hp, mana, mlvl, ammo, pos, spells), encoding="latin-1")
    (data / "players" / "bot gm.xml").write_text(
        player("Bot GM", GM_ACCOUNT, 0, 3, 100, 5000, 5000, 50, 2268, pos, spells), encoding="latin-1")

    account = ('<?xml version="1.0"?>\n<account pass="{}" type="0" premDays="0">\n\t<characters>\n{}'
               '\t</characters>\n</account>\n')
    (data / "accounts" / f"{ACCOUNT}.xml").write_text(
        account.format(args.password, "".join(f'\t\t<character name="{c[0]}" />\n' for c in CHARS)))
    (data / "accounts" / f"{GM_ACCOUNT}.xml").write_text(
        account.format(args.password, '\t\t<character name="Bot GM" />\n'))
    print(f"ok: {len(CHARS) + 1} personajes en {data} (cuentas {ACCOUNT} y {GM_ACCOUNT})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
