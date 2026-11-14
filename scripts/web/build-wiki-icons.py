#!/usr/bin/env python3
"""Íconos de ítems para la wiki: recorta del atlas de la web los ítems que usan los artículos.

Busca `{item:N}` e `icono: N` en web/site/src/wiki/*.md, más los `reward_ids` y `pending_items` de
web/site/src/data/quests.json, y deja web/assets/wiki/items/<N>.png.
recortado de web/assets/items/items-atlas.png con la posición de web/data/items_all.json. El atlas
pone cada sprite abajo a la derecha de una celda de 64 px: los ítems de 32 px quedan en 32x32 y
los grandes (2x2) en 64x64. Si la web ya tiene una imagen del ítem (assets/premium, assets/gems)
se usa esa, que se ve mejor en gemas y monedas. Deja la lista de íconos disponibles en
web/site/src/wiki/_icons.json: la wiki solo muestra esos (nunca una imagen rota).
Solo genera los que faltan; --force los rehace todos. Usa `sips` (viene con macOS), no compila nada.

  python3 scripts/web/build-wiki-icons.py
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIKI = ROOT / "web/site/src/wiki"
QUESTS = ROOT / "web/site/src/data/quests.json"
ATLAS = ROOT / "web/assets/items/items-atlas.png"
CATALOG = ROOT / "web/data/items_all.json"
OUT = ROOT / "web/assets/wiki/items"
MANIFEST = WIKI / "_icons.json"
FALLBACKS = ("web/assets/premium/{id}-small.png", "web/assets/gems/{id}-small.png", "web/assets/gems/{id}-large.png")


def used_ids() -> set[int]:
    ids: set[int] = set()
    for md in WIKI.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        ids.update(int(n) for n in re.findall(r"\{item:(\d+)\}", text))
        ids.update(int(n) for n in re.findall(r"^icono:\s*(\d+)\s*$", text, re.M))
    if QUESTS.is_file():
        data = json.loads(QUESTS.read_text(encoding="utf-8"))
        for q in data.get("quests", []) + data.get("proposals", []):
            ids.update(int(n) for n in q.get("reward_ids", []))
        ids.update(int(q["id"]) for q in data.get("pending_items", []))
    return ids


def png_alpha(path: Path) -> tuple[int, int, list[list[int]]]:
    """Ancho, alto y canal alfa de un PNG RGBA de 8 bits (lo que escribe sips)."""
    data = path.read_bytes()
    pos, idat = 8, b""
    w = h = 0
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", body[:10])
            if (depth, ctype) != (8, 6):
                raise SystemExit(f"{path}: PNG no RGBA de 8 bits")
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    raw, stride, prev, rows = zlib.decompress(idat), w * 4, bytearray(w * 4), []
    for y in range(h):
        f, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - 4] if i >= 4 else 0
            b, c = prev[i], prev[i - 4] if i >= 4 else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(list(line[3::4]))
        prev = line
    return w, h, rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if not shutil.which("sips"):
        raise SystemExit("falta `sips` (macOS)")
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    cell, cols = data["atlas"]["cell"], data["atlas"]["cols"]
    index = {it["sid"]: i for i, it in enumerate(data["items"]) if it.get("img")}
    OUT.mkdir(parents=True, exist_ok=True)
    made, missing = 0, []
    for sid in sorted(used_ids()):
        dest = OUT / f"{sid}.png"
        if dest.exists() and not a.force:
            continue
        # Primero las imágenes que ya usa la web (gemas y premium: se ven mejor que el sprite
        # de 1 unidad de los apilables); si no hay, el atlas.
        src = next((ROOT / f.format(id=sid) for f in FALLBACKS if (ROOT / f.format(id=sid)).is_file()), None)
        if src is not None or sid not in index:
            if src is None:
                missing.append(sid)
            else:
                shutil.copy2(src, dest)
                print(f"  {sid:>5} (de {src.relative_to(ROOT)})")
                made += 1
            continue
        i = index[sid]
        x, y = (i % cols) * cell, (i // cols) * cell
        subprocess.run(["sips", "-c", str(cell), str(cell), "--cropOffset", str(y), str(x),
                        str(ATLAS), "--out", str(dest)], check=True, capture_output=True)
        _w, _h, alpha = png_alpha(dest)
        half = cell // 2
        big = any(alpha[r][c] for r in range(cell) for c in range(cell) if r < half or c < half)
        if not big:     # sprite de 32 px: solo el cuadrante de abajo a la derecha
            subprocess.run(["sips", "-c", str(half), str(half), "--cropOffset", str(y + half), str(x + half),
                            str(ATLAS), "--out", str(dest)], check=True, capture_output=True)
        print(f"  {sid:>5} {data['items'][i]['name']}{' (grande)' if big else ''}")
        made += 1
    have = sorted(int(p.stem) for p in OUT.glob("*.png") if p.stem.isdigit())
    MANIFEST.write_text(json.dumps(have) + "\n", encoding="utf-8")
    print(f"íconos nuevos: {made} · en total: {len(have)} · lista en {MANIFEST.relative_to(ROOT)}")
    if missing:
        print("sin imagen (la wiki no muestra ícono; agregar <id>.png a mano en web/assets/wiki/items/):",
              ", ".join(map(str, missing)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
