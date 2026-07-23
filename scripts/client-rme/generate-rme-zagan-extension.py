#!/usr/bin/env python3
"""Genera extensión RME con los items Zagan (server ids 20100+) en la paleta."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def categorize(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ("sword", "blade", "hammer", "axe", "bow", "wand", "rod")):
        return "Weapons"
    if "shield" in n or "ward" in n:
        return "Shields"
    if "helm" in n or "crest" in n or "hood" in n:
        return "Helmets"
    if "armor" in n or "plate" in n or "robe" in n or "mail" in n:
        return "Armors"
    if "leg" in n or "greave" in n:
        return "Legs"
    if "boot" in n:
        return "Boots"
    if "ring" in n or "amulet" in n or "crystal" in n:
        return "Jewelry"
    if "rune" in n or "spell" in n:
        return "Runes"
    return "Other"


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from lib.project_root import project_root  # noqa: E402

    root = project_root(Path(__file__))
    manifest_path = root / "zagan-test" / "manifest.json"
    out_path = root / "rme-extensions" / "yurots-zagan-items.xml"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_cat: dict[str, list[int]] = {}
    for entry in manifest:
        cat = categorize(entry["itemName"])
        by_cat.setdefault(cat, []).append(int(entry["serverId"]))

    lines = [
        '<materialsextension',
        '	name="YurOTS Zagan Items"',
        '	author="YurOTS"',
        '	description="Items custom del pack Zagan+Square (server ids 20100+)."',
        '	client="all">',
        "",
    ]
    for cat in sorted(by_cat):
        lines.append(f'\t<tileset name="Zagan {cat}">')
        lines.append("\t\t<raw>")
        for sid in sorted(by_cat[cat]):
            lines.append(f'\t\t\t<item id="{sid}"/>')
        lines.append("\t\t</raw>")
        lines.append("\t</tileset>")
        lines.append("")
    lines.append("</materialsextension>")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK {out_path} ({len(manifest)} items, {len(by_cat)} tilesets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
