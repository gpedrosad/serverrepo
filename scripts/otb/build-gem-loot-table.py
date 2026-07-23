#!/usr/bin/env python3
"""Genera web/data/gem-drops.json desde loot XML de monstruos rage."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

GEMS = [
    {
        "id": 2145,
        "key": "diamond",
        "name": "Small Diamond",
        "short": "Diamond",
        "big": "Blue Gem",
        "use": "Vender a Parived · 20× → Blue Gem",
    },
    {
        "id": 2146,
        "key": "sapphire",
        "name": "Small Sapphire",
        "short": "Sapphire",
        "big": "Yellow Gem",
        "use": "Imbuir botas · 20× → Yellow Gem (+haste)",
    },
    {
        "id": 2147,
        "key": "ruby",
        "name": "Small Ruby",
        "short": "Ruby",
        "big": "Big Ruby",
        "use": "Imbuir arma · 20× → Big Ruby (+velocidad)",
    },
    {
        "id": 2149,
        "key": "emerald",
        "name": "Small Emerald",
        "short": "Emerald",
        "big": "Big Emerald",
        "use": "Imbuir armadura · 20× → Big Emerald (+skills)",
    },
    {
        "id": 2150,
        "key": "amethyst",
        "name": "Small Amethyst",
        "short": "Amethyst",
        "big": "Violet Gem",
        "use": "Imbuir wand/rod · 20× → Violet Gem (+ML)",
    },
]
GEM_IDS = {g["id"] for g in GEMS}
TIERS = ["angry", "furious", "enraged"]
MULT = {"angry": "×1", "furious": "×2.4", "enraged": "×3.2"}


def title_case(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split())


def collect_gem_ids(el: ET.Element, acc: set[int]) -> None:
    for child in el:
        if child.tag == "item":
            iid = int(child.get("id", 0))
            if iid in GEM_IDS:
                acc.add(iid)
        collect_gem_ids(child, acc)


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from lib.project_root import project_root  # noqa: E402

    root = project_root(Path(__file__))
    monster_dir = root / "server/YurOTS/ots/data/monster"
    out_path = root / "web/data/gem-drops.json"

    by_gem: dict[str, dict[str, list[str]]] = {g["key"]: {t: [] for t in TIERS} for g in GEMS}

    for path in sorted(monster_dir.glob("*.xml")):
        stem = path.stem
        tier = next((t for t in TIERS if stem.startswith(f"{t} ")), None)
        if not tier:
            continue
        base = stem[len(tier) + 1 :]
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            continue
        loot = tree.getroot().find("loot")
        if loot is None:
            continue
        found: set[int] = set()
        collect_gem_ids(loot, found)
        label = title_case(base)
        for gem in GEMS:
            if gem["id"] in found:
                by_gem[gem["key"]][tier].append(label)

    payload = {
        "tiers": [{"id": t, "label": t.capitalize(), "mult": MULT[t]} for t in TIERS],
        "gems": [],
    }
    for gem in GEMS:
        monsters = {t: sorted(by_gem[gem["key"]][t]) for t in TIERS}
        payload["gems"].append(
            {
                **gem,
                "monsters": monsters,
                "counts": {t: len(monsters[t]) for t in TIERS},
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK {out_path} ({len(payload['gems'])} gemas)")


if __name__ == "__main__":
    main()
