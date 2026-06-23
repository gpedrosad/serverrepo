# YurOTS en Docker — Guía de setup

Repositorio usado: https://github.com/divinity76/YurOTS (branch default).
Commit inspeccionado a fecha de clonado. YurOTS 0.9.4f (protocolo Tibia 7.6).

## 1. Requisitos

- macOS con Docker Desktop (probado en Apple Silicon / arm64).
- El servidor compila **en 32-bit** (`linux/386`) dentro del container, emulado
  vía QEMU. Esto es necesario porque YurOTS asume `sizeof(unsigned long) == 4`
  (modelo LLP64 de Windows/MinGW) en su serialización binaria (OTB/OTBM). En
  Linux 64-bit, `unsigned long` = 8 bytes y la carga de `items.otb` / mapa falla
  con double-free. Compilando i386 replicamos el modelo de Windows.

## 2. Estructura del proyecto

```
~/Desktop/yurots-principal/
├── Dockerfile              # i386/ubuntu:20.04 + build-essential, libxml2, lua5.1, boost-regex, zlib
├── docker-compose.yml      # servicio "yurots", puertos 7171 y 7172, bind mount de server/YurOTS
├── run.sh                  # docker compose run --rm --service-ports yurots bash
├── server/YurOTS/          # repo clonado (bind mount en /app/YurOTS)
│   └── ots/
│       ├── config.lua      # configuración del servidor (ip=127.0.0.1, port=7171)
│       ├── data/           # datos: world, items, monsters, npc, spells, etc.
│       │   └── world/test.otbm   # mapa (copia en backups/)
│       └── source/         # código C++ + Makefile generado + linux_compat.h
│           ├── Makefile    # generado a partir del .cbp de CodeBlocks
│           ├── linux_compat.h  # macros para símbolos Windows-only
│           └── yurots      # binario compilado
├── backups/
│   └── yurots-original.otbm   # copia del mapa original
└── docs/SETUP.md           # este archivo
```

## 3. Rutas clave (dentro del container)

| Concepto        | Ruta en el container            | En el host                                   |
|-----------------|---------------------------------|----------------------------------------------|
| Repo            | `/app/YurOTS`                   | `~/Desktop/yurots-principal/server/YurOTS`        |
| Carpeta server  | `/app/YurOTS/ots`               | `~/Desktop/yurots-principal/server/YurOTS/ots`    |
| Binario         | `/app/YurOTS/ots/source/yurots` | `~/Desktop/yurots-principal/server/YurOTS/ots/source/yurots` |
| Config          | `/app/YurOTS/ots/config.lua`    | `~/Desktop/yurots-principal/server/YurOTS/ots/config.lua` |
| Mapa .otbm      | `/app/YurOTS/ots/data/world/test.otbm` | `~/Desktop/yurots-principal/server/YurOTS/ots/data/world/test.otbm` |
| Makefile        | `/app/YurOTS/ots/source/Makefile` | idem host                                    |

## 4. Puertos

- **7171**: login + game (YurOTS 7.6 usa un único puerto para todo el protocolo;
  no hay `gamePort` separado). Configurado en `config.lua` con `port = "7171"`.
- **7172**: expuesto en el compose por compatibilidad futura, pero el server no
  escucha aquí en este protocolo.
- IP configurada: `ip = "127.0.0.1"` en `config.lua` (cambiado desde `"auto"`).

## 5. Build y ejecución

### Construir la imagen (solo la primera vez o tras cambiar el Dockerfile)

```bash
cd ~/Desktop/yurots-principal
docker compose build
```

### Entrar al container interactivo (compilar / correr a mano)

```bash
cd ~/Desktop/yurots-principal
./run.sh
```

`run.sh` equivale a:
```
docker compose run --rm --service-ports yurots bash
```
`--service-ports` publica 7171 y 7172 hacia el host (necesario para que el
cliente Tibia conecte a 127.0.0.1:7171).

### Compilar dentro del container

```bash
cd /app/YurOTS/ots/source
make clean && make
```

El binario queda en `/app/YurOTS/ots/source/yurots`.

### Ejecutar el servidor

El servidor busca `config.lua` y `data/` **relativos al directorio de trabajo**,
que debe ser `/app/YurOTS/ots` (no `source/`). Por eso el `working_dir` del
compose es `ots`.

```bash
cd /app/YurOTS/ots
./source/yurots
```

Salida esperada (resumen):
```
:: YurOTS 0.9.4f
:: Loading lua script config.lua... [done]
:: Loading spells.xml...            [done]
:: Loading actions.xml...           [done]
:: Loading commands.xml...          [done]
:: Loading items.otb...             [done]
:: Loading items.xml...             [done]
:: Loading guilds.xml...            [done]
:: Loading queue.xml...             [done]
:: Loading summons.xml...           [done]
:: Loading monsters.xml...          [done]
:: Loading map from: OTBM
Map size: 512x512
:: Loading npc.xml...               [done]
:: Loading houses.xml...            [done]
:: Loading pvparenas.xml...         [done]
:: Loading readables.xml...         [done]
:: Starting Server... [done]
:: YurOTS Server Running...
```

Verificar desde el host (otra terminal) que el puerto está abierto:
```bash
nc -z -w3 127.0.0.1 7171 && echo "7171 ABIERTO"
```

### Detener el servidor

`Ctrl+C` dentro del container, o `exit` para salir (el container se elimina por
`--rm`). Si lo levantaste en background con `docker compose run -d`, usa
`docker rm -f yurots-running`.

## 6. Datos / accounts

YurOTS usa **accounts en XML** (`sourcedata = "XML"` en config.lua). **No
requiere MySQL.** Las cuentas/players viven en `data/accounts/` y
`data/players/` como `.xml`. No se agregó servicio MySQL al docker-compose.

## 7. Errores encontrados y cómo se resolvieron

El repo original solo trae proyectos Dev-C++ (`.dev`) y CodeBlocks (`.cbp`) y
MSVC (`.vcproj`): **no hay Makefile**. Se generó `ots/source/Makefile` a partir
del `.cbp`, con los 48 `.cpp` (excluyendo `mdump.cpp` que es Windows-only) y
todos los defines `YUR_*`/`TLM_*`/etc. del proyecto original.

Compilando en Linux se encontraron estos problemas y se resolvieron así:

1. **`uint64_t` redefinido** (`definitions.h`): el archivo definía
   `typedef unsigned long long uint64_t;` fuera del bloque `#ifdef WIN32`,
   colisionando con `<stdint.h>` del sistema. Movido al bloque Windows.
   - `definitions.h`
2. **`memcpy` sin incluir** (`fileloader.h`): agregado `#include <cstring>`.
3. **Headers ICU de Boost.Regex requieren C++11+**: el `.cbp` usaba C++ viejo.
   Subido el estándar a `-std=gnu++14` (el código legacy tolera con
   `-fpermissive`).
4. **`_atoi64` (Windows-only)**: mapeado a `atoll` vía `-D_atoi64=atoll` en el
   Makefile (usado en `monsters.cpp` e `ioplayerxml.cpp` con `YUR_HIGH_LEVELS`).
5. **`__int64` no definido en `luascript.h`**: agregado `#include "definitions.h"`
   (que define `typedef int64_t __int64;` en el path Linux).
6. **`lua_dofile` (Lua 5.0) no existe en Lua 5.1**: mapeado a `luaL_dofile` vía
   `-Dlua_dofile=luaL_dofile` (mismo contrato: 0 = OK).
7. **`luaopen_loadlib` (Lua 5.0) no existe en Lua 5.1**: mapeado a
   `luaopen_package` vía `-Dluaopen_loadlib=luaopen_package`.
   - **Nota**: llamar a `luaopen_package` individualmente (sin `luaopen_base`
     antes) dispara `PANIC: unprotected error in call to Lua API (no calling
     environment)` en este build de lua5.1. Por eso, en `spells.cpp`, `npc.cpp`
     y `actions.cpp` se reemplazaron las 5 llamadas individuales
     (`luaopen_loadlib/base/math/string/io`) por una sola `luaL_openlibs()` (que
     abre en el orden correcto). Lo mismo se aplicó en `luascript.cpp::OpenFile`.
8. **`std::max(1LL, int*int)` ambiguo** (`protocol76.cpp`): en 64-bit `long long`
   ≠ `long` para `std::max`. Fuerzado el tipo con `std::max<long long>(...)`.
   (En i386 este fix es inocuo pero se mantiene.)
9. **`strcmp` sin incluir** (`summons.cpp`): agregado `#include <cstring>`.
10. **`return false` en función que retorna `Item*`** (`iomapotbm.cpp:409`):
    bug legacy tolerado por MSVC. Cambiado a `return NULL` (consistente con el
    resto de la función).
11. **Símbolos MinGW/Windows en `tools.cpp`**: `_timeb`, `_ftime`, `ltoa`,
    `_ultoa`, `_i64toa`, `_ui64toa` no existen en Linux. Creado
    `ots/source/linux_compat.h` con macros equivalentes (`_timeb`→`timeb`,
    `_ftime`→`ftime`, `ltoa(v,b,r)`→`sprintf`+devuelve `buf`), incluido vía
    `-include linux_compat.h` en el Makefile.
12. **Check de root** (`otserv.cpp`): `_NO_ROOT_PERMISSION_` definido
    incondicionalmente en el path Linux abortaba si se ejecuta como root. En
    Docker todo corre como root por diseño, así que se comentó el `#define`.
13. **`_HOMEDIR_CONF_`** (`otserv.cpp`): idem, definido en path Linux, hacía
    buscar `$HOME/.otserv/config.lua` (inexistente). Comentado para usar
    `config.lua` relativo al CWD.
14. **`ip = "auto"`** en `config.lua`: cambiado a `ip = "127.0.0.1"`.
15. **Double-free al cargar `items.otb`** (bug raíz de tamaño de tipos): el
    `FileLoader` usaba `sizeof(unsigned long)` para leer campos binarios de 4
    bytes del formato OTB. En Linux 64-bit, `unsigned long` = 8 → lectura
    incorrecta de `version` → path de error → `fclose(m_file)` sin setear
    `m_file = NULL` → double-free en el destructor. En vez de patchear todos los
    `unsigned long` del código de serialización, se compiló en **32-bit
    (`linux/386`)** donde `unsigned long` = 4, replicando el modelo LLP64 de
    Windows para el que fue escrito YurOTS. Esto arregla de golpe todos los
    bugs de tamaño de enteros en la carga de OTB/OTBM.

## 8. Archivos modificados del repo original

Todos los cambios están en `server/YurOTS/ots/source/` (bind mount, persistentes
en el host):

- `definitions.h` — mover typedef `uint64_t` al bloque Windows; mantener
  `XML_GCC_FREE`.
- `fileloader.h` — agregar `#include <cstring>`.
- `luascript.h` — agregar `#include "definitions.h"`.
- `luascript.cpp` — `luaL_openlibs(luaState)` tras `lua_open()` en `OpenFile`.
- `spells.cpp`, `npc.cpp`, `actions.cpp` — reemplazar las 5 `luaopen_*`
  individuales por `luaL_openlibs(luaState)`.
- `summons.cpp` — agregar `#include <cstring>`.
- `iomapotbm.cpp` — `return false` → `return NULL` (línea ~409).
- `protocol76.cpp` — `std::max(1LL, ...)` → `std::max<long long>(1LL, ...)`
  (2 sitios).
- `tools.cpp` — sin cambios directos; se cubre vía `linux_compat.h`.
- `otserv.cpp` — comentar `#define _NO_ROOT_PERMISSION_` y
  `#define _HOMEDIR_CONF_` (path Linux).
- `ots/source/Makefile` — **nuevo** (generado).
- `ots/source/linux_compat.h` — **nuevo**.
- `config.lua` — `ip = "auto"` → `ip = "127.0.0.1"`.

## 9. Siguientes pasos (no hechos todavía, según indicación)

- [ ] Editar el mapa en Remere's Map Editor (usar `backups/yurots-original.otbm`
      como referencia y `server/YurOTS/ots/data/world/test.otbm` como working
      copy). Protocolo 7.6 / OTBM.
- [ ] Cliente Tibia 7.6 apuntando a 127.0.0.1:7171.
- [ ] Sistemas custom / PvP: pendiente hasta validar el server en juego.
