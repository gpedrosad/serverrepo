#!/usr/bin/env python3
"""Review every natural entrance and match its native sprite to the surrounding terrain.

python3.11 scripts/map/style-hole-entrances.py [--apply]
Does not open clients, start servers or change positions/landing geometry.
"""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import struct
import sys

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / "kb")]
from mapdata import MAP, REPO, load_otb, parse_tree, serialize_tree
from epstein_cave_repair import index
from portal_temple_style import item_offsets
from hole_entrance_style import HOLES, choose

REPORT = MAP.parent / "generated-hole-entrances.json"


def walkable(ids, otb):
    return bool(ids) and not any("block_solid" in otb[i]["flags"] for i in ids)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    raw = MAP.read_bytes()
    root = parse_tree(raw)
    otb = load_otb()
    nodes, values, _ = index(root, otb)
    previous = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    prior = {tuple(r["position"]): r for r in previous.get("entrances", [])}
    actions = (REPO / "server/YurOTS/ots/data/actions/actions.xml").read_text()
    records, changed = [], {}
    for p, ids in sorted(values.items()):
        source = next((i for i in ids if i in HOLES), None)
        # A previous natural hole on a wooden floor becomes the matching native ladder cutout.
        if source is None and p in prior and prior[p]["target"] == 409 and 409 in ids:
            source = 409
        if source is None:
            continue
        assert len(nodes[p]) == 1 and nodes[p][0][0] == 5, p
        target, family = choose(values, p, otb, source)
        assert f'itemid="{target}" script="teleport.lua"' in actions, target
        x, y, z = p
        lower = values.get((x, y, z + 1), [])
        assert 1386 in lower and walkable(lower, otb), (p, "blocked descent", lower)
        assert walkable(values.get((x, y + 1, z), []), otb), (p, "blocked return")
        record = dict(position=list(p), source=prior.get(p, {}).get("source", source),
                      target=target, terrain=family, down=[x, y, z + 1], up=[x, y + 1, z])
        records.append(record)
        if target != source:
            new = [target if i == source else i for i in ids]
            changed[p] = (ids, new)
            for props, offset in item_offsets(nodes[p][0], otb):
                if struct.unpack_from("<H", props, offset)[0] == source:
                    struct.pack_into("<H", props, offset, target)
    print(json.dumps(dict(reviewed=len(records), changed=len(changed),
                          terrain=dict(Counter(r["terrain"] for r in records)),
                          arrivals="all clear")))
    for p, (old, new) in changed.items():
        print(f"  {p}: {old} -> {new}")
    if not args.apply:
        return
    # Update exact tile-id manifests so generators still recognize their own tiles.
    updates = {}
    for path in sorted(MAP.parent.glob("generated-*.json")):
        if path == REPORT:
            continue
        data = json.loads(path.read_text())
        cells = data.get("cells")
        count = 0
        if isinstance(cells, dict):
            for p, (old, new) in changed.items():
                key = ",".join(map(str, p))
                if cells.get(key) == old:
                    cells[key] = new
                    count += 1
        if count:
            updates[path] = json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
    backup = REPO / "backups/map" / ("hole-entrances-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    for path in [MAP, *updates]:
        shutil.copy2(path, backup / path.name)
    MAP.write_bytes(serialize_tree(root, raw[:4]))
    for path, text in updates.items():
        path.write_text(text)
    REPORT.write_text('{"version":1,"entrances":[\n' + ",\n".join(json.dumps(r, separators=(",", ":")) for r in records) + "\n]}\n")
    print(f"Updated {len(updates)} ownership manifests; backup: {backup}")


if __name__ == "__main__":
    main()
