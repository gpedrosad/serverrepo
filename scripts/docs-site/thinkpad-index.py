#!/usr/bin/env python3
"""Portada del sitio de mapas de la ThinkPad (http://192.168.1.17:8077).

Lee SITIO/mapa/meta.json (build-floor-map.py) y SITIO/monstruos/data.json (build-monster-map.py)
y escribe SITIO/index.html: enlace al mapa interactivo, un cuadro por piso y las vistas de zona.

Uso: python3 scripts/docs-site/thinkpad-index.py SITIO COMMIT
"""
from __future__ import annotations

import html
import json
import sys
import time
from pathlib import Path

FLOOR_NAMES = {7: "superficie", 6: "piso 1 arriba", 5: "piso 2 arriba", 4: "piso 3 arriba", 3: "piso 4 arriba",
               2: "piso 5 arriba", 0: "El Crisol", 8: "subsuelo 1", 9: "subsuelo 2", 10: "subsuelo 3", 11: "subsuelo 4"}

PAGE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Retro76 · Mapas</title>
<style>
:root {{ --bg: #14161b; --card: #1d2027; --line: #2c313b; --text: #e6e8ec; --muted: #9aa1ad; --accent: #e0b04a; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--text); font: 15px/1.5 system-ui, sans-serif; }}
main {{ max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }}
h1 {{ margin: 0 0 4px; font-size: 26px; }}
h2 {{ margin: 32px 0 12px; font-size: 18px; color: var(--accent); }}
p.sub {{ margin: 0; color: var(--muted); }}
a {{ color: inherit; text-decoration: none; }}
.hero {{ display: block; margin-top: 20px; padding: 20px; border: 1px solid var(--accent); border-radius: 10px;
        background: linear-gradient(135deg, #2a2415, var(--card)); }}
.hero strong {{ font-size: 20px; color: var(--accent); }}
.hero span {{ display: block; color: var(--muted); margin-top: 4px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }}
.card {{ background: var(--card); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
.card:hover {{ border-color: var(--accent); }}
.card img {{ display: block; width: 100%; height: 150px; object-fit: contain; background: #000; image-rendering: pixelated; }}
.card div {{ padding: 8px 10px; }}
.card b {{ display: block; }}
.card small {{ color: var(--muted); }}
footer {{ margin-top: 40px; color: var(--muted); font-size: 13px; }}
</style>
</head>
<body>
<main>
<h1>Retro76 · Mapas del server</h1>
<p class="sub">Lo que está deployado en la ThinkPad. Se regenera solo cuando cambia el mapa, los spawns o los monstruos.</p>
<a class="hero" href="monstruos.html">
  <strong>Mapa interactivo &rarr;</strong>
  <span>Todos los pisos como se ven en el juego, cada monstruo y NPC en su lugar, buscador y zonas.{monster_line}</span>
</a>
<h2>Pisos</h2>
<div class="grid">
{floors}
</div>
<h2>Zonas</h2>
<div class="grid">
{details}
</div>
<footer>Generado {built} desde <code>main</code> {commit}. Fuente: <code>scripts/docs-site/thinkpad-maps.sh</code>.</footer>
</main>
</body>
</html>
"""


def card(href: str, img: str, title: str, sub: str) -> str:
    return (f'<a class="card" href="{href}"><img loading="lazy" src="{img}" alt=""><div><b>{html.escape(title)}</b>'
            f'<small>{html.escape(sub)}</small></div></a>')


def main() -> int:
    site, commit = Path(sys.argv[1]), sys.argv[2]
    meta = json.loads((site / "mapa/meta.json").read_text(encoding="utf-8"))
    floors = sorted(meta.get("floors", []), key=lambda f: (f["z"] != 7, f["z"]))
    floor_cards = [card(f"monstruos.html#z={f['z']}", f"mapa/z{f['z']}.png", f"Piso {f['z']}",
                        f"{FLOOR_NAMES.get(f['z'], '')} · {f['n']:,} casillas".replace(",", "."))
                   for f in floors]
    detail_cards = [card(f"mapa/{d['key']}.png", f"mapa/{d['key']}.png", d.get("title", d["key"]), "vista como en el juego")
                    for d in meta.get("details", [])]
    monster_line = ""
    data = site / "monstruos/data.json"
    if data.is_file():
        try:
            spawns = json.loads(data.read_text(encoding="utf-8")).get("spawns", [])
            monster_line = f" {len(spawns)} spawns."
        except (ValueError, AttributeError):
            pass
    (site / "index.html").write_text(PAGE.format(
        monster_line=monster_line, floors="\n".join(floor_cards), details="\n".join(detail_cards),
        built=time.strftime("%Y-%m-%d %H:%M"), commit=html.escape(commit)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
