# Sesión editor de mapa y servidor local (jul 2026)

Documento de lo implementado en esta sesión: mapa `test.otbm`, entorno Zagan test, NPCs, monstruos, items custom y corrección de IDs en el cliente.

---

## Cómo abrir el map editor (RME)

```bash
# Desde Finder (doble clic) o terminal:
./scripts/open-rme-zagan-terminal.command

# Equivalente:
./scripts/open-rme-zagan-test.sh
```

**Qué hace el script:**

1. Recupera XQuartz si hace falta (`recover-rme-macos.sh`).
2. Sincroniza `items-zagan-test.otb` → RME (`setup-rme-zagan-items.sh`).
3. Configura cliente 7.6 Zagan en `rme-client-760-zagan-test` (`setup-rme-config.sh`).
4. Exporta criaturas del servidor a RME (`setup-rme-creatures.sh`).
5. Instala extensiones (`yurots-zagan-items.xml`, criaturas) (`setup-rme-extensions.sh`).
6. Abre `server/YurOTS/ots/data/world/test.otbm` con el binario en `rme-zagan-test-root/build/rme`.

**Variables útiles:**

| Variable | Efecto |
|----------|--------|
| `SKIP_ZAGAN_SERVER_RESTART=1` | No reinicia Docker al abrir RME |
| `OPEN_RME_FAST=1` | No regenera todo el pack Zagan, solo sync RME |
| `MAP_OVERRIDE` | Ruta al `.otbm` (default: `test.otbm`) |

**Mapa editado:** `server/YurOTS/ots/data/world/test.otbm`  
**Spawns:** `server/YurOTS/ots/data/world/test-spawn.xml` (el servidor no lee monstruos del OTBM; hay que mantener spawns en XML o pintarlos y exportar).

---

## 1. Serpent Spawn (monstruo que no aparecía)

### Problema

Había spawns de `serpent spawn` en `test-spawn.xml` pero **no existía** el XML del monstruo → el servidor no los creaba.

### Solución

| Archivo | Cambio |
|---------|--------|
| `server/.../monster/serpent spawn.xml` | Creado: looktype 220, corpse 4323, ~2800 HP, ataques veneno/hydra |
| `server/.../monster/monsters.xml` | `<monster name="Serpent Spawn" file="serpent spawn.xml" />` |

**Spawns activos (6):**

- Z6: `90,193` y `92,202`
- Z8: `85,168`, `103,179`, `76,181`, `83,193`

### Loot añadido después

- **Magic turban** (server id `2663`) — chance ~1.4%
- **Nightglass dagger** (server id `20137`) — rare en bolsa ~0.45%
- Loot generoso previo: serpent sword, tower shield, BOH, giant sword, etc.

---

## 2. Magic turban (+1 ML)

- Item vanilla **mystic turban** (`2663`), tratado como **magic turban** en juego.
- Al equipar en cabeza: **+1 magic level** efectivo (`getEffectiveMagLevel`).
- Implementación en C++ (`player.cpp`, `const76.h` → `ITEM_MAGIC_TURBAN = 2663`).
- Descripción al mirar el item en `item.cpp`.

---

## 3. Nightglass dagger (item Zagan `20137`)

### Loot

Drop raro de Serpent Spawn (ver arriba).

### Imbuidos de velocidad (hasta 5)

- Gema: **big ruby** (`2156`) con la daga equipada.
- Stacks: +5%, +10%, +15%, +20%, +25% velocidad de ataque.
- Probabilidad de éxito: **90% → 80% → 70% → 60% → 50%** (−10% por stack).
- Action IDs dedicados: `9060`–`9064` (`ITEM_NIGHTGLASS_SPEED_AID` en `const76.h`).
- Lógica en `data/actions/scripts/gem_imbue.lua` + `player.cpp` (`imbueNightglassSpeed`).

### Animación al pegar

- Proyectil **Sudden Death** en melee.
- Impacto con efecto **mort area** y número violeta.
- `game.cpp` + `Player::wieldsNightglassDagger()`.

---

## 4. Hell Quest — Nimral `346, 168, 7`

### Contexto en el mapa

- **Nimral** en `346, 168, 7` (`npc.xml`).
- Un sqm al lado = zona Hell Quest.

### `boat.lua` (todos los Nimral, mismos destinos)

| Destino | Aterrizaje | Notas |
|---------|------------|-------|
| Elfland | `111 60 6` | no mueve temple |
| Epstein Island | `85 209 7` | no mueve temple |
| **Hell Quest** | `347 168 7` | un sqm a la derecha del Nimral; sin level requerido; no mueve temple |
| Dragon Land | `122 119 7` | no mueve temple |
| The City | `171 65 7` | no mueve temple |

- Hell Quest: 20 gp, sin requisito de level, free pueden viajar.
- El viaje no toca `masterPos` / temple.
- Si el player ya está exactamente en el sqm de destino, el NPC no cobra ni repite el viaje.
- Confirmación pulida: si responden otra cosa que no sea yes/si o no, el NPC repregunta.
- `Fargum` quedó en City en `171 66 7`; el aterrizaje de The City sigue en `171 65 7`, un sqm al norte.
- El viaje intencional cierra conversación antes del teleport para no reentrar al script del NPC.

**NPCs de barco en el mapa:** `Fargum 171,66,7` · `Nimral 122,117,7` · `Nimral 346,168,7` · `Nimral 85,210,7` · `Nimral 111,61,6`

---

## 5. Fix IDs Zagan — red carpet vs southern axe

### Problema

El builder (`build_zagan_test_assets.py`) **reutilizaba client IDs** de items del mapa para sprites nuevos. Al parchear `Tibia.dat`, el client id `4858` (red carpet) mostraba el sprite de **southern axe**, pero el mapa seguía usando server id `4398` → alfombras rotas.

Lo mismo afectaba flat roof, hawser, butterfly kit, etc.

### Causa técnica

- Cada item tiene **server id** (OTB, mapa, servidor) y **client id** (`.dat`, cliente/RME).
- El builder “sacrifica” client ids de items de 1 sprite y les pone el sprite nuevo.
- Si ese client id lo usa el mapa, **el tile cambia de aspecto** aunque el server id siga siendo “red carpet”.

### Solución en `scripts/build_zagan_test_assets.py`

1. **Escaneo de `test.otbm`** — todos los server ids en tiles, incluyendo nodos hijo `OTBM_ITEM` (no solo atributos en tile).
2. **Protección de client ids** usados por esos items en el OTB base.
3. **Rangos explícitos** de carpet: server `1794–1802` y `4394–4402`.
4. **Palabras clave** en nombres OTB: carpet, roof, hawser, ship, butterfly, etc.

Tras regenerar: **0 conflictos** entre items Zagan y tiles del mapa. Southern axe pasó a client id `4782` (ya no comparte con red carpet).

**Regenerar assets:**

```bash
python3 scripts/build_zagan_test_assets.py
./scripts/install-zagan-test-env.sh   # copia a cliente, RME y servidor
```

---

## 6. Servidor local — arranque y fallos

### Entorno

```bash
YUROTS_ITEMS_OTB=data/items/items-zagan-test.otb \
YUROTS_ITEMS_XML=data/items/items-zagan-test.xml \
docker compose up -d yurots
```

El mapa **requiere** `items-zagan-test.otb` (tiene items custom `20100+` pintados en el mapa). Con OTB base → error de formato o crash.

### Segfault al cargar mapa

**Síntoma:** `qemu: uncaught target signal 11` después de `Loading map from: OTBM`; cliente en “Connecting…” sin login.

**Causa:** Binario `server/YurOTS/ots/source/yurots` corrupto o ausente (p. ej. tras un `git restore` fallido del ejecutable).

**Fix:**

```bash
docker exec yurots bash -c 'cd /app/YurOTS/ots/source && make clean && make -j4'
YUROTS_ITEMS_OTB=data/items/items-zagan-test.otb \
YUROTS_ITEMS_XML=data/items/items-zagan-test.xml \
docker compose restart yurots
```

Esperar en logs: `:: Retro76 Server Running...`

### Cliente

```bash
./scripts/play-zagan-test-client.sh   # regenera + reinicia server + abre cliente
# o solo cliente (server ya arriba):
OTCLIENT_DIR=client-local-zagan-test ./scripts/play-yurots-client.sh
```

**Login test:** `275783` / `123456qa`

---

## 7. Rankings web (Top Axe / Club)

Fuera del editor, pero en la misma sesión:

- `web/data.py` — skills club (1) y axe (3).
- `web/index.html` — pestañas Club y Axe en panel Top.

---

## Archivos tocados (resumen)

| Área | Archivos |
|------|----------|
| Monstruo | `monster/serpent spawn.xml`, `monsters.xml`, `test-spawn.xml` |
| NPC / viajes | `npc.xml`, `npc/scripts/boat.lua` |
| Items / imbue | `const76.h`, `player.cpp`, `item.cpp`, `game.cpp`, `creature.h`, `gem_imbue.lua` |
| Builder Zagan | `scripts/build_zagan_test_assets.py`, `zagan-test/manifest.json` |
| Mapa | `test.otbm` (sin cambios directos en esta sesión; spawns en XML) |
| RME | `scripts/open-rme-zagan-terminal.command`, `rme-zagan-test-root/`, `rme-client-760-zagan-test/` |

---

## Checklist después de editar el mapa en RME

1. Guardar `test.otbm`.
2. Si agregaste **spawns** en RME → exportar o editar `test-spawn.xml`.
3. Si agregaste **items Zagan** nuevos → correr `build_zagan_test_assets.py` + `install-zagan-test-env.sh`.
4. Reiniciar Docker: `docker compose restart yurots` (OTB solo se carga al arranque).
5. Probar en cliente Zagan test que tiles del mapa (carpets, decoración) no se vean como armas/items custom.

---

## Referencias

- `docs/ZAGAN_TEST_HANDOFF.md` — handoff técnico del pack Zagan
- `docs/ZAGAN_TEST_ITEMS.md` — ids y comandos `/i`
- `docs/IMPORTAR_ITEM_DESDE_IMAGEN.md` — pipeline BMP/PNG → item en juego
- `zagan-test/manifest.json` — 55 items, server ids `20100–20154`
