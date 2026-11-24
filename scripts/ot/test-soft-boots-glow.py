#!/usr/bin/env python3
"""Prueba de las Soft Boots que brillan puestas (docs/gameplay/SOFT_BOOTS.md#brillo-puestas), en un servidor de
PRUEBA con bots (make-test-bots.py). Puestas tienen que ser el ítem "in use" (client 6070, con destellos) y en la
mochila las de siempre (client 3549).

En la copia de datos, en "bot knight.xml":
  - pies (slot 8): <item id="2640" time="9000"/>   (9 s: se gastan durante la prueba)
  - mano izquierda (slot 6): <item id="20124"/>    (Azure Sunstone, para recargarlas puestas)

  python3 scripts/ot/test-soft-boots-glow.py --port 7275

No apuntarlo al servidor donde se juega.
"""
from __future__ import annotations

import argparse
import importlib.util
import struct
import sys
import time
from pathlib import Path

_spec = importlib.util.spec_from_file_location("gifts", Path(__file__).with_name("test-level-gifts.py"))
_g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_g)
Client, check, packet, pos = _g.Client, _g.check, _g.packet, _g.pos

BOOTS, BOOTS_IN_USE, WORN, SUNSTONE = 3549, 6070, 3550, 4828
FEET, LEFT_HAND = 8, 6


def slot_set(client, since, slot, cid):
    """El server puso `cid` en el slot (0x78 slot id)."""
    return b"\x78" + bytes([slot]) + struct.pack("<H", cid) in client.buf[since:]


def container_add(client, since, cid):
    """Entró `cid` a un contenedor abierto (0x70 contenedor id)."""
    return any(client.buf[i + 2:i + 4] == struct.pack("<H", cid)
               for i in range(since, len(client.buf) - 4) if client.buf[i] == 0x70)


def move(client, frm: bytes, cid, stack, to: bytes):
    client.sock.sendall(packet(b"\x78" + frm + struct.pack("<HB", cid, stack) + to + b"\x01"))


def use_with(client, frm: bytes, cid, to: bytes, to_cid):
    client.sock.sendall(packet(b"\x83" + frm + struct.pack("<HB", cid, 0) + to + struct.pack("<HB", to_cid, 0)))


def wait_for(client, cond, secs):
    end = time.time() + secs
    while time.time() < end:
        if cond():
            return True
        client.read(0.5)
    return cond()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=7275)
    a = ap.parse_args()
    fails = 0

    k = Client(a.port, 111111, "Bot Knight")
    k.read(0.5)
    fails += not check(slot_set(k, 0, FEET, BOOTS_IN_USE), "al entrar, las botas puestas brillan (client 6070)")
    fails += not check(not slot_set(k, 0, FEET, BOOTS), "al entrar, no llegan como las de siempre (3549)")

    k.open_bag()
    m = k.mark()
    # al lugar 19 (vacío): el lugar 0 de la mochila de los bots es otra mochila y las metería adentro
    move(k, pos(0xFFFF, FEET, 0), BOOTS_IN_USE, 0, pos(0xFFFF, 0x40, 19))     # pies -> mochila
    k.read(1.0)
    fails += not check(container_add(k, m, BOOTS), "sacadas a la mochila: vuelven a ser las de siempre (3549)")
    fails += not check(not container_add(k, m, BOOTS_IN_USE), "en la mochila no brillan")

    m = k.mark()
    move(k, pos(0xFFFF, 0x40, 0), BOOTS, 0, pos(0xFFFF, FEET, 0))             # mochila -> pies
    k.read(1.0)
    fails += not check(slot_set(k, m, FEET, BOOTS_IN_USE), "puestas otra vez: brillan")

    m = k.mark()
    k.sock.sendall(packet(b"\x8C" + pos(0xFFFF, FEET, 0) + struct.pack("<HB", BOOTS_IN_USE, 0)))
    k.read(0.8)
    raw = k.buf[m:]                    # la descripción trae saltos de línea: messages() la descarta
    i = raw.find(b"You see")
    look = raw[i:i + 160].split(b"\x02\x00")[0].decode("latin-1") if i >= 0 else ""
    print(f"         look: {look!r}")
    fails += not check("soft boots" in look and "Faster regeneration" in look, "al mirarlas: soft boots con su regen")

    m = k.mark()
    worn = wait_for(k, lambda: slot_set(k, m, FEET, WORN), 20)
    fails += not check(worn, "al agotarse pasan a worn (3550) y dejan de brillar")

    m = k.mark()
    use_with(k, pos(0xFFFF, LEFT_HAND, 0), SUNSTONE, pos(0xFFFF, FEET, 0), WORN)
    fails += not check(wait_for(k, lambda: slot_set(k, m, FEET, BOOTS_IN_USE), 6),
                       "recargadas puestas con la Azure Sunstone: vuelven a brillar")

    print("RESULTADO:", "OK" if not fails else f"{fails} falla(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
