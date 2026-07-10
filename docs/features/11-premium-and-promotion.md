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

## Comportamiento actual del vencimiento

- `premiumTicks` baja mientras el personaje esta **online**.
- Cuando pasa de un valor positivo a `0`, el server hace tres cosas enseguida:
  - teletransporta al personaje a su templo (`masterPos`);
  - le resetea el outfit a ropa basica segun sexo:
    - mujer: `PLAYER_FEMALE_1`
    - hombre / oldmale: `PLAYER_MALE_1`
    - colores base: `head=20`, `body=30`, `legs=40`, `feet=50`
  - manda el mensaje:
    - `Se te acabo el premium. Fuiste enviado al templo con la ropa basica.`

## Alcance y limites

- Esto corre en `Player::checkPremium(int thinkTics)`.
- Solo dispara una vez en la transicion `premiumTicks > 0 -> 0`.
- No cambia `promoted`; promotion sigue intacta.
- Si `freepremmy = "yes"`, el contador puede seguir bajando, pero **no** se fuerza el
  teleport ni el reseteo de ropa porque el server sigue considerando premium
  habilitado globalmente.

## Portabilidad

Media. El concepto es bueno, pero depende mucho del modelo economico del otro server.

## Referencias actuales

- `docs/REGEN_FOOD.md`
- `server/YurOTS/ots/data/npc/scripts/promote.lua`
- `server/YurOTS/ots/source/player.cpp`
- `server/YurOTS/ots/source/creature.cpp`
- `server/YurOTS/ots/config.lua`
