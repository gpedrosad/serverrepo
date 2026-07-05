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
2. **NUNCA** commitear data runtime de jugadores: `accounts/`, `players/` (excepto `0-4.xml`), `online.xml`, `queue.xml`, `houseitems.xml`, `web/state/*.json`.
3. **NUNCA** commitear binarios ni artefactos: `source/yurots`, `*.o`, `*.bak`, `*.patch`, `core.*`, `*.log` rotados.
4. **NUNCA** deployar al VPS si el usuario solo pidió debug local. **Siempre preguntar**.
5. **SIEMPRE** usar `DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh` para deployar (nada de `docker cp` artesanal).
6. **SIEMPRE** verificar el estado del servidor con `python3 scripts/ot-probe.py 127.0.0.1 7171` después de tocar el OT (local o VPS).
7. **SIEMPRE** correr `bash scripts/test-local-smoke.sh` antes de cambios delicados (código C++, scripts Lua, OTBM, configs que afectan boot).
8. **SIEMPRE** consultar `docs/INDEX.md` y el doc del subsistema antes de tocar ese subsistema.
9. **SIEMPRE** leer el doc de deploy completo al menos una vez antes del primer deploy al VPS.
10. Si algo no se entiende del flujo o del incidente, **preguntar antes de actuar**.

---

## 3. Cómo encontrar el doc correcto

El proyecto usa un sistema *self-learning*: cada subsistema tiene su propio doc. Antes de tocar algo, **leer el doc que corresponde**.

| Subsistema | Doc |
|------------|-----|
| Gemas / minería / crafting | `docs/gameplay/GEMS.md` |
| PvP, frag list, balance de combate | `docs/PVP_SYSTEM.md` |
| Trade, items, transacciones | `docs/TRADE_SYSTEM.md` |
| Cliente retro76 / updater | `docs/CLIENT.md` y `docs/CLIENT_UPDATER_RETRO76.md` |
| Sockets, cuelgues, kicks | `docs/systems/SOCKET_DEBUG_LOGGING.md` y `docs/systems/PREVENT_OT_HANGS.md` |
| Crash / core dumps | `docs/systems/CRASH_DIAGNOSTICS.md` |
| RME / edición de mapa | `docs/RME_SETUP.md` |
| Cambios de mapa / OTBM | `docs/CAMBIAR-MAPA.md` |

Si el subsistema no aparece en la tabla, buscar en `docs/INDEX.md` o preguntar.

---

## 4. Workflow de cambio típico

Para un cambio serio (no trivial) seguir este orden, sin saltearse pasos:

1. **Local**: editar en Mac. Levantar con `docker compose -f docker-compose.prod.yml up -d yurots`.
2. **Probar local**: correr `bash scripts/test-local-smoke.sh` y luego `python3 scripts/ot-probe.py 127.0.0.1 7171`.
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
| Smoke tests locales | `bash scripts/test-local-smoke.sh` |

---

## 8. Resumen ejecutivo para agentes con poca atención

- Data de jugadores = sagrada. Si la tocás sin backup, rompiste el server.
- Deploy al VPS = preguntar primero, usar el script, verificar con probe.
- Doc del subsistema = leerlo antes de tocarlo.
- `Up` no significa OK. Probeá.
- Cambios chicos, commits chicos, reportes claros.
- Cuando dudes: **preguntá**.
