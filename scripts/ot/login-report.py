#!/usr/bin/env python3
"""Informe de accesos a partir de data/logs/logins-*.jsonl (servidor) y web-*.jsonl (web).

Uso:
  python3 scripts/ot/login-report.py                       # últimos 14 días
  python3 scripts/ot/login-report.py --days 30
  python3 scripts/ot/login-report.py --logs RUTA/data/logs

Solo lee archivos; no toca el servidor ni los datos de jugadores. Ver docs/systems/LOGIN_EVENTS.md.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOGS = ROOT / "server/YurOTS/ots/data/logs"
DAY = 86400


def load_events(logs_dir: Path) -> list[dict]:
    events = []
    for path in sorted(logs_dir.glob("logins-*.jsonl")) + sorted(logs_dir.glob("web-*.jsonl")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # línea cortada por un apagado brusco
    events.sort(key=lambda e: e.get("t", 0))
    return events


def day_of(t: int) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d")


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.0f}%" if b else "-"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logs", type=Path, default=DEFAULT_LOGS)
    ap.add_argument("--days", type=int, default=14)
    args = ap.parse_args()

    events = load_events(args.logs)
    if not events:
        print(f"No hay eventos en {args.logs}")
        return
    now = int(dt.datetime.now(dt.timezone.utc).timestamp())
    since = now - args.days * DAY
    recent = [e for e in events if e.get("t", 0) >= since]

    # Por día: cuentas creadas, cuentas que llegaron a la lista de personajes, personajes que entraron.
    per_day = collections.defaultdict(lambda: collections.Counter())
    accounts_in = collections.defaultdict(set)
    chars_in = collections.defaultdict(set)
    fails = collections.Counter()
    fail_ips = collections.Counter()
    sessions = []
    for e in recent:
        d, ev = day_of(e["t"]), e.get("event", "")
        per_day[d][ev] += 1
        if ev == "charlist_ok":
            accounts_in[d].add(e.get("acc"))
        elif ev == "game_login":
            chars_in[d].add(e.get("name"))
        elif ev in ("charlist_fail", "game_fail", "account_create_fail"):
            fails[(ev, e.get("reason", ""))] += 1
            if e.get("reason") in ("wrong_password", "no_account", "no_account_or_char"):
                fail_ips[e.get("ip", "")] += 1
        elif ev == "game_logout" and e.get("value", -1) >= 0:
            sessions.append(e["value"])

    print(f"== Últimos {args.days} días (UTC)\n")
    print(f"{'día':10}  {'cuentas':>7}  {'logins lista':>12}  {'cuentas':>7}  {'personajes':>10}  {'fallos':>6}")
    print(f"{'':10}  {'nuevas':>7}  {'de personajes':>12}  {'distintas':>7}  {'en juego':>10}  {'':>6}")
    for d in sorted(per_day):
        c = per_day[d]
        nfail = c["charlist_fail"] + c["game_fail"]
        print(f"{d:10}  {c['account_created']:>7}  {c['charlist_ok']:>12}  {len(accounts_in[d]):>7}  "
              f"{len(chars_in[d]):>10}  {nfail:>6}")

    # Embudo de activación: cuentas creadas en el período que llegaron a entrar al juego.
    created = {e["acc"]: e for e in recent if e.get("event") == "account_created"}
    first_game = {}
    for e in events:
        if e.get("event") == "game_login" and e.get("acc") not in first_game:
            first_game[e.get("acc")] = e["t"]
    logged_acc_days = collections.defaultdict(set)
    for e in events:
        if e.get("event") == "game_login":
            logged_acc_days[e.get("acc")].add(e["t"] // DAY)
    entered = [a for a, e in created.items() if a in first_game and first_game[a] >= e["t"]]
    entered_24h = [a for a in entered if first_game[a] - created[a]["t"] <= DAY]
    print("\n== Embudo de cuentas nuevas")
    print(f"cuentas creadas:            {len(created)}")
    print(f"entraron al juego alguna vez: {len(entered)} ({pct(len(entered), len(created))})")
    print(f"entraron en las primeras 24 h: {len(entered_24h)} ({pct(len(entered_24h), len(created))})")

    # Retención: de las cuentas que entraron por primera vez, cuántas volvieron N días después.
    print("\n== Retención (cuentas con primer login en el período)")
    cohort = [a for a, t in first_game.items() if t >= since]
    for n in (1, 7, 30):
        eligible = [a for a in cohort if first_game[a] + n * DAY <= now]
        back = [a for a in eligible if any(d >= first_game[a] // DAY + n for d in logged_acc_days[a])]
        print(f"volvieron al día {n:>2} o después: {len(back)}/{len(eligible)} ({pct(len(back), len(eligible))})")

    print("\n== Fallos por motivo")
    for (ev, reason), n in fails.most_common():
        print(f"{n:>6}  {ev:20} {reason}")
    suspicious = [(ip, n) for ip, n in fail_ips.most_common(10) if n >= 10]
    if suspicious:
        print("\n== IPs con 10 o más fallos de credenciales (posible fuerza bruta)")
        for ip, n in suspicious:
            print(f"{n:>6}  {ip}")

    if sessions:
        sessions.sort()
        print("\n== Sesiones")
        print(f"sesiones: {len(sessions)}  mediana: {sessions[len(sessions) // 2] // 60} min  "
              f"media: {sum(sessions) // len(sessions) // 60} min")

    # Pico de jugadores por hora (aprox.: logins menos logouts acumulados).
    online, peak = 0, collections.Counter()
    for e in recent:
        if e.get("event") == "game_login":
            online += 1
        elif e.get("event") == "game_logout":
            online = max(0, online - 1)
        else:
            continue
        hour = dt.datetime.fromtimestamp(e["t"], dt.timezone.utc).hour
        peak[hour] = max(peak[hour], online)
    if peak:
        print("\n== Pico de jugadores por hora (UTC)")
        print("  ".join(f"{h:02d}h:{peak[h]}" for h in range(24) if h in peak))


if __name__ == "__main__":
    main()
