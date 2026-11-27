"""Registro interno de visitas y descargas de la web (no público)."""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

DOWNLOAD_KEYS = {
    "Retro76-Windows.zip": "windows",
    "Retro76-Mac.zip": "mac",
}

MAX_VISITORS_PER_DAY = 20000


def analytics_download_key(filename: str) -> str:
    return DOWNLOAD_KEYS.get(filename, "")   # tope: con IPs inventadas el archivo no crece sin fin
PREMIUM_EVENTS = frozenset({
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
})

MAX_PREMIUM_RECENT = 200

_lock = threading.Lock()


def _today() -> str:
    # Hora local del contenedor (TZ=America/Santiago en el VPS): los días cortan igual que el resto de las métricas.
    return datetime.now().strftime("%Y-%m-%d")


FLUSH_SECONDS = 30   # se escribe a disco como mucho cada 30 s (antes: el JSON entero en cada página vista)


class WebAnalytics:
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict | None = None
        self._last_save = 0.0
        self._dirty = False

    def _read_disk(self) -> dict:
        if not self.state_file.is_file():
            return {"days": {}}
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"days": {}}
        if "days" not in data:
            data["days"] = {}
        return data

    def _load(self) -> dict:
        """Estado en memoria (se lee del disco una sola vez). Llamar con _lock tomado."""
        if self._data is None:
            self._data = self._read_disk()
        return self._data

    def _save(self, data: dict) -> None:
        """Marca cambios y escribe si pasaron FLUSH_SECONDS desde la última vez. Llamar con _lock tomado."""
        self._data = data
        self._dirty = True
        if time.monotonic() - self._last_save >= FLUSH_SECONDS:
            self._write()

    def _write(self) -> None:
        if self._data is None or not self._dirty:
            return
        tmp = self.state_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.state_file)
        self._last_save = time.monotonic()
        self._dirty = False

    def flush(self) -> None:
        """Escribe lo pendiente (lo llama un hilo cada FLUSH_SECONDS y el apagado de la web)."""
        with _lock:
            try:
                self._write()
            except OSError:
                pass

    def _day_bucket(self, data: dict, day: str) -> dict:
        days = data.setdefault("days", {})
        bucket = days.setdefault(
            day,
            {"visitors": [], "downloads": {"windows": 0, "mac": 0}, "premium": {"counts": {}, "recent": []}},
        )
        bucket.setdefault("visitors", [])
        bucket.setdefault("downloads", {"windows": 0, "mac": 0})
        # Desde el 27 nov 2026 (docs/systems/METRICAS.md): páginas vistas, de dónde llegan, idioma y clientes del updater.
        for key in ("pageviews", "referrers", "langs", "locales"):
            bucket.setdefault(key, {})
        bucket.setdefault("updater_ips", [])
        bucket.setdefault("updater_checks", 0)
        premium = bucket.setdefault("premium", {"counts": {}, "recent": []})
        premium.setdefault("counts", {})
        premium.setdefault("recent", [])
        return bucket

    def record_visit(self, ip: str) -> None:
        if not ip:
            return
        with _lock:
            data = self._load()
            bucket = self._day_bucket(data, _today())
            if ip not in bucket["visitors"] and len(bucket["visitors"]) < MAX_VISITORS_PER_DAY:
                bucket["visitors"].append(ip)
            self._save(data)

    def record_pageview(self, ip: str, path: str, lang: str, referrer_host: str = "", locale: str = "") -> None:
        """Una página del sitio servida: visitante único del día, vistas por página, idioma de la página,
        sitio de origen (solo hosts externos: otservlist.org, google...) y locale del navegador (pt-BR, es-CL...)."""
        def bump(d: dict, key: str, cap: int = 500) -> None:
            if key and (key in d or len(d) < cap):
                d[key] = d.get(key, 0) + 1
        with _lock:
            data = self._load()
            bucket = self._day_bucket(data, _today())
            if ip and ip not in bucket["visitors"] and len(bucket["visitors"]) < MAX_VISITORS_PER_DAY:
                bucket["visitors"].append(ip)
            bump(bucket["pageviews"], path[:80])
            bump(bucket["langs"], lang)
            bump(bucket["referrers"], referrer_host[:80])
            bump(bucket["locales"], locale[:12])
            self._save(data)

    def record_updater(self, ip: str) -> None:
        """El cliente abrió y pidió la lista del updater: cuenta chequeos y clientes únicos (instalaciones activas)."""
        with _lock:
            data = self._load()
            bucket = self._day_bucket(data, _today())
            bucket["updater_checks"] = bucket.get("updater_checks", 0) + 1
            if ip and ip not in bucket["updater_ips"] and len(bucket["updater_ips"]) < MAX_VISITORS_PER_DAY:
                bucket["updater_ips"].append(ip)
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

    def record_premium_event(self, ip: str, event: str, detail: dict | None = None) -> None:
        if event not in PREMIUM_EVENTS:
            return
        with _lock:
            data = self._load()
            bucket = self._day_bucket(data, _today())
            premium = bucket["premium"]
            counts = premium["counts"]
            counts[event] = counts.get(event, 0) + 1
            entry = {
                "t": int(datetime.now(timezone.utc).timestamp()),
                "ip": ip or "",
                "event": event,
            }
            if detail:
                entry["detail"] = detail
            recent = premium["recent"]
            recent.append(entry)
            if len(recent) > MAX_PREMIUM_RECENT:
                del recent[: len(recent) - MAX_PREMIUM_RECENT]
            self._save(data)

    def premium_summary(self, last_days: int = 30) -> list[dict]:
        data = self._load()
        days = sorted(data.get("days", {}).keys(), reverse=True)[:last_days]
        rows = []
        for day in sorted(days):
            premium = data["days"][day].get("premium", {})
            counts = premium.get("counts", {})
            rows.append(
                {
                    "date": day,
                    "counts": dict(counts),
                    "recent": list(premium.get("recent", [])),
                }
            )
        return rows

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
                    "pageviews": sum(bucket.get("pageviews", {}).values()),
                    "top_pages": dict(sorted(bucket.get("pageviews", {}).items(), key=lambda kv: -kv[1])[:8]),
                    "referrers": dict(sorted(bucket.get("referrers", {}).items(), key=lambda kv: -kv[1])[:8]),
                    "langs": dict(bucket.get("langs", {})),
                    "locales": dict(sorted(bucket.get("locales", {}).items(), key=lambda kv: -kv[1])[:8]),
                    "updater_clients": len(bucket.get("updater_ips", [])),
                    "updater_checks": bucket.get("updater_checks", 0),
                    "premium": dict(bucket.get("premium", {}).get("counts", {})),
                }
            )
        return rows
