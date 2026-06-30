#!/usr/bin/env python3
"""Extrae sprites premium (scrolls + golden amulet) para la web."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "extract_gems", ROOT / "scripts/extract-gem-sprites.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["extract_gems"] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)

PREMIUM_EXPORTS = (
    mod.GemExport(1954, "scroll-1w", "Premium scroll (1 semana)", "small", 32),
    mod.GemExport(2345, "scroll-2w", "Premium scroll (2 semanas)", "small", 32),
    mod.GemExport(2130, "golden-amulet", "Golden amulet", "small", 32),
)


def main() -> int:
    out_dir = ROOT / "web/assets/premium"
    out_dir.mkdir(parents=True, exist_ok=True)
    dat_path, spr_path, otb_path = mod.find_assets()
    jpg_bg = (10, 10, 10)
    dat = mod.DatReader(dat_path.read_bytes())
    spr = mod.SprReader(spr_path.read_bytes())
    items: list[dict] = []
    for gem in PREMIUM_EXPORTS:
        client_id = mod.resolve_client_id(otb_path, gem.server_id)
        sprite_id = dat.sprite_ids_for_client_item(client_id)[0]
        image = spr.decode(sprite_id)
        entry = mod.export_gem(gem, sprite_id, image, out_dir, also_jpg=True, jpg_bg=jpg_bg)
        entry["clientId"] = client_id
        items.append(entry)
        print(f"  ok {entry['files']['jpg']:20}  {gem.display_name}")
    manifest = {
        "source": {
            "dat": str(dat_path),
            "spr": str(spr_path),
            "otb": str(otb_path),
            "clientVersion": mod.CLIENT_VERSION,
        },
        "items": items,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"\nmanifest: {out_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
