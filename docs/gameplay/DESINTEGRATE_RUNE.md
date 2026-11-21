# Desintegrate Rune

`Desintegrate` (`adito tera`, rune `2310`) ya no queda como item "huerfano": ahora tiene implementacion real de uso.

## Estado actual

- El spell instantaneo `adito tera` sigue creando la rune `2310`.
- La rune usa `server/YurOTS/ots/data/spells/runes/desintegrate.lua`.
- La logica real vive en C++ con `SpellScript::luaActionDoDesintegrate(...)`.

## Que destruye

`Desintegrate` ahora intenta destruir, a distancia valida y con linea de tiro:

- `magic wall` (`1497` / `1498`)
- `wild growth` (`1499`, runa `2269`)
- objetos del set legacy de destruccion del server, el mismo set que ya usaba `destroy.lua` para items destruibles de mapa (bloqueado en PZ y casas para jugadores normales)

Eso deja la separacion asi:

- `Destroy Field` (`2261`, migrada a `spells.xml` + `doDestroyField` con exhaust compartido de 1 s) quita fire/energy/poison fields, excluyendo `1497`, `1498`, `1499` y Crimson Cage
- `Desintegrate` cubre justamente esos solidos (`magic wall` / `wild growth`) y tambien basura/objetos destruibles del suelo fuera de PZ/casas

Duracion y decay de Magic Wall (15s, `DECAY_INTERVAL`): ver [`MAGIC_WALL.md`](MAGIC_WALL.md).

## Reglas de uso

- Si el target esta en otro piso: `You need to be on the same floor.`
- Si no hay linea de tiro: `You cannot throw there.`
- Si no hay nada desintegrable en ese tile: puff en el caster y la rune **no** se consume.
- Si si hay target valido: puff en el tile objetivo y la rune consume una carga normal.

## Hardening del runtime

Tambien se corrigio `SpellScript::castSpell(...)` para que falle cerrado:

- si falta `onCast`, devuelve `false`
- si Lua tira error en `lua_pcall`, devuelve `false`

Con eso evitamos el caso anterior donde una rune/spell roto podia terminar "saliendo bien" y consumiendose sin ejecutar efecto real.

Mas adelante (jul 2026, commit `33557889`) se agrego `SpellScript::safeCast(...)` en los call sites de `game.cpp` / `monster.cpp` para no crashear si el script nunca cargo (archivo faltante / nombre mal). Ver [`SPELL_RUNTIME.md`](SPELL_RUNTIME.md).

## Archivos clave

- `server/YurOTS/ots/data/spells/instant/adito tera.lua`
- `server/YurOTS/ots/data/spells/runes/desintegrate.lua`
- `server/YurOTS/ots/data/actions/scripts/destroyfield.lua`
- `server/YurOTS/ots/source/spells.cpp`
- `server/YurOTS/ots/source/spells.h`
