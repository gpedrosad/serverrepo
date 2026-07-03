# CLAUDE.md — Contexto Técnico · Servidor YurOTS (Retro76)

## Lectura obligatoria antes de cualquier tarea
1. `/Contexto/MEMORY.md` — aprendizajes acumulados del equipo
2. `AGENTS.md` — roles del equipo y sus restricciones
3. Este archivo — mapa técnico del proyecto
4. `LEERCODEX.md` — guía rápida de incidentes en producción (cuelgues/crashes/deploy)

---

## ¿Qué es este repo?

Es el **repo principal del SERVIDOR** del juego **Retro76** — un **OTServ Tibia 7.6** sobre el motor **YurOTS**. Corre en **Docker** y sirve el mundo autoritativo al que se conecta el cliente oficial (repo aparte `clienteretro`, OTClientV8 7.60).

- **El server es la fuente de verdad.** Simula el mundo, valida input, persiste cuentas/personajes. El cliente solo renderiza y envía input.
- Es un motor **C++** (`server/YurOTS/ots/source/`) + una capa de **scripting Lua/XML** (`server/YurOTS/ots/data/`) + **mundo** `.otbm` + **infra** (Docker/VPS/deploy/watchdog) + **web** (rankings/status).

| Dato | Valor |
|------|-------|
| Juego | Retro76 — OTServ Tibia **7.6** (motor YurOTS) |
| Repo | `https://github.com/gpedrosad/serverrepo.git` — rama `main` |
| Producción | VPS `64.176.20.238` — dominio **retro76.cl** — puerto **7171** |
| Local (dev) | Docker, `127.0.0.1:7171` |
| Persistencia | **XML** (`sourcedata = "XML"`), no SQL |
| Mapa | OTBM (`data/world/test.otbm`) |
| Cliente pareja | `clienteretro` (OTClient 7.60) — contrato de protocolo **7.60** |

---

## ⚠️ Regla de oro del repo: la data de jugadores es SAGRADA

La data **runtime** solo vive en el VPS y **nunca** se commitea ni se pisa en deploy:

```
server/YurOTS/ots/data/
├── accounts/*.xml      # SOLO VPS — sagrado (.gitignore)
├── players/*.xml       # SOLO VPS — sagrado, EXCEPTO plantillas 0-4.xml (sí versionadas)
├── vip/                # SOLO VPS
├── houseitems.xml      # SOLO VPS — items dentro de casas
├── online.xml · queue.xml   # runtime, ignorados
```

**Prohibido en el VPS:** `git stash -u`, `git clean`, `git reset --hard` sin backup, `git pull` a mano.
Un deploy mal hecho **borra cuentas y personajes reales**. El guardrail (`.claude/hooks/guardrail.sh`) bloquea estos comandos.

---

## Estructura del repo

```
serverrepo/
├── Dockerfile · docker-compose.yml · docker-compose.prod.yml
├── run.sh                     # entra al container a compilar
├── README.md · OTINFO · LEERCODEX.md
├── deploy/nginx/              # reverse proxy prod
├── rme-client-760/            # Tibia.dat + Tibia.spr para RME (editor de mapa)
├── rme-extensions/            # creatures.xml y extensiones RME
├── scripts/                   # deploy, watchdog, probe, diagnósticos, web, setup RME
├── web/                       # rankings, status, funnel premium (Python)
├── docs/                      # documentación técnica + docs/features/*
├── backups/                   # backup del mapa original
└── server/YurOTS/ots/         # ===== EL SERVIDOR (bind mount) =====
    ├── config.lua             # puerto 7171, ip, rates, map, sourcedata=XML
    ├── source/                # ===== MOTOR C++ =====
    │   ├── Makefile
    │   ├── game.cpp/.h · map.cpp · player.cpp · creature.cpp · container.cpp
    │   ├── protocol76.cpp · networkmessage.cpp · otserv.cpp   # red/protocolo/sockets
    │   ├── socket_debug.cpp   # YUROTS_SOCKET_DEBUG, logs [socket]
    │   ├── actions.cpp · spells.cpp · movement.cpp            # puentes motor↔script
    │   └── ...
    ├── data/                  # ===== SCRIPTING / CONTENIDO =====
    │   ├── actions/           # actions.xml + lib/ + scripts/*.lua (usar objetos)
    │   ├── spells/            # instant/ + runes/ + lib/ + spells.xml
    │   ├── monster/           # *.xml (monstruos custom incluidos)
    │   ├── npc/               # NPCs (diálogos, tiendas)
    │   ├── items/             # items.otb (binario) + items.xml
    │   ├── houses/ · houses.xml
    │   ├── world/             # test.otbm (mapa) · test-spawn.xml · test-house.xml · npc.xml
    │   ├── players/           # 0-4.xml plantillas (resto SAGRADO)
    │   ├── commands.xml · guilds.xml · readables.xml · trainingareas.xml · pvparenas.xml
    │   └── yurots.log         # log persistente del OT
    └── docs/
```

---

## Flujos críticos

### Arranque / compilación
```
docker compose -f docker-compose.prod.yml up -d --build
  → container compila source/ (make) → binario source/yurots
  → yurots lee config.lua (puerto 7171, map, rates, sourcedata=XML)
  → carga mapa OTBM, spawns, casas, NPCs, scripts (actions/spells)
  → escucha en 7171 (login + game)
```
Recompilar dentro del container: `./run.sh` → `cd /app/YurOTS/ots/source && make clean && make`.

### Conexión y login (contrato con el cliente)
```
Cliente (retro76.cl:7171, proto 7.60) → ProtocolLogin (cuenta XML)
  → selección de personaje → ProtocolGame (mundo)
  → protocol76.cpp parsea input y serializa estado autoritativo del mundo
```

### Incidente activo de producción (jul 2026): CUELGUES
El proceso vive y acepta TCP pero el protocolo del juego no responde. Ver `LEERCODEX.md` §8 y
`docs/PREVENT_OT_HANGS.md`, `docs/SOCKET_DEBUG_LOGGING.md`, `docs/OT_HANG_ROOT_CAUSE_SEND_BLOCKING.md`.
Diagnóstico: `scripts/ot-probe.py`, `scripts/ot-diagnostics.sh`. Watchdog: cron 2 min, restart tras 2 fallos.

---

## Contratos con el cliente (`clienteretro`)

- **Protocolo fijo 7.60.** El parseo de `ProtocolGame` cliente↔server debe coincidir.
- **`stackable` es contrato:** el flag en `items.otb`/`items.xml` (server) debe coincidir con el `.dat` del cliente (`data/things/760`). Si difieren → desync de parseo (`no thing at pos`). Relevante para volver stackable un ítem (ej. comida de `exevo pan`): es cambio **server-side** (items.otb + lógica de merge en `player.cpp`/`container.cpp`), coordinado con el asset del cliente.
- El server **no** debe compensar bugs del cliente inventando estado, ni el cliente simular autoridad. Cambios que cruzan el límite los aprueba `/arquitecto` + `/protocolo`.

---

## Reglas y convenciones

- **Data de jugadores sagrada** (accounts/players reales): nunca commitear ni pisar en deploy.
- **El server es autoritativo:** toda mecánica real (stacking, loot, combate, exhaust, cap) vive acá, no en el cliente.
- **Protocolo fijo 7.60.** No mezclar features/assets de otras versiones.
- **`stackable` = contrato** items.otb ↔ .dat del cliente.
- **No editar el binario compilado** `source/yurots` a mano — se regenera con `make`.
- **Deploy solo por el flujo documentado** (`scripts/deploy-vps.sh`, `DEPLOY_I_READ_README=yes`). Leer `scripts/README-DEPLOY-VPS.md`.
- **Debug de sockets** (`YUROTS_SOCKET_DEBUG=1`) está ACTIVO en prod (jul 2026) — desactivar tras el root cause.
- **Los agentes no commitean ni pushean** — se sugiere al usuario al final.

---

## Cómo correr el server (local)

```bash
docker compose -f docker-compose.prod.yml up -d --build
python3 scripts/ot-probe.py 127.0.0.1 7171     # ¿responde el juego?
./scripts/play-yurots-client.sh                 # cliente de prueba → 127.0.0.1:7171
./scripts/web.sh                                 # rankings/status en http://localhost:8080
```

> Cambios de C++: requieren recompilar (`make`) dentro del container y reiniciar.
> Cambios de data Lua/XML: se releen al reiniciar el OT (no compilan).
> Cambios de mapa: editar con RME (`scripts/open-rme.sh`) → `docs/CAMBIAR-MAPA.md`.
