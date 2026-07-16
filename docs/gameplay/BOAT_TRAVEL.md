# Boat Travel

Sistema de viajes compartido por los NPCs:

- `Nimral`
- `Fargum`

Ambos usan el mismo script:

- `server/YurOTS/ots/data/npc/scripts/boat.lua`

## Reglas actuales

- Viajar **no cambia el temple** del jugador.
- El NPC teleporta al jugador al `sqm` exacto configurado en cada destino.
- Si el jugador ya está parado exactamente en el destino, el NPC no cobra ni repite el viaje.
- Hell Quest no tiene requisito de level.
- Durante una confirmación de viaje, si el jugador responde algo distinto de `yes/si` o `no`, el NPC repregunta.

## Destinos actuales

| Destino | Precio | Keywords | Aterrizaje |
|---------|--------|----------|------------|
| Elfland | `20 gp` | `elfland`, `elf land` | `111 60 6` |
| Epstein Island | `20 gp` | `epstein island`, `epstein` | `85 209 7` |
| Hell Quest | `20 gp` | `hell quest`, `hell` | `347 168 7` |
| Dragon Land | `50 gp` | `dragon land` | `122 119 7` |
| Alice Maze | `20 gp` | `alice maze`, `maze`, `laberinto` | `413 103 7` |
| Gauntlet | `20 gp` | `gauntlet` | `452 41 7` |
| The City | `20 gp` | `city`, `the city` | `171 65 7` |

## Gauntlet

Destino del gauntlet de teleports (ver [`MAPEAR_TP_GAUNTLET.md`](../items-and-map/MAPEAR_TP_GAUNTLET.md)).

- Aterrizaje: `452 41 7` (borde este de la sala 0).
- NPC de vuelta: un solo `Nimral` en la **primera sala** en `450 41 7`.
- Tras las salas puzzle hay una **sala final 3×3** con Wrath, cofre de quest (soft boots) y un solo TP al templo.
- Desde cualquier Nimral/Fargum: `hi` → `gauntlet` → `yes` (20 gp).

## Hell Quest

El `Fargum` de City está en:

- `171 66 7`

El aterrizaje de City está al lado, un `sqm` al norte:

- `171 65 7`

El `Nimral` de Hell Quest está en:

- `346 168 7`

El aterrizaje quedó un `sqm` a la derecha:

- `347 168 7`

Eso evita que el jugador caiga sobre el mismo tile del NPC.

## Notas de implementación

- El chequeo de “ya estás ahí” compara la posición actual del player con el `dest` exacto del viaje.
- El temple no se toca: `boat.lua` no llama a `setPlayerMasterPos`.
- El teleport real se hace con `travelPlayerTo(...)`, no con texto tipo comando.
- `boat.lua` cierra la conversación con `npcResetState()` **antes** del teleport.
- En C++, `Npc::onCreatureDisappear` no llama al script Lua cuando `tele=true`, para evitar re-entrar al `lua_State` del NPC durante `onCreatureSay`.
- Todos los Nimral/Fargum ofrecen la misma lista `ALL_TRAVELS` (incluido Gauntlet).

## Referencias

- `server/YurOTS/ots/data/npc/scripts/boat.lua`
- `server/YurOTS/ots/data/world/npc.xml`
- `docs/items-and-map/MAPEAR_TP_GAUNTLET.md`
- `docs/items-and-map/SESION_EDITOR_MAPA_JUL2026.md`
