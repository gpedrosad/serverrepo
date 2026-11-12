# Pruebas con sanitizers y bots (errores de memoria del servidor)

> **Estado:** hecho por primera vez el 2026-11-12 en la ThinkPad (arreglos en `main` y deployados ese día). Encontró una caída remota sin login, dos
> corrupciones de memoria, una carrera en la configuración y tres cuentas de azar que no hacen lo que dicen
> (§ 5: la corrección está en el binario, apagada; se prende desde `config.lua`).
> **Regla:** los bots y el binario de prueba corren sobre una **copia** de los datos, en otro puerto. Nunca
> contra el servidor donde se juega (`exercise-server.py` se niega a usar el puerto 7171).

El servidor es C++ viejo: un error de memoria no siempre lo tira en el momento, a veces corrompe algo y se cae
(o se cuelga) minutos después en otro lado. Para encontrarlos se compila una copia con **AddressSanitizer**
(memoria) y **UBSan** (operaciones indefinidas), se la levanta aparte y se la maltrata con bots. Cada error
sale en el log con el archivo y la línea.

## 1. Avisos del compilador (siempre activos)

El `Makefile` compila con `-Wall` menos los avisos que en este código son ruido (`WARN`), y **sin
`-fpermissive`**. El build normal tiene que salir **sin ningún aviso**: los que quedan activos suelen ser
errores de verdad (variable sin inicializar, `delete` donde iba `delete[]`, sangría que engaña). Comprobar
después de tocar C++:

```bash
ssh thinkpad 'cd ~/build/deploy-src && grep -c "warning:" build.log'   # tiene que dar 0
```

(guardando la salida del `make` en `build.log`; ver [THINKPAD_TEST_SERVER.md](THINKPAD_TEST_SERVER.md)).

## 2. Compilar la copia con sanitizers

En la ThinkPad (la Mac mini no compila), con la imagen del servidor. Tarda ~5 min; el binario pesa ~50 MB
y corre varias veces más lento, por eso es solo para pruebas.

```bash
# desde la Mac, parado en el repo: código a una carpeta aparte de la ThinkPad
rsync -a --exclude "*.o" --exclude yurots server/YurOTS/ots/source/ thinkpad:build/asan-src/

ssh thinkpad 'cd ~/build/asan-src && docker run --rm --entrypoint "" -v "$PWD":/src -w /src \
  serverrepo-yurots:latest bash -c "rm -f *.o yurots; make -j4 \
  CXX=\"g++ -fsanitize=address -fsanitize=undefined -fno-sanitize=alignment -fsanitize-recover=address\" \
  OPT=\"-O1 -fno-omit-frame-pointer\" yurots" > build.log 2>&1'
```

- `rm -f *.o`: el `Makefile` no sigue dependencias de headers; después de tocar un `.h` hay que recompilar todo.
- `-fno-sanitize=alignment`: el protocolo lee enteros de un buffer de bytes en cualquier posición (miles de
  avisos que en x86 no son un problema).
- `-fsanitize-recover=address` + `halt_on_error=0`: sigue corriendo después del primer error, así una
  corrida muestra varios.

## 3. Levantar la copia (puerto 7173, solo local)

```bash
ssh thinkpad
mkdir -p ~/build/asan-run && cd ~/build/asan-run
rsync -a --exclude source --exclude "*.log" ~/apps/serverrepo/server/YurOTS/ots ./     # copia de datos y config
mkdir -p ots/source && cp ~/build/asan-src/yurots ots/source/yurots
sed -i 's/^port = .*/port = "7173"/; s/^ip = .*/ip = "127.0.0.1"/' ots/config.lua
python3 ~/apps/serverrepo/scripts/ot/make-test-bots.py ots/data 150 86 6             # cuentas de los bots

docker run -d --name yurots-asan --security-opt seccomp=unconfined -p 127.0.0.1:7173:7173 \
  -v ~/build/asan-run:/app/YurOTS -w /app/YurOTS/ots \
  -e YUROTS_ITEMS_OTB=data/items/items-zagan-test.otb -e YUROTS_ITEMS_XML=data/items/items-zagan-test.xml \
  -e ASAN_OPTIONS=detect_leaks=0:halt_on_error=0 -e UBSAN_OPTIONS=print_stacktrace=1 \
  --entrypoint "" serverrepo-yurots:latest bash -c "./source/yurots > /app/YurOTS/asan-server.log 2>&1"
```

- `150 86 6` es una casilla libre cerca del templo; los bots aparecen ahí. Con otro mapa, elegir otra.
- `make-test-bots.py` crea las cuentas 111111 (6 personajes) y 111112 (Bot GM) con una contraseña de prueba.
  Se niega a escribir dentro de un repo git, para que nunca caigan en los datos reales.
- `seccomp=unconfined`: ASan lo necesita en esta imagen i386.
- Tarda ~1 min en cargar el mapa (`Retro76 Server Running...` en `asan-server.log`).

## 4. Maltratarlo con bots

```bash
cd ~/apps/serverrepo
python3 scripts/ot/exercise-server.py --port 7173 --account 111111 --password asantest \
  --chars "Bot Knight" "Bot Sorc" "Bot Druid" "Bot Pally" "Bot Mage" "Bot Tank" \
  --gm-account 111112 --gm-char "Bot GM" --center 150 86 6 --minutes 5 --fuzz --seed 3

# errores encontrados
grep -a "runtime error\|ERROR: AddressSanitizer\|SUMMARY\|terminate" ~/build/asan-run/asan-server.log | sort | uniq -c
ls ~/build/asan-run/ots/data/crash-*.log        # si se cayó
```

`exercise-server.py` (un hilo por personaje): camina, habla, dice todos los hechizos de `spells.xml`, tira
runas, ataca lo que ve, mueve y usa ítems, abre contenedores, se desconecta bien o cortando el socket y
vuelve a entrar. El Bot GM invoca monstruos al lado (`/m`) y hace `/save`, `/clean`. Con `--fuzz` manda
además paquetes con opcodes y cuerpos al azar. Otro hilo golpea el puerto sin entrar al juego: consultas de
estado, logins malos, paquetes vacíos o cortados y pedidos al account creator. Cambiar `--seed` da otra
corrida; al final imprime cuántos logins, paquetes y golpes hizo, y avisa si el servidor dejó de aceptar
conexiones.

Cómo leer el log:

- `runtime error: ...` (UBSan) trae archivo y línea. **Cada lugar se informa una sola vez por corrida.**
- `ERROR: AddressSanitizer: ...` trae la pila completa; lo importante son las primeras líneas de `game.cpp`,
  `protocol76.cpp`, etc.
- Direcciones sin nombre: `addr2line -f -C -e yurots 0x...` dentro de la imagen.
- `failed to load external entity "data/accounts/NNN.xml"` es normal: son los logins malos de los bots.

Al terminar: `docker rm -f yurots-asan` y borrar `~/build/asan-src` y `~/build/asan-run`.

## 5. Qué encontró (nov 2026)

Cinco corridas con `--fuzz` sobre el binario con sanitizers (semillas 3, 7, 11, 17 y 19; más de 288.000
paquetes, 57.000 de ellos rotos a propósito, y 2.900 golpes al puerto) y una sobre el binario normal `-O2`
(semilla 13, 53.000 paquetes) terminan sin ningún informe ni caída después de estos arreglos:

| Dónde | Qué pasaba | Arreglo |
|---|---|---|
| `networkmessage.cpp` | **Caída remota sin login.** Un paquete más corto de lo que el código esperaba hacía leer más allá de lo recibido. Con un paquete vacío (`00 00`) mandado después de una consulta de estado (el healthcheck de Docker hace una cada 30 s), `GetRaw()` armaba un texto de largo negativo → `std::length_error` → servidor caído. Lo mismo desde adentro con la ventana de casas (opcode `0x8A`) | `canRead()`: todas las lecturas (`GetByte`, `GetU16`, `GetU32`, `GetString`, `GetRaw`, `SkipBytes`) comprueban que el dato esté dentro del paquete; si no, devuelven 0 o texto vacío |
| `game.cpp` (`checkPlayerWalk`, `playerAutoWalk`) | Un auto-walk (opcode `0x64`) sin pasos válidos hacía `pop_front()` sobre una lista vacía: memoria corrupta | Si el camino está vacío no se agenda la caminata |
| `luascript.cpp` | `g_config` (un solo estado de Lua) se lee desde el hilo de cada conexión sin candado. Con dos logins a la vez se pisaban: `datadir` volvía como `"15"` y un login bueno salía rechazado ("Please enter a valid account number and password") o, peor, podía corromper la pila de Lua. Además, cada clave que no existía dejaba un valor colgado en la pila | `luaLock` (`std::mutex`) en las lecturas de config y `lua_pop` en todos los caminos |
| `luascript.cpp` (`OpenFile`) | `/reload config` (GM) cerraba y volvía a cargar el estado de Lua mientras los hilos de las conexiones lo leían, y perdía el estado anterior | Carga el archivo en un estado nuevo y lo cambia con el candado puesto; si el archivo tiene un error queda la config anterior |
| `protocol76.cpp` (`flushOutputBuffer`) | No es un error de memoria: con un socket cortado, cada envío escribía `Player send disconnect` otra vez hasta que el hilo que lee cerraba el socket (10.201 líneas en 4 minutos de bots) | Una línea por socket (`sendFailSocket`) |
| `fileloader.cpp` / `.h` | `delete` de memoria pedida con `new[]` (al cargar `items.otb` y el mapa) | `delete[]` |
| `items.cpp` | `ItemType::blockPickupable` sin inicializar | `= false` en el constructor |
| `aac.cpp` | El account creator armaba el número de cuenta con una cuenta que desborda en 32 bits (salían números negativos o de menos de 6 cifras) y el control de "no hay números libres" nunca se cumplía | `random_range(100000, 999999)` y el control antes de guardar el número |
| `monster.cpp`, `player.cpp` | Tres cuentas con overflow de enteros (abajo) | Misma cuenta, sin overflow. **El juego no cambia** |

### Tres cuentas de azar que no hacen lo que dicen (corrección apagada por defecto)

Las tres tienen un overflow que hace que el resultado sea distinto del que el código pretende. Se midió con
el compilador del servidor (2 millones de tiradas cada una). Se dejaron **dando el mismo resultado que
antes**, ahora sin comportamiento indefinido, porque corregirlas cambia el balance del juego:

| Qué | Configurado | Lo que sale hoy | Si se corrige |
|---|---|---|---|
| **Loot y summons** (`Monster::getRandom()`): la mitad de las tiradas da un número enorme y falla siempre | 1 % · 10 % · 100 % | 0,51 % · 4,97 % · 50 % | El doble de loot en todo el servidor (y los ítems con chance 100 % caen siempre) |
| **Cambio de blanco** (`Monster::onThink`, `changetarget` del XML): la cuenta da siempre 0 | X % por think | 100 %: todo monstruo con `changetarget > 0` busca otro blanco en cada think | Los monstruos se quedan más con el mismo jugador (más fácil "tanquear" para otros) |
| **Defensa del jugador** (`Player::getDefense()`): el tope de la tirada da 0 o 1 | entre defensa/4 y defensa (defensa 150: promedio 93,8) | entre 0 y defensa/4 (defensa 150: promedio 18,7) | Escudos y skill de shielding bloquean ~5 veces más: los knights aguantan mucho más |

Cada lugar tiene un comentario `OJO:` que explica la cuenta. La versión corregida de cada una ya está en el
binario, **apagada**, y se prende con una línea en `server/YurOTS/ots/config.lua` (sin compilar):

| Línea en `config.lua` | Qué corrige |
|---|---|
| `fixlootchance = 1` | Loot y summons con la chance configurada (el doble que hoy) |
| `fixchangetarget = 1` | Cambio de blanco con el X % del XML (`changetarget` va de 0 a 10000; casi todos los monstruos tienen 200 = 2 % por think) |
| `fixshielddefense = 1` | Tirada de defensa entre defensa/4 y defensa |

Se leen al arrancar y con `/reload config` (GM). Sin la línea, o con `0`, todo sigue como siempre. Como hoy el
servidor está balanceado (drop rates, monstruos, PvP) sobre los valores reales, conviene prender de a una y
probarla jugando. Si el loot queda muy alto con `fixlootchance`, `lootmul` lo baja.

## Relacionado

- [LIMPIEZA_CODIGO_NOV2026.md](LIMPIEZA_CODIGO_NOV2026.md): limpieza del código y pendientes
- [CRASH_DIAGNOSTICS.md](CRASH_DIAGNOSTICS.md): cómo leer un crash del servidor real
- [THINKPAD_TEST_SERVER.md](THINKPAD_TEST_SERVER.md): compilar y deployar en la ThinkPad
