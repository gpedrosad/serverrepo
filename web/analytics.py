"""Registro interno de visitas y descargas de la web (no público)."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

DOWNLOAD_KEYS = {
    "Retro76-Windows.zip": "windows",
    "Retro76-Mac.zip": "mac",
}

_lock = threading.Lock()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class WebAnalytics:
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not self.state_file.is_file():
            return {"days": {}}
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"days": {}}
        if "days" not in data:
            data["days"] = {}
        return data

    def _save(self, data: dict) -> None:
        tmp = self.state_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.state_file)

    def _day_bucket(self, data: dict, day: str) -> dict:
        days = data.setdefault("days", {})
        bucket = days.setdefault(
            day,
            {"visitors": [], "downloads": {"windows": 0, "mac": 0}},
        )
        bucket.setdefault("visitors", [])
        bucket.setdefault("downloads", {"windows": 0, "mac": 0})
        return bucket

    def record_visit(self, ip: str) -> None:
        if not ip:
            return
        with _lock:
            data = self._load()
            bucket = self._day_bucket(data, _today())
            if ip not in bucket["visitors"]:
                bucket["visitors"].append(ip)
            self._save(data)

    def record_download(self, filename: str) -> None:
        key = DOWNLOAD_KEYS.get(filename)
        if not key:
            return
        with _lock:
            data = self._load()
            bucket = self._day_bucket(data, _today())
            bucket["downloads"][key] = bucket["downloads"].get(key, 0) + 1
            self._save(data)

    def summary(self, last_days: int = 30) -> list[dict]:
        data = self._load()
        days = sorted(data.get("days", {}).keys(), reverse=True)[:last_days]
        rows = []
        for day in sorted(days):
            bucket = data["days"][day]
            dl = bucket.get("downloads", {})
            rows.append(
                {
                    "date": day,
                    "visitors": len(bucket.get("visitors", [])),
                    "downloads_windows": dl.get("windows", 0),
                    "downloads_mac": dl.get("mac", 0),
                    "downloads_total": dl.get("windows", 0) + dl.get("mac", 0),
                }
            )
        return rows
