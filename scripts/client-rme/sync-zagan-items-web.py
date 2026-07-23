#!/usr/bin/env python3
"""Copia previews Zagan a la web privada y genera el catálogo JSON."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.project_root import project_root  # noqa: E402

ROOT = project_root(Path(__file__))
sys.path.insert(0, str(ROOT / "web"))

from zagan_items import sync_all  # noqa: E402


def main() -> None:
    result = sync_all()
    print(f"Zagan web catalog: {result['items']} items, {result['images']} images")


if __name__ == "__main__":
    main()
