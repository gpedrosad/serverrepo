# Fix: Kicks periódicos por lectura TCP incompleta

> **Estado: PREPARADO EN REPO, NO DESPLEGADO**
>
> Cambios en `networkmessage.cpp`, `networkmessage.h` y `protocol76.cpp`.
> Requiere recompilar el binario OT (`yurots`) y reiniciar el container.

## Problema

Jugadores conectados se desconectan del juego de forma intermitente (se ven como
"kicks") aunque el servidor sigue en línea y otros jugadores no se ven afectados
al mismo tiempo.

En logs del VPS el patrón típico es:

1. Baja el contador de jugadores online (`N players` → `N-1`).
2. Unos segundos después aparece `loaded data/players/<nombre>.xml` (re-login).
3. La sesión dura entre decenas de segundos y pocos minutos, sin intervalo fijo.

## Causa raíz (servidor)

El kick no es un comando explícito: es una **desconexión por fallo de lectura**
en el hilo de protocolo del jugador.

```cpp
// protocol76.cpp — Protocol76::ReceiveLoop()
while (msg.ReadFromSocket(s)) {
    parsePacket(msg);
}
// Si ReadFromSocket devuelve false → removeCreature(player)
```

`NetworkMessage::ReadFromSocket` asumía que TCP entrega siempre el encabezado (2
bytes de tamaño) y el cuerpo del paquete **en una sola llamada a `recv()`**:

```cpp
// Código anterior (bug)
m_MsgSize = recv(socket, m_MsgBuf, 2, 0);
if (m_MsgSize != 2) return false;   // ← 1 byte recibido = kick

m_MsgSize += recv(socket, m_MsgBuf + 2, datasize, 0);
if (m_MsgSize != 2 + datasize) return false;  // ← cuerpo partido = kick
```

En TCP los paquetes pueden llegar **fragmentados**. Un `recv()` puede devolver
menos bytes de los pedidos incluso en sockets bloqueantes. El servidor interpretaba
cualquier lectura incompleta como cierre de conexión y expulsaba al personaje.

En Linux además no se manejaba `EAGAIN`/`EWOULDBLOCK` en la lectura (solo en
Windows para el caso sin datos), lo que agrava fallos en timeouts de socket.

### Descartado como causa principal

| Hipótesis | Motivo |
|-----------|--------|
| Conexión inestable del cliente (WiFi, móvil) | Afecta a múltiples jugadores en el mismo VPS con patrones similares; el servidor corta la sesión ante lectura incompleta **sin distinguir** red del cliente. El bug es determinista en el código. |
| Anti-AFK | `TR_ANTI_AFK_DISABLED` en el Makefile |
| Kick por ping (`npings >= 6`) | `kickPlayer()` comentado en `player.cpp` |
| Autosave | Cada 10 min, solo mensaje; no desconecta |
| Timeout 5 s en todas las conexiones | Ya corregido: handshake 5 s, sesión de juego 7 días (`clearSocketRecvTimeout`) |
| `{0,0}` en `SO_RCVTIMEO` (Linux) | Ya corregido: no usar timeout cero |

### Contribuyentes secundarios (corregidos)

- **`clearSocketRecvTimeout(s)` después de `s = 0`** en login de juego (`otserv.cpp`): el timeout de
  handshake (5 s) nunca se quitaba → `recv timeout or would block` en logs y kicks ~cada 5 s.
  **Fix:** llamar `clearSocketRecvTimeout(s)` antes de `s = 0`.
  reemplaza la sesión (`Replacing active session for player: ...`). Agravante al
  reconectar, no explica la caída inicial.
- **Reinicio del container** (`exit 137` en deploy): desconecta a todos, no es
  kick periódico individual.

## Fix aplicado en el repo

### 1. `recvExact()` — lectura bloqueante hasta completar N bytes

Nuevo helper en `networkmessage.cpp` que hace bucle sobre `recv()` hasta recibir
exactamente `len` bytes, o hasta EOF/error/timeout.

### 2. `ReadFromSocket()` reescrito

- Lee 2 bytes de cabecera con `recvExact`.
- Valida `datasize` (rango 0 … `NETWORKMESSAGE_MAXSIZE - 2`).
- Lee el cuerpo con `recvExact`.
- Registra motivo de fallo en `m_LastReadFailReason`.

### 3. Log en desconexión (`protocol76.cpp`)

Al fallar la lectura se imprime en stdout del servidor:

```
Player recv disconnect: Broskas (peer closed connection)
Player recv disconnect: GM Kaiser (invalid packet size)
```

Útil para confirmar en producción que ya no hay kicks por lectura parcial.

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `server/YurOTS/ots/source/networkmessage.cpp` | `recvExact`, `ReadFromSocket` robusto |
| `server/YurOTS/ots/source/networkmessage.h` | `getLastReadFailReason()`, `m_LastReadFailReason` |
| `server/YurOTS/ots/source/protocol76.cpp` | Log al desconectar por recv |

## Despliegue (cuando se autorice)

```bash
# En local o CI: compilar imagen / binario
# En VPS:
DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
```

Tras el deploy, monitorear logs del container OT:

```bash
docker logs -f retro76.ot 2>&1 | grep -E 'Player recv disconnect|players'
```

**Éxito esperado:** desaparecen desconexiones frecuentes sin línea `Player recv
disconnect` previa; si quedan kicks, el log mostrará el motivo real (`peer closed`,
`recv timeout`, etc.).

## Relación con otros fixes de estabilidad

- **Timeout de socket** (`otserv.cpp`): handshake 5 s, juego 7 días — complementario.
- **Web sin sondas a 7171** (`web/data.py`): evita cuelgues del proceso OT por
  conexiones basura; problema distinto a kicks por jugador.
- **Watchdog / observabilidad**: detecta OT colgado; no sustituye este fix.

## Referencias en código

- `Protocol76::ReceiveLoop` — `server/YurOTS/ots/source/protocol76.cpp`
- `NetworkMessage::ReadFromSocket` — `server/YurOTS/ots/source/networkmessage.cpp`
- `setSocketRecvTimeout` / `clearSocketRecvTimeout` — `server/YurOTS/ots/source/otserv.cpp`
- `replaceconnectedcharacter` — `server/YurOTS/ots/config.lua`
