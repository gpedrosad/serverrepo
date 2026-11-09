#!/usr/bin/env python3
"""Etiqueta piezas con DeepSeek vía opencode (sin API key; usa la cuenta de opencode).

Igual que label_deepseek.py (mismo esquema y validación, misma caché .cache/labels)
pero llama `opencode run -m <modelo>` en una carpeta aislada, sin herramientas, con
varias piezas por pedido. Solo texto: hechos medidos, sin sprites.

Uso:
  python3 label_opencode.py [--model opencode-go/deepseek-v4.1-flash] [--batch 15]
                            [--workers 8] [--limit N] [--only-used|--only-unused]

Segunda pasada con imagen (--vision-review): para las piezas usadas en el mapa manda,
además de los hechos, la etiqueta anterior + motivos de review.json y UNA imagen por pieza
(sprite ampliado a la izquierda, recorte 7x7 del mapa con la casilla en rojo a la derecha),
adjunta con `opencode run -f`. La etiqueta vieja queda en .cache/labels_v1/.
  python3 label_opencode.py --vision-review [--batch 5] [--min-uses 1] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from label_deepseek import CACHE, SCHEMA_VERSION, SYSTEM, compact_facts, ids_in, validate
from mapdata import KB_DIR, Renderer, load_tiles, png_bytes

CACHE_V1 = CACHE.parent / "labels_v1"

OC_CONFIG = {
    "$schema": "https://opencode.ai/config.json",
    "permission": {"edit": "deny", "bash": "deny", "webfetch": "deny", "external_directory": "deny"},
    "tools": {t: False for t in ("bash", "edit", "write", "read", "grep", "glob", "list", "patch",
                                 "webfetch", "todowrite", "todoread", "task")},
}
BATCH_RULES = """
Vas a recibir VARIAS piezas. No hay imágenes: decidí solo con los HECHOS (nombre, flags, uso).
Devolvé SOLO un objeto JSON (sin texto ni ``` alrededor) cuyas claves son los ids (como string)
y cada valor es el objeto de etiqueta con EXACTAMENTE estos campos:
category, terrain, border{is_border,under_terrain,over_terrain,edge}, wall{is_wall,part,material},
settings[], walkable_expected, pairs_with_ids[], avoid_with_ids[], description_es, usage_rule_es,
sprite_matches_name (true si no hay motivo para dudar), confidence (0..1; sin imagen, máx 0.8).
"""

REVIEW_RULES = """
SEGUNDA PASADA, AHORA CON IMÁGENES. Recibís VARIAS piezas. Cada pieza tiene UNA imagen adjunta;
ORDEN dice qué imagen (1, 2, 3...) es de qué id. En cada imagen: a la izquierda el sprite ampliado;
a la derecha, si existe, un recorte 7x7 del mapa real con la casilla de la pieza marcada en rojo.
Cada pieza trae HECHOS, ETIQUETA_ANTERIOR (sin imagen o de otro modelo) y MOTIVOS de revisión.
Mirá la imagen y corregí lo que esté mal: categoría, terreno, border.edge (de qué lado de la casilla
está el OTRO terreno, mirá el recorte), wall.part, material, settings, sprite_matches_name y los textos.
Si la anterior está bien, repetila. Los flags del .dat (unpassable, ground, ground_border) mandan.
Devolvé SOLO un objeto JSON (sin texto ni ``` alrededor) cuyas claves son los ids (como string)
y cada valor es la etiqueta con EXACTAMENTE estos campos:
category, terrain, border{is_border,under_terrain,over_terrain,edge}, wall{is_wall,part,material},
settings[], walkable_expected, pairs_with_ids[], avoid_with_ids[], description_es, usage_rule_es,
sprite_matches_name, confidence (0..1, honesta).
"""

_lock = threading.Lock()
stats = {"ok": 0, "fail": 0, "calls": 0}


def run_opencode(workdir: Path, model: str, prompt: str, files: list[str] = ()) -> str:
    cmd = ["opencode", "run", "-m", model, "--format", "json"]
    for fp in files:
        cmd += ["-f", fp]
    res = subprocess.run(cmd + [prompt],
                         cwd=workdir, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600)
    text = []
    for line in res.stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        part = ev.get("part") or {}
        if ev.get("type") == "text" and part.get("text"):
            text.append(part["text"])
    if not text:
        raise RuntimeError(f"sin texto (rc={res.returncode}): {res.stderr[-300:]}")
    out = "".join(text).strip()
    if out.startswith("```"):
        out = out.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
    start, end = out.find("{"), out.rfind("}")
    return out[start:end + 1]


def label_batch(workdir: Path, model: str, ids: list[str], facts: dict, names: dict) -> list[str]:
    payload = {i: compact_facts(facts[i], names) for i in ids}
    prompt = SYSTEM + "\n" + BATCH_RULES + "\nHECHOS:\n" + json.dumps(payload, ensure_ascii=False)
    pending, done = list(ids), []
    for attempt in range(3):
        if not pending:
            break
        try:
            with _lock:
                stats["calls"] += 1
            raw = json.loads(run_opencode(workdir, model, prompt if attempt == 0 else
                                          SYSTEM + "\n" + BATCH_RULES + "\nHECHOS:\n" +
                                          json.dumps({i: payload[i] for i in pending}, ensure_ascii=False)))
        except Exception as e:  # noqa: BLE001 — se reintenta
            time.sleep(3 * (attempt + 1))
            last = str(e)
            continue
        still = []
        for i in pending:
            lab = raw.get(i) or raw.get(str(int(i)))
            try:
                clean = validate(lab or {}, ids_in(facts[i]))
                clean["confidence"] = min(clean["confidence"], 0.8)
            except Exception:  # noqa: BLE001
                still.append(i)
                continue
            rec = {"_schema": SCHEMA_VERSION, "id": int(i), "name": facts[i]["name"], "model": model,
                   "vision": False, "via": "opencode", "label": clean}
            (CACHE / f"{i}.json").write_text(json.dumps(rec, ensure_ascii=False))
            err = CACHE / f"{i}.error.txt"
            if err.exists():
                err.unlink()
            done.append(i)
        pending = still
    with _lock:
        stats["ok"] += len(done)
        stats["fail"] += len(pending)
    return pending


def upscale(w: int, h: int, rgba: bytes, s: int) -> tuple[int, int, bytes]:
    out = bytearray()
    for y in range(h):
        row = rgba[y * w * 4:(y + 1) * w * 4]
        big = b"".join(bytes(row[i:i + 4]) * s for i in range(0, len(row), 4))
        out += big * s
    return w * s, h * s, bytes(out)


def composite(renderer: Renderer, tiles, sid: int, f: dict) -> bytes | None:
    """Sprite ampliado + recorte 7x7 del mapa, lado a lado, en un solo PNG."""
    parts = []
    im = renderer.item(sid)
    if im:
        w, h, rgba = im
        parts.append(upscale(w, h, rgba, 4 if max(w, h) <= 32 else 2))
    if f.get("sample_positions"):
        x, y, z = f["sample_positions"][0]
        w, h, rgba = renderer.area(tiles, x - 3, y - 3, x + 3, y + 3, z, highlight=(x, y))
        parts.append(upscale(w, h, rgba, 2))
    if not parts:
        return None
    gap = 16
    W = sum(p[0] for p in parts) + gap * (len(parts) - 1)
    H = max(p[1] for p in parts)
    img = bytearray(b"\x10\x10\x14\xff" * (W * H))
    ox = 0
    for w, h, rgba in parts:
        for y in range(h):
            o = (y * W + ox) * 4
            img[o:o + w * 4] = rgba[y * w * 4:(y + 1) * w * 4]
        ox += w + gap
    return png_bytes(W, H, bytes(img))


def review_batch(workdir: Path, model: str, ids: list[str], facts: dict, names: dict,
                 prev: dict, reasons: dict, images: dict) -> list[str]:
    pending, done = list(ids), []
    for attempt in range(3):
        if not pending:
            break
        with_img = [i for i in pending if images.get(i)]
        orden = {str(n): i for n, i in enumerate(with_img, 1)}
        payload = {i: {"HECHOS": compact_facts(facts[i], names), "ETIQUETA_ANTERIOR": prev.get(i),
                       "MOTIVOS": reasons.get(i, [])} for i in pending}
        prompt = (SYSTEM + "\n" + REVIEW_RULES + "\nORDEN (imagen -> id): " + json.dumps(orden)
                  + "\nPIEZAS:\n" + json.dumps(payload, ensure_ascii=False))
        try:
            with _lock:
                stats["calls"] += 1
            raw = json.loads(run_opencode(workdir, model, prompt, [images[i] for i in with_img]))
        except Exception:  # noqa: BLE001 — se reintenta
            time.sleep(3 * (attempt + 1))
            continue
        still = []
        for i in pending:
            lab = raw.get(i) or raw.get(str(int(i)))
            try:
                clean = validate(lab or {}, ids_in(facts[i]))
            except Exception:  # noqa: BLE001
                still.append(i)
                continue
            old = CACHE / f"{i}.json"
            if old.exists() and not (CACHE_V1 / f"{i}.json").exists():
                (CACHE_V1 / f"{i}.json").write_text(old.read_text())
            rec = {"_schema": SCHEMA_VERSION, "id": int(i), "name": facts[i]["name"], "model": model,
                   "vision": bool(images.get(i)), "via": "opencode", "pass": 2, "label": clean}
            old.write_text(json.dumps(rec, ensure_ascii=False))
            done.append(i)
        pending = still
    with _lock:
        stats["ok"] += len(done)
        stats["fail"] += len(pending)
    return pending


def vision_review(a, facts: dict, names: dict) -> None:
    pieces = json.loads((KB_DIR / "pieces.json").read_text())["items"]
    reasons = {str(r["id"]): r["reasons"] for r in json.loads((KB_DIR / "review.json").read_text())["items"]}
    CACHE_V1.mkdir(parents=True, exist_ok=True)

    def done(i):
        p = CACHE / f"{i}.json"
        return p.exists() and json.loads(p.read_text()).get("pass", 1) >= 2

    todo = [i for i, f in facts.items() if f["map_uses"] >= a.min_uses and not done(i)]
    todo.sort(key=lambda i: (-facts[i]["map_uses"], int(i)))
    if a.limit:
        todo = todo[:a.limit]
    workdir = Path(tempfile.mkdtemp(prefix="oc-review-"))
    (workdir / "opencode.json").write_text(json.dumps(OC_CONFIG))
    (workdir / "img").mkdir()
    renderer, tiles = Renderer(), load_tiles()
    images = {}
    for i in todo:
        png = composite(renderer, tiles, int(i), facts[i])
        if png:
            (workdir / "img" / f"{i}.png").write_bytes(png)
            images[i] = str(workdir / "img" / f"{i}.png")
    prev = {i: (pieces.get(i) or {}).get("label") for i in todo}
    batches = [todo[k:k + a.batch] for k in range(0, len(todo), a.batch)]
    print(f"revisión con imagen: {len(todo)} piezas ({len(images)} con imagen) en {len(batches)} pedidos, "
          f"{a.model}, {a.workers} en paralelo, {workdir}", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(review_batch, workdir, a.model, b, facts, names, prev, reasons, images) for b in batches]
        for n, f in enumerate(as_completed(futs), 1):
            failed = f.result()
            if failed or n % 10 == 0 or n == len(batches):
                print(f"[{n}/{len(batches)}] ok={stats['ok']} fail={stats['fail']} pedidos={stats['calls']} "
                      f"{time.time() - t0:.0f}s" + (f" sin etiqueta: {failed[:5]}" if failed else ""), flush=True)
    print(json.dumps(stats))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="opencode-go/deepseek-v4.1-flash")
    ap.add_argument("--batch", type=int, default=15)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only-used", action="store_true")
    ap.add_argument("--only-unused", action="store_true")
    ap.add_argument("--vision-review", action="store_true")
    ap.add_argument("--min-uses", type=int, default=1)
    a = ap.parse_args()

    facts = json.loads((KB_DIR / "facts.json").read_text())["items"]
    names = {int(k): v["name"] for k, v in facts.items()}
    if a.vision_review:
        if a.batch == 15:
            a.batch = 5
        return vision_review(a, facts, names)
    CACHE.mkdir(parents=True, exist_ok=True)
    todo = [i for i in facts if not (CACHE / f"{i}.json").exists()]
    if a.only_used:
        todo = [i for i in todo if facts[i]["map_uses"]]
    if a.only_unused:
        todo = [i for i in todo if not facts[i]["map_uses"]]
    todo.sort(key=lambda i: (-facts[i]["map_uses"], int(i)))
    if a.limit:
        todo = todo[:a.limit]
    batches = [todo[k:k + a.batch] for k in range(0, len(todo), a.batch)]
    print(f"{len(todo)} piezas en {len(batches)} pedidos, {a.model}, {a.workers} en paralelo", flush=True)

    workdir = Path(tempfile.mkdtemp(prefix="oc-label-"))
    (workdir / "opencode.json").write_text(json.dumps(OC_CONFIG))
    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(label_batch, workdir, a.model, b, facts, names) for b in batches]
        for n, f in enumerate(as_completed(futs), 1):
            failed = f.result()
            if failed or n % 10 == 0 or n == len(batches):
                print(f"[{n}/{len(batches)}] ok={stats['ok']} fail={stats['fail']} pedidos={stats['calls']} "
                      f"{time.time() - t0:.0f}s" + (f" sin etiqueta: {failed[:5]}" if failed else ""), flush=True)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
