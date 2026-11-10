#!/usr/bin/env python3
"""Borra del C++ los comentarios que son código desactivado, no los que explican.

Cuenta como código: líneas de comentario que terminan en ; { } (y tienen paréntesis,
asignación, ->, ::, ++ o un break/return), o que empiezan con if(/for(/while(/return.
Un /* ... */ de 3+ líneas se borra si al menos la mitad de sus líneas son código.
Nunca toca licencias (GNU, Copyright) ni comentarios con TODO/FIXME/NOTE/YUR CHANGE.

Uso (desde server/YurOTS/ots/source):
  python3 ../../../../scripts/code/strip-dead-comments.py --dry *.cpp *.h   # solo cuenta
  python3 ../../../../scripts/code/strip-dead-comments.py *.cpp *.h         # aplica
Después: scripts/code/check-cpp-equivalence.py --comments <ref> para comprobar que el
código, sin comentarios, quedó idéntico. Ver docs/systems/LIMPIEZA_CODIGO_NOV2026.md.
"""
import re
import sys

CODE_END = re.compile(r'[;{}]\s*$')
CODE_START = re.compile(r'^\s*(if|for|while|switch|return|else\b|case\b|delete\b)\s*[\(\w]')
PROSE = re.compile(r'[A-Za-z]{3,}\s+[A-Za-z]{3,}\s+[A-Za-z]{3,}\s+[A-Za-z]{3,}')
KEEP = re.compile(r'\b(TODO|FIXME|NOTE|XXX|YUR CHANGE|BUG|HACK)\b', re.I)


def looks_code(text):
    t = text.strip()
    if not t or KEEP.search(t):
        return False
    if t in ('{', '}', '};'):
        return True
    if CODE_END.search(t) and not re.search(r'[.!?:]\s*$', t.rstrip(';{} ')):
        return re.search(r'[\(\)=\[\]]|->|::|\+\+|--|^\s*(break|continue|return)\b', t) is not None
    return bool(CODE_START.match(t)) and '(' in t and PROSE.search(t) is None


def tokens(src):
    """(tipo, inicio, fin) de cada comentario; salta strings y chars."""
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith('//', i):
            j = src.find('\n', i)
            j = n if j < 0 else j
            yield 'line', i, j
            i = j
        elif src.startswith('/*', i):
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            yield 'block', i, j
            i = j
        elif c in '"\'':
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == '\\' else 1
            i = j + 1
        else:
            i += 1


def dead_comments(src):
    for kind, a, b in tokens(src):
        body = src[a:b]
        if kind == 'line':
            if looks_code(body[2:]):
                yield a, b
            continue
        inner = body[2:-2]
        lines = [l.strip().lstrip('*').strip() for l in inner.split('\n')]
        lines = [l for l in lines if l]
        if body.count('\n') < 2 or not lines or re.search(r'GNU|This program|Copyright|Inc\.', inner):
            continue
        code = sum(1 for l in lines if looks_code(l))
        if code >= 2 and code * 2 >= len(lines):
            yield a, b


def strip(src):
    out, last, n = [], 0, 0
    for a, b in dead_comments(src):
        out.append(src[last:a])
        last = b
        n += 1
    out.append(src[last:])
    res = []
    blank = 0
    for line in ''.join(out).split('\n'):
        cr = '\r' if line.endswith('\r') else ''
        core = line[:-1] if cr else line
        if core.strip() == '':
            blank += 1
            if blank > 1:	# un comentario borrado no deja líneas en blanco de más
                continue
            res.append(cr)
        else:
            blank = 0
            res.append(core.rstrip() + cr if core.rstrip() != core and core not in src else line)
    return '\n'.join(res), n


def main():
    dry = '--dry' in sys.argv
    total = 0
    for path in [a for a in sys.argv[1:] if a != '--dry']:
        src = open(path, encoding='latin-1', newline='').read()
        res, n = strip(src)
        if n:
            total += n
            print(f'{path}: {n} comentarios de código')
            if not dry:
                open(path, 'w', encoding='latin-1', newline='').write(res)
    print('total:', total)


if __name__ == '__main__':
    main()
