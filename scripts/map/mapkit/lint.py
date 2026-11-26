"""Lint numérico de una zona: errores (no se escribe) y medidas de calidad (puntaje para elegir semilla).

Errores (cualquiera descarta la semilla):
  void          casillas sin tile a la vista (±9, ±7) de algo caminable
  unreachable   caminable que no se alcanza desde la entrada
  border        pieza de borde (costa, tierra, pared de cueva) que falta o no es la única válida
  coast_walk    costa (bloquea) en una casilla que debería ser caminable
  big_cover     sprite de 2x2 cuyo dibujo tapa una casilla caminable (tapa al jugador; salvo `big_ok` del tema)
  roof          cueva: casilla caminable sin nada arriba (se ven los pisos de arriba)
  cut           el recorrido quedó cortado (más del 2 % de lo caminable no se alcanza y se tapó)
  leak          casilla libre pegada a lo caminable (deja salir del recorrido: atajo por el bosque)
  loose         decoración que se levanta o se empuja (pickupable / moveable)
  spawn         spawn fuera de lo caminable, repetido o a menos de 6 de la llegada
  shortcut      el recorrido se puede cortar: un punto del recorrido queda a menos del 70 % de su distancia
Medidas:
  walk, monsters, density (casillas por monstruo), path (pasos hasta el fondo), narrow (% caminable de 1 de
  ancho), straight_coast (% de costa en tramos rectos de 7+), tree_cover (% del bosque con árbol 2x2)
"""
from __future__ import annotations

from . import VIEW, Otb, grow, neighbors_in


def lint(plan: dict, spec: dict, theme, existing: dict, otb: Otb, size) -> dict:
    tiles, walk, dist = plan["tiles"], plan["walk"], plan["dist"]
    z = spec["z"]
    errs = {}

    def err(k, c):
        errs.setdefault(k, []).append(c)

    have = set(tiles) | {(x, y) for (x, y, zz) in existing if zz == z}
    for (x, y) in walk:
        for dx in range(-VIEW[0], VIEW[0] + 1):
            for dy in range(-VIEW[1], VIEW[1] + 1):
                if (x + dx, y + dy) not in have:
                    err("void", (x + dx, y + dy))
    start = plan["info"]["landing"] or min(walk)
    for c in walk - set(dist):
        err("unreachable", c)
    # bordes: toda casilla pegada a la forma (agua, sendero, piso de cueva) lleva SU única pieza
    for key, shape in plan.get("borders") or [("coast", plan["water"]), ("trail_edge", plan["trail"])]:
        b = theme.border(key)
        for c in grow(shape, 1) - shape:
            if c not in tiles:
                continue
            want = b.pieces(neighbors_in(shape, *c))
            if not want or len(want) != 1 or want[0] not in tiles[c]:
                err("border", c)
    coast_ground = theme.get("coast", {}).get("ground")
    big_ok = set(theme.get("big_ok", ()))
    for c, ids in tiles.items():
        if coast_ground is not None and ids[0] == coast_ground and c in walk:
            err("coast_walk", c)
        for i in ids[1:]:
            w, h = size(i)
            if (w > 1 or h > 1) and i not in big_ok and any((c[0] - a, c[1] - b) in walk
                                        for a in range(w) for b in range(h) if (a, b) != (0, 0)):
                err("big_cover", c)
            if otb.loose(i):
                err("loose", c)
    for c in plan["info"].get("roof_missing", ()):
        err("roof", c)
    lost = plan["info"].get("lost", 0)
    if lost > 0.02 * (len(walk) + lost):
        errs["cut"] = [f"{lost} casillas caminables quedaron sueltas"]
    for c in grow(walk, 1) - walk:
        if c in tiles and otb.walkable(tiles[c]):
            err("leak", c)
    seen = set()
    clear = spec["harbor"].get("clear", 8) if spec.get("harbor") else spec.get("clear", 6)
    near = {(start[0] + a, start[1] + b) for a in range(-clear, clear + 1) for b in range(-clear, clear + 1)}
    for _c, _z, mons in plan["spawns"]:
        for _n, p, _t in mons:
            if p not in walk or p in seen or p in near:
                err("spawn", p)
            seen.add(p)
    run = {}
    for x, y, r in plan["samples"]:
        c = (round(x), round(y))
        if c in dist:
            run[c] = r
    if run:
        r0 = min(run.values())
        d0 = dist[min(run, key=run.get)]
        for c, r in run.items():
            if r - r0 > 20 and dist[c] - d0 < 0.7 * (r - r0):
                err("shortcut", c)

    # medidas
    monsters = sum(len(m) for _c, _z, m in plan["spawns"])
    narrow = sum(1 for (x, y) in walk if ((x - 1, y) not in walk and (x + 1, y) not in walk)
                 or ((x, y - 1) not in walk and (x, y + 1) not in walk))
    shore = plan["shore"]
    straight = 0
    for (x, y) in shore:
        for dx, dy in ((1, 0), (0, 1)):
            n = 1
            for s in (1, -1):
                k = 1
                while (x + dx * k * s, y + dy * k * s) in shore and \
                        tiles[(x + dx * k * s, y + dy * k * s)][1:2] == tiles[(x, y)][1:2]:
                    n += 1
                    k += 1
            if n >= 7:
                straight += 1
                break
    forest = plan["forest"]
    trees = sum(1 for c in forest if any(size(i) != (1, 1) for i in tiles[c][1:]))
    m = {
        "walk": len(walk), "monsters": monsters, "spawns": len(plan["spawns"]),
        "density": round(len(walk) / max(1, monsters), 1),
        "path": max(dist.values()) if dist else 0,
        "narrow": round(100 * narrow / max(1, len(walk)), 1),
        "straight_coast": round(100 * straight / max(1, len(shore)), 1),
        "tree_cover": round(100 * trees / max(1, len(forest)), 1),
    }
    lo, hi = spec.get("density", [30, 45])
    score = 100.0
    score -= 1.5 * m["narrow"]
    score -= 0.6 * m["straight_coast"]
    score -= 2.0 * max(0, lo - m["density"], m["density"] - hi)
    if forest:
        score -= 0.3 * max(0, 8 - m["tree_cover"])
    m["score"] = round(score, 1)
    m["errors"] = {k: len(v) for k, v in errs.items()}
    m["examples"] = {k: v[:3] for k, v in errs.items()}
    return m
