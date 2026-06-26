"""Lee datos del server Retro76 para la web."""
from __future__ import annotations

import json
import re
import socket
import struct
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

VOCATIONS = ["Rook", "Sorcerer", "Druid", "Paladin", "Knight"]
VOC_SHORT = ["—", "S", "D", "P", "K"]
ACCOUNT_MIN = 100_000
ACCOUNT_MAX = 999_999
FEMALE_LOOK = {1: "136", 2: "137", 3: "139", 4: "133"}
MALE_LOOK = {1: "130", 2: "130", 3: "131", 4: "131"}
SKILL_NAMES = {
    0: "Fist",
    2: "Sword",
    4: "Distance",
    5: "Shield",
    6: "Fishing",
}
VOC_TEMPLATES = frozenset({"0", "1", "2", "3", "4"})
HIDDEN_RANK_PLAYERS = frozenset({"yurez", "yurez the next", "gm kaiser"})


def is_public_rank_player(name: str) -> bool:
    return name.strip().lower() not in HIDDEN_RANK_PLAYERS


def player_save_path(players_dir: Path, name: str) -> Path:
    return players_dir / f"{name.strip().lower()}.xml"


def player_name_taken(players_dir: Path, name: str) -> bool:
    key = name.strip().lower()
    if not players_dir.is_dir():
        return False
    for path in players_dir.glob("*.xml"):
        if path.stem in VOC_TEMPLATES:
            continue
        if path.stem.lower() == key:
            return True
    return False


def read_server_ip(config_path: Path) -> str:
    if not config_path.is_file():
        return "127.0.0.1"
    for line in config_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r'^\s*ip\s*=\s*"([^"]+)"', line)
        if m and m.group(1) != "auto":
            return m.group(1)
    return "127.0.0.1"


def fmt_num(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def rel_time(ts: int) -> str:
    if ts <= 0:
        return "—"
    diff = int(time.time()) - ts
    if diff < 60:
        return "ahora"
    if diff < 3600:
        return f"hace {diff // 60}m"
    if diff < 86400:
        return f"hace {diff // 3600}h"
    if diff < 604800:
        return f"hace {diff // 86400}d"
    return datetime.fromtimestamp(ts).strftime("%d/%m/%y")


def fmt_uptime(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"


def _validate_registration(acc: int, name: str, password: str, sex: int, voc: int) -> str | None:
    if acc < ACCOUNT_MIN or acc > ACCOUNT_MAX:
        return f"Cuenta inválida (usa {ACCOUNT_MIN}-{ACCOUNT_MAX})"
    name = name.strip()
    if not re.fullmatch(r"[a-zA-Z ]{3,20}", name):
        return "Nombre inválido (3-20 letras y espacios)"
    if name.lower().startswith("gm"):
        return "El nombre no puede empezar por GM"
    if not re.fullmatch(r"[a-zA-Z0-9]{3,20}", password):
        return "Contraseña inválida (3-20 alfanuméricos)"
    if sex not in (0, 1):
        return "Sexo inválido"
    if voc not in (1, 2, 3, 4):
        return "Vocación inválida"
    return None


def create_account(
    accounts_dir: Path,
    players_dir: Path,
    acc: int,
    name: str,
    password: str,
    sex: int,
    voc: int,
) -> dict:
    err = _validate_registration(acc, name, password, sex, voc)
    if err:
        return {"ok": False, "message": err}

    name = name.strip()
    acc_path = accounts_dir / f"{acc}.xml"
    player_path = player_save_path(players_dir, name)
    template_path = players_dir / f"{voc}.xml"

    if acc_path.exists():
        return {"ok": False, "message": "Ese número de cuenta ya existe"}
    if player_name_taken(players_dir, name):
        return {"ok": False, "message": "Ese nombre ya está en uso"}
    if not template_path.is_file():
        return {"ok": False, "message": "Vocación no disponible"}

    try:
        account_xml = (
            '<?xml version="1.0"?>\n'
            f'<account pass="{escape(password)}" type="0" premDays="0">\n'
            f'\t<characters>\n\t\t<character name="{escape(name)}" />\n'
            f"\t</characters>\n</account>\n"
        )
        tree = ET.parse(template_path)
        root = tree.getroot()
        root.set("name", name)
        root.set("account", str(acc))
        root.set("sex", str(sex))
        look = root.find("look")
        if look is not None:
            look.set("type", MALE_LOOK[voc] if sex == 1 else FEMALE_LOOK[voc])

        accounts_dir.mkdir(parents=True, exist_ok=True)
        players_dir.mkdir(parents=True, exist_ok=True)
        acc_path.write_text(account_xml, encoding="utf-8")
        tree.write(player_path, encoding="utf-8", xml_declaration=True)
    except OSError:
        return {"ok": False, "message": "No se pudo guardar la cuenta en el servidor"}

    return {
        "ok": True,
        "account": acc,
        "message": f"Cuenta {acc} creada. Entra con ese número y tu contraseña en el cliente.",
    }


def fetch_server_status(host: str, port: int, timeout: float = 2.0) -> dict:
    out = {
        "online": False,
        "players_online": 0,
        "players_max": 28,
        "players_peak": 0,
        "uptime_seconds": 0,
        "servername": "Retro76",
        "version": "",
    }
    try:
        payload = struct.pack("<H", 0xFFFF) + b"info"
        packet = struct.pack("<H", len(payload)) + payload
        with socket.create_connection((host, port), timeout) as sock:
            sock.sendall(packet)
            data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
        root = ET.fromstring(data.decode("utf-8", errors="replace"))
        out["online"] = True
        si = root.find("serverinfo")
        if si is not None:
            out["uptime_seconds"] = int(si.get("uptime", "0"))
            out["servername"] = si.get("servername", "Retro76")
            out["version"] = si.get("version", "")
            out["players_max"] = int(root.find("players").get("max", "28") if root.find("players") is not None else "28")
        pl = root.find("players")
        if pl is not None:
            out["players_online"] = int(pl.get("online", "0"))
            out["players_peak"] = int(pl.get("peak", "0"))
            out["players_max"] = int(pl.get("max", str(out["players_max"])))
    except OSError:
        pass
    except ET.ParseError:
        out["online"] = False
    return out


def parse_player(path: Path) -> dict | None:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    if root.tag != "player":
        return None

    access = int(root.get("access", "0"))
    lastlogin = int(root.get("lastlogin", "0"))
    banned = int(root.get("banned", "0"))
    if access > 0 or lastlogin <= 0 or banned != 0:
        return None

    voc = int(root.get("voc", "0"))
    skills: dict[int, int] = {}
    skills_el = root.find("skills")
    if skills_el is not None:
        for sk in skills_el.findall("skill"):
            skills[int(sk.get("skillid", "0"))] = int(sk.get("level", "0"))

    skull_el = root.find("skull")
    frags = int(skull_el.get("kills", "0")) if skull_el is not None else 0
    skull = int(skull_el.get("type", "0")) if skull_el is not None else 0

    guild_el = root.find("guild")
    guild = guild_el.get("name", "") if guild_el is not None else ""

    deaths = []
    deaths_el = root.find("deaths")
    if deaths_el is not None:
        for d in deaths_el.findall("death"):
            t = int(d.get("time", "0"))
            if t > 0:
                deaths.append(
                    {
                        "victim": root.get("name", "?"),
                        "killer": d.get("name", "?"),
                        "level": int(d.get("level", "0")),
                        "time": t,
                    }
                )

    now = int(time.time())
    active = lastlogin > 0 and (now - lastlogin) < 300

    return {
        "name": root.get("name", "?"),
        "level": int(root.get("level", "1")),
        "exp": int(root.get("exp", "0")),
        "voc": voc,
        "vocation": VOCATIONS[voc] if 0 <= voc < len(VOCATIONS) else "?",
        "vocation_short": VOC_SHORT[voc] if 0 <= voc < len(VOC_SHORT) else "?",
        "maglevel": int(root.get("maglevel", "0")),
        "guild": guild,
        "frags": frags,
        "skull": skull,
        "lastlogin": lastlogin,
        "lastlogin_rel": rel_time(lastlogin),
        "active": active,
        "skills": skills,
        "deaths": deaths,
    }


def load_otinfo(otinfo_file: Path) -> list[dict]:
    if not otinfo_file.is_file():
        return []
    sections: list[dict] = []
    current_title = "Info"
    lines: list[str] = []
    for raw in otinfo_file.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip():
            if lines:
                sections.append({"title": current_title, "lines": lines})
                lines = []
            continue
        if line.isupper() and not line.startswith(" "):
            if lines:
                sections.append({"title": current_title, "lines": lines})
                lines = []
            current_title = line.strip()
        else:
            lines.append(line.strip())
    if lines:
        sections.append({"title": current_title, "lines": lines})
    return sections


def load_online(online_file: Path) -> list[dict]:
    if not online_file.is_file():
        return []
    try:
        root = ET.parse(online_file).getroot()
    except ET.ParseError:
        return []
    out = []
    for p in root.findall("player"):
        voc = int(p.get("voc", "0"))
        out.append(
            {
                "name": p.get("name", "?"),
                "level": int(p.get("level", "1")),
                "voc": voc,
                "vocation": VOCATIONS[voc] if 0 <= voc < len(VOCATIONS) else "?",
                "vocation_short": VOC_SHORT[voc] if 0 <= voc < len(VOC_SHORT) else "?",
                "exp": int(p.get("exp", "0")),
                "exp_fmt": fmt_num(int(p.get("exp", "0"))),
            }
        )
    out.sort(key=lambda x: (-x["level"], x["name"].lower()))
    return out


def load_daily_state(state_file: Path) -> dict:
    if state_file.is_file():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_daily_state(state_file: Path, state: dict) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def daily_rankings(players: list[dict], state_file: Path) -> tuple[list[dict], list[dict]]:
    today = datetime.now().strftime("%Y%m%d")
    state = load_daily_state(state_file)

    if state.get("date") != today:
        state = {
            "date": today,
            "exp_baseline": {p["name"]: p["exp"] for p in players},
            "frags_baseline": {p["name"]: p["frags"] for p in players},
        }

    exp_base: dict = state.setdefault("exp_baseline", {})
    frags_base: dict = state.setdefault("frags_baseline", {})

    for p in players:
        name = p["name"]
        if name not in exp_base:
            exp_base[name] = p["exp"]
        if name not in frags_base:
            frags_base[name] = p["frags"]

    power: list[dict] = []
    frags_today: list[dict] = []
    for p in players:
        gain = max(0, p["exp"] - int(exp_base.get(p["name"], p["exp"])))
        frag_gain = max(0, p["frags"] - int(frags_base.get(p["name"], p["frags"])))
        if gain > 0:
            row = {
                "name": p["name"],
                "level": p["level"],
                "vocation_short": p["vocation_short"],
                "gain": gain,
                "gain_fmt": fmt_num(gain),
            }
            power.append(row)
        if frag_gain > 0:
            frags_today.append(
                {
                    "name": p["name"],
                    "level": p["level"],
                    "vocation_short": p["vocation_short"],
                    "frags": frag_gain,
                }
            )

    power.sort(key=lambda x: (-x["gain"], -x["level"], x["name"].lower()))
    frags_today.sort(key=lambda x: (-x["frags"], -x["level"], x["name"].lower()))

    state["date"] = today
    save_daily_state(state_file, state)
    return power, frags_today


def top_fraggers(players: list[dict]) -> list[dict]:
    rows = [
        {
            "name": p["name"],
            "level": p["level"],
            "vocation_short": p["vocation_short"],
            "frags": p["frags"],
            "skull": p["skull"],
        }
        for p in players
        if p["frags"] > 0
    ]
    rows.sort(key=lambda x: (-x["frags"], -x["level"], x["name"].lower()))
    return rows


def build_payload(
    players_dir: Path,
    otinfo_file: Path,
    online_file: Path,
    state_file: Path,
    ot_host: str,
    ot_port: int,
    server_ip: str = "127.0.0.1",
) -> dict:
    players: list[dict] = []
    all_deaths: list[dict] = []

    if players_dir.is_dir():
        for path in players_dir.glob("*.xml"):
            p = parse_player(path)
            if not p:
                continue
            pub = {k: v for k, v in p.items() if k not in ("skills", "deaths")}
            pub["exp_fmt"] = fmt_num(p["exp"])
            pub["sword"] = p["skills"].get(2, p["skills"].get(0, 0))
            pub["distance"] = p["skills"].get(4, 0)
            players.append(pub)
            all_deaths.extend(p["deaths"])

    players.sort(key=lambda p: (-p["level"], -p["exp"], p["name"].lower()))
    public_players = [p for p in players if is_public_rank_player(p["name"])]

    by_ml = sorted(public_players, key=lambda p: (-p["maglevel"], -p["level"], p["name"].lower()))
    by_sword = sorted(public_players, key=lambda p: (-p["sword"], -p["level"], p["name"].lower()))
    by_dist = sorted(public_players, key=lambda p: (-p["distance"], -p["level"], p["name"].lower()))
    by_frags = sorted(public_players, key=lambda p: (-p["frags"], -p["level"], p["name"].lower()))

    all_deaths.sort(key=lambda d: -d["time"])
    for i, d in enumerate(all_deaths[:20], 1):
        d["rank"] = i
        d["time_rel"] = rel_time(d["time"])

    status = fetch_server_status(ot_host, ot_port)
    status["uptime_fmt"] = fmt_uptime(status["uptime_seconds"])

    online = [p for p in load_online(online_file) if is_public_rank_player(p.get("name", ""))]
    powergamers, frags_today = daily_rankings(public_players, state_file)
    top_frags = top_fraggers(public_players)

    return {
        "updated": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        "connect": {"host": server_ip, "port": ot_port},
        "server": status,
        "online": online,
        "powergamers": powergamers[:15],
        "top_fraggers": top_frags[:15],
        "frags_today": frags_today[:15],
        "players": public_players,
        "rankings": {
            "level": public_players,
            "ml": by_ml,
            "sword": by_sword,
            "distance": by_dist,
            "frags": by_frags,
        },
        "deaths": all_deaths[:20],
        "otinfo": load_otinfo(otinfo_file),
        "vocations": VOCATIONS[1:],
    }
