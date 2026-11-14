#!/usr/bin/env python3
"""Genera las fotos de ruta de todas las quests y el JSON que usa /quests.

Lee `scripts/map/quest-routes.json` (lo genera `build-quest-routes.py`) y dibuja **una imagen
por tramo/piso** sobre el mapa real, con una sola flecha roja. Las imágenes van a
`web/assets/wiki/routes/quests/<quest>/` y el manifiesto a
`web/assets/wiki/routes/quests/manifest.json`. También escribe
`web/site/src/data/quest_routes.json` para la página /quests.

Requiere Pillow. Uso:
  python3 scripts/map/build-quest-route-images.py
  python3 scripts/map/build-quest-route-images.py --map OTRO.otbm
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "web/assets/wiki/routes/quests"
DATA = ROOT / "web/site/src/data/quest_routes.json"
ROUTES = HERE / "quest-routes.json"

_spec = importlib.util.spec_from_file_location("rimg", HERE / "build-route-images.py")
bi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bi)


def slug(text: str) -> str:
    text = text.lower().replace("→", "-")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:48] or "ruta"


def main() -> int:
    ap = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    ap.add_argument("--map", type=Path, default=bi.MAP, help="OTBM a usar (por defecto test.otbm del repo)")
    args = ap.parse_args()
    bi.MAP_PATH = args.map
    bi.SCALE = 8
    bi.MARGIN = 8
    floors = bi.load_map()
    rnd = bi.Renderer()
    routes = json.loads(ROUTES.read_text(encoding="utf-8"))["routes"]
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    page = {}

    for route in routes:
        qid = route["quest"]
        rdir = OUT / qid
        rdir.mkdir(parents=True, exist_ok=True)
        for old in rdir.glob("*.jpg"):
            old.unlink()
        images = []
        total = len(route["segments"])
        for n, segment in enumerate(route["segments"], 1):
            pts = segment["points"]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            x0, x1 = max(0, min(xs) - bi.MARGIN), min(511, max(xs) + bi.MARGIN)
            y0, y1 = max(0, min(ys) - bi.MARGIN), min(511, max(ys) + bi.MARGIN)
            min_w, min_h = 70, 45
            cx, cy = (min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2
            if x1 - x0 + 1 < min_w:
                x0 = max(0, min(511 - min_w + 1, cx - min_w // 2))
                x1 = x0 + min_w - 1
            if y1 - y0 + 1 < min_h:
                y0 = max(0, min(511 - min_h + 1, cy - min_h // 2))
                y1 = y0 + min_h - 1
            img = rnd.crop(floors, segment["z"], x0, y0, x1, y1)
            bi.draw_path(img, pts, x0, y0)
            label = route.get("target_label") or route["name"]
            bi.banner(img, f"Cómo llegar: {route['name']} — parte {n}/{total}",
                      f"{label} · flechas rojas = camino")
            for m in route.get("markers", []):
                if m["z"] == segment["z"] and x0 <= m["x"] <= x1 and y0 <= m["y"] <= y1:
                    bi.draw_marker(img, m["x"], m["y"], x0, y0, m["label"])
            name = f"{n:02d}-{slug(label)}.jpg"
            img.save(rdir / name, quality=84, optimize=True)
            images.append({"file": f"quests/{qid}/{name}",
                           "caption": f"{route['name']}: {label}",
                           "step": n})
        manifest[qid] = images
        page[qid] = {"note": route.get("note", ""), "steps": route.get("steps", []), "images": images}
        print(f"{qid}: {len(images)} imágenes")

    mpath = OUT / "manifest.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    version = hashlib.sha1(mpath.read_bytes()).hexdigest()[:10]
    for qid, info in page.items():
        for img in info["images"]:
            img["src"] = f"/assets/wiki/routes/{img['file']}?v={version}"
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(page, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK {OUT}: {sum(len(v) for v in manifest.values())} imágenes")
    print(f"OK {DATA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
