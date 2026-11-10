#!/usr/bin/env python3
"""Mirar, comparar y verificar sprites de criaturas del cliente 7.6. Sin dependencias (no usa Pillow).

  sprite_tool.py looks                        looktypes libres, custom ya usados y quién usa cada look
  sprite_tool.py inspect LOOK|PRESET          estructura, colores (HSV), partes y mapa en texto por cuadro
  sprite_tool.py sheet LOOK|PRESET salida.png hoja 4 direcciones x 3 cuadros; con preset: original | nuevo
  sprite_tool.py scene PRESET salida.png      el sprite sobre un recorte real del mapa, a tamaño de juego
  sprite_tool.py verify                       Tibia.dat/.spr de RME contra git: qué looks cambiaron y que
                                              ítems, efectos y sprites viejos siguen idénticos

Los presets son los de add_recolor_look.py. Nada de esto escribe en Tibia.dat / Tibia.spr.
Receta completa: docs/gameplay/SPRITE_RECOLOR_GUIDE.md.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "scripts/map/kb"))
import add_recolor_look as recolor  # noqa: E402
from add_black_dragon_look import read_outfits, read_spr  # noqa: E402

DATA_DIR = REPO / "server/YurOTS/ots/data"
DIRECTIONS = ("norte", "este", "sur", "oeste")
SHEET_BG = (52, 72, 78, 255)
HOLD_AREA = (178, 145, 197, 154, 8)                      # bodega del naufragio
HOLD_SPOTS = "182,148,s;185,149,e;188,148,w;184,151,n;190,150,s,orig"
CREATURE_OFFSET = 8                                       # el cliente dibuja las criaturas 8 px arriba a la izquierda


# ---------- datos ----------

def load(things_dir: Path | None = None) -> dict:
    return recolor.load_things(things_dir or recolor.RME_THINGS)


def resolve(target: str) -> tuple[int, dict | None]:
    """'9' -> (9, None); 'tide-priest' -> (looktype base, preset)."""
    if target.isdigit():
        return int(target), None
    if target not in recolor.PRESETS:
        raise SystemExit(f"'{target}' no es un looktype ni un preset. Presets: {', '.join(sorted(recolor.PRESETS))}")
    preset = recolor.PRESETS[target]
    return preset["source"], preset


def creatures_by_look() -> dict[int, list[str]]:
    """Looktype -> monstruos y NPC del servidor que lo usan."""
    found: dict[int, list[str]] = {}
    for folder, tag in (("monster", "monster"), ("npc", "npc")):
        for path in sorted((DATA_DIR / folder).glob("*.xml")):
            text = path.read_text(errors="replace")
            look = re.search(r'<look\s+type="(\d+)"', text)
            name = re.search(rf'<{tag}\s+name="([^"]+)"', text)
            if look and name:
                found.setdefault(int(look.group(1)), []).append(name.group(1) + (" (NPC)" if tag == "npc" else ""))
    return found


def ranges(numbers: list[int]) -> str:
    out, start, prev = [], None, None
    for n in sorted(numbers) + [None]:
        if start is None:
            start = prev = n
        elif n is not None and n == prev + 1:
            prev = n
        else:
            out.append(str(start) if start == prev else f"{start}-{prev}")
            start = prev = n
    return ", ".join(out)


# ---------- imagen ----------

class Canvas:
    def __init__(self, width: int, height: int, color=SHEET_BG, rgba: bytearray | None = None):
        self.w, self.h = width, height
        self.px = rgba if rgba is not None else bytearray(bytes(color) * (width * height))

    def blit(self, frame: list, size: int, left: int, top: int) -> None:
        for i, p in enumerate(frame):
            if p[3]:
                x, y = left + i % size, top + i // size
                if 0 <= x < self.w and 0 <= y < self.h:
                    o = (y * self.w + x) * 4
                    self.px[o:o + 4] = bytes(p[:3]) + b"\xff"

    def save(self, path: Path, scale: int) -> None:
        from mapdata import png_bytes
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png_bytes(self.w, self.h, bytes(self.px), scale=scale))


# ---------- looks ----------

def cmd_looks(a) -> int:
    things = load(a.things)
    used = creatures_by_look()
    presets = {p["target"]: (name, p) for name, p in recolor.PRESETS.items()}
    free = [n for n, o in enumerate(things["outfits"], 1) if not any(o["ids"])]
    free_unused = [n for n in free if n not in used]
    print(f"Looktypes en el dat: {things['counts'][1]} (el protocolo 7.6 admite hasta 255). Sprites: {things['spr_count']}.")
    print(f"Libres (sin sprites y sin monstruo ni NPC que los use): {ranges(free_unused)}")
    taken = sorted(n for n in free if n in used)
    if taken:
        print(f"Sin sprites pero usados por un monstruo o NPC (se ven invisibles): {ranges(taken)}")
    print("\nCustom por preset:")
    for target in sorted(presets):
        name, p = presets[target]
        state = "aplicado" if any(things["outfits"][target - 1]["ids"]) else "SIN aplicar en este dat"
        print(f"  {target}  {p['name']:<16} preset {name:<15} base {p['source']:<4} {state}")
    nxt = next((n for n in free_unused if n > max(presets)), None)
    print(f"\nPróximo libre sugerido: {nxt}")
    if a.all:
        print("\nLook  forma  sprites  monstruos y NPC que lo usan")
        for n, o in enumerate(things["outfits"], 1):
            if any(o["ids"]):
                shape = {12: "1x1", 48: "2x2"}.get(len(o["ids"]), "otra")
                print(f"  {n:<4} {shape:<5} {len(o['ids']):<7}  {', '.join(used.get(n, []))}")
    return 0


# ---------- inspect ----------

HUES = ((0.04, "r"), (0.11, "n"), (0.20, "y"), (0.45, "g"), (0.55, "c"), (0.72, "b"), (0.85, "v"), (0.95, "m"), (1.01, "r"))
HUE_LEGEND = ("Letras por color: r rojo, n naranja/piel, y amarillo, g verde, c celeste, b azul, v violeta, m magenta; "
              "MAYÚSCULA = claro (v >= 0.5). Grises (s < 0.18): # casi negro, + medio, o claro. '.' transparente.")


def hue_char(pixel) -> str:
    h, s, v = recolor.hsv(pixel)
    if v < 0.13:
        return "#"
    if s < 0.18:
        return "#" if v < 0.3 else ("+" if v < 0.6 else "o")
    letter = next(c for limit, c in HUES if h < limit)
    return letter.upper() if v >= 0.5 else letter


def part_letters(names: list[str]) -> dict[str, str]:
    letters: dict[str, str] = {}
    for name in names:
        letters[name] = next(c for c in name + "abcdefghijklmnopqrstuvwxyz" if c.isalpha() and c not in letters.values())
    return letters


def text_map(frame: list, size: int, char_of) -> list[str]:
    points = [(i % size, i // size) for i, p in enumerate(frame) if p[3]]
    if not points:
        return ["  (cuadro vacío)"]
    x0, x1 = min(x for x, _ in points), max(x for x, _ in points)
    y0, y1 = min(y for _, y in points), max(y for _, y in points)
    lines = ["     " + "".join(str(x // 10) if x % 10 == 0 else " " for x in range(x0, x1 + 1)),
             "     " + "".join(str(x % 10) for x in range(x0, x1 + 1))]
    for y in range(y0, y1 + 1):
        row = "".join(char_of(frame[y * size + x]) if frame[y * size + x][3] else "." for x in range(x0, x1 + 1))
        lines.append(f"  {y:>2} {row}")
    return lines


def cmd_inspect(a) -> int:
    things = load(a.things)
    look, preset = resolve(a.target)
    parts_of = None
    if a.parts:
        parts_of = recolor.PRESETS[a.parts].get("parts")
        if parts_of is None:
            raise SystemExit(f"El preset {a.parts} no declara 'parts'")
    elif preset and not a.new:
        parts_of = preset.get("parts")
    frames, size = recolor.look_frames(things, look)
    if a.new:
        if preset is None:
            raise SystemExit("--new necesita un preset, no un número de look")
        _orig, frames, size = recolor.build_preset(things, preset)
        parts_of = None
    ids = things["outfits"][look - 1]["ids"]
    title = f"Look {look}" + (f" (base del preset {a.target})" if preset else "")
    if a.new:
        title = f"Preset {a.target}: sprite nuevo (look {preset['target']})"
    print(f"{title}: {'2x2' if size == 64 else '1x1'}, cuadros de {size}x{size} px, {len(ids)} sprites "
          f"(ids {min(i for i in ids if i)}-{max(ids)}).")
    print("Cuadro = anim * 4 + dirección; dirección 0 norte (de espaldas), 1 este, 2 sur (de frente), 3 oeste.")

    colors: Counter = Counter()
    for frame in frames:
        colors.update(p[:3] for p in frame if p[3])
    total = sum(colors.values())
    print(f"\nColores: {len(colors)} distintos, {total} píxeles en los 12 cuadros.")
    if a.colors:
        print(f"Los {min(a.colors, len(colors))} más usados:")
        print("  r   g   b    píxeles    h     s     v   " + ("parte" if parts_of else "letra"))
    for color, count in colors.most_common(a.colors):
        h, s, v = recolor.hsv(color)
        tag = parts_of(color + (255,)) if parts_of else hue_char(color + (255,))
        print(f"  {color[0]:>3} {color[1]:>3} {color[2]:>3}  {count:>6}   {h:.2f}  {s:.2f}  {v:.2f}   {tag}")

    def summary(tag_of, label):
        groups: dict[str, list] = {}
        for color, count in colors.items():
            groups.setdefault(tag_of(color + (255,)), []).append((recolor.hsv(color), count))
        print(f"\nResumen por {label} (rango de tono h, saturación s y brillo v de sus píxeles):")
        for tag, items in sorted(groups.items(), key=lambda kv: -sum(n for _c, n in kv[1])):
            pixels = sum(n for _c, n in items)
            spans = "  ".join(f"{name} {min(c[k] for c, _n in items):.2f}-{max(c[k] for c, _n in items):.2f}"
                              for k, name in enumerate("hsv"))
            print(f"  {tag:<6} {pixels:>5} px {100 * pixels / total:>5.1f} %   {spans}")

    summary(hue_char, "letra de color")
    if parts_of:
        summary(parts_of, "parte")

    letters = None
    if parts_of:
        names = sorted({parts_of(c + (255,)) for c in colors})
        letters = part_letters(names)
        print("\nLetras por parte: " + ", ".join(f"{letter} = {name}" for name, letter in letters.items())
              + "; MAYÚSCULA = claro (v >= 0.5). '.' transparente.")
    else:
        print("\n" + HUE_LEGEND)

    def char_of(pixel):
        if letters is None:
            return hue_char(pixel)
        letter = letters[parts_of(pixel)]
        return letter.upper() if recolor.hsv(pixel)[2] >= 0.5 else letter

    wanted = range(12) if a.frames == "all" else [int(n) for n in a.frames.split(",")]
    for index in wanted:
        frame = frames[index]
        print(f"\nCuadro {index} (anim {index // 4}, {DIRECTIONS[index % 4]}):")
        if parts_of:
            parts = [parts_of(p) for p in frame]
            for name in letters:
                points = recolor.part_points(parts, name, size)
                groups = sorted(recolor._clusters(points), key=len, reverse=True)
                if not groups:
                    continue
                big = groups[0]
                cx, cy = recolor.centroid(big)
                xs, ys = [x for x, _ in big], [y for _, y in big]
                print(f"  {name}: {len(points)} px en {len(groups)} grupo(s); el mayor tiene {len(big)} px, "
                      f"x {min(xs)}-{max(xs)}, y {min(ys)}-{max(ys)}, centro ({cx:.1f}, {cy:.1f})")
        print("\n".join(text_map(frame, size, char_of)))
    return 0


# ---------- sheet ----------

def cmd_sheet(a) -> int:
    things = load(a.things)
    look, preset = resolve(a.target)
    if preset:
        left, right, size = recolor.build_preset(things, preset)
        blocks = [left, right]
    else:
        frames, size = recolor.look_frames(things, look)
        blocks = [frames]
    gap = 8
    canvas = Canvas(len(blocks) * 4 * size + (len(blocks) - 1) * gap, 3 * size)
    for b, frames in enumerate(blocks):
        for index, frame in enumerate(frames):
            canvas.blit(frame, size, b * (4 * size + gap) + (index % 4) * size, (index // 4) * size)
    scale = a.scale or (6 if size == 32 else 3)
    canvas.save(a.out, scale)
    what = "izquierda el original, derecha el nuevo" if preset else f"look {look}"
    print(f"{a.out}: {what}; columnas = norte, este, sur, oeste; filas = 3 cuadros de animación; x{scale}.")
    return 0


# ---------- scene ----------

def cmd_scene(a) -> int:
    from mapdata import Renderer, load_tiles
    things = load(a.things)
    _look, preset = resolve(a.target)
    if preset is None:
        raise SystemExit("scene necesita un preset")
    original, new, size = recolor.build_preset(things, preset)
    x1, y1, x2, y2, z = (int(n) for n in a.area.split(",")) if a.area else HOLD_AREA
    spots = a.at or (HOLD_SPOTS if not a.area else
                     ";".join(f"{x1 + (x2 - x1) * k // 5},{(y1 + y2) // 2},{'sewn'[k - 1]}" for k in range(1, 5)))
    width, height, rgba = Renderer().area(load_tiles(), x1, y1, x2, y2, z)
    canvas = Canvas(width, height, rgba=rgba)
    for spot in spots.split(";"):
        fields = [f.strip() for f in spot.split(",")]
        x, y, direction = int(fields[0]), int(fields[1]), "nesw".index(fields[2].lower())
        which = fields[3] if len(fields) > 3 else "new"
        anim = int(fields[4]) if len(fields) > 4 else 0
        if which == "new":
            frames, side = new, size
        elif which == "orig":
            frames, side = original, size
        else:
            frames, side = recolor.look_frames(things, int(which))
        canvas.blit(frames[anim * 4 + direction], side,
                    (x - x1 + 1) * 32 - side - CREATURE_OFFSET, (y - y1 + 1) * 32 - side - CREATURE_OFFSET)
    canvas.save(a.out, a.scale)
    print(f"{a.out}: zona {x1},{y1} a {x2},{y2} piso {z}, x{a.scale}. Criaturas: {spots}")
    return 0


# ---------- verify ----------

def cmd_verify(a) -> int:
    things_dir = (a.things or recolor.RME_THINGS).resolve()
    new = load(things_dir)
    rel = things_dir.relative_to(REPO)
    try:
        old_dat = subprocess.run(["git", "-C", str(REPO), "show", f"{a.base}:{rel}/Tibia.dat"], capture_output=True, check=True).stdout
        old_spr = subprocess.run(["git", "-C", str(REPO), "show", f"{a.base}:{rel}/Tibia.spr"], capture_output=True, check=True).stdout
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"No se pudo leer {rel} en {a.base}: {error.stderr.decode().strip()}")
    old_outfits, old_counts = read_outfits(old_dat)
    old_count, old_offsets = read_spr(old_spr)
    failures = []

    def check(ok: bool, text: str) -> None:
        print(("  OK     " if ok else "  FALLA  ") + text)
        if not ok:
            failures.append(text)

    print(f"{rel} contra {a.base}:")
    check(old_counts == new["counts"], f"cantidades de ítems / looktypes / efectos / proyectiles: {new['counts']}")
    check(old_dat[:old_outfits[0]["start"]] == new["dat"][:new["outfits"][0]["start"]], "ítems idénticos byte a byte")
    check(old_dat[old_outfits[-1]["end"]:] == new["dat"][new["outfits"][-1]["end"]:], "efectos y proyectiles idénticos byte a byte")

    def look_bytes(dat, outfit, spr, offsets):
        return (dat[outfit["start"]:outfit["sprite_pos"]],
                [recolor.sprite_record(spr, offsets, sid) for sid in outfit["ids"]])

    changed, touched = [], set()
    for n, (before, after) in enumerate(zip(old_outfits, new["outfits"]), 1):
        if look_bytes(old_dat, before, old_spr, old_offsets) != look_bytes(new["dat"], after, new["spr"], new["offsets"]):
            kind = "nuevo" if not any(before["ids"]) else ("borrado" if not any(after["ids"]) else "editado")
            changed.append(n)
            touched.update(before["ids"])
            ids = [i for i in after["ids"] if i]
            print(f"  CAMBIO look {n}: {kind}" + (f", sprites {min(ids)}-{max(ids)}" if ids else ""))
    if not changed:
        print("  Ningún looktype cambió.")
    if a.expect is not None:
        expected = sorted(int(n) for n in a.expect.split(",") if n)
        check(changed == expected, f"cambiaron solo los looks esperados {expected} (cambiaron {changed})")

    different = [sid for sid in range(1, old_count + 1) if sid not in touched
                 and recolor.sprite_record(old_spr, old_offsets, sid) != recolor.sprite_record(new["spr"], new["offsets"], sid)]
    check(not different, f"los {old_count - len(touched - {0})} sprites viejos de otros looks e ítems siguen idénticos"
          + (f" (distintos: {different[:10]}...)" if different else ""))
    check(new["spr_count"] >= old_count, f"sprites: {old_count} -> {new['spr_count']}")

    for name, p in recolor.PRESETS.items():
        target = new["outfits"][p["target"] - 1]
        if not any(target["ids"]):
            print(f"  --     preset {name}: look {p['target']} sin aplicar")
            continue
        _orig, frames, size = recolor.build_preset(new, p)
        sprites = recolor.frames_to_sprites(frames, size)
        same = len(sprites) == len(target["ids"]) and all(
            recolor.decode_sprite(new["spr"], new["offsets"], sid) == sprites[i] for i, sid in enumerate(target["ids"]))
        check(same, f"preset {name} reproduce el look {p['target']}" + ("" if same else " (falta --replace o el preset cambió)"))

    backups = sorted(path.name for path in things_dir.glob("*.bak-*"))
    check(not backups, "sin respaldos .bak-* por borrar" + (f": {', '.join(backups)}" if backups else ""))
    print("\nTODO BIEN" if not failures else f"\n{len(failures)} PROBLEMA(S)")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--things", type=Path, help="carpeta con Tibia.dat y Tibia.spr (por omisión, la de RME)")
    sub = ap.add_subparsers(dest="command", required=True)

    s = sub.add_parser("looks", help="looktypes libres y custom")
    s.add_argument("--all", action="store_true", help="lista también cada look con sprites y qué monstruos lo usan")
    s.set_defaults(run=cmd_looks)

    s = sub.add_parser("inspect", help="estructura, colores, partes y mapa en texto")
    s.add_argument("target", help="número de looktype o nombre de preset (muestra su criatura base)")
    s.add_argument("--frames", default="0,1,2,3", help="cuadros a mostrar: lista '2,6,10' o 'all' (por omisión, anim 0)")
    s.add_argument("--colors", type=int, default=12, help="cuántos colores listar")
    s.add_argument("--parts", choices=sorted(recolor.PRESETS), help="usar el clasificador de partes de este preset")
    s.add_argument("--new", action="store_true", help="con un preset: mostrar el sprite nuevo en vez del base")
    s.set_defaults(run=cmd_inspect)

    s = sub.add_parser("sheet", help="hoja ampliada; con preset, original | nuevo")
    s.add_argument("target")
    s.add_argument("out", type=Path)
    s.add_argument("--scale", type=int)
    s.set_defaults(run=cmd_sheet)

    s = sub.add_parser("scene", help="el sprite sobre el mapa real")
    s.add_argument("target")
    s.add_argument("out", type=Path)
    s.add_argument("--area", help="x1,y1,x2,y2,z en casillas (por omisión, la bodega del naufragio)")
    s.add_argument("--at", help="criaturas 'x,y,dir[,cual[,anim]]' separadas por ';'. dir = n/e/s/w; "
                                "cual = new (por omisión), orig o un número de looktype")
    s.add_argument("--scale", type=int, default=2)
    s.set_defaults(run=cmd_scene)

    s = sub.add_parser("verify", help="integridad de Tibia.dat/.spr contra git")
    s.add_argument("--base", default="HEAD", help="commit o rama de referencia (por omisión HEAD)")
    s.add_argument("--expect", help="looks que debían cambiar, ej. '235' ('' = ninguno)")
    s.set_defaults(run=cmd_verify)

    a = ap.parse_args()
    return a.run(a)


if __name__ == "__main__":
    sys.exit(main())
