# Cambios aplicados — "Sí a todo" (nov 2026)

Resumen de todo lo implementado a partir de las propuestas de `.propuesta-antigravity.txt`: ítems nuevos y set endgame reutilizando sprites 7.6 / Zagan existentes, correcciones críticas de loot, balance de monstruos nuevos/8.60 y creación de los 4 spots de caza restantes cerca de la city.

> **Estado:** todo aplicado solo en local. **No** se realizó compilación de C++, Docker, deploy, commit ni push. Todos los backups previos se preservaron.

---

## 1. Ítems nuevos y Sets Endgame (`items-zagan-test.otb` + Lua + C++)

Script idempotente de alta/actualización OTB: [`scripts/otb/apply-si-a-todo-items.py`](../../scripts/otb/apply-si-a-todo-items.py).
Todos los ítems reutilizan `client_id` ya existentes en el cliente 7.6 / Zagan (sin modificar `Tibia.dat`/`Tibia.spr` ni inventar IDs inexistentes).

### 1.1 Ítems nuevos agregados en `items-zagan-test.otb` (`20372`–`20374`)

> **IDs:** al principio se usaron `20369`–`20371`, pero `main` ya los había ocupado con la Frost Mine (`20369` runa, `20370` fuego). Antes del merge se pasaron a `20372`–`20374` en el script OTB, el loot y este doc; el OTB se regeneró con el script sobre el de `main`.

| Server ID | Nombre | Client ID reutilizado | Prototipo | Stats / Efecto | Drop |
|---:|---|---:|---|---|---|
| `20372` | **aurora blade** | `3284` (ice rapier) | `2407` bright sword | Sword 1H, **atk 36 / def 30**, 28 oz; **1250 ms** de ataque (ya activo en `player.cpp` por nombre) | Frost Dragon (0,45 %), Ice Spider (0,35 %) |
| `20373` | **aurora axe** | `3335` (twin axe) | `2430` knight axe | Axe 1H, **atk 34 / def 22**, 52 oz; **1250 ms** de ataque (ya activo en `player.cpp` por nombre) | Frost Dragon (0,45 %), Ice Monk (0,30 %), Crystal Spider (0,25 %) |
| `20374` | **frostbound bow** | `3350` (bow) | `2456` bow | Bow 2H, **+1 attack** a flechas (ya activo en `player.cpp:320-323`), 31 oz | Elvenbane Ranger (0,80 %), Frost Dragon (0,40 %), Crystal Spider (0,25 %) |

### 1.2 Set Endgame de Mago (*Starbinder / Arcane*) — sprites Zagan propios ya presentes en el cliente

| Server ID | Nombre | Slot | Stats OTB | Bonus C++ (al compilar) | Drop |
|---:|---|---|---|---|---|
| `20118` | **starbinder hood** | Cabeza | Arm 6, 18 oz | Sorc/Druid: **+1 ML** y **−5 % daño elemental** | Elven Archmage (0,50 %), Dark Mage (0,45 %), Warlock (0,30 %) |
| `20148` | **kilnfire leggings** | Piernas | Arm 8, 28 oz | Sorc/Druid: **+1 ML** y **−5 % daño elemental** | Metal Dragon (0,45 %), Fury (0,40 %), Hellhound (0,25 %) |
| `20129` | **wayfarer boots** | Pies | Arm 2, 9 oz (imbuible con Yellow Gem en `gem_imbue.lua`) | **+20 speed** y **−5 % daño elemental** | Frost Dragon (0,50 %), Wyrm (0,45 %), Vampire Bride (0,35 %) |
| `20149` | **mosaic shield** | Escudo | Def 33, 34 oz | **−6 % daño elemental** | Metal Hydra (0,45 %), Dark Hydra (0,35 %), Quara Hydromancer (0,30 %) |

### 1.3 Set Endgame de Metal (*Machina / Obsidian*) — identidad para familia Metal

| Server ID | Nombre | Slot | Stats OTB | Bonus C++ (al compilar) | Drop |
|---:|---|---|---|---|---|
| `20152` | **fox machina helmet** | Cabeza | Arm 10, 42 oz | **−6 % daño elemental** | Metal Demon (0,60 %), Metal Dragon (0,45 %) |
| `20104` | **basalt greaves** | Piernas | Arm 9, 65 oz | **−5 % daño físico** | Metal Demon (0,55 %), Metal Hydra (0,45 %), Behemoth (0,25 %) |
| `20147` | **obsidian regalia** | Armadura | Arm 16, 78 oz (sidegrade a MPA sin power creep) | **−6 % daño elemental** | Metal Demon (0,40 %), Wrath (0,25 %) |
| `20151` | **sunforge shield** | Escudo | Def 36, 32 oz | **−5 % daño elemental** | Ashen Lord (1,00 %), Metal Dragon (0,40 %) |

### 1.4 Otros equipos Zagan activados y consumibles de bosses (100 % Lua, sin pisar premium `20131`/`20132`)

| Server ID | Nombre | Tipo / Efecto | Drop |
|---:|---|---|---|
| `20120` | **boltworker crossbow** | Crossbow 2H, **+1 attack** a bolts (activo ya en `player.cpp`, puente entre Crossbow y Arbalest) | Imperial Hero (0,45 %), Wyrm (0,35 %), Worker Golem (0,35 %) |
| `20153` | **frostwarden aegis** | Escudo Def 32, 42 oz | Frost Dragon (0,55 %), Crystal Spider (0,35 %), Quara Pincher (0,25 %) |
| `20102` | **morlen crest** | Casco Arm 9, 38 oz | Root Colossus (0,60 %), Quara Predator (0,45 %), Wyrm (0,40 %) |
| `20124` | **azure sunstone** | Consumible Lua ([`soft_boots_recharge.lua`](../../server/YurOTS/ots/data/actions/scripts/soft_boots_recharge.lua)): recarga **worn soft boots (`3550`) → soft boots (`3549`)** (4 h) | Ashen Lord, Orshabaal, The Fallen Emperor, Lord of Elvenbane, Demodras, Wrath |
| `20125` | **verdant sunstone** | Consumible Lua ([`verdant_sunstone.lua`](../../server/YurOTS/ots/data/actions/scripts/verdant_sunstone.lua)): restaura HP y maná al máximo (cooldown 60 s) | Ashen Lord, Orshabaal, The Fallen Emperor, Lord of Elvenbane, Demodras, Custodio del Lago, Capataz de Hierro |

**Hooks C++ editados (sin compilar):**
- `server/YurOTS/ots/source/const76.h`: constantes `ITEM_STARBINDER_HOOD`..`ITEM_SUNFORGE_SHIELD` (sin cambios de ABI/struct en `Creature`/`Player`).
- `server/YurOTS/ots/source/player.cpp`: `+1 ML` en `Starbinder Hood` y `Kilnfire Leggings` (Sorc/Druid), `+20 speed` en `Wayfarer Boots`, y llamada a `checkBoh()` al mover `SLOT_LEGS`.
- `server/YurOTS/ots/source/game.cpp`: reducciones elementales/físicas en `GameState::applyAmulets()` siguiendo el mismo patrón que `Imperial/Sapphire Crown Armor`.
- `server/YurOTS/ots/source/item.cpp`: descripciones completas al hacer look.

---

## 2. Correcciones de loot, supplies y balance de monstruos

Script aplicado: [`scripts/monsters/apply-si-a-todo-balance.py`](../../scripts/monsters/apply-si-a-todo-balance.py) (64 monstruos base actualizados) + regeneración de 35 familias Rage (105 variantes `Angry`/`Furious`/`Enraged`) con `scripts/monsters/rage-variants.py --write --only ...` (sin pisar las 42 familias Rage históricas hechas a mano).

### 2.1 Errores críticos de loot y bugs corregidos

- **Quara Predator:** eliminados `2390` (*Magic Longsword*, 0,69 %) y `2496` (*Horned Helmet*, 0,39 %); reemplazados por loot coherente con su nivel (Platinum Coin, Power Bolt, Avalanche Rune, Warrior Helmet, Tower Shield, Morlen Crest, Giant Sword).
- **Thornback Tortoise:** eliminados dos `2391` (*War Hammer*, uno al 15,98 %!); reemplazados por Plate Shield y Battle Shield.
- **Earth Elemental:** eliminado `2546` (*Burst Arrow* ×30 al 20 %!) y deduplicadas tres entradas de `1294` (*Small Stone*); agregados Stone Shower, Small Emerald, Scale Armor y Plate Shield.
- **Worker Golem:** deduplicados 3× War Hammer, 2× Might Ring y 2× Small Diamond; agregados Stone Shower, Steel Shield y Boltworker Crossbow.
- **Chakoya Windcaller (84 HP):** eliminado `2656` (*Blue Robe*); reemplazado por Cape e Icicle Rune.
- **Elder Beholder:** corregido `<summon name="baby beholder"/>` (inexistente) → `gazer`; balanceado de 1100 HP / 290 exp a **700 HP / 580 exp**, arm/def 25/25, melee 0–110, con loot de beholder/mago (Beholder Shield, Spellbook, Wand of Plague, HMM, Hat of the Mad).
- **Zombie:** corregido `2205` (anillo activo) → `2168` (*Life Ring* normal).
- **Wyrm & Nightstalker:** retirados ítems mal mapeados de 8.60 (`2455`/`2456`/`2654`/`2657` en Wyrm; `2391` en Nightstalker) y reemplazados por loot temático coherente.
- **Ice Spider y 7 monstruos clásicos (+12 variantes Rage):** limpiadas líneas muertas `<item id="0"/>`.
- **Stacks de oro `countmax > 100`:** partidos en stacks `<= 100` en todos los monstruos base actualizados para evitar el recorte silencioso de `monsters.cpp`.

### 2.2 Balance de monstruos nuevos / 8.60

| Monstruo | Antes | Después | Motivo |
|---|---|---|---|
| **Quara Predator** | arm/def 45/45, melee 40–320, exp 1600 | arm/def **38/38**, melee **40–270**, exp **1800** | Melee y armadura excesivos frente a su exp |
| **Quara Pincher** | arm/def 50/50, exp 1200 | arm/def **38/38**, exp **1350** | Armadura casi de Demon en mob mid-high |
| **Quara Mantassin** | arm/def 15/15, exp 400 | arm/def **18/18**, exp **500** | Ratio exp/HP muy bajo (0,50) |
| **Tortoise / Thornback** | arm/def 30/30 y 40/40 | arm/def **16/18** y **22/24** | Armadura de dragón en mobs lv 10–15 |
| **Undead Gladiator** | arm/def 45/45 | arm/def **32/34** | Armadura mayor que un Dragon Lord |
| **Ice Spider** | arm/def 40/40, melee 140–340, exp 1400 | arm/def **32/34**, melee **100–260**, exp **1550** | Pegaba más fuerte que un Frost Dragon por 1000 exp menos |
| **Red Kongra** | HP 600, exp 230, arm/def 8/11 | HP **550**, exp **340**, arm/def **18/20** | Ratio exp/HP muy bajo (0,38) |
| **Mutated Tiger** | melee 80–260, exp 750 | melee **65–220**, exp **850** | Melee demasiado alto para su rango |
| **Bog Raider** | exp 800 | exp **950** | Drena vida + se cura + área (1300 HP) |
| **Pirate Corsair / Dragon Hatchling** | exp 350 / exp 185 (arm 18/20) | exp **450** / exp **230** (arm **16/18**) | Alinear exp/HP con su dificultad real |

### 2.3 Nuevos loots temáticos distribuidos

- **Supplies de hunt:** Avalanche (`2274`), Icicle (`2271`), Thunderstorm (`2315`), Stone Shower (`2288`), Holy Missile (`2295`), Magic Wall (`2293`), Wild Growth (`2269`), Anchor (`2296`), Crimson Cage (`20273`), SD (`2268`), Power Bolt (`2547`).
- **Hueco de Mago y Paladín:** Enchanted Spear (`20156` en Imperial Hero, Wyrm, Serpent Spawn), nuevas fuentes de Crystal Arrow (`2352` en Elven Archmage, Lord of Elvenbane, Orc Warlord), Tempest Rod (`2183` en Quara Hydromancer, Dark Hydra), Hat of the Mad (`2323` en Warlock, Dark Mage, Banshee, Elder Beholder, Vampire Bride), Boltworker Crossbow (`20120`), Frostbound Bow (`20374`), set Starbinder.
- **Joyería y gemas faltantes:** Axe Ring (`2208` en Orc Warlord, Behemoth, Dwarf Guard, Capataz de Hierro), Stone Skin Amulet (`2197`), Elven Amulet (`2198`), Dragon Necklace (`2201`), Yellow Gem (`2154`), más gemas pequeñas en la familia Metal.
- **Exclusivos preservados:** no se agregaron ultra-rares (Blessed Shield, Golden Helmet, DSL, Soft Boots, AOL), armas 8.x de Pozos del Infierno ni armas de El Crisol a mobs comunes.

---

## 3. Cuatro spots de caza nuevos cerca de la city

Los spots 1, 2 y 3 (Alcantarilla Mutada, Nido de Seda Negra y Cripta de los Ojos) ya estaban creados y desplegados en la sesión previa ([`MAPEAR_HUNTS_CITY.md`](../items-and-map/MAPEAR_HUNTS_CITY.md)). Ahora se completaron los **spots 4, 5 y 6 (ambas variantes de superficie)**, cada uno con generador determinista e idempotente, manifiesto JSON, carteles en `readables.xml`, teleports `/ir` en `gmplaces.xml` y backups en `backups/map/`:

| # | Zona | Entrada | `/ir` (GM) | Pisos | Nivel | Casillas | Spawns / Monstruos | Generador |
|---|---|---|---|---|---:|---:|---|---|
| 4 | **Gruta Submarina del Río** | `176,58,7` (camino del muelle, cartel `177,58,7`) | `/ir grotto` | z8–z11 acceso · z12 | 45–75 | 1.037 | 23 mobs (dens. 45,1): Blood Crab ×2, Quara Constrictor ×1, Water Elemental ×11, Quara Hydromancer ×6, Bog Raider ×3 | `scripts/map/generate-river-grotto.py` |
| 5 | **Demona Local (Warlocks y Behemoths)** | `119,129,7` (oeste de Torre del Mago Oscuro, cartel `118,128,7`) | `/ir demona` | z8–z11 acceso · z12 (2 alas) | 75–120+ | 1.157 / 1.226 | 41 mobs: **Ala de Piedra** (Cyclops Smith ×2, Stone Golem ×2, Behemoth ×16, Wyrm ×5) · **Ala Arcana** (Priestess ×3, Necromancer ×2, Warlock ×11 sueltos a sep. 13) | `scripts/map/generate-demona-local.py` |
| 6a | **Campamento de Amazonas** | `75,33,7` (puente norte al oeste del Castillo Imperial, cartel `74,34,7`) | `/ir amazons` | z7 (isla nueva) | 15–30 | 233 | 18 mobs (dens. 12,9): Amazon ×11, Valkyrie ×5, Assassin ×2 | `scripts/map/generate-amazon-camp.py` |
| 6b | **Campamento Bárbaro** | `222,24,7` (costa nevada NE, cartel `224,25,7`) | `/ir barbarians` | z7 (cabo nevado) | 15–40 | 342 | 20 mobs (dens. 17,1): Barbarian Headsplitter ×4, Skullhunter ×6, Brutetamer ×5, Bloodwalker ×4, Frost Giant ×1 | `scripts/map/generate-barbarian-camp.py` |

Revisión visual de la gruta (22 nov): [arena, agua animada y corales](../items-and-map/RIVER_GROTTO.md), conservando recorrido y spawns.

*(También se corrigió el relleno de roca `[101]` en `generate-mutated-sewers.py` y `generate-spider-nest.py` para que los 7 generadores vecinos convivan con `changed: 0` en `--dry-run`.)*

---

## 4. Validaciones ejecutadas

- `python3.11 scripts/map/check-map-load.py` → `test.otbm con items-zagan-test.otb: 0 errores`.
- `python3.11 scripts/map/check-upper-view.py` en Gruta Submarina (`z8–z12`) y Demona Local (`z8–z12`) → `OK: desde ninguna casilla se ve el piso de arriba`.
- `python3.11 scripts/map/scan-map-depots.py` → **11 lockers (`depotid=1`) intactos**.
- `python3.11 scripts/map/sync-houses-with-map.py --dry-run` → `houses.xml ya coincide con el mapa`.
- **Idempotencia (`--dry-run`):** `changed: 0` en los 4 generadores nuevos y en los 3 previos (`mutated-sewers`, `spider-nest`, `beholder-crypt`).
- **XML bien formados:** 549/549 archivos XML validados (`actions.xml`, `gmplaces.xml`, `readables.xml`, `test-spawn.xml`, `monsters.xml` y todos los `data/monster/*.xml`) → **0 errores**.
- **OTB vs `Tibia.dat`:** 5.250 ítems cargados, 0 `client_id` fuera de rango, 0 errores de sintaxis `stackable`, 0 `id="0"`, 0 summons inexistentes, 0 anillos activos en loot.
- **Spawns en casillas libres:** los 102 monstruos de los 4 spots nuevos (23 + 41 + 18 + 20) y los 4 destinos `/ir` verificados sobre tiles transitables, sin objetos bloqueantes (`block_solid` / `block_pathfind`) y sin flags de casa/PZ.

---

## 5. Qué quedó pendiente

1. **Compilar C++ (en la ThinkPad, con OK de Gonzalo):** los cambios en `const76.h`, `player.cpp`, `game.cpp` e `item.cpp` activan los bonus de `+1 ML`, `+20 speed` y reducciones de daño elemental/físico de los sets *Starbinder* y *Machina*, además de sus descripciones al hacer look. *(Nota: Aurora Blade/Axe, Boltworker Crossbow, Frostbound Bow, los stats base del OTB y las acciones Lua de Azure/Verdant Sunstone ya funcionan sin recompilar.)*
2. **Pruebas in-game antes de deployar:**
   - Levantar el OT local y validar con `python3 scripts/ot/ot-probe.py 127.0.0.1 7171`.
   - Probar el locker del templo in-game (regla §2.10 de `AGENTS.md` / `docs/gameplay/DEPOTS.md`).
   - Recorrer `/ir grotto`, `/ir demona`, `/ir amazons` y `/ir barbarians` (bajar y subir todas las escaleras `469`/`1386`, verificar puentes y costas).
   - Probar `/i` y `/loot` de los ítems nuevos (`20372`–`20374`, sets `20102`/`20104`/`20118`/`20120`/`20124`/`20125`/`20129`/`20147`–`20153`) y las acciones Lua de `azure sunstone` (`20124` sobre `3550`) y `verdant sunstone` (`20125`).
3. **Minimapa y web (opcional post-aprobación):** si se despliega el mapa nuevo, regenerar `minimap.otmm` para `clienteretro` (no hace falta tocar `Tibia.dat`/`Tibia.spr` porque se reutilizaron sprites ya existentes) y actualizar catálogos web (`/items`, `/items-nuevos`, `MONSTRUOS.md`) si se desea.
4. **Commit, push y deploy a la ThinkPad:** pendientes del OK explícito de Gonzalo siguiendo `docs/systems/THINKPAD_TEST_SERVER.md`.
5. **Detalle menor en 6 variantes Rage históricas:** `angry/furious/enraged hydra.xml` y `angry/furious/enraged serpent spawn.xml` conservan su `countmax="250"`/`180` original en oro (no se sobrescribieron para preservar sus drops hechos a mano; el motor los acota a 100 al cargar).
