#!/usr/bin/env python3
"""Crea o rehace un looktype de criatura recoloreando otra del cliente 7.6 (motor genérico).

Cada criatura es un preset: un archivo en scripts/client-rme/presets/ (tide_priest.py = preset
`tide-priest`) con `PRESET = dict(name, source, target, ...)`. La lista, con su estado, sale de
`python3 scripts/client-rme/sprite_tool.py looks`. Para empezar uno nuevo: `sprite_tool.py new`.

El método copia la estructura de la criatura base (tamaño, direcciones, cuadros) a un looktype
vacío y le pone sprites nuevos pintados píxel por píxel, así la animación queda idéntica.

Uso:
  python3 scripts/client-rme/add_recolor_look.py --preset tide-priest --preview x.png         # solo vista previa
  python3 scripts/client-rme/add_recolor_look.py --preset tide-priest DIR_THINGS              # aplicar
  python3 scripts/client-rme/add_recolor_look.py --preset tide-priest DIR_THINGS --replace    # rehacer el look

DIR_THINGS = carpeta con Tibia.dat y Tibia.spr (se modifican en el lugar, con copia
.bak-<preset>). Idempotente: si el looktype destino ya tiene sprites, no cambia nada, salvo con
--replace, que vuelve a generar esos mismos sprites con el preset actual (para editar un look
que ya existe; los ids de sprites no cambian).
Aplicar a devtools/rme/rme-client-760/ (RME, en git) y a la base del cliente de jugadores.

Receta paso a paso: docs/gameplay/SPRITE_RECOLOR_GUIDE.md. Piezas para escribir presets:
scripts/client-rme/sprite_kit.py. Para mirar, comparar y verificar: scripts/client-rme/sprite_tool.py.
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from add_black_dragon_look import decode_sprite, encode_sprite, read_outfits, read_spr, write_preview, write_spr  # noqa: E402
from sprite_kit import Frame, palette_recolor  # noqa: E402

RME_THINGS = HERE.parents[1] / "devtools/rme/rme-client-760"
PRESET_DIR = HERE / "presets"
PRESET_KEYS = {"name", "source", "target", "recolor", "palettes", "parts", "detail", "frames_post"}


def load_presets() -> dict:
    """Lee los presets: un archivo por criatura en presets/ con `PRESET = dict(...)`.
    El nombre del preset es el del archivo, con guiones (tide_priest.py -> tide-priest)."""
    presets, by_target = {}, {}
    for path in sorted(PRESET_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"sprite_preset_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        preset = dict(module.PRESET)
        problems = [f"falta '{key}'" for key in ("name", "source", "target") if key not in preset]
        problems += [f"clave desconocida '{key}'" for key in preset if key not in PRESET_KEYS]
        if "recolor" not in preset and "palettes" not in preset:
            problems.append("falta 'recolor' o 'palettes'")
        if ("palettes" in preset or "detail" in preset) and not preset.get("parts"):
            problems.append("'palettes' y 'detail' necesitan 'parts' (el clasificador de partes)")
        if preset.get("target") in by_target:
            problems.append(f"el look {preset['target']} ya es de {by_target[preset['target']]}")
        if problems:
            raise SystemExit(f"presets/{path.name}: " + "; ".join(problems))
        by_target[preset["target"]] = path.name
        preset["file"] = path
        presets[path.stem.replace("_", "-")] = preset
    return presets


PRESETS = load_presets()


def frames_2x2(decoded: dict[int, list]) -> list[list]:
    """Cuadros 64x64 en orden anim -> dirección; tiles 2x2 empezando por abajo-derecha."""
    frames = []
    for anim in range(3):
        for direction in range(4):
            frame = [(0, 0, 0, 0)] * (64 * 64)
            base = (anim * 4 + direction) * 4
            for tile in range(4):
                ox, oy = (1 - tile % 2) * 32, (1 - tile // 2) * 32
                for i, p in enumerate(decoded[base + tile]):
                    if p[3]:
                        frame[(oy + i // 32) * 64 + ox + i % 32] = p
            frames.append(frame)
    return frames


def split_2x2(frames: list[list]) -> dict[int, list]:
    """Inverso de frames_2x2: vuelve a los 48 sprites de 32x32 en el orden del .dat."""
    decoded = {}
    for anim in range(3):
        for direction in range(4):
            frame = frames[anim * 4 + direction]
            base = (anim * 4 + direction) * 4
            for tile in range(4):
                ox, oy = (1 - tile % 2) * 32, (1 - tile // 2) * 32
                decoded[base + tile] = [frame[(oy + i // 32) * 64 + ox + i % 32] for i in range(1024)]
    return decoded


def load_things(things_dir: Path) -> dict:
    """Lee Tibia.dat / Tibia.spr de una carpeta: bytes, looktypes y tabla de sprites."""
    dat_path, spr_path = things_dir / "Tibia.dat", things_dir / "Tibia.spr"
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    outfits, counts = read_outfits(dat)
    spr_count, offsets = read_spr(spr)
    return dict(dat_path=dat_path, spr_path=spr_path, dat=dat, spr=spr, outfits=outfits, counts=counts,
                spr_count=spr_count, offsets=offsets)


def look_frames(things: dict, look: int) -> tuple[list[list], int]:
    """Los 12 cuadros de un looktype (índice = anim * 4 + dirección) y su lado en píxeles:
    32 si la criatura es 1x1 (12 sprites) o 64 si es 2x2 (48 sprites)."""
    ids = things["outfits"][look - 1]["ids"]
    if len(ids) not in (12, 48):
        raise SystemExit(f"Look {look}: se espera una criatura 1x1 o 2x2 con 4 direcciones y 3 cuadros "
                         f"(12 o 48 sprites); tiene {len(ids)}")
    decoded = {i: decode_sprite(things["spr"], things["offsets"], sid) for i, sid in enumerate(ids)}
    return (frames_2x2(decoded), 64) if len(ids) == 48 else ([decoded[i] for i in range(12)], 32)


def build_preset(things: dict, p: dict) -> tuple[list[list], list[list], int]:
    """Cuadros del base, cuadros nuevos (paleta + retoque por cuadro) y lado del cuadro."""
    original, size = look_frames(things, p["source"])
    recolor = p.get("recolor") or palette_recolor(p["parts"], p["palettes"], original)
    new = [[recolor(px) for px in frame] for frame in original]
    if p.get("frames_post"):                      # retoque con los 12 cuadros a la vez (presets viejos)
        new = p["frames_post"](original, new)
    if p.get("detail"):                           # rasgo propio, cuadro por cuadro
        frames = []
        for index, (orig, px) in enumerate(zip(original, new)):
            frame = Frame(index, orig, px, size, p["parts"])
            p["detail"](frame)
            frames.append(frame.px)
        new = frames
    return original, new, size


def frames_to_sprites(frames: list[list], size: int) -> dict[int, list]:
    """Cuadros -> sprites de 32x32 en el orden del .dat."""
    return split_2x2(frames) if size == 64 else dict(enumerate(frames))


def sprite_record(spr: bytes, offsets: list[int], sprite_id: int) -> bytes:
    """Bytes tal cual de un sprite en el .spr (vacío si el id no tiene datos)."""
    off = offsets[sprite_id - 1] if 0 < sprite_id <= len(offsets) else 0
    if not off:
        return b""
    return spr[off:off + 5 + struct.unpack_from("<H", spr, off + 3)[0]]


def replace_sprites(spr: bytes, offsets: list[int], replacements: dict[int, bytes]) -> bytes:
    """Reescribe el .spr cambiando solo los sprites de `replacements` (id -> registro nuevo).
    Los demás quedan byte a byte iguales y en el mismo orden; solo se corren los offsets."""
    order = sorted((off, sid) for sid, off in enumerate(offsets, 1) if off)
    missing = [sid for sid in replacements if not offsets[sid - 1]]
    if missing:
        raise SystemExit(f"Sprites sin datos, no se pueden reemplazar: {missing}")
    start = 6 + 4 * len(offsets)
    if order and order[0][0] != start:
        raise SystemExit("Tibia.spr con formato inesperado: los sprites no empiezan después de la tabla")
    body, new_offsets = bytearray(), [0] * len(offsets)
    for off, sid in order:
        new_offsets[sid - 1] = start + len(body)
        body += replacements.get(sid) or sprite_record(spr, offsets, sid)
    return spr[:6] + struct.pack(f"<{len(offsets)}I", *new_offsets) + bytes(body)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("things_dir", type=Path, nargs="?")
    ap.add_argument("--preset", choices=sorted(PRESETS), required=True)
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--replace", action="store_true",
                    help="si el looktype destino ya existe, rehacer sus sprites con el preset actual")
    a = ap.parse_args()
    p = PRESETS[a.preset]

    things = load_things(a.things_dir or RME_THINGS)
    dat, spr, offsets, spr_count = things["dat"], things["spr"], things["offsets"], things["spr_count"]
    if things["counts"][1] < p["target"]:
        raise SystemExit(f"El dat tiene {things['counts'][1]} looktypes; se esperaba al menos {p['target']}")
    source, target = things["outfits"][p["source"] - 1], things["outfits"][p["target"] - 1]
    _original, frames, size = build_preset(things, p)
    decoded = frames_to_sprites(frames, size)

    if a.preview:
        write_preview(a.preview, frames, scale=3 if size == 64 else 6, size=size)
        print(f"Vista previa: {a.preview}")
    if a.things_dir is None:
        return 0

    new_records = [encode_sprite(decoded[i]) for i in range(len(source["ids"]))]
    if any(target["ids"]):
        if not a.replace:
            print(f"El looktype {p['target']} ya tiene sprites; no se cambia nada "
                  f"(--replace los rehace con el preset actual).")
            return 0
        new_ids = target["ids"]
        if len(new_ids) != len(new_records) or not all(new_ids):
            raise SystemExit(f"El looktype {p['target']} no tiene la forma del base {p['source']}; no se reemplaza")
        new_dat = dat
        new_spr = replace_sprites(spr, offsets, dict(zip(new_ids, new_records)))
        if new_spr == spr:
            print(f"El looktype {p['target']} ya es igual al preset; no se cambia nada.")
            return 0
        done = f"sprites {new_ids[0]}-{new_ids[-1]} rehechos"
    else:
        new_ids = [spr_count + 1 + i for i in range(len(new_records))]
        entry = dat[source["start"]:source["sprite_pos"]] + struct.pack(f"<{len(new_ids)}H", *new_ids)
        new_dat = dat[:target["start"]] + entry + dat[target["end"]:]
        new_spr = write_spr(struct.unpack_from("<I", spr, 0)[0], offsets, spr, new_records)
        done = f"sprites {new_ids[0]}-{new_ids[-1]} agregados ({spr_count} -> {spr_count + len(new_records)})"

    check, _ = read_outfits(new_dat)
    assert check[p["target"] - 1]["ids"] == new_ids
    _c, new_offsets = read_spr(new_spr)
    assert all(decode_sprite(new_spr, new_offsets, sid) == decoded[i] for i, sid in enumerate(new_ids))

    for path, data, before in ((things["dat_path"], new_dat, dat), (things["spr_path"], new_spr, spr)):
        if data == before:
            continue
        backup = path.with_name(f"{path.name}.bak-{a.preset}")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_bytes(data)
    print(f"Looktype {p['target']} = {p['name']}; {done}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
