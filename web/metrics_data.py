"""Arma el resumen de métricas de Retro76 en un dict (lo sirve stats/server.py como JSON y HTML).

Lee solo archivos (nada se escribe): data/logs/metrics-*.jsonl, logins-*.jsonl, web-*.jsonl, funnel-*.jsonl y
web/state/analytics.json, más el protocolo de estado del juego para "ahora". Ver docs/systems/METRICAS.md y
docs/systems/STATS_WEB.md.

Las IPs nunca salen tal cual: van como `ip_id`, un hash corto con sal (STATS_IP_SALT) que distingue personas sin
mostrar la dirección.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
import re
import socket
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(os.environ.get("RETRO76_ROOT", Path(__file__).resolve().parents[1]))
DATA = ROOT / "server/YurOTS/ots/data"
LOGS = DATA / "logs"
ANALYTICS = ROOT / "web/state/analytics.json"
SALT = os.environ.get("STATS_IP_SALT", "retro76")
FUNNEL_ORDER = ["visit", "download", "client_open", "account_created", "first_login", "level20", "level50", "level100",
                "promoted", "premium_click", "premium_active", "house"]
FUNNEL_LABELS = {
    "visit": "visitó la web (IP nueva)", "download": "descargó el cliente", "client_open": "abrió el cliente por 1ª vez",
    "account_created": "creó cuenta", "first_login": "entró al juego por 1ª vez", "level20": "nivel 20", "level50": "nivel 50",
    "level100": "nivel 100", "promoted": "promotion", "premium_click": "abrió WhatsApp premium",
    "premium_active": "premium activo", "house": "compró casa",
}


def ip_id(ip: str) -> str:
    return hashlib.sha256((SALT + (ip or "")).encode()).hexdigest()[:10] if ip else ""


def _jsonl(pattern: str) -> list[dict]:
    rows = []
    for path in sorted(LOGS.glob(pattern)):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def _day(t: int) -> str:
    return dt.datetime.fromtimestamp(t).strftime("%Y-%m-%d")


def _staff() -> set[str]:
    out = set()
    for path in (DATA / "players").glob("*.xml"):
        try:
            r = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        if int(r.get("access", "0") or 0) > 0:
            out.add(r.get("account", ""))
    return out


def server_now() -> dict:
    host, port = os.environ.get("OT_HOST", "127.0.0.1"), int(os.environ.get("OT_PORT", "7171"))
    try:
        with socket.create_connection((host, port), timeout=3) as s:
            s.sendall(b"\x06\x00\xff\xffinfo")
            buf = b""
            while chunk := s.recv(4096):
                buf += chunk
    except OSError as exc:
        return {"online": False, "error": str(exc)[:80]}
    text = buf.decode("utf-8", "replace")
    out: dict = {"online": "<tsqp" in text}
    for key, pat in (("players_online", r'online="(\d+)"'), ("players_max", r'max="(\d+)"'),
                     ("players_peak", r'peak="(\d+)"'), ("uptime_s", r'uptime="(\d+)"')):
        if m := re.search(pat, text):
            out[key] = int(m.group(1))
    return out


def build_summary(days: int = 30, events_limit: int = 200) -> dict:
    now = time.time()
    today = dt.date.today()
    day_list = [(today - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    staff = _staff()

    samples: dict = collections.defaultdict(list)
    snaps: dict = {}
    for r in _jsonl("metrics-*.jsonl"):
        if r.get("kind") == "sample":
            samples[_day(r["t"])].append(r)
        elif r.get("kind") == "snapshot":
            snaps[r.get("day") or _day(r["t"])] = {k: v for k, v in r.items() if k not in ("kind", "t", "ts", "day")}

    logins = [r for r in _jsonl("logins-*.jsonl") if str(r.get("acc", "")) not in staff]
    web_ev = _jsonl("web-*.jsonl")
    funnel = [r for r in _jsonl("funnel-*.jsonl") if str(r.get("acc", "")) not in staff]
    for r in funnel:
        if r.get("step") == "level":
            r["step"] = f"level{r.get('level')}"
    first_seen: dict = {}
    for r in sorted(logins, key=lambda r: r.get("t", 0)):
        if r.get("event") == "game_login":
            first_seen.setdefault(r.get("acc"), _day(r["t"]))
    try:
        web = json.loads(ANALYTICS.read_text(encoding="utf-8")).get("days", {})
    except (OSError, json.JSONDecodeError):
        web = {}

    daily = []
    for d in day_list:
        row: dict = {"date": d}
        s = samples.get(d, [])
        if s:
            online = [x.get("players_online", 0) for x in s if x.get("ot_up")]
            cpu = [x for x in s if "cpu_total_jiffies" in x]
            cpu_pct = None
            if len(cpu) > 1:
                tot = cpu[-1]["cpu_total_jiffies"] - cpu[0]["cpu_total_jiffies"]
                idle = cpu[-1]["cpu_idle_jiffies"] - cpu[0]["cpu_idle_jiffies"]
                cpu_pct = round(100 * (tot - idle) / tot, 1) if tot > 0 else None
            row["game"] = {
                "samples": len(s), "uptime_pct": round(100 * sum(1 for x in s if x.get("ot_up")) / len(s), 1),
                "online_avg": round(sum(online) / len(online), 2) if online else 0, "online_peak": max(online, default=0),
                "cpu_pct": cpu_pct, "ram_free_min_mb": min(x.get("mem_avail_mb", 0) for x in s),
                "yurots_mem_max_mb": max(x.get("yurots_mem_mb", 0) for x in s),
                "net_in_gb": round((max(x.get("net_rx_bytes", 0) for x in s) - min(x.get("net_rx_bytes", 0) for x in s)) / 1e9, 3),
                "net_out_gb": round((max(x.get("net_tx_bytes", 0) for x in s) - min(x.get("net_tx_bytes", 0) for x in s)) / 1e9, 3),
                "restarts": max(x.get("yurots_restarts", 0) for x in s) - min(x.get("yurots_restarts", 0) for x in s),
                "disk_used_pct": s[-1].get("disk_used_pct"),
            }
        if d in snaps:
            row["players"] = snaps[d]
        dl = [r for r in logins if _day(r.get("t", 0)) == d]
        game = [r for r in dl if r.get("event") == "game_login"]
        outs = [r.get("value", 0) for r in dl if r.get("event") == "game_logout" and r.get("value")]
        row["access"] = {
            "accounts_created": sum(1 for r in web_ev if r.get("event") == "account_created" and _day(r.get("t", 0)) == d),
            "accounts_played": len({r.get("acc") for r in game}),
            "first_time_players": sum(1 for fd in first_seen.values() if fd == d),
            "game_logins": len(game), "avg_session_min": round(sum(outs) / len(outs) / 60, 1) if outs else None,
            "login_fails": sum(1 for r in dl if str(r.get("event", "")).endswith("_fail")),
            "unique_ips": len({r.get("ip") for r in game}),
        }
        b = web.get(d)
        if b:
            dls = b.get("downloads", {})
            row["web"] = {
                "visitors": len(b.get("visitors", [])), "pageviews": sum(b.get("pageviews", {}).values()),
                "downloads_windows": dls.get("windows", 0), "downloads_mac": dls.get("mac", 0),
                "client_opens_unique": len(b.get("updater_ips", [])), "updater_checks": b.get("updater_checks", 0),
                "page_langs": b.get("langs", {}), "referrers": b.get("referrers", {}), "browser_locales": b.get("locales", {}),
                "top_pages": dict(sorted(b.get("pageviews", {}).items(), key=lambda kv: -kv[1])[:10]),
                "premium_funnel": b.get("premium", {}).get("counts", {}),
            }
        steps = collections.Counter(r.get("step") for r in funnel if _day(r.get("t", 0)) == d)
        if steps:
            row["funnel"] = dict(steps)
        daily.append(row)

    # embudo del período: personas únicas por paso (IP para pasos web, cuenta para pasos de juego)
    in_period = [r for r in funnel if _day(r.get("t", 0)) in set(day_list)]
    uniq: dict = collections.defaultdict(set)
    for r in in_period:
        uniq[r.get("step")].add(r.get("acc") or r.get("ip"))
    visit_ips = {r.get("ip") for r in in_period if r.get("step") == "visit"}
    funnel_steps = []
    for st in FUNNEL_ORDER:
        ips = {r.get("ip") for r in in_period if r.get("step") == st and r.get("ip")}
        funnel_steps.append({"step": st, "label": FUNNEL_LABELS[st], "people": len(uniq.get(st, set())),
                             "from_web_visitors": len(ips & visit_ips) if st != "visit" else len(visit_ips)})

    def tot(section: str, key: str) -> float:
        return sum((r.get(section) or {}).get(key, 0) or 0 for r in daily)

    totals = {
        "web_visitors": tot("web", "visitors"), "web_pageviews": tot("web", "pageviews"),
        "downloads": tot("web", "downloads_windows") + tot("web", "downloads_mac"),
        "client_opens_unique_daily_sum": tot("web", "client_opens_unique"),
        "accounts_created": tot("access", "accounts_created"), "first_time_players": tot("access", "first_time_players"),
        "game_logins": tot("access", "game_logins"),
        "online_peak": max(((r.get("game") or {}).get("online_peak", 0) for r in daily), default=0),
    }
    refs: collections.Counter = collections.Counter()
    locs: collections.Counter = collections.Counter()
    for r in daily:
        refs.update((r.get("web") or {}).get("referrers", {}))
        locs.update((r.get("web") or {}).get("browser_locales", {}))
    totals["referrers"] = dict(refs.most_common(15))
    totals["browser_locales"] = dict(locs.most_common(15))

    recent_events = []
    for r in sorted(funnel, key=lambda r: -r.get("t", 0))[:events_limit]:
        e = {k: v for k, v in r.items() if k not in ("ip",)}
        e["ip_id"] = ip_id(r.get("ip", ""))
        recent_events.append(e)
    recent_logins = []
    for r in sorted(logins, key=lambda r: -r.get("t", 0))[:100]:
        recent_logins.append({"ts": r.get("ts"), "event": r.get("event"), "name": r.get("name", ""),
                              "acc": r.get("acc"), "reason": r.get("reason", ""), "ip_id": ip_id(r.get("ip", ""))})

    now_status = server_now()
    alerts = []
    if not now_status.get("online"):
        alerts.append("El servidor del juego NO responde ahora.")
    for r in daily[-2:]:
        g = r.get("game") or {}
        if g and g.get("uptime_pct", 100) < 100:
            alerts.append(f"{r['date']}: uptime {g['uptime_pct']}%")
        if g.get("restarts"):
            alerts.append(f"{r['date']}: {g['restarts']} reinicio(s) del contenedor")
        if g and g.get("ram_free_min_mb", 999) < 150:
            alerts.append(f"{r['date']}: RAM libre mínima {g['ram_free_min_mb']} MB (considerar plan de 2 GB)")
        if g and (g.get("disk_used_pct") or 0) > 85:
            alerts.append(f"{r['date']}: disco al {g['disk_used_pct']}%")
        if (r.get("access") or {}).get("login_fails", 0) > 50:
            alerts.append(f"{r['date']}: {r['access']['login_fails']} logins fallidos (¿fuerza bruta?)")

    return {
        "generated_at": dt.datetime.fromtimestamp(now).isoformat(timespec="seconds"),
        "timezone": time.strftime("%Z"), "period_days": days, "server_now": now_status,
        "alerts": alerts, "totals": totals, "funnel": funnel_steps, "daily": daily,
        "recent_funnel_events": recent_events, "recent_logins": recent_logins,
        "notes": "Las cuentas con GM no cuentan. ip_id = hash corto de la IP (misma persona = mismo ip_id). "
                 "Ver /<token>/llms.txt para el significado de cada campo.",
    }
