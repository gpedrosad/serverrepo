"""Parse player spells from spells.xml for the web UI."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

# Base vocations shown on the web (promoted paladin shares id 5 with some spells).
VOCATION_SECTIONS: tuple[tuple[str, str, frozenset[int]], ...] = (
    ("sorcerer", "Sorcerer", frozenset({1})),
    ("druid", "Druid", frozenset({2})),
    ("paladin", "Paladin", frozenset({3, 5})),
    ("knight", "Knight", frozenset({4})),
)

_SKIP_SPELL_NAMES = frozenset({"death"})
_MAX_PLAYER_MAGLV = 99

_SPELL_OPEN = re.compile(
    r'<spell\s+name="([^"]+)"\s+words="([^"]+)"\s+maglv="(\d+)"\s+mana="(\d+)"\s+enabled="(\d+)"',
    re.IGNORECASE,
)
_VOCATION_ID = re.compile(r'<vocation\s+id="(\d+)"')


def _spell_kind(words: str) -> str:
    w = words.lower()
    if w.startswith("exevo con"):
        return "Munición"
    if w.startswith(("adori", "adevo", "adura", "adana", "adito", "adeta")):
        return "Runa"
    return "Instant"


def _parse_spells_xml(text: str) -> list[dict]:
    spells: list[dict] = []
    for match in _SPELL_OPEN.finditer(text):
        name, words, maglv_s, mana_s, enabled = match.groups()
        if enabled != "1" or name.lower() in _SKIP_SPELL_NAMES:
            continue
        maglv = int(maglv_s)
        if maglv > _MAX_PLAYER_MAGLV:
            continue

        chunk = text[match.start() : match.end() + 400]
        voc_ids = {int(v) for v in _VOCATION_ID.findall(chunk)}
        if not voc_ids:
            continue

        spells.append(
            {
                "name": name,
                "words": words,
                "maglv": maglv,
                "mana": int(mana_s),
                "kind": _spell_kind(words),
                "vocations": sorted(voc_ids),
            }
        )
    return spells


@lru_cache(maxsize=4)
def _cached_by_path(path_str: str, mtime_ns: int) -> dict:
    path = Path(path_str)
    text = path.read_text(encoding="utf-8", errors="replace")
    all_spells = _parse_spells_xml(text)

    sections: list[dict] = []
    for section_id, label, voc_ids in VOCATION_SECTIONS:
        items = [s for s in all_spells if voc_ids.intersection(s["vocations"])]
        items.sort(key=lambda s: (s["mana"], s["maglv"], s["name"].lower()))
        sections.append(
            {
                "id": section_id,
                "label": label,
                "count": len(items),
                "spells": items,
            }
        )

    return {"sections": sections, "total": len(all_spells)}


def build_spells_payload(spells_file: Path) -> dict:
    if not spells_file.is_file():
        return {"sections": [], "total": 0}
    stat = spells_file.stat()
    return _cached_by_path(str(spells_file.resolve()), stat.st_mtime_ns)
