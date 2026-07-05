# Respawn con animación — REVERTIDO

> **Estado:** no aplicado en producción (revertido el 2026-07-04).
> El respawn clásico volvió al comportamiento documentado en `docs/CAMBIOS_SESION_2026-07-03.md` §8.

## Comportamiento actual (restaurado)

- Si el `spawntime` venció y un player normal **ve** el tile de spawn → el monstruo **no** aparece todavía; el timer **no** se reinicia.
- Cuando el tile deja de estar visible → respawn en el siguiente chequeo (~20 s).
- Si nadie ve el tile → respawn inmediato en el siguiente chequeo.

## Qué se revirtió

- Secuencia de efectos mágicos antes del spawn
- `Game::animatedSpawnStep` y flag `pendingAnimatedSpawn`
- Spawn forzado con gente mirando

## Historial

Implementado el 2026-07-03 (commit `c991e24`), revertido el 2026-07-04 por pedido de gameplay.
