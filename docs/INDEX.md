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
| [`gameplay/EXP_RATE.md`](gameplay/EXP_RATE.md) | Tiers de experiencia por nivel (`expmul`). |
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
| [`gameplay/EMERALD_SCARAB.md`](gameplay/EMERALD_SCARAB.md) | Emerald Scarab: variante de Ancient Scarab, 1500 HP / 1150 exp, estallido de veneno y look 242 esmeralda/dorado con gema en el lomo. |
| [`gameplay/ROOT_COLOSSUS.md`](gameplay/ROOT_COLOSSUS.md) | Root Colossus: guardián vegetal (look 243), 4800 HP / 3400 exp, raíces y esporas; spawn local al final de la progresión del Abismo del Valle de las Bestias, con rootcleaver (axe 1H) y heartwood maul (club 2H) de loot raro. |
| [`gameplay/CLIENT_EFFECTS.md`](gameplay/CLIENT_EFFECTS.md) | Efectos y proyectiles nuevos del cliente por recoloreo (pack "ice": `NM_ME_ICE_*`, `NM_ANI_FROSTBALL`), límites y cómo agregar packs. |
| [`gameplay/HELL_QUEST.md`](gameplay/HELL_QUEST.md) | **Hell Quest** (Isla del Infierno): caza en 3 pisos, puertas de nivel 80/100, boss **Ashen Lord** y Cámara de la Elección (4 cofres, se elige uno); criatura nueva **Hellhound** (`generate-hell-quest.py`). |
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
| [`gameplay/ENCHANTED_SPEAR.md`](gameplay/ENCHANTED_SPEAR.md) | **Enchanted Spear (20156):** spear mejorada (ataque 36, 80% hit, no se apila), sprite de cristal y luz de color propia; 4 estilos; proyectil propio `NM_ANI_ENCHANTED_SPEAR` (16) con luz en vuelo. |
| [`gameplay/DEPOTS.md`](gameplay/DEPOTS.md) | **Depots:** lockers 2589, XML vs mapa, incidente jul 2026, checklist pre-deploy de mapa. |
| [`gameplay/HOUSES.md`](gameplay/HOUSES.md) | **Casas:** dueños en `data/houses/*.xml`, deploy, backup/recuperación, **items fantasma** (caso Maximus `166,39,7` jul 2026). |
| [`gameplay/GOLDEN_ACCESSORIES.md`](gameplay/GOLDEN_ACCESSORIES.md) | Golden amulet y golden ring: auto-bank, bonus de oro e interacción entre ambos. |
| [`gameplay/SOFT_BOOTS.md`](gameplay/SOFT_BOOTS.md) | **Soft Boots (3549):** +3 HP / +12 MP cada 3 s, 4 h de uso → worn (3550); C++ `YUR_SOFT_BOOTS`. |
| [`gameplay/NPC_SYSTEM.md`](gameplay/NPC_SYSTEM.md) | **NPCs:** cómo se cargan, componentes de `lib/npc/`, `npcDefine`, recetas, API C++, lista de NPCs y pruebas sin servidor (`scripts/npc/run_npc_tests.py`). |
| [`gameplay/NPC_CONFIRMATION.md`](gameplay/NPC_CONFIRMATION.md) | Confirmación de transacciones con NPC (anti-misflow). |
| [`gameplay/SELLER_FLUIDS.md`](gameplay/SELLER_FLUIDS.md) | Sistema de vendedores de fluids/potions. |
| [`gameplay/DARK_RODO_RUNE_BACKPACKS.md`](gameplay/DARK_RODO_RUNE_BACKPACKS.md) | Backpacks especiales de runas y Dark Rodo. |
| [`gameplay/RUNE_WEIGHT_RL.md`](gameplay/RUNE_WEIGHT_RL.md) | Peso de runas y lógica RL asociada. |
| [`gameplay/DESINTEGRATE_RUNE.md`](gameplay/DESINTEGRATE_RUNE.md) | Implementación real de la rune Desintegrate: magic wall, wild growth y objetos destruibles. |
| [`gameplay/SPELL_RUNTIME.md`](gameplay/SPELL_RUNTIME.md) | **Spells/runas:** carga XML→Lua, `safeCast` anti-crash, restauración Soulfire/Paralyze/etc. (jul 2026). Leer antes de tocar `spells.xml` / `spells.cpp`. |
| [`gameplay/SPELL_EXHAUSTION.md`](gameplay/SPELL_EXHAUSTION.md) | **Exhausted:** ofensivo 2 s / no-ofensivo 1 s, sin `exhaustedadd` en casts, bindings Paralyze/Anchor/etc. con exhaust compartido, visibilidad say. |
| [`gameplay/MAGIC_WALL.md`](gameplay/MAGIC_WALL.md) | **Magic Wall:** duración 15s, `DECAY_INTERVAL`, bug de relanzar sin reiniciar timer (jul 2026). |
| [`gameplay/ANCHOR_RUNE.md`](gameplay/ANCHOR_RUNE.md) | Anchor Rune (2296): root de 1s (no paralyze) para war/combos. |
| [`gameplay/SPELL_CAST_VISIBILITY.md`](gameplay/SPELL_CAST_VISIBILITY.md) | Visibilidad del cast de hechizos (efectos visuales). |
| [`gameplay/SPELL_EXORI_GRAN.md`](gameplay/SPELL_EXORI_GRAN.md) | Hechizo exori gran: balance, área, daño. |
| [`gameplay/SPELL_EXORI_HUR.md`](gameplay/SPELL_EXORI_HUR.md) | **exori hur** (Whirlwind Throw, knight): lanza el arma de melee al blanco (rango 5); daño por nivel, skill y ataque del arma (fórmula TFS); proyectil según arma. Bindings `getPlayerWeapon` / `getPlayerSkill`. |
| [`gameplay/SPELL_EXORI_CON.md`](gameplay/SPELL_EXORI_CON.md) | **exori con** (Ethereal Spear, paladin): lanza etérea al blanco (rango 7×5); daño por nivel y skill de distancia (fórmula TFS); proyectil de la Enchanted Spear. |
| [`gameplay/SPELLS_NOV2026.md`](gameplay/SPELLS_NOV2026.md) | **8 hechizos de versiones nuevas adaptados a 7.6:** Brutal Strike, Front Sweep, Wound Cleansing (knight); Divine Missile, Divine Healing, Sharpshooter (paladin); Ice Strike, Eternal Winter (druid). Fórmulas, adaptaciones y `exeta res`. |
| [`gameplay/SPELL_ECO.md`](gameplay/SPELL_ECO.md) | **Eco** (`utevo vis`, sorcerer): el próximo golpe a un blanco se repite 1 s después al 50 % (25 % vs jugadores), sin maná ni espera; espera propia 25 s. Cómo se limitó, cómo ajustarlo y el C++. |
| [`gameplay/SPELL_EXORI_VIS_HUR.md`](gameplay/SPELL_EXORI_VIS_HUR.md) | **exori vis hur**: Energy Strike a distancia (Sorc/Druid), visual HMM, rango 5; revert solo Lua+XML. |
| [`gameplay/SPELL_EXETA_RES.md`](gameplay/SPELL_EXETA_RES.md) | **exeta res** (Challenge): taunt Knight 3×3, lock 6 s sin retarget/flee; binding `doChallenge` + rebuild C++. |
| [`gameplay/TRAINING_BONUS_PARCHMENT.md`](gameplay/TRAINING_BONUS_PARCHMENT.md) | Sistema de pergaminos de bonus de training. |
| [`gameplay/PRIVATE_TRAINER_DUMMY.md`](gameplay/PRIVATE_TRAINER_DUMMY.md) | Private Trainer Dummy: item **`20155`** (clientId kit sofá `2776`), look monstruo trainer monk (`57`). |
| [`gameplay/ZAGAN_CONSUMABLE_RUNES.md`](gameplay/ZAGAN_CONSUMABLE_RUNES.md) | Runas consumibles Zagan: experience recovery (20131) y training extension (20132). |
| [`gameplay/TRAINING_ZONE_NO_PVP.md`](gameplay/TRAINING_ZONE_NO_PVP.md) | Zonas de training con flag de no-PvP. |
| [`gameplay/WANDS.md`](gameplay/WANDS.md) | Wands/rods (11 items), flujo de `useWand()`, escalado de daño por ML, Crimson Wand (20123), tuning `wandmlfactor`. |

---

## Items y mapa

Importación de items, mapeo por código, items de prueba, sesiones de editor.

| Doc | Cubre / cuándo leerlo |
|-----|-----------------------|
| [`items-and-map/IMPORTAR_ITEM_DESDE_IMAGEN.md`](items-and-map/IMPORTAR_ITEM_DESDE_IMAGEN.md) | Si un item nuevo no entra o se ve mal: pipeline de import desde imagen. |
| [`items-and-map/PIEZAS_DE_MAPA.md`](items-and-map/PIEZAS_DE_MAPA.md) | **Cómo usar paredes, escaleras y muebles en un generador de mapa:** muebles de dos piezas (ataúdes, bancos), sillas por dirección, mesas enteras, regla de piezas de pared y llegada de escaleras. `render-pieces.py` para mirarlas antes. |
| [`items-and-map/CROWN_ARMORS.md`](items-and-map/CROWN_ARMORS.md) | **Imperial y Sapphire Crown Armor** (20161–20162): crown armor recoloreada (`recolor_item.py`), −10% de daño elemental o físico (C++), loot raro de demonios, warlocks, behemoths y jefes. |
| [`items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md`](items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md) | **Ítems de otras versiones:** sprite sacado de un cliente 8.x píxel a píxel y stats de su `items.xml`. Emerald Sword, Avenger, Arcane Staff y Arbalest (20157–20160); `extract_client_sprites.py` + `add_custom_items.py`. |
| [`items-and-map/MAPEAR_CON_CODIGO.md`](items-and-map/MAPEAR_CON_CODIGO.md) | Mapear items/pisos por código (no manual) usando scripts. |
| [`items-and-map/MAPEAR_PASO_DEL_NORTE.md`](items-and-map/MAPEAR_PASO_DEL_NORTE.md) | Paso del Norte: puerta norte, bosque, Tundra Helada, Cuevas del Dragón (z8) y Nido Negro (z9) con `generate-north-pass.py`. |
| [`items-and-map/MAPA_DE_MONSTRUOS.md`](items-and-map/MAPA_DE_MONSTRUOS.md) | Mapa interactivo de todos los pisos con cada spawn, NPC y zona (`build-monster-map.py`). |
| [`items-and-map/MAPEAR_LABERINTO.md`](items-and-map/MAPEAR_LABERINTO.md) | Laberinto procedural 2 sqm: camino 406, fondo 100 (pared), teleport al templo (`generate-maze.py`). |
| [`items-and-map/MAPEAR_ISLA_HELADA.md`](items-and-map/MAPEAR_ISLA_HELADA.md) | **Isla del Hielo Eterno** (barco `frozen isle`, reemplaza al Alice Maze): sendero por etapas, grutas z8, guarida z9 con los cofres del crimson wand/helmet (`generate-frozen-isle.py`). |
| [`items-and-map/REVISION_ESTETICA_HIELO_2026_11_13.md`](items-and-map/REVISION_ESTETICA_HIELO_2026_11_13.md) | Revisión visual y funcional de Frozen Isle y la Tundra: bote incompleto, llegada de escalera en pared, spawn duplicado y mejoras estéticas; imágenes y prioridades, sin cambios de mapa. |
| [`items-and-map/MAPEAR_ISLA_NATURAL.md`](items-and-map/MAPEAR_ISLA_NATURAL.md) | **Isla natural** (portal plaza del templo `156,47,7`): herradura chica con un sendero, 3 campamentos de Cyclops y cueva de 4 salas hasta el Grorlam (`generate-natural-island.py`). |
| [`items-and-map/MAPEAR_VALLE_DE_LAS_BESTIAS.md`](items-and-map/MAPEAR_VALLE_DE_LAS_BESTIAS.md) | **Valle de las Bestias** (portal plaza del templo `158,47,7`, reemplazó al hunt maze): valle natural z7 (Minotauros, Cíclopes, Ruinas) + Catacumbas z8 + Abismo z9 hasta Demonios (`generate-beast-valley.py`). |
| [`items-and-map/MAPEAR_CUEVAS_BAMBU.md`](items-and-map/MAPEAR_CUEVAS_BAMBU.md) | **Cuevas de Bambú**: bajada opcional bajo Bamboo Camp (escalera en `172,99,7`), pozo z8 y cueva z9 con 3 salas y monstruos que suben de dificultad (`generate-bamboo-depths.py`). |
| [`items-and-map/EPSTEIN_HUNTS.md`](items-and-map/EPSTEIN_HUNTS.md) | **Epstein Island (isla de caza nivel medio/alto, 4 pisos):** Mutant Camp / Terror Bird Nest / Dragon Roost, cuevas z8, piso z9 y z10 con Mutated Tiger, Tide Priest y Bog Raider; sin NPCs, tienda ni Oracle; barco abierto a todos (`generate-epstein-hunts.py`, `generate-epstein-caves.py`, `generate-epstein-cleanup.py`). |
| [`items-and-map/MAPEAR_ISLOTE_MINOTAURO.md`](items-and-map/MAPEAR_ISLOTE_MINOTAURO.md) | **Islote del Minotauro** (canal junto al muelle de la ciudad): islote z7 con puente y minotauros comunes + cuevas z10–z12 con Archer, Guard y Mage cada vez más fuertes (`generate-minotaur-isle.py`). |
| [`gameplay/WAVE_ARENA.md`](gameplay/WAVE_ARENA.md) | Wave Arena "Claro de la Selva": 20 oleadas en grupo, jefe cada 5, ranking por oleadas limpias y premio semanal; portal plaza del templo `166,47,7`. |
| [`gameplay/CRUCIBLE.md`](gameplay/CRUCIBLE.md) | El Crisol v2: hub PZ + 3 arenas temáticas (Foso de Arena, Coliseo, Trono de Fuego), entrada en grupo por plataforma, arenas independientes, bosses diarios; portal plaza del templo `164,47,7`. Patrones de paredes y alfombra. |
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
