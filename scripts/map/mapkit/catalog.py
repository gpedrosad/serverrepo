#!/usr/bin/env python3
"""Catálogo de piezas por tema: escribe la sección generada de docs/items-and-map/MAPAS.md y una hoja de sprites.

Sale de `themes.json` (qué ids usa cada tema y la regla de cada categoría) más los datos reales de cada id:
tamaño del dibujo (.dat), si bloquea, si se levanta o se empuja (.otb) y su client id. Así la guía no se
desactualiza: si se agrega una pieza al tema, se vuelve a correr esto.

  python3.11 scripts/map/mapkit/catalog.py            # reescribe el bloque CATALOGO de MAPAS.md + hojas
  python3.11 scripts/map/mapkit/catalog.py --check    # falla si el bloque no está al día (para el lint)
  python3.11 scripts/map/mapkit/catalog.py --fmt      # deja themes.json con listas en una línea
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mapkit as K  # noqa: E402

DOC = K.REPO / "docs/items-and-map/MAPAS.md"
IMG = K.REPO / "docs/items-and-map/img"
BEGIN, END = "<!-- BEGIN CATALOGO (scripts/map/mapkit/catalog.py) -->", "<!-- END CATALOGO -->"


def compact(o, ind=0):
    pad = "  " * (ind + 1)
    flat = lambda v: not isinstance(v, (dict, list)) or (isinstance(v, list) and all(  # noqa: E731
        not isinstance(x, (dict, list)) for x in v))
    if isinstance(o, dict):
        if ind > 1 and all(flat(v) for v in o.values()):
            return json.dumps(o, ensure_ascii=False)
        return "{\n" + ",\n".join(pad + json.dumps(k, ensure_ascii=False) + ": " + compact(v, ind + 1)
                                  for k, v in o.items()) + "\n" + "  " * ind + "}"
    return json.dumps(o, ensure_ascii=False)


def ids_of(v):
    if isinstance(v, int):
        return [v]
    if isinstance(v, list) and all(isinstance(x, int) for x in v):
        return list(dict.fromkeys(v))
    if isinstance(v, dict) and "side" in v:
        out = [v["ground"]] if "ground" in v else []
        return out + list(v["side"].values()) + list(v["corner"].values()) + list(v["inner"].values())
    return []


def render(themes) -> tuple[str, list]:
    import mapdata
    otb = K.Otb()
    r = mapdata.Renderer()
    notes = themes.get("_categorias", {})
    lines, sheets = [], []
    for name, th in themes.items():
        if name.startswith("_"):
            continue
        lines += [f"### Tema `{name}`", "", th.get("about", ""), "",
                  "| Categoría | Ids (server) | Dibujo | Bloquea | Regla |", "|---|---|---|---|---|"]
        every = []
        for cat, v in th.items():
            ids = ids_of(v)
            if not ids:
                continue
            every += ids
            sizes = sorted({f"{r.entry(i)['w']}x{r.entry(i)['h']}" if r.entry(i) else "?" for i in ids})
            blocks = {otb.blocks(i) for i in ids}
            loose = [i for i in ids if otb.loose(i)]
            rule = notes.get(cat, v.get("note", "") if isinstance(v, dict) else "")
            if loose:
                rule += f" **Se levantan/empujan: {loose}**"
            shown = ", ".join(map(str, ids)) if len(ids) <= 14 else f"{ids[0]}–{ids[-1]} ({len(ids)})"
            lines.append(f"| `{cat}` | {shown} | {'/'.join(sizes)} | "
                         f"{'sí' if blocks == {True} else 'no' if blocks == {False} else 'mixto'} | {rule} |")
        props = th.get("props", {})
        if props:
            lines += ["", "Claros (`props`, los elige jev o la ficha):", "",
                      "| Tipo | Qué es | Piso (suelto) | Borde (bloquea) |", "|---|---|---|---|"]
            for k, p in props.items():
                lines.append(f"| `{k}` | {p['about']} | {', '.join(p['floor'])} ({p['floor_rate']:.0%}) | "
                             f"{', '.join(p['edge'])} ({p['edge_rate']:.0%})" + (f" + `{p['center']}` al centro" if p.get("center") else "") + " |")
        sheet = IMG / f"tema-{name}.png"
        sheets.append((sheet, sorted(set(every))))
        lines += ["", f"![Piezas del tema {name}](img/{sheet.name})", ""]
    return "\n".join(lines), sheets


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--fmt", action="store_true")
    a = ap.parse_args()
    path = K.HERE / "themes.json"
    themes = json.loads(path.read_text())
    if a.fmt:
        path.write_text(compact(themes) + "\n")
        return 0
    body, sheets = render(themes)
    doc = DOC.read_text()
    if BEGIN not in doc:
        raise SystemExit(f"falta el bloque {BEGIN} en {DOC}")
    head, rest = doc.split(BEGIN, 1)
    new = head + BEGIN + "\n" + body + "\n" + END + rest.split(END, 1)[1]
    if a.check:
        if new != doc:
            print("el catálogo de MAPAS.md está desactualizado: correr scripts/map/mapkit/catalog.py")
            return 1
        print("catálogo al día")
        return 0
    DOC.write_text(new)
    for sheet, ids in sheets:
        subprocess.run([sys.executable, str(K.MAPDIR / "render-pieces.py"), "--sheet", str(sheet),
                        *map(str, ids)], check=True, stdout=subprocess.DEVNULL)
        try:
            from PIL import Image
            im = Image.open(sheet)
            im.thumbnail((1100, 1100))
            im.convert("RGB").quantize(128).save(sheet, optimize=True)     # ~4 veces más liviana para git
        except ImportError:
            pass
    print(f"OK {DOC} y {len(sheets)} hoja(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
