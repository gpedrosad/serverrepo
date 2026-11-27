#!/usr/bin/env python3
"""Registra las métricas del servidor cada 5 minutos (cron del VPS) para poder medir después.

Escribe una línea JSON por muestra en server/YurOTS/ots/data/logs/metrics-AAAA-MM.jsonl:

  kind "sample" (cada corrida): jugadores online, máximo y récord del protocolo de estado, uptime del juego,
      reinicios del contenedor, carga, RAM, swap, disco, bytes de red y CPU acumulada de la máquina, y CPU/RAM de
      los contenedores yurots y retro76-web.
  kind "snapshot" (una vez por día, la primera corrida del día): cuentas, personajes (sin plantillas ni cuentas
      de GM), por vocación y por rango de nivel, nivel máximo, premium activos, activos en 1/7/30 días y casas con
      dueño.

Solo lee: no toca el juego ni los datos de jugadores. Sin dependencias (stdlib).

  python3 scripts/ot/collect-metrics.py            # una muestra (lo que corre el cron)
  python3 scripts/ot/collect-metrics.py --print    # muestra en pantalla, sin escribir

Informe: scripts/ot/metrics-report.py. Doc: docs/systems/METRICAS.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(os.environ.get("RETRO76_ROOT", Path(__file__).resolve().parents[2]))
DATA = ROOT / "server/YurOTS/ots/data"
LOGS = DATA / "logs"
OT_HOST, OT_PORT = os.environ.get("OT_HOST", "127.0.0.1"), int(os.environ.get("OT_PORT", "7171"))
CONTAINERS = ("yurots", "retro76-web")
VOC_TEMPLATES = {"0", "1", "2", "3", "4"}
VOCATIONS = {0: "none", 1: "sorcerer", 2: "druid", 3: "paladin", 4: "knight"}
LEVEL_BANDS = ((1, 19, "1-19"), (20, 49, "20-49"), (50, 99, "50-99"), (100, 10**9, "100+"))


def ot_status() -> dict:
    """Protocolo de estado (tsqp) del juego: lo mismo que lee otservlist."""
    try:
        with socket.create_connection((OT_HOST, OT_PORT), timeout=5) as s:
            s.sendall(b"\x06\x00\xff\xffinfo")
            buf = b""
            while len(buf) < 8192:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
    except OSError as exc:
        return {"ot_up": False, "ot_error": str(exc)[:80]}
    text = buf.decode("utf-8", "replace")
    out = {"ot_up": "<tsqp" in text}
    if m := re.search(r"<players ([^/]*)/>", text):
        for k in ("online", "max", "peak"):
            if v := re.search(rf'{k}="(\d+)"', m.group(1)):
                out[f"players_{k}"] = int(v.group(1))
    if v := re.search(r'uptime="(\d+)"', text):
        out["ot_uptime_s"] = int(v.group(1))
    if v := re.search(r'<monsters total="(\d+)"', text):
        out["monsters"] = int(v.group(1))
    return out


def system() -> dict:
    out: dict = {}
    try:
        out["load1"], out["load5"], out["load15"] = (float(x) for x in Path("/proc/loadavg").read_text().split()[:3])
        mem = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":", 1)
            mem[k] = int(v.split()[0]) // 1024
        out["mem_total_mb"] = mem.get("MemTotal", 0)
        out["mem_avail_mb"] = mem.get("MemAvailable", 0)
        out["swap_used_mb"] = mem.get("SwapTotal", 0) - mem.get("SwapFree", 0)
        cpu = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
        vals = [int(x) for x in cpu]
        out["cpu_total_jiffies"] = sum(vals)
        out["cpu_idle_jiffies"] = vals[3] + (vals[4] if len(vals) > 4 else 0)
        rx = tx = 0
        for line in Path("/proc/net/dev").read_text().splitlines()[2:]:
            name, rest = line.split(":", 1)
            if name.strip() in ("lo",) or name.strip().startswith(("docker", "veth", "br-")):
                continue
            f = rest.split()
            rx += int(f[0])
            tx += int(f[8])
        out["net_rx_bytes"], out["net_tx_bytes"] = rx, tx
    except (OSError, ValueError, IndexError):
        pass
    du = shutil.disk_usage("/")
    out["disk_used_pct"] = round(du.used * 100 / du.total, 1)
    out["disk_free_gb"] = round(du.free / 1e9, 1)
    return out


def _mib(text: str) -> float:
    m = re.match(r"([\d.]+)\s*([KMG]i?B)", text.strip())
    if not m:
        return 0.0
    n, unit = float(m.group(1)), m.group(2)[0]
    return round(n / 1024 if unit == "K" else n * 1024 if unit == "G" else n, 1)


def containers() -> dict:
    out: dict = {}
    try:
        res = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}", *CONTAINERS],
                             capture_output=True, text=True, timeout=30)
        for line in res.stdout.splitlines():
            name, cpu, mem = line.split("|")
            key = name.replace("-", "_")
            out[f"{key}_cpu_pct"] = float(cpu.rstrip("%") or 0)
            out[f"{key}_mem_mb"] = _mib(mem.split("/")[0])
        res = subprocess.run(["docker", "inspect", "-f", "{{.RestartCount}}", "yurots"], capture_output=True, text=True, timeout=15)
        if res.stdout.strip().isdigit():
            out["yurots_restarts"] = int(res.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return out


def snapshot(now: float) -> dict:
    """Foto del día de cuentas y personajes. Las cuentas con algún GM (access > 0) no cuentan: son del staff."""
    chars = []
    for path in (DATA / "players").glob("*.xml"):
        if path.stem in VOC_TEMPLATES:
            continue
        try:
            r = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        chars.append({
            "acc": r.get("account", ""), "access": int(r.get("access", "0") or 0), "level": int(r.get("level", "1") or 1),
            "voc": int(r.get("voc", "0") or 0), "promoted": r.get("promoted", "0") == "1",
            "last": int(r.get("lastlogin", "0") or 0), "prem": int(r.get("premticks", "0") or 0) > 0,
        })
    staff = {c["acc"] for c in chars if c["access"] > 0}
    players = [c for c in chars if c["acc"] not in staff]
    accounts = [p for p in (DATA / "accounts").glob("*.xml") if p.stem not in staff]
    by_voc: dict = {}
    by_band: dict = {}
    for c in players:
        by_voc[VOCATIONS.get(c["voc"], str(c["voc"]))] = by_voc.get(VOCATIONS.get(c["voc"], str(c["voc"])), 0) + 1
        band = next(b for lo, hi, b in LEVEL_BANDS if lo <= c["level"] <= hi)
        by_band[band] = by_band.get(band, 0) + 1
    houses_owned = 0
    for path in (DATA / "houses").glob("*.xml"):
        try:
            owner = ET.parse(path).getroot().find("owner")
        except ET.ParseError:
            continue
        if owner is not None and (owner.get("name") or "").strip():
            houses_owned += 1
    active = lambda days: sum(1 for c in players if c["last"] >= now - days * 86400)  # noqa: E731
    return {
        "accounts": len(accounts), "characters": len(players), "staff_accounts": len(staff),
        "by_vocation": by_voc, "by_level": by_band, "max_level": max((c["level"] for c in players), default=0),
        "promoted": sum(c["promoted"] for c in players), "premium_active": sum(c["prem"] for c in players),
        "active_1d": active(1), "active_7d": active(7), "active_30d": active(30), "houses_owned": houses_owned,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print", action="store_true", help="mostrar sin escribir")
    a = ap.parse_args()
    now = time.time()
    rows = [{"kind": "sample", **ot_status(), **system(), **containers()}]
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    marker = LOGS / ".metrics-snapshot-day"
    if a.print or not marker.exists() or marker.read_text().strip() != day:
        rows.append({"kind": "snapshot", "day": day, **snapshot(now)})
    for row in rows:
        row.update(t=int(now), ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)))
    if a.print:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
        return 0
    LOGS.mkdir(parents=True, exist_ok=True)
    with (LOGS / time.strftime("metrics-%Y-%m.jsonl", time.gmtime(now))).open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if any(r["kind"] == "snapshot" for r in rows):
        marker.write_text(day)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
