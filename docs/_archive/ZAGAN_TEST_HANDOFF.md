# Zagan Test Handoff

Este documento es un handoff técnico para otra IA. Resume el trabajo ya hecho para importar 5 sprites de `/Users/gonzalo/Downloads/Zagan+Square/` como items nuevos, reales, equipables y estáticos dentro de este proyecto.

## Objetivo

Usar 5 sprites BMP del pack `Zagan+Square` como items nuevos del juego, no como decoraciones sueltas:

- visibles en cliente 7.6
- reconocidos por `items.otb`
- equipables de verdad
- visibles y usables en un entorno test de RME
- arrancables en un entorno local de cliente + Docker

## Estado actual

La parte de integración de assets ya está hecha.

- Se generaron 5 items nuevos con ids propias.
- Se creó un builder local que parchea `Tibia.dat`, `Tibia.spr` e `items.otb`.
- Se creó un cliente test aislado.
- Se creó un RME test aislado.
- Se agregó soporte en el server para cargar `items.otb/xml` alternativos por config/env.
- Se agregaron wrappers para reconstruir e iniciar el entorno test.

Lo que no quedó confirmado dentro de esta sesión:

- No quedó validado end-to-end que Docker haya arrancado el server test.
- No quedó validado end-to-end que el cliente se haya abierto correctamente.
- No quedó validado manualmente en GUI que RME muestre los items en su palette.

La última prueba de arranque fue interrumpida por el usuario y `/tmp/zagan-start.log` quedó vacío.

## Items creados

Estos ids salen de `zagan-test/manifest.json`:

- `20100` `zagan sword`
- `20101` `square shield`
- `20102` `zagan helmet`
- `20103` `square armor`
- `20104` `zagan legs`

Detalle completo:

- `20100` `zagan sword` → `clientId=5080` `spriteId=10963`
- `20101` `square shield` → `clientId=5086` `spriteId=10964`
- `20102` `zagan helmet` → `clientId=5087` `spriteId=10965`
- `20103` `square armor` → `clientId=5088` `spriteId=10966`
- `20104` `zagan legs` → `clientId=5089` `spriteId=10967`

## Cómo se modelaron

No se creó lógica nueva de equipamiento. Cada item nuevo duplica un prototipo existente en `items.otb`, cambiando `serverId`, `clientId`, `name`, `description` y el sprite en `Tibia.dat/.spr`.

Prototipos usados:

- `zagan sword` duplica `serverId 2409` `serpent sword`
- `square shield` duplica `serverId 2515` `guardian shield`
- `zagan helmet` duplica `serverId 2457` `steel helmet`
- `square armor` duplica `serverId 2476` `knight armor`
- `zagan legs` duplica `serverId 2477` `knight legs`

Eso significa que ya heredan slot y comportamiento equipable desde el OTB base.

## Archivos importantes

Builder principal:

- `scripts/build_zagan_test_assets.py`

Documentación breve existente:

- `docs/ZAGAN_TEST_ITEMS.md`

Wrappers creados:

- `scripts/install-zagan-test-env.sh`
- `scripts/play-zagan-test-client.sh`
- `scripts/open-rme-zagan-test.sh`
- `scripts/start-local-zagan-test.sh`

Assets generados:

- `zagan-test/manifest.json`
- `zagan-test/previews/`
- `zagan-test/client-things/760/Tibia.dat`
- `zagan-test/client-things/760/Tibia.spr`
- `zagan-test/server-items/items.otb`
- `zagan-test/server-items/items.xml`

Instalación local test:

- `client-local-zagan-test/`
- `rme-client-760-zagan-test/`
- `rme-zagan-test-root/`
- `server/YurOTS/ots/data/items/items-zagan-test.otb`
- `server/YurOTS/ots/data/items/items-zagan-test.xml`

## Cambios de runtime ya hechos

### Server

Se tocó `server/YurOTS/ots/source/otserv.cpp` para que el server pueda leer rutas alternativas:

- config Lua: `items_otb`, `items_xml`
- variables de entorno: `YUROTS_ITEMS_OTB`, `YUROTS_ITEMS_XML`

Fallback actual:

- `data/items/items.otb`
- `data/items/items.xml`

### Docker

Se tocó `docker-compose.yml` para propagar:

- `YUROTS_ITEMS_OTB`
- `YUROTS_ITEMS_XML`

### RME

Se tocó `scripts/open-rme.sh` para aceptar:

- `RME_CLIENT_DIR_OVERRIDE`
- `MAP_OVERRIDE`

Y `scripts/setup-rme-config.sh` ya acepta:

- `RME_CLIENT_DIR_OVERRIDE`

## Qué hace cada script

### `scripts/install-zagan-test-env.sh`

Reconstruye e instala el pack test.

Hace esto:

1. Ejecuta `scripts/build_zagan_test_assets.py`
2. Copia `Tibia.dat/.spr` test a `client-local-zagan-test`
3. Copia `Tibia.dat/.spr` test a `rme-client-760-zagan-test`
4. Copia `items.otb/xml` test al server
5. Crea/actualiza `rme-zagan-test-root`
6. Copia `items.otb` test a `rme-zagan-test-root/data/760/items.otb`

### `scripts/play-zagan-test-client.sh`

Reconstruye el entorno test y abre `client-local-zagan-test`.

### `scripts/open-rme-zagan-test.sh`

Reconstruye el entorno test y abre un RME aislado apuntando a:

- `RME_ROOT=$ROOT/rme-zagan-test-root`
- `RME_BIN=$RME_ROOT/build/rme`
- `RME_CLIENT_DIR_OVERRIDE=$ROOT/rme-client-760-zagan-test`

Si existe, usa este mapa por defecto:

- `server/YurOTS/ots/data/world/test-rme.otbm`

Si no existe, cae al default de `scripts/open-rme.sh`:

- `server/YurOTS/ots/data/world/test.otbm`

### `scripts/start-local-zagan-test.sh`

Reconstruye el entorno test, exporta:

- `OTCLIENT_DIR=$ROOT/client-local-zagan-test`
- `YUROTS_ITEMS_OTB=data/items/items-zagan-test.otb`
- `YUROTS_ITEMS_XML=data/items/items-zagan-test.xml`

y luego delega en:

- `scripts/start-local.sh`

Eso debería:

1. fijar IP `127.0.0.1` en `server/YurOTS/ots/config.lua`
2. levantar Docker
3. recompilar el server dentro del contenedor
4. reiniciar `yurots`
5. esperar healthcheck
6. abrir el cliente test

## Dependencias implícitas

Este flujo asume que existen:

- `client-local/`
- `~/dev/rme/build/rme`
- `~/dev/rme/data/760/`
- `server/YurOTS/...`
- el pack fuente `/Users/gonzalo/Downloads/Zagan+Square/`

También asume que `python3` y Pillow están disponibles para `scripts/build_zagan_test_assets.py`.

## Requisitos de la imagen fuente

Este pipeline actual sirve para items estáticos simples de cliente 7.6. No está pensado para outfits, criaturas, animaciones ni objetos multi-tile.

La imagen fuente debería cumplir esto:

- tamaño exacto `32x32`
- idealmente formato `BMP`
- un solo sprite por archivo
- fondo magenta puro `RGB 255,0,255` si se quiere usar color key clásico
- o transparencia real, pero sin semitransparencias
- sprite ya centrado y listo visualmente dentro del cuadro `32x32`

Notas importantes del builder:

- `scripts/build_zagan_test_assets.py` rechaza cualquier imagen que no sea `32x32`
- el loader convierte la imagen a `RGBA`
- cualquier pixel exactamente igual a magenta `255,0,255,255` pasa a transparente
- el encoder de `SPR` solo diferencia entre pixel visible y pixel invisible
- la alpha parcial no se preserva como tal, así que conviene usar solo opaco o transparente

Requisitos del item destino:

- el item nuevo hereda el comportamiento de un prototipo existente
- el prototipo elegido debe ser un item simple de `1` sprite
- el script hoy aborta si el prototipo tiene más de un sprite

En otras palabras:

- si querés un casco nuevo, duplicá un casco simple
- si querés una sword nueva, duplicá una sword simple
- no conviene usar como prototipo un item animado o compuesto

## Cómo crear un sprite nuevo desde una imagen

### Paso 1. Preparar la imagen

Crear o editar la imagen con estas reglas:

1. dejarla en `32x32`
2. limpiar el fondo para que sea transparente o magenta puro
3. evitar sombras suaves con alpha parcial
4. dejar el sprite ya alineado como debería verse en inventario/mapa

Si la imagen original viene más grande:

1. recortarla
2. escalarla manualmente
3. revisar pixel-art a mano si hace falta
4. exportarla final en `32x32`

### Paso 2. Guardar el archivo fuente

Guardar el archivo en:

- `/Users/gonzalo/Downloads/Zagan+Square/`

El builder actual usa esa carpeta fija como `SOURCE_DIR`.

Si se quiere usar otra carpeta, hay que editar:

- `SOURCE_DIR` en `scripts/build_zagan_test_assets.py`

### Paso 3. Elegir el prototipo correcto

Buscar un item base que ya tenga el comportamiento deseado:

- sword para armas
- shield para escudos
- helmet para cascos
- armor para chest armor
- legs para piernas
- boots para botas
- amulet/ring si más adelante se quiere slot accesorio

Regla práctica:

- elegir un prototipo con el mismo slot y comportamiento que el item nuevo

### Paso 4. Declarar el item en `ITEM_SPECS`

Editar `scripts/build_zagan_test_assets.py` y agregar o reemplazar una entrada en `ITEM_SPECS`.

Ejemplo:

```python
ItemSpec(
    bmp_name="mi_item.bmp",
    prototype_server_id=2409,
    item_name="my custom sword",
    description="A custom sword imported from an image.",
),
```

Qué significa cada campo:

- `bmp_name`: nombre exacto del archivo dentro de `SOURCE_DIR`
- `prototype_server_id`: item real del server que se va a duplicar
- `item_name`: nombre final del item
- `description`: descripción final del item en OTB

### Paso 5. Reconstruir el pack

Desde la raíz del repo:

```bash
./scripts/install-zagan-test-env.sh
```

Eso regenera:

- `Tibia.dat`
- `Tibia.spr`
- `items.otb`
- previews `.png`
- `manifest.json`

### Paso 6. Validar el resultado generado

Revisar:

- `zagan-test/previews/`
- `zagan-test/manifest.json`

Objetivo:

- confirmar que el preview se vea bien
- confirmar que recibió `serverId`, `clientId` y `spriteId`
- confirmar que el nombre final quedó correcto

### Paso 7. Probarlo en cliente/RME/server

Cliente test:

```bash
./scripts/play-zagan-test-client.sh
```

RME test:

```bash
./scripts/open-rme-zagan-test.sh
```

Server + cliente:

```bash
./scripts/start-local-zagan-test.sh
```

## Cómo extender el pipeline para más sprites

Hoy el builder está hardcodeado para 5 items en `ITEM_SPECS`.

Para agregar más:

1. sumar nuevas entradas a `ITEM_SPECS`
2. asegurarse de que cada `bmp_name` exista en `SOURCE_DIR`
3. elegir un `prototype_server_id` correcto
4. volver a correr `./scripts/install-zagan-test-env.sh`

Lo que el builder hace automáticamente:

- toma el siguiente `serverId` disponible empezando en `20100`
- reutiliza `clientId` 5080/5086-5089 dentro del rango ya cargado por OTClient; no toca `item_count`
- en el OTB test elimina los items originales que usaban esos `clientId`
- toma el siguiente `spriteId` disponible en `SPR`
- genera preview `.png`
- duplica el prototipo en `items.otb`
- actualiza `manifest.json`

## Limitaciones actuales del pipeline

- solo items estáticos simples
- solo sprites `32x32`
- solo un sprite por item nuevo
- no maneja animaciones
- no maneja objetos de varios tiles
- no maneja outfits
- no maneja criaturas
- no agrega lógica gameplay nueva aparte de la heredada del prototipo

## Cómo reconstruir todo desde cero

Desde la raíz del repo:

```bash
./scripts/install-zagan-test-env.sh
```

## Cómo abrir el cliente test

```bash
./scripts/play-zagan-test-client.sh
```

## Cómo abrir el RME test

```bash
./scripts/open-rme-zagan-test.sh
```

## Cómo levantar server test + cliente

```bash
./scripts/start-local-zagan-test.sh
```

## Cómo verificar rápido

### Ver ids y mapping

```bash
cat zagan-test/manifest.json
```

### Ver previews

```bash
ls zagan-test/previews
```

### Confirmar que el server test está instalado

```bash
ls server/YurOTS/ots/data/items/items-zagan-test.otb
ls server/YurOTS/ots/data/items/items-zagan-test.xml
```

### Confirmar que RME test usa el OTB test

```bash
cmp -s zagan-test/server-items/items.otb rme-zagan-test-root/data/760/items.otb && echo OK
```

## Riesgos / notas para otra IA

- No tocar `items.otb` base manualmente si no hace falta.
- Para seguir agregando sprites, reutilizar `scripts/build_zagan_test_assets.py`.
- Los items nuevos reemplazan sprites/OTB de ids de bajo uso (`5080`, `5086-5089`) para no romper el `.dat` ni desplazar outfits.
- Los ids `20001..20099` no convienen en este server porque hay una remap especial; por eso los nuevos empiezan en `20100`.
- Si Docker levanta pero el server no reconoce los items, lo primero a verificar es que el binario dentro del contenedor haya sido recompilado después del cambio en `otserv.cpp`.
- Si RME muestra los sprites pero no los clasifica bien, revisar que `rme-zagan-test-root/data/760/items.otb` sea exactamente el test OTB.
- Si el cliente abre pero el server rechaza los items, revisar que el server haya cargado `items-zagan-test.otb` y no el OTB base.

## Siguiente paso recomendado

La siguiente IA debería hacer esta validación end-to-end:

1. correr `./scripts/start-local-zagan-test.sh`
2. confirmar que Docker levanta `yurots`
3. abrir el cliente y loguear
4. crear/spawnear los ids `20100..20104`
5. confirmar equipamiento real en juego
6. abrir `./scripts/open-rme-zagan-test.sh`
7. confirmar que RME ve los 5 items nuevos

## Resumen corto

La importación técnica ya está hecha. Lo pendiente no es modelado de datos sino validación en runtime.
