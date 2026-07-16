# Exhausted — spells y runas (YurOTS / Retro76)

Documento del cooldown mágico del jugador: cómo se aplica, qué lo ignora, y dónde se configura.

Leer **antes** de tocar tiempos de cast, spam de curas/runas, o bindings C++ nuevos en `spells.cpp`.

Relacionados: [`SPELL_RUNTIME.md`](SPELL_RUNTIME.md) (carga Lua / `safeCast`), [`SPELL_CAST_VISIBILITY.md`](SPELL_CAST_VISIBILITY.md) (texto del spell vs exhausted), [`ML_RATE.md`](ML_RATE.md) (spam `exura` y ML).

---

## Config actual (`config.lua`)

| Clave | Valor actual | Qué hace |
|-------|--------------|----------|
| `exhausted` | **2000** ms | Exhaust post-cast ofensivo / no-heal (spells, runas “mágicas”, conjurar, haste, yell…) |
| `exhaustedheal` | **1000** ms | Exhaust post-cast de **curas** (`offensive=false` y `minDamage != 0`) |
| `exhaustedadd` | **300** ms | Penalidad al intentar castear / yell mientras ya estás exhausted |

Carga en C++ (`luascript.cpp` → `g_config.EXHAUSTED` / `EXHAUSTED_HEAL` / `EXHAUSTED_ADD`). Requiere **restart del OT** (no recompilar).

GM / access ≥ `accessprotect` (2): **no** se les aplica exhausted en casts mágicos ni yell.

---

## Estado runtime

| Campo | Dónde | Notas |
|-------|-------|--------|
| `Creature::exhaustedTicks` | `creature.h` | Contador en ms; se inicializa en 0 |
| Tick del jugador | `Player::onThink` → **1000** ms | Cada segundo resta `thinkTicks` si `exhaustedTicks >= 1000` |
| Umbral “estás exhausted” | `exhaustedTicks >= 1000` | Si el contador está entre 1 y 999, **no** bloquea (casi siempre 0 o ≥1000) |

Mensaje al fallar: `"You are exhausted."` (`MSG_SMALLINFO`, a veces con puff).

Con los valores actuales:

| Acción | Exhaust aplicado | Ventana efectiva de bloqueo |
|--------|------------------|-----------------------------|
| Cura (`exura`, etc.) | 1000 ms | ~1 s (un tick de player) |
| Ataque / área / runa vía `creatureMakeMagic` | 2000 ms | ~2 s (dos ticks) |
| Spam mientras exhausted | `+= 300` ms | Alarga el timer |

---

## Flujo canónico (spells / runas “mágicas”)

Casi todo pasa por `Game::creatureMakeMagic` → `creatureOnPrepareMagicAttack` → (éxito) setea `exhaustedTicks`.

```
Lua onCast
  → doTargetMagic / doAreaMagic / doTargetExMagic / do*GroundMagic / makeRune…
    → creatureThrowRune / creatureCastSpell
      → creatureMakeMagic
        1) creatureOnPrepareMagicAttack  ← chequea exhausted + mana
        2) aplica efecto
        3) si causeExhaustion(true) → setea EXHAUSTED o EXHAUSTED_HEAL
```

### 1) Chequeo previo (`game.cpp` — `creatureOnPrepareMagicAttack`)

Para players con `access < ACCESS_PROTECT`:

1. Si `exhaustedTicks >= 1000` **y** `me->causeExhaustion(true)` → mensaje + `exhaustedTicks += EXHAUSTED_ADD` → **return false** (no gasta mana).
2. Si mana insuficiente → puff / “not enough mana”.
3. Si OK → resta mana y `addManaSpent`.

### 2) Aplicación post-éxito (`game.cpp` tras el cast)

```cpp
if (me->causeExhaustion(true)) {
#ifdef YUR_HEAL_EXHAUST
  if (!me->offensive && me->minDamage != 0)  // cura
    attackPlayer->exhaustedTicks = g_config.EXHAUSTED_HEAL;
  else
#endif
    attackPlayer->exhaustedTicks = g_config.EXHAUSTED;
}
```

`YUR_HEAL_EXHAUST` está activo en el `Makefile` del server.

### Quién causa exhausted (`causeExhaustion`)

| Clase mágica | `causeExhaustion` | Ejemplos |
|--------------|-------------------|----------|
| `MagicEffectClass` (base) | `return hasTarget` (en call sites siempre pasan `true`) | Target spells genéricos |
| `MagicEffectAreaClass` | siempre `true` | GEB, UE, waves, GFB… |
| `MagicEffectTargetGroundClass` | siempre `true` | Magic Wall, Wild Growth, fields |
| `MagicEffectTargetCreatureCondition` | siempre `false` | Ticks de DoT (Soulfire, poison…) |
| `MagicEffectItem` (fields en suelo) | `false` | No re-exhaustea al pisar |
| `MagicEffectAreaNoExhaustionClass` | `false` | **Wands/rods** y burst arrow |

---

## Curas vs ofensivos

| Condición | Exhaust |
|-----------|---------|
| `offensive == false` **y** `minDamage != 0` | `exhaustedheal` (1000) |
| Cualquier otro efecto que cause exhaust | `exhausted` (2000) |

Implicaciones prácticas:

- `exura` / `exura gran` / `exura vita` / `exura sio` → heal exhaust.
- Haste (`utani hur`), light, food, **conjurar runas** (`makeRune`): `offensive=false` pero `minDamage==0` → **exhaust de ataque (2000)**, no heal.
- Mass healing con rama `minDmg = 0` (algunos scripts) puede caer en exhaust de ataque si esa rama se usa.

---

## Reducciones Lua (post-cast)

Registradas en `spells.cpp`:

| Función Lua | Efecto |
|-------------|--------|
| `reduceExhaustion(cid)` | Si `exhaustedTicks >= EXHAUSTED/2`, lo baja a `EXHAUSTED/2` (hoy: 2000 → **1000**) |
| `reduceExhaustionByPercent(cid, percent)` | Cap a `EXHAUSTED * percent / 100` (ej. 75 → **1500**) |

Usado hoy en:

| Spell | Helper |
|-------|--------|
| `exori vis`, `exori flam`, `exori mort` | `reduceExhaustion` |
| `exevo mort hur` | `reduceExhaustionByPercent(..., 75)` |

Se llaman **después** de un `doAreaMagic` exitoso: el cast pone 2000 y luego el helper lo corta.

---

## Runas: dos mundos

### A) Runas vía magic pipeline (sí exhausted)

Cualquier runa cuyo Lua use `doTargetMagic`, `doAreaMagic`, `doTargetExMagic`, `do*GroundMagic`, etc.

Ejemplos: HMM, SD, GFB, Explosion, MW, Soulfire, Envenom, UH rune…

- Chequean exhausted en `creatureOnPrepareMagicAttack`.
- Aplican exhausted al éxito.
- DoTs (Soulfire): el **lanzamiento** exhaustea; los ticks del condition **no**.

Uso de runa: `Game::playerUseItemEx` / `playerUseBattleWindow` → `SpellScript::safeCast` → script Lua. No hay chequeo de exhausted **fuera** de `creatureMakeMagic`.

### B) Bindings C++ custom (hoy: **sin** exhausted)

Estos helpers **no** pasan por `creatureMakeMagic`. No chequean `exhaustedTicks` al inicio ni lo setean al éxito:

| Lua / binding | Runa / uso |
|---------------|------------|
| `doParalyze` | Paralyze `2278` |
| `doAnchorRoot` | Anchor `2296` |
| `doDesintegrate` | Desintegrate `2310` |
| `doCurePoison` | Antidote `2266` |
| `doAnimateDead` | Animate Dead `2316` |
| `doConvinceCreature` | Convince `2290` |
| `doChameleon` | Chameleon `2291` |

Consecuencia: se pueden spamear a ritmo de click / charges (y validaciones propias: PZ, line of sight, target, etc.), **sin** cooldown de exhausted compartido con SD/UH.

Si se quiere exhausted en una de estas, hay que:

1. Chequear `exhaustedTicks >= 1000` al inicio (y opcionalmente `+= EXHAUSTED_ADD` + mensaje), y
2. Setear `exhaustedTicks = EXHAUSTED` (o `EXHAUSTED_HEAL`) al éxito,

o bien reescribir el efecto para que pase por `creatureThrowRune` / `creatureMakeMagic`.

---

## Instant spells especiales

| Caso | Exhaust |
|------|---------|
| Spells Lua normales (`doAreaMagic` / `doTargetMagic`) | Pipeline normal |
| `exani hur` / `exani tera` (C++ hardcode) | Chequean `exhaustedTicks >= 1000` **antes**; **no** setean exhausted al éxito (solo mana) |
| Conjurar runas / arrows / food | Via `creatureThrowRune` → exhaust **2000** (no heal) |
| Yell | Si exhausted: `+= EXHAUSTED_ADD` + mensaje; si no: setea `EXHAUSTED` y yellea |

Visibilidad del texto del spell al fallar por exhausted: [`SPELL_CAST_VISIBILITY.md`](SPELL_CAST_VISIBILITY.md).

---

## Qué **no** usa exhausted de spells

| Sistema | Comportamiento |
|---------|----------------|
| Wands / rods (`useWand`) | `MagicEffectAreaNoExhaustionClass` — delay propio del arma (`getAttackDelayMs`), no exhausted mágico |
| Burst arrow | Misma clase NoExhaustion |
| Ataque melee / distancia físico | Cooldown de ataque, no `exhaustedTicks` |
| Monstruos | `exhaustedTicks` propio del AI (`monster.xml` `exhaustion` / `cycleticks`) — **otro sistema** |

---

## Archivos clave

| Archivo | Rol |
|---------|-----|
| `server/YurOTS/ots/config.lua` | `exhausted`, `exhaustedheal`, `exhaustedadd` |
| `server/YurOTS/ots/source/luascript.cpp` | Carga a `g_config` |
| `server/YurOTS/ots/source/creature.h` | `exhaustedTicks` |
| `server/YurOTS/ots/source/game.cpp` | Chequeo, aplicación, tick, yell, `exani *` |
| `server/YurOTS/ots/source/magic.h` / `magic.cpp` | `causeExhaustion` por clase de efecto |
| `server/YurOTS/ots/source/spells.cpp` | `reduceExhaustion*`, bindings custom, `makeRune` |
| `server/YurOTS/ots/data/spells/instant/*.lua` | Scripts que llaman helpers de reduce |

---

## Checklist al tocar exhausted

1. ¿El cambio es solo config? Editá `config.lua` y restart — no hace falta rebuild.
2. ¿Querés heal más lento/rápido? Tocá `exhaustedheal`, no `exhausted`.
3. ¿Spell nuevo con `doAreaMagic`/`doTargetMagic`? Hereda el pipeline solo; no hace falta código extra.
4. ¿Binding C++ nuevo tipo Paralyze/Anchor? **Decidir explícitamente** si debe compartir exhausted; hoy los custom no lo hacen.
5. ¿Usás `reduceExhaustion*`? Probar in-game el timing real (post-cast + tick de 1 s).
6. Tras rebuild C++: `docker compose … up -d yurots` + `python3 scripts/ot-probe.py 127.0.0.1 7171`.

---

## Cómo probar in-game

1. Spam `exura` → exhausted ~1 s; mensaje; palabras no deben verse si el cast falla (ver visibility).
2. Spam `exori` / SD → exhausted ~2 s.
3. Castear SD y luego UH → deben compartir el mismo `exhaustedTicks`.
4. Usar Paralyze / Anchor en cadena → hoy **sin** exhausted (solo charges / validaciones).
5. Wand spam → sin mensaje de exhausted; ritmo = attack delay.
6. Conjurar runa en PZ → exhaust 2 s + soul si aplica.
