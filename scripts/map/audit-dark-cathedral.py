#!/usr/bin/env python3
"""Auditoría de la Dark Cathedral sobre el test.otbm REAL (read-only, no el modelo del generador).

Qué comprueba (error = sale con código 1):
  1. Conectividad multi-piso: BFS 8-dir + escaleras (1385) + agujeros (432) desde la llegada.
     Ninguna casilla pisable puede quedar sin acceso.
  2. Pares escalera/agujero: cada 432 tiene su 1385 en (x, y, z+1) y las cuatro llegadas
     (caer x,y+1 / subir x,y-1 de cada lado) son piso libre.
  3. Cueva (pisos 351/352/355, paredes 356-367): cada pared con la pieza que toca por vecinos
     (pieces_for), ninguna roca de 1 casilla entre dos pisos (pelada, sin pieza posible) y todo
     el piso alcanzable desde la boca.
  4. Vacío a la vista en el MISMO piso: la media pantalla (8x6) de cada pisable tiene tile dentro
     de la caja. Ojo: check-upper-view.py sólo mira el piso de arriba; esto se ve negro.
  5. Spawns de test-spawn.xml dentro de la caja sobre piso pisable.
  6. Pilas raras: casillas sin ground, con 2+ grounds o con más de 2 ítems.
  7. Huesos de dragón cortados (3122-3127, 2247): partes del esqueleto grande, sueltas se ven mal.

Informativo (no falla): decoración bloqueante en mitad de un paso (vecinos pisables en ambos
ejes — los marcos de piedra de los agujeros van a aparecer, es a propósito) y, con --cuellos,
las casillas cuyo remate desconecta el piso (las puertas de 1 casilla son diseño, no error).

  python3 scripts/map/audit-dark-cathedral.py
  python3 scripts/map/audit-dark-cathedral.py --box 118 284 177 353 --z 7 8 9 --cuellos
Doc: docs/items-and-map/DARK_CATHEDRAL.md (sección "Revisión de patrones y pasos trabados").
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import xml.etree.ElementTree as ET
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kb"))
from mapdata import DIRS, REPO, load_tiles  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "north_pass", Path(__file__).resolve().parent / "generate-north-pass.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)

ALL8, Blocking, reach = NP.ALL8, NP.Blocking, NP.reach
neighbors_in, pieces_for = NP.neighbors_in, NP.pieces_for
WALL_SIDE, WALL_CORNER, WALL_INNER = NP.WALL_SIDE, NP.WALL_CORNER, NP.WALL_INNER

CAVE_FLOOR = {351, 352, 355}
CAVE_WALL = set(range(356, 368))
STAIR_UP, HOLE, ROCK = 1385, 432, 101
DRAGON_PARTS = set(range(3122, 3128)) | {2247}
CARD = ((1, 0), (-1, 0), (0, 1), (0, -1))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--box", nargs=4, type=int, default=(85, 264, 183, 373),
                    help="x0 y0 x1 y1 (default: caja de la Dark Cathedral)")
    ap.add_argument("--z", nargs="+", type=int, default=(7, 8, 9), help="pisos a auditar")
    ap.add_argument("--arrival", default="148,335,7", help="x,y,z de la llegada (portal de la plaza)")
    ap.add_argument("--cave-floor", nargs="+", type=int, default=(154, 298),
                    help="boca de la cueva en el piso más profundo con cueva (x y)")
    ap.add_argument("--cuellos", action="store_true",
                    help="listar cuellos de botella (quitar la casilla desconecta piso; lento)")
    a = ap.parse_args()
    x0, y0, x1, y1 = a.box
    zs = tuple(a.z)
    ax, ay, az = (int(v) for v in a.arrival.split(","))
    errors: list[str] = []
    notes: list[str] = []

    bl = Blocking()
    allt = load_tiles()
    box = {k: v for k, v in allt.items() if x0 <= k[0] <= x1 and y0 <= k[1] <= y1 and k[2] in zs}
    otb = bl.otb

    def it_at(x, y, z):
        return box.get((x, y, z), [])

    def walkable(x, y, z):
        return bl.walkable(it_at(x, y, z))

    def floor_walk(z):
        return {(x, y) for (x, y, zz) in box if zz == z and walkable(x, y, zz)}

    # --- 1. conectividad multi-piso desde la llegada --------------------------------------------
    if not walkable(ax, ay, az):
        print(f"ERROR: la llegada {ax},{ay},{az} no es piso pisable: {it_at(ax, ay, az)}")
        return 1
    dist = {(ax, ay, az): 0}
    q = deque(dist)
    while q:
        x, y, z = q.popleft()
        for dx, dy in ALL8:
            n = (x + dx, y + dy, z)
            if n not in dist and walkable(*n):
                dist[n] = dist[(x, y, z)] + 1
                q.append(n)
        it = it_at(x, y, z)
        for n in ([(x, y + 1, z + 1)] if HOLE in it else []) + \
                  ([(x, y - 1, z - 1)] if STAIR_UP in it else []):
            if n not in dist and walkable(*n):
                dist[n] = dist[(x, y, z)] + 1
                q.append(n)
    print("=== 1. conectividad desde la llegada (8-dir + escaleras + agujeros) ===")
    for z in zs:
        w = floor_walk(z)
        lost = sorted(c for c in w if (c[0], c[1], z) not in dist)
        print(f"z{z}: {len(w)} pisables, {len(lost)} sin acceso")
        for c in lost[:10]:
            errors.append(f"z{z} {c}: pisable sin acceso desde la llegada, items={it_at(c[0], c[1], z)}")

    # --- 2. pares escalera/agujero y llegadas ----------------------------------------------------
    print("\n=== 2. escaleras 1385 / agujeros 432 ===")
    holes = {k for k, v in box.items() if HOLE in v}
    stairs = {k for k, v in box.items() if STAIR_UP in v}
    for hx, hy, hz in sorted(holes):
        ok_pair = (hx, hy, hz + 1) in stairs
        ok_down = walkable(hx, hy + 1, hz + 1)
        ok_up = walkable(hx, hy - 1, hz) if ok_pair else False
        print(f"agujero {hx},{hy},{hz}: par {'OK' if ok_pair else 'FALTA'}; "
              f"caida -> {hx},{hy + 1},{hz + 1} {'OK' if ok_down else 'BLOQUEADA'}; "
              f"subida -> {hx},{hy - 1},{hz} {'OK' if ok_up else 'BLOQUEADA'}")
        if not ok_pair:
            errors.append(f"agujero {hx},{hy},{hz} sin su escalera en z+1")
        if not ok_down:
            errors.append(f"agujero {hx},{hy},{hz}: la caida cae sobre piso no libre")
        if ok_pair and not ok_up:
            errors.append(f"escalera {hx},{hy},{hz + 1}: al subir se llega a piso no libre")
    for sx, sy, sz in sorted(stairs):
        if (sx, sy, sz - 1) not in holes:
            errors.append(f"escalera {sx},{sy},{sz} sin agujero arriba")

    # --- 3. cueva: piezas, rocas de 1 casilla, conectividad desde la boca ------------------------
    print("\n=== 3. cueva (pisos 351/352/355, paredes 356-367) ===")
    zc = min((zz for (x, y, zz) in box if it_at(x, y, zz) and it_at(x, y, zz)[0] in CAVE_FLOOR),
             default=None)
    if zc is not None:
        cf = {(x, y) for (x, y, zz) in box if zz == zc and it_at(x, y, zc)[0] in CAVE_FLOOR}
        cw = {(x, y) for (x, y, zz) in box if zz == zc and any(i in CAVE_WALL for i in it_at(x, y, zc))}
        print(f"z{zc}: piso {len(cf)} casillas, paredes {len(cw)}")
        bad_pieces = 0
        for c in sorted(cw):
            exp = pieces_for(neighbors_in(cf, *c), WALL_SIDE, WALL_CORNER, WALL_INNER)
            act = [i for i in it_at(c[0], c[1], zc) if i in CAVE_WALL][0]
            if exp is None or act != exp[0]:
                bad_pieces += 1
                errors.append(f"z{zc} {c}: pieza de pared {act}, esperada {exp[0] if exp else 'ninguna'}")
        narrow = 0
        for (x, y, zz), it in box.items():
            if zz != zc or it != [ROCK]:
                continue
            if ((x, y - 1) in cf and (x, y + 1) in cf) or ((x - 1, y) in cf and (x + 1, y) in cf):
                narrow += 1
                errors.append(f"z{zc} {x},{y}: roca de 1 casilla entre dos pisos de cueva (pelada)")
        print(f"piezas de pared incorrectas: {bad_pieces}; rocas peladas de 1 casilla: {narrow}")
        mx, my = a.cave_floor
        if (mx, my) in cf:
            lost_c = cf - set(reach(cf, (mx, my), ALL8))
            print(f"desde la boca {mx},{my}: {len(cf) - len(lost_c)}/{len(cf)} alcanzables")
            for c in sorted(lost_c)[:8]:
                errors.append(f"z{zc} {c}: bolsillo de cueva sin acceso desde la boca")
        else:
            notes.append(f"la boca {mx},{my} no es piso de cueva en z{zc} (pasar --cave-floor)")

    # --- 4. vacio a la vista en el mismo piso -----------------------------------------------------
    print("\n=== 4. vacio en el mismo piso (media pantalla 8x6 de cada pisable) ===")
    for z in zs:
        w = floor_walk(z)
        voids = []
        for (x, y) in w:
            for dx in range(-8, 9):
                for dy in range(-6, 7):
                    c = (x + dx, y + dy, z)
                    if x0 <= c[0] <= x1 and y0 <= c[1] <= y1 and c not in box:
                        voids.append((c, (x, y)))
        print(f"z{z}: {len(w)} pisables con {len(voids)} casillas sin tile a la vista")
        for c, o in voids[:5]:
            errors.append(f"z{z} {c[0]},{c[1]}: sin tile, visible desde {o}")

    # --- 5. spawns --------------------------------------------------------------------------------
    print("\n=== 5. spawns dentro de la caja ===")
    spawn_xml = REPO / "server/YurOTS/ots/data/world/test-spawn.xml"
    n = bad = 0
    if spawn_xml.exists():
        for sp in ET.parse(spawn_xml).getroot().iter("spawn"):
            cx, cy, cz = int(sp.get("centerx")), int(sp.get("centery")), int(sp.get("centerz"))
            if not (x0 <= cx <= x1 and y0 <= cy <= y1 and cz in zs):
                continue
            n += 1
            if not walkable(cx, cy, cz):
                bad += 1
                errors.append(f"spawn {cx},{cy},{cz} sobre casilla no pisable: {it_at(cx, cy, cz)}")
    print(f"{n} spawns, {bad} sobre casilla no pisable")

    # --- 6. pilas raras ----------------------------------------------------------------------------

    def is_ground(i):
        return otb.get(i, {}).get("group") == "ground"

    print("\n=== 6. casillas raras / huesos cortados ===")
    weird = bones = 0
    for (x, y, z), it in sorted(box.items()):
        g = sum(1 for i in it if is_ground(i))
        if g != 1 or len(it) > 2:
            weird += 1
            errors.append(f"z{z} {x},{y}: {g} grounds, {len(it)} items: {it}")
        if any(i in DRAGON_PARTS for i in it):
            bones += 1
            errors.append(f"z{z} {x},{y}: hueso de dragon cortado {it}")
    print(f"casillas raras: {weird}; huesos cortados: {bones}")

    # --- 7. decoracion bloqueante en mitad de un paso (informativo) --------------------------------
    print("\n=== 7. decoracion bloqueante en mitad de paso (INFO: los marcos de agujero van a salir) ===")
    interior = {103, 431, 407, 406} | CAVE_FLOOR        # salas/cripta/cueva, no jungla
    walks = {z: floor_walk(z) for z in zs}
    for (x, y, z), it in sorted(box.items()):
        if len(it) < 2 or it[0] not in interior \
                or any(i in CAVE_WALL or i in (1514, 1515) for i in it[1:]):
            continue
        w = walks[z]
        if ((x, y - 1) in w and (x, y + 1) in w) or ((x - 1, y) in w and (x + 1, y) in w):
            if any(bl.blocks(i) for i in it[1:]):
                notes.append(f"z{z} {x},{y}: {it} con paso pisable en ambos ejes")

    # --- 8. cuellos de botella (opcional, lento) ---------------------------------------------------
    if a.cuellos:
        print("\n=== 8. cuellos de botella (INFO: las puertas de 1 casilla son diseno) ===")
        for z in zs:
            cells = floor_walk(z)
            src = (ax, ay) if z == az else sorted(cells)[0]
            base = len(reach(cells, src, ALL8))
            cuts = []
            for c in sorted(cells):
                if c == src:
                    continue
                if len(reach(cells - {c}, src, ALL8)) < base - 1:
                    cuts.append(c)
            print(f"z{z}: {len(cuts)} cuellos")
            for c in sorted(cuts)[:15]:
                d = len(reach(cells - {c}, src, ALL8))
                print(f"   z{z} {c}: aisla {base - 1 - d} casillas, items={it_at(c[0], c[1], z)}")

    print()
    for m in notes[:20]:
        print("INFO", m)
    if errors:
        print(f"\nFAIL: {len(errors)} problemas")
        for m in errors[:40]:
            print("ERROR", m)
        return 1
    print("OK: 0 problemas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
