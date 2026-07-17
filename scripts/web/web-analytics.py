#!/usr/bin/env python3
"""Resumen interno de visitas y descargas de retro76.cl (no público)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))

from analytics import WebAnalytics  # noqa: E402

STATE = Path(os.environ.get("ANALYTICS_STATE", ROOT / "web/state/analytics.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Estadísticas internas de la web Retro76")
    parser.add_argument("--days", type=int, default=30, help="Días a mostrar (default: 30)")
    args = parser.parse_args()

    rows = WebAnalytics(STATE).summary(last_days=args.days)
    if not rows:
        print("Sin datos todavía.")
        return 0

    print(f"{'Fecha':<12} {'Visitantes':>10} {'Win':>6} {'Mac':>6} {'Total DL':>9}")
    print("-" * 48)
    for r in rows:
        print(
            f"{r['date']:<12} {r['visitors']:>10} "
            f"{r['downloads_windows']:>6} {r['downloads_mac']:>6} {r['downloads_total']:>9}"
        )

    today = rows[-1] if rows else None
    if today:
        print()
        print(
            f"Hoy ({today['date']}): {today['visitors']} visitantes únicos, "
            f"{today['downloads_total']} descargas "
            f"(Win {today['downloads_windows']}, Mac {today['downloads_mac']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
