# Mapear con código — islas procedurales en OTBM

Guía de cómo generar terreno en el mapa de YurOTS **sin pintar tile por tile en RME**, usando un script Python que escribe directamente en `test.otbm`.

Relacionado:

- [docs/CAMBIAR-MAPA.md](CAMBIAR-MAPA.md) — flujo RME → servidor → deploy
- [docs/RME_SETUP.md](RME_SETUP.md) — abrir Remere's Map Editor
- `scripts/generate-island.py` — generador de islas
- [MAPEAR_LABERINTO.md](MAPEAR_LABERINTO.md) — laberinto 2 sqm con suelo 406 (`generate-maze.py`)
- `scripts/sync-houses-from-rme.py` — casas (no aplica a islas vacías)

---

## Resumen

| Qué hace el script | Qué **no** hace |
|--------------------|-----------------|
| Crea suelo (agua, arena, tierra, pasto) en zona vacía | No coloca monstruos |
| Inserta nodos OTBM en el mapa existente | No modifica tiles ya ocupados |
| Escribe un JSON con centro y bounds para spawns | No exporta `test-spawn.xml` solo |
| Hace backup la primera vez (`test.otbm.bak`) | No reemplaza el mapa entero |

**Flujo recomendado:**

```
generate-island.py  →  reiniciar servidor  →  RME (spawns/decoración)  →  exportar test-spawn.xml
```

---

## Contexto: por qué no es “solo RME”

YurOTS carga el mundo desde un archivo **OTBM** binario (`server/YurOTS/ots/data/world/test.otbm`). RME es el editor visual estándar, pero el formato OTBM también se puede **leer y parchear con código**.

En este repo ya existía lógica OTBM en Python:

- `scripts/sync-houses-with-map.py` — lee tiles del mapa para validar casas
- `scripts/sync-houses-from-rme.py` — parchea nodos `HOUSETILE` → `TILE`

El generador de islas reutiliza el mismo modelo mental: **recorrer el árbol de nodos OTBM, insertar tiles nuevos, no tocar el resto del mapa**.

---

## Cómo funciona OTBM (lo mínimo)

El servidor (`server/YurOTS/ots/source/iomapotbm.cpp`) interpreta el mapa como un árbol de nodos:

```
ROOT (OTBM_ROOTV1)
└── MAP_DATA (OTBM_MAP_DATA)
    ├── TILE_AREA (base x, y, z)
    │   ├── TILE (offset x, y + atributos)
    │   │   └── ITEM (items encima del suelo)
    │   └── TILE ...
    └── TILE_AREA ...
```

Constantes usadas por el script:

| Byte / tipo | Valor | Significado |
|-------------|------:|-------------|
| `NODE_START` | `0xFE` | Inicio de nodo |
| `NODE_END` | `0xFF` | Fin de nodo |
| `ESCAPE_CHAR` | `0xFD` | Escape en props |
| `OTBM_TILE_AREA` | `4` | Bloque de tiles |
| `OTBM_TILE` | `5` | Un tile |
| `OTBM_ATTR_ITEM` | `9` | Ground o item (ushort id) |

Cada **tile** guarda el suelo como el primer `OTBM_ATTR_ITEM` con el **server item id** del ground (ej. mar = `4608`).

Los offsets dentro de un `TILE_AREA` son **bytes** (`0–255`). Por eso el script agrupa tiles en bloques de hasta 256×256 respecto a una base `(base_x, base_y, z)`.

---

## Algoritmo del generador de islas

### 1. Elegir zona vacía

El mapa YurOTS es 512×512 pero el terreno jugable ocupa aprox. `x: 20–300`, `y: 2–246`. Hay mucho espacio vacío (sin nodos OTBM) hacia el sureste.

La isla de ejemplo se colocó en **`350, 180, 7`** porque:

- No colisiona con ciudad, casas ni cuevas existentes
- Cabe entera en un solo `TILE_AREA` (radio 14 + margen de agua)

El script **rechaza** generar si algún tile del área ya existe en el OTBM.

### 2. Forma procedural

Para cada celda en un cuadrado alrededor del centro:

1. Calcula distancia normalizada al centro (`dist = sqrt(dx²+dy²) / radius`)
2. Añade “wobble” con `sin/cos` para bordes menos circulares
3. Asigna suelo según anillos:

| Condición `dist` | Suelo | Server id | Rol |
|------------------|-------|----------:|-----|
| `> 1.05` | Mar | `4608` | Agua alrededor |
| `> 0.92` | Costa | `4526` | Arena/orilla (mismo id que costas del mapa actual) |
| `> 0.78` | Tierra | `231` | Transición |
| `≤ 0.78` | Pasto | `405`, `598`, `407` | Interior (aleatorio con `--seed`) |
| `> 1.18` | — | — | No se escribe tile (void) |

Los ids se eligieron **muestreando el `test.otbm` existente** (qué grounds aparecen junto al agua `4608`), no desde memoria genérica de Tibia.

### 3. Codificar nodos OTBM

Por cada tile nuevo:

```
FE 05                    # TILE
  [x_off][y_off]         # offset respecto al área
  09 [ground_id LE uint16] # OTBM_ATTR_ITEM
FF
```

Los nodos se agrupan en uno o más `TILE_AREA` y se serializan en binario con escape de `FE`/`FF`/`FD` en las props.

### 4. Insertar en el mapa

En lugar de reescribir el OTBM completo (~1 MB):

1. Parsea el body (después de los 4 bytes de versión)
2. Localiza el nodo `MAP_DATA` (tipo `2`)
3. Inserta los nuevos `TILE_AREA` **justo antes** del `NODE_END` que cierra `MAP_DATA`
4. Escribe el archivo

Esto preserva casas, items, depots y el resto del mundo intactos.

### 5. Manifiesto JSON

Tras generar, escribe `server/YurOTS/ots/data/world/generated-island.json` con:

- Centro y bounds de la isla
- Conteo de tiles (tierra / agua)
- Centro sugerido para spawn
- Fragmento XML listo para pegar en `test-spawn.xml`

---

## Uso

### Generar isla (defaults)

```bash
python3 scripts/generate-island.py
docker compose restart yurots
```

Defaults: centro `(350, 180, 7)`, radio `14`, semilla `42`.

### Simular sin escribir

```bash
python3 scripts/generate-island.py --dry-run
```

### Parámetros

| Flag | Default | Descripción |
|------|---------|-------------|
| `--center-x` | `350` | Centro X |
| `--center-y` | `180` | Centro Y |
| `--z` | `7` | Piso |
| `--radius` | `14` | Radio aproximado en tiles |
| `--seed` | `42` | Forma del borde y variación de pasto |
| `--map` | `test.otbm` | OTBM a parchear |
| `--manifest` | `generated-island.json` | Salida JSON |
| `--dry-run` | — | Solo imprime resumen |

Ejemplo — isla más grande en otra zona:

```bash
python3 scripts/generate-island.py --center-x 300 --center-y 100 --radius 20 --seed 7
```

### Ver en juego

1. Reiniciar servidor (el OTBM se carga solo al arranque)
2. Cliente local: `./scripts/play-yurots-client.sh`
3. GM: `/pos` o teleport a `350, 180, 7`

### Abrir en RME

```bash
./scripts/open-rme.sh
```

En RME: **Go to Position** → `350, 180, 7`.

> Si RME tenía el mapa abierto antes del script, cerralo y volvé a abrirlo para ver los tiles nuevos.

---

## Monstruos (manual, como pediste)

El script **solo genera terreno**. Los spawns van aparte.

### Opción A — RME (recomendada)

1. `./scripts/open-rme.sh`
2. Ir a la isla (`350, 180, 7`)
3. Spawn brush → colocar área de respawn
4. Exportar / guardar → actualizar `test-spawn.xml`
5. `docker compose restart yurots`

### Opción B — Editar XML

En `server/YurOTS/ots/data/world/test-spawn.xml`, dentro de `<spawns>`:

```xml
<spawn centerx="350" centery="180" centerz="7" radius="8">
  <monster name="troll" x="350" y="180" z="7" spawntime="60"/>
  <monster name="orc" x="352" y="182" z="7" spawntime="90"/>
</spawn>
```

El bloque sugerido también está en `generated-island.json` → campo `spawnXmlHint`.

Los nombres deben existir en `server/YurOTS/ots/data/monster/monsters.xml`.

---

## Isla de ejemplo ya generada

| Campo | Valor |
|-------|-------|
| Centro | `350, 180, 7` |
| Bounds tierra | X `335–364`, Y `165–195` |
| Tiles totales | 861 |
| Tierra | 683 |
| Agua | 178 |
| Backup (si existe) | `server/YurOTS/ots/data/world/test.otbm.bak` |

---

## Cosas para afinar

### Forma y tamaño

| Parámetro | Efecto | Sugerencia |
|-----------|--------|------------|
| `--radius` | Tamaño de la isla | `10–18` para hunts chicas; `20–30` para zonas grandes |
| `--seed` | Borde irregular y pasto | Probar `1, 7, 42, 99` hasta que guste la silueta |
| Umbrales en `island_ground()` | Grosor de costa / agua | Editar `1.05`, `0.92`, `0.78`, `1.18` en el script |
| `wobble` (`0.06 * sin * cos`) | Irregularidad del contorno | Subir a `0.10` para bahías; bajar a `0.03` para círculo limpio |

### Suelos y apariencia

| Afinar | Dónde | Notas |
|--------|-------|-------|
| IDs de agua/arena/pasto | Constantes `GROUND_*` al inicio del script | Deben ser grounds válidos en `items.otb` |
| Bordes autotile (transiciones bonitas) | No implementado | RME con brushes de sea/sand/grass después de generar |
| Árboles, rocas, decoración | No implementado | RME o futuro script de `OTBM_ITEM` hijos |
| Múltiples pisos (z 8, 9…) | `--z` | Útil para torres o cuevas subterráneas bajo la isla |

### Ubicación

Para encontrar huecos vacíos en el mapa:

```bash
python3 scripts/sync-houses-with-map.py --dry-run   # validar casas
# O inspeccionar generated-island.json / RME en zonas x>300
```

Evitar:

- Tiles dentro de casas (`HOUSETILE` en RME)
- Solapar islas ya generadas (el script falla si hay conflicto)
- Poner islas sobre depots, temples o spawns críticos sin revisar

### Workflow con git y VPS

Si commiteás el mapa con la isla:

```bash
git add server/YurOTS/ots/data/world/test.otbm
git add server/YurOTS/ots/data/world/generated-island.json   # opcional, metadata
# Si cambiaste spawns en RME:
git add server/YurOTS/ots/data/world/test-spawn.xml
```

En VPS: seguir [docs/CAMBIAR-MAPA.md](CAMBIAR-MAPA.md) y [scripts/README-DEPLOY-VPS.md](../scripts/README-DEPLOY-VPS.md). **No hace falta** `sync-houses-from-rme.py` si solo agregaste terreno vacío sin casas.

---

## Limitaciones actuales

1. **Solo suelo** — no coloca paredes, items, teleportes ni NPCs
2. **No sobrescribe** — si el tile ya existe, aborta (no “pinta encima”)
3. **Una isla por ejecución** — para varias islas, correr el script varias veces con distintos centros (sin solapar)
4. **Sin borrado** — no hay `remove-island.py`; restaurar desde `test.otbm.bak` o git
5. **Bordes crudos** — sin autotiling de RME; la costa puede verse cuadrada hasta pulir en editor
6. **Solo `test.otbm`** por defecto — si usás `test-rme.otbm` para casas, pasá `--map` explícito
7. **Spawns no persisten en OTBM** — van en `test-spawn.xml` (convención YurOTS)

---

## Extensiones posibles (roadmap)

Ideas naturales para seguir el mismo enfoque:

| Feature | Descripción |
|---------|-------------|
| `generate-spawns-from-yaml.py` | Lista `monsters: [{name, count}]` → bloque XML |
| `generate-maze.py` | ✅ Laberinto 2 sqm, camino 406, fondo 100, validación walkable — [MAPEAR_LABERINTO.md](MAPEAR_LABERINTO.md) |
| `generate-cave.py` | Room rectangular con paredes y entrada |
| `patch-map-from-yaml.py` | Lista `{x, y, z, ground, items[]}` → OTBM |
| OTBM2JSON | Migraciones masivas (reemplazar item ids en todo el mapa) |
| `--replace` | Sobrescribir ground en región existente |
| Decoración procedural | Palmeras, rocas, montículos como items OTBM hijos |

El parser de `sync-houses-with-map.py` y el writer de `generate-island.py` pueden fusionarse en un módulo `scripts/otbm_toolkit.py` si crece el uso.

---

## Errores frecuentes

| Síntoma | Causa | Solución |
|---------|--------|----------|
| `N tile(s) ya existen en el mapa` | Centro solapa terreno existente | Cambiar `--center-x/y` o bajar `--radius` |
| Isla no visible en cliente | Servidor no reiniciado o RME con archivo viejo | `docker compose restart yurots`; reabrir RME |
| Isla no visible in-game | Cliente con mapa cacheado | Reconectar; verificar coordenadas |
| Servidor no arranca tras editar OTBM | OTBM corrupto | Restaurar `test.otbm.bak` o `git checkout -- test.otbm` |
| Spawns no aparecen | `test-spawn.xml` sin actualizar | Exportar desde RME o editar XML |
| `Could not load map` | Nodo OTBM mal formado | No editar binario a mano; revisar cambios en el script |

---

## Archivos involucrados

| Archivo | Rol |
|---------|-----|
| `scripts/generate-island.py` | Generador |
| `server/YurOTS/ots/data/world/test.otbm` | Mapa activo |
| `server/YurOTS/ots/data/world/test.otbm.bak` | Backup automático (primera ejecución) |
| `server/YurOTS/ots/data/world/generated-island.json` | Metadata de la última isla |
| `server/YurOTS/ots/data/world/test-spawn.xml` | Spawns (manual / RME) |
| `server/YurOTS/ots/config.lua` | `map = "data/world/test.otbm"` |
| `scripts/open-rme.sh` | Abrir editor |
| `scripts/sync-houses-from-rme.py` | Solo si tocás casas en RME |

---

## Checklist rápido

```
[ ] python3 scripts/generate-island.py --dry-run
[ ] python3 scripts/generate-island.py (con parámetros deseados)
[ ] docker compose restart yurots && docker logs yurots --tail 20
[ ] Probar in-game en spawnCenter del JSON
[ ] ./scripts/open-rme.sh → decorar + spawns en la isla
[ ] Exportar test-spawn.xml si usaste RME
[ ] Reiniciar servidor y probar respawns
[ ] git commit cuando estés conforme
```

---

## Referencia técnica del loader del servidor

El loader relevante está en `server/YurOTS/ots/source/iomapotbm.cpp`:

- Lee `OTBM_TILE` → crea tile en `(base_x + off_x, base_y + off_y, z)`
- Primer `OTBM_ATTR_ITEM` en props = ground o item stackable
- Items adicionales = nodos hijos `OTBM_ITEM`

El generador solo escribe el caso mínimo (ground en props, sin hijos), que es suficiente para terreno walkable.
