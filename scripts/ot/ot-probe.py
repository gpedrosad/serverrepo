#!/usr/bin/env python3
"""Sonda el protocolo info del OT con salida detallada para logs/diagnóstico."""
from __future__ import annotations

import argparse
import json
import socket
import struct
import sys
import time
import xml.etree.ElementTree as ET


def probe(host: str, port: int, timeout: float = 8.0) -> dict:
    t0 = time.monotonic()
    out: dict = {
        "ok": False,
        "host": host,
        "port": port,
        "elapsed_ms": 0.0,
        "bytes": 0,
        "error": "",
        "players_online": 0,
        "uptime_seconds": 0,
        "servername": "",
    }
    try:
        payload = struct.pack("<H", 0xFFFF) + b"info"
        packet = struct.pack("<H", len(payload)) + payload
        with socket.create_connection((host, port), timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(packet)
            data = b""
            while True:
                chunk = sock.recv(8192)
                if not chunk:
                    break
                data += chunk
        out["bytes"] = len(data)
        if not data or b"serverinfo" not in data:
            out["error"] = f"invalid_response ({len(data)} bytes)"
            return out
        root = ET.fromstring(data.decode("utf-8", errors="replace"))
        si = root.find("serverinfo")
        pl = root.find("players")
        if si is not None:
            out["uptime_seconds"] = int(si.get("uptime", "0"))
            out["servername"] = si.get("servername", "")
        if pl is not None:
            out["players_online"] = int(pl.get("online", "0"))
        out["ok"] = True
    except OSError as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    except ET.ParseError as exc:
        out["error"] = f"ParseError: {exc}"
    finally:
        out["elapsed_ms"] = round((time.monotonic() - t0) * 1000, 1)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Sonda protocolo info del OT")
    p.add_argument("host", nargs="?", default="127.0.0.1")
    p.add_argument("port", nargs="?", type=int, default=7171)
    p.add_argument("--timeout", type=float, default=8.0)
    p.add_argument("--json", action="store_true", help="Salida JSON")
    p.add_argument("--quiet", action="store_true", help="Sin salida si OK")
    args = p.parse_args()

    result = probe(args.host, args.port, args.timeout)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif not args.quiet or not result["ok"]:
        status = "OK" if result["ok"] else "FAIL"
        print(
            f"{status} {result['host']}:{result['port']} "
            f"{result['elapsed_ms']}ms "
            f"bytes={result['bytes']} "
            f"players={result['players_online']} "
            f"uptime={result['uptime_seconds']}s "
            f"error={result['error']}"
        )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
