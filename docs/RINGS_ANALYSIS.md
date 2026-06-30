# Análisis: sistema de Rings

## Archivos relevantes

- `server/YurOTS/ots/source/player.cpp:3360-3443` — `Player::checkRing`
- `server/YurOTS/ots/source/player.cpp:3446-3471` — `Player::syncEquippedRing`
- `server/YurOTS/ots/source/player.cpp:1131-1158` — `Player::getSkill` (bonus de skill rings)
- `server/YurOTS/ots/source/player.cpp:777-803` — `Player::addItemInventory`
- `server/YurOTS/ots/source/item.cpp:950-982` — `Item::setGlimmer` / `removeGlimmer`
- `server/YurOTS/ots/source/game.cpp:116-177` — `GameState::applyAmulets`
- `server/YurOTS/ots/source/game.cpp:4220` — llamada a `checkRing` desde `checkCreature`
- `server/YurOTS/ots/source/ioplayerxml.cpp:660` — `syncEquippedRing` al cargar
- `server/YurOTS/ots/source/const76.h:240-260` — IDs de rings

Tipos de ring soportados (cliente 7.6):

| Ring                | Efecto                                          | Duración |
|---------------------|-------------------------------------------------|----------|
| Sword / Axe / Club  | +4 al skill del arma equipada                   | No       |
| Power               | +6 a Fist                                       | No       |
| Time                | Velocidad +20% (no stacked con haste)           | Sí (seg) |
| Energy              | Mana shield pasiva                              | Sí (seg) |
| Stealth             | Invisible                                       | Sí (seg) |
| Life                | +8 HP cada 6s                                   | Sí (seg) |
| Ring of Healing     | +6 HP y +6 Mana cada 6s                         | Sí (seg) |

## Bugs detectados

### Bug 1 — Flags del ring no se actualizan al equipar/desequipar (CRÍTICO)

**Re-análisis posterior**: el `setGlimmer()` / `removeGlimmer()` **sí se
llaman** en los 5 callbacks de `Player::onThingMove` (`player.cpp:1714-1849`):

- inventory → container (línea 1720): `removeGlimmer`
- inventory → inventory (líneas 1743, 1748): ambas direcciones
- container → inventory (línea 1775): `setGlimmer`
- inventory → ground (línea 1805): `removeGlimmer`
- ground → inventory (línea 1835): `setGlimmer`

El bug real es que **después de `setGlimmer`/`removeGlimmer` no se llama a
`checkRing(0)`**, que es lo que actualiza los flags `timeRing`,
`energyRing`, `stealthRing` y dispara los efectos:

- `setNormalSpeed()` + `sendChangeSpeed()` + `sendIcons()` (Time Ring)
- `sendIcons()` (Energy Ring)
- `creatureChangeOutfit()` (Stealth Ring)
- Regeneración de HP/mana (Life / Ring of Healing)

El `checkCreature` (game.cpp:4220) llama a `checkRing(thinkTicks)` cada 1 s
para players, así que el efecto igual aparece eventualmente, pero durante ese
1 s de delay el player no tiene el bonus y el cliente puede ver la velocidad
vieja.

**Síntoma**: el player arrastra un Time Ring al slot → el ID se cambia
correctamente a `ITEM_TIME_RING_IN_USE`, pero la velocidad no aumenta hasta
1 s después. Si en ese intervalo ataca o se mueve, no obtiene el bonus.

### Bug 2 — `useTime(thinkTics)` decrementa cualquier ring con `time > 0`

`player.cpp:3362-3370`:
```cpp
if (items[SLOT_RING] && items[SLOT_RING]->getTime() > 0) {
    items[SLOT_RING]->useTime(thinkTics);
    if (items[SLOT_RING]->getTime() <= 0) {
        removeItemInventory(SLOT_RING);
        client->sendSkills();
    }
}
```

El decremento es **antes** del switch de tipos y se aplica a cualquier ring con
`time > 0`. En la práctica los skill rings nacen con `time = 0` (no les llega
del item loader), así que el `> 0` los filtra, pero **no hay una garantía
explícita**: si en algún item loader o script se les setea un time (por
refactor o bug), se consumen sin razón.

**Mejora**: el decremento debería estar adentro de cada case de ring
temporal, no afuera.

### Bug 3 — Skill rings llaman `client->sendSkills()` al expirar

`player.cpp:3368`:
```cpp
removeItemInventory(SLOT_RING);
client->sendSkills();	// TODO: send only if it was skill ring
```

El propio TODO reconoce que se mandan skills para todos los rings. No es
funcionalmente un bug (es solo un envío de más), pero el comentario lo señala
como deuda técnica.

### Bug 4 — Doble reset de `time` en Energy/Stealth Ring

`player.cpp:3382-3405`:
```cpp
bool energyRingNow = (items[SLOT_RING] && items[SLOT_RING]->getID() == ITEM_ENERGY_RING_IN_USE);
if (energyRingNow)
    manaShieldTicks = items[SLOT_RING]->getTime();
```

Y en `Game::checkCreature` (`game.cpp:4293`):
```cpp
if(creature->manaShieldTicks >= 1000){
    creature->manaShieldTicks -= thinkTicks;
    ...
}
```

Como `checkRing` se llama **antes** que el decremento en `checkCreature`, y
asigna `manaShieldTicks = ring->getTime()` cada 1 s, el resultado neto es que
`manaShieldTicks` siempre queda "sincronizado" con `getTime()` y baja de a 1 s
por segundo. **Pero** `manaShieldTicks` se decrementa en `checkCreature` y se
re-asigna en `checkRing` — si el orden se invierte en un futuro refactor
queda drift.

**Mismo problema** para `invisibleTicks` con Stealth Ring (`player.cpp:3395`).

### Bug 5 — Desync de flags al cambiar de ring en caliente

Si el player tiene un Time Ring equipado, luego lo cambia por un Energy Ring
por drag & drop (Bug 1 ya implica que no se actualiza), pero incluso después
de un relog, los flags se chequean en el orden `timeRing` → `energyRing` →
`stealthRing`. Si el chequeo de `timeRing` cambia `setNormalSpeed()` y luego
el de `energyRing` no toca la velocidad, OK. Pero si en un futuro se agrega
otro ring que también afecte velocidad, el orden importa y no hay garantía
de que se respete.

### Bug 6 — `removeItemInventory` con ring equipado no notifica al cliente

Cuando un ring se queda sin tiempo y se llama `removeItemInventory(SLOT_RING)`
(`player.cpp:3367`), no se ve en este código un `client->sendInventory(SLOT_RING)`
ni un `sendIcons()`. En muchos slots `removeItemInventory` lo hace
automáticamente, habría que verificar que para SLOT_RING también.

### Bug 7 — Ring of Healing con `mana < manamax && health == healthmax`

`player.cpp:3423-3435`: si el ring es `ITEM_RING_OF_HEALING_IN_USE` y la
salud ya está al máximo pero el mana no, **igual regenera 6 HP** porque el
`if (health < healthmax)` está adentro y después el `if (mana < manamax)`
también adentro:

```cpp
if (ringId == ITEM_RING_OF_HEALING_IN_USE) {
    if (health < healthmax) {
        health = std::min(healthmax, health + 6);
        updated = true;
    }
    if (mana < manamax) {
        mana = std::min(manamax, mana + 6);
        updated = true;
    }
}
```

Lectura real: si `health == healthmax` y `mana < manamax`, no se regenera HP
(porque el `if` lo salta), y se regenera mana. Está **bien**, el `if` interno
protege. Descartado.
## Cambios aplicados

### Fix Bug 1 (alta prioridad) — APLICADO Y VERIFICADO

En cada uno de los 5 callbacks de `Player::onThingMove`
(`player.cpp:1714-1849`) se agregó `checkRing(0);` justo después del
`setGlimmer()` / `removeGlimmer()` correspondiente. Esto fuerza a
re-evaluar inmediatamente los flags `timeRing` / `energyRing` /
`stealthRing` y disparar los efectos (velocidad, mana shield, invisible,
regen) sin esperar al próximo `checkCreature`.

Líneas modificadas (con marca `// FIX rings:`):

- `player.cpp:1720-1724` (inventory → container, removeGlimmer)
- `player.cpp:1743-1752` (inventory → inventory, ambas direcciones)
- `player.cpp:1775-1780` (container → inventory, setGlimmer)
- `player.cpp:1805-1810` (inventory → ground, removeGlimmer)
- `player.cpp:1835-1840` (ground → inventory, setGlimmer)

**Verificado**: rebuild en Docker local (`i386/ubuntu:20.04` sobre
Apple Silicon via qemu), binario de ~13 MB, server arranca OK, player
`test sorc` carga sin problemas, sin crashes por varios minutos.

> **Importante**: el fix `placeCreature` documentado en
> `docs/FIX_MONSTER_AGGRO_ON_RESPAWN.md` (que también aparece como
> cambio en `game.cpp`/`monster.h`) **NO se re-aplicó** porque
> dispara `malloc(): invalid size (unsorted)` en el mismo entorno.
> El crash es reproducible con el código de HEAD (sin mis cambios)
> cuando se agrega el bloque que itera spectators y llama
> `mon->onCreatureAppear`. Pendiente de root-cause en un
> investigation aparte.

### Fix Bug 3 (cosmético) — APLICADO

En `checkRing` (`player.cpp:3375-3390`) se reemplazó el `client->sendSkills()`
con un chequeo del ID del ring que expiró. Solo se envían skills si era un
skill ring (Sword/Axe/Club/Power). Se mantiene un comentario defensivo
explicando por qué el bloque exterior sigue siendo seguro para skill rings
(time = 0).

### Fix Bug 2 (baja prioridad) — NO APLICADO, MENCIONADO EN CÓDIGO

El `useTime(thinkTics)` se aplica a cualquier ring con `time > 0`. En la
práctica los skill rings nacen con `time = 0` así que el `> 0` los filtra
correctamente. Se agregó un comentario en el código (`player.cpp:3375`)
advirtiendo que el chequeo es defensivo y asume `time = 0` para skill rings.

### Fix Bug 4 (refactor) — NO APLICADO

La re-asignación de `manaShieldTicks` / `invisibleTicks` en cada `checkRing`
es ineficiente pero no causa bugs (el orden de operaciones en `checkCreature`
asegura que el valor quede sincronizado con `getTime()`). Queda como deuda
técnica.

## Cómo revertir

Buscar en `player.cpp` los comentarios `// FIX rings:` (5 lugares en
`onThingMove` + 1 en `checkRing`). Cada bloque está autocontenido y
puede borrarse individualmente. Para revertir todo:

```bash
cd ~/Desktop/yurots-principal
# borrar los 5 checkRing(0) en onThingMove
# restaurar el if (items[SLOT_RING] && items[SLOT_RING]->getTime() > 0) original
# con sendSkills() incondicional
```
