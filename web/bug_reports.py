"""Almacén de reportes de bugs enviados desde la web."""
from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path

HOUR_LIMIT = 3
DAY_LIMIT = 8
MAX_STORED = 2000
MAX_TITLE = 80
MAX_DESC = 2000
MAX_CHARACTER = 20

CATEGORIES = frozenset({"gameplay", "crash", "visual", "cuenta", "otro"})


class BugReportStore:
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not self.state_file.is_file():
            return {"reports": [], "ips": {}}
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"reports": [], "ips": {}}
        data.setdefault("reports", [])
        data.setdefault("ips", {})
        return data

    def _save(self, data: dict) -> None:
        tmp = self.state_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.state_file)

    def _prune_ips(self, data: dict, now: float) -> None:
        ips = {}
        for ip, rec in data.get("ips", {}).items():
            hour = [t for t in rec.get("hour", []) if now - t < 3600]
            day = [t for t in rec.get("day", []) if now - t < 86400]
            if hour or day:
                ips[ip] = {"hour": hour, "day": day}
        data["ips"] = ips

    def check_rate(self, ip: str) -> str | None:
        now = time.time()
        data = self._load()
        self._prune_ips(data, now)
        rec = data.setdefault("ips", {}).setdefault(ip, {"hour": [], "day": []})
        if len(rec["hour"]) >= HOUR_LIMIT:
            return "Demasiados reportes desde esta IP. Inténtalo más tarde."
        if len(rec["day"]) >= DAY_LIMIT:
            return "Límite diario de reportes alcanzado desde esta IP."
        return None

    def record_attempt(self, ip: str) -> None:
        now = time.time()
        data = self._load()
        self._prune_ips(data, now)
        rec = data.setdefault("ips", {}).setdefault(ip, {"hour": [], "day": []})
        rec["hour"].append(now)
        rec["day"].append(now)
        self._save(data)

    def add_report(
        self,
        *,
        character: str,
        category: str,
        title: str,
        description: str,
        ip: str,
    ) -> dict:
        character = character.strip()
        title = title.strip()
        description = description.strip()
        category = category.strip().lower()

        if category not in CATEGORIES:
            return {"ok": False, "message": "Categoría inválida."}
        if len(title) < 5:
            return {"ok": False, "message": "El título debe tener al menos 5 caracteres."}
        if len(title) > MAX_TITLE:
            return {"ok": False, "message": f"El título no puede superar {MAX_TITLE} caracteres."}
        if len(description) < 15:
            return {"ok": False, "message": "Describe el bug con al menos 15 caracteres."}
        if len(description) > MAX_DESC:
            return {"ok": False, "message": f"La descripción no puede superar {MAX_DESC} caracteres."}
        if character and (
            len(character) > MAX_CHARACTER
            or not re.fullmatch(r"[a-zA-Z ]{1,20}", character)
        ):
            return {"ok": False, "message": "Nombre de personaje inválido."}

        rate_err = self.check_rate(ip)
        if rate_err:
            return {"ok": False, "message": rate_err}

        now = time.time()
        report = {
            "id": uuid.uuid4().hex[:12],
            "created_at": int(now),
            "ip": ip,
            "character": character,
            "category": category,
            "title": title,
            "description": description,
            "status": "open",
        }

        data = self._load()
        self._prune_ips(data, now)
        reports = data.setdefault("reports", [])
        reports.append(report)
        if len(reports) > MAX_STORED:
            data["reports"] = reports[-MAX_STORED:]
        rec = data.setdefault("ips", {}).setdefault(ip, {"hour": [], "day": []})
        rec["hour"].append(now)
        rec["day"].append(now)
        self._save(data)

        return {
            "ok": True,
            "message": "Reporte enviado. Gracias por ayudar a mejorar Retro76.",
            "id": report["id"],
        }
