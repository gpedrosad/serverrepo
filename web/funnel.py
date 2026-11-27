"""Hitos del embudo de jugadores (desde el 27 nov 2026): una línea JSON por hito, con la IP para poder seguir a la
misma persona de un paso al siguiente (visita → descarga → abre el cliente → cuenta → primer login → niveles → premium).

Escribe en server/YurOTS/ots/data/logs/funnel-AAAA-MM.jsonl, junto a logins-*.jsonl. La web registra los pasos web
(visit, download, client_open, account_created, premium_click); scripts/ot/collect-metrics.py los del juego
(first_login, level, promoted, premium_active, house). Los pasos `once` se registran una sola vez por IP (la primera
vez que esa IP lo hace); la lista de IPs ya vistas vive en web/state/funnel_seen.json.

Runtime con IPs: en .gitignore, no se commitea. Doc: docs/systems/METRICAS.md#embudo.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

_lock = threading.Lock()
MAX_SEEN = 200_000   # tope por paso: con IPs inventadas el archivo no crece sin fin


class Funnel:
    def __init__(self, logs_dir: Path, seen_file: Path) -> None:
        self.logs_dir = logs_dir
        self.seen_file = seen_file
        self._seen: dict[str, set[str]] | None = None

    def _load_seen(self) -> dict[str, set[str]]:
        if self._seen is None:
            try:
                raw = json.loads(self.seen_file.read_text(encoding="utf-8"))
                self._seen = {k: set(v) for k, v in raw.items()}
            except (OSError, json.JSONDecodeError):
                self._seen = {}
        return self._seen

    def _save_seen(self) -> None:
        tmp = self.seen_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({k: sorted(v) for k, v in (self._seen or {}).items()}), encoding="utf-8")
        tmp.replace(self.seen_file)

    def record(self, step: str, ip: str, *, once: bool = False, **extra) -> bool:
        """Registra el hito. Con once=True solo la primera vez de esa IP para ese paso. Devuelve si escribió.
        Sin once, igual marca `first` = si es la primera vez de esa IP en ese paso."""
        now = time.time()
        try:
            with _lock:
                seen = self._load_seen().setdefault(step, set())
                first = bool(ip) and ip not in seen
                if once and not first:
                    return False
                if first and len(seen) < MAX_SEEN:
                    seen.add(ip)
                    self.seen_file.parent.mkdir(parents=True, exist_ok=True)
                    self._save_seen()
                row = {"t": int(now), "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
                       "step": step, "ip": ip or "", "first": first}
                row.update({k: v for k, v in extra.items() if v not in (None, "")})
                self.logs_dir.mkdir(parents=True, exist_ok=True)
                with (self.logs_dir / time.strftime("funnel-%Y-%m.jsonl", time.gmtime(now))).open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            return True
        except OSError:
            return False
