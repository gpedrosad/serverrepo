#!/usr/bin/env python3
"""Genera `scripts/map/quest-routes.json`: rutas desde el depot a todas las quests.

Reutiliza el buscador de `build-routes.py` (casillas, escaleras, rampas, agujeros, puertas y
teleports). Para las quests en salas cerradas, la ruta termina en la entrada/palanca y la nota
explica que el cofre está adentro. Las quests de barco/portal incluyen el salto.

Uso:
  python3 scripts/map/build-quest-routes.py
  python3 scripts/map/build-quest-routes.py --map OTRO.otbm
"""
from __future__ import annotations

import collections
import importlib.util
import json
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "quest-routes.json"

_spec = importlib.util.spec_from_file_location("routes", HERE / "build-routes.py")
br = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(br)


def reach_all(start):
    q = collections.deque([start])
    seen = {start}
    while q:
        x, y, z = q.popleft()
        for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z)):
            if n in br.walk and n not in seen:
                seen.add(n)
                q.append(n)
        for n in br.vert.get((x, y, z), ()):
            if n not in seen:
                seen.add(n)
                q.append(n)
    return seen


def nearest(cands, target):
    same = [p for p in cands if p[2] == target[2]]
    if same:
        return min(same, key=lambda p: abs(p[0] - target[0]) + abs(p[1] - target[1]))
    return min(cands, key=lambda p: abs(p[0] - target[0]) + abs(p[1] - target[1]))


def resolve_walk(target, reachable):
    return target if target in reachable else nearest(reachable, target)


def quest_walk(qid, name, target, label, note="", steps=None):
    actual = resolve_walk(target, REACH)
    steps = steps or ["Sal del depot y sigue las flechas rojas.",
                      f"El camino termina en {label}."]
    route = br.route_walk(f"quest-{qid}", name, actual, steps)
    for m in route["markers"]:
        if m["kind"] == "target":
            m["label"] = label
    route.update({"quest": qid, "note": note, "target_label": label})
    return route


def quest_jump(qid, name, kind, origin, landing, target, label, note="", steps=None,
               origin_label=None, landing_label=None):
    reachable = REACH_LANDING.get(landing)
    if reachable is None:
        reachable = REACH_LANDING[landing] = reach_all(landing)
    actual = resolve_walk(target, reachable) if target else None
    steps = steps or ["Sal del depot y sigue las flechas hasta el portal o barco.",
                      "Entra y sigue el camino marcado.",
                      f"El camino termina en {label}."]
    route = br.route_jump(f"quest-{qid}", name, kind, origin, landing, actual, steps,
                          origin_label or ("Portal" if kind == "portal" else "Fargum (barco)"),
                          landing_label or "Llegada")
    for m in route["markers"]:
        if m["kind"] == "target":
            m["label"] = label
    route.update({"quest": qid, "note": note, "target_label": label})
    return route


# --- definiciones --------------------------------------------------------------------------------
# target = casilla caminable (cofre, entrada o palanca). label = lo que se marca en el mapa.
QUESTS = [
    ("annihilator", "Annihilator", "walk", (194, 118, 9), "Entrada del Annihilator",
     "La sala se abre con la palanca; los cofres están adentro."),
    ("pharaoh", "Pharaoh Quest", "walk", (205, 165, 9), "Tumbas del desierto",
     "Los cofres están dentro de las tumbas."),
    ("imperial", "Castillo Imperial", "walk", (96, 28, 3), "Tesorería del castillo",
     "La tesorería está detrás del trono, en el último piso."),
    ("hell", "Hell Quest", "boat", (172, 66, 7), (345, 211, 7), (343, 136, 9),
     "Cámara de la Elección", "El barco te deja en el sur de la isla; sigue el camino al norte."),
    ("gauntlet", "TP Gauntlet", "boat", (172, 66, 7), (452, 41, 7), (451, 77, 7),
     "Sala final del Gauntlet", "El barco te deja en la entrada; sigue las salas hasta el final."),
    ("frozen-lumberjack", "Isla del Hielo: cofre del leñador", "boat", (172, 66, 7),
     (395, 104, 7), (373, 96, 7), "Cofre del leñador",
     "El cofre está en el desvío del bosque, al oeste del sendero."),
    ("frozen-yeti", "Isla del Hielo: tesoro del Yeti", "boat", (172, 66, 7),
     (395, 104, 7), (368, 63, 7), "Islote del Yeti",
     "El cofre está en el islote, en el desvío del lago."),
    ("frozen-lair", "Isla del Hielo: guarida", "boat", (172, 66, 7),
     (395, 104, 7), (393, 16, 9), "Guarida de la Isla del Hielo",
     "La guarida está al final del sendero, después de las grutas."),
    ("desert-lizard", "Desierto: Templo de los lagartos", "walk", (241, 78, 7),
     "Templo de los lagartos", "El cofre está contra la pared del fondo del templo."),
    ("desert-bone", "Desierto: Campo de huesos", "walk", (258, 114, 7),
     "Campo de huesos", "El cofre está al este de los obeliscos."),
    ("fire-cave", "Cueva de Fuego (3 cofres)", "walk", (87, 75, 8),
     "Palanca de la Cueva de Fuego", "La palanca abre la cueva; los cofres están abajo."),
    ("boh", "Boots of Haste", "walk", (128, 63, 6), "Torre de Boots of Haste",
     "El cofre está en la torre, junto a la entrada."),
    ("guardian-halberd", "Guardian Halberd", "walk", (138, 141, 6),
     "Campamento orco", "El cofre está dentro del campamento."),
    ("crusader-helmet", "Crusader Helmet", "walk", (196, 40, 7),
     "Costa de los piratas", "El cofre está en la costa, pasando la entrada."),
    ("lady-helmet", "Lady Helmet", "walk", (242, 21, 8), "Zona helada",
     "El cofre está en la zona helada."),
    ("steel-boots", "Steel Boots", "walk", (217, 73, 8), "Cueva de demonios",
     "El cofre está dentro de la cueva."),
    ("knight-legs", "Knight Legs", "walk", (88, 80, 8), "Cripta/dungeon",
     "El cofre está dentro de la cripta."),
    ("ancients-a", "Helmet of the Ancients (tumba)", "walk", (213, 140, 8),
     "Entrada de la tumba", "El cofre está dentro de la tumba."),
    ("ancients-b", "Helmet of the Ancients (cripta)", "walk", (232, 126, 9),
     "Cripta de los Ancients", "El cofre está dentro de la cripta."),
    ("shield-honour", "Shield of Honour", "walk", (213, 140, 8),
     "Entrada de la guarida de la hydra", "La guarida está al este; sigue el camino."),
    ("dark-shield", "Dark Shield (2 cofres)", "walk", (135, 38, 9),
     "Entrada del dungeon de minotauros", "Los cofres están dentro del dungeon."),
    ("giant-sword", "Giant Sword", "walk", (183, 117, 9), "Cueva de behemoths",
     "El cofre está dentro de la cueva."),
    ("bright-sword", "Bright Sword", "walk", (145, 135, 9), "Cripta",
     "El cofre está dentro de la cripta."),
    ("golden-armor", "Golden Armor", "walk", (162, 153, 9), "Fortaleza orca",
     "El cofre está dentro de la fortaleza."),
    ("amazon-shield", "Amazon Shield", "walk", (74, 93, 10), "Cueva de las amazonas",
     "El cofre está dentro de la cueva."),
    ("pvp-arena", "Arena PvP", "walk", (119, 35, 9), "Arena PvP",
     "La arena está al final del camino."),
    ("daily-task", "Daily Task (Huntmaster)", "walk", (138, 53, 6), "Huntmaster",
     "El Huntmaster está en el templo."),
    ("wave-arena", "Wave Arena", "portal", (166, 47, 7), (176, 403, 7), None,
     "Campamento de la Wave Arena", "El portal te deja en el campamento."),
    ("sand-clock", "Reloj de Arena", "portal", (168, 47, 7), (338, 395, 6), None,
     "Sala del Reloj", "El portal te deja en la sala."),
    ("crucible", "El Crisol", "portal", (164, 47, 7), (83, 85, 0), None,
     "Sala del Crisol", "El portal te deja en la sala de las tres puertas."),
]

REACH = None
REACH_LANDING = {}


def main() -> int:
    global REACH
    ap = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    ap.add_argument("--map", type=Path, default=br.MAP, help="OTBM a usar (por defecto test.otbm del repo)")
    args = ap.parse_args()
    br.MAP_PATH = args.map
    br.tiles = br.load_map()
    br.walk, br.vert = br.build_graph(br.tiles)
    REACH = reach_all(br.TEMPLE)
    print(f"mapa: {len(br.tiles)} casillas, {len(br.walk)} caminables, {len(REACH)} alcanzables desde el depot")

    routes = []
    for q in QUESTS:
        qid, name, kind = q[0], q[1], q[2]
        if kind == "walk":
            _, _, _, target, label, note = q
            routes.append(quest_walk(qid, name, target, label, note))
        else:
            _, _, _, origin, landing, target, label, note = q
            routes.append(quest_jump(qid, name, kind, origin, landing, target, label, note))

    OUT.write_text(json.dumps({"routes": routes}, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf-8")
    print(f"OK {OUT}: {len(routes)} quests")
    for r in routes:
        pts = sum(len(s["points"]) for s in r["segments"])
        print(f"  {r['quest']:20} {r['kind']:6} {pts:3} puntos  {len(r['jumps'])} saltos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
