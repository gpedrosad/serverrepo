#!/usr/bin/env python3
"""Inserta las fotos de ruta (web/assets/wiki/routes) en los artículos de la wiki.

Lee `web/assets/wiki/routes/manifest.json` (lo genera `scripts/map/build-route-images.py`) y
reemplaza el bloque marcado con `<!-- RUTA_IMAGENES:START -->` / `<!-- RUTA_IMAGENES:END -->` en
cada artículo. El bloque se inserta antes de `## Relacionado` (o al final).

  python3 scripts/map/build-route-images.py
  python3 scripts/web/apply-wiki-routes.py
  scripts/web/build-site.sh
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIKI = ROOT / "web/site/src/wiki"
MANIFEST = ROOT / "web/assets/wiki/routes/manifest.json"
SECTION = "## Cómo llegar desde el depot"

PAGES = {
    "isla-natural": "isla-natural",
    "epstein-island": "epstein-island",
    "valle-de-las-bestias": "valle-de-las-bestias",
    "el-crisol": "el-crisol",
    "wave-arena": "wave-arena",
    "reloj-de-arena": "reloj-de-arena",
    "isla-del-hielo-eterno": "isla-del-hielo",
    "hell-quest": "hell-quest",
    "castillo-imperial": "castillo-imperial",
    "desierto-de-las-ruinas": "desierto-de-las-ruinas",
    "islote-del-minotauro": "islote-del-minotauro",
    "barcos": "barco-fargum",
    "depots": "templo-plaza",
}


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for page, slug in PAGES.items():
        path = WIKI / f"{page}.md"
        text = path.read_text(encoding="utf-8")
        images = manifest.get(slug, [])
        if not images:
            print(f"{page}: sin imágenes para {slug}")
            continue
        lines = ["## Cómo llegar desde el depot", "",
                 "Flechas rojas = camino. Fotos del mapa real, paso por paso.", ""]
        for img in images:
            lines += [f"**Paso {img['step']} · piso z{img['z']}**", "",
                      f"![{img['caption']}](/assets/wiki/routes/{img['file']})", ""]
        block = "\n".join(lines).rstrip() + "\n\n"
        # sacar marcadores viejos y la sección anterior (si existe), y volver a insertarla
        text = text.replace("<!-- RUTA_IMAGENES:START -->\n", "").replace("<!-- RUTA_IMAGENES:END -->\n", "")
        text = text.replace("<!-- RUTA_IMAGENES:START -->", "").replace("<!-- RUTA_IMAGENES:END -->", "")
        text = re.sub(rf"^{re.escape(SECTION)}\n.*?(?=^## |\Z)", "", text, flags=re.M | re.S)
        marker = "## Relacionado"
        if marker in text:
            text = text.replace(marker, f"{block}{marker}", 1)
        else:
            text = text.rstrip() + "\n\n" + block
        path.write_text(text, encoding="utf-8")
        print(f"{page}: {len(images)} fotos ({slug})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
