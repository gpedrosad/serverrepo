# Fix: Monstruos no atacan a player quieto al respawnear

> **Estado actual: NO APLICADO** — el fix del segundo bloque (la
> iteración de spectators en `Game::placeCreature`) causa
> `malloc(): invalid size (unsorted)` y SIGABRT en el entorno local
> de pruebas (Docker `i386/ubuntu:20.04` sobre Apple Silicon via qemu).
> El crash es reproducible y NO depende del fix de `setGlimmer`/`friend
> class Game` — basta agregar el loop que itera espectadores en
> `placeCreature` para que el server muera al cargar el spawn inicial.
>
> El fix de `syncEquippedRing` descrito abajo **sí funciona** y se
> aplicó por separado (ver `docs/RINGS_ANALYSIS.md`), pero no resuelve
> el problema de "monstruo no ataca player quieto al respawnear" — eso
> requiere el segundo bloque que está pendiente de investigación.

## Problema

Cuando un monstruo respawneaba sobre (o muy cerca de) un player que **no se
estaba moviendo**, el monstruo quedaba en `STATE_IDLE` y nunca lo atacaba. El
player tenía que moverse para que el monstruo reaccionara.

## Causa raíz

El flujo de "ver a un player cercano" en `Monster` se gatilla únicamente por:

- `Monster::onCreatureMove()` (`monster.cpp:855`) → llamada cuando OTRO creature
  se mueve dentro del rango de visión.
- `Monster::onCreatureEnter()` (`monster.cpp:913`) → llamada cuando OTRO creature
  aparece/entra al rango.

Y `Monster::startThink()` (`monster.cpp:1150`) — que es lo único que programa
el `eventCheckAttacking` cada 500 ms — solo se invoca desde
`Monster::selectTarget()` (`monster.cpp:973`).

**Resultado**: si el player está quieto, ninguno de los dos hooks se dispara, el
monstruo nunca llama a `selectTarget`, nunca se programa
`eventCheckAttacking`, y el monstruo respawneado no ataca hasta que el player
mueva un solo paso.

Adicionalmente, en `Game::placeCreature` (`game.cpp:1406`) la línea:

```cpp
//c->eventCheckAttacking = addEvent(makeTask(2000, ...));
```

está **comentada**, así que ni siquiera al colocar la criatura se programa el
ciclo de ataque como fallback.

`Game::sendAddThing()` (`game.cpp:5274`) sí itera los spectators de la posición
y les llama `onThingAppear`, pero:
- En `Player::onThingAppear` (`player.cpp:1868`) solo se envía un paquete visual
  al cliente, no se genera aggro.
- En `Monster::onThingAppear` (`monster.cpp:827`) el "thing" que llega es **el
  propio monstruo nuevo**, así que los monstruos ya spawneados tampoco
  reaccionan contra el nuevo.

## Fix aplicado

En `server/YurOTS/ots/source/game.cpp`, dentro de `Game::placeCreature()`,
justo después de programar `eventCheck` y antes del `}` del `if(success)`:

```cpp
// FIX yurots-principal: detectar creatures ya presentes al spawnear.
// Sin esto, un monstruo que respawnea junto a un player quieto nunca
// recibe onCreatureAppear/onCreatureMove, queda en STATE_IDLE y no ataca.
if(Monster* mon = dynamic_cast<Monster*>(c)) {
    SpectatorVec nearbyList;
    SpectatorVec::const_iterator cit;
    getSpectators(Range(c->pos, true), nearbyList);
    for(cit = nearbyList.begin(); cit != nearbyList.end(); ++cit) {
        if(*cit != c) {
            mon->onCreatureAppear(*cit);
        }
    }
}
```

`Monster::onCreatureAppear` (`monster.cpp:777`) ya implementa la lógica
correcta: si el creature está en rango y es atacable, llama a
`onCreatureEnter` → `selectTarget` → `startThink` → agenda el ciclo de ataque.

## Cómo revertir si rompe algo

1. Abrir `server/YurOTS/ots/source/game.cpp`.
2. Localizar el bloque que comienza con el comentario
   `// FIX yurots-principal: detectar creatures ya presentes al spawnear.`
3. Borrar **todo el bloque** (las 13 líneas, incluido el `if(Monster* mon = ...`)
   y su `}` de cierre).
4. Recompilar el server.

Si el problema fuera que ahora los monstruos detectan players a través de
paredes: revisar `Monster::isCreatureReachable()` y
`Monster::isCreatureAttackable()` — son los filtros que
`onCreatureAppear`/`onCreatureEnter` aplican antes de llamar a
`selectTarget`. El fix los respeta, pero si en el futuro cambia su
semántica conviene volver a chequear.

Si el problema fuera performance (muchos monstruos spawneando en zonas
pobladas): envolver el bloque con `#ifdef YUR_SPAWN_AGGRO_FIX` y apagar el
flag en `config.lua` si se agrega una opción.
