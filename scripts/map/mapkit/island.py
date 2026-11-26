"""Receta "island": isla de pasto rodeada de agua, sendero de tierra con claros, bosque cerrado y un puerto.

Lo que sale de la ficha (`zones/<zona>.json`): caja, recorrido, anchos, claros, puerto y etapas.
Lo que decide jev (con fallback): qué tiene cada claro y qué monstruos van en cada etapa (ver build.py).
Todo lo demás es geometría con semilla: dos corridas con la misma semilla dan el mismo mapa.
"""
from __future__ import annotations

import math
import random

from . import (ALL8, CARD, Noise, Otb, blob, box_cells, chaikin, grow, neighbors_in, place_stages, polyline,
               reach, slices_by)

OPEN = {"w": (-1, 0), "e": (1, 0), "n": (0, -1), "s": (0, 1)}


def _sizes():
    import mapdata
    r = mapdata.Renderer()
    cache = {}

    def size(sid):
        if sid not in cache:
            e = r.entry(sid)
            cache[sid] = (e["w"], e["h"]) if e else (1, 1)
        return cache[sid]
    return size


def footprint(c, size):
    """Casillas que tapa un sprite de w x h anclado en `c` (se dibuja hacia arriba-izquierda)."""
    w, h = size
    return {(c[0] - dx, c[1] - dy) for dx in range(w) for dy in range(h)}


def build(spec: dict, theme, seed: int, decisions: dict, otb: Otb | None = None, world: dict | None = None) -> dict:
    otb = otb or Otb()
    size = _sizes()
    rng = random.Random(f"{spec['name']}-{seed}")
    nz = Noise(seed * 7919 + 13)
    allowed = box_cells(spec["land"])
    box = box_cells(spec["box"])
    lx0, ly0, lx1, ly1 = spec["land"]
    edge_nz = Noise(seed * 31 + 5)
    # el límite de la tierra con ruido: si no, la isla choca contra la caja y la costa sale recta
    allowed_shore = {c for c in allowed if min(c[0] - lx0, lx1 - c[0], c[1] - ly0, ly1 - c[1])
                     >= 4 * edge_nz.fbm(c[0] / 5, c[1] / 5, 2, 21)}
    coast, edge = theme.border("coast"), theme.border("trail_edge")

    # 1. sendero: el recorrido redondeado, con ancho y desvío que varían con ruido
    route = [tuple(p) for p in spec["route"]]
    ag = next((g for g in spec["glades"] if g.get("role") in ("harbor", "portal") and "center" in g), None)
    if ag and tuple(ag["center"]) != route[0]:
        route.insert(0, tuple(ag["center"]))          # el sendero sale de la llegada (puerto o portal)
    pts = chaikin(route, 2)
    samples = polyline(pts, 0.5)
    total = samples[-1][2]
    w0, w1 = spec["trail_width"]
    trail = set()
    for i, (x, y, run) in enumerate(samples):
        j = min(i + 1, len(samples) - 1)
        tx, ty = samples[j][0] - samples[max(i - 1, 0)][0], samples[j][1] - samples[max(i - 1, 0)][1]
        n = math.hypot(tx, ty) or 1.0
        off = (nz.fbm(run / 11, 3.3, 2, 2) - 0.5) * 3.0
        cx, cy = x - ty / n * off, y + tx / n * off
        r = (w0 + (w1 - w0) * nz.fbm(run / 8, 1.7, 2, 1)) / 2
        for gx in range(int(cx - r) - 1, int(cx + r) + 2):
            for gy in range(int(cy - r) - 1, int(cy + r) + 2):
                if (gx + 0.5 - cx - 0.5) ** 2 + (gy + 0.5 - cy - 0.5) ** 2 <= r * r:
                    trail.add((gx, gy))

    def at(frac):
        k = min(range(len(samples)), key=lambda i: abs(samples[i][2] - frac * total))
        return round(samples[k][0]), round(samples[k][1])

    # 2. claros (el primero es el puerto si la ficha lo dice)
    glades = []
    for k, g in enumerate(spec["glades"]):
        if "center" in g:
            c = tuple(g["center"])
        else:
            # el claro va AL COSTADO del sendero (no encima): del lado con más lugar libre
            c0 = at(g["at"])
            k0 = min(range(len(samples)), key=lambda i: abs(samples[i][2] - g["at"] * total))
            a, b = samples[max(k0 - 2, 0)], samples[min(k0 + 2, len(samples) - 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            n = math.hypot(tx, ty) or 1.0
            off = g.get("offset", max(g["r"]) - 1)
            best = None
            for sgn in (1, -1):
                cand = (round(c0[0] - ty / n * off * sgn), round(c0[1] + tx / n * off * sgn))
                room = min(math.hypot(cand[0] - x, cand[1] - y) for x, y, r in samples
                           if abs(r - g["at"] * total) > 12)
                inside = cand in allowed
                if best is None or (inside, room) > best[0]:
                    best = ((inside, room), cand)
            c = best[1] if g.get("role") != "end" else c0
        cells = blob(c, g["r"][0], g["r"][1], nz, 0.35, o=40 + k)
        glades.append({"center": c, "cells": cells, "role": g.get("role", "glade"), "spec": g})
    core = set(trail) | {c for g in glades for c in g["cells"]}
    margin = spec.get("forest", [3, 6])[0] + 2
    inner = {c for c in allowed if all((c[0] + dx, c[1] + dy) in allowed for dx in (-margin, margin)
                                       for dy in (-margin, margin))}
    clipped = trail - inner
    trail &= inner
    trail = edge.settle(trail, inner)
    tstart = min(trail, key=lambda c: math.hypot(c[0] - samples[0][0], c[1] - samples[0][1]))
    tend = min(trail, key=lambda c: math.hypot(c[0] - samples[-1][0], c[1] - samples[-1][1]))
    if tend not in reach(trail, tstart, ALL8):
        raise RuntimeError(f"sendero cortado (recortadas por el borde: {sorted(clipped)[:3]}). Si no hay recortadas, el sendero es "
                           "demasiado angosto (trail_width mínimo 2,2: los tramos de 1 casilla se borran al cerrar bordes); "
                           "alejar el recorrido del borde")
    for g in glades:
        g["cells"] &= inner
    # ensanches: rincones de pasto pegados al sendero (que no sea un caño de ancho fijo)
    pockets = {c for c in grow(trail, 2) - trail if c in inner and nz.fbm(c[0] / 5, c[1] / 5, 2, 7) > 0.58}
    walk = grow(trail, 1) | pockets | {c for g in glades for c in g["cells"]}
    walk &= inner

    # 3. tierra: bosque de profundidad variable alrededor de lo caminable; el puerto queda abierto al agua
    f0, f1 = spec.get("forest", [3, 6])
    harbor = next((g for g in glades if g["role"] == "harbor"), None)
    portal = next((g for g in glades if g["role"] == "portal"), None)
    open_cells = set()
    if harbor:
        dx, dy = OPEN[spec["harbor"]["open"]]
        for c in harbor["cells"]:
            for k in range(2, 30):
                open_cells.add((c[0] + dx * k, c[1] + dy * k))
        open_cells -= walk
        open_cells -= grow(walk - harbor["cells"], 3)
    dist = {c: 0 for c in walk}
    frontier = list(walk)
    for d in range(1, f1 + 1):
        nxt = []
        for (x, y) in frontier:
            for ddx, ddy in ALL8:
                n = (x + ddx, y + ddy)
                if n in allowed and n not in dist:
                    dist[n] = d
                    nxt.append(n)
        frontier = nxt
    land = {c for c, d in dist.items()
            if (c in allowed_shore or d <= 1) and d <= f0 + (f1 - f0) * nz.fbm(c[0] / 6, c[1] / 6, 3, 3) and (c not in open_cells or d <= 1)}
    # sin lagunas encerradas: el agua que no toca el borde de la caja pasa a ser tierra
    sea = box - land
    outer = {c for c in sea if c[0] in (min(x for x, _ in box), max(x for x, _ in box))
             or c[1] in (min(y for _, y in box), max(y for _, y in box))}
    seen, todo = set(outer), list(outer)
    while todo:
        x, y = todo.pop()
        for ddx, ddy in CARD:
            n = (x + ddx, y + ddy)
            if n in sea and n not in seen:
                seen.add(n)
                todo.append(n)
    land |= (sea - seen) & allowed
    keep = grow(walk, 1)
    water = coast.settle(box - land, box - keep)
    for _ in range(20):
        land = box - water
        shore = {c for c in land if neighbors_in(water, *c) & {"n", "s", "e", "w", "ne", "nw", "se", "sw"}}
        bad = set()
        for c in shore:
            pcs = coast.pieces(neighbors_in(water, *c))
            if pcs is None or len(pcs) != 1:
                bad.add(c)
        if not bad:
            break
        if bad & keep:
            raise RuntimeError(f"costa imposible junto a lo caminable: {sorted(bad & keep)[:4]}")
        water = coast.settle(water | bad, box - keep)
    else:
        raise RuntimeError("la costa no converge")
    land = box - water
    shore = {c for c in land if neighbors_in(water, *c)}
    if shore & walk:
        raise RuntimeError(f"costa en lo caminable: {sorted(shore & walk)[:4]}")

    # 4. suelos
    tiles = {}
    for c in box:
        if c in water:
            tiles[c] = [theme["water"]]
        elif c in shore:
            tiles[c] = [theme["coast"]["ground"], coast.piece_at(water, c)]
        elif c in trail:
            tiles[c] = [theme["trail"]]
        else:
            p = edge.piece_at(trail, c)
            tiles[c] = [p if p else theme["grass"]]

    # 5. bosque. Solo la franja pegada a lo caminable (`hedge`) tiene que bloquear, cerrada en las 8
    #    direcciones: así no hay atajos. Más adentro, donde nadie llega, pasto con árboles sueltos (un bosque
    #    macizo de punta a punta se ve como una pared verde; pedido de Gonzalo, 26 nov 2026).
    forest = land - walk - shore
    hedge = forest & grow(walk, 1)
    dens = spec.get("tree_density", {"hedge": 0.75, "inner": 0.5, "bush": 0.15})
    for c in sorted(hedge):
        tiles[c].append(rng.choice(theme["blockers_1x1"]))
    # segunda fila irregular de arbustos (que el borde no sea un cerco recto)
    for c in sorted(forest & grow(walk, 2) - hedge):
        if nz.fbm(c[0] / 3, c[1] / 3, 2, 11) > 0.5:
            tiles[c].append(rng.choice(theme["blockers_1x1"]))
    canopy = set()
    for c in sorted(forest, key=lambda c: (rng.random(), c)):
        if rng.random() > (dens["hedge"] if c in hedge else dens["inner"]):
            continue
        tree = rng.choice(theme["trees_rare"]) if rng.random() < 0.03 else rng.choice(theme["trees_2x2"])
        foot = footprint(c, size(tree))
        if foot <= forest and not (foot & canopy):
            if len(tiles[c]) > 1:
                tiles[c][-1] = tree
            else:
                tiles[c].append(tree)
            canopy |= foot
    for c in sorted(forest - hedge - canopy):
        if len(tiles[c]) > 1:
            continue
        r = rng.random()
        if r < dens["bush"]:
            tiles[c].append(rng.choice(theme["blockers_1x1"]))
        elif r < dens["bush"] + 0.04:
            tiles[c].append(rng.choice(theme["flowers"]))

    # 6. llegada: puerto (Nimral + bote en el agua) o portal (teleport desde el templo), y cartel
    info = {"landing": None, "npc": None, "sign": None, "boat": {}, "return": None, "props": {}}
    if harbor:
        dx, dy = OPEN[spec["harbor"]["open"]]
        hc = harbor["cells"] & walk
        landing = max(sorted(hc - trail), key=lambda c: c[0] * dx + c[1] * dy - 0.3 * abs(
            (c[1] - harbor["center"][1]) if dx else (c[0] - harbor["center"][0])))
        info["landing"] = landing
        npc = next((n for n in ((landing[0] + dy, landing[1] + dx), (landing[0] - dy, landing[1] - dx),
                                (landing[0] - dx, landing[1] - dy)) if n in walk), None)
        info["npc"] = npc
        # bote: 5 piezas horizontales (oeste -> este) sobre agua, a 2 casillas de la costa
        boat = None
        for k in range(2, 12):
            bx, by = landing[0] + dx * (k + (4 if dx < 0 else 0)), landing[1] + dy * k
            if dx == 0:
                bx = landing[0] - 2
            cells = [(bx + i, by) for i in range(5)]
            if all(c in water and not neighbors_in(land, *c) for c in cells):
                boat = cells
                break
        if boat is None:
            raise RuntimeError("no entra el bote frente al puerto")
        for c, it in zip(boat, theme["boat_h"]):
            tiles[c].append(it)
            info["boat"][c] = it
    if portal:
        # llegada = casilla caminable del claro del portal fuera del sendero; vuelta = vecina fuera del sendero
        pc = tuple(portal["center"])
        cells = sorted(portal["cells"] & walk, key=lambda c: abs(c[0] - pc[0]) + abs(c[1] - pc[1]))
        if not cells:
            raise RuntimeError("el claro del portal quedó sin casillas caminables")
        landing = next((c for c in cells if c not in trail), cells[0])
        info["landing"] = landing
        ret = next((n for n in ((landing[0] + 1, landing[1]), (landing[0] - 1, landing[1]),
                                (landing[0], landing[1] + 1), (landing[0], landing[1] - 1))
                    if n in walk and n not in trail), None)
        if ret is None:
            raise RuntimeError("no hay casilla de vuelta junto a la llegada del portal")
        info["return"] = ret
    if info["landing"]:
        for c in sorted(forest, key=lambda c: abs(c[0] - info["landing"][0]) + abs(c[1] - info["landing"][1])):
            if c in canopy or not (neighbors_in(walk, *c) & {"n", "s", "e", "w"}):
                continue
            if abs(c[0] - info["landing"][0]) + abs(c[1] - info["landing"][1]) > 4:
                break
            tiles[c][-1] = theme["sign"]
            info["sign"] = c
            break
        if info["sign"] is None:
            raise RuntimeError("no hay borde de bosque para el cartel de la llegada")

    # 7. claros: lo que decidió jev (o el fallback) — piso suelto y bloqueos en el borde sin cortar el paso
    reserved = {info["landing"], info["npc"], info["return"]} | (grow({info["landing"]}, 2) if info["landing"] else set())
    start = info["landing"] or next(iter(sorted(trail)))
    base = len(reach(walk, start))
    for k, g in enumerate(glades):
        kind = decisions.get("glades", {}).get(str(k)) or g["spec"].get("props")
        if not kind or g["role"] in ("harbor", "portal"):
            continue
        prop = theme["props"][kind]
        info["props"][str(k)] = kind
        cells = sorted(g["cells"] & walk)
        if prop.get("center") and g["center"] in walk and g["center"] not in reserved:
            tiles[g["center"]].append(theme[prop["center"]])
            reserved.add(g["center"])
        for c in cells:
            if c in reserved or len(tiles[c]) > 1:
                continue
            border = 8 - len(neighbors_in(walk, *c))
            if border >= 2 and rng.random() < prop["edge_rate"]:
                item = rng.choice(theme[rng.choice(prop["edge"])])
                foot = footprint(c, size(item)) - {c}
                if foot & walk or c in trail:
                    continue
                walk.discard(c)
                if len(reach(walk, start)) != base - 1:
                    walk.add(c)
                    continue
                base -= 1
                tiles[c].append(item)
            elif border < 2 and rng.random() < prop["floor_rate"]:
                tiles[c].append(rng.choice(theme[rng.choice(prop["floor"])]))
    # 8. flores y hongos sueltos en el pasto del borde del sendero
    for c in sorted(walk - trail):
        if c not in reserved and len(tiles[c]) == 1 and rng.random() < 0.035:
            tiles[c].append(rng.choice(theme["flowers"] + theme["mushrooms"]))

    walk = {c for c in walk if otb.walkable(tiles[c])}
    d = reach(walk, start)
    lost = walk - set(d)
    for c in lost:                      # bolsillos sueltos: bosque
        tiles[c].append(rng.choice(theme["blockers_1x1"]))
    walk -= lost
    info["lost"] = len(lost)

    # 9. monstruos por etapas a lo largo del recorrido caminado
    z = spec["z"]
    stages = decisions.get("stages") or spec["stages"]
    avoid = set(reserved)
    if info["landing"]:
        clear = spec.get("harbor", {}).get("clear", 8) if harbor else spec.get("portal", {}).get("clear", 6)
        avoid |= grow({info["landing"]}, clear)
    avoid |= {c for c in walk if len(tiles[c]) > 1}
    srng = random.Random(f"{spec['name']}-spawns-{seed}")
    spawns = place_stages(stages, slices_by(walk - avoid, d.__getitem__, len(stages)), walk, avoid, z, srng)

    return {"tiles": tiles, "walk": walk, "dist": d, "trail": trail, "shore": shore, "water": water,
            "land": land, "forest": forest, "glades": glades, "spawns": spawns, "info": info,
            "samples": samples, "seed": seed, "stages": stages}
