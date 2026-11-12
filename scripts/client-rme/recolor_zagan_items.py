#!/usr/bin/env python3
"""Dibujo para los ítems Zagan que no tenían: un ítem vanilla del mismo tipo, recoloreado.

Los sprites del pack Zagan se perdieron (docs/items-and-map/ZAGAN_TEST_ITEMS.md). draw_zagan_items.py redibujó
los 17 con uso; los otros 38 seguían mostrando el ítem vanilla cuyo client id ocupan (tierra, pasto, una pared,
un paquete). Acá cada uno toma el dibujo de un ítem vanilla de su mismo tipo con otro color, para que lo que
se ve coincida con lo que es.

  python3.11 scripts/client-rme/recolor_zagan_items.py --preview /tmp/zagan.png
  python3.11 scripts/client-rme/recolor_zagan_items.py --apply devtools/rme/rme-client-760

Escribe en el client id que cada ítem ya tiene en items-zagan-test.otb (el OTB no cambia), con los flags del
.dat del ítem base. Re-aplicar reemplaza los sprites en el lugar. Ningún ítem vanilla en uso comparte esos
client ids (comprobado contra el mapa, el loot y los NPC).

Tabla ITEMS: server id -> (nombre de archivo, server id del ítem base, opciones de color):
  hue    tono nuevo en grados
  sat    multiplica la saturación;  smin  saturación mínima (para teñir grises)
  val    multiplica el brillo;      gamma exponente del brillo (>1 oscurece los medios)
  gold   True deja igual el oro (tono 24-75° y claro) y los brillos casi blancos
  only   "metal" tiñe solo lo gris (deja la madera y el cuero como están)
"""
from __future__ import annotations

import argparse
import colorsys
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import draw_zagan_items as Z  # noqa: E402
from recolor_item import item_pixels  # noqa: E402

THINGS = REPO / "devtools/rme/rme-client-760"


def C(hue, sat=1.0, smin=0.0, val=1.0, gamma=1.0, gold=False, only="all"):
    return dict(hue=hue, sat=sat, smin=smin, val=val, gamma=gamma, gold=gold, only=only)


ITEMS: dict[int, tuple[str, int, dict]] = {
    # --- escudos
    20101: ("quarry_ward", 2532, C(32, 0.9, 0.22, 0.82)),                 # ancient shield -> piedra de cantera
    20128: ("ironhide_bulwark", 2530, C(215, 0.5, 0.18, 0.62, 1.1)),      # copper shield -> disco de hierro
    20149: ("mosaic_shield", 2542, C(172, 1.0, 0.45, 1.0)),               # plasma shield -> azulejos turquesa
    20150: ("bloodreaver_aegis", 2534, C(356, 1.1, 0.6, 0.85)),           # vampire shield -> sangre
    20151: ("sunforge_shield", 2539, C(42, 1.0, 0.62, 0.98, 1.35)),       # phoenix shield -> sol dorado
    20153: ("frostwarden_aegis", 2513, C(196, 1.0, 0.42, 1.12)),          # battle shield -> hielo
    # --- cascos
    20102: ("morlen_crest", 2475, C(168, 1.0, 0.36, 0.95)),               # warrior helmet -> jade
    20118: ("starbinder_hood", 2663, C(268, 1.0, 0.5, 0.95)),             # mystic turban -> violeta
    20152: ("fox_machina_helmet", 2457, C(200, 0.25, 0.0, 1.22, 0.85)),   # steel helmet -> blanco (+ visor verde)
    # --- armaduras
    20103: ("ashlar_plate", 2463, C(38, 1.0, 0.3, 0.95)),                 # plate armor -> sillar de arenisca
    20109: ("rubbleguard_mail", 2483, C(24, 1.0, 0.32, 0.72)),            # scale armor -> escombro pardo
    20127: ("ashlord_mantle", 2656, C(14, 1.05, 0.5, 0.9, gold=True)),    # blue robe -> brasa
    20145: ("tiled_breastplate", 2465, C(186, 1.0, 0.5, 0.9)),            # brass armor -> teja esmaltada
    20146: ("quarryguard_armor", 2489, C(212, 0.6, 0.14, 1.3, 0.9)),      # dark armor -> granito gris
    20147: ("obsidian_regalia", 2472, C(278, 1.2, 0.42, 0.62, 1.25)),     # magic plate armor -> obsidiana
    # --- piernas
    20104: ("basalt_greaves", 2647, C(222, 1.0, 0.25, 0.55, 1.1)),        # plate legs -> basalto
    20116: ("marcher_leggings", 2648, C(84, 1.0, 0.42, 0.88)),            # chain trousers -> verde de marcha
    20117: ("cordovan_leggings", 2649, C(352, 1.15, 0.5, 0.85)),          # leather trousers -> cordobán
    20148: ("kilnfire_leggings", 2478, C(16, 1.2, 0.6, 0.95)),            # brass legs -> rojo de horno
    # --- botas
    20129: ("wayfarer_boots", 2643, C(204, 0.9, 0.35, 0.95)),             # leather boots -> azul polvoriento
    # --- amuletos
    20107: ("venomqueen_heart", 2173, C(112, 1.2, 0.6, 1.0)),             # amulet of loss -> veneno
    20108: ("bonepriest_phylactery", 2197, C(276, 1.0, 0.36, 1.05)),      # stone skin amulet -> hueso violáceo
    # --- anillos / orbes
    20106: ("hollow_orb", 2192, C(262, 0.55, 0.2, 0.7, 1.15)),            # crystal ball -> orbe apagado
    20124: ("azure_sunstone", 2154, C(206, 1.0, 0.6, 0.95)),              # yellow gem -> azul
    20125: ("verdant_sunstone", 2154, C(128, 1.0, 0.6, 0.9)),             # yellow gem -> verde
    20144: ("relic_of_ulm", 2354, C(166, 1.0, 0.5, 0.9)),                 # ornamented ankh -> jade
    # --- armas
    20111: ("rift_hammer", 2391, C(284, 1.0, 0.55, 1.0, only="metal")),   # war hammer -> cabeza violeta
    20115: ("granite_mace", 2398, C(18, 1.0, 0.3, 0.95, only="metal")),   # mace -> granito rosado
    20119: ("reachbrand_lance", 2414, C(20, 1.0, 0.75, 1.1, only="metal")),   # dragon lance -> punta al rojo
    20120: ("boltworker_crossbow", 2455, C(212, 0.8, 0.3, 0.8)),          # crossbow -> acero azulado
    # --- runas
    20133: ("lifewell_rune", 2273, C(336, 0.9, 0.5, 1.05)),               # adura vita -> rosa
    20134: ("emberstorm_rune", 2304, C(30, 1.0, 0.7, 1.05)),              # gran flam -> naranja
    20135: ("shattercall_rune", 2313, C(215, 0.35, 0.1, 1.0)),            # explosion -> gris acero
    20136: ("arcflash_rune", 2279, C(54, 1.0, 0.7, 1.15)),                # energy wall -> amarillo eléctrico
    20140: ("flamecoil_rune", 2303, C(322, 1.0, 0.65, 0.95)),             # fire wall -> magenta
    20141: ("mireveil_rune", 2285, C(64, 0.8, 0.4, 0.62)),                # poison field -> oliva de pantano
    20142: ("stonelock_rune", 2278, C(28, 0.6, 0.3, 0.78)),               # paralyze -> piedra parda
    20143: ("venomthread_rune", 2292, C(156, 1.1, 0.6, 1.0)),             # envenom -> verde agua
}


def recolor(pixels, o):
    out = []
    for r, g, b, a in pixels:
        if not a:
            out.append((0, 0, 0, 0))
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        hd = h * 360
        keep = o["gold"] and ((24 <= hd <= 75 and v > 0.5 and s > 0.3) or (s < 0.2 and v > 0.85))
        if o["only"] == "metal" and s >= 0.3:
            keep = True
        if keep:
            out.append((r, g, b, 255))
            continue
        if v < 0.14:                                    # contorno: casi negro, apenas teñido
            ns, nv = min(1.0, max(s * o["sat"], o["smin"] * 0.5)), v * 0.9
        else:
            ns = min(1.0, max(s * o["sat"], o["smin"] if o["sat"] else 0.0))
            nv = min(1.0, (v ** o["gamma"]) * o["val"])
        rr, gg, bb = colorsys.hsv_to_rgb(o["hue"] / 360, ns, nv)
        out.append((int(rr * 255), int(gg * 255), int(bb * 255), 255))
    return out


def fox_visor(img: Image.Image) -> None:
    """Las ranuras del visor (lo oscuro rodeado de casco) pasan a verde brillante."""
    px = img.load()
    slots = [(x, y) for y in range(8, 22) for x in range(32)
             if px[x, y][3] and max(px[x, y][:3]) < 80
             and all(0 <= x + dx < 32 and px[x + dx, y][3] for dx in (-3, 3))
             and all(px[x, y + dy][3] for dy in (-3, 3))]
    for x, y in slots:
        px[x, y] = (96, 240, 120, 255) if (x, y - 1) not in slots else (36, 176, 78, 255)


POST = {20152: fox_visor}
_CACHE: dict[int, Image.Image] = {}
_BASE_CID: dict[int, int] = {}


def base_pixels(base_sid: int):
    if not _BASE_CID:
        _BASE_CID.update({sid: v["cid"] for sid, v in Z.otb_index(Z.BASE_OTB).items()})
    return item_pixels(THINGS, _BASE_CID[base_sid])


def render(sid: int) -> Image.Image:
    if sid not in _CACHE:
        _name, base_sid, opts = ITEMS[sid]
        img = Image.new("RGBA", (32, 32))
        img.putdata(recolor(base_pixels(base_sid), opts))
        if sid in POST:
            POST[sid](img)
        _CACHE[sid] = img
    return _CACHE[sid]


def preview(path: Path, names: dict[int, str], only: list[int] | None) -> None:
    sids = only or list(ITEMS)
    scale, cols, cw, ch = 3, 8, 150, 132
    rows = (len(sids) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cw, rows * ch), (58, 78, 84, 255))
    draw = ImageDraw.Draw(sheet)
    for i, sid in enumerate(sids):
        x, y = (i % cols) * cw, (i // cols) * ch
        old = Image.new("RGBA", (32, 32))
        old.putdata(base_pixels(ITEMS[sid][1]))
        sheet.alpha_composite(old, (x + 6, y + 8))
        sheet.alpha_composite(render(sid).resize((32 * scale, 32 * scale), Image.NEAREST), (x + 44, y + 4))
        draw.text((x + 4, y + 102), str(sid), fill=(190, 210, 215, 255))
        draw.text((x + 4, y + 114), names.get(sid, ITEMS[sid][0])[:24], fill=(255, 255, 255, 255))
    sheet.save(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", type=Path, help="hoja con el ítem base (chico) y el nuevo (3x)")
    ap.add_argument("--only", type=int, nargs="*", help="server ids para la vista previa")
    ap.add_argument("--png-dir", type=Path)
    ap.add_argument("--apply", type=Path, metavar="DIR_THINGS")
    a = ap.parse_args()
    names = {sid: v["name"] for sid, v in Z.otb_index(Z.ZAGAN_OTB).items()}
    if a.preview:
        preview(a.preview, names, a.only)
        print(f"vista previa: {a.preview}")
    if a.png_dir:
        a.png_dir.mkdir(parents=True, exist_ok=True)
        for sid, (fname, _b, _o) in ITEMS.items():
            render(sid).save(a.png_dir / f"{fname}.png")
        print(f"{len(ITEMS)} PNG en {a.png_dir}")
    if a.apply:
        for sid in ITEMS:                      # leer todos los base antes de escribir nada
            render(sid)
        Z.apply(a.apply, {sid: (fname, None, base) for sid, (fname, base, _o) in ITEMS.items()}, render)
    if not (a.preview or a.png_dir or a.apply):
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
