# Índice de documentación — Yurots

Índice maestro de toda la documentación del proyecto. Organizado por dominio.
Para un overview del repo ver `../README.md`. Para diagnóstico rápido de cuelgues empezar por `../LEERCODEX.md`.

## Leer primero

Antes de tocar cualquier cosa, leer en este orden:

| # | Documento | Cuándo leerlo |
|---|-----------|---------------|
| 1 | [`../LEERCODEX.md`](../LEERCODEX.md) | Siempre primero. Punto de entrada rápido para IAs, diagnóstico de cuelgues OT. |
| 2 | [`PROYECTO.md`](PROYECTO.md) | Para entender la arquitectura general, deploy, data sagrada, decisiones de diseño. |
| 3 | [`../AGENTS.md`](../AGENTS.md) | Si sos un agente AI: instrucciones operativas, restricciones, convenciones. |
| 4 | [`systems/THINKPAD_TEST_SERVER.md`](systems/THINKPAD_TEST_SERVER.md) | Antes de cualquier deploy. No hay producción por ahora; el único servidor es el de la ThinkPad. |
| 5 | [`INDEX.md`](INDEX.md) | Este archivo. Mapa completo de la documentación. |

---

## Operación y setup

Docs operativos planos. Setup, deploy, cliente, smoke tests, migración.

| Doc | Cubre / cuándo leerlo |
|-----|-----------------------|
| [`SETUP.md`](SETUP.md) | Setup inicial del entorno de desarrollo local. |
| [`RME_SETUP.md`](RME_SETUP.md) | Configurar el editor de mapa (RME) en macOS/Linux. |
| [`CAMBIAR-MAPA.md`](CAMBIAR-MAPA.md) | Procedimiento para cambiar/actualizar el mapa del servidor. |
| [`CLIENT.md`](CLIENT.md) | Todo sobre el cliente custom Tibia 7.6. |
| [`CLIENT_UPDATER_RETRO76.md`](CLIENT_UPDATER_RETRO76.md) | Auto-actualización del cliente (funcionando): cómo publicar sprites/módulos nuevos con `publish_client.py`. |
| [`PVP_SYSTEM.md`](PVP_SYSTEM.md) | Reglas, balance y configuración del sistema PvP. |
| [`TRADE_SYSTEM.md`](TRADE_SYSTEM.md) | Sistema de trade entre jugadores. |
| [`CHARACTER_SESSION_REPLACEMENT.md`](CHARACTER_SESSION_REPLACEMENT.md) | Reemplazo de sesión de personaje, recovery de cuentas. |
| [`SMOKE_TESTS.md`](SMOKE_TESTS.md) | Tests de humo locales antes de cada release. |
| [`MIGRATION_PLAYBOOK.md`](MIGRATION_PLAYBOOK.md) | Playbook para migraciones grandes (esquema DB, data, deploys críticos). |
| [`_archive/DEPLOY-PENDIENTE-VPS-JUL2026.md`](_archive/DEPLOY-PENDIENTE-VPS-JUL2026.md) | *(archivado)* Snapshot jul 2026: qué faltaba deployar al VPS. |
| [`_archive/PUSH-MAIN-JUL2026-SPELLS-NPC-NO-VPS.md`](_archive/PUSH-MAIN-JUL2026-SPELLS-NPC-NO-VPS.md) | *(archivado)* Push a main jul 2026 sin VPS (spells/NPC). |

---

## Sistemas y estabilidad

Todo lo relacionado con estabilidad del OT server, cuelgues, sockets, crashes.

| Doc | Cubre / cuándo leerlo |
|-----|-----------------------|
| [`systems/THINKPAD_TEST_SERVER.md`](systems/THINKPAD_TEST_SERVER.md) | **Servidor de prueba en la ThinkPad** (el único servidor por ahora; no hay producción): acceso, cuenta GM, cómo deployar cambios de datos sin pisar el trabajo sin commitear de otras sesiones, historial de deploys. |
| [`systems/PREVENT_OT_HANGS.md`](systems/PREVENT_OT_HANGS.md) | Si el server se cuelga o se observa lentitud: checklist preventivo. |
| [`systems/CRASH_DIAGNOSTICS.md`](systems/CRASH_DIAGNOSTICS.md) | Si el OT crashea: cómo recolectar diagnóstico y encontrar la causa. |
| [`systems/SOCKET_DEBUG_LOGGING.md`](systems/SOCKET_DEBUG_LOGGING.md) | Si hay kicks masivos, desconexiones o problemas de socket. |
| [`systems/OT_HANG_ROOT_CAUSE_SEND_BLOCKING.md`](systems/OT_HANG_ROOT_CAUSE_SEND_BLOCKING.md) | Análisis técnico de la causa raíz del cuelgue por send blocking. |
| [`systems/LIMPIEZA_CODIGO_NOV2026.md`](systems/LIMPIEZA_CODIGO_NOV2026.md) | Limpieza del C++ (opciones de compilación, Windows, código comentado), binarios fuera de git, caché de la web, pendientes. Reglas para no volver a ensuciarlo y cómo comprobar sin compilar. |
| [`systems/SANITIZER_TESTS.md`](systems/SANITIZER_TESTS.md) | Buscar errores de memoria del servidor: binario con AddressSanitizer/UBSan sobre una copia de los datos + bots (`exercise-server.py`). Qué encontró en nov 2026 y las tres cuentas de azar pendientes de decisión. |
| [`systems/LOGIN_EVENTS.md`](systems/LOGIN_EVENTS.md) | Registro de logins y cuentas nuevas: embudo, retención, fallos por motivo, fuerza bruta. |

---

## Gameplay y mecánicas

Mecánicas in-game, rates, sistemas de entrenamiento, objetos de gameplay.

| Doc | Cubre / cuándo leerlo |
|-----|-----------------------|
| [`gameplay/EXPEDITION_SUPPLIES.md`](gameplay/EXPEDITION_SUPPLIES.md) | Suministros de Seller para primeras hunts: Delver Kit, Trail Boots y vendajes apilables. |
| [`gameplay/EXP_RATE.md`](gameplay/EXP_RATE.md) | Tiers de experiencia por nivel (`expmul`). |
| [`gameplay/PARTY_EXP.md`](gameplay/PARTY_EXP.md) | **Exp compartida y bonus en party:** reparto entre miembros vivos cerca (≤30 sqm, ±1 piso), +25/+50/+75 % con 2/3/4+ miembros y doble texto flotante (blanco + celeste `+X`). |
| [`gameplay/ML_RATE.md`](gameplay/ML_RATE.md) | Configuración y tuning del rate de magic level. |
| [`gameplay/REGEN_FOOD.md`](gameplay/REGEN_FOOD.md) | Sistema de regeneración vía comida. |
| [`gameplay/RAGE_MONSTERS.md`](gameplay/RAGE_MONSTERS.md) | Mecánica de monstruos enraged. |
| [`gameplay/RESPAWN_SYSTEM.md`](gameplay/RESPAWN_SYSTEM.md) | Funcionamiento real del respawn de monstruos, visibilidad, timers y acumulacion por kiteo fuera del area. |
| [`gameplay/MONSTER_CREATION.md`](gameplay/MONSTER_CREATION.md) | Flujo completo para crear monstruos nuevos: XML, alta en `monsters.xml`, RME y spawns. |
| [`gameplay/CUSTOM_MONSTER_WORKFLOW.md`](gameplay/CUSTOM_MONSTER_WORKFLOW.md) | Monstruo custom paso a paso: diseño, hechizos propios, sprite nuevo (looktype), arte web con nano banana, pruebas y deploy. Caso Black Dragon. |
| [`gameplay/SPRITE_RECOLOR_GUIDE.md`](gameplay/SPRITE_RECOLOR_GUIDE.md) | **Receta para crear o editar el sprite de una criatura:** comandos en orden (`sprite_tool.py`), plantilla de preset, trucos, umbrales de cada base y errores conocidos. |
| [`gameplay/SPRITE_BASES.md`](gameplay/SPRITE_BASES.md) | Catálogo generado de las criaturas que sirven de base para un sprite: forma, quién la usa, colores y si ya está estudiada (`sprite_tool.py bases --write`). |
| [`gameplay/BLACK_DRAGON.md`](gameplay/BLACK_DRAGON.md) | Black Dragon: stats, aliento oscuro y sprite propio (looktype 230, requiere actualizar el cliente). |
| [`gameplay/FROST_DRAGON.md`](gameplay/FROST_DRAGON.md) | Frost Dragon: dragón de hielo sin fuego (aliento helado, bola de nieve, ventisca), look 231 recoloreado del Dragon. |
| [`gameplay/ICE_MONK.md`](gameplay/ICE_MONK.md) | Ice Monk: monje-mago de hielo a distancia, look 232 (Monk recoloreado), hechizos y sprite. |
| [`gameplay/DROWNED_SAILOR.md`](gameplay/DROWNED_SAILOR.md) | Drowned Sailor: marinero ahogado del naufragio, look 233 (Crypt Shambler recoloreado), algas que inmovilizan 1 s. |
| [`gameplay/TIDE_PRIEST.md`](gameplay/TIDE_PRIEST.md) | Tide Priest: sacerdote de la marea del naufragio, look 234 (Necromancer recoloreado con fuego de San Telmo), saca maná y llama Drowned Sailors. |
| [`gameplay/BLUE_ELF_ARCANIST.md`](gameplay/BLUE_ELF_ARCANIST.md) | Blue Elf Arcanist: variante cosmética azul del Elf Arcanist (looktype 63, paleta 33/106/68/124, sin cliente nuevo). |
| [`gameplay/ICE_SPIDER.md`](gameplay/ICE_SPIDER.md) | Ice Spider: variante de hielo del Giant Spider, más fuerte (1800 HP, 1400 exp, ice ball + blizzard, looktype 235 recoloreado, requiere cliente nuevo). |
| [`gameplay/DARK_HYDRA.md`](gameplay/DARK_HYDRA.md) | Dark Hydra: variante de caza de Hydra, 3200 HP / 3000 exp, aliento de drenaje y look 241 carbón/violeta con marcas arcanas. |
| [`gameplay/MONSTRUOS.md`](gameplay/MONSTRUOS.md) | **Catálogo de todos los monstruos** (generado con `scripts/monsters/monster-catalog.py --write`): originales de YurOTS, traídos de 8.60 y creados acá, con vida/exp, sprite, cadáver, dónde spawnean y su doc; y cómo se hacen los cadáveres propios (`creature_corpses.py`). |
| [`gameplay/MONSTER_LOOT_SIMULATION.md`](gameplay/MONSTER_LOOT_SIMULATION.md) | **Simulación de loot (1.000 kills) y balance:** auditoría de los 544 monstruos (HP, ataques, nota de dificultad, valor esperado/simulado NPC y total), ajustes de balance, asignación de drops Zagan y expansión de Mad/Parived. |
| [`gameplay/ARMAS.md`](gameplay/ARMAS.md) | **Catálogo de las armas propias** (generado con `scripts/items/weapon-catalog.py --write`): Melee Relics, El Crisol, Paladin Stars, armas PvP, wands, armas 8.x y demás, con hoja de imágenes, ataque/defensa, efecto, de dónde salen (loot, quest) y su doc. |
| [`gameplay/METAL_MONSTERS.md`](gameplay/METAL_MONSTERS.md) | Metal Dragon, Metal Hydra y Metal Demon: monstruos cyborg (acero negro + neón), looks 186–188, cadáveres metálicos 20225–20227, láser/ácido/plasma/descarga, variantes rage; spawn en el Valle de las Bestias y el Inferno. |
| [`gameplay/EMERALD_SCARAB.md`](gameplay/EMERALD_SCARAB.md) | Emerald Scarab: variante de Ancient Scarab, 1500 HP / 1150 exp, estallido de veneno y look 242 esmeralda/dorado con gema en el lomo. |
| [`gameplay/RED_KONGRA.md`](gameplay/RED_KONGRA.md) | Red Kongra: variante carmesí del Kongra, 600 HP / 230 exp, rugido + prisa (kit) y look 254 con ojos ámbar encendidos (requiere actualizar el cliente). |
| [`gameplay/ROOT_COLOSSUS.md`](gameplay/ROOT_COLOSSUS.md) | Root Colossus: guardián vegetal (look 243), 4800 HP / 3400 exp, raíces y esporas; spawn local al final de la progresión del Abismo del Valle de las Bestias, con rootcleaver (axe 1H) y heartwood maul (club 2H) de loot raro. |
| [`gameplay/PETRIFIED_SANCTUARY.md`](gameplay/PETRIFIED_SANCTUARY.md) | Santuario bajo el lago élfico: Gargoyles, golems y Crystal Spiders; Custodio del Lago (look 229), accesos, loot y regeneración. |
| [`gameplay/DWARVEN_MINE.md`](gameplay/DWARVEN_MINE.md) | Mina Enana junto al camino al desierto: galerías z9/z10 con Dwarfs, Soldiers, Guards, Geomancers y Capataz de Hierro (look 189); rieles y vagonetas 8.60. |
| [`gameplay/CLIENT_EFFECTS.md`](gameplay/CLIENT_EFFECTS.md) | Efectos y proyectiles nuevos del cliente por recoloreo (pack "ice": `NM_ME_ICE_*`, `NM_ANI_FROSTBALL`), límites y cómo agregar packs. |
| [`gameplay/HELL_QUEST.md`](gameplay/HELL_QUEST.md) | **Hell Quest** (Isla del Infierno): caza en 3 pisos, puertas de nivel 80/100, boss **Ashen Lord** y Cámara de la Elección (4 cofres, se elige uno); criatura nueva **Hellhound** (`generate-hell-quest.py`). |
| [`gameplay/QUESTS.md`](gameplay/QUESTS.md) | **Registro de quests**: 40 cofres agrupados en 25 quests + 5 sistemas, niveles recomendados, ubicaciones, recompensas y 9 propuestas de quests nuevas. Página pública `/quests` (datos en `web/site/src/data/quests.json`). |
| [`gameplay/QUEST_BOOTS_OF_HASTE.md`](gameplay/QUEST_BOOTS_OF_HASTE.md) | **Quest de Boots of Haste / Cripta de Raíces** (casa de teleports al sur del depot): 7 salas, monstruos y visual propia de piedra/musgo/ámbar; nivel recomendado 80–100. |
| [`gameplay/IMPERIAL_CASTLE.md`](gameplay/IMPERIAL_CASTLE.md) | **Castillo Imperial** (isla al noroeste del templo): 6 pisos de dificultad creciente, jefe **The Fallen Emperor** (look 244), **Imperial Hero** (look 240), Imperial Archer, Court Mage e Imperial Squire, y quest de 2 cofres en la tesorería (`generate-imperial-castle.py`). |
| [`gameplay/DESERT_HUNTS.md`](gameplay/DESERT_HUNTS.md) | **Desierto de las Ruinas** (isla de arena al este): la ciudad del desierto sin casas ni NPC, con 9 zonas de caza de nivel 8 a 90, jefes Furious Ancient Scarab y Omruc y 2 cofres de quest (`generate-desert-hunts.py`). |
| [`gameplay/IMPORTAR_CRIATURA_DE_OTRA_VERSION.md`](gameplay/IMPORTAR_CRIATURA_DE_OTRA_VERSION.md) | **Criaturas de otra versión** (cliente 8.60): `import_client_look.py`, las 25 importadas (piratas, Wyvern, hatchlings, mutated, chakoyas, bárbaros, gigantes y golems de hielo, Crystal Spider, Bog Raider), los 19 looks restantes (tortugas, mammoth, blood crab, quaras, Cyclops Smith/Drone, Wyrm, elementales, Zombie, Vampire Bride, Worker Golem, Undead Gladiator, Nightstalker) con stats, corpses, spawn y cómo sumar más. |
| [`gameplay/MONSTER_KITS.md`](gameplay/MONSTER_KITS.md) | **Kits de ataque de los monstruos nuevos** (Castillo Imperial y criaturas de 8.60): hielo, cañonazos, rugidos... con daño escalado (`apply-monster-kits.py`). Los de siempre no se tocan. |
| [`gameplay/POWER_HIT.md`](gameplay/POWER_HIT.md) | **Power hit**: todo ataque de jugador puede salir ×1,5 (8%) o ×2,5 (1%, *mega*) con efecto dorado/fucsia propio (pack `power`); se ajusta en `config.lua`. |
| [`gameplay/BOAT_TRAVEL.md`](gameplay/BOAT_TRAVEL.md) | Viajes de Nimral/Fargum: destinos (incl. Gauntlet), Hell Quest, confirmación y reglas de temple. |
| [`gameplay/MOST_WANTED_SYSTEM.md`](gameplay/MOST_WANTED_SYSTEM.md) | Sistema de bounty / most wanted entre jugadores. |
| [`gameplay/DAILY_TASK.md`](gameplay/DAILY_TASK.md) | **Daily Task (Huntmaster):** 3 contratos/día por rango de level, kills + oro o exp, streak. |
| [`gameplay/STAIRS.md`](gameplay/STAIRS.md) | Escaleras, escaleras de mano, trampillas y agujeros al usarlos con click derecho; dónde se aterriza. |
| [`gameplay/GEMS.md`](gameplay/GEMS.md) | Sistema de gemas: drop, uso, imbuements. Antes de tocar gemas, leer esto. |
| [`gameplay/CRYSTAL_ARROW.md`](gameplay/CRYSTAL_ARROW.md) | **Crystal Arrow (2352):** throwable tipo spear, Blue Gem speed ×5, hit 85%; spears 70% hit. |
| [`gameplay/PALADIN_STARS.md`](gameplay/PALADIN_STARS.md) | Gale, Venom y Storm Star: tres arrojadizas reutilizables para paladín, velocidad/veneno/energía y proyectiles propios. |
| [`gameplay/THROWING_FIREBALL.md`](gameplay/THROWING_FIREBALL.md) | Throwable Fireball: arrojadiza basada en la Snowball, con ítem animado y proyectil con estela de brasas. |
| [`gameplay/MELEE_RELICS.md`](gameplay/MELEE_RELICS.md) | Riftblade (combo de tres golpes), Aethercleaver (maná por daño real) y Graviton Maul (crush según armadura); sprites e impactos propios. |
| [`gameplay/QUICKSILVER_KATANA.md`](gameplay/QUICKSILVER_KATANA.md) | Katana de una mano (20660), ataque 32, defensa 16 y golpes cada 650 ms. |
| [`gameplay/DARK_SPIDER.md`](gameplay/DARK_SPIDER.md) | Dark Spider de 3.400 HP y velocidad 355 en Duskweb Hollow. |
| [`gameplay/ENCHANTED_SPEAR.md`](gameplay/ENCHANTED_SPEAR.md) | **Enchanted Spear (20156):** spear mejorada (ataque 36, 80% hit, no se apila), sprite de cristal y luz de color propia; 4 estilos; proyectil propio `NM_ANI_ENCHANTED_SPEAR` (16) con luz en vuelo. |
| [`gameplay/DEPOTS.md`](gameplay/DEPOTS.md) | **Depots:** lockers 2589, XML vs mapa, incidente jul 2026, checklist pre-deploy de mapa. |
| [`items-and-map/DEPOT_ELECTRICO.md`](items-and-map/DEPOT_ELECTRICO.md) | **Depot eléctrico** (y la calavera cian, reemplazada por la negra el 19 nov: ver `gameplay/PINK_SKULL.md`): 30 piezas propias para paredes, ventanas y remates del depot completo (229 piezas en mapa), IDs 20200–20210 y 20420–20438; fuentes del arte, renders y conservación de lockers. |
| [`gameplay/GM_INVISIBLE.md`](gameplay/GM_INVISIBLE.md) | **`/invisible` del GM** (nov 2026): pasa por encima de jugadores y monstruos, nadie choca con él y se ve a sí mismo como un Ghost (looktype 48). |
| [`gameplay/GM_COMANDOS.md`](gameplay/GM_COMANDOS.md) | **Comandos de GM para probar contenido** (nov 2026): `/god` (apagar la protección), `/ir` (lugares de `data/gmplaces.xml`), `/i` por nombre, `/nivel`, `/skill`, `/ml`, `/loot` (simula N muertes), `/matar`, `/speed` y el look de GM con ids, action/unique id y la casilla. |
| [`gameplay/HOUSES.md`](gameplay/HOUSES.md) | **Casas:** dueños en `data/houses/*.xml`, deploy, backup/recuperación, **items fantasma** (caso Maximus `166,39,7` jul 2026). |
| [`gameplay/HANGABLES.md`](gameplay/HANGABLES.md) | **Tapestries en las paredes**: los ítems `hangable` se cuelgan en paredes con gancho; en las casas se guardan y solo los mueven dueño e invitados. |
| [`gameplay/AOL_RARES.md`](gameplay/AOL_RARES.md) | **AOL y armas rare no se llevan juntos**: bloqueo al mover y al comprar el AOL; al morir con los dos, el AOL no protege. |
| [`gameplay/EQUIP_SWAP.md`](gameplay/EQUIP_SWAP.md) | **Cambiar equipo arrastrando**: un ítem de la mochila sobre un slot ocupado los intercambia; el GM usa todos los ítems. |
| [`gameplay/GOLDEN_ACCESSORIES.md`](gameplay/GOLDEN_ACCESSORIES.md) | Golden amulet y golden ring: auto-bank, bonus de oro e interacción entre ambos. |
| [`gameplay/SOFT_BOOTS.md`](gameplay/SOFT_BOOTS.md) | **Soft Boots (2640):** +3 HP / +12 MP cada 3 s, 4 h de uso → worn (2641), recarga con Azure Sunstone (`20124`). |
| [`gameplay/NPC_SYSTEM.md`](gameplay/NPC_SYSTEM.md) | **NPCs:** cómo se cargan, componentes de `lib/npc/`, `npcDefine`, recetas, API C++, lista de NPCs y pruebas sin servidor (`scripts/npc/run_npc_tests.py`). |
| [`gameplay/NPC_CONFIRMATION.md`](gameplay/NPC_CONFIRMATION.md) | Confirmación de transacciones con NPC (anti-misflow). |
| [`gameplay/SELLER_FLUIDS.md`](gameplay/SELLER_FLUIDS.md) | Sistema de vendedores de fluids/potions. |
| [`gameplay/DARK_RODO_RUNE_BACKPACKS.md`](gameplay/DARK_RODO_RUNE_BACKPACKS.md) | Backpacks especiales de runas y Dark Rodo. |
| [`gameplay/RUNE_WEIGHT_RL.md`](gameplay/RUNE_WEIGHT_RL.md) | Peso de runas y lógica RL asociada. |
| [`gameplay/DESINTEGRATE_RUNE.md`](gameplay/DESINTEGRATE_RUNE.md) | Implementación real de la rune Desintegrate: magic wall, wild growth y objetos destruibles. |
| [`gameplay/SPELL_RUNTIME.md`](gameplay/SPELL_RUNTIME.md) | **Spells/runas:** carga XML→Lua, `safeCast` anti-crash, restauración Soulfire/Paralyze/etc. (jul 2026). Leer antes de tocar `spells.xml` / `spells.cpp`. |
| [`gameplay/SPELL_EXHAUSTION.md`](gameplay/SPELL_EXHAUSTION.md) | **Exhausted:** ofensivo 2 s / no-ofensivo 1 s, sin `exhaustedadd` en casts, bindings Paralyze/Anchor/etc. con exhaust compartido, visibilidad say. |
| [`gameplay/SERVER_LANGUAGE.md`](gameplay/SERVER_LANGUAGE.md) | Idioma visible del juego: inglés; 77 carteles, NPCs, arenas, mensajes C++ y ayuda GM. Comandos `!sponsor`, `/go`, `/level`, `/killmonsters`, `/help`; alias anteriores compatibles. |
| [`gameplay/READABLES.md`](gameplay/READABLES.md) | **Cartas, scrolls y libros:** leer/escribir según el `items.otb`, `scrolltexts.xml` del piso, ids. |
| [`gameplay/MAGIC_WALL.md`](gameplay/MAGIC_WALL.md) | **Magic Wall:** duración 15s, `DECAY_INTERVAL`, bug de relanzar sin reiniciar timer (jul 2026). |
| [`gameplay/LEVEL_UP_REWARDS.md`](gameplay/LEVEL_UP_REWARDS.md) | Subir de nivel: efecto 50 y "LEVEL UP" que ven todos, una caja de regalo por nivel (6 rangos, oro / ítem / raro) y aviso a todo el server de los raros (cajas y monstruos). Prueba con bots `test-level-gifts.py`. |
| [`gameplay/PADRINAZGO.md`](gameplay/PADRINAZGO.md) | Padrinazgo (`!padrino`): un nuevo (nivel ≤ 15) elige padrino (nivel ≥ 30); al llegar a 20/35/50/80/100 los dos ganan oro y caja, aviso a todos. `data/sponsors.xml` runtime. Prueba con bots `test-sponsor.py`. |
| [`gameplay/SUMMONS.md`](gameplay/SUMMONS.md) | Summons de jugadores: velocidad del dueño, siempre un paso detrás, cambian de lugar al darse vuelta y aparecen a su lado al cambiar de piso. Prueba con bots `test-summon-follow.py`. |
| [`gameplay/ANCHOR_RUNE.md`](gameplay/ANCHOR_RUNE.md) | Anchor Rune (2296): root de 1s (no paralyze) para war/combos. |
| [`gameplay/FROST_MINE.md`](gameplay/FROST_MINE.md) | Frost Mine Rune (20369): comprable en Dark Rodo, fuego azul 20370, una detonación al pisar otro jugador; solo PvP, 1 s de armado, 30 s y límite de 3. |
| [`gameplay/CRIMSON_CAGE_RUNE.md`](gameplay/CRIMSON_CAGE_RUNE.md) | Crimson Cage Rune (20273, `adevo grav res`): encierra al blanco en 8 paredes rojas por 3 s (evento propio, no el decay de 5 s). |
| [`gameplay/SPELL_CAST_VISIBILITY.md`](gameplay/SPELL_CAST_VISIBILITY.md) | Visibilidad del cast de hechizos (efectos visuales). |
| [`gameplay/SPELL_EXORI_GRAN.md`](gameplay/SPELL_EXORI_GRAN.md) | Hechizo exori gran: balance, área, daño. |
| [`gameplay/SPELL_EXORI_HUR.md`](gameplay/SPELL_EXORI_HUR.md) | **exori hur** (Whirlwind Throw, knight): lanza el arma de melee al blanco (rango 5); daño por nivel, skill y ataque del arma (fórmula TFS); proyectil según arma. Bindings `getPlayerWeapon` / `getPlayerSkill`. |
| [`gameplay/SPELL_EXORI_CON.md`](gameplay/SPELL_EXORI_CON.md) | **exori con** (Ethereal Spear, paladin): lanza etérea al blanco (rango 7×5); daño por nivel y skill de distancia (fórmula TFS); proyectil de la Enchanted Spear. |
| [`gameplay/SPELLS_NOV2026.md`](gameplay/SPELLS_NOV2026.md) | **8 hechizos de versiones nuevas adaptados a 7.6:** Brutal Strike, Front Sweep, Wound Cleansing (knight); Divine Missile, Divine Healing, Sharpshooter (paladin); Ice Strike, Eternal Winter (druid). Fórmulas, adaptaciones y `exeta res`. |
| [`gameplay/SPELLS_FEEDBACK.md`](gameplay/SPELLS_FEEDBACK.md) | **8 hechizos de nov 2026 (2ª tanda):** `exori con gran`, `exeta sio`, `exana res`, `exori vis con`, `exura tera`, `exevo vis tera`, `utito tera`, `utamo mort`. Qué hacen, avisos al jugador, íconos con cuenta regresiva en el cliente y el arreglo del efecto que salía como sangre. |
| [`gameplay/SPELL_ECO.md`](gameplay/SPELL_ECO.md) | **Eco** (`utevo vis`, sorcerer): el próximo golpe a un blanco se repite 1 s después al 50 % (25 % vs jugadores), sin maná ni espera; espera propia 25 s. Cómo se limitó, cómo ajustarlo y el C++. |
| [`gameplay/SPELL_ATTACK_SPEED.md`](gameplay/SPELL_ATTACK_SPEED.md) | **Frenzy** (`utito hur`, knight) y **Rapid Fire** (`utito san hur`, paladin): golpes 40 % / 35 % más rápidos por 6 s, espera 20 s, efecto constante sobre el jugador e ícono en el cliente. C++, números en Lua y prueba con bots. |
| [`gameplay/SPELL_EXORI_VIS_HUR.md`](gameplay/SPELL_EXORI_VIS_HUR.md) | **exori vis hur**: Energy Strike a distancia (Sorc/Druid), visual HMM, rango 5; revert solo Lua+XML. |
| [`gameplay/SPELL_EXETA_RES.md`](gameplay/SPELL_EXETA_RES.md) | **exeta res** (Challenge): taunt Knight 3×3, lock 6 s sin retarget/flee; binding `doChallenge` + rebuild C++. |
| [`gameplay/TRAINING_BONUS_PARCHMENT.md`](gameplay/TRAINING_BONUS_PARCHMENT.md) | Sistema de pergaminos de bonus de training. |
| [`gameplay/PRIVATE_TRAINER_DUMMY.md`](gameplay/PRIVATE_TRAINER_DUMMY.md) | Private Trainer Dummy: item **`20155`** (clientId kit sofá `2776`), look monstruo trainer monk (`57`). |
| [`gameplay/PINK_SKULL.md`](gameplay/PINK_SKULL.md) | **Pink Skull** (implementada nov 2026): calavera rosa de castigo que pone un GM con `/pink`; al morir se pierde todo. Comandos, código y cliente. |
| [`gameplay/RIVER_STONE_TROLLS.md`](gameplay/RIVER_STONE_TROLLS.md) | **River Troll (252) y Stone Troll (253)**: los dos trolls nuevos del río y las ruinas, con sprites dibujados, spawns, la **Guarida** (cueva z8, `generate-troll-den.py`) y variantes rage. |
| [`gameplay/ZAGAN_CONSUMABLE_RUNES.md`](gameplay/ZAGAN_CONSUMABLE_RUNES.md) | Runas consumibles Zagan: experience recovery (20131) y training extension (20132). |
| [`gameplay/TRAINING_ZONE_NO_PVP.md`](gameplay/TRAINING_ZONE_NO_PVP.md) | Zonas de training con flag de no-PvP. |
| [`gameplay/WANDS.md`](gameplay/WANDS.md) | Wands/rods (11 items), flujo de `useWand()`, escalado de daño por ML, Crimson Wand (20123), tuning `wandmlfactor`. |

---

## Items y mapa

Importación de items, mapeo por código, items de prueba, sesiones de editor.

| Doc | Cubre / cuándo leerlo |
|-----|-----------------------|
| [`items-and-map/IMPORTAR_ITEM_DESDE_IMAGEN.md`](items-and-map/IMPORTAR_ITEM_DESDE_IMAGEN.md) | Si un item nuevo no entra o se ve mal: pipeline de import desde imagen. |
| [`items-and-map/PLAZA_ARCANA.md`](items-and-map/PLAZA_ARCANA.md) | Plaza, galería y torres de basalto/cian; entrada, faroles y rejas propios, fuentes y vistas previas. |
| [`items-and-map/MAIN_BRIDGE.md`](items-and-map/MAIN_BRIDGE.md) | Puente principal Ironbound (141,65,6): basalto, hierro/bronce, pasos PvP de 1 sqm preservados y sprites propios. Ribera de rotworms retirada; agua original restaurada. |
| [`items-and-map/TRANSICIONES_DEPOT.md`](items-and-map/TRANSICIONES_DEPOT.md) | Muelle junto al depot y 8 puentes de madera: barandas, faroles y rampa dibujados (20282–20300, `dock_bridge_art.py`), conservando trazado y paso. |
| [`items-and-map/MAPAS.md`](items-and-map/MAPAS.md) | **Guía única de mapas (26 nov 2026):** flujo con **mapkit** (ficha de zona en `scripts/map/zones/`, temas, receta, lint numérico, varias semillas), decisiones chicas con **jev** (OpenRouter `typesafe/jev-router`, ~US$0,001 por zona), valores por defecto, catálogo de piezas por tema con requisitos (generado), reglas de piezas (muebles, paredes, escaleras, botes, cuevas, techo, puente de referencia z6), zonas de caza (recorrido, etapas, densidad) y la tabla de errores que ya pasaron. Reemplaza a `PIEZAS_DE_MAPA.md` y `ZONAS_DE_CAZA.md`. |
| [`map-rendering.md`](map-rendering.md) | **Render de mapas sin GUI** (`scripts/map/render/maprender.mjs`, Node + sharp): regiones con sprites reales a 32–1 px por casilla, minimapa, capas (transitable, densidad de monstruos/ítems, cambios vs otro commit), ASCII, `diff` entre mapas, variantes lado a lado, `--cells` para ver propuestas sin escribir y `ask` (imagen chica a un modelo de visión barato, ~US$0,00003, con log y tope). Mediciones, alternativas y qué modelo usar. |
| [`items-and-map/RIVER_GROTTO.md`](items-and-map/RIVER_GROTTO.md) | Submerged River Grotto: agua animada, arena y corales; apariencias exclusivas que conservan colisiones/velocidad y vistas previas. |
| [`items-and-map/HOLE_ENTRANCES.md`](items-and-map/HOLE_ENTRANCES.md) | Revisión de los 48 hoyos: variantes por terreno, apertura sobre nieve y conservación de bajadas/retornos; normalizador compartido. |
| [`items-and-map/CROWN_ARMORS.md`](items-and-map/CROWN_ARMORS.md) | **Imperial y Sapphire Crown Armor** (20161–20162): crown armor recoloreada (`recolor_item.py`), −10% de daño elemental o físico (C++), loot raro de demonios, warlocks, behemoths y jefes. |
| [`items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md`](items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md) | **Ítems de otras versiones:** sprite sacado de un cliente 8.x píxel a píxel y stats de su `items.xml`. Emerald Sword, Avenger, Arcane Staff y Arbalest (20157–20160); `extract_client_sprites.py` + `add_custom_items.py`. |
| [`items-and-map/MAPEAR_CON_CODIGO.md`](items-and-map/MAPEAR_CON_CODIGO.md) | Mapear items/pisos por código (no manual) usando scripts. |
| [`items-and-map/MAPEAR_PASO_DEL_NORTE.md`](items-and-map/MAPEAR_PASO_DEL_NORTE.md) | Paso del Norte: puerta norte, bosque, Tundra Helada, Cuevas del Dragón (z8) y Nido Negro (z9) con `generate-north-pass.py`. |
| [`items-and-map/MAPA_DE_MONSTRUOS.md`](items-and-map/MAPA_DE_MONSTRUOS.md) | Mapa interactivo de todos los pisos con cada spawn, NPC y zona (`build-monster-map.py`). |
| [`items-and-map/MAPEAR_LABERINTO.md`](items-and-map/MAPEAR_LABERINTO.md) | Laberinto procedural 2 sqm: camino 406, fondo 100 (pared), teleport al templo (`generate-maze.py`). |
| [`items-and-map/MAPEAR_ISLA_HELADA.md`](items-and-map/MAPEAR_ISLA_HELADA.md) | **Isla del Hielo Eterno** (barco `frozen isle`, reemplaza al Alice Maze): sendero por etapas, grutas z8, guarida z9 con los cofres del crimson wand/helmet (`generate-frozen-isle.py`). |
| [`items-and-map/REVISION_ESTETICA_HIELO_2026_11_13.md`](items-and-map/REVISION_ESTETICA_HIELO_2026_11_13.md) | Revisión visual y funcional de Frozen Isle y la Tundra: bote incompleto, llegada de escalera en pared, spawn duplicado y mejoras estéticas; imágenes y prioridades, sin cambios de mapa. |
| [`items-and-map/CITY_VISUAL_FIXES_2026_11_24.md`](items-and-map/CITY_VISUAL_FIXES_2026_11_24.md) | Arreglos visuales de la city (24 nov 2026): canoa de la ensenada del Barquero, maleza en el fuerte pirata, bordes de pasto colgados, duplicados y dead trees 2716; qué se dejó a propósito (islote de nieve = punta de la isla de hielo) e imágenes de antes/después. |
| [`items-and-map/REMOVE_DEAD_TREE_2715_2026_11_24.md`](items-and-map/REMOVE_DEAD_TREE_2715_2026_11_24.md) | Dead trees 2715 fuera del mapa (24 nov 2026): 44 sacados (41 del Camino de los Caídos + 3 manuales), 2715 fuera de `DEAD_SMALL` de `generate-epstein-road.py`, verificaciones e imágenes antes/después. |
| [`items-and-map/TRANSICIONES_TERRENO_2026_11_24.md`](items-and-map/TRANSICIONES_TERRENO_2026_11_24.md) | Transiciones de terreno pasto↔tierra (24 nov 2026): el patio de tierra junto a la puerta de `186,76,7` cortaba recto contra el pasto. Los suelos 110–121 son textura de tierra con pasto recortado en recto, no un borde. Arreglo: grass border de RME 7.6 (`4542–4553`, una sola capa: el pasto pinta su borde sobre la tierra, 3.922 piezas en 2.971 tiles) + 163 suelos 110–121 corregidos (`fix-transiciones-20261124.py`); dudosas y conservadas. |
| [`items-and-map/MAPEAR_ISLA_NATURAL.md`](items-and-map/MAPEAR_ISLA_NATURAL.md) | **Isla natural** (portal plaza del templo `156,47,7`): herradura chica con un sendero, 3 campamentos de Cyclops y cueva de 3 pisos (z8–z10) hasta la Old Widow (`generate-natural-island.py`). |
| [`items-and-map/MAPEAR_VALLE_DE_LAS_BESTIAS.md`](items-and-map/MAPEAR_VALLE_DE_LAS_BESTIAS.md) | **Valle de las Bestias** (portal plaza del templo `158,47,7`, reemplazó al hunt maze): valle compacto z7 (Minotauros, Cíclopes, Ruinas) + 3 cuevas de dos pisos (Catacumbas, Quaras, Dragones) y Abismo z10 hasta Demonios (`generate-beast-valley.py`). |
| [`items-and-map/MAPEAR_POZOS_DEL_INFIERNO.md`](items-and-map/MAPEAR_POZOS_DEL_INFIERNO.md) | **Pozos del Infierno** (portal `159,47,7`): cueva de fuego 90–130 en 4 pisos (Yerma de Ceniza, Pozos de Ceniza, Garganta de Magma, Corazón) con puertas de nivel 90/100, Arena de las Furias y Cámara de las Armas — la fuente de las armas 8.x (Emerald Sword, Avenger, Arcane Staff, Arbalest) (`generate-inferno-pits.py`). |
| [`items-and-map/MAPEAR_CATACUMBA_IMPERIAL.md`](items-and-map/MAPEAR_CATACUMBA_IMPERIAL.md) | **Cripta Imperial** (boca en la orilla sur del pantano `94,92,7`, unida al túnel del Spot del Dragón Negro): pasillo de caza en U en z8 (548 casillas, 14 monstruos) con la guarnición imperial — Squire/Archer al frente, Court Mage, Imperial Hero de a 2 al fondo, sin rage (`generate-imperial-crypt.py`; regenerar dragón → cripta → dragón). |
| [`items-and-map/NECROMANCER_CAVE_EXTENSION.md`](items-and-map/NECROMANCER_CAVE_EXTENSION.md) | **Ramal de Necromancer y Hero** (`82,117,8`): ampliación sur de 248 casillas y ocho monstruos no muertos, con Lich al fondo. |
| [`items-and-map/DUSKWEB_HOLLOW.md`](items-and-map/DUSKWEB_HOLLOW.md) | **Duskweb Hollow** (costa de `25,128,7`): península con sendero y cueva independiente de arañas, con dos Dark Spiders al fondo. |
| [`items-and-map/ELVENBANE.md`](items-and-map/ELVENBANE.md) ([MAPEAR_ELVENBANE.md](items-and-map/MAPEAR_ELVENBANE.md)) | **Elvenbane** (portal plaza del templo `157,47,7`): fortaleza élfica de Tibia clásico en 7 pisos (isla con castillo + túnel + sótanos + adarve y torres), de Orcos/Elfos a un Dragon en la cima. Las 19 conexiones son escalera de mano (`generate-elvenbane.py`). |
| [`items-and-map/MAPEAR_FOSO_OLVIDADO.md`](items-and-map/MAPEAR_FOSO_OLVIDADO.md) | **El Foso Olvidado** (reemplaza la Arena PvP de z9): entrada por las cloacas de la ciudad, corredor y 3 pisos de laberinto z10–z12, de nivel 20 a 100+, con tortugas/quaras 8.60, elementales, golems, faraones y Orshabaal (`generate-forgotten-pit.py`). |
| [`items-and-map/MAPEAR_TORRE_BARQUERO.md`](items-and-map/MAPEAR_TORRE_BARQUERO.md) | **Torre del Barquero**: reemplaza el patio de mesas junto al bote de Fargum por una torre de 5 pisos (z7–z3) con un monstruo por piso: Tortoise, Thornback, Blood Crab, Quara Constrictor y Quara Predator (`generate-fargum-tower.py`). |
| [`items-and-map/MAPEAR_TORRES_KONGRA.md`](items-and-map/MAPEAR_TORRES_KONGRA.md) | **Torres del Kongra** (selva del Bamboo Camp): tres torres medias — Kongra en la planta baja, Red Kongra (nuevo, [`gameplay/RED_KONGRA.md`](gameplay/RED_KONGRA.md)) arriba; 12 rojos en total (`generate-kongra-towers.py`). |
| [`items-and-map/MAPEAR_TORRE_MAGO.md`](items-and-map/MAPEAR_TORRE_MAGO.md) | **Torre del Mago Oscuro**: 6 pisos (z7–z2) al sur de la city, en el claro entre el río y la roca; magos cada vez más fuertes hasta el Dark Mage (`generate-mage-tower.py`). |
| [`items-and-map/CALDERA_AZUL.md`](items-and-map/CALDERA_AZUL.md) | **Caldera Azul**: lava azul (`20680`, `recolor_lava.py`), 5 monstruos de fuego frío (looks 145–149, jefe Azhurak) y zona de caza sobre un mar de lava azul (`generate-azure-caldera.py`); portal `163,47,7`. |
| [`items-and-map/ISLA_VOLCANICA.md`](items-and-map/ISLA_VOLCANICA.md) | Isla volcánica del noroeste: el mar de lava cuadrado pasa a caldera orgánica con orilla de roca y mar hasta el borde del mapa (sin vacío negro); `fix-volcanic-shore.py`, una sola vez. |
| [`items-and-map/MAPEAR_CAMPO_DE_BRASAS.md`](items-and-map/MAPEAR_CAMPO_DE_BRASAS.md) | **Campo de Brasas**: la península de 36,63,7 crece 162 casillas sobre la lava, con bordes, decoración y Demon Skeleton / Fire Devil / Bone Beast (`generate-ember-field.py`). |
| [`items-and-map/HERO_DEPTHS.md`](items-and-map/HERO_DEPTHS.md) | **Profundidades del Héroe** (hueco `146,93,9` en el lugar de los Hero): mazmorra de 5 pisos z10–z14 en el mismo estilo (losa negra, ladrillo, tapices, lava), Black Knights; cómo convive con Demona Local, Mutated Sewers, Spider Nest y la Gruta (`generate-hero-depths.py`). |
| [`items-and-map/MAPEAR_DUNGEON_CITY.md`](items-and-map/MAPEAR_DUNGEON_CITY.md) | **Dungeon de la city** (agujero `185,58,7`, al sur de la Torre del Barquero): cueva de 3 pisos z8–z10 con Orc Berserker Pot Thrower, Carniphila, Dragon Lord Hatchling, Emerald Scarab y Dark Hydra; reglas de cuevas (bloques 2x2, vacío a la vista, agujero + escalera de mano) y los errores del primer dungeon (`generate-city-depths.py`). |
| [`items-and-map/MAPEAR_HUNTS_CITY.md`](items-and-map/MAPEAR_HUNTS_CITY.md) | **Tres hunts nuevos cerca de la city** (nov 2026): Alcantarilla Profunda/Mutada (`168,53,8`, Rats + Mutated), Nido de Seda Negra (`105,80,7`, Giant Spiders + Wyverns) y Cripta de los Ojos (`78,34,7`, Beholders + Vampires + Banshees). |
| [`gameplay/CAMBIOS_SI_A_TODO.md`](gameplay/CAMBIOS_SI_A_TODO.md) | **Paquete "Sí a todo" (nov 2026):** Aurora Blade/Axe, Frostbound Bow, sets endgame Starbinder/Machina, consumibles de bosses (Azure/Verdant Sunstone), fixes/balance de 64 monstruos (+105 Rage) y 4 spots nuevos cerca de la city (Gruta Submarina, Demona Local, Campamento Amazonas y Campamento Bárbaro). |
| [`items-and-map/MAPEAR_BORRAR_TORRE_DEPOT.md`](items-and-map/MAPEAR_BORRAR_TORRE_DEPOT.md) | **Torre de escaleras del depot — eliminada**: shaft de piedra 3×3 a la derecha del depot (z2–z6, 5 spawns rage) borrado completo, entrada de z7 restaurada a pavement y depot/edificio derecho intactos (`remove-depot-stair-tower.py`). |
| [`items-and-map/MAPEAR_TIENDA_SELLER.md`](items-and-map/MAPEAR_TIENDA_SELLER.md) | **Tienda del Seller — recorte del fondo sur**: pasa de y46–56 a y46–54; displays de z6 reubicados en la franja oeste, armas de z5 sobre las mesas de y53 y muro sur movido a y54 (`shrink-seller-shop.py`). |
| [`items-and-map/MAPEAR_CUEVAS_BAMBU.md`](items-and-map/MAPEAR_CUEVAS_BAMBU.md) | **Cuevas de Bambú** (bajada `172,99,7` en el claro de Bamboo Camp): v2 natural (19 nov 2026), pozo z8 como islote en la lava de los behemoths y cueva z9 de tres cámaras sin vacío ni lava a la vista; techos flotantes del claro sacados (`generate-bamboo-depths.py`, `remove-floating-roofs.py`). |
| [`items-and-map/DARK_CATHEDRAL.md`](items-and-map/DARK_CATHEDRAL.md) | **Dark Cathedral — documentación completa:** cajas por piso, plantas (nave negra, ruinas, salón gris, cripta -1 con cueva natural G–J, cripta -2 con columnas/octógono/zigzag/óvalo), escaleras `432`+`1385` con llegadas, portales, 128 spawns, elección de ítems y validaciones. Resumen operativo en [`items-and-map/MAPEAR_DARK_CATHEDRAL.md`](items-and-map/MAPEAR_DARK_CATHEDRAL.md); portal plaza del templo `155,47,7` con `generate-dark-cathedral.py`. |
| [`items-and-map/EPSTEIN_HUNTS.md`](items-and-map/EPSTEIN_HUNTS.md) | **Epstein Island (isla de caza nivel medio/alto, 4 pisos):** Mutant Camp / Terror Bird Nest / Dragon Roost, cuevas z8, piso z9 y z10 con Mutated Tiger, Tide Priest y Bog Raider; **Camino de los Caídos** (franja nueva en el mar con Zombies y Undead Gladiators, `generate-epstein-road.py`); sin NPCs, tienda ni Oracle; barco abierto a todos (`generate-epstein-hunts.py`, `generate-epstein-caves.py`, `generate-epstein-cleanup.py`). |
| [`items-and-map/CURIOUS_HOUSES.md`](items-and-map/CURIOUS_HOUSES.md) | **Tres casas flotantes comprables**: una en Kongras, una élfica y una junto al río; 9 sqm, plataformas, pasarelas, PZ y techos completos. |
| [`items-and-map/ELF_WEST.md`](items-and-map/ELF_WEST.md) | **Elfland / Ruinas del Sauce**: terrazas de mármol claro y ampliación occidental por puente; cuatro elfos nuevos y luces esmeralda fijas. |
| [`items-and-map/MAPEAR_SPOT_DRAGON.md`](items-and-map/MAPEAR_SPOT_DRAGON.md) | **Spot del Dragón Negro** (lago al oeste de los elfos): Black Dragon aislado en una isla, puente 1×4 y caza subiendo y bajando por agujero + túnel z8, con ramal a la Cripta Imperial (`generate-dragon-spot.py`). |
| [`items-and-map/MAPEAR_ISLA_DARK_HYDRAS.md`](items-and-map/MAPEAR_ISLA_DARK_HYDRAS.md) | **Isla de las Dark Hydras** (mar al sur del bosque, bajada en `50,138,7`): isla larga con 6 Dark Hydras sueltas, entrada como el Spot del Dragón Negro — agujero, túnel z8 de 1 de ancho, islote del cazador y puente 1×4 (`generate-dark-hydra-isle.py`). |
| [`items-and-map/MAPEAR_GLACIAR_DEL_ESTE.md`](items-and-map/MAPEAR_GLACIAR_DEL_ESTE.md) | **Glaciar del Este** (sale de la punta este de la isla de hielo vieja, `262,39,7`): sendero de hunt largo en serpentina con monstruos de hielo por etapas — Chakoya, Frost Giants, Ice Golem/Monk, hatchlings y Crystal Spider — y al fondo Frost Dragons e Ice Spiders (`generate-glacier-reach.py`). |
| [`items-and-map/MAPEAR_CLARO_DE_LOS_LOBOS.md`](items-and-map/MAPEAR_CLARO_DE_LOS_LOBOS.md) | **Claro de los Lobos (Wolf Grove)**: isla de bosque al sureste, rehecha con mapkit el 26 nov 2026; se llega en barco (destino Wolf Grove), sendero en S con 5 claros, Wolf → Winter Wolf → War Wolf/Bear. |
| [`items-and-map/MAPEAR_TORRE_PUENTE.md`](items-and-map/MAPEAR_TORRE_PUENTE.md) | **Torre del Puente** (en medio del río, junto a las tiendas): 6 pisos z7–z2 con piratas, quaras y ahogados hasta un Quara Predator, y **puentes** Islote del Minotauro ↔ isla del Castillo ↔ torre (`generate-bridge-tower.py`). |
| [`items-and-map/MAPEAR_ISLOTE_MINOTAURO.md`](items-and-map/MAPEAR_ISLOTE_MINOTAURO.md) | **Islote del Minotauro** (canal junto al muelle de la ciudad): islote z7 con puente y minotauros comunes + cuevas z10–z12 con Archer, Guard y Mage cada vez más fuertes (`generate-minotaur-isle.py`). |
| [`gameplay/WAVE_ARENA.md`](gameplay/WAVE_ARENA.md) | Wave Arena "Claro de la Selva": 20 oleadas en grupo, jefe cada 5, ranking por oleadas limpias y premio semanal; portal plaza del templo `166,47,7`. |
| [`gameplay/FOLLOW.md`](gameplay/FOLLOW.md) | **Follow** (`0xA2`), **"usar" de lejos** (camina y usa: escaleras, puertas, palancas) y **modo perseguir** del ataque: el server camina al jugador al lado del blanco (A* a la casilla libre más cercana, cada 300 ms); se corta al caminar, con Esc o al atacar. `test-follow.py`. |
| [`gameplay/CRUCIBLE.md`](gameplay/CRUCIBLE.md) | El Crisol v4: escalera diaria Bronze → Silver → Gold con premio por puerta, jefe de Oro una vez por día, guardián Varkon (cuenta regresiva, contador, premio, limpieza), hub PZ + 3 arenas temáticas, entrada en grupo por plataforma; portal plaza del templo `164,47,7`. Patrones de paredes y alfombra. |
| [`gameplay/SAND_CLOCK.md`](gameplay/SAND_CLOCK.md) | **Reloj de Arena:** sala chica (11×9) compartida: descanso de 30 s y 6 oleadas de 60 s que suben de nivel, braseros que marcan la oleada, Chronos; portal plaza del templo `168,47,7`. |
| [`items-and-map/MAPEAR_TP_GAUNTLET.md`](items-and-map/MAPEAR_TP_GAUNTLET.md) | Gauntlet: 40 salas 3×3 + sala final 3×3 (Wrath + demon armor, 1 TP); barco `gauntlet`. |
| [`items-and-map/ISLAND_BANDS.md`](items-and-map/ISLAND_BANDS.md) | Cómo componer las bandas agua→shore→dirt→grass para que una isla no se vea con corte duro. Especificación de las 5 bandas y 7 reglas críticas. |
| [`items-and-map/ZAGAN_TEST_ITEMS.md`](items-and-map/ZAGAN_TEST_ITEMS.md) | Ítems Zagan (`20100`+): qué es cada uno, sprites redibujados y recoloreados, revisión de nombre/tipo/dibujo de nov 2026. |
| [`items-and-map/SESION_EDITOR_MAPA_JUL2026.md`](items-and-map/SESION_EDITOR_MAPA_JUL2026.md) | Bitácora de la sesión de editor de mapa de julio 2026. |

---

## Catálogo de features

Catálogo de **migración/portabilidad** (16 fichas congeladas). No es el inventario exhaustivo del server: mecánicas nuevas viven en [`gameplay/`](gameplay/) y se listan arriba. El índice de fichas está en [`FEATURE_CATALOG.md`](FEATURE_CATALOG.md).

| Doc | Feature |
|-----|---------|
| [`FEATURE_CATALOG.md`](FEATURE_CATALOG.md) | Índice de fichas de portabilidad (no exhaustivo; ver sección Gameplay). |
| [`features/01-training-daily-system.md`](features/01-training-daily-system.md) | Training diario. |
| [`features/02-training-no-pvp.md`](features/02-training-no-pvp.md) | Training en zonas no-PvP. |
| [`features/03-training-bonus-parchment.md`](features/03-training-bonus-parchment.md) | Pergaminos de bonus de training. |
| [`features/04-bounty-most-wanted.md`](features/04-bounty-most-wanted.md) | Sistema bounty / most wanted. |
| [`features/05-npc-transaction-confirmation.md`](features/05-npc-transaction-confirmation.md) | Confirmación de transacciones NPC. |
| [`features/06-bank-backed-economy.md`](features/06-bank-backed-economy.md) | Economía respaldada por bank. |
| [`features/07-seller-fluid-packs-and-vials.md`](features/07-seller-fluid-packs-and-vials.md) | Vendedores de fluids, packs y vials. |
| [`features/08-rune-backpacks-dark-rodo.md`](features/08-rune-backpacks-dark-rodo.md) | Backpacks de runas y Dark Rodo. |
| [`features/09-rage-monsters.md`](features/09-rage-monsters.md) | Monstruos enraged. |
| [`features/10-gems-and-imbuements.md`](features/10-gems-and-imbuements.md) | Gemas e imbuements. |
| [`features/11-premium-and-promotion.md`](features/11-premium-and-promotion.md) | Premium account y promotion. |
| [`features/12-soft-boots.md`](features/12-soft-boots.md) | Soft boots (catálogo); detalle técnico en [`gameplay/SOFT_BOOTS.md`](gameplay/SOFT_BOOTS.md). |
| [`features/13-rune-weight-rl.md`](features/13-rune-weight-rl.md) | Peso de runas y lógica RL. |
| [`features/14-spell-cast-visibility.md`](features/14-spell-cast-visibility.md) | Visibilidad del cast de hechizos. |
| [`features/15-exori-gran.md`](features/15-exori-gran.md) | Hechizo exori gran. |
| [`features/16-utility-spell-access.md`](features/16-utility-spell-access.md) | Acceso a hechizos utilitarios. |
| [`features/18-web-astro.md`](features/18-web-astro.md) | Web en Astro: páginas, diseño, cómo compilar (en la ThinkPad) y cómo la sirve `server.py`. Incluye la **wiki** para jugadores (`/wiki`, artículos en `web/site/src/wiki/`). |
| [`features/17-web-footer.md`](features/17-web-footer.md) | Footer de la web: franja de ítems en pixel art, dirección del server para copiar, estado en vivo, links y aviso legal. |
| [`features/19-web-catalogo-items.md`](features/19-web-catalogo-items.md) | Catálogos privados `/items` y `/items-all`: de dónde salen, cómo regenerarlos con el cliente y el OTB actuales. |

---

## Búsqueda rápida por síntoma

| Síntoma / necesidad | Ir a |
|---------------------|------|
| El OT se cuelga o está lento | [`systems/PREVENT_OT_HANGS.md`](systems/PREVENT_OT_HANGS.md) |
| El OT crashea y no sé por qué | [`systems/CRASH_DIAGNOSTICS.md`](systems/CRASH_DIAGNOSTICS.md) |
| Kicks masivos o desconexiones | [`systems/SOCKET_DEBUG_LOGGING.md`](systems/SOCKET_DEBUG_LOGGING.md) |
| Quiero entender la causa raíz de cuelgues | [`systems/OT_HANG_ROOT_CAUSE_SEND_BLOCKING.md`](systems/OT_HANG_ROOT_CAUSE_SEND_BLOCKING.md) |
| Cuántos jugadores nuevos entran, vuelven o fallan al loguear | [`systems/LOGIN_EVENTS.md`](systems/LOGIN_EVENTS.md) |
| Un item no entra o se ve mal | [`items-and-map/IMPORTAR_ITEM_DESDE_IMAGEN.md`](items-and-map/IMPORTAR_ITEM_DESDE_IMAGEN.md) |
| Necesito mapear items por código | [`items-and-map/MAPEAR_CON_CODIGO.md`](items-and-map/MAPEAR_CON_CODIGO.md) |
| Generar una isla coherente (bandas agua/pasto) | [`items-and-map/ISLAND_BANDS.md`](items-and-map/ISLAND_BANDS.md) |
| Quiero generar un laberinto por código | [`items-and-map/MAPEAR_LABERINTO.md`](items-and-map/MAPEAR_LABERINTO.md) |
| Cuevas progresivas de nivel 20 a 100+ | [`items-and-map/MAPEAR_FOSO_OLVIDADO.md`](items-and-map/MAPEAR_FOSO_OLVIDADO.md) |
| Quiero un gauntlet de salas 3×3 con TPs | [`items-and-map/MAPEAR_TP_GAUNTLET.md`](items-and-map/MAPEAR_TP_GAUNTLET.md) + [`gameplay/BOAT_TRAVEL.md`](gameplay/BOAT_TRAVEL.md) |
| Quiero crear un monstruo nuevo | [`gameplay/MONSTER_CREATION.md`](gameplay/MONSTER_CREATION.md) |
| Dónde está cada monstruo del mapa | [`items-and-map/MAPA_DE_MONSTRUOS.md`](items-and-map/MAPA_DE_MONSTRUOS.md) |
| Quiero un monstruo con sprite propio o hechizos nuevos | [`gameplay/CUSTOM_MONSTER_WORKFLOW.md`](gameplay/CUSTOM_MONSTER_WORKFLOW.md) |
| Quiero crear o retocar el sprite de una criatura | [`gameplay/SPRITE_RECOLOR_GUIDE.md`](gameplay/SPRITE_RECOLOR_GUIDE.md) |
| Voy a tocar gemas o imbuements | [`gameplay/GEMS.md`](gameplay/GEMS.md) → [`features/10-gems-and-imbuements.md`](features/10-gems-and-imbuements.md) |
| Skill ring + emerald armor + crimson no suman | [`gameplay/GEMS.md`](gameplay/GEMS.md) (Big Emerald / stacking) + `Player::getSkill` en `player.cpp` |
| Voy a hacer deploy | [`systems/THINKPAD_TEST_SERVER.md`](systems/THINKPAD_TEST_SERVER.md) (solo con OK de Gonzalo) |
| Necesito migrar DB o data crítica | [`MIGRATION_PLAYBOOK.md`](MIGRATION_PLAYBOOK.md) |
| Voy a cambiar el mapa del server | [`CAMBIAR-MAPA.md`](CAMBIAR-MAPA.md) → [`gameplay/DEPOTS.md`](gameplay/DEPOTS.md) |
| Jugadores reportan depot vacío | [`gameplay/DEPOTS.md`](gameplay/DEPOTS.md) |
| Deploy / dueños de casas borrados | [`gameplay/HOUSES.md`](gameplay/HOUSES.md) |
| Wand pega siempre igual sin importar ML / imbue de Violet | [`gameplay/WANDS.md`](gameplay/WANDS.md) |
| Quiero ver fichas de portabilidad (migración) | [`FEATURE_CATALOG.md`](FEATURE_CATALOG.md) |
| Quiero ver qué features tiene el juego | [`INDEX.md`](INDEX.md) (sección Gameplay) + [`FEATURE_CATALOG.md`](FEATURE_CATALOG.md) |
| Portal templo / El Crisol | [`gameplay/CRUCIBLE.md`](gameplay/CRUCIBLE.md) |
| Wave Arena / oleadas | [`gameplay/WAVE_ARENA.md`](gameplay/WAVE_ARENA.md) |
| Necesito configurar el editor RME | [`RME_SETUP.md`](RME_SETUP.md) |
| Tests de humo antes de release | [`SMOKE_TESTS.md`](SMOKE_TESTS.md) |
