"""Manifest del auto-updater de OTClientV8 para el cliente Retro76.

El cliente (binario + data.zip) hace POST a /api/updater.php al abrirse. Se responde con todos los archivos del
cliente publicado (web/updater/files/, lo arma scripts/client-rme/publish_client.py) y su CRC32 en hex minúscula de 8
dígitos, el formato del cliente (filesChecksums y g_crypt.crc32 del binario 3.2). El cliente baja solo los que
cambiaron desde <url><ruta>, arma un data.zip nuevo en su carpeta de usuario y lo usa desde ahí en adelante.
Doc: docs/CLIENT_UPDATER_RETRO76.md.
"""
from __future__ import annotations

import zlib
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent
UPDATER_FILES_DIR = WEB_DIR / "updater" / "files"

# Sin estos el cliente publicado está roto: se devuelve un error en vez de un manifest a medias.
REQUIRED_FILES = (
    "init.lua",
    "data/things/760/Tibia.dat",
    "data/things/760/Tibia.spr",
)

_cache: dict[str, tuple[int, int, str]] = {}


def crc32_hex(path: Path) -> str:
    """CRC32 como lo calcula el cliente: 8 dígitos hex en minúscula (con ceros a la izquierda)."""
    st = path.stat()
    hit = _cache.get(str(path))
    if hit and hit[0] == st.st_mtime_ns and hit[1] == st.st_size:
        return hit[2]
    value = format(zlib.crc32(path.read_bytes()) & 0xFFFFFFFF, "08x")
    _cache[str(path)] = (st.st_mtime_ns, st.st_size, value)
    return value


def build_updater_response(files_url: str, root: Path = UPDATER_FILES_DIR) -> dict:
    files: dict[str, str] = {}
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root).as_posix()
            if path.is_file() and not any(part.startswith(".") for part in rel.split("/")):
                files[f"/{rel}"] = crc32_hex(path)
    payload: dict = {
        "url": files_url.rstrip("/"),
        "files": files,
        "keepFiles": True,
    }
    missing = [rel for rel in REQUIRED_FILES if f"/{rel}" not in files]
    if missing:
        payload["error"] = ("El cliente publicado en el servidor está incompleto (falta "
                            + ", ".join(missing) + "). Avisar al administrador.")
    return payload
