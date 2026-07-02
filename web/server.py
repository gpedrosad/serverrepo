#!/usr/bin/env python3
"""Retro76 web — highscores, status, deaths, OTINFO."""
from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from analytics import WebAnalytics
from data import build_payload, create_account, read_server_ip, server_status_from_files
from debug_log import get_logger, log_exception, log_http, setup_logging
from premium_orders import create_premium_order, parse_multipart_form, premium_config_payload
from register_guard import RegisterGuard

ROOT = Path(__file__).resolve().parents[1]
PLAYERS_DIR = Path(os.environ.get("PLAYERS_DIR", ROOT / "server/YurOTS/ots/data/players"))
ACCOUNTS_DIR = Path(os.environ.get("ACCOUNTS_DIR", ROOT / "server/YurOTS/ots/data/accounts"))
OTINFO_FILE = Path(os.environ.get("OTINFO_FILE", ROOT / "OTINFO"))
ONLINE_FILE = Path(os.environ.get("ONLINE_FILE", ROOT / "server/YurOTS/ots/data/online.xml"))
STATE_FILE = Path(os.environ.get("STATE_FILE", ROOT / "web/state/daily.json"))
PEAK_STATE = Path(os.environ.get("PEAK_STATE", ROOT / "web/state/peak.json"))
REGISTER_STATE = Path(os.environ.get("REGISTER_STATE", ROOT / "web/state/register.json"))
PREMIUM_ORDERS_FILE = Path(os.environ.get("PREMIUM_ORDERS_FILE", ROOT / "web/state/premium_orders.json"))
PREMIUM_UPLOADS_DIR = Path(os.environ.get("PREMIUM_UPLOADS_DIR", ROOT / "web/uploads/comprobantes"))
ANALYTICS_STATE = Path(os.environ.get("ANALYTICS_STATE", ROOT / "web/state/analytics.json"))
CONFIG_FILE = Path(os.environ.get("CONFIG_FILE", ROOT / "server/YurOTS/ots/config.lua"))
OT_HOST = os.environ.get("OT_HOST", "127.0.0.1")
OT_PORT = int(os.environ.get("OT_PORT", "7171"))
SERVER_IP = os.environ.get("SERVER_IP") or read_server_ip(CONFIG_FILE)
PORT = int(os.environ.get("PORT", "8080"))
INDEX = Path(__file__).resolve().parent / "index.html"
DOWNLOADS_DIR = Path(__file__).resolve().parent / "downloads"
WEB_DIR = Path(__file__).resolve().parent
ASSET_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}

guard = RegisterGuard(REGISTER_STATE)
analytics = WebAnalytics(ANALYTICS_STATE)
setup_logging()
log = get_logger("server")
_ot_monitor_last_online: bool | None = None


def get_payload() -> dict:
    t0 = time.monotonic()
    try:
        return build_payload(
            PLAYERS_DIR,
            OTINFO_FILE,
            ONLINE_FILE,
            STATE_FILE,
            OT_HOST,
            OT_PORT,
            SERVER_IP,
            PEAK_STATE,
            CONFIG_FILE,
        )
    except Exception as exc:
        log_exception("payload", exc, context="build_payload")
        raise
    finally:
        elapsed_ms = (time.monotonic() - t0) * 1000
        if elapsed_ms >= 2000:
            log.warning("build_payload lento: %.0fms", elapsed_ms)


def ot_monitor_loop() -> None:
    global _ot_monitor_last_online
    monitor_log = get_logger("monitor")
    while True:
        time.sleep(60)
        try:
            status = server_status_from_files(ONLINE_FILE, CONFIG_FILE, PEAK_STATE)
            online = bool(status.get("online"))
            players = status.get("players_online", 0)
            source = status.get("source", "?")
            if _ot_monitor_last_online is not None and online != _ot_monitor_last_online:
                monitor_log.warning(
                    "OT cambió estado (%s): %s → %s (players=%s)",
                    source,
                    _ot_monitor_last_online,
                    online,
                    players,
                )
            if not online:
                monitor_log.warning("OT offline según %s (players=%s)", source, players)
            _ot_monitor_last_online = online
        except Exception as exc:
            log_exception("monitor", exc, context="ot_monitor_loop")


def client_ip(handler: BaseHTTPRequestHandler) -> str:
    headers = getattr(handler, "headers", None)
    if headers is not None:
        fwd = headers.get("X-Forwarded-For", "")
        if fwd:
            return fwd.split(",")[0].strip()
    addr = getattr(handler, "client_address", None)
    if addr:
        return addr[0]
    return "?"


class Handler(BaseHTTPRequestHandler):
    server_version = "Retro76Web/1.0"
    _response_code = 0

    def send_response(self, code: int, message: str | None = None) -> None:
        self._response_code = code
        super().send_response(code, message)

    def handle_one_request(self) -> None:
        t0 = time.monotonic()
        self._response_code = 0
        path = "?"
        try:
            super().handle_one_request()
            path = self.path.split("?", 1)[0]
        except (ConnectionResetError, BrokenPipeError):
            self._response_code = 499
            path = getattr(self, "path", "?").split("?", 1)[0]
        except Exception as exc:
            path = getattr(self, "path", "?").split("?", 1)[0]
            log_exception("http", exc, context=f"{self.command} {path}")
            try:
                self.send_error(500, "Internal Server Error")
            except Exception:
                pass
        finally:
            elapsed_ms = (time.monotonic() - t0) * 1000
            code = self._response_code or 0
            cmd = getattr(self, "command", "?")
            log_http(cmd, path, code, elapsed_ms, client_ip(self))

    def _json(self, code: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_HEAD(self) -> None:
        path = self.path.split("?", 1)[0]
        if path.startswith("/downloads/"):
            self._download(path[len("/downloads/"):], head_only=True)
        elif path.startswith("/assets/") or path.startswith("/components/"):
            self._static(path, head_only=True)
        else:
            self.send_error(404)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            analytics.record_visit(client_ip(self))
            self._file(INDEX, "text/html; charset=utf-8")
        elif path == "/api/data":
            try:
                self._json(200, get_payload())
            except Exception as exc:
                log_exception("api", exc, context="/api/data")
                self._json(500, {"ok": False, "message": "Error interno al cargar datos"})
        elif path == "/api/register-challenge":
            self._json(200, guard.new_challenge())
        elif path == "/api/premium-config":
            self._json(200, premium_config_payload())
        elif path == "/api/premium-analytics":
            self._premium_analytics()
        elif path.startswith("/downloads/"):
            self._download(path[len("/downloads/"):])
        elif path.startswith("/assets/") or path.startswith("/components/"):
            self._static(path)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/api/create-account":
            self._create_account()
        elif path == "/api/premium-event":
            self._premium_event()
        elif path == "/api/premium-order":
            self._premium_order()
        else:
            self.send_error(404)

    def _create_account(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        ip = client_ip(self)
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            err = guard.verify(
                ip,
                str(body.get("challenge_id", "")),
                str(body.get("captcha", "")),
                str(body.get("company", "")),
                float(body.get("form_ts", 0)),
            )
            if err:
                result = {"ok": False, "message": err}
            else:
                result = create_account(
                    ACCOUNTS_DIR,
                    PLAYERS_DIR,
                    int(body.get("account", 0)),
                    str(body.get("name", "")),
                    str(body.get("password", "")),
                    int(body.get("sex", -1)),
                    int(body.get("voc", 0)),
                )
                if result.get("ok"):
                    guard.record_attempt(ip)
        except (json.JSONDecodeError, TypeError, ValueError):
            result = {"ok": False, "message": "Datos inválidos"}

        self._json(200, result)

    def _premium_event(self) -> None:
        ip = client_ip(self)
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 4096:
            self._json(400, {"ok": False})
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(400, {"ok": False})
            return
        event = str(body.get("event", "")).strip()
        detail = body.get("detail")
        if not isinstance(detail, dict):
            detail = None
        analytics.record_premium_event(ip, event, detail)
        self._json(200, {"ok": True})

    def _premium_analytics(self) -> None:
        token = os.environ.get("PREMIUM_ANALYTICS_TOKEN", "")
        if not token or self.headers.get("X-Analytics-Token") != token:
            self.send_error(404)
            return
        days = 14
        q = self.path.split("?", 1)
        if len(q) > 1:
            for part in q[1].split("&"):
                if part.startswith("days="):
                    try:
                        days = max(1, min(90, int(part.split("=", 1)[1])))
                    except ValueError:
                        pass
        self._json(200, {"days": analytics.premium_summary(days)})

    def _premium_order(self) -> None:
        ip = client_ip(self)
        analytics.record_premium_event(ip, "submit_received")
        rate_err = guard.check_rate(ip)
        if rate_err:
            analytics.record_premium_event(ip, "submit_fail", {"reason": "rate_limit"})
            self._json(200, {"ok": False, "message": rate_err})
            return
        try:
            fields = parse_multipart_form(self)
        except ValueError as exc:
            analytics.record_premium_event(ip, "submit_fail", {"reason": "invalid_form", "message": str(exc)})
            self._json(200, {"ok": False, "message": str(exc)})
            return
        if fields.get("company"):
            analytics.record_premium_event(ip, "submit_fail", {"reason": "honeypot"})
            self._json(200, {"ok": False, "message": "No se pudo enviar la donación."})
            return
        try:
            form_ts = float(fields.get("form_ts", 0))
        except (TypeError, ValueError):
            form_ts = 0.0
        if time.time() - form_ts < 3:
            analytics.record_premium_event(ip, "submit_fail", {"reason": "too_fast"})
            self._json(200, {"ok": False, "message": "El formulario se envió demasiado rápido."})
            return
        result = create_premium_order(
            orders_file=PREMIUM_ORDERS_FILE,
            uploads_dir=PREMIUM_UPLOADS_DIR,
            players_dir=PLAYERS_DIR,
            character_name=str(fields.get("character_name", "")),
            plan_id=str(fields.get("plan_id", "")),
            golden_amulet=str(fields.get("golden_amulet", "")).lower() in {"1", "true", "on", "yes"},
            receipt_name=str(fields.get("_receipt_name", "")),
            receipt_bytes=fields.get("_receipt_bytes") or b"",
            client_ip=ip,
        )
        if result.get("ok"):
            guard.record_attempt(ip)
            analytics.record_premium_event(
                ip,
                "submit_ok",
                {
                    "order_id": result.get("order_id"),
                    "plan_id": str(fields.get("plan_id", "")),
                    "golden_amulet": str(fields.get("golden_amulet", "")).lower() in {"1", "true", "on", "yes"},
                },
            )
        else:
            analytics.record_premium_event(
                ip,
                "submit_fail",
                {"reason": "validation", "message": result.get("message", "")},
            )
        self._json(200, result)

    def _static(self, url_path: str, *, head_only: bool = False) -> None:
        rel = url_path.lstrip("/")
        path = (WEB_DIR / rel).resolve()
        if not str(path).startswith(str(WEB_DIR.resolve())):
            self.send_error(404)
            return
        if not path.is_file():
            self.send_error(404)
            return
        suffix = path.suffix.lower()
        ctype = ASSET_TYPES.get(suffix, "application/octet-stream")
        cache = "public, max-age=86400" if suffix in {".png", ".jpg", ".jpeg", ".webp", ".svg"} else "no-store"
        self._file(path, ctype, head_only=head_only, cache=cache)

    def _download(self, name: str, *, head_only: bool = False) -> None:
        if not name or ".." in name or "/" in name:
            self.send_error(404)
            return
        path = DOWNLOADS_DIR / name
        if not path.is_file():
            self.send_error(404)
            return
        ctype = "application/octet-stream"
        if name.endswith(".zip"):
            ctype = "application/zip"
        elif name.endswith(".dmg"):
            ctype = "application/x-apple-diskimage"
        self._file(path, ctype, head_only=head_only, download_name=name)

    def _file(self, path: Path, ctype: str, *, head_only: bool = False, cache: str | None = None, download_name: str | None = None) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if cache:
            self.send_header("Cache-Control", cache)
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.end_headers()
        if not head_only:
            if download_name:
                analytics.record_download(download_name)
            self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        return


def start_ot_monitor() -> None:
    t = threading.Thread(target=ot_monitor_loop, name="ot-monitor", daemon=True)
    t.start()
    log.info(
        "web iniciada port=%s status=files+docker ot=%s:%s log=%s",
        PORT,
        OT_HOST,
        OT_PORT,
        os.environ.get("WEB_LOG_FILE", "web/logs/retro76-web.log"),
    )


if __name__ == "__main__":
    start_ot_monitor()
    print(f"Retro76 web: http://localhost:{PORT}/")
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
