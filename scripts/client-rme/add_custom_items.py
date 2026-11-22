#!/usr/bin/env python3
"""Agrega ítems nuevos (PNG 32x32, o 64x64/64x32 para 2x2/2x1; para ítems animados,
32x(32*cuadros) en 1x1 o 64x(64*cuadros) en 2x2, apilados verticalmente con frames=N)
al cliente y al servidor, sobre los archivos actuales.

Para ítems traídos de otras versiones (ej. armas de 8.x) o dibujados (Root Colossus), sin el builder viejo (build_zagan_test_assets.py,
que necesita el pack Zagan perdido y client-local). Cada ítem de NEW_ITEMS:

  - Cliente (Tibia.dat / Tibia.spr, en cada --things): agrega el sprite al final del .spr y hace que su
    client id (uno "sacrificado": un ítem viejo que el servidor nunca da) se vea como el prototipo pero
    con el sprite nuevo. El client id es fijo, así es el mismo en el cliente de RME y en el de jugadores.
  - Servidor (items-zagan-test.otb, en cada --otb): nodo nuevo con su server id fijo, copiado del
    prototipo (slot, peso, tipo de arma) con nombre, descripción, ataque y defensa propios.

Extras: `decor=True` copia los bloques del prototipo sin stats (decoración de mapa); `light=(nivel,
color)` reescribe la luz — flag .dat 0x15 y attr OTB 0x2A (ITEM_ATTR_LIGHT2) — para ítems con luz
propia (magic tree rojo, blue bassin). `frames=N` instala los N cuadros de animación del PNG
(1x1, 2x2, 2x1 y 1x2). `appearance=server_id` permite usar otro prototipo visual;
`ground_overlay=True` convierte ese terreno en borde decorativo sin cambiar el suelo
ni su velocidad (exclusivo y opt-in; ver RIVER_GROTTO.md).

Re-ejecutable: si el ítem ya está (mismo sprite en el .dat, nodo con ese server id), no cambia nada.
Elegir client ids: `--candidates` lista primero los nuevos libres (5090-6089, entradas vacías al final del
.dat, ver LAST_CLIENT_ID) y después los viejos que se pueden sacrificar sin riesgo (ni en el mapa, ni en
loot, NPC, acciones o scripts, ni destino de una pudrición, ni suelos, cadáveres o decoración).

  python3.11 scripts/client-rme/add_custom_items.py --candidates
  python3.11 scripts/client-rme/add_custom_items.py --things devtools/rme/rme-client-760 \\
      --otb server/YurOTS/ots/data/items/items-zagan-test.otb [--things OTRO_CLIENTE/data/things/760]

Necesita Pillow (en la Mac mini: python3.11). Los PNG están en devtools/zagan-test/custom-sprites/
(los saca extract_client_sprites.py). Doc: docs/items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md.
"""
from __future__ import annotations

import argparse
import re
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build_zagan_test_assets as B  # noqa: E402

SPRITES = ROOT / "devtools" / "zagan-test" / "custom-sprites"
ITEM_ATTR_WEAPON2 = 0x26
ITEM_ATTR_ARMOR2 = 0x28   # u16 armor, double weight, u16 slot
ITEM_ATTR_DECAY = 0x1F
ITEM_ATTR_ROTATETO = 0x1E
ITEM_ATTR_DECAY2 = 0x25
ITEM_ATTR_LIGHT2 = 0x2A    # u16 nivel, u16 color (ITEM_ATTR_LIGHT2 de source/itemloader.h)
FLAG_PICKUPABLE = 1 << 5
FLAG_MOVEABLE = 1 << 6

# Client ids nuevos (nov 2026): el .dat de 7.6 terminaba en el 5089 y cada ítem nuevo tenía que sacrificar uno
# viejo. Ahora el .dat lleva entradas vacías hasta LAST_CLIENT_ID (sin dibujo, sprite 0, sin flags: el cliente
# no dibuja nada y el servidor nunca las manda). Un ítem nuevo usa una de ellas como client_id y apply_things la
# reemplaza por el prototipo con sus sprites. --candidates las lista primero. Para más: subir LAST_CLIENT_ID y
# correr el instalador (agrega las que falten al final de los ítems, antes de los outfits).
FIRST_NEW_CLIENT_ID = 5090
LAST_CLIENT_ID = 6089
# flags: ninguno (0xFF); 1x1, 1 capa, patrón 1x1x1, 1 cuadro; sprite 0
BLANK_DAT_ENTRY = b"\xff" + bytes([1, 1, 1, 1, 1, 1, 1]) + b"\x00\x00"

# Tamaño en bytes del argumento de cada flag del prefijo .dat (7.55–7.72). Tabla canónica:
# scripts/map/kb/mapdata.py (DAT_ARGS). El 23 se remapea a 252 (sin argumento) desde 7.55.
DAT_ARGS = {0x00: 2, 0x08: 2, 0x09: 2, 0x15: 4, 0x18: 4, 0x19: 2, 0x1C: 2, 0x1D: 2}


def ground_overlay(prefix: bytes) -> bytes:
    """Keep native terrain patterns/animation as a walkable ground-border skin."""
    out, pos = bytearray(b'\x01'), 0
    while pos < len(prefix):
        attr = prefix[pos]
        pos += 1
        if attr == 0xFF:
            return bytes(out) + b'\xff' + prefix[pos:]
        size = DAT_ARGS.get(252 if attr == 23 else attr, 0)
        if attr not in (0x00, 0x01, 0x0C, 0x0F):
            out.append(attr)
            out += prefix[pos:pos + size]
        pos += size
    raise ValueError("Terrain appearance without DAT terminator")


def with_light(prefix: bytes, level: int, color: int) -> bytes:
    """Prefijo .dat con la luz (flag 0x15) reescrita: nivel u16 + color u16.
    Copia intacto el argumento de cada flag y todo lo que sigue al 0xFF (el 0xFF
    no es el final del prefijo: detrás vienen width/height/layers/pattern/frames)."""
    out, pos, found = bytearray(), 0, False
    while pos < len(prefix):
        attr = prefix[pos]
        out.append(attr)
        pos += 1
        if attr == 0xFF:
            if not found:
                out[-1:] = b'\x15' + struct.pack('<HH', level, color) + b'\xff'
            out += prefix[pos:]
            break
        n = DAT_ARGS.get(252 if attr == 23 else attr, 0)
        if attr == 0x15:
            found = True
            out += struct.pack("<HH", level, color)
        else:
            out += prefix[pos:pos + n]
        pos += n
    return bytes(out)

# server_id y client_id fijos: no cambiarlos una vez repartido el cliente. Prototipos (server ids de 7.6):
# 2407 bright sword (espada 1 mano), 2393 giant sword (espada 2 manos), 2391 war hammer (maza 2 manos),
# 2455 crossbow (ballesta). Los cuatro primeros usan stats de Tibia 8.60 (items.xml de RME data/860).
NEW_ITEMS = [
    dict(name="emerald sword", server_id=20157, client_id=3348, prototype=2407, png="emerald_sword.png",
         attack=49, defence=33, descr="A sword with a blade of polished emerald."),
    dict(name="avenger", server_id=20158, client_id=3346, prototype=2393, png="the_avenger.png",
         attack=50, defence=38, descr="This holy blade was forged of shattered dreams."),
    dict(name="arcane staff", server_id=20159, client_id=3345, prototype=2391, png="arcane_staff.png",
         attack=50, defence=30, descr="It is enchanted with ancient magic that renders a weak staff into a powerful weapon."),
    dict(name="arbalest", server_id=20160, client_id=3575, prototype=2455, png="arbalest.png",
         attack=2, defence=0, descr="It is a bit heavy due to the iron mounting, but very precise. Adds +2 to bolts."),
    # Armaduras: `armor` en vez de attack/defence (peso y slot, los del prototipo). 2487 crown armor (arm 13).
    # Sprites: la crown armor del cliente recoloreada con scripts/client-rme/recolor_item.py (comandos en
    # docs/items-and-map/CROWN_ARMORS.md). Ventaja propia en C++ (GameState::applyAmulets).
    dict(name="imperial crown armor", server_id=20161, client_id=3570, prototype=2487,
         png="imperial_crown_armor.png", armor=14,
         descr="Forged for the emperors of old, its violet plates still shine with royal gold."),
    dict(name="sapphire crown armor", server_id=20162, client_id=3564, prototype=2487,
         png="sapphire_crown_armor.png", armor=14,
         descr="Sapphire plates bound in gold. Blades and claws slide off it."),
    # Root Colossus: armas fisicas, sin procs ni cambios de C++. Sprites reproducibles con draw_root_weapons.py.
    dict(name="rootcleaver", server_id=20163, client_id=3573, prototype=2430,
         png="rootcleaver.png", attack=49, defence=31,
         descr="A jade-edged axe bound to a living root. Claimed from a Root Colossus."),
    dict(name="heartwood maul", server_id=20164, client_id=3561, prototype=2391,
         png="heartwood_maul.png", attack=52, defence=28,
         descr="Ancient heartwood held together by twisted roots. Claimed from a Root Colossus."),
    # Aurora Shield: el Ice Monk la soltaba con el id 20160, que terminó siendo la arbalest. Prototipo 2515
    # guardian shield (def 30). La Aurora Blade y la Aurora Axe siguen sin crearse (no tienen drop).
    dict(name="aurora shield", server_id=20165, client_id=3473, prototype=2515,
         png="aurora_shield.png", attack=0, defence=30,
         descr="Its golden rim holds a field of violet light, like the sky over the frozen north."),
    # Corpses de monstruos nuevos: contenedores 1x1 o 2x2. El prototipo aporta
    # flags/capacidad; no se tocan bloques de arma/armadura.
    dict(name="blue elf arcanist corpse", server_id=20166, client_id=3741, prototype=2979,
         png="blue_elf_arcanist_corpse.png", corpse=True,
         descr="The corpse of a blue elf arcanist."),
    dict(name="ice spider corpse", server_id=20167, client_id=3660, prototype=2857,
         png="ice_spider_corpse.png", corpse=True, tiles=2,
         descr="The frozen corpse of an ice spider."),
    dict(name="ice monk corpse", server_id=20168, client_id=3739, prototype=3128,
         png="ice_monk_corpse.png", corpse=True,
         descr="The frozen corpse of an ice monk."),
    dict(name="drowned sailor corpse", server_id=20169, client_id=3735, prototype=3128,
         png="drowned_sailor_corpse.png", corpse=True,
         descr="The corpse of a drowned sailor."),
    dict(name="tide priest corpse", server_id=20170, client_id=3673, prototype=3128,
         png="tide_priest_corpse.png", corpse=True,
         descr="The corpse of a tide priest."),
    dict(name="frost dragon corpse", server_id=20171, client_id=3659, prototype=3104,
         png="frost_dragon_corpse.png", corpse=True, tiles=2,
         descr="The frozen corpse of a frost dragon."),
    dict(name="black dragon corpse", server_id=20172, client_id=3605, prototype=3104,
         png="black_dragon_corpse.png", corpse=True, tiles=2,
         descr="The charred corpse of a black dragon."),
    # Corpses de las criaturas 8.60 importadas (nov 2026).
    dict(name="dead tortoise", server_id=20173, client_id=3604, prototype=3128,
         png="dead_tortoise.png", corpse=True, descr="The shell of a dead tortoise."),
    dict(name="dead thornback tortoise", server_id=20174, client_id=3603, prototype=3128,
         png="dead_thornback_tortoise.png", corpse=True, descr="The spiked shell of a dead thornback tortoise."),
    dict(name="dead mammoth", server_id=20175, client_id=3534, prototype=3104,
         png="dead_mammoth.png", corpse=True, tiles=2, descr="The corpse of a woolly mammoth."),
    dict(name="dead blood crab", server_id=20176, client_id=3533, prototype=3104,
         png="dead_blood_crab.png", corpse=True, tiles=2, descr="The broken shell of a blood crab."),
    dict(name="dead quara constrictor", server_id=20177, client_id=3504, prototype=3104,
         png="dead_quara_constrictor.png", corpse=True, tiles=2, descr="The corpse of a quara constrictor."),
    dict(name="dead quara hydromancer", server_id=20178, client_id=3503, prototype=3104,
         png="dead_quara_hydromancer.png", corpse=True, tiles=2, descr="The corpse of a quara hydromancer."),
    dict(name="dead quara mantassin", server_id=20179, client_id=3476, prototype=3104,
         png="dead_quara_mantassin.png", corpse=True, tiles=2, descr="The corpse of a quara mantassin."),
    dict(name="dead quara pincher", server_id=20180, client_id=3475, prototype=3104,
         png="dead_quara_pincher.png", corpse=True, tiles=2, descr="The corpse of a quara pincher."),
    dict(name="dead quara predator", server_id=20181, client_id=3474, prototype=3104,
         png="dead_quara_predator.png", corpse=True, tiles=2, descr="The corpse of a quara predator."),
    dict(name="dead cyclops", server_id=20182, client_id=3472, prototype=3104,
         png="dead_cyclops.png", corpse=True, tiles=2, descr="The corpse of a cyclops."),
    dict(name="dead wyrm", server_id=20183, client_id=3469, prototype=3104,
         png="dead_wyrm.png", corpse=True, tiles=2, descr="The corpse of a wyrm."),
    dict(name="remains of an earth elemental", server_id=20184, client_id=3468, prototype=3104,
         png="remains_of_an_earth_elemental.png", corpse=True, tiles=2, descr="A pile of earth and stone."),
    dict(name="remains of a water elemental", server_id=20185, client_id=3467, prototype=3128,
         png="remains_of_a_water_elemental.png", corpse=True, descr="A puddle of elemental water."),
    dict(name="slain zombie", server_id=20186, client_id=3466, prototype=3128,
         png="slain_zombie.png", corpse=True, descr="The corpse of a slain zombie."),
    dict(name="dead vampire bride", server_id=20187, client_id=3464, prototype=3128,
         png="dead_vampire_bride.png", corpse=True, descr="The corpse of a vampire bride."),
    dict(name="dead worker golem", server_id=20188, client_id=3463, prototype=2849,
         png="dead_worker_golem.png", corpse=True, tiles="2x1", descr="The broken remains of a worker golem."),
    dict(name="slain undead gladiator", server_id=20189, client_id=3461, prototype=3128,
         png="slain_undead_gladiator.png", corpse=True, descr="The corpse of an undead gladiator."),
    dict(name="slain nightstalker", server_id=20190, client_id=3460, prototype=3128,
         png="slain_nightstalker.png", corpse=True, descr="The corpse of a nightstalker."),
    # Magic tree rojo (nov 2026): decoración de mapa 2x2 animada en 2 cuadros, como la azul del
    # templo (server 2699, client 3613). Prototipo: el magic tree mismo (bloques OTB copiados,
    # sin stats). Los sparkles pasan de azul-lavanda a rojo intercambiando canales rojo/azul
    # (recolor_magic_tree.py) y la luz (flag .dat 0x15 + attr OTB 0x2A) de azul (143) a rojo
    # (187, el mismo color de luz del NM_ME_WHIRL_SLASH). Client 3455: "hacket" sacrificado.
    dict(name="red magic tree", server_id=20191, client_id=3455, prototype=2699,
         png="red_magic_tree.png", decor=True, tiles=2, frames=2, light=(6, 187),
         descr="A tree shimmering with red magic."),
    # Blue bassin (nov 2026): decoración de mapa. El coal bassin de 7.6 (server 1483,
    # client 2112) con la llama en azul: 1x1 animado en 2 cuadros y luz propia. El
    # fuego pasa a azul frío intercambiando canales rojo/azul (recolor_basin.py):
    # rojos -> azul profundo, naranjas -> celeste, amarillos -> cian; el hierro y la
    # mata de la base no se tocan. La luz (flag .dat 0x15 + attr OTB 0x2A) baja de
    # cálida (color 206) a azul 143 (la del magic tree del templo), mismo nivel 8.
    # frames=2 con tiles 1x1: el PNG apila los 2 cuadros verticalmente (32x64).
    # Client 3454: "broom" sacrificado.
    dict(name="blue bassin", server_id=20192, client_id=3454, prototype=1483,
         png="blue_basin.png", decor=True, frames=2, light=(8, 143),
         descr="It burns with cold blue flames."),
    # Black fire sword (nov 2026): la fire sword de 7.6 (server 2392, client 3280, 1x1 animada en 2
    # cuadros, luz 3 naranja 199) con fuego negro: recolor_black_fire_sword.py invierte el brillo de la
    # llama y le da tono violeta (corazón casi negro, puntas violetas) y pasa la empuñadura a hierro
    # oscuro. Espada de 1 mano mejorada sin efectos (atk 35 / def 22; la fire sword es 24 / 20). Luz
    # violeta tenue (nivel 3, color 113 = r3 g0 b5). Loot raro de las Dark Hydras. Client 3237:
    # "broken hilt" sacrificado.
    dict(name="black fire sword", server_id=20193, client_id=3237, prototype=2392,
         png="black_fire_sword.png", frames=2, light=(3, 113), attack=35, defence=22,
         descr="The blade is a black flame."),
    # Cadáveres de los Metal (nov 2026): el cadáver del original recoloreado con las paletas del preset
    # (creature_corpses.py escribe los PNG). Clients sacrificados: rabbit present, document (antes music piece 3236: la tiene el GM), cookbook.
    dict(name="metal dragon corpse", server_id=20225, client_id=3242, prototype=3104,
         png="metal_dragon_corpse.png", corpse=True, tiles=2,
         descr="The wrecked frame of a metal dragon. Coolant still glows in its veins."),
    dict(name="metal hydra corpse", server_id=20226, client_id=3216, prototype=4283,
         png="metal_hydra_corpse.png", corpse=True, tiles=2,
         descr="The wrecked frame of a metal hydra, leaking acid."),
    dict(name="metal demon corpse", server_id=20227, client_id=3234, prototype=2916,
         png="metal_demon_corpse.png", corpse=True, tiles=2,
         descr="The wrecked frame of a metal demon. Its reactor still flickers."),
    # Cadáveres propios para los monstruos nuevos que usaban el de otra criatura (nov 2026). Los PNG los
    # escribe creature_corpses.py: preset = el cadáver base con la receta del sprite; look (8.60) = un
    # cadáver de 7.6 parecido con la gama de colores del look. Clients: runas sin uso y adornos sueltos.
    dict(name="dead hellhound", server_id=20228, client_id=3202, prototype=2969,
         png="dead_hellhound.png", corpse=True, tiles="2x1",
         descr="The corpse of a hellhound."),
    dict(name="dead dark hydra", server_id=20229, client_id=3201, prototype=4283,
         png="dead_dark_hydra.png", corpse=True, tiles=2,
         descr="The corpse of a dark hydra."),
    dict(name="dead emerald scarab", server_id=20230, client_id=3196, prototype=3004,
         png="dead_emerald_scarab.png", corpse=True, tiles=2,
         descr="The corpse of an emerald scarab."),
    dict(name="remains of a root colossus", server_id=20231, client_id=3194, prototype=2931,
         png="remains_of_a_root_colossus.png", corpse=True, tiles=2,
         descr="The remains of a root colossus."),
    dict(name="dead red kongra", server_id=20232, client_id=3193, prototype=4268,
         png="dead_red_kongra.png", corpse=True, tiles=2,
         descr="The corpse of a red kongra."),
    dict(name="dead river troll", server_id=20233, client_id=3186, prototype=2806,
         png="dead_river_troll.png", corpse=True, tiles=1,
         descr="The corpse of a river troll."),
    dict(name="dead stone troll", server_id=20234, client_id=3185, prototype=2806,
         png="dead_stone_troll.png", corpse=True, tiles=1,
         descr="The corpse of a stone troll."),
    dict(name="dead thornwarden", server_id=20235, client_id=3184, prototype=4280,
         png="dead_thornwarden.png", corpse=True, tiles=2,
         descr="The corpse of a thornwarden."),
    dict(name="dead orc warchief", server_id=20236, client_id=3181, prototype=2967,
         png="dead_orc_warchief.png", corpse=True, tiles=1,
         descr="The corpse of an orc warchief."),
    dict(name="dead elvenbane ranger", server_id=20237, client_id=3175, prototype=2981,
         png="dead_elvenbane_ranger.png", corpse=True, tiles=1,
         descr="The corpse of an elvenbane ranger."),
    dict(name="dead elven archmage", server_id=20238, client_id=3171, prototype=2979,
         png="dead_elven_archmage.png", corpse=True, tiles=1,
         descr="The corpse of an elven archmage."),
    dict(name="dead imperial hero", server_id=20239, client_id=3170, prototype=3128,
         png="dead_imperial_hero.png", corpse=True, tiles=1,
         descr="The corpse of an imperial hero."),
    dict(name="dead lord of elvenbane", server_id=20240, client_id=3169, prototype=3128,
         png="dead_lord_of_elvenbane.png", corpse=True, tiles=1,
         descr="The corpse of a lord of elvenbane."),
    dict(name="ashes of the ashen lord", server_id=20241, client_id=3168, prototype=2916,
         png="ashes_of_the_ashen_lord.png", corpse=True, tiles=2,
         descr="The ashes of the ashen lord."),
    dict(name="remains of the fallen emperor", server_id=20242, client_id=3167, prototype=3025,
         png="remains_of_the_fallen_emperor.png", corpse=True, tiles=2,
         descr="The remains of the fallen emperor."),
    dict(name="dead chakoya", server_id=20243, client_id=3163, prototype=3113,
         png="dead_chakoya.png", corpse=True, tiles=1,
         descr="The corpse of a chakoya tribewarden."),
    dict(name="dead frost giant", server_id=20244, client_id=3162, prototype=3069,
         png="dead_frost_giant.png", corpse=True, tiles=2,
         descr="The corpse of a frost giant."),
    dict(name="remains of an ice golem", server_id=20245, client_id=3161, prototype=2952,
         png="remains_of_an_ice_golem.png", corpse=True, tiles=2,
         descr="The remains of an ice golem."),
    dict(name="dead crystal spider", server_id=20246, client_id=3159, prototype=2857,
         png="dead_crystal_spider.png", corpse=True, tiles=2,
         descr="The corpse of a crystal spider."),
    dict(name="dead bog raider", server_id=20247, client_id=3231, prototype=2824,
         png="dead_bog_raider.png", corpse=True, tiles=1,
         descr="The corpse of a bog raider."),
    dict(name="dead wyvern", server_id=20248, client_id=3218, prototype=3104,
         png="dead_wyvern.png", corpse=True, tiles=2,
         descr="The corpse of a wyvern."),
    dict(name="dead husky", server_id=20249, client_id=3209, prototype=2839,
         png="dead_husky.png", corpse=True, tiles=1,
         descr="The corpse of a husky."),
    # Crimson Cage Rune (nov 2026): runa y pared roja de 3 s. Copias de la runa de magic wall (2293) y de la
    # magic wall (1498: 2x2, 3 cuadros, bloquea paso y proyectiles) con los sprites de recolor_crimson_cage.py.
    # Clients sacrificados: dos broken bottle (server 2022 y 2010), ninguno en jugadores ni casas.
    # Gameplay en C++ (doCrimsonCage, spells.cpp). Doc: docs/gameplay/CRIMSON_CAGE_RUNE.md.
    dict(name="crimson cage rune", server_id=20273, client_id=2892, prototype=2293,
         png="crimson_cage_rune.png", decor=True,
         descr="Throw it at a creature to lock it inside crimson walls for 3 seconds."),
    dict(name="crimson wall", server_id=20274, client_id=2878, prototype=1498,
         png="crimson_cage_wall.png", decor=True, tiles=2, frames=3, light=(3, 180),
         descr="A cage of crimson magic. It fades within seconds."),
    # Tapestries con banderas y estandartes de guerra (nov 2026): copias del purple tapestry (1857: 2x2,
    # 3 patrones = enrollado / pared horizontal / pared vertical, hangable) con los dibujos de
    # make_flag_tapestries.py. frames=3 instala los 12 sprites; la cabecera (3 patrones) es la del prototipo.
    # Clients sacrificados: broken boots, broken glas x2, rotten meat, fishbone, old twig, horn (3957).
    # Se cuelgan en paredes con gancho (docs/gameplay/HANGABLES.md); los vende la NPC de muebles.
    dict(name="brazil tapestry", server_id=20275, client_id=3123, prototype=1857,
         png="brazil_tapestry.png", decor=True, tiles=2, frames=3,
         descr="A tapestry with the flag of Brazil. Hang it on a wall."),
    dict(name="chile tapestry", server_id=20276, client_id=3118, prototype=1857,
         png="chile_tapestry.png", decor=True, tiles=2, frames=3,
         descr="A tapestry with the flag of Chile. Hang it on a wall."),
    dict(name="usa tapestry", server_id=20277, client_id=3117, prototype=1857,
         png="usa_tapestry.png", decor=True, tiles=2, frames=3,
         descr="A tapestry with the flag of the United States. Hang it on a wall."),
    dict(name="argentina tapestry", server_id=20278, client_id=3112, prototype=1857,
         png="argentina_tapestry.png", decor=True, tiles=2, frames=3,
         descr="A tapestry with the flag of Argentina. Hang it on a wall."),
    dict(name="pirate banner", server_id=20279, client_id=3111, prototype=1857,
         png="pirate_banner.png", decor=True, tiles=2, frames=3,
         descr="A black banner with a skull and crossbones. Hang it on a wall."),
    dict(name="war banner", server_id=20280, client_id=3106, prototype=1857,
         png="war_banner.png", decor=True, tiles=2, frames=3,
         descr="A blood red war banner with crossed swords. Hang it on a wall."),
    dict(name="royal banner", server_id=20281, client_id=3103, prototype=1857,
         png="royal_banner.png", decor=True, tiles=2, frames=3,
         descr="A royal banner with a golden crown. Hang it on a wall."),
    # Las mismas 7, fijas (server 20320-20326; ojo: 20282-20296 son del muelle, dock_bridge_art.py) (fixed=True: sin moveable/pickupable en el OTB) y con el mismo client id (el server compara por client id: Items::sameClientItem, docs/gameplay/HANGABLES.md): se cuelgan
    # en el mapa como exhibición (local de Obi) sin que nadie se las lleve. No agregan sprites al cliente.
    dict(name="brazil tapestry", server_id=20320, client_id=3123, prototype=1857,
         png="brazil_tapestry.png", decor=True, tiles=2, frames=3, fixed=True,
         descr="On display. Obi sells them: say flags."),
    dict(name="chile tapestry", server_id=20321, client_id=3118, prototype=1857,
         png="chile_tapestry.png", decor=True, tiles=2, frames=3, fixed=True,
         descr="On display. Obi sells them: say flags."),
    dict(name="usa tapestry", server_id=20322, client_id=3117, prototype=1857,
         png="usa_tapestry.png", decor=True, tiles=2, frames=3, fixed=True,
         descr="On display. Obi sells them: say flags."),
    dict(name="argentina tapestry", server_id=20323, client_id=3112, prototype=1857,
         png="argentina_tapestry.png", decor=True, tiles=2, frames=3, fixed=True,
         descr="On display. Obi sells them: say flags."),
    dict(name="pirate banner", server_id=20324, client_id=3111, prototype=1857,
         png="pirate_banner.png", decor=True, tiles=2, frames=3, fixed=True,
         descr="On display. Obi sells them: say flags."),
    dict(name="war banner", server_id=20325, client_id=3106, prototype=1857,
         png="war_banner.png", decor=True, tiles=2, frames=3, fixed=True,
         descr="On display. Obi sells them: say flags."),
    dict(name="royal banner", server_id=20326, client_id=3103, prototype=1857,
         png="royal_banner.png", decor=True, tiles=2, frames=3, fixed=True,
         descr="On display. Obi sells them: say flags."),
    # Trofeos de jefes (nov 2026): tapestries con el jefe de frente sobre terciopelo y borde dorado
    # (make_flag_tapestries.py, TROPHIES). Rare de cada jefe. Clients sacrificados: libros sin uso; los 4 primeros
    # usaban 2845/2844/2840/2836, que se quedó el muelle (dock_bridge_art.py, 20297-20300): ahora 3021/3014/1780/2872.
    dict(name="demodras trophy", server_id=20330, client_id=3021, prototype=1857,
         png="demodras_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of Demodras, the dragon of the dungeon. Hang it on a wall."),
    dict(name="orshabaal trophy", server_id=20331, client_id=3014, prototype=1857,
         png="orshabaal_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of Orshabaal, the demon lord. Hang it on a wall."),
    dict(name="old widow trophy", server_id=20332, client_id=1780, prototype=1857,
         png="old_widow_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of the Old Widow, queen of the spiders. Hang it on a wall."),
    dict(name="ashen lord trophy", server_id=20333, client_id=2872, prototype=1857,
         png="ashen_lord_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of the Ashen Lord, still smouldering. Hang it on a wall."),
    dict(name="fallen emperor trophy", server_id=20334, client_id=2832, prototype=1857,
         png="fallen_emperor_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of The Fallen Emperor. Hang it on a wall."),
    dict(name="elvenbane trophy", server_id=20335, client_id=2831, prototype=1857,
         png="lord_of_elvenbane_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of the Lord of Elvenbane. Hang it on a wall."),
    # Trofeos de los monstruos nuevos (rare 0,5 %) y de los jefes de las torres de Elvenbane (5 %).
    dict(name="black dragon trophy", server_id=20341, client_id=2965, prototype=1857,
         png="black_dragon_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of a Black Dragon. Hang it on a wall."),
    dict(name="dark hydra trophy", server_id=20342, client_id=2951, prototype=1857,
         png="dark_hydra_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of a Dark Hydra. Hang it on a wall."),
    dict(name="root colossus trophy", server_id=20343, client_id=2906, prototype=1857,
         png="root_colossus_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of a Root Colossus. Hang it on a wall."),
    dict(name="emerald scarab trophy", server_id=20344, client_id=2852, prototype=1857,
         png="emerald_scarab_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of an Emerald Scarab. Hang it on a wall."),
    dict(name="frost dragon trophy", server_id=20345, client_id=2851, prototype=1857,
         png="frost_dragon_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of a Frost Dragon. Hang it on a wall."),
    dict(name="hellhound trophy", server_id=20346, client_id=3020, prototype=1857,
         png="hellhound_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of a Hellhound. Hang it on a wall."),
    dict(name="imperial hero trophy", server_id=20347, client_id=3002, prototype=1857,
         png="imperial_hero_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of an Imperial Hero. Hang it on a wall."),
    dict(name="red kongra trophy", server_id=20348, client_id=2984, prototype=1857,
         png="red_kongra_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of a Red Kongra. Hang it on a wall."),
    dict(name="elvenbane ranger trophy", server_id=20349, client_id=2971, prototype=1857,
         png="elvenbane_ranger_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of the Elvenbane Ranger. Hang it on a wall."),
    dict(name="elven archmage trophy", server_id=20350, client_id=2970, prototype=1857,
         png="elven_archmage_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of the Elven Archmage. Hang it on a wall."),
    dict(name="orc warchief trophy", server_id=20351, client_id=3077, prototype=1857,
         png="orc_warchief_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of the Orc Warchief. Hang it on a wall."),
    dict(name="thornwarden trophy", server_id=20352, client_id=3011, prototype=1857,
         png="thornwarden_trophy.png", decor=True, tiles=2, frames=3,
         descr="A trophy of the Thornwarden. Hang it on a wall."),
    # Luces de colores (nov 2026): candelabro 2042 / lámpara 2045 encendidos con la llama recoloreada
    # (make_color_lights.py), luz de color propia y sin pudrición (no se apagan). Los vende Obi.
    dict(name="blue candelabrum", server_id=20336, client_id=2825, prototype=2042,
         png="blue_candelabrum.png", decor=True, frames=2, light=(6, 17), nodecay=True,
         descr="A candelabrum burning with a blue flame."),
    dict(name="green candelabrum", server_id=20337, client_id=2821, prototype=2042,
         png="green_candelabrum.png", decor=True, frames=2, light=(6, 31), nodecay=True,
         descr="A candelabrum burning with a green flame."),
    # Luz fija de las ruinas élficas: mismo dibujo publicado que 20337.
    dict(name="elven sanctuary light", server_id=20353, client_id=2821, prototype=20337,
         png="green_candelabrum.png", decor=True, fixed=True, frames=2, light=(6, 31), nodecay=True,
         descr="An emerald flame bound to the elven ruins."),
    dict(name="violet candelabrum", server_id=20338, client_id=2818, prototype=2042,
         png="violet_candelabrum.png", decor=True, frames=2, light=(6, 113), nodecay=True,
         descr="A candelabrum burning with a violet flame."),
    dict(name="magenta lamp", server_id=20339, client_id=2814, prototype=2045,
         png="magenta_lamp.png", decor=True, frames=2, light=(6, 184), nodecay=True,
         descr="A lamp that glows magenta."),
    dict(name="cyan lamp", server_id=20340, client_id=2966, prototype=2045,
         png="cyan_lamp.png", decor=True, frames=2, light=(6, 29), nodecay=True,
         descr="A lamp that glows cyan."),
    # Regalos de nivel (nov 2026): una caja por nivel nuevo, por rango (Player::onLevelAdvance; se abren con
    # data/actions/scripts/level_gift.lua). El present 7.6 recoloreado (make_level_gifts.py) sobre el
    # teddy bear 2112: ítem suelto, no contenedor (no se puede llenar). Doc: docs/gameplay/LEVEL_UP_REWARDS.md.
    dict(name="novice gift", server_id=20354, client_id=5090, prototype=2112,
         png="level_gift_novice.png", decor=True,
         descr="A gift for reaching level 2-19. Use it to open it."),
    dict(name="adventurer gift", server_id=20355, client_id=5091, prototype=2112,
         png="level_gift_adventurer.png", decor=True,
         descr="A gift for reaching level 20-34. Use it to open it."),
    dict(name="veteran gift", server_id=20356, client_id=5092, prototype=2112,
         png="level_gift_veteran.png", decor=True,
         descr="A gift for reaching level 35-49. Use it to open it."),
    dict(name="champion gift", server_id=20357, client_id=5093, prototype=2112,
         png="level_gift_champion.png", decor=True,
         descr="A gift for reaching level 50-79. Use it to open it."),
    dict(name="heroic gift", server_id=20358, client_id=5094, prototype=2112,
         png="level_gift_heroic.png", decor=True, light=(2, 204),
         descr="A gift for reaching level 80-99. Use it to open it."),
    dict(name="legendary gift", server_id=20359, client_id=5095, prototype=2112,
         png="level_gift_legendary.png", decor=True, light=(3, 204),
         descr="A gift for reaching level 100+. Use it to open it."),

    # Mina enana: decoracion 8.60, sin stats ni movimiento.
    dict(name="mine rail north-south", server_id=20360, client_id=5096, prototype=1794,
         png="mine_rail_ns.png", decor=True, fixed=True,
         descr="Iron and timber from the dwarven copper mine."),
    dict(name="mine rail east-west", server_id=20361, client_id=5097, prototype=1794,
         png="mine_rail_ew.png", decor=True, fixed=True,
         descr="Iron and timber from the dwarven copper mine."),
    dict(name="mine rail south-east", server_id=20362, client_id=5098, prototype=1794,
         png="mine_rail_se.png", decor=True, fixed=True,
         descr="Iron and timber from the dwarven copper mine."),
    dict(name="mine rail south-west", server_id=20363, client_id=5099, prototype=1794,
         png="mine_rail_sw.png", decor=True, fixed=True,
         descr="Iron and timber from the dwarven copper mine."),
    dict(name="mine rail north-east", server_id=20364, client_id=5100, prototype=1794,
         png="mine_rail_ne.png", decor=True, fixed=True,
         descr="Iron and timber from the dwarven copper mine."),
    dict(name="mine rail north-west", server_id=20365, client_id=5101, prototype=1794,
         png="mine_rail_nw.png", decor=True, fixed=True,
         descr="Iron and timber from the dwarven copper mine."),
    dict(name="mine ore wagon", server_id=20366, client_id=5102, prototype=1285,
         png="mine_ore_wagon.png", decor=True, fixed=True,
         descr="Iron and timber from the dwarven copper mine."),
    dict(name="mine timber support", server_id=20367, client_id=5103, prototype=1515,
         png="mine_timber_support.png", decor=True, fixed=True, tiles=2,
         descr="Iron and timber from the dwarven copper mine."),
    dict(name="snowy cave entrance", server_id=20368, client_id=5104, prototype=485,
         png="snow_cave_entrance.png", decor=True, fixed=True, layers=2,
         descr="An icy opening surrounded by snow."),
    dict(name="frost mine rune", server_id=20369, client_id=5105, prototype=2301,
         png="frost_mine_rune.png", decor=True,
         descr="Shop-only PvP trap. Blue fire detonates when another player steps on it."),
    dict(name="frost mine", server_id=20370, client_id=5106, prototype=1492,
         png="frost_mine_fire.png", decor=True, fixed=True, nodecay=True, frames=2, light=(4, 137),
         descr="Blue fire. It arms after 1 second and fades after 30 seconds."),
    # Runas clásicas/modernas cuyos client ids originales (3156/3158/3161/3175/3202) se reutilizaron en mapa/cadáveres.
    dict(name="adevo grav vita", server_id=2269, client_id=5107, prototype=2285,
         png="wild_growth_rune.png", decor=True,
         descr=""),
    dict(name="adori frigo", server_id=2271, client_id=5108, prototype=2311,
         png="icicle_rune.png", decor=True,
         descr=""),
    dict(name="adori mas frigo", server_id=2274, client_id=5109, prototype=2304,
         png="avalanche_rune.png", decor=True,
         descr=""),
    dict(name="adori mas tera", server_id=2288, client_id=5110, prototype=2304,
         png="stone_shower_rune.png", decor=True,
         descr=""),
    dict(name="adori mas vis", server_id=2315, client_id=5111, prototype=2262,
         png="thunderstorm_rune.png", decor=True,
         descr=""),

]
# Muelle del depot y puentes (nov 2026): barandas, faroles y rampa de madera dibujados por dock_bridge_art.py
# (server 20282-20300, clients sacrificados anotados ahí). Doc: docs/items-and-map/TRANSICIONES_DEPOT.md.
from dock_bridge_art import dock_items  # noqa: E402
NEW_ITEMS += dock_items()
from river_grotto_assets import river_items  # noqa: E402
NEW_ITEMS += river_items()


def u16(payload: bytes | None) -> int | None:
    return struct.unpack("<H", payload)[0] if payload and len(payload) == 2 else None


def load_otb(path: Path):
    data = path.read_bytes()
    root, end = B.parse_node(data, 4)
    if end != len(data):
        raise SystemExit(f"{path}: bytes de más al final del items.otb")
    return data, root


def node_ids(node) -> tuple[int | None, int | None, str]:
    _flags, blocks = B.parse_item_props(node.props)
    name = B.get_block_payload(blocks, B.ITEM_ATTR_NAME) or b""
    return (u16(B.get_block_payload(blocks, B.ITEM_ATTR_SERVERID)), u16(B.get_block_payload(blocks, B.ITEM_ATTR_CLIENTID)),
            name.decode("latin-1"))


def sprite_records(png: Path, tiles: int | str = 1, frames: int = 1) -> list[bytes]:
    """Registros de sprite para un item 1x1, 2x2, 2x1 o 1x2. Con frames>1 el PNG
    apila los cuadros verticalmente, según la altura de cada cuadro.
    Los multi-sprite se parten en el orden del .dat: para 2x2 abajo-derecha,
    abajo-izquierda, arriba-derecha, arriba-izquierda; para 2x1 derecha, izquierda;
    para 1x2 abajo, arriba."""
    if frames > 1 and tiles not in (1, 2, "2x1", "1x2"):
        raise SystemExit(f"{png.name}: formato de animación no soportado: {tiles}")
    image = B.Image.open(png).convert("RGBA")
    if tiles == "2x1":
        size = (64, 32 * frames)
        boxes = [(x0, 32*f, x1, 32*(f+1)) for f in range(frames)
                 for x0, x1 in ((32, 64), (0, 32))]
    elif tiles == "1x2":
        size = (32, 64 * frames)
        boxes = [(0, y0+64*f, 32, y1+64*f) for f in range(frames)
                 for y0, y1 in ((32, 64), (0, 32))]
    elif frames > 1 and tiles == 1:
        size = (32, 32 * frames)
        boxes = [(0, 32 * f, 32, 32 * (f + 1)) for f in range(frames)]
    elif tiles == 2:
        base = [(32, 32, 64, 64), (0, 32, 32, 64), (32, 0, 64, 32), (0, 0, 32, 32)]
        size = (64, 64 * frames)
        boxes = [(x0, y0 + 64 * f, x1, y1 + 64 * f) for f in range(frames) for x0, y0, x1, y1 in base]
    else:
        size, boxes = (32, 32), None
    if image.size != size:
        raise SystemExit(f"{png.name}: mide {image.size}, tiene que ser {size[0]}x{size[1]}")
    image.putdata([(0, 0, 0, 0) if p[3] == 0 else (p[0], p[1], p[2], 255) for p in image.getdata()])
    if boxes is None:
        return [B.encode_sprite_record(image)]
    return [B.encode_sprite_record(image.crop(box)) for box in boxes]


# ---------- candidatos a sacrificar ----------

def candidates(things: Path, otb: Path, exclude_paths=()) -> list[tuple[int, list[int], str]]:
    entries, _tail = B.DatReader((things / "Tibia.dat").read_bytes()).read_item_entries()
    item_count = B.DatReader((things / "Tibia.dat").read_bytes()).item_count
    _data, root = load_otb(otb)
    c2s, s2c, c2n, c2flags, used_custom, targets = {}, {}, {}, {}, set(), set()
    for node in root.children:
        flags, blocks = B.parse_item_props(node.props)
        for attr, payload in blocks:
            if attr in (ITEM_ATTR_DECAY, ITEM_ATTR_DECAY2, ITEM_ATTR_ROTATETO) and len(payload) >= 2:
                targets.add(struct.unpack_from("<H", payload)[0])
        sid, cid, name = node_ids(node)
        if sid is None or cid is None:
            continue
        if sid >= 20100:
            used_custom.add(cid)
        c2s.setdefault(cid, set()).add(sid)
        s2c[sid] = cid
        c2flags[cid] = struct.unpack("<I", flags[:4])[0] if len(flags) >= 4 else 0
        if name:
            c2n[cid] = name
    map_ids = B.load_map_server_ids(B.MAP_OTBM)
    protected = B.build_protected_client_ids(map_ids, s2c, c2n)
    data, refs = ROOT / "server/YurOTS/ots/data", set()
    files = (list(data.glob("monster/*.xml")) + list(data.glob("npc/**/*.lua")) + list(data.glob("actions/**/*.lua"))
             + list(data.glob("actions/*.xml")) + list(data.glob("spells/**/*.lua")) + list((ROOT / "scripts").rglob("*.py"))
             + [data / "items/items.xml", data / "items/items-zagan-test.xml"])
    excluded = {Path(p).resolve() for p in exclude_paths}
    for f in files:
        if f.is_file() and f.resolve() not in excluded:
            refs |= {int(x) for x in re.findall(r"\b(\d{3,5})\b", f.read_text(errors="replace")) if 100 <= int(x) <= 20000}
    bad_name = re.compile(r"dead|skeleton|corpse|remains|body|blood|pool|fire|burning|slime|puddle|trail|ash|bones|carcass")
    taken = set(B.CORE_RESERVED_CLIENT_IDS) | set(B.EXTERNAL_CLIENT_IDS) | used_custom | {i["client_id"] for i in NEW_ITEMS}
    out = []
    free_new = [(e.client_id, [], "(libre, nuevo)") for e in entries
                if e.client_id >= FIRST_NEW_CLIENT_ID and e.raw == BLANK_DAT_ENTRY
                and e.client_id not in taken and e.client_id not in c2s]
    for e in entries:
        c = e.client_id
        if c > item_count or c >= FIRST_NEW_CLIENT_ID or c in taken or c in protected or len(e.sprite_ids) != 1:
            continue
        if not c2flags.get(c, 0) & FLAG_PICKUPABLE:
            continue
        sids, name = c2s.get(c, set()), c2n.get(c, "?")
        if not sids or bad_name.search(name.lower()) or c in refs:
            continue
        if any(s in refs or s in map_ids or s in targets for s in sids):
            continue
        out.append((c, sorted(sids), name))
    return free_new + sorted(out, reverse=True)


# ---------- aplicar ----------

def apply_things(things: Path, otb_root, dry: bool) -> list[str]:
    dat_path, spr_path = things / "Tibia.dat", things / "Tibia.spr"
    dat, spr = dat_path.read_bytes(), spr_path.read_bytes()
    reader = B.DatReader(dat)
    entries, tail = reader.read_item_entries()
    by_cid = {e.client_id: i for i, e in enumerate(entries)}
    spr_reader = B.SprReader(spr)
    records = [None] + [spr_reader.sprite_raw(i) for i in range(1, spr_reader.sprite_count + 1)]
    s2c = {}
    for node in otb_root.children:
        sid, cid, _name = node_ids(node)
        if sid is not None and cid is not None:
            s2c.setdefault(sid, cid)
    new_entries, log, changed = [e.raw for e in entries], [], False
    item_count = reader.item_count
    if item_count < LAST_CLIENT_ID:
        added = list(range(item_count + 1, LAST_CLIENT_ID + 1))
        new_entries += [BLANK_DAT_ENTRY] * len(added)
        for cid in added:
            by_cid[cid] = len(entries)
            entries.append(B.DatItemEntry(client_id=cid, prefix=BLANK_DAT_ENTRY[:-2], sprite_ids=[0],
                                          raw=BLANK_DAT_ENTRY))
        item_count = LAST_CLIENT_ID
        changed = True
        log.append(f"  client ids nuevos {added[0]}-{added[-1]}: {len(added)} entradas vacías al final de los ítems")
    for item in NEW_ITEMS:
        tiles = item.get("tiles", 1)
        frames = item.get("frames", 1)
        layers = item.get("layers", 1)
        per_frame = 2 if tiles in ("2x1", "1x2") else 4 if tiles == 2 else 1
        sprite_count = per_frame * frames * layers
        # Capas nativas (puertas): dentro de cada cuadro, apiladas verticalmente.
        # El prefijo del prototipo conserva la cantidad real de capas/cuadros.
        new_records = sprite_records(SPRITES / item["png"], tiles, frames * layers)
        idx = by_cid.get(item["client_id"])
        proto_cid = s2c.get(item.get("appearance", item["prototype"]))
        if idx is None or proto_cid not in by_cid:
            raise SystemExit(f"{things}: falta el client id {item['client_id']} o el del prototipo {item['prototype']}")
        proto = entries[by_cid[proto_cid]]
        if len(proto.sprite_ids) != sprite_count:
            raise SystemExit(f"prototipo {item['prototype']} tiene {len(proto.sprite_ids)} sprites, se esperaban {sprite_count}")
        new_prefix = ground_overlay(proto.prefix) if item.get("ground_overlay") else proto.prefix
        if "light" in item:
            new_prefix = with_light(new_prefix, *item["light"])
        current = entries[idx]
        if (len(current.sprite_ids) == sprite_count and current.prefix == new_prefix
                and all(records[current.sprite_ids[i]] == new_records[i] for i in range(sprite_count))):
            log.append(f"  {item['name']}: ya está (client {item['client_id']}, sprite {current.sprite_ids[0]})")
            continue
        new_sprite_ids = list(range(len(records), len(records) + sprite_count))
        records.extend(new_records)
        new_entries[idx] = new_prefix + struct.pack(f"<{sprite_count}H", *new_sprite_ids)
        changed = True
        log.append(f"  {item['name']}: client {item['client_id']} -> sprites nuevos {new_sprite_ids}")
    if changed and not dry:
        new_dat = B.write_dat(reader.signature, item_count, reader.outfit_count, reader.effect_count,
                              reader.missile_count, new_entries, tail)
        # validar antes de tocar los archivos: que el .dat nuevo parsea entero, con las
        # mismas entradas byte a byte y el mismo tail (outfits/efectos/proyectiles
        # intactos). Un prefijo mal armado (p. ej. sin las dimensiones tras el 0xFF)
        # desincroniza todo el .dat.
        try:
            re_entries, re_tail = B.DatReader(new_dat).read_item_entries()
        except (struct.error, IndexError) as ex:
            raise SystemExit(f"{things}: el .dat reescrito no parsea ({ex}); no se escribe nada") from ex
        if [e.raw for e in re_entries] != new_entries or re_tail != tail:
            raise SystemExit(f"{things}: el .dat reescrito no parsea igual que el original; no se escribe nada")
        for path in (dat_path, spr_path):
            backup = path.with_name(path.name + ".bak-custom-items")
            if not backup.exists():
                shutil.copy2(path, backup)
        dat_path.write_bytes(new_dat)
        spr_path.write_bytes(B.write_spr(spr_reader.signature, records))
    return log


def apply_otb(path: Path, dry: bool) -> list[str]:
    data, root = load_otb(path)
    by_sid = {}
    for node in root.children:
        sid, _cid, _name = node_ids(node)
        if sid is not None:
            by_sid.setdefault(sid, node)
    log, changed = [], False
    for item in NEW_ITEMS:
        proto = by_sid.get(item["prototype"])
        if proto is None:
            raise SystemExit(f"{path}: no está el prototipo {item['prototype']}")
        flags, blocks = B.parse_item_props(proto.props)
        if item.get("fixed"):
            # Versión de exhibición: mismo dibujo, pero el server no deja moverla ni levantarla.
            f = struct.unpack("<I", flags)[0] & ~(FLAG_MOVEABLE | FLAG_PICKUPABLE)
            flags = struct.pack("<I", f)
        if item.get("corpse") or item.get("decor"):
            pass  # contenedor/decoración: se copian flags/capacidad del prototipo sin tocar stats
        elif "armor" in item:
            armor = B.get_block_payload(blocks, ITEM_ATTR_ARMOR2)
            if not armor or len(armor) != 12:
                raise SystemExit(f"prototipo {item['prototype']} sin bloque de armadura")
            blocks = B.upsert_block(blocks, ITEM_ATTR_ARMOR2, struct.pack("<H", item["armor"]) + armor[2:])
        else:
            weapon = B.get_block_payload(blocks, ITEM_ATTR_WEAPON2)
            if not weapon or len(weapon) != 5:
                raise SystemExit(f"prototipo {item['prototype']} sin bloque de arma")
            blocks = B.upsert_block(blocks, ITEM_ATTR_WEAPON2, weapon[:3] + bytes([item["attack"], item["defence"]]))
        if item.get("nodecay"):
            # Siempre igual: sin pudrición (las luces de color no se apagan solas como el candelabro base).
            blocks = [(a, p) for a, p in blocks if a not in (ITEM_ATTR_DECAY, ITEM_ATTR_DECAY2)]
        if "light" in item:
            # la luz vive en el OTB como ITEM_ATTR_LIGHT2 (0x2A): u16 nivel + u16 color
            blocks = B.upsert_block(blocks, ITEM_ATTR_LIGHT2, struct.pack("<HH", *item["light"]))
        descr = item["descr"].encode("latin-1")
        if len(descr) >= 128:
            raise SystemExit(f"descripción de {item['name']} demasiado larga ({len(descr)} bytes, máximo 127)")
        blocks = B.upsert_block(blocks, B.ITEM_ATTR_SERVERID, struct.pack("<H", item["server_id"]))
        blocks = B.upsert_block(blocks, B.ITEM_ATTR_CLIENTID, struct.pack("<H", item["client_id"]))
        blocks = B.upsert_block(blocks, B.ITEM_ATTR_NAME, item["name"].encode("latin-1"))
        # Legacy Items::loadFromOtb rejects a zero-byte final attribute.
        if descr:
            blocks = B.upsert_block(blocks, B.ITEM_ATTR_DESCR, descr)
        else:
            blocks = [(a, p) for a, p in blocks if a != B.ITEM_ATTR_DESCR]
        new_node = B.Node(node_type=proto.node_type, props=B.build_item_props(flags, blocks), children=[])
        old = by_sid.get(item["server_id"])
        if old is not None and old.props == new_node.props:
            log.append(f"  {item['name']}: ya está (server {item['server_id']})")
            continue
        if old is not None:
            root.children[root.children.index(old)] = new_node
            log.append(f"  {item['name']}: server {item['server_id']} actualizado")
        else:
            root.children.append(new_node)
            stats = ("corpse" if item.get("corpse") else
                     "decoración" if item.get("decor") else
                     f"arm {item['armor']}" if "armor" in item else
                     f"atk {item['attack']} def {item['defence']}")
            log.append(f"  {item['name']}: server {item['server_id']} nuevo (client {item['client_id']}, "
                       f"prototipo {item['prototype']}, {stats})")
        changed = True
    if changed and not dry:
        backup = path.with_name(path.name + ".bak-custom-items")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_bytes(data[:4] + B.write_node(root))
    return log


def main() -> int:
    global NEW_ITEMS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--things", type=Path, action="append", default=[], help="carpeta con Tibia.dat y Tibia.spr (repetible)")
    ap.add_argument("--otb", type=Path, action="append", default=[], help="items.otb del servidor (repetible)")
    ap.add_argument("--candidates", action="store_true", help="listar client ids que se pueden sacrificar")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", type=int, nargs="+", help="instalar solo estos server ids (sin reconstruir otros assets)")
    a = ap.parse_args()
    if a.only:
        selected = set(a.only)
        unknown = selected - {i["server_id"] for i in NEW_ITEMS}
        if unknown:
            raise SystemExit(f"server ids desconocidos: {sorted(unknown)}")
        NEW_ITEMS = [i for i in NEW_ITEMS if i["server_id"] in selected]
    otbs = a.otb or [ROOT / "server/YurOTS/ots/data/items/items-zagan-test.otb"]
    if a.candidates:
        rows = candidates(ROOT / "devtools/rme/rme-client-760", otbs[0])
        free = [r for r in rows if not r[1]]
        print(f"{len(free)} client ids nuevos libres"
              + (f" ({free[0][0]}-{free[-1][0]}); usar estos primero" if free else
                 ": no hay (correr el instalador con --things para agregarlos)"))
        for row in free[:10]:
            print(" ", *row)
        sac = rows[len(free):]
        print(f"{len(sac)} client ids viejos se pueden sacrificar (client, server ids, nombre):")
        for row in sac[:20]:
            print(" ", *row)
        return 0
    _data, otb_root = load_otb(otbs[0])
    for things in a.things:
        print(f"{things}:")
        print("\n".join(apply_things(things, otb_root, a.dry_run)))
    for otb in otbs:
        print(f"{otb}:")
        print("\n".join(apply_otb(otb, a.dry_run)))
    if a.dry_run:
        print("dry-run: no se escribió nada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
