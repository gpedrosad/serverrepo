#!/usr/bin/env python3
"""Etiqueta cada pieza con DeepSeek (OpenRouter), solo con salida JSON validada.

Entrada: facts.json (extract_facts.py) + sprite + recorte del mapa donde se usa.
Salida:  docs/items-and-map/map-kb/.cache/labels/<id>.json (una por pieza, reanudable)

Uso:
  OPENROUTER_KEY_FILE=/ruta/key python3 label_deepseek.py [--ids 406,407] [--limit N]
         [--workers 32] [--model deepseek/deepseek-v4-flash-vision-exp] [--only-used] [--force]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from mapdata import KB_DIR, Renderer, load_tiles, png_bytes

API = "https://openrouter.ai/api/v1/chat/completions"
CACHE = KB_DIR / ".cache" / "labels"
SCHEMA_VERSION = "labels.v1"

CATEGORY = ["ground", "ground_border", "wall", "wall_decoration", "door", "window", "floor_change",
            "nature_tree", "nature_bush_plant", "nature_rock", "water_feature", "furniture",
            "container", "light_source", "decoration", "structure", "teleport_magic", "item", "other"]
TERRAIN = ["grass", "dirt", "sand", "stone", "cobblestone", "marble", "wood", "water", "swamp",
           "snow", "ice", "lava", "cave", "mud", "gravel", "metal", "carpet", "void", "mixed", "none"]
EDGE = ["n", "s", "e", "w", "nw_outer", "ne_outer", "sw_outer", "se_outer",
        "nw_inner", "ne_inner", "sw_inner", "se_inner", "full", "none", "unknown"]
WALL_PART = ["horizontal", "vertical", "corner_nw", "corner_se", "pole", "end", "none", "unknown"]
SETTING = ["temple", "city", "house", "forest", "jungle", "desert", "snow", "swamp", "cave",
           "dungeon", "beach", "volcanic", "underwater", "arena", "any"]

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["category", "terrain", "border", "wall", "settings", "walkable_expected",
                 "pairs_with_ids", "avoid_with_ids", "description_es", "usage_rule_es",
                 "sprite_matches_name", "confidence"],
    "properties": {
        "category": {"type": "string", "enum": CATEGORY},
        "terrain": {"type": "string", "enum": TERRAIN},
        "border": {"type": "object", "additionalProperties": False,
                   "required": ["is_border", "under_terrain", "over_terrain", "edge"],
                   "properties": {"is_border": {"type": "boolean"},
                                  "under_terrain": {"type": "string", "enum": TERRAIN},
                                  "over_terrain": {"type": "string", "enum": TERRAIN},
                                  "edge": {"type": "string", "enum": EDGE}}},
        "wall": {"type": "object", "additionalProperties": False,
                 "required": ["is_wall", "part", "material"],
                 "properties": {"is_wall": {"type": "boolean"},
                                "part": {"type": "string", "enum": WALL_PART},
                                "material": {"type": "string", "enum": TERRAIN}}},
        "settings": {"type": "array", "items": {"type": "string", "enum": SETTING}},
        "walkable_expected": {"type": "boolean"},
        "pairs_with_ids": {"type": "array", "items": {"type": "integer"}},
        "avoid_with_ids": {"type": "array", "items": {"type": "integer"}},
        "description_es": {"type": "string"},
        "usage_rule_es": {"type": "string"},
        "sprite_matches_name": {"type": "boolean"},
        "confidence": {"type": "number"},
    },
}

SYSTEM = f"""Eres un catalogador de piezas de mapa de Tibia 7.6 (OTBM). Recibes HECHOS medidos por código
(flags del cliente, capa de dibujo, estadísticas de uso y vecinos en el mapa real) y 1-2 imágenes:
(1) el sprite de la pieza, (2) si existe, un recorte 7x7 del mapa con la casilla de la pieza marcada en rojo.

Devuelve SOLO el JSON del esquema. Reglas:
- Los HECHOS mandan sobre tu intuición. layer=ground => category=ground. layer=border (flag ground_border)
  => casi siempre ground_border. layer=bottom suele ser pared/estructura/árbol grande.
- border.edge: lado de la casilla donde está el OTRO terreno (el que el borde tapa/contornea).
  Usa different_ground_neighbor_share: el/los lados con valor alto son el borde. Lado simple => n/s/e/w;
  dos lados contiguos altos => *_outer; solo una diagonal alta => *_inner. Si no es borde: "none".
- border.under_terrain = suelo debajo (ground_under); over_terrain = terreno que dibuja el borde.
- wall.part: horizontal = corre este-oeste; vertical = norte-sur; según same_item_neighbor_share y sprite.
- pairs_with_ids / avoid_with_ids: SOLO ids que aparecen en los HECHOS (vecinos, mismo tile). Máximo 6 cada uno.
- description_es: qué es, máx 140 caracteres. usage_rule_es: dónde/cuándo ponerla para que el mapa
  no se vea mal, máx 200 caracteres, en tono de regla ("Va sobre X, con Y al norte...").
- sprite_matches_name=false si la imagen claramente no corresponde al nombre.
- confidence 0..1 honesta. Si no hay uso en mapa ni imagen clara, baja la confianza.
Enums válidos: category={CATEGORY}; terrain={TERRAIN}; edge={EDGE}; part={WALL_PART}; settings={SETTING}."""

_lock = threading.Lock()
_stats = {"ok": 0, "fail": 0, "cost": 0.0, "tok_in": 0, "tok_out": 0}


def compact_facts(f: dict, names: dict) -> dict:
    out = {k: v for k, v in f.items() if k not in ("neighbor_ground", "sample_positions", "client_id")}
    if "neighbor_ground" in f:
        out["neighbor_ground"] = {d: [f"{r['id']}:{names.get(r['id'], 'vacío' if r['id'] == -1 else '?')}"
                                      f" {r['share']}" for r in lst] for d, lst in f["neighbor_ground"].items()}
    return out


def validate(obj: dict, allowed_ids: set[int]) -> dict:
    def enum(v, allowed, default):
        return v if v in allowed else default
    b, w = obj.get("border") or {}, obj.get("wall") or {}
    clean = {
        "category": enum(obj.get("category"), CATEGORY, "other"),
        "terrain": enum(obj.get("terrain"), TERRAIN, "none"),
        "border": {"is_border": bool(b.get("is_border")),
                   "under_terrain": enum(b.get("under_terrain"), TERRAIN, "none"),
                   "over_terrain": enum(b.get("over_terrain"), TERRAIN, "none"),
                   "edge": enum(b.get("edge"), EDGE, "unknown")},
        "wall": {"is_wall": bool(w.get("is_wall")),
                 "part": enum(w.get("part"), WALL_PART, "unknown"),
                 "material": enum(w.get("material"), TERRAIN, "none")},
        "settings": sorted({s for s in obj.get("settings", []) if s in SETTING}) or ["any"],
        "walkable_expected": bool(obj.get("walkable_expected")),
        "pairs_with_ids": [i for i in obj.get("pairs_with_ids", []) if isinstance(i, int) and i in allowed_ids][:6],
        "avoid_with_ids": [i for i in obj.get("avoid_with_ids", []) if isinstance(i, int) and i in allowed_ids][:6],
        "description_es": str(obj.get("description_es", ""))[:200],
        "usage_rule_es": str(obj.get("usage_rule_es", ""))[:260],
        "sprite_matches_name": bool(obj.get("sprite_matches_name", True)),
        "confidence": max(0.0, min(1.0, float(obj.get("confidence", 0)))),
    }
    bad = [k for k in ("category", "terrain") if obj.get(k) != clean[k]]
    if bad:
        raise ValueError(f"enum inválido en {bad}")
    return clean


def ids_in(f: dict) -> set[int]:
    s = set()
    for key in ("ground_under", "same_tile_items"):
        s |= {r["id"] for r in f.get(key, [])}
    for lst in f.get("neighbor_ground", {}).values():
        s |= {r["id"] for r in lst if r["id"] > 0}
    return s


def call(key: str, model: str, messages: list, use_schema: bool, effort: str | None = None) -> tuple[dict, dict]:
    body = {"model": model, "messages": messages, "temperature": 0.1, "max_tokens": 12000,
            "usage": {"include": True}}
    if effort:
        body["reasoning"] = {"effort": effort}
    if use_schema:
        body["response_format"] = {"type": "json_schema",
                                   "json_schema": {"name": "map_piece", "strict": True, "schema": SCHEMA}}
    else:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(API, data=json.dumps(body).encode(), headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "X-Title": "serverrepo map-kb"})
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.loads(r.read())
    if "choices" not in resp:
        raise RuntimeError(f"sin choices: {str(resp)[:300]}")
    text = resp["choices"][0]["message"].get("content") or ""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text), resp.get("usage", {})


def label_one(sid: str, f: dict, names: dict, renderer: Renderer, tiles, key: str, model: str,
              vision: bool, effort: str | None = None) -> str:
    content = [{"type": "text", "text": "HECHOS:\n" + json.dumps(compact_facts(f, names), ensure_ascii=False)}]
    if vision:
        im = renderer.item(int(sid))
        if im:
            w, h, rgba = im
            content.append({"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(png_bytes(w, h, rgba, scale=2)).decode()}})
        if f.get("sample_positions"):
            x, y, z = f["sample_positions"][0]
            w, h, rgba = renderer.area(tiles, x - 3, y - 3, x + 3, y + 3, z, highlight=(x, y))
            content.append({"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(png_bytes(w, h, rgba)).decode()}})
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]
    allowed = ids_in(f)
    last = None
    for attempt in range(5):
        try:
            raw, usage = call(key, model, messages, use_schema=attempt < 3, effort=effort)
            clean = validate(raw, allowed)
            rec = {"_schema": SCHEMA_VERSION, "id": int(sid), "name": f["name"], "model": model,
                   "vision": vision, "label": clean}
            (CACHE / f"{sid}.json").write_text(json.dumps(rec, ensure_ascii=False))
            with _lock:
                _stats["ok"] += 1
                _stats["cost"] += float(usage.get("cost") or 0)
                _stats["tok_in"] += int(usage.get("prompt_tokens") or 0)
                _stats["tok_out"] += int(usage.get("completion_tokens") or 0)
            return "ok"
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:200]!r}"
            time.sleep(min(60, 2 ** attempt * (5 if e.code == 429 else 1)))
        except Exception as e:  # noqa: BLE001 — se reintenta y se registra
            last = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt)
    with _lock:
        _stats["fail"] += 1
    (CACHE / f"{sid}.error.txt").write_text(last or "?")
    return f"fail {last}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--model", default="deepseek/deepseek-v4-flash-vision-exp")
    ap.add_argument("--no-vision", action="store_true")
    ap.add_argument("--only-used", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only-unused", action="store_true")
    ap.add_argument("--effort", choices=["low", "medium", "high"])
    a = ap.parse_args()

    key_file = os.environ.get("OPENROUTER_KEY_FILE")
    key = open(key_file).read().strip() if key_file else os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        sys.exit("falta OPENROUTER_KEY_FILE u OPENROUTER_API_KEY")

    facts = json.loads((KB_DIR / "facts.json").read_text())["items"]
    names = {int(k): v["name"] for k, v in facts.items()}
    CACHE.mkdir(parents=True, exist_ok=True)
    todo = list(facts)
    if a.ids:
        todo = [i for i in a.ids.split(",") if i in facts]
    if a.only_used:
        todo = [i for i in todo if facts[i]["map_uses"]]
    if a.only_unused:
        todo = [i for i in todo if not facts[i]["map_uses"]]
    # primero lo más usado: si se corta, lo importante ya está
    todo.sort(key=lambda i: -facts[i]["map_uses"])
    if not a.force:
        todo = [i for i in todo if not (CACHE / f"{i}.json").exists()]
    if a.limit:
        todo = todo[:a.limit]
    print(f"{len(todo)} piezas, modelo {a.model}, {a.workers} en paralelo", flush=True)

    renderer = Renderer()
    tiles = load_tiles()
    for i in todo[:64]:  # precalentar caché de sprites antes de los hilos
        renderer.item(int(i))
    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(label_one, i, facts[i], names, renderer, tiles, key, a.model,
                          not a.no_vision, a.effort): i for i in todo}
        for n, fut in enumerate(as_completed(futs), 1):
            res = fut.result()
            if res != "ok" or n % 100 == 0 or n == len(todo):
                print(f"[{n}/{len(todo)}] {futs[fut]} {res[:160]} | ok={_stats['ok']} fail={_stats['fail']} "
                      f"${_stats['cost']:.3f} {time.time() - t0:.0f}s", flush=True)
    print(json.dumps(_stats))


if __name__ == "__main__":
    main()
