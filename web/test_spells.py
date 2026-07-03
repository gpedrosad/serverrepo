from __future__ import annotations

import unittest
from pathlib import Path

from spells import build_spells_payload


SPELLS_XML = Path(__file__).resolve().parents[1] / "server/YurOTS/ots/data/spells/spells.xml"


class SpellsPayloadTests(unittest.TestCase):
    def test_builds_sections_sorted_by_mana(self) -> None:
        payload = build_spells_payload(SPELLS_XML)
        self.assertGreater(payload["total"], 40)
        sections = {s["id"]: s for s in payload["sections"]}
        self.assertEqual(set(sections), {"sorcerer", "druid", "paladin", "knight"})

        sorc = sections["sorcerer"]["spells"]
        self.assertGreater(len(sorc), 20)
        manas = [s["mana"] for s in sorc]
        self.assertEqual(manas, sorted(manas))
        self.assertEqual(sorc[0]["mana"], min(manas))

    def test_excludes_monster_and_death_spells(self) -> None:
        payload = build_spells_payload(SPELLS_XML)
        names = {s["name"] for sec in payload["sections"] for s in sec["spells"]}
        self.assertNotIn("death", {n.lower() for n in names})
        self.assertNotIn("banshee_sonar", names)

    def test_paladin_includes_promoted_only_spells(self) -> None:
        payload = build_spells_payload(SPELLS_XML)
        pal = next(s for s in payload["sections"] if s["id"] == "paladin")
        words = {s["words"] for s in pal["spells"]}
        self.assertIn("exevo con", words)
        self.assertIn("utani slow", words)


if __name__ == "__main__":
    unittest.main()
