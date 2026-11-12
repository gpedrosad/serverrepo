#!/usr/bin/env python3
"""Bots que usan y maltratan un servidor de PRUEBA para que aparezcan errores de memoria.

Pensado para un binario compilado con AddressSanitizer/UBSan corriendo sobre una COPIA de los datos (ver
docs/systems/SANITIZER_TESTS.md). No apuntarlo al servidor donde se juega: los bots mueren, tiran ítems, crean
cuentas con el account creator y mandan paquetes rotos a propósito.

  python3 scripts/ot/exercise-server.py --port 7173 --account 111111 --password asantest \
      --chars "Bot Knight" "Bot Sorc" --gm-account 111112 --gm-char "Bot GM" --minutes 5

Qué hace cada bot (un hilo por personaje), al azar:
  - camina, gira, habla, usa comandos (!online, !exp...), cambia modo de pelea, mira casillas;
  - dice todos los hechizos de spells.xml y usa la runa del slot de munición;
  - ataca a las criaturas que ve (saca los ids de los paquetes del servidor);
  - mueve y usa ítems del inventario y del piso, abre contenedores;
  - se desconecta bien (logout) o cortando el socket, y vuelve a entrar;
  - con --fuzz: manda paquetes con opcodes y cuerpos al azar (lo que haría un cliente roto o malicioso).
El bot GM (opcional) invoca monstruos al lado suyo con /m y hace /save, /clean, /getonline, /reload config.
Aparte, un hilo golpea el puerto sin entrar al juego: consultas de estado, logins de cuenta malos, primeros
paquetes con basura y pedidos al account creator.
"""
from __future__ import annotations

import argparse
import random
import re
import socket
import struct
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPELLS_XML = ROOT / "server" / "YurOTS" / "ots" / "data" / "spells" / "spells.xml"
MONSTERS = ["Rat", "Troll", "Orc Warrior", "Cyclops", "Dragon", "Demon Skeleton", "Necromancer", "Fire Elemental",
            "Hero", "Vampire", "Beholder", "Dragon Lord", "Demon", "Giant Spider", "Warlock", "Hydra"]
CHAT = ["hi", "hello", "trade", "bye", "yes", "no", "job", "name", "!online", "!exp", "!mana", "!frags", "!pz",
        "!uptime", "!premmy", "!house", "exiva \"Bot GM\"", "exiva \"nadie\"", "exura sio \"Bot Knight\"",
        "utevo res \"rat\"", "utevo res \"demon\"", "exani tera", "exani hur \"up\"", "exani hur \"down\"",
        "alana sio \"Bot Sorc\"", "aleta sio", "aleta som", "x" * 250, "\"", "  ", "/m Demon", "/a 5", "/goto 1 1 1"]
# Opcodes que el cliente 7.6 manda en juego (para que el fuzz no sea solo ruido que el servidor descarta).
GAME_OPCODES = [0x14, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B, 0x6C, 0x6D, 0x6F, 0x70, 0x71, 0x72, 0x78, 0x7D,
                0x7E, 0x7F, 0x80, 0x82, 0x83, 0x84, 0x85, 0x87, 0x88, 0x89, 0x8A, 0x8C, 0x96, 0x97, 0x98, 0x99, 0x9A,
                0x9B, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xAA, 0xAB, 0xBE, 0xC9, 0xCA, 0xD2, 0xD3, 0xDC, 0xDD]

stop = threading.Event()
stats: dict[str, int] = {}
stats_lock = threading.Lock()


def count(key: str, n: int = 1) -> None:
    with stats_lock:
        stats[key] = stats.get(key, 0) + n


def s(value: str) -> bytes:
    raw = value.encode("latin-1", "replace")
    return struct.pack("<H", len(raw)) + raw


def packet(body: bytes) -> bytes:
    return struct.pack("<H", len(body)) + body


def pos(x: int, y: int, z: int) -> bytes:
    return struct.pack("<HHB", x & 0xFFFF, y & 0xFFFF, z & 0xFF)


def recv_some(sock: socket.socket, timeout: float) -> bytes:
    sock.settimeout(timeout)
    try:
        return sock.recv(65536)
    except socket.timeout:
        return b""


def load_spell_words(path: Path = SPELLS_XML) -> list[str]:
    try:
        text = path.read_text(encoding="latin-1")
    except OSError:
        return ["exura", "exori", "utevo lux", "utani hur", "exevo gran mas vis"]
    return sorted(set(re.findall(r'words="([^"]+)"', text)))


class Bot(threading.Thread):
    def __init__(self, a, account: int, password: str, name: str, gm: bool = False):
        super().__init__(daemon=True, name=name)
        self.a, self.account, self.password, self.char, self.gm = a, account, password, name, gm
        self.rng = random.Random(f"{a.seed}:{name}")
        self.sock: socket.socket | None = None
        self.creatures: list[int] = []
        self.spells = a.spells

    # --- conexión ---
    def login(self) -> bool:
        try:
            sock = socket.create_connection((self.a.host, self.a.port), timeout=10)
            body = struct.pack("<HBHB", 0x020A, 2, 760, 0) + struct.pack("<I", self.account)
            body += s(self.char) + s(self.password)
            sock.sendall(packet(body))
            first = recv_some(sock, 60.0)
        except OSError:
            count("login: sin conexión")
            return False
        # 0x14 = mensaje de error. Si entra, el paquete trae 0x0A (a veces después de un 0xA1 con los skills).
        if len(first) < 3 or first[2] == 0x14:
            msg = first[5:5 + 50].decode("latin-1", "replace") if len(first) > 5 else "sin respuesta"
            count("login rechazado: " + "".join(c if c.isprintable() else "?" for c in msg))
            sock.close()
            return False
        self.sock = sock
        self.learn(first)
        count("logins")
        return True

    def close(self, clean: bool) -> None:
        if not self.sock:
            return
        try:
            if clean:
                self.sock.sendall(packet(b"\x14"))
                time.sleep(0.3)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass
        self.sock = None
        count("logout" if clean else "corte de socket")

    def send(self, body: bytes) -> None:
        if self.sock:
            self.sock.sendall(packet(body))
            count("paquetes")

    def learn(self, data: bytes) -> None:
        """Saca ids de criaturas de los paquetes: 0x61 0x00, id a olvidar (4), id (4), nombre."""
        for m in re.finditer(rb"\x61\x00....(....)([\x01-\x1e])\x00([A-Za-z ']{1,30})", data, re.S):
            cid = struct.unpack("<I", m.group(1))[0]
            if len(m.group(3)) >= m.group(2)[0] and cid not in self.creatures:
                self.creatures.append(cid)
        del self.creatures[:-40]

    # --- acciones ---
    def act(self) -> None:
        r = self.rng
        roll = r.random()
        if self.gm:
            if roll < 0.45:
                self.send(b"\x96\x01" + s("/m " + r.choice(MONSTERS)))
            elif roll < 0.55:
                self.send(b"\x96\x01" + s(r.choice(["/save", "/clean", "/getonline", "/pos", "/info Bot Knight", "/reload config"])))
            elif roll < 0.8:
                self.send(bytes([r.choice([0x65, 0x66, 0x67, 0x68])]))
            else:
                self.send(b"\x96\x01" + s(r.choice(self.spells)))
            return
        if roll < 0.22:      # caminar (incluye diagonales)
            self.send(bytes([r.choice([0x65, 0x66, 0x67, 0x68, 0x6A, 0x6B, 0x6C, 0x6D])]))
        elif roll < 0.27:    # girar
            self.send(bytes([r.choice([0x6F, 0x70, 0x71, 0x72])]))
        elif roll < 0.47:    # hechizos
            self.send(b"\x96\x01" + s(r.choice(self.spells)))
        elif roll < 0.55:    # hablar / comandos / yell / whisper
            self.send(bytes([0x96, r.choice([1, 1, 2, 3])]) + s(r.choice(CHAT)))
        elif roll < 0.68 and self.creatures:   # atacar / seguir
            self.send(bytes([r.choice([0xA1, 0xA1, 0xA1, 0xA2])]) + struct.pack("<I", r.choice(self.creatures)))
        elif roll < 0.74:    # runa del slot de munición a una casilla cercana o a una criatura
            x, y, z = self.a.near(r)
            self.send(b"\x83" + pos(0xFFFF, 10, 0) + struct.pack("<HB", r.choice(self.a.runes), 0)
                      + pos(x, y, z) + struct.pack("<HB", 99, r.choice([0, 1, 2])))
        elif roll < 0.79:    # modo de pelea
            self.send(bytes([0xA0, r.choice([1, 2, 3]), r.choice([0, 1])]))
        elif roll < 0.84:    # mirar
            x, y, z = self.a.near(r)
            self.send(b"\x8C" + pos(x, y, z) + struct.pack("<HB", r.randrange(100, 3000), r.randrange(0, 4)))
        elif roll < 0.90:    # usar algo del inventario o del piso
            if r.random() < 0.5:
                slot = r.randrange(1, 11)
                self.send(b"\x82" + pos(0xFFFF, slot, 0) + struct.pack("<HBB", r.randrange(100, 3000), 0, r.randrange(0, 4)))
            else:
                x, y, z = self.a.near(r)
                self.send(b"\x82" + pos(x, y, z) + struct.pack("<HBB", r.randrange(100, 3000), r.randrange(0, 4), 0))
        elif roll < 0.96:    # mover ítems: inventario <-> piso <-> contenedor
            def place() -> bytes:
                k = r.random()
                if k < 0.4:
                    return pos(0xFFFF, r.randrange(1, 11), 0)
                if k < 0.6:
                    return pos(0xFFFF, 0x40 + r.randrange(0, 3), r.randrange(0, 20))
                return pos(*self.a.near(r))
            self.send(b"\x78" + place() + struct.pack("<HB", r.randrange(100, 3000), r.randrange(0, 4))
                      + place() + bytes([r.choice([1, 1, 5, 100])]))
        elif roll < 0.98:    # cerrar contenedor / subir de contenedor / parar
            self.send(r.choice([b"\x87\x00", b"\x88\x00", b"\xBE", b"\x69"]))
        else:                # canales y lista vip
            self.send(r.choice([b"\x97", b"\x98\x04\x00", b"\x99\x04\x00", b"\xDC" + s("Bot GM"),
                                b"\xDD" + struct.pack("<I", 0x10000001)]))

    def fuzz(self) -> None:
        r = self.rng
        op = r.choice(GAME_OPCODES) if r.random() < 0.8 else r.randrange(0, 256)
        if op == 0x14:
            return
        k = r.random()
        if k < 0.3:
            body = b""
        elif k < 0.9:
            body = bytes(r.randrange(0, 256) for _ in range(r.randrange(1, 40)))
        else:   # un string con largo declarado mayor al real
            body = struct.pack("<H", r.choice([0xFFFF, 5000, 300])) + bytes(r.randrange(32, 127) for _ in range(r.randrange(0, 20)))
        self.send(bytes([op]) + body)
        count("fuzz")

    def run(self) -> None:
        r = self.rng
        while not stop.is_set():
            if not self.login():
                time.sleep(2.0)
                continue
            session_end = time.monotonic() + r.uniform(8, 60)
            try:
                while not stop.is_set() and time.monotonic() < session_end:
                    if self.a.fuzz and not self.gm and r.random() < 0.25:
                        self.fuzz()
                    else:
                        self.act()
                    data = recv_some(self.sock, r.uniform(0.05, 0.4))
                    if data:
                        self.learn(data)
            except OSError:
                count("servidor cerró la conexión")
                self.sock = None
                time.sleep(1.0)
                continue
            self.close(clean=r.random() < 0.6)
            time.sleep(r.uniform(0.2, 2.0))
        self.close(clean=True)


def knock(a) -> None:
    """Golpea el puerto sin entrar al juego."""
    r = random.Random(f"{a.seed}:knock")
    while not stop.is_set():
        k = r.random()
        try:
            with socket.create_connection((a.host, a.port), timeout=5) as sock:
                if k < 0.3:      # estado
                    sock.sendall(packet(struct.pack("<H", 0xFFFF) + b"info"))
                elif k < 0.5:    # login de cuenta (lista de personajes), a veces con datos malos
                    acc = a.account if r.random() < 0.5 else r.randrange(0, 2 ** 32)
                    pw = a.password if r.random() < 0.5 else "x" * r.choice([0, 1, 40, 300])
                    sock.sendall(packet(struct.pack("<BHH", 1, 2, 760) + bytes(12) + struct.pack("<I", acc) + s(pw)))
                elif k < 0.65:   # entrar al mundo con datos malos
                    sock.sendall(packet(struct.pack("<HBHB", 0x020A, 2, r.choice([760, 0, 860]), 0)
                                        + struct.pack("<I", r.randrange(0, 2 ** 32)) + s("No Existe") + s("x")))
                elif k < 0.8:    # account creator
                    name = "".join(r.choice("abcdefghij") for _ in range(r.randrange(0, 12)))
                    sock.sendall(packet(struct.pack("<H", 0xFFAC) + f"{name} pw {r.randrange(0, 3)} {r.randrange(0, 6)}".encode()))
                elif k < 0.85:   # paquete vacío o de un byte (antes tiraba el servidor: GetRaw con largo negativo)
                    sock.sendall(packet(r.choice([b"", b"\xff", b"\x01", b"\x0a", b"\xff\xff", b"\xac\xff", b"\x01\xff"])))
                elif k < 0.92:   # basura
                    sock.sendall(packet(bytes(r.randrange(0, 256) for _ in range(r.randrange(0, 60)))))
                else:            # largo declarado enorme y cortar
                    sock.sendall(struct.pack("<H", 0xFFFF) + bytes(r.randrange(0, 256) for _ in range(20)))
                recv_some(sock, 1.0)
            count("golpes al puerto")
        except OSError:
            count("golpe: sin conexión")
        time.sleep(r.uniform(0.1, 0.6))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--account", type=int, required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--chars", nargs="+", required=True)
    ap.add_argument("--gm-account", type=int)
    ap.add_argument("--gm-password")
    ap.add_argument("--gm-char")
    ap.add_argument("--center", type=int, nargs=3, default=(130, 53, 6), metavar=("X", "Y", "Z"),
                    help="zona donde están los bots (para apuntar runas y mover ítems)")
    ap.add_argument("--runes", type=int, nargs="+", default=[2268, 2311, 2273, 2304, 2313, 2305, 2293])
    ap.add_argument("--spells-xml", type=Path, default=SPELLS_XML, help="de dónde sacar las palabras de los hechizos")
    ap.add_argument("--minutes", type=float, default=3.0)
    ap.add_argument("--fuzz", action="store_true", help="además manda paquetes rotos")
    ap.add_argument("--seed", default="1")
    a = ap.parse_args()
    if a.port == 7171:
        ap.error("esto es para un servidor de prueba en otro puerto, no para el 7171 donde se juega")
    a.spells = load_spell_words(a.spells_xml)
    cx, cy, cz = a.center
    a.near = lambda r: (cx + r.randrange(-6, 7), cy + r.randrange(-6, 7), cz)

    bots = [Bot(a, a.account, a.password, name) for name in a.chars]
    if a.gm_char:
        bots.append(Bot(a, a.gm_account or a.account, a.gm_password or a.password, a.gm_char, gm=True))
    threads = bots + [threading.Thread(target=knock, args=(a,), daemon=True)]
    for t in threads:
        t.start()
    end = time.monotonic() + a.minutes * 60
    try:
        while time.monotonic() < end:
            time.sleep(5)
            try:   # si el servidor murió, no tiene sentido seguir
                socket.create_connection((a.host, a.port), timeout=5).close()
            except OSError:
                print("el servidor dejó de aceptar conexiones: revisar su log")
                break
    except KeyboardInterrupt:
        pass
    stop.set()
    for t in threads:
        t.join(timeout=5)
    for key in sorted(stats):
        print(f"  {stats[key]:7d}  {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
