# 11. Premium y promotion con perks reales

## Que es

Escalera de progreso/estatus en dos ejes:

- **Premium** — donación; exp, training, outfits, regen tier alto
- **Promotion** (Orlan) — lvl 20 + 20k gp; **free y premium**; título de vocación + regen tier intermedio

Regen al comer usa **4 tiers**: free → promoted → premium → promoted+premium. Detalle en [REGEN_FOOD.md](../REGEN_FOOD.md).

## Por que valio la pena

- premium se siente util (cantidad de regen mayor)
- promotion tiene peso para todos (ticks mas rapidos)
- premium + promotion es el combo tope sin ser tan extremo como el sistema viejo de 3 tiers

## Que conviene conservar al portarlo

- perks comprensibles (ticks vs cantidad en pantalla)
- promotion no atada a premium en Orlan; premium sigue siendo ventaja en regen
- persistencia de `promoted` en XML del player

## Riesgos

- si premium da demasiado poder, se siente pay to win
- vectores hardcodeados en C++; tuning requiere recompilar

## Nota de esta copia

- Orlan: `data/npc/scripts/promote.lua` (ingles, lvl 20 + 20k, sin premium obligatorio)
- Vectores: `player.cpp` (`promotedGain*`, `premiumGain*`, `advancedGain*`)
- `queuepremmy = "yes"` en config — cola premium opcional segun config

## Portabilidad

Media. El concepto es bueno, pero depende mucho del modelo economico del otro server.

## Referencias actuales

- `docs/REGEN_FOOD.md`
- `server/YurOTS/ots/data/npc/scripts/promote.lua`
- `server/YurOTS/ots/source/player.cpp`
- `server/YurOTS/ots/source/creature.cpp`
- `server/YurOTS/ots/config.lua`
