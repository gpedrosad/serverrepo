# scripts/ — herramientas del repo

Los scripts viven en subcarpetas por dominio. En la raíz de `scripts/` quedan **symlinks de compatibilidad** con los nombres históricos (`ot-probe.py`, `ot-diagnostics.sh`, etc.) para no romper docs, cron ni hábitos.

`resolve-project-root.sh` se queda en la raíz de `scripts/` (lo usan casi todos los `.sh`).
Python en subcarpetas debe resolver el repo con `lib.project_root.project_root()` (no `parents[1]`).

## Carpetas

| Carpeta | Contenido |
|---------|-----------|
| [`deploy/`](deploy/) | Backup runtime, **respaldo automático cada hora** (`auto-backup-runtime.sh` en la ThinkPad + `pull-auto-backups.sh` en la Mac; ver `docs/systems/THINKPAD_TEST_SERVER.md#respaldo-automático-de-jugadores`), server-save (y cron de medianoche), docker entrypoint |
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
| **`mapkit/build.py`** + `mapkit/` + `zones/*.json` | **Motor único de zonas** (nov 2026): ficha JSON → semillas → lint → decisiones chicas con jev → `--preview` / `--write`. `mapkit/catalog.py` regenera el catálogo de piezas de la guía ([MAPAS.md](../docs/items-and-map/MAPAS.md)) |
| `temple-portals.py` + `portal_citadel_layout.py` + `portal_temple_style.py` + `portal_temple_details.py` + `portal_temple_architecture.py` | Plaza, ocho portales, galería, pórtico y torre sureste con escaleras; `--dry-run` |
| `validate-portal-citadel.py` | Audita mapa/assets contra `--before`; rutas, teleports y ámbito exacto |
| `root-crypt.py` | Visual propia de la quest BoH al sur del depot; `--dry-run`, conserva huella/colisión/cofres/teleports |
| `bridge_rotworm_bank.py` / `render-bridge-rotworms.py` | Ribera retirada; `--remove` restaura el agua y elimina sus cuatro spawns con guardas de propiedad. Generación desactivada por manifiesto; render histórico ([doc](../docs/items-and-map/MAIN_BRIDGE.md)) |
| `bridge-trap-steps.py` / `render-main-bridge.py` | Puente principal Ironbound en z6: acabado de basalto/bronce y comparación visual, con trazado PvP intacto ([doc](../docs/items-and-map/MAIN_BRIDGE.md)) |
| `city-bridge-transitions.py` | Muelle junto al depot y puentes de madera (`BRIDGES`): barandas, faroles y rampa de `client-rme/dock_bridge_art.py`; saca cuerdas y wild growth; `--dry-run`, conserva huella y escaleras |
| `find-wood-bridges.py` | Lista madera transitable junto al agua (puentes, muelles, barcos) para elegir dónde poner barandas; `--z` |
| `electric-depot-walls.py` / `render-electric-depot.py` | Unifica variantes cian en lockers, ala norte y vestíbulo del depot; `--apply`, inversión exacta con `--before` ([DEPOT_ELECTRICO.md](../docs/items-and-map/DEPOT_ELECTRICO.md)) |
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
| `epstein_cave_repair.py` | Repara contornos, relleno visible y fogatas sobre escaleras sin regenerar recorridos/spawns; `--dry-run` |
| `generate-epstein-road.py` | Epstein Island: Camino de los Caídos, franja de tierra nueva en el mar (puente desde la punta sur) con Zombies y Undead Gladiators; bloque `EPSTEIN_ROAD` (`--dry-run --preview`) |
| `generate-epstein-cleanup.py` | Epstein Island: saca NPCs/tienda y el Oracle, y agrega el portal de salida al templo |
| `curious-houses.py` | Tres casas flotantes comprables (Kongras, elfos, río), plataformas/pasarelas y registro/PZ; `--dry-run`, exige agua y conserva todos los pasos públicos y dueños previos |
| `generate-river-grotto.py` / `river_grotto_style.py` / `render-river-grotto.py` | Gruta del río y accesos: bancos de arena, agua animada y corales, conservando rutas y spawns; `--dry-run` ([doc](../docs/items-and-map/RIVER_GROTTO.md)) |
| `generate-petrified-sanctuary.py` / `render-petrified-sanctuary.py` | Santuario z9 bajo el lago élfico, accesos z7/z8, etapas de monstruos, guardas de conservación y vistas con sprites reales; `--dry-run` en el generador ([doc](../docs/gameplay/PETRIFIED_SANCTUARY.md)) |
| `generate-dwarven-mine.py` / `dwarven_mine_layout.py` / `render-dwarven-mine.py` | Mina Enana z9/z10, túnel de acceso, estaciones, etapas de monstruos y forja; `--dry-run` y guardas de conservación ([doc](../docs/gameplay/DWARVEN_MINE.md)) |
| `reshape-river-street.py` | River Street III–V: casas más cortas, patios, pasillos de tierra y puente de sogas de 1 casilla hasta el arco de los trolls (`--dry-run --png`; ver `docs/gameplay/HOUSES.md`) |
| `arrange-mad-shop.py` | Tienda de Mad (z6 del Seller): 13 raros en el piso de Mad y el mostrador, fuera del alcance de los jugadores; valida con flood fill (`--replace`; ver `docs/items-and-map/MAPEAR_TIENDA_SELLER.md`) |
| `generate-maze.py` | Laberinto Alice |
| `generate-tp-gauntlet.py` | Gauntlet |
| `generate-island.py` | Islas procedurales |
| `scan-map-depots.py` / `patch-map-depot-ids.py` | Auditoría/parche depots |
| `style-hole-entrances.py` / `render-hole-entrances.py` | Revisa todos los hoyos, selecciona variantes nativas por suelo y valida llegadas; `--apply` actualiza mapa y manifiestos, con respaldo ([doc](../docs/items-and-map/HOLE_ENTRANCES.md)) |
| `check-reachable.py` | ¿Se llega caminando desde el templo (z7) a una entrada? Dibuja la zona si no: `check-reachable.py 119,129 176,58` (ver `docs/items-and-map/MAPAS.md#errores-que-ya-pasaron`) |
| `check-upper-view.py` | Casillas bajo tierra desde donde el cliente ve el piso de arriba (arriba vacío); `--fix` pone techo de roca solo en casillas vacías (ver `docs/items-and-map/MAPAS.md#techo`) |
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
| `build_frost_mine.py` | Recolorea fuego/runa nativos para Frost Mine; instalar solo 20369/20370 con `add_custom_items.py` ([doc](../docs/gameplay/FROST_MINE.md)) |
| `sprite_tool.py` | Sprites de criaturas: `bases`, `new`, `inspect`, `check`, `verify` (guía: `docs/gameplay/SPRITE_RECOLOR_GUIDE.md`) |
| `add_paladin_stars.py` + `paladin_star_art.py` | Tres stars de paladín con proyectiles e impactos propios; `--prepare`, `--preview`, `--apply` |
| `add_melee_relics.py` / `melee_relic_art.py` / `validate_melee_relics.py` | Tres armas melee e impactos 47–49; generación, instalación idempotente y auditoría ([MELEE_RELICS.md](../docs/gameplay/MELEE_RELICS.md)) |
| `validate_paladin_stars.py` | Compara el pack con `--before` y exige sprites/looks/OTB anteriores intactos |
| `portal_citadel_assets.py` | Once piezas nuevas de la plaza arcana; `--prepare`, `--apply` |
| `portal_detail_assets.py` | Arco abierto, faroles y rejas exclusivos del templo; `--prepare`, `--apply` |
| `root_crypt_assets.py` | Once piezas de piedra, raíces y luz ámbar de la quest BoH; `--prepare`, `--apply` |
| `recolor_cyan_skull.py` | Recolorea la calavera roja nativa a cian conservando dibujo y alpha; `--client RUTA_CLIENTERETRO` |
| `city_bridge_z6_art.py` / `ironbound_bridge_material.py` / `ironbound_bridge_deck.py` | Barandas 3D, pavimento y pilares del puente principal; material privado y anclas fijas para conservar el PvP |
| `depot_electric_assets.py` | Prepara e instala las 30 piezas eléctricas del depot (20200–20210 + 20420–20438); `--complete-only`, `--prepare-completion`, `--dry-run` |
| `add_recolor_look.py` + `presets/` + `sprite_kit.py` | Aplica un preset de criatura (un archivo por criatura en `presets/`) a `Tibia.dat`/`.spr` |
| `play-yurots-client.sh` / `open-rme.sh` | Cliente y RME locales |
| `patch-tibia760-client.py` | Patcher cliente 7.6 |
| `publish_client.py` | Publica el cliente Retro76 (updater + zips; el de Mac con `Retro76.app`). Doc: `docs/CLIENT_UPDATER_RETRO76.md` |
| `make_level_gifts.py` | Dibuja las 6 cajas de regalo de nivel recoloreando el present de 7.6; `--preview` ([LEVEL_UP_REWARDS.md](../docs/gameplay/LEVEL_UP_REWARDS.md)) |
| `make_mac_icon.py` | Ícono de `Retro76.app` (`.icns`) y de la ventana del cliente (`clienticon.png`) |

### ot / web / deploy

Ver comandos de arriba; deploy: ver abajo.

| Script | Uso |
|--------|-----|
| `ot/exercise-server.py` | Bots que usan y maltratan un servidor de prueba ([SANITIZER_TESTS.md](../docs/systems/SANITIZER_TESTS.md)) |
| `ot/test-level-gifts.py` | Prueba con bots en un servidor aparte: cajas por nivel, abrirlas, no repetir y aviso de raros ([LEVEL_UP_REWARDS.md](../docs/gameplay/LEVEL_UP_REWARDS.md)) |
| `ot/test-sponsor.py` | Prueba con bots del padrinazgo: reglas, aceptar, hitos con el padrino conectado y desconectado, sin repetir ([PADRINAZGO.md](../docs/gameplay/PADRINAZGO.md)) |
| `ot/test-pot-thrower.py` | Prueba con bots del Orc Berserker Pot Thrower: tira ollas (no bebederos) y no se pueden levantar ([MONSTRUOS.md](../docs/gameplay/MONSTRUOS.md)) |
| `ot/test-summon-follow.py` | Prueba con bots en un servidor aparte: el summon sigue al dueño a un paso, con su velocidad y al cambiar de piso ([SUMMONS.md](../docs/gameplay/SUMMONS.md)) |

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

- `map/generate-elf-west.py` — Elfland y Ruinas del Sauce al oeste; `--dry-run`, guardas de costa, spawns y patrimonio. Doc: `docs/items-and-map/ELF_WEST.md`.
