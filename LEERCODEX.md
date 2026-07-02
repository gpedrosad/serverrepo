# LEERCODEX — Guía para agentes IA (Codex, Cursor, etc.)

> **Leer este archivo primero** si entrás al repo para diagnosticar caídas, cuelgues o problemas del OT en producción.
>
> Última actualización: jul 2026. Incidente activo: **cuelgues recurrentes** en retro76.cl (investigación con `YUROTS_SOCKET_DEBUG=1`).

---

## 1. Qué es este proyecto (30 segundos)

| Item | Valor |
|------|--------|
| Juego | **Retro76** — OTServ Tibia 7.6 (motor YurOTS) |
| Repo | `https://github.com/gpedrosad/serverrepo.git` — rama `main` |
| Local (dev) | `~/Desktop/yurots-principal/` — Docker, `127.0.0.1:7171` |
| Producción | VPS `64.176.20.238` — dominio **retro76.cl** — puerto **7171** |
| Data de jugadores | **Solo en el VPS** — nunca en GitHub |

**Regla de oro:** la data runtime (`accounts/`, `players/` reales, `houseitems.xml`) es sagrada. Ver [scripts/README-DEPLOY-VPS.md](scripts/README-DEPLOY-VPS.md) antes de cualquier `git` en el VPS.

---

## 2. Cómo acceder

### SSH al VPS (producción)

```bash
ssh root@64.176.20.238
cd ~/yurots-principal
```

Requiere clave SSH configurada en el entorno del agente. Sin SSH solo podés leer código local y documentación.

### Docker local (Mac)

```bash
cd ~/Desktop/yurots-principal
docker compose up -d yurots          # local (docker-compose.yml)
docker compose -f docker-compose.prod.yml up -d yurots   # igual que prod
```

### Cliente de prueba

```bash
./scripts/play-yurots-client.sh   # conecta a 127.0.0.1:7171
```

---

## 3. Tipos de fallo — no confundir

| Síntoma | Tipo | Container Docker | `ot-probe` | Acción típica |
|---------|------|------------------|------------|---------------|
| Nadie entra, web “offline” | **Cuelgue** | `Up (healthy)` | **FAIL timeout**, 0 bytes | Restart OT; capturar logs antes |
| Kicks masivos | Socket / timeout | `Up` | Puede OK o FAIL | Ver `rcv_ms=5000` en logs |
| Container reinició solo | **Crash** | `RestartCount` sube | FAIL luego OK | Ver `yurots.log`, cores en `/cores` |
| `Could not load houses` | Mapa/casas | Crash al boot | FAIL | `sync-houses-with-map.py --dry-run` |

El caso **más frecuente en jul 2026** es **cuelgue**: el proceso vive, el puerto acepta TCP, pero el protocolo del juego no responde.

---

## 4. Mapa de documentación (leer según el problema)

| Archivo | Cuándo leerlo |
|---------|----------------|
| **[LEERCODEX.md](LEERCODEX.md)** (este) | Entrada rápida para IA |
| [docs/PREVENT_OT_HANGS.md](docs/PREVENT_OT_HANGS.md) | Cuelgues, watchdog, recuperación |
| [docs/SOCKET_DEBUG_LOGGING.md](docs/SOCKET_DEBUG_LOGGING.md) | Logs `[socket]`, `YUROTS_SOCKET_DEBUG`, incidente jul 2026 |
| [docs/FIX_OT_STABILITY_KICKS_AND_HANG.md](docs/FIX_OT_STABILITY_KICKS_AND_HANG.md) | Fixes históricos de sockets (código) |
| [docs/CRASH_DIAGNOSTICS.md](docs/CRASH_DIAGNOSTICS.md) | Core dumps, `crash-*.log`, `snapshot-*.txt` |
| [scripts/README-DEPLOY-VPS.md](scripts/README-DEPLOY-VPS.md) | Deploy seguro, backups, comandos prohibidos |
| [docs/PROYECTO.md](docs/PROYECTO.md) | Arquitectura Mac / GitHub / VPS |
| [docs/CAMBIAR-MAPA.md](docs/CAMBIAR-MAPA.md) | Cambiar `.otbm`, casas, spawns |

---

## 5. Scripts de diagnóstico (usar en este orden)

Todos viven en `scripts/`. En el VPS: `cd ~/yurots-principal` primero.

### 5.1 Probe — ¿responde el juego?

```bash
python3 scripts/ot-probe.py 127.0.0.1 7171
python3 scripts/ot-probe.py 127.0.0.1 7171 --quiet   # exit 0/1 para scripts
```

- **OK** ~2–10 ms, `bytes>0`, `players=N` → servidor sano.
- **FAIL** ~8000 ms, `bytes=0`, `TimeoutError` → **cuelgue** clásico.

### 5.2 Diagnóstico completo (snapshot)

```bash
./scripts/ot-diagnostics.sh
./scripts/ot-diagnostics.sh --append   # escribe en /var/log/retro76/diagnostics.log
```

Incluye: Docker, últimos logs, sockets en 7171, CLOSE-WAIT, probe, watchdog, `yurots.log`, validación mapa/casas.

### 5.3 Healthcheck (bash, protocolo info)

```bash
bash scripts/healthcheck-ot.sh 127.0.0.1 7171
```

Usado por deploy y watchdog tras restart.

### 5.4 Watchdog (auto-recuperación)

- Script: `scripts/ot-watchdog.sh`
- Cron cada **2 min** en VPS
- **2 fallos seguidos** del probe → `docker compose restart -t 45 yurots`
- Logs:
  - `/var/log/retro76/watchdog.log` (si corrió `install-ot-observability.sh`)
  - `/var/log/ot-watchdog.log` (cron legado en algunos VPS)

```bash
tail -30 /var/log/retro76/watchdog.log
tail -30 /var/log/ot-watchdog.log
crontab -l | grep ot-watchdog
```

### 5.5 Instalar / refrescar observabilidad (VPS, una vez)

```bash
./scripts/install-ot-observability.sh
```

---

## 6. Dónde están los logs

| Log | Ruta (VPS) | Contenido |
|-----|------------|-----------|
| **OT persistente** | `~/yurots-principal/server/YurOTS/ots/yurots.log` | Todo stdout/stderr con timestamp UTC |
| Docker | `docker logs yurots` | Mismo stream, puede rotar |
| Diagnóstico periódico | `/var/log/retro76/diagnostics.log` | Snapshots cada 5 min |
| Watchdog | `/var/log/retro76/watchdog.log` o `/var/log/ot-watchdog.log` | Reinicios automáticos |
| Web | `/var/log/retro76/web.log` | Registro/rankings |
| Crash handler | `server/YurOTS/ots/data/crash-*.log` | Stack trace si SIGSEGV etc. |
| Snapshot players | `server/YurOTS/ots/data/snapshot-*.txt` | Quién estaba online al crash |
| Core dumps | `~/yurots-principal/cores/` | Binarios core para gdb |

### Greps útiles (cuelgue / sockets)

```bash
# Desconexiones con detalle (siempre activo)
grep 'Player recv disconnect' server/YurOTS/ots/yurots.log | tail -40

# ¿Timeout de handshake residual en juego? (BUG)
grep 'rcv_ms=5000' server/YurOTS/ots/yurots.log | tail -20

# Debug verbose (ACTIVO en prod jul 2026)
grep '\[socket\]' server/YurOTS/ots/yurots.log | tail -50
docker logs yurots 2>&1 | grep '\[socket\]' | tail -50

# Listen roto
grep 'Listen select failed' server/YurOTS/ots/yurots.log | tail -10

# Sockets colgados
ss -tan | grep 7171 | head -30
ss -tan state close-wait | grep 7171
```

---

## 7. Estado actual de producción (jul 2026)

| Config | Valor |
|--------|--------|
| Mapa desplegado | **Mapa once** (`test.otbm`) — commit `368fb5f` |
| Templo principal | **130, 53, 6** — commit `174d9c7` |
| Templo rook | `85, 211, 7` (`players/0.xml`) |
| NPC Tonka | `140, 50, 7` |
| Socket debug | **`YUROTS_SOCKET_DEBUG=1`** — commit `ec9b0dd` en `docker-compose.prod.yml` |
| Verificar debug | `docker exec yurots printenv YUROTS_SOCKET_DEBUG` → `1` |

**Desactivar debug** cuando termine la investigación: quitar `environment` en `docker-compose.prod.yml`, push, `docker compose -f docker-compose.prod.yml up -d yurots`. Ver [docs/SOCKET_DEBUG_LOGGING.md](docs/SOCKET_DEBUG_LOGGING.md).

---

## 8. Playbook: el servidor “se cayó” (cuelgue)

Ejecutar **en el VPS**, **antes** de reiniciar si querés evidencia para root cause:

```bash
ssh root@64.176.20.238
cd ~/yurots-principal

# 1. Confirmar cuelgue
python3 scripts/ot-probe.py 127.0.0.1 7171

# 2. Snapshot completo (guardar salida)
./scripts/ot-diagnostics.sh | tee /tmp/ot-hang-$(date +%Y%m%d-%H%M%S).txt

# 3. Últimas líneas relevantes
tail -100 server/YurOTS/ots/yurots.log
docker logs yurots --tail 50
tail -20 /var/log/ot-watchdog.log 2>/dev/null || tail -20 /var/log/retro76/watchdog.log

# 4. Recuperar
docker compose -f docker-compose.prod.yml restart -t 45 yurots

# 5. Verificar
sleep 8
python3 scripts/ot-probe.py 127.0.0.1 7171
docker logs yurots --tail 5
```

**Interpretación rápida:**

| En logs | Significa |
|---------|-----------|
| Loot/save normal → luego silencio + probe FAIL | Cuelgue de event loop |
| Ráfaga `Player recv disconnect` | Tormenta de desconexiones previa al cuelgue |
| `rcv_ms=5000` en jugador en juego | Timeout handshake no limpiado — bug en `otserv.cpp` / `networkmessage.cpp` |
| `peer closed` / `errno=110` | Clientes timeout esperando respuesta del servidor colgado |
| `protId=0xffff` desde `172.18.0.1` | Healthcheck Docker — **normal** |

El watchdog debería reiniciar solo en ~4 min (2 fallos × cron 2 min). Si el usuario pide arreglo inmediato, restart manual está bien.

---

## 9. Playbook: crash real (SIGSEGV, container reinició)

```bash
cd ~/yurots-principal

docker inspect yurots --format 'restarts={{.RestartCount}} started={{.State.StartedAt}}'
docker logs yurots 2>&1 | grep -E 'Segmentation|SIGSEGV|Could not load' | tail -20

ls -lt server/YurOTS/ots/data/crash-*.log 2>/dev/null | head -3
ls -lt server/YurOTS/ots/data/snapshot-*.txt 2>/dev/null | head -3
ls -lt cores/ 2>/dev/null | head -5

# Analizar core (si existe)
./scripts/extract-core.sh
```

Ver [docs/CRASH_DIAGNOSTICS.md](docs/CRASH_DIAGNOSTICS.md).

---

## 10. Playbook: deploy / cambios en VPS

**Nunca** en el VPS: `git stash -u`, `git clean`, `git pull` sin backup.

```bash
cd ~/yurots-principal
DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
```

Desde Mac (sin entrar al VPS):

```bash
ssh root@64.176.20.238 'cd ~/yurots-principal && git fetch origin main && DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh'
```

Backups automáticos: `~/ot-backups/pre-deploy-FECHA/`

Cambio de mapa: [docs/CAMBIAR-MAPA.md](docs/CAMBIAR-MAPA.md)

---

## 11. Archivos de código relevantes (debug sockets)

| Archivo | Rol |
|---------|-----|
| `server/YurOTS/ots/source/socket_debug.cpp` | `YUROTS_SOCKET_DEBUG`, logs `[socket]` |
| `server/YurOTS/ots/source/networkmessage.cpp` | Timeouts recv, errno |
| `server/YurOTS/ots/source/otserv.cpp` | Accept, login, listen |
| `server/YurOTS/ots/source/protocol76.cpp` | ReceiveLoop, disconnect |
| `docker-compose.prod.yml` | `YUROTS_SOCKET_DEBUG=1`, healthcheck 7171 |
| `scripts/docker-entrypoint.sh` | `yurots.log` con timestamps |
| `scripts/ot-watchdog.sh` | Auto-restart por probe |

---

## 12. Data paths importantes

```
server/YurOTS/ots/
├── config.lua              # ip VPS: 64.176.20.238 (no commitear IP local)
├── data/
│   ├── world/test.otbm     # Mapa (en git)
│   ├── world/npc.xml       # Posiciones NPC (en git)
│   ├── houses.xml          # Casas (en git)
│   ├── accounts/*.xml      # SOLO VPS — sagrado
│   ├── players/*.xml       # SOLO VPS — sagrado (excepto 0–4.xml plantillas)
│   └── houseitems.xml      # SOLO VPS
└── yurots.log              # Log persistente OT
```

---

## 13. Comandos de una línea (cheat sheet)

```bash
# ¿Vivo?
python3 ~/yurots-principal/scripts/ot-probe.py 127.0.0.1 7171

# Diagnóstico todo-en-uno
~/yurots-principal/scripts/ot-diagnostics.sh

# Reiniciar OT (prod)
docker compose -f ~/yurots-principal/docker-compose.prod.yml restart -t 45 yurots

# Seguir logs en vivo
tail -f ~/yurots-principal/server/YurOTS/ots/yurots.log

# Cuentas/personajes en VPS
ls -1 ~/yurots-principal/server/YurOTS/ots/data/accounts/*.xml | wc -l
ls -1 ~/yurots-principal/server/YurOTS/ots/data/players/*.xml | wc -l

# Validar mapa
python3 ~/yurots-principal/scripts/sync-houses-with-map.py --dry-run
```

---

## 14. Qué NO hacer (agentes IA)

1. **No** `git stash -u` / `git clean` en el VPS.
2. **No** copiar `players/` desde Mac al VPS.
3. **No** commitear `accounts/` ni players reales.
4. **No** asumir que `docker ps = healthy` implica que el juego responde — siempre `ot-probe`.
5. **No** desactivar el watchdog sin avisar.
6. **No** hacer deploy a VPS si el usuario solo pidió debug local (preguntar).

---

## 15. Flujo de decisión (diagrama)

```
¿Jugadores no pueden entrar?
        │
        ├─ ot-probe OK ──► Problema cliente/red/DNS — no es el OT
        │
        └─ ot-probe FAIL
                │
                ├─ docker ps: Exit / Restarting ──► Crash → §9
                │
                └─ docker ps: Up
                        │
                        ├─ bytes=0 timeout ──► Cuelgue → §8, capturar logs, restart
                        │
                        └─ Connection refused ──► OT caído o arrancando → logs boot
```

---

## 16. Commits de referencia (jul 2026)

| Commit | Qué |
|--------|-----|
| `368fb5f` | Mapa once + Tonka + templo inicial |
| `174d9c7` | Templo corregido 130,53,6 |
| `ec9b0dd` | `YUROTS_SOCKET_DEBUG=1` en prod |
| `468447f` | Docs cuelgues + socket debug |
| `pre-ot-send-blocking-fix` (tag) | Estado **antes** del fix send/gameLock |
| (commit fix) | `game.cpp` + `networkmessage.cpp` + `protocol76.cpp` |

### Rollback del fix send bloqueante

```bash
cd ~/yurots-principal
git fetch --tags
DEPLOY_I_READ_README=yes ./scripts/rollback-ot-send-blocking-fix.sh
```

Ver [docs/OT_HANG_ROOT_CAUSE_SEND_BLOCKING.md](docs/OT_HANG_ROOT_CAUSE_SEND_BLOCKING.md).

---

## 17. Siguiente paso para root cause

1. Esperar próximo cuelgue con debug activo.
2. Ejecutar bloque §8 **antes** del restart.
3. Buscar en evidencia: `rcv_ms=5000`, ráfaga de disconnects, CLOSE-WAIT alto, último log antes del silencio.
4. Documentar hallazgo en `docs/FIX_OT_STABILITY_KICKS_AND_HANG.md`.
5. Desactivar `YUROTS_SOCKET_DEBUG` tras el fix.

---

*Si este archivo queda desactualizado, actualizarlo junto con cualquier cambio en observabilidad, deploy o incidentes de producción.*
