#!/usr/bin/env python3
"""Hechos deterministas de cada pieza del mapa (sin LLM).

Salida (docs/items-and-map/map-kb/):
  facts.json      server_id -> flags, capa, uso en test.otbm, vecinos por dirección
  adjacency.json  pares (pieza A, dirección, pieza B) con conteos, solo suelos y bordes
  zones.json      zonas generadas (generated-*.json) con su caja y generador
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from mapdata import DIRS, KB_DIR, REPO, WORLD, dat_facts, layer_of, load_otb, load_tiles, parse_dat

TOP = 5


def top(counter: Counter, otb, n=TOP):
    total = sum(counter.values()) or 1
    return [{"id": k, "name": otb.get(k, {}).get("name", ""), "share": round(v / total, 3)}
            for k, v in counter.most_common(n)]


def main() -> None:
    otb, dat = load_otb(), parse_dat()
    tiles = load_tiles()
    layer = {}
    for sid, r in otb.items():
        e = dat.get(r.get("cid"))
        if e:
            layer[sid] = layer_of(e)

    def ground_of(items):
        for s in items:
            if layer.get(s) == "ground":
                return s
        return None

    ground_at = {pos: ground_of(items) for pos, items in tiles.items()}

    count = Counter()
    floors = defaultdict(Counter)
    samples = defaultdict(list)
    under = defaultdict(Counter)          # suelo debajo de la pieza
    with_items = defaultdict(Counter)     # otras piezas en la misma casilla
    nb_ground = defaultdict(lambda: defaultdict(Counter))  # dir -> suelo vecino
    nb_same = defaultdict(Counter)        # dir -> vecino tiene la misma pieza
    nb_diff_ground = defaultdict(Counter)  # dir -> el suelo vecino difiere del propio
    adjacency = Counter()

    for (x, y, z), items in tiles.items():
        g = ground_at[(x, y, z)]
        uniq = list(dict.fromkeys(items))
        for s in uniq:
            count[s] += 1
            floors[s][z] += 1
            if len(samples[s]) < 40:
                samples[s].append([x, y, z])
            if g is not None and s != g:
                under[s][g] += 1
            for o in uniq:
                if o != s and o != g:
                    with_items[s][o] += 1
            for d, (dx, dy) in DIRS.items():
                npos = (x + dx, y + dy, z)
                nitems = tiles.get(npos)
                if nitems is None:
                    nb_ground[s][d][-1] += 1  # -1 = vacío
                    continue
                ng = ground_at.get(npos)
                nb_ground[s][d][ng if ng is not None else 0] += 1
                if s in nitems:
                    nb_same[s][d] += 1
                if g is not None and ng != g:
                    nb_diff_ground[s][d] += 1
                if layer.get(s) in ("ground", "border"):
                    for o in dict.fromkeys(nitems):
                        if layer.get(o) in ("ground", "border"):
                            adjacency[(s, d, o)] += 1

    candidates = set(count)
    for sid, r in otb.items():
        e = dat.get(r.get("cid"))
        if e and 0x10 not in e["flags"]:
            candidates.add(sid)

    facts = {}
    for sid in sorted(candidates):
        r = otb.get(sid, {})
        e = dat.get(r.get("cid"))
        if e is None:
            continue
        n = count[sid]
        f = {"id": sid, "client_id": r.get("cid"), "name": r.get("name", ""),
             "otb_group": r["group"], "otb_flags": r["flags"], "layer": layer[sid],
             **dat_facts(e), "map_uses": n}
        if n:
            f["floors"] = dict(sorted(floors[sid].items()))
            step = max(1, len(samples[sid]) // 5)
            f["sample_positions"] = samples[sid][::step][:5]
            f["ground_under"] = top(under[sid], otb)
            f["same_tile_items"] = top(with_items[sid], otb)
            f["same_item_neighbor_share"] = {d: round(nb_same[sid][d] / n, 3) for d in DIRS}
            f["different_ground_neighbor_share"] = {d: round(nb_diff_ground[sid][d] / n, 3) for d in DIRS}
            f["neighbor_ground"] = {d: [{"id": k, "share": round(v / n, 3)}
                                        for k, v in nb_ground[sid][d].most_common(3)] for d in DIRS}
        facts[str(sid)] = f

    KB_DIR.mkdir(parents=True, exist_ok=True)
    (KB_DIR / "facts.json").write_text(json.dumps(
        {"_schema": "facts.v1", "_doc": "README.md", "items": facts}, ensure_ascii=False, indent=1))

    adj = [{"a": a, "dir": d, "b": b, "count": c} for (a, d, b), c in adjacency.items() if c >= 2]
    adj.sort(key=lambda r: (r["a"], r["dir"], -r["count"]))
    (KB_DIR / "adjacency.json").write_text(json.dumps(
        {"_schema": "adjacency.v1", "_note": "b aparece en la casilla vecina de a en dirección dir; solo suelos y bordes; count>=2",
         "pairs": adj}, ensure_ascii=False))

    zones = []
    for p in sorted(WORLD.glob("generated-*.json")):
        try:
            d = json.loads(p.read_text())
        except ValueError:
            continue
        gen = REPO / "scripts/map" / p.name.replace("generated-", "generate-").replace(".json", ".py")
        boxes, points = [], []
        box_keys = (("x0", "y0", "x1", "y1"), ("fromX", "fromY", "toX", "toY"), ("x1", "y1", "x2", "y2"))

        def walk(o, path=""):
            if isinstance(o, dict):
                for kx1, ky1, kx2, ky2 in box_keys:
                    if {kx1, ky1, kx2, ky2, "z"} <= set(o):
                        x1, y1, x2, y2, z = o[kx1], o[ky1], o[kx2], o[ky2], o["z"]
                        n = sum(1 for xx in range(x1, x2 + 1) for yy in range(y1, y2 + 1) if (xx, yy, z) in tiles)
                        boxes.append({"path": path or "/", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "z": z,
                                      "tiles_in_map": n, "tiles_in_box": (x2 - x1 + 1) * (y2 - y1 + 1)})
                        break
                else:
                    if {"x", "y", "z"} <= set(o) and all(isinstance(o[k], int) for k in "xyz"):
                        pos = (o["x"], o["y"], o["z"])
                        points.append({"path": path, "x": pos[0], "y": pos[1], "z": pos[2],
                                       "in_map": pos in tiles,
                                       "items": [{"id": s, "name": otb.get(s, {}).get("name", "")}
                                                 for s in tiles.get(pos, [])]})
                for k, v in o.items():
                    walk(v, f"{path}/{k}")
            elif isinstance(o, list):
                for i, v in enumerate(o[:60]):
                    walk(v, f"{path}/{i}")
        walk(d)
        zones.append({"zone": p.stem.replace("generated-", ""), "file": str(p.relative_to(REPO)),
                      "generator": str(gen.relative_to(REPO)) if gen.exists() else None,
                      "points_missing_in_map": sum(1 for q in points if not q["in_map"]),
                      "boxes": boxes[:40], "points": points[:80]})
    (KB_DIR / "zones.json").write_text(json.dumps({"_schema": "zones.v1", "zones": zones}, ensure_ascii=False, indent=1))

    print(f"facts: {len(facts)} piezas ({sum(1 for f in facts.values() if f['map_uses'])} usadas en el mapa)")
    print(f"adjacency: {len(adj)} pares; zones: {len(zones)}")


if __name__ == "__main__":
    main()
