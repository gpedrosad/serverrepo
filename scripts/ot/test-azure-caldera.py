#!/usr/bin/env python3
"""Prueba de la Caldera Azul (docs/items-and-map/CALDERA_AZUL.md) en un servidor de PRUEBA con bots
(make-test-bots.py con los bots en la plaza del templo: 163 49 7).

  1. el portal 163,47,7 lleva a la llegada 660,378,7;
  2. en la llegada se ve la lava azul (client id 6080) y los monstruos de la zona aparecen en pantalla;
  3. el TP de vuelta (656,378) devuelve a la plaza, a 163,48,7.

  python3 scripts/ot/test-azure-caldera.py --port 7275

No apuntarlo al servidor donde se juega.
"""
from __future__ import annotations

import argparse
import importlib.util
import struct
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("gifts", Path(__file__).with_name("test-level-gifts.py"))
_g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_g)
Client, check = _g.Client, _g.check

NORTH, WEST = b"\x65", b"\x68"
BLUE_LAVA_CLIENT = 6080


def pos(x, y, z):
    return struct.pack("<HHB", x, y, z)


def step(c, d):
    c.sock.sendall(_g.packet(d))
    c.read(1.2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=7275)
    a = ap.parse_args()
    fails = 0

    gm = Client(a.port, 111112, "Bot GM")
    k = Client(a.port, 111111, "Bot Knight")
    for c in (gm, k):
        c.read(0.5)
    gm.say("/send Bot Knight, 163 48 7")
    gm.read(0.5)
    k.read(0.5)

    print("1. Portal del templo")
    k0 = k.mark()
    step(k, NORTH)                                   # 163,48 -> portal 163,47
    k.read(1.0)
    got = k.buf[k0:]
    fails += not check(b"\x64" + pos(660, 378, 7) in got, "el portal 163 lleva a 660,378,7")

    print("2. La zona")
    fails += not check(struct.pack("<H", BLUE_LAVA_CLIENT) in got, "llega la lava azul (client 6080) en la vista")
    gm.say("/goto 700 346 7")                        # mitad del camino
    g0 = gm.mark()
    gm.read(2.0)
    view = gm.buf[g0:]
    seen = [n for n in ("Azure Skeleton", "Azure Devil", "Azure Bonebeast", "Azure Lich") if n.encode() in view]
    fails += not check(bool(seen), f"monstruos de la zona en pantalla: {', '.join(seen) or 'ninguno'}")

    print("3. TP de vuelta")
    gm.say("/send Bot Knight, 657 378 7")
    gm.read(0.5)
    k0 = k.mark()
    step(k, WEST)                                    # 657 -> TP 656
    k.read(1.0)
    fails += not check(b"\x64" + pos(163, 48, 7) in k.buf[k0:], "el TP de vuelta deja en 163,48,7")

    print("FALLAS:", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
