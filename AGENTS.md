# AGENTS.md — Contrato para agentes IA en YurOTS / Retro76

> Este archivo es el contrato de comportamiento para **cualquier** agente de IA (Codex, Cursor, opencode, Claude Code, etc.) que abra este repositorio.
>
> Si entrás a trabajar acá, este archivo tiene prioridad sobre tu entrenamiento por defecto. Cuando algo no se entienda o choque con la documentación existente, **preguntale al usuario** antes de improvisar.

---

## 0. Contexto mínimo del proyecto

| Item | Valor |
|------|--------|
| Juego | **Retro76** — OTServ Tibia 7.6 (motor **YurOTS** en C++ legacy) |
| Repo | `https://github.com/gpedrosad/serverrepo.git` — rama `main` |
| Local (dev) | `~/Desktop/yurots-principal/` — Docker, `127.0.0.1:7171` |
| Producción | VPS `64.176.20.238` — dominio **retro76.cl** — puerto **7171** |
| Data de jugadores | **Solo en el VPS** — sagrada, no se toca sin backup |
| Stack | C++ legacy, Lua scripts, OTBM maps, Docker `i386`, bash/python |

---

## 1. Antes de tocar nada — checklist obligatorio

Antes de proponer **cualquier** cambio, leer en este orden:

1. `README.md` — overview general del repo.
2. `AGENTS.md` — este archivo (ya lo estás leyendo).
3. `LEERCODEX.md` — playbooks de incidente, SSH, scripts y diagnóstico.
4. `docs/INDEX.md` — índice maestro de toda la documentación.
5. Según la tarea:
   - Deploy al VPS → `scripts/README-DEPLOY-VPS.md`
   - Cambios grandes / arquitectura → `docs/PROYECTO.md`
   - Subsistema puntual → el doc específico (ver sección 3).

Si alguno de estos archivos no existe, **avisar** al usuario antes de seguir.

---

## 2. Reglas de oro (no negociables)

1. **NUNCA** ejecutar `git stash -u`, `git clean -fd`, `git reset --hard` ni borrado masivo dentro del VPS. Eso borra cuentas y personajes reales.
2. **NUNCA** commitear data runtime de jugadores: `accounts/`, `players/` (excepto `0-4.xml`), `online.xml`, `queue.xml`, `houseitems.xml`, `data/houses/*.xml` con dueños reales de prod, `web/state/*.json`.
3. **NUNCA** commitear binarios ni artefactos: `source/yurots`, `*.o`, `*.bak`, `*.patch`, `core.*`, `*.log` rotados.
4. **NUNCA** deployar al VPS si el usuario solo pidió debug local. **Siempre preguntar**.
5. **SIEMPRE** usar `DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh` para deployar (nada de `docker cp` artesanal).
6. **SIEMPRE** verificar el estado del servidor con `python3 scripts/ot-probe.py 127.0.0.1 7171` después de tocar el OT (local o VPS).
7. Smoke tests locales **desactivados temporalmente** (`scripts/.smoke-tests-disabled`). No correr `test-local-smoke.sh` salvo que el usuario pida reactivarlos o use `--force`. Para validar boot/protocolo usar `ot-probe.py`.
8. **SIEMPRE** consultar `docs/INDEX.md` y el doc del subsistema antes de tocar ese subsistema.
9. **SIEMPRE** leer el doc de deploy completo al menos una vez antes del primer deploy al VPS.
10. Si algo no se entiende del flujo o del incidente, **preguntar antes de actuar**.
11. **NUNCA** deployar un `test.otbm` nuevo sin probar depots in-game (locker temple → debe mostrar items del jugador, no contenedor vacío). Ver `docs/gameplay/DEPOTS.md`.
12. Si un jugador reporta “depot vacío”, **no tocar** `players/*.xml` de entrada: los items suelen estar en `<depot depotid="1">`; el bug es mapa/C++, no pérdida de data.

---

## 3. Cómo encontrar el doc correcto

El proyecto usa un sistema *self-learning*: cada subsistema tiene su propio doc. Antes de tocar algo, **leer el doc que corresponde**.

| Subsistema | Doc |
|------------|-----|
| Gemas / minería / crafting | `docs/gameplay/GEMS.md` |
| Crystal Arrow (spear-like + Blue Gem speed + hit chance) | `docs/gameplay/CRYSTAL_ARROW.md` |
| Daily Task / Huntmaster (contratos diarios) | `docs/gameplay/DAILY_TASK.md` |
| PvP, frag list, balance de combate | `docs/PVP_SYSTEM.md` |
| Trade, items, transacciones | `docs/TRADE_SYSTEM.md` |
| Depots, lockers 2589, deploy de mapa | `docs/gameplay/DEPOTS.md` |
| Magic Wall (duración / decay de fields) | `docs/gameplay/MAGIC_WALL.md` |
| Wands, rods, Crimson Wand, escalado de ML | `docs/gameplay/WANDS.md` |
| Spells / runas (carga Lua, safeCast, Soulfire, Paralyze, Anchor) | `docs/gameplay/SPELL_RUNTIME.md` |
| Whirlwind Throw (`exori hur`) target a distancia | `docs/gameplay/SPELL_EXORI_HUR.md` |
| Energy Strike Hur (`exori vis hur`) target a distancia (Sorc/Druid, visual HMM) | `docs/gameplay/SPELL_EXORI_VIS_HUR.md` |
| Exhausted (spells/runas, heal vs attack, bindings sin exhaust) | `docs/gameplay/SPELL_EXHAUSTION.md` |
| Cambiar / exportar mapa OTBM | `docs/CAMBIAR-MAPA.md` |
| Cliente retro76 / updater | `docs/CLIENT.md` y `docs/CLIENT_UPDATER_RETRO76.md` |
| Sockets, cuelgues, kicks | `docs/systems/SOCKET_DEBUG_LOGGING.md` y `docs/systems/PREVENT_OT_HANGS.md` |
| Crash / core dumps | `docs/systems/CRASH_DIAGNOSTICS.md` |
| RME / edición de mapa | `docs/RME_SETUP.md` |
| Cambios de mapa / OTBM | `docs/CAMBIAR-MAPA.md` |
| Items custom Zagan (sprites, OTB, gameplay) | `docs/items-and-map/ZAGAN_TEST_ITEMS.md` y `docs/items-and-map/IMPORTAR_ITEM_DESDE_IMAGEN.md` |

Si el subsistema no aparece en la tabla, buscar en `docs/INDEX.md` o preguntar.

---

## 3.1 Animaciones de armas (projectiles / `shootType`)

En YurOTS 7.6 las "animaciones de arma" son los proyectiles de distancia enviados con
`sendDistanceShoot`. No hay animación configurable de swing para armas melee normales:
el hit visual melee sale del target (`bloodeffect`) o de `NM_ME_PUFF` si no pega.

Fuentes canónicas:
- Constantes C++: `server/YurOTS/ots/source/const76.h`
- Mapeo OTB -> C++: `server/YurOTS/ots/source/itemloader.h` y `server/YurOTS/ots/source/items.cpp`
- Uso en combate: `server/YurOTS/ots/source/player.cpp` (`GetDistWeapon`, `getSubFightType`) y `server/YurOTS/ots/source/game.cpp` (`sendDistanceShoot`)
- Constantes Lua para spells/runes: `server/YurOTS/ots/data/spells/lib/spells.lua`

**Importante:** `server/YurOTS/ots/data/items/items.xml` no configura `shootType`.
Ese XML solo sobreescribe atributos como `weight`, `charges`, `time`, `door` y `questbox`.
Para cambiar la animación real de un arma, munición o arma mágica hay que editar/parchear
`server/YurOTS/ots/data/items/items.otb` (y el OTB equivalente de test si aplica).

Tipos disponibles:

| OTB `shootType` | C++ `DIST_*` | Lua `NM_ANI_*` | Uso típico |
|-----------------|--------------|----------------|------------|
| `OTB_DIST_NONE` (`0`) | `DIST_NONE` | `NM_ANI_NONE` (`0`) | Sentinel interno/no projectile en spells. Evitar en armas reales salvo prueba visual, porque comparte valor C++ con spear. |
| `OTB_DIST_BOLT` (`1`) | `DIST_BOLT` | `NM_ANI_BOLT` (`1`) | Bolts de crossbow. |
| `OTB_DIST_ARROW` (`2`) | `DIST_ARROW` | `NM_ANI_ARROW` (`2`) | Arrows de bow. |
| `OTB_DIST_FIRE` (`3`) | `DIST_FIRE` | `NM_ANI_FIRE` (`3`) | Misil/fireball visual, armas mágicas de fuego. |
| `OTB_DIST_ENERGY` (`4`) | `DIST_ENERGY` | `NM_ANI_ENERGY` (`4`) | Misil de energía, armas mágicas de energía. |
| `OTB_DIST_POISONARROW` (`5`) | `DIST_POISONARROW` | `NM_ANI_POISONARROW` (`5`) | Flecha/misil venenoso. |
| `OTB_DIST_BURSTARROW` (`6`) | `DIST_BURSTARROW` | `NM_ANI_BURSTARROW` (`6`) | Burst arrow / explosivo. |
| `OTB_DIST_THROWINGSTAR` (`7`) | `DIST_THROWINGSTAR` | `NM_ANI_THROWINGSTAR` (`7`) | Throwing star. |
| `OTB_DIST_THROWINGKNIFE` (`8`) | `DIST_THROWINGKNIFE` | `NM_ANI_THROWINGKNIFE` (`8`) | Throwing knife. |
| `OTB_DIST_SMALLSTONE` (`9`) | `DIST_SMALLSTONE` | `NM_ANI_SMALLSTONE` (`9`) | Small stone. |
| `OTB_DIST_SUDDENDEATH` (`10`) | `DIST_SUDDENDEATH` | `NM_ANI_SUDDENDEATH` (`10`) | Sudden death/death missile. |
| `OTB_DIST_LARGEROCK` (`11`) | `DIST_LARGEROCK` | `NM_ANI_LARGEROCK` (`11`) | Large rock, usado por `exori hur`. |
| `OTB_DIST_SNOWBALL` (`12`) | `DIST_SNOWBALL` | `NM_ANI_SNOWBALL` (`12`) | Snowball. |
| `OTB_DIST_POWERBOLT` (`13`) | `DIST_POWERBOLT` | `NM_ANI_POWERBOLT` (`13`) | Power bolt. |
| `OTB_DIST_SPEAR` (`14`) | `DIST_SPEAR` | `NM_ANI_SPEAR` (`0`, solo C++) | Spear. Caso legacy: el valor C++ es `0`; usar el valor OTB `14` al editar items. |
| `OTB_DIST_POISONFIELD` (`15`) | `DIST_POISONFIELD` | `NM_ANI_FLYPOISONFIELD` (`14`, solo C++) | Proyectil de poison field/poison cloud volando; usado por monstruos y fields. |

Cómo se usa en armas:
- Bow/crossbow con ammo: el proyectil lo define la munición equipada en `SLOT_AMMO`, no el arco. `GetDistWeapon()` devuelve el ammo cuando el `amuType` coincide (`AMU_ARROW` o `AMU_BOLT`).
- Armas arrojadizas: deben ser `weaponType = DIST`, `amuType = AMU_NONE`; el motor usa el `shootType` del arma misma y consume el stack si corresponde.
- Armas mágicas/custom a distancia: `weaponType = MAGIC` también usa el `shootType` del item para el proyectil.
- Melee normal: no manda `sendDistanceShoot`. La excepción custom actual es Nightglass Dagger (`YUR_BOH`), que manda `NM_ANI_FIRE` desde C++.
- Spells/runes Lua: usar `animationEffect = NM_ANI_*` en el script. `NM_ANI_NONE = 0` no se envía porque `magic.cpp` solo dispara proyectil si `animationEffect > 0`.

Después de tocar `items.otb`, armas o lógica C++ relacionada:
1. Levantar local con `docker compose -f docker-compose.prod.yml up -d yurots`.
2. Correr `python3 scripts/ot-probe.py 127.0.0.1 7171` (smoke tests desactivados; ver regla §2.7).
3. Probar in-game con el cliente: equipar arma/ammo y atacar a distancia; el contenedor `Up` no confirma que el protocolo esté OK.

---

## 4. Workflow de cambio típico

Para un cambio serio (no trivial) seguir este orden, sin saltearse pasos:

1. **Local**: editar en Mac. Levantar con `docker compose -f docker-compose.prod.yml up -d yurots`.
2. **Probar local**: `python3 scripts/ot-probe.py 127.0.0.1 7171` (smoke tests desactivados temporalmente).
3. **Stage selectivo**: `git add` solo lo relevante (código fuente, datos de juego, docs). Verificar con `git status` antes de commitear.
4. **Commit + push**: `git commit -m "..."` y `git push origin main`.
5. **Deploy al VPS** (solo si el usuario lo autorizó): `DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh`.
6. **Verificar post-deploy**: `ot-probe.py` contra el VPS, `docker logs yurots --tail 30`, y conteo de cuentas/personajes para detectar pérdidas.

Si en cualquier paso aparece algo raro (probe FAIL, smoke test FAIL, archivos sensibles en `git status`), **frenar y avisar** al usuario.

---

## 5. Comunicación con el usuario

**Preguntar antes** de:
- Deployar al VPS.
- Cambios que recompilen el binario C++ (rebuild largo, riesgo de regresión).
- Cambios en data runtime (accounts, players, houses, online.xml).
- Cualquier acción irreversible (`git reset --hard`, `rm -rf`, drop de DB, etc.).
- Cambios de scope grande (refactor, migraciones, reescrituras).

**No preguntar** para:
- Investigar (leer archivos, buscar con grep, entender el código).
- Correr scripts read-only (`ot-probe.py`, `ot-diagnostics.sh`, `git status`, `git log`).
- Cambios locales que no se commitean.
- Proponer planes o diffs para review.

**Reportar siempre** al final del trabajo:
- Qué archivos tocaste (con `file_path:line_number` cuando aplique).
- Qué scripts corriste y qué resultados viste.
- Si quedó algo pendiente o dudoso.

---

## 6. Anti-patrones

Cosas que un agente **NO** debe hacer en este repo:

- **Reescribir archivos "para limpiar"** sin que lo pidan. YurOTS es viejo y muchos paths feos son intencionales.
- **"Mejorar" código legacy** por iniciativa propia. Si ves un `goto` viejo que funciona, no lo toques.
- **Sugerir migrar a otro motor/framework** (OTX, TFS, etc.). Es YurOTS 7.6 y se queda en YurOTS 7.6.
- **Asumir que el contenedor `Up` significa que el server responde**. El caso clásico de jul 2026: contenedor `Up (healthy)`, puerto acepta TCP, pero el protocolo OT no responde. **Siempre** probar con `ot-probe.py`.
- **Hacer PRs / commits enormes**. Un cambio lógico por commit. Si el diff pasa de ~300 líneas, partirlo.
- **Borrar archivos "huérfanos"** sin confirmar con el usuario. Pueden ser parte del deploy.
- **Inventar paths, comandos o flags** que no estén en el repo. Si dudás, leer primero.

---

## 7. Stack y comandos rápidos

| Tarea | Comando |
|-------|---------|
| Build del binario (dentro del container) | `cd /app/YuroTS/ots/source && make clean && make` |
| Levantar local (modo prod) | `docker compose -f docker-compose.prod.yml up -d yurots` |
| Probe de estado del OT | `python3 scripts/ot-probe.py 127.0.0.1 7171` |
| Diagnóstico completo | `./scripts/ot-diagnostics.sh` |
| Logs del servidor | `tail -f server/YurOTS/ots/yurots.log` |
| Logs Docker | `docker logs yurots --tail 50 -f` |
| Web local (status page) | `./scripts/web.sh` → http://localhost:8080 |
| Cliente de prueba | `./scripts/play-yurots-client.sh` |
| Deploy al VPS | `DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh` |
| Smoke tests locales | Desactivados (`scripts/.smoke-tests-disabled`). Reactivar: borrar ese archivo. Forzar: `bash scripts/test-local-smoke.sh --force` |
| Rebuild C++ (sin clean, más rápido) | `docker compose -f docker-compose.prod.yml run --rm yurots bash -c 'cd /app/YuroTS/ots/source && make -j2 yurots'` |
| Cliente / mapa Zagan test | `./scripts/play-zagan-test-client.sh` o `./scripts/open-rme-zagan-test.sh` |

---

## 8. Items custom Zagan — gameplay en C++

Los items del pack Zagan (`zagan-test/manifest.json`, server ids `20100+`, OTB `items-zagan-test.otb`) tienen **dos capas**:

1. **Assets** — sprites, `.dat`, OTB, nombres: `scripts/build_zagan_test_assets.py` + `scripts/install-zagan-test-env.sh`.
2. **Gameplay** — bonus de skills, wands, paralyze, etc.: **obligatorio en C++** (`server/YurOTS/ots/source/`). El `gameplaySpec` del manifest es solo documentación; el servidor **no lo lee**.

Tras tocar C++: rebuild del binario + `docker compose restart yurots` + `python3 scripts/ot-probe.py 127.0.0.1 7171`. Si se agregó un miembro a `Creature`/`Player` (ej. `imbueCrimsonHelm` en `creature.h`), hacer **`make clean && make`** — un build parcial puede segfaultear al boot.

### Vocaciones promovidas (Master Sorcerer, Elder Druid, Elite Knight, Royal Paladin)

En YurOTS 7.6 **no hay ids de vocación separados** para promoted. El enum sigue siendo:

| `playervoc_t` | Base | Promoted (`promoted=1`) |
|---------------|------|-------------------------|
| `1` | Sorcerer | Master Sorcerer |
| `2` | Druid | Elder Druid |
| `3` | Paladin | Royal Paladin |
| `4` | Knight | Elite Knight |

Nombres en runtime: `config.lua` → `promoted_vocations`. Flag persistido en XML del player (`promoted`).

**Regla para C++:** chequear `VOCATION_SORCERER`/`VOCATION_DRUID` o `VOCATION_PALADIN`/`VOCATION_KNIGHT` — **no** inventar voc `5+`. Usar helpers:

- `isKnightOrPaladinFamily()` en `player.cpp` — helmet / emerald armor skills
- `isSorcererOrDruidFamily()` en `game.cpp` — crimson wand en `useWand()`

### Checklist al dar gameplay a un item Zagan

| Paso | Dónde |
|------|--------|
| Constante `ITEM_*` | `const76.h` |
| Descripción al look | `item.cpp` (`fullDescription`) |
| Bonus equipado (skills, ML, speed) | `player.cpp` — `getSkill()`, `getEffectiveMagLevel()`, `checkBoh()` |
| Refrescar UI al equipar/desequipar | Ver patrón **helmet / `SLOT_HEAD`** abajo; body/wand usan `checkBoh()` + `sendStats()`/`sendSkills()` |
| Wand / rod custom | `player.cpp` — `isWandItem()`, `getWandId()`; `game.cpp` — `useWand()` bajo `#ifdef JD_WANDS` |
| Delay de ataque custom (wands) | `player.cpp` — `getAttackDelayMs()` |
| Efecto on-hit (PvP, etc.) | `game.cpp` |
| OTB slot/tipo incorrecto | Parchear con script tipo `scripts/patch-fury-cape-otb.py` o regenerar desde prototipo en el builder |
| Premio en quest chest del mapa test | `data/actions/scripts/quest.lua` — `uniqueId` debe caer en rango válido (`20100`–`20199`) |
| Login con item ya equipado | `ioplayerxml.cpp` — `checkBoh()` tras cargar `inventory` |

### Patrón referencia: bonus de skills en helmet (`SLOT_HEAD`) — Crimson Helmet

Implementación probada en **`20113`**. Copiar este patrón para futuros helmets con bonus de skills.

**1. `getSkill()` — leer el slot en vivo (como los rings), no solo cache:**

```cpp
if (items[SLOT_HEAD] && items[SLOT_HEAD]->getID() == ITEM_CRIMSON_HELMET &&
    isKnightOrPaladinFamily(vocation) && /* sword/club/axe/dist */)
    return skills[skilltype][skillinfo] + 1;
```

**2. `checkBoh()` — cache `imbueCrimsonHelm` solo para detectar cambios** y disparar `sendSkills()` cuando `hadCrimsonHelm != crimsonHelmNow` (mismo patrón que `imbueEmeraldArmor`).

**3. `Player::refreshHeadSkillBonus(fromSlot, toSlot)`** — punto único de refresco UI para head:

- Solo actúa si `fromSlot == SLOT_HEAD` o `toSlot == SLOT_HEAD`
- Orden: **`checkBoh()` primero**, luego `client->sendSkills()`
- Llamar **después** de que `game.cpp` ya actualizó `items[]` (nunca antes del move)

**4. Dónde llamar `refreshHeadSkillBonus`:**

| Momento | Archivo / función |
|---------|-------------------|
| Equip/desequip directo | `addItemInventory()`, `removeItemInventory()` si `pos == SLOT_HEAD` |
| Drag & drop | Todos los overloads de `Player::onThingMove()` que tocan `SLOT_HEAD` — **al final**, tras `sendThingMove` |
| Login con casco puesto | `ioplayerxml.cpp` — `checkBoh()` al terminar de cargar `inventory` |

Caminos de `onThingMove` que deben cubrir `SLOT_HEAD`: inventory↔inventory, inventory→container, container→inventory, inventory→ground, ground→inventory.

**5. No hacer:** llamar `sendSkills()` **antes** de `checkBoh()` ni confiar solo en `imbueCrimsonHelm` dentro de `getSkill()` — al desequipar el bonus quedaba pegado en la UI.

### Items con gameplay implementado (referencia jul 2026)

| Server id | Nombre | Qué hace | Archivos clave |
|-----------|--------|----------|----------------|
| `20113` | crimson helmet | Knight/Elite Knight y Paladin/Royal Paladin: +1 sword, club, axe, distance (`SLOT_HEAD`). UI vía `refreshHeadSkillBonus()` + `getSkill()` en vivo. | `const76.h`, `creature.h` (`imbueCrimsonHelm`), `player.cpp`, `player.h`, `ioplayerxml.cpp`, `item.cpp` |
| `20114` | fury cape | Sorc/Master Sorc y Druid/Elder Druid: +1 ML (`SLOT_ARMOR`) | `player.cpp` (`imbueArmorMl`, `checkBoh`) |
| `20105` | medusa sword | Paralyze PvP on-hit | `game.cpp` (`applyMedusaParalyze`) |
| `20139` | sword of silence | 10% silencio PvP 2–3s (solo spells hablados; runas/potions OK); CD 12s/target | `game.cpp` (`applySwordOfSilence`), `creature.h` (`silenceTicks`), `item.cpp`, OTB via `scripts/patch-sword-of-silence-otb.py`, loot Fury `fury.xml` chance 400 |
| `20123` | crimson wand | Sorc/Master Sorc y Druid/Elder Druid lv33+: wand 55–65 dmg, 13 mana, range 5, delay 667ms, animación **adori gran** (HMM), imbue ML hasta +4 | `const76.h`, `player.cpp` (`isWandItem`, `getWandId`, `getAttackDelayMs`), `game.cpp` (`useWand`, `isSorcererOrDruidFamily`), `item.cpp` |
| `20126` | train wand | Sorc/MS y Druid/ED: solo trainers (`trainer=1`), 0 mana, `addManaSpent(1)` (~50% Vortex), daño 1–1 | `const76.h`, `player.cpp` (`isWandItem`, `getWandId`), `game.cpp` (`useWand`), `item.cpp` |
| `2352` | crystal arrow | Throwable DIST tipo spear (atk 35, **85% hit**, no se consume). Blue Gem → hasta 5 stacks +5% attack speed (AID 9070–9074). Spears (`2389`) suben a **70% hit**. Loot: Enraged Hero `450`, Furious Amazon `300`. | `const76.h` (`SPEAR_HIT_CHANCE`, `CRYSTAL_ARROW_HIT_CHANCE`), `creature.h` (`imbueCrystalArrowSpeed`), `player.cpp`, `item.cpp`, `game.cpp` (rare loot), `gem_imbue.lua`, OTB via `scripts/patch-crystal-arrow-otb.py` |

### Pitfalls que ya mordieron a agentes

- **Bonus en `getSkill()` pero la UI no sube al equipar** — falta `sendSkills()` en algún camino de `SLOT_HEAD` (típico: ground→inventory olvidado). Usar `refreshHeadSkillBonus()`.
- **Bonus en UI no baja al desequipar** — bug real jul 2026 en Crimson Helmet: `sendSkills()` se llamaba **antes** de `checkBoh()`, y `getSkill()` leía solo `imbueCrimsonHelm` cacheado. Fix: `getSkill()` lee `items[SLOT_HEAD]` en vivo + `refreshHeadSkillBonus()` siempre hace `checkBoh()` → `sendSkills()` **después** del move.
- **Bonuses de skill que no se apilan** — bug real jul 2026: axe ring + emerald armor + crimson helmet no sumaban porque `getSkill()` hacía `return base + X` en cascada (ring ganaba; sin ring emerald ocultaba crimson/`tempoBuff`). Fix: acumular en una sola `value` (mismo patrón que `getEffectiveMagLevel()`). No volver a early-return por fuente.
- **Wand con sprite de inferno pero ataca melee** — falta registrar el id en `isWandItem()` + `getWandId()` + rama en `useWand()`. Sin eso `getWandId()` devuelve 0 y el combate usa daño físico normal.
- **Crimson Wand / promoted mages** — Master Sorcerer y Elder Druid son `promoted=1` con `VOCATION_SORCERER`/`VOCATION_DRUID`. Usar `isSorcererOrDruidFamily()` en `useWand()`; no crear voc ids nuevos.
- **Crimson Helmet / promoted fighters** — Elite Knight y Royal Paladin son `promoted=1` con `VOCATION_KNIGHT`/`VOCATION_PALADIN`. Usar `isKnightOrPaladinFamily()` en `getSkill()` y `checkBoh()`.
- **Animación adori gran** — copiar la runa HMM: `ATTACK_ENERGY`, `NM_ANI_FIRE`, `NM_ME_EXPLOSION_DAMAGE`, `NM_ME_ENERGY_DAMAGE` (ver `data/spells/runes/heavy magic missile.lua`).
- **Quest chest no da premio** — `quest.lua` rechazaba `uniqueId` fuera de `1001`–`4999`; items Zagan usan `20100+`.
- **Solo manifest / solo OTB no alcanza** — si el item “debería” hacer algo en combate o stats, buscar en `source/` si existe `ITEM_*`; si no, implementar.
- **Rebuild parcial tras tocar `creature.h`** — agregar miembros a `Creature` sin `make clean` dejó el server en crash loop al cargar mapa (jul 2026).

### Depots en mapa (lockers 2589) — incidente jul 2026

**Doc completo:** [`docs/gameplay/DEPOTS.md`](docs/gameplay/DEPOTS.md) — leer **antes** de tocar `test.otbm` o deployar mapa.

**Síntoma:** jugadores abren locker del temple → contenedor vacío; reportan que “perdieron” el depot.

**Realidad:** los items siguen en `players/*.xml` (`<depot depotid="1">`). El mapa no enlazaba el locker con ese id.

**Causa raíz:** lockers `2589` exportados desde RME como **tile inline** (`OTBM_ATTR_ITEM`) **sin** `OTBM_ATTR_DEPOT_ID` → `container->depot == 0` → el motor abre el contenedor vacío del mapa, no el depot del jugador.

**Fix en producción (commit `8acdba0`):** `actions.cpp` → `resolveMapDepotId()` + `openContainer()` — lockers `2589–2592` sin depot id en OTBM resuelven a **`depotid=1`**. Funciona en las **ubicaciones actuales** del mapa (no hace falta mover tiles).

**Checklist mínimo antes de deploy de mapa:**

```bash
python3 scripts/scan-map-depots.py server/YurOTS/ots/data/world/test.otbm
python3 scripts/sync-houses-with-map.py --dry-run
# In-game local: abrir locker temple con char que tenga items en depot → deben verse
```

**Reglas para agentes (resumen):**

1. **Nunca** deployar mapa sin prueba in-game de depot (regla de oro §2.11).
2. **Nunca** editar `players/*.xml` por “depot vacío” sin verificar que el XML aún tiene items.
3. `patch-map-depot-ids.py` **no** parchea lockers inline de RME — no confiar solo en ese script.
4. `scan-map-depots.py` audita lockers antes del deploy.
5. `deploy-vps.sh` preserva `players/` — el deploy de mapa no debe tocar depots XML.
6. Temple = `depotid 1`. Otros ids (`405` casas, etc.) requieren config explícita en RME o extender `resolveMapDepotId()`.

---

## 9. Resumen ejecutivo para agentes con poca atención

- Data de jugadores = sagrada. Si la tocás sin backup, rompiste el server.
- Deploy al VPS = preguntar primero, usar el script, verificar con probe.
- Doc del subsistema = leerlo antes de tocarlo.
- `Up` no significa OK. Probeá.
- Cambios chicos, commits chicos, reportes claros.
- Cuando dudes: **preguntá**.
- Items Zagan con `gameplaySpec` en el manifest **requieren C++** para funcionar en juego (ver sección 8).
- Helmet con bonus de skills: **`refreshHeadSkillBonus()`** + `getSkill()` leyendo `items[SLOT_HEAD]` en vivo — no solo cache en `checkBoh()`.
- **Depot vacío tras cambio de mapa:** items en XML, locker sin enlace → `docs/gameplay/DEPOTS.md` + `resolveMapDepotId()` en `actions.cpp`. Probar locker antes de deploy de `test.otbm`.
- **Dueños de casas en deploy:** `data/houses/*.xml` es runtime en VPS → `docs/gameplay/HOUSES.md`. Nunca `git checkout -- data/houses/` en prod; `deploy-vps.sh` respalda y restaura dueños.
