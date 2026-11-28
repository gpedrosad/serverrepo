# Auto-actualización del cliente Retro76

> **Estado:** funcionando desde el 2026-11-11 (probado en macOS: un cliente con el `Tibia.spr` viejo bajó lo
> que cambió, se reinició solo y quedó con los sprites nuevos).
> **Repo cliente:** `~/apps/clienteretro` en la ThinkPad (`github.com/gpedrosad/clienteretro`, `mac/` + `windows/`).
> **Web:** contenedor `retro76-web` en el VPS, detrás de Caddy: el updater es `http://retro76.cl/api/updater.php` (HTTP plano a
> propósito) desde el 27 nov 2026; antes, la ThinkPad. Ver [VPS_VULTR.md](systems/VPS_VULTR.md#cliente).

Los jugadores descargan el cliente **una sola vez**. Cada vez que lo abren, el cliente pregunta a la web qué
archivos hay, baja solo los que cambiaron (sprites, módulos, `init.lua`, lo que sea) y sigue. Nadie tiene que
volver a descargar el zip cuando se agregan ítems o looks.

Desde el 19 nov 2026 también pregunta **al apretar Login**, así no hay que cerrar el cliente para tener lo último
(ver [Al apretar Login](#al-apretar-login)).

## Cómo funciona

```
Jugador abre el cliente (binario + data.zip)
  └─ init.lua: Services.updater = "http://retro76.cl/api/updater.php"
       └─ POST → web/server.py → web/client_updater.py
            responde {url, files: {"/ruta": crc32}, keepFiles: true} con todo web/updater/files/
       └─ compara con los CRC de su data.zip; baja los distintos desde url + ruta
       └─ arma un data.zip nuevo en su carpeta de usuario y lo usa desde ahí
          (macOS: ~/Library/Application Support/retro_oficial/data.zip)
       └─ si cambió init.lua / corelib / updater / un .otmod se reinicia solo; si no, recarga los módulos
```

- El updater de OTClientV8 **solo funciona si el cliente corre desde un `data.zip`**
  (`g_resources.isLoadedFromArchive()`). Por eso el zip de descarga trae binario + lanzador + `LEEME.txt` +
  `data.zip`, y no la carpeta suelta. El repo `clienteretro` sigue con los archivos sueltos (para editarlos);
  el `data.zip` se arma al publicar.
- El `data.zip` de la carpeta de usuario tiene prioridad sobre el de la carpeta del cliente (el binario lo busca
  primero ahí). Si alguien vuelve a descargar el zip, el updater lo pone al día igual.
- **CRC:** 8 dígitos hex en minúscula, con ceros a la izquierda (`0660c1c3`). Es lo que devuelven
  `g_resources.filesChecksums()` y `g_crypt.crc32` en el binario 3.2; sin los ceros falla con
  `Invalid checksum ... Should be 660c1c3, is: 0660c1c3`.
- `keepFiles: true`: el cliente conserva los archivos que ya no estén publicados (borrar un archivo no lo quita
  de los clientes; no hace falta).
- La URL de descarga se arma con el `Host` del pedido (`UPDATER_FILES_URL` vacío). Si algún día la web va detrás
  de un proxy o dominio, definir `UPDATER_FILES_URL` en el contenedor.
- Si la web no responde, el cliente muestra "Updater Error"; al aceptar, carga normal y se actualiza la próxima vez.
- El binario no se actualiza (en macOS rompería la firma/Gatekeeper). Un binario nuevo = descarga nueva.

## Al apretar Login

`EnterGame.doLogin` (`modules/client_entergame/entergame.lua`) llama a `Updater.checkBeforeLogin` antes de
conectar (`modules/updater/updater.lua`); los dos con un comentario `Retro76`:

| La web dice | Qué hace el cliente |
|-------------|---------------------|
| Nada cambió | Sigue el login enseguida (en la LAN tarda milisegundos; se ve "Checking for updates..." un instante) |
| Cambiaron sprites (`data/things/`) o el minimapa (`data/minimap.otmm`) | Abre la ventana del updater, los baja, rearma el `data.zip`, recarga los sprites (`modules.game_things.load()`) y **sigue el login solo**, con la misma cuenta. No se reinicia |
| Cambió código del cliente (módulos, `init.lua`, imágenes, lo demás) | Los baja y **se reinicia solo** (no se puede recargar con el juego cargado); al volver muestra "Client updated ... Press Login again" (setting `updated-at-login`) |
| No responde en 5 s (`Updater.loginTimeout`) o da error | Entra sin actualizar y lo anota en el log |

- "Cancel" en el cartel de "Checking for updates..." vuelve a la pantalla de login.
- Si se aprieta Login (o Enter) de nuevo mientras revisa o baja, ese segundo intento se ignora.
- Si falla una descarga, el "Updater Error" deja entrar con los archivos que tenía.
- Lo normal (ítems, looks, mapa) es lo primero: sprites y minimapa sin reiniciar.
- **La primera vez** cada cliente tiene que tomar este cambio al abrirse (como cualquier cambio del updater, se
  reinicia una vez solo). Desde ahí ya actualiza en el login.

Probado el 19 nov 2026 con el cliente de Mac real, una carpeta de usuario aparte y una web de prueba en
`127.0.0.1:8099`:
- Sin cambios: conecta directo.
- Cambiaron `Tibia.dat`, `Tibia.spr` y `minimap.otmm` con el cliente abierto: al apretar Login bajó los 3, los
  sprites pasaron de 13984 a 13888 (los servidos) sin reiniciar y siguió conectando solo.
- **Sin probar:** el reinicio cuando cambia un módulo. Es el mismo reinicio de siempre al abrir el cliente; lo
  nuevo es solo el aviso.

## App de Mac (`Retro76.app`)

Desde nov 2026 el zip de Mac trae `Retro76.app` (con ícono propio) en vez de `otclient_mac` +
`Iniciar Cliente.command` sueltos:

```
Retro76-Mac/
├── LEEME.txt
└── Retro76.app/Contents/
    ├── Info.plist            ← clienteretro/mac/Retro76.app (va en git)
    ├── MacOS/Retro76         ← lanzador bash (va en git)
    └── Resources/
        ├── Retro76.icns      ← scripts/client-rme/make_mac_icon.py (va en git)
        ├── otclient_mac      ← lo agrega publish_client.py
        └── data.zip          ← lo agrega publish_client.py
```

- El lanzador (`MacOS/Retro76`, bash) abre XQuartz, busca el `DISPLAY`, quita la cuarentena y corre `otclient_mac`
  **desde `Contents/Resources`** (el binario busca `data.zip` en la carpeta actual). Desde el 27 nov 2026
  (`clienteretro` `fbc2268`) además hace solo los dos pasos que antes eran a mano, con mensajes en español,
  portugués o inglés según el idioma del Mac:
  - **Moverse a Aplicaciones.** Una app descargada y sin mover la corre macOS desde una copia de solo lectura
    (`/private/var/.../AppTranslocation/`), y desde ahí no se puede quitar la cuarentena. El lanzador lo detecta, saca
    la ruta real con `security translocate-original-path`, pregunta y la mueve a `/Applications` (o a
    `~/Applications` si no puede), reemplazando una versión anterior, y se vuelve a abrir. Si no puede, pide
    arrastrarla a mano como antes. El updater no se ve afectado: escribe en `~/Library/Application Support/retro_oficial/`.
  - **Instalar XQuartz.** Si falta `/opt/X11/lib/libX11.6.dylib` (el binario está enlazado contra ella), pregunta,
    baja el instalador oficial `XQuartz-2.8.6.pkg` de GitHub (~120 MB, a `~/Library/Caches/Retro76/`), comprueba
    su **SHA-256** (`9ac35a50…`, el mismo que publica GitHub; firmado y notarizado por XQuartz), lo abre, espera
    hasta 30 min a que termine, carga `org.xquartz.startx` para no tener que reiniciar la sesión y abre el juego.
    Si la descarga falla o el hash no coincide, no abre nada y manda a xquartz.org.
  - Probar sin instalar nada: `RETRO76_DRY=1 RETRO76_YES=1` (y `RETRO76_X11LIB=/no/existe` para simular que falta
    XQuartz). Para cambiar de versión de XQuartz: actualizar `XQ_VERSION` y `XQ_SHA256` juntos.
  - **Sin probar en un Mac real sin XQuartz:** el instalador y el traslado se probaron por partes (descarga, hash,
    caché y mover con carpetas de prueba), no de punta a punta.
- La app no está firmada: la primera vez hay que abrirla con clic derecho → Abrir (o "Abrir igualmente" en
  Privacidad y seguridad). Igual que el `.command` de antes.
- `clienteretro/mac/` conserva `otclient_mac` e `Iniciar Cliente.command` para jugar desde el repo; la
  `Retro76.app` del repo no tiene binario ni datos (los pone `publish_client.py` en el zip).
- Ícono: Crown Shield sobre Magic Sword, sacados del propio `Tibia.spr`, en los colores de la web.
  `make_mac_icon.py --window-icon` escribe el mismo dibujo en 64x64 como `data/images/clienticon.png`, que es
  el ícono de la ventana del cliente (Mac y Windows; llega a todos por el updater).

## Publicar un cambio (sprites, módulos, init.lua)

En la ThinkPad, con `serverrepo` ya en el commit nuevo:

```bash
ssh thinkpad 'cd ~/apps/serverrepo && python3 scripts/client-rme/publish_client.py'
# o, desde el repo del cliente: ~/apps/clienteretro/build-zips.sh
```

El script (`scripts/client-rme/publish_client.py`):

1. copia `Tibia.dat` / `Tibia.spr` de `devtools/rme/rme-client-760` a `mac/` y `windows/` del cliente
   (`--no-sync` para saltearlo);
2. comprueba que `mac/` y `windows/` tengan los mismos datos (solo cambian binarios, lanzadores y LEEME);
3. reemplaza `web/updater/files/` con esos datos (no va a git);
4. arma `web/downloads/Retro76-Mac.zip` y `Retro76-Windows.zip` para quien instala por primera vez.

`--dry-run` muestra qué archivos cambiarían. No hace falta reiniciar la web: lee la carpeta en cada pedido.
Después, commitear en `~/apps/clienteretro` (sprites/`init.lua` cambiados) y `git push origin main` desde la
ThinkPad: desde nov 2026 el repo pushea por SSH con su propio deploy key (`~/.ssh/github_clienteretro`, con
escritura; `core.sshCommand` y `pushurl` en la config local del repo). Cada deploy key sirve para un solo
repo: `ssh -i ~/.ssh/github_clienteretro -T git@github.com` tiene que decir `Hi gpedrosad/clienteretro!`.

Cambios en Lua del cliente (`modules/`, `init.lua`): editar **igual** en `mac/` y `windows/`, o el script se
niega a publicar.

## Probar sin tocar a los jugadores

Se probó así (nov 2026): `web/server.py` local en otro puerto (`PORT=8099 python3.11 web/server.py`; necesita
Python ≤ 3.12 por `cgi`; alcanza también un servidor chico que use `build_updater_response(url, root)` de
`web/client_updater.py` con otra carpeta), un cliente de prueba con `APP_NAME` distinto en su `init.lua` (otra carpeta de
usuario) y `Services.updater` apuntando al puerto local, y un `data.zip` con un `Tibia.spr` viejo. Para ver qué
hace, agregar `g_logger.info(...)` en `modules/updater/updater.lua` del zip de prueba: sale en la salida del
binario. Al terminar, borrar `~/Library/Application Support/<APP_NAME de prueba>`.

Para probar el login sin tocar nada: en el `init.lua` de prueba, al final de `loadModules()`, programar
`EnterGame.doLogin("test", "test")` con `scheduleEvent` contra un servidor que no existe (`127.0.0.1:7999`) y
loguear `g_sprites.getSpritesCount()`. Ojo:
- **La ventana de prueba le roba el foco al cliente con el que se está jugando** (los Enter van a la de prueba).
  Avisar antes.
- No abrir XQuartz desde el script (`open -a XQuartz`) si ya está abierto: el cliente de prueba se cerró solo.
- `Xvfb` de XQuartz no sirve para correrlo sin ventana: no tiene GLX (`Couldn't choose RGBA, double buffered
  fbconfig`).

## Archivos

| Archivo | Rol |
|---------|-----|
| `clienteretro/{mac,windows}/init.lua` | `Services.updater` y servidor `192.168.1.17:7171` |
| `clienteretro/{mac,windows}/modules/updater/` | Updater de OTClientV8 + `Updater.checkBeforeLogin` (revisar al apretar Login) |
| `clienteretro/{mac,windows}/modules/client_entergame/entergame.lua` | `doLogin` pasa por `checkBeforeLogin` antes de conectar |
| `clienteretro/build-zips.sh` | Atajo a `publish_client.py` |
| `clienteretro/mac/Retro76.app/` | `Info.plist`, lanzador e ícono de la app de Mac |
| `scripts/client-rme/make_mac_icon.py` | Genera `Retro76.icns` y `clienticon.png` |
| `scripts/client-rme/publish_client.py` | Publica el cliente y arma los zips |
| `web/client_updater.py` | Manifest con los CRC |
| `web/server.py` | `/api/updater.php`, `/updater/files/…`, `/downloads/…` |
| `web/updater/files/` | Cliente publicado (no va a git) |
| `web/downloads/Retro76-*.zip` | Descarga completa (no va a git) |

## Relacionado

- [CLIENT.md](./CLIENT.md): cliente local de desarrollo
- [systems/THINKPAD_TEST_SERVER.md](./systems/THINKPAD_TEST_SERVER.md): deploy en la ThinkPad
- [items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md](./items-and-map/IMPORTAR_ITEM_DE_OTRA_VERSION.md): ítems nuevos
  (después de cambiar el `.dat`/`.spr`, publicar el cliente)
