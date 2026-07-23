# Mapear con código — laberinto procedural en OTBM

Guía de cómo se generó el laberinto de Retro76: caminos de **2 sqm** con suelo **id 406**, fondo **id 100**, entrada al sur, teleport al templo al norte.

Relacionado:

- [MAPEAR_CON_CODIGO.md](MAPEAR_CON_CODIGO.md) — mismo enfoque OTBM (islas procedurales)
- [MAPEAR_HUNT_MAZE.md](MAPEAR_HUNT_MAZE.md) — laberinto de caza **aparte** (portal templo viejo); no modifica Alice
- [CAMBIAR-MAPA.md](../CAMBIAR-MAPA.md) — flujo RME → servidor → deploy
- [RME_SETUP.md](../RME_SETUP.md) — abrir Remere's Map Editor
- [gameplay/RESPAWN_SYSTEM.md](../gameplay/RESPAWN_SYSTEM.md) — cómo cargan los spawns
- `scripts/generate-maze.py` — generador del laberinto

---

## Resumen

| Qué hace el script | Qué **no** hace |
|--------------------|-----------------|
| Genera un laberinto perfecto (sin loops) con caminos de 2×2 tiles | No coloca monstruos |
| Fondo id **100** en todo el footprint; camino id **406** | No exporta `test-spawn.xml` |
| Entrada al sur; teleport **1387** al norte → templo `130,53,6` | No reemplaza el mapa entero |
| `--replace` reescribe el footprint del laberinto en `test.otbm` | No hace autotiling ni paredes visibles |

**Flujo usado en jul 2026:**

```
generate-maze.py  →  RME (spawns)  →  exportar test-spawn.xml  →  restart servidor  →  cliente local
```

---

## Laberinto generado (instancia actual)

| Campo | Valor |
|-------|-------|
| Script | `scripts/generate-maze.py --replace` |
| Semilla | `76` |
| Celdas lógicas | `14 × 22` (más largo al norte) |
| Suelo camino | server id `406` (white marble floor) |
| Fondo | server id `100` (void decorativo) |
| Ancho del camino | 2 sqm |
| Borde sur (anchor) | `380, 103, 7` |
| Entrada (sur) | `380, 102, 7` |
| Salida + teleport (norte) | `408, 18, 7` → templo `130, 53, 6` |
| Footprint | X `380–433`, Y `18–103`, z `7` |
| Tiles | 2460 camino, 2184 fondo, 4 teleports |
| Conectividad | 2460/2460 tiles 406 alcanzables (entrada → salida) |
| Manifiesto | `server/YurOTS/ots/data/world/generated-maze.json` |

Los monstruos van en RME sobre el camino y se exportan a `test-spawn.xml` (hay que re-colocarlos si regenerás el laberinto con `--replace`).

---

## Requisitos del diseño

1. **Camino de 2 sqm** — cada “sala” del laberinto ocupa un bloque 2×2 de tiles; los pasillos que conectan salas adyacentes también son 2×2.
2. **Fondo 100** — rellena todo el footprint; **no es walkable** (pared decorativa). Solo el camino 406 se puede pisar.
3. **Caminos unidos** — cada arista del grafo pinta un puente 2×2 de id 406 en el hueco entre celdas; sin ese puente queda 100 y no se puede cruzar.
4. **Orientación** — entrada al sur (`cy = cells_y - 1`), salida al norte (`cy = 0`) con teleport al templo.
5. **Validación** — antes de escribir el OTBM, flood-fill desde la entrada: todos los tiles 406 deben ser un solo componente y alcanzar la salida.

---

## Geometría: cómo se traduce “2 sqm” a tiles

El laberinto usa **celdas lógicas** con paso de **4 tiles** por eje (`CELL_STRIDE = 4`):

| Bloque | Tamaño | Suelo | Walkable |
|--------|--------|-------|----------|
| Sala / pasillo | 2×2 | 406 | Sí |
| Hueco entre celdas (pared) | 2×2 | 100 | No |
| Puente entre celdas vecinas | 2×2 | 406 | Sí (solo si hay arista en el grafo) |

Layout de dos celdas vecinas en horizontal:

```
┌──┬──┬──┬──┬──┬──┐
│██│██│▓▓│▓▓│██│██│   ██ = camino 406 (walkable)
└──┴──┴──┴──┴──┴──┘   ▓▓ = fondo 100 (pared, no walkable)
  celda A   puente  celda B
```

- **Celda** `(cx, cy)` → bloque 2×2 en `(origin_x + cx*4, cell_base_y(cy))`.
- **Puente horizontal** entre `(cx,cy)` y `(cx+1,cy)` → bloque en `x = cx*4 + 2`.
- **Puente vertical** entre `(cx,cy)` y `(cx,cy+1)` → bloque en `y = cell_base_y(cy) + 2` (cy menor = más al norte).

> Bug corregido jul 2026: el puente vertical estaba desplazado 4 tiles y dejaba huecos de 100 entre salas — el laberinto se veía unido visualmente en algunas direcciones pero no se podía atravesar.

---

## Algoritmo

1. **Grafo de celdas** — grilla `cells_x × cells_y` (default 14×22).
2. **Backtracking recursivo** — desde la celda sur-oeste `(0, cells_y-1)`, elegir vecino al azar (`--seed`), marcar arista.
3. **Rasterizar** — fondo 100 en footprint; celdas visitadas → 406; cada arista → puente 406 (`connection_block_tiles`).
4. **Validar conectividad** — BFS desde entrada: 100% de tiles 406 alcanzables y salida alcanzable (`validate_walkable_path`).
5. **Teleport** — item 1387 en bloque de salida norte → templo `130,53,6`.
6. **OTBM** — escribir con `--replace` en el footprint.

Funciones clave en `scripts/generate-maze.py`: `generate_maze_cells`, `connection_block_tiles`, `validate_walkable_path`, `patch_otbm`.

---

## Uso del script

### Simular sin escribir

```bash
python3 scripts/generate-maze.py --dry-run
```

### Generar / regenerar (reemplaza footprint)

```bash
python3 scripts/generate-maze.py --replace
docker compose -f docker-compose.prod.yml restart yurots
```

El script imprime `Conectividad: OK — N/N tiles de camino alcanzables`. Si falla, no escribe el mapa.

### Parámetros

| Flag | Default | Descripción |
|------|---------|-------------|
| `--origin-x` | `380` | Borde oeste del footprint |
| `--origin-y-south` | `103` | Borde sur del footprint (entrada) |
| `--z` | `7` | Piso |
| `--cells-x` | `14` | Celdas en X |
| `--cells-y` | `22` | Celdas en Y (más = más largo al norte) |
| `--seed` | `76` | Forma del laberinto |
| `--replace` | — | Borra tiles previos en el footprint y escribe de nuevo |
| `--temple-x/y/z` | `130/53/6` | Destino del teleport |
| `--dry-run` | — | Solo imprime resumen + validación |

Ejemplo — laberinto más chico en otra zona:

```bash
python3 scripts/generate-maze.py \
  --origin-x 400 --origin-y-south 120 \
  --cells-x 10 --cells-y 10 \
  --seed 42 --dry-run
```

### Regenerar en la misma zona

Usar `--replace` (ya no hace falta borrar a mano en RME). El script elimina tiles del footprint y vuelve a escribir.

### Regenerar sin `--replace`

Aborta si hay tiles existentes en el footprint.

---

## Monstruos (paso manual en RME)

El OTBM **no** guarda respawns activos del servidor. Después de generar el laberinto:

1. Abrir RME: `./scripts/open-rme.sh` (o `scripts/open-rme-zagan-terminal.command` con items Zagan).
2. **Go to Position** → `380, 102, 7` (entrada sur; ver `generated-maze.json`).
3. Spawn brush → colocar spawns sobre tiles de camino (2 sqm de ancho).
4. Guardar / exportar → actualizar `server/YurOTS/ots/data/world/test-spawn.xml`.
5. Reiniciar servidor para cargar spawns.

Ver también [gameplay/MONSTER_CREATION.md](../gameplay/MONSTER_CREATION.md).

---

## Probar en local

```bash
# Servidor (si no está arriba)
docker compose -f docker-compose.prod.yml up -d yurots

# Verificar protocolo OT (no confiar solo en "Up")
python3 scripts/ot-probe.py 127.0.0.1 7171

# Cliente
./scripts/play-yurots-client.sh
```

En juego (GM):

- Entrada sur: `/pos 380 102 7`
- Salida / teleport: `/pos 408 18 7`

---

## Ver en RME

```bash
./scripts/open-rme.sh
```

Si RME ya estaba abierto antes de correr el script, cerrarlo y volver a abrir para ver tiles nuevos.

Posiciones sugeridas en RME:

- Entrada sur: `380, 102, 7`
- Salida norte (teleport): `408, 18, 7`
- Centro aproximado: `406, 60, 7`

---

## Archivos involucrados

| Archivo | Rol |
|---------|-----|
| `scripts/generate-maze.py` | Generador del laberinto |
| `server/YurOTS/ots/data/world/test.otbm` | Mapa activo (patcheado) |
| `server/YurOTS/ots/data/world/generated-maze.json` | Metadata: entrada, centro, bounds |
| `server/YurOTS/ots/data/world/test-spawn.xml` | Spawns (RME / manual) |
| `server/YurOTS/ots/data/world/test.otbm.bak` | Backup automático (primera ejecución del script) |

---

## Limitaciones

1. Solo suelos 100 (fondo) y 406 (camino) — sin decoración extra ni paredes con sprite propio.
2. Sin `--replace`, aborta si el footprint ya tiene tiles en el OTBM.
3. Spawns en `test-spawn.xml` aparte — convención YurOTS; se pierden al regenerar el footprint si no re-exportás desde RME.
4. Fuera del footprint no hay tiles — el jugador no puede salir del laberinto salvo por el teleport de salida o borde sin tile adyacente.
5. El fondo 100 **bloquea** el paso — si un puente 406 falta o está mal ubicado, el camino queda cortado (el script valida esto antes de escribir).

---

## Conectividad y manifiesto JSON

Tras generar, `server/YurOTS/ots/data/world/generated-maze.json` incluye:

| Campo | Ejemplo | Significado |
|-------|---------|-------------|
| `entry` | `380, 102, 7` | Tile de entrada (sur) |
| `exit` | `408, 18, 7` | Tile de salida con teleport |
| `teleportDest` | `130, 53, 6` | Templo de aterrizaje |
| `footprint` | X `380–433`, Y `18–103` | Región que `--replace` borra/reescribe |
| `connectivity.reachablePathTiles` | `2460` | Tiles 406 alcanzables desde entrada |
| `connectivity.totalPathTiles` | `2460` | Total tiles de camino |
| `connectivity.exitReachable` | `true` | La salida es alcanzable caminando |

Si `reachablePathTiles < totalPathTiles`, el script aborta con `camino fragmentado` y **no** modifica el OTBM.

Validación interna (`validate_walkable_path`):

1. Flood-fill (BFS) desde `entry` solo por tiles con `ground == 406`.
2. Comprobar que el conjunto visitado cubre **todos** los tiles de camino.
3. Comprobar que al menos un tile de `exit` fue visitado.

---

## Errores frecuentes

| Síntoma | Causa | Solución |
|---------|--------|----------|
| `N tile(s) ya existen en el mapa` | Origen solapa terreno | Usar `--replace` o cambiar `--origin-x/y-south` |
| Camino se ve cortado / no se puede cruzar | Puente 406 mal colocado; queda 100 en medio | Regenerar con script actual; verificar `Conectividad: OK` |
| `camino fragmentado: N tile(s)...` | Validación BFS falló | El mapa no se escribe; revisar semilla o reportar bug |
| Laberinto no visible | Servidor sin restart o RME con archivo viejo | Restart + reabrir RME |
| Monstruos no aparecen | `test-spawn.xml` sin exportar o spawn sobre 100 | Spawns solo en tiles 406; restart servidor |
| `Could not load map` | OTBM corrupto | Restaurar `test.otbm.bak` o `git checkout` |

---

## Checklist rápido

```
[ ] python3 scripts/generate-maze.py --dry-run --replace
[ ] python3 scripts/generate-maze.py --replace   # debe decir Conectividad: OK
[ ] docker compose -f docker-compose.prod.yml restart yurots
[ ] python3 scripts/ot-probe.py 127.0.0.1 7171
[ ] ./scripts/open-rme.sh → spawns en el camino
[ ] Exportar / guardar test-spawn.xml
[ ] Restart servidor + ./scripts/play-yurots-client.sh
[ ] /pos 380 102 7 in-game (entrada sur)
[ ] git commit test.otbm + test-spawn.xml cuando estés conforme
```

---

## Historial (jul 2026)

| Versión | Cambio |
|---------|--------|
| v1 | Laberinto 14×14, solo camino 406, void negro (sin tile) |
| v2 | Fondo 100, 14×22 (más largo al norte), teleport 1387 → templo |
| v3 | **Fix conectividad**: puentes verticales en `cell_base_y + 2`; validación BFS obligatoria |

El bug de v2 dejaba huecos de id 100 entre salas en el eje vertical: las celdas parecían juntas pero no se podía caminar. v3 corrige `connection_block_tiles()` y exige `Conectividad: OK` antes de escribir.

---

## Referencia cruzada

El writer OTBM comparte el mismo modelo que [MAPEAR_CON_CODIGO.md](MAPEAR_CON_CODIGO.md) (`generate-island.py`). A futuro ambos podrían unificarse en `scripts/otbm_toolkit.py`.
