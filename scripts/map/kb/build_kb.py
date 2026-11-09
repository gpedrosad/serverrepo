#!/usr/bin/env python3
"""Une hechos + etiquetas DeepSeek, corrige con reglas duras y revisa el mapa.

Salida (docs/items-and-map/map-kb/):
  pieces.json       pieza final: hechos clave + etiqueta + correcciones aplicadas
  review.json       piezas donde la etiqueta contradice los hechos o la confianza es baja
  border_sets.json  bordes agrupados por (suelo debajo, terreno del borde) y lado
  wall_sets.json    paredes agrupadas por material y parte
  map_lint.json     problemas detectados en test.otbm con coordenada y zona
  overview_z*.png   vista del mapa por piso (1 px = 1 casilla, color de minimapa)
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from mapdata import DIRS, KB_DIR, load_tiles, png_bytes

CACHE = KB_DIR / ".cache" / "labels"
NATURAL = {"grass", "dirt", "sand", "snow", "ice", "swamp", "mud", "gravel", "water", "lava", "cave"}


def load_labels() -> dict[int, dict]:
    out = {}
    for p in CACHE.glob("*.json"):
        rec = json.loads(p.read_text())
        out[rec["id"]] = rec
    return out


def harden(f: dict, label: dict) -> tuple[dict, list[dict]]:
    """Aplica reglas duras; devuelve etiqueta corregida y lista de correcciones."""
    lab = json.loads(json.dumps(label))
    fixes = []

    def fix(field, old, new, why):
        fixes.append({"field": field, "from": old, "to": new, "rule": why})

    flags = set(f["dat_flags"])
    layer = f["layer"]
    if layer == "ground" and lab["category"] != "ground":
        fix("category", lab["category"], "ground", "dat flag ground")
        lab["category"] = "ground"
    if layer != "border" and lab["border"]["is_border"]:
        fix("border.is_border", True, False, "sin flag ground_border")
        lab["border"] = {"is_border": False, "under_terrain": "none", "over_terrain": "none", "edge": "none"}
    if layer == "border" and not lab["border"]["is_border"] and lab["category"] == "ground_border":
        fix("border.is_border", False, True, "flag ground_border y categoría borde")
        lab["border"]["is_border"] = True
    blocking = "unpassable" in flags
    if lab["walkable_expected"] == blocking:
        fix("walkable_expected", lab["walkable_expected"], not blocking, "flag unpassable del .dat")
        lab["walkable_expected"] = not blocking
    if lab["category"] == "wall" and not lab["wall"]["is_wall"]:
        fix("wall.is_wall", False, True, "categoría wall")
        lab["wall"]["is_wall"] = True
    if lab["wall"]["is_wall"] and lab["category"] not in ("wall", "door", "window", "wall_decoration", "structure"):
        fix("wall.is_wall", True, False, f"categoría {lab['category']}")
        lab["wall"] = {"is_wall": False, "part": "none", "material": lab["wall"]["material"]}
    return lab, fixes


def main() -> None:
    facts = json.loads((KB_DIR / "facts.json").read_text())["items"]
    labels = load_labels()
    pieces, review = {}, []
    for k, f in facts.items():
        sid = int(k)
        rec = labels.get(sid)
        base = {k2: f[k2] for k2 in ("id", "name", "layer", "otb_group", "dat_flags", "size_tiles",
                                       "pattern", "map_uses") if k2 in f}
        if f.get("floors"):
            base["floors"] = f["floors"]
            base["sample_positions"] = f["sample_positions"]
        if rec is None:
            base["label"] = None
            pieces[k] = base
            continue
        lab, fixes = harden(f, rec["label"])
        base.update({"label": lab, "label_model": rec["model"], "label_fixes": fixes})
        pieces[k] = base
        reasons = [x["rule"] for x in fixes]
        if lab["confidence"] < 0.6:
            reasons.append(f"confianza {lab['confidence']}")
        if not lab["sprite_matches_name"]:
            reasons.append("sprite no coincide con el nombre (¿id Zagan reutilizado?)")
        if lab["border"]["is_border"] and lab["border"]["edge"] in ("unknown", "none"):
            reasons.append("borde sin lado")
        if reasons:
            review.append({"id": sid, "name": f["name"], "map_uses": f["map_uses"], "reasons": reasons})
    review.sort(key=lambda r: -r["map_uses"])

    # sets de bordes
    bsets = defaultdict(lambda: defaultdict(list))
    for k, p in pieces.items():
        lab = p.get("label")
        if lab and lab["border"]["is_border"]:
            key = f"{lab['border']['under_terrain']}->{lab['border']['over_terrain']}"
            bsets[key][lab["border"]["edge"]].append({"id": p["id"], "name": p["name"], "map_uses": p["map_uses"]})
    full_edges = ["n", "s", "e", "w", "nw_outer", "ne_outer", "sw_outer", "se_outer",
                  "nw_inner", "ne_inner", "sw_inner", "se_inner"]
    border_sets = []
    for key, edges in sorted(bsets.items(), key=lambda kv: -sum(len(v) for v in kv[1].values())):
        border_sets.append({"set": key, "edges": {e: sorted(v, key=lambda r: -r["map_uses"]) for e, v in edges.items()},
                            "missing_edges": [e for e in full_edges if e not in edges]})

    wsets = defaultdict(lambda: defaultdict(list))
    for k, p in pieces.items():
        lab = p.get("label")
        if lab and lab["wall"]["is_wall"]:
            wsets[lab["wall"]["material"]][lab["wall"]["part"]].append(
                {"id": p["id"], "name": p["name"], "map_uses": p["map_uses"]})
    wall_sets = [{"material": m, "parts": {pt: sorted(v, key=lambda r: -r["map_uses"]) for pt, v in parts.items()}}
                 for m, parts in sorted(wsets.items())]

    # revisión del mapa
    tiles = load_tiles()
    zones = json.loads((KB_DIR / "zones.json").read_text())["zones"]
    boxes = [(z["zone"], b) for z in zones for b in z["boxes"]]

    def zone_of(x, y, z):
        for name, b in boxes:
            if b["z"] == z and b["x1"] <= x <= b["x2"] and b["y1"] <= y <= b["y2"]:
                return name
        return None

    layer = {int(k): f["layer"] for k, f in facts.items()}
    terrain = {int(k): (p["label"] or {}).get("terrain") for k, p in pieces.items() if p.get("label")}
    issues = []

    def add(rule, pos, ids, detail):
        issues.append({"rule": rule, "x": pos[0], "y": pos[1], "z": pos[2], "zone": zone_of(*pos),
                       "ids": ids, "detail": detail})

    solid = {int(k) for k, f in facts.items() if "unpassable" in f["dat_flags"]}
    ground_at = {}
    for pos, items in tiles.items():
        grounds = [s for s in items if layer.get(s) == "ground"]
        ground_at[pos] = grounds[0] if grounds else None
        if items and not grounds and not any(s in solid for s in items):
            add("R1_sin_suelo", pos, items[:4], "casilla pisable sin suelo (ningún ítem bloquea): se ve vacío")
        if len(grounds) > 1:
            add("R2_dos_suelos", pos, grounds, "más de un suelo en la casilla")
    for pos, items in tiles.items():
        g = ground_at[pos]
        borders = [s for s in items if layer.get(s) == "border"]
        x, y, z = pos
        diff_dirs = [d for d, (dx, dy) in DIRS.items()
                     if (x + dx, y + dy, z) in tiles and ground_at.get((x + dx, y + dy, z)) not in (g, None)]
        if borders and g is not None and not diff_dirs:
            add("R3_borde_huerfano", pos, borders, "borde sin ningún vecino con otro suelo")
        if g is None or terrain.get(g) not in NATURAL:
            continue
        for d in ("e", "s"):
            dx, dy = DIRS[d]
            npos = (x + dx, y + dy, z)
            ng = ground_at.get(npos)
            if ng is None or ng == g or terrain.get(ng) not in NATURAL or terrain.get(ng) == terrain.get(g):
                continue
            nb = [s for s in tiles[npos] if layer.get(s) == "border"]
            if not borders and not nb:
                add("R4_transicion_sin_borde", pos, [g, ng],
                    f"{terrain.get(g)} junto a {terrain.get(ng)} ({d}) sin borde en ninguna de las dos")
    by_rule = Counter(i["rule"] for i in issues)
    by_zone = Counter((i["zone"] or "fuera_de_zonas", i["rule"]) for i in issues)

    # vista general por piso (color de minimapa 6x6x6)
    mm = {int(k): f.get("minimap_color") for k, f in facts.items()}
    overview = []
    floors = defaultdict(list)
    for (x, y, z), items in tiles.items():
        floors[z].append((x, y, items))
    for z, lst in sorted(floors.items()):
        xs = [t[0] for t in lst]
        ys = [t[1] for t in lst]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        W, H = x1 - x0 + 1, y1 - y0 + 1
        img = bytearray(b"\x10\x10\x14\xff" * (W * H))
        for x, y, items in lst:
            c = None
            for s in items:
                if mm.get(s) is not None:
                    c = mm[s]
            if c is None:
                continue
            o = ((y - y0) * W + (x - x0)) * 4
            img[o:o + 4] = bytes(((c // 36) % 6 * 51, (c // 6) % 6 * 51, c % 6 * 51, 255))
        name = f"overview_z{z}.png"
        (KB_DIR / name).write_bytes(png_bytes(W, H, img, scale=2))
        overview.append({"z": z, "file": name, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "px_per_tile": 2,
                         "tiles": len(lst)})

    def dump(name, obj):
        (KB_DIR / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1))

    dump("pieces.json", {"_schema": "pieces.v1", "labeled": sum(1 for p in pieces.values() if p.get("label")),
                         "total": len(pieces), "items": pieces})
    dump("review.json", {"_schema": "review.v1", "count": len(review), "items": review})
    dump("border_sets.json", {"_schema": "border_sets.v1", "sets": border_sets})
    dump("wall_sets.json", {"_schema": "wall_sets.v1", "sets": wall_sets})
    dump("map_lint.json", {"_schema": "map_lint.v1", "by_rule": dict(by_rule),
                           "by_zone": [{"zone": z, "rule": r, "count": c} for (z, r), c in sorted(by_zone.items())],
                           "issues": issues})
    dump("overview.json", {"_schema": "overview.v1", "floors": overview})
    print(f"piezas {len(pieces)} (etiquetadas {sum(1 for p in pieces.values() if p.get('label'))}), "
          f"revisar {len(review)}, sets de bordes {len(border_sets)}, sets de paredes {len(wall_sets)}")
    print("lint:", dict(by_rule))


if __name__ == "__main__":
    main()
