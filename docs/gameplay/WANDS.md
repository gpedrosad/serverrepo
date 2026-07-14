# Wands, Rods y Crimson Wand — sistema de daño y escalado por ML

Documentación técnica del sistema de wands/rods en YurOTS 7.6 (mod Retro76): qué wand existe, cómo se usan, qué daño hacen, y cómo interactúan con el magic level y la Violet Gem.

> **TL;DR:** Ninguna wand del server escala daño con ML por defecto. A partir de este cambio (commit pendiente) **todas** las 11 wands escalan daño por `getEffectiveMagLevel() * wandmlfactor`. Con `wandmlfactor = 0.5` (default), un mage de ML 20 pega +10 dmg, ML 50 pega +25 dmg, y con Violet Gem 4/4 la Crimson Wand (55-65) llega a ~82-92 dmg.

---

## 0. Contexto

| Item | Valor |
|------|-------|
| Sistema | `useWand()` en `game.cpp` (guard `#ifdef JD_WANDS`) |
| Identificación | `isWandItem()` en `player.cpp:3103` |
| Delay custom | `Player::getAttackDelayMs()` en `player.cpp:3258` (solo Crimson) |
| ML imbue (Violet) | `checkBoh()` + `imbueWandMl` en `player.cpp:3174-3251` |
| Config | `config.lua` → `wandmlfactor` (default `0.5`) |

---

## 1. Wands y rods implementadas

| Server ID | Nombre | Vocación | Level | Mana | Rango | Daño base (sin ML) | Attack type |
|-----------|--------|----------|-------|------|-------|--------------------|-------------|
| 2181 | Snakebite Rod | Druid | 7 | 2 | 5 | 8–18 | poison (NM_ANI_FLYPOISONFIELD) |
| 2182 | Moonlight Rod | Druid | 13 | 3 | 5 | 14–24 | energy (NM_ANI_ENERGY) |
| 2183 | Volcanic Rod | Druid | 19 | 5 | 5 | 25–35 | fire (NM_ANI_FIRE) |
| 2185 | Quagmire Rod | Druid | 26 | 8 | 5 | 40–50 | poison (NM_ANI_FLYPOISONFIELD) |
| 2186 | Tempest Rod | Druid | 33 | 13 | 5 | 60–70 | energy (NM_ANI_ENERGY) |
| 2187 | Wand of Inferno | Sorcerer | 33 | 13 | 5 | 60–70 | fire (NM_ANI_FIRE) |
| **2190** | **Wand of Vortex** | **Sorcerer** | **7** | **2** | **5** | **8–18** | **energy (NM_ANI_ENERGY)** |
| **2191** | **Wand of Dragonbreath** | **Sorcerer** | **13** | **3** | **5** | **14–24** | **fire (NM_ANI_FIRE)** |
| **2188** | **Wand of Plague** | **Sorcerer** | **19** | **5** | **5** | **25–35** | **poison (NM_ANI_FLYPOISONFIELD)** |
| **2189** | **Wand of Cosmic Energy** | **Sorcerer** | **26** | **8** | **5** | **40–50** | **energy (NM_ANI_ENERGY)** |
| **20123** | **Crimson Wand** | **Sorc / MS / Druid / ED** | **33** | **13** | **5** | **55–65** | **energy + animación HMM (NM_ANI_FIRE + NM_ME_EXPLOSION_DAMAGE + NM_ME_ENERGY_DAMAGE)** |
| **20126** | **Train Wand** | **Sorc / MS / Druid / ED** | **1** | **0** (crédito ML 1) | **5** | **1–1** | **energy (NM_ANI_ENERGY) — solo trainers** |

> Constantes en `server/YurOTS/ots/source/const76.h:218-279`. Crimson Wand en línea `233`.
> Lógica de daño: `server/YurOTS/ots/source/game.cpp:7298-7496` (`Game::useWand`).

### Diferencias visuales por wand

- **Fire wands** (Volcanic, Dragonbreath, Inferno): animación `NM_ANI_FIRE`, color `0xC7`, hit `NM_ME_FIRE_AREA`.
- **Energy wands** (Moonlight, Quagmire NO — Quagmire es poison, Tempest, Vortex, Cosmic): `NM_ANI_ENERGY`/`NM_ME_ENERGY_DAMAGE`/`NM_ME_ENERGY_AREA`, color `0x47` (o `0x49` para Tempest).
- **Poison wands/rods** (Snakebite, Quagmire, Plague): `NM_ANI_FLYPOISONFIELD`/`NM_ME_POISEN_RINGS`, color `0x60`.
- **Crimson Wand** (custom, server id 20123): `ATTACK_ENERGY` + `NM_ANI_FIRE` + `NM_ME_EXPLOSION_DAMAGE` + `NM_ME_ENERGY_DAMAGE`. Animación copiada de la runa **Heavy Magic Missile** (`data/spells/runes/heavy magic missile.lua`).
- **Train Wand** (custom, server id 20126): misma animación energy que Vortex. Solo funciona contra monstruos `trainer="1"`; no gasta mana; `addManaSpent(1)` por hit (~50% Vortex); sin scaling `wandmlfactor`.

---

## 2. Flujo de uso (lo que pasa cuando equipás una wand y atacás)

```
[Player hace click en wand equipada]
        |
        v
[isWandItem() reconoce la wand]    <- player.cpp:3103
        |
        v
[attack] --> creatureOnPrepareAttack --> checks PZ
        |
        v
[Player::getWandId()]              <- player.cpp:3930 (bajo JD_WANDS)
   busca en SLOT_RIGHT..SLOT_LEFT un item cuyo ID esté en la lista de wands
   (incluye ITEM_CRIMSON_WAND)
        |
        v
[Game::useWand(player, target, wandid)]    <- game.cpp:7284
   1. check de vocación (Sorc / Druid / promoted) y level mínimo
   2. check de mana >= g_config.MANA_*
   3. check de rango (abs(x) <= RANGE_*, abs(y) <= RANGE_*)
   4. setea minDamage / maxDamage (FIJOS, 8-18, 14-24, 25-35, 40-50, 55-65, 60-70)
   5. setea attackType / animationEffect / hitEffect / areaEffect / animationColor
   6. *** NUEVO (jul 2026): bonus de ML ***
      minDamage += floor(getEffectiveMagLevel() * wandmlfactor)
      maxDamage += floor(getEffectiveMagLevel() * wandmlfactor)
   7. creatureThrowRune(player, target->pos, runeAreaSpell)    <- game.cpp:4114
        |
        v
[MagicEffectAreaNoExhaustionClass::getDamage]    <- magic.cpp:64 (clase base)
   damage = random_range(minDamage, maxDamage)
   (NO usa ML, NO usa maglevel; solo el minDamage/maxDamage seteado en useWand)
        |
        v
[damage al target, mana -= cost, addManaSpent]
```

### El bug clásico de la crimson wand (y de las 10 vanilla)

`MagicEffectClass::getDamage()` (`magic.cpp:64`) **nunca** mira `maglevel`, `getEffectiveMagLevel()`, ni `imbueWandMl`. Solo hace `random_range(minDamage, maxDamage)`. Los valores min/max se setean en `useWand()` como **constantes fijas** hardcoded.

Resultado antes del fix: aunque tengas 4 violet gems en la crimson wand (`imbueWandMl = 4`) y tu ML efectivo sea 50, la wand seguía pegando 55-65 igual que un mage nivel 1. La ML imbue solo afectaba:
- UI: `getEffectiveMagLevel()` → `protocol76.cpp:2872` muestra el número más alto
- Spell level requirement: `game.cpp:5064, 5163, 5231` te deja castear spells de nivel más alto
- **No** el daño de la wand

Esto hacía a la crimson wand inútil para su propuesta de diseño ("mejor wand, requiere inversión en violet gems") y a las 10 vanilla indiferentes a la inversión en ML.

### El fix (este cambio)

Antes de `creatureThrowRune()` (`game.cpp:7517`), sumar al minDamage y al maxDamage el bonus de ML:

```cpp
if(g_config.WAND_ML_FACTOR > 0.0){
    const int64_t mlBonus = (int64_t)(player->getEffectiveMagLevel() * g_config.WAND_ML_FACTOR);
    if(mlBonus > 0){
        runeAreaSpell.minDamage += (int)mlBonus;
        runeAreaSpell.maxDamage += (int)mlBonus;
    }
}
```

`getEffectiveMagLevel()` (definido en `player.cpp:3253`):

```cpp
int64_t Player::getEffectiveMagLevel() const
{
    return maglevel + imbueWandMl + imbueHelmMl + imbueArmorMl;
}
```

Por lo tanto el bonus incluye **toda** la ML imbue del jugador:
- `maglevel` (natural)
- `imbueWandMl` (de la violet gem en **esta u otra wand** — 0 a 4)
- `imbueHelmMl` (de Magic Turban en head — 0 o 1)
- `imbueArmorMl` (de Fury Cape en armor — 0 o 1, solo Sorc/Druid)

### Ejemplos numéricos (con `wandmlfactor = 0.5`)

| Setup | `getEffectiveMagLevel()` | Bonus | Wand base | Daño final |
|-------|--------------------------|-------|-----------|------------|
| Sorc ML 20, sin imbue, Wand of Vortex | 20 | +10 | 8–18 | 18–28 |
| Sorc ML 50, sin imbue, Wand of Inferno | 50 | +25 | 60–70 | 85–95 |
| Sorc ML 50 + Magic Turban, Wand of Inferno | 51 | +25 | 60–70 | 85–95 |
| Sorc ML 50 + Fury Cape, Wand of Inferno | 51 | +25 | 60–70 | 85–95 |
| Sorc ML 50 + Magic Turban + Fury Cape, Wand of Inferno | 52 | +26 | 60–70 | 86–96 |
| Sorc ML 50 + Violet 4/4, Wand of Inferno | 54 | +27 | 60–70 | 87–97 |
| Sorc ML 50 + Magic Turban + Fury Cape + Violet 4/4, Wand of Inferno | 56 | +28 | 60–70 | 88–98 |
| **MS ML 50 + Violet 4/4, Crimson Wand** | **54** | **+27** | **55–65** | **82–92** |
| **MS ML 80 + Violet 4/4 + Magic Turban + Fury Cape, Crimson Wand** | **86** | **+43** | **55–65** | **98–108** |

(Redondeo floor en cada cálculo.)

### Por qué la crimson wand es la más beneficiada

La crimson wand tiene:
- `dmg/mana` = `60/13` = **4.6** (Wand of Inferno = `65/13` = 5.0)
- `dmg/mana` = `55/13` = **4.2** (min) hasta `65/13` = **5.0** (max)

Pero su **diferencial** respecto a la Wand of Inferno (que es su "competidora directa", mismo level/mana/ataque type) es:
- Sin ML scaling: **pega igual o un poco menos** (55-65 vs 60-70). Inútil.
- Con ML scaling (`wandmlfactor = 0.5`): pega un poco menos en base, pero el scaling hace que **a ML alta la crimson quede comparable** (un MS ML 80 con 4/4 violet llega a 98-108 vs 105-115 de inferno con mismo ML).
- A ML baja (donde el scaling aporta poco), la Wand of Inferno sigue siendo mejor — coherente con que la crimson es un item end-game.

La Violet Gem tiene un costo real: 20 small amethyst → 1 violet (NPC Tonka, `exchange amethyst`), y el imbue tiene 50% fail chance (ver `docs/gameplay/GEMS.md`). Eso justifica que la crimson wand necesite ML alta para brillar.

---

## 3. Configuración (`config.lua`)

```lua
-- magic level damage factor for wands/rods (JD_WANDS)
-- damage is increased by: floor( getEffectiveMagLevel() * wandmlfactor )
-- getEffectiveMagLevel() = maglevel + imbueWandMl (violet gem) + imbueHelmMl + imbueArmorMl
--   ML 20 (no imbue) at factor 0.5 -> +10 dmg
--   ML 50 (no imbue) at factor 0.5 -> +25 dmg
--   ML 50 + violet gem 4/4 at factor 0.5 -> +27 dmg
--   crimson wand 55-65 + ML 50 + 4/4 violet -> ~82-92 dmg
-- set to 0 to disable ML scaling on wands (vanilla YurOTS behavior)
wandmlfactor = 0.5
```

### Tuning guide

| Factor | Sensación | Caso de uso |
|--------|-----------|-------------|
| `0.0` | Vanilla. Wands escalan 0 con ML. | Debug / rollback |
| `0.25` | Sutil. Un ML 50 aporta +12 dmg. | Server con énfasis en hechizos |
| `0.5` (default) | Moderado. ML 50 → +25. | Balance estándar (recomendado) |
| `0.75` | Fuerte. ML 50 → +37. | Server con énfasis en builds mágicas |
| `1.0` | Agresivo. ML 50 → +50. | ML = stat dominante, casi OTX-style |

Si se sube mucho, vigilar la interacción con spells de daño área (GFB, UE) que ya escalan con ML por `BURST_DMG_MLVL = 5.0` y la runa HMM (que es la animación copiada por crimson wand). Riesgo de wizards one-shot-eando bosses.

---

## 4. Implementación técnica

### Archivos tocados

| Archivo | Cambio |
|---------|--------|
| `server/YurOTS/ots/config.lua` | Agrega `wandmlfactor = 0.5` |
| `server/YurOTS/ots/source/luascript.h` | Declara `double WAND_ML_FACTOR;` bajo `#ifdef JD_WANDS` |
| `server/YurOTS/ots/source/luascript.cpp` | Carga `wandmlfactor` con default `0.5` |
| `server/YurOTS/ots/source/game.cpp` | En `useWand()`, antes de `creatureThrowRune`, suma el bonus |

### Decisiones de diseño

1. **No se modifican los `minDamage`/`maxDamage` base de las 10 wands vanilla.** El bonus se suma **encima** del daño base. Si querés volver a vanilla, poné `wandmlfactor = 0` y queda idéntico.
2. **El bonus usa `getEffectiveMagLevel()`, no `maglevel` directamente.** Esto significa que violet gem, magic turban, fury cape **todos** suman al daño de la wand. Es coherente: lo que hace más daño con spells debería hacer más daño con wand.
3. **El bonus se aplica a las 11 wands por igual.** No se le da tratamiento especial a crimson. La crimson brilla naturalmente porque su item design предполага ML alta (requiere level 33 + violet gem 4/4 para ser competitiva).
4. **No se toca `MagicEffectClass::getDamage()`.** El cambio está contenido en `useWand()` y no afecta a spells, runas, ni GFB. Riesgo de regresión bajo.
5. **Guard `if(g_config.WAND_ML_FACTOR > 0.0)`** permite desactivar el bonus sin recompilar (solo editando config.lua y reiniciando el OT).

### Lo que NO se cambió (y por qué)

- **`Player::getAttackDelayMs()`** sigue devolviendo 667 ms solo para crimson wand (`player.cpp:3261`). Es independiente del daño.
- **`isWandItem()` y `getWandId()`** ya incluían ITEM_CRIMSON_WAND desde el deploy Zagan. No hubo que tocarlos.
- **La cadena de if-else de `useWand()`** (que tiene un bug pre-existente: `if` en vez de `else if` para Moonlight Rod, `game.cpp:7370`) **no se tocó.** Queda como está hasta un fix aparte.

---

## 5. Verificación

### Local (antes de deploy a producción)

```bash
# 1. Levantar OT local
docker compose -f docker-compose.prod.yml up -d yurots

# 2. Probe de estado
python3 scripts/ot-probe.py 127.0.0.1 7171

# 3. Equipar crimson wand SIN imbue, pegar a un Training Dummy o monstruo bajo
#    Esperado: daño ~55-65 +/- 5
# 4. Equipar crimson wand CON violet gem 4/4, mismo target
#    Esperado: daño = 55-65 + floor(ML * 0.5) por cada hit
# 5. Equipar Magic Turban + Fury Cape, mismo target
#    Esperado: daño aún mayor (ML efectiva +2)
# 6. Equipar wand of inferno, repetir 3-5
#    Esperado: 60-70 base + bonus ML; consistente con la tabla de ejemplos

# 7. Cambiar wandmlfactor a 0 en config.lua, reiniciar OT, repetir
#    Esperado: comportamiento vanilla (daño fijo)
```

### En producción (VPS, solo después de OK explícito)

```bash
# 1. Backup de config.lua y de players/accounts antes de deploy
DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh

# 2. Verificar que el binario tiene el cambio
docker exec yurots strings /app/YuroTS/ots/source/yurots | grep -i "wandmlfactor" || echo "WARN: binario no actualizado"

# 3. Probe contra el VPS
python3 scripts/ot-probe.py retro76.cl 7171

# 4. In-game test con GM char: equipar crimson wand, pegar dummy, verificar daño
```

---

## 6. Items custom Zagan con gameplay de wand

| Server ID | Nombre | Qué hace | Doc |
|-----------|--------|----------|-----|
| `20123` | Crimson Wand | Wand 55-65 dmg, 13 mana, range 5, delay 667ms, animación HMM, scaling por ML (este fix) | este doc + `docs/items-and-map/ZAGAN_TEST_ITEMS.md` |
| `20126` | Train Wand | Solo trainers (`trainer=1`): 0 mana, `addManaSpent(1)` (~50% Vortex), daño 1-1, sorc/druid (incl. promoted) | este doc + `docs/gameplay/PRIVATE_TRAINER_DUMMY.md` |

Items custom con gameplay C++ adicional que **conviven** con el sistema de wands:
- `20113` Crimson Helmet: bonus de skills (no toca wands)
- `20114` Fury Cape: +1 ML al slot armor (Sorc/Druid) — **sí** aporta al bonus de ML de la wand
- `20105` Medusa Sword: paralyze PvP on-hit (arma cuerpo a cuerpo, no wand)
- `20139` Sword of Silence: 10% silencio PvP 2-3s (arma cuerpo a cuerpo, no wand)
- `20137` Nightglass Dagger: dagger con scaling speed + fire animation custom

Ver `docs/items-and-map/ZAGAN_TEST_ITEMS.md` para el pipeline completo (assets + gameplay C++).

---

## 7. Pitfalls / cosas a tener en cuenta

- **Bonus escala con TODA la ML efectiva**, no solo `maglevel` natural. Un sorc con Fury Cape + Magic Turban + Violet 4/4 + ML 50 natural va a pegar con un bonus de +28. Asegurarse de que el balance de PvP no se rompa.
- **PvP con wands + violet gem** se vuelve relevante en late game. Si se reporta "wands op en PvP", bajar `wandmlfactor` a 0.3 o 0.25 antes que nerfear las wands base.
- **El damage final se sigue computando con `random_range(minDamage, maxDamage)`.** El bonus es determinístico (suma constante al min y al max), pero el hit específico sigue siendo random. No hay cambio en la "forma" de la distribución.
- **No confundir `getEffectiveMagLevel()` con `maglevel` raw.** En el protocolo76 se muestra el primero. En el XML del player se persiste el segundo. El bonus usa el primero.
- **Wands/rods no consumen charges** (no son `wand` con `charges` en el OTB). Cuestan mana por hit. El violet gem imbue es **persistente en el actionid** del item (`AID 9030-9033`).
- **Crimson Wand NO usa el rango ni la mana de `g_config.MANA_INFERNO`/`RANGE_INFERNO`.** Tiene valores hardcoded (`mana = 13`, `dist = 5`) en el branch de `useWand()`. Esto es deliberado (item custom), pero si se cambia la config de inferno, crimson no se ve afectada.

---

## 8. Cómo reportar bugs o proponer cambios

Si ves que una wand está OP/UP después del cambio:

1. **No tocar código sin avisar.** AGENTS.md §2 / §5.
2. Reportar con:
   - Wand usada (server id, nombre)
   - Vocación + level + ML del jugador
   - ML imbue (cuántos violet gem stacks)
   - Items equipped que suman ML (Magic Turban, Fury Cape)
   - Target (jugador/monstruo, level, hp)
   - Daño observado vs esperado
3. Tuning sugerido: ajustar `wandmlfactor` en `config.lua` antes que tocar C++.

Para cambios estructurales (agregar una wand nueva, cambiar el sistema de ML imbue, etc.):
- AGENTS.md §3: leer el doc del subsistema antes de tocarlo.
- Doc del sistema de gemas: `docs/gameplay/GEMS.md`.
- Doc del sistema de items custom: `docs/items-and-map/ZAGAN_TEST_ITEMS.md`.
