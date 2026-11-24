#!/usr/bin/env python3
"""Prueba del Crisol v4 (docs/gameplay/CRUCIBLE.md) en un servidor de PRUEBA con bots
(make-test-bots.py con los bots parados en la sala: 605 104 0).

  1. Varkon saluda y explica la escalera;
  2. Silver cerrada sin Bronze; en grupo, el que no cumple se queda en la sala;
  3. Bronze, Silver y Gold en orden: cuenta regresiva, pelea, premio y puerta siguiente;
  4. el jefe de Oro una sola vez por día; la palanca de info muestra el progreso;
  5. entrar a una arena sin la palanca (relog adentro) te manda a la sala;
  6. una arena abandonada se vacía sola y la corrida siguiente arranca limpia (sin elites de más).

  python3 scripts/ot/test-crucible.py --port 7275

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
Client, check, pos = _g.Client, _g.check, _g.pos

LEVER_CLIENT = (2772, 2773)                 # 1945 / 1946: la palanca cambia de lado al usarla
LEVERS = {"bronze": (601, 100, 0), "silver": (605, 100, 0), "gold": (609, 100, 0), "info": (600, 105, 0)}
PADS = {"bronze": "601 101 0", "silver": "604 101 0", "gold": "608 101 0"}
HALL = "605 104 0"


def has(client, since, needle):
    return any(needle in t for _c, t in client.messages(since))


def pull(client, lever, flipped):
    """Usa la palanca; flipped dice de qué lado está (cambia de id con cada uso que entra)."""
    client.use(pos(*LEVERS[lever]), LEVER_CLIENT[flipped[lever]], 1, 0)
    client.read(0.8)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=7275)
    a = ap.parse_args()
    fails = 0
    flipped = {k: 0 for k in LEVERS}

    gm = Client(a.port, 111112, "Bot GM")
    knight = Client(a.port, 111111, "Bot Knight")
    mage = Client(a.port, 111111, "Bot Mage")
    pally = Client(a.port, 111111, "Bot Pally")
    for c in (gm, knight, mage, pally):
        c.read(0.5)

    def send(who, where):
        gm.say(f"/send {who}, {where}")
        gm.read(0.4)

    def fight(lever, door_label):
        """Desde que se tiró la palanca: cuenta, pelea, el GM borra los monstruos. Devuelve la marca."""
        k0 = knight.mark()
        knight.read(6.5)
        nonlocal fails
        fails += not check(has(knight, k0, "FIGHT!"), f"{door_label}: aparecen los monstruos tras la cuenta")
        gm.say("/goto Bot Knight")
        gm.read(0.5)
        k1 = knight.mark()
        gm.say("/killmonsters")
        gm.read(2.5)
        knight.read(0.5)
        return k1

    print("1. Varkon")
    k0 = knight.mark()
    knight.say("hi")
    knight.read(1.0)
    said = knight.buf[k0:].decode("latin-1")        # lo que dice un NPC llega como habla (0xAA), no como 0xB4
    fails += not check("Clear Bronze, then Silver, then Gold" in said, "Varkon explica la escalera")
    knight.say("bye")
    knight.read(0.5)

    print("2. Silver cerrada sin Bronze")
    send("Bot Pally", "605 101 0")
    p0 = pally.mark()
    pull(pally, "silver", flipped)
    fails += not check(has(pally, p0, "opens after you clear the Bronze gate"), "Silver pide Bronze")

    print("3. Bronze en grupo (Knight tira, Mage en la plataforma)")
    send("Bot Knight", PADS["bronze"])
    send("Bot Mage", "600 102 0")
    k0, m0 = knight.mark(), mage.mark()
    pull(knight, "bronze", flipped)
    flipped["bronze"] ^= 1
    mage.read(0.3)
    fails += not check(has(knight, k0, "Crucible Bronze gate"), "el que tira entra")
    fails += not check(has(mage, m0, "Crucible Bronze gate"), "el de la plataforma entra con él")
    fails += not check(has(knight, k0, "arrive in 5 s"), "aviso de la cuenta regresiva")
    k1 = fight("bronze", "Bronze")
    mage.read(0.3)
    fails += not check(has(knight, k1, "Crucible Bronze cleared! Reward"), "premio Bronze al que tiró")
    fails += not check(has(mage, m0, "Crucible Bronze cleared! Reward"), "premio Bronze al del grupo")
    fails += not check(has(knight, k1, "Silver gate is now open"), "avisa que se abrió Silver")

    print("4. Silver: el Pally (sin Bronze) se queda en la sala")
    for who in ("Bot Knight", "Bot Mage"):
        send(who, HALL)
    gm.say(f"/goto {HALL}")
    gm.read(4.0)                                  # Varkon vacía la arena
    send("Bot Knight", PADS["silver"])
    k0, p0 = knight.mark(), pally.mark()
    pull(knight, "silver", flipped)
    flipped["silver"] ^= 1
    pally.read(0.3)
    fails += not check(has(knight, k0, "Crucible Silver gate"), "Knight entra a Silver")
    fails += not check(has(pally, p0, "You stay behind"), "el Pally se queda: le falta Bronze")
    k1 = fight("silver", "Silver")
    fails += not check(has(knight, k1, "Crucible Silver cleared! Reward"), "premio Silver")

    print("5. Gold: jefe una vez por día")
    send("Bot Knight", HALL)
    gm.say(f"/goto {HALL}")
    gm.read(4.0)
    send("Bot Knight", PADS["gold"])
    k0 = knight.mark()
    pull(knight, "gold", flipped)
    flipped["gold"] ^= 1
    fails += not check(has(knight, k0, "Crucible Gold gate"), "Knight entra a Gold")
    k1 = fight("gold", "Gold")
    fails += not check(has(knight, k1, "has fallen! The Gold boss is done"), "aviso del jefe caído")
    fails += not check(has(knight, k1, "You conquered the Crucible today"), "premio Gold")
    send("Bot Knight", HALL)
    gm.say(f"/goto {HALL}")
    gm.read(4.0)
    send("Bot Knight", PADS["gold"])
    k0 = knight.mark()
    pull(knight, "gold", flipped)
    fails += not check(has(knight, k0, "already defeated today's Gold boss"), "Gold cerrada el resto del día")
    send("Bot Knight", "601 105 0")
    k0 = knight.mark()
    pull(knight, "info", flipped)
    flipped["info"] ^= 1
    fails += not check(has(knight, k0, "Bronze: cleared. Silver: cleared. Gold: cleared."), "palanca de info: progreso")

    print("6. Entrar sin palanca")
    m0 = mage.mark()
    send("Bot Mage", "620 106 0")
    mage.read(2.0)
    fails += not check(has(mage, m0, "Enter the Crucible arenas with the levers"), "relog adentro: vuelve a la sala")

    print("7. Arena abandonada")
    send("Bot Mage", HALL)
    send("Bot Knight", PADS["bronze"])
    pull(knight, "bronze", flipped)
    flipped["bronze"] ^= 1
    knight.read(6.5)
    send("Bot Knight", HALL)                      # se va a mitad de la pelea
    knight.read(4.0)
    send("Bot Knight", PADS["bronze"])
    k0 = knight.mark()
    pull(knight, "bronze", flipped)
    flipped["bronze"] ^= 1
    knight.read(6.5)
    fails += not check(has(knight, k0, "Crucible Bronze gate"), "la arena abandonada quedó libre")
    fails += not check(has(knight, k0, "| 4 enemies left"), "corrida limpia: elite + 3 (no se acumulan)")
    fails += not check(not has(knight, k0, "| 5 enemies left") and not has(knight, k0, "| 8 enemies left"),
                       "nada sobrante de la corrida anterior")
    send("Bot Knight", HALL)

    print("FALLAS:", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
