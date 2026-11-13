#!/usr/bin/env python3
"""River Street III, IV y V: casas más cortas, patios y paso al río (nov 2026).

Antes eran tres casas de 3x5 pegadas pared con pared, que llegaban hasta la orilla del río.
Ahora (z7):

  - cada casa tiene 3x3 por dentro (pared sur en y 63);
  - entre casa y casa queda un pasillo de 1 casilla (x 150 y x 156) de la calle a la orilla:
    III se corre 1 al oeste y V 1 al este; IV queda en su lugar;
  - III y V tienen un patio de 3x2 al sur, cercado, con salida desde la casa (hueco en la pared sur);
  - IV no tiene patio: debajo de ella se juntan los dos pasillos (camino de tierra) y sale un puente
    de sogas de 1 casilla (x 153, mismo kit que el puente de 181-184, 80-88) que cruza el río; del
    otro lado un camino de tierra lleva al arco de las ruinas de los trolls (153, 78);
  - donde una pared o el patio caen sobre la orilla se conserva la pieza de borde del agua.

Las puertas quedan donde estaban (148, 153 y 158 en la fila 59), así los data/houses/<casa>.xml
(frontdoor) no cambian: el server viejo los reescribe al apagarse y no hay nada que pisar.
Solo cambia el mapa en la zona y estas tres casas en data/houses.xml.

Valida antes de escribir: las casas no tienen dueño ni ítems guardados, ninguna casilla tocada
tiene ítems con atributos, desde la calle se cruza el puente por los dos pasillos, los patios solo
se alcanzan desde su casa y houses.xml queda igual al mapa (sync-houses-with-map.py).

Uso:
  python3 scripts/map/reshape-river-street.py --dry-run [--png /tmp/river.png]
  python3 scripts/map/reshape-river-street.py --replace
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import struct
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "kb"))
from mapdata import (MAP, REPO, T_AREA, T_HOUSETILE, T_ITEM, T_TILE, Renderer, load_otb,  # noqa: E402
                     parse_tree, png_bytes, serialize_tree)

DATA = REPO / "server/YurOTS/ots/data"
HOUSES_XML = DATA / "houses.xml"
Z = 7

# --- piezas ---------------------------------------------------------------------------------------
POST, HORIZ, VERT, CORNER = 1038, 1039, 1043, 1044      # pared "framework" (medida en estas casas)
WIN_H, WIN_V, DOOR = 1263, 1264, 1212
TORCH_N, TORCH_W = 2059, 2061
FENCE_V = 1518                                          # baranda de madera vertical (la más usada)
GRASS, WOOD = 4756, 405
FLOWERS = (4158, 2740)
LANTERN = 3744

# --- casas: pared exterior (x0, y0, x1, y1), puerta, ventanas, hueco al patio, patio ----------------
WALL_TOP, WALL_BOTTOM = 59, 63
HOUSES = {
    "River Street III": dict(x0=145, x1=149, door=148, win_n=147, opening=147, patio=(146, 148), fence=149),
    "River Street IV": dict(x0=151, x1=155, door=153, win_n=154, opening=None, patio=None, fence=None,
                            win_s=153),
    "River Street V": dict(x0=157, x1=161, door=158, win_n=159, opening=159, patio=(158, 160), fence=157),
}
PATIO_Y = (64, 65)
LANES = (150, 156)                                      # pasillos de la calle al río
JOIN_Y = (64, 65)                                       # debajo de IV se juntan los pasillos
BRIDGE_X, BRIDGE_Y = 153, (66, 72)                      # puente de 1 casilla: orilla norte a orilla sur
SOUTH_PATH = (152, 154, 73, 77)                         # camino de tierra del puente al arco de los trolls
ARCH = (153, 78)                                        # arco de piedra de las ruinas de los trolls
LANTERN_MOVE = ((161, 59), (162, 59))                   # el farol de la esquina pasa 1 al este
STREET = [(150, 58), (156, 58)]                         # calle frente a cada pasillo
REGION = (144, 58, 162, 78)                             # solo se tocan casillas acá adentro

# --- orilla: pasto con borde sobre agua (4526 + pieza); bajo una pared se conserva la pieza ---------
SHORE_GROUND, SHORE = 4526, range(4644, 4656)
WATER = 4608

# --- camino de tierra: piso con el borde de pasto ya dibujado (medidos en el mapa, 79-83 al sur) ---
DIRT = 103
DIRT_EDGE = {"n": 110, "s": 111, "w": 112, "e": 113,
             "nw": 114, "ne": 115, "se": 116, "sw": 117}             # pasto de ese lado / esquina externa
DIRT_INNER = {"nw": 118, "ne": 119, "se": 120, "sw": 121}            # solo la diagonal es pasto

# --- puente de sogas: copiado del puente del mapa en 181-184, 80-88 (piso 405 en el medio) -----------
# Columna oeste (x-1) y este (x+1) del piso: borde de madera 436/437 sobre agua y soga encima.
BRIDGE_WEST = {"north": [436, None, 3761, 3775], "water": [436, 3777], "last": [436, 3789],
               "south": [436, None, 3791, 3779], "post": 3761}       # None = la pieza de orilla existente
BRIDGE_EAST = {"north": [437, None, 3774, 3760], "water": [437, 3776], "knot": [437, 3790, 3776],
               "south": [437, None, 3778], "post": 3760}
SWAMP_SMALL, SWAMP_BIG = 2771, 2777
BANK_PLANTS = {(151, 66): SWAMP_SMALL, (156, 72): SWAMP_BIG}         # plantas de orilla junto al puente


def desired(existing: dict) -> tuple[dict, dict, dict]:
    """Casillas nuevas {pos: (ground_items, pz)} y tiles de cada casa."""
    out, house_tiles = {}, {}
    street_base = lambda x: existing[(x, WALL_TOP)][:2]  # noqa: E731  adoquín + pasto de la fila de la calle
    for name, h in HOUSES.items():
        x0, x1 = h["x0"], h["x1"]
        inner = {(x, y) for x in range(x0 + 1, x1) for y in range(WALL_TOP + 1, WALL_BOTTOM)}
        line = {(x, y) for x in range(x0, x1 + 1) for y in range(WALL_TOP, WALL_BOTTOM + 1)} - inner
        opening = (h["opening"], WALL_BOTTOM) if h["opening"] else None
        if opening:
            line.discard(opening)
        for (x, y) in sorted(line):
            w, n = (x - 1, y) in line, (x, y - 1) in line
            piece = CORNER if w and n else HORIZ if w else VERT if n else POST
            if y == WALL_TOP:
                ground = list(street_base(x))
            elif x == x0:
                ground = [GRASS]                        # columna oeste: suelo de afuera (PIEZAS_DE_MAPA.md)
                old = existing[(x, y)]
                if old[0] == SHORE_GROUND and len(old) > 1 and old[1] in SHORE:
                    ground = old[:2]                    # la pared queda sobre la orilla: el borde del agua sigue
            else:
                ground = [WOOD]
            items = [piece]
            if (x, y) == (h["door"], WALL_TOP):
                items = [DOOR]
            elif (x, y) == (h["win_n"], WALL_TOP):
                items = [WIN_H]
            elif (x, y) == (x0 + 1, WALL_TOP) and h["door"] != x0 + 1:
                items = [HORIZ, TORCH_N]
            elif (x, y) == (x1 - 1, WALL_TOP) and h["door"] == x0 + 1:
                items = [HORIZ, TORCH_N]
            elif h.get("win_s") and (x, y) == (h["win_s"], WALL_BOTTOM):
                items = [WIN_H]
            elif (x, y) == (x0, WALL_TOP + 2):
                items = [VERT, TORCH_W]
            elif (x, y) == (x1, WALL_TOP + 2):
                items = [WIN_V]
            out[(x, y)] = (ground + items, False)
        tiles = set(inner)
        for c in inner:
            out[c] = ([WOOD], True)
        if opening:
            out[opening] = ([WOOD], True)
            tiles.add(opening)
            px0, px1 = h["patio"]
            for x in range(px0, px1 + 1):
                for y in PATIO_Y:
                    old = existing[(x, y)]
                    if old[0] == SHORE_GROUND and len(old) > 1 and old[1] in SHORE:
                        out[(x, y)] = (old[:2], False)  # esquina de orilla: se respeta la curva del río
                        continue
                    flower = [FLOWERS[(x + y) % 2]] if (x + y) % 3 == 0 else []
                    out[(x, y)] = ([GRASS] + flower, True)
                    tiles.add((x, y))
            for y in PATIO_Y:
                out[(h["fence"], y)] = ([GRASS, FENCE_V], False)
        house_tiles[name] = tiles

    # camino de tierra: los dos pasillos, la explanada bajo IV y del puente al arco de los trolls
    dirt = {(x, y) for x in LANES for y in range(WALL_TOP + 1, JOIN_Y[1] + 1)}
    dirt |= {(x, y) for x in range(LANES[0], LANES[1] + 1) for y in JOIN_Y}
    sx0, sx1, sy0, sy1 = SOUTH_PATH
    dirt |= {(x, y) for x in range(sx0, sx1 + 1) for y in range(sy0, sy1 + 1)}
    bridge = {(BRIDGE_X, y) for y in range(BRIDGE_Y[0], BRIDGE_Y[1] + 1)}
    # sin borde de pasto contra: paredes y casas, el puente, la calle y el muro/arco de las ruinas
    hard = set(out) | bridge | {(x, WALL_TOP) for x in LANES}
    hard |= {(x, ARCH[1]) for x in range(sx0 - 1, sx1 + 1)}
    hard -= {c for c, (it, _pz) in out.items() if it[-1] == FENCE_V}  # la baranda está sobre pasto
    hard -= {c for c, (_it, pz) in out.items() if pz and c[1] in PATIO_Y}
    for c in sorted(dirt):
        out[c] = ([dirt_ground(c, dirt, hard)], False)
        rest = [i for i in existing[c][1:] if i != 4015]                  # planta que tapaba el puente
        if c[1] > JOIN_Y[1] and rest:                                     # al norte eran las casas viejas
            raise SystemExit(f"ERROR: {c} tiene {rest}; el camino no lo pisa")
    for x in LANES:                                                       # la calle sin flequillo de pasto
        out[(x, WALL_TOP)] = (existing[(x, WALL_TOP)][:1], False)

    # puente de sogas
    y0, y1 = BRIDGE_Y
    for c in bridge:
        out[c] = ([WOOD], False)
    for x, kit in ((BRIDGE_X - 1, BRIDGE_WEST), (BRIDGE_X + 1, BRIDGE_EAST)):
        for y in range(y0, y1 + 1):
            old = existing[(x, y)]
            if y in (y0, y1):
                if old[0] != SHORE_GROUND or len(old) != 2 or old[1] not in SHORE:
                    raise SystemExit(f"ERROR: ({x},{y}) no es orilla simple: {old}")
                kind = "north" if y == y0 else "south"
                out[(x, y)] = ([SHORE_GROUND] + [old[1] if i is None else i for i in kit[kind]], False)
            else:
                if old != [WATER]:
                    raise SystemExit(f"ERROR: ({x},{y}) no es agua: {old}")
                kind = "last" if y == y1 - 1 and "last" in kit else \
                       "knot" if "knot" in kit and (y - y0) % 2 == 0 else "water"
                out[(x, y)] = ([WATER] + kit[kind], False)
        post = (x, y1 + 1)
        out[post] = (out[post][0] + [kit["post"]], False)                # postes en la punta sur
    for c, plant in BANK_PLANTS.items():
        old = existing[c]
        if old[0] != SHORE_GROUND or len(old) != 2:
            raise SystemExit(f"ERROR: {c} no es orilla simple: {old}")
        out[c] = (old + [plant], False)

    src, dst = LANTERN_MOVE
    out[dst] = (list(existing[dst]) + [LANTERN], False)
    return out, house_tiles, {"street_base": street_base, "dirt": dirt}


def dirt_ground(c, dirt: set, hard: set) -> int:
    """Piso de tierra con el borde de pasto que le toca según sus vecinos."""
    x, y = c
    def grass(dx, dy):  # noqa: E306
        n = (x + dx, y + dy)
        return n not in dirt and n not in hard
    side = {k: grass(dx, dy) for k, (dx, dy) in {"n": (0, -1), "s": (0, 1), "w": (-1, 0), "e": (1, 0)}.items()}
    if (side["n"] and side["s"]) or (side["w"] and side["e"]):
        raise SystemExit(f"ERROR: {c}: camino de tierra de 1 casilla, no hay pieza para eso")
    for k in ("nw", "ne", "se", "sw"):
        if side[k[0]] and side[k[1]]:
            return DIRT_EDGE[k]
    for k in ("n", "s", "w", "e"):
        if side[k]:
            return DIRT_EDGE[k]
    diag = [k for k, (dx, dy) in {"nw": (-1, -1), "ne": (1, -1), "se": (1, 1), "sw": (-1, 1)}.items()
            if grass(dx, dy)]
    return DIRT_INNER[diag[0]] if len(diag) == 1 else DIRT


# --- mapa crudo -----------------------------------------------------------------------------------
def read_region(root) -> dict:
    """{(x, y): (node, area)} de las casillas de REGION en z7, con sus ítems crudos."""
    out = {}
    for area in root[2][0][2]:
        if area[0] != T_AREA:
            continue
        ax, ay, az = struct.unpack_from("<HHB", bytes(area[1]), 0)
        if az != Z:
            continue
        for t in area[2]:
            if t[0] not in (T_TILE, T_HOUSETILE):
                continue
            x, y = ax + t[1][0], ay + t[1][1]
            if REGION[0] <= x <= REGION[2] and REGION[1] <= y <= REGION[3]:
                out[(x, y)] = (t, area, (ax, ay))
    return out


def stack_of(node) -> list[int]:
    props = bytes(node[1])
    ground = []
    pos = 2
    while pos < len(props):
        a = props[pos]
        if a == 3:
            pos += 5
        elif a == 9:
            ground = [struct.unpack_from("<H", props, pos + 1)[0]]
            pos += 3
        else:
            break
    return ground + [struct.unpack_from("<H", bytes(i[1]), 0)[0] for i in node[2] if i[0] == T_ITEM]


def new_node(x, y, base, items, pz):
    props = bytearray([x - base[0], y - base[1]])
    if pz:
        props += b"\x03" + struct.pack("<I", 1)
    props += b"\x09" + struct.pack("<H", items[0])
    return [T_TILE, props, [[T_ITEM, bytearray(struct.pack("<H", i)), []] for i in items[1:]]]


# --- validación -----------------------------------------------------------------------------------
def bfs(walk: set, start) -> set:
    seen, q = {start}, deque([start])
    while q:
        x, y = q.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in walk and n not in seen:
                seen.add(n)
                q.append(n)
    return seen


def validate(region: dict, out: dict, house_tiles: dict, otb: dict) -> list[str]:
    errs = []
    solid = {sid for sid, r in otb.items() if "block_solid" in r["flags"]}
    for c in out:
        if c not in region:
            errs.append(f"{c}: no hay casilla en el mapa")
            continue
        node = region[c][0]
        if any(len(bytes(i[1])) > 2 or i[2] for i in node[2]):
            errs.append(f"{c}: tiene ítems con atributos o contenido; no se toca")
    for name in HOUSES:
        f = DATA / "houses" / f"{name}.xml"
        if 'owner name=""' not in f.read_text(encoding="utf-8"):
            errs.append(f"{name}: tiene dueño ({f.name}); no se cambia una casa ocupada")
    hi = DATA / "houseitems.xml"
    if hi.exists():
        saved = {(int(a), int(b)) for a, b, z in re.findall(r'<tile x="(\d+)" y="(\d+)" z="(\d+)"', hi.read_text(errors="replace"))
                 if int(z) == Z}
        old = {c for c in region if REGION[0] <= c[0] <= REGION[2]}
        if saved & old:
            errs.append(f"houseitems.xml tiene ítems en la zona: {sorted(saved & old)[:5]}")
    # caminable (casas incluidas: el chequeo de patios lo hace aparte)
    world = {c: stack_of(v[0]) for c, v in region.items()}
    world.update({c: it for c, (it, _pz) in out.items()})
    walk = {c for c, it in world.items() if it and not any(i in solid for i in it)}
    houses = set().union(*house_tiles.values())
    public = walk - houses
    for s in STREET:
        if ARCH not in bfs(public, s):
            errs.append(f"desde la calle {s} no se llega por el puente al arco de los trolls {ARCH}")
    for name, tiles in house_tiles.items():
        h = HOUSES[name]
        inside = bfs(walk & (tiles | {(h["door"], WALL_TOP)}), (h["door"], WALL_TOP))
        if not tiles <= inside:
            errs.append(f"{name}: {len(tiles - inside)} casillas de la casa no se alcanzan desde la puerta")
        if h["patio"]:
            patio = {c for c in tiles if c[1] in PATIO_Y}
            if patio & bfs(public | patio, STREET[0]):
                errs.append(f"{name}: al patio se entra sin pasar por la casa")
    return errs


def write_houses(house_tiles: dict):
    src = HOUSES_XML.read_text(encoding="utf-8")
    for name, tiles in house_tiles.items():
        body = "\n".join(f'<tile x="{x}" y="{y}" z="{Z}" />' for x, y in sorted(tiles))
        pat = re.compile(rf'<house name="{re.escape(name)}">.*?</house>', re.S)
        if not pat.search(src):
            raise SystemExit(f"ERROR: {name} no está en houses.xml")
        src = pat.sub(lambda _m: f'<house name="{name}">\n{body}\n</house>', src, count=1)
    HOUSES_XML.write_text(src, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--png", type=Path)
    a = ap.parse_args()

    otb = load_otb()
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    region = read_region(root)
    existing = {c: stack_of(v[0]) for c, v in region.items()}
    if BRIDGE_WEST["post"] in existing[(BRIDGE_X - 1, BRIDGE_Y[0])]:
        print("River Street: el mapa ya tiene este cambio (puente de sogas); no hay nada que hacer")
        return 0
    out, house_tiles, _ = desired(existing)
    errs = validate(region, out, house_tiles, otb)
    print(f"River Street: {len(out)} casillas cambiadas; " +
          ", ".join(f"{n.split()[-1]} {len(t)} casillas" for n, t in house_tiles.items()))
    if a.png:
        world = {(x, y, Z): stack_of(v[0]) for (x, y), v in region.items()}
        world.update({(x, y, Z): it for (x, y), (it, _pz) in out.items()})
        w, h, rgba = Renderer().area(world, REGION[0], REGION[1], REGION[2] + 1, REGION[3] + 1, Z)
        a.png.write_bytes(png_bytes(w, h, rgba))
        print(f"PNG {a.png}")
    if errs:
        print("ERRORES:\n  " + "\n  ".join(errs))
        return 1
    if a.dry_run or not a.replace:
        print("(dry-run)" if a.dry_run else "usá --replace para escribir")
        return 0

    for c, (items, pz) in out.items():
        node, area, base = region[c]
        area[2][area[2].index(node)] = new_node(c[0], c[1], base, items, pz)
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    write_houses(house_tiles)
    spec = importlib.util.spec_from_file_location("shm", HERE / "sync-houses-with-map.py")
    shm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shm)
    bad = shm.sync_houses(MAP, HOUSES_XML, dry_run=True)
    if bad:
        print(f"ERROR: houses.xml no coincide con el mapa ({bad} tiles)", file=sys.stderr)
        return 1
    print(f"OK {MAP} y houses.xml (River Street III, IV, V)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
