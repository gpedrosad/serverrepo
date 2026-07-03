# Cliente Tibia 7.6 para YurOTS

## Recomendado en Mac: OTClientV8

Usá **otclientv8-master** (sin Wine, sin IP changer manual):

```bash
./scripts/play-yurots-client.sh
```

Lee la IP de `config.lua` y conecta a `YurOTS` en el login. Por defecto busca el cliente en `~/Downloads/otclientv8-master` (variable `OTCLIENT_DIR` para otra ruta).

En el login elegí **YurOTS**, cuenta numérica + contraseña.

## Cliente oficial parcheado (Windows / Wine)

Cliente **oficial 7.6** parcheado como `YurOTS.exe` (sin IP changer).

## Generar para compartir (Desktop + ZIP)

```bash
python3 scripts/patch-tibia760-client.py --desktop
```

Crea:

- `~/Desktop/YurOTS-Cliente-7.6/` — carpeta lista para enviar
- `~/Desktop/YurOTS-Cliente-7.6.zip` — comprimido listo para adjuntar

## Solo en el repo (desarrollo)

```bash
python3 scripts/patch-tibia760-client.py
```

Salida en `client-760/` (gitignored).

## Jugar en Mac (Wine)

```bash
./scripts/play-yurots-client.sh
```

## Requisito

Copia de Tibia 7.6 en `~/Downloads/tibia76/` con `Tibia.exe`, `Tibia.dat`, `Tibia.spr`, `Tibia.pic`.

Tras cambiar `ip` en `config.lua`, volvé a ejecutar el script con `--desktop`.

## Cursor, crosshair y marcado de tiles

El cliente local de este repo usa varias capas visuales distintas alrededor del mouse:

- `pointer`: cursor base del cliente. No usa la flecha del sistema; carga un asset propio desde [client-local/data/cursors/cursors.otml](../client-local/data/cursors/cursors.otml).
- `target`: cursor temporal para acciones `use with`, trade y algunos hotkeys/action bar.
- `crosshair`: overlay dibujado sobre el tile (`sqm`) del mapa. Sus imágenes viven en `client-local/data/images/crosshair/`.
- `highlightThingsUnderCursor`: marcado del `thing` bajo el mouse, aplicado desde `UIGameMap` con `setMarked(...)`.

Referencias de código:

- Carga de cursores custom: [client-local/modules/client_styles/styles.lua](../client-local/modules/client_styles/styles.lua)
- Opción de `crosshair`: [client-local/modules/client_options/options.lua](../client-local/modules/client_options/options.lua)
- Opción de `Highlight things under cursor`: [client-local/modules/client_options/interface.otui](../client-local/modules/client_options/interface.otui)
- Marcado runtime bajo el mouse: [client-local/modules/game_interface/widgets/uigamemap.lua](../client-local/modules/game_interface/widgets/uigamemap.lua)

### Cambio aplicado en julio 2026

Se dejó por defecto:

- `Crosshair = None`
- `Highlight things under cursor = false`

Además se agregó una migración chica en `client_options/options.lua` para que clientes que ya tuvieran esos settings guardados también los apaguen una vez en el próximo arranque.

### Qué era cada cosa visual

- El "azul en las puntas del sqm" correspondía al `crosshair` `Default`.
- El resaltado automático al pasar el mouse sobre criaturas/items/tiles era `Highlight things under cursor`.
- El cursor de mano blanca viene del asset `pointer.png`; eso es independiente del `crosshair` y del highlight.

### Cómo volver a activarlo

En `Options > Interface`:

- `Crosshair`: `None`, `Default`, `Full`
- `Highlight things under cursor`: checkbox

Si alguna vez hace falta cambiar la forma del cursor base, los assets están en `client-local/data/cursors/` y el `hot-spot` se define en `cursors.otml`.
