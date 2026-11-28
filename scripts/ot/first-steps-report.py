#!/usr/bin/env python3
"""Primeros pasos y retención de Retro76 (docs/systems/PRIMEROS_PASOS.md). Solo lectura.

Junta el embudo de la web (funnel-*.jsonl), los logins (logins-*.jsonl) y el registro de juego del servidor
(play-*.jsonl: sesiones, posiciones, niveles y muertes) para responder:

  1. ¿En qué paso se va la gente? (embudo completo, de la visita a volver otro día)
  2. ¿Qué hace cada personaje nuevo en sus primeras horas?
  3. ¿Dónde y cómo estaban los que se fueron? (último nivel, si murió antes de irse, zona)
  4. ¿Qué tan probable es que alguien se quede? (relación de cada dato con quedarse y una regresión
     logística: P(quedarse) = 1 / (1 + e^-(b0 + b1·x1 + ...)), con datos estandarizados)

  python3 scripts/ot/first-steps-report.py              # personajes que entraron por primera vez en 30 días
  python3 scripts/ot/first-steps-report.py --days 90
  python3 scripts/ot/first-steps-report.py --json       # todo en JSON (para bots u otros informes)

Las cuentas con algún GM no cuentan. "Se quedó" = volvió a jugar otro día dentro de los 7 días de su primer
ingreso; recién se sabe a los 7 días (antes queda "pendiente").
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(os.environ["RETRO76_ROOT"]) if os.environ.get("RETRO76_ROOT") else Path(__file__).resolve().parents[2]
DATA = ROOT / "server/YurOTS/ots/data"
LOGS = DATA / "logs"
SPAWNS = DATA / "world/test-spawn.xml"
MODEL_FILE = LOGS / ".retention-model.json"
VOC_TEMPLATES = {"0", "1", "2", "3", "4"}
VOCATIONS = {0: "sin voc", 1: "sorcerer", 2: "druid", 3: "paladin", 4: "knight"}
DEPOT = (127, 57)          # punto de partida (MAPA_DE_MONSTRUOS.md)
DAY = 86400
RETURN_WINDOW = 7 * DAY
MIN_TRAIN = 12             # personajes con resultado conocido para entrenar el modelo
MIN_CLASS = 4              # y al menos estos en cada grupo (se quedó / se fue)


# ---------------------------------------------------------------- datos

def jsonl(pattern: str) -> list[dict]:
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


def load_players() -> tuple[dict, set]:
    chars, staff = {}, set()
    for path in (DATA / "players").glob("*.xml"):
        if path.stem in VOC_TEMPLATES:
            continue
        try:
            r = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        name = r.get("name") or path.stem
        acc = r.get("account", "")
        if int(r.get("access", "0") or 0) > 0:
            staff.add(acc)
        chars[name.lower()] = {"name": name, "acc": acc, "level": int(r.get("level", "1") or 1),
                               "voc": int(r.get("voc", "0") or 0), "last": int(r.get("lastlogin", "0") or 0)}
    return chars, staff


def local_day(t: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(t))


# ---------------------------------------------------------------- zonas

class Zones:
    """Nombra una posición por los monstruos que aparecen cerca (spawns del mapa) o por la ciudad."""

    def __init__(self):
        self.spawns: list[tuple[int, int, int, str]] = []
        try:
            root = ET.parse(SPAWNS).getroot()
        except (OSError, ET.ParseError):
            return
        for sp in root.iter("spawn"):
            cx, cy, cz = int(sp.get("centerx", 0)), int(sp.get("centery", 0)), int(sp.get("centerz", 7))
            for m in sp:
                self.spawns.append((cx + int(m.get("x", 0)), cy + int(m.get("y", 0)), int(m.get("z", cz)),
                                    (m.get("name") or "?").strip().title()))

    def name(self, x: int, y: int, z: int, train: bool = False) -> str:
        if train:
            return "sala de training"
        if z in (6, 7) and max(abs(x - DEPOT[0]), abs(y - DEPOT[1])) <= 12:
            return "depot / templo"
        near: dict[str, int] = {}
        for sx, sy, sz, n in self.spawns:
            if sz == z and abs(sx - x) <= 10 and abs(sy - y) <= 10:
                near[n] = near.get(n, 0) + 1
        dx, dy = x - DEPOT[0], y - DEPOT[1]
        where = f"{abs(dy)} {'S' if dy > 0 else 'N'} {abs(dx)} {'E' if dx > 0 else 'O'} del depot, piso {z}"
        if not near:
            if max(abs(dx), abs(dy)) <= 30 and z in (5, 6, 7):
                return f"ciudad ({where})"
            return f"sin monstruos ({where})"
        top = sorted(near.items(), key=lambda kv: -kv[1])[:2]
        return " + ".join(n for n, _ in top) + f" ({where})"


# ---------------------------------------------------------------- personajes

def build(days: int, now: float) -> dict:
    chars, staff = load_players()
    logins = [r for r in jsonl("logins-*.jsonl") if str(r.get("acc", "")) not in staff]
    play = [r for r in jsonl("play-*.jsonl") if str(r.get("acc", "")) not in staff]
    funnel = jsonl("funnel-*.jsonl")
    zones = Zones()

    first_login: dict[str, float] = {}
    display: dict[str, str] = {}
    sessions: dict[str, list[tuple[float, float]]] = {}   # (inicio, duración s) desde logins
    login_ip: dict[str, str] = {}
    for r in sorted(logins, key=lambda r: r.get("t", 0)):
        name = (r.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if r.get("event") == "game_login":
            first_login.setdefault(key, r.get("t", 0))
            display.setdefault(key, name)
            login_ip.setdefault(key, r.get("ip", ""))
        elif r.get("event") == "game_logout" and isinstance(r.get("value"), (int, float)):
            dur = float(r["value"])
            sessions.setdefault(key, []).append((r.get("t", 0) - dur, dur))

    psess: dict[str, list[dict]] = {}
    levels: dict[str, list[dict]] = {}
    deaths: dict[str, list[dict]] = {}
    positions: list[dict] = []
    for r in play:
        key = (r.get("name") or "").lower()
        ev = r.get("event")
        if ev == "session":
            psess.setdefault(key, []).append(r)
        elif ev == "level":
            levels.setdefault(key, []).append(r)
        elif ev == "death":
            deaths.setdefault(key, []).append(r)
        elif ev == "pos":
            positions.append(r)

    since = now - days * DAY
    out = []
    for key, t0 in first_login.items():
        if t0 < since:
            continue
        info = chars.get(key, {})
        if info.get("acc") in staff:
            continue
        ss = sorted(sessions.get(key, []))
        ps = sorted(psess.get(key, []), key=lambda r: r.get("start", r.get("t", 0)))
        d1 = t0 + DAY
        first_day = local_day(t0)
        first_sess = next((d for s, d in ss if s >= t0 - 5), None)
        returned_at = next((s for s, _ in ss if local_day(s) != first_day and s <= t0 + RETURN_WINDOW), None)
        if returned_at is not None:
            label = 1
        elif now - t0 >= RETURN_WINDOW:
            label = 0
        else:
            label = None
        last_seen = max([s + d for s, d in ss] + [info.get("last", 0), t0])
        d1_ps = [p for p in ps if p.get("start", p.get("t", 0)) < d1]
        first_ps = ps[0] if ps else None
        lv_events = sorted(levels.get(key, []), key=lambda r: r.get("t", 0))
        max_level = max([info.get("level", 0)] + [r.get("to", 0) for r in lv_events])

        def online_before(t: float) -> float:
            total = 0.0
            for s, d in ss:
                if s + d <= t:
                    total += d
                elif s <= t:
                    total += t - s
            return total / 60.0

        reach = {}
        for target in (10, 15, 20, 30):
            ev = next((r for r in lv_events if r.get("to", 0) >= target), None)
            if ev:
                reach[target] = round(online_before(ev.get("t", 0)), 1)

        mons: dict[str, int] = {}
        for p in d1_ps:
            for m, c in (p.get("mons") or {}).items():
                mons[m] = mons.get(m, 0) + int(c)
        last_ps = ps[-1] if ps else None
        row = {
            "name": display.get(key, info.get("name", key)), "acc": info.get("acc", ""),
            "voc": VOCATIONS.get(info.get("voc", 0), "?"), "first_login": int(t0), "ip": login_ip.get(key, ""),
            "level_now": info.get("level", 0), "max_level": max_level, "label": label,
            "returned_after_h": round((returned_at - t0) / 3600, 1) if returned_at else None,
            "last_seen": int(last_seen), "days_since_seen": round((now - last_seen) / DAY, 1),
            "sessions": len(ss), "days_played": len({local_day(s) for s, _ in ss}),
            "online_min": round(sum(d for _, d in ss) / 60, 1),
            "reach_min": reach,
            # primeras 24 h (rasgos para el modelo)
            "first_session_min": round(first_sess / 60, 1) if first_sess is not None else None,
            "d1_sessions": sum(1 for s, _ in ss if s < d1),
            "d1_online_min": round(sum(min(d, max(0.0, d1 - s)) for s, d in ss if s < d1) / 60, 1),
            "has_play": bool(ps),
            "d1_levels": sum(max(0, p.get("lvl1", 0) - p.get("lvl0", 0)) for p in d1_ps) if ps else None,
            "d1_deaths": sum(p.get("deaths", 0) for p in d1_ps) if ps else None,
            "died_first_session": (1 if (first_ps or {}).get("deaths", 0) > 0 else 0) if ps else None,
            "d1_kills": sum(p.get("kills", 0) for p in d1_ps) if ps else None,
            "d1_zones": sum(p.get("zones", 0) for p in d1_ps) if ps else None,
            "d1_train_min": round(sum(p.get("train_s", 0) for p in d1_ps) / 60, 1) if ps else None,
            "d1_chat": sum(p.get("says", 0) + p.get("pms", 0) + p.get("chan", 0) for p in d1_ps) if ps else None,
            "d1_party": (1 if any(p.get("party_s", 0) > 0 for p in d1_ps) else 0) if ps else None,
            "top_monsters": sorted(mons.items(), key=lambda kv: -kv[1])[:5],
            "deaths": [{"t": d.get("t"), "lvl": d.get("lvl"), "killer": d.get("killer"), "pvp": d.get("pvp", 0),
                        "zone": zones.name(d.get("x", 0), d.get("y", 0), d.get("z", 7))} for d in deaths.get(key, [])],
            "last_session": None if not last_ps else {
                "min": round(last_ps.get("online_s", last_ps.get("dur", 0)) / 60, 1), "lvl": last_ps.get("lvl1"),
                "died_last": last_ps.get("died_last", 0), "killer": last_ps.get("last_killer", ""),
                "hp": last_ps.get("hp"), "zone": zones.name(last_ps.get("x", 0), last_ps.get("y", 0), last_ps.get("z", 7))},
        }
        out.append(row)
    out.sort(key=lambda r: r["first_login"])
    return {"chars": out, "funnel": funnel, "positions": positions, "zones": zones, "deaths": deaths,
            "chars_xml": chars, "staff": staff}


# ---------------------------------------------------------------- embudo

def funnel_table(data: dict, days: int, now: float) -> list[tuple[str, int]]:
    since = now - days * DAY
    web = [r for r in data["funnel"] if r.get("t", 0) >= since]
    ips = lambda step: {r.get("ip") for r in web if r.get("step") == step and r.get("ip")}  # noqa: E731
    accs = {str(r.get("acc")) for r in web if r.get("step") == "account_created" and r.get("acc") is not None}
    chars = data["chars"]
    rows = [
        ("visitó la web (IP)", len(ips("visit"))),
        ("descargó el cliente (IP)", len(ips("download"))),
        ("abrió el cliente (IP)", len(ips("client_open"))),
        ("creó cuenta", len(accs)),
        ("entró al juego (personajes)", len(chars)),
    ]
    # Pasos del juego anidados: cada uno cuenta a los que además pasaron todos los anteriores.
    steps = [("jugó 10 min o más el 1er día", lambda c: c["d1_online_min"] >= 10),
             ("llegó a nivel 10", lambda c: c["max_level"] >= 10),
             ("llegó a nivel 15", lambda c: c["max_level"] >= 15),
             ("llegó a nivel 20", lambda c: c["max_level"] >= 20)]
    alive = list(chars)
    for label, ok in steps:
        alive = [c for c in alive if ok(c)]
        rows.append((label, len(alive)))
    return rows


def retention_line(chars: list[dict]) -> tuple[int, int]:
    known = [c for c in chars if c["label"] is not None]
    return sum(1 for c in known if c["label"] == 1), len(known)


# ---------------------------------------------------------------- modelo

FEATURES = [
    ("first_session_min", "minutos de la 1ª sesión", math.log1p),
    ("d1_online_min", "minutos jugados el 1er día", math.log1p),
    ("d1_sessions", "sesiones el 1er día", None),
    ("d1_levels", "niveles subidos el 1er día", None),
    ("d1_deaths", "muertes el 1er día", None),
    ("died_first_session", "murió en la 1ª sesión (0/1)", None),
    ("d1_kills", "monstruos matados el 1er día", math.log1p),
    ("d1_zones", "zonas recorridas el 1er día", math.log1p),
    ("d1_train_min", "minutos de training el 1er día", math.log1p),
    ("d1_chat", "mensajes de chat el 1er día", math.log1p),
    ("d1_party", "jugó en party el 1er día (0/1)", None),
]


def _value(row: dict, key: str, fn):
    v = row.get(key)
    if v is None:
        return None
    return fn(v) if fn else float(v)


def univariate(rows: list[dict]) -> list[dict]:
    """Relación de cada dato con quedarse: correlación punto-biserial y % que se quedó arriba/abajo de la mediana."""
    out = []
    for key, label, fn in FEATURES:
        pairs = [(_value(r, key, fn), r["label"]) for r in rows if r["label"] is not None and r.get(key) is not None]
        if len(pairs) < 4:
            continue
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        if len(set(xs)) < 2:
            continue          # todos iguales (p. ej. nadie usó party): no dice nada
        med = statistics.median(xs)
        hi = [y for x, y in pairs if x > med]
        lo = [y for x, y in pairs if x <= med]
        r = None
        if len(set(xs)) > 1 and len(set(ys)) > 1:
            mx, my = statistics.mean(xs), statistics.mean(ys)
            sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
            r = sum((x - mx) * (y - my) for x, y in pairs) / (len(pairs) * sx * sy)
        stay = [r_["label"] for r_ in rows if r_["label"] is not None]
        out.append({"feature": key, "label": label, "n": len(pairs), "r": None if r is None else round(r, 2),
                    "median": round(med, 2) if fn is None else round(math.expm1(med), 1),
                    "stay_above": None if not hi else round(100 * sum(hi) / len(hi)),
                    "stay_below": None if not lo else round(100 * sum(lo) / len(lo)),
                    "base": round(100 * sum(stay) / len(stay)) if stay else None})
    return out


def logistic(xs: list[list[float]], ys: list[int], l2: float = 1.0, iters: int = 3000, lr: float = 0.1) -> list[float]:
    n, k = len(xs), len(xs[0])
    w = [0.0] * (k + 1)
    for _ in range(iters):
        grad = [0.0] * (k + 1)
        for x, y in zip(xs, ys):
            z = w[0] + sum(wi * xi for wi, xi in zip(w[1:], x))
            p = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))
            e = p - y
            grad[0] += e
            for j in range(k):
                grad[j + 1] += e * x[j]
        for j in range(k + 1):
            reg = (l2 * w[j]) if j > 0 else 0.0
            w[j] -= lr * (grad[j] + reg) / n
    return w


def auc(scores: list[float], ys: list[int]) -> float | None:
    pos = [s for s, y in zip(scores, ys) if y == 1]
    neg = [s for s, y in zip(scores, ys) if y == 0]
    if not pos or not neg:
        return None
    wins = sum(1.0 if p > q else 0.5 if p == q else 0.0 for p in pos for q in neg)
    return wins / (len(pos) * len(neg))


def train(rows: list[dict]) -> dict:
    labeled = [r for r in rows if r["label"] is not None]
    n1 = sum(r["label"] for r in labeled)
    n0 = len(labeled) - n1
    result = {"n": len(labeled), "stayed": n1, "left": n0, "trained": False}
    if len(labeled) < MIN_TRAIN or n1 < MIN_CLASS or n0 < MIN_CLASS:
        result["why"] = (f"hacen falta {MIN_TRAIN} personajes con resultado (hay {len(labeled)}) y al menos "
                         f"{MIN_CLASS} que se quedaron y {MIN_CLASS} que se fueron (hay {n1} y {n0})")
        return result
    feats = [(k, lab, fn) for k, lab, fn in FEATURES
             if sum(1 for r in labeled if r.get(k) is not None) >= 0.8 * len(labeled)]
    cols = []
    for k, lab, fn in feats:
        vals = [_value(r, k, fn) for r in labeled if r.get(k) is not None]
        mean = statistics.mean(vals)
        sd = statistics.pstdev(vals)
        if sd == 0:
            continue
        cols.append({"feature": k, "label": lab, "log": fn is not None, "mean": mean, "sd": sd,
                     "fill": statistics.median(vals)})

    def vec(r):
        out = []
        for c in cols:
            v = _value(r, c["feature"], math.log1p if c["log"] else None)
            out.append(((c["fill"] if v is None else v) - c["mean"]) / c["sd"])
        return out

    xs = [vec(r) for r in labeled]
    ys = [r["label"] for r in labeled]
    w = train_w = logistic(xs, ys)
    # validación dejando uno afuera (con pocos datos, el número honesto)
    loo = []
    for i in range(len(xs)):
        wi = logistic(xs[:i] + xs[i + 1:], ys[:i] + ys[i + 1:], iters=1500)
        loo.append(wi[0] + sum(a * b for a, b in zip(wi[1:], xs[i])))
    for c, coef in zip(cols, w[1:]):
        c["coef"] = round(coef, 3)
        c["odds_x_sd"] = round(math.exp(coef), 2)
    result.update({"trained": True, "intercept": round(train_w[0], 3), "features": cols,
                   "auc_loo": None if auc(loo, ys) is None else round(auc(loo, ys), 2), "t": int(time.time())})
    return result


def predict(model: dict, row: dict) -> float | None:
    if not model.get("trained"):
        return None
    z = model["intercept"]
    for c in model["features"]:
        fn = math.log1p if c["log"] else None
        v = _value(row, c["feature"], fn)
        v = c["fill"] if v is None else v
        z += c["coef"] * (v - c["mean"]) / c["sd"]
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def risk_flags(row: dict) -> list[str]:
    """Señales de riesgo mientras no hay modelo (hipótesis a validar con los datos)."""
    flags = []
    if row["first_session_min"] is not None and row["first_session_min"] < 15:
        flags.append("1ª sesión < 15 min")
    if row["died_first_session"]:
        flags.append("murió en la 1ª sesión")
    if row["d1_levels"] == 0:
        flags.append("no subió de nivel el 1er día")
    if row["d1_chat"] == 0:
        flags.append("no habló con nadie")
    if row["label"] is None and row["returned_after_h"] is None and row["days_since_seen"] >= 2:
        flags.append(f"no vuelve hace {row['days_since_seen']:.0f} días")
    return flags


# ---------------------------------------------------------------- informe

def where_they_left(data: dict, now: float) -> dict:
    gone = [c for c in data["chars"] if c["label"] == 0 or (c["label"] is None and c["days_since_seen"] >= 7)]
    lv: dict[str, int] = {}
    zones: dict[str, int] = {}
    died = 0
    with_play = 0
    for c in gone:
        band = f"{(c['max_level'] // 5) * 5}-{(c['max_level'] // 5) * 5 + 4}"
        lv[band] = lv.get(band, 0) + 1
        ls = c["last_session"]
        if ls:
            with_play += 1
            died += 1 if ls["died_last"] else 0
            zones[ls["zone"]] = zones.get(ls["zone"], 0) + 1
    return {"gone": len(gone), "with_play": with_play, "died_last": died,
            "levels": sorted(lv.items(), key=lambda kv: int(kv[0].split("-")[0])),
            "zones": sorted(zones.items(), key=lambda kv: -kv[1])[:10]}


def heat(data: dict, days: int, now: float) -> tuple[list, list]:
    since = now - days * DAY
    z = data["zones"]
    spent: dict[str, int] = {}
    for p in data["positions"]:
        if p.get("t", 0) >= since:
            n = z.name(p.get("x", 0), p.get("y", 0), p.get("z", 7), bool(p.get("train")))
            spent[n] = spent.get(n, 0) + 2          # una muestra = 2 min
    died: dict[str, int] = {}
    for rows in data["deaths"].values():
        for d in rows:
            if d.get("t", 0) >= since:
                n = f"{d.get('killer') or '?'} en {z.name(d.get('x', 0), d.get('y', 0), d.get('z', 7))}"
                died[n] = died.get(n, 0) + 1
    return (sorted(spent.items(), key=lambda kv: -kv[1])[:12], sorted(died.items(), key=lambda kv: -kv[1])[:10])


def fmt_t(t: float) -> str:
    return time.strftime("%d/%m %H:%M", time.localtime(t))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=30, help="personajes que entraron por primera vez en estos días")
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    args = ap.parse_args()
    now = time.time()
    data = build(args.days, now)
    chars = data["chars"]
    model = train(chars)
    if model.get("trained"):
        try:
            MODEL_FILE.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    for c in chars:
        c["p_stay"] = None if predict(model, c) is None else round(predict(model, c), 2)
        c["risk"] = risk_flags(c)
    fun = funnel_table(data, args.days, now)
    uni = univariate(chars)
    left = where_they_left(data, now)
    spent, died = heat(data, args.days, now)

    if args.json:
        print(json.dumps({"days": args.days, "funnel": fun, "chars": chars, "relations": uni, "model": model,
                          "where_they_left": left, "time_by_zone_min": spent, "deaths_by_zone": died},
                         ensure_ascii=False, indent=1, default=str))
        return 0

    print(f"== Embudo ({args.days} días) ==")
    prev = None
    for label, n in fun:
        drop = "" if prev in (None, 0) or n > prev else f"  ({100 * n / prev:.0f} % del paso anterior)"
        print(f"  {label:<38} {n:>5}{drop}")
        prev = n
    back, known = retention_line(chars)
    if known:
        print(f"  {'volvió otro día (de los que ya tienen 7 días)':<38} {back:>5}  ({100 * back / known:.0f} % de {known})")
    else:
        print("  volvió otro día: todavía nadie cumplió 7 días desde su primer ingreso")

    print(f"\n== Primeros pasos de cada personaje nuevo ({len(chars)}) ==")
    if not chars:
        print("  (nadie entró por primera vez en el período)")
    for c in chars:
        state = {1: "SE QUEDÓ", 0: "SE FUE", None: "pendiente"}[c["label"]]
        p = "" if c["p_stay"] is None else f"  P(quedarse)={c['p_stay']:.0%}"
        print(f"  {c['name']} ({c['voc']}, cuenta {c['acc']}) · entró {fmt_t(c['first_login'])} · {state}{p}")
        reach = ", ".join(f"nivel {k} a los {v:.0f} min" for k, v in sorted(c["reach_min"].items())) or "sin datos de niveles"
        print(f"      1ª sesión {c['first_session_min']} min · {c['sessions']} sesión(es) en {c['days_played']} día(s) · "
              f"{c['online_min']:.0f} min en total · nivel {c['level_now']} · {reach}")
        if c["has_play"]:
            mons = ", ".join(f"{m} {n}" for m, n in c["top_monsters"]) or "nada"
            print(f"      1er día: {c['d1_levels']} niveles, {c['d1_kills']} monstruos ({mons}), {c['d1_deaths']} muertes, "
                  f"{c['d1_zones']} zonas, {c['d1_train_min']:.0f} min de training, {c['d1_chat']} mensajes, "
                  f"party {'sí' if c['d1_party'] else 'no'}")
        for d in c["deaths"][:3]:
            print(f"      murió en nivel {d['lvl']} por {d['killer'] or '?'}{' (PvP)' if d['pvp'] else ''} — {d['zone']}")
        ls = c["last_session"]
        if ls:
            print(f"      última sesión: {ls['min']} min, nivel {ls['lvl']}, vida {ls['hp']} %, "
                  f"{'MURIÓ al final (' + (ls['killer'] or '?') + ')' if ls['died_last'] else 'salió vivo'} — {ls['zone']}")
        print(f"      visto hace {c['days_since_seen']} días" + (f" · señales: {', '.join(c['risk'])}" if c["risk"] else ""))

    print(f"\n== Dónde se va la gente ({left['gone']} que no volvieron en 7 días) ==")
    if left["gone"]:
        print("  nivel al irse: " + ", ".join(f"{b}: {n}" for b, n in left["levels"]))
        if left["with_play"]:
            print(f"  murieron al final de su última sesión: {left['died_last']} de {left['with_play']}")
            for z, n in left["zones"]:
                print(f"  última posición: {z} ({n})")
    if spent:
        print("\n  Tiempo por zona (niveles 1-40, minutos):")
        for z, m in spent:
            print(f"    {m:>6}  {z}")
    if died:
        print("\n  Dónde y de qué mueren:")
        for z, n in died:
            print(f"    {n:>4}  {z}")

    print("\n== Qué se relaciona con quedarse ==")
    if not uni:
        print("  (todavía no hay personajes con resultado: hace falta que pasen 7 días desde su primer ingreso)")
    for u in uni:
        r = "—" if u["r"] is None else f"{u['r']:+.2f}"
        above = "—" if u["stay_above"] is None else f"{u['stay_above']} %"
        print(f"  {u['label']:<36} r={r}  se quedó: {above} si > {u['median']} · "
              f"{u['stay_below']} % si ≤ (base {u['base']} %, n={u['n']})")
    if uni:
        print("  (r va de -1 a +1: positivo = cuanto más de eso, más se quedan)")

    print("\n== Modelo: P(quedarse) = 1 / (1 + e^-(b0 + Σ bi·zi)), zi = (xi − media) / desvío ==")
    if not model.get("trained"):
        print(f"  Sin modelo todavía: {model['why']}.")
        print("  Mientras tanto, las señales de riesgo de cada personaje son hipótesis a confirmar.")
    else:
        print(f"  n={model['n']} (se quedaron {model['stayed']}, se fueron {model['left']}) · "
              f"AUC dejando uno afuera = {model['auc_loo']} (0,5 = azar, 1 = perfecto)")
        print(f"  b0 = {model['intercept']:+.3f}")
        for c in sorted(model["features"], key=lambda c: -abs(c["coef"])):
            print(f"  {c['coef']:+.3f} · {c['label']}{' (log)' if c['log'] else ''}  → "
                  f"×{c['odds_x_sd']} chances de quedarse por cada desvío más")
        print("  Ojo: datos muy parecidos entre sí (minutos y monstruos, por ejemplo) se reparten el peso; para leer")
        print("  cada uno por separado, mirar la tabla de arriba.")
    pend = [c for c in chars if c["label"] is None]
    if pend:
        print("\n== Nuevos todavía sin resultado ==")
        for c in sorted(pend, key=lambda c: (c["p_stay"] if c["p_stay"] is not None else 0.5)):
            p = "" if c["p_stay"] is None else f"P={c['p_stay']:.0%} · "
            print(f"  {c['name']}: {p}{', '.join(c['risk']) or 'sin señales de riesgo'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
