# docs/_archive/

Documentación **archivada** — obsoleta, superseded, o one-off.

**NO leer salvo que estés investigando historia del proyecto** o buscando el contexto original de un cambio. Los docs vigentes están en `docs/`, `docs/systems/`, `docs/gameplay/`, `docs/items-and-map/` y `docs/features/`. El índice maestro está en [../INDEX.md](../INDEX.md).

## ¿Por qué están acá?

| Doc | Razón de archivo |
|-----|------------------|
| `CAMBIOS_SESION_2026-07-03.md` | Resumen de sesión one-off. Lo que sigue vigente quedó reflejado en `docs/PROYECTO.md`, `docs/gameplay/GEMS.md`, `docs/gameplay/ML_RATE.md`, etc. |
| `SPAWN_ANIMATION.md` | Nota de reversión puntual. El comportamiento vigente está documentado en `docs/PROYECTO.md` y `docs/items-and-map/SESION_EDITOR_MAPA_JUL2026.md`. |
| `RINGS_ANALYSIS.md` | Análisis inicial del sistema de rings. El estado actual está en `docs/PROYECTO.md` y los cambios aplicados en el commit `fix rings` referenciado por el CHANGELOG. |
| `STAIRS_DEFAULT_ROLLBACK.md` | Rollback de un parche puntual. El estado del motor (default) está vigente. |
| `FIX_OT_STABILITY_KICKS_AND_HANG.md` | Superseded por `docs/systems/PREVENT_OT_HANGS.md` y `docs/systems/OT_HANG_ROOT_CAUSE_SEND_BLOCKING.md`. |
| `FIX_PLAYER_KICKS_READFROMSOCKET.md` | Superseded por `docs/systems/PREVENT_OT_HANGS.md` y `docs/systems/SOCKET_DEBUG_LOGGING.md`. |
| `FIX_MONSTER_AGGRO_ON_RESPAWN.md` | Fix que terminó rompiendo el build (`malloc(): invalid size`). NO se aplicó. |
| `DARK_RODO_AUDIT.md` | Auditoría one-off (jun 2026). La mayoría de los fixes están aplicados en `data/npc/scripts/runes.lua`, `data/npc/scripts/lib/npc.lua`, `data/world/npc.xml` y `source/npc.cpp`. |
| `ZAGAN_TEST_HANDOFF.md` | Handoff técnico inicial. Superseded por `docs/items-and-map/ZAGAN_TEST_ITEMS.md` y `docs/items-and-map/SESION_EDITOR_MAPA_JUL2026.md`. |
| `DEPLOY-PENDIENTE-VPS-JUL2026.md` | Checklist operativo one-off (jul 2026). El procedimiento vigente es `scripts/deploy/README-DEPLOY-VPS.md`. |
| `PUSH-MAIN-JUL2026-SPELLS-NPC-NO-VPS.md` | Nota de release one-off (jul 2026). Spells vigentes en `docs/gameplay/SPELL_*.md`. |

## Reglas para esta carpeta

- No agregar docs nuevos acá sin pensar dos veces: si el contenido sigue vigente, va en otro lugar.
- Si un doc acá vuelve a ser relevante, moverlo a su carpeta correcta y borrarlo de acá.
- Git preserva el historial, así que aunque se borren, el contenido se puede recuperar con `git log -- <path>`.
