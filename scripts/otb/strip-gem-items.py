#!/usr/bin/env python3
"""Remove gem items from player XML saves. Does not touch imbuement actionIds."""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# docs/GEMS.md + const76.h — NOT coins (2148 gold, 2152 platinum).
GEM_ITEM_IDS = frozenset({
    2145,  # small diamond
    2146,  # small sapphire
    2147,  # small ruby
    2149,  # small emerald
    2150,  # small amethyst
    2151,  # talon
    2153,  # violet gem
    2154,  # yellow gem
    2155,  # big emerald
    2156,  # big ruby
    2157,  # gold nugget
    2158,  # blue gem
    2159,  # scarab coin
})

TEMPLATE_PLAYERS = frozenset({"0.xml", "1.xml", "2.xml", "3.xml", "4.xml"})


def item_id(el: ET.Element) -> int | None:
    raw = el.get("id")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def strip_items(parent: ET.Element) -> tuple[int, int]:
    """Remove gem <item> nodes recursively. Returns (removed_items, removed_stacks)."""
    removed_items = 0
    removed_stacks = 0
    for child in list(parent):
        if child.tag == "item":
            iid = item_id(child)
            if iid in GEM_ITEM_IDS:
                count = int(child.get("count", "1"))
                removed_items += 1
                removed_stacks += count
                parent.remove(child)
                continue
            sub_items, sub_stacks = strip_items(child)
            removed_items += sub_items
            removed_stacks += sub_stacks
            inside = child.find("inside")
            if inside is not None and len(inside) == 0:
                child.remove(inside)
        else:
            sub_items, sub_stacks = strip_items(child)
            removed_items += sub_items
            removed_stacks += sub_stacks
    return removed_items, removed_stacks


def process_player(path: Path, dry_run: bool) -> tuple[bool, int, int]:
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag != "player":
        return False, 0, 0

    removed_items = 0
    removed_stacks = 0
    for section in ("inventory", "depots"):
        node = root.find(section)
        if node is None:
            continue
        items, stacks = strip_items(node)
        removed_items += items
        removed_stacks += stacks

    if removed_items == 0:
        return False, 0, 0

    if not dry_run:
        tree.write(path, encoding="unicode", xml_declaration=True)
    return True, removed_items, removed_stacks


def process_houseitems(path: Path, dry_run: bool) -> tuple[bool, int, int]:
    if not path.is_file():
        return False, 0, 0
    tree = ET.parse(path)
    root = tree.getroot()
    removed_items = 0
    removed_stacks = 0
    items, stacks = strip_items(root)
    removed_items += items
    removed_stacks += stacks
    if removed_items == 0:
        return False, 0, 0
    if not dry_run:
        tree.write(path, encoding="unicode", xml_declaration=True)
    return True, removed_items, removed_stacks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "data_dir",
        type=Path,
        help="Path to server/YurOTS/ots/data",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    players_dir = data_dir / "players"
    houseitems = data_dir / "houseitems.xml"

    if not players_dir.is_dir():
        print(f"ERROR: no existe {players_dir}", file=sys.stderr)
        return 1

    changed_players = 0
    total_items = 0
    total_stacks = 0

    for path in sorted(players_dir.glob("*.xml")):
        if path.name in TEMPLATE_PLAYERS:
            continue
        changed, items, stacks = process_player(path, args.dry_run)
        if changed:
            changed_players += 1
            total_items += items
            total_stacks += stacks
            mode = "would strip" if args.dry_run else "stripped"
            print(f"{mode}: {path.name} ({items} nodes, {stacks} stack count)")

    changed_house, h_items, h_stacks = process_houseitems(houseitems, args.dry_run)
    if changed_house:
        mode = "would strip" if args.dry_run else "stripped"
        print(f"{mode}: houseitems.xml ({h_items} nodes, {h_stacks} stack count)")
        total_items += h_items
        total_stacks += h_stacks

    prefix = "DRY-RUN" if args.dry_run else "OK"
    print(
        f"{prefix}: {changed_players} players touched, "
        f"{total_items} item nodes, {total_stacks} total stack count"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
