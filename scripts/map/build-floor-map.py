#!/usr/bin/env python3
"""Mapa por pisos del sitio local de docs: minimapa de cada piso de test.otbm y vistas de detalle.

Uso (desde la raíz del repo):
  python3 scripts/map/build-floor-map.py SALIDA/mapa/
Escribe z<piso>.png (colores de minimapa, 2 px por casilla), <zona>.png (vista como en el juego) y
meta.json, que lee mapa.html. Solo lee el repo. Lo corre scripts/docs-site/refresh-maps.sh.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kb"))
from mapdata import KB_DIR, Renderer, load_tiles, png_bytes  # noqa: E402

# clave, título, caja x0 y0 x1 y1, piso, escala
DETAILS = [
    ("crisol", "El Crisol (z0): hub + 3 arenas", (72, 74, 176, 98), 0, 1),
    ("templo", "Plaza del templo y portales (z7)", (146, 36, 178, 62), 7, 2),
    ("norte", "Campo norte y puerta al Paso del Norte (z7)", (116, 0, 213, 30), 7, 1),
    ("isla", "Isla natural con Cyclops (z7)", (122, 424, 189, 485), 7, 1),
    ("cueva", "Cueva bajo la isla (z8)", (122, 424, 189, 485), 8, 1),
]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    tiles = load_tiles()
    facts = json.loads((KB_DIR / "facts.json").read_text())["items"]
    mm = {int(k): f.get("minimap_color") for k, f in facts.items()}

    floors = defaultdict(list)
    for (x, y, z), items in tiles.items():
        floors[z].append((x, y, items))
    overview = []
    for z, lst in sorted(floors.items()):
        x0, y0 = min(t[0] for t in lst), min(t[1] for t in lst)
        x1, y1 = max(t[0] for t in lst), max(t[1] for t in lst)
        w, h = x1 - x0 + 1, y1 - y0 + 1
        img = bytearray(b"\x10\x10\x14\xff" * (w * h))
        for x, y, items in lst:
            c = None
            for sid in items:                       # el ítem de más arriba con color manda
                if mm.get(sid) is not None:
                    c = mm[sid]
            if c is None:
                continue
            o = ((y - y0) * w + (x - x0)) * 4
            img[o:o + 4] = bytes(((c // 36) % 6 * 51, (c // 6) % 6 * 51, c % 6 * 51, 255))
        (out / f"z{z}.png").write_bytes(png_bytes(w, h, bytes(img), scale=2))
        overview.append(dict(z=z, x0=x0, y0=y0, x1=x1, y1=y1, n=len(lst)))

    r = Renderer()
    for key, _title, (a, b, c, d), z, scale in DETAILS:
        w, h, px = r.area(tiles, a, b, c, d, z)
        (out / f"{key}.png").write_bytes(png_bytes(w, h, px, scale=scale))

    meta = dict(build=int(time.time()), floors=overview,   # build: versión para las URLs (caché)
                details=[dict(key=k, title=t, box=list(box), z=z) for k, t, box, z, _s in DETAILS])
    (out / "meta.json").write_text(json.dumps(meta))
    print(f"OK {out}: {len(overview)} pisos, {len(DETAILS)} vistas de detalle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
