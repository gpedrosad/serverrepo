#!/usr/bin/env python3
"""Prueba de la ayuda a los que llegan (docs/gameplay/NEWBIE_PROTECTION.md) en un servidor de PRUEBA con bots
(make-test-bots.py: Bot Novato nivel 8 en la cuenta 111113, Bot Mage nivel 20 en la 111111, Bot GM en la 111112).

  1. Bot Novato ve el aviso de protección al entrar;
  2. ataque: cuenta los golpes de Bot Novato en 15 s contra un Elite Trainer Monk y contra un "Speed Dummy"
     (el mismo monk con trainer="0", hay que agregarlo en la COPIA de los datos, ver la doc): contra el dummy
     tiene que pegar ~1,6 veces más;
  3. Bot Novato muere (el GM le pone dragones al lado): al volver avisa, conserva mochila, exp y nivel;
  4. control: Bot Mage (nivel 20) muere y pierde la mochila y exp, sin aviso de protección.

  python3 scripts/ot/test-newbie-protection.py --port 7275

Antes de cada corrida volver a crear los bots (make-test-bots.py): las muertes quedan guardadas.

No apuntarlo al servidor donde se juega.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import struct
import sys
import time
from pathlib import Path

_spec = importlib.util.spec_from_file_location("gifts", Path(__file__).with_name("test-level-gifts.py"))
_g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_g)
Client, check, BACKPACK_CLIENT = _g.Client, _g.check, _g.BACKPACK_CLIENT


def texts(client, since=0):
    return [t for _c, t in client.messages(since)]


def stats(client):
    """Última exp y nivel del paquete 0xA0 (vida, vida máx, cap, exp U32, nivel U16)."""
    found = None
    for m in re.finditer(rb"\xA0(..)(..)(..)(....)(..)", client.buf, re.S):
        hp, hpmax = struct.unpack("<H", m.group(1))[0], struct.unpack("<H", m.group(2))[0]
        if 0 < hpmax < 20000 and hp <= hpmax:
            found = (struct.unpack("<I", m.group(4))[0], struct.unpack("<H", m.group(5))[0])
    return found


def has_backpack(client):
    return re.search(rb"\x78\x03" + struct.pack("<H", BACKPACK_CLIENT), client.buf) is not None


def summon(gm, client, name):
    start = client.mark()
    gm.say(f"/m {name}")
    client.read(1.0)
    raw = name.title().encode("latin-1")
    ids = [struct.unpack("<I", m.group(1))[0]
           for m in re.finditer(rb"\x61\x00....(....)" + struct.pack("<H", len(raw)) + re.escape(raw),
                                client.buf[start:], re.S)]
    return ids[-1] if ids else None


def hits(client, since, own_pos):
    """Efectos (sangre, puff, bloqueo) que no caen en la casilla del bot: sus golpes al blanco."""
    n = 0
    for m in re.finditer(rb"\x83(.....)([\x00-\x03])", client.buf[since:], re.S):
        if m.group(1) != own_pos:
            n += 1
    return n


def position_seen_by(viewer, creature_id):
    """Casilla de un personaje según lo que ve otro: el último 0x6A (aparece) con su id."""
    cid = re.escape(struct.pack("<I", creature_id))
    found = None
    for m in re.finditer(rb"\x6A(.....)(?:\x61\x00....|\x62\x00)" + cid, viewer.buf, re.S):
        found = m.group(1)
    return found


def die(port, gm, account, name, monster, wait):
    bot = Client(port, account, name)
    gm.say(f"/c {name}")
    gm.read(1.0)
    bot.read(0.5)
    before = (stats(bot), has_backpack(bot))
    for _ in range(3):
        gm.say(f"/m {monster}")
        gm.read(0.4)
    bot.read(wait)                               # los dragones lo matan en pocos segundos
    gm.say("/killmonsters")
    gm.read(1.0)
    try:
        bot.sock.close()
    except OSError:
        pass
    time.sleep(2)
    again = Client(port, account, name)
    again.read(1.0)
    return before, (stats(again), has_backpack(again)), texts(again)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=7275)
    ap.add_argument("--seconds", type=float, default=15.0)
    ap.add_argument("--killer", default="dragon lord")
    a = ap.parse_args()
    fails = 0

    print("1. Aviso al entrar")
    novato = Client(a.port, 111113, "Bot Novato")
    novato.read(0.5)
    fails += not check(any(t.startswith("Newbie protection:") for t in texts(novato)), "aviso de protección")

    print("2. Ataque más rápido contra monstruos, no contra trainers")
    gm = Client(a.port, 111112, "Bot GM")
    gm.say("/c Bot Novato")
    gm.read(1.5)
    novato.read(0.5)
    me = position_seen_by(gm, novato.id)
    print(f"  Bot Novato en {struct.unpack('<HHB', me) if me else '?'}")
    if not me:
        fails += not check(False, "no se sabe dónde quedó Bot Novato")
    counts = {}
    for target in ("Elite Trainer Monk", "Speed Dummy"):
        cid = summon(gm, novato, target)
        if not cid:
            fails += not check(False, f"no apareció {target} (¿falta en la copia?)")
            continue
        novato.attack(cid)
        novato.read(2.0)                         # que llegue al lado
        start = novato.mark()
        novato.read(a.seconds)
        counts[target] = hits(novato, start, me)
        novato.attack(0)
        gm.say("/killmonsters")
        gm.read(1.0)
        novato.read(0.5)
    print(f"  golpes en {a.seconds:.0f} s: {counts}")
    if len(counts) == 2 and counts["Elite Trainer Monk"]:
        ratio = counts["Speed Dummy"] / counts["Elite Trainer Monk"]
        fails += not check(1.35 <= ratio <= 1.95, f"monstruo / trainer = {ratio:.2f} (esperado ~1,67)")
    novato.sock.close()

    print("3. Bot Novato muere protegido")
    before, after, msgs = die(a.port, gm, 111113, "Bot Novato", a.killer, 40)
    print(f"  antes {before}  después {after}")
    fails += not check(any("newbie protection kept" in t for t in msgs), "aviso de muerte protegida")
    fails += not check(after[1], "conserva la mochila")
    fails += not check(before[0] and after[0] and after[0] == before[0], "misma exp y nivel")

    print("4. Control: Bot Mage (nivel 20) muere sin protección")
    before, after, msgs = die(a.port, gm, 111111, "Bot Mage", a.killer, 40)
    print(f"  antes {before}  después {after}")
    fails += not check(not any("newbie protection" in t.lower() for t in msgs), "sin avisos de protección")
    fails += not check(not after[1], "perdió la mochila")
    fails += not check(before[0] and after[0] and after[0][0] < before[0][0], "perdió exp")

    print("RESULTADO:", "OK" if not fails else f"{fails} falla(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
