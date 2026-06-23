# Remere's Map Editor — assets 7.6

YurOTS usa mapa **OTBM 7.6**. RME ([hampusborgos/rme](https://github.com/hampusborgos/rme)) necesita:

- `Tibia.dat` (metadata)
- `Tibia.spr` (sprites)

Esos archivos **no van en el repo del server**. Se copian desde **otclientv8-master** con el script incluido.

## Arranque rápido (recomendado)

```bash
~/Desktop/yurots-principal/scripts/open-rme.sh
```

Eso hace todo solo:

1. Copia `Tibia.dat` / `Tibia.spr` a `rme-client-760/`
2. Escribe `rme.cfg` con la ruta del client 7.6
3. Abre RME con `test.otbm`

Requisito: RME compilado en `~/dev/rme/build/rme` (ver [Compiling on macOS](https://github.com/hampusborgos/rme/wiki/Compiling-on-macOS)).

## 1. Copiar assets (una vez)

```bash
cd ~/Desktop/yurots-principal
./scripts/setup-rme-client.sh
```

Origen:

```
~/Downloads/otclientv8-master/data/things/760/Tibia.dat
~/Downloads/otclientv8-master/data/things/760/Tibia.spr
```

Destino:

```
~/Desktop/yurots-principal/rme-client-760/
```

## 2. Config automática (sin Preferencias)

RME 3.x **no tiene Edit → Preferences** mientras el diálogo de bienvenida está abierto (el menú entero queda deshabilitado). Las preferencias están en el botón **Preferences** del welcome dialog.

Para evitar configurar a mano:

```bash
./scripts/setup-rme-config.sh
```

Escribe:

| Archivo | Qué contiene |
|---------|----------------|
| `~/Library/Preferences/.rme/rme.cfg` | Config global |
| `~/dev/rme/build/rme.cfg` | Config local junto al binario |

Claves importantes:

- `ASSETS_DATA_DIRS` → carpeta con `Tibia.dat` y `Tibia.spr`
- `DEFAULT_CLIENT_VERSION=3` → client 7.6
- `CHECK_SIGNATURES=0` → necesario con assets de OTClient V8

## 3. Abrir el mapa de YurOTS

Mapa:

```
~/Desktop/yurots-principal/server/YurOTS/ots/data/world/test.otbm
```

Si pide **items.otb**:

```
~/Desktop/yurots-principal/server/YurOTS/ots/data/items/items.otb
```

## 4. Compilar RME (si no lo tenés)

Según el repo oficial:

```bash
brew install git cmake wxmac boost libarchive vcpkg pkg-config
git clone https://github.com/hampusborgos/rme.git ~/dev/rme
cd ~/dev/rme && mkdir build && cd build
cmake .. && make -j4
./rme
```

Al compilar, el binario queda en `build/rme` y busca `data/` en el directorio padre (`../data`).

## 5. Pantalla negra al abrir test.otbm

Causa habitual en Mac: RME compilado contra **OpenGL de XQuartz** (`/opt/X11/lib/libGL`) en vez del OpenGL nativo. El minimap puede verse, pero el panel central queda negro.

Recompilá así (una vez):

```bash
~/Desktop/yurots-principal/scripts/rebuild-rme-macos.sh
~/Desktop/yurots-principal/scripts/open-rme.sh
```

Requisitos: `brew install wxwidgets` y vcpkg en `~/dev/vcpkg`.

Si el mapa abre pero no ves la ciudad: **Ctrl+G** → posición `140`, `50`, `7` (piso 7).

## 6. Si vuelve el error "Could not locate metadata and/or sprite files"

```bash
ls -la ~/Desktop/yurots-principal/rme-client-760/
./scripts/setup-rme-client.sh
./scripts/setup-rme-config.sh
```

Reiniciá RME después de cambiar la config.

## 7. Monstruos custom (Trainer Monk, etc.)

Los monstruos propios de YurOTS **no están en la lista estándar de Tibia 7.6**. RME los carga de dos formas:

1. **`setup-rme-creatures.sh`** — escribe definiciones en `creatures.xml` (user data).
2. **`rme-extensions/yurots-creatures.xml`** — extensión con tilesets visibles en la paleta.

Al abrir RME con `open-rme.sh`, ambos se instalan solos. **Reiniciá RME** si ya lo tenías abierto.

### Dónde encontrarlos en RME

Paleta **Creatures** → desplegable de categorías:

| Categoría | Monstruos |
|-----------|-----------|
| **YurOTS Training** | Trainer Monk, Elite Trainer Monk |
| **YurOTS Custom** | Bone Beast, Murius, Old Widow |
| **Others** | Cualquier otro importado manualmente |

Alternativa manual: **File → Import → Import Monsters/NPCs** y elegir el `.xml` del monstruo (aparece en **Others**).

Referencia: [OTLand — custom monsters in RME](https://otland.net/threads/put-custom-monsters-in-rme-map-editor.142548/).

## 8. Notas

- Los assets vienen de `data/things/760/` del OTClient V8; compatibles con RME 7.60.
- `rme-client-760/` está incluido en el repo principal (`Tibia.dat` + `Tibia.spr`).
- Backup del mapa: `backups/yurots-original.otbm`
