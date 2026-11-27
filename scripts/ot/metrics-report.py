#!/usr/bin/env python3
"""Informe de métricas de Retro76: juego, jugadores, accesos y web, día por día.

Junta lo que se registra solo (docs/systems/METRICAS.md):
  - data/logs/metrics-*.jsonl   cron cada 5 min (collect-metrics.py): online, uptime, recursos, foto diaria
  - data/logs/logins-*.jsonl    servidor C++: logins al juego y sesiones (docs/systems/LOGIN_EVENTS.md)
  - data/logs/web-*.jsonl       web: cuentas creadas
  - web/state/analytics.json    web: visitantes, páginas, de dónde llegan, idioma, descargas, updater, embudo premium

Las cuentas con algún GM (access > 0) no cuentan como jugadores.

  ssh vps 'python3 ~/apps/serverrepo/scripts/ot/metrics-report.py'            # últimos 7 días
  ssh vps 'python3 ~/apps/serverrepo/scripts/ot/metrics-report.py --days 30'
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(os.environ.get("RETRO76_ROOT", Path(__file__).resolve().parents[2]))
DATA = ROOT / "server/YurOTS/ots/data"
LOGS = DATA / "logs"
ANALYTICS = ROOT / "web/state/analytics.json"


def jsonl(pattern: str) -> list[dict]:
    rows = []
    for path in sorted(LOGS.glob(pattern)):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def local_day(t: int) -> str:
    return dt.datetime.fromtimestamp(t).strftime("%Y-%m-%d")


def staff_accounts() -> set[str]:
    out = set()
    for path in (DATA / "players").glob("*.xml"):
        try:
            r = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        if int(r.get("access", "0") or 0) > 0:
            out.add(r.get("account", ""))
    return out


def table(title: str, cols: list[str], rows: list[list]) -> None:
    print(f"\n== {title} ==")
    if not rows:
        print("  (sin datos todavía)")
        return
    widths = [max(len(str(c)), *(len(str(r[i])) for r in rows)) for i, c in enumerate(cols)]
    print("  " + "  ".join(str(c).ljust(w) for c, w in zip(cols, widths)))
    for r in rows:
        print("  " + "  ".join(str(v).ljust(w) for v, w in zip(r, widths)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    today = dt.date.today()
    days = [(today - dt.timedelta(days=i)).isoformat() for i in range(a.days - 1, -1, -1)]
    staff = staff_accounts()

    # --- juego y máquina (muestras cada 5 min) ---
    metrics = jsonl("metrics-*.jsonl")
    samples = collections.defaultdict(list)
    snaps: dict[str, dict] = {}
    for r in metrics:
        if r.get("kind") == "sample":
            samples[local_day(r["t"])].append(r)
        elif r.get("kind") == "snapshot":
            snaps[r.get("day") or local_day(r["t"])] = r
    rows = []
    for d in days:
        s = samples.get(d, [])
        if not s:
            continue
        online = [x.get("players_online", 0) for x in s if x.get("ot_up")]
        up = sum(1 for x in s if x.get("ot_up"))
        rx = max(x.get("net_rx_bytes", 0) for x in s) - min(x.get("net_rx_bytes", 0) for x in s)
        tx = max(x.get("net_tx_bytes", 0) for x in s) - min(x.get("net_tx_bytes", 0) for x in s)
        cpu = [x for x in s if "cpu_total_jiffies" in x]
        busy = ""
        if len(cpu) > 1:
            dt_tot = cpu[-1]["cpu_total_jiffies"] - cpu[0]["cpu_total_jiffies"]
            dt_idle = cpu[-1]["cpu_idle_jiffies"] - cpu[0]["cpu_idle_jiffies"]
            busy = f"{100 * (dt_tot - dt_idle) / dt_tot:.0f}%" if dt_tot > 0 else ""
        restarts = max(x.get("yurots_restarts", 0) for x in s) - min(x.get("yurots_restarts", 0) for x in s)
        rows.append([d, len(s), f"{100 * up / len(s):.1f}%", f"{sum(online) / len(online):.1f}" if online else "-",
                     max(online, default=0), busy, min(x.get("mem_avail_mb", 0) for x in s),
                     max(x.get("yurots_mem_mb", 0) for x in s), f"{rx / 1e9:.2f}/{tx / 1e9:.2f}", restarts])
    table("Juego y máquina (cada 5 min)", ["día", "muestras", "uptime", "online prom", "online pico", "CPU",
                                            "RAM libre mín MB", "yurots MB máx", "red GB in/out", "reinicios"], rows)

    # --- jugadores (foto diaria) ---
    rows = []
    for d in days:
        sn = snaps.get(d)
        if sn:
            rows.append([d, sn.get("accounts", 0), sn.get("characters", 0), sn.get("active_1d", 0), sn.get("active_7d", 0),
                         sn.get("active_30d", 0), sn.get("premium_active", 0), sn.get("max_level", 0),
                         sn.get("houses_owned", 0), " ".join(f"{k}:{v}" for k, v in sorted(sn.get("by_level", {}).items()))])
    table("Jugadores (foto del día, sin cuentas de GM)", ["día", "cuentas", "personajes", "activos 1d", "7d", "30d",
                                                         "premium", "nivel máx", "casas", "niveles"], rows)

    # --- accesos (logins del juego y cuentas nuevas de la web) ---
    logins = [r for r in jsonl("logins-*.jsonl") if str(r.get("acc", "")) not in staff]
    web_ev = jsonl("web-*.jsonl")
    first_seen: dict = {}
    for r in sorted(logins, key=lambda r: r.get("t", 0)):
        if r.get("event") == "game_login":
            first_seen.setdefault(r.get("acc"), local_day(r["t"]))
    rows = []
    for d in days:
        dl = [r for r in logins if local_day(r.get("t", 0)) == d]
        game = [r for r in dl if r.get("event") == "game_login"]
        outs = [r.get("value", 0) for r in dl if r.get("event") == "game_logout" and r.get("value")]
        fails = sum(1 for r in dl if str(r.get("event", "")).endswith("_fail"))
        created = sum(1 for r in web_ev if r.get("event") == "account_created" and local_day(r.get("t", 0)) == d)
        new_players = sum(1 for acc, fd in first_seen.items() if fd == d)
        rows.append([d, created, len({r.get("acc") for r in game}), new_players, len(game),
                     f"{sum(outs) / len(outs) / 60:.0f}" if outs else "-", fails, len({r.get("ip") for r in game})])
    table("Accesos (sin cuentas de GM)", ["día", "cuentas nuevas", "jugaron (cuentas)", "primera vez", "logins",
                                          "sesión prom min", "fallos", "IPs"], rows)

    # --- web ---
    try:
        web = json.loads(ANALYTICS.read_text(encoding="utf-8")).get("days", {})
    except (OSError, json.JSONDecodeError):
        web = {}
    rows, refs, locs, pages = [], collections.Counter(), collections.Counter(), collections.Counter()
    funnel = collections.Counter()
    for d in days:
        b = web.get(d)
        if not b:
            continue
        dl = b.get("downloads", {})
        rows.append([d, len(b.get("visitors", [])), sum(b.get("pageviews", {}).values()), dl.get("windows", 0),
                     dl.get("mac", 0), len(b.get("updater_ips", [])), b.get("updater_checks", 0),
                     " ".join(f"{k}:{v}" for k, v in sorted(b.get("langs", {}).items()))])
        refs.update(b.get("referrers", {}))
        locs.update(b.get("locales", {}))
        pages.update(b.get("pageviews", {}))
        funnel.update(b.get("premium", {}).get("counts", {}))
    table("Web", ["día", "visitantes", "páginas vistas", "descargas win", "mac", "clientes updater", "chequeos",
                  "idioma de página"], rows)
    print(f"\n  De dónde llegan: {', '.join(f'{k} {v}' for k, v in refs.most_common(10)) or '(directo)'}")
    print(f"  Navegadores: {', '.join(f'{k} {v}' for k, v in locs.most_common(10)) or '-'}")
    print(f"  Páginas más vistas: {', '.join(f'{k} {v}' for k, v in pages.most_common(10)) or '-'}")
    order = ["tab_view", "checkout_open", "plan_select", "step2", "step3", "submit_click"]
    print("  Embudo premium: " + " → ".join(f"{e} {funnel.get(e, 0)}" for e in order)
          + "  (submit_click = abrió WhatsApp con el pedido)")

    funnel_report(days, staff)
    return 0


FUNNEL_STEPS = [
    ("visit", "visitó la web", "ip"), ("download", "descargó el cliente", "ip"), ("client_open", "abrió el cliente", "ip"),
    ("account_created", "creó cuenta", "acc"), ("first_login", "entró al juego", "acc"),
    ("level20", "llegó a nivel 20", "acc"), ("level50", "llegó a nivel 50", "acc"), ("level100", "llegó a nivel 100", "acc"),
    ("promoted", "promotion", "acc"), ("premium_click", "abrió WhatsApp premium", "ip"),
    ("premium_active", "premium activo", "acc"), ("house", "compró casa", "acc"),
]


def funnel_report(days: list[str], staff: set[str]) -> None:
    """Embudo por hitos (data/logs/funnel-*.jsonl): personas únicas por paso en el período y cuántas de una IP que
    visitó la web siguieron hasta cada paso (sigue a la misma IP/cuenta)."""
    rows = [r for r in jsonl("funnel-*.jsonl") if local_day(r.get("t", 0)) in days and str(r.get("acc", "")) not in staff]
    for r in rows:
        if r.get("step") == "level":
            r["step"] = f"level{r.get('level')}"
    by_step: dict = collections.defaultdict(set)
    ips_of: dict = collections.defaultdict(set)
    acc_ip: dict = {}
    for r in rows:
        step, key = r.get("step"), None
        kind = next((k for s_, _, k in FUNNEL_STEPS if s_ == step), "ip")
        key = r.get("acc") if kind == "acc" else r.get("ip")
        if key:
            by_step[step].add(key)
        if r.get("ip"):
            ips_of[step].add(r["ip"])
        if r.get("acc") and r.get("ip"):
            acc_ip.setdefault(r["acc"], r["ip"])
    visited = ips_of.get("visit", set())
    out = []
    for step, label, kind in FUNNEL_STEPS:
        n = len(by_step.get(step, set()))
        from_web = len(ips_of.get(step, set()) & visited) if step != "visit" else len(visited)
        out.append([label, n, "personas (IP)" if kind == "ip" else "cuentas", from_web])
    table("Embudo de jugadores (hitos, sin cuentas de GM)", ["paso", "en el período", "contado por", "con IP que visitó la web"], out)
    print("  Hitos crudos con IP, cuenta y hora: data/logs/funnel-AAAA-MM.jsonl")


if __name__ == "__main__":
    raise SystemExit(main())
