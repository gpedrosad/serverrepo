#!/usr/bin/env python3
"""Imágenes del catálogo privado /items, sacadas del cliente actual.

Lee web/data/items_catalog.json (la lista curada de ítems custom) y, para cada ítem, recorta su
sprite del atlas web/assets/items/items-atlas.png (lo genera scripts/export-items-catalog-web.py
con el Tibia.dat/.spr y el OTB de producción). Deja web/assets/items/custom/<serverId>.png, que es
lo que sirve /api/zagan-items/img/ (web/zagan_items.py), y actualiza en el JSON `image`, `clientId`
y los stats (ataque, defensa, armadura, slot, peso) leídos del OTB de producción. Avisa si un ítem no existe en el OTB o no tiene sprite.

Antes había imágenes en web/private/zagan-items/ (fuera de git, solo en el VPS) que se perdieron.

    python3.11 scripts/export-items-catalog-web.py --dat devtools/rme/rme-client-760/Tibia.dat \\
        --spr devtools/rme/rme-client-760/Tibia.spr --otb server/YurOTS/ots/data/items/items-zagan-test.otb
    python3.11 scripts/web/build-items-catalog.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web"))
import zagan_items as Z  # noqa: E402  (decodifica stats del OTB)

OTB = ROOT / "server/YurOTS/ots/data/items/items-zagan-test.otb"
STATS = ("group", "attack", "defence", "armor", "weight", "weaponType", "slot", "magLevel")
CATALOG = ROOT / "web/data/items_catalog.json"
ALL = ROOT / "web/data/items_all.json"
ATLAS = ROOT / "web/assets/items/items-atlas.png"
OUT = ROOT / "web/assets/items/custom"


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    data = json.loads(ALL.read_text(encoding="utf-8"))
    cell, cols = data["atlas"]["cell"], data["atlas"]["cols"]
    index = {it["sid"]: (i, it) for i, it in enumerate(data["items"])}
    atlas = Image.open(ATLAS).convert("RGBA")
    OUT.mkdir(parents=True, exist_ok=True)
    otb_root, _ = Z._parse_node(OTB.read_bytes(), 4)
    stats = {}
    for node_type, props, _ in otb_root[2]:
        info = Z._decode_otb_item(node_type, props)
        if info:
            stats[int(info["serverId"])] = info

    problems = []
    for row in catalog:
        sid = row["serverId"]
        if sid not in index:
            problems.append(f"{sid} {row['name']}: no existe en el OTB")
            continue
        i, it = index[sid]
        if not it.get("img"):
            problems.append(f"{sid} {row['name']}: sin sprite en el cliente")
            continue
        x, y = (i % cols) * cell, (i // cols) * cell
        tile = atlas.crop((x, y, x + cell, y + cell))
        half = cell // 2
        # el atlas ancla cada sprite abajo a la derecha: los de 32 px quedan en el cuarto inferior derecho
        if not tile.crop((0, 0, cell, half)).getbbox() and not tile.crop((0, 0, half, cell)).getbbox():
            tile = tile.crop((half, half, cell, cell))
        tile.save(OUT / f"{sid}.png", optimize=True)
        row["image"] = f"{sid}.png"
        row["clientId"] = it["cid"]
        for k in STATS:                       # stats del OTB de producción
            row[k] = stats.get(sid, {}).get(k)

    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(catalog) - len(problems)} imágenes en {OUT.relative_to(ROOT)}")
    for p in problems:
        print("  ojo:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
