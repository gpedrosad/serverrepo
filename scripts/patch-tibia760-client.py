#!/usr/bin/env python3
"""Parchea Tibia.exe 7.6: reemplaza login hostnames por la IP del server."""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

CLIENT_EXE = "YurOTS.exe"
SOURCE_EXE = "Tibia.exe"
ASSET_FILES = ("Tibia.dat", "Tibia.spr", "Tibia.pic")
HOST_SLOTS = (
    582728,  # tibia2.cipsoft.com
    582748,  # tibia1.cipsoft.com
    582768,  # server.tibia.com
    582788,  # server2.tibia.com
    585084,  # test.cipsoft.com
)
SLOT_SIZE = 20
KNOWN_HOSTS = (
    b"tibia2.cipsoft.com",
    b"tibia1.cipsoft.com",
    b"server.tibia.com",
    b"server2.tibia.com",
    b"test.cipsoft.com",
)


def read_ip_from_config(config_path: Path) -> str:
    text = config_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'^\s*ip\s*=\s*"([^"]+)"\s*$', text, re.MULTILINE)
    if not match:
        raise SystemExit(f"No se encontró ip en {config_path}")
    return match.group(1)


def patch_exe(data: bytearray, ip: str) -> None:
    ip_bytes = ip.encode("ascii")
    if len(ip_bytes) > SLOT_SIZE:
        raise SystemExit(f"IP demasiado larga para el slot ({len(ip_bytes)} > {SLOT_SIZE}): {ip}")

    slot = ip_bytes + b"\x00" * (SLOT_SIZE - len(ip_bytes))
    for offset in HOST_SLOTS:
        current = bytes(data[offset : offset + SLOT_SIZE])
        if not any(host in current for host in KNOWN_HOSTS):
            raise SystemExit(
                f"Slot inesperado en offset {offset}: {current!r}. "
                "¿Es otro build de Tibia.exe?"
            )
        data[offset : offset + SLOT_SIZE] = slot


def main() -> int:
    parser = argparse.ArgumentParser(description="Parchea Tibia 7.6 para YurOTS")
    parser.add_argument(
        "--source",
        type=Path,
        help="Carpeta con Tibia.exe original (default: ~/Downloads/tibia76)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        help="Carpeta destino del cliente (default: <repo>/client-760)",
    )
    parser.add_argument(
        "--ip",
        help="IP del server (default: leída de server/YurOTS/ots/config.lua)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Ruta a config.lua",
    )
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="Copia el cliente listo a ~/Desktop/YurOTS-Cliente-7.6 y crea .zip",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    source = args.source or Path.home() / "Downloads" / "tibia76"
    dest = args.dest or project_root / "client-760"
    config = args.config or project_root / "server/YurOTS/ots/config.lua"
    ip = args.ip or read_ip_from_config(config)

    source_exe = source / SOURCE_EXE
    if not source_exe.is_file():
        raise SystemExit(f"No existe {source_exe}")

    dest.mkdir(parents=True, exist_ok=True)
    for name in ASSET_FILES:
        src = source / name
        if src.is_file():
            shutil.copy2(src, dest / name)

    data = bytearray(source_exe.read_bytes())
    patch_exe(data, ip)
    exe_path = dest / CLIENT_EXE
    exe_path.write_bytes(data)
    legacy = dest / SOURCE_EXE
    if legacy.is_file():
        legacy.unlink()

    readme = dest / "LEEME.txt"
    readme.write_text(
        f"""YurOTS — Cliente Tibia 7.6
==========================

1. Ejecutá {CLIENT_EXE} (Windows).
2. Login con número de cuenta y contraseña.
3. No hace falta IP changer: ya apunta a {ip}:7171

Crear cuenta: http://{ip}:8080/ (pestaña Cuenta)
Info del server: http://{ip}:8080/

Solo Windows nativo. En Mac hace falta Wine/CrossOver.
""",
        encoding="utf-8",
    )

    print(f"Cliente parcheado en {dest}")
    print(f"IP de login: {ip}:7171")
    print(f"Ejecutable: {CLIENT_EXE}")

    if args.desktop:
        import zipfile

        desktop_dir = Path.home() / "Desktop" / "YurOTS-Cliente-7.6"
        zip_path = Path.home() / "Desktop" / "YurOTS-Cliente-7.6.zip"
        if desktop_dir.exists():
            shutil.rmtree(desktop_dir)
        shutil.copytree(dest, desktop_dir)
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(desktop_dir.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(desktop_dir.parent))
        print(f"Carpeta: {desktop_dir}")
        print(f"ZIP:     {zip_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
