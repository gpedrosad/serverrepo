"""Resolve the yurots-principal repo root (AGENTS.md / .git).

Python scripts live under scripts/<subdir>/ after the folder reorg. Hardcoding
parents[1] points at scripts/, not the repo — use this helper instead.
"""
from __future__ import annotations

from pathlib import Path


def project_root(start: Path | None = None) -> Path:
    """Walk up from *start* (default: this file) until AGENTS.md or .git."""
    cur = (start or Path(__file__)).resolve()
    if cur.is_file():
        cur = cur.parent
    for p in [cur, *cur.parents]:
        if (p / "AGENTS.md").is_file() or (p / ".git").is_dir():
            return p
    raise RuntimeError("no se encontró la raíz del repo (AGENTS.md / .git)")


def scripts_dir(start: Path | None = None) -> Path:
    """Canonical scripts/ directory (repo_root / 'scripts')."""
    return project_root(start) / "scripts"
