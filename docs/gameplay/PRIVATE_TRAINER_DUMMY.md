# Private Trainer Dummy

## Objetivo

Permitir training dentro de casas usando el sprite del item custom `20118`, sin
crear un sistema nuevo de combate contra items.

## Implementacion

YurOTS 7.6 no ataca `Item` directamente: el protocolo de ataque apunta a
`Creature`. Para que se vea como item y sea atacable, se creo un monster
trainer:

- Monster: `Private Trainer Dummy`
- Archivo: `server/YurOTS/ots/data/monster/private trainer dummy.xml`
- Apariencia: `<look type="20118" .../>`
- Registro: `server/YurOTS/ots/data/monster/monsters.xml`
- RME: categoria `YurOTS Training` en `rme-extensions/yurots-creatures.xml`
- Item de placement: `20118`
- Script Lua: `server/YurOTS/ots/data/actions/scripts/private_trainer_dummy.lua`
- Persistencia runtime: `server/YurOTS/ots/data/private_trainers.xml`

## Comportamiento

- Es atacable como creature.
- Tiene `trainer="1"` y `skillrate="1.0"`, igual que el Trainer Monk normal.
- No hace dano.
- No se puede empujar (`pushable="0"`).
- No empuja ni destruye items (`canpushitems="0"`).
- Tiene armor/defense muy altos e inmunidades para que no se consuma/muera en
  uso normal.
- Solo se puede colocar dentro de una house.
- Solo el owner de la house puede colocarlo.
- Maximo 1 Private Trainer Dummy por house.
- Al colocarlo, el item `20118` se consume.
- No hay retiro ni devolucion del item.
- No se coloca sobre puerta de house, teleports, escaleras/floor change, tiles
  ocupados por creatures o tiles donde el monster no pueda pararse.

## Como usarlo como item

El player recibe el item `20118` y lo usa sobre un SQM valido dentro de su
house. Si pasa las validaciones, el servidor crea el monster en ese SQM, guarda
la posicion en `private_trainers.xml` y consume el item.

El archivo `private_trainers.xml` es data runtime: no se versiona, pero los
scripts de backup/deploy lo conservan junto a `houseitems.xml`.

## Como usarlo en mapa/RME

Tambien se puede colocar como criatura/spawn con nombre exacto:

```xml
<monster name="Private Trainer Dummy" x="0" y="0" z="7" spawntime="60" />
```

En RME aparece en:

```text
Creatures -> YurOTS Training -> Private Trainer Dummy
```

## Nota importante

Si un jugador tiene un item `20118` real en inventario o en una casa, ese item
no se vuelve atacable por si mismo. La version atacable es la criatura que usa
`20118` como look visual.

Si una house o el SQM elegido es protection zone y el motor no permite atacar
desde ahi, el dummy puede colocarse pero el cliente no podra usarlo para
entrenar. En ese caso hay que ajustar el mapa/regla de combat aparte.
