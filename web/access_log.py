"""Eventos de alta de cuentas desde la web, en el mismo formato que el registro de logins del juego.

Escribe una línea JSON por evento en server/YurOTS/ots/data/logs/web-AAAA-MM.jsonl (junto a
logins-AAAA-MM.jsonl, que escribe el servidor C++). Nunca se guarda la contraseña.
Ver docs/systems/LOGIN_EVENTS.md.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

_lock = threading.Lock()


class AccessLog:
    def __init__(self, logs_dir: Path) -> None:
        self.logs_dir = logs_dir

    def record(self, event: str, acc: int, name: str, ip: str, reason: str = "", **extra) -> None:
        now = time.time()
        row = {
            "t": int(now),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "event": event,
            "acc": int(acc) if acc else 0,
            "name": name or "",
            "ip": ip or "",
        }
        if reason:
            row["reason"] = reason
        row.update(extra)
        path = self.logs_dir / time.strftime("web-%Y-%m.jsonl", time.gmtime(now))
        line = json.dumps(row, ensure_ascii=False) + "\n"
        try:
            with _lock:
                self.logs_dir.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8") as f:
                    f.write(line)
        except OSError:
            # El registro nunca debe impedir crear la cuenta.
            pass
