#!/usr/bin/env python3
"""Resumen del funnel premium desde web/state/analytics.json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FUNNEL = [
    "tab_view",
    "checkout_open",
    "plan_select",
    "step2",
    "amulet_toggle",
    "step3",
    "receipt_selected",
    "submit_click",
    "submit_received",
    "submit_ok",
    "submit_fail",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "web/state/analytics.json",
    )
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    if not args.file.is_file():
        print(f"No existe {args.file}", file=sys.stderr)
        return 1

    data = json.loads(args.file.read_text(encoding="utf-8"))
    days = sorted(data.get("days", {}).keys(), reverse=True)[: args.days]
    totals = {k: 0 for k in FUNNEL}
    all_recent: list[dict] = []

    for day in sorted(days):
        premium = data["days"][day].get("premium", {})
        counts = premium.get("counts", {})
        for k in FUNNEL:
            totals[k] += counts.get(k, 0)
        for ev in premium.get("recent", []):
            ev = dict(ev)
            ev["date"] = day
            all_recent.append(ev)

    print(f"Funnel premium (últimos {len(days)} días con datos)\n")
    for k in FUNNEL:
        print(f"  {k:18} {totals[k]:4}")

    if all_recent:
        print("\nÚltimos eventos:")
        for ev in sorted(all_recent, key=lambda e: e.get("t", 0))[-25:]:
            detail = ev.get("detail")
            extra = f" {detail}" if detail else ""
            print(f"  [{ev.get('date')}] {ev.get('event')} {ev.get('ip', '')}{extra}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
