# Spell cast visibility

## Objetivo

Evitar que el texto del spell aparezca en chat cuando el spell no llega a ejecutarse.

Detalle del sistema exhausted (tiempos, heal vs attack, runas): [`SPELL_EXHAUSTION.md`](SPELL_EXHAUSTION.md).

Caso reportado:

- el jugador spamea / deja apretado un hotkey
- el spell falla por exhausted u otra validacion interna
- igual se ve el mensaje en pantalla

## Causa

El flujo de voz del cliente pasa por:

- `server/YurOTS/ots/source/protocol76.cpp`
- `server/YurOTS/ots/source/game.cpp`

`Protocol76::parseSay(...)` llama `game->creatureSaySpell(player, text)`.

| Resultado | Comportamiento |
|-----------|----------------|
| `SPELL_CAST_SUCCESS` | Reenvia como `SPEAK_SAY` (palabras visibles) |
| `SPELL_CAST_BLOCKED` | `return` sin hablar |
| `SPELL_NOT_RECOGNIZED` | Chat normal (no era spell) |

### Bug original

`Game::creatureSaySpell(...)` devolvia exito apenas encontraba un spell valido por palabras, aunque `castSpell(...)` fallara.

### Bug residual (hotkey hold)

Habia un heuristic `didPlayerSpendSpellResources` que forzaba exito si subia `exhaustedTicks`.

Antes, al fallar por exhausted se hacia `exhaustedTicks += EXHAUSTED_ADD` sin gastar mana → el heuristic marcaba SUCCESS → palabras fantasma.

## Cambio aplicado

Archivo: `server/YurOTS/ots/source/game.cpp`

1. Retorno real: `SPELL_CAST_SUCCESS` / `SPELL_CAST_BLOCKED` / `SPELL_NOT_RECOGNIZED`.
2. Heuristic solo mira **mana** o **soul** gastados. **No** mira `exhaustedTicks`.
3. Fallar por exhausted en spells **ya no** suma `exhaustedadd` (ver [`SPELL_EXHAUSTION.md`](SPELL_EXHAUSTION.md)).

## Impacto funcional

Cubren exhausted, target invalido, validaciones Lua, y cualquier `return false` del `onCast`.

## Archivos relacionados

- `server/YurOTS/ots/source/game.cpp` (`creatureSaySpell`, `didPlayerSpendSpellResources`)
- `server/YurOTS/ots/source/protocol76.cpp` (`parseSay`)
- `server/YurOTS/ots/source/spells.cpp`
- [`SPELL_EXHAUSTION.md`](SPELL_EXHAUSTION.md)

## Como probar

1. Dejar apretado hotkey de `exura` / `exori` hasta exhausted
2. Debe aparecer `You are exhausted.`
3. Las palabras magicas **no** deben imprimirse mientras falle
4. Al terminar el exhausted, el siguiente cast si muestra texto y aplica
