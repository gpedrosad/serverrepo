#!/usr/bin/env python3
"""YurOTS web — highscores, status, deaths, guilds, OTINFO."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from data import build_payload, create_account

ROOT = Path(__file__).resolve().parents[1]
PLAYERS_DIR = Path(os.environ.get("PLAYERS_DIR", ROOT / "server/YurOTS/ots/data/players"))
GUILDS_FILE = Path(os.environ.get("GUILDS_FILE", ROOT / "server/YurOTS/ots/data/guilds.xml"))
OTINFO_FILE = Path(os.environ.get("OTINFO_FILE", ROOT / "OTINFO"))
ONLINE_FILE = Path(os.environ.get("ONLINE_FILE", ROOT / "server/YurOTS/ots/data/online.xml"))
STATE_FILE = Path(os.environ.get("STATE_FILE", ROOT / "web/state/daily.json"))
OT_HOST = os.environ.get("OT_HOST", "127.0.0.1")
OT_PORT = int(os.environ.get("OT_PORT", "7171"))
PORT = int(os.environ.get("PORT", "8080"))
INDEX = Path(__file__).resolve().parent / "index.html"


def get_payload() -> dict:
    return build_payload(
        PLAYERS_DIR, GUILDS_FILE, OTINFO_FILE, ONLINE_FILE, STATE_FILE, OT_HOST, OT_PORT
    )


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/api/create-account":
            length = int(self.headers.get("Content-Length", "0"))
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                result = create_account(
                    OT_HOST,
                    OT_PORT,
                    str(body.get("name", "")),
                    str(body.get("password", "")),
                    int(body.get("sex", -1)),
                    int(body.get("voc", 0)),
                )
            except (json.JSONDecodeError, TypeError, ValueError):
                result = {"ok": False, "message": "Petición inválida"}
            data = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._file(INDEX, "text/html; charset=utf-8")
        elif path == "/api/data":
            data = json.dumps(get_payload(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)

    def _file(self, path: Path, ctype: str) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        return


if __name__ == "__main__":
    print(f"YurOTS web: http://localhost:{PORT}/")
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
