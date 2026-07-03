# MEMORY.md — Aprendizajes del Equipo · Servidor YurOTS (Retro76)

> Índice de contexto cargado al inicio de cada sesión. Formato de entrada: `- [ROL][FECHA] descripción.`
> Proyecto: OTServ Tibia 7.6 (motor YurOTS) · producción en retro76.cl:7171 · repo `gpedrosad/serverrepo`.

## Aprendizajes del Equipo

### Arquitecto / Tech Lead
- [Arquitecto][2026-07-03] **Equipo de desarrollo del server montado.** Scaffolding creado en `serverrepo`: `CLAUDE.md` (mapa técnico), `AGENTS.md` (roles), `Contexto/MEMORY.md` (este), `.claude/commands/*.md` (11 roles), `.claude/hooks/` (guardrail reforzado + consolidate-memory), `.claude/settings.json`. Roster: `/arquitecto`, `/engine`, `/gameplay`, `/mundo`, `/datos`, `/protocolo`, `/infra`, `/seguridad`, `/qa`, `/auditor`, `/web`. Espejo del equipo del cliente (`clienteretro`) pero adaptado a un servidor OT (motor C++ + scripting + infra).
- [Arquitecto][2026-07-03] **Relación cliente↔server.** `serverrepo` es la fuente de verdad; `clienteretro` (OTClient 7.60) solo renderiza. Dos contratos cruzan el límite y los custodia arquitecto+protocolo: (1) **protocolo 7.60** (parseo ProtocolGame), (2) **`stackable`** (`items.otb` del server ↔ `.dat` del cliente `data/things/760`). Un cambio de stackable es server-side pero requiere tocar el asset del cliente en paralelo.
- [Arquitecto][2026-07-03] **La data de jugadores es sagrada** (`accounts/`, `players/` reales, `vip/`, `houseitems.xml`): solo vive en el VPS, en `.gitignore`, nunca se commitea ni se pisa en deploy. El guardrail bloquea `git commit`/`push`, `git stash -u`, `git clean`, `git reset --hard` y `git add` de esa data.

### Engine / C++ Core
- [Engine][2026-07-03][BLOQUEANTE] **Escribir en ítems (scrolls/papel) NO está implementado.** `Protocol76::parseTextWindow` (`source/protocol76.cpp:1450-1469`) responde literal `"Write not working yet."` y el `readItem->setText(new_text)` está COMENTADO → todo lo que el jugador teclea se descarta. El TODO del autor: mover a Game bajo `gameLock` + validar que el ítem sea accesible. Para un "scroll escribible por jugadores" hay que completar esto. La ventana escribible solo se abre vía Lua `doShowTextWindow(uid,maxlen,canWrite)` (`actions.cpp:1421`), no automático al usar.
- [Engine][2026-07-03] **Persistencia de texto de ítems = solo en casas.** `Item::serialize/unserialize` guardan el atributo `text` (`item.cpp:357-361,412-416`); `Houses::SaveHouseItems` lo escribe a `houseitems.xml` (`houses.cpp:476-511`). Ítems tirados en piso NO se guardan al reiniciar. `Item::setText` tiene modo "write 1 time" vía `readOnlyId` en items.otb (`item.cpp:855-866`): tras la 1ª escritura el ítem muta a su variante read-only si ese id está seteado.
- [Engine][2026-07-03] **Incidente activo (jul 2026): cuelgues en prod.** El proceso vive y acepta TCP pero el protocolo del juego no responde. Debug con `YUROTS_SOCKET_DEBUG=1` (activo en `docker-compose.prod.yml`). Código relevante: `otserv.cpp`, `networkmessage.cpp`, `protocol76.cpp`, `socket_debug.cpp`, `game.cpp`. Root cause candidato: send bloqueante bajo gameLock (`docs/OT_HANG_ROOT_CAUSE_SEND_BLOCKING.md`). Recompilar con `make` dentro del container.

### Gameplay / Scripting
- [Gameplay][2026-07-03] Capa de contenido en `data/`: actions (`actions/scripts/*.lua` + `actions.xml`), spells (`spells/instant`, `spells/runes`, `spells.xml`). Features custom documentadas en `OTINFO` y `docs/features/` (exori gran, exevo pan, soft boots, imbuements, training, magic wall).

### Mundo / Map & Spawns
- [Mundo][2026-07-03] Mapa activo `data/world/test.otbm` (mapa "once", commit `368fb5f`). Templo principal **130,53,6**; templo rook `85,211,7`; NPC Tonka `140,50,7`. Editar con RME (`scripts/open-rme.sh`). `houseitems.xml` es sagrado (solo VPS).

### Data / Items & Monsters
- [Datos][2026-07-03] Ítems en `items.otb` (binario) + `items.xml`. **`stackable` es contrato con el cliente** (.otb ↔ .dat 7.60): si difieren, desync de parseo (`no thing at pos`). Rates en `OTINFO`: exp escalonada x5→x2, loot x3, skills x4, ML x5.

### Protocolo / Networking
- [Protocolo][2026-07-03] Protocolo fijo **7.60**, persistencia XML (`sourcedata="XML"`). Login por cuentas XML → ProtocolGame. Síntomas de desync: `no thing at pos`, `rcv_ms=5000` (timeout handshake residual). Contrato `stackable` .otb↔.dat.

### Infra / DevOps & Deploy
- [Infra][2026-07-03][CRITICO] **Deploy solo por `scripts/deploy-vps.sh`** con `DEPLOY_I_READ_README=yes` (leer `scripts/README-DEPLOY-VPS.md`). Prohibido en VPS: `git stash -u`, `git clean`, `git reset --hard` sin backup, `git pull` a mano — borran cuentas/personajes. Verificar vida con `ot-probe.py` (docker healthy ≠ juego responde). Watchdog: cron 2 min, restart tras 2 fallos.

### Seguridad / Anti-cheat
- [Security][2026-07-03][CRITICO] **El cliente es editable** (Lua en disco) → no confiar en él. Toda mecánica real debe ser server-side y validada. Reglas anti-cheat en `OTINFO` (bots, MC máx 2 online / prohibido en combate, dupes, RMT=ban). Cuentas en `accounts/*.xml` (solo VPS) — no exponer ni loggear credenciales.

### QA Engineer
- [QA][2026-07-03] Smoke tests en `docs/SMOKE_TESTS.md` (login, save, spells, runas, muerte, movimiento). Verificar vida con `python3 scripts/ot-probe.py 127.0.0.1 7171` antes de asumir sano. Logs en `server/YurOTS/ots/yurots.log`.

### Code Auditor
- [Auditor][2026-07-03] Alcance: C++ (`source/`) + Lua/XML (`data/`) + scripts infra. Focos: autoridad server-side, sockets/memoria (estabilidad), exploits, deuda técnica. Formato: hallazgo · riesgo · causa probable · opciones.

### Web / Rankings & Status
- [Web][2026-07-03] Web en `web/` (Python), lanzada con `scripts/web.sh` (local `:8080`) / `web-public.sh` (cloudflared). Estado en `web/state/*.json` (ignorado). No exponer data sagrada de jugadores en rankings.

### Feature: scroll escribible por jugadores (persistente, público) — IMPLEMENTADA (falta build+QA)
- [Arquitecto][2026-07-03] **Decisión final (cambió respecto del plan inicial).** Pedido: scroll 1949 en 129,53,7 donde un jugador escribe en vivo, se guarda y lo leen todos. Se convocó a `/engine`+`/gameplay`+`/datos`+`/mundo` en paralelo. **Se DESCARTÓ la ruta "casa"** (veredicto de `/mundo`): 129,53,7 es zona depot pública; hacerla casa la vuelve intransitable ("You are not invited" sin owner), y `houseitems.xml` solo serializa ítems moveables → o no persiste (no-moveable) o **DUPLICA el scroll** en cada reboot (el .otbm recrea el original en blanco + LoadHouseItems añade el escrito), y contamina un archivo sagrado. Elegido: **motor + archivo custom `scrolltexts.xml`**, plegado en el módulo `readables` (ya compilado, sin nuevo .cpp/Makefile/define).
- [Engine][2026-07-03] **Implementación (5 archivos, server-side, sin tocar cliente):**
  1. `source/protocol76.cpp` `parseTextWindow` (~1450): sacado "Write not working yet."; ahora bajo `gameLock` (patrón parseLookAt; `parsePacket` NO se despacha con lock, sin deadlock), cap 255, sanitiza control chars salvo `\n`, guard `!isRemoved`, `setText(clean)` + `Readables::SaveScrollText(pos)`, balancea refcount + `else` para no filtrar ref stale. `#include "readables.h"` agregado.
  2. `source/readables.h`: +`LoadScrollTexts` / +`SaveScrollText`; +`#include <string>`.
  3. `source/readables.cpp`: implementadas ambas (load al boot → `setText` en top item del tile; save = upsert por posición en `scrolltexts.xml`). Newlines guardados como `\n` literal (evita la normalización de atributos XML). +`#include <sstream>`.
  4. `source/otserv.cpp` (~782): llama `Readables::LoadScrollTexts` tras readables (no-fatal si falta el archivo).
  5. `data/scrolltexts.xml`: seed vacío. Key = posición del tile; `item->pos` es confiable (lo setea el loader OTBM, `iomapotbm.cpp:233`).
- [Engine][2026-07-03] **No hizo falta tocar Lua:** `rwitems.lua` ya abre el 1949 escribible (`doShowTextWindow(uid,100,1)`), incluso por un bug benigno (`rw and 1` siempre truthy en Lua). Tampoco hizo falta broadcast: el texto se ve al ABRIR la ventana, no en el tile.
- [Datos][2026-07-03][PENDIENTE] **Verificar en `items.otb` que el id 1949 tenga `readOnlyId == 0`.** Si no es 0, `Item::setText` (`item.cpp:855`) muta el ítem a su variante read-only tras la 1ª escritura → dejaría de ser reescribible y el hook Lua por itemid no volvería a disparar. Requisito para "cualquiera reescribe". No inspeccionable desde XML (binario) — usar editor de items.
- [Infra/QA][2026-07-03][PENDIENTE] **Falta compilar + smoke test.** No se puede compilar en la máquina Windows (necesita el container i386): `./run.sh` → `cd /app/YurOTS/ots/source && make clean && make`. QA: usar scroll en 129,53,7 → escribir → otro pj lo lee igual → reiniciar OT → el texto sigue. Ojo deploy: `scrolltexts.xml` es contenido runtime (como houseitems) — evaluar si va en `.gitignore` para no chocar en deploy al VPS.

### Feature: GENERALIZADA a todos los ítems escribibles (cartas/scrolls/papel/labels/libros en blanco)
- [Engine][2026-07-03] **Default en `Actions::UseItem` (`actions.cpp:274`, fallthrough antes del `sendCancel`).** Si ningún action script consumió el ítem y no es container, y el ítem tiene flag RW: `int rw = item->getRWInfo(); if(rw & (CAN_BE_READ|CAN_BE_WRITTEN)) { canWrite = rw & CAN_BE_WRITTEN; player->sendTextWindow(item, canWrite?100:0, canWrite); return true; }`. Ya está bajo `gameLock` (tomado en `Game::playerUseItem`, game.cpp:4968). Así CUALQUIER ítem readable/writeable abre ventana al usarlo, sin listarlo por itemid. Antes NO había default (Lua ni C++): solo abrían los ids en actions.xml.
- [Engine][2026-07-03] **Exclusión de texto predefinido = por flag del `.otb`.** WRITEABLE → editable; READABLE-only (libros/tomes de lore, mapas, written parchment 1969, stamped letter 2598) → solo lectura. `readOnlyId` (item.cpp:855) hace write-once automático para cartas clásicas (letter 2597→stamped 2598, paper→written parchment). No hace falta chequear readOnlyId explícito: el id post-mutación ya trae sus flags.
- [Datos][2026-07-03][CAVEAT] **El lore de libros es por-INSTANCIA** (`text` del ejemplar), no siempre por-tipo. Si el server tiene libros de lore sobre un id de grupo WRITEABLE con texto horneado en el mapa, el default permitiría sobrescribirlos. En 7.6 clásico los libros de lore son READABLE-only (cubiertos), pero conviene spot-check en items.otb de los ids de "book/tome" usados con lore en el mapa. Política alternativa si aparece: gate por "text vacío" o usar readOnlyId.
- [Gameplay][2026-07-03] **actions.xml depurado:** se quitaron los registros genéricos de `rwitems.lua` (1947-1952, 1955-1986, 2597-2599) → ahora caen al default C++ (que además CORRIGE el bug de `rwitems.lua:44` `rw and 1/2`, que en Lua abría TODO como escribible ignorando el flag). Se conservan: `1953` (training parchment, lógica de claim) y `1954/2345` (premium_scroll.lua). `rwitems.lua` queda intacto (sigue sirviendo al 1953).
- [Engine][2026-07-03] **Persistencia doble, ambas cubiertas.** `parseTextWindow` discrimina por `readItem->pos.x != 0xFFFF` (sentinel canónico del engine: container.cpp:56, player.cpp:794,1580): ítems de PISO → `scrolltexts.xml`; ítems en INVENTARIO/depot/container → persisten solos vía savePlayer (`ioplayerxml.cpp:722,873,893` usan `Item::serialize`, que guarda `text`). Verificado el conflicto entre informes: el save del jugador SÍ serializa `text`.

### Pendientes / Próximos pasos
- [Estado][2026-07-03] **Commitear el scaffolding del equipo** (`CLAUDE.md`, `AGENTS.md`, `Contexto/`, `.claude/`) en `main` — requiere OK del usuario (ningún agente pushea solo). Sugerido: `chore: scaffolding del equipo de agentes del server`.
- [Estado][2026-07-03] **Incidente abierto:** root cause de cuelgues jul 2026. Esperar próximo cuelgue con `YUROTS_SOCKET_DEBUG=1`, capturar evidencia (`LEERCODEX.md` §8) antes del restart, y **desactivar el debug tras el fix**.

--- Sesión cerrada: 2026-07-03 16:22 ---

--- Sesión cerrada: 2026-07-03 17:37 ---

--- Sesión cerrada: 2026-07-03 17:55 ---

--- Sesión cerrada: 2026-07-03 18:30 ---

--- Sesión cerrada: 2026-07-03 18:44 ---

--- Sesión cerrada: 2026-07-03 18:56 ---

--- Sesión cerrada: 2026-07-03 19:07 ---

--- Sesión cerrada: 2026-07-03 19:16 ---
