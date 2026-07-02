"""Protección básica para registro web: captcha, rate limit, honeypot."""
from __future__ import annotations

import json
import random
import time
import uuid
from pathlib import Path

HOUR_LIMIT = 5
DAY_LIMIT = 15
CHALLENGE_TTL = 600
MIN_FORM_SECONDS = 3


class RegisterGuard:
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not self.state_file.is_file():
            return {"ips": {}, "challenges": {}}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"ips": {}, "challenges": {}}

    def _save(self, data: dict) -> None:
        self.state_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _prune(self, data: dict, now: float) -> None:
        data["challenges"] = {
            k: v for k, v in data.get("challenges", {}).items() if v.get("exp", 0) > now
        }
        ips = {}
        for ip, rec in data.get("ips", {}).items():
            hour = [t for t in rec.get("hour", []) if now - t < 3600]
            day = [t for t in rec.get("day", []) if now - t < 86400]
            if hour or day:
                ips[ip] = {"hour": hour, "day": day}
        data["ips"] = ips

    def new_challenge(self) -> dict:
        now = time.time()
        data = self._load()
        self._prune(data, now)
        a, b = random.randint(2, 9), random.randint(2, 9)
        cid = uuid.uuid4().hex
        data.setdefault("challenges", {})[cid] = {"a": a, "b": b, "exp": now + CHALLENGE_TTL}
        self._save(data)
        return {"id": cid, "question": f"{a} + {b}"}

    def check_rate(self, ip: str) -> str | None:
        now = time.time()
        data = self._load()
        self._prune(data, now)
        rec = data.setdefault("ips", {}).setdefault(ip, {"hour": [], "day": []})
        if len(rec["hour"]) >= HOUR_LIMIT:
            return "Demasiados intentos. Inténtalo más tarde."
        if len(rec["day"]) >= DAY_LIMIT:
            return "Límite diario alcanzado desde esta IP."
        return None

    def record_attempt(self, ip: str) -> None:
        now = time.time()
        data = self._load()
        self._prune(data, now)
        rec = data.setdefault("ips", {}).setdefault(ip, {"hour": [], "day": []})
        rec["hour"].append(now)
        rec["day"].append(now)
        self._save(data)

    def verify_captcha(
        self,
        challenge_id: str,
        answer: str,
        honeypot: str,
        form_ts: float,
        *,
        honeypot_message: str = "No se pudo enviar el formulario.",
    ) -> str | None:
        if honeypot:
            return honeypot_message
        if time.time() - form_ts < MIN_FORM_SECONDS:
            return "El formulario se envió demasiado rápido."
        now = time.time()
        data = self._load()
        self._prune(data, now)
        ch = data.get("challenges", {}).pop(challenge_id, None)
        self._save(data)
        if not ch:
            return "Captcha expirado. Recarga la página."
        try:
            if int(str(answer).strip()) != ch["a"] + ch["b"]:
                return "Captcha incorrecto."
        except (TypeError, ValueError):
            return "Captcha incorrecto."
        return None

    def verify(
        self,
        ip: str,
        challenge_id: str,
        answer: str,
        honeypot: str,
        form_ts: float,
    ) -> str | None:
        captcha_err = self.verify_captcha(
            challenge_id,
            answer,
            honeypot,
            form_ts,
            honeypot_message="No se pudo crear la cuenta.",
        )
        if captcha_err:
            return captcha_err
        return self.check_rate(ip)
