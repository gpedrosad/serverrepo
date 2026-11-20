#!/usr/bin/env python3
"""Prueba de summons que siguen al dueño (docs/gameplay/SUMMONS.md) en un servidor de PRUEBA con bots.

Un druida (cuenta de make-test-bots.py) va con /c del GM a --start (fuera de PZ: en PZ no se invoca), invoca
un summon (--monster, de data/summons.xml), camina y el GM lo lleva a --dest, en otro piso. Lee los
paquetes del servidor para saber dónde está la rata y comprueba:
  1. que la rata tenga la velocidad del druida (paquete 0x8F);
  2. que después de cada paso la rata quede al lado del druida (y casi siempre en la casilla que dejó);
  3. que al cambiar de piso la rata aparezca al lado del druida en el piso nuevo.

  python3 scripts/ot/test-summon-follow.py --port 7275 --start 116 60 7 --dest 120 46 6

No apuntarlo al servidor donde se juega (usa las cuentas de prueba 111111 y 111112).
"""
from __future__ import annotations

import argparse
import re
import socket
import struct
import sys
import time


def s(value: str) -> bytes:
    raw = value.encode("latin-1")
    return struct.pack("<H", len(raw)) + raw


def packet(body: bytes) -> bytes:
    return struct.pack("<H", len(body)) + body


class Client:
    def __init__(self, port, account, password, name):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=10)
        body = struct.pack("<HBHB", 0x020A, 2, 760, 0) + struct.pack("<I", account) + s(name) + s(password)
        self.sock.sendall(packet(body))
        self.buf = b""
        self.read(2.0)
        m = re.search(rb"\x0A(....)", self.buf, re.S)
        if not m:
            raise SystemExit(f"{name}: no entró ({self.buf[:60]!r})")
        self.id = struct.unpack("<I", m.group(1))[0]
        m = re.search(rb"\x64(.....)", self.buf, re.S)
        self.pos = struct.unpack("<HHB", m.group(1)) if m else None

    def read(self, secs):
        end = time.time() + secs
        self.sock.settimeout(0.2)
        while time.time() < end:
            try:
                data = self.sock.recv(65536)
                if not data:
                    break
                self.buf += data
            except socket.timeout:
                pass
        return self.buf

    def say(self, text):
        self.sock.sendall(packet(b"\x96\x01" + s(text)))

    def step(self, opcode):
        self.sock.sendall(packet(bytes([opcode])))


def unpack_pos(b):
    return struct.unpack("<HHB", b)


NAME = rb"\x6A(.....)\x61\x00....(....)..(?:Wolf|Rat|Skeleton|Orc|Troll|Bear|Ghoul|Demon Skeleton|Fire Elemental)"


def track(buf, rat_id, rat_pos, me_id, me_pos):
    """Recorre los paquetes en orden: altas (0x6A), movidas (0x6D) y velocidades (0x8F)."""
    speeds = {}
    # 0x69 (casilla actualizada): así avisa Game::teleport cuando se teletransporta un monstruo
    for m in re.finditer(NAME + rb"|[\x6A\x69](.....)(?:..){0,4}?\x62\x00(....)|\x6D(.....)(.)(.....)"
                         rb"|\x8F(....)(..)", buf, re.S):
        if m.group(1):
            rat_id, rat_pos = struct.unpack("<I", m.group(2))[0], unpack_pos(m.group(1))
        elif m.group(3):
            cid = struct.unpack("<I", m.group(4))[0]
            if cid == rat_id:
                rat_pos = unpack_pos(m.group(3))
            elif cid == me_id:
                me_pos = unpack_pos(m.group(3))
        elif m.group(5):
            frm, to = unpack_pos(m.group(5)), unpack_pos(m.group(7))
            if frm == me_pos:           # primero el dueño: al cambiar de lugar comparten casilla un instante
                me_pos = to
            elif frm == rat_pos:
                rat_pos = to
        else:
            speeds[struct.unpack("<I", m.group(8))[0]] = struct.unpack("<H", m.group(9))[0]
    return rat_id, rat_pos, me_pos, speeds


def creature_speeds(buf):
    """Velocidad de cada criatura en sus altas (0x61): id, nombre, vida, dirección, outfit, luz, velocidad."""
    out = {}
    for m in re.finditer(rb"\x61\x00....(....)", buf, re.S):
        i = m.end()
        try:
            cid = struct.unpack("<I", m.group(1))[0]
            n = struct.unpack_from("<H", buf, i)[0]
            i += 2 + n + 2                      # nombre, vida, dirección
            look = buf[i]                       # en 7.6 el looktype es de 1 byte
            i += 1 + (4 if look else 2) + 2     # outfit (colores o ítem) y luz
            out[cid] = struct.unpack_from("<H", buf, i)[0]
        except struct.error:
            pass
    return out


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1])) if a and b and a[2] == b[2] else 99


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=7275)
    ap.add_argument("--password", default="asantest")
    ap.add_argument("--monster", default="Wolf", help="criatura de data/summons.xml")
    ap.add_argument("--start", type=int, nargs=3, default=[116, 60, 7], help="casilla libre fuera de PZ")
    ap.add_argument("--dest", type=int, nargs=3, default=[120, 46, 6], help="casilla libre en otro piso, fuera de PZ")
    a = ap.parse_args()

    druid = Client(a.port, 111111, a.password, "Bot Druid")
    gm = Client(a.port, 111112, a.password, "Bot GM")
    gm.say(f"/goto {a.start[0]} {a.start[1]} {a.start[2]}")
    gm.read(1.0)
    gm.say("/c Bot Druid")
    druid.read(1.5)
    druid.pos = tuple(a.start)
    print(f"druida {druid.id} en {druid.pos}")
    mark = len(druid.buf)
    druid.say(f'utevo res "{a.monster.lower()}')   # el cliente manda sin comilla de cierre
    druid.read(1.5)
    rat_id, rat_pos, me, speeds = track(druid.buf[mark:], None, None, druid.id, druid.pos)
    if not rat_id:
        print("FALLA: no apareció la rata")
        return 1
    print(f"rata {rat_id} en {rat_pos}")

    fails = behind = steps = back = 0
    for opcode in [0x66] * 5 + [0x68] * 5 + [0x66] * 3:   # este, oeste, este
        before = me
        mark = len(druid.buf)
        druid.step(opcode)
        druid.read(0.7)
        rat_id, rat_pos, me, _speeds = track(druid.buf[mark:], rat_id, rat_pos, druid.id, me)
        speeds.update(_speeds)
        if me == before:
            continue            # paso bloqueado
        steps += 1
        back += opcode == 0x68
        d = cheb(rat_pos, me)
        behind += rat_pos == before
        if d > 1:
            fails += 1
        print(f"  druida {me}  rata {rat_pos}  distancia {d}{'  (en la casilla que dejó)' if rat_pos == before else ''}")
    added = creature_speeds(druid.buf)
    my_speed = speeds.get(druid.id, added.get(druid.id))
    rat_speed = speeds.get(rat_id, added.get(rat_id))
    print(f"velocidad: rata {rat_speed}, druida {my_speed}")

    gm.say(f"/goto {a.dest[0]} {a.dest[1]} {a.dest[2]}")
    gm.read(1.0)
    mark = len(druid.buf)
    gm.say("/c Bot Druid")
    druid.read(2.0)
    me = tuple(a.dest)
    rat_id, rat_pos, _me, speeds = track(druid.buf[mark:], rat_id, rat_pos, druid.id, me)
    tp_ok = cheb(rat_pos, me) <= 1 and rat_pos[2] == me[2]
    print(f"después de /c: druida {me}  rata {rat_pos}  {'OK' if tp_ok else 'FALLA'}")

    ok = rat_id and steps >= 10 and back >= 4 and fails == 0 and tp_ok and rat_speed == my_speed
    print(f"{'OK' if ok else 'FALLA'}: {steps} pasos ({back} de vuelta, cambiando de lugar con la rata), "
          f"{fails} con la rata lejos, {behind} en la casilla que dejó")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
