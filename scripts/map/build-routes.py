#!/usr/bin/env python3
"""Genera `scripts/map/routes.json`: rutas desde el templo a los destinos principales.

El mapa interactivo (`build-monster-map.py`) lee ese JSON y dibuja los caminos. Las rutas se
calculan sobre `test.otbm` (casillas caminables, escaleras, rampas, agujeros y teleports), así que
si cambia el mapa hay que volver a correr este script:

  python3 scripts/map/build-routes.py

Solo lee el repo y escribe `scripts/map/routes.json`. No toca el mapa ni los spawns.
"""
from __future__ import annotations

import collections
import json
import struct
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, load_otb, parse_tree  # noqa: E402

OUT = HERE / "routes.json"
MAP_PATH = MAP
OTB = load_otb()

UP_IDS = {1385, 1394, 1396, 1404, 3685, 3687, 1392, 1402, 3683, 1388, 1398, 3679,
          1390, 1400, 3681, 3688, 1553, 1555, 1557, 1559}
LADDER_UP_IDS = {1386, 3678}
TEMPLE = (127, 57, 6)


def flags_of(item) -> list:
    return OTB.get(item["id"], {}).get("flags", [])


def group_of(item) -> str:
    return OTB.get(item["id"], {}).get("group", "none")


def needs_count(sid: int) -> bool:
    rec = OTB.get(sid, {})
    return "stackable" in rec.get("flags", []) or rec.get("group") in ("splash", "fluid")


def parse_item(node) -> dict | None:
    p = bytes(node[1])
    if len(p) < 2:
        return None
    sid = struct.unpack_from("<H", p)[0]
    pos = 2 + (1 if needs_count(sid) else 0)
    rec = {"id": sid, "action": None, "unique": None, "tele": None, "depot": None,
           "text": None, "children": []}
    while pos < len(p):
        a = p[pos]
        pos += 1
        if a in (4, 5, 10):
            if pos + 2 > len(p):
                break
            v = struct.unpack_from("<H", p, pos)[0]
            pos += 2
            if a == 4:
                rec["action"] = v
            elif a == 5:
                rec["unique"] = v
            else:
                rec["depot"] = v
        elif a in (6, 7):
            if pos + 2 > len(p):
                break
            n = struct.unpack_from("<H", p, pos)[0]
            pos += 2
            rec["text" if a == 6 else "desc"] = p[pos:pos + n].decode("latin-1", "replace")
            pos += n
        elif a == 8:
            if pos + 5 > len(p):
                break
            x, y, z = struct.unpack_from("<HHB", p, pos)
            pos += 5
            rec["tele"] = (x, y, z)
        elif a == 12:
            pos += 1
        else:
            break
    for child in node[2]:
        if child[0] == T_ITEM:
            c = parse_item(child)
            if c:
                rec["children"].append(c)
    return rec


def load_map() -> dict:
    root = parse_tree(MAP_PATH.read_bytes())
    tiles = {}
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        for tile in area[2]:
            if tile[0] not in (T_TILE, T_HOUSETILE):
                continue
            tp = bytes(tile[1])
            x, y = ax + tp[0], ay + tp[1]
            pos = 6 if tile[0] == T_HOUSETILE and len(tp) >= 6 else 2
            items = []
            while pos < len(tp):
                a = tp[pos]
                pos += 1
                if a == 3:
                    pos += 4
                elif a == 9:
                    sid = struct.unpack_from("<H", tp, pos)[0]
                    pos += 2 + (1 if needs_count(sid) else 0)
                    items.append({"id": sid, "action": None, "unique": None, "tele": None,
                                  "depot": None, "text": None, "children": []})
                else:
                    break
            for child in tile[2]:
                if child[0] == T_ITEM:
                    it = parse_item(child)
                    if it:
                        items.append(it)
            tiles[(x, y, az)] = {"items": items}
    return tiles


def tile_walkable(tiles, pos) -> bool:
    t = tiles.get(pos)
    if not t:
        return False
    if not any(group_of(it) == "ground" for it in t["items"]):
        return False
    # Las puertas cerradas se pueden abrir: para armar la ruta las tratamos como paso.
    return not any("block_solid" in flags_of(it) and OTB.get(it["id"], {}).get("name") != "closed door"
                   for it in t["items"])


def dirs_of(tiles, pos) -> set:
    d = set()
    for it in tiles[pos]["items"]:
        fl = flags_of(it)
        if "floorchange_north" in fl:
            d.add("N")
        if "floorchange_east" in fl:
            d.add("E")
        if "floorchange_south" in fl:
            d.add("S")
        if "floorchange_west" in fl:
            d.add("W")
    return d


def up_landing(tiles, pos):
    d = dirs_of(tiles, pos)
    x, y, z = pos
    if not d:
        return None
    if "N" in d and "E" in d:
        return (x + 1, y - 1, z - 1)
    if "N" in d and "W" in d:
        return (x - 1, y - 1, z - 1)
    if "S" in d and "E" in d:
        return (x + 1, y + 1, z - 1)
    if "S" in d and "W" in d:
        return (x - 1, y + 1, z - 1)
    if "N" in d:
        return (x, y - 1, z - 1)
    if "S" in d:
        return (x, y + 1, z - 1)
    if "E" in d:
        return (x + 1, y, z - 1)
    if "W" in d:
        return (x - 1, y, z - 1)
    return None


def down_landing(tiles, pos):
    x, y, z = pos
    below = (x, y, z + 1)
    d = dirs_of(tiles, below)
    if not d:
        return below
    if "N" in d and "E" in d:
        return (x - 1, y + 1, z + 1)
    if "N" in d and "W" in d:
        return (x + 1, y + 1, z + 1)
    if "S" in d and "E" in d:
        return (x - 1, y - 1, z + 1)
    if "S" in d and "W" in d:
        return (x + 1, y - 1, z + 1)
    if "N" in d:
        return (x, y + 1, z + 1)
    if "S" in d:
        return (x, y - 1, z + 1)
    if "E" in d:
        return (x - 1, y, z + 1)
    if "W" in d:
        return (x + 1, y, z + 1)
    return below


def item_fc_landing(tiles, pos, sid):
    x, y, z = pos
    if sid in LADDER_UP_IDS:
        return (x, y + 1, z - 1)
    below = (x, y, z + 1)
    t = tiles.get(below)
    if t:
        for it in t["items"]:
            if it["id"] in UP_IDS:
                s = it["id"]
                if s in {1385, 1394, 1396, 1404, 3685, 3687}:
                    return (x, y + 1, z + 1)
                if s in {1392, 1402, 3683}:
                    return (x, y - 1, z + 1)
                if s in {1388, 1398, 3679}:
                    return (x - 1, y, z + 1)
                if s in {1390, 1400, 3681, 3688}:
                    return (x + 1, y, z + 1)
                if s == 1555:
                    return (x - 1, y + 1, z + 1)
                if s == 1553:
                    return (x + 1, y + 1, z + 1)
                if s == 1557:
                    return (x - 1, y - 1, z + 1)
                if s == 1559:
                    return (x + 1, y - 1, z + 1)
    return below


def build_graph(tiles):
    walk = {p for p in tiles if tile_walkable(tiles, p)}
    vert: dict[tuple, set] = {}

    def add(a, b):
        if b in walk:
            vert.setdefault(a, set()).add(b)

    for p in walk:
        for it in tiles[p]["items"]:
            sid = it["id"]
            if it["tele"] is not None:
                add(p, it["tele"])
            fl = flags_of(it)
            if "floorchange_down" in fl:
                add(p, down_landing(tiles, p))
            if dirs_of(tiles, p):
                q = up_landing(tiles, p)
                if q:
                    add(p, q)
                    add(q, p)          # rampa/escalera: se puede subir y bajar
            elif sid in UP_IDS:
                add(p, item_fc_landing(tiles, p, sid))
            elif sid in LADDER_UP_IDS:
                add(p, item_fc_landing(tiles, p, sid))
    return walk, vert


def bfs(start, goal, walk, vert):
    if start not in walk or goal not in walk:
        return None
    q = collections.deque([start])
    prev = {start: None}
    while q:
        p = q.popleft()
        if p == goal:
            break
        x, y, z = p
        for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z)):
            if n in walk and n not in prev:
                prev[n] = p
                q.append(n)
        for n in vert.get(p, ()):
            if n not in prev:
                prev[n] = p
                q.append(n)
    if goal not in prev:
        return None
    path = []
    p = goal
    while p is not None:
        path.append(p)
        p = prev[p]
    return path[::-1]


def simplify(path):
    if len(path) <= 2:
        return path
    out = [path[0]]
    for i in range(1, len(path) - 1):
        a, b, c = path[i - 1], path[i], path[i + 1]
        if b[2] != a[2] or c[2] != b[2]:
            out.append(b)
            continue
        d1 = (b[0] - a[0], b[1] - a[1])
        d2 = (c[0] - b[0], c[1] - b[1])
        if d1 != d2 or i % 3 == 0:
            out.append(b)
    out.append(path[-1])
    return out


def split_segments(path):
    segs = []
    cur = []
    for p in path:
        if cur and p[2] != cur[-1][2]:
            segs.append((cur[-1][2], cur))
            cur = [cur[-1], p]
        else:
            cur.append(p)
    if cur:
        segs.append((cur[-1][2], cur))
    return [(z, [[q[0], q[1]] for q in pts]) for z, pts in segs]


def walk_part(start, goal, walk, vert):
    path = bfs(start, goal, walk, vert)
    if path is None:
        raise SystemExit(f"no encontré camino de {start} a {goal}")
    path = simplify(path)
    return split_segments(path), path


def transition_markers(path):
    out = []
    for a, b in zip(path, path[1:]):
        if a[2] != b[2]:
            out.append({"x": a[0], "y": a[1], "z": a[2], "label": "Escalera",
                        "kind": "stairs"})
    return out


def door_markers(path):
    out = []
    for p in path:
        if any(OTB.get(it["id"], {}).get("name") == "closed door" for it in tiles[p]["items"]):
            out.append({"x": p[0], "y": p[1], "z": p[2], "label": "Puerta", "kind": "door"})
    return out


def route_walk(slug, name, target, steps):
    segs, path = walk_part(TEMPLE, target, walk, vert)
    return {
        "slug": slug, "name": name, "kind": "walk",
        "start": [TEMPLE[0], TEMPLE[1], TEMPLE[2]],
        "steps": steps,
        "segments": [{"z": z, "points": pts} for z, pts in segs],
        "jumps": [],
        "markers": [{"x": TEMPLE[0], "y": TEMPLE[1], "z": TEMPLE[2], "label": "Depot",
                     "kind": "start"},
                    {"x": target[0], "y": target[1], "z": target[2], "label": name,
                     "kind": "target"}] + transition_markers(path) + door_markers(path),
    }


def route_jump(slug, name, kind, origin, landing, target, steps, origin_label, landing_label):
    segs1, path1 = walk_part(TEMPLE, origin, walk, vert)
    segs2 = []
    path2 = []
    if target:
        segs2, path2 = walk_part(landing, target, walk, vert)
    segments = [{"z": z, "points": pts} for z, pts in segs1 + segs2]
    markers = [{"x": TEMPLE[0], "y": TEMPLE[1], "z": TEMPLE[2], "label": "Depot",
                "kind": "start"},
               {"x": origin[0], "y": origin[1], "z": origin[2], "label": origin_label,
                "kind": kind},
               {"x": landing[0], "y": landing[1], "z": landing[2], "label": landing_label,
                "kind": "arrival"}]
    if target:
        markers.append({"x": target[0], "y": target[1], "z": target[2], "label": name,
                        "kind": "target"})
    markers += transition_markers(path1) + transition_markers(path2) + door_markers(path1) + door_markers(path2)
    return {
        "slug": slug, "name": name, "kind": kind,
        "start": [TEMPLE[0], TEMPLE[1], TEMPLE[2]],
        "steps": steps,
        "segments": segments,
        "jumps": [{"from": list(origin), "to": list(landing),
                   "label": "Portal" if kind == "portal" else "Barco"}],
        "markers": markers,
    }


def main() -> int:
    global MAP_PATH, tiles, walk, vert
    ap = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    ap.add_argument("--map", type=Path, default=MAP, help="OTBM a usar (por defecto test.otbm del repo)")
    args = ap.parse_args()
    MAP_PATH = args.map
    tiles = load_map()
    walk, vert = build_graph(tiles)
    print(f"mapa: {len(tiles)} casillas, {len(walk)} caminables, {sum(len(v) for v in vert.values())} conexiones verticales")

    routes = [
        route_walk("templo-plaza", "Depot y plaza de portales", (156, 47, 7), [
            "Sal del depot y sube al templo; la salida a la plaza es la escalera del este.",
            "Llegas a la plaza de portales.",
            "Los portales a las hunts están en la fila norte; el barco, al sureste.",
        ]),
        route_jump("isla-natural", "Isla natural", "portal", (156, 47, 7), (147, 462, 7),
                   (163, 464, 7), [
                       "Sal del depot a la plaza y entra al portal ISLA NATURAL.",
                       "Llegas a la punta oeste de la isla; sigue el sendero al este hasta la cueva.",
                       "La cueva baja tres pisos; al fondo espera la Old Widow.",
                   ], "Portal Isla natural", "Llegada a la isla"),
        route_jump("valle-de-las-bestias", "Valle de las Bestias", "portal", (158, 47, 7),
                   (312, 360, 7), (312, 252, 7), [
                       "Sal del depot a la plaza y entra al portal VALLE DE LAS BESTIAS.",
                       "Llegas al sur del valle.",
                       "Sigue el camino al norte hasta las Ruinas y la escalera a las Catacumbas.",
                   ], "Portal Valle de las Bestias", "Llegada al valle"),
        route_jump("el-crisol", "El Crisol", "portal", (164, 47, 7), (83, 85, 0), None, [
            "Sal del depot a la plaza y entra al portal CRISOL.",
            "Llegas a la Sala del Crisol.",
            "Las tres puertas están al norte: Bronce, Plata y Oro.",
        ], "Portal El Crisol", "Sala del Crisol"),
        route_jump("wave-arena", "Wave Arena", "portal", (166, 47, 7), (176, 403, 7),
                   None, [
                       "Sal del depot a la plaza y entra al portal WAVE ARENA.",
                       "Llegas al campamento.",
                       "El claro de la arena está al norte y se entra con la palanca.",
                   ], "Portal Wave Arena", "Campamento"),
        route_jump("reloj-de-arena", "Reloj de Arena", "portal", (168, 47, 7), (338, 395, 6),
                   None, [
                       "Sal del depot a la plaza y entra al portal RELOJ DE ARENA.",
                       "Llegas a la sala del Reloj.",
                       "El reloj y las 6 oleadas están en la sala.",
                   ], "Portal Reloj de Arena", "Sala del Reloj"),
        route_walk("barco-fargum", "Barco: Fargum", (172, 66, 7), [
            "Sal del depot a la ciudad y anda al muelle sureste; Fargum está en el muelle.",
            "Dile el destino: `elfland`, `epstein island`, `hell quest`, `dragon land`, `frozen isle`, `gauntlet` o `city`.",
            "El viaje cuesta entre 20 y 50 gp.",
        ]),
        route_jump("isla-del-hielo", "Isla del Hielo", "boat", (172, 66, 7), (395, 104, 7),
                   (392, 15, 7), [
                       "Sal del depot a la ciudad y anda al muelle sureste; habla con Fargum.",
                       "Dile `frozen isle` (20 gp).",
                       "Llegas al sur de la isla.",
                       "Sigue el sendero al norte hasta la bajada a las grutas.",
                   ], "Fargum (barco)", "Muelle de Frozen Isle"),
        route_jump("hell-quest", "Hell Quest", "boat", (172, 66, 7), (345, 211, 7),
                   (358, 146, 7), [
                       "Sal del depot a la ciudad y anda al muelle sureste; habla con Fargum.",
                       "Dile `hell quest` (20 gp).",
                       "Llegas a la isla de lava.",
                       "Sigue el camino al norte hasta la bajada.",
                   ], "Fargum (barco)", "Muelle de Hell Quest"),
        route_jump("epstein-island", "Epstein Island", "boat", (172, 66, 7), (85, 209, 7),
                   (80, 201, 8), [
                       "Sal del depot a la ciudad y anda al muelle sureste; habla con Fargum.",
                       "Dile `epstein island` (20 gp).",
                       "Llegas a la isla.",
                       "Las cuevas y hunts están al norte; la primera bajada es la del norte.",
                   ], "Fargum (barco)", "Muelle de Epstein"),
        route_walk("castillo-imperial", "Castillo Imperial", (96, 34, 3), [
            "Sal del depot a la ciudad y anda al noroeste, al torreón y puente de madera.",
            "Cruza el puente y baja por la trampilla al patio del castillo.",
            "Las escaleras te llevan por los 6 pisos hasta el trono.",
        ]),
        route_walk("desierto-de-las-ruinas", "Desierto de las Ruinas", (198, 74, 7), [
            "Sal del depot a la ciudad y anda al este.",
            "Pasa el túnel bajo la muralla.",
            "Llegas a la entrada del desierto; sigue el camino de piedra.",
        ]),
        route_walk("islote-del-minotauro", "Islote del Minotauro", (110, 52, 7), [
            "Sal del depot a la ciudad y anda al oeste, al muelle.",
            "Cruza el puente de madera al islote.",
            "Los minotauros están en el islote; la cueva baja en la punta oeste.",
        ]),
    ]

    data = {"generatedBy": "scripts/map/build-routes.py", "depot": list(TEMPLE), "routes": routes}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"OK {OUT}: {len(routes)} rutas")
    for r in routes:
        pts = sum(len(s["points"]) for s in r["segments"])
        print(f"  {r['slug']:24} {r['kind']:6} {pts:3} puntos  {len(r['jumps'])} saltos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
