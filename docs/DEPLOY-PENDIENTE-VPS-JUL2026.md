# Deploy pendiente VPS — julio 2026 (gameplay Zagan + fixes)

> **Estado:** en curso — commit con mapa, Fury, items Zagan y gameplay C++.  
> **Último deploy en producción:** `7312baf8` — *Deploy julio 2026: Zagan items, mapa, updater web y descargas cliente.*  
> **Backup pre-deploy hecho:** `pre-zagan-gameplay` — VPS `20260707-234114` (74 cuentas, 83 players). Espejo Mac: `~/ot-backups/vps-pre-zagan-gameplay-20260707-234114`.

## Decisión de producto

**Sí — queremos llevar al VPS todos los cambios de código y gameplay listados abajo.**

El VPS ya tiene desde el deploy anterior:

- `items-zagan-test.otb` / `items-zagan-test.xml` (Docker: `YUROTS_ITEMS_OTB` / `YUROTS_ITEMS_XML`)
- Mapa `test.otbm` del commit `7312baf8`
- Cliente/updater con sprites Zagan

Lo que **falta** en producción es sobre todo **lógica C++** y scripts asociados: en el VPS hoy no hay `ITEM_CRIMSON_*`, `refreshHeadSkillBonus`, private trainers, fix de spawn, ni desintegrate corregido.

### Alcance ampliado (jul 2026 — acordado en chat)

Además del gameplay C++, **sí va al VPS**:

| Incluir | Archivos |
|---------|----------|
| Mapa editado | `data/world/test.otbm`, `data/world/test-spawn.xml` (+ spawns Fury) |
| Monstruo Fury | `data/monster/fury.xml`, entrada en `monsters.xml` |
| Items Zagan | `data/items/items-zagan-test.otb` (parches helmet/cape/medusa) |
| Viaje laberinto | `data/npc/scripts/boat.lua`, `data/world/npc.xml` (Nimral en Alice Maze) |

### Restricciones que siguen vigentes

| No tocar | Motivo |
|----------|--------|
| **`houseitems.xml`** runtime | El deploy lo preserva del backup |
| Depots en **`players/*.xml`** | Data sagrada; `deploy-vps.sh` restaura desde backup |
| Artefactos locales | `.bak`, `test 2.otbm`, cores, logs, scripts `patch-map-depot-ids.py` |

`houses.xml` **no cambia** en este commit; `sync-houses-with-map.py --dry-run` debe pasar antes del deploy.

---

## Qué va al VPS (inventario completo)

### 1. Items Zagan — lógica C++ (prioridad alta)

Sin esto los items existen en OTB pero no funcionan bien en prod.

| Item | ID | Archivos | Comportamiento |
|------|-----|----------|----------------|
| Crimson Helmet | `20113` | `player.cpp/h`, `creature.cpp/h`, `ioplayerxml.cpp`, `const76.h`, `item.cpp` | +1 sword/club/axe/distance para knight/paladin (incl. promoted). `refreshHeadSkillBonus()` + lectura en vivo de `SLOT_HEAD`. UI actualiza al equipar/desequipar. |
| Crimson Wand | `20123` | `game.cpp/h`, `player.cpp`, `const76.h`, `item.cpp` | Wand real: sorc/druid lv33+, dmg 55–65, mana 13, range 5, delay 667 ms, animación adori gran. Incluye Master Sorcerer / Elder Druid. |
| Fury Cape | `20114` | `player.cpp`, `game.cpp`, `item.cpp` | Bonus ML en armor slot (misma familia voc que helmet). |
| Medusa Sword | `20105` | `game.cpp`, `item.cpp` | Lógica de combate custom del arma. |
| Sword of Silence | `20139` | `game.cpp`, `creature.h/cpp`, `item.cpp`, `const76.h`, OTB patch | 10% silencio PvP 2–3s (spells hablados); CD 12s/target; atk 42. **Local only** hasta autorización. |

Constantes en `server/YurOTS/ots/source/const76.h`:

```cpp
ITEM_MEDUSA_SWORD = 20105,
ITEM_CRIMSON_HELMET = 20113,
ITEM_FURY_CAPE = 20114,
ITEM_CRIMSON_WAND = 20123,
ITEM_SWORD_OF_SILENCE = 20139,
```

**Rebuild obligatorio** en VPS (el script de deploy compila dentro del container). Si se tocó `creature.h`, preferir `make clean && make` local antes de confiar en el build.

### 2. Private Trainer Dummy (`20118`)

| Pieza | Ruta |
|-------|------|
| C++ persistencia | `source/private_trainers.cpp`, `source/private_trainers.h` (archivos nuevos) |
| Boot | `source/otserv.cpp` — carga `private_trainers.xml` |
| Actions | `source/actions.cpp/h`, `data/actions/actions.xml`, `data/actions/scripts/private_trainer_dummy.lua` |
| Monster | `data/monster/private trainer dummy.xml`, entrada en `data/monster/monsters.xml` |
| Doc | `docs/gameplay/PRIVATE_TRAINER_DUMMY.md` |

`private_trainers.xml` es **runtime** (gitignored). Si no existe en VPS, el boot **sigue** (`Load()` retorna `true` con archivo ausente). El deploy lo incluye en backup/restore cuando exista.

### 3. Fix respawn — anti-duplicación por kiteo

| Archivo | Cambio |
|---------|--------|
| `source/spawn.cpp` | El slot de spawn sigue ocupado aunque el monstro se aleje del área; evita duplicados vivos. |
| Doc | `docs/gameplay/RESPAWN_SYSTEM.md` (ya documenta el fix del `2026-07-06`) |

### 4. Rune Desintegrate — fix C++

| Archivo | Cambio |
|---------|--------|
| `source/spells.cpp`, `source/spells.h` | Targets legacy (magic wall, wild growth, muebles, etc.), `addressOfSpell` como light userdata, helpers de tile. |
| Doc | `docs/gameplay/DESINTEGRATE_RUNE.md` |

### 5. Comando GM `/ips`

| Archivo | Cambio |
|---------|--------|
| `source/commands.cpp/h` | Implementación del comando |
| `data/commands.xml` | Registro `access="2"` |

### 6. Quest chests — items Zagan

| Archivo | Cambio |
|---------|--------|
| `data/actions/scripts/quest.lua` | Rango `uniqueId` `20100–20199` para premios custom (además de `1001–4999` vanilla). |

### 7. OTB

| Archivo | Notas |
|---------|-------|
| `data/items/items-zagan-test.otb` | Diff pequeño vs prod (`193113 → 193229` bytes). Incluir si hay correcciones de slot/atributos posteriores al deploy anterior. |

### 8. Web (opcional en el mismo deploy)

Cambios locales desde `7312baf8` en `web/index.html`, `web/server.py`, `web/premium_orders.py`. Incluir si el release de julio los tenía pendientes; no bloquean gameplay OT.

### 9. Documentación de agentes

| Archivo | Contenido |
|---------|-----------|
| `AGENTS.md` | Patrones vocaciones promovidas, `refreshHeadSkillBonus`, pitfalls rebuild. |

---

## Qué NO va en este deploy

| Archivo / carpeta | Motivo |
|-------------------|--------|
| `data/world/test.otbm.*.bak`, `test 2.otbm`, `test-rme.otbm` | Artefactos locales |
| `data/world/test-house*.xml`, `data/houses.xml.bak` | Backups locales |
| `scripts/patch-map-depot-ids.py`, `scripts/scan-map-depots.py` | Herramientas de lab, no runtime |
| `server/YurOTS/ots/source/yurots` | Binario — se compila en VPS |
| `cores/`, `*.log`, `Tibia.dat` / `Tibia.spr` en raíz | Artefactos locales / cliente |

---

## Checklist pre-deploy

- [x] Backup runtime VPS: `BACKUP_LABEL=pre-zagan-gameplay ./scripts/backup-runtime-data.sh --vps`
- [ ] Smoke test local: `bash scripts/test-local-smoke.sh`
- [ ] Probe local OK: `python3 scripts/ot-probe.py 127.0.0.1 7171`
- [ ] Probar in-game local: crimson helmet equip/unequip, crimson wand, fury cape, medusa (según tengan items)
- [ ] Commit **selectivo** (ver sección siguiente) — **sin** `test.otbm` ni casas
- [ ] Push a `main` (autorización del usuario)
- [ ] Deploy: `DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh` en el VPS
- [ ] Post-deploy: probe, conteo cuentas/players, logs sin error de casas

---

## Estrategia de commits sugerida

Un solo commit lógico o dos, pero **nunca** mezclar mapa con gameplay:

```text
fix(gameplay): Zagan items C++, private trainers, spawn y desintegrate

Incluye:
- server/YurOTS/ots/source/{const76,creature,game,item,ioplayerxml,player,spawn,spells,actions,commands,otserv,private_trainers}.*
- server/YurOTS/ots/data/actions/{actions.xml,scripts/quest.lua,scripts/private_trainer_dummy.lua}
- server/YurOTS/ots/data/commands.xml
- server/YurOTS/ots/data/monster/{monsters.xml,private trainer dummy.xml}
- server/YurOTS/ots/data/items/items-zagan-test.otb  (si aplica)
- AGENTS.md
- docs/DEPLOY-PENDIENTE-VPS-JUL2026.md
```

Excluir explícitamente del `git add`: `test.otbm`, `houses.xml`, `test-spawn.xml` (hasta validar coordenadas), binarios, backups, cores.

---

## Qué hace el deploy (y por qué es seguro para DP/casas)

Ver [`scripts/README-DEPLOY-VPS.md`](../scripts/README-DEPLOY-VPS.md). Resumen:

1. Backup `players/`, `accounts/`, `houseitems.xml`, `private_trainers.xml`, etc.
2. `git pull origin main` — solo trae lo commiteado (sin mapa si no lo incluimos)
3. Restaura runtime con `cp -an` — **no pisa** depots en XML ni items en casas
4. Rebuild C++ en Docker + restart
5. `sync-houses-with-map.py --dry-run` — valida; no modifica
6. Healthcheck puerto 7171

Si el pull **no** cambia `test.otbm`, el mapa en prod queda idéntico → depots y tiles de casas intactos.

---

## Verificación post-deploy

```bash
# Desde Mac
python3 scripts/ot-probe.py 64.176.20.238 7171

# En VPS
docker logs yurots --tail 40
# Buscar: sin "Could not load houses", sin fallo en private_trainers.xml
```

Comparar conteos con backup `pre-zagan-gameplay`:

- Cuentas: **74**
- Players: **83**

Pruebas in-game (con items Zagan en mano o vía GM):

- Crimson Helmet: skills suben al equipar y bajan al sacar (knight/paladin promoted incluidos)
- Crimson Wand: ataca con proyectil, consume mana
- Fury cape / Medusa: según diseño
- Private trainer `20118` en casa (si se distribuye el item)
- Desintegrate sobre magic wall / wild growth

**Cliente:** no debería hacer falta nuevo parche si el deploy de julio ya publicó sprites Zagan; estos cambios son servidor.

---

## Rollback

Si algo falla después del deploy:

1. **No** usar `git stash -u` ni `git reset --hard` en el VPS.
2. Restaurar runtime desde `~/ot-backups/pre-deploy-FECHA/` o desde `pre-zagan-gameplay`.
3. Revertir commit en `main` y volver a deployar, o restaurar binario anterior desde backup del script.

---

## Referencias

- Items Zagan (pack): [`items-and-map/ZAGAN_TEST_ITEMS.md`](items-and-map/ZAGAN_TEST_ITEMS.md)
- Private trainer: [`gameplay/PRIVATE_TRAINER_DUMMY.md`](gameplay/PRIVATE_TRAINER_DUMMY.md)
- Respawn: [`gameplay/RESPAWN_SYSTEM.md`](gameplay/RESPAWN_SYSTEM.md)
- Desintegrate: [`gameplay/DESINTEGRATE_RUNE.md`](gameplay/DESINTEGRATE_RUNE.md)
- Deploy seguro: [`../scripts/README-DEPLOY-VPS.md`](../scripts/README-DEPLOY-VPS.md)
- Agentes / pitfalls C++: [`../AGENTS.md`](../AGENTS.md)
