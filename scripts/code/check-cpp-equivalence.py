#!/usr/bin/env python3
"""Comprueba que el C++ actual genera el mismo código que el de otro commit, sin compilar.

Para cada .cpp/.h de server/YurOTS/ots/source que existe en los dos lados:
  - default: resuelve con unifdef TODAS las condiciones (#if/#ifdef) con una misma
    configuración (las macros de --flags con su valor; el resto, sin definir) y compara el
    código sin comentarios. Si da igual, el binario de Linux sale igual.
  - --comments: compara el código sin comentarios ni espacios. Sirve para
    strip-dead-comments.py (solo se borraron comentarios).

Uso (desde la raíz del repo):
  python3 scripts/code/check-cpp-equivalence.py origin/main
  python3 scripts/code/check-cpp-equivalence.py --flags flags.h origin/main
  python3 scripts/code/check-cpp-equivalence.py --comments HEAD~1
flags.h: líneas "#define X" / "#undef X" (formato de unifdef -f). Necesita unifdef
(viene con las Xcode Command Line Tools; en Linux: apt install unifdef).
Ver docs/systems/LIMPIEZA_CODIGO_NOV2026.md.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = 'server/YurOTS/ots/source'
sys.path.insert(0, str(Path(__file__).resolve().parent))


def git_show(ref, path):
    r = subprocess.run(['git', 'show', f'{ref}:{path}'], cwd=ROOT, capture_output=True)
    return r.stdout.decode('latin-1') if r.returncode == 0 else None


def macros(text):
    names = set()
    for line in re.findall(r'^\s*#\s*(?:el)?if.*$', text, re.M):
        line = re.sub(r'//.*|/\*.*?\*/', '', line)
        names.update(re.findall(r'[A-Za-z_]\w*', line))
    return names - {'if', 'ifdef', 'ifndef', 'elif', 'defined'}


def unifdef(text, flags_file, tmp):
    src = tmp / 'in.cpp'
    src.write_text(text, encoding='latin-1')
    r = subprocess.run(['unifdef', '-f', str(flags_file), str(src)], capture_output=True)
    return r.stdout.decode('latin-1').rstrip('\n')


def code_only(text):
    import importlib.util
    spec = importlib.util.spec_from_file_location('sdc', Path(__file__).resolve().parent / 'strip-dead-comments.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out, last = [], 0
    for _kind, a, b in mod.tokens(text):
        out.append(text[last:a])
        out.append(' ')
        last = b
    out.append(text[last:])
    return re.sub(r'\s+', ' ', ''.join(out)).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref')
    ap.add_argument('--flags', help='archivo #define/#undef para unifdef')
    ap.add_argument('--comments', action='store_true')
    args = ap.parse_args()

    files = sorted(p for p in (ROOT / SRC).iterdir() if p.suffix in ('.cpp', '.h'))
    pairs = []
    for p in files:
        old = git_show(args.ref, f'{SRC}/{p.name}')
        if old is not None:
            pairs.append((p.name, old, p.read_text(encoding='latin-1')))

    bad = 0
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        if not args.comments:
            given = {}
            if args.flags:
                for line in Path(args.flags).read_text().splitlines():
                    m = re.match(r'#\s*(define|undef)\s+(\w+)(.*)', line)
                    if m:
                        given[m.group(2)] = line
            names = set()
            for _n, old, new in pairs:
                names |= macros(old) | macros(new)
            flags = tmp / 'flags.h'
            flags.write_text('\n'.join(list(given.values()) +
                                       [f'#undef {n}' for n in sorted(names - set(given))]) + '\n')
        for name, old, new in pairs:
            if args.comments:
                same = code_only(old) == code_only(new)
            else:
                same = code_only(unifdef(old, flags, tmp)) == code_only(unifdef(new, flags, tmp))
            if not same:
                bad += 1
                print('DIFIERE', name)
    print(f'{len(pairs) - bad} iguales, {bad} distintos (contra {args.ref})')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
