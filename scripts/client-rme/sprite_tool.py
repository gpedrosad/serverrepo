#!/usr/bin/env python3
"""Mirar, comparar, crear y verificar sprites de criaturas del cliente 7.6. Sin dependencias (no usa Pillow).

  sprite_tool.py looks                        looktypes libres, presets (con su archivo) y quién usa cada look
  sprite_tool.py bases [--write]              catálogo de criaturas que sirven de base, con sus colores
  sprite_tool.py new NOMBRE --base LOOK       crea presets/NOMBRE.py listo para editar (partes y paletas)
  sprite_tool.py inspect LOOK|PRESET          estructura, colores (HSV), partes y mapa en texto por cuadro
  sprite_tool.py check PRESET                 hoja + escena en un paso y cuántos píxeles cambiaron
  sprite_tool.py sheet LOOK|PRESET salida.png hoja 4 direcciones x 3 cuadros; con preset: original | nuevo
  sprite_tool.py scene PRESET salida.png      el sprite sobre un recorte real del mapa, a tamaño de juego
  sprite_tool.py verify                       Tibia.dat/.spr de RME contra git: qué looks cambiaron y que
                                              ítems, efectos y sprites viejos siguen idénticos

Los presets son los archivos de scripts/client-rme/presets/. Nada de esto escribe en Tibia.dat / Tibia.spr.
Receta completa: docs/gameplay/SPRITE_RECOLOR_GUIDE.md.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "scripts/map/kb"))
import add_recolor_look as recolor  # noqa: E402
import sprite_kit as kit  # noqa: E402
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

def next_free(things: dict, used: dict) -> int | None:
    """Primer looktype sin sprites ni monstruo/NPC, después del último custom."""
    last = max(p["target"] for p in recolor.PRESETS.values())
    return next((n for n, o in enumerate(things["outfits"], 1)
                 if n > last and not any(o["ids"]) and n not in used), None)


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
        print(f"  {target}  {p['name']:<18} preset {name:<15} base {p['source']:<4} {state}   presets/{p['file'].name}")
    print(f"\nPróximo libre sugerido: {next_free(things, used)}")
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
    h, s, v = kit.hsv(pixel)
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
    elif not preset:
        parts_of = kit.BASE_PARTS.get(look)                 # base ya estudiada: mapa por partes
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
        h, s, v = kit.hsv(color)
        tag = parts_of(color + (255,)) if parts_of else hue_char(color + (255,))
        print(f"  {color[0]:>3} {color[1]:>3} {color[2]:>3}  {count:>6}   {h:.2f}  {s:.2f}  {v:.2f}   {tag}")

    def summary(tag_of, label):
        groups: dict[str, list] = {}
        for color, count in colors.items():
            groups.setdefault(tag_of(color + (255,)), []).append((kit.hsv(color), count))
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
        return letter.upper() if kit.hsv(pixel)[2] >= 0.5 else letter

    wanted = range(12) if a.frames == "all" else [int(n) for n in a.frames.split(",")]
    for index in wanted:
        frame = frames[index]
        print(f"\nCuadro {index} (anim {index // 4}, {DIRECTIONS[index % 4]}):")
        if parts_of:
            parts = [parts_of(p) for p in frame]
            for name in letters:
                points = kit.part_points(parts, name, size)
                groups = sorted(kit.clusters(points), key=len, reverse=True)
                if not groups:
                    continue
                big = groups[0]
                cx, cy = kit.centroid(big)
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


# ---------- new ----------

def part_stats(frames: list[list], parts_of) -> list[tuple[str, int, list]]:
    """(parte, píxeles, [oscuro, medio, claro]) de cada parte, de la más grande a la más chica."""
    by_part: dict[str, Counter] = {}
    for frame in frames:
        for p in frame:
            if p[3]:
                by_part.setdefault(parts_of(p), Counter())[p[:3]] += 1
    out = []
    for name, colors in by_part.items():
        ordered = sorted(colors.elements(), key=lambda c: kit.luma(c + (255,)))
        picks = [ordered[int((len(ordered) - 1) * q)] for q in (0.05, 0.5, 0.95)]
        out.append((name, len(ordered), picks))
    return sorted(out, key=lambda t: -t[1])


def family_rules(frames: list[list], min_share: float = 0.02) -> tuple[list[tuple[str, str]], object]:
    """Reglas por familia de color para un base sin clasificador: las familias con al menos 2 % de los
    píxeles quedan como parte propia y el resto va a 'rest'. Devuelve (reglas en texto, clasificador)."""
    counts = Counter(kit.color_family(p) for frame in frames for p in frame if p[3])
    total = sum(counts.values())
    kept = [name for name, _rule in kit.FAMILIES if counts[name] >= total * min_share]
    rules = [(name, rule) for name, rule in kit.FAMILIES if name in kept]

    def part(pixel):
        if pixel[3] == 0:
            return None
        family = kit.color_family(pixel)
        return family if family in kept else "rest"
    return rules, part


PRESET_TEMPLATE = '''"""{name}: {base_name} ({base}) -> look {target}. QUÉ CAMBIA Y CUÁL ES SU RASGO PROPIO.

Creado con `sprite_tool.py new`. Receta: docs/gameplay/SPRITE_RECOLOR_GUIDE.md.
Doc del monstruo: docs/gameplay/NOMBRE.md.
"""
from sprite_kit import *  # noqa: F401,F403

{parts_block}

# Colores nuevos de cada parte, de oscuro a claro (3 a 5 colores). Una parte comentada queda igual que
# en el base. `(paleta, 0.8)` aclara y `(paleta, 1.2)` oscurece; un solo color `(r, g, b)` la pinta pareja.
# Al lado de cada parte: sus colores de hoy (oscuro, medio, claro) y cuánto ocupa del base.
palettes = {{
{palette_lines}
}}


def detail(f):
    """Rasgo propio, cuadro por cuadro. f.anim 0-2 (0 quieto), f.direction 0 norte, 1 este, 2 sur, 3 oeste.
    f.w = {size}. Pintar sobre f.px con f.set / f.fill / f.orb / f.glow / f.eyes / f.hang (sprite_kit.Frame)."""
    # Ejemplo: el grupo más grande de una parte es un objeto o la cara.
    # obj = f.biggest("{first_part}")
    # if obj:
    #     cx, cy = centroid(obj)
    #     f.orb(cx, cy, (2.6, 3.1, 2.8)[f.anim], [(255, 255, 255), (150, 240, 255), (20, 90, 190)])
    #     f.glow(cx, cy, 3, 3, (60, 190, 240))


PRESET = dict(name="{name}", source={base}, target={target}, parts=parts, palettes=palettes, detail=detail)
'''


def cmd_new(a) -> int:
    things = load(a.things)
    used = creatures_by_look()
    if not re.fullmatch(r"[a-z][a-z0-9-]*", a.name):
        raise SystemExit("El nombre va en minúsculas con guiones, ej. ash-ghoul")
    path = recolor.PRESET_DIR / (a.name.replace("-", "_") + ".py")
    if path.exists() or a.name in recolor.PRESETS:
        raise SystemExit(f"Ya existe {path.relative_to(REPO)}")
    target = a.target or next_free(things, used)
    if any(things["outfits"][target - 1]["ids"]) or target in used or target in {p["target"] for p in recolor.PRESETS.values()}:
        raise SystemExit(f"El look {target} no está libre (ver `sprite_tool.py looks`)")
    frames, size = recolor.look_frames(things, a.base)
    if a.base in kit.BASE_PARTS:
        parts_of = kit.BASE_PARTS[a.base]
        parts_block = (f"# Partes del base: clasificador ya probado ({parts_of.__name__} en sprite_kit.py).\n"
                       f"parts = BASE_PARTS[{a.base}]")
    else:
        rules, parts_of = family_rules(frames)
        lines = "\n".join(f'    ("{name}", lambda h, s, v: {rule}),' for name, rule in rules)
        parts_block = ("# Partes del base, por familia de color (h, s, v de 0 a 1). Gana la primera regla que se cumple.\n"
                       "# Es un primer corte automático: ajustar o separar partes mirando `sprite_tool.py inspect "
                       f"{a.name}`.\nparts = parts_by_rules(\n{lines}\n    (\"rest\", None),\n)")
    stats = part_stats(frames, parts_of)
    total = sum(n for _name, n, _c in stats)
    palette_lines = "\n".join(f'    # "{name}": [{", ".join(str(c) for c in picks)}],  # {100 * n / total:.0f} %'
                              for name, n, picks in stats)
    base_name = ", ".join(used.get(a.base, [])) or f"look {a.base}"
    pretty = a.name.replace("-", " ").title()
    path.write_text(PRESET_TEMPLATE.format(name=pretty, base_name=base_name, base=a.base, target=target, size=size,
                                           parts_block=parts_block, palette_lines=palette_lines,
                                           first_part=stats[-1][0] if len(stats) > 1 else stats[0][0]))
    print(f"Creado {path.relative_to(REPO)}: {pretty}, base {a.base} ({base_name}, "
          f"{'2x2' if size == 64 else '1x1'}) -> look {target}. Partes: "
          + ", ".join(f"{name} {100 * n / total:.0f} %" for name, n, _c in stats))
    print("Ya funciona tal cual (sale igual al base). Siguiente:\n"
          f"  python3 scripts/client-rme/sprite_tool.py inspect {a.name}     # partes en texto\n"
          f"  editar palettes y detail en {path.relative_to(REPO)}\n"
          f"  python3 scripts/client-rme/sprite_tool.py check {a.name}       # hoja + escena")
    return 0


# ---------- check ----------

def cmd_check(a) -> int:
    things = load(a.things)
    _look, preset = resolve(a.target)
    if preset is None:
        raise SystemExit("check necesita un preset")
    out = a.dir or Path(tempfile.gettempdir()) / "sprites"
    sheet, scene = out / f"{a.target}-hoja.png", out / f"{a.target}-escena.png"
    cmd_sheet(argparse.Namespace(things=a.things, target=a.target, out=sheet, scale=None))
    cmd_scene(argparse.Namespace(things=a.things, target=a.target, out=scene, area=a.area, at=a.at, scale=2))
    original, new, size = recolor.build_preset(things, preset)
    changed = sum(1 for fo, fn in zip(original, new) for po, pn in zip(fo, fn) if po != pn)
    opaque = sum(1 for frame in original for p in frame if p[3])
    added = sum(1 for fo, fn in zip(original, new) for po, pn in zip(fo, fn) if not po[3] and pn[3])
    print(f"Píxeles cambiados: {changed} ({100 * changed / max(1, opaque):.0f} % de la silueta); "
          f"agregados fuera de la silueta: {added}.")
    if not changed:
        print("AVISO: el sprite nuevo es igual al base (¿palettes todavía comentadas?).")
    print(f"Mirar: {sheet}  y  {scene}")
    return 0


# ---------- bases ----------

def cmd_bases(a) -> int:
    things = load(a.things)
    used = creatures_by_look()
    sources = {}
    for name, p in recolor.PRESETS.items():
        sources.setdefault(p["source"], []).append(name)
    customs = {p["target"] for p in recolor.PRESETS.values()}
    rows = []
    for n, outfit in enumerate(things["outfits"], 1):
        if len(outfit["ids"]) not in (12, 48) or not any(outfit["ids"]) or n in customs:
            continue
        frames, size = recolor.look_frames(things, n)
        counts = Counter(kit.color_family(p) for frame in frames for p in frame if p[3])
        total = sum(counts.values())
        colors = ", ".join(f"{name} {100 * c / total:.0f}" for name, c in counts.most_common() if c >= total * 0.05)
        studied = []
        if n in kit.BASE_PARTS:
            studied.append(f"`BASE_PARTS[{n}]`")
        if n in sources:
            studied.append(", ".join(f"`{s}`" for s in sources[n]))
        who = ", ".join(used.get(n, [])) or "—"
        rows.append(f"| {n} | {'2x2' if size == 64 else '1x1'} | {who} | {colors} | {'; '.join(studied)} |")
    text = BASES_HEADER + "\n".join(rows) + "\n"
    if a.write:
        BASES_DOC.write_text(text)
        print(f"{BASES_DOC.relative_to(REPO)}: {len(rows)} bases")
    else:
        print(text)
    return 0


BASES_DOC = REPO / "docs/gameplay/SPRITE_BASES.md"
BASES_HEADER = """# Bases para sprites de criaturas

Catálogo de las criaturas del cliente 7.6 que sirven de base para un preset (1x1 o 2x2, 4 direcciones,
3 cuadros), para elegir una **sin abrir imágenes ni correr `inspect` en muchas**. Buscar por nombre o por
color con grep. Generado con `python3 scripts/client-rme/sprite_tool.py bases --write`: no editar a mano,
volver a generarlo después de crear un look o un monstruo nuevo.

- **Colores:** familias con al menos 5 % de los píxeles, en %. `dark` es el contorno y las sombras casi
  negras; `gray` los grises sin color; `orange` incluye la piel y los marrones.
- **Estudiada:** ya tiene clasificador de partes probado (`BASE_PARTS[n]` en `sprite_kit.py`) o algún
  preset que la usa. Conviene empezar por estas.

Receta: [`SPRITE_RECOLOR_GUIDE.md`](SPRITE_RECOLOR_GUIDE.md).

| Look | Forma | Monstruos y NPC que la usan | Colores (%) | Estudiada |
|-----:|-------|-----------------------------|-------------|-----------|
"""


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

    s = sub.add_parser("new", help="crear presets/NOMBRE.py listo para editar, a partir de un base")
    s.add_argument("name", help="nombre del preset en minúsculas con guiones, ej. ash-ghoul")
    s.add_argument("--base", type=int, required=True, help="looktype base (elegir con `bases`)")
    s.add_argument("--target", type=int, help="looktype destino (por omisión, el próximo libre)")
    s.set_defaults(run=cmd_new)

    s = sub.add_parser("check", help="hoja + escena de un preset en un paso, con cuántos píxeles cambió")
    s.add_argument("target", help="nombre del preset")
    s.add_argument("--dir", type=Path, help="carpeta de salida (por omisión, la temporal del sistema /sprites)")
    s.add_argument("--area", help="como en scene")
    s.add_argument("--at", help="como en scene")
    s.set_defaults(run=cmd_check)

    s = sub.add_parser("bases", help="catálogo de criaturas que sirven de base, con sus colores")
    s.add_argument("--write", action="store_true", help="escribir docs/gameplay/SPRITE_BASES.md")
    s.set_defaults(run=cmd_bases)

    s = sub.add_parser("verify", help="integridad de Tibia.dat/.spr contra git")
    s.add_argument("--base", default="HEAD", help="commit o rama de referencia (por omisión HEAD)")
    s.add_argument("--expect", help="looks que debían cambiar, ej. '235' ('' = ninguno)")
    s.set_defaults(run=cmd_verify)

    a = ap.parse_args()
    return a.run(a)


if __name__ == "__main__":
    sys.exit(main())
