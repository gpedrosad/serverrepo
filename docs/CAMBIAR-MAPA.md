# Cambiar el mapa (RME → local → ThinkPad)

Guía paso a paso para reemplazar `test.otbm` sin romper casas, spawns ni el arranque del servidor.

Relacionado:

- [docs/RME_SETUP.md](RME_SETUP.md) — abrir RME y assets 7.6
- [docs/items-and-map/MAPEAR_CON_CODIGO.md](items-and-map/MAPEAR_CON_CODIGO.md) — generar terreno (islas) con `generate-island.py`
- [docs/items-and-map/MAPEAR_PASO_DEL_NORTE.md](items-and-map/MAPEAR_PASO_DEL_NORTE.md): puerta norte y región nueva (bosque, tundra, cuevas del dragón) con `generate-north-pass.py`
- [docs/items-and-map/MAPA_DE_MONSTRUOS.md](items-and-map/MAPA_DE_MONSTRUOS.md): mapa interactivo de spawns y NPC (`build-monster-map.py`)
- [docs/items-and-map/MAPEAR_LABERINTO.md](items-and-map/MAPEAR_LABERINTO.md) — laberinto 2 sqm (camino 406, fondo 100, teleport templo) con `generate-maze.py`
- [docs/items-and-map/MAPEAR_VALLE_DE_LAS_BESTIAS.md](items-and-map/MAPEAR_VALLE_DE_LAS_BESTIAS.md) — Valle de las Bestias (reemplazó al hunt maze); portal `158,47,7` con `generate-beast-valley.py`
- [docs/items-and-map/MAPEAR_ISLOTE_MINOTAURO.md](items-and-map/MAPEAR_ISLOTE_MINOTAURO.md) — Islote del Minotauro (canal junto al muelle, z7 + cuevas z10–z12) con `generate-minotaur-isle.py`
- [docs/gameplay/WAVE_ARENA.md](gameplay/WAVE_ARENA.md) — Wave Arena oleadas; portal `166,47,7`
- [docs/gameplay/CRUCIBLE.md](gameplay/CRUCIBLE.md) — El Crisol (3 puertas + bosses diarios); portal `164,47,7` con `scripts/map/generate-crucible.py`
- [docs/gameplay/SAND_CLOCK.md](gameplay/SAND_CLOCK.md) — Reloj de Arena (fases globales); portal `168,47,7` con `scripts/map/generate-sand-clock.py`
- [docs/systems/THINKPAD_TEST_SERVER.md](systems/THINKPAD_TEST_SERVER.md) — deploy seguro al servidor de la ThinkPad (no hay producción por ahora)
- [docs/PROYECTO.md](PROYECTO.md) — qué data es sagrada y qué va en git

---

## Archivos que forman el mapa

| Archivo en repo | Origen (RME) | Qué define |
|-----------------|--------------|------------|
| `server/YurOTS/ots/data/world/test.otbm` | Guardar mapa OTBM | Tiles, items, casas (HOUSETILE), depots en mapa |
| `server/YurOTS/ots/data/world/test-house.xml` | Export casas / metadata RME | Lista de casas (`houseid`, entrada, town) |
| `server/YurOTS/ots/data/world/test-spawn.xml` | Export spawns RME | Respawns de monstruos |
| `server/YurOTS/ots/data/houses.xml` | **Generado por script** | Tiles de cada casa (lo lee el servidor) |
| `server/YurOTS/ots/data/world/npc.xml` | Manual / editor | Posiciones de NPCs (no van dentro del OTBM) |

El servidor carga `test.otbm` desde `config.lua` (`map = "data/world/test.otbm"`).

### Portales del templo (plaza, z7) — nov 2026

Todos los portales están en la plaza `155,43 – 169,52`, sobre la fila vieja. Portal en `y=47`, cartel en `y=46`, llegada al volver en `y=48`. La fila vieja (`y=53–55`) quedó como pasillo, sin portales.

Los maneja **un solo script**: `python3 scripts/map/temple-portals.py` (idempotente). Arma la plaza, pone portales y carteles (`readables.xml`, bloque `TEMPLE_PORTAL_SIGNS`) y reapunta todo teleport de vuelta al templo hacia la llegada del portal de su zona. Si regenerás una zona con su generador, volvé a correrlo. Para agregar un portal: sumarlo a `PORTALS` en ese script.

| Portal | Llegada al volver | Sistema | Doc / generador |
|--------|-------------------|---------|-----------------|
| `156,47,7` | `156,48,7` | Isla natural (herradura: 3 campamentos Cyclops + cueva con Grorlam) | [`MAPEAR_ISLA_NATURAL.md`](items-and-map/MAPEAR_ISLA_NATURAL.md) |
| `158,47,7` | `158,48,7` | Valle de las Bestias (el gauntlet también vuelve acá) | [`MAPEAR_VALLE_DE_LAS_BESTIAS.md`](items-and-map/MAPEAR_VALLE_DE_LAS_BESTIAS.md) |
| `164,47,7` | `164,48,7` | El Crisol | [`CRUCIBLE.md`](gameplay/CRUCIBLE.md) |
| `166,47,7` | `166,48,7` | Wave Arena | [`WAVE_ARENA.md`](gameplay/WAVE_ARENA.md) |
| `168,47,7` | `168,48,7` | Reloj de Arena | [`SAND_CLOCK.md`](gameplay/SAND_CLOCK.md) |

Sacados en nov 2026: Arena de Fosos, Fish TP (ya no existían en el mapa), Bleed Room y Floor campus.

---

## 1. Editar en Remere's Map Editor

```bash
./scripts/open-rme.sh
```

Antes de guardar:

- **Casas:** definilas en RME (HOUSETILE). Si borrás una casa del mapa, también hay que quitar su entrada en `data/houses/*.xml` (ver paso 4).
- **Spawns:** usá el spawn editor de RME; al exportar genera `test-spawn.xml`.
- **Depots:** colocalos en RME con el depot ID correcto. En Retro76 el temple usa **`depotid=1`**. Tras exportar, corré `python3 scripts/scan-map-depots.py server/YurOTS/ots/data/world/test.otbm`. **Probar in-game** antes de deploy (ver [`gameplay/DEPOTS.md`](gameplay/DEPOTS.md)).
- **Puertas de nivel:** puerta cerrada + **actionId = nivel + 1000** (ej. nivel 20 → `1020`). Script: `data/actions/scripts/leveldoor.lua`.
- **NPCs:** las posiciones van en `npc.xml`, no solo en el mapa.

Guardá / exportá desde RME (o copiá desde `~/Downloads` si guardaste ahí):

- `test.otbm` (o tu nombre, ej. `MAPA ACTUALIZADO CUATRO.otbm`)
- `test-house.xml`
- `test-spawn.xml`

---

## 2. Copiar al repo (Mac / local)

Desde la raíz del proyecto:

```bash
cp "/Users/gonzalo/Downloads/TU_MAPA.otbm" \
  server/YurOTS/ots/data/world/test.otbm

cp ~/Downloads/test-house.xml server/YurOTS/ots/data/world/test-house.xml
cp ~/Downloads/test-spawn.xml server/YurOTS/ots/data/world/test-spawn.xml
```

Ajustá la ruta del `.otbm` al nombre que hayas usado al guardar.

---

## 3. Sincronizar casas (obligatorio)

RME guarda casas como **HOUSETILE** dentro del OTBM. El servidor YurOTS necesita:

1. OTBM sin HOUSETILE (tiles normales)
2. `houses.xml` con los tiles de cada casa

```bash
python3 scripts/sync-houses-from-rme.py
```

El script:

- Lee `test-rme.otbm` o `test.otbm`
- Regenera `data/houses.xml` desde `test-house.xml` + tiles del mapa
- Convierte HOUSETILE → TILE en `test.otbm`
- Valida que no queden tiles inválidos

Si falla con `Tile (x/y/z) is not valid`, hay casas en `houses.xml` que no existen en el mapa — volvé a exportar desde RME o corré el script de nuevo.

**Validación extra (solo lectura):**

```bash
python3 scripts/sync-houses-with-map.py --dry-run
```

Debe decir: `houses.xml ya coincide con el mapa.`

---

## 4. Casas eliminadas del mapa

Si borraste casas en RME (ej. River Street I y II):

1. No deben aparecer en `test-house.xml` tras exportar.
2. Borrá el XML del dueño si existe:

   ```bash
   rm -f "server/YurOTS/ots/data/houses/River Street I.xml"
   rm -f "server/YurOTS/ots/data/houses/River Street II.xml"
   ```

3. `sync-houses-from-rme.py` ya no las incluirá en `houses.xml`.

**No edites `houses.xml` a mano** salvo emergencia; usá el script.

---

## 5. NPCs y otros datos

| Cambio | Archivo |
|--------|---------|
| Mover NPC (Dufi, Guild Master, etc.) | `server/YurOTS/ots/data/world/npc.xml` |
| Nuevo monstruo en spawn | `test-spawn.xml` + definición en `data/monster/` |
| Items en casas de jugadores | `houseitems.xml` (runtime del servidor, no git) |
| Dueños y permisos de casas | `data/houses/*.xml` (runtime del servidor; ver [`gameplay/HOUSES.md`](gameplay/HOUSES.md)) |

Tras mover NPCs, reiniciá el servidor (no hace falta recompilar).

---

## 6. Probar en local (Docker)

```bash
docker compose restart yurots
docker logs yurots --tail 30
```

Debe aparecer:

- `Loaded in X s`
- `Loading houses.xml... [done]`
- `Retro76 Server Running...`

Si falla en casas, revisá el paso 3.

Cliente local:

```bash
./scripts/play-yurots-client.sh
```

Conectar a `127.0.0.1:7171`.

---

## 7. Qué commitear a GitHub (cuando el mapa esté listo)

**Sí incluir:**

- `server/YurOTS/ots/data/world/test.otbm`
- `server/YurOTS/ots/data/world/test-house.xml`
- `server/YurOTS/ots/data/world/test-spawn.xml`
- `server/YurOTS/ots/data/houses.xml`
- `server/YurOTS/ots/data/world/npc.xml` (si cambió)
- `scripts/sync-houses-from-rme.py` (si aún no está en main)

**No incluir:**

- `test-rme.otbm`, `*.bak`, `test.otbm.bak` (copias locales)
- `config.lua` con otra IP — en el repo queda `ip = "127.0.0.1"`; la ThinkPad usa su IP (`192.168.1.17`) sin commitear
- `data/accounts/`, `data/players/` reales, logs, binario `source/yurots`
- `client-local/`

---

## 8. Subir a la ThinkPad

No hay producción por ahora: el único servidor es el de la ThinkPad. Solo cuando el mapa esté probado en local
y con el OK de Gonzalo:

1. `git push origin main` desde tu Mac
2. Seguir "Deploy de cambios de datos" en [systems/THINKPAD_TEST_SERVER.md](systems/THINKPAD_TEST_SERVER.md):
   revisar archivos de otras sesiones, respaldar datos de jugadores (incluye `houses` y `houseitems.xml`),
   `git merge --ff-only origin/main`, `docker restart -t 45 yurots`, revisar el log (`Loaded in …`) y
   `ot-probe.py 192.168.1.17 7171`.

Un mapa nuevo no se recompila. Antes de reiniciar, correr `sync-houses-with-map.py --dry-run` y probar depots
in-game (ver [`gameplay/DEPOTS.md`](gameplay/DEPOTS.md)).

---

## Checklist rápido

```
[ ] Guardar/exportar OTBM + test-house.xml + test-spawn.xml desde RME
[ ] Copiar los 3 archivos a server/YurOTS/ots/data/world/
[ ] python3 scripts/sync-houses-from-rme.py
[ ] python3 scripts/sync-houses-with-map.py --dry-run
[ ] python3 scripts/scan-map-depots.py server/YurOTS/ots/data/world/test.otbm
[ ] Borrar data/houses/*.xml de casas eliminadas (si aplica)
[ ] Actualizar npc.xml (si moviste NPCs)
[ ] docker compose restart yurots + revisar logs
[ ] Probar in-game: casas, depots (locker temple con char que tenga items), spawns, puertas
[ ] git commit + push (solo cuando estés conforme)
[ ] Con OK de Gonzalo: deploy a la ThinkPad (docs/systems/THINKPAD_TEST_SERVER.md)
```

---

## Errores frecuentes

| Síntoma | Causa | Solución |
|---------|--------|----------|
| `Tile (x/y/z) is not valid!` al cargar casas | `houses.xml` con tiles que ya no están en el mapa | `sync-houses-from-rme.py` |
| `Could not load houses!` | Casa en `houses.xml` sin archivo en `data/houses/Nombre.xml` | Crear XML o quitar casa del mapa |
| `You can not use this object` (depot) | Jugador sin ese `depotid` en su XML | Abrir depot en RME con ID estándar (ej. 1) o fix en `actions.cpp` |
| Depot vacío al abrir locker 2589 | Locker sin `depotid` en OTBM (export RME inline) | Ver [`gameplay/DEPOTS.md`](gameplay/DEPOTS.md); `resolveMapDepotId()` en `actions.cpp`; probar in-game antes de deploy |
| Puerta no pide nivel | Falta actionId o itemid sin `leveldoor.lua` | actionId = nivel + 1000 |
| Spawns no aparecen | `test-spawn.xml` viejo o monstruo sin definición | Reexportar spawns; revisar `data/monster/monsters.xml` |
| El servidor no arranca tras el deploy (casas) | Mismo desajuste mapa/casas | Arreglar en Mac, push, volver a deploy |

---

## Notas de esta iteración (mapa 2026-07)

- Mapa de referencia probado en local: **MAPA ACTUALIZADO CUATRO** (export RME).
- Casas: 35 (sin River Street I / II).
- Hub NPCs: Dufi `128,51,5`; Guild Master `129,51,5`.
- Spawns nuevos incluyen Enraged Hydra/Vampire, Angry Giant Spider, Mini Trainer Monk (zona ~129–134, 63).
- Depots y puertas: configurar en RME; evitar parches manuales al OTBM salvo casos puntuales.
