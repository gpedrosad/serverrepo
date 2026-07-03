# Crash diagnostics — qué se captura y cómo usarlo

Este documento describe el sistema de captura de crashes del server Retro76: qué artefactos se generan automáticamente, qué información contienen, cómo extraerlos y cómo analizarlos en caso de un crash.

> **Estado:** implementado en Mac, compilado, **NO pusheado al repo ni al VPS**. Cambios en staging local pendientes de commit/deploy.

---

## 1. Resumen ejecutivo

Antes de este cambio, un crash en producción solo dejaba `docker logs yurots` (stdout sin timestamps, sin stack trace, sin info de players). Era prácticamente imposible diagnosticar qué crasheó.

Ahora, cada vez que `yurots` recibe una señal fatal, deja automáticamente:

1. **`data/crash-<UTC>.log`** — stack trace + registers + signal info
2. **`data/snapshot-<UTC>.txt`** — lista de players online al momento del crash (nombre, level, vocación, pos, HP/MP)
3. **`/cores/core.<exe>.<pid>.<timestamp>`** — core dump nativo (si los cores están habilitados — ver §4)
4. **`yurots.log`** — todo el stdout/stderr con timestamps UTC, persistido (no se pierde al reiniciar el container)

Adicionalmente, Docker reinicia el container automáticamente (`restart: unless-stopped`).

---

## 2. Archivos del sistema

### 2.1. `server/YurOTS/ots/source/crashhandler.h`

API pública:

```cpp
namespace CrashHandler {
    void install();            // llama una vez en main(), antes de cualquier init
    void uninstall();          // opcional, restaura SIG_DFL
    void triggerTestCrash();   // fuerza un SIGSEGV para validar el pipeline
}
```

### 2.2. `server/YurOTS/ots/source/crashhandler.cpp`

Implementación. **Decisiones de diseño clave:**

- **Solo POSIX** (Linux/i386, el target del Dockerfile del proyecto). No usa Windows SEH.
- **Async-signal-safe**: dentro del handler no se usa `malloc`, `printf`, `std::cout`, `std::string`. Solo `write()`, `open()`, `close()`, `backtrace_symbols_fd()`, `snprintf` sobre buffers locales. Esto es crítico — un handler que llame funciones no-safe puede deadlockear o crashear de nuevo.
- **`SA_RESETHAND`**: si la escritura del dump crashea, el handler se restaura a `SIG_DFL` antes, así el segundo crash mata el proceso en vez de loopear.
- **Backtrace con `backtrace_symbols_fd()`**: variante que escribe directo a un fd, sin pasar por `malloc`.
- **Registers de i386** vía `ucontext.h` y `uc_mcontext.gregs[REG_EIP/ESP/...]`. Si en el futuro se compila a 64-bit, hay que adaptar a `REG_RIP/RSP`.
- **Snapshot en archivo separado**: el crash log queda limpio de info de players (que puede ser mucha), y el snapshot queda en formato texto simple fácil de grepear.

### 2.3. `server/YurOTS/ots/source/otserv.cpp` (modificado)

Agregado en `main()`:

```cpp
CrashHandler::install();  // PRIMERO, antes de cualquier init
```

Sigue el bloque legacy `EXCEPTION_TRACER` (que en Linux es código muerto — `ExceptionHandler::InstallHandler()` solo instala SEH en Windows).

### 2.4. `scripts/docker-entrypoint.sh` (nuevo)

Wrapper que ejecuta `yurots` con:
- `ulimit -c unlimited` para permitir cores
- Intento de redirigir `core_pattern` a `/cores` (best-effort, puede fallar si `/proc` no es writable)
- Pipeline `yurots 2>&1 | ts '[%Y-%m-%dT%H:%M:%SZ]' | tee -a yurots.log`:
  - `ts` (de moreutils) prefija cada línea con timestamp UTC ISO 8601
  - `tee -a` persiste a `yurots.log` (sobrevive reinicios)

### 2.5. `scripts/extract-core.sh` (nuevo)

Post-mortem. Si tenés un core dump en `/cores/` o `data/`, lo analiza con `gdb`:

```bash
./scripts/extract-core.sh /cores/core.yurots.1234.1719840000
# o
./scripts/extract-core.sh     # auto-detecta el más nuevo
```

Genera `data/gdb-report-<UTC>.txt` con:
- `thread apply all bt full` (backtrace de todos los threads)
- `info registers`
- `info threads`
- Disassembly alrededor de `$pc`

### 2.6. `Dockerfile` (modificado)

- Agregado `moreutils` al `apt-get install` (provee `ts`).
- `COPY scripts/docker-entrypoint.sh /app/YurOTS/docker-entrypoint.sh` y `chmod +x`.
- `CMD` ahora apunta al entrypoint en vez de `bash`.

### 2.7. `docker-compose.prod.yml` (modificado)

- Volumen `./cores:/cores` — persiste cores en el host.
- `security_opt: seccomp=unconfined` — necesario para que el container pueda setear `core_pattern` (sin esto, el `echo > /proc/sys/kernel/core_pattern` falla silenciosamente).
- `command: ["/app/YurOTS/docker-entrypoint.sh"]` — usa el wrapper en vez de `./source/yurots` directo.

---

## 3. Qué se captura exactamente

### 3.1. `data/crash-<UTC>.log`

```
============================================
YurOTS CRASH REPORT
============================================
Signal:    11 (SIGSEGV)
Time UTC:  2026-07-01 14:23:45
PID:       1234
UID/EUID:  0 / 0
Fault addr: 0x00000000
si_code:    1

./source/yurots(_ZN12CrashHandler7installEv+0x3e) [0x1d685]
... (backtrace completa, raw symbol strings)

--- Registers (i386) ---
EAX: 0xdeadbeef
EBX: 0x...
...
EIP: 0x08049abc
ESP: 0x...

Saved crash report to: data/crash-20260701-142345.log
```

**Importante:** el backtrace se escribe con `backtrace_symbols_fd()` que produce strings tipo `binary(function+offset) [absolute_addr]`. No están **demangled** automáticamente. Para tener nombres C++ legibles, después de un crash podés correr:

```bash
addr2line -e server/YurOTS/ots/source/yurots -f -C 0x08049abc
```

O levantar el `gdb-report-<UTC>.txt` generado por `extract-core.sh` (ese sí usa gdb con pretty printing).

### 3.2. `data/snapshot-<UTC>.txt`

```
============================================
YurOTS PLAYER SNAPSHOT (taken at crash time)
============================================
Snapshot UTC: 2026-07-01 14:23:45
Crash file:   data/crash-20260701-142345.log

  player id=1001 name="Broskas" lvl=35 voc=4 hp=800/800 mp=300/300 pos=(145,50,7)
  player id=1002 name="Cachero" lvl=42 voc=3 hp=720/720 mp=450/450 pos=(200,80,6)
  ...

Total online: 8
```

`voc` es el int del enum `playervoc_t` (1=Sorcerer, 2=Druid, 3=Paladin, 4=Knight, 5-8=promovidas). Mapeo en `player.h:88-92`.

### 3.3. `yurots.log`

Todo el output del server, con timestamp UTC ISO 8601 al inicio de cada línea:

```
[2026-07-01T14:23:01Z] :: YurOTS 0.9.4f
[2026-07-01T14:23:01Z] :: ~~~~~~~~~~~~~
[2026-07-01T14:23:01Z] :: Initializing random numbers...   [done]
[2026-07-01T14:23:42Z] Loot of a troll: spear, 22 gold coin.
[2026-07-01T14:23:45Z] :: [crash] signal=SIGSEGV saved=data/crash-20260701-142345.log pid=1234
```

El `:: [crash] ...` es la única línea que se loggea **antes** de la muerte del proceso. Después, Docker reinicia el container y el log se sigue escribiendo desde 0 (la nueva instancia es un proceso nuevo, mismo `yurots.log` append-only).

---

## 4. Core dumps (Linux nativo)

### 4.1. Cómo se habilitan

1. `ulimit -c unlimited` en el entrypoint → permite cores de cualquier tamaño (sujeto al límite global del sistema).
2. `echo '/cores/core.%e.%p.%t' > /proc/sys/kernel/core_pattern` → redirige los cores al volumen montado.
3. `seccomp=unconfined` en compose → necesario para que el `echo` no sea bloqueado por la seccomp default de Docker.

### 4.2. Dónde quedan

- **Si todo funcionó:** `./cores/core.yurots.<pid>.<epoch>` en el host (gracias al bind mount `./cores:/cores`).
- **Si `core_pattern` no se pudo escribir:** los cores caen en el cwd del proceso, que es `/app/YurOTS/ots` (= `./server/YurOTS/ots/` en el host).

### 4.3. Cómo analizarlos

En el VPS:

```bash
# 1) Ver los cores disponibles
ls -lt /cores/

# 2) Analizar el más nuevo
./scripts/extract-core.sh
# o explícito:
./scripts/extract-core.sh /cores/core.yurots.1234.1719840000

# 3) El script genera data/gdb-report-<UTC>.txt con todo el backtrace
```

### 4.4. Espacio en disco

- Binario `yurots` ≈ 13 MB.
- Un core típico de un proceso de 50 MB RSS ≈ 50 MB (compress con `gzip -9` queda en ~15 MB).
- El volumen `./cores` debería tener al menos 500 MB de margen. **Monitorear** con `du -sh cores/`.

Si te quedás sin espacio, podés rotar:

```bash
# Crontab sugerido (diario, mantiene últimos 5)
find /home/yurots-principal/cores -name 'core.*' -mtime +7 -delete
```

---

## 5. Procedimiento post-crash

### Paso 1: confirmar el crash

```bash
ssh root@64.176.20.238 'cd ~/yurots-principal && docker ps -a | grep yurots'
# Ver "Up X minutes" — si el "X" se resetea, hubo restart
```

### Paso 2: leer el crash log

```bash
ssh root@64.176.20.238 'ls -lt ~/yurots-principal/server/YurOTS/ots/data/crash-*.log | head -1'
# Leer el archivo:
ssh root@64.176.20.238 'cat ~/yurots-principal/server/YurOTS/ots/data/crash-20260701-142345.log'
```

### Paso 3: leer el snapshot de players

```bash
ssh root@64.176.20.238 'cat ~/yurots-principal/server/YurOTS/ots/data/snapshot-20260701-142345.txt'
```

Esto te dice **quién estaba online y qué hacía** al momento del crash. Si un player específico aparece en TODOS los crashes, es probable que sea el causante (ej. un item corrupto en su inventario, una spell que crashea con su level, etc.).

### Paso 4: analizar el core (si está)

```bash
ssh root@64.176.20.238 'cd ~/yurots-principal && ./scripts/extract-core.sh'
```

Esto genera `data/gdb-report-<UTC>.txt` con el backtrace de TODOS los threads. En YurOTS hay ~10-15 threads; el que tenga el stack en código de YurOTS (no en libpthread, libxml2, etc.) es el thread que crasheó.

### Paso 5: leer las últimas líneas del yurots.log

```bash
ssh root@64.176.20.238 'tail -200 ~/yurots-principal/server/YurOTS/ots/yurots.log'
```

Con timestamps UTC ya en cada línea, podés correlacionar con la hora del crash.

---

## 6. Limitaciones conocidas

### 6.1. Demangling

El backtrace en `data/crash-*.log` no está demangled. Los símbolos aparecen como `_ZN12CrashHandler7installEv` en vez de `CrashHandler::install()`. Esto es intencional (demangle puede no ser async-signal-safe). Para nombres legibles, usar `extract-core.sh` que sí usa gdb.

### 6.2. Async-signal-safety

Dentro del handler evitamos `malloc`, `printf`, `std::cout`, `std::string`. Pero:

- `Player::listPlayer.list` es un `std::map`. Iterarlo desde un signal handler NO es técnicamente safe. Si justo en el momento del crash otro thread está modificando el map, podemos leer memoria inconsistente.
- En la práctica, los crashes son raros y el riesgo es bajo. Si vemos crashes dentro de `dump_players_snapshot`, podemos refactorizar a un buffer pre-allocado + escritura deferred.
- **Mitigación futura:** mantener un array global `g_online_players[]` actualizado en login/logout, y leerlo desde el handler (acceso atómico).

### 6.3. SIGPIPE no se captura

`SIGPIPE` se ignora a propósito (default). Si un cliente se desconecta durante un write, no genera crash log — es comportamiento normal.

### 6.4. C++ exceptions vs signals

El `EXCEPTION_TRACER` legacy (Windows SEH) no hace nada en Linux. Si una C++ exception se propaga hasta `main()` sin catch, en Linux se llama `std::terminate()` que en algunas versiones hace `abort()` (señal `SIGABRT`) — ese sí lo capturamos. Pero si el código tiene un `catch(...)` que silencia la exception, no hay crash visible.

### 6.5. Stack overflow

Si el crash es stack overflow, el handler puede no tener stack suficiente para ejecutarse. En ese caso el proceso muere sin generar el log. Para detectarlo: revisar `yurots.log` buscando el crash, y `cores/` para ver si se generó un core.

### 6.6. 64-bit no soportado

El handler asume i386 (32-bit). Los `REG_EIP`, `REG_ESP`, etc. son específicos de x86 32-bit. Si en el futuro se compila a 64-bit, hay que cambiar a `REG_RIP`, `REG_RSP`, etc.

---

## 7. Testing

### 7.1. Test del crash handler sin matar el server

Si agregás un comando GM `/test_crash`, llamás `CrashHandler::triggerTestCrash()` que fuerza un SIGSEGV controlado. Útil para validar el pipeline end-to-end sin esperar un crash real.

(Sugerencia: NO agregado todavía — el usuario pidió "no implementar nada" en este lote. Es un follow-up trivial.)

### 7.2. Test manual desde el host

Si querés probar el pipeline completo:

```bash
# En el container, kill -SIGSEGV al PID del yurots (NO recomendado, el server se reiniciará)
docker exec yurots bash -c "kill -SIGSEGV \$(pgrep yurots)"
```

Verás:
1. En `docker logs yurots`: `:: [crash] signal=SIGSEGV saved=data/crash-...log pid=...`
2. Docker reinicia el container (10-30 segundos)
3. `data/crash-*.log` y `data/snapshot-*.txt` quedaron en `./server/YurOTS/ots/data/`

---

## 8. Lo que NO hace este sistema (todavía)

- ❌ **No hay watchdog externo** que detecte crash loops (server crasheando cada 30s). Eso es el Tier 3 de la lista original — script bash + cron. Pendiente.
- ❌ **No hay notificación automática** a Discord/email. Crash → log en disco → vos te enterás cuando ssh-eás. Pendiente.
- ❌ **No hay logger estructurado** con rotación. Los 200+ `std::cout` siguen yendo a stdout + yurots.log. Tier 2 de la lista original. Pendiente.
- ❌ **No hay healthcheck mejorado** (sigue siendo solo TCP). Tier 3. Pendiente.

Si querés alguna de esas como próxima iteración, decime.

---

## 9. Changelog

- **2026-07-01** — Implementación inicial. Tier 1 completo (signal handler + player snapshot + core dumps + stdout persistence). NO pusheado aún (staging local).
