# scripts/ — herramientas del repo

Los scripts viven en subcarpetas por dominio. En la raíz de `scripts/` quedan **symlinks de compatibilidad** con los nombres históricos (`ot-probe.py`, `ot-diagnostics.sh`, etc.) para no romper docs, cron ni hábitos.

`resolve-project-root.sh` se queda en la raíz de `scripts/` (lo usan casi todos los `.sh`).
Python en subcarpetas debe resolver el repo con `lib.project_root.project_root()` (no `parents[1]`).

## Carpetas

| Carpeta | Contenido |
|---------|-----------|
| [`deploy/`](deploy/) | Backup runtime, server-save (y cron de medianoche), docker entrypoint |
| [`ot/`](ot/) | Probe, diagnostics, watchdog, start-local, smoke tests |
| [`map/`](map/) | Generadores OTBM, depots, sync de houses |
| [`monsters/`](monsters/) | `apply-monster-kits.py`: ataques de su tema para los monstruos nuevos ([MONSTER_KITS.md](../docs/gameplay/MONSTER_KITS.md)). `rage-variants.py`: audita y genera las variantes Angry/Furious/Enraged de los monstruos nuevos ([RAGE_MONSTERS.md](../docs/gameplay/RAGE_MONSTERS.md)) |
| [`otb/`](otb/) | Patches OTB / gems sprites / loot tables |
| [`client-rme/`](client-rme/) | RME, clientes locales, Zagan test assets, patcher |
| [`web/`](web/) | Web local, analytics, premium funnel, `build-site.sh` (compila la web Astro en la ThinkPad) |
| [`lib/`](lib/) | Helpers compartidos (`project_root.py`) |
| [`code/`](code/) | Limpieza del C++ y comprobación sin compilar (`check-cpp-equivalence.py`, `strip-dead-comments.py`) |
| [`npc/`](npc/) | Banco de pruebas de NPCs |

## Comandos más usados (rutas históricas = OK)

```bash
python3 scripts/ot-probe.py 127.0.0.1 7171
./scripts/ot-diagnostics.sh
./scripts/web.sh
./scripts/play-yurots-client.sh
./scripts/open-rme.sh
```

Equivalente canónico:

```bash
python3 scripts/ot/ot-probe.py 127.0.0.1 7171
./scripts/ot/ot-diagnostics.sh
./scripts/web/web.sh
./scripts/client-rme/play-yurots-client.sh
./scripts/client-rme/open-rme.sh
```

## Inventario por carpeta

### map/

| Script | Uso |
|--------|-----|
| `temple-portals.py` + `portal_citadel_layout.py` | Dueño único de la plaza arcana y sus ocho portales; `--dry-run` |
| `validate-portal-citadel.py` | Audita mapa/assets contra `--before`; rutas, teleports y ámbito exacto |
| `electric-depot-walls.py` | Aplica variantes cian solo a las murallas de la sala de lockers; `--apply`, inversión exacta con `--before` ([DEPOT_ELECTRICO.md](../docs/items-and-map/DEPOT_ELECTRICO.md)) |
| `roomkit.py` | Piezas comunes de los generadores de salas (Crisol, Wave Arena): `Room`, paredes, validación con flags del `.otb`, escritura del OTBM |
| `generate-crucible.py` | El Crisol v3: hub PZ + 3 arenas temáticas, carteles y bloque `LAYOUT` de `crucible.lua` (`--dry-run --png` para previsualizar; portal en la plaza: `temple-portals.py`) |
| `generate-natural-island.py` | Isla natural: herradura con sendero, 3 campamentos Cyclops y cueva de 4 salas; escribe mapa, spawns, carteles y manifiesto (`--dry-run --preview`) |
| `generate-sand-clock.py` | Reloj de Arena OTBM (portal en la plaza: `temple-portals.py`) |
| `remove-old-event-areas.py` | Borra las casillas viejas del Crisol / Wave Arena / Reloj de Arena (previas al distrito de eventos x>=560; eran vacío en el mapa original) |
| `generate-wave-arena.py` | Wave Arena v2 (Claro de la Selva): campamento PZ + claro 13x11, carteles y bloque `LAYOUT` de `wave_arena.lua` (`--dry-run --png`) |
| `generate-beast-valley.py` | Valle de las Bestias (portal 158,47,7; reemplazó al hunt maze) |
| `generate-minotaur-isle.py` | Islote del Minotauro: islote junto al muelle con puente + cuevas z10–z12 (`--dry-run --png`) |
| `generate-forgotten-pit.py` | El Foso Olvidado: reemplaza la Arena PvP por entrada z9 + corredor y 3 laberintos z10–z12, con spawns progresivos y jefes (`--dry-run --preview-dir`; retira la arena y vacía `pvparenas.xml`) |
| `generate-fargum-tower.py` | Torre del Barquero: saca el patio de mesas junto al bote de Fargum y hace una torre de 5 pisos (z7–z3) con un monstruo por piso (`--dry-run --preview-dir`) |
| `generate-bamboo-depths.py` | Cuevas de Bambú: bajada bajo Bamboo Camp, pozo z8 y cueva z9 con 3 salas y spawns progresivos (`--dry-run --preview`) |
| `generate-epstein-hunts.py` | Epstein Island (nivel medio/alto, 4 pisos): zonas z7, cuevas z8, z9 y z10 con Mutated Tiger, Tide Priest y Bog Raiders (`--dry-run`) |
| `generate-city-depths.py` | Dungeon de la city (agujero `185,58,7`): cueva z8–z10 en bloques 2x2, salas con decoración fija, agujeros + escaleras de mano y spawns por sala; valida paredes, vacío a la vista y recorrido (`--dry-run --preview`; ver `docs/items-and-map/MAPEAR_DUNGEON_CITY.md`) |
| `generate-city-hunts.py` | Tripulación pirata del barco del este y polizón (solo `test-spawn.xml`) |
| `generate-epstein-caves.py` | Epstein Island: cuevas largas z8 + z9 + z10, agujeros y escaleras; escribe `generated-epstein-caves.json` (`--dry-run --preview-dir`) |
| `generate-epstein-cleanup.py` | Epstein Island: saca NPCs/tienda y el Oracle, y agrega el portal de salida al templo |
| `reshape-river-street.py` | River Street III–V: casas más cortas, patios, pasillos de tierra y puente de sogas de 1 casilla hasta el arco de los trolls (`--dry-run --png`; ver `docs/gameplay/HOUSES.md`) |
| `arrange-mad-shop.py` | Tienda de Mad (z6 del Seller): 13 raros en el piso de Mad y el mostrador, fuera del alcance de los jugadores; valida con flood fill (`--replace`; ver `docs/items-and-map/MAPEAR_TIENDA_SELLER.md`) |
| `generate-maze.py` | Laberinto Alice |
| `generate-tp-gauntlet.py` | Gauntlet |
| `generate-island.py` | Islas procedurales |
| `scan-map-depots.py` / `patch-map-depot-ids.py` | Auditoría/parche depots |
| `check-upper-view.py` | Casillas bajo tierra desde donde el cliente ve el piso de arriba (arriba vacío); `--fix` pone techo de roca solo en casillas vacías (ver `docs/items-and-map/PIEZAS_DE_MAPA.md#techo`) |
| `sync-houses-*.py` | Houses ↔ mapa / RME |

### otb/

| Script | Uso |
|--------|-----|
| `patch-crucible-rares-otb.py` | 7 armas exclusivas del Crisol |
| `patch-crystal-arrow-otb.py` | Crystal Arrow DIST |
| `patch-fury-cape-otb.py` / `patch-medusa-sword-otb.py` / `patch-sword-of-silence-otb.py` / `patch-windsting-axe-otb.py` | Items Zagan |
| `extract-gem-sprites.py` / `build-gem-loot-table.py` | Assets/web de gemas |

### client-rme/

| Script | Uso |
|--------|-----|
| `build_zagan_test_assets.py` | Pipeline sprites/OTB/dat Zagan |
| `sprite_tool.py` | Sprites de criaturas: `bases`, `new`, `inspect`, `check`, `verify` (guía: `docs/gameplay/SPRITE_RECOLOR_GUIDE.md`) |
| `add_paladin_stars.py` + `paladin_star_art.py` | Tres stars de paladín con proyectiles e impactos propios; `--prepare`, `--preview`, `--apply` |
| `add_melee_relics.py` / `melee_relic_art.py` / `validate_melee_relics.py` | Tres armas melee e impactos 47–49; generación, instalación idempotente y auditoría ([MELEE_RELICS.md](../docs/gameplay/MELEE_RELICS.md)) |
| `validate_paladin_stars.py` | Compara el pack con `--before` y exige sprites/looks/OTB anteriores intactos |
| `portal_citadel_assets.py` | Once piezas nuevas de la plaza arcana; `--prepare`, `--apply` |
| `recolor_cyan_skull.py` | Recolorea la calavera roja nativa a cian conservando dibujo y alpha; `--client RUTA_CLIENTERETRO` |
| `depot_electric_assets.py` | Prepara e instala las once piezas eléctricas del depot (20200–20210); `--prepare`, `--dry-run` |
| `add_recolor_look.py` + `presets/` + `sprite_kit.py` | Aplica un preset de criatura (un archivo por criatura en `presets/`) a `Tibia.dat`/`.spr` |
| `play-yurots-client.sh` / `open-rme.sh` | Cliente y RME locales |
| `patch-tibia760-client.py` | Patcher cliente 7.6 |
| `publish_client.py` | Publica el cliente Retro76 (updater + zips; el de Mac con `Retro76.app`). Doc: `docs/CLIENT_UPDATER_RETRO76.md` |
| `make_mac_icon.py` | Ícono de `Retro76.app` (`.icns`) y de la ventana del cliente (`clienticon.png`) |

### ot / web / deploy

Ver comandos de arriba; deploy: ver abajo.

## Deploy

No hay script de deploy ni servidor de producción por ahora. Los deploys van a la ThinkPad, solo con el OK de
Gonzalo, siguiendo [`docs/systems/THINKPAD_TEST_SERVER.md`](../docs/systems/THINKPAD_TEST_SERVER.md).

## Smoke tests

Flag: `ot/.smoke-tests-disabled` (symlink en `scripts/.smoke-tests-disabled`).  
Desactivados temporalmente — ver `AGENTS.md` §2.7.

## NPCs

| Script | Qué hace |
|--------|----------|
| `npc/run_npc_tests.py` | Prueba todos los NPCs contra transcripciones grabadas (LuaJIT + `npc/harness.lua`), sin levantar el servidor. Ver `docs/gameplay/NPC_SYSTEM.md` |

## Código C++ (limpieza sin compilar)

| Script | Qué hace |
|--------|----------|
| `code/check-cpp-equivalence.py <ref>` | Comprueba que el C++ actual da el mismo código que `<ref>` (resuelve los `#if` con `--flags code/linux-build-flags.h` y compara sin comentarios). `--comments` compara solo sin comentarios |
| `code/strip-dead-comments.py` | Borra comentarios que son código desactivado (`--dry` para contar) |
| `code/linux-build-flags.h` | Configuración del build de Linux para `unifdef -f` |

Ver `docs/systems/LIMPIEZA_CODIGO_NOV2026.md`.
