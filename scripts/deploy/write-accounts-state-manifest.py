#!/usr/bin/env python3
"""Genera accounts-state.json desde un árbol de backup (accounts/ + players/)."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def player_summary(path: Path) -> Optional[dict[str, Any]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    if root.tag != "player":
        return None
    spawn = root.find("spawn")
    pos = None
    if spawn is not None:
        pos = {k: spawn.get(k) for k in ("x", "y", "z") if spawn.get(k) is not None}
        if not pos:
            pos = None
    return {
        "name": root.get("name"),
        "account": root.get("account"),
        "level": int(root.get("level", "0") or 0),
        "voc": int(root.get("voc", "0") or 0),
        "exp": root.get("exp"),
        "access": int(root.get("access", "0") or 0),
        "banned": root.get("banned", "0"),
        "lastlogin": root.get("lastlogin"),
        "pos": pos,
        "file": path.name,
    }


def build_manifest(data_dir: Path) -> dict[str, Any]:
    accounts_dir = data_dir / "accounts"
    players_dir = data_dir / "players"
    templates = {"0.xml", "1.xml", "2.xml", "3.xml", "4.xml"}

    players_by_name: dict[str, dict[str, Any]] = {}
    for p in sorted(players_dir.glob("*.xml")):
        if p.name in templates:
            continue
        info = player_summary(p)
        if info and info.get("name"):
            players_by_name[info["name"].lower()] = info

    accounts: list[dict[str, Any]] = []
    for acc_path in sorted(accounts_dir.glob("*.xml")):
        try:
            root = ET.parse(acc_path).getroot()
        except ET.ParseError:
            continue
        if root.tag != "account":
            continue
        characters: list[dict[str, Any]] = []
        chars_el = root.find("characters")
        if chars_el is not None:
            for ch in chars_el.findall("character"):
                name = ch.get("name", "")
                entry: dict[str, Any] = {"name": name}
                pinfo = players_by_name.get(name.lower())
                if pinfo:
                    entry.update(
                        {
                            "level": pinfo["level"],
                            "voc": pinfo["voc"],
                            "exp": pinfo["exp"],
                            "access": pinfo["access"],
                            "banned": pinfo["banned"],
                            "lastlogin": pinfo["lastlogin"],
                            "pos": pinfo["pos"],
                            "player_file": pinfo["file"],
                        }
                    )
                characters.append(entry)
        accounts.append(
            {
                "account_id": acc_path.stem,
                "type": root.get("type"),
                "premDays": root.get("premDays"),
                "balance": root.get("balance"),
                "characters": characters,
                "file": acc_path.name,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_dir": str(data_dir),
        "accounts_count": len(accounts),
        "players_files": len(players_by_name),
        "accounts": accounts,
    }


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Uso: {sys.argv[0]} <backup_dir> <out.json>", file=sys.stderr)
        sys.exit(1)
    data_dir = Path(sys.argv[1])
    out = Path(sys.argv[2])
    payload = build_manifest(data_dir)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK {payload['accounts_count']} cuentas, {payload['players_files']} personajes → {out}")


if __name__ == "__main__":
    main()
