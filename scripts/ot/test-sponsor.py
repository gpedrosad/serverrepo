#!/usr/bin/env python3
"""Prueba del padrinazgo (docs/gameplay/PADRINAZGO.md) en un servidor de PRUEBA con bots (make-test-bots.py:
Bot Knight nivel 60 y Bot Mage nivel 20 en la cuenta 111111, Bot Novato nivel 8 en la 111113, Bot GM).

  1. reglas: padrino de nivel < 30, misma cuenta;
  2. pedir y aceptar: el ahijado recibe la caja de bienvenida;
  3. hito 20 con el padrino conectado: premio para los dos y aviso a todos;
  4. hito 35 con el padrino desconectado: su premio le llega al entrar;
  5. bajar y volver a subir no repite premios; !padrino muestra el estado.

  python3 scripts/ot/test-sponsor.py --port 7275

No apuntarlo al servidor donde se juega.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("gifts", Path(__file__).with_name("test-level-gifts.py"))
_g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_g)
Client, check = _g.Client, _g.check


def texts(client, since):
    return [t for _c, t in client.messages(since)]


def has(client, since, needle):
    return any(needle in t for t in texts(client, since))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=7275)
    a = ap.parse_args()
    fails = 0

    gm = Client(a.port, 111112, "Bot GM")
    knight = Client(a.port, 111111, "Bot Knight")
    novato = Client(a.port, 111113, "Bot Novato")
    for c in (gm, knight, novato):
        c.read(0.5)
    fails += not check("!padrino Nombre" in novato.buf.decode("latin-1"), "al entrar, el nuevo ve el aviso de !padrino")

    print("1. Reglas")
    n0 = novato.mark()
    novato.say("!padrino Bot Mage")              # Bot Mage no está conectado
    novato.read(0.8)
    fails += not check(has(novato, n0, "no esta conectado"), "padrino desconectado")
    mage = Client(a.port, 111111, "Bot Mage")
    mage.read(0.5)
    n0 = novato.mark()
    novato.say("!padrino Bot Mage")              # nivel 20
    novato.read(0.8)
    fails += not check(has(novato, n0, "nivel 30 o mas"), "padrino de nivel 20: rechazado")
    gm.say("/nivel 10 Bot Mage")
    gm.read(0.5)
    m0 = mage.mark()
    mage.say("!padrino Bot Knight")              # misma cuenta
    mage.read(0.8)
    fails += not check(has(mage, m0, "tu propio padrino"), "misma cuenta: rechazado")

    print("2. Pedir y aceptar")
    n0, k0 = novato.mark(), knight.mark()
    novato.say("!padrino Bot Knight")
    novato.read(0.5)
    knight.read(0.5)
    fails += not check(has(knight, k0, "quiere que seas su padrino"), "el padrino recibe el pedido")
    knight.say("!padrino aceptar Bot Novato")
    knight.read(0.5)
    novato.read(0.8)
    fails += not check(has(novato, n0, "Bot Knight es tu padrino"), "el ahijado se entera")
    fails += not check(has(knight, k0, "Ahora eres padrino de Bot Novato"), "el padrino se entera")
    fails += not check(has(novato, n0, "novice gift"), "caja de bienvenida")
    n0 = novato.mark()
    novato.say("!padrino Bot Knight")
    novato.read(0.6)
    fails += not check(has(novato, n0, "Ya tienes padrino"), "no se puede pedir otro")

    print("3. Hito 20 con el padrino conectado")
    n0, k0, g0 = novato.mark(), knight.mark(), gm.mark()
    gm.say("/nivel 21 Bot Novato")
    novato.read(1.0)
    knight.read(0.5)
    gm.read(0.5)
    fails += not check(has(novato, n0, "llegaste a nivel 20. Recibes 2000 gp"), "premio del ahijado")
    fails += not check(has(knight, k0, "llego a nivel 20. Recibes 5000 gp"), "premio del padrino")
    fails += not check(has(gm, g0, "ahijado de Bot Knight, llego a nivel 20"), "aviso a todos")

    print("4. Hito 35 con el padrino desconectado")
    gm.say("/kick Bot Knight")                   # en el muelle suele quedar "en pelea" y no deja salir
    gm.read(1.0)
    knight.sock.close()
    n0 = novato.mark()
    gm.say("/nivel 36 Bot Novato")
    novato.read(1.0)
    fails += not check(has(novato, n0, "llegaste a nivel 35"), "premio del ahijado")
    knight = Client(a.port, 111111, "Bot Knight")
    knight.read(1.0)
    fails += not check(has(knight, 0, "llego a nivel 35. Recibes 10000 gp"), "el padrino lo cobra al entrar")

    print("5. Sin repetir y estado")
    n0, k0 = novato.mark(), knight.mark()
    gm.say("/nivel 30 Bot Novato")
    gm.read(0.3)
    gm.say("/nivel 37 Bot Novato")
    novato.read(1.0)
    knight.read(0.5)
    fails += not check(not has(novato, n0, "Padrinazgo:") and not has(knight, k0, "Padrinazgo:"),
                       "bajar y volver a subir: sin premios")
    k0 = knight.mark()
    knight.say("!padrino")
    knight.read(0.6)
    status = [t for t in texts(knight, k0) if "ahijados" in t]
    print("         " + (status[0] if status else "(sin estado)"))
    fails += not check(bool(status) and "Bot Novato (nivel 37, premio en 50)" in status[0], "estado del padrino")
    n0 = novato.mark()
    novato.say("!padrino")
    novato.read(0.6)
    mine = [t for t in texts(novato, n0) if "Tu padrino" in t]
    print("         " + (mine[0] if mine else "(sin estado)"))
    fails += not check(bool(mine) and "nivel 50" in mine[0], "estado del ahijado")

    print("RESULTADO:", "OK" if not fails else f"{fails} falla(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
