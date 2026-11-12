#!/usr/bin/env python3
"""Publica el cliente Retro76 para el auto-updater y arma los zips de descarga.

Se corre en la ThinkPad, donde están el repo del cliente (~/apps/clienteretro) y la web (contenedor retro76-web):

  python3 scripts/client-rme/publish_client.py            # sincroniza sprites, publica y arma zips
  python3 scripts/client-rme/publish_client.py --dry-run  # solo dice qué cambiaría

Qué hace:
  1. Copia Tibia.dat / Tibia.spr de devtools/rme/rme-client-760 (la fuente de verdad) a mac/ y windows/ del
     cliente (data/things/760/). Con --no-sync se publica el cliente tal cual.
  2. Comprueba que mac/ y windows/ tengan los mismos archivos de datos (solo cambian binarios y lanzadores).
  3. Copia esos datos (init.lua, data/, modules/, layouts/...) a web/updater/files/. El updater de la web
     (web/client_updater.py) lista esa carpeta con su CRC32; los clientes bajan lo que les cambió al abrirse.
  4. Arma web/downloads/Retro76-Mac.zip y Retro76-Windows.zip: binario + lanzador + LEEME + data.zip (los datos
     empaquetados; el updater de OTClientV8 solo funciona cuando el cliente corre desde un data.zip).

Después de publicar no hace falta reiniciar nada: la web lee web/updater/files/ en cada pedido.
Doc: docs/CLIENT_UPDATER_RETRO76.md.
"""
from __future__ import annotations

import argparse
import filecmp
import io
import shutil
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THINGS = ROOT / "devtools" / "rme" / "rme-client-760"
WEB = ROOT / "web"

# Archivos de cada plataforma (en la raíz de mac/ o windows/); todo lo demás son datos comunes.
PLATFORM_FILES = {
    "mac": ["otclient_mac", "Iniciar Cliente.command", "LEEME.txt"],
    "windows": ["otclient_gl.exe", "otclient_dx.exe", "d3dcompiler_47.dll", "libEGL.dll", "libGLESv2.dll",
                "Iniciar Cliente.bat", "LEEME.txt"],
}
EXECUTABLE = {"otclient_mac", "Iniciar Cliente.command"}
ALL_PLATFORM = {name for names in PLATFORM_FILES.values() for name in names}
ZIP_NAMES = {"mac": "Retro76-Mac", "windows": "Retro76-Windows"}
ZIP_DATE = (2026, 1, 1, 0, 0, 0)  # fecha fija: el mismo contenido da el mismo zip


def data_files(platform_dir: Path) -> dict[str, Path]:
    """ruta relativa -> archivo, de los datos comunes (sin binarios, lanzadores, logs ni ocultos)."""
    out = {}
    for path in sorted(platform_dir.rglob("*")):
        rel = path.relative_to(platform_dir).as_posix()
        parts = rel.split("/")
        if not path.is_file() or any(p.startswith(".") for p in parts) or rel.endswith(".log"):
            continue
        if len(parts) == 1 and rel in ALL_PLATFORM:
            continue
        out[rel] = path
    return out


def zip_entry(zf: zipfile.ZipFile, name: str, data: bytes, executable: bool = False) -> None:
    info = zipfile.ZipInfo(name, ZIP_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100755 if executable else 0o100644) << 16
    info.create_system = 3  # unix, para que se respeten los permisos
    zf.writestr(info, data)


def build_data_zip(files: dict[str, Path]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for rel, path in files.items():
            zip_entry(zf, rel, path.read_bytes())
    return buf.getvalue()


def crc(path: Path) -> str:
    return format(zlib.crc32(path.read_bytes()) & 0xFFFFFFFF, "08x")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", type=Path, default=Path.home() / "apps" / "clienteretro",
                    help="repo del cliente (con mac/ y windows/)")
    ap.add_argument("--no-sync", action="store_true", help="no copiar Tibia.dat/.spr desde devtools/rme")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    dirs = {plat: a.client / plat for plat in PLATFORM_FILES}
    for plat, d in dirs.items():
        if not (d / "init.lua").is_file():
            raise SystemExit(f"no encuentro {d}/init.lua: ¿--client apunta al repo del cliente?")

    # 1. sprites
    if not a.no_sync:
        for plat, d in dirs.items():
            for name in ("Tibia.dat", "Tibia.spr"):
                src, dst = THINGS / name, d / "data" / "things" / "760" / name
                if not dst.is_file() or not filecmp.cmp(src, dst, shallow=False):
                    print(f"  sprites: {src.relative_to(ROOT)} -> {dst}")
                    if not a.dry_run:
                        shutil.copyfile(src, dst)

    # 2. mac y windows con los mismos datos
    files = {plat: data_files(d) for plat, d in dirs.items()}
    mac, win = files["mac"], files["windows"]
    diff = sorted(set(mac) ^ set(win)) + sorted(r for r in set(mac) & set(win)
                                                  if not filecmp.cmp(mac[r], win[r], shallow=False))
    if diff and not a.dry_run:
        raise SystemExit("mac/ y windows/ tienen datos distintos (deben ser iguales):\n  " + "\n  ".join(diff[:30]))

    # 3. carpeta del updater
    dest = WEB / "updater" / "files"
    old = data_files(dest) if dest.is_dir() else {}
    changed = [r for r in mac if r not in old or not filecmp.cmp(mac[r], old[r], shallow=False)]
    removed = [r for r in old if r not in mac]
    print(f"updater: {len(mac)} archivos, {len(changed)} cambiados, {len(removed)} borrados")
    for rel in changed[:20]:
        print(f"  ~ {rel}")
    for rel in removed[:20]:
        print(f"  - {rel}")
    if a.dry_run:
        return 0
    tmp = dest.with_name("files.new")
    shutil.rmtree(tmp, ignore_errors=True)
    for rel, path in mac.items():
        (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, tmp / rel)
    if dest.exists():
        dest.rename(dest.with_name("files.old"))
    tmp.rename(dest)
    shutil.rmtree(dest.with_name("files.old"), ignore_errors=True)

    # 4. zips de descarga
    data_zip = build_data_zip(mac)
    downloads = WEB / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    for plat, d in dirs.items():
        top = ZIP_NAMES[plat]
        out = downloads / f"{top}.zip"
        with zipfile.ZipFile(out.with_suffix(".tmp"), "w") as zf:
            for name in PLATFORM_FILES[plat]:
                zip_entry(zf, f"{top}/{name}", (d / name).read_bytes(), executable=name in EXECUTABLE)
            zip_entry(zf, f"{top}/data.zip", data_zip)
        out.with_suffix(".tmp").replace(out)
        print(f"descarga: {out} ({out.stat().st_size // 1024} KB)")

    print(f"Tibia.dat crc {crc(dest / 'data/things/760/Tibia.dat')}, Tibia.spr crc {crc(dest / 'data/things/760/Tibia.spr')}")
    print("Listo: los clientes con updater se actualizan al abrirse.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
