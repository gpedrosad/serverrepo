# MEMORY.md — Aprendizajes del Equipo · Servidor YurOTS (Retro76)

> Índice de contexto cargado al inicio de cada sesión. Formato de entrada: `- [ROL][FECHA] descripción.`
> Proyecto: OTServ Tibia 7.6 (motor YurOTS) · producción en retro76.cl:7171 · repo `gpedrosad/serverrepo`.

## Aprendizajes del Equipo

### Arquitecto / Tech Lead
- [Arquitecto][2026-07-03] **Equipo de desarrollo del server montado.** Scaffolding creado en `serverrepo`: `CLAUDE.md` (mapa técnico), `AGENTS.md` (roles), `Contexto/MEMORY.md` (este), `.claude/commands/*.md` (11 roles), `.claude/hooks/` (guardrail reforzado + consolidate-memory), `.claude/settings.json`. Roster: `/arquitecto`, `/engine`, `/gameplay`, `/mundo`, `/datos`, `/protocolo`, `/infra`, `/seguridad`, `/qa`, `/auditor`, `/web`. Espejo del equipo del cliente (`clienteretro`) pero adaptado a un servidor OT (motor C++ + scripting + infra).
- [Arquitecto][2026-07-03] **Relación cliente↔server.** `serverrepo` es la fuente de verdad; `clienteretro` (OTClient 7.60) solo renderiza. Dos contratos cruzan el límite y los custodia arquitecto+protocolo: (1) **protocolo 7.60** (parseo ProtocolGame), (2) **`stackable`** (`items.otb` del server ↔ `.dat` del cliente `data/things/760`). Un cambio de stackable es server-side pero requiere tocar el asset del cliente en paralelo.
- [Arquitecto][2026-07-03] **La data de jugadores es sagrada** (`accounts/`, `players/` reales, `vip/`, `houseitems.xml`): solo vive en el VPS, en `.gitignore`, nunca se commitea ni se pisa en deploy. El guardrail bloquea `git commit`/`push`, `git stash -u`, `git clean`, `git reset --hard` y `git add` de esa data.

### Engine / C++ Core
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

### Pendientes / Próximos pasos
- [Estado][2026-07-03] **Commitear el scaffolding del equipo** (`CLAUDE.md`, `AGENTS.md`, `Contexto/`, `.claude/`) en `main` — requiere OK del usuario (ningún agente pushea solo). Sugerido: `chore: scaffolding del equipo de agentes del server`.
- [Estado][2026-07-03] **Incidente abierto:** root cause de cuelgues jul 2026. Esperar próximo cuelgue con `YUROTS_SOCKET_DEBUG=1`, capturar evidencia (`LEERCODEX.md` §8) antes del restart, y **desactivar el debug tras el fix**.

--- Sesión cerrada: 2026-07-03 16:22 ---
