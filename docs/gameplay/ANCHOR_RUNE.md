# Anchor Rune (2296)

Root momentáneo de **1 segundo** para war/combos. **No** es Paralyze: no aplica `ATTACK_PARALYZE`, no usa el icono de paralyze y no deja al target a speed 40 por un minuto.

## Estado actual

- Item / rune id: `2296`
- Alta en `data/spells/spells.xml`: `<rune name="Anchor" id="2296" ...>`
- Script: `data/spells/runes/anchor.lua` → `doAnchorRoot(cid, centerpos)`
- Lógica: `SpellScript::luaActionDoAnchorRoot` en `source/spells.cpp`
- Movimiento bloqueado vía `Creature::rootTicks` (`creature.h`), decrementado en el think de `game.cpp`

## Comportamiento

- Duración: **1000 ms** (`ANCHOR_ROOT_MS`)
- Efecto visual: `NM_ME_MAGIC_ENERGIE` en el target
- Mensaje al target (jugador): `You are rooted.` + `sendCancelWalk()`
- No se puede rootear a uno mismo ni a GM (`ACCESS_PROTECT`)
- Mismo piso + línea de tiro; si falla → puff / cancel
- Fuera de PZ (caster y target); en PvP marca fight / `pzLocked` como otras ofensivas

## Diferencia vs Paralyze (2278)

| | Anchor `2296` | Paralyze `2278` |
|--|---------------|-----------------|
| Mecánica | `rootTicks` (no camina) | `ATTACK_PARALYZE` + speed 40 |
| Duración | 1 s | 60 s |
| Icono paralyze | No | Sí |
| Lua | `doAnchorRoot` | `doParalyze` |

## Archivos clave

- `server/YurOTS/ots/data/spells/runes/anchor.lua`
- `server/YurOTS/ots/data/spells/spells.xml`
- `server/YurOTS/ots/source/spells.cpp` (`luaActionDoAnchorRoot`)
- `server/YurOTS/ots/source/creature.h` / `game.cpp` (`rootTicks`)

Contexto del fix de carga/crash de runas: [`SPELL_RUNTIME.md`](SPELL_RUNTIME.md).
