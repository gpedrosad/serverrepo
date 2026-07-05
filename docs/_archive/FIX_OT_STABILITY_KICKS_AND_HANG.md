# Estabilidad OT: kicks por timeout y cuelgues en 7171

> **Estado: fix en repo — desplegar con `deploy-vps.sh`**

## Síntomas observados (producción, jul 2026)

1. **Kicks masivos** — jugadores caen cada pocos segundos y reconectan.
2. **Log repetido:**
   ```
   Player recv disconnect: <nombre> (recv timeout or would block)
   ```
3. **Cuelgue del puerto 7171** — container vivo, probe `FAIL ... TimeoutError` (8 s).
4. **Watchdog** reinicia el container tras 2 healthchecks fallidos (~4 min).

## Causa raíz: `SO_RCVTIMEO` de handshake en sesiones de juego

### Flujo roto

1. `ConnectionHandler` ponía **timeout de 5 s** en **todas** las conexiones al aceptar.
2. El primer paquete (login / info) se leía con ese timeout — correcto para bots.
3. En login de juego (`0x020A`), el timeout **debía quitarse** antes de `ReceiveLoop`.
4. **Bugs encadenados:**
   - `clearSocketRecvTimeout(s)` se llamaba **después** de `s = 0` → no afectaba el socket real.
   - `clearSocketRecvTimeout` usaba **7 días** en vez de recv bloqueante sin límite.
   - En Linux, `{0,0}` en `SO_RCVTIMEO` se interpretó mal; en realidad significa **sin timeout** en sockets bloqueantes (`man 7 socket`).
5. `ReadFromSocket` / `recvExact` trataban `EAGAIN`/`EWOULDBLOCK` como **desconexión fatal** → kick.

### Por qué parecía “cada ~5 segundos”

Cliente quieto → `recv()` espera el siguiente paquete → vence `SO_RCVTIMEO` de 5 s →
`recv timeout or would block` → `removeCreature` → reconexión en bucle.

### Por qué colgaba el servidor

Tormenta de kicks/reconexiones → muchos sockets en `CLOSE-WAIT` / hilos en `ConnectionHandler` →
el hilo principal deja de responder al probe `0xFFFF info` en 7171 a tiempo → watchdog reinicia.

No era un crash del binario; era **degradación por desconexiones en cascada**.

## Fix aplicado

### `networkmessage.h` / `networkmessage.cpp`

| Función | Uso |
|---------|-----|
| `setSocketHandshakeRecvTimeout(s)` | 5 s solo para el **primer** `ReadFromSocket` |
| `setSocketGameRecvBlocking(s)` | Quita timeout, fuerza socket **bloqueante** (`fcntl`, `SO_RCVTIMEO {0,0}` en Linux) |
| `ReadFromSocket` | Si falla por `would block`, reintenta una vez tras `setSocketGameRecvBlocking` |

### `otserv.cpp` — `ConnectionHandler`

```cpp
setSocketHandshakeRecvTimeout(s);
if (msg.ReadFromSocket(s)) {
    setSocketGameRecvBlocking(s);   // inmediatamente tras el primer paquete
    // ... login / juego ...
    setSocketGameRecvBlocking(s);   // antes de ReceiveLoop
    protocol->ReceiveLoop();
}
```

### `protocol76.cpp` — `ReceiveLoop`

```cpp
if (s)
    setSocketGameRecvBlocking(s);
```

### Logging (ya desplegado antes)

```
Player recv disconnect: <nombre> (<motivo>)
```

Tras el fix, **no** deberían aparecer `recv timeout or would block` en jugadores quietos.

## Descartado

| Hipótesis | Motivo |
|-----------|--------|
| WiFi / cliente inestable | Mismo motivo en muchos jugadores; patrón fijo ~5 s = timeout servidor |
| Anti-AFK | Deshabilitado en build |
| Kick por ping | `kickPlayer()` comentado |
| `recvExact` / TCP fragmentado | Fix previo; no explica intervalo de 5 s |

## Despliegue

```bash
DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
```

## Verificación post-deploy

```bash
python3 scripts/ot-probe.py 127.0.0.1 7171
docker logs -f yurots 2>&1 | grep -E 'Player recv disconnect|Server Running'
```

**OK:** jugadores quietos >30 s sin línea `recv timeout or would block`.

**Mal:** sigue el patrón → revisar que el binario compiló (`docker exec yurots stat yurots`).

**Logs detallados:** ver `docs/SOCKET_DEBUG_LOGGING.md` (estado de socket, errno, modo verbose).

## Historial de commits relacionados

- `f2c8754` — `recvExact` + log de desconexión
- `da16261` — `clearSocketRecvTimeout` antes de `s=0` (insuficiente solo)
- *(este fix)* — handshake vs juego separados; recv bloqueante real en `ReceiveLoop`
- **Listen `EINTR`** — `select()==-1` por señal cerraba el puerto 7171; el juego seguía pero nadie conectaba

## Archivos

- `server/YurOTS/ots/source/networkmessage.cpp`
- `server/YurOTS/ots/source/networkmessage.h`
- `server/YurOTS/ots/source/otserv.cpp`
- `server/YurOTS/ots/source/protocol76.cpp`
- `docs/FIX_PLAYER_KICKS_READFROMSOCKET.md` (contexto anterior)
