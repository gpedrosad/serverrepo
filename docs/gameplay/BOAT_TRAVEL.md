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

| Destino | Precio | Aterrizaje |
|---------|--------|------------|
| Elfland | `20 gp` | `111 60 6` |
| Epstein Island | `20 gp` | `85 209 7` |
| Hell Quest | `20 gp` | `347 168 7` |
| Dragon Land | `50 gp` | `122 119 7` |
| The City | `20 gp` | `171 65 7` |

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

## Referencias

- `server/YurOTS/ots/data/npc/scripts/boat.lua`
- `server/YurOTS/ots/data/world/npc.xml`
- `docs/items-and-map/SESION_EDITOR_MAPA_JUL2026.md`
