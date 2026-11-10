# scripts/ — herramientas del repo

Los scripts viven en subcarpetas por dominio. En la raíz de `scripts/` quedan **symlinks de compatibilidad** con los nombres históricos (`deploy-vps.sh`, `ot-probe.py`, etc.) para no romper docs, cron del VPS ni hábitos.

`resolve-project-root.sh` se queda en la raíz de `scripts/` (lo usan casi todos los `.sh`).
Python en subcarpetas debe resolver el repo con `lib.project_root.project_root()` (no `parents[1]`).

## Carpetas

| Carpeta | Contenido |
|---------|-----------|
| [`deploy/`](deploy/) | Deploy VPS, backup runtime, server-save, docker entrypoint, HTTPS |
| [`ot/`](ot/) | Probe, diagnostics, watchdog, start-local, smoke tests |
| [`map/`](map/) | Generadores OTBM, depots, sync de houses |
| [`otb/`](otb/) | Patches OTB / gems sprites / loot tables |
| [`client-rme/`](client-rme/) | RME, clientes locales, Zagan test assets, patcher |
| [`web/`](web/) | Web local, analytics, premium funnel |
| [`lib/`](lib/) | Helpers compartidos (`project_root.py`) |
| [`code/`](code/) | Limpieza del C++ y comprobación sin compilar (`check-cpp-equivalence.py`, `strip-dead-comments.py`) |
| [`npc/`](npc/) | Banco de pruebas de NPCs |

## Comandos más usados (rutas históricas = OK)

```bash
DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
python3 scripts/ot-probe.py 127.0.0.1 7171
./scripts/ot-diagnostics.sh
./scripts/web.sh
./scripts/play-yurots-client.sh
./scripts/open-rme.sh
```

Equivalente canónico:

```bash
./scripts/deploy/deploy-vps.sh
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
| `generate-crucible.py` | El Crisol v2: hub PZ + 3 arenas temáticas, carteles y bloque `LAYOUT` de `crucible.lua` (`--dry-run --png` para previsualizar; portal en la plaza: `temple-portals.py`) |
| `temple-portals.py` | Plaza del templo con todos los portales + reapunta vueltas (correr después de cualquier generador de zona) |
| `generate-natural-island.py` | Isla irregular con costa/bordes del mapa real; `--cave` agrega cueva z+1 con agujero y escalera |
| `spawn-island-cave.py` / `link-island-temple.py` | Spawns de la cueva / vuelta al templo + cyclops de la isla |
| `generate-sand-clock.py` | Reloj de Arena OTBM (portal en la plaza: `temple-portals.py`) |
| `generate-wave-arena.py` | Wave Arena |
| `generate-hunt-maze.py` | Hunt maze |
| `generate-maze.py` | Laberinto Alice |
| `generate-tp-gauntlet.py` | Gauntlet |
| `generate-island.py` | Islas procedurales |
| `scan-map-depots.py` / `patch-map-depot-ids.py` | Auditoría/parche depots |
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
| `play-yurots-client.sh` / `open-rme.sh` | Cliente y RME locales |
| `patch-tibia760-client.py` | Patcher cliente 7.6 |

### ot / web / deploy

Ver comandos de arriba; deploy: leer **antes** [`deploy/README-DEPLOY-VPS.md`](deploy/README-DEPLOY-VPS.md).

## Deploy

Leer **antes**: [`deploy/README-DEPLOY-VPS.md`](deploy/README-DEPLOY-VPS.md)  
(también: `scripts/README-DEPLOY-VPS.md` vía symlink).

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
