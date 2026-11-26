#!/usr/bin/env python3
"""Arma una zona desde su ficha: decisiones chicas con jev, varias semillas, lint, vista previa y escritura.

  python3.11 scripts/map/mapkit/build.py scripts/map/zones/claro-de-los-lobos.json --preview /tmp/z.png
  python3.11 scripts/map/mapkit/build.py scripts/map/zones/claro-de-los-lobos.json --write
  opciones: --seeds N  --seed S (fija)  --no-jev  --redecide (vuelve a preguntar a jev)

Qué decide jev (cada respuesta se valida y se guarda en zones/<zona>.decisions.json; sin clave usa la ficha):
  stages   qué monstruos del `monster_pool` van en cada etapa, de a cuántos, spawntime y separación
  glades   qué tiene cada claro (menú `props` del tema)
  sign     el texto del cartel de la entrada
  tune     si ninguna semilla da la densidad pedida, nuevas separaciones (y se vuelve a probar)
  pick     cuál de las 3 mejores semillas (por puntaje de lint) queda, mirando su mapa en ASCII

Guía: docs/items-and-map/MAPAS.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mapkit as K  # noqa: E402
from mapkit import cave, island, lint as L  # noqa: E402
from mapkit.jev import Jev  # noqa: E402

RECIPES = {"island": island.build, "cave": cave.build}
SRC = "scripts/map/mapkit/build.py"


def monster_facts(names):
    out = {}
    for n in names:
        f = K.REPO / f"server/YurOTS/ots/data/monster/{n.lower()}.xml"
        t = f.read_text(encoding="latin-1") if f.exists() else ""
        hp = re.search(r'<health now="(\d+)"', t)
        xp = re.search(r'experience="(\d+)"', t)
        out[n] = {"hp": int(hp.group(1)) if hp else None, "exp": int(xp.group(1)) if xp else None}
    return out


def ask_stages(jev, spec, known):
    pool = [n for n in spec["monster_pool"] if n in known]
    facts = monster_facts(pool)
    n = len(spec["stages"])
    prompt = (f"Hunting zone '{spec['title']}' for player levels {spec['levels']}, a forest trail on an island. "
              f"Monsters available (hp, exp): {json.dumps(facts)}. Design exactly {n} stages from the entrance "
              "(easiest) to the far end (hardest). Each stage: monsters (1-2 names from the list), per (monsters "
              "per spawn: 1 or 2; start with 1, end with 2), spawntime (seconds, 80-180, harder = slower), "
              "gap (tiles between spawn centers, 9-13). Reply {\"stages\": [{\"monsters\": [..], \"per\": 1, "
              "\"spawntime\": 90, \"gap\": 11}, ...]}")

    def check(ans):
        st = ans["stages"]
        if len(st) != n:
            raise ValueError("cantidad de etapas")
        out = []
        for s in st:
            ms = [m for m in s["monsters"] if m in pool]
            if not ms or len(ms) != len(s["monsters"]) or len(ms) > 2:
                raise ValueError(f"monstruos {s['monsters']}")
            per, sp, gap = int(s["per"]), int(s["spawntime"]), int(s["gap"])
            if per not in (1, 2) or not 80 <= sp <= 180 or not 9 <= gap <= 13:
                raise ValueError("números fuera de rango")
            out.append({"monsters": ms, "per": per, "spawntime": sp, "gap": gap})
        return out
    return jev.decide("stages", prompt, check, spec["stages"])


def ask_glades(jev, spec, theme):
    menu = {k: v["about"] for k, v in theme["props"].items()}
    gl = [{"index": i, "where": g.get("role", "glade"), "along_trail": g.get("at", 0)}
          for i, g in enumerate(spec["glades"]) if g.get("role") not in ("harbor", "portal")]
    prompt = (f"Zone '{spec['title']}' ({theme['about']}). Monsters: {', '.join(spec['monster_pool'])}. "
              f"Choose a decoration kind for each glade along the trail (0 = entrance, 1 = far end). "
              f"Kinds: {json.dumps(menu)}. Make it tell a story from the entrance to the end; no two neighbouring "
              "glades with the same kind. Reply {\"glades\": {\"<index>\": \"<kind>\", ...}}")
    want = {str(g["index"]) for g in gl}

    def check(ans):
        g = {str(k): v for k, v in ans["glades"].items()}
        if set(g) != want or any(v not in menu for v in g.values()):
            raise ValueError("claros o tipos inválidos")
        return g
    kinds = list(menu)
    fallback = {str(g["index"]): kinds[i % len(kinds)] for i, g in enumerate(gl)}
    return jev.decide("glades", prompt + f"\nGlades: {json.dumps(gl)}", check, fallback)


def ask_sign(jev, spec, stages):
    name = spec.get("game_name", spec["title"])
    prompt = (f"Write the text of the wooden sign at the entrance of '{name}' (English, old-school "
              f"Tibia tone). Levels {spec['levels']}. Stages: {json.dumps([s['monsters'] for s in stages])}. "
              f"First line: {name.upper()}. Max 4 lines, max 38 characters per line, plain ASCII. "
              "Reply {\"lines\": [\"...\"]}")

    def check(ans):
        lines = [str(x) for x in ans["lines"]]
        if not 2 <= len(lines) <= 4 or any(len(x) > 38 or not x.isascii() or '"' in x for x in lines):
            raise ValueError("cartel fuera de medida")
        return "\n".join(lines)
    return jev.decide("sign", prompt, check, spec["sign"])


def ask_tune(jev, spec, stages, metrics):
    lo, hi = spec.get("density", [30, 45])
    prompt = (f"A hunting zone has {metrics['walk']} walkable tiles and {metrics['monsters']} monsters: "
              f"{metrics['density']} tiles per monster, but the target is {lo}-{hi}. Stages (gap = min tiles "
              f"between spawn centers; bigger gap = fewer monsters): {json.dumps(stages)}. Return new integer "
              "gaps (9-14), one per stage, to land in the target. Reply {\"gaps\": [..]}")

    def check(ans):
        g = [int(x) for x in ans["gaps"]]
        if len(g) != len(stages) or not all(9 <= x <= 14 for x in g):
            raise ValueError("separaciones inválidas")
        return [dict(s, gap=x) for s, x in zip(stages, g)]
    step = 1 if metrics["density"] < lo else -1
    fallback = [dict(s, gap=max(9, min(14, s["gap"] + step))) for s in stages]
    return jev.decide(f"tune-{metrics['density']}", prompt, check, fallback)


def ascii_map(plan, spec, scale=2):
    x0, y0, x1, y1 = spec.get("land", spec["box"])
    mons = {p for _c, _z, ms in plan["spawns"] for _n, p, _t in ms}
    rank = "~,#.=*MH"

    def ch(c):
        if c == plan["info"]["landing"]:
            return "H"
        if c in mons:
            return "M"
        if c in plan["water"]:
            return "~"
        if c in plan["shore"]:
            return ","
        if c not in plan["walk"]:
            return "#"
        if len(plan["tiles"][c]) > 1:
            return "*"
        return "=" if c in plan["trail"] else "."
    rows = []
    for y in range(y0, y1 + 1, scale):
        row = ""
        for x in range(x0, x1 + 1, scale):
            cs = [ch((x + a, y + b)) for a in range(scale) for b in range(scale)]
            row += max(cs, key=rank.index)
        rows.append(row.rstrip("~") or "~")
    return "\n".join(rows)


def ask_pick(jev, spec, finalists):
    legend = "~ water, ',' coast, # forest, . grass walk, = dirt trail, * decoration, M monster, H boat landing"
    body = "\n\n".join(f"OPTION {i} metrics {json.dumps({k: m[k] for k in ('walk', 'monsters', 'density', 'path', 'narrow', 'straight_coast', 'tree_cover', 'score')})}\n{ascii_map(p, spec)}"
                       for i, (p, m) in enumerate(finalists))
    prompt = (f"Pick the best looking and best playing layout for '{spec['title']}' (2x downsampled, {legend}). "
              "Prefer: organic coastline, varied trail width, monsters spread evenly along the trail, no long "
              f"straight edges, glades that read as places.\n\n{body}\n\nReply {{\"choice\": <index>, \"why\": \"short\"}}")

    def check(ans):
        i = int(ans["choice"])
        if not 0 <= i < len(finalists):
            raise ValueError("índice")
        return i
    seeds = "-".join(str(p["seed"]) for p, _m in finalists)
    return jev.decide(f"pick-{seeds}", prompt, check, 0)


def run_seeds(spec, theme, seeds, decisions, existing, otb, size):
    out = []
    for s in seeds:
        try:
            plan = RECIPES[spec["recipe"]](spec, theme, s, decisions, otb)
        except RuntimeError as e:
            print(f"  semilla {s}: no sale ({e})")
            continue
        m = L.lint(plan, spec, theme, existing, otb, size)
        flag = "OK " if not m["errors"] else "ERR"
        print(f"  semilla {s:3d} {flag} puntaje {m['score']:5.1f}  caminable {m['walk']:4d}  monstruos {m['monsters']:3d}"
              f"  densidad {m['density']:5.1f}  recorrido {m['path']:3d}  angosto {m['narrow']:4.1f}%"
              f"  costa recta {m['straight_coast']:4.1f}%  árboles {m['tree_cover']:4.1f}%"
              + (f"  errores {m['errors']} {m['examples']}" if m["errors"] else ""))
        out.append((plan, m))
    return out


def write_zone(spec, theme, plan, m, sign_text):
    z = spec["z"]
    info = plan["info"]
    cells = {(x, y, z): ids for (x, y), ids in plan["tiles"].items()}
    if plan.get("ceiling"):
        cells.update({(x, y, z - 1): ids for (x, y), ids in plan["ceiling"].items()})
    manifest = K.WORLD / spec["manifest"]
    key = spec["name"].upper().replace("-", "_")
    report = {"spec": f"scripts/map/zones/{spec['name']}.json", "seed": plan["seed"],
              "entry": [*info["landing"], z],
              "npc": [*info["npc"], z] if info["npc"] else None,
              "sign": [*info["sign"], z] if info["sign"] else None,
              "return": [*info["return"], z] if info.get("return") else None,
              **{k: m[k] for k in ("walk", "monsters", "spawns", "density", "path", "score")}}
    filler = [theme["filler"]] if "filler" in theme else [theme["water"]]
    changed = K.write_cells(cells, manifest, filler, spec["name"], report, dry_run=False,
                            extra_files=(K.SPAWNS, K.READABLES, K.NPCS, K.BOAT))
    # spawns, cartel, Nimral y destino del barco (bloques con dueño; sacan lo viejo del generador anterior)
    old_keys = spec.get("legacy_blocks", {})
    sp = K.SPAWNS.read_text(encoding="latin-1")
    sp = K.xml_block(sp, old_keys.get("spawns", f"{key}_SPAWNS"), K.spawn_xml(plan["spawns"]), "</spawns>", SRC)
    K.SPAWNS.write_text(sp, encoding="latin-1")
    rd = K.READABLES.read_text(encoding="latin-1")
    rd = K.xml_block(rd, old_keys.get("signs", f"{key}_SIGNS"), K.readable_line(*info["sign"], z, sign_text),
                     "</readables>", SRC)
    K.READABLES.write_text(rd, encoding="latin-1")
    h = spec.get("harbor")
    if h:
        npc = K.NPCS.read_text(encoding="latin-1")
        line = f'<npc name="{h["npc"]}" x="{info["npc"][0]}" y="{info["npc"][1]}" z="{z}" dir="2"/>'
        npc = K.xml_block(npc, f"{key}_NPC", "\t" + line, "</npclist>", SRC)
        K.NPCS.write_text(npc, encoding="latin-1")
        t = h["travel"]
        boat = K.BOAT.read_text(encoding="utf-8")
        keys = ", ".join(f"'{k}'" for k in t["keys"])
        entry = (f"\t{{keys = {{{keys}}}, price = {t['price']}, dest = {{{info['landing'][0]}, {info['landing'][1]}, {z}}}, "
                 f"name = '{t['name']}'}}, -- {SRC} ({spec['name']})")
        pat = re.compile(rf"^\t\{{keys = .*name = '{re.escape(t['name'])}'\}},.*$", re.M)
        if pat.search(boat):
            boat = pat.sub(lambda _: entry, boat, count=1)
        else:
            boat = boat.replace("\t{keys = {'city', 'the city'}", entry + "\n\t{keys = {'city', 'the city'}", 1)
            if entry not in boat:
                raise SystemExit("no encontré dónde agregar el destino en boat.lua")
        K.BOAT.write_text(boat, encoding="utf-8")
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--seeds", type=int)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--no-jev", action="store_true")
    ap.add_argument("--redecide", action="store_true")
    a = ap.parse_args()

    spec = json.loads(a.spec.read_text())
    theme = K.load_theme(spec["theme"])
    otb = K.Otb()
    size = island._sizes()
    known = K.known_monsters()
    jev = Jev(a.spec.with_suffix(".decisions.json"), enabled=not a.no_jev, redecide=a.redecide)
    existing = {p: v for p, v in K.load_tiles().items() if p[2] == spec["z"]}
    bx = K.box_cells(spec["box"])
    manifest = K.WORLD / spec["manifest"]
    owned = set(json.loads(manifest.read_text())["cells"]) if manifest.exists() else set()
    existing = {p: v for p, v in existing.items() if (p[0], p[1]) not in bx or ",".join(map(str, p)) not in owned}

    print(f"== {spec['title']} ({spec['recipe']}, tema {spec['theme']})")
    decisions = {"stages": ask_stages(jev, spec, known), "glades": ask_glades(jev, spec, theme)}
    for st in decisions["stages"]:
        bad = [n for n in st["monsters"] if n not in known]
        if bad:
            raise SystemExit(f"monstruo inexistente: {bad}")
    seeds = [a.seed] if a.seed is not None else list(range(1, (a.seeds or spec.get("seeds", 8)) + 1))
    results = run_seeds(spec, theme, seeds, decisions, existing, otb, size)
    lo, hi = spec.get("density", [30, 45])
    good = [r for r in results if not r[1]["errors"]]
    for _ in range(2):
        if not good or any(lo <= m["density"] <= hi for _p, m in good):
            break
        best = max(good, key=lambda r: r[1]["score"])[1]
        decisions["stages"] = ask_tune(jev, spec, decisions["stages"], best)
        print("  -> nuevas separaciones:", [s["gap"] for s in decisions["stages"]])
        results = run_seeds(spec, theme, seeds, decisions, existing, otb, size)
        good = [r for r in results if not r[1]["errors"]]
    if not good:
        print("ninguna semilla pasa el lint: no se escribe nada")
        print(jev.summary())
        return 1
    good.sort(key=lambda r: -r[1]["score"])
    finalists = good[:3]
    pick = ask_pick(jev, spec, finalists) if len(finalists) > 1 else 0
    plan, m = finalists[pick]
    sign = ask_sign(jev, spec, decisions["stages"])
    print(f"elegida: semilla {plan['seed']} (puntaje {m['score']}), claros {plan['info']['props']}")
    print(f"llegada {plan['info']['landing']}, {spec.get('harbor', {}).get('npc', '-')} {plan['info']['npc']}, "
          f"cartel {plan['info']['sign']}, vuelta {plan['info'].get('return')}: {sign!r}")
    if a.preview:
        mons = [p for _c, _z, ms in plan["spawns"] for _n, p, _t in ms]
        cells = {(x, y, spec["z"]): ids for (x, y), ids in plan["tiles"].items()}
        K.preview(cells, spec["box"], spec["z"], a.preview, marks=mons)
        a.preview.with_suffix(".txt").write_text(ascii_map(plan, spec, 1) + "\n")
        print("vista previa:", a.preview)
    if a.write:
        n = write_zone(spec, theme, plan, m, sign)
        print(f"escrito: {n} casillas cambiadas; manifiesto {spec['manifest']}")
    print(jev.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
