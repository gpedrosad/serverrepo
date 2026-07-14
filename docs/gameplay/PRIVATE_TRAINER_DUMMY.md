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
- Tiene `trainer="1"` y `skillrate="0.7"` (~30% mas lento que el Trainer Monk normal).
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
- Si la house es protection zone, cualquier player que ya este dentro de la
  misma house puede atacar al `Private Trainer Dummy`; la regla no abre PvP ni
  permite atacar otros monsters/players en PZ.

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

## Train Wand (`20126`) — ML en casa

Los mages pueden entrenar **magic level** en el Private Trainer Dummy (y en
Trainer Monks del mapa) con el **Train Wand** (`20126`):

- Solo Sorcerer / Master Sorcerer / Druid / Elder Druid.
- Solo dispara contra monstruos con `trainer="1"`.
- No gasta mana (en casas la comida no regenera mana por PZ).
- Cada hit da `addManaSpent(1)` — ~50% del ritmo de Wand of Vortex.
- No sirve para cazar (cancel message fuera de dummies).

Ver [`WANDS.md`](WANDS.md).
