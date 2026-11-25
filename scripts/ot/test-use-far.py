#!/usr/bin/env python3
"""Prueba de "usar de lejos" (docs/gameplay/FOLLOW.md) en un servidor de PRUEBA con bots (make-test-bots.py).

Escalera de mano de la cueva en cruz: 56,165,9 (sube a z8).

  1. a 5 casillas, "usar" la escalera: el Knight camina hasta el lado y sube (termina en z8);
  2. "usar" de lejos y enseguida dar un paso a mano: se cancela, no sube;
  3. al lado, "usar" sube como siempre.

  python3 scripts/ot/test-use-far.py --port 7275

No apuntarlo al servidor donde se juega.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import struct
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("gifts", Path(__file__).with_name("test-level-gifts.py"))
_g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_g)
Client, check, packet = _g.Client, _g.check, _g.packet

LADDER = (56, 165, 9)
LADDER_CLIENT = 1948            # server 1386
EAST = b"\x66"


def pos(x, y, z):
    return struct.pack("<HHB", x, y, z)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=7275)
    a = ap.parse_args()
    fails = 0

    gm = Client(a.port, 111112, "Bot GM")
    k = Client(a.port, 111111, "Bot Knight")
    for c in (gm, k):
        c.read(0.5)

    def where():
        g0 = gm.mark()
        gm.say("/info Bot Knight")
        gm.read(1.2)
        txt = gm.buf[g0:].decode("latin-1", "replace")
        m = re.search(r"position\s*\(?\s*(\d+)\D+(\d+)\D+(\d+)", txt)
        if not m:
            print("    (respuesta de /info:", repr(txt[-160:]), ")")
        return tuple(int(v) for v in m.groups()) if m else None

    def place(p):
        gm.say(f"/send Bot Knight, {p[0]} {p[1]} {p[2]}")
        gm.read(0.5)
        k.read(0.3)

    def use_ladder():
        k.sock.sendall(packet(b"\x82" + pos(*LADDER) + struct.pack("<HBB", LADDER_CLIENT, 1, 0)))

    # la cueva tiene Fire Devils: el GM la limpia para que no maten al Knight a mitad de la prueba
    gm.say(f"/goto {LADDER[0] + 3} {LADDER[1]} {LADDER[2]}")
    gm.read(0.6)
    gm.say("/killmonsters")
    gm.read(0.6)

    print("1. Usar de lejos")
    place((LADDER[0] + 5, LADDER[1], LADDER[2]))
    use_ladder()
    k.read(4.0)
    p = where()
    fails += not check(p is not None and p[2] == LADDER[2] - 1, f"camina hasta la escalera y sube (queda en {p})")

    print("2. Un paso a mano cancela")
    place((LADDER[0] + 5, LADDER[1], LADDER[2]))
    use_ladder()
    k.read(0.15)
    k.sock.sendall(packet(EAST))
    k.read(3.0)
    p = where()
    fails += not check(p is not None and p[2] == LADDER[2], f"no sube (queda en {p})")

    print("3. Al lado")
    place((LADDER[0] + 1, LADDER[1], LADDER[2]))
    use_ladder()
    k.read(1.0)
    p = where()
    fails += not check(p is not None and p[2] == LADDER[2] - 1, f"sube enseguida (queda en {p})")

    print("FALLAS:", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
