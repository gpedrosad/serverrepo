#!/usr/bin/env python3
"""Retro76 web — highscores, status, deaths, OTINFO."""
from __future__ import annotations

import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote

from access_log import AccessLog
from analytics import WebAnalytics
from bug_reports import BugReportStore
from data import (
    HIDDEN_RANK_PLAYERS,
    VOC_TEMPLATES,
    build_payload,
    create_account,
    get_character_profile,
    read_server_ip,
    server_status_from_files,
)
from debug_log import get_logger, log_exception, log_http, setup_logging
from premium_orders import create_premium_order, parse_addon_selections, parse_multipart_form, premium_config_payload
from register_guard import RegisterGuard
from client_updater import UPDATER_FILES_DIR, build_updater_response
from zagan_items import image_path, load_catalog

ROOT = Path(__file__).resolve().parents[1]
PLAYERS_DIR = Path(os.environ.get("PLAYERS_DIR", ROOT / "server/YurOTS/ots/data/players"))
ACCOUNTS_DIR = Path(os.environ.get("ACCOUNTS_DIR", ROOT / "server/YurOTS/ots/data/accounts"))
LOGS_DIR = Path(os.environ.get("LOGS_DIR", ROOT / "server/YurOTS/ots/data/logs"))
OTINFO_FILE = Path(os.environ.get("OTINFO_FILE", ROOT / "OTINFO"))
ONLINE_FILE = Path(os.environ.get("ONLINE_FILE", ROOT / "server/YurOTS/ots/data/online.xml"))
STATE_FILE = Path(os.environ.get("STATE_FILE", ROOT / "web/state/daily.json"))
PEAK_STATE = Path(os.environ.get("PEAK_STATE", ROOT / "web/state/peak.json"))
REGISTER_STATE = Path(os.environ.get("REGISTER_STATE", ROOT / "web/state/register.json"))
BUG_REPORTS_FILE = Path(os.environ.get("BUG_REPORTS_FILE", ROOT / "web/state/bug_reports.json"))
PREMIUM_ORDERS_FILE = Path(os.environ.get("PREMIUM_ORDERS_FILE", ROOT / "web/state/premium_orders.json"))
PREMIUM_UPLOADS_DIR = Path(os.environ.get("PREMIUM_UPLOADS_DIR", ROOT / "web/uploads/comprobantes"))
ANALYTICS_STATE = Path(os.environ.get("ANALYTICS_STATE", ROOT / "web/state/analytics.json"))
CONFIG_FILE = Path(os.environ.get("CONFIG_FILE", ROOT / "server/YurOTS/ots/config.lua"))
OT_HOST = os.environ.get("OT_HOST", "127.0.0.1")
OT_PORT = int(os.environ.get("OT_PORT", "7171"))
UPDATER_FILES_URL = os.environ.get("UPDATER_FILES_URL", "https://retro76.cl/updater/files")
SITE_URL = os.environ.get("SITE_URL", "https://retro76.cl").rstrip("/")
SERVER_IP = os.environ.get("SERVER_IP") or read_server_ip(CONFIG_FILE)
PORT = int(os.environ.get("PORT", "8080"))
# Páginas del sitio: web/site (Astro) compilado en web/dist (scripts/web/build-site.sh).
DIST_DIR = Path(__file__).resolve().parent / "dist"
INDEX = DIST_DIR / "index.html"
CHARACTER_PAGE = DIST_DIR / "character.html"
SITE_PAGES = ("top", "power", "pk", "muertes", "gemas", "spells", "reglas", "info", "cuenta", "cliente", "premium", "bugs")
CHARACTER_PAGE_EN = DIST_DIR / "en" / "character.html"
WIKI_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")  # /wiki/<slug> -> dist/wiki/<slug>.html


def site_page_file(path: str) -> Path | None:
    """'/top' -> dist/top.html, '/en' -> dist/en.html, '/en/top' -> dist/en/top.html; None si no es página."""
    name = path.strip("/")
    if name in ("", "index.html"):
        return DIST_DIR / "index.html"
    if name == "en":
        return DIST_DIR / "en.html"
    if name in SITE_PAGES:
        return DIST_DIR / f"{name}.html"
    if name.startswith("en/") and name[3:] in SITE_PAGES:
        return DIST_DIR / "en" / f"{name[3:]}.html"
    if name == "wiki":
        return DIST_DIR / "wiki.html"
    if name.startswith("wiki/") and WIKI_SLUG.fullmatch(name[5:]):
        page = DIST_DIR / "wiki" / f"{name[5:]}.html"
        return page if page.is_file() else None
    return None


def wiki_slugs() -> list[str]:
    """Artículos publicados de la wiki (los que Astro compiló en dist/wiki/)."""
    return sorted(p.stem for p in (DIST_DIR / "wiki").glob("*.html") if WIKI_SLUG.fullmatch(p.stem))
ITEMS_PAGE = Path(__file__).resolve().parent / "items.html"
ITEMS_ALL_PAGE = Path(__file__).resolve().parent / "items-all.html"
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
bug_reports = BugReportStore(BUG_REPORTS_FILE)
analytics = WebAnalytics(ANALYTICS_STATE)
access_log = AccessLog(LOGS_DIR)
setup_logging()
log = get_logger("server")
_ot_monitor_last_online: bool | None = None


# build_payload lee y parsea el XML de todos los jugadores: antes se hacía en cada visita a la
# portada. Se guarda PAYLOAD_TTL segundos y, si llegan varias visitas juntas, una sola lo arma
# (las demás esperan el lock y reciben el mismo resultado).
PAYLOAD_TTL = float(os.environ.get("WEB_PAYLOAD_TTL", "30"))
_payload_lock = threading.Lock()
_payload_cache: tuple[float, dict] | None = None


def get_payload() -> dict:
    global _payload_cache
    with _payload_lock:
        now = time.monotonic()
        if _payload_cache is not None and now - _payload_cache[0] < PAYLOAD_TTL:
            return _payload_cache[1]
        payload = _build_payload_logged()
        _payload_cache = (time.monotonic(), payload)
        return payload


def _build_payload_logged() -> dict:
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
            path = getattr(self, "path", "?").split("?", 1)[0]
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
        if path in ("/favicon.png", "/favicon.ico"):
            self._file(WEB_DIR / "assets/brand/favicon.png", "image/png", head_only=True, cache="public, max-age=86400")
        elif path.startswith("/downloads/"):
            self._download(path[len("/downloads/"):], head_only=True)
        elif path.startswith("/updater/files/"):
            self._updater_file(path[len("/updater/files/"):], head_only=True)
        elif path.startswith("/assets/") or path.startswith("/components/") or path.startswith("/data/"):
            self._static(path, head_only=True)
        elif path.startswith("/_astro/"):
            self._astro_asset(path, head_only=True)
        elif site_page_file(path):
            self._site_page(path, head_only=True)
        else:
            self.send_error(404)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html", "/en"):
            analytics.record_visit(client_ip(self))
            self._site_page(path)
        elif path in ("/favicon.png", "/favicon.ico"):
            self._file(WEB_DIR / "assets/brand/favicon.png", "image/png", cache="public, max-age=86400")
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
        elif path.startswith("/api/character/"):
            self._character_api(path[len("/api/character/"):])
        elif path.startswith("/character/"):
            self._file(CHARACTER_PAGE, "text/html; charset=utf-8", cache="no-cache")
        elif path.startswith("/en/character/"):
            self._file(CHARACTER_PAGE_EN, "text/html; charset=utf-8", cache="no-cache")
        elif site_page_file(path):
            self._site_page(path)
        elif path.startswith("/_astro/"):
            self._astro_asset(path)
        elif path == "/robots.txt":
            self._robots_txt()
        elif path == "/sitemap.xml":
            self._sitemap_xml()
        elif path == "/items":
            self._items_page()
        elif path == "/items-all":
            self._file(ITEMS_ALL_PAGE, "text/html; charset=utf-8", cache="no-store")
        elif path == "/api/zagan-items":
            self._zagan_items_api()
        elif path.startswith("/api/zagan-items/img/"):
            self._zagan_item_image(path[len("/api/zagan-items/img/"):])
        elif path.startswith("/downloads/"):
            self._download(path[len("/downloads/"):])
        elif path.startswith("/updater/files/"):
            self._updater_file(path[len("/updater/files/"):])
        elif path.startswith("/assets/") or path.startswith("/components/") or path.startswith("/data/"):
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
        elif path == "/api/bug-report":
            self._bug_report()
        elif path == "/api/updater.php":
            self._updater_api()
        else:
            self.send_error(404)

    def _create_account(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        ip = client_ip(self)
        acc, name = 0, ""
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            try:
                acc = int(body.get("account", 0))
            except (TypeError, ValueError):
                acc = 0
            name = str(body.get("name", ""))[:40]
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

        if result.get("ok"):
            access_log.record("account_created", acc, name, ip,
                              voc=body.get("voc"), sex=body.get("sex"))
        else:
            access_log.record("account_create_fail", acc, name, ip, reason=str(result.get("message", ""))[:120])
        self._json(200, result)

    def _bug_report(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 8192:
            self._json(400, {"ok": False, "message": "Datos inválidos."})
            return
        ip = client_ip(self)
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            err = guard.verify_captcha(
                str(body.get("challenge_id", "")),
                str(body.get("captcha", "")),
                str(body.get("company", "")),
                float(body.get("form_ts", 0)),
            )
            if err:
                result = {"ok": False, "message": err}
            else:
                result = bug_reports.add_report(
                    character=str(body.get("character", "")),
                    category=str(body.get("category", "")),
                    title=str(body.get("title", "")),
                    description=str(body.get("description", "")),
                    ip=ip,
                )
        except (json.JSONDecodeError, TypeError, ValueError):
            result = {"ok": False, "message": "Datos inválidos."}

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

    def _items_admin_token(self) -> str:
        return "2424"

    def _items_token_ok(self) -> bool:
        token = self._items_admin_token()
        if not token:
            return False
        if self.headers.get("X-Items-Token") == token:
            return True
        query = self.path.split("?", 1)
        if len(query) > 1:
            for part in query[1].split("&"):
                if part.startswith("token="):
                    return unquote(part.split("=", 1)[1]) == token
        return False

    def _character_api(self, raw_name: str) -> None:
        name = unquote(raw_name.split("?", 1)[0]).strip()
        if not name or "/" in name or ".." in name or len(name) > 40:
            self._json(404, {"ok": False, "message": "Personaje no encontrado"})
            return
        try:
            profile = get_character_profile(PLAYERS_DIR, name)
        except Exception as exc:
            log_exception("api", exc, context="/api/character")
            self._json(500, {"ok": False, "message": "Error interno"})
            return
        if not profile:
            self._json(404, {"ok": False, "message": "Personaje no encontrado"})
            return
        self._json(200, {"ok": True, "character": profile})

    def _robots_txt(self) -> None:
        body = (
            "User-agent: *\n"
            "Allow: /\n"
            "Disallow: /api/\n"
            "Disallow: /items\n"
            "Disallow: /updater/\n"
            f"\nSitemap: {SITE_URL}/sitemap.xml\n"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sitemap_xml(self) -> None:
        urls = [f"{SITE_URL}/"] + [f"{SITE_URL}/{page}" for page in SITE_PAGES]
        urls += [f"{SITE_URL}/en"] + [f"{SITE_URL}/en/{page}" for page in SITE_PAGES]
        urls += [f"{SITE_URL}/wiki"] + [f"{SITE_URL}/wiki/{slug}" for slug in wiki_slugs()]
        if PLAYERS_DIR.is_dir():
            names = sorted(
                p.stem
                for p in PLAYERS_DIR.glob("*.xml")
                if p.stem not in VOC_TEMPLATES and p.stem.lower() not in HIDDEN_RANK_PLAYERS
            )
            urls.extend(f"{SITE_URL}/character/{quote(name)}" for name in names)
        entries = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{entries}\n"
            "</urlset>\n"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _items_page(self) -> None:
        if not self._items_admin_token():
            self.send_error(404)
            return
        self._file(ITEMS_PAGE, "text/html; charset=utf-8", cache="no-store")

    def _zagan_items_api(self) -> None:
        if not self._items_token_ok():
            self.send_error(404)
            return
        self._json(200, {"items": load_catalog()})

    def _zagan_item_image(self, name: str) -> None:
        if not self._items_token_ok():
            self.send_error(404)
            return
        safe_name = name.split("?", 1)[0]
        if not safe_name or "/" in safe_name or ".." in safe_name:
            self.send_error(404)
            return
        path = image_path(safe_name)
        if path is None:
            self.send_error(404)
            return
        suffix = path.suffix.lower()
        ctype = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
        self._file(path, ctype, cache="private, max-age=3600")

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
        result = create_premium_order(
            orders_file=PREMIUM_ORDERS_FILE,
            uploads_dir=PREMIUM_UPLOADS_DIR,
            players_dir=PLAYERS_DIR,
            character_name=str(fields.get("character_name", "")),
            plan_id=str(fields.get("plan_id", "")),
            addon_selections=parse_addon_selections(fields),
            receipt_name=str(fields.get("_receipt_name", "")),
            receipt_bytes=fields.get("_receipt_bytes") or b"",
            client_ip=ip,
        )
        if result.get("ok"):
            guard.record_attempt(ip)
            selections = parse_addon_selections(fields)
            analytics.record_premium_event(
                ip,
                "submit_ok",
                {
                    "order_id": result.get("order_id"),
                    "plan_id": str(fields.get("plan_id", "")),
                    "addons": selections,
                    "golden_amulet": selections.get("golden_amulet", False),
                },
            )
        else:
            analytics.record_premium_event(
                ip,
                "submit_fail",
                {"reason": "validation", "message": result.get("message", "")},
            )
        self._json(200, result)

    def _site_page(self, url_path: str, *, head_only: bool = False) -> None:
        self._file(site_page_file(url_path), "text/html; charset=utf-8", head_only=head_only, cache="no-cache")

    def _astro_asset(self, url_path: str, *, head_only: bool = False) -> None:
        """JS/CSS de Astro: el nombre lleva hash, así que se cachea un año."""
        path = (DIST_DIR / url_path.lstrip("/")).resolve()
        if not str(path).startswith(str((DIST_DIR / "_astro").resolve())) or not path.is_file():
            self.send_error(404)
            return
        ctype = ASSET_TYPES.get(path.suffix.lower(), "application/octet-stream")
        self._file(path, ctype, head_only=head_only, cache="public, max-age=31536000, immutable")

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
        if suffix == ".json":
            ctype = "application/json; charset=utf-8"
        cache = "public, max-age=86400" if suffix in {".png", ".jpg", ".jpeg", ".webp", ".svg"} else "no-store"
        self._file(path, ctype, head_only=head_only, cache=cache)

    def _updater_api(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 0:
            try:
                self.rfile.read(length)
            except Exception:
                pass
        payload = build_updater_response(UPDATER_FILES_URL)
        if payload.get("error"):
            log.warning("updater manifest incompleto: %s", payload["error"])
        self._json(200, payload)

    def _updater_file(self, rel: str, *, head_only: bool = False) -> None:
        if not rel or ".." in rel.split("/"):
            self.send_error(404)
            return
        path = (UPDATER_FILES_DIR / rel).resolve()
        root = UPDATER_FILES_DIR.resolve()
        if not str(path).startswith(str(root)) or not path.is_file():
            self.send_error(404)
            return
        suffix = path.suffix.lower()
        ctype = ASSET_TYPES.get(suffix, "application/octet-stream")
        self._file(path, ctype, head_only=head_only, cache="public, max-age=300")

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
