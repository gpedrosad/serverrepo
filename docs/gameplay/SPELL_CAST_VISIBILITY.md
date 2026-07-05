# Spell cast visibility

## Objetivo

Evitar que el texto del spell aparezca en chat cuando el spell no llega a ejecutarse.

Caso reportado:

- el jugador spamea palabras magicas
- el spell falla por exhausted u otra validacion interna
- igual se ve el mensaje en pantalla

## Causa

El flujo de voz del cliente pasa por:

- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/protocol76.cpp`
- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp`

`Protocol76::parseSay(...)` llama `game->creatureSaySpell(player, text)`.

Si esa funcion devuelve `true`, el mensaje se reenvia como `SPEAK_SAY`.

El problema era que `Game::creatureSaySpell(...)` devolvia `true` apenas encontraba un spell valido por palabras, aunque `castSpell(...)` devolviera `false`.

## Cambio aplicado

Archivo tocado:

- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp`

Se cambio el retorno para usar el resultado real de:

- `SpellScript::castSpell(...)`

Antes:

- si el texto matcheaba un spell, el mensaje se mostraba igual

Ahora:

- el mensaje solo se muestra si `castSpell(...)` devuelve `true`

## Impacto funcional

Esto no solo cubre exhausted.

Tambien evita mostrar el texto si el spell falla por:

- target invalido
- validaciones internas del script Lua
- cualquier `return false` del `onCast`

## Archivos relacionados

- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp`
- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/protocol76.cpp`
- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/spells.cpp`

## Como probar

1. Tirar un spell repetidamente hasta entrar en exhausted
2. Verificar que aparezca `You are exhausted.`
3. Verificar que las palabras magicas no se impriman mientras el cast falle
4. Esperar que termine el exhausted
5. Volver a tirar el spell
6. Verificar que ahora si aparezca el texto y se ejecute

## Que revisar si algo raro pasa

- spells Lua que hoy dependan de devolver `false`
- spells con target que fallen silenciosamente
- scripts custom en `server/YurOTS/ots/data/spells/instant/`

## Nota tecnica

La base ya soportaba este comportamiento porque `SpellScript::castSpell(...)` devuelve boolean.
El bug era que `Game::creatureSaySpell(...)` ignoraba ese valor y trataba cualquier match de palabras como cast exitoso.
