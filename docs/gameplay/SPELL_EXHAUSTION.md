# Exhausted — spells y runas (YurOTS / Retro76)

Documento del cooldown mágico del jugador: cómo se aplica, qué lo ignora, y dónde se configura.

Leer **antes** de tocar tiempos de cast, spam de curas/runas, o bindings C++ nuevos en `spells.cpp`.

Relacionados: [`SPELL_RUNTIME.md`](SPELL_RUNTIME.md) (carga Lua / `safeCast`), [`SPELL_CAST_VISIBILITY.md`](SPELL_CAST_VISIBILITY.md) (texto del spell vs exhausted), [`ML_RATE.md`](ML_RATE.md) (spam `exura` y ML).

Referencia de diseño (jul 2026): alineado con [Nostalrius 7.7](https://github.com/Ezzz-dev/Nostalrius) / consenso Cip 7.4–7.6 — timer único, ofensivo 2 s / no-ofensivo 1 s, **sin** alargar exhaust al fallar un cast.

---

## Config actual (`config.lua`)

| Clave | Valor actual | Qué hace |
|-------|--------------|----------|
| `exhausted` | **2000** ms | Exhaust post-cast **ofensivo** (`offensive=true`) |
| `exhaustedheal` | **1000** ms | Exhaust post-cast **no-ofensivo**: curas + support (haste, light, food, conjurar, antidote, chameleon, desintegrate…) |
| `exhaustedadd` | **0** ms | Solo yell: ms a sumar si yell mientras exhausted. Spells **no** lo usan (fallar por exhaust no alarga el timer). |

Carga en C++ (`luascript.cpp` → `g_config.EXHAUSTED` / `EXHAUSTED_HEAL` / `EXHAUSTED_ADD`). Requiere **restart del OT** (no recompilar) para cambios de config.

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
| Cura / support (`exura`, haste, conjure…) | 1000 ms | ~1 s (un tick de player) |
| Ataque / área / runa ofensiva | 2000 ms | ~2 s (dos ticks) |
| Spam cast mientras exhausted | **no** suma tiempo | Solo mensaje; timer sigue bajando |
| Yell mientras exhausted | `+= exhaustedadd` (hoy 0) | Sin penalidad con config actual |

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

1. Si `exhaustedTicks >= 1000` **y** `me->causeExhaustion(true)` → mensaje → **return false** (no gasta mana, **no** alarga el timer).
2. Si mana insuficiente → puff / “not enough mana”.
3. Si OK → resta mana y `addManaSpent`.

### 2) Aplicación post-éxito (`game.cpp` tras el cast)

```cpp
if (me->causeExhaustion(true)) {
#ifdef YUR_HEAL_EXHAUST
  if (!me->offensive)  // heal + support
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

## Ofensivo vs no-ofensivo

| Condición | Exhaust |
|-----------|---------|
| `offensive == false` | `exhaustedheal` (1000) |
| `offensive == true` (u otro efecto que cause exhaust) | `exhausted` (2000) |

Implicaciones prácticas:

- `exura` / `exura gran` / `exura vita` / `exura sio` → 1 s.
- Haste (`utani hur`), light, food, **conjurar runas** (`makeRune`): `offensive=false` → **1 s** (antes caían en 2 s por exigir `minDamage != 0`).
- Ataque / runas ofensivas → 2 s.
- SD → UH: mismo timer; tras SD hay que esperar ~2 s.

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
| `exori vis`, `exori flam`, `exori mort`, `exori vis hur` | `reduceExhaustion` |
| `exevo mort hur` | `reduceExhaustionByPercent(..., 75)` |

Se llaman **después** de un `doAreaMagic` exitoso: el cast pone 2000 y luego el helper lo corta.

---

## Runas: pipeline mágico + bindings C++

### A) Runas vía magic pipeline

Cualquier runa cuyo Lua use `doTargetMagic`, `doAreaMagic`, `doTargetExMagic`, `do*GroundMagic`, etc.

Ejemplos: HMM, SD, GFB, Explosion, MW, Soulfire, Envenom, UH rune…

- Chequean exhausted en `creatureOnPrepareMagicAttack`.
- Aplican exhausted al éxito (ofensivo 2 s / no-ofensivo 1 s).
- DoTs (Soulfire): el **lanzamiento** exhaustea; los ticks del condition **no**.
- Charge se consume solo si `safeCast` / binding devolvió éxito.

### B) Bindings C++ custom (**con** exhausted, jul 2026)

Helpers compartidos en `spells.cpp`: `playerSpellExhaustBlocked` / `applyPlayerSpellExhaust`.

| Lua / binding | Exhaust al éxito | Estilo |
|---------------|------------------|--------|
| `doParalyze` | 2000 | ofensivo |
| `doAnchorRoot` | 2000 | ofensivo |
| `doAnimateDead` | 2000 | ofensivo |
| `doConvinceCreature` | 2000 | ofensivo |
| `doCurePoison` | 1000 | support |
| `doChameleon` | 1000 | support |
| `doDesintegrate` | 1000 | support |

Comparten el mismo `exhaustedTicks` que SD/UH. Fallar por exhausted **no** gasta charge (el charge se descuenta solo si el cast tuvo éxito en `playerUseItemEx` / `playerUseBattleWindow`).

Binding C++ nuevo: **usar esos helpers** (o pasar por `creatureMakeMagic`). No dejar paths sin exhaust.

---

## Instant spells especiales

| Caso | Exhaust |
|------|---------|
| Spells Lua normales (`doAreaMagic` / `doTargetMagic`) | Pipeline normal |
| `exeta res` | Exhaust vía `doTargetMagic` previo; `doChallenge` solo aplica taunt |
| `exani hur` / `exani tera` (C++ hardcode) | Chequean `exhaustedTicks >= 1000` **antes**; **no** setean exhausted al éxito (solo mana) |
| Conjurar runas / arrows / food | Via `creatureThrowRune` → **exhaustedheal** (1 s, `offensive=false`) |
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
| `server/YurOTS/ots/source/game.cpp` | Chequeo, aplicación, tick, yell, `exani *`, visibilidad say |
| `server/YurOTS/ots/source/magic.h` / `magic.cpp` | `causeExhaustion` por clase de efecto |
| `server/YurOTS/ots/source/spells.cpp` | `reduceExhaustion*`, bindings + helpers de exhaust |
| `server/YurOTS/ots/data/spells/instant/*.lua` | Scripts que llaman helpers de reduce |

---

## Checklist al tocar exhausted

1. ¿El cambio es solo config? Editá `config.lua` y restart — no hace falta rebuild.
2. ¿Querés heal/support más lento/rápido? Tocá `exhaustedheal`, no `exhausted`.
3. ¿Spell nuevo con `doAreaMagic`/`doTargetMagic`? Hereda el pipeline solo; marcá `offensive` bien en Lua.
4. ¿Binding C++ nuevo? Usar `playerSpellExhaustBlocked` + `applyPlayerSpellExhaust(healStyle)`.
5. ¿Usás `reduceExhaustion*`? Probar in-game el timing real (post-cast + tick de 1 s).
6. Tras rebuild C++: `docker compose … up -d yurots` + `python3 scripts/ot-probe.py 127.0.0.1 7171`.

---

## Cómo probar in-game

1. Spam / hotkey hold `exura` → exhausted ~1 s; mensaje; **sin** palabras fantasma (ver visibility).
2. Spam `exori` / SD → exhausted ~2 s; fallos **no** alargan el timer.
3. Castear SD y luego UH → deben compartir el mismo `exhaustedTicks` (~2 s).
4. Haste / conjurar blank → exhaust ~1 s (no 2 s).
5. Paralyze / Anchor en cadena → exhausted compartido; no spam libre.
6. Wand spam → sin mensaje de exhausted; ritmo = attack delay.
7. Conjurar runa en PZ → exhaust 1 s + soul si aplica.
