# Logs de red OT — guía de diagnóstico

> **En repo, no desplegado aún** (jul 2026). Cuando se despliegue, activar verbose solo si hace falta.

## Qué ha estado pasando (resumen)

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

## Cómo activar (cuando se despliegue)

### Local / Docker

```bash
# docker-compose.yml — servicio yurots:
environment:
  - YUROTS_SOCKET_DEBUG=1

docker compose up -d yurots
docker logs -f yurots 2>&1 | grep -E '\[socket\]|Player recv disconnect'
```

### VPS (sin tocar jugadores en horario pico)

En `docker-compose.prod.yml`, agregar bajo `yurots`:

```yaml
environment:
  - YUROTS_SOCKET_DEBUG=1
```

Luego `docker compose -f docker-compose.prod.yml up -d yurots` (solo reinicia OT, no recompila).

Para verbose **sin** reinicio: no es posible — la variable se lee al arrancar cada hilo la primera vez.

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
tail -f /var/log/retro76/watchdog.log
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

## Próximo deploy

1. `git pull` + `deploy-vps.sh` (compila con logs nuevos).
2. Dejar **sin** `YUROTS_SOCKET_DEBUG` al principio — las líneas `Player recv disconnect` ya traen `rcv_ms` y `errno`.
3. Si sigue el problema, activar `YUROTS_SOCKET_DEBUG=1` y reproducir con un jugador quieto 30 s.
