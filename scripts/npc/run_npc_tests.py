#!/usr/bin/env python3
"""Pruebas de NPCs por transcripción (golden files), sin levantar el servidor.

Para cada script de data/npc/scripts genera un guion (saludo, palabras clave del
propio script con cantidades, sí/no, ocupado, timeout, alejarse) y lo corre con
harness.lua en LuaJIT (mismo dialecto que el server). La salida se compara con
scripts/npc/golden/<script>.txt.

Uso:
  python3 scripts/npc/run_npc_tests.py            # compara contra golden
  python3 scripts/npc/run_npc_tests.py --record   # graba golden + guion congelado (solo si el cambio es a propósito)
  python3 scripts/npc/run_npc_tests.py food boat  # solo esos scripts
"""
from __future__ import annotations

import argparse
import difflib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OTS = REPO / "server/YurOTS/ots"
SCRIPTS = OTS / "data/npc/scripts"
GOLDEN = HERE / "golden"
EXTRA = HERE / "scenarios"
LUA = shutil.which("luajit") or shutil.which("lua5.1")

WORD = re.compile(r"""(['"])([a-z][a-z0-9 '\-]{0,24})\1""")
GENERIC = ["help", "ayuda", "offer", "trade", "list", "info", "job", "name", "yes", "no", "si",
           "sell", "buy", "all", "status", "deposit 100", "withdraw 50", "balance", "transfer 10 to player1002"]


def keywords(text: str) -> list[str]:
    out = []
    for m in WORD.finditer(text):
        w = m.group(2).strip()
        if w and "/" not in w and w not in out and not w.endswith(".lua"):
            out.append(w)
    return out


def scenario(script: Path, text: str | None = None) -> str:
    """Guion congelado (golden/<script>.scenario.txt) o, si no hay, generado del texto del script."""
    frozen = GOLDEN / (script.stem + ".scenario.txt")
    if text is None and frozen.exists():
        return frozen.read_text()
    kws = keywords(text if text is not None else script.read_text(encoding="latin-1"))
    lines = ["# generado por run_npc_tests.py", "near 1001", "near 1002",
             "say 1001 hello there", "say 1001 hi", "say 1002 hi", "say 1001 help"]
    for w in GENERIC + kws:
        for variant in (w, f"5 {w}", f"{w} 100", f"{w} all"):
            lines += [f"say 1001 {variant}", "say 1001 yes", f"say 1001 {variant}", "say 1001 no"]
        lines.append("think")
    lines += ["say 1001 bye", "say 1001 hi", "advance 40", "think", "say 1001 hi", "far 1001", "think",
              "near 1001", "say 1001 hola", "disappear 1001", "say 1002 hi", "set 1002 money 0",
              "set 1002 slots 0", "set 1002 level 1"]
    for w in kws[:60]:
        lines += [f"say 1002 {w}", "say 1002 yes"]
    lines += ["say 1002 chau", "think 3"]
    extra = EXTRA / (script.stem + ".txt")
    if extra.exists():
        lines += extra.read_text().splitlines()
    return "\n".join(lines) + "\n"


def transcript(script: Path) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(scenario(script))
        scen = f.name
    rel = script.relative_to(OTS)
    res = subprocess.run([LUA, str(HERE / "harness.lua"), str(rel), scen], cwd=OTS,
                         capture_output=True, text=True, timeout=120)
    Path(scen).unlink()
    return res.stdout + (("STDERR " + res.stderr) if res.stderr else "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    ap.add_argument("only", nargs="*")
    a = ap.parse_args()
    if not LUA:
        sys.exit("falta luajit (brew install luajit)")
    GOLDEN.mkdir(exist_ok=True)
    scripts = sorted(p for p in SCRIPTS.glob("*.lua"))
    if a.only:
        scripts = [p for p in scripts if p.stem in a.only]
    failed = 0
    for s in scripts:
        out = transcript(s)
        g = GOLDEN / (s.stem + ".txt")
        says = out.count("\nSAY ")
        errs = out.count("\nERROR ")
        if a.record:
            (GOLDEN / (s.stem + ".scenario.txt")).write_text(scenario(s))
            g.write_text(out)
            print(f"grabado {s.stem:15s} {len(out.splitlines()):6d} líneas, {says} respuestas, {errs} errores")
            continue
        if not g.exists():
            print(f"SIN GOLDEN {s.stem}")
            failed += 1
            continue
        old = g.read_text()
        if old == out:
            print(f"ok  {s.stem:15s} ({says} respuestas)")
        else:
            failed += 1
            diff = list(difflib.unified_diff(old.splitlines(), out.splitlines(), "golden", "ahora", n=2, lineterm=""))
            print(f"DIF {s.stem}: {len(diff)} líneas de diferencia")
            print("\n".join(diff[:40]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
