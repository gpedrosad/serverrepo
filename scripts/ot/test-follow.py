#!/usr/bin/env python3
"""Prueba del follow (docs/gameplay/FOLLOW.md) en un servidor de PRUEBA con bots
(make-test-bots.py con los bots en un lugar abierto, por defecto la plaza del templo: 161 50 7).

  1. el Knight sigue al Mage (0xA2): cuando el GM lo manda a 5 casillas, el Knight camina hasta quedar al lado;
  2. el Mage se vuelve a mover y el Knight lo vuelve a alcanzar;
  3. con Esc (0xBE) el Knight deja de seguir: el Mage se mueve y el Knight se queda quieto;
  4. modo perseguir (0xA0): atacando un Spit Nettle en el claro de la Wave Arena, con perseguir el Knight se acerca
     hasta el cuerpo a cuerpo (queda al lado o lo mata); con "quieto" no se mueve.

  python3 scripts/ot/test-follow.py --port 7275 --start 161 50 7

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


def pos(x, y, z):
    return struct.pack("<HHB", x, y, z)


def track(buf: bytes, start):
    """Sigue los paquetes 0x6D (criatura se mueve) desde `start`: devuelve la última posición del jugador."""
    cur = start
    i = 0
    while True:
        m = re.compile(re.escape(b"\x6d" + pos(*cur)) + rb"(.)(.....)", re.S).search(buf, i)
        if not m:
            return cur
        cur = struct.unpack("<HHB", m.group(2))
        i = m.end()


def adjacent(a, b):
    return a[2] == b[2] and abs(a[0] - b[0]) <= 1 and abs(a[1] - b[1]) <= 1 and a != b


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=7275)
    ap.add_argument("--start", type=int, nargs=3, default=(161, 50, 7))
    a = ap.parse_args()
    sx, sy, sz = a.start
    fails = 0

    gm = Client(a.port, 111112, "Bot GM")
    knight = Client(a.port, 111111, "Bot Knight")
    mage = Client(a.port, 111111, "Bot Mage")
    for c in (gm, knight, mage):
        c.read(0.5)

    def send(who, p):
        gm.say(f"/send {who}, {p[0]} {p[1]} {p[2]}")
        gm.read(0.4)

    k_pos = (sx, sy, sz)
    send("Bot Knight", k_pos)
    send("Bot Mage", (sx + 1, sy, sz))
    knight.read(0.5)
    k0 = knight.mark()

    print("1. Follow")
    knight.sock.sendall(packet(b"\xA2" + struct.pack("<I", mage.id)))
    knight.read(0.5)
    target = (sx + 5, sy + 2, sz)
    send("Bot Mage", target)
    knight.read(4.0)
    k_pos = track(knight.buf[k0:], k_pos)
    fails += not check(adjacent(k_pos, target), f"el Knight alcanza al Mage ({k_pos} junto a {target})")

    print("2. Se vuelve a mover")
    k0 = knight.mark()
    target2 = (sx - 1, sy + 3, sz)
    send("Bot Mage", target2)
    knight.read(4.0)
    k_pos = track(knight.buf[k0:], k_pos)
    fails += not check(adjacent(k_pos, target2), f"lo vuelve a alcanzar ({k_pos} junto a {target2})")

    print("3. Esc corta el follow")
    knight.sock.sendall(packet(b"\xBE"))
    knight.read(0.5)
    k0 = knight.mark()
    before = k_pos
    send("Bot Mage", (sx + 5, sy, sz))
    knight.read(3.0)
    k_pos = track(knight.buf[k0:], k_pos)
    fails += not check(k_pos == before, f"el Knight se queda quieto ({k_pos})")

    print("4. Modo perseguir")
    spot, nettle_at = (603, 214, 7), (607, 210, 7)
    send("Bot Knight", spot)
    gm.say(f"/goto {nettle_at[0]} {nettle_at[1] - 1} {nettle_at[2]}")
    gm.read(0.5)
    gm.sock.sendall(packet(b"\x71"))                 # gira al sur (0x71; 0x67 sería caminar): aparece delante
    gm.read(0.5)
    k0 = knight.mark()
    gm.say("/m Spit Nettle")
    gm.read(0.5)
    gm.say(f"/goto {spot[0]} {spot[1] + 3} {spot[2]}")  # el GM se aparta
    gm.read(0.5)
    knight.read(0.8)
    m = re.search(rb"\x61\x00....(....)\x0b\x00Spit Nettle", knight.buf[k0:], re.S)
    fails += not check(bool(m), "el Knight ve al Spit Nettle")
    if m:
        nid = m.group(1)
        k_pos = spot
        k0 = knight.mark()
        knight.sock.sendall(packet(b"\xA0\x01\x01\x01"))   # ofensivo, perseguir, seguro
        knight.sock.sendall(packet(b"\xA1" + nid))
        knight.read(5.0)
        k_pos = track(knight.buf[k0:], k_pos)
        n_pos = track(knight.buf[k0:], nettle_at)           # el nettle también camina
        killed = any("Loot of a spit nettle" in t for _c, t in knight.messages(k0))
        fails += not check(adjacent(k_pos, n_pos) or killed,
                           f"con perseguir llega al cuerpo a cuerpo ({k_pos}, nettle {n_pos}, muerto: {killed})")
        if killed:                                          # otro para la prueba de 'quieto'
            gm.say(f"/goto {nettle_at[0]} {nettle_at[1] - 1} {nettle_at[2]}")
            gm.read(0.5)
            gm.sock.sendall(packet(b"\x71"))
            gm.read(0.4)
            k1 = knight.mark()
            gm.say("/m Spit Nettle")
            gm.read(0.5)
            gm.say(f"/goto {spot[0]} {spot[1] + 3} {spot[2]}")
            gm.read(0.5)
            knight.read(0.5)
            m = re.search(rb"\x61\x00....(....)\x0b\x00Spit Nettle", knight.buf[k1:], re.S) or m
            nid = m.group(1)
        knight.sock.sendall(packet(b"\xBE"))
        knight.read(0.3)
        send("Bot Knight", spot)
        knight.read(0.5)
        k_pos = spot
        k0 = knight.mark()
        knight.sock.sendall(packet(b"\xA0\x01\x00\x01"))   # ofensivo, quieto, seguro
        knight.sock.sendall(packet(b"\xA1" + nid))
        knight.read(3.0)
        k_pos = track(knight.buf[k0:], k_pos)
        fails += not check(k_pos == spot, f"con 'quieto' no se mueve ({k_pos})")

    print("FALLAS:", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
