#!/usr/bin/env python3
"""Caldera Azul: zona de caza sobre un mar de lava azul (z7, distrito de eventos, nov 2026).

La misma estética que la isla volcánica del noroeste (tierra 103 sobre lava, bordes 4667-4678 puestos
sobre la lava según dónde está la tierra, árboles muertos, madera vieja, manchas de ceniza 3152) pero con
la lava azul 20680 y blue bassins 20192 en vez de coal basins. Doc: docs/items-and-map/CALDERA_AZUL.md.

  Llegada (sur)  portal del templo -> 660,378; TP de vuelta y cartel al lado
  Camino         zigzag de 5-7 de ancho (filas y 378 / 362 / 346 / 330), ensanches a mitad de cada tramo
  Santuario      sala 11x8 de mármol negro y ladrillo al norte, puerta al sur: Azhurak (jefe)

Monstruos por etapas según la distancia caminando desde la llegada (receta de ZONAS_DE_CAZA.md): sueltos
al entrar, de a 2 al fondo, 11-12 casillas entre centros. Todos propios de la zona (looks 145-149).

Valida antes de escribir (si algo falla no escribe nada): ids del .otb, toda la tierra conectada, nada de
lava de 1 casilla entre dos tierras ni tierra suelta, ninguna casilla caminable ve el vacío (todo a ±9, ±7
existe), la caja no pisa nada del mapa, spawns sobre tierra libre y lejos de la llegada.

  python3.11 scripts/map/generate-azure-caldera.py --dry-run --png /tmp/caldera.png
  python3.11 scripts/map/generate-azure-caldera.py --replace
Después: python3 scripts/map/temple-portals.py (portal 163,47,7 -> llegada).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from roomkit import (REPO, SIGN, TELEPORT, WORLD, Checker, Map, Room, build_room,  # noqa: E402
                     patch_readables, render_png, write_map)

_spec = importlib.util.spec_from_file_location("ember", HERE / "generate-ember-field.py")
_ember = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ember)
lava_borders = _ember.lava_borders                     # la regla de bordes de la isla volcánica

Z = 7
BOX = (638, 298, 752, 394)                              # todo lo de adentro se escribe (mar de lava)
SPAWNS_XML = WORLD / "test-spawn.xml"
MANIFEST = WORLD / "generated-azure-caldera.json"
S_BEGIN = "<!-- BEGIN AZURE_CALDERA_SPAWNS (scripts/map/generate-azure-caldera.py) -->"
S_END = "<!-- END AZURE_CALDERA_SPAWNS -->"
R_BEGIN, R_END = "<!-- BEGIN AZURE_CALDERA_SIGNS -->", "<!-- END AZURE_CALDERA_SIGNS -->"

BLUE_LAVA, DIRT, ASH = 20680, 103, 3152
BLUE_BASIN = 20192
DEAD_TREES, RUSH_WOOD = (2709, 2717, 2720), 2721
SHRINE_FLOOR = 407
COFFIN_HEAD, COFFIN_FOOT = 1413, 1411                  # ataúd con gema azul + pie abajo (un ataúd = 2 piezas)

TEMPLE_LANDING = (163, 48, 7)                           # llegada del portal "caldera" en la plaza
ARRIVAL = (660, 378, Z)
RETURN_TP = (656, 378, Z)
ARRIVAL_SIGN = (656, 377, Z)
SIGN_TEXT = ("THE AZURE CALDERA\nCold-fire undead. Level 60+.\nThe path ends at Azhurak's shrine.\n"
             "Portal to the temple: here.")

# recorrido (puntos unidos por tramos rectos); filas separadas por 16
PATH = [(660, 378), (728, 378), (728, 362), (662, 362), (662, 346), (728, 346), (728, 330), (695, 330),
        (695, 322)]
SHRINE = Room(690, 311, 11, 8, Z)                       # interior 690-700, 311-318; puerta al sur
DOOR = [(694, 319), (695, 319), (696, 319)]
BOSS = (695, 314)
COFFINS = [692, 695, 698]                               # cabeceras en y 311, pies en y 312

# etapas: (nombres, por spawn, spawntime s, separación mínima entre centros)
STAGES = [
    (("Azure Skeleton",), 1, 90, 12),
    (("Azure Skeleton", "Azure Devil"), 1, 100, 11),
    (("Azure Devil", "Azure Bonebeast"), 2, 120, 12),
    (("Azure Bonebeast", "Azure Lich"), 2, 150, 12),
]
BOSS_SPAWN = ("Azhurak", 1800)
CLEAR = 6                                               # nada a menos de esto de la llegada, el TP y la puerta


def h(x, y, k=0):
    """Ruido determinista (mismo resultado en cada corrida)."""
    n = (x * 73856093) ^ (y * 19349663) ^ (k * 83492791)
    n = (n ^ (n >> 13)) * 1274126177
    return (n ^ (n >> 16)) & 0xFFFFFFFF


def n8(x, y):
    return [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def smooth(i, k, step=7):
    """Ruido suave a lo largo del recorrido (0 a 1): interpola valores al azar cada `step` casillas."""
    a, b = (h(i // step, 0, k) % 1000) / 1000, (h(i // step + 1, 0, k) % 1000) / 1000
    t = (i % step) / step
    t = t * t * (3 - 2 * t)
    return a + (b - a) * t


def segment_cells():
    """Casillas del eje del recorrido, en orden."""
    out = []
    for (x0, y0), (x1, y1) in zip(PATH, PATH[1:]):
        dx = (x1 > x0) - (x1 < x0)
        dy = (y1 > y0) - (y1 < y0)
        x, y = x0, y0
        while (x, y) != (x1, y1):
            out.append((x, y))
            x, y = x + dx, y + dy
    out.append(PATH[-1])
    return out


def shrine_apron():
    """El santuario con su anillo de paredes y una casilla de tierra alrededor."""
    r = SHRINE
    return {(x, y) for x in range(r.x0 - 2, r.x1 + 3) for y in range(r.y0 - 2, r.y1 + 3)}


def turn_indices():
    out, i = [], 0
    for (x0, y0), (x1, y1) in zip(PATH, PATH[1:]):
        i += abs(x1 - x0) + abs(y1 - y0)
        out.append(i)
    return out


TURNS = turn_indices()


def land_mask():
    axis = segment_cells()
    land = set()
    for i, (x, y) in enumerate(axis):
        # el eje ondula ±1-2 casillas hacia los costados y el ancho va de 5 a 9 (ruido suave a lo largo)
        horiz = (axis[min(i + 1, len(axis) - 1)][1] == y) if i + 1 < len(axis) else True
        near_turn = min(abs(i - j) for j in TURNS) < 4
        off = 0 if near_turn else round((smooth(i, 11) - 0.5) * 4)
        cx, cy = (x, y + off) if horiz else (x + off, y)
        hw = 2 + round(smooth(i, 12) * 2)
        for dx in range(-hw, hw + 1):
            for dy in range(-hw, hw + 1):
                if dx * dx + dy * dy <= hw * hw + hw:
                    land.add((cx + dx, cy + dy))
    # ensanches: a mitad de cada tramo largo y en las esquinas, más la llegada
    discs = [(ARRIVAL[0], ARRIVAL[1], 4)]
    for (x0, y0), (x1, y1) in zip(PATH, PATH[1:]):
        if abs(x1 - x0) + abs(y1 - y0) >= 20:
            discs.append(((x0 + x1) // 2 + (h(x0, y0, 2) % 7) - 3, (y0 + y1) // 2, 4))
        discs.append((x1, y1, 3))
    for cx, cy, r in discs:
        for x in range(cx - r, cx + r + 1):
            for y in range(cy - r, cy + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + 1:
                    land.add((x, y))
    land |= shrine_apron()
    land.add(RETURN_TP[:2])
    land.add(ARRIVAL_SIGN[:2])
    # bordes con ruido: muerde o agrega casillas sueltas del contorno
    edge = [p for p in land if any(q not in land for q in n8(*p))]
    for p in edge:
        if h(*p, 3) % 100 < 18 and p not in shrine_apron():
            land.discard(p)
    for p in list(land):
        for q in n8(*p):
            if q not in land and h(*q, 4) % 100 < 10:
                land.add(q)
    protected = set(axis) | shrine_apron() | {RETURN_TP[:2], ARRIVAL_SIGN[:2]}
    for _ in range(3):                                   # suavizar
        changed = False
        for x in range(BOX[0], BOX[2] + 1):
            for y in range(BOX[1], BOX[3] + 1):
                c = sum(q in land for q in n8(x, y))
                if (x, y) not in land and (c >= 5 or ((x, y - 1) in land and (x, y + 1) in land)
                                            or ((x - 1, y) in land and (x + 1, y) in land)):
                    land.add((x, y))
                    changed = True
                elif (x, y) in land and c <= 2 and (x, y) not in protected:
                    land.discard((x, y))
                    changed = True
        if not changed:
            break
    # charcos de lava encerrados: los chicos se rellenan, los de 6+ quedan (como en la isla volcánica)
    seen = set()
    for x in range(BOX[0], BOX[2] + 1):
        for y in range(BOX[1], BOX[3] + 1):
            if (x, y) in land or (x, y) in seen:
                continue
            comp, todo, outside = [], [(x, y)], False
            seen.add((x, y))
            while todo:
                p = todo.pop()
                comp.append(p)
                for q in ((p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)):
                    if not (BOX[0] <= q[0] <= BOX[2] and BOX[1] <= q[1] <= BOX[3]):
                        outside = True
                    elif q not in land and q not in seen:
                        seen.add(q)
                        todo.append(q)
            if not outside and len(comp) < 6:
                land |= set(comp)
    return land, axis


def dist_to(cells, targets):
    """Distancia Chebyshev de cada casilla al conjunto targets (BFS en 8 direcciones)."""
    dist = {p: 0 for p in targets if p in cells}
    q = deque(dist)
    while q:
        p = q.popleft()
        for n in n8(*p):
            if n in cells and n not in dist:
                dist[n] = dist[p] + 1
                q.append(n)
    return dist


def walk_from(start, free):
    dist = {start: 0}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in free and n not in dist:
                dist[n] = dist[(x, y)] + 1
                q.append(n)
    return dist


def build():
    land, axis = land_mask()
    shrine_cells = set((x, y) for x, y, _z in SHRINE.cells())
    shrine_ring = {(x, y) for x in range(SHRINE.x0 - 1, SHRINE.x1 + 2) for y in range(SHRINE.y0 - 1, SHRINE.y1 + 2)}
    m = Map()
    for x in range(BOX[0], BOX[2] + 1):
        for y in range(BOX[1], BOX[3] + 1):
            m.ground((x, y, Z), DIRT if (x, y) in land else BLUE_LAVA)
    # bordes de lava (sobre la casilla de lava, según la tierra de alrededor)
    isdirt = lambda x, y: (x, y) in land                   # noqa: E731
    for x in range(BOX[0], BOX[2] + 1):
        for y in range(BOX[1], BOX[3] + 1):
            if (x, y) not in land:
                for b in lava_borders(isdirt, x, y):
                    m.add((x, y, Z), b)
    # santuario
    build_room(m, SHRINE, SHRINE_FLOOR, "brick")
    for x, y in DOOR:                                     # puerta: sin pared en el sur
        m.t[(x, y, Z)]["items"] = []
    for cx in COFFINS:
        m.add((cx, SHRINE.y0, Z), COFFIN_HEAD)
        m.add((cx, SHRINE.y0 + 1, Z), COFFIN_FOOT)
    for p in ((SHRINE.x0, SHRINE.y0), (SHRINE.x1, SHRINE.y0), (SHRINE.x0, SHRINE.y1), (SHRINE.x1, SHRINE.y1)):
        m.add(p + (Z,), BLUE_BASIN)
    for dx in (-1, 0, 1):                                # círculo de ceniza bajo el jefe
        for dy in (-1, 0, 1):
            if abs(dx) + abs(dy) < 2 or h(dx, dy, 14) % 2:
                m.floor((BOSS[0] + dx, BOSS[1] + dy, Z), ASH)
    # ceniza: manchas lejos de la lava
    from_lava = dist_to(land, {p for p in land if any(q not in land for q in n8(*p))})
    ash = set()
    for p in sorted(land):                                # manchas redondeadas de 1-2 de radio
        if h(*p, 5) % 1000 < 14:
            r = 1 + h(*p, 13) % 2
            for dx in range(-r - 1, r + 2):
                for dy in range(-r, r + 1):
                    q = (p[0] + dx, p[1] + dy)
                    if dx * dx + dy * dy * 2 <= r * r + 2 and h(*q, 6) % 100 < 85:
                        ash.add(q)
    for q in ash:
        if q in land and q not in shrine_ring and from_lava.get(q, 0) >= 2:
            m.floor(q + (Z,), ASH)
    # llegada: TP de vuelta y cartel
    m.add(RETURN_TP, TELEPORT, tele=TEMPLE_LANDING)
    m.add(ARRIVAL_SIGN, SIGN)
    # decoración que bloquea: lejos del eje del camino, sin cortar el paso
    from_axis = dist_to(land, set(axis))
    walk_cells = land - shrine_ring
    blocked = {RETURN_TP[:2], ARRIVAL_SIGN[:2]}
    near_keep = {ARRIVAL[:2], RETURN_TP[:2]} | set(DOOR)
    wish = []
    for (x, y) in sorted(walk_cells):
        if from_axis.get((x, y), 0) < 2 or min(abs(x - a) + abs(y - b) for a, b in near_keep) < 4:
            continue
        r = h(x, y, 7) % 1000
        if r < 30:
            wish.append(((x, y), DEAD_TREES[h(x, y, 8) % 3]))
        elif r < 52:
            wish.append(((x, y), RUSH_WOOD))
    for i in range(6, len(axis) - 1, 11):                # blue bassins a lo largo del camino (luz)
        (x, y), (nx, ny) = axis[i], axis[i + 1]
        side = 2 if h(x, y, 9) % 2 else -2
        p = (x, y + side) if ny == y else (x + side, y)     # al costado del eje, del lado que toque
        if p in walk_cells:
            wish.append((p, BLUE_BASIN))
    for x in (DOOR[0][0] - 2, DOOR[-1][0] + 2):           # dos braseros flanqueando la puerta
        wish.append(((x, DOOR[0][1] + 1), BLUE_BASIN))
    start = ARRIVAL[:2]
    free_all = land - {p for p in land if any(i["id"] in WALL_IDS for i in m.t[p + (Z,)]["items"])} - blocked
    deco = {}
    for p, item in wish:
        if p in deco or p in blocked:
            continue
        deco[p] = item
        if len(walk_from(start, free_all - set(deco))) != len(walk_from(start, free_all)) - len(deco):
            del deco[p]
    for p, item in deco.items():
        m.add(p + (Z,), item)
    free = free_all - set(deco) - {(x, y) for x, y in ((cx, SHRINE.y0) for cx in COFFINS)} \
        - {(cx, SHRINE.y0 + 1) for cx in COFFINS} \
        - {p for p in ((SHRINE.x0, SHRINE.y0), (SHRINE.x1, SHRINE.y0), (SHRINE.x0, SHRINE.y1), (SHRINE.x1, SHRINE.y1))}
    return m, land, axis, free, shrine_cells


WALL_IDS = {v for w in __import__("roomkit").WALLS.values() for v in w.values()}


def place_spawns(free, shrine_cells):
    walk = walk_from(ARRIVAL[:2], free)
    keep = [ARRIVAL[:2], RETURN_TP[:2]] + DOOR
    cand = sorted((d, p) for p, d in walk.items() if p not in shrine_cells
                  and min(abs(p[0] - a) + abs(p[1] - b) for a, b in keep) >= CLEAR)
    n = len(cand)
    centers, out = [], []
    for i, (names, per, st, sep) in enumerate(STAGES):
        band = cand[i * n // len(STAGES):(i + 1) * n // len(STAGES)]
        k = 0
        for _d, (x, y) in band:
            if any(abs(x - a) + abs(y - b) < sep for a, b in centers):
                continue
            room = sum((x + dx, y + dy) in free for dx in range(-2, 3) for dy in range(-2, 3))
            if room < per + 3 + 12:
                continue
            centers.append((x, y))
            mons = [names[(k + j) % len(names)] for j in range(per)]
            k += per
            out.append(dict(x=x, y=y, radius=2 if per == 1 else 3, stage=i + 1, monsters=mons, spawntime=st))
    out.append(dict(x=BOSS[0], y=BOSS[1], radius=1, stage=5, monsters=[BOSS_SPAWN[0]], spawntime=BOSS_SPAWN[1]))
    return out, walk


def spawn_block(spawns):
    lines = [f"\t{S_BEGIN}"]
    for s in spawns:
        lines.append(f'\t<spawn centerx="{s["x"]}" centery="{s["y"]}" centerz="{Z}" radius="{s["radius"]}">')
        for j, name in enumerate(s["monsters"]):
            dx = 0 if j == 0 else 1
            lines.append(f'\t\t<monster name="{name}" x="{dx}" y="0" z="{Z}" spawntime="{s["spawntime"]}" />')
        lines.append("\t</spawn>")
    lines.append(f"\t{S_END}")
    return "\n".join(lines) + "\n"


def validate(m, land, free, spawns, walk):
    c = Checker(m)
    c.tiles()
    errs = c.errs
    # la caja no pisa nada del mapa real (zona nueva en un lugar vacío)
    sys.path.insert(0, str(HERE / "kb"))
    import mapdata
    real = mapdata.load_tiles()
    taken = [k for k in real if k[2] == Z and BOX[0] <= k[0] <= BOX[2] and BOX[1] <= k[1] <= BOX[3]]
    if taken and not all(real[k] == [t["ground"]] + [i["id"] for i in t["items"]]
                         for k, t in ((k, m.t.get(k)) for k in taken) if t):
        pass                                            # ya generada antes: se reescribe
    foreign = [k for k in taken if k not in m.t]
    if foreign:
        errs.append(f"la caja tiene {len(foreign)} casillas que no son de la Caldera")
    for k in real:
        if k[2] == Z and not (BOX[0] <= k[0] <= BOX[2] and BOX[1] <= k[1] <= BOX[3]) \
                and BOX[0] - 9 <= k[0] <= BOX[2] + 9 and BOX[1] - 7 <= k[1] <= BOX[3] + 7:
            errs.append(f"casilla ajena pegada a la caja: {k}")
            break
    # todo lo caminable conectado y sin ver el vacío
    if len(walk) != len(free):
        errs.append(f"{len(free) - len(walk)} casillas caminables sin acceso desde la llegada")
    for x, y in free:
        if not (BOX[0] + 9 <= x <= BOX[2] - 9 and BOX[1] + 7 <= y <= BOX[3] - 7):
            errs.append(f"{(x, y)} ve el borde de la caja (vacío)")
            break
    # lava de 1 casilla entre dos tierras / tierra suelta
    for x in range(BOX[0] + 1, BOX[2]):
        for y in range(BOX[1] + 1, BOX[3]):
            if (x, y) not in land and (((x - 1, y) in land and (x + 1, y) in land)
                                       or ((x, y - 1) in land and (x, y + 1) in land)):
                errs.append(f"lava de 1 casilla entre tierras en {(x, y)}")
            if (x, y) in land and not any(q in land for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))):
                errs.append(f"tierra suelta en {(x, y)}")
    for need, p in (("llegada", ARRIVAL[:2]), ("puerta del santuario", DOOR[1]), ("jefe", BOSS)):
        if p not in walk:
            errs.append(f"{need} {p} inaccesible")
    tp_next = [q for q in ((RETURN_TP[0] + 1, RETURN_TP[1]), (RETURN_TP[0], RETURN_TP[1] + 1)) if q in walk]
    if not tp_next:
        errs.append("no se llega al TP de vuelta")
    for s in spawns:
        if (s["x"], s["y"]) not in free:
            errs.append(f"spawn {s['monsters']} en {(s['x'], s['y'])} sin piso libre")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", type=Path, default=WORLD / "test.otbm")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--png", type=Path)
    a = ap.parse_args()

    m, land, axis, free, shrine_cells = build()
    spawns, walk = place_spawns(free, shrine_cells)
    errs = validate(m, land, free, spawns, walk)
    per_stage = {}
    for s in spawns:
        per_stage.setdefault(s["stage"], []).append(len(s["monsters"]))
    print(f"Caldera Azul: {len(m.t)} casillas, {len(land)} de tierra, {len(free)} caminables; "
          f"camino {len(axis)} casillas")
    for st, lst in sorted(per_stage.items()):
        print(f"  etapa {st}: {len(lst)} spawns, {sum(lst)} monstruos")
    if a.png:
        render_png(m, a.png, Z)
        print(f"PNG {a.png}")
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs[:30]))
        return 1
    if a.dry_run or not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    write_map(a.map, m, BOX, Z, Checker(m).stackable)
    sx = SPAWNS_XML.read_text(encoding="latin-1")
    block = spawn_block(spawns)
    pat = re.compile(r"[ \t]*" + re.escape(S_BEGIN) + r".*?" + re.escape(S_END) + r"\n?", re.S)
    sx = pat.sub(lambda _m: block, sx, count=1) if pat.search(sx) else sx.replace("</spawns>", block + "</spawns>")
    SPAWNS_XML.write_text(sx, encoding="latin-1")
    patch_readables(R_BEGIN, R_END, [dict(x=ARRIVAL_SIGN[0], y=ARRIVAL_SIGN[1], z=Z, text=SIGN_TEXT)])
    MANIFEST.write_text(json.dumps({
        "name": "generated-azure-caldera", "box": BOX, "z": Z, "arrival": ARRIVAL, "returnTp": RETURN_TP,
        "templeLanding": TEMPLE_LANDING, "shrine": SHRINE.box(), "boss": BOSS, "tiles": len(m.t),
        "land": len(land), "walkable": len(free),
        "spawns": [{k: s[k] for k in ("x", "y", "stage", "monsters", "spawntime")} for s in spawns],
    }, indent=1) + "\n", encoding="utf-8")
    print(f"OK {a.map}, test-spawn.xml, readables y {MANIFEST.name}")
    print("Después: python3 scripts/map/temple-portals.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
