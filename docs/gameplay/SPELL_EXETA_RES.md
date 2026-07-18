# Spell: `exeta res` (Challenge) — jul 2026

Taunt de Knight: monstruos cercanos te toman de target y **no cambian / no huyen** durante **6 s**.

Oficial (TibiaWiki): Challenge — Elite Knight, 40 mana, lvl 20. En Retro76: **Knight / EK** (`voc 4`), maglv **5**, mana **40** (sin exigir `promoted`).

Relacionados: [`SPELL_RUNTIME.md`](SPELL_RUNTIME.md), [`SPELL_EXHAUSTION.md`](SPELL_EXHAUSTION.md).

---

## Specs

| Atributo | Valor |
|----------|--------|
| words | `exeta res` |
| XML name | Challenge |
| maglv / mana | 5 / 40 |
| vocación | Knight (`id="4"`, incluye Elite Knight) |
| rango | **1** Chebyshev (cuadrado 3×3 centrado en el caster) |
| duración lock | **6000 ms** |
| afecta | monstruos (no players, no summons, no private trainers) |
| exhaust | ofensivo normal (~2000 ms) vía `doTargetMagic` |
| visual | sonido azul en caster; `NM_ME_MAGIC_ENERGIE` en cada mob afectado |

---

## Cómo funciona

1. Lua gasta mana / exhaust con `doTargetMagic` sobre sí mismo.
2. `doChallenge(cid)` (C++) recorre tiles 3×3 y llama `Monster::applyChallenge(caster, 6000)`.
3. El monstruo fija `attackedCreature` al knight y setea `challengeTicks` / `challengedBy`.
4. Mientras `challengeTicks >= 1000`:
   - no retarget (`changeTargetChance` ignorado)
   - no entra en `STATE_FLEEING` (útil vs mobs con `runAwayHealth`)
   - si pierde el target, lo re-aplica al challenger
5. `game.cpp` baja el timer en el think de criaturas no-player.

---

## Archivos

| Archivo | Rol |
|---------|-----|
| `data/spells/instant/exeta res.lua` | Script Instant |
| `data/spells/spells.xml` | Entrada Challenge |
| `source/creature.h` / `creature.cpp` | `challengeTicks`, `challengedBy` |
| `source/monster.h` / `monster.cpp` | `applyChallenge`, lock en `selectTarget` / `reThink` |
| `source/spells.h` / `spells.cpp` | Binding `doChallenge` |
| `source/game.cpp` | Tick del timer |

**Rebuild C++ obligatorio** (`creature.h` cambió → preferir `make clean && make`).

---

## Cómo revertir

1. Borrar `instant/exeta res.lua` y la línea Challenge en `spells.xml`.
2. Quitar `doChallenge` / `luaActionDoChallenge` de `spells.h` / `spells.cpp`.
3. Quitar `applyChallenge` / `isChallengeLocked` y los guards de challenge en `monster.cpp` / `monster.h`.
4. Quitar `challengeTicks` / `challengedBy` de `creature.h` / `creature.cpp` y el tick en `game.cpp`.
5. `make clean && make`, restart, `ot-probe.py`.

O `git revert` del commit si quedó aislado.

---

## Checklist de prueba

1. Rebuild limpio + restart `yurots` + `python3 scripts/ot-probe.py 127.0.0.1 7171`
2. Knight ML ≥ 5, mana ≥ 40, 2+ monstruos a ≤1 SQM (ideal: uno pegándole a un party member)
3. `exeta res` → ambos te targetean; efecto azul en ellos
4. Durante ~6 s no deberían cambiar de target ni huir al low HP
5. Tras 6 s vuel a AI normal
6. Summons / players en el área no se ven afectados

---

## Notas de diseño

- Oficial es solo EK comprable; acá cualquier Knight con maglv puede usarlo (server chico).
- El binding **no** gasta mana solo: depende del `doTargetMagic` previo (exhaust correcto).
- Si el path al knight está bloqueado, el mob puede quedar en `STATE_TARGETNOTREACHABLE` pero sigue “lockado” al challenger (mismo caveat que Cip).
