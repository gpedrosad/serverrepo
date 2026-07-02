# Cómo prevenir cuelgues del OT y tener logs útiles

Guía operativa para **retro76.cl** (VPS). Complementa:
- [FIX_OT_STABILITY_KICKS_AND_HANG.md](FIX_OT_STABILITY_KICKS_AND_HANG.md) — causas técnicas ya corregidas en código
- [SOCKET_DEBUG_LOGGING.md](SOCKET_DEBUG_LOGGING.md) — logs de red detallados (**debug activo en prod desde jul 2026**)

---

## Incidente jul 2026 — cuelgues recurrentes (investigación abierta)

**Contexto:** tras deploy del mapa once + templo `130,53,6` (commits `368fb5f`, `174d9c7`), el servidor colgó **varias veces en pocas horas** el 2 jul 2026.

| Qué ven los jugadores | Qué muestra el servidor |
|----------------------|-------------------------|
| Cliente deja de responder, desconexión | `docker ps` → `Up (healthy)` |
| No pueden reconectar | `ot-probe` → **timeout 8 s, 0 bytes** |
| A veces muchos kickeados a la vez | Últimas líneas: `Player recv disconnect: ... (peer closed)` |

**No es** crash con core dump ni reinicio del container. Es **cuelgue del event loop**: el proceso sigue, a veces hasta procesa loot/save, y luego deja de atender el protocolo en 7171.

**Acciones tomadas:**

1. Restarts manuales cuando el probe falló (antes de que el watchdog complete 2 fallos).
2. Activado `YUROTS_SOCKET_DEBUG=1` en producción (`ec9b0dd`) — ver [SOCKET_DEBUG_LOGGING.md](SOCKET_DEBUG_LOGGING.md).
3. Watchdog en cron cada 2 min (`/var/log/ot-watchdog.log` o `/var/log/retro76/watchdog.log` según instalación).

**Cuando vuelva a pasar** — capturar evidencia **antes** de reiniciar:

```bash
ssh root@64.176.20.238
cd ~/yurots-principal
python3 scripts/ot-probe.py 127.0.0.1 7171
./scripts/ot-diagnostics.sh | tee /tmp/ot-hang-$(date +%Y%m%d-%H%M%S).txt
tail -100 server/YurOTS/ots/yurots.log
docker logs yurots --tail 50
```

**Recuperación inmediata:**

```bash
docker compose -f docker-compose.prod.yml restart -t 45 yurots
python3 scripts/ot-probe.py 127.0.0.1 7171
```

---

## Qué “caída” es en la práctica

| Síntoma | Qué pasa | Quién lo detecta |
|---------|----------|------------------|
| Nadie entra / web “offline” | Proceso vivo, **7171 no responde** al protocolo info | `ot-probe`, jugadores |
| Kicks masivos | `Player recv disconnect` en logs | Jugadores + `docker logs` |
| Crash real | Container reinicia solo (`restart: unless-stopped`) | Docker, core en `/cores` |

El caso más frecuente era **cuelgue**: el juego seguía (loot, saves) pero el puerto dejaba de aceptar conexiones.

---

## Prevención en código (ya desplegado)

Mantener el servidor en un commit que incluya al menos `4d78ee7`:

1. **Sockets de juego** — sin timeout de handshake en sesión activa (`setSocketGameRecvBlocking`).
2. **Listen `EINTR`** — no cerrar el puerto 7171 si `select()` es interrumpido.
3. **Mana** — valores y pulso documentados en [REGEN_FOOD.md](REGEN_FOOD.md).

**No hacer en el VPS:** `git stash -u`, `git clean`, `git pull` a mano sin backup (ver [README-DEPLOY-VPS.md](../scripts/README-DEPLOY-VPS.md)).

---

## Capa 1 — Auto-recuperación (watchdog)

El watchdog prueba el protocolo **info** (no solo TCP) cada **2 minutos**. Si falla **2 veces seguidas**, reinicia el container con gracia (`stop -t 45`).

### Instalar o actualizar (en el VPS)

```bash
cd ~/yurots-principal
./scripts/install-ot-observability.sh
```

Eso configura:
- Cron watchdog → `/var/log/retro76/watchdog.log`
- Cron diagnóstico cada 5 min → `/var/log/retro76/diagnostics.log`
- Web log → `/var/log/retro76/web.log`

### Ver si el watchdog está activo

```bash
crontab -l | grep -E 'ot-watchdog|retro76-ot-diagnostics'
tail -f /var/log/retro76/watchdog.log
```

---

## Capa 2 — Logs persistentes

### A) Salida del servidor OT (stdout)

Con `docker-compose.prod.yml` + `docker-entrypoint.sh`, cada línea del OT se guarda con timestamp en:

```
~/yurots-principal/server/YurOTS/ots/yurots.log
```

(persiste en el volumen del host; sobrevive reinicios del container)

```bash
tail -f ~/yurots-principal/server/YurOTS/ots/yurots.log
grep -E 'Player recv disconnect|Listen select failed' server/YurOTS/ots/yurots.log | tail -30
```

### B) Docker logs (útil pero rotan)

```bash
docker logs -f yurots 2>&1 | grep -E '\[socket\]|Player recv disconnect|Listen select'
```

### C) Diagnóstico periódico

```bash
tail -f /var/log/retro76/diagnostics.log
```

Snapshot manual:

```bash
cd ~/yurots-principal && ./scripts/ot-diagnostics.sh
```

### D) Logs de red verbose — **ACTIVO en prod (jul 2026)**

En `docker-compose.prod.yml`, bajo `yurots` (commit `ec9b0dd`):

```yaml
environment:
  - YUROTS_SOCKET_DEBUG=1
```

Genera líneas `[socket]` en login y cambios de modo de socket. Ver [SOCKET_DEBUG_LOGGING.md](SOCKET_DEBUG_LOGGING.md) para interpretación y cómo desactivar.

**Cuando termine la investigación:** quitar el bloque `environment`, push y `docker compose -f docker-compose.prod.yml up -d yurots`.

---

## Capa 3 — Qué mirar cuando “se cayó”

Orden recomendado:

```bash
# 1. ¿Responde ahora?
python3 ~/yurots-principal/scripts/ot-probe.py 127.0.0.1 7171

# 2. ¿Watchdog reinició?
tail -30 /var/log/retro76/watchdog.log

# 3. ¿Patrón de socket o listen?
grep -E 'Player recv disconnect|Listen select failed' \
  ~/yurots-principal/server/YurOTS/ots/yurots.log | tail -40

# 4. ¿Sockets colgados?
ss -tan | grep 7171 | head -20

# 5. Snapshot completo
~/yurots-principal/scripts/ot-diagnostics.sh
```

### Interpretación rápida

| Log | Significado |
|-----|-------------|
| `Listen select failed` | El puerto se cerró (bug viejo o error real de red) |
| `rcv_ms=5000` en disconnect | Timeout de handshake aún activo en juego → falta deploy/fix |
| `peer closed connection` | Cliente o red cerró TCP (normal al salir) |
| Probe OK pero jugadores kickeados | Problema de sesión, no de listen |
| Probe FAIL + loot en logs viejos | Cuelgue clásico (watchdog debería reiniciar) |

---

## Capa 4 — Deploy seguro (no reintroducir bugs)

```bash
cd ~/yurots-principal
# Verificar IP pública tras pull (el repo trae 127.0.0.1 / retro76.cl)
grep '^ip ' server/YurOTS/ots/config.lua   # debe ser 64.176.20.238

DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
```

Post-deploy:

```bash
python3 scripts/ot-probe.py 127.0.0.1 7171
docker logs yurots --tail 5   # "Retro76 Server Running..."
```

---

## Capa 5 — Prevención operativa

1. **No sondar 7171 desde la web** — ya desactivado (`OT_STATUS_SOURCE=docker`).
2. **Deploy en horario bajo** si es un cambio grande de binario.
3. **Backups automáticos** del deploy script en `~/ot-backups/pre-deploy-*`.
4. **Alertas manuales** — revisar `watchdog.log` 1× al día o usar un monitor externo que haga HTTP a la web + probe al OT desde fuera.

### Monitor externo mínimo (opcional)

Cada 5 min desde tu Mac o un cron:

```bash
curl -sf https://retro76.cl/api/data >/dev/null && \
ssh root@64.176.20.238 'python3 ~/yurots-principal/scripts/ot-probe.py 127.0.0.1 7171 --quiet'
```

Si falla → mirar `watchdog.log` y `yurots.log`.

---

## Resumen en una línea

**Código actual + watchdog + `yurots.log` + `ot-diagnostics` cada 5 min** = prevención y evidencia para la próxima vez que pase.
