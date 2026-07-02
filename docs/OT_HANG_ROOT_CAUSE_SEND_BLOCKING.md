# Causa raíz probable del cuelgue OT: `send()` bloqueante bajo `gameLock`

> Estado: investigación documentada y fix defensivo aplicado en repo el 2026-07-02.
>
> Alcance: cuelgues del OT en `retro76.cl` donde el proceso sigue vivo, el watchdog termina reiniciando, y no hay `SIGSEGV` ni core dump nuevo.

Relacionado:
- [FIX_OT_STABILITY_KICKS_AND_HANG.md](FIX_OT_STABILITY_KICKS_AND_HANG.md)
- [PREVENT_OT_HANGS.md](PREVENT_OT_HANGS.md)
- [SOCKET_DEBUG_LOGGING.md](SOCKET_DEBUG_LOGGING.md)
- [LEERCODEX.md](../LEERCODEX.md)

---

## 1. Resumen ejecutivo

La hipótesis más fuerte para los cuelgues recurrentes de julio 2026 ya no es el bug viejo de `SO_RCVTIMEO` del handshake.

Ese bug explicaba:
- kicks masivos
- `recv timeout or would block`
- `rcv_ms=5000` en sesiones de juego

Pero el patrón nuevo observado el **2026-07-02** encaja mejor con otra falla:

1. El servidor acumula mensajes para jugadores.
2. El loop del juego llama `flushSendBuffers()`.
3. Ese flush termina haciendo `send()` a clientes.
4. Si un cliente queda lento o deja de drenar su socket, ese `send()` puede bloquear.
5. Como ocurría dentro del hilo del juego y/o bajo `gameLock`, el mundo entero deja de avanzar.
6. Los clientes terminan cerrando TCP (`peer closed`) y el watchdog reinicia el container.

En corto: **un cliente lento podía congelar el loop global del juego**.

---

## 2. Qué pasó el 2026-07-02

### Incidente confirmado

En producción, el watchdog registró este ciclo:

- `2026-07-02 19:40:11 UTC` → primer fallo de healthcheck
- `2026-07-02 19:42:11 UTC` → segundo fallo de healthcheck
- `2026-07-02 19:42:22 UTC` → `reiniciando yurots (restart -t 45)`
- `2026-07-02 19:43:18 UTC` → `recuperado tras restart`

Eso corresponde a:
- `16:40:11 -03`
- `16:42:11 -03`
- `16:42:22 -03`
- `16:43:18 -03`

También hubo otro episodio parecido el mismo día:

- `2026-07-02 19:24:12 UTC` → segundo fallo
- `2026-07-02 19:24:23 UTC` → restart
- `2026-07-02 19:25:19 UTC` → recuperación

### Qué mostró la evidencia

- El container estaba `running` antes del restart.
- No hubo `RestartCount` creciente por crash.
- No hubo core dump nuevo asociado a ese horario.
- Docker terminó forzando la salida tras `45s`, lo que sugiere proceso colgado o no cooperativo al shutdown.
- Los logs previos al incidente mostraban desconexiones `peer closed`, no `SIGSEGV`.

Conclusión operativa:

- **No fue crash del binario.**
- **Sí fue cuelgue / congelamiento de runtime.**

---

## 3. Qué quedó descartado

### A) No parece ser el bug viejo del handshake

El fix previo separó handshake vs juego:

- `setSocketHandshakeRecvTimeout(s)` solo para el primer paquete
- `setSocketGameRecvBlocking(s)` antes de `ReceiveLoop`

Además, la evidencia reciente no muestra como síntoma dominante:

- `recv timeout or would block`
- desconexiones de jugador con `rcv_ms=5000` en sesión de juego

Importante:

La línea:

```text
[socket] handshake timeout 5s on sock=...
```

**no significa que el handshake haya fallado**. Solo indica que el socket recibió la configuración de timeout de 5s para el primer `ReadFromSocket`.

### B) No parece ser crash clásico

No encaja con:

- `SIGSEGV`
- `Segmentation fault`
- `crash-*.log` nuevo en el mismo minuto
- `core` nuevo asociado al incidente

### C) No parece ser solo “red mala de clientes”

Si fuera únicamente red de clientes:

- no debería congelarse el mundo completo
- no debería requerir watchdog restart del server
- no debería repetirse el patrón “proceso vivo pero servicio muerto”

---

## 4. La cadena técnica probable

La cadena sospechosa es esta:

1. El juego genera mensajes para uno o más jugadores.
2. Esos mensajes se acumulan en `OutputBuffer`.
3. El loop del juego llama `flushSendBuffers()`.
4. `flushSendBuffers()` manda datos reales a sockets.
5. Si uno de esos sockets está lento, el `send()` queda esperando.
6. Mientras tanto, el hilo del juego deja de avanzar o avanza con latencia extrema.

Eso explica muy bien:

- loot/save normal poco antes del incidente
- luego silencio o actividad incompleta
- desconexiones en ráfaga
- necesidad de restart manual/automático

---

## 5. Evidencia en código

### 5.1 `Game::flushSendBuffers()` terminaba haciendo I/O de red

Antes del fix, `flushSendBuffers()` recorría `BufferedPlayers` y llamaba:

- `Player::flushMsg()`
- `Protocol76::flushOutputBuffer()`
- `NetworkMessage::WriteToSocket()`

Ruta:

- [server/YurOTS/ots/source/game.cpp](../server/YurOTS/ots/source/game.cpp)
- [server/YurOTS/ots/source/player.cpp](../server/YurOTS/ots/source/player.cpp)
- [server/YurOTS/ots/source/protocol76.cpp](../server/YurOTS/ots/source/protocol76.cpp)
- [server/YurOTS/ots/source/networkmessage.cpp](../server/YurOTS/ots/source/networkmessage.cpp)

### 5.2 `flushSendBuffers()` estaba dentro de caminos críticos del loop

Se llamaba desde rutas sensibles del juego, por ejemplo:

- `Game::checkPlayerWalk()`
- `Game::checkCreature()`
- `Game::checkCreatureAttacking()`
- `Game::checkDecay()`

Todas forman parte del tick del mundo.

### 5.3 En Linux los sockets de juego quedaban bloqueantes

El código actual de gameplay usa:

```cpp
setSocketGameRecvBlocking(s);
```

Eso es correcto para `recv`, pero significa que el socket queda en modo bloqueante si después se usa `send()` sin defensas adicionales.

### 5.4 `WriteToSocket()` podía esperar demasiado

Antes del hardening nuevo:

- en Linux usaba `send(..., flags=0)`
- reintentaba muchísimas veces con `EAGAIN/EWOULDBLOCK`
- no acotaba de forma práctica el tiempo total de un cliente lento

Eso abría la puerta a que una sola conexión degradada se llevara puesto el ritmo del servidor.

---

## 6. Por qué esto puede colgar “todo” y no solo un jugador

El problema no es solamente “un jugador no recibe sus mensajes”.

El problema es dónde ocurre el envío:

- si el envío se hace mientras el loop del juego está en trabajo crítico
- o si se sostiene `gameLock` alrededor del proceso

entonces se bloquea:

- movimiento
- combate
- decay
- pings
- actualizaciones a otros clientes

Resultado visible:

- jugadores ya conectados quedan congelados
- luego se desconectan
- el watchdog observa servicio muerto y reinicia

---

## 7. Open question honesta

La hipótesis de `send()` bloqueante explica **muy bien** el congelamiento del mundo y las desconexiones en cascada.

Lo que todavía queda como punto a seguir observando es esto:

- el `ot-probe` de `0xFFFF info` también llegó a hacer timeout

Eso podría significar una de estas dos cosas:

1. el bloqueo del loop principal genera suficiente degradación como para afectar el resto del proceso;
2. además del bloqueo de `send()`, hay una segunda amplificación en el path de `accept` / creación de threads / presión general de sockets.

O sea:

- **la hipótesis actual es fuerte**
- **pero todavía la tratamos como “causa raíz probable”, no como verdad matemática cerrada**

---

## 8. Fix defensivo aplicado en repo

Se aplicaron tres cambios para cortar esta clase de cuelgue.

### A) `WriteToSocket()` ahora acota el daño de un cliente lento

Archivo:
- [server/YurOTS/ots/source/networkmessage.cpp](../server/YurOTS/ots/source/networkmessage.cpp)

Cambio:

- en Linux usa flags por envío para no quedarse bloqueado indefinidamente
- limita reintentos
- maneja `EINTR`

Objetivo:

- que un cliente lento deje de ser capaz de frenar el proceso completo

### B) `flushOutputBuffer()` ahora corta la conexión si el envío se estanca

Archivo:
- [server/YurOTS/ots/source/protocol76.cpp](../server/YurOTS/ots/source/protocol76.cpp)

Cambio:

- si `WriteToSocket()` falla, se loguea
- se ejecuta `disconnectConnection()`

Objetivo:

- aislar al cliente problemático en vez de arrastrar al servidor

### C) `flushSendBuffers()` dejó de hacer I/O de red bajo `gameLock`

Archivo:
- [server/YurOTS/ots/source/game.cpp](../server/YurOTS/ots/source/game.cpp)

Cambio:

- bajo `gameLock` solo mueve las colas (`BufferedPlayers`, `ToReleaseThings`)
- el `flushMsg()` real ocurre fuera del lock
- además, los callers críticos (`checkPlayerWalk`, `checkCreature`, `checkCreatureAttacking`, `checkDecay`) ya no hacen el flush dentro de la sección crítica

Objetivo:

- separar el trabajo de mundo del trabajo de socket

---

## 9. Qué valida este fix

Si la hipótesis es correcta, después del deploy deberíamos ver:

- menos o ningún watchdog restart por cuelgue
- si un cliente se degrada, aparece algo tipo `Player send disconnect`
- el mundo sigue respondiendo para el resto
- `ot-probe` sigue OK incluso bajo carga o clientes problemáticos

### Señales buenas post-deploy

- `python3 scripts/ot-probe.py 127.0.0.1 7171` estable
- sin nuevos `healthcheck falló (2/2)` en watchdog
- sin restart automáticos por cuelgue
- sin ráfagas masivas de `peer closed` justo antes de silencio global

### Señales malas post-deploy

- sigue habiendo cuelgues completos
- vuelve a repetirse “probe FAIL + proceso vivo + restart watchdog”
- el nuevo log de `Player send disconnect` explota en volumen y termina igual en freeze

Si eso pasa, la siguiente línea de investigación es:

- modelo `1 thread por conexión`
- presión de threads en `ConnectionHandler`
- posibles rutas adicionales de I/O bloqueante fuera del flush principal

---

## 10. Verificación recomendada en producción

Después de deploy:

```bash
ssh root@64.176.20.238
cd ~/yurots-principal
python3 scripts/ot-probe.py 127.0.0.1 7171
docker logs yurots --tail 50
tail -40 /var/log/ot-watchdog.log
```

Durante las primeras horas:

```bash
grep 'Player send disconnect' server/YurOTS/ots/yurots.log | tail -40
grep '\[ot-watchdog\]' /var/log/ot-watchdog.log | tail -40
python3 scripts/ot-probe.py 127.0.0.1 7171
```

Si vuelve a pasar un cuelgue:

```bash
./scripts/ot-diagnostics.sh | tee /tmp/ot-hang-$(date +%Y%m%d-%H%M%S).txt
tail -120 server/YurOTS/ots/yurots.log
tail -80 /var/log/ot-watchdog.log
ss -tan | grep 7171 | head -30
```

---

## 11. Limitaciones de validación local

No quedó una compilación local completa validada en esta máquina porque el árbol actual ya falla por motivos de entorno/base que no nacen de este cambio:

- falta `lua.h` en el entorno local
- hay errores legacy en headers como `fileloader.h` e `item.h`

Eso significa:

- el fix quedó aplicado en código
- el diff es coherente
- pero la validación final tiene que hacerse en el entorno real de build/deploy del proyecto

---

## 12. Conclusión

La mejor explicación actual para los cuelgues del 2026-07-02 es:

**I/O de salida a clientes demasiado bloqueante ejecutado en el camino crítico del loop del juego.**

El hardening aplicado apunta exactamente a ese punto:

- limitar `send()`
- desconectar sockets de salida rota
- sacar el flush del `gameLock`

Si después del deploy desaparecen los cuelgues y, como mucho, quedan desconexiones aisladas de clientes lentos, esa hipótesis quedará prácticamente confirmada.

Si no, esta documentación deja listo el siguiente nivel de investigación sin volver a mezclarlo con el bug viejo del handshake.

---

## 13. Deploy y rollback

### Deploy (VPS)

```bash
cd ~/yurots-principal
DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
```

El script hace backup de `players/` y `accounts/` antes del pull. El fix **requiere recompilar** (cambios en `.cpp`).

### Rollback rápido

Antes del deploy se etiquetó el estado previo:

| Tag | Qué es |
|-----|--------|
| `pre-ot-send-blocking-fix` | Último commit en `main` **sin** este fix |

```bash
cd ~/yurots-principal
git fetch --tags
DEPLOY_I_READ_README=yes ./scripts/rollback-ot-send-blocking-fix.sh
```

Eso restaura los tres `.cpp` del tag, recompila y reinicia. No toca mapa ni jugadores.

### Backup extra del binario (opcional, manual)

```bash
cp server/YurOTS/ots/source/yurots server/YurOTS/ots/source/yurots.pre-send-blocking-fix
```

### Volver a activar el fix

```bash
git checkout main -- \
  server/YurOTS/ots/source/game.cpp \
  server/YurOTS/ots/source/networkmessage.cpp \
  server/YurOTS/ots/source/protocol76.cpp
DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
```

### Cuándo hacer rollback

- Crashes nuevos o corrupción tras el deploy
- Cuelgues **peores** que antes
- Explosión de `Player send disconnect` que vacía el servidor

Si solo ves desconexiones aisladas de clientes lentos y el probe sigue OK, **no** rollback — es el comportamiento esperado del fix.
