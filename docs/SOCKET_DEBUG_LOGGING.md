# Logs de red OT — guía de diagnóstico

> **Estado (jul 2026):** `YUROTS_SOCKET_DEBUG=1` **activo en producción** (VPS) desde commit `ec9b0dd` para investigar cuelgues recurrentes. Desactivar cuando se identifique la causa raíz (ver § Desactivar).

Relacionado: [PREVENT_OT_HANGS.md](PREVENT_OT_HANGS.md), [FIX_OT_STABILITY_KICKS_AND_HANG.md](FIX_OT_STABILITY_KICKS_AND_HANG.md).

---

## Incidente en curso (jul 2026)

Tras el deploy del **mapa once** (2 jul 2026), el OT en **retro76.cl** volvió a colgarse varias veces el mismo día:

| Hora UTC (aprox.) | Síntoma | Acción |
|-------------------|---------|--------|
| ~18:54 | Probe timeout, jugadores `peer closed` / `errno=110` | Restart manual |
| ~19:07 | Mismo patrón tras loot/save normal | Restart manual |
| ~19:02–19:10 | Watchdog detectó 1 fallo, luego probe OK (ventana de restart) | Auto / manual |

**Patrón:** no es crash del proceso. Docker muestra `Up (healthy)` pero `ot-probe` hace **timeout ~8 s** con **0 bytes**. Los logs se cortan con desconexiones masivas de jugadores; antes suele haber loot y `server save... ok` normales.

**Hipótesis abierta:** cuelgue del event loop (hilos/sockets), posiblemente relacionado con tormenta de desconexiones o bug distinto al timeout de handshake ya corregido. Los logs `[socket]` activados deben mostrar si reaparece `rcv_ms=5000` en sesión de juego o anomalías en `ReceiveLoop`.

**Evidencia a capturar en el próximo cuelgue:**

```bash
# En el VPS, justo cuando falle el probe:
cd ~/yurots-principal
python3 scripts/ot-probe.py 127.0.0.1 7171
./scripts/ot-diagnostics.sh
tail -80 server/YurOTS/ots/yurots.log | grep -E '\[socket\]|Player recv disconnect|Listen select'
tail -20 /var/log/ot-watchdog.log
ss -tan | grep 7171 | head -20
```

Guardar la salida antes de reiniciar manualmente (el watchdog tarda ~4 min en 2 fallos consecutivos con cron cada 2 min).

---

## Qué ha estado pasando (histórico)

| Fase | Síntoma | Causa |
|------|---------|-------|
| 1 | Kicks cada ~5 s, muchos jugadores | `SO_RCVTIMEO` de handshake (5 s) seguía en sesiones de juego |
| 2 | `clearSocketRecvTimeout(s)` después de `s=0` | El timeout nunca se quitaba del socket real |
| 3 | Fix `recvExact` + log básico | Ayudó a ver el motivo, no arregló el timeout |
| 4 | Separar handshake / juego (`87deae2`) | `setSocketGameRecvBlocking` tras el primer paquete |
| 5 | Cuelgue 7171 + watchdog restart | Tormenta de kicks → muchos sockets `CLOSE-WAIT` → probe timeout |

**No era** WiFi del cliente, anti-AFK ni ping kick. Era **lógica de sockets en el servidor**.

Commits clave: `f2c8754`, `da16261`, `87deae2`. Ver `docs/FIX_OT_STABILITY_KICKS_AND_HANG.md`.

---

## Tipos de log

### Siempre (sin configurar nada)

Cada desconexión por fallo de `recv`:

```
Player recv disconnect: ulfhed (recv timeout or would block) sock=12 rcv_ms=5000 nonblock=0 errno=11 (Resource temporarily unavailable)
```

Campos:

| Campo | Qué indica |
|-------|------------|
| `sock` | FD del socket al desconectar |
| `rcv_ms` | `SO_RCVTIMEO` en ms (**5000 = bug de handshake aún activo**) |
| `nonblock` | 1 = socket no bloqueante (inusual en juego) |
| `errno` | Código del sistema al fallar `recv` |

### Verbose (`YUROTS_SOCKET_DEBUG=1`)

Prefijo `[socket]` — login, cambios de modo, reintentos:

```
[socket] accept sock=11 rcv_ms=0 nonblock=0 peer=181.89.225.123
[socket] handshake timeout 5s on sock=11 rcv_ms=5000 nonblock=0
[socket] game recv blocking on sock=11 rcv_ms=0 nonblock=0
[socket] first packet protId=0x20a sock=11 rcv_ms=0 nonblock=0
[socket] game login ok player=ulfhed entering ReceiveLoop sock=11 rcv_ms=0 nonblock=0
[socket] ReceiveLoop start player=ulfhed sock=11 rcv_ms=0 nonblock=0
```

---

## Estado actual en producción

| Item | Valor |
|------|--------|
| Commit que activó debug | `ec9b0dd` |
| Archivo | `docker-compose.prod.yml` → `environment: YUROTS_SOCKET_DEBUG=1` |
| Aplicar cambio | `docker compose -f docker-compose.prod.yml up -d yurots` (recrea container; no recompila) |
| Verificar | `docker exec yurots printenv YUROTS_SOCKET_DEBUG` → `1` |
| Log en disco | `~/yurots-principal/server/YurOTS/ots/yurots.log` |
| Log Docker | `docker logs yurots 2>&1 \| grep '\[socket\]'` |

Ejemplo de login **correcto** (sin timeout residual en juego):

```
[socket] game recv blocking on sock=13 rcv_ms=0 nonblock=0
[socket] game login ok player=Pallo entering ReceiveLoop sock=13 rcv_ms=0 nonblock=0
[socket] ReceiveLoop start player=Pallo sock=13 rcv_ms=0 nonblock=0
```

El healthcheck de Docker envía `protId=0xffff` (info) desde `172.18.0.1` — es normal, no es un jugador.

---

## Cómo activar / desactivar

### Activar (local o VPS)

```yaml
# docker-compose.yml (local) o docker-compose.prod.yml (VPS) — servicio yurots:
environment:
  - YUROTS_SOCKET_DEBUG=1
```

```bash
docker compose -f docker-compose.prod.yml up -d yurots   # VPS
docker compose up -d yurots                               # local
docker logs -f yurots 2>&1 | grep -E '\[socket\]|Player recv disconnect'
```

La variable se lee **al arrancar** el proceso (caché estática en `socket_debug.cpp`). Cambiarla exige **recrear/reiniciar** el container.

### Desactivar (cuando termine la investigación)

1. Comentar o borrar el bloque `environment` en `docker-compose.prod.yml`.
2. `git commit` + `git push` + en VPS: `git pull && docker compose -f docker-compose.prod.yml up -d yurots`.
3. Confirmar: `docker exec yurots printenv YUROTS_SOCKET_DEBUG` debe fallar o estar vacío.

En producción estable conviene dejarlo **apagado**; las líneas `Player recv disconnect` ya incluyen `rcv_ms` y `errno` sin verbose.

---

## Comandos útiles

```bash
# Solo desconexiones (producción normal)
docker logs yurots 2>&1 | grep 'Player recv disconnect'

# ¿Sigue el timeout de 5s en juego?
docker logs yurots 2>&1 | grep 'rcv_ms=5000'

# Login + sockets (debug)
docker logs yurots 2>&1 | grep '\[socket\]'

# Probe manual
python3 scripts/ot-probe.py 127.0.0.1 7171

# Watchdog
tail -f /var/log/retro76/watchdog.log    # si install-ot-observability.sh
tail -f /var/log/ot-watchdog.log           # cron legado en algunos VPS
```

---

## Cómo leer resultados

| Log | Diagnóstico |
|-----|-------------|
| `rcv_ms=5000` en disconnect de jugador en juego | Timeout de handshake **no** se quitó → revisar `setSocketGameRecvBlocking` / orden en `otserv.cpp` |
| `rcv_ms=0 nonblock=0` y disconnect `peer closed` | Cliente cerró TCP (salida normal o crash cliente) |
| `invalid packet size` | Paquete corrupto o ataque |
| Muchos `[socket] recv header timeout, retry` | Timeout residual; el reintento debería corregir — si persiste, bug |
| `removeCreature after disconnect` (verbose) | Servidor sacó al personaje del mapa |
| Probe FAIL + container Up | Cuelgue (hilos/sockets), no crash — ver watchdog + `CLOSE-WAIT` en `ot-diagnostics.sh` |

---

## Archivos

| Archivo | Rol |
|---------|-----|
| `server/YurOTS/ots/source/socket_debug.cpp` | Helpers de log y estado de socket |
| `server/YurOTS/ots/source/networkmessage.cpp` | Timeout handshake/juego + errno en recv |
| `server/YurOTS/ots/source/otserv.cpp` | Log de accept, protId, login |
| `server/YurOTS/ots/source/protocol76.cpp` | Disconnect detallado + ReceiveLoop |

---

## Próximos pasos (investigación)

1. **Mantener** `YUROTS_SOCKET_DEBUG=1` hasta el próximo cuelgue reproducido.
2. Antes de reiniciar manualmente, ejecutar el bloque de evidencia de § Incidente en curso.
3. Buscar en logs:
   - `rcv_ms=5000` en disconnect de jugador **en juego** → bug de handshake residual.
   - Ráfaga de `Player recv disconnect` seguida de silencio en logs + probe FAIL → cuelgue clásico.
   - `Listen select failed` → puerto listen cerrado (otro bug).
4. Cuando haya causa y fix, **desactivar** verbose (§ Desactivar) y documentar el fix en [FIX_OT_STABILITY_KICKS_AND_HANG.md](FIX_OT_STABILITY_KICKS_AND_HANG.md).
