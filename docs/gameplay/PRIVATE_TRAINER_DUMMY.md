# Private Trainer Dummy

## Objetivo

Permitir training dentro de casas usando un item de placement dedicado
(`20155`), sin crear un sistema nuevo de combate contra items.

## Implementacion

YurOTS 7.6 no ataca `Item` directamente: el protocolo de ataque apunta a
`Creature`. Para que se vea como item y sea atacable, se creo un monster
trainer:

- Monster: `Private Trainer Dummy`
- Archivo: `server/YurOTS/ots/data/monster/private trainer dummy.xml`
- Apariencia criatura: look type **`57`** (trainer monk, visible en cliente vanilla)
- Registro: `server/YurOTS/ots/data/monster/monsters.xml`
- RME: categoria `YurOTS Training` en `rme-extensions/yurots-creatures.xml`
- Item de placement: **`20155`** (`private trainer dummy`)
- Script Lua: `server/YurOTS/ots/data/actions/scripts/private_trainer_dummy.lua`
- Persistencia runtime: `server/YurOTS/ots/data/private_trainers.xml`
- OTB: `scripts/patch-private-trainer-dummy-otb.js` → `items-zagan-test.otb`

### Nota sobre ids (jul 2026)

| Id | Rol |
|----|-----|
| **`20118`** | `starbinder hood` (casco). Ya **no** se usa como look del monstruo (quedaba invisible sin sprite custom). |
| **`20155`** | Item de placement. **clientId** = kit de sofá (`3902` → `2776`, usable y sin choque de `reverseLookUp`). |

El item en inventario se ve como construction kit (sofá); la criatura colocada se ve como **trainer monk** (look type `57`).

> **Pitfall jul 2026:** reutilizar el clientId del wooden chair kit (`2775` / server `3901`) rompía el Use: `GetItemId()` hace `reverseLookUp(clientId)` 1:1 y el action no corría (o rompía los kits reales).

## Comportamiento

- Es atacable como creature.
- Tiene `trainer="1"` y `skillrate="0.7"` (~30% mas lento que el Trainer Monk normal).
- No hace dano.
- No se puede empujar (`pushable="0"`).
- No empuja ni destruye items (`canpushitems="0"`).
- Tiene armor/defense muy altos e inmunidades para que no se consuma/muera en
  uso normal.
- Solo se puede colocar dentro de una house.
- Cualquier player que este dentro de esa misma house puede colocarlo.
- Maximo 1 Private Trainer Dummy por house.
- Al colocarlo, el item `20155` se consume.
- No hay retiro ni devolucion del item.
- No se coloca sobre puerta de house, teleports, escaleras/floor change, tiles
  ocupados por creatures o tiles donde el monster no pueda pararse.
- Si la house es protection zone, cualquier player que ya este dentro de la
  misma house puede atacar al `Private Trainer Dummy`; la regla no abre PvP ni
  permite atacar otros monsters/players en PZ.

## Como usarlo como item

1. Poné el item **`20155`** en el **suelo** de una house donde estes adentro (SQM libre).
2. Dale **Use** al item en el piso (no use-with).
3. Si pasa las validaciones, el servidor crea el monster en ese mismo SQM,
   guarda la posicion en `private_trainers.xml` y consume el item.

GM:

```text
/i 20155 1
```

Si lo usás desde el inventario te pide: *Put the private trainer dummy on a house tile first.*

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

Si un jugador tiene un item `20155` real en inventario, ese item no se vuelve
atacable por si mismo. La version atacable es la criatura (look type `57`).

**Pitfall:** el clientId del item de placement **no** puede ser el del casco
(`4835`) ni reutilizar el del wooden chair kit (`2775`/`3901`). En 7.6 el
cliente decide Use vs equipar según el DAT/clientId; además `reverseLookUp`
es 1:1 y dos server ids con el mismo clientId rompen el Use.

## Train Wand (`20126`) — ML en casa

Los mages pueden entrenar **magic level** en el Private Trainer Dummy (y en
Trainer Monks del mapa) con el **Train Wand** (`20126`):

- Solo Sorcerer / Master Sorcerer / Druid / Elder Druid.
- Solo dispara contra monstruos con `trainer="1"`.
- No gasta mana (en casas la comida no regenera mana por PZ).
- Cada hit da `addManaSpent(1)` — ~50% del ritmo de Wand of Vortex.
- No sirve para cazar (cancel message fuera de dummies).
- En house PZ usa la misma excepción que melee: `canAttackPrivateTrainerInHouse`
  también aplica al path mágico (`creatureOnPrepareMagicAttack` + filtro PZ de
  `creatureMakeMagic`), así la Train Wand funciona contra el dummy en casa.

Ver [`WANDS.md`](WANDS.md).
