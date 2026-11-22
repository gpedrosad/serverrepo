#!/usr/bin/env python3
"""Prueba del Orc Berserker Pot Thrower (docs/gameplay/MONSTRUOS.md) en un servidor de PRUEBA con bots
(make-test-bots.py): el hechizo orcb_pot_throw tiene que poner ollas (pot, client 3465), no bebederos
(trough, client 2524), y la olla no se puede levantar ni mover.

En la copia de datos del server de prueba, para no esperar ni morir:
  - orc berserker pot thrower.xml: el ataque "rune" con probability="100" cycleticks="2000";
  - el ataque melee con mindamage="1" maxdamage="2".

  python3 scripts/ot/test-pot-thrower.py --port 7275

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
Client, check, packet, pos = _g.Client, _g.check, _g.packet, _g.pos

POT_CLIENT = 3465
TROUGH_CLIENT = 2524


def added(client, since, cid):
    """Posiciones donde apareció el ítem (0x6A x y z id)."""
    found = []
    for m in re.finditer(rb"\x6A(.....)" + re.escape(struct.pack("<H", cid)), client.buf[since:], re.S):
        found.append(struct.unpack("<HHB", m.group(1)))
    return found


def move(client, frm, cid, stack, to):
    client.sock.sendall(packet(b"\x78" + pos(*frm) + struct.pack("<HB", cid, stack) + to + b"\x01"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=7275)
    ap.add_argument("--wait", type=float, default=40.0, help="segundos máximos esperando la primera olla")
    a = ap.parse_args()
    fails = 0

    gm = Client(a.port, 111112, "Bot GM")
    knight = Client(a.port, 111111, "Bot Knight")
    for c in (gm, knight):
        c.read(0.5)
    k0 = knight.mark()
    gm.say("/m Orc Berserker Pot Thrower")
    gm.read(0.5)

    pots, troughs = [], []
    end = time.time() + a.wait
    while time.time() < end and not pots and not troughs:
        knight.read(1.0)
        gm.read(0.1)
        pots, troughs = added(knight, k0, POT_CLIENT), added(knight, k0, TROUGH_CLIENT)
    print(f"         ollas: {pots}  bebederos: {troughs}")
    fails += not check(bool(pots), "el orco tira ollas (pot 3465)")
    fails += not check(not troughs, "no tira bebederos (trough 2524)")
    if not pots:
        print("RESULTADO:", f"{fails} falla(s)")
        return 1

    knight.read(0.5)
    target = pots[0]
    for stack in (1, 2):
        m0 = knight.mark()
        move(knight, target, POT_CLIENT, stack, pos(0xFFFF, 0x40, 0))      # a la mochila
        move(knight, target, POT_CLIENT, stack, pos(0xFFFF, 10, 0))        # a la mano (ammo)
        knight.read(0.6)
        texts = [t for _c, t in knight.messages(m0)]
        print(f"         stackpos {stack}: {texts}")
    picked = [t for _c, t in knight.messages(k0) if "cannot move" in t]
    fails += not check(bool(picked), "levantar la olla: 'You cannot move this object.'")
    ids = knight.open_bag()
    fails += not check(POT_CLIENT not in ids, "la olla no está en la mochila")

    print("RESULTADO:", "OK" if not fails else f"{fails} falla(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
