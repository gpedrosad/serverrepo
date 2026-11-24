# Simulación de Loot (1.000 kills) y Balance — Retro76

> Auditoría completa de los **544 monstruos** registrados en `server/YurOTS/ots/data/monster/monsters.xml`
> (**213 activos base/boss**, **9 inactivos**, **4 trainers** y **318 variantes Rage**), simulando **1.000 muertes**
> de cada criatura con las reglas exactas del motor C++ actual (`monsters.cpp`, `items.cpp`, `config.lua`).
>
> **Estado actual (nov 2026, post-ajustes):** **0 advertencias XML/C++** (antes 14 en `main`) y **0 familias Rage invertidas** `Furious > Enraged` (antes 36).

---

## 1. Metodología y reglas reales del motor simuladas

### 1.1 Reglas de loot fieles a C++ (`monsters.cpp` + `config.lua`)

La simulación ejecuta un Monte Carlo determinístico (`seed = 20261122`, **1.000 kills** por criatura) replicando línea por línea `MonsterType::createLoot` / `createLootItem` y `Monsters::loadLootItem` con la configuración vigente:

| Parámetro / Regla C++ | Valor / Comportamiento real |
|---|---|
| `lootmul` / `fixlootchance` | `1` / `1` (chances exactas del XML sobre `CHANCE_MAX = 100.000`) |
| `goldlootfloorpercent` | `70%` — las pilas de monedas (`2148`, `2152`, `2160`) con `countmax > 1` caen entre `ceil(0.70 × countmax)` y `countmax` |
| **Oro duplicado en C++** | `monsters.cpp:384` multiplica `ITEM_COINS_GOLD` (`2148`) **×2** tras la tirada (ej. `countmax=100` da 140–200 gp) |
| **Equipos raros a la mitad** | `isRareEquipmentLootItem()` (`monsters.cpp:156`) **divide la chance `/2`** para armas `atk ≥ 30`, escudos `def ≥ 28`, armaduras `arm ≥ 10`, cascos `arm ≥ 7`, legs `arm ≥ 6`, botas `arm ≥ 3` o con speed, y la lista fija (BOH, MPA, DSM, Crown/Golden set, etc.) |
| **Contenedores (`<inside>`)** | El contenido solo se tira si primero cae la bolsa (`1987`/`1988`) según su propia `chance` |
| **Límite `countmax ≤ 100`** | `loadLootItem()` recorta cualquier `countmax > 100` a `100` (ya corregido en todos los XML: **0 recortes activos**) |
| **Golden Ring (`2179`) bloqueado** | `createLootItem()` devuelve `NULL` para `2179` (ya reemplazado en `Lich` y `Orc Warlord` + Rage) |
| **Multiplicador de gemas Rage (borrado)** | `getRageGemChancePercent` comparaba contra `"angry "`/`"furious "`/`"enraged "` en minúsculas y los XML usan mayúscula, así que nunca se aplicó. El escalado Enraged > Furious está en los XML y en `scripts/monsters/rage-variants.py`; el código muerto se borró el 24 nov 2026 (la simulación no cambia) |
| **Cuenta base simulada** | **Free sin Golden Ring**. Con **Premium** la chance sube **+10%** (`premmylootbonus = 10`) y con **Golden Ring** el oro en monedas sube **+20%** |

### 1.2 Cómo se valora el loot

Cada monstruo muestra **tres cifras de valor** para 1.000 kills:

1. **Oro 1k**: monedas puras (`gold coin`, `platinum coin`, `crystal coin`) convertidas a `gp`.
2. **NPC Líq. 1k**: **Oro + todos los ítems vendibles a NPC** con precio exacto de `loot.lua` (**Mad**) y `parived.lua` (**Parived**). Liquidez 100% garantizada.
3. **Total Aprox. 1k**: **NPC Líquido + valor estimado conservador** de drops útiles o raros que **Mad/Parived no compran** (anillos, wands/rods, perlas, munición/runas, equipo clásico sin NPC y raros custom Retro76/Zagan). Comida, bolsas y basura valen `0 gp`. Ver **Apéndice A**.

### 1.3 Nota de Dificultad (0.0 a 10.0)

Combina supervivencia efectiva (**EHP**: HP ajustado por `armor`, `defense` y curación propia) y peligro ofensivo (**DPS sostenido** de melee + distancia + hechizos evaluados con `level`/`maglevel` reales del monstruo, más **Burst máximo** en un turno, **Mana Drain**, **Summons**, **Paralyze/Root**, **Invisibilidad**, **Haste/Velocidad**, **Kiteo a distancia** e **Inmunidades**).

---

## 2. Correcciones y ajustes de balance aplicados (nov 2026)

### 2.1 Bugs críticos corregidos

| Problema detectado | Corrección aplicada | Efecto (esperado en 1.000 kills) |
|---|---|---|
| **36 familias Rage** tenían `Furious > Enraged` | Actualizado `scripts/monsters/rage-variants.py` (gemas superiores + Gold Nugget 2× en `Enraged`), regeneradas las 60 familias curadas y parcheadas las 46 históricas (preservando todos los raros custom `20000+`/`2352`) | **0 familias invertidas** (ej. Demon: `1.18M → 1.50M → 3.04M → 4.11M`) |
| **Demodras** (`14.100 HP`) tenía bolsa `1987` al `6.67%` | Bolsa subida a `100%` y raros ajustados al rango de boss (DSM, RH, Dragon Lance, Sapphire Crown Armor, platinum) | `495.9k NPC / 861k Total` (`0.06 gp/HP`) → **`2.91M NPC / 3.51M Total`** (`0.25 gp/HP`) |
| **Hydra Rage y Serpent Spawn Rage** (6 XML) tenían oro `countmax > 100` (`250`/`180`) recortado por C++ | Sincronizados con sus bases en pilas ≤ 100 | **0 recortes** en `loadLootItem()` |
| **Lich y Orc Warlord (+ Rage)** (8 XML) tenían `Golden Ring (2179)` bloqueado en C++ | Reemplazado por `Platinum Amulet` + platinum (Lich) y `Knight Axe` / `Knight Armor` / `Crusader Helmet` (Orc Warlord) | Lich y Orc Warlord (+ Rage) sin drops muertos |
| **Angry / Furious / Enraged Demon** eran más lentos que `Demon` base (`228/234/244` vs `245`) | Velocidades sincronizadas a **`263 / 269 / 279`** (`245 + 18/24/34`) | Progresión de velocidad coherente |
| **Elephant** dropeaba `2973` (`dead orc rider`) y `514 gp` en 1k kills | Reemplazado por `3956` (`elephant tusk`) + `2148` (`25 @ 80%`) | `514 gp` → **`71.9k`** (`0.22 gp/HP`) |
| **Demon Skeleton y Minotaur Archer** tenían líneas rotas `id="0000"` | Eliminadas las entradas inválidas | XMLs limpios sin IDs inexistentes |

### 2.2 Rebalanceo de monstruos (Antes vs. Después — esperado en 1.000 kills)

| Monstruo | Dif. | HP | EXP | Antes (NPC / Total) | Después (NPC / Total) | `gp/HP` final | Tipo de ajuste |
|---|---:|---:|---:|---:|---:|---:|---|
| **Old Widow** | 8.3 | 8.230 | 2.800 | 294.7k / 298.7k | **3.07M / 3.19M** | `0.39` | Buff boss (platinum, Knight set, BOH, Steel Boots, Big Emerald) |
| **Grorlam** | 6.7 | 2.750 | 1.600 | 34.0k / 45.8k | **1.43M / 1.43M** | `0.52` | Buff boss (platinum, War Hammer, Warrior Helm, Tower Shield, Steel Boots) |
| **Demodras** | 8.4 | 14.100 | 4.500 | 495.9k / 861.0k | **3.00M / 3.61M** | `0.26` | Fix bolsa 100% + buff boss |
| **Rahemos** | 8.0 | 6.000 | 3.100 | 395.0k / 395.0k | **1.59M / 1.70M** | `0.28` | Buff faraón (platinum, Blue Robe, Skull Staff, Violet Gem) |
| **Dipthrah** | 8.0 | 3.500 | 2.900 | 395.0k / 395.0k | **1.34M / 1.34M** | `0.38` | Buff faraón (platinum, Skull Staff, Medusa Shield, Blue Gem) |
| **Omruc** | 7.4 | 3.000 | 2.000 | 361.0k / 361.0k | **1.08M / 1.21M** | `0.40` | Buff faraón (platinum, Crown Armor, BOH, Stealth Ring) |
| **Behemoth** | 7.4 | 4.000 | 2.500 | 378.4k / 400.1k | **877.5k / 913.5k** | `0.23` | Buff hunt Tier 5 (oro, platinum, GS, Steel Boots, Fire Axe) |
| **Wyrm** | 6.3 | 1.825 | 1.550 | 76.8k / 152.8k | **426.4k / 528.6k** | `0.29` | Buff hunt Tier 4 (oro, platinum, Skull Staff, Crown Helmet, Diamonds) |
| **Orc Berserker Pot Thrower** | 6.1 | 1.500 | 1.050 | 74.3k / 83.6k (550 EXP) | **357.5k / 380.0k** | `0.25` | Buff EXP `550→1050` + loot Tier 4 (oro, Knight Axe, Warrior Helm) |
| **Elder Beholder** | 6.4 | 700 | 750 | 124.1k / 124.1k (290 EXP) | **330.1k / 344.4k** | `0.49` | Buff EXP `290→750` + loot (oro, Beholder Shield, War Hammer, Emeralds) |
| **Worker Golem** | 6.1 | 1.470 | 1.250 | 151.1k / 172.9k | **483.6k / 529.7k** | `0.36` | Buff hunt Tier 4 + limpieza de 3 líneas duplicadas de War Hammer |
| **Orc Warlord** | 6.1 | 950 | 670 | 68.0k / 109.1k | **284.2k / 440.8k** | `0.46` | Reemplazo Golden Ring + buff loot Tier 4 |
| **Lich** | 5.9 | 880 | 900 | 186.8k / 186.8k | **345.7k / 345.7k** | `0.39` | Reemplazo Golden Ring + platinum y perlas |
| **Bone Beast** | 5.5 | 515 | 580 | 48.8k / 50.8k | **148.6k / 153.6k** | `0.30` | Buff hunt Tier 3 (oro, Plate set, Bone Shield, Amethyst) |
| **Dwarf Geomancer** | 5.0 | 380 | 245 | 34.0k / 35.5k | **110.8k / 122.2k** | `0.32` | Buff hunt Tier 3 (oro, Small Sapphire, Clerical Mace, Dwarven Ring) |
| **Dark Monk** | 5.1 | 225 | 145 | 34.0k / 37.6k | **83.0k / 101.5k** | `0.45` | Buff hunt Tier 3 (oro, Mystic Turban, Life Ring) |
| **Monk** | 5.0 | 240 | 200 | 34.0k / 37.6k | **83.0k / 101.5k** | `0.42` | Buff hunt Tier 3 (oro, Mystic Turban, Life Ring) |
| **Crypt Shambler** | 4.9 | 330 | 195 | 34.6k / 40.6k | **92.7k / 100.7k** | `0.31` | Buff hunt Tier 3 (oro, Two-Handed Sword, Bone Shield, Black Pearl) |
| **Assassin** | 4.2 | 175 | 105 | 0 / 0 | **68.5k / 80.5k** | `0.46` | Loot temático agregado (oro, stars/knives, Scarf, Serpent Sword, Stealth Ring) |
| **Imperial Hero** | 7.4 | 3.000 | 2.600 | 1.11M / 1.65M | **741.8k / 1.06M** | `0.35` | Nerf medido (oro, Crown set e Imperial Crown Armor) |
| **Dwarf Guard** | 4.7 | 245 | 185 | 183.0k / 206.4k | **148.0k / 150.3k** | `0.61` | Nerf medido (oro y tasa de Battle Hammer / Double Axe) |
| **Mutated Human** | 4.6 | 240 | 150 | 153.8k / 157.0k | **97.5k / 97.5k** | `0.41` | Nerf medido de oro (`100+30` → `60+20`) |
| **Mummy** | 4.5 | 240 | 150 | 136.0k / 193.0k | **106.0k / 142.0k** | `0.59` | Nerf medido de oro (`80` → `50`) |
| **Minotaur Archer** | 4.0 | 100 | 65 | 72.5k / 107.8k | **49.0k / 69.8k** | `0.70` | Nerf medido de oro y armaduras (eliminado también `id="0000"`) |
| **Rotworm** | 2.8 | 65 | 40 | 73.3k / 73.3k | **39.5k / 39.5k** | `0.61` | Nerf medido de oro (`40@100%` → `22@90%`) |

### 2.3 Curva de referencia resultante por Tier (post-ajustes)

| Tier de Dificultad | Rango Dif. | # Monstruos | HP mediano | EXP mediana | NPC Líq. mediano (1k) | Total Aprox. mediano (1k) | `gp/HP` mediano |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Tier 6 — Endgame y Bosses** | 7.8–10.0 | 26 | 7.800 | 6.400 | 1.36M | 2.87M | `0.38` |
| **Tier 5 — Difícil** | 6.8–7.8 | 21 | 3.200 | 2.900 | 667.8k | 884.9k | `0.28` |
| **Tier 4 — Medio-Alto** | 5.8–6.8 | 23 | 1.250 | 900 | 306.8k | 344.4k | `0.29` |
| **Tier 3 — Medio-Bajo** | 4.5–5.8 | 56 | 410 | 250 | 107.8k | 122.8k | `0.28` |
| **Tier 2 — Fácil** | 3.0–4.5 | 53 | 150 | 90 | 43.0k | 51.2k | `0.31` |
| **Tier 1 — Muy Fácil / Fauna** | 0.0–3.0 | 34 | 55 | 25 | 11.2k | 11.2k | `0.27` |

### 2.4 Nuevos drops Zagan, drops clásicos en hunts y expansión de Mad/Parived

Para hacer más estimulantes las hunts que daban casi solo monedas y completar la asignación de los **18 ítems Zagan** que todavía no tenían fuente de drop (respetando todos los drops ya configurados en `main`, como `Memory Shard`, `Black Fire Sword`, `Paladin Stars` y los 12 Zagan ya asignados):

#### Segundos raros en El Crisol (7 bosses diarios)
| Boss | Segundo raro agregado (ID) | Stats / Tipo | Chance XML (real C++) | Valor Mad/Parived |
|---|---|---|---:|---:|
| Crucible Ashlord | `ashlord mantle` (`20127`) | Armor 11 | `6000` (3.0%) | 12k (Mad) |
| Crucible Bloodreaver | `bloodreaver aegis` (`20150`) | Shield def 31 | `6000` (3.0%) | 12k (Mad) |
| Crucible Frostwarden | `frostwarden aegis` (`20153`) | Shield def 30 | `6000` (3.0%) | 10k (Mad) |
| Crucible Ironhide | `ironhide bulwark` (`20128`) | Shield def 30 | `6000` (3.0%) | 10k (Mad) |
| Crucible Stormcaller | `rift hammer` (`20111`) | 2H Club atk 45 | `5000` (2.5%) | 25k (Mad) |
| Crucible Venomqueen | `venomqueen heart` (`20107`) | Reliquia / Amulet | `3500` (3.5%) | 12k (Parived) |
| Crucible Bonepriest | `bonepriest phylactery` (`20108`) | Reliquia / Amulet | `3500` (3.5%) | 12k (Parived) |

#### Sets temáticos Zagan y chase drops nuevos por zona (heredados por variantes Rage)
| Zona / Línea | Monstruo | Ítems Zagan agregados (ID, chance real C++) |
|---|---|---|
| **Set de Cantera** | Stone Golem | `granite mace` (`20115`, atk 16, 1.5%) |
| **Set de Cantera** | Cyclops Smith | `quarryguard armor` (`20146`, arm 10, 0.6%) |
| **Set de Cantera** | Worker Golem | `ashlar plate` (`20103`, arm 12, 0.4%) |
| **Set de Cantera** | Grorlam | `rubbleguard mail` (`20109`, arm 13, 1.25%) + `quarry ward` (`20101`, def 30, 1.25%) |
| **Desierto** | Ancient Scarab | `tiled breastplate` (`20145`, arm 12, 0.4%) |
| **Línea Imperial** | Imperial Squire | `marcher leggings` (`20116`, legs 8, 0.15%) |
| **Línea Imperial** | Imperial Archer | `cordovan leggings` (`20117`, legs 8, 0.6%) |
| **Línea Imperial** | Imperial Hero | `reachbrand lance` (`20119`, 2H axe atk 47, 0.2%) |
| **Hunts mid/high** | Nightstalker | `hollow orb` (`20106`, 0.5%, 4k Parived) + `BOH` (0.15%) |
| **Hunts mid/high** | Lich | `relic of ulm` (`20144`, 0.5%, 5k Parived) + `blue robe` (0.2%) |

#### Drops clásicos 7.6 agregados a hunts que eran 80–100% monedas
- **Dragon Lord Hatchling** (antes 100% monedas): `dragon shield`, `fire sword`, `small sapphire`.
- **Yeti** (antes 95% monedas): `crystal mace`, `boots of haste`, `blue gem`, más `small sapphire`.
- **Efreet / Marid**: `wand of inferno` + `big/small emerald` (Efreet); `blue robe` + `blue gem` + `small sapphire` (Marid).
- **Mutated Bat / Rat**: `vampire shield`, `obsidian lance`, `black pearl` (Bat); `tower shield`, `stealth ring`, `life crystal` (Rat).
- **Pirate Corsair / Buccaneer / Drowned Sailor**: `fire sword`, `platinum amulet`, `white pearl` (Corsair); `knight axe`, `white pearl` (Buccaneer); `ancient shield`, `life ring`, perlas (Drowned Sailor).
- **Demon Skeleton / Red Kongra / Earth Elemental / Lizard Templar / Quara Constrictor**: limpiado `id="0000"` en Demon Skeleton y agregados `life ring`, `black/white pearl`, `knight armor/legs/axe`, `sentinel shield`, `moonlight rod` y gemas temáticas.

#### Expansión de compras en NPCs (`loot.lua` y `parived.lua`)
- **Parived**: ahora compra `white pearl` (160 gp), `black pearl` (280 gp) y las 6 reliquias/tesoros Zagan (`hollow orb`, `azure/verdant sunstone` 4k, `relic of ulm` 5k, `venomqueen heart`/`bonepriest phylactery` 12k).
- **Mad**: ahora compra 19 equipos clásicos intermedios (`red robe`, `noble/dark/scale armor`, `strange/dark/steel helmet`, `griffin/scarab/ancient/tusk/dark/battle shield`, `great halberd`, `daramanian waraxe`, `obsidian lance`, `orcish axe`, `crystal mace`, `crocodile boots`) y los 24 equipos Zagan nuevos.
- **Impacto en liquidez NPC**: `Banshee` sube de 42% → **97% líquido**, `Ancient/Emerald Scarab` de 62–68% → **98% líquido**, `Quara Hydromancer` de 65% → **81% líquido**.

### 2.5 Puntos dejados intencionalmente (decisiones de diseño)

- **Fire Elemental / Slime / War Wolf / Husky**: se mantienen en `0 gp` (comportamiento clásico 7.6 / summon / mascota).
- **Dark Mage** (`5.200 HP`, `8.000 EXP`, `0.11 gp/HP`): se dejó intacto porque compensa con una EXP altísima (`1.54 EXP/HP`, mayor que un Demon).
- **The Fallen Emperor / Ashen Lord / Orshabaal / Bosses del Crisol**: jefes únicos o diarios de alto riesgo — coherentes con su rareza de respawn.
- **Furious Amazon** (`214 HP`, `1.54 gp/HP`): mantiene su drop exclusivo de `Crystal Arrow (2352)` documentado en `docs/gameplay/CRYSTAL_ARROW.md`.

---

## 3. Simulación de 1.000 kills — Monstruos Base y Bosses (226 criaturas)

Las columnas **Oro 1k**, **NPC Líq. 1k**, **Total 1k** y **Top Drops (1k)** muestran el resultado directo de la simulación de **1.000 kills** (`seed = 20261122`). El indicador `gp/HP` y el **Balance** usan el valor esperado exacto.

Leyenda de ataque: `M:` melee, `D:` distancia, `Sp:` golpe máximo de hechizo ofensivo, `(DPS/Burst)`: daño sostenido/s y combo pico en 1 turno.

### Tier 6 — Endgame y Bosses (26 monstruos — mediana 1k: 1.36M NPC / 2.87M Total, `0.38 gp/HP`)

| Monstruo | Spawns | HP | EXP | Ataque (DPS / Burst) | Dif. | Oro 1k | NPC Líq. 1k | Total 1k | gp/HP | Top Drops (1k sim) | Balance |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---|
| Ashen Lord | 1 | 32.000 | 18.000 | M:220-560 / Sp:≤485 [AoE,ManaDrain,Heal,Summon×2] (473/1045) | **9.6** | 8.82M | 10.84M | 12.20M | `0.38` | 15× demon shield, 5× demon helmet, 4× magic plate armor | 🟣 Muy Alto |
| Orshabaal | 1 | 22.400 | 12.000 | M:410-1090 / Sp:≤700 [Heal,AoE,ManaDrain,Summon×2] (514/1790) | **9.6** | 725.8k | 5.74M | 11.48M | `0.44` | 10× golden boots, 487× violet gem, 6× magic longsword | 🟣 Muy Alto |
| Wrath | 1 | 15.000 | 12.500 | M:320-780 / Sp:≤400 [Heal,AoE,ManaDrain] (371/1180) | **9.0** | 507.5k | 1.80M | 2.64M | `0.16` | 7× mastermind shield, 9× fury cape, 4× magic plate armor | 🟢 Parejo |
| The Fallen Emperor | 1 | 12.000 | 9.000 | M:200-460 / Sp:≤768 [AoE,Heal,Summon×2] (312/1228) | **8.9** | 780.0k | 5.11M | 9.19M | `0.74` | 34× imperial crown armor, 91× crown legs, 87× crown armor | 🟣 Muy Alto |
| Metal Demon | 6 | 9.500 | 7.200 | M:210-540 / Sp:≤460 [Heal,AoE,ManaDrain] (412/1000) | **8.6** | 381.6k | 2.13M | 2.13M | `0.14` | 9× mastermind shield, 5× magic plate armor, 3× golden legs | 🟠 Bajo |
| Demon | 52 | 8.200 | 6.000 | M:192-510 / Sp:≤400 [Heal,AoE,ManaDrain,Summon×2] (402/910) | **8.6** | 354.8k | 1.33M | 1.45M | `0.14` | 3× magic plate armor, 3× mastermind shield, 2× golden legs | 🔴 Muy Bajo |
| Lord of Elvenbane | 1 | 12.000 | 15.000 | M:150-400 / Sp:≤350 [AoE,Heal,Haste,Summon×2] (212/750) | **8.5** | 3.99M | 5.66M | 6.08M | `0.42` | 6× magic plate armor, 26× golden armor, 14× crystal arrow | 🟢 Parejo |
| Demodras | 1 | 14.100 | 4.500 | M:100-300 / Sp:≤485 [AoE,Heal] (243/785) | **8.4** | 759.2k | 2.92M | 3.17M | `0.26` | 24× royal helmet, 14× dragon scale mail, 26× dragon lance | 🟢 Parejo |
| Crucible Bloodreaver | Lua | 9.800 | 8.500 | M:250-580 / Sp:≤426 [AoE] (290/1006) | **8.4** | 1.04M | 2.23M | 4.21M | `0.51` | 16× bloodreaver saber, 95× big ruby, 33× bloodreaver aegis | 🔵 Alto |
| Fury | 13 | 9.200 | 7.800 | M:240-640 / Sp:≤200 [Heal,AoE,ManaDrain] (264/840) | **8.4** | 376.8k | 1.26M | 1.68M | `0.20` | 7× fury cape, 4× mastermind shield, 2× magic plate armor | 🟠 Bajo |
| Old Widow | 1 | 8.230 | 2.800 | M:260-650 / Sp:≤10 [AoE,Haste,Heal,Summon×2] (229/660) | **8.3** | 768.2k | 3.25M | 3.36M | `0.39` | 20× steel boots, 20× boots of haste, 108× big emerald | 🟢 Parejo |
| Crucible Ironhide | Lua | 9.000 | 7.200 | M:220-520 / Sp:≤285 [AoE] (248/805) | **8.2** | 525.5k | 1.66M | 4.19M | `0.46` | 23× ironhide crusher, 73× gold nugget, 34× ironhide bulwark | 🟢 Parejo |
| Crucible Frostwarden | Lua | 7.500 | 6.400 | M:160-400 / Sp:≤415 [AoE] (207/815) | **8.1** | 426.6k | 1.21M | 2.89M | `0.46` | 17× frostwarden chillblade, 76× blue gem, 30× frostwarden aegis | 🟢 Parejo |
| Crucible Ashlord | Lua | 7.200 | 6.200 | M:180-420 / Sp:≤400 [AoE] (210/820) | **8.0** | 412.6k | 1.29M | 3.86M | `0.49` | 27× ashlord emberblade, 71× big ruby, 28× ashlord mantle | 🟢 Parejo |
| Rahemos | 1 | 6.000 | 3.100 | M:105-317 / Sp:≤450 [Heal,AoE,Summon×2] (146/767) | **8.0** | 690.1k | 1.56M | 1.68M | `0.28` | 76× violet gem, 17× blue robe, 57× platinum amulet | 🟢 Parejo |
| Dipthrah | 1 | 3.500 | 2.900 | M:310-800 [Drunk,Heal,Summon×5] (222/800) | **8.0** | 560.9k | 1.37M | 1.37M | `0.38` | 65× blue gem, 576× small sapphire, 13× medusa shield | 🟢 Parejo |
| Crucible Stormcaller | Lua | 7.600 | 7.400 | M:60-180 / Sp:≤479 [AoE,Dist(4)] (149/659) | **7.9** | 484.2k | 1.57M | 4.82M | `0.51` | 33× stormcaller maul, 20× rift hammer, 90× blue gem | 🟢 Parejo |
| Crucible Bonepriest | Lua | 6.800 | 6.800 | M:80-220 / Sp:≤457 [AoE,Dist(3)] (162/677) | **7.9** | 426.4k | 1.02M | 3.16M | `0.42` | 25× bonepriest reaver, 41× bonepriest phylactery, 205× small sapphire | 🟢 Parejo |
| Crucible Venomqueen | Lua | 7.800 | 7.000 | M:150-380 / Sp:≤92 [AoE] (145/472) | **7.8** | 411.9k | 1.52M | 3.34M | `0.38` | 26× venomqueen fang, 44× venomqueen heart, 89× big emerald | 🟢 Parejo |
| Orc Warchief | 1 | 7.000 | 5.500 | M:120-330 / Sp:≤216 [AoE,Haste,Summon×2] (140/546) | **7.8** | 607.2k | 852.4k | 852.4k | `0.13` | 22× crusader helmet, 10× fire axe, 33× halberd | 🔴 Muy Bajo |
| Ashmunrah | 1 | 6.000 | 3.100 | M:0-310 / D:110-190 / Sp:≤462 [AoE] (158/772) | **7.8** | 695.7k | 774.0k | 928.5k | `0.16` | 2× phoenix shield, 11× wand of cosmic energy, 7× griffin shield | 🔴 Muy Bajo |
| Mahrdis | 1 | 6.000 | 3.050 | M:0-300 / D:50-150 / Sp:≤450 [AoE] (141/750) | **7.8** | 697.9k | 760.4k | 1.01M | `0.16` | 4× phoenix shield, 9× wand of cosmic energy, 7× griffin shield | 🔴 Muy Bajo |
| Morguthis | 1 | 6.000 | 3.000 | M:0-290 / D:110-160 / Sp:≤439 [AoE] (149/729) | **7.8** | 702.1k | 780.4k | 933.6k | `0.16` | 2× phoenix shield, 9× wand of cosmic energy, 17× scarab shield | 🔴 Muy Bajo |
| Thalas | 1 | 6.000 | 2.950 | M:0-270 / D:120-200 / Sp:≤415 [AoE] (168/685) | **7.8** | 692.2k | 791.7k | 824.4k | `0.16` | 12× griffin shield, 15× scarab shield, 5× wand of cosmic energy | 🔴 Muy Bajo |
| Vashresamun | 1 | 6.000 | 2.950 | M:0-280 / D:110-180 / Sp:≤427 [AoE] (151/707) | **7.8** | 698.2k | 758.7k | 918.0k | `0.16` | 2× phoenix shield, 12× wand of cosmic energy, 11× scarab shield | 🔴 Muy Bajo |
| Serpent Spawn | 11 | 5.000 | 3.600 | M:90-260 / D:0-140 / Sp:≤300 [AoE,Heal,Summon×3] (137/560) | **7.8** | 493.7k | 810.7k | 865.1k | `0.20` | 4× boots of haste, 27× serpent sword, 6× tower shield | 🟠 Bajo |

### Tier 5 — Difícil (21 monstruos — mediana 1k: 667.8k NPC / 884.9k Total, `0.28 gp/HP`)

| Monstruo | Spawns | HP | EXP | Ataque (DPS / Burst) | Dif. | Oro 1k | NPC Líq. 1k | Total 1k | gp/HP | Top Drops (1k sim) | Balance |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---|
| Root Colossus | 1 | 4.800 | 3.400 | M:140-360 / Sp:≤180 [AoE] (142/540) | **7.5** | 335.3k | 507.0k | 1.28M | `0.28` | 4× rootcleaver, 1× heartwood maul, 4× steel boots | 🟢 Parejo |
| Thornwarden | 1 | 6.500 | 5.500 | M:80-220 / Sp:≤200 [AoE,Heal] (107/420) | **7.4** | 640.4k | 781.7k | 933.7k | `0.14` | 38× quagmire rod, 345× small emerald, 11× big emerald | 🟢 Parejo |
| Behemoth | 34 | 4.000 | 2.500 | M:160-400 / D:92-170 [Haste] (140/400) | **7.4** | 440.3k | 883.1k | 920.0k | `0.23` | 12× giant sword, 4× steel boots, 7× fire axe | 🟢 Parejo |
| Imperial Hero | 10 | 3.000 | 2.600 | M:150-380 / D:90-210 / Sp:≤150 [AoE,Heal] (144/530) | **7.4** | 272.4k | 562.4k | 722.1k | `0.35` | 1× imperial crown armor, 5× crown legs, 6× crown shield | 🟢 Parejo |
| Omruc | 1 | 3.000 | 2.000 | Sp:≤400 [Heal,Invis,Dist(4),Summon×5] (89/400) | **7.4** | 575.3k | 1.09M | 1.21M | `0.40` | 9× boots of haste, 12× crown armor, 53× stealthring | 🟢 Parejo |
| Elvenbane Ranger | 1 | 5.000 | 4.500 | M:25-70 / D:40-140 / Sp:≤110 [AoE,Haste,Dist(4),Summon×2] (80/250) | **7.3** | 573.2k | 573.2k | 1.39M | `0.29` | 27× crystal arrow, 91× bow, 359× spear | 🟢 Parejo |
| Elven Archmage | 1 | 4.200 | 5.000 | M:40-150 / Sp:≤150 [AoE,Heal,Dist(4),Summon×2] (106/300) | **7.3** | 571.0k | 847.5k | 1.18M | `0.29` | 46× wand of cosmic energy, 18× blue robe, 5× crystal arrow | 🟢 Parejo |
| Dark Spider | 2 | 3.400 | 3.200 | M:180-410 / Sp:≤90 [AoE] (155/500) | **7.3** | 305.4k | 384.6k | 384.6k | `0.12` | 16× platinum amulet, 157× small sapphire | 🟠 Bajo |
| Metal Hydra | 3 | 3.400 | 3.300 | M:90-230 / Sp:≤290 [AoE,Heal] (119/520) | **7.3** | 566.0k | 1.01M | 1.03M | `0.32` | 3× royal helmet, 3× boots of haste, 213× small emerald | 🟢 Parejo |
| Warlock | 18 | 3.200 | 4.000 | M:27-85 / Sp:≤200 [AoE,ManaDrain,Invis,Dist(5)] (78/285) | **7.3** | 315.5k | 587.5k | 805.6k | `0.23` | 14× ring of the skies, 6× golden armor, 8× blue robe | 🟢 Parejo |
| Dark Mage | 1 | 5.200 | 8.000 | M:15-45 / Sp:≤90 [ManaDrain,AoE,Dist(4)] (112/135) | **7.2** | 342.8k | 475.5k | 551.5k | `0.11` | 19× wand of cosmic energy, 5× blue robe, 201× small amethyst | 🟠 Bajo |
| Dark Hydra | 13 | 3.200 | 3.000 | M:90-220 / Sp:≤300 [AoE,Heal] (118/520) | **7.2** | 567.8k | 918.8k | 988.1k | `0.32` | 5× royal helmet, 3× boots of haste, 8× tempest rod | 🟢 Parejo |
| Metal Dragon | 3 | 2.900 | 3.200 | M:90-250 / Sp:≤300 [AoE,Heal] (123/550) | **7.2** | 419.2k | 1.18M | 1.20M | `0.34` | 8× royal helmet, 5× dragon scale mail, 3× sunforge shield | 🟢 Parejo |
| Black Dragon | 16 | 2.600 | 2.900 | M:80-240 / Sp:≤290 [AoE,Heal] (122/530) | **7.1** | 387.5k | 1.01M | 1.02M | `0.34` | 8× royal helmet, 14× dragon lance, 3× dragon scale mail | 🟢 Parejo |
| Quara Predator | 45 | 2.200 | 1.800 | M:40-270 / Sp:≤270 [Haste] (110/540) | **7.0** | 224.5k | 307.8k | 310.5k | `0.15` | 2× giant sword, 78× small diamond, 2× warrior helmet | 🟠 Bajo |
| Hydra | 25 | 2.250 | 2.100 | M:60-150 / Sp:≤300 [Heal,AoE] (93/450) | **6.9** | 459.5k | 804.0k | 817.8k | `0.35` | 8× boots of haste, 7× warrior helmet, 1× royal helmet | 🟢 Parejo |
| Black Knight | 48 | 1.800 | 1.600 | M:82-275 / D:72-180 / Sp:≤150 [AoE] (103/425) | **6.9** | 212.9k | 426.3k | 427.3k | `0.24` | 6× dragon lance, 2× boots of haste, 66× dark helmet | 🟢 Parejo |
| Lake Custodian | 1 | 3.300 | 2.400 | M:70-175 / Sp:≤130 [AoE] (74/305) | **6.8** | 318.3k | 512.6k | 524.6k | `0.16` | 409× small sapphire, 4× crystal mace, 11× verdant sunstone | 🟠 Bajo |
| Frost Dragon | 10 | 2.200 | 2.400 | M:70-210 / Sp:≤260 [AoE,Heal] (118/470) | **6.8** | 324.5k | 639.7k | 639.7k | `0.28` | 6× crystal mace, 277× small sapphire, 11× ice rapier | 🟢 Parejo |
| Dragon Lord | 60 | 1.900 | 2.100 | M:62-205 / Sp:≤250 [AoE,Heal] (112/455) | **6.8** | 287.6k | 606.1k | 612.9k | `0.36` | 3× royal helmet, 2× dragon scale mail, 6× dragon lance | 🟢 Parejo |
| Quara Pincher | 41 | 1.800 | 1.350 | M:30-230 / Sp:≤270 (111/500) | **6.8** | 294.4k | 401.6k | 401.6k | `0.22` | 3× frostwarden aegis, 100× small ruby, 5× warrior helmet | 🟠 Bajo |

### Tier 4 — Medio-Alto (23 monstruos — mediana 1k: 306.8k NPC / 344.4k Total, `0.29 gp/HP`)

| Monstruo | Spawns | HP | EXP | Ataque (DPS / Burst) | Dif. | Oro 1k | NPC Líq. 1k | Total 1k | gp/HP | Top Drops (1k sim) | Balance |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---|
| Grorlam | 1 | 2.750 | 1.600 | M:50-220 / D:50-150 [Haste,Heal,Summon×2] (54/220) | **6.7** | 366.5k | 1.46M | 1.46M | `0.52` | 14× steel boots, 25× tower shield, 12× quarry ward | 🟣 Muy Alto |
| Ice Spider | 34 | 1.800 | 1.550 | M:100-260 / Sp:≤150 [AoE,Heal,Haste] (100/410) | **6.7** | 125.7k | 290.0k | 294.0k | `0.16` | 18× platinum amulet, 159× small sapphire, 204× iron helmet | 🟢 Parejo |
| Giant Spider | 25 | 1.300 | 900 | M:120-300 / Sp:≤10 [AoE,Haste,Heal,Summon×5] (106/310) | **6.7** | 128.2k | 245.7k | 246.7k | `0.19` | 19× platinum amulet, 201× iron helmet, 4× knight legs | 🟢 Parejo |
| Banshee | 9 | 1.000 | 900 | M:80-250 / Sp:≤330 [AoE,Heal] (111/580) | **6.6** | 68.0k | 211.9k | 222.4k | `0.32` | 10× red robe, 4× blue robe, 12× lifering | 🟢 Parejo |
| Hero | 19 | 1.400 | 1.200 | M:100-250 / D:52-130 (88/250) | **6.5** | 169.0k | 347.8k | 366.4k | `0.26` | 7× crown armor, 108× scarf, 11× crown helmet | 🟢 Parejo |
| Emerald Scarab | 4 | 1.500 | 1.150 | M:65-220 / D:0-90 / Sp:≤85 [AoE,Haste] (76/305) | **6.4** | 238.0k | 339.1k | 347.7k | `0.24` | 11× daramanian waraxe, 130× small emerald, 1× great halberd | 🟢 Parejo |
| Hellhound | 71 | 1.500 | 1.300 | M:60-210 / Sp:≤140 [AoE] (81/350) | **6.4** | 211.5k | 288.5k | 292.4k | `0.19` | 3× fire axe, 7× fire sword, 48× small ruby | 🟢 Parejo |
| Elder Beholder | 6 | 700 | 750 | M:0-110 / Sp:≤459 [AoE,Summon×5] (92/569) | **6.4** | 211.1k | 321.2k | 333.6k | `0.49` | 15× war hammer, 101× small emerald, 14× beholder shield | 🟢 Parejo |
| Wyrm | 20 | 1.825 | 1.550 | M:40-130 / Sp:≤110 [AoE,Heal] (61/240) | **6.3** | 221.3k | 470.3k | 568.7k | `0.29` | 14× skull staff, 20× wand of cosmic energy, 22× platinum amulet | 🟢 Parejo |
| Crystal Spider | 15 | 1.250 | 900 | M:50-200 / Sp:≤150 [AoE,Haste] (71/350) | **6.3** | 188.0k | 297.3k | 300.8k | `0.23` | 191× small sapphire, 2× frostwarden aegis, 5× knight legs | 🟢 Parejo |
| Mutated Tiger | 12 | 1.100 | 850 | M:65-220 / Sp:≤160 [Heal,AoE,Haste] (90/380) | **6.3** | 200.3k | 223.3k | 231.6k | `0.22` | 6× knight axe, 2× knight armor, 8× lifering | 🟢 Parejo |
| Iron Foreman | 1 | 1.800 | 1.250 | M:55-125 / Sp:≤90 [AoE] (53/215) | **6.2** | 266.7k | 328.5k | 357.5k | `0.21` | 162× small amethyst, 6× verdant sunstone, 42× dwarfenring | 🟢 Parejo |
| Ancient Scarab | 29 | 1.000 | 720 | M:54-180 / D:0-90 / Sp:≤20 [Haste,Summon×5] (61/200) | **6.2** | 167.2k | 264.9k | 270.9k | `0.29` | 3× great halberd, 2× tiled breastplate, 4× daramanian waraxe | 🟢 Parejo |
| Orc Berserker Pot Thrower | 4 | 1.500 | 1.050 | M:76-190 [AoE] (66/190) | **6.1** | 194.2k | 387.8k | 413.8k | `0.25` | 15× warrior helmet, 19× knight axe, 52× swordring | 🟢 Parejo |
| Worker Golem | 38 | 1.470 | 1.250 | M:50-160 / Sp:≤88 [AoE,Heal] (60/248) | **6.1** | 245.3k | 500.7k | 535.3k | `0.36` | 9× tower shield, 21× war hammer, 12× knight armor | 🟢 Parejo |
| Orc Warlord | 31 | 950 | 670 | M:90-225 / D:48-120 (79/225) | **6.1** | 119.7k | 308.7k | 451.5k | `0.46` | 3× crystal arrow, 12× crusader helmet, 14× knight armor | 🟢 Parejo |
| Bog Raider | 13 | 1.300 | 950 | M:30-110 / Sp:≤130 [AoE,Heal] (52/240) | **6.0** | 170.9k | 199.1k | 212.9k | `0.17` | 56× small emerald, 11× ring of healing, 11× plate legs | 🟠 Bajo |
| Dragon | 93 | 1.000 | 700 | M:37-110 / Sp:≤140 [AoE,Heal] (61/250) | **6.0** | 213.7k | 365.8k | 387.4k | `0.37` | 69× broad sword, 7× dragon shield, 7× dragon hammer | 🟢 Parejo |
| Undead Gladiator | 17 | 1.000 | 800 | M:40-150 / D:45-120 / Sp:≤110 (57/260) | **5.9** | 236.3k | 280.8k | 317.3k | `0.32` | 141× scimitar, 1466× throwing star, 44× brass armor | 🟢 Parejo |
| Mutated Bat | 23 | 900 | 615 | M:50-165 / Sp:≤160 [AoE] (62/325) | **5.9** | 188.5k | 229.3k | 250.6k | `0.30` | 74× black pearl, 13× energyring, 9× obsidian lance | 🟢 Parejo |
| Lich | 16 | 880 | 900 | M:10-90 / Sp:≤112 [Heal] (47/202) | **5.9** | 215.7k | 327.5k | 327.5k | `0.39` | 20× platinum amulet, 7× relic of ulm, 60× black pearl | 🟢 Parejo |
| Vampire Bride | 16 | 1.200 | 1.050 | M:30-120 / Sp:≤80 [Heal] (47/200) | **5.8** | 235.0k | 337.8k | 374.9k | `0.31` | 2× boots of haste, 98× small ruby, 58× moonlight rod | 🟢 Parejo |
| Necromancer | 32 | 580 | 580 | M:0-50 / Sp:≤105 [Heal,AoE,Dist(5),Summon×5] (38/155) | **5.8** | 68.0k | 250.9k | 250.9k | `0.37` | 5× boots of haste, 58× clerical mace, 2× skull staff | 🟢 Parejo |

### Tier 3 — Medio-Bajo (56 monstruos — mediana 1k: 107.8k NPC / 122.8k Total, `0.28 gp/HP`)

| Monstruo | Spawns | HP | EXP | Ataque (DPS / Burst) | Dif. | Oro 1k | NPC Líq. 1k | Total 1k | gp/HP | Top Drops (1k sim) | Balance |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---|
| Pirate Corsair | 4 | 675 | 450 | M:50-170 / D:40-140 / Sp:≤88 [AoE,Haste] (62/258) | **5.7** | 142.7k | 204.3k | 208.4k | `0.30` | 7× fire sword, 76× white pearl, 11× dark armor | 🟢 Parejo |
| Priestess | 18 | 390 | 420 | M:0-70 / Sp:≤105 [Heal,ManaDrain,Dist(5),Summon×5] (60/175) | **5.7** | 24.1k | 46.4k | 60.3k | `0.15` | 83× white pearl, 30× small diamond, 37× silver brooch | 🟠 Bajo |
| Frost Dragon Hatchling | 5 | 800 | 745 | M:20-90 / Sp:≤110 [AoE,Heal] (39/200) | **5.6** | 100.7k | 108.9k | 108.9k | `0.13` | 33× small sapphire | 🟢 Parejo |
| Quara Mantassin | 18 | 800 | 500 | M:20-120 / Sp:≤80 [Haste] (40/200) | **5.6** | 172.8k | 189.2k | 207.2k | `0.27` | 9× stealthring, 33× halberd, 8× small sapphire | 🟢 Parejo |
| Dragon Lord Hatchling | 7 | 750 | 645 | M:30-90 / Sp:≤125 [AoE,Heal] (45/215) | **5.6** | 192.2k | 223.4k | 223.4k | `0.31` | 61× small sapphire, 3× dragon shield, 1× fire sword | 🟢 Parejo |
| Tide Priest | 6 | 720 | 620 | M:0-40 / Sp:≤95 [ManaDrain,Heal,Dist(4),Summon×2] (32/135) | **5.6** | 102.2k | 144.0k | 189.9k | `0.26` | 118× small sapphire, 17× energyring, 5× wand of cosmic energy | 🟢 Parejo |
| Murius | 2 | 650 | 300 | M:0-150 [Heal,Summon×5] (38/150) | **5.6** | 33.9k | 65.3k | 65.3k | `0.10` | 102× battle shield, 27× double axe, 21× brass armor | 🟠 Bajo |
| Efreet | 4 | 550 | 300 | M:0-140 / Sp:≤80 [AoE] (39/220) | **5.6** | 122.8k | 156.0k | 193.3k | `0.36` | 6× wand of Inferno, 73× small emerald, 3× big emerald | 🟢 Parejo |
| Ghost | 16 | 150 | 120 | M:14-36 / Sp:≤45 [AoE] (18/81) | **5.6** | 26.1k | 78.3k | 116.4k | `0.82` | 99× clerical mace, 13× stealthring, 15× ancient shield | 🔵 Alto |
| Yeti | 8 | 1.000 | 700 | M:37-110 / D:25-65 [Heal] (37/110) | **5.5** | 129.5k | 174.0k | 174.0k | `0.24` | 118× small sapphire, 3× blue gem | 🟢 Parejo |
| Wyvern | 12 | 795 | 515 | M:30-120 / Sp:≤80 [AoE,Heal] (42/200) | **5.5** | 140.4k | 151.1k | 187.3k | `0.22` | 6× wand of Inferno, 43× small sapphire, 41× power bolt | 🟢 Parejo |
| Nightstalker | 29 | 700 | 500 | M:30-110 / Sp:≤80 [Haste] (45/190) | **5.5** | 95.4k | 174.8k | 187.6k | `0.29` | 8× hollow orb, 1× boots of haste, 5× stealthring | 🟢 Parejo |
| Ice Monk | 15 | 650 | 520 | M:10-45 / Sp:≤95 [AoE,Heal,Dist(4),Summon×2] (40/140) | **5.5** | 77.1k | 103.1k | 155.3k | `0.26` | 5× tempest rod, 104× small sapphire, 1× aurora shield | 🟢 Parejo |
| Marid | 4 | 550 | 300 | M:0-140 / Sp:≤80 [AoE] (39/220) | **5.5** | 108.4k | 181.1k | 224.0k | `0.39` | 96× life crystal, 3× blue robe, 91× small sapphire | 🔵 Alto |
| Bone Beast | 17 | 515 | 580 | M:49-160 / Sp:≤70 [AoE] (50/230) | **5.5** | 109.8k | 148.2k | 154.0k | `0.30` | 34× plate armor, 16× plate legs, 51× small amethyst | 🟢 Parejo |
| Quara Hydromancer | 20 | 1.100 | 800 | M:15-80 / Sp:≤55 [AoE,Heal] (30/135) | **5.4** | 166.3k | 227.5k | 321.5k | `0.29` | 12× wand of cosmic energy, 6× tempest rod, 148× white pearl | 🔵 Alto |
| Court Mage | 7 | 650 | 520 | M:0-45 / Sp:≤102 [AoE,Heal,Dist(4)] (42/147) | **5.4** | 120.5k | 159.9k | 163.6k | `0.22` | 8× violet gem, 37× small amethyst, 10× mind stone | 🟢 Parejo |
| Vampire | 32 | 450 | 290 | M:0-160 / Sp:≤100 [AoE] (55/260) | **5.4** | 16.3k | 150.7k | 150.7k | `0.34` | 5× vampire shield, 5× ice rapier, 15× spikesword | 🟢 Parejo |
| Earth Elemental | 7 | 650 | 450 | M:25-80 / Sp:≤55 [AoE,Heal] (32/135) | **5.3** | 101.3k | 144.5k | 150.1k | `0.24` | 79× small emerald, 86× small amethyst, 1278× small stone | 🟢 Parejo |
| Mutated Rat | 18 | 550 | 450 | M:40-155 / Sp:≤10 [AoE,Heal] (50/165) | **5.3** | 160.3k | 179.9k | 203.6k | `0.39` | 7× stealthring, 22× halberd, 1× tower shield | 🔵 Alto |
| Red Kongra | 12 | 550 | 340 | M:0-115 / Sp:≤64 [AoE,Haste] (33/179) | **5.3** | 59.9k | 151.0k | 157.5k | `0.27` | 119× steel helmet, 40× plate armor, 77× small ruby | 🟢 Parejo |
| Water Elemental | 2 | 550 | 650 | M:30-100 / Sp:≤80 [AoE,Heal] (42/180) | **5.3** | 117.4k | 134.9k | 154.4k | `0.28` | 14× lifering, 4× platinum amulet, 6× energyring | 🟢 Parejo |
| Imperial Archer | 7 | 450 | 300 | M:10-50 / D:50-130 / Sp:≤88 [AoE,Dist(4)] (49/218) | **5.3** | 91.8k | 115.8k | 129.4k | `0.38` | 2× cordovan leggings, 62× crossbow, 2509× bolt | 🟢 Parejo |
| Pirate Buccaneer | 5 | 425 | 250 | M:40-150 / D:30-100 / Sp:≤88 [AoE] (55/238) | **5.3** | 91.0k | 112.7k | 115.0k | `0.28` | 40× white pearl, 3× knight axe, 43× battle shield | 🟢 Parejo |
| Demon Skeleton | 68 | 400 | 240 | M:54-180 (58/180) | **5.3** | 68.0k | 104.4k | 113.3k | `0.29` | 11× guardians shield, 29× black pearl, 53× battlehammer | 🟢 Parejo |
| Drowned Sailor | 12 | 520 | 280 | M:25-85 / Sp:≤55 [Paralyze] (30/140) | **5.2** | 67.9k | 93.0k | 99.8k | `0.20` | 7× ancient shield, 9× lifering, 42× white pearl | 🟢 Parejo |
| Orc Leader | 16 | 450 | 270 | M:45-130 / D:38-74 (44/130) | **5.2** | 51.1k | 113.6k | 155.1k | `0.32` | 7× warrior helmet, 115× scimitar, 31× broad sword | 🟢 Parejo |
| Blue Elf Arcanist | 5 | 220 | 174 | D:10-70 / Sp:≤80 [Heal,Dist(5)] (46/150) | **5.2** | 34.0k | 34.0k | 61.2k | `0.27` | 31× life crystal, 21× crystal necklace, 102× bow | 🟢 Parejo |
| Elf Arcanist | 11 | 220 | 174 | D:10-70 / Sp:≤80 [Heal,Dist(5)] (46/150) | **5.2** | 33.9k | 33.9k | 53.5k | `0.27` | 18× life crystal, 16× crystal necklace, 95× bow | 🟢 Parejo |
| Zombie | 17 | 500 | 280 | M:20-90 / Sp:≤55 (32/145) | **5.1** | 89.7k | 111.6k | 122.9k | `0.25` | 15× lifering, 51× steel helmet, 58× battlehammer | 🟢 Parejo |
| Quara Constrictor | 24 | 450 | 250 | M:20-100 / Sp:≤80 [AoE] (38/180) | **5.1** | 144.4k | 178.0k | 192.4k | `0.43` | 91× white pearl, 54× brass armor, 9× lifering | 🔵 Alto |
| Blue Djinn | 11 | 330 | 190 | M:0-125 / Sp:≤80 [AoE] (34/205) | **5.1** | 33.7k | 65.5k | 65.5k | `0.23` | 127× small sapphire | 🟢 Parejo |
| Fire Elemental | 65 | 280 | 220 | M:25-90 / Sp:≤160 [AoE] (62/250) | **5.1** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Dark Monk | 17 | 225 | 145 | M:36-120 [Heal,Haste] (39/120) | **5.1** | 68.1k | 79.6k | 101.1k | `0.45` | 22× lifering, 23× mystic turban, 20× powerring | 🟢 Parejo |
| Cyclops Smith | 18 | 435 | 255 | M:25-90 / D:27-72 / Sp:≤55 (32/145) | **5.0** | 98.0k | 144.5k | 148.0k | `0.36` | 4× quarryguard armor, 62× battle axe, 61× battlehammer | 🟢 Parejo |
| Ice Golem | 5 | 385 | 295 | M:20-110 / Sp:≤60 [AoE] (35/170) | **5.0** | 86.5k | 107.3k | 109.3k | `0.30` | 63× small sapphire, 1× ice rapier, 31× plate shield | 🟢 Parejo |
| Dwarf Geomancer | 13 | 380 | 245 | M:27-54 / D:41-120 [Heal,ManaDrain,Dist(4)] (16/120) | **5.0** | 76.5k | 112.7k | 124.3k | `0.32` | 75× small sapphire, 58× clerical mace, 20× dwarfenring | 🟢 Parejo |
| Green Djinn | 7 | 330 | 190 | M:0-125 / Sp:≤80 [AoE] (34/205) | **5.0** | 67.7k | 67.7k | 86.4k | `0.25` | 25× orb | 🟢 Parejo |
| Mammoth | 3 | 320 | 160 | M:20-100 / Sp:≤80 [Haste] (35/180) | **5.0** | 61.8k | 70.8k | 82.0k | `0.25` | 112× elephant tusk, 6× tusk shield | 🟢 Parejo |
| Monk | 15 | 240 | 200 | M:0-150 [Heal] (30/150) | **5.0** | 67.9k | 86.9k | 109.4k | `0.42` | 38× mystic turban, 24× lifering, 18× powerring | 🟢 Parejo |
| Lizard Templar | 27 | 410 | 140 | M:0-100 [Heal] (25/100) | **4.9** | 33.9k | 77.5k | 116.3k | `0.30` | 65× hatchet lizard, 31× two-handed sword, 69× steel helmet | 🟢 Parejo |
| Dragon Hatchling | 15 | 380 | 230 | M:15-55 / Sp:≤90 [AoE,Heal] (26/145) | **4.9** | 75.7k | 75.7k | 75.7k | `0.20` | — | 🟢 Parejo |
| Crypt Shambler | 45 | 330 | 195 | M:41-130 (43/130) | **4.9** | 67.7k | 91.8k | 99.1k | `0.31` | 43× black pearl, 20× two-handed sword, 500× throwing star | 🟢 Parejo |
| Pirate Cutthroat | 7 | 325 | 175 | M:30-110 / D:20-60 / Sp:≤80 (40/190) | **4.9** | 72.9k | 89.3k | 90.2k | `0.27` | 47× steel helmet, 106× sabre, 17× scale armor | 🟢 Parejo |
| Barbarian Bloodwalker | 6 | 305 | 195 | M:20-110 / Sp:≤64 [Haste,AoE] (36/174) | **4.9** | 61.8k | 79.3k | 81.9k | `0.26` | 49× battle axe, 10× halberd, 51× chain armor | 🟢 Parejo |
| Orc Berserker | 45 | 210 | 195 | M:76-190 [Haste] (66/190) | **4.9** | 26.0k | 56.0k | 61.5k | `0.32` | 28× halberd, 52× battle axe, 11× swordring | 🟢 Parejo |
| Gargoyle | 12 | 250 | 150 | M:0-140 / D:30-60 (35/140) | **4.8** | 42.9k | 50.1k | 50.1k | `0.20` | 12× dark armor | 🟠 Bajo |
| Blood Crab | 18 | 290 | 160 | M:15-70 / Sp:≤80 (26/150) | **4.7** | 31.5k | 38.3k | 38.3k | `0.13` | 63× chain armor, 27× brass legs, 6× white pearl | 🔴 Muy Bajo |
| Beholder | 7 | 260 | 170 | M:0-60 / Sp:≤60 [ManaDrain,Dist(4),Summon×5] (19/120) | **4.7** | 107.7k | 133.5k | 150.7k | `0.53` | 10× beholder shield, 18× two-handed sword, 33× steel shield | 🟢 Parejo |
| Dwarf Guard | 48 | 245 | 185 | M:48-120 (42/120) | **4.7** | 71.4k | 146.3k | 147.3k | `0.61` | 78× double axe, 198× battlehammer, 148× scale armor | 🔵 Alto |
| Minotaur Mage | 36 | 155 | 150 | M:0-20 / Sp:≤100 [AoE,Dist(5),Summon×5] (51/120) | **4.7** | 34.0k | 49.9k | 50.3k | `0.31` | 48× brass armor, 39× chain trousers, 33× adori gran | 🟢 Parejo |
| Frost Giant | 4 | 270 | 150 | M:15-90 / D:10-60 / Sp:≤44 [AoE] (29/134) | **4.6** | 54.7k | 59.1k | 64.4k | `0.24` | 29× viking shield, 31× battlehammer, 5× small sapphire | 🟢 Parejo |
| Mutated Human | 12 | 240 | 150 | M:20-90 / Sp:≤50 [AoE] (31/140) | **4.6** | 93.0k | 97.1k | 97.1k | `0.41` | 43× sword, 10× scale armor, 2× strange helmet | 🟢 Parejo |
| Frost Giantess | 2 | 275 | 150 | M:10-70 / D:20-90 / Sp:≤44 [AoE] (23/134) | **4.5** | 57.4k | 59.7k | 63.6k | `0.22` | 26× viking shield, 9× small sapphire | 🟠 Bajo |
| Stone Golem | 22 | 270 | 160 | M:16-80 (24/80) | **4.5** | 33.9k | 55.0k | 56.9k | `0.20` | 116× scale armor, 19× granite mace, 610× small stone | 🟠 Bajo |
| Mummy | 22 | 240 | 150 | M:35-92 (32/92) | **4.5** | 84.9k | 108.2k | 148.0k | `0.59` | 83× black pearl, 14× timering, 74× silver brooch | 🔵 Alto |

### Tier 2 — Fácil (53 monstruos — mediana 1k: 43.0k NPC / 51.2k Total, `0.31 gp/HP`)

| Monstruo | Spawns | HP | EXP | Ataque (DPS / Burst) | Dif. | Oro 1k | NPC Líq. 1k | Total 1k | gp/HP | Top Drops (1k sim) | Balance |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---|
| Thornback Tortoise | 16 | 300 | 150 | M:15-55 / Sp:≤35 [AoE] (20/90) | **4.4** | 71.7k | 79.5k | 81.4k | `0.27` | 23× white pearl, 11× black pearl, 39× plate shield | 🟢 Parejo |
| Cyclops | 42 | 260 | 150 | M:25-80 (26/80) | **4.4** | 45.9k | 88.3k | 98.3k | `0.39` | 330× short sword, 37× dark helmet, 20× clubring | 🔵 Alto |
| Fire Devil | 22 | 200 | 110 | M:0-30 / Sp:≤70 [AoE,Dist(4)] (26/100) | **4.4** | 33.9k | 77.0k | 101.5k | `0.48` | 14× guardians shield, 116× scimitar, 29× double axe | 🔵 Alto |
| Cyclops Drone | 13 | 325 | 200 | M:15-60 / D:18-48 (19/60) | **4.3** | 43.0k | 50.3k | 53.3k | `0.16` | 80× short sword, 4× clubring, 17× battle shield | 🟢 Parejo |
| Scarab | 6 | 320 | 120 | M:21-60 [Haste] (16/60) | **4.3** | 67.9k | 82.2k | 88.1k | `0.28` | 39× small amethyst, 23× small emerald, 23× daramanian mace | 🟢 Parejo |
| Pirate Marauder | 8 | 210 | 125 | M:20-80 / D:10-40 / Sp:≤28 [AoE] (26/108) | **4.3** | 55.5k | 60.9k | 63.5k | `0.30` | 72× sabre, 44× plate shield, 36× chain armor | 🟢 Parejo |
| Minotaur Guard | 53 | 185 | 160 | M:40-100 (35/100) | **4.3** | 34.0k | 67.0k | 67.0k | `0.36` | 91× battle shield, 28× double axe, 25× brass armor | 🟢 Parejo |
| Kongra | 28 | 340 | 105 | M:0-60 (15/60) | **4.2** | 34.0k | 77.0k | 77.0k | `0.21` | 36× plate armor, 75× steel helmet, 100× scale armor | 🟢 Parejo |
| Witch | 11 | 300 | 120 | M:0-40 / Sp:≤10 [AoE,Heal,Dist(3)] (12/50) | **4.2** | 33.8k | 33.8k | 38.2k | `0.13` | 18× heavy machete, 8× golden sickle, 12× garlic necklace | 🟠 Bajo |
| Carniphila | 3 | 255 | 110 | M:0-90 (15/90) | **4.2** | 17.1k | 17.1k | 17.1k | `0.07` | — | 🔴 Muy Bajo |
| Orc Rider | 7 | 180 | 110 | M:0-88 (22/88) | **4.2** | 34.1k | 59.7k | 59.7k | `0.36` | 9× obsidian lance, 65× battle shield, 16× orcish axe | 🟢 Parejo |
| Assassin | 9 | 175 | 105 | M:38-78 / D:22-47 [Haste] (23/78) | **4.2** | 37.2k | 76.2k | 84.1k | `0.46` | 12× serpent sword, 25× scarf, 2× stealthring | 🟢 Parejo |
| Hunter | 13 | 150 | 150 | D:37-84 [Dist(5)] (36/84) | **4.2** | 33.9k | 69.0k | 78.8k | `0.57` | 85× brass armor, 41× small ruby, 73× bow | 🔵 Alto |
| Orc Shaman | 27 | 115 | 110 | M:0-15 / Sp:≤50 [Heal,Dist(5),Summon×5] (13/65) | **4.2** | 34.2k | 34.9k | 39.5k | `0.33` | 22× wand of vortex, 25× chain helmet, 42× spear | 🟢 Parejo |
| Lizard Snakecharmer | 4 | 325 | 185 | M:0-30 [Heal,Summon×4] (8/30) | **4.1** | 101.3k | 101.3k | 181.3k | `0.51` | 83× charmer tiara, 7× bast skirt | 🟣 Muy Alto |
| Bandit | 27 | 245 | 65 | M:22-65 (17/65) | **4.1** | 26.0k | 26.7k | 26.7k | `0.11` | 72× hatchet | 🟠 Bajo |
| Elf Scout | 9 | 160 | 75 | D:10-70 [Dist(5)] (25/70) | **4.1** | 17.6k | 17.6k | 25.7k | `0.16` | 103× bow, 2838× arrow, 1× longsword | 🟠 Bajo |
| Slime | 10 | 150 | 160 | M:27-75 [Summon×4] (20/75) | **4.1** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Spit Nettle | 2 | 150 | 25 | D:10-100 (22/100) | **4.1** | 9.024 | 9.024 | 9.024 | `0.06` | — | 🔴 Muy Bajo |
| Stalker | 4 | 150 | 90 | D:27-64 [Invis,Dist(3)] (15/64) | **4.1** | 33.9k | 51.0k | 52.9k | `0.36` | 9× obsidian lance, 36× brass legs, 206× throwing star | 🟢 Parejo |
| Minotaur Archer | 25 | 100 | 65 | M:0-5 / D:40-100 [Dist(5)] (38/100) | **4.0** | 23.7k | 48.3k | 68.3k | `0.70` | 5307× bolt, 29× brass armor, 71× scale armor | 🔵 Alto |
| Stone Troll | 5 | 160 | 90 | M:20-55 / D:12-30 (19/55) | **3.9** | 59.9k | 59.9k | 63.1k | `0.40` | 821× small stone, 5× morning star | 🟢 Parejo |
| Barbarian Brutetamer | 6 | 145 | 90 | M:5-30 / Sp:≤35 [AoE,Heal,Dist(3),Summon×2] (12/65) | **3.9** | 43.6k | 46.1k | 49.9k | `0.35` | 3× ring of healing, 10× small sapphire | 🟢 Parejo |
| Barbarian Skullhunter | 7 | 135 | 85 | M:15-55 / Sp:≤28 [AoE,Haste] (19/83) | **3.9** | 38.9k | 42.1k | 43.8k | `0.32` | 43× chain armor, 29× viking helmet, 5× battle axe | 🟢 Parejo |
| Elephant | 13 | 320 | 160 | M:0-40 (10/40) | **3.8** | 34.2k | 34.2k | 70.4k | `0.22` | 362× elephant tusk | 🟢 Parejo |
| Terror Bird | 3 | 300 | 150 | M:0-40 / D:0-40 [Heal] (10/40) | **3.8** | 17.0k | 17.0k | 17.0k | `0.06` | — | 🔴 Muy Bajo |
| Merlkin | 5 | 230 | 110 | Sp:≤37 [Dist(3)] (11/37) | **3.8** | 21.1k | 21.1k | 69.1k | `0.31` | 48× liche staff | 🟢 Parejo |
| Valkyrie | 8 | 190 | 85 | M:0-50 / D:10-25 (14/50) | **3.8** | 34.0k | 74.5k | 88.6k | `0.44` | 45× small diamond, 29× crystal necklace, 39× small ruby | 🟢 Parejo |
| Tortoise | 13 | 185 | 90 | M:10-40 / Sp:≤20 (13/60) | **3.8** | 29.3k | 30.3k | 31.2k | `0.18` | 18× plate shield, 9× battlehammer, 1× battle shield | 🟠 Bajo |
| Husky | 2 | 140 | 90 | M:5-50 / Sp:≤20 [Haste] (15/70) | **3.8** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Gazer | 4 | 250 | 120 | M:0-40 (8/40) | **3.7** | 29.1k | 29.1k | 29.1k | `0.12` | — | 🟠 Bajo |
| Barbarian Headsplitter | 5 | 100 | 85 | M:10-50 / D:10-45 / Sp:≤28 [AoE,Haste] (16/78) | **3.7** | 38.0k | 40.9k | 42.0k | `0.42` | 22× scale armor, 18× viking helmet, 71× hatchet | 🟢 Parejo |
| Dworc Voodoomaster | 6 | 250 | 100 | M:0-30 / D:0-10 (8/30) | **3.6** | 17.0k | 17.0k | 28.5k | `0.12` | 46× tribal mask | 🟠 Bajo |
| Orc Warrior | 104 | 125 | 50 | M:0-60 (12/60) | **3.6** | 28.0k | 34.2k | 36.1k | `0.28` | 68× sabre, 57× chain armor, 31× poison dagger | 🟢 Parejo |
| Ghoul | 38 | 100 | 85 | M:0-50 [Heal] (10/50) | **3.6** | 51.2k | 64.5k | 92.9k | `0.86` | 33× lifering, 113× scale armor, 61× viking helmet | 🔵 Alto |
| Lizard Sentinel | 11 | 265 | 100 | M:0-30 / D:0-20 (8/30) | **3.5** | 43.4k | 43.4k | 61.1k | `0.22` | 59× sentinel shield | 🟢 Parejo |
| Tarantula | 40 | 225 | 120 | M:0-30 (8/30) | **3.4** | 34.0k | 78.6k | 78.6k | `0.34` | 87× steel helmet, 22× plate legs, 118× scale armor | 🟢 Parejo |
| War Wolf | 8 | 140 | 55 | M:0-40 (10/40) | **3.4** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Dwarf Soldier | 20 | 135 | 70 | M:0-40 / D:7-28 (10/40) | **3.4** | 26.0k | 45.5k | 82.1k | `0.58` | 30× dwarfenring, 104× crossbow, 199× chain armor | 🔵 Alto |
| Smuggler | 27 | 130 | 48 | M:7-36 (11/36) | **3.3** | 59.5k | 86.9k | 86.9k | `0.68` | 96× brass armor, 34× brass legs | 🔵 Alto |
| Wild Warrior | 30 | 120 | 55 | M:0-40 (8/40) | **3.3** | 51.1k | 79.9k | 95.5k | `0.74` | 78× steel shield, 6× war hammer, 31× brass armor | 🔵 Alto |
| Amazon | 11 | 110 | 60 | D:17-44 [Dist(3)] (9/44) | **3.3** | 35.9k | 62.8k | 75.6k | `0.68` | 57× small ruby, 32× crystal necklace, 254× sabre | 🔵 Alto |
| Elf | 26 | 100 | 42 | M:12-48 / D:15-30 (12/48) | **3.3** | 25.9k | 29.2k | 39.7k | `0.41` | 3557× arrow, 70× bow, 43× longsword | 🟢 Parejo |
| Sibang | 8 | 225 | 95 | M:0-20 / D:0-20 (5/20) | **3.2** | 20.0k | 20.0k | 20.0k | `0.09` | — | 🔴 Muy Bajo |
| Crocodile | 14 | 105 | 40 | M:0-40 (10/40) | **3.2** | 17.0k | 37.0k | 37.0k | `0.26` | 20× crocodile boots | 🟢 Parejo |
| Orc Spearman | 5 | 105 | 38 | M:0-15 / D:1-35 [Dist(3)] (9/35) | **3.2** | 13.7k | 13.7k | 14.5k | `0.14` | 165× spear | 🔴 Muy Bajo |
| Imperial Squire | 10 | 95 | 45 | M:5-28 / Sp:≤20 (9/48) | **3.2** | 27.1k | 30.0k | 30.0k | `0.47` | 59× sword | 🟢 Parejo |
| Chakoya Windcaller | 3 | 84 | 48 | M:0-20 / Sp:≤35 [AoE,Dist(3)] (9/55) | **3.2** | 19.5k | 23.0k | 23.0k | `0.29` | 14× small sapphire | 🟢 Parejo |
| Minotaur | 57 | 100 | 50 | M:0-40 (8/40) | **3.1** | 49.7k | 59.2k | 66.0k | `0.65` | 111× chain armor, 110× plate shield, 98× chain helmet | 🔵 Alto |
| River Troll | 6 | 85 | 42 | M:8-32 / D:8-18 (10/32) | **3.1** | 42.9k | 42.9k | 43.9k | `0.52` | 215× spear | 🟢 Parejo |
| Chakoya Toolshaper | 3 | 80 | 40 | M:5-30 / D:5-25 / Sp:≤20 (10/50) | **3.1** | 18.1k | 18.5k | 18.5k | `0.24` | 35× hatchet | 🟠 Bajo |
| Chakoya Tribewarden | 4 | 68 | 40 | M:5-35 / Sp:≤20 (11/55) | **3.1** | 15.4k | 15.8k | 15.8k | `0.24` | 39× mace | 🟠 Bajo |
| Dwarf | 23 | 90 | 45 | M:0-30 (8/30) | **3.0** | 26.0k | 26.7k | 34.2k | `0.40` | 15× dwarfenring, 69× hatchet | 🟢 Parejo |

### Tier 1 — Muy Fácil / Fauna (34 monstruos — mediana 1k: 11.2k NPC / 11.2k Total, `0.27 gp/HP`)

| Monstruo | Spawns | HP | EXP | Ataque (DPS / Burst) | Dif. | Oro 1k | NPC Líq. 1k | Total 1k | gp/HP | Top Drops (1k sim) | Balance |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---|
| Polar Bear | 14 | 85 | 28 | M:0-35 (7/35) | **2.9** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Lion | 8 | 80 | 30 | M:0-35 (7/35) | **2.9** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Larva | 9 | 70 | 44 | M:12-37 (10/37) | **2.9** | 16.9k | 16.9k | 16.9k | `0.24` | — | 🟢 Parejo |
| Hyaena | 5 | 60 | 20 | M:0-40 (8/40) | **2.9** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Dworc Venomsniper | 21 | 80 | 30 | M:0-30 / D:0-10 (8/30) | **2.8** | 16.9k | 16.9k | 21.3k | `0.27` | 1503× poison arrow, 174× throwing knife | 🟢 Parejo |
| Rotworm | 58 | 65 | 40 | M:0-37 (7/37) | **2.8** | 34.9k | 40.6k | 40.6k | `0.61` | 109× sword, 22× mace | 🟣 Muy Alto |
| Frost Troll | 40 | 55 | 23 | M:0-40 (8/40) | **2.8** | 25.9k | 25.9k | 25.9k | `0.47` | — | 🔵 Alto |
| Skeleton | 16 | 50 | 35 | M:0-35 (7/35) | **2.7** | 15.3k | 18.9k | 21.7k | `0.44` | 47× viking helmet, 31× sword, 113× hatchet | 🔵 Alto |
| Bear | 18 | 80 | 23 | M:0-25 (5/25) | **2.6** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Dworc Fleshhunter | 4 | 80 | 35 | M:0-20 (5/20) | **2.6** | 23.0k | 23.0k | 49.3k | `0.62` | 242× bone shield, 35× poison dagger | 🟣 Muy Alto |
| Tiger | 6 | 75 | 40 | M:0-20 (5/20) | **2.6** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Orc | 21 | 70 | 25 | M:0-25 (6/25) | **2.6** | 17.0k | 22.2k | 22.2k | `0.31` | 105× sabre | 🔵 Alto |
| Goblin | 38 | 50 | 25 | M:0-25 / D:0-35 (7/35) | **2.6** | 16.9k | 22.5k | 23.7k | `0.48` | 93× short sword, 390× small stone | 🔵 Alto |
| Crab | 6 | 55 | 30 | M:0-25 (6/25) | **2.5** | 19.8k | 19.8k | 19.8k | `0.35` | — | 🔵 Alto |
| Swamp Troll | 3 | 55 | 25 | M:0-25 (5/25) | **2.5** | 21.1k | 21.1k | 21.1k | `0.38` | — | 🔵 Alto |
| Scorpion | 9 | 45 | 45 | M:0-28 (7/28) | **2.5** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Cobra | 11 | 65 | 30 | D:5-13 (4/13) | **2.2** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Centipede | 11 | 70 | 30 | M:0-10 (2/10) | **2.0** | 40.9k | 43.0k | 43.0k | `0.61` | 207× mace | 🟣 Muy Alto |
| Wasp | 9 | 35 | 24 | M:0-18 (4/18) | **2.0** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Bat | 5 | 30 | 30 | M:5-20 (5/20) | **2.0** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Winter Wolf | 49 | 30 | 20 | M:0-25 (5/25) | **2.0** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Troll | 58 | 50 | 20 | M:0-13 (3/13) | **1.9** | 18.9k | 18.9k | 23.0k | `0.46` | 32× bronze amulet, 312× spear, 18× silver amulet | 🔵 Alto |
| Poison Spider | 14 | 26 | 22 | M:0-20 (4/20) | **1.8** | 13.5k | 13.5k | 13.5k | `0.52` | — | 🔵 Alto |
| Wolf | 22 | 25 | 18 | M:0-20 (4/20) | **1.8** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Cave Rat | 11 | 30 | 10 | M:0-15 (3/15) | **1.7** | 16.0k | 16.0k | 16.0k | `0.53` | — | 🔵 Alto |
| Bug | 17 | 29 | 18 | M:0-10 (2/10) | **1.4** | 7.024 | 7.024 | 7.024 | `0.24` | — | 🟢 Parejo |
| Rat | 8 | 20 | 5 | M:0-10 (2/10) | **1.2** | 11.4k | 11.4k | 11.4k | `0.56` | — | 🟢 Parejo |
| Spider | 11 | 20 | 12 | M:0-9 (2/9) | **1.1** | 8.152 | 8.152 | 8.152 | `0.40` | — | 🟢 Parejo |
| Snake | 4 | 15 | 10 | M:0-7 (1/7) | **0.8** | 0 | 0 | 0 | `0.00` | — | ⚫ Sin loot |
| Deer | 8 | 25 | 0 | 0 [Dist(8)] (0/0) | **0.6** | 0 | 0 | 0 | `0.00` | — | Fauna/Sin EXP |
| Flamingo | 1 | 25 | 0 | 0 [Dist(6)] (0/0) | **0.6** | 0 | 0 | 0 | `0.00` | — | Fauna/Sin EXP |
| Parrot | 1 | 25 | 0 | 0 [Dist(4)] (0/0) | **0.6** | 0 | 0 | 0 | `0.00` | — | Fauna/Sin EXP |
| Pig | 3 | 15 | 0 | 0 [Dist(2)] (0/0) | **0.5** | 0 | 0 | 0 | `0.00` | — | Fauna/Sin EXP |
| Rabbit | 8 | 15 | 0 | 0 [Dist(8)] (0/0) | **0.5** | 0 | 0 | 0 | `0.00` | — | Fauna/Sin EXP |

### Inactivos en mapa/eventos y Trainers (13 criaturas)

| Monstruo | Tipo | HP | EXP | Ataque | Dif. | Oro 1k | NPC Líq. 1k | Total 1k | Top Drops (1k sim) |
|---|---|---:|---:|---|---:|---:|---:|---:|---|
| Deathslicer | No spawneado | 1.000 | 0 | M:105-555 | 8.3 | 310.4k | 344.1k | 344.1k | 338× battlehammer |
| Panda | No spawneado | 80 | 23 | M:0-10 | 2.1 | 0 | 0 | 0 | — |
| Badger | No spawneado | 20 | 0 | M:0-5 [Dist(3)] | 0.9 | 0 | 0 | 0 | — |
| Black Sheep | No spawneado | 20 | 0 | 0 [Dist(8)] | 0.5 | 0 | 0 | 0 | — |
| Dog | No spawneado | 20 | 0 | 0 | 0.5 | 0 | 0 | 0 | — |
| Sheep | No spawneado | 20 | 0 | 0 [Dist(5)] | 0.5 | 0 | 0 | 0 | — |
| Skunk | No spawneado | 20 | 0 | 0 [Dist(3)] | 0.5 | 0 | 0 | 0 | — |
| Chicken | No spawneado | 15 | 0 | 0 [Dist(5)] | 0.5 | 0 | 0 | 0 | — |
| Butterfly | No spawneado | 2 | 0 | 0 [Dist(3)] | 0.4 | 0 | 0 | 0 | — |
| Private Trainer Dummy | Trainer | 500.000 | 0 | 0 (Trainer) | 0.0 | 0 | 0 | 0 | — |
| Elite Trainer Monk | Trainer | 50.000 | 0 | 0 (Trainer) | 0.0 | 0 | 0 | 0 | — |
| Mini Trainer Monk | Trainer | 50.000 | 0 | 0 (Trainer) | 0.0 | 0 | 0 | 0 | — |
| Trainer Monk | Trainer | 50.000 | 0 | 0 (Trainer) | 0.0 | 0 | 0 | 0 | — |

---

## 4. Simulación de 1.000 kills — Variantes Rage (318 criaturas, 106 familias)

Cada familia aparece ordenada según la dificultad del monstruo base (de más difícil a más fácil). Tras los ajustes, las **106 familias** cumplen estrictamente `Base < Angry < Furious < Enraged` en valor esperado de loot.

| Monstruo Rage | HP | EXP | Ataque (DPS / Burst) | Dif. | Oro 1k | NPC Líq. 1k | Total 1k | gp/HP | Top Drops (1k sim) |
|---|---:|---:|---|---:|---:|---:|---:|---:|---|
| Angry Metal Demon | 19.000 | 18.000 | M:357-918 / Sp:≤460 [Heal,AoE,ManaDrain] (648/1378) | **9.4** | 390.6k | 1.55M | 1.55M | `0.08` | 4× magic plate armor, 2× mastermind shield, 8× giant sword |
| Furious Metal Demon | 23.750 | 23.760 | M:462-1188 / Sp:≤460 [Heal,AoE,ManaDrain] (817/1648) | **9.7** | 394.5k | 2.91M | 2.91M | `0.11` | 5× magic plate armor, 32× gold nugget, 1223× small emerald |
| Enraged Metal Demon | 28.975 | 30.240 | M:567-1458 / Sp:≤460 [Heal,AoE,ManaDrain] (986/1918) | **9.9** | 399.4k | 3.47M | 3.47M | `0.12` | 54× gold nugget, 1947× small emerald, 2170× small amethyst |
| Angry Demon | 16.400 | 15.000 | M:326-867 / Sp:≤400 [Heal,AoE,ManaDrain,Summon×2] (382/1267) | **9.2** | 335.3k | 1.48M | 1.96M | `0.09` | 6× mastermind shield, 3× medusa sword, 2× imperial crown armor |
| Furious Demon | 20.500 | 19.800 | M:422-1122 / Sp:≤400 [Heal,AoE,ManaDrain,Summon×2] (470/1522) | **9.4** | 353.9k | 2.81M | 3.49M | `0.15` | 64× gold nugget, 3× imperial crown armor, 4× medusa sword |
| Enraged Demon | 25.010 | 25.200 | M:518-1377 / Sp:≤400 [Heal,AoE,ManaDrain,Summon×2] (558/1777) | **9.7** | 348.8k | 3.34M | 3.86M | `0.16` | 71× gold nugget, 1837× small emerald, 2083× small amethyst |
| Angry Serpent Spawn | 10.000 | 9.000 | M:153-442 / D:0-238 / Sp:≤300 [AoE,Heal,Summon×3] (198/742) | **8.4** | 476.7k | 941.7k | 1.03M | `0.11` | 10× tower shield, 3× nightglass dagger, 2× boots of haste |
| Furious Serpent Spawn | 12.500 | 11.880 | M:198-572 / D:0-308 / Sp:≤300 [AoE,Heal,Summon×3] (242/872) | **8.8** | 474.9k | 2.24M | 2.31M | `0.18` | 35× gold nugget, 1131× small emerald, 1220× small amethyst |
| Enraged Serpent Spawn | 15.250 | 15.120 | M:243-702 / D:0-378 / Sp:≤300 [AoE,Heal,Summon×3] (286/1002) | **9.0** | 495.8k | 3.26M | 3.33M | `0.21` | 71× gold nugget, 1797× small emerald, 2089× small amethyst |
| Angry Root Colossus | 9.600 | 8.500 | M:238-612 / Sp:≤180 [AoE] (230/792) | **8.2** | 331.8k | 582.0k | 2.25M | `0.15` | 6× heartwood maul, 5× rootcleaver, 4× giant sword |
| Furious Root Colossus | 12.000 | 11.220 | M:308-792 / Sp:≤180 [AoE] (292/972) | **8.5** | 324.4k | 1.77M | 3.00M | `0.22` | 5× rootcleaver, 3× heartwood maul, 38× gold nugget |
| Enraged Root Colossus | 14.640 | 14.280 | M:378-972 / Sp:≤180 [AoE] (355/1152) | **8.7** | 326.6k | 2.72M | 3.05M | `0.24` | 66× gold nugget, 1719× small emerald, 2145× small amethyst |
| Angry Behemoth | 8.000 | 6.250 | M:272-680 / D:156-289 [Haste] (238/680) | **8.2** | 448.6k | 1.13M | 1.16M | `0.15` | 10× steel boots, 8× giant sword, 337× small amethyst |
| Furious Behemoth | 10.000 | 8.250 | M:352-880 / D:202-374 [Haste] (308/880) | **8.5** | 445.8k | 2.40M | 2.69M | `0.26` | 11× steel boots, 1234× small emerald, 1520× small amethyst |
| Enraged Behemoth | 12.200 | 10.500 | M:432-1080 / D:248-459 [Haste] (378/1080) | **8.8** | 442.0k | 3.23M | 3.69M | `0.31` | 46× gold nugget, 2174× small amethyst, 1723× small emerald |
| Angry Imperial Hero | 6.000 | 6.500 | M:255-646 / D:153-357 / Sp:≤150 [AoE,Heal] (237/796) | **8.1** | 274.8k | 840.0k | 1.47M | `0.20` | 5× imperial crown armor, 13× crown armor, 6× crown legs |
| Furious Imperial Hero | 7.500 | 8.580 | M:330-836 / D:198-462 / Sp:≤150 [AoE,Heal] (304/986) | **8.4** | 271.6k | 2.12M | 2.40M | `0.32` | 33× gold nugget, 1184× small emerald, 1339× small amethyst |
| Enraged Imperial Hero | 9.150 | 10.920 | M:405-1026 / D:243-567 / Sp:≤150 [AoE,Heal] (370/1176) | **8.7** | 275.1k | 3.04M | 3.46M | `0.36` | 68× gold nugget, 1817× small emerald, 2193× small amethyst |
| Angry Metal Hydra | 6.800 | 8.250 | M:153-391 / Sp:≤290 [AoE,Heal] (175/681) | **7.9** | 568.2k | 1.21M | 1.24M | `0.18` | 5× royal helmet, 5× boots of haste, 351× small emerald |
| Furious Metal Hydra | 8.500 | 10.890 | M:198-506 / Sp:≤290 [AoE,Heal] (215/796) | **8.2** | 566.4k | 2.49M | 2.52M | `0.28` | 1463× small emerald, 36× gold nugget, 1469× small amethyst |
| Enraged Metal Hydra | 10.370 | 13.860 | M:243-621 / Sp:≤290 [AoE,Heal] (255/911) | **8.4** | 558.7k | 3.14M | 3.17M | `0.32` | 61× gold nugget, 2016× small emerald, 2154× small amethyst |
| Angry Warlock | 6.400 | 10.000 | M:46-144 / Sp:≤200 [AoE,ManaDrain,Invis,Dist(5)] (93/344) | **7.8** | 329.2k | 730.5k | 987.9k | `0.13` | 17× ring of the skies, 8× golden armor, 9× skull staff |
| Furious Warlock | 8.000 | 13.200 | M:59-187 / Sp:≤200 [AoE,ManaDrain,Invis,Dist(5)] (104/387) | **8.1** | 319.0k | 2.04M | 2.74M | `0.31` | 38× gold nugget, 3× imperial crown armor, 22× ring of the skies |
| Enraged Warlock | 9.760 | 16.800 | M:73-230 / Sp:≤200 [AoE,ManaDrain,Invis,Dist(5)] (116/430) | **8.3** | 323.5k | 3.01M | 3.43M | `0.36` | 71× gold nugget, 1887× small emerald, 2089× small amethyst |
| Angry Dark Hydra | 6.400 | 7.500 | M:153-374 / Sp:≤300 [AoE,Heal] (172/674) | **7.8** | 559.2k | 989.8k | 1.03M | `0.18` | 5× royal helmet, 5× medusa shield, 204× small amethyst |
| Furious Dark Hydra | 8.000 | 9.900 | M:198-484 / Sp:≤300 [AoE,Heal] (211/784) | **8.1** | 549.3k | 2.23M | 2.26M | `0.29` | 1279× small emerald, 27× gold nugget, 1326× small amethyst |
| Enraged Dark Hydra | 9.760 | 12.600 | M:243-594 / Sp:≤300 [AoE,Heal] (250/894) | **8.3** | 558.2k | 3.43M | 3.52M | `0.33` | 76× gold nugget, 2227× small amethyst, 1729× small emerald |
| Angry Metal Dragon | 5.800 | 8.000 | M:153-425 / Sp:≤300 [AoE,Heal] (182/725) | **7.8** | 404.6k | 981.7k | 996.7k | `0.19` | 6× royal helmet, 259× small sapphire, 7× tower shield |
| Furious Metal Dragon | 7.250 | 10.560 | M:198-550 / Sp:≤300 [AoE,Heal] (225/850) | **8.1** | 411.1k | 2.22M | 2.23M | `0.32` | 1448× small amethyst, 1136× small emerald, 851× small ruby |
| Enraged Metal Dragon | 8.845 | 13.440 | M:243-675 / Sp:≤300 [AoE,Heal] (267/975) | **8.3** | 421.4k | 3.10M | 3.11M | `0.36` | 60× gold nugget, 1765× small emerald, 2191× small amethyst |
| Angry Black Dragon | 5.200 | 7.250 | M:136-408 / Sp:≤290 [AoE,Heal] (178/698) | **7.7** | 385.2k | 1.20M | 1.21M | `0.20` | 9× royal helmet, 5× dragon scale mail, 8× tower shield |
| Furious Black Dragon | 6.500 | 9.570 | M:176-528 / Sp:≤290 [AoE,Heal] (218/818) | **8.0** | 389.3k | 2.14M | 2.15M | `0.34` | 1240× small emerald, 30× gold nugget, 1346× small amethyst |
| Enraged Black Dragon | 7.930 | 12.180 | M:216-648 / Sp:≤290 [AoE,Heal] (258/938) | **8.2** | 402.1k | 3.12M | 3.13M | `0.39` | 61× gold nugget, 1804× small emerald, 2060× small amethyst |
| Angry Quara Predator | 4.070 | 4.140 | M:64-432 / Sp:≤270 [Haste] (157/702) | **7.6** | 228.2k | 417.7k | 420.4k | `0.10` | 4× tower shield, 142× small amethyst, 90× small diamond |
| Furious Quara Predator | 5.060 | 5.400 | M:82-554 / Sp:≤270 [Haste] (192/824) | **7.8** | 223.3k | 1.08M | 1.08M | `0.22` | 742× small emerald, 18× gold nugget, 885× small amethyst |
| Enraged Quara Predator | 6.160 | 6.840 | M:100-675 / Sp:≤270 [Haste] (227/945) | **8.0** | 230.8k | 1.63M | 1.63M | `0.27` | 1311× small emerald, 1469× small amethyst, 23× gold nugget |
| Angry Hydra | 4.500 | 5.250 | M:102-255 / Sp:≤300 [Heal,AoE] (130/555) | **7.4** | 453.7k | 843.3k | 867.0k | `0.21` | 5× boots of haste, 159× small emerald, 189× small amethyst |
| Furious Hydra | 5.625 | 6.930 | M:132-330 / Sp:≤300 [Heal,AoE] (156/630) | **7.7** | 459.3k | 2.16M | 2.19M | `0.40` | 1259× small emerald, 1430× small amethyst, 26× gold nugget |
| Enraged Hydra | 6.862 | 8.820 | M:162-405 / Sp:≤300 [Heal,AoE] (182/705) | **7.9** | 460.6k | 2.93M | 2.96M | `0.46` | 50× gold nugget, 1753× small emerald, 1930× small amethyst |
| Angry Black Knight | 3.330 | 3.680 | M:131-440 / D:115-288 / Sp:≤150 [AoE] (157/590) | **7.5** | 213.4k | 443.7k | 444.7k | `0.15` | 2× boots of haste, 152× small amethyst, 97× small emerald |
| Furious Black Knight | 4.140 | 4.800 | M:168-564 / D:148-369 / Sp:≤150 [AoE] (197/714) | **7.8** | 212.2k | 1.33M | 1.33M | `0.33` | 950× small amethyst, 759× small emerald, 18× gold nugget |
| Enraged Black Knight | 5.040 | 6.080 | M:205-688 / D:180-450 / Sp:≤150 [AoE] (237/838) | **8.0** | 212.1k | 2.20M | 2.35M | `0.42` | 44× gold nugget, 1221× small emerald, 10× boots of haste |
| Angry Frost Dragon | 4.400 | 6.000 | M:119-357 / Sp:≤260 [AoE,Heal] (167/617) | **7.5** | 325.8k | 766.1k | 766.1k | `0.17` | 389× small sapphire, 19× ice rapier, 5× dragon lance |
| Furious Frost Dragon | 5.500 | 7.920 | M:154-462 / Sp:≤260 [AoE,Heal] (202/722) | **7.7** | 331.3k | 1.93M | 1.93M | `0.35` | 1215× small emerald, 1425× small amethyst, 24× gold nugget |
| Enraged Frost Dragon | 6.710 | 10.080 | M:189-567 / Sp:≤260 [AoE,Heal] (237/827) | **7.9** | 329.8k | 2.75M | 2.75M | `0.42` | 56× gold nugget, 1813× small emerald, 2013× small amethyst |
| Angry Dragon Lord | 3.800 | 5.250 | M:105-348 / Sp:≤250 [AoE,Heal] (158/598) | **7.4** | 292.0k | 873.4k | 879.3k | `0.21` | 6× dragon scale mail, 6× dragon lance, 2× royal helmet |
| Furious Dragon Lord | 4.750 | 6.930 | M:136-451 / Sp:≤250 [AoE,Heal] (192/701) | **7.7** | 290.4k | 1.93M | 1.93M | `0.42` | 31× gold nugget, 1225× small emerald, 1373× small amethyst |
| Enraged Dragon Lord | 5.795 | 8.820 | M:167-554 / Sp:≤250 [AoE,Heal] (225/804) | **7.9** | 291.3k | 2.79M | 2.80M | `0.50` | 60× gold nugget, 1810× small emerald, 2085× small amethyst |
| Angry Quara Pincher | 3.330 | 3.105 | M:48-368 / Sp:≤270 (150/638) | **7.3** | 294.9k | 463.6k | 463.6k | `0.15` | 161× small ruby, 7× warrior helmet, 107× small emerald |
| Furious Quara Pincher | 4.140 | 4.050 | M:61-471 / Sp:≤270 (179/741) | **7.6** | 294.8k | 1.13M | 1.13M | `0.28` | 750× small emerald, 841× small amethyst, 599× small ruby |
| Enraged Quara Pincher | 5.040 | 5.130 | M:75-575 / Sp:≤270 (208/845) | **7.8** | 292.2k | 1.71M | 1.71M | `0.34` | 1172× small emerald, 1417× small amethyst, 25× gold nugget |
| Angry Ice Spider | 3.330 | 3.565 | M:160-416 / Sp:≤150 [AoE,Heal,Haste] (154/566) | **7.3** | 125.3k | 381.8k | 389.8k | `0.11` | 238× small sapphire, 126× small emerald, 203× iron helmet |
| Furious Ice Spider | 4.140 | 4.650 | M:205-533 / Sp:≤150 [AoE,Heal,Haste] (195/683) | **7.6** | 128.1k | 1.13M | 1.14M | `0.26` | 22× gold nugget, 792× small emerald, 915× small amethyst |
| Enraged Ice Spider | 5.040 | 5.890 | M:250-650 / Sp:≤150 [AoE,Heal,Haste] (235/800) | **7.9** | 126.9k | 1.57M | 1.57M | `0.32` | 31× gold nugget, 1203× small emerald, 1339× small amethyst |
| Angry Giant Spider | 2.405 | 2.070 | M:192-480 / Sp:≤10 [AoE,Haste,Heal,Summon×5] (169/490) | **7.4** | 128.2k | 261.1k | 267.1k | `0.11` | 18× platinum amulet, 214× iron helmet, 5× knight armor |
| Furious Giant Spider | 2.990 | 2.700 | M:246-615 / Sp:≤10 [AoE,Haste,Heal,Summon×5] (217/625) | **7.7** | 126.0k | 1.00M | 1.01M | `0.34` | 770× small emerald, 888× small amethyst, 15× gold nugget |
| Enraged Giant Spider | 3.640 | 3.420 | M:300-750 / Sp:≤10 [AoE,Haste,Heal,Summon×5] (264/760) | **8.0** | 126.5k | 1.56M | 1.57M | `0.44` | 1177× small emerald, 29× gold nugget, 1397× small amethyst |
| Angry Hero | 2.590 | 2.760 | M:160-400 / D:83-208 (140/400) | **7.2** | 168.9k | 396.9k | 427.0k | `0.17` | 93× scarf, 4× crown armor, 3× crown shield |
| Furious Hero | 3.220 | 3.600 | M:205-512 / D:107-266 (179/512) | **7.5** | 169.5k | 1.21M | 1.23M | `0.37` | 27× gold nugget, 918× small amethyst, 706× small emerald |
| Enraged Hero | 3.920 | 4.560 | M:250-625 / D:130-325 (219/625) | **7.7** | 170.0k | 1.68M | 1.75M | `0.46` | 1175× small emerald, 1467× small amethyst, 28× gold nugget |
| Angry Emerald Scarab | 2.775 | 2.645 | M:104-352 / D:0-144 / Sp:≤85 [AoE,Haste] (119/437) | **7.1** | 238.2k | 399.1k | 406.9k | `0.16` | 221× small emerald, 2× great halberd, 114× small amethyst |
| Furious Emerald Scarab | 3.450 | 3.450 | M:133-451 / D:0-184 / Sp:≤85 [AoE,Haste] (151/536) | **7.4** | 237.3k | 1.13M | 1.14M | `0.33` | 861× small emerald, 891× small amethyst, 15× gold nugget |
| Enraged Emerald Scarab | 4.200 | 4.370 | M:162-550 / D:0-225 / Sp:≤85 [AoE,Haste] (183/635) | **7.6** | 238.5k | 1.76M | 1.77M | `0.40` | 1380× small emerald, 1409× small amethyst, 28× gold nugget |
| Angry Hellhound | 2.775 | 2.990 | M:96-336 / Sp:≤140 [AoE] (121/476) | **7.1** | 213.6k | 333.1k | 336.1k | `0.13` | 7× fire sword, 107× small ruby, 103× small emerald |
| Furious Hellhound | 3.450 | 3.900 | M:123-430 / Sp:≤140 [AoE] (151/570) | **7.3** | 211.6k | 1.06M | 1.06M | `0.30` | 860× small emerald, 943× small amethyst, 537× small ruby |
| Enraged Hellhound | 4.200 | 4.940 | M:150-525 / Sp:≤140 [AoE] (182/665) | **7.6** | 212.4k | 1.63M | 1.63M | `0.38` | 1557× small amethyst, 1218× small emerald, 29× gold nugget |
| Angry Wyrm | 3.376 | 3.565 | M:64-208 / Sp:≤110 [AoE,Heal] (87/318) | **6.9** | 219.0k | 503.5k | 602.4k | `0.18` | 20× wand of cosmic energy, 8× skull staff, 18× platinum amulet |
| Furious Wyrm | 4.198 | 4.650 | M:82-266 / Sp:≤110 [AoE,Heal] (106/376) | **7.1** | 217.2k | 1.22M | 1.30M | `0.31` | 734× small emerald, 16× gold nugget, 799× small amethyst |
| Enraged Wyrm | 5.110 | 5.890 | M:100-325 / Sp:≤110 [AoE,Heal] (125/435) | **7.4** | 219.4k | 1.79M | 1.90M | `0.36` | 31× gold nugget, 1447× small amethyst, 1154× small emerald |
| Angry Crystal Spider | 2.312 | 2.070 | M:80-320 / Sp:≤150 [AoE,Haste] (108/470) | **6.9** | 187.3k | 393.1k | 398.6k | `0.16` | 219× small sapphire, 4× frostwarden aegis, 119× small emerald |
| Furious Crystal Spider | 2.875 | 2.700 | M:102-410 / Sp:≤150 [AoE,Haste] (136/560) | **7.2** | 188.2k | 1.03M | 1.03M | `0.37` | 855× small amethyst, 617× small emerald, 15× gold nugget |
| Enraged Crystal Spider | 3.500 | 3.420 | M:125-500 / Sp:≤150 [AoE,Haste] (164/650) | **7.4** | 185.7k | 1.67M | 1.68M | `0.46` | 34× gold nugget, 1249× small emerald, 1340× small amethyst |
| Angry Mutated Tiger | 2.035 | 1.955 | M:104-352 / Sp:≤160 [Heal,AoE,Haste] (133/512) | **6.9** | 195.9k | 297.6k | 309.5k | `0.16` | 136× small amethyst, 98× small emerald, 4× knight armor |
| Furious Mutated Tiger | 2.530 | 2.550 | M:133-451 / Sp:≤160 [Heal,AoE,Haste] (165/611) | **7.2** | 199.6k | 1.00M | 1.01M | `0.40` | 743× small emerald, 926× small amethyst, 15× gold nugget |
| Enraged Mutated Tiger | 3.080 | 3.230 | M:162-550 / Sp:≤160 [Heal,AoE,Haste] (197/710) | **7.4** | 199.2k | 1.57M | 1.58M | `0.51` | 33× gold nugget, 1090× small emerald, 1362× small amethyst |
| Angry Ancient Scarab | 1.850 | 1.656 | M:86-288 / D:0-144 / Sp:≤20 [Haste,Summon×5] (96/308) | **6.8** | 167.1k | 390.0k | 396.3k | `0.20` | 4× great halberd, 4× tiled breastplate, 7× daramanian waraxe |
| Furious Ancient Scarab | 2.300 | 2.160 | M:111-369 / D:0-184 / Sp:≤20 [Haste,Summon×5] (123/389) | **7.1** | 166.9k | 1.10M | 1.11M | `0.48` | 761× small emerald, 894× small amethyst, 13× gold nugget |
| Enraged Ancient Scarab | 2.800 | 2.736 | M:135-450 / D:0-225 / Sp:≤20 [Haste,Summon×5] (149/470) | **7.4** | 167.2k | 1.55M | 1.56M | `0.61` | 1489× small amethyst, 1188× small emerald, 840× small ruby |
| Angry Orc Berserker Pot Thrower | 2.775 | 2.415 | M:122-304 [AoE] (106/304) | **6.8** | 194.8k | 458.3k | 486.3k | `0.17` | 14× warrior helmet, 195× small amethyst, 19× knight axe |
| Furious Orc Berserker Pot Thrower | 3.450 | 3.150 | M:156-389 [AoE] (136/389) | **7.1** | 194.7k | 1.16M | 1.18M | `0.33` | 805× small emerald, 941× small amethyst, 17× gold nugget |
| Enraged Orc Berserker Pot Thrower | 4.200 | 3.990 | M:190-475 [AoE] (166/475) | **7.3** | 192.7k | 1.61M | 1.63M | `0.41` | 1537× small amethyst, 1141× small emerald, 24× gold nugget |
| Angry Worker Golem | 2.720 | 2.875 | M:80-256 / Sp:≤88 [AoE,Heal] (91/344) | **6.8** | 237.8k | 495.9k | 549.6k | `0.22` | 21× war hammer, 204× small amethyst, 5× tower shield |
| Furious Worker Golem | 3.381 | 3.750 | M:102-328 / Sp:≤88 [AoE,Heal] (115/416) | **7.0** | 242.0k | 1.21M | 1.24M | `0.39` | 919× small amethyst, 723× small emerald, 14× gold nugget |
| Enraged Worker Golem | 4.116 | 4.750 | M:125-400 / Sp:≤88 [AoE,Heal] (139/488) | **7.3** | 245.1k | 1.74M | 1.79M | `0.45` | 1192× small emerald, 1484× small amethyst, 26× gold nugget |
| Angry Orc Warlord | 1.615 | 1.407 | M:135-338 / D:72-180 (118/338) | **6.7** | 118.1k | 291.7k | 411.0k | `0.28` | 11× crusader helmet, 2× crystal arrow, 21× stealthring |
| Furious Orc Warlord | 1.995 | 1.809 | M:171-428 / D:91-228 (150/428) | **7.0** | 119.4k | 674.0k | 814.2k | `0.44` | 465× small emerald, 16× crusader helmet, 478× small amethyst |
| Enraged Orc Warlord | 2.422 | 2.278 | M:207-518 / D:110-276 (181/518) | **7.3** | 119.0k | 963.1k | 1.13M | `0.53` | 679× small emerald, 841× small amethyst, 417× small ruby |
| Angry Bog Raider | 2.405 | 2.185 | M:48-176 / Sp:≤130 [AoE,Heal] (73/306) | **6.6** | 171.4k | 277.6k | 287.6k | `0.12` | 155× small emerald, 121× small amethyst, 49× small ruby |
| Furious Bog Raider | 2.990 | 2.850 | M:61-225 / Sp:≤130 [AoE,Heal] (88/355) | **6.8** | 169.6k | 961.1k | 969.8k | `0.33` | 782× small emerald, 844× small amethyst, 14× gold nugget |
| Enraged Bog Raider | 3.640 | 3.610 | M:75-275 / Sp:≤130 [AoE,Heal] (104/405) | **7.1** | 172.4k | 1.50M | 1.51M | `0.43` | 1190× small emerald, 1486× small amethyst, 29× gold nugget |
| Angry Dragon | 1.850 | 1.610 | M:59-176 / Sp:≤140 [AoE,Heal] (83/316) | **6.6** | 213.0k | 404.4k | 427.7k | `0.24` | 61× broad sword, 113× small emerald, 108× small amethyst |
| Furious Dragon | 2.300 | 2.100 | M:76-225 / Sp:≤140 [AoE,Heal] (99/365) | **6.8** | 213.5k | 1.11M | 1.14M | `0.49` | 766× small emerald, 910× small amethyst, 524× small ruby |
| Enraged Dragon | 2.800 | 2.660 | M:92-275 / Sp:≤140 [AoE,Heal] (116/415) | **7.0** | 212.3k | 1.75M | 1.78M | `0.62` | 35× gold nugget, 1259× small emerald, 1417× small amethyst |
| Angry Undead Gladiator | 1.850 | 1.840 | M:64-240 / D:72-192 / Sp:≤110 (85/350) | **6.5** | 240.1k | 383.2k | 418.1k | `0.22` | 137× small amethyst, 96× small emerald, 122× scimitar |
| Furious Undead Gladiator | 2.300 | 2.400 | M:82-308 / D:92-246 / Sp:≤110 (107/418) | **6.8** | 238.8k | 1.10M | 1.14M | `0.48` | 952× small amethyst, 735× small emerald, 17× gold nugget |
| Enraged Undead Gladiator | 2.800 | 3.040 | M:100-375 / D:112-300 / Sp:≤110 (128/485) | **7.0** | 234.5k | 1.60M | 1.63M | `0.59` | 29× gold nugget, 1421× small amethyst, 1136× small emerald |
| Angry Mutated Bat | 1.530 | 1.292 | M:75-248 / Sp:≤160 [AoE] (89/408) | **6.5** | 185.5k | 244.2k | 259.2k | `0.18` | 14× obsidian lance, 64× black pearl, 69× small amethyst |
| Furious Mutated Bat | 1.890 | 1.660 | M:95-314 / Sp:≤160 [AoE] (110/474) | **6.8** | 185.4k | 587.4k | 600.8k | `0.32` | 576× small amethyst, 408× small emerald, 258× small ruby |
| Enraged Mutated Bat | 2.295 | 2.091 | M:115-379 / Sp:≤160 [AoE] (132/539) | **7.0** | 186.9k | 960.5k | 972.0k | `0.40` | 920× small amethyst, 732× small emerald, 506× small ruby |
| Angry Lich | 1.628 | 2.070 | M:16-144 / Sp:≤184 [Heal] (79/328) | **6.6** | 217.4k | 428.4k | 428.4k | `0.26` | 26× platinum amulet, 6× relic of ulm, 108× small emerald |
| Furious Lich | 2.024 | 2.700 | M:20-184 / Sp:≤240 [Heal] (103/424) | **6.9** | 218.5k | 1.18M | 1.18M | `0.57` | 19× gold nugget, 725× small emerald, 872× small amethyst |
| Enraged Lich | 2.464 | 3.420 | M:25-225 / Sp:≤304 [Heal] (130/529) | **7.2** | 217.3k | 1.80M | 1.80M | `0.71` | 1263× small emerald, 30× gold nugget, 1320× small amethyst |
| Angry Vampire Bride | 2.220 | 2.415 | M:48-192 / Sp:≤80 [Heal] (70/272) | **6.4** | 236.3k | 371.2k | 412.0k | `0.20` | 145× small ruby, 119× small emerald, 131× small amethyst |
| Furious Vampire Bride | 2.760 | 3.150 | M:61-246 / Sp:≤80 [Heal] (87/326) | **6.7** | 240.4k | 1.09M | 1.13M | `0.41` | 987× small amethyst, 762× small emerald, 15× gold nugget |
| Enraged Vampire Bride | 3.360 | 3.990 | M:75-300 / Sp:≤80 [Heal] (104/380) | **7.0** | 240.5k | 1.53M | 1.57M | `0.51` | 1174× small emerald, 1368× small amethyst, 22× gold nugget |
| Angry Necromancer | 986 | 1.218 | M:0-75 / Sp:≤105 [Heal,AoE,Dist(5),Summon×5] (43/180) | **6.1** | 67.9k | 347.5k | 347.5k | `0.31` | 7× boots of haste, 50× clerical mace, 65× small amethyst |
| Furious Necromancer | 1.218 | 1.566 | M:0-95 / Sp:≤105 [Heal,AoE,Dist(5),Summon×5] (47/200) | **6.3** | 67.9k | 703.3k | 703.3k | `0.53` | 8× boots of haste, 409× small emerald, 475× small amethyst |
| Enraged Necromancer | 1.479 | 1.972 | M:0-115 / Sp:≤105 [Heal,AoE,Dist(5),Summon×5] (51/220) | **6.5** | 67.9k | 994.0k | 994.0k | `0.69` | 8× boots of haste, 877× small amethyst, 691× small emerald |
| Angry Pirate Corsair | 1.148 | 945 | M:75-255 / D:60-210 / Sp:≤88 [AoE,Haste] (90/343) | **6.3** | 142.6k | 226.0k | 230.3k | `0.19` | 6× fire sword, 7× platinum amulet, 67× white pearl |
| Furious Pirate Corsair | 1.418 | 1.215 | M:95-323 / D:76-266 / Sp:≤88 [AoE,Haste] (112/411) | **6.6** | 142.8k | 536.8k | 540.6k | `0.38` | 447× small emerald, 519× small amethyst, 227× small ruby |
| Enraged Pirate Corsair | 1.721 | 1.530 | M:115-391 / D:92-322 / Sp:≤88 [AoE,Haste] (134/479) | **6.8** | 142.3k | 803.1k | 807.5k | `0.50` | 804× small amethyst, 605× small emerald, 486× small ruby |
| Angry Quara Mantassin | 1.360 | 1.050 | M:30-180 / Sp:≤80 [Haste] (57/260) | **6.1** | 177.2k | 208.3k | 234.3k | `0.17` | 13× stealthring, 23× halberd, 36× small emerald |
| Furious Quara Mantassin | 1.680 | 1.350 | M:38-228 / Sp:≤80 [Haste] (71/308) | **6.4** | 177.3k | 526.8k | 552.8k | `0.32` | 503× small amethyst, 385× small emerald, 269× small ruby |
| Enraged Quara Mantassin | 2.040 | 1.700 | M:46-276 / Sp:≤80 [Haste] (85/356) | **6.6** | 170.4k | 901.9k | 925.9k | `0.43` | 920× small amethyst, 720× small emerald, 452× small ruby |
| Angry Tide Priest | 1.224 | 1.302 | M:0-60 / Sp:≤95 [ManaDrain,Heal,Dist(4),Summon×2] (36/155) | **6.0** | 102.8k | 160.5k | 206.0k | `0.16` | 22× energyring, 124× small sapphire, 3× wand of cosmic energy |
| Furious Tide Priest | 1.512 | 1.674 | M:0-76 / Sp:≤95 [ManaDrain,Heal,Dist(4),Summon×2] (39/171) | **6.2** | 102.8k | 481.5k | 513.9k | `0.34` | 559× small amethyst, 378× small emerald, 323× small sapphire |
| Enraged Tide Priest | 1.836 | 2.108 | M:0-92 / Sp:≤95 [ManaDrain,Heal,Dist(4),Summon×2] (42/187) | **6.4** | 102.4k | 807.6k | 831.0k | `0.46` | 897× small amethyst, 713× small emerald, 458× small sapphire |
| Angry Wyvern | 1.352 | 1.082 | M:45-180 / Sp:≤80 [AoE,Heal] (60/260) | **6.1** | 140.1k | 161.4k | 197.6k | `0.14` | 6× wand of Inferno, 42× small sapphire, 24× small emerald |
| Furious Wyvern | 1.670 | 1.390 | M:57-228 / Sp:≤80 [AoE,Heal] (75/308) | **6.4** | 139.7k | 477.7k | 519.9k | `0.30` | 426× small emerald, 516× small amethyst, 245× small ruby |
| Enraged Wyvern | 2.027 | 1.751 | M:69-276 / Sp:≤80 [AoE,Heal] (90/356) | **6.6** | 138.4k | 841.5k | 853.7k | `0.41` | 740× small emerald, 842× small amethyst, 12× gold nugget |
| Angry Nightstalker | 1.190 | 1.050 | M:45-165 / Sp:≤80 [Haste] (62/245) | **6.0** | 94.1k | 218.4k | 238.6k | `0.18` | 4× blue robe, 9× hollow orb, 1× boots of haste |
| Furious Nightstalker | 1.470 | 1.350 | M:57-209 / Sp:≤80 [Haste] (76/289) | **6.3** | 87.4k | 492.8k | 513.7k | `0.36` | 565× small amethyst, 446× small emerald, 238× small ruby |
| Enraged Nightstalker | 1.785 | 1.700 | M:69-253 / Sp:≤80 [Haste] (90/333) | **6.5** | 87.9k | 880.3k | 905.0k | `0.48` | 867× small amethyst, 659× small emerald, 475× small ruby |
| Angry Ice Monk | 1.105 | 1.092 | M:15-68 / Sp:≤95 [AoE,Heal,Dist(4),Summon×2] (46/163) | **5.9** | 77.1k | 112.1k | 131.3k | `0.16` | 99× small sapphire, 2× tempest rod, 9× lifering |
| Furious Ice Monk | 1.365 | 1.404 | M:19-86 / Sp:≤95 [AoE,Heal,Dist(4),Summon×2] (50/181) | **6.1** | 77.3k | 422.0k | 468.1k | `0.36` | 395× small emerald, 491× small amethyst, 269× small sapphire |
| Enraged Ice Monk | 1.657 | 1.768 | M:23-103 / Sp:≤95 [AoE,Heal,Dist(4),Summon×2] (54/198) | **6.3** | 76.6k | 747.7k | 793.8k | `0.50` | 719× small emerald, 859× small amethyst, 481× small ruby |
| Angry Quara Hydromancer | 2.035 | 1.840 | M:24-128 / Sp:≤55 [AoE,Heal] (44/183) | **6.1** | 165.4k | 318.9k | 392.7k | `0.20` | 9× wand of cosmic energy, 129× small emerald, 145× small amethyst |
| Furious Quara Hydromancer | 2.530 | 2.400 | M:31-164 / Sp:≤55 [AoE,Heal] (55/219) | **6.4** | 168.4k | 979.5k | 1.08M | `0.43` | 757× small emerald, 944× small amethyst, 14× gold nugget |
| Enraged Quara Hydromancer | 3.080 | 3.040 | M:38-200 / Sp:≤55 [AoE,Heal] (66/255) | **6.7** | 168.0k | 1.53M | 1.65M | `0.54` | 1250× small emerald, 1443× small amethyst, 23× gold nugget |
| Angry Court Mage | 1.105 | 1.092 | M:0-68 / Sp:≤120 [AoE,Heal,Dist(4)] (51/188) | **5.9** | 122.4k | 146.5k | 148.8k | `0.14` | 58× small amethyst, 2× violet gem, 18× small emerald |
| Furious Court Mage | 1.365 | 1.404 | M:0-86 / Sp:≤135 [AoE,Heal,Dist(4)] (58/221) | **6.1** | 121.5k | 465.4k | 469.1k | `0.35` | 538× small amethyst, 379× small emerald, 227× small ruby |
| Enraged Court Mage | 1.657 | 1.768 | M:0-103 / Sp:≤150 [AoE,Heal,Dist(4)] (65/253) | **6.3** | 123.5k | 777.8k | 780.8k | `0.48` | 907× small amethyst, 724× small emerald, 399× small ruby |
| Angry Vampire | 765 | 609 | M:0-240 / Sp:≤100 [AoE] (75/340) | **6.0** | 16.2k | 347.2k | 347.2k | `0.38` | 6× boots of haste, 4× vampire shield, 4× ice rapier |
| Furious Vampire | 945 | 783 | M:0-304 / Sp:≤100 [AoE] (91/404) | **6.2** | 16.1k | 592.1k | 592.1k | `0.70` | 429× small emerald, 487× small amethyst, 3× boots of haste |
| Enraged Vampire | 1.148 | 986 | M:0-368 / Sp:≤100 [AoE] (107/468) | **6.4** | 16.3k | 872.5k | 872.5k | `0.77` | 759× small emerald, 826× small amethyst, 431× small ruby |
| Angry Earth Elemental | 1.105 | 945 | M:38-120 / Sp:≤55 [AoE,Heal] (45/175) | **5.8** | 99.7k | 169.0k | 175.7k | `0.15` | 147× small emerald, 97× small amethyst, 3× knight legs |
| Furious Earth Elemental | 1.365 | 1.215 | M:48-152 / Sp:≤55 [AoE,Heal] (56/207) | **6.1** | 105.5k | 486.8k | 493.3k | `0.35` | 636× small amethyst, 475× small emerald, 219× small ruby |
| Enraged Earth Elemental | 1.657 | 1.530 | M:57-184 / Sp:≤55 [AoE,Heal] (66/239) | **6.3** | 98.3k | 787.9k | 794.3k | `0.49` | 919× small emerald, 933× small amethyst, 416× small ruby |
| Angry Mutated Rat | 935 | 945 | M:60-232 / Sp:≤10 [AoE,Heal] (74/242) | **5.9** | 157.6k | 187.4k | 212.2k | `0.24` | 9× stealthring, 55× small amethyst, 1× tower shield |
| Furious Mutated Rat | 1.155 | 1.215 | M:76-294 / Sp:≤10 [AoE,Heal] (94/304) | **6.2** | 165.3k | 535.4k | 562.3k | `0.47` | 452× small emerald, 482× small amethyst, 245× small ruby |
| Enraged Mutated Rat | 1.402 | 1.530 | M:92-356 / Sp:≤10 [AoE,Heal] (113/366) | **6.5** | 159.3k | 838.5k | 869.1k | `0.62` | 725× small emerald, 810× small amethyst, 450× small ruby |
| Angry Red Kongra | 935 | 714 | M:0-172 / Sp:≤64 [AoE,Haste] (47/236) | **5.8** | 60.0k | 130.1k | 130.1k | `0.13` | 114× steel helmet, 35× plate armor, 147× scale armor |
| Furious Red Kongra | 1.155 | 918 | M:0-218 / Sp:≤64 [AoE,Haste] (58/282) | **6.1** | 60.3k | 447.7k | 447.7k | `0.38` | 534× small amethyst, 391× small emerald, 247× small ruby |
| Enraged Red Kongra | 1.402 | 1.156 | M:0-264 / Sp:≤64 [AoE,Haste] (70/328) | **6.3** | 60.0k | 799.6k | 799.6k | `0.55` | 746× small emerald, 870× small amethyst, 11× gold nugget |
| Angry Water Elemental | 935 | 1.365 | M:45-150 / Sp:≤80 [AoE,Heal] (59/230) | **5.9** | 118.3k | 149.7k | 165.5k | `0.17` | 4× platinum amulet, 6× energyring, 28× small emerald |
| Furious Water Elemental | 1.155 | 1.755 | M:57-190 / Sp:≤80 [AoE,Heal] (72/270) | **6.1** | 111.7k | 466.3k | 482.8k | `0.42` | 449× small emerald, 549× small amethyst, 235× small ruby |
| Enraged Water Elemental | 1.402 | 2.210 | M:69-230 / Sp:≤80 [AoE,Heal] (85/310) | **6.3** | 110.1k | 836.9k | 863.9k | `0.58` | 735× small emerald, 907× small amethyst, 13× gold nugget |
| Angry Imperial Archer | 765 | 630 | M:15-75 / D:75-195 / Sp:≤88 [AoE,Dist(4)] (70/283) | **5.9** | 92.7k | 161.9k | 176.6k | `0.24` | 5× cordovan leggings, 52× small amethyst, 35× small emerald |
| Furious Imperial Archer | 945 | 810 | M:19-95 / D:95-247 / Sp:≤88 [AoE,Dist(4)] (87/335) | **6.1** | 92.3k | 548.5k | 562.6k | `0.53` | 12× cordovan leggings, 559× small amethyst, 426× small emerald |
| Enraged Imperial Archer | 1.148 | 1.020 | M:23-115 / D:115-299 / Sp:≤88 [AoE,Dist(4)] (104/387) | **6.4** | 93.5k | 862.6k | 876.3k | `0.72` | 760× small emerald, 847× small amethyst, 12× gold nugget |
| Angry Pirate Buccaneer | 722 | 525 | M:60-225 / D:45-150 / Sp:≤88 [AoE] (79/313) | **5.8** | 89.7k | 118.7k | 120.9k | `0.18` | 40× white pearl, 24× small emerald, 102× sabre |
| Furious Pirate Buccaneer | 892 | 675 | M:76-285 / D:57-190 / Sp:≤88 [AoE] (98/373) | **6.1** | 91.9k | 448.2k | 450.5k | `0.50` | 441× small emerald, 524× small amethyst, 271× small ruby |
| Enraged Pirate Buccaneer | 1.084 | 850 | M:92-345 / D:69-230 / Sp:≤88 [AoE] (117/433) | **6.3** | 91.1k | 788.9k | 791.0k | `0.72` | 845× small amethyst, 662× small emerald, 463× small ruby |
| Angry Drowned Sailor | 884 | 588 | M:38-128 / Sp:≤55 [Paralyze] (44/183) | **5.7** | 67.9k | 101.3k | 105.8k | `0.13` | 6× ancient shield, 24× black pearl, 37× white pearl |
| Furious Drowned Sailor | 1.092 | 756 | M:48-162 / Sp:≤55 [Paralyze] (56/217) | **6.0** | 67.9k | 434.7k | 448.9k | `0.40` | 558× small amethyst, 406× small emerald, 284× small ruby |
| Enraged Drowned Sailor | 1.326 | 952 | M:57-195 / Sp:≤55 [Paralyze] (66/250) | **6.2** | 68.1k | 761.0k | 765.5k | `0.57` | 737× small emerald, 845× small amethyst, 10× gold nugget |
| Angry Orc Leader | 765 | 567 | M:68-195 / D:57-111 (66/195) | **5.8** | 50.9k | 142.2k | 183.5k | `0.24` | 5× warrior helmet, 109× scimitar, 27× broad sword |
| Furious Orc Leader | 945 | 729 | M:86-247 / D:72-141 (83/247) | **6.1** | 51.0k | 455.4k | 501.0k | `0.52` | 435× small emerald, 532× small amethyst, 244× small ruby |
| Enraged Orc Leader | 1.148 | 918 | M:103-299 / D:87-170 (100/299) | **6.3** | 51.1k | 770.2k | 816.0k | `0.72` | 754× small emerald, 844× small amethyst, 446× small ruby |
| Angry Blue Elf Arcanist | 374 | 365 | D:15-105 / Sp:≤97 [Heal,Dist(5)] (59/202) | **5.7** | 34.0k | 43.0k | 66.4k | `0.19` | 25× life crystal, 17× crystal necklace, 104× bow |
| Furious Blue Elf Arcanist | 462 | 470 | D:19-133 / Sp:≤113 [Heal,Dist(5)] (70/246) | **6.0** | 33.8k | 344.8k | 368.1k | `0.84` | 513× small amethyst, 409× small emerald, 208× small ruby |
| Enraged Blue Elf Arcanist | 561 | 592 | D:23-161 / Sp:≤128 [Heal,Dist(5)] (80/289) | **6.2** | 34.0k | 683.0k | 706.9k | `1.28` | 702× small emerald, 800× small amethyst, 440× small ruby |
| Angry Zombie | 850 | 588 | M:30-135 / Sp:≤55 (46/190) | **5.6** | 92.0k | 136.7k | 141.9k | `0.16` | 52× steel helmet, 25× halberd, 36× small emerald |
| Furious Zombie | 1.050 | 756 | M:38-171 / Sp:≤55 (57/226) | **5.9** | 91.5k | 446.6k | 455.6k | `0.43` | 499× small emerald, 474× small amethyst, 228× small ruby |
| Enraged Zombie | 1.275 | 952 | M:46-207 / Sp:≤55 (68/262) | **6.1** | 90.9k | 744.4k | 751.9k | `0.61` | 663× small emerald, 818× small amethyst, 444× small ruby |
| Angry Quara Constrictor | 765 | 525 | M:30-150 / Sp:≤80 [AoE] (52/230) | **5.7** | 150.3k | 192.3k | 208.4k | `0.27` | 72× small amethyst, 46× brass armor, 66× white pearl |
| Furious Quara Constrictor | 945 | 675 | M:38-190 / Sp:≤80 [AoE] (64/270) | **5.9** | 148.0k | 492.6k | 508.3k | `0.55` | 514× small amethyst, 399× small emerald, 224× small ruby |
| Enraged Quara Constrictor | 1.148 | 850 | M:46-230 / Sp:≤80 [AoE] (76/310) | **6.1** | 147.3k | 881.8k | 901.5k | `0.74` | 731× small emerald, 897× small amethyst, 12× gold nugget |
| Angry Dark Monk | 349 | 276 | M:50-168 [Heal,Haste] (54/168) | **5.6** | 68.1k | 89.0k | 109.5k | `0.31` | 23× lifering, 27× mystic turban, 27× small amethyst |
| Furious Dark Monk | 439 | 348 | M:63-210 [Heal,Haste] (68/210) | **5.9** | 68.3k | 205.6k | 228.8k | `0.52` | 188× small amethyst, 137× small emerald, 88× small ruby |
| Enraged Dark Monk | 529 | 442 | M:76-252 [Heal,Haste] (82/252) | **6.1** | 68.3k | 305.9k | 336.9k | `0.66` | 358× small amethyst, 241× small emerald, 203× small ruby |
| Angry Cyclops Smith | 740 | 536 | M:38-135 / D:40-108 / Sp:≤55 (46/190) | **5.5** | 96.9k | 170.4k | 173.6k | `0.23` | 7× quarryguard armor, 51× battle axe, 75× battle shield |
| Furious Cyclops Smith | 914 | 688 | M:48-171 / D:51-137 / Sp:≤55 (58/226) | **5.8** | 100.9k | 496.8k | 499.2k | `0.53` | 492× small emerald, 574× small amethyst, 247× small ruby |
| Enraged Cyclops Smith | 1.109 | 867 | M:57-207 / D:62-166 / Sp:≤55 (69/262) | **6.0** | 99.8k | 792.1k | 794.5k | `0.74` | 706× small emerald, 840× small amethyst, 477× small ruby |
| Angry Ice Golem | 654 | 620 | M:30-165 / Sp:≤60 [AoE] (52/225) | **5.6** | 86.6k | 114.2k | 117.4k | `0.19` | 48× small sapphire, 28× small amethyst, 20× small emerald |
| Furious Ice Golem | 808 | 796 | M:38-209 / Sp:≤60 [AoE] (65/269) | **5.8** | 87.6k | 460.5k | 463.3k | `0.55` | 531× small amethyst, 416× small emerald, 250× small ruby |
| Enraged Ice Golem | 982 | 1.003 | M:46-253 / Sp:≤60 [AoE] (78/313) | **6.1** | 84.9k | 746.2k | 748.2k | `0.79` | 694× small emerald, 802× small amethyst, 476× small ruby |
| Angry Dwarf Geomancer | 646 | 514 | M:40-81 / D:62-180 [Heal,ManaDrain,Dist(4)] (24/180) | **5.6** | 77.2k | 127.9k | 142.2k | `0.21` | 105× small sapphire, 47× clerical mace, 25× dwarfenring |
| Furious Dwarf Geomancer | 798 | 662 | M:51-103 / D:78-228 [Heal,ManaDrain,Dist(4)] (31/228) | **5.8** | 77.1k | 423.4k | 442.8k | `0.57` | 519× small amethyst, 412× small emerald, 248× small ruby |
| Enraged Dwarf Geomancer | 969 | 833 | M:62-124 / D:94-276 [Heal,ManaDrain,Dist(4)] (37/276) | **6.1** | 76.9k | 741.7k | 761.8k | `0.81` | 797× small amethyst, 632× small emerald, 464× small ruby |
| Angry Mammoth | 544 | 336 | M:30-150 / Sp:≤80 [Haste] (50/230) | **5.5** | 60.7k | 75.1k | 87.5k | `0.17` | 124× elephant tusk, 4× tusk shield, 21× small emerald |
| Furious Mammoth | 672 | 432 | M:38-190 / Sp:≤80 [Haste] (62/270) | **5.8** | 61.6k | 394.7k | 406.7k | `0.61` | 514× small amethyst, 411× small emerald, 240× small ruby |
| Enraged Mammoth | 816 | 544 | M:46-230 / Sp:≤80 [Haste] (74/310) | **6.0** | 61.1k | 706.2k | 714.8k | `0.90` | 908× small amethyst, 709× small emerald, 439× small ruby |
| Angry Lizard Templar | 636 | 266 | M:0-140 [Heal] (35/140) | **5.3** | 34.0k | 100.3k | 140.3k | `0.20` | 74× hatchet lizard, 44× two-handed sword, 55× small emerald |
| Furious Lizard Templar | 800 | 336 | M:0-175 [Heal] (44/175) | **5.6** | 34.1k | 213.8k | 256.1k | `0.30` | 161× small emerald, 188× small amethyst, 72× hatchet lizard |
| Enraged Lizard Templar | 964 | 427 | M:0-210 [Heal] (52/210) | **5.8** | 34.1k | 305.1k | 349.6k | `0.37` | 308× small emerald, 363× small amethyst, 170× small ruby |
| Angry Dragon Hatchling | 646 | 483 | M:22-82 / Sp:≤90 [AoE,Heal] (35/172) | **5.4** | 76.2k | 89.0k | 89.0k | `0.13` | 29× small emerald, 28× small amethyst |
| Furious Dragon Hatchling | 798 | 621 | M:28-104 / Sp:≤90 [AoE,Heal] (42/194) | **5.6** | 74.5k | 403.0k | 403.0k | `0.51` | 535× small amethyst, 411× small emerald, 236× small ruby |
| Enraged Dragon Hatchling | 969 | 782 | M:34-126 / Sp:≤90 [AoE,Heal] (49/216) | **5.8** | 75.6k | 715.9k | 715.9k | `0.76` | 820× small amethyst, 631× small emerald, 564× small ruby |
| Angry Crypt Shambler | 561 | 410 | M:62-195 (64/195) | **5.5** | 68.3k | 103.3k | 110.9k | `0.20` | 20× two-handed sword, 39× black pearl, 25× small emerald |
| Furious Crypt Shambler | 693 | 526 | M:78-247 (81/247) | **5.8** | 67.9k | 447.3k | 454.9k | `0.62` | 581× small amethyst, 440× small emerald, 251× small ruby |
| Enraged Crypt Shambler | 841 | 663 | M:94-299 (98/299) | **6.1** | 68.0k | 725.8k | 733.1k | `0.90` | 866× small amethyst, 673× small emerald, 417× small ruby |
| Angry Pirate Cutthroat | 552 | 368 | M:45-165 / D:30-90 / Sp:≤80 (57/245) | **5.5** | 72.7k | 95.8k | 96.8k | `0.18` | 36× steel helmet, 105× sabre, 23× small amethyst |
| Furious Pirate Cutthroat | 682 | 473 | M:57-209 / D:38-114 / Sp:≤80 (71/289) | **5.7** | 71.7k | 382.5k | 383.6k | `0.61` | 395× small emerald, 450× small amethyst, 237× small ruby |
| Enraged Pirate Cutthroat | 829 | 595 | M:69-253 / D:46-138 / Sp:≤80 (85/333) | **6.0** | 70.7k | 716.4k | 717.4k | `0.90` | 730× small emerald, 797× small amethyst, 498× small ruby |
| Angry Barbarian Bloodwalker | 518 | 410 | M:30-165 / Sp:≤64 [Haste,AoE] (53/229) | **5.5** | 62.3k | 89.8k | 91.8k | `0.18` | 35× small amethyst, 31× battle axe, 14× halberd |
| Furious Barbarian Bloodwalker | 640 | 526 | M:38-209 / Sp:≤64 [Haste,AoE] (66/273) | **5.7** | 63.3k | 412.2k | 414.6k | `0.64` | 433× small emerald, 529× small amethyst, 236× small ruby |
| Enraged Barbarian Bloodwalker | 778 | 663 | M:46-253 / Sp:≤64 [Haste,AoE] (79/317) | **6.0** | 60.1k | 780.8k | 782.6k | `0.95` | 860× small amethyst, 657× small emerald, 14× gold nugget |
| Angry Orc Berserker | 357 | 410 | M:114-285 [Haste] (100/285) | **5.5** | 26.0k | 94.0k | 104.0k | `0.30` | 49× small emerald, 57× small amethyst, 20× swordring |
| Furious Orc Berserker | 441 | 526 | M:144-361 [Haste] (126/361) | **5.8** | 26.0k | 378.2k | 391.7k | `0.91` | 515× small amethyst, 368× small emerald, 232× small ruby |
| Enraged Orc Berserker | 536 | 663 | M:175-437 [Haste] (153/437) | **6.1** | 26.1k | 691.1k | 780.6k | `1.66` | 872× small amethyst, 642× small emerald, 461× small ruby |
| Angry Gargoyle | 425 | 315 | M:0-210 / D:45-90 (52/210) | **5.4** | 43.1k | 62.0k | 62.0k | `0.15` | 14× dark armor, 35× small amethyst, 14× small emerald |
| Furious Gargoyle | 525 | 405 | M:0-266 / D:57-114 (66/266) | **5.7** | 43.0k | 375.2k | 375.2k | `0.73` | 514× small amethyst, 397× small emerald, 217× small ruby |
| Enraged Gargoyle | 638 | 510 | M:0-322 / D:69-138 (80/322) | **5.9** | 43.0k | 702.1k | 702.1k | `1.12` | 681× small emerald, 837× small amethyst, 477× small ruby |
| Angry Blood Crab | 493 | 336 | M:22-105 / Sp:≤80 (37/185) | **5.2** | 30.9k | 50.2k | 50.2k | `0.10` | 33× small amethyst, 25× small emerald, 27× brass legs |
| Furious Blood Crab | 609 | 432 | M:28-133 / Sp:≤80 (45/213) | **5.4** | 30.4k | 379.6k | 379.6k | `0.60` | 442× small emerald, 542× small amethyst, 254× small ruby |
| Enraged Blood Crab | 740 | 544 | M:34-161 / Sp:≤80 (54/241) | **5.6** | 30.6k | 694.8k | 694.8k | `0.94` | 818× small amethyst, 654× small emerald, 451× small ruby |
| Angry Dwarf Guard | 416 | 388 | M:72-180 (63/180) | **5.3** | 71.5k | 153.3k | 155.8k | `0.39` | 69× double axe, 175× battlehammer, 158× scale armor |
| Furious Dwarf Guard | 514 | 500 | M:91-228 (80/228) | **5.6** | 72.3k | 462.4k | 465.9k | `0.93` | 544× small amethyst, 399× small emerald, 210× small ruby |
| Enraged Dwarf Guard | 625 | 629 | M:110-276 (96/276) | **5.9** | 71.6k | 804.4k | 809.4k | `1.54` | 722× small emerald, 884× small amethyst, 453× small ruby |
| Angry Minotaur Mage | 264 | 315 | M:0-30 / Sp:≤100 [AoE,Dist(5),Summon×5] (53/130) | **5.1** | 33.8k | 62.5k | 62.8k | `0.23` | 46× brass armor, 34× small emerald, 26× small amethyst |
| Furious Minotaur Mage | 326 | 405 | M:0-38 / Sp:≤100 [AoE,Dist(5),Summon×5] (55/138) | **5.2** | 33.8k | 372.7k | 373.0k | `1.17` | 497× small amethyst, 391× small emerald, 244× small ruby |
| Enraged Minotaur Mage | 395 | 510 | M:0-46 / Sp:≤100 [AoE,Dist(5),Summon×5] (56/146) | **5.4** | 33.9k | 687.4k | 688.0k | `1.81` | 669× small emerald, 821× small amethyst, 411× small ruby |
| Angry Frost Giant | 459 | 315 | M:22-135 / D:15-90 / Sp:≤44 [AoE] (42/179) | **5.1** | 55.2k | 74.3k | 80.1k | `0.17` | 38× small amethyst, 25× small emerald, 30× viking shield |
| Furious Frost Giant | 567 | 405 | M:28-171 / D:19-114 / Sp:≤44 [AoE] (52/215) | **5.4** | 54.5k | 410.7k | 415.8k | `0.69` | 481× small emerald, 538× small amethyst, 235× small ruby |
| Enraged Frost Giant | 688 | 510 | M:34-207 / D:23-138 / Sp:≤44 [AoE] (63/251) | **5.6** | 53.9k | 750.3k | 757.0k | `1.05` | 703× small emerald, 872× small amethyst, 11× gold nugget |
| Angry Mutated Human | 408 | 315 | M:30-135 / Sp:≤50 [AoE] (45/185) | **5.1** | 91.2k | 109.6k | 109.6k | `0.27` | 29× small emerald, 28× small amethyst, 51× sword |
| Furious Mutated Human | 504 | 405 | M:38-171 / Sp:≤50 [AoE] (56/221) | **5.4** | 91.0k | 413.0k | 413.0k | `0.84` | 515× small amethyst, 404× small emerald, 256× small ruby |
| Enraged Mutated Human | 612 | 510 | M:46-207 / Sp:≤50 [AoE] (67/257) | **5.6** | 91.8k | 699.5k | 699.5k | `1.23` | 921× small amethyst, 641× small emerald, 432× small ruby |
| Angry Frost Giantess | 468 | 315 | M:15-105 / D:30-135 / Sp:≤44 [AoE] (33/179) | **5.1** | 54.8k | 67.7k | 70.8k | `0.15` | 23× small emerald, 27× small amethyst, 21× viking shield |
| Furious Frost Giantess | 578 | 405 | M:19-133 / D:38-171 / Sp:≤44 [AoE] (41/215) | **5.3** | 52.0k | 378.9k | 383.7k | `0.67` | 539× small amethyst, 418× small emerald, 258× small ruby |
| Enraged Frost Giantess | 701 | 510 | M:23-161 / D:46-207 / Sp:≤44 [AoE] (49/251) | **5.6** | 55.0k | 718.3k | 722.7k | `1.02` | 684× small emerald, 780× small amethyst, 452× small ruby |
| Angry Stone Golem | 459 | 336 | M:24-120 (36/120) | **5.1** | 34.0k | 60.4k | 62.2k | `0.14` | 100× scale armor, 16× granite mace, 19× small emerald |
| Furious Stone Golem | 567 | 432 | M:30-152 (46/152) | **5.4** | 34.0k | 388.2k | 390.1k | `0.68` | 533× small amethyst, 416× small emerald, 250× small ruby |
| Enraged Stone Golem | 688 | 544 | M:37-184 (55/184) | **5.6** | 33.8k | 686.9k | 688.5k | `1.04` | 902× small amethyst, 691× small emerald, 421× small ruby |
| Angry Mummy | 408 | 315 | M:52-138 (48/138) | **5.1** | 84.8k | 117.0k | 148.8k | `0.38` | 76× black pearl, 70× silver brooch, 8× timering |
| Furious Mummy | 504 | 405 | M:66-175 (60/175) | **5.4** | 85.0k | 439.5k | 481.4k | `0.95` | 547× small amethyst, 436× small emerald, 230× small ruby |
| Enraged Mummy | 612 | 510 | M:80-212 (73/212) | **5.7** | 84.5k | 733.0k | 786.9k | `1.33` | 861× small amethyst, 643× small emerald, 442× small ruby |
| Angry Thornback Tortoise | 510 | 315 | M:22-82 / Sp:≤35 [AoE] (28/117) | **4.9** | 74.8k | 91.1k | 93.0k | `0.18` | 38× small amethyst, 15× small emerald, 21× white pearl |
| Furious Thornback Tortoise | 630 | 405 | M:28-104 / Sp:≤35 [AoE] (35/139) | **5.2** | 73.7k | 407.9k | 409.5k | `0.65` | 543× small amethyst, 406× small emerald, 238× small ruby |
| Enraged Thornback Tortoise | 765 | 510 | M:34-126 / Sp:≤35 [AoE] (42/161) | **5.5** | 73.0k | 750.6k | 752.5k | `0.97` | 666× small emerald, 757× small amethyst, 13× gold nugget |
| Angry Cyclops | 442 | 315 | M:38-120 (40/120) | **5.0** | 46.9k | 104.9k | 114.9k | `0.26` | 338× short sword, 46× halberd, 20× clubring |
| Furious Cyclops | 546 | 405 | M:48-152 (50/152) | **5.3** | 46.8k | 416.9k | 425.9k | `0.80` | 418× small emerald, 478× small amethyst, 238× small ruby |
| Enraged Cyclops | 663 | 510 | M:57-184 (60/184) | **5.5** | 46.3k | 767.7k | 774.7k | `1.18` | 868× small amethyst, 672× small emerald, 451× small ruby |
| Angry Cyclops Drone | 552 | 420 | M:22-90 / D:27-72 (28/90) | **4.9** | 40.8k | 58.0k | 59.6k | `0.11` | 27× small amethyst, 78× short sword, 17× small emerald |
| Furious Cyclops Drone | 682 | 540 | M:28-114 / D:34-91 (36/114) | **5.2** | 41.6k | 389.5k | 391.3k | `0.56` | 572× small amethyst, 429× small emerald, 248× small ruby |
| Enraged Cyclops Drone | 829 | 680 | M:34-138 / D:41-110 (43/138) | **5.4** | 41.1k | 729.3k | 730.0k | `0.86` | 712× small emerald, 870× small amethyst, 11× gold nugget |
| Angry Scarab | 496 | 228 | M:29-84 [Haste] (23/84) | **4.8** | 69.8k | 83.1k | 87.5k | `0.18` | 23× small emerald, 39× scarab coin, 18× small amethyst |
| Furious Scarab | 624 | 288 | M:37-105 [Haste] (28/105) | **5.1** | 67.0k | 185.0k | 189.9k | `0.31` | 240× small amethyst, 151× small emerald, 60× small ruby |
| Enraged Scarab | 752 | 366 | M:44-126 [Haste] (34/126) | **5.4** | 67.4k | 326.6k | 332.2k | `0.43` | 404× small amethyst, 299× small emerald, 207× small ruby |
| Angry Pirate Marauder | 326 | 238 | M:28-112 / D:14-56 / Sp:≤28 [AoE] (36/140) | **4.8** | 55.4k | 67.6k | 70.8k | `0.21` | 83× sabre, 19× small amethyst, 55× plate shield |
| Furious Pirate Marauder | 410 | 300 | M:35-140 / D:18-70 / Sp:≤28 [AoE] (45/168) | **5.1** | 54.2k | 177.8k | 180.1k | `0.43` | 210× small amethyst, 113× small emerald, 97× small ruby |
| Enraged Pirate Marauder | 494 | 381 | M:42-168 / D:21-84 / Sp:≤28 [AoE] (54/196) | **5.3** | 54.6k | 267.7k | 270.0k | `0.58` | 365× small amethyst, 242× small emerald, 155× small ruby |
| Angry Minotaur Guard | 314 | 336 | M:60-150 (52/150) | **5.0** | 34.0k | 76.3k | 76.3k | `0.25` | 98× battle shield, 30× brass armor, 35× small amethyst |
| Furious Minotaur Guard | 388 | 432 | M:76-190 (66/190) | **5.2** | 34.2k | 400.8k | 400.8k | `1.03` | 425× small emerald, 503× small amethyst, 260× small ruby |
| Enraged Minotaur Guard | 472 | 544 | M:92-230 (80/230) | **5.5** | 33.9k | 767.8k | 767.8k | `1.55` | 769× small emerald, 853× small amethyst, 457× small ruby |
| Angry Hunter | 255 | 315 | D:56-126 [Dist(5)] (55/126) | **4.8** | 34.0k | 76.5k | 86.9k | `0.33` | 105× brass armor, 33× small amethyst, 26× small emerald |
| Furious Hunter | 315 | 405 | D:70-160 [Dist(5)] (69/160) | **5.1** | 33.9k | 415.4k | 429.0k | `1.32` | 448× small emerald, 529× small amethyst, 310× small ruby |
| Enraged Hunter | 382 | 510 | D:85-193 [Dist(5)] (83/193) | **5.4** | 34.2k | 709.0k | 722.1k | `1.96` | 862× small amethyst, 663× small emerald, 471× small ruby |
| Angry Orc Shaman | 178 | 209 | M:0-21 / Sp:≤50 [Heal,Dist(5),Summon×5] (15/71) | **4.5** | 33.8k | 56.4k | 58.6k | `0.33` | 46× small amethyst, 26× small emerald, 14× small sapphire |
| Furious Orc Shaman | 224 | 264 | M:0-26 / Sp:≤50 [Heal,Dist(5),Summon×5] (16/76) | **4.7** | 34.2k | 188.9k | 195.2k | `0.88` | 215× small emerald, 246× small amethyst, 107× small ruby |
| Enraged Orc Shaman | 270 | 336 | M:0-32 / Sp:≤50 [Heal,Dist(5),Summon×5] (18/82) | **4.9** | 33.8k | 255.4k | 260.4k | `0.98` | 344× small amethyst, 273× small emerald, 204× small ruby |
| Angry Minotaur Archer | 155 | 124 | M:0-7 / D:56-140 [Dist(5)] (53/140) | **4.5** | 23.5k | 55.4k | 74.6k | `0.50` | 5181× bolt, 30× brass armor, 25× small amethyst |
| Furious Minotaur Archer | 195 | 156 | M:0-9 / D:70-175 [Dist(5)] (66/175) | **4.8** | 23.5k | 166.6k | 188.3k | `0.97` | 139× small emerald, 156× small amethyst, 91× small ruby |
| Enraged Minotaur Archer | 235 | 198 | M:0-10 / D:84-210 [Dist(5)] (79/210) | **5.1** | 23.5k | 290.0k | 310.5k | `1.29` | 371× small amethyst, 276× small emerald, 208× small ruby |
| Angry Stone Troll | 248 | 171 | M:28-77 / D:17-42 (26/77) | **4.4** | 60.2k | 67.8k | 70.6k | `0.29` | 16× small emerald, 18× small amethyst, 755× small stone |
| Furious Stone Troll | 312 | 216 | M:35-96 / D:21-52 (33/96) | **4.7** | 60.0k | 170.0k | 174.0k | `0.57` | 167× small amethyst, 121× small emerald, 89× small ruby |
| Enraged Stone Troll | 376 | 274 | M:42-116 / D:25-63 (40/116) | **5.0** | 60.1k | 289.6k | 292.8k | `0.77` | 278× small emerald, 346× small amethyst, 213× small ruby |
| Angry Barbarian Brutetamer | 225 | 171 | M:7-42 / Sp:≤35 [AoE,Heal,Dist(3),Summon×2] (15/77) | **4.3** | 44.1k | 53.0k | 55.5k | `0.26` | 23× small amethyst, 2× ring of healing, 9× small emerald |
| Furious Barbarian Brutetamer | 283 | 216 | M:9-52 / Sp:≤35 [AoE,Heal,Dist(3),Summon×2] (18/87) | **4.6** | 45.5k | 165.0k | 167.5k | `0.58` | 181× small amethyst, 134× small emerald, 89× small ruby |
| Enraged Barbarian Brutetamer | 341 | 274 | M:10-63 / Sp:≤35 [AoE,Heal,Dist(3),Summon×2] (21/98) | **4.8** | 46.1k | 263.2k | 267.0k | `0.81` | 364× small amethyst, 241× small emerald, 186× small ruby |
| Angry Barbarian Skullhunter | 209 | 162 | M:21-77 / Sp:≤28 [AoE,Haste] (26/105) | **4.4** | 38.0k | 47.0k | 49.0k | `0.24` | 21× small amethyst, 33× viking helmet, 7× small emerald |
| Furious Barbarian Skullhunter | 263 | 204 | M:26-96 / Sp:≤28 [AoE,Haste] (32/124) | **4.7** | 37.7k | 145.2k | 146.7k | `0.60` | 171× small amethyst, 113× small emerald, 96× small ruby |
| Enraged Barbarian Skullhunter | 317 | 259 | M:32-116 / Sp:≤28 [AoE,Haste] (38/144) | **4.9** | 37.9k | 263.9k | 265.4k | `0.84` | 267× small emerald, 324× small amethyst, 207× small ruby |
| Angry Valkyrie | 294 | 162 | M:0-70 / D:14-35 (20/70) | **4.3** | 34.1k | 58.6k | 71.7k | `0.24` | 24× crystal necklace, 19× double axe, 20× small emerald |
| Furious Valkyrie | 370 | 204 | M:0-88 / D:18-44 (25/88) | **4.6** | 33.8k | 234.5k | 246.9k | `0.67` | 289× small amethyst, 200× small emerald, 169× small ruby |
| Enraged Valkyrie | 446 | 259 | M:0-105 / D:21-52 (30/105) | **4.8** | 34.2k | 297.3k | 310.7k | `0.70` | 277× small emerald, 342× small amethyst, 240× small ruby |
| Angry Tortoise | 287 | 171 | M:14-56 / Sp:≤20 (18/76) | **4.3** | 30.7k | 38.4k | 40.0k | `0.14` | 23× small amethyst, 8× small emerald, 33× plate shield |
| Furious Tortoise | 361 | 216 | M:18-70 / Sp:≤20 (23/90) | **4.6** | 29.2k | 145.3k | 146.7k | `0.40` | 198× small amethyst, 126× small emerald, 84× small ruby |
| Enraged Tortoise | 435 | 274 | M:21-84 / Sp:≤20 (27/104) | **4.8** | 30.4k | 241.9k | 243.0k | `0.59` | 278× small emerald, 316× small amethyst, 182× small ruby |
| Angry Barbarian Headsplitter | 155 | 162 | M:14-70 / D:14-63 / Sp:≤28 [AoE,Haste] (22/98) | **4.1** | 37.4k | 47.4k | 48.8k | `0.32` | 19× small amethyst, 15× small emerald, 19× scale armor |
| Furious Barbarian Headsplitter | 195 | 204 | M:18-88 / D:18-79 / Sp:≤28 [AoE,Haste] (28/116) | **4.4** | 38.0k | 151.9k | 153.5k | `0.80` | 186× small amethyst, 130× small emerald, 86× small ruby |
| Enraged Barbarian Headsplitter | 235 | 259 | M:21-105 / D:21-94 / Sp:≤28 [AoE,Haste] (33/133) | **4.6** | 38.4k | 259.3k | 260.6k | `1.13` | 266× small emerald, 327× small amethyst, 186× small ruby |
| Angry Orc Warrior | 194 | 95 | M:0-84 (17/84) | **4.1** | 28.1k | 42.0k | 43.5k | `0.22` | 26× small amethyst, 14× small emerald, 57× sabre |
| Furious Orc Warrior | 244 | 120 | M:0-105 (21/105) | **4.4** | 27.9k | 187.3k | 188.7k | `0.80` | 272× small amethyst, 161× small emerald, 143× small ruby |
| Enraged Orc Warrior | 294 | 152 | M:0-126 (25/126) | **4.6** | 27.9k | 250.5k | 252.0k | `0.89` | 344× small amethyst, 242× small emerald, 197× small ruby |
| Angry Ghoul | 155 | 162 | M:0-70 [Heal] (14/70) | **4.0** | 51.0k | 69.2k | 88.4k | `0.60` | 21× lifering, 101× scale armor, 58× viking helmet |
| Furious Ghoul | 195 | 204 | M:0-88 [Heal] (18/88) | **4.3** | 50.7k | 219.5k | 246.7k | `1.29` | 251× small amethyst, 191× small emerald, 123× small ruby |
| Enraged Ghoul | 235 | 259 | M:0-105 [Heal] (21/105) | **4.6** | 51.1k | 299.9k | 327.5k | `1.37` | 314× small emerald, 360× small amethyst, 208× small ruby |
| Angry Dwarf Soldier | 209 | 133 | M:0-56 / D:10-39 (14/56) | **3.9** | 26.1k | 52.7k | 81.1k | `0.41` | 98× crossbow, 189× chain armor, 17× dwarfenring |
| Furious Dwarf Soldier | 263 | 168 | M:0-70 / D:12-49 (18/70) | **4.2** | 25.9k | 218.1k | 252.2k | `0.94` | 278× small amethyst, 214× small emerald, 121× small ruby |
| Enraged Dwarf Soldier | 317 | 214 | M:0-84 / D:15-59 (21/84) | **4.5** | 26.0k | 278.1k | 320.3k | `1.00` | 275× small emerald, 336× small amethyst, 199× small ruby |
| Angry Amazon | 170 | 114 | D:24-62 [Dist(3)] (13/62) | **3.8** | 35.8k | 56.2k | 71.0k | `0.41` | 37× crystal necklace, 267× sabre, 19× small amethyst |
| Furious Amazon | 214 | 144 | D:30-77 [Dist(3)] (16/77) | **4.1** | 36.1k | 216.0k | 295.6k | `1.54` | 2× crystal arrow, 289× small amethyst, 174× small emerald |
| Enraged Amazon | 258 | 183 | D:36-92 [Dist(3)] (19/92) | **4.4** | 35.9k | 406.5k | 426.9k | `1.77` | 12× gold nugget, 350× small amethyst, 277× small ruby |
| Angry Imperial Squire | 138 | 79 | M:6-36 / Sp:≤20 (11/56) | **3.5** | 27.5k | 44.0k | 44.0k | `0.35` | 1× marcher leggings, 59× sword, 9× small amethyst |
| Furious Imperial Squire | 171 | 99 | M:8-45 / Sp:≤20 (14/65) | **3.8** | 27.2k | 109.9k | 109.9k | `0.63` | 135× small amethyst, 2× marcher leggings, 75× small emerald |
| Enraged Imperial Squire | 209 | 126 | M:10-53 / Sp:≤20 (17/73) | **4.0** | 27.2k | 170.4k | 170.4k | `0.78` | 233× small amethyst, 172× small emerald, 84× small ruby |
| Angry Chakoya Windcaller | 122 | 84 | M:0-26 / Sp:≤35 [AoE,Dist(3)] (11/61) | **3.5** | 21.4k | 27.9k | 27.9k | `0.23` | 15× small amethyst, 8× small sapphire, 6× small emerald |
| Furious Chakoya Windcaller | 151 | 106 | M:0-32 / Sp:≤35 [AoE,Dist(3)] (12/67) | **3.8** | 20.1k | 87.6k | 87.6k | `0.58` | 124× small amethyst, 81× small emerald, 52× small ruby |
| Enraged Chakoya Windcaller | 185 | 134 | M:0-38 / Sp:≤35 [AoE,Dist(3)] (14/73) | **4.0** | 20.6k | 140.7k | 140.7k | `0.78` | 234× small amethyst, 159× small emerald, 77× small ruby |
| Angry Minotaur | 155 | 95 | M:0-56 (11/56) | **3.6** | 49.6k | 68.1k | 74.7k | `0.47` | 103× chain armor, 102× plate shield, 18× small emerald |
| Furious Minotaur | 195 | 120 | M:0-70 (14/70) | **3.9** | 49.4k | 223.4k | 230.4k | `1.15` | 291× small amethyst, 199× small emerald, 141× small ruby |
| Enraged Minotaur | 235 | 152 | M:0-84 (17/84) | **4.2** | 49.9k | 283.6k | 290.9k | `1.23` | 370× small amethyst, 266× small emerald, 198× small ruby |
| Angry River Troll | 123 | 74 | M:10-42 / D:10-23 (13/42) | **3.5** | 42.9k | 48.3k | 49.6k | `0.39` | 17× small amethyst, 8× small emerald, 250× spear |
| Furious River Troll | 153 | 92 | M:13-51 / D:13-29 (16/51) | **3.8** | 43.0k | 106.3k | 107.7k | `0.70` | 124× small amethyst, 85× small emerald, 38× small ruby |
| Enraged River Troll | 187 | 118 | M:15-61 / D:15-34 (19/61) | **4.0** | 43.1k | 168.0k | 169.3k | `0.87` | 298× small amethyst, 138× small emerald, 75× small ruby |
| Angry Chakoya Toolshaper | 116 | 70 | M:6-39 / D:6-32 / Sp:≤20 (12/59) | **3.5** | 18.0k | 20.8k | 20.8k | `0.20` | 8× small amethyst, 4× small emerald, 24× hatchet |
| Furious Chakoya Toolshaper | 144 | 88 | M:8-48 / D:8-40 / Sp:≤20 (15/68) | **3.7** | 18.6k | 80.9k | 80.9k | `0.57` | 111× small amethyst, 75× small emerald, 59× small ruby |
| Enraged Chakoya Toolshaper | 176 | 112 | M:10-57 / D:10-48 / Sp:≤20 (18/77) | **4.0** | 20.0k | 135.9k | 135.9k | `0.78` | 247× small amethyst, 151× small emerald, 73× small ruby |
| Angry Chakoya Tribewarden | 99 | 70 | M:6-46 / Sp:≤20 (14/66) | **3.5** | 15.4k | 19.6k | 19.6k | `0.20` | 11× small amethyst, 6× small emerald, 51× mace |
| Furious Chakoya Tribewarden | 122 | 88 | M:8-56 / Sp:≤20 (17/76) | **3.7** | 15.2k | 80.0k | 80.0k | `0.65` | 120× small amethyst, 87× small emerald, 50× small ruby |
| Enraged Chakoya Tribewarden | 150 | 112 | M:10-66 / Sp:≤20 (20/86) | **3.9** | 16.1k | 139.9k | 139.9k | `0.90` | 242× small amethyst, 171× small emerald, 78× small ruby |
| Angry Dwarf | 130 | 79 | M:0-39 (10/39) | **3.4** | 26.0k | 30.7k | 36.2k | `0.31` | 11× dwarfenring, 12× small amethyst, 6× small emerald |
| Furious Dwarf | 162 | 99 | M:0-48 (12/48) | **3.6** | 26.0k | 102.1k | 111.6k | `0.70` | 162× small amethyst, 96× small emerald, 50× small ruby |
| Enraged Dwarf | 198 | 126 | M:0-57 (14/57) | **3.9** | 26.1k | 138.8k | 153.3k | `0.81` | 214× small amethyst, 153× small emerald, 71× small ruby |
| Angry Rotworm | 94 | 70 | M:0-48 (10/48) | **3.2** | 34.5k | 42.6k | 42.6k | `0.46` | 97× sword, 6× small emerald, 7× small amethyst |
| Furious Rotworm | 117 | 88 | M:0-59 (12/59) | **3.5** | 34.2k | 105.1k | 105.1k | `0.88` | 116× small amethyst, 78× small emerald, 59× small ruby |
| Enraged Rotworm | 143 | 112 | M:0-70 (14/70) | **3.7** | 34.2k | 150.9k | 150.9k | `1.11` | 221× small amethyst, 154× small emerald, 76× small ruby |
| Angry Skeleton | 72 | 61 | M:0-46 (9/46) | **3.1** | 15.6k | 24.8k | 27.4k | `0.36` | 13× small emerald, 44× viking helmet, 11× small amethyst |
| Furious Skeleton | 90 | 77 | M:0-56 (11/56) | **3.4** | 15.6k | 92.4k | 97.5k | `1.10` | 171× small amethyst, 84× small emerald, 48× small ruby |
| Enraged Skeleton | 110 | 98 | M:0-66 (13/66) | **3.6** | 15.3k | 139.7k | 144.0k | `1.31` | 233× small amethyst, 164× small emerald, 82× small ruby |
| Angry Orc | 102 | 44 | M:0-32 (8/32) | **3.0** | 17.1k | 32.9k | 32.9k | `0.31` | 36× small amethyst, 107× sabre, 7× small ruby |
| Furious Orc | 126 | 55 | M:0-40 (10/40) | **3.3** | 17.1k | 91.8k | 91.8k | `0.77` | 166× small amethyst, 84× small emerald, 51× small ruby |
| Enraged Orc | 154 | 70 | M:0-48 (12/48) | **3.6** | 17.0k | 144.5k | 144.5k | `0.92` | 271× small amethyst, 155× small emerald, 70× small ruby |
| Angry Troll | 72 | 35 | M:0-17 (3/17) | **2.3** | 19.0k | 22.7k | 26.2k | `0.38` | 11× small amethyst, 321× spear, 30× bronze amulet |
| Furious Troll | 90 | 44 | M:0-21 (4/21) | **2.6** | 19.0k | 99.4k | 104.0k | `1.09` | 197× small amethyst, 74× small emerald, 65× small ruby |
| Enraged Troll | 110 | 56 | M:0-25 (5/25) | **2.8** | 19.0k | 125.4k | 130.0k | `1.30` | 233× small amethyst, 140× small emerald, 58× small ruby |

---

## Apéndice A — Precios de referencia utilizados

### A.1 Precios exactos de NPC (incluidos en `NPC Líq. 1k`)
- **Monedas**: Gold Coin (`2148`) = 1 gp, Platinum Coin (`2152`) = 100 gp, Crystal Coin (`2160`) = 10.000 gp.
- **Mad (`data/npc/scripts/loot.lua`)**: MPA 100k, MMS 80k, Golden Legs 80k, DSM 40k, Demon Shield 40k, Royal Helmet 30k, Steel Boots 30k, BOH 30k, Golden Armor 20k, Giant Sword 17k, Vampire Shield 15k, Crown Armor/Legs 12k, Blue Robe 10k, Fire Axe 10k, Dragon Lance 10k, Medusa Shield 9k, Crown/Tower Shield 8k, Bright Sword 7k, Crusader Helmet / Skull Staff 6k, Warrior Helmet / Ice Rapier 5k, Fire Sword / Dragon Shield / Amazon Shield 4k, Knight Armor/Legs 3.5k, Dragon Hammer 3k, Crown Helmet / War Hammer / Platinum Amulet 2.5k, Devil Helmet / Guardian Shield / Serpent Sword / Knight Axe 2k, Beholder Shield / Lady Armor 1.5k, Spike Sword 1.2k, Plate Legs 700, Two-Handed Sword / Scarf 600, Plate Armor / Broad Sword / Mystic Turban 500, Halberd 400, Double Axe / Clerical Mace 300, Brass Armor 250, Battle Axe / Dwarven Shield 200, Iron Helmet 150, Brass/Chain Legs / Battle Hammer 100, Short Sword 60, Chain Armor / Sword / Sabre 50, Chain Helmet 30, Mace / Hatchet 10.
- **Parived (`data/npc/scripts/parived.lua`)**: Gold Nugget 10k, Big Emerald / Big Ruby / Blue Gem 5k, Violet Gem 4k, Yellow Gem 1k, Small Diamond / Talon 300, Small Sapphire / Ruby / Emerald 250, Small Amethyst 200, Scarab Coin 100.

### A.2 Estimaciones conservadoras de mercado / utilidad (sumadas solo en `Total 1k`)
- **Anillos (50% de Dufi)**: Might Ring 3.5k, Stealth Ring 2k, Energy Ring 1.5k, Ring of Healing 1.25k, Time Ring 1k, Life Ring 750, Sword/Axe/Club/Dwarven Ring 500, Power Ring 250; Ring of the Skies 15k, Emerald Bangle 800, Crystal Ring 250.
- **Wands/Rods (40% de Dark Rodo)**: Tempest/Inferno 6k, Cosmic Energy/Quagmire 4k, Plague/Volcanic 2k, Dragonbreath/Moonlight 400, Vortex/Snakebite 200.
- **Perlas, cristales y munición**: Black Pearl 280, White Pearl 160, Life Crystal 400, Orb 750, Mind Stone 170, Crystal Necklace 400, Golden Mug 250; SD 150, HMM 10, Burst Arrow 8, Throwing Star/Knife 8, Power Bolt/Spear 5, Small Stone 3, Bolt 2, Arrow 1.
- **Equipo clásico sin comprador NPC**: Magic Longsword 250k, Golden Boots 250k, Great Shield 200k, Demon Armor/Legs 150k, Horned Helmet 100k, Demon Helmet 80k, Phoenix Shield 50k, Great Halberd 20k, Crystal Mace 12k, Red Robe 10k, Daramanian Waraxe / Griffin Shield 4k, Scarab Shield 2k, Obsidian Lance / Ancient Shield / Tusk Shield / Noble Armor 1.5k, Dark Armor 600, Strange Helmet / Dark Shield 500, Dark Helmet 300, Steel Helmet/Shield 200, Scale Armor / Battle Shield 100.
- **Raros custom Retro76 / Zagan**: Rootcleaver 150k, Heartwood Maul 150k, Imperial/Sapphire Crown Armor 120k, Ironhide Crusher 110k, Bloodreaver Saber 105k, Sword of Silence 100k, Stormcaller/Ashlord/Frostwarden 95k, Bonepriest Reaver 85k, Medusa Sword 80k, Windsting Axe 75k, Venomqueen Fang 70k, Fury Cape 60k, Crystal Arrow 30k, Nightglass Dagger 25k, Aurora Shield 15k.

## Apéndice B — Verificación técnica XML vs. C++ (0 advertencias)

Todos los **544 XML** pasan la validación estricta de `loadLootItem()` / `createLootItem()` sin advertencias (`countmax ≤ 100`, sin `Golden Ring` bloqueado, sin `chance1` en ítems no stackables y sin `chance1 ≤ chancemax`).
