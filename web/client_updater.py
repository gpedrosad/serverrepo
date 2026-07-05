"""Manifest OTClientV8 para parches de sprites Retro76 (CRC32b)."""
from __future__ import annotations

import zlib
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent
UPDATER_FILES_DIR = WEB_DIR / "updater" / "files"

THINGS_FILES = (
    "data/things/760/Tibia.dat",
    "data/things/760/Tibia.spr",
)


def crc32b_hex(path: Path) -> str:
    """Checksum compatible con OTCv8 / PHP hash_file('crc32b')."""
    digest = zlib.crc32(path.read_bytes()) & 0xFFFFFFFF
    parsed = format(digest, "x").lstrip("0")
    return parsed or "0"


def build_updater_response(files_url: str) -> dict:
    files: dict[str, str] = {}
    missing: list[str] = []
    for rel in THINGS_FILES:
        path = UPDATER_FILES_DIR / rel
        if not path.is_file():
            missing.append(rel)
            continue
        files[f"/{rel}"] = crc32b_hex(path)
    payload: dict = {
        "url": files_url.rstrip("/"),
        "files": files,
        "keepFiles": True,
    }
    if missing:
        payload["error"] = f"Faltan archivos del updater: {', '.join(missing)}"
    return payload
