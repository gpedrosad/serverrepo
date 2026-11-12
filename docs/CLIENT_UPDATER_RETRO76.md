# Auto-actualización del cliente Retro76

> **Estado:** funcionando desde el 2026-11-11 (probado en macOS: un cliente con el `Tibia.spr` viejo bajó lo
> que cambió, se reinició solo y quedó con los sprites nuevos).
> **Repo cliente:** `~/apps/clienteretro` en la ThinkPad (`github.com/gpedrosad/clienteretro`, `mac/` + `windows/`).
> **Web:** contenedor `retro76-web` en la ThinkPad, http://192.168.1.17:8080.

Los jugadores descargan el cliente **una sola vez**. Cada vez que lo abren, el cliente pregunta a la web qué
archivos hay, baja solo los que cambiaron (sprites, módulos, `init.lua`, lo que sea) y sigue. Nadie tiene que
volver a descargar el zip cuando se agregan ítems o looks.

## Cómo funciona

```
Jugador abre el cliente (binario + data.zip)
  └─ init.lua: Services.updater = "http://192.168.1.17:8080/api/updater.php"
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
Después, commitear en `~/apps/clienteretro` (sprites/`init.lua` cambiados). La ThinkPad no tiene credenciales de
GitHub: el push se hace desde la Mac trayendo el commit por ssh
(`git fetch thinkpad:apps/clienteretro main` en un clon y `git push`).

Cambios en Lua del cliente (`modules/`, `init.lua`): editar **igual** en `mac/` y `windows/`, o el script se
niega a publicar.

## Probar sin tocar a los jugadores

Se probó así (nov 2026): `web/server.py` local en otro puerto (`PORT=8099 python3.11 web/server.py`; necesita
Python ≤ 3.12 por `cgi`), un cliente de prueba con `APP_NAME` distinto en su `init.lua` (otra carpeta de
usuario) y `Services.updater` apuntando al puerto local, y un `data.zip` con un `Tibia.spr` viejo. Para ver qué
hace, agregar `g_logger.info(...)` en `modules/updater/updater.lua` del zip de prueba: sale en la salida del
binario. Al terminar, borrar `~/Library/Application Support/<APP_NAME de prueba>`.

## Archivos

| Archivo | Rol |
|---------|-----|
| `clienteretro/{mac,windows}/init.lua` | `Services.updater` y servidor `192.168.1.17:7171` |
| `clienteretro/{mac,windows}/modules/updater/` | Updater de OTClientV8 (sin cambios) |
| `clienteretro/build-zips.sh` | Atajo a `publish_client.py` |
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
