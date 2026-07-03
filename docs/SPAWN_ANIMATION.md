# Respawn con animación ante espectadores

## Comportamiento

Cuando un spawnpoint clásico (`spawn.cpp`) cumple su `spawntime`:

| Situación | Qué pasa |
|-----------|----------|
| Nadie ve el tile de spawn | El monstruo aparece **al instante** (sin animación). |
| Algún player normal ve el tile (`Player::CanSee`) | Se ejecuta una **secuencia de 3 efectos** y luego aparece el monstruo. |

El timer **no se reinicia** por tener gente cerca: en cuanto vence el `spawntime`, el spawn entra en cola de aparición (inmediata o animada).

## Animación

Secuencia sobre el tile de spawn, un paso cada **800 ms**:

1. `NM_ME_YELLOW_RINGS` — anillos amarillos (aviso inicial)
2. `NM_ME_MAGIC_ENERGIE` — energía mágica (carga)
3. `NM_ME_PUFF` — humo (aparición)

Tras el tercer paso (~2,4 s desde el inicio) se llama a `Spawn::respawn()` y el monstruo entra al mapa.

Los efectos se envían solo a **players** en rango de espectadores; GMs con `access >= ACCESS_PROTECT` no bloquean ni disparan la rama animada.

## Archivos tocados

- `server/YurOTS/ots/source/spawn.h` — flag `pendingAnimatedSpawn`, API `runAnimatedRespawnStep`
- `server/YurOTS/ots/source/spawn.cpp` — lógica de animación y decisión instantánea vs animada
- `server/YurOTS/ots/source/game.h` / `game.cpp` — `Game::animatedSpawnStep` con `gameLock` para callbacks del scheduler

## Constantes (spawn.cpp)

```cpp
static const int SPAWN_ANIM_STEP_MS = 800;
static const int SPAWN_ANIM_STEPS = 3;
```

Para cambiar duración o intensidad visual, ajustar esos valores o el `switch` de `sendSpawnAppearEffects`.

## Qué no cambia

- Spawn inicial al arrancar el server (`Spawn::startup`) — sin animación.
- Monstruos furiosos al morir (`Game::trySpawnRageMonster`) — lógica separada en `game.cpp`.
- Cadencia global del chequeo de spawns — sigue siendo cada **20 s** (`SpawnManager::startup`).

## Cómo revertir

1. En `spawn.cpp`, restaurar el bloque `idle()` que hacía `continue` cuando `playerFound` (ver historial del 2026-07-03).
2. Eliminar `sendSpawnAppearEffects`, `beginAnimatedRespawn`, `runAnimatedRespawnStep` y el flag `pendingAnimatedSpawn`.
3. Eliminar `Game::animatedSpawnStep` de `game.cpp` / `game.h`.
4. Recompilar el server.

## Verificación manual

1. Matar un monstruo en un spawn con `spawntime` corto (p. ej. 60 s en XML → 60 000 ms internos).
2. Quedarse quieto mirando el tile de spawn hasta que venza el timer.
3. Deberías ver los 3 efectos y luego el monstruo, sin tener que alejarte.
4. Repetir sin nadie en pantalla: el monstruo debe aparecer en el siguiente tick de spawn (~20 s) sin efectos previos.
