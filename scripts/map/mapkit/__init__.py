"""mapkit: motor único para generar zonas de mapa (nov 2026).

Una zona se describe con una ficha corta (`scripts/map/zones/<zona>.json`), usa un tema del catálogo
(`themes.json`) y una receta (`island.py`, ...). `build.py` prueba varias semillas, las mide con `lint.py`
y, si hace falta, deja que jev (`jev.py`) elija entre las mejores. Guía: docs/items-and-map/MAPAS.md.

Este módulo junta lo que antes estaba copiado en cada generador: geometría, piezas de borde (costa,
tierra, paredes), ruido, recorridos, spawns por etapas y la escritura segura en test.otbm con
manifiesto de dueño (nunca pisa casillas ajenas).
"""
from __future__ import annotations

import json
import math
import re
import shutil
import struct
import sys
from collections import deque
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAPDIR = HERE.parent
for _p in (str(MAPDIR), str(MAPDIR / "kb")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import mapdata  # noqa: E402
from mapdata import MAP, REPO, DIRS, load_otb, load_tiles, parse_tree, png_bytes, serialize_tree  # noqa: E402

WORLD = MAP.parent
ZONES = MAPDIR / "zones"
SPAWNS = WORLD / "test-spawn.xml"
NPCS = WORLD / "npc.xml"
READABLES = REPO / "server/YurOTS/ots/data/readables.xml"
MONSTERS = REPO / "server/YurOTS/ots/data/monster/monsters.xml"
BOAT = REPO / "server/YurOTS/ots/data/npc/scripts/boat.lua"

VIEW = (9, 7)                          # media pantalla + colchón: nada de vacío a esta distancia
CARD = ((1, 0), (-1, 0), (0, 1), (0, -1))
ALL8 = tuple(DIRS.values())
DIAG_SIDES = {"nw": ("n", "w"), "ne": ("n", "e"), "sw": ("s", "w"), "se": ("s", "e")}


# --- geometría --------------------------------------------------------------------------------------

def grow(cells, r: int) -> set:
    return {(x + dx, y + dy) for (x, y) in cells for dx in range(-r, r + 1) for dy in range(-r, r + 1)}


def box_cells(b) -> set:
    x0, y0, x1, y1 = b
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def reach(walk: set, start, steps=CARD) -> dict:
    """BFS caminando: casilla -> pasos."""
    dist = {start: 0}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in steps:
            n = (x + dx, y + dy)
            if n in walk and n not in dist:
                dist[n] = dist[(x, y)] + 1
                q.append(n)
    return dist


def neighbors_in(mask, x, y) -> set:
    return {d for d, (dx, dy) in DIRS.items() if (x + dx, y + dy) in mask}


class Noise:
    """Value noise 2D con octavas (determinista por semilla)."""

    def __init__(self, seed: int):
        self.seed = seed

    def _h(self, x: int, y: int, o: int) -> float:
        n = (x * 374761393 + y * 668265263 + (self.seed + o * 1013) * 2147483647) & 0xFFFFFFFF
        n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 0xFFFF

    def _v(self, x: float, y: float, o: int) -> float:
        xi, yi = math.floor(x), math.floor(y)
        fx, fy = x - xi, y - yi
        sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a, b = self._h(xi, yi, o), self._h(xi + 1, yi, o)
        c, d = self._h(xi, yi + 1, o), self._h(xi + 1, yi + 1, o)
        return (a + (b - a) * sx) + ((c + (d - c) * sx) - (a + (b - a) * sx)) * sy

    def fbm(self, x: float, y: float, octaves=3, o=0) -> float:
        s, amp, f, norm = 0.0, 1.0, 1.0, 0.0
        for i in range(octaves):
            s += amp * self._v(x * f, y * f, o + i)
            norm += amp
            amp *= 0.5
            f *= 2.0
        return s / norm


def polyline(points, step=0.5):
    """Puntos cada `step` casillas a lo largo de una polilínea: [(x, y, recorrido)]."""
    out, run = [], 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(seg / step))
        for i in range(n):
            t = i / n
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, run + seg * t))
        run += seg
    out.append((*points[-1], run))
    return out


def chaikin(points, rounds=2):
    """Redondea las esquinas de un recorrido (los extremos quedan fijos)."""
    pts = [tuple(map(float, p)) for p in points]
    for _ in range(rounds):
        new = [pts[0]]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            new += [(0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1), (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)]
        new.append(pts[-1])
        pts = new
    return pts


def blob(center, rx, ry, noise: Noise, wobble=0.3, o=0) -> set:
    """Mancha elíptica con borde irregular (claros, lagunas)."""
    cx, cy = center
    out = set()
    for x in range(int(cx - rx * 1.5) - 1, int(cx + rx * 1.5) + 2):
        for y in range(int(cy - ry * 1.5) - 1, int(cy + ry * 1.5) + 2):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d <= 1 + wobble * (noise.fbm(x / 4, y / 4, 2, o) - 0.5) * 2:
                out.add((x, y))
    return out


# --- piezas de borde ----------------------------------------------------------------------------------

class Border:
    """Familia de bordes de 12 piezas (costa, tierra sobre pasto, paredes de cueva).

    La pieza va en la casilla de AFUERA de la forma y sale de en qué lados está la forma:
    `side[d]`, `corner[(ns, ew)]` (dos lados), `inner[diag]` (solo en diagonal)."""

    def __init__(self, spec: dict):
        self.side = {k: int(v) for k, v in spec["side"].items()}
        self.corner = {tuple(k.split(",")): int(v) for k, v in spec["corner"].items()}
        self.inner = {k: int(v) for k, v in spec["inner"].items()}
        self.ids = set(self.side.values()) | set(self.corner.values()) | set(self.inner.values())

    def pieces(self, other: set) -> list | None:
        card = other & {"n", "e", "s", "w"}
        if {"n", "s"} <= card or {"e", "w"} <= card:
            return None
        out = []
        if len(card) == 2:
            out.append(self.corner[(next(c for c in card if c in "ns"), next(c for c in card if c in "ew"))])
        elif len(card) == 1:
            out.append(self.side[next(iter(card))])
        for diag, (a, b) in DIAG_SIDES.items():
            if diag in other and a not in card and b not in card:
                out.append(self.inner[diag])
        return out

    def piece_at(self, shape: set, c) -> int | None:
        """La única pieza de la casilla `c` (afuera de `shape`), None si no toca, error si es ambigua."""
        near = neighbors_in(shape, *c)
        if not near:
            return None
        pcs = self.pieces(near)
        if pcs is None or len(pcs) != 1:
            raise RuntimeError(f"borde ambiguo en {c}: {sorted(near)} -> {pcs}")
        return pcs[0]

    def settle(self, shape: set, allowed: set) -> set:
        """Agranda `shape` (sin salir de `allowed`) hasta que todo su contorno tenga UNA pieza válida, y saca
        las casillas de 1 de ancho. Es lo que hace que la forma "cierre" con las piezas que existen."""
        shape = set(shape)
        for _ in range(400):
            changed = False
            for (x, y) in list(shape):
                out = {d for d, (dx, dy) in DIRS.items() if (x + dx, y + dy) not in shape}
                if {"n", "s"} <= out or {"e", "w"} <= out:
                    shape.discard((x, y))
                    changed = True
            ring = grow(shape, 1) - shape
            for c in ring:
                if c not in allowed:
                    continue
                pcs = self.pieces(neighbors_in(shape, *c))
                if pcs is None or len(pcs) > 1:
                    shape.add(c)
                    changed = True
            if not changed:
                return shape
        raise RuntimeError("los bordes no convergen")


# --- catálogo de temas ----------------------------------------------------------------------------------

class Theme(dict):
    def border(self, key) -> Border:
        return Border(self[key])


def load_theme(name: str) -> Theme:
    data = json.loads((HERE / "themes.json").read_text())
    if name not in data:
        raise SystemExit(f"tema desconocido: {name} (hay: {', '.join(k for k in data if not k.startswith('_'))})")
    return Theme(data[name])


class Otb:
    def __init__(self):
        self.otb = load_otb()

    def blocks(self, sid: int) -> bool:
        return "block_solid" in self.otb.get(sid, {}).get("flags", [])

    def walkable(self, ids) -> bool:
        return bool(ids) and not any(self.blocks(i) for i in ids)

    def stackable(self, sid: int) -> bool:
        return "stackable" in self.otb.get(sid, {}).get("flags", [])

    def is_ground(self, sid: int) -> bool:
        return self.otb.get(sid, {}).get("group") == "ground"

    def loose(self, sid: int) -> bool:
        """Se levanta o se empuja (no sirve como decoración fija)."""
        f = self.otb.get(sid, {}).get("flags", [])
        return "pickupable" in f or "moveable" in f


# --- monstruos y spawns ---------------------------------------------------------------------------------

def known_monsters() -> set:
    return set(re.findall(r'name="([^"]+)"', MONSTERS.read_text(encoding="latin-1")))


def slices_by(cells, key, n):
    order = sorted(cells, key=lambda c: (key(c), c))
    size = len(order) / n
    return [set(order[int(i * size):int((i + 1) * size)]) for i in range(n)]


def place_stages(stages, slices, walk, avoid, z, rng):
    """Etapas (nombres, por spawn, spawntime, separación) en sus franjas, de fácil a difícil. Cada spawn queda a
    `separación` (Manhattan) de TODOS los centros ya puestos; necesita `por spawn + 3` casillas libres a 2."""
    out, centers = [], []
    for st, pool in zip(stages, slices):
        names, per, spawntime, gap = st["monsters"], st["per"], st["spawntime"], st["gap"]
        cands = sorted((pool & walk) - avoid)
        rng.shuffle(cands)
        k = 0
        for c in cands:
            if any(abs(c[0] - o[0]) + abs(c[1] - o[1]) < gap for o in centers):
                continue
            spots = [(c[0] + dx, c[1] + dy) for dx in range(-2, 3) for dy in range(-2, 3)
                     if (c[0] + dx, c[1] + dy) in walk and (c[0] + dx, c[1] + dy) not in avoid]
            if len(spots) < per + 3:
                continue
            rng.shuffle(spots)
            centers.append(c)
            out.append((c, z, [(names[(k + i) % len(names)], s, spawntime) for i, s in enumerate(spots[:per])]))
            k += per
    return out


def spawn_xml(spawns) -> str:
    lines = []
    for (cx, cy), z, mons in spawns:
        lines.append(f'\t<spawn centerx="{cx}" centery="{cy}" centerz="{z}" radius="3">')
        for name, (mx, my), st in mons:
            lines.append(f'\t\t<monster name="{name}" x="{mx - cx}" y="{my - cy}" z="{z}" spawntime="{st}" />')
        lines.append("\t</spawn>")
    return "\n".join(lines)


def xml_block(text: str, key: str, body: str, close: str, src: str) -> str:
    """Reemplaza (o agrega antes de `close`) el bloque <!-- BEGIN key --> ... <!-- END key -->."""
    marked = f"\t<!-- BEGIN {key} ({src}) -->\n{body}\n\t<!-- END {key} -->\n"
    pattern = rf"[ \t]*<!-- BEGIN {key}(?: \([^>]*\))? -->.*?<!-- END {key} -->\n?"
    if re.search(pattern, text, re.S):
        return re.sub(pattern, lambda _: marked, text, count=1, flags=re.S)
    return text.replace(close, marked + close, 1)


def readable_line(x, y, z, text: str) -> str:
    from xml.sax.saxutils import escape
    return f'\t<readable x="{x}" y="{y}" z="{z}" text="{escape(text, {chr(34): "&quot;"}).replace(chr(10), chr(92) + "n")}"/>'


# --- escritura segura en test.otbm ----------------------------------------------------------------------

def item_node(iid: int, otb: Otb):
    props = bytearray(struct.pack("<H", iid))
    if otb.stackable(iid):
        props.append(1)                  # los apilables llevan cantidad o el mapa no carga
    return [mapdata.T_ITEM, props, []]


def _index(root):
    from epstein_cave_repair import index
    return index(root, load_otb())


def _tile_flags(props):
    from portal_citadel_layout import tile_flags
    return tile_flags(props)


def write_cells(cells: dict, manifest: Path, filler: list, name: str, report: dict, dry_run: bool,
                extra_files=(), claims=None) -> int:
    """Escribe `cells` {(x, y, z): [ids]} en test.otbm. Solo pisa casillas vacías o que el manifiesto anterior
    dice que son de esta zona (y no cambiaron desde entonces); nunca casas, flags ni ítems con atributos.
    `claims` {(x, y, z): [ids originales]}: casillas ajenas que la zona toma a propósito (la bajada de una cueva);
    solo si siguen como se las vio, y el manifiesto guarda lo original para devolverlo si la zona las suelta.
    Casillas que eran de la zona y ya no están en `cells` vuelven a `filler` (o a lo original). Devuelve cuántas
    cambian."""
    otb = Otb()
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    nodes, values, areas = _index(root)
    dup = [p for p, ns in nodes.items() if len(ns) != 1]
    if dup:
        raise SystemExit(f"casillas duplicadas en el mapa: {dup[:4]}")
    mf = json.loads(manifest.read_text()) if manifest.exists() else {}
    previous, claimed_before = mf.get("cells", {}), mf.get("claimed", {})
    claims = claims or {}
    cells = dict(cells)
    for p, ids in cells.items():
        old = values.get(p)
        owned = previous.get(",".join(map(str, p))) == old
        if old is not None and not owned and claims.get(p) != old:
            raise SystemExit(f"casilla ajena protegida: {p}: {old}")
        for tile in nodes.get(p, []):
            if tile[0] != mapdata.T_TILE or _tile_flags(tile[1]):
                raise SystemExit(f"casa o flags protegidos: {p}")
            if any(c[0] != mapdata.T_ITEM or len(c[1]) not in (2, 3) or c[2] for c in tile[2]):
                raise SystemExit(f"ítem con atributos protegido: {p}")
    for key, ids in previous.items():
        p = tuple(int(n) for n in key.split(","))
        if p not in cells and values.get(p) == ids:
            cells[p] = list(claimed_before.get(key, filler))
    changed = sum(values.get(p) != ids for p, ids in cells.items())
    if dry_run:
        return changed
    backup = REPO / "backups/map" / f"{name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup.mkdir(parents=True)
    for f in (MAP, *extra_files):
        shutil.copy2(f, backup / Path(f).name)
    for (x, y, z), ids in sorted(cells.items()):
        key = (x // 256 * 256, y // 256 * 256, z)
        if key not in areas:
            areas[key] = [mapdata.T_AREA, bytearray(struct.pack("<HHB", *key)), []]
            root[2][0][2].append(areas[key])
        if (x, y, z) in nodes:
            tile = nodes[(x, y, z)][0]
        else:
            tile = [mapdata.T_TILE, bytearray([x % 256, y % 256]), []]
            areas[key][2].append(tile)
            nodes[(x, y, z)] = [tile]
        ground = otb.is_ground(ids[0])
        tile[1] = bytearray([x % 256, y % 256]) + (struct.pack("<BH", 9, ids[0]) if ground else b"")
        tile[2] = [item_node(i, otb) for i in ids[1 if ground else 0:]]
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    claimed = {k: v for k, v in claimed_before.items() if tuple(int(n) for n in k.split(",")) in claims}
    for p, ids in claims.items():
        claimed.setdefault(",".join(map(str, p)), list(ids))
    keep = {",".join(map(str, p)): ids for p, ids in sorted(cells.items())
            if ",".join(map(str, p)) not in claimed_before or p in claims}
    out = dict(name=name, **report, cells=keep)
    if claimed:
        out["claimed"] = claimed
    manifest.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    return changed


# --- vista previa ---------------------------------------------------------------------------------------

def preview(cells: dict, box, z: int, path: Path, max_side=1400, marks=()):
    """PNG con los sprites reales: el mapa actual con `cells` encima. `marks` = casillas a resaltar (monstruos)."""
    tiles = load_tiles()
    tiles.update(cells)
    x0, y0, x1, y1 = box
    W, H, img = mapdata.Renderer().area(tiles, x0, y0, x1, y1, z)
    for (mx, my) in marks:
        if not (x0 <= mx <= x1 and y0 <= my <= y1):
            continue
        bx, by = (mx - x0) * 32, (my - y0) * 32
        for i in range(8, 24):
            for X, Y in ((bx + i, by + 16), (bx + 16, by + i)):
                o = (Y * W + X) * 4
                img[o:o + 4] = b"\xff\x20\x20\xff"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes(W, H, bytes(img)))
    try:
        from PIL import Image
        im = Image.open(path)
        im.thumbnail((max_side, max_side))
        im.save(path)
    except ImportError:
        pass
    return path
