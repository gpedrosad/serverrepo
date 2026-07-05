# Training Zone Sin PvP

## Objetivo

Evitar que los jugadores puedan hacerse PvP entre ellos dentro de la `training zone`, sin cambiar el PvP del resto del servidor.

La regla aplicada es:

- Si atacante y objetivo estan dentro de `training zone`, no se permite PvP.
- Esto cubre:
  - `player -> player`
  - `player summon -> player`
  - `player -> player summon`
- Los monstruos normales siguen funcionando como antes.

## Zona afectada

La `training zone` se sigue definiendo en:

- [server/YurOTS/ots/data/trainingareas.xml](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/data/trainingareas.xml:1)

Actualmente:

- `fromx=133 fromy=7 fromz=7`
- `tox=160 toy=18 toz=7`
- `exit=160,54,7`

## Implementacion

Se hizo en dos capas para que no quede ningun hueco raro:

1. `Target lock`

Archivo:

- [server/YurOTS/ots/source/game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:5066)

Que hace:

- Impide seleccionar/seguir atacando a otro player dentro de `training zone`.
- Si se intenta atacar ahi, el cliente recibe:
  - `Players cannot PvP inside the training zone.`

2. `Damage lock`

Archivos:

- [server/YurOTS/ots/source/game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:165)
- [server/YurOTS/ots/source/game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:390)

Que hace:

- Aunque algun ataque pase el lock inicial, el dano se fuerza a `0` dentro de `training zone`.
- Aplica tanto para ataques fisicos como para spell/rune damage que entren por esos caminos.

3. `Visual / efectos`

Archivo:

- [server/YurOTS/ots/source/magic.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/magic.cpp:36)

Que hace:

- Evita mostrar efectos ofensivos de PvP bloqueado dentro de `training zone`.
- Esto reduce la sensacion de bug de "parece que pego pero no pega".

## Archivos modificados

- [server/YurOTS/ots/source/game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:1)
- [server/YurOTS/ots/source/magic.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/magic.cpp:1)
- [docs/TRAINING_ZONE_NO_PVP.md](/Users/gonzalo/Desktop/yurots-principal/docs/TRAINING_ZONE_NO_PVP.md:1)

## Comportamiento esperado

Dentro de `training zone`:

- No se puede pegar entre players.
- No deberia aplicarse `pz lock` por esos intentos.
- No deberia quedar `inFight` por ese intento de PvP local.
- Los spells ofensivos entre players no deberian producir dano ahi.

Fuera de `training zone`:

- Todo el PvP mantiene el comportamiento anterior.

## Como debuggearlo

Si algo no funciona, revisar en este orden:

1. Verificar que el tile realmente pertenezca a `trainingareas.xml`.

2. Confirmar que el binario fue compilado con:

- `-DYUR_TRAINING_AREA`

Referencia:

- [server/YurOTS/ots/source/Makefile](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/Makefile:16)

3. Revisar los puntos de decision:

- `Game::playerSetAttackedCreature(...)`
- `GameState::onAttack(..., const MagicEffectClass*)`
- `GameState::onAttack(..., Creature*)`
- `MagicEffectClass::getMagicEffect(...)`

4. Probar estos casos manuales:

- Player A melee a Player B dentro de training.
- Player A rune/spell a Player B dentro de training.
- Summon de Player A contra Player B dentro de training.
- Player A contra summon de Player B dentro de training.
- Repetir las 4 pruebas fuera de training para confirmar que el PvP general no se rompio.

## Si rompe algo

Puntos sensibles:

- Si un spell usa otro camino de dano no cubierto por `GameState::onAttack`, puede requerir un guard adicional.
- Si una zona de training futura se define mal en XML, el bloqueo no se aplicara ahi.
- Si alguien reporta "no puedo atacar" fuera de training, revisar primero coordenadas del tile y si la zona XML quedo demasiado grande.

## Rollback rapido

Si queres revertir esta funcionalidad, sacar los bloques agregados de:

- [server/YurOTS/ots/source/game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:1)
- [server/YurOTS/ots/source/magic.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/magic.cpp:1)

Y recompilar el servidor.
