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
| 4 | [`../scripts/deploy/README-DEPLOY-VPS.md`](../scripts/deploy/README-DEPLOY-VPS.md) | Antes de cualquier deploy a producción. |
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
| [`CLIENT_UPDATER_RETRO76.md`](CLIENT_UPDATER_RETRO76.md) | Sistema de updater/autoupdate del cliente Retro76. |
| [`PVP_SYSTEM.md`](PVP_SYSTEM.md) | Reglas, balance y configuración del sistema PvP. |
| [`TRADE_SYSTEM.md`](TRADE_SYSTEM.md) | Sistema de trade entre jugadores. |
| [`CHARACTER_SESSION_REPLACEMENT.md`](CHARACTER_SESSION_REPLACEMENT.md) | Reemplazo de sesión de personaje, recovery de cuentas. |
| [`SMOKE_TESTS.md`](SMOKE_TESTS.md) | Tests de humo locales y en VPS antes de cada release. |
| [`MIGRATION_PLAYBOOK.md`](MIGRATION_PLAYBOOK.md) | Playbook para migraciones grandes (esquema DB, data, deploys críticos). |
| [`../scripts/deploy/README-DEPLOY-VPS.md`](../scripts/deploy/README-DEPLOY-VPS.md) | Deploy seguro en VPS de producción (checklist, rollback). Ver también [`../scripts/README.md`](../scripts/README.md). |
| [`_archive/DEPLOY-PENDIENTE-VPS-JUL2026.md`](_archive/DEPLOY-PENDIENTE-VPS-JUL2026.md) | *(archivado)* Snapshot jul 2026: qué faltaba deployar al VPS. |
| [`_archive/PUSH-MAIN-JUL2026-SPELLS-NPC-NO-VPS.md`](_archive/PUSH-MAIN-JUL2026-SPELLS-NPC-NO-VPS.md) | *(archivado)* Push a main jul 2026 sin VPS (spells/NPC). |

---

## Sistemas y estabilidad

Todo lo relacionado con estabilidad del OT server, cuelgues, sockets, crashes.

| Doc | Cubre / cuándo leerlo |
|-----|-----------------------|
| [`systems/PREVENT_OT_HANGS.md`](systems/PREVENT_OT_HANGS.md) | Si el server se cuelga o se observa lentitud: checklist preventivo. |
| [`systems/CRASH_DIAGNOSTICS.md`](systems/CRASH_DIAGNOSTICS.md) | Si el OT crashea: cómo recolectar diagnóstico y encontrar la causa. |
| [`systems/SOCKET_DEBUG_LOGGING.md`](systems/SOCKET_DEBUG_LOGGING.md) | Si hay kicks masivos, desconexiones o problemas de socket. |
| [`systems/OT_HANG_ROOT_CAUSE_SEND_BLOCKING.md`](systems/OT_HANG_ROOT_CAUSE_SEND_BLOCKING.md) | Análisis técnico de la causa raíz del cuelgue por send blocking. |

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
| [`gameplay/BOAT_TRAVEL.md`](gameplay/BOAT_TRAVEL.md) | Viajes de Nimral/Fargum: destinos (incl. Gauntlet), Hell Quest, confirmación y reglas de temple. |
| [`gameplay/MOST_WANTED_SYSTEM.md`](gameplay/MOST_WANTED_SYSTEM.md) | Sistema de bounty / most wanted entre jugadores. |
| [`gameplay/DAILY_TASK.md`](gameplay/DAILY_TASK.md) | **Daily Task (Huntmaster):** 3 contratos/día por rango de level, kills + oro o exp, streak. |
| [`gameplay/GEMS.md`](gameplay/GEMS.md) | Sistema de gemas: drop, uso, imbuements. Antes de tocar gemas, leer esto. |
| [`gameplay/CRYSTAL_ARROW.md`](gameplay/CRYSTAL_ARROW.md) | **Crystal Arrow (2352):** throwable tipo spear, Blue Gem speed ×5, hit 85%; spears 70% hit. |
| [`gameplay/DEPOTS.md`](gameplay/DEPOTS.md) | **Depots:** lockers 2589, XML vs mapa, incidente jul 2026, checklist pre-deploy de mapa. |
| [`gameplay/HOUSES.md`](gameplay/HOUSES.md) | **Casas:** dueños en `data/houses/*.xml`, deploy, backup y recuperación (incidente jul 2026). |
| [`gameplay/GOLDEN_ACCESSORIES.md`](gameplay/GOLDEN_ACCESSORIES.md) | Golden amulet y golden ring: auto-bank, bonus de oro e interacción entre ambos. |
| [`gameplay/SOFT_BOOTS.md`](gameplay/SOFT_BOOTS.md) | **Soft Boots (3549):** +3 HP / +12 MP cada 3 s, 4 h de uso → worn (3550); C++ `YUR_SOFT_BOOTS`. |
| [`gameplay/NPC_CONFIRMATION.md`](gameplay/NPC_CONFIRMATION.md) | Confirmación de transacciones con NPC (anti-misflow). |
| [`gameplay/SELLER_FLUIDS.md`](gameplay/SELLER_FLUIDS.md) | Sistema de vendedores de fluids/potions. |
| [`gameplay/DARK_RODO_RUNE_BACKPACKS.md`](gameplay/DARK_RODO_RUNE_BACKPACKS.md) | Backpacks especiales de runas y Dark Rodo. |
| [`gameplay/RUNE_WEIGHT_RL.md`](gameplay/RUNE_WEIGHT_RL.md) | Peso de runas y lógica RL asociada. |
| [`gameplay/DESINTEGRATE_RUNE.md`](gameplay/DESINTEGRATE_RUNE.md) | Implementación real de la rune Desintegrate: magic wall, wild growth y objetos destruibles. |
| [`gameplay/SPELL_RUNTIME.md`](gameplay/SPELL_RUNTIME.md) | **Spells/runas:** carga XML→Lua, `safeCast` anti-crash, restauración Soulfire/Paralyze/etc. (jul 2026). Leer antes de tocar `spells.xml` / `spells.cpp`. |
| [`gameplay/SPELL_EXHAUSTION.md`](gameplay/SPELL_EXHAUSTION.md) | **Exhausted:** `exhausted`/`exhaustedheal`/`exhaustedadd`, pipeline `creatureMakeMagic`, reduceExhaustion, bindings custom sin exhaust (Paralyze/Anchor/etc.). |
| [`gameplay/MAGIC_WALL.md`](gameplay/MAGIC_WALL.md) | **Magic Wall:** duración 15s, `DECAY_INTERVAL`, bug de relanzar sin reiniciar timer (jul 2026). |
| [`gameplay/ANCHOR_RUNE.md`](gameplay/ANCHOR_RUNE.md) | Anchor Rune (2296): root de 1s (no paralyze) para war/combos. |
| [`gameplay/SPELL_CAST_VISIBILITY.md`](gameplay/SPELL_CAST_VISIBILITY.md) | Visibilidad del cast de hechizos (efectos visuales). |
| [`gameplay/SPELL_EXORI_GRAN.md`](gameplay/SPELL_EXORI_GRAN.md) | Hechizo exori gran: balance, área, daño. |
| [`gameplay/SPELL_EXORI_HUR.md`](gameplay/SPELL_EXORI_HUR.md) | **exori hur** target a distancia (battle list, rango 5) + binding `getAttackedCreaturePos`; incluye script viejo y pasos de revert (jul 2026). |
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
| [`items-and-map/MAPEAR_CON_CODIGO.md`](items-and-map/MAPEAR_CON_CODIGO.md) | Mapear items/pisos por código (no manual) usando scripts. |
| [`items-and-map/MAPEAR_LABERINTO.md`](items-and-map/MAPEAR_LABERINTO.md) | Laberinto procedural 2 sqm: camino 406, fondo 100 (pared), teleport al templo (`generate-maze.py`). |
| [`items-and-map/MAPEAR_TP_GAUNTLET.md`](items-and-map/MAPEAR_TP_GAUNTLET.md) | Gauntlet: 40 salas 3×3 + sala final 3×3 (Wrath + demon armor, 1 TP); barco `gauntlet`. |
| [`items-and-map/ISLAND_BANDS.md`](items-and-map/ISLAND_BANDS.md) | Cómo componer las bandas agua→shore→dirt→grass para que una isla no se vea con corte duro. Especificación de las 5 bandas y 7 reglas críticas. |
| [`items-and-map/ZAGAN_TEST_ITEMS.md`](items-and-map/ZAGAN_TEST_ITEMS.md) | Items de prueba del entorno Zagan (dev/test). |
| [`items-and-map/SESION_EDITOR_MAPA_JUL2026.md`](items-and-map/SESION_EDITOR_MAPA_JUL2026.md) | Bitácora de la sesión de editor de mapa de julio 2026. |

---

## Catálogo de features

Catálogo completo de features del juego. Cada feature tiene su doc individual en `docs/features/`. El index maestro está en [`FEATURE_CATALOG.md`](FEATURE_CATALOG.md).

| Doc | Feature |
|-----|---------|
| [`FEATURE_CATALOG.md`](FEATURE_CATALOG.md) | Índice maestro de features (leer primero si buscás una feature específica). |
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

---

## Búsqueda rápida por síntoma

| Síntoma / necesidad | Ir a |
|---------------------|------|
| El OT se cuelga o está lento | [`systems/PREVENT_OT_HANGS.md`](systems/PREVENT_OT_HANGS.md) |
| El OT crashea y no sé por qué | [`systems/CRASH_DIAGNOSTICS.md`](systems/CRASH_DIAGNOSTICS.md) |
| Kicks masivos o desconexiones | [`systems/SOCKET_DEBUG_LOGGING.md`](systems/SOCKET_DEBUG_LOGGING.md) |
| Quiero entender la causa raíz de cuelgues | [`systems/OT_HANG_ROOT_CAUSE_SEND_BLOCKING.md`](systems/OT_HANG_ROOT_CAUSE_SEND_BLOCKING.md) |
| Un item no entra o se ve mal | [`items-and-map/IMPORTAR_ITEM_DESDE_IMAGEN.md`](items-and-map/IMPORTAR_ITEM_DESDE_IMAGEN.md) |
| Necesito mapear items por código | [`items-and-map/MAPEAR_CON_CODIGO.md`](items-and-map/MAPEAR_CON_CODIGO.md) |
| Generar una isla coherente (bandas agua/pasto) | [`items-and-map/ISLAND_BANDS.md`](items-and-map/ISLAND_BANDS.md) |
| Quiero generar un laberinto por código | [`items-and-map/MAPEAR_LABERINTO.md`](items-and-map/MAPEAR_LABERINTO.md) |
| Quiero un gauntlet de salas 3×3 con TPs | [`items-and-map/MAPEAR_TP_GAUNTLET.md`](items-and-map/MAPEAR_TP_GAUNTLET.md) + [`gameplay/BOAT_TRAVEL.md`](gameplay/BOAT_TRAVEL.md) |
| Quiero crear un monstruo nuevo | [`gameplay/MONSTER_CREATION.md`](gameplay/MONSTER_CREATION.md) |
| Voy a tocar gemas o imbuements | [`gameplay/GEMS.md`](gameplay/GEMS.md) → [`features/10-gems-and-imbuements.md`](features/10-gems-and-imbuements.md) |
| Skill ring + emerald armor + crimson no suman | [`gameplay/GEMS.md`](gameplay/GEMS.md) (Big Emerald / stacking) + `Player::getSkill` en `player.cpp` |
| Voy a hacer deploy a producción | [`../scripts/deploy/README-DEPLOY-VPS.md`](../scripts/deploy/README-DEPLOY-VPS.md) |
| Necesito migrar DB o data crítica | [`MIGRATION_PLAYBOOK.md`](MIGRATION_PLAYBOOK.md) |
| Voy a cambiar el mapa del server | [`CAMBIAR-MAPA.md`](CAMBIAR-MAPA.md) → [`gameplay/DEPOTS.md`](gameplay/DEPOTS.md) |
| Jugadores reportan depot vacío | [`gameplay/DEPOTS.md`](gameplay/DEPOTS.md) |
| Deploy / dueños de casas borrados | [`gameplay/HOUSES.md`](gameplay/HOUSES.md) |
| Wand pega siempre igual sin importar ML / imbue de Violet | [`gameplay/WANDS.md`](gameplay/WANDS.md) |
| Quiero ver qué features tiene el juego | [`FEATURE_CATALOG.md`](FEATURE_CATALOG.md) |
| Necesito configurar el editor RME | [`RME_SETUP.md`](RME_SETUP.md) |
| Tests de humo antes de release | [`SMOKE_TESTS.md`](SMOKE_TESTS.md) |
