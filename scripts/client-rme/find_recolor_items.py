#!/usr/bin/env python3
"""Busca ítems custom (server id >= 20100) cuyo sprite es un recolor de un ítem vanilla.

Para cada ítem custom compara el primer sprite con el de todos los ítems vanilla (server id < 20000) del
mismo cliente canónico: IoU de la silueta (alpha) y correlación del brillo dentro de la silueta común.
Silueta >= 0.90 y brillo >= 0.80 = recolor (misma forma y mismo sombreado, otro tono).

  python3.11 scripts/client-rme/find_recolor_items.py [--things devtools/rme/rme-client-760] [--min-iou 0.8]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build_zagan_test_assets as B  # noqa: E402
import draw_zagan_items as Z  # noqa: E402
from add_black_dragon_look import decode_sprite, read_spr  # noqa: E402


def load(things: Path):
    entries, _ = B.DatReader((things / "Tibia.dat").read_bytes()).read_item_entries()
    spr = (things / "Tibia.spr").read_bytes()
    _n, offsets = read_spr(spr)
    by_cid = {e.client_id: e for e in entries}
    cache: dict[int, np.ndarray] = {}

    def px(cid: int) -> np.ndarray | None:
        if cid not in cache:
            e = by_cid.get(cid)
            if not e or not e.sprite_ids:
                cache[cid] = None
            else:
                cache[cid] = np.array(decode_sprite(spr, offsets, e.sprite_ids[0]), dtype=np.float32).reshape(32, 32, 4)
        return cache[cid]
    return px


def compare(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    ma, mb = a[..., 3] > 0, b[..., 3] > 0
    inter, union = (ma & mb).sum(), (ma | mb).sum()
    iou = inter / union if union else 0.0
    both = ma & mb
    if both.sum() < 8:
        return iou, 0.0
    la = a[..., :3].mean(-1)[both]
    lb = b[..., :3].mean(-1)[both]
    if la.std() < 1 or lb.std() < 1:
        return iou, 0.0
    return float(iou), float(np.corrcoef(la, lb)[0, 1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--things", type=Path, default=REPO / "devtools/rme/rme-client-760")
    ap.add_argument("--min-iou", type=float, default=0.80)
    a = ap.parse_args()
    px = load(a.things)
    otb = Z.otb_index(Z.ZAGAN_OTB)
    vanilla = [(s, v) for s, v in otb.items() if s < 20000]
    vpx = []
    for s, v in vanilla:
        p = px(v["cid"])
        if p is not None and (p[..., 3] > 0).sum() > 20:
            vpx.append((s, v, p))
    for sid in sorted(s for s in otb if s >= 20100):
        v = otb[sid]
        p = px(v["cid"])
        if p is None or (p[..., 3] > 0).sum() < 20:
            continue
        best = None
        for bs, bv, bp in vpx:
            if bv["cid"] == v["cid"]:
                continue
            iou, corr = compare(p, bp)
            score = iou + 0.5 * corr
            if best is None or score > best[0]:
                best = (score, iou, corr, bs, bv["name"])
        if best and best[1] >= a.min_iou:
            tag = "RECOLOR" if best[1] >= 0.90 and best[2] >= 0.80 else "parecido"
            print(f"{sid}\t{v['name']}\tcid {v['cid']}\tbase {best[3]} {best[4]}\tiou {best[1]:.2f}\tbrillo {best[2]:.2f}\t{tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
