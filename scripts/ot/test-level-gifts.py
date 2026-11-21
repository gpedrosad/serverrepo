#!/usr/bin/env python3
"""Prueba de los regalos de nivel y los avisos de raros (docs/gameplay/LEVEL_UP_REWARDS.md) en un servidor de
PRUEBA con bots (cuentas de make-test-bots.py). Comprueba:
  1. subir de nivel con /nivel: una caja por nivel nuevo, del rango que toca; efecto 50 y "LEVEL UP" que ve
     también el GM que está al lado;
  2. abrir las cajas (en la mano y en la mochila): oro o ítem, y el aviso a todos cuando sale un raro;
  3. bajar y volver a subir no da cajas de nuevo; el nivel siguiente da una sola;
  4. raro de un monstruo: el Bot Knight mata ratas hasta que el GM ve el aviso. En la COPIA de los datos la
     rata tiene que soltar algo raro (p. ej. <item id="2472" chance="400"/>) y lootmul alto.

  python3 scripts/ot/test-level-gifts.py --port 7275

Para que el Bot Mage tenga lugar, en la copia: manos vacías y mochila vacía (ver la doc). No apuntarlo al
servidor donde se juega.
"""
from __future__ import annotations

import argparse
import re
import socket
import struct
import sys
import time

PASSWORD = "asantest"
GIFT_CLIENT = {20354: 5090, 20355: 5091, 20356: 5092, 20357: 5093, 20358: 5094, 20359: 5095}
BACKPACK_CLIENT = 2854          # 1988
COINS_CLIENT = {3031, 3035, 3043}   # gold, platinum, crystal: apilables (llevan un byte de cantidad)
LEVEL_UP_EFFECT = 50


def s(value: str) -> bytes:
    raw = value.encode("latin-1")
    return struct.pack("<H", len(raw)) + raw


def packet(body: bytes) -> bytes:
    return struct.pack("<H", len(body)) + body


def pos(x, y, z) -> bytes:
    return struct.pack("<HHB", x, y, z)


class Client:
    def __init__(self, port, account, name):
        self.name = name
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=10)
        body = struct.pack("<HBHB", 0x020A, 2, 760, 0) + struct.pack("<I", account) + s(name) + s(PASSWORD)
        self.sock.sendall(packet(body))
        self.buf = b""
        self.read(2.0)
        m = re.search(rb"\x0A(....)", self.buf, re.S)
        if not m:
            raise SystemExit(f"{name}: no entró ({self.buf[:60]!r})")
        self.id = struct.unpack("<I", m.group(1))[0]

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

    def mark(self):
        return len(self.buf)

    def say(self, text):
        self.sock.sendall(packet(b"\x96\x01" + s(text)))

    def use(self, where: bytes, client_id: int, stack=0, index=0):
        self.sock.sendall(packet(b"\x82" + where + struct.pack("<HBB", client_id, stack, index)))

    def open_bag(self):
        """Abre la mochila (contenedor 0) y devuelve los client ids de lo que tiene, en orden."""
        for _try in range(3):                    # si ya estaba abierta, el primer "use" la cierra
            start = self.mark()
            self.use(pos(0xFFFF, 3, 0), BACKPACK_CLIENT, 0, 0)
            self.read(0.6)
            m = re.search(rb"\x6E\x00(..)(..)", self.buf[start:], re.S)
            if m:
                break
        else:
            return []
        i = start + m.end() - 2
        name_len = struct.unpack_from("<H", self.buf, i)[0]
        i += 2 + name_len + 2                    # nombre, capacidad, tiene padre
        count = self.buf[i]
        i += 1
        ids = []
        for _ in range(count):
            cid = struct.unpack_from("<H", self.buf, i)[0]
            i += 2 + (1 if cid in COINS_CLIENT else 0)
            ids.append(cid)
        return ids

    def close_bag(self):
        self.sock.sendall(packet(b"\x87\x00"))
        self.read(0.3)

    def attack(self, creature_id):
        self.sock.sendall(packet(b"\xA1" + struct.pack("<I", creature_id)))

    def messages(self, since=0):
        out = []
        for m in re.finditer(rb"\xB4(.)(..)", self.buf[since:], re.S):
            n = struct.unpack("<H", m.group(2))[0]
            text = self.buf[since + m.end():since + m.end() + n]
            if len(text) == n and all(32 <= c < 256 for c in text):
                out.append((m.group(1)[0], text.decode("latin-1")))
        return out


def check(ok, what):
    print(("  OK     " if ok else "  FALLA  ") + what)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=7275)
    ap.add_argument("--mage-level", type=int, default=20, help="nivel del Bot Mage al empezar")
    ap.add_argument("--to", type=int, default=37)
    ap.add_argument("--rats", type=int, default=20)
    a = ap.parse_args()
    fails = 0

    gm = Client(a.port, 111112, "Bot GM")
    mage = Client(a.port, 111111, "Bot Mage")
    gm.say("/c Bot Mage")
    gm.read(1.0)
    mage.read(1.0)

    print("1. Subir de nivel")
    m0, g0 = mage.mark(), gm.mark()
    gm.say(f"/nivel {a.to} Bot Mage")
    mage.read(2.0)
    gm.read(0.5)
    got = []
    for _t, text in mage.messages(m0):
        r = re.match(r"You received an? (\w+ gift) for reaching level (\d+)!", text)
        if r:
            got.append((int(r.group(2)), r.group(1)))
    want = list(range(a.mage_level + 1, a.to + 1))

    def tier(lv):
        return ("legendary" if lv >= 100 else "heroic" if lv >= 80 else "champion" if lv >= 50 else
                "veteran" if lv >= 35 else "adventurer" if lv >= 20 else "novice") + " gift"
    fails += not check([lv for lv, _ in got] == want, f"una caja por nivel {want[0]}-{want[-1]} ({len(got)} cajas)")
    fails += not check(all(name == tier(lv) for lv, name in got), "cada caja del rango de su nivel")
    on_ground = mage.buf[m0:].count(b"It is on the ground")
    print(f"         {on_ground} en el suelo (sin lugar)")
    effect = rb"\x83.....\x33"                                  # efecto 50 se manda como 51
    fails += not check(re.search(effect, mage.buf[m0:], re.S) is not None, "el que sube ve el efecto 50")
    fails += not check(re.search(effect, gm.buf[g0:], re.S) is not None, "el GM de al lado ve el efecto 50")
    fails += not check(b"LEVEL UP" in gm.buf[g0:], "el GM ve el texto LEVEL UP")

    print("2. Abrir las cajas")
    m0, g0 = mage.mark(), gm.mark()
    order = [GIFT_CLIENT[20355]] * 14 + [GIFT_CLIENT[20356]] * 3
    for slot in (5, 6):                                         # manos
        mage.use(pos(0xFFFF, slot, 0), order[0])
        mage.read(0.4)
    for _ in range(len(got)):                                   # lo que sale entra adelante: buscar la caja
        ids = mage.open_bag()
        gifts = [i for i, cid in enumerate(ids) if cid in GIFT_CLIENT.values()]
        if not gifts:
            break
        mage.use(pos(0xFFFF, 0x40, gifts[0]), ids[gifts[0]], gifts[0], 0)
        mage.read(0.4)
        mage.close_bag()
    mage.read(1.0)
    gm.read(0.5)
    opened = [t for _c, t in mage.messages(m0) if t.startswith("You opened ")]
    rares = [t for _c, t in gm.messages(g0) if t.startswith("Bot Mage opened ")]
    for t in opened[:6]:
        print("         " + t)
    for t in rares:
        print("         [a todos] " + t)
    n_open = mage.buf[m0:].count(b"You opened ") + gm.buf[g0:].count(b"Bot Mage opened ")
    fails += not check(n_open == len(got) - on_ground,
                       f"se abrieron {n_open} de {len(got) - on_ground} en la mochila y las manos ({len(rares)} raros)")
    left = [c for c in mage.open_bag() if c in GIFT_CLIENT.values()]
    mage.close_bag()
    fails += not check(not left, f"no quedan cajas en la mochila ({len(left)})")

    print("3. Sin repetir")
    m0 = mage.mark()
    gm.say(f"/nivel {a.to - 5} Bot Mage")
    gm.read(0.5)
    gm.say(f"/nivel {a.to} Bot Mage")
    mage.read(1.5)
    again = [t for _c, t in mage.messages(m0) if t.startswith("You received")]
    fails += not check(not again, f"bajar y volver a {a.to}: 0 cajas ({len(again)})")
    m0 = mage.mark()
    gm.say(f"/nivel {a.to + 1} Bot Mage")
    mage.read(1.5)
    one = [t for _c, t in mage.messages(m0) if t.startswith("You received")]
    fails += not check(len(one) == 1 and f"level {a.to + 1}!" in one[0], f"nivel {a.to + 1}: una caja ({one})")

    print("4. Raro de un monstruo, aviso a todos")
    knight = Client(a.port, 111111, "Bot Knight")
    gm.say("/c Bot Knight")
    gm.read(1.0)
    seen = None
    for i in range(a.rats):
        k0, g0 = knight.mark(), gm.mark()
        gm.say("/m rat")
        knight.read(0.8)
        ids = [struct.unpack("<I", m.group(1))[0] for m in re.finditer(rb"\x61\x00....(....)\x03\x00Rat",
                                                                          knight.buf[k0:], re.S)]
        if not ids:
            continue
        knight.attack(ids[-1])
        knight.read(4.0)
        gm.read(0.3)
        hits = [t for _c, t in gm.messages(g0) if t.startswith("Bot Knight found ")]
        if hits:
            seen = (i + 1, hits[0])
            break
    fails += not check(seen is not None, f"aviso de raro: {seen}")
    print("RESULTADO:", "OK" if not fails else f"{fails} falla(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
