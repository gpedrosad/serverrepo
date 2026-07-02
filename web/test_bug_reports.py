from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bug_reports import BugReportStore


class BugReportStoreTests(unittest.TestCase):
    def test_add_report_persists_and_rate_limits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = BugReportStore(Path(tmp) / "bugs.json")
            ip = "203.0.113.10"

            ok = store.add_report(
                character="Test Knight",
                category="gameplay",
                title="El NPC no responde",
                description="Hablé con el NPC en el temple y no abrió el diálogo de trade.",
                ip=ip,
            )
            self.assertTrue(ok["ok"])
            self.assertIn("id", ok)

            data = store._load()
            self.assertEqual(len(data["reports"]), 1)
            self.assertEqual(data["reports"][0]["character"], "Test Knight")
            self.assertEqual(data["reports"][0]["category"], "gameplay")
            self.assertEqual(data["reports"][0]["ip"], ip)

            for i in range(2):
                result = store.add_report(
                    character="",
                    category="crash",
                    title=f"Crash número {i}",
                    description="El cliente se cerró solo al entrar al depot del temple.",
                    ip=ip,
                )
                self.assertTrue(result["ok"])

            blocked = store.add_report(
                character="",
                category="otro",
                title="Cuarto reporte bloqueado",
                description="Este reporte debería ser rechazado por límite horario.",
                ip=ip,
            )
            self.assertFalse(blocked["ok"])
            self.assertIn("Demasiados reportes", blocked["message"])

    def test_validation_rejects_short_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = BugReportStore(Path(tmp) / "bugs.json")
            result = store.add_report(
                character="",
                category="visual",
                title="Sprite roto",
                description="muy corto",
                ip="127.0.0.1",
            )
            self.assertFalse(result["ok"])
            self.assertEqual(store._load()["reports"], [])


if __name__ == "__main__":
    unittest.main()
